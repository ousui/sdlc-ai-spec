"""Strict same-Lineage frozen control recovery; candidates convey no Authority."""
from __future__ import annotations

from copy import deepcopy
import json

from packages.sdlc_artifact_store import ArtifactStoreError, compute_sha256
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_phasekit.common import PhaseKitError
from packages.sdlc_runtime import parse_canonical_artifact
from packages.sdlc_runtime.authority import FrozenAuthorityVerificationError

from imp_common import ImpError, canonical, exact_base, require
from imp_result import read_member, retained_result_snapshot, snapshot_reference


def _candidate(store, reference):
    from imp_verifier import ImpVerifier
    artifact, revision = exact_base(reference, "IMP")
    stored = store.read_revision(artifact, revision)
    state = ImpVerifier(store.project_root).verify_recovery_candidate(stored)
    require(state["stage"] == "executed" and not state.get("failure")
            and not state["method"].get("open_items") and not state["method"].get("exceptions")
            and not state["method"].get("external_effects")
            and not any(item.startswith(("VFY-", "RLS-")) for item in state["request"]["rework"]),
            "IMP_CONTROL_RECOVERY_INVALID", "Unresolved product obligations or external effects require execution")
    return stored, state


def _no_product_return(store, reference, binding):
    # A caller must not conceal an unresolved Return by omitting --input.
    # Only the latest frozen control Revision of each Lineage is applicable.
    catalog = ArtifactCatalog(store)
    artifact_id, _ = exact_base(reference, "IMP")
    for phase in ("VFY", "RLS"):
        for artifact in catalog.list_artifacts(phase):
            frozen = [item for item in catalog.list_revisions(artifact.artifact_id) if item.state == "frozen"]
            if not frozen:
                continue
            latest = max(frozen, key=lambda item: item.revision)
            parsed = parse_canonical_artifact(store.read_revision(artifact.artifact_id, latest.revision).payload.primary_blob)
            for table in parsed.tables:
                for row in table.rows:
                    if row.get("Return Phase") != "IMP" and row.get("Follow-up Disposition") != "return_imp":
                        continue
                    values = " ".join(row.values())
                    require(artifact_id not in values and binding.reference not in values,
                            "IMP_CONTROL_RECOVERY_INVALID", "Unresolved product Return disqualifies no-change recovery")


def resolve_recovery(store, binding, current, reference, *, previous=None):
    """Pure admission: exact candidate, current causal sequence, genuine failure."""
    from imp_readiness import current_result, provider_read_only
    artifact, revision = exact_base(reference, "IMP")
    require(current is not None and artifact == current.artifact_id,
            "IMP_CONTROL_RECOVERY_INVALID", "Recovery must keep the same stable IMP Artifact Lineage")
    retained = bool(reference in current.rework_references and revision < current.revision
                    and ((previous and previous["request"].get("control_recovery") == reference)
                         or (previous is None and current.state == "active")))
    require(retained or (revision == current.revision and current.state in {"completed", "abandoned"}),
            "IMP_CONTROL_RECOVERY_INVALID", "Recovery reference is stale or does not identify the Current frozen Attempt")
    stored, state = _candidate(store, reference)
    require(state["binding"] == binding.to_dict()
            and current.binding_reference == binding.reference
            and sorted(current.execution_scope) == sorted(binding.execution_scope),
            "IMP_CONTROL_RECOVERY_INVALID", "Recovery cannot change Binding, Context, Scope or Outcome")
    _no_product_return(store, reference, binding)
    if not retained:
        if current.state == "abandoned":
            require((current.abandon_reason or "").startswith("complete:"),
                    "IMP_CONTROL_RECOVERY_INVALID", "Frozen abandonment must record the exact complete failure")
        else:
            try:
                current_result(store, provider_read_only(store.project_root), reference)
            except ImpError as exc:
                require(exc.code == "IMP_DEPENDENCY_INCOMPLETE", "IMP_CONTROL_RECOVERY_INVALID",
                        "Candidate failure is not a recoverable input-chain failure")
            except ArtifactStoreError:
                # Candidate-local verification already proved that the retained
                # IMP closure is complete. A later Store miss can therefore
                # only belong to the recursively resolved former input chain.
                pass
            except (PhaseKitError, FrozenAuthorityVerificationError) as exc:
                require("Authority Reference" in str(exc), "IMP_CONTROL_RECOVERY_INVALID",
                        "Candidate failure is not a recoverable Lifecycle Authority failure")
            else:
                raise ImpError("IMP_CONTROL_RECOVERY_INVALID", "Current frozen Result remains valid; no control recovery is needed")
    return stored, state


