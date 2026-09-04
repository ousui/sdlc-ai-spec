"""Real ArtifactStore terminal-state fixtures for Claim Provider tests."""

import json
from pathlib import Path

from packages.sdlc_artifact_store import (
    ArtifactStore,
    CanonicalMember,
    CanonicalRevisionPayload,
    ClaimReservation,
    compute_sha256,
)
from packages.sdlc_phasekit import (
    CheckOutcome,
    PhaseInputs,
    StructuredPhaseVerifier,
    manifest,
    render_phase_artifact,
    table,
)

IMP_BINDING_HEADERS = (
    "IMP Binding Reference", "Binding Lineage Key", "Attempt", "Owner",
    "Rework References",
)
IMP_RESULT_HEADERS = (
    "ID", "Resource", "Baseline Reference", "Change Reference",
    "Result Reference", "Changed Scope", "Approach Step References",
)
EVALUATION_CONTRACT_SET = "claim-provider-fixture@sha256:" + "a" * 64
PRE_EXECUTION_CONTRACT = "sdlc-ai-spec/imp-pre-execution-readback/v1"


def _json_bytes(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _json_member(member_id: str, value) -> CanonicalMember:
    raw = _json_bytes(value)
    return CanonicalMember(
        member_id,
        f"evidence/{member_id.lower()}.json",
        "application/json",
        raw,
        compute_sha256(raw),
    )


def _allocate(root: Path, claim):
    store = ArtifactStore.open_read_write(root)
    store.initialize()
    reservation = ClaimReservation(
        claim.binding_lineage, claim.attempt_token, claim.owner
    )
    store.allocate_artifact(
        "IMP",
        external_artifact_id=claim.artifact_id,
        claim=reservation,
    )
    control = store.allocate_revision(
        claim.artifact_id,
        base_revision=claim.revision - 1 if claim.revision > 1 else None,
        external_revision=claim.revision,
        claim=reservation,
    )
    return store, control


def prepare_frozen_claim(
    root: Path,
    claim,
    *,
    state_mutator=None,
    snapshot_mutator=None,
) -> None:
    """Create a genuinely frozen, passing exact IMP Revision."""

    store, control = _allocate(root, claim)
    if control.state == "frozen":
        return
    authority = root / ".sdlc" / "authority" / (
        f"claim-{claim.artifact_id}-{claim.revision}.txt"
    )
    authority.parent.mkdir(exist_ok=True)
    authority.write_text("Fixture owner approved the exact Claim Revision\n")
    authority_reference = (
        authority.relative_to(root).as_posix()
        + "@"
        + compute_sha256(authority.read_bytes())
    )
    reference = f"{claim.artifact_id}@{claim.revision}"
    resources = []
    snapshot_members = []
    for index, resource_name in enumerate(
        sorted(
            item.removeprefix("resource:")
            for item in claim.execution_scope
            if item.startswith("resource:")
        ),
        start=1,
    ):
        identity = f"RES-{index:03d}"
        baseline_id = "BASE-" + identity
        content = f"fixture:{resource_name}\n".encode()
        snapshot = {
            "contract": "sdlc-ai-spec/imp-resource-snapshot/v1",
            "resource": resource_name,
            "existed": True,
            "root_mode": 0o755,
            "entries": [{
                "path": "fixture.txt",
                "sha256": compute_sha256(content).split(":", 1)[1],
                "content_hex": content.hex(),
                "mode": 0o644,
            }],
            "directories": [],
        }
        if snapshot_mutator is not None:
            snapshot_mutator(snapshot)
        snapshot_raw = _json_bytes(snapshot)
        snapshot_members.append(CanonicalMember(
            baseline_id,
            f"snapshots/{baseline_id.lower()}.json",
            "application/json",
            snapshot_raw,
            compute_sha256(snapshot_raw),
        ))
        resources.append({
            "id": identity,
            "resource": resource_name,
            "root": ".",
            "baseline_member": baseline_id,
            "baseline_reference": f"{reference}/{baseline_id}",
            "change_member": "CHANGE-" + identity,
            "change_reference": "N/A",
            "result_member": "RESULT-" + identity,
            "result_reference": f"{reference}/{baseline_id}",
            "changed_paths": [],
            "changed_scope": [],
            "steps": [],
        })
    method_checks = []
    check_records = []
    check_members = []
    for index, resource in enumerate(resources, start=1):
        check_id = f"CHK-{index:03d}"
        method_checks.append({
            "id": check_id,
            "name": f"Verify {resource['resource']} fixture",
            "kind": "equals",
            "resource": resource["resource"],
            "path": "fixture.txt",
            "expected": f"fixture:{resource['resource']}\n",
        })
        check_records.append({
            "id": check_id,
            "name": f"Verify {resource['resource']} fixture",
            "resource": resource["resource"],
            "path": "fixture.txt",
            "result": "pass",
            "evidence_member": "EVD-" + check_id,
        })
        check_members.append(_json_member("EVD-" + check_id, {
            "command": ["fixture-check", resource["resource"]],
            "cwd": ".",
            "exit_code": 0,
            "stdout": "fixture matches\n",
            "stderr": "",
            "result": "pass",
        }))
    claim_state = {
        "binding_lineage": claim.binding_lineage,
        "binding_reference": claim.binding_reference,
        "artifact_id": claim.artifact_id,
        "revision": claim.revision,
        "attempt": claim.attempt,
        "owner": claim.owner,
        "execution_scope": list(claim.execution_scope),
        "dependency_results": list(claim.dependency_results),
        "rework_references": list(claim.rework_references),
    }
    checklist = {
        "claim_identity": claim_state,
        "resource_baselines": [
            {
                "id": resource["id"],
                "resource": resource["resource"],
                "baseline_reference": resource["baseline_reference"],
            }
            for resource in resources
        ],
        "check_ids": [item["id"] for item in method_checks],
    }
    checklist_digest = compute_sha256(_json_bytes(checklist))
    pre_evidence = _json_member("EVD-PRE", {
        "contract": PRE_EXECUTION_CONTRACT,
        "artifact_reference": reference,
        "observed_at": "2026-09-01T12:00:00Z",
        "evaluation_contract_set": EVALUATION_CONTRACT_SET,
        "checklist": checklist,
        "checklist_digest": checklist_digest,
        "executor": claim.owner,
        "result": "pass",
    })
    state = {
        "contract": "sdlc-ai-spec/imp-state/v1",
        "stage": "executed",
        "claim": claim_state,
        "request": {
            "dependencies": list(claim.dependency_results),
            "rework": list(claim.rework_references),
        },
        "method": {"steps": [], "checks": method_checks},
        "resources": resources,
        "checks": check_records,
        "pre_execution": {
            "contract": PRE_EXECUTION_CONTRACT,
            "evidence_member": "EVD-PRE",
            "evidence_sha256": pre_evidence.sha256,
            "observed_at": "2026-09-01T12:00:00Z",
            "evaluation_contract_set": EVALUATION_CONTRACT_SET,
            "checklist_digest": checklist_digest,
        },
        "failure": None,
    }
    if state_mutator is not None:
        state_mutator(state)
    state_raw = _json_bytes(state)
    state_member = CanonicalMember(
        "IMP-STATE",
        "evidence/imp-state.json",
        "application/json",
        state_raw,
        compute_sha256(state_raw),
    )
    members = (*snapshot_members, pre_evidence, *check_members, state_member)
    raw = render_phase_artifact(
        artifact_id=claim.artifact_id,
        phase="IMP",
        revision=claim.revision,
        status="ready",
        profile="full",
        phase_inputs=PhaseInputs(
            "CTX-20260901100000-01@1",
            tuple(claim.dependency_results),
        ),
        title="Claim Provider terminal-state fixture",
        sections=(
            (
                "### 实施绑定 Implementation Binding",
                table(IMP_BINDING_HEADERS, ((
                    claim.binding_reference,
                    claim.binding_lineage,
                    claim.attempt,
                    claim.owner,
                    ", ".join(claim.rework_references) or "None",
                ),)),
            ),
            (
                "## 实施结果 Implementation Result",
                table(IMP_RESULT_HEADERS, tuple(
                    (
                        resource["id"],
                        resource["resource"],
                        resource["baseline_reference"],
                        resource["change_reference"],
                        resource["result_reference"],
                        "None",
                        "None",
                    )
                    for resource in resources
                )),
            ),
        ),
        checks={
            f"CORE-G-{index:03d}": CheckOutcome("pass", "Fixture authority")
            for index in range(1, 10)
        } | {
            f"IMP-G-{index:03d}": CheckOutcome("pass", "Fixture IMP result")
            for index in range(1, 7)
        },
        open_items=(),
        evidence=(),
        exceptions=(),
        lifecycle_applicability=(),
        final_confirmation={
            "mode": "human",
            "confirmer": claim.owner,
            "role": "Fixture Claim Owner",
            "authority_reference": authority_reference,
            "confirmed_at": "2026-09-01T12:00:00Z",
        },
        gate_result="pass",
        evaluation_contract_set=EVALUATION_CONTRACT_SET,
        evaluator="Claim Provider fixture",
        members=members,
    )
    store.write_open_revision(
        CanonicalRevisionPayload(
            claim.artifact_id,
            "IMP",
            claim.revision,
            "ready",
            raw,
            "text/markdown",
            compute_sha256(raw),
            members,
            manifest(members),
        ),
        expected_generation=control.generation,
    )
    store.freeze_revision(
        claim.artifact_id,
        claim.revision,
        verifier=StructuredPhaseVerifier(root, phase="IMP"),
    )


def prepare_abandoned_claim(root: Path, claim, reason: str) -> None:
    """Create the exact abandoned Revision required before Claim abandon."""

    store, control = _allocate(root, claim)
    if control.state == "abandoned":
        return
    store.abandon_revision(claim.artifact_id, claim.revision, reason=reason)
