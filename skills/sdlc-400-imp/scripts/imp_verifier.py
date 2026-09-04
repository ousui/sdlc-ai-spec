"""Recompute IMP canonical content, immutable Results and authority without writes."""
from __future__ import annotations

from dataclasses import replace
import json
from types import SimpleNamespace

from packages.sdlc_artifact_store import ArtifactStore, DomainVerification, compute_sha256
from packages.sdlc_runtime import FrozenArtifactAuthorityVerifier, parse_canonical_artifact
from packages.sdlc_runtime.canonical import authority_reference

from imp_binding import resolve_binding
from imp_builder import ImpBuilder, final_confirmation_from_payload
from imp_candidate import verify_persisted_candidates
from imp_check import evaluate
from imp_common import Binding, canonical, require
from imp_executor import (
    PROJECT_CHECK_CONTRACT, _project_command, validate_execution_history,
    verify_pre_execution_readback,
)
from imp_method import validate_method
from imp_readiness import _control_rework, provider_read_only, validate_chain, verify_claim_snapshot
from imp_result import (
    read_member, read_state, retained_result_snapshot, snapshot_reference,
    verify_result_set,
)


class _CandidateLocalChecks(FrozenArtifactAuthorityVerifier):
    """Check intrinsic frozen records without granting their former Authority."""
    def _verify_authority_file(self, reference, revision, confirmation):
        authority_reference(confirmation["Authority Reference"])