def recovery_method(store, reference, supplied=None):
    _, candidate = _candidate(store, reference)
    method = deepcopy(candidate["method"])
    method["operations"] = []
    require(supplied is None or canonical(supplied) == canonical(method),
            "IMP_CONTROL_RECOVERY_INVALID", "No-change recovery must retain the exact Method and local Checks without product operations")
    return method


def verify_candidate_resources(store, reference, binding, roots, snapshots):
    stored, candidate = _candidate(store, reference)
    require(candidate["binding"] == binding.to_dict()
            and roots == {row["resource"]: row["root"] for row in candidate["resources"]},
            "IMP_CONTROL_RECOVERY_INVALID", "Recovery candidate Binding or Resource roots differ")
    for row in candidate["resources"]:
        require(snapshots[row["resource"]] == retained_result_snapshot(stored, row),
            "IMP_CONTROL_RECOVERY_INVALID", "Current Resource differs from the immutable recovery candidate Result")
    return stored, candidate


def recovery_evidence(store, state, snapshots):
    """Evidence is derived from current readbacks after the new Checklist."""
    reference = state["request"]["control_recovery"]
    stored, candidate = _candidate(store, reference)
    fields = ("id", "resource", "baseline_reference", "change_reference", "result_reference", "changed_scope", "steps")
    records = []
    for row in candidate["resources"]:
        snapshot = retained_result_snapshot(stored, row)
        require(snapshots[row["resource"]] == snapshot, "IMP_CONTROL_RECOVERY_INVALID",
                "Post-checklist Resource readback differs from the frozen candidate")
        records.append({"candidate_result": {key: row[key] for key in fields},
                        "observed_sha256": compute_sha256(canonical(snapshot))})
    return {
        "contract": "sdlc-ai-spec/imp-control-recovery-evidence/v1",
        "candidate": reference, "candidate_payload": stored.verification_binding,
        "candidate_binding": candidate["binding"], "claim": state["claim"],
        "pre_execution": state["pre_execution"], "resources": records,
        "result": "pass", "authority_inherited": False,
    }


def verify_recovery_evidence(store, stored, state):
    reference = state["request"]["control_recovery"]
    artifact, revision = exact_base(reference, "IMP")
    require(artifact == stored.control.artifact_id and revision < stored.control.revision
            and reference in state["claim"]["rework_references"]
            and reference not in state["request"]["artifact_inputs"],
            "IMP_CONTROL_RECOVERY_INVALID", "Recovery is a same-Artifact candidate, not an authoritative Input")
    _, candidate = _candidate(store, reference)
    require(state["binding"] == candidate["binding"]
            and state["claim"]["attempt"] > candidate["claim"]["attempt"]
            and canonical(state["method"]) == canonical(recovery_method(store, reference))
            and not state["completed_operations"] and not state["actions"],
            "IMP_CONTROL_RECOVERY_INVALID", "Recovery cannot inherit the previous Attempt or change its Method")
    require([(row["id"], row["resource"], row["root"]) for row in state["resources"]] ==
            [(row["id"], row["resource"], row["root"]) for row in candidate["resources"]],
            "IMP_CONTROL_RECOVERY_INVALID", "Recovery Result identities or Resource roots differ")
    if state["stage"] == "executed":
        snapshots = {row["resource"]: snapshot_reference(store, row["result_reference"], row["resource"], local=stored)
                     for row in state["resources"]}
        require(all(row["baseline_reference"] == row["result_reference"] and row["change_reference"] == "N/A"
                    and not row["changed_scope"] and not row["steps"] for row in state["resources"]),
                "IMP_CONTROL_RECOVERY_INVALID", "Recovery must record current no-change Results")
        proof = json.loads(read_member(stored, "EVD-RECOVERY").raw_bytes)
        require(proof == recovery_evidence(store, state, snapshots), "IMP_CONTROL_RECOVERY_INVALID",
                "Recovery Evidence is not bound to this Attempt and its immutable Resource readback")
