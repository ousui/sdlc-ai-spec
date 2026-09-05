"""Target-side post-release Confirmation with all-item no-write preflight."""
from __future__ import annotations

from rls_common import assert_no_secret, require
from rls_items import normalize_requested_ids


def confirm_items(
    artifact: dict, target, item_ids, *, force_fail: bool = False,
    pipeline_only: bool = False, human_evidence: dict | None = None,
    trusted_observations=None, persist=None,
) -> dict:
    # Reject sensitive input before shape errors can enter caller error receipts.
    assert_no_secret(human_evidence)
    require(getattr(target, "target_id", None) == artifact["release_contract"]["release_target"],
            "RLS_TARGET_STATE_UNVERIFIED", "Confirmation target does not match the Release Contract")
    ids, warnings = normalize_requested_ids(item_ids, "rcf")
    require(ids, "RLS_CONFIRMATION_CONTRACT_INCOMPLETE", "at least one RCF must be selected")
    by_id = {row["id"]: row for row in artifact["confirmations"]}
    require(all(item_id in by_id for item_id in ids), "RLS_CONFIRMATION_CONTRACT_INCOMPLETE", "unknown RCF")
    require(not pipeline_only, "RLS_TARGET_STATE_UNVERIFIED", "pipeline success cannot establish a target-side pass")
    require(all(by_id[item_id]["result"] == "pending" for item_id in ids),
            "RLS_TARGET_STATE_UNVERIFIED", "every selected RCF must be pending")
    target.assert_expected_state(artifact["release_contract"]["target_baseline"], artifact.get("target_snapshot_after"))
    observations = {}
    human_ids = [identity for identity in ids if by_id[identity].get("subjective")]
    if human_evidence is not None:
        require(isinstance(human_evidence, dict), "RLS_HUMAN_EVIDENCE_INVALID", "human observations must be structured")
        if "contract" in human_evidence:
            require(len(human_ids) == 1, "RLS_HUMAN_EVIDENCE_INVALID", "one record cannot cover multiple RCFs")
            observations[human_ids[0]] = human_evidence
        else:
            require(set(human_evidence) == set(human_ids), "RLS_HUMAN_EVIDENCE_INVALID", "human observation map must exactly cover selected human RCFs")
            observations = human_evidence
    options = {identity: dict(force_fail=force_fail, human_evidence=observations.get(identity),
                             artifact=artifact, trusted_observations=trusted_observations) for identity in ids}
    # Invalid later items must not leave an earlier false observation behind.
    for identity in ids:
        target.preflight_confirmation(by_id[identity], artifact["release_contract"]["release_reference"], **options[identity])
    for identity in ids:
        row = by_id[identity]
        target.assert_expected_state(artifact["release_contract"]["target_baseline"], artifact.get("target_snapshot_after"))
        result, evidence_item, state = target.confirm(row, artifact["release_contract"]["release_reference"], **options[identity])
        row.update(observed=state, result=result, evidence_references=[evidence_item["reference"]])
        if result == "fail" and row.get("follow_up") == "none":
            row["follow_up"] = "retry_rls"
        artifact["evidence"].append(evidence_item)
        if persist is not None:
            persist(artifact)
    artifact["warnings"].extend(warnings)
    return artifact


def exception_resolution_state(confirmations: list[dict], *, current_active_exception: bool = False) -> str:
    results = {row["result"] for row in confirmations}
    if "pending" in results or "not_run" in results:
        return "carried"
    if "waived" in results:
        require(current_active_exception, "RLS_CONFIRMATION_CONTRACT_INCOMPLETE", "re-waived Confirmation needs a current active Exception")
        return "superseded"
    if results and results <= {"pass", "fail"}:
        return "resolved"
    return "carried"