class ImpVerifier:
    def __init__(self, project_root):
        self.project_root = project_root

    def verify_payload(self, stored):
        return self._verify_payload(stored, local_candidate=False)

    def verify_recovery_candidate(self, stored):
        require(stored.control.state == "frozen", "IMP_CONTROL_RECOVERY_INVALID",
                "Only a frozen historical Payload can be a control-recovery candidate")
        return self._verify_payload(stored, local_candidate=True)

    def _verify_payload(self, stored, *, local_candidate):
        store = ArtifactStore.open_read_only(self.project_root)
        state = read_state(stored)
        binding = (Binding(**state["binding"]) if local_candidate else
                   resolve_binding(store, state["binding"]["reference"]))
        require(state["binding"] == binding.to_dict(), "IMP_BINDING_MISMATCH",
                "IMP does not preserve the exact upstream Context, Binding and Lineage")
        parsed = parse_canonical_artifact(stored.payload.primary_blob)
        require(parsed.front_matter.get("context") == binding.context_reference
                and binding.context_reference != binding.upstream_reference,
                "IMP_BINDING_MISMATCH", "IMP Context must equal the upstream's real CTX relationship")
        require(parsed.front_matter.get("inputs") == state["request"]["artifact_inputs"],
                "IMP_BINDING_MISMATCH", "IMP input relationships disagree with the retained request")
        claim = state["claim"]
        require((claim["artifact_id"], claim["revision"], claim["binding_reference"], claim["binding_lineage"]) ==
                (stored.control.artifact_id, stored.control.revision, binding.reference, binding.lineage),
                "IMP_BINDING_MISMATCH", "IMP identity or Binding differs from its Claim Reservation")
        reservation = stored.control.claim
        require(reservation is not None and (reservation.binding_lineage, reservation.attempt, reservation.owner) ==
                (binding.lineage, str(claim["attempt"]), claim["owner"]),
                "IMP_BINDING_MISMATCH", "IMP Reservation Owner or Attempt mismatch")
        require(claim["execution_scope"] == list(binding.execution_scope)
                and claim["dependency_results"] == state["request"]["dependencies"]
                and claim["rework_references"] == state["request"]["rework"],
                "IMP_BINDING_MISMATCH", "Claim Scope, Input or Rework mismatch")
        subjects = state["request"]["rework_subjects"]
        require(set(subjects) == {item for item in state["request"]["rework"]
                                 if item.startswith(("VFY-", "RLS-"))},
                "IMP_BINDING_MISMATCH", "Retained Rework Subjects do not match the exact Control Input Set")
        if not local_candidate:
            for control, subject in subjects.items():
                _control_rework(store, control, binding, SimpleNamespace(**claim), subject_reference=subject)
        method = validate_method(state["method"], binding)
        require(canonical(method) == canonical(state["method"]), "IMP_READINESS_FAILED", "Method is not canonical")
        validate_execution_history(
            method, state.get("completed_operations"), state.get("actions")
        )
        verify_result_set(store, stored, state, local_candidate=local_candidate)
        verify_persisted_candidates(stored, state, binding)
        if state.get("pre_execution") is not None:
            verify_pre_execution_readback(stored, state)
        if state["request"].get("control_recovery") and not local_candidate:
            from imp_recovery import verify_recovery_evidence
            verify_recovery_evidence(store, stored, state)
        if state["stage"] == "executed":
            require(state.get("pre_execution"), "IMP_READINESS_FAILED", "Execution has no persisted pre-execution readback")
            specs = method["checks"]
            require([item["id"] for item in state["checks"]] == [item["id"] for item in specs],
                    "IMP_CHECK_FAILED", "Applicable Check set is incomplete")
            records = {row["resource"]: row for row in state["resources"]}
            for check, spec in zip(state["checks"], specs):
                expected_path = (
                    spec.get("cwd", ".")
                    if spec["kind"] == "project_command"
                    else spec["path"]
                )
                require(check == {
                    "id": spec["id"], "name": spec["name"],
                    "resource": spec["resource"], "path": expected_path,
                    "result": check.get("result"),
                    "evidence_member": "EVD-" + spec["id"],
                }, "IMP_CHECK_FAILED",
                    "Stored Check identity or target differs from its Method")
                evidence = json.loads(read_member(stored, check["evidence_member"]).raw_bytes)
                require(evidence.get("result") == check["result"] and
                        (evidence.get("exit_code") == 0) == (check["result"] == "pass"),
                        "IMP_CHECK_FAILED", "Local Check result differs from Execution Evidence")
                record = records[check["resource"]]
                snapshot = (retained_result_snapshot(stored, record) if local_candidate else
                            snapshot_reference(store, record["result_reference"], check["resource"], local=stored))
                if spec["kind"] == "project_command":
                    _, recorded = _project_command(spec)
                    expected_keys = {
                        "contract", "resource", "subject_sha256", "command",
                        "executed_command", "cwd", "timeout_seconds", "isolation",
                        "sandbox", "network", "exit_code", "stdout", "stderr", "result",
                    }
                    require(set(evidence) == expected_keys
                            and evidence["contract"] == PROJECT_CHECK_CONTRACT
                            and evidence["resource"] == spec["resource"]
                            and evidence["subject_sha256"] == compute_sha256(canonical(snapshot))
                            and evidence["command"] == spec["command"]
                            and evidence["executed_command"] == recorded
                            and evidence["cwd"] == spec.get("cwd", ".")
                            and evidence["timeout_seconds"] == spec.get("timeout_seconds", 120)
                            and evidence["isolation"] == "complete-resource-snapshot"
                            and evidence["sandbox"] in {
                                "python-audit-hook", "darwin-sandbox-exec", "linux-bwrap",
                            }
                            and evidence["network"] == "denied-offline-no-credentials",
                            "IMP_CHECK_FAILED",
                            "Project Check Evidence is not bound to the immutable Result and declared adapter")
                    continue
                command = evidence.get("command", [])
                require(len(command) == 8 and command[-3] == spec["kind"] and command[-1] == spec.get("expected", ""),
                        "IMP_CHECK_FAILED", "Execution Evidence is bound to another Check")
                target = next((item for item in snapshot["entries"] if item["path"] == check["path"]), None)
                if check["result"] == "pass":
                    require(target is not None, "IMP_CHECK_FAILED", "Check subject is absent from immutable Result")
                    raw = bytes.fromhex(target["content_hex"])
                    require(evaluate(spec["kind"], raw, spec.get("expected", "")), "IMP_CHECK_FAILED",
                            "Immutable Result does not satisfy the recorded local Check")
                    observed = json.loads(evidence["stdout"])
                    require(observed.get("sha256") == target["sha256"], "IMP_CHECK_FAILED",
                            "Check did not observe the final immutable Subject")
        else:
            require(state["stage"] == "prepared" and not state.get("checks"),
                    "IMP_RESULT_INCOMPLETE", "Unsupported IMP execution state")
        builder = ImpBuilder(self.project_root)
        unsigned = builder.build(
            artifact_id=stored.control.artifact_id, revision=stored.control.revision,
            state=state, members=stored.payload.members, final_confirmation=None,
            _candidate_only=local_candidate,
        )
        final = final_confirmation_from_payload(
            stored.payload.primary_blob, state, unsigned.subject_digest
        )
        rebuilt = builder.build(
            artifact_id=stored.control.artifact_id,
            revision=stored.control.revision,
            state=state,
            members=stored.payload.members,
            final_confirmation=final,
            _candidate_only=local_candidate,
        )
        require(rebuilt.raw_bytes == stored.payload.primary_blob and rebuilt.status == stored.payload.artifact_status
                and rebuilt.manifest.raw_bytes == stored.payload.manifest.raw_bytes,
                "IMP_RESULT_INCOMPLETE", "Canonical Artifact differs from recomputed IMP records")
        if stored.control.state == "frozen":
            verifier = _CandidateLocalChecks if local_candidate else FrozenArtifactAuthorityVerifier
            verifier(self.project_root).verify(
                f"{stored.control.artifact_id}@{stored.control.revision}", stored,
            )
        return state

    def verify(self, reference, revision):
        state = self.verify_payload(revision)
        require(revision.payload.artifact_status in {"ready", "ready_with_exception"},
                "IMP_FINAL_CONFIRMATION_STALE", "IMP is not ready to freeze")
        provider = provider_read_only(self.project_root)
        claim = provider.resolve(state["binding"]["reference"]) if provider else None
        require(claim is not None and claim.state in {"active", "completed"}, "IMP_CLAIM_CONFLICT",
                "Current Claim is not eligible for finalization")
        verify_claim_snapshot(revision, state, claim)
        binding = resolve_binding(ArtifactStore.open_read_only(self.project_root), claim.binding_reference)
        validate_chain(ArtifactStore.open_read_only(self.project_root), binding, claim)
        prospective = replace(revision, control=replace(revision.control, state="frozen"))
        proof = FrozenArtifactAuthorityVerifier(self.project_root).verify(reference, prospective)
        return DomainVerification(reference, proof.payload_binding, True, "IMP is locally ready for VFY after Claim complete")
