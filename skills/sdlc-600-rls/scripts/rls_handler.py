"""Private create/execute/confirm/revise/check/cancel choreography."""
from __future__ import annotations

from copy import deepcopy

from rls_builder import abandoned_reservation, build_provisional, no_artifact_result
from rls_common import canonical_json, require, sha256_bytes, sha256_value, utc_now
from rls_conclusion import apply_conclusion
from rls_confirmation import confirm_items
from rls_contract import assert_revision_change_allowed, final_confirmation_digest
from rls_executor import execute_items
from rls_evidence import build_cancel_evidence
from rls_revision import candidate_contract_delta
from rls_verifier import check_read_only, verify


def create(candidate, **kwargs):
    if candidate.rls_applicability in {"n/a", "waived"}:
        return no_artifact_result(candidate)
    require(
        candidate.rls_applicability != "pending",
        "RLS_APPLICABILITY_PENDING",
        "RLS applicability is pending",
    )
    return build_provisional(candidate, **kwargs)


def execute(artifact, target, item_ids, authorization, **kwargs):
    require(
        artifact["artifact"]["revision_state"] == "open",
        "RLS_EXECUTION_FAILED",
        "only an open RLS Revision can execute",
    )
    return execute_items(artifact, target, item_ids, authorization, **kwargs)


def confirm(artifact, target, item_ids, **kwargs):
    require(
        artifact["artifact"]["revision_state"] == "open",
        "RLS_TARGET_STATE_UNVERIFIED",
        "only an open RLS Revision can confirm",
    )
    return confirm_items(artifact, target, item_ids, **kwargs)


def mark_not_run_before_effect(artifact: dict, reason_reference: str) -> dict:
    require(
        not artifact.get("target_effect"),
        "RLS_TARGET_STATE_UNVERIFIED",
        "RCF not_run is only valid before any target effect",
    )
    for row in artifact["confirmations"]:
        if row["result"] == "pending":
            row["result"] = "not_run"
            row["observed"] = "release stopped before target effect"
            row["evidence_references"] = [reason_reference]
    return artifact


def finalize(artifact: dict, *, confirmer_identity: str = "rls-confirmer") -> dict:
    apply_conclusion(artifact)
    artifact["final_confirmation"] = {
        "confirmer_identity": confirmer_identity,
        "confirmed_at": utc_now(),
        "digest": final_confirmation_digest(artifact),
    }
    verify(artifact, finalizing=True)
    return artifact


def cancel(artifact: dict, target) -> dict:
    require(
        artifact["artifact"]["revision_state"] == "open"
        and not artifact.get("effect_uncertain")
        and not artifact.get("target_effect")
        and (
            artifact.get("target_snapshot_before") is None
            or artifact.get("target_snapshot_before") == artifact.get("target_snapshot_after")
        ),
        "RLS_CANCEL_NOT_ALLOWED",
        "cancel requires proof of zero target effect",
    )
    require(
        getattr(target, "target_id", None)
        == artifact["release_contract"]["release_target"],
        "RLS_CANCEL_NOT_ALLOWED",
        "cancellation target does not match the Release Contract",
    )
    try:
        before = target.assert_expected_state(
            artifact["release_contract"]["target_baseline"],
            artifact.get("target_snapshot_after"),
        )
    except Exception as exc:
        require(False, "RLS_TARGET_STATE_DRIFT", "target drift prevents cancellation")
    affected = [row["id"] for row in artifact["release_items"] + artifact["confirmations"] if row["result"] == "pending"]
    evidence = build_cancel_evidence(artifact, before, affected)
    artifact["evidence"].append(evidence)
    for item in artifact["release_items"]:
        if item["result"] == "pending":
            item["result"] = "cancelled"
            item["evidence_references"] = [evidence["reference"]]
    for row in artifact["confirmations"]:
        if row["result"] == "pending":
            row["result"] = "not_run"
            row["observed"] = "cancelled before target effect"
            row["evidence_references"] = [evidence["reference"]]
    artifact["cancel_requested"] = True
    artifact["target_snapshot_before"] = before
    artifact["target_snapshot_after"] = target.snapshot()
    if artifact.get("provisional", True):
        return finalize(artifact, confirmer_identity="cancel-controller")
    apply_conclusion(artifact)
    verify(artifact)
    return artifact


def retry_revision(old: dict, candidate, target_baseline) -> dict:
    assert_revision_change_allowed(
        old, candidate, old["release_contract"]["release_target"]
    )
    require(
        old["artifact"]["revision_state"] == "frozen",
        "RLS_CONTRACT_INVALID",
        "retry requires a frozen prior RLS Revision",
    )
    release_items = []
    for row in old["release_items"]:
        reset = dict(row)
        reset.update(result="pending", follow_up="none", evidence_references=[])
        release_items.append(reset)
    confirmations = []
    for row in old["confirmations"]:
        reset = dict(row)
        reset.update(result="pending", follow_up="none", observed=None, evidence_references=[])
        confirmations.append(reset)
    return build_provisional(
        candidate,
        release_reference=old["release_contract"]["release_reference"],
        release_target=old["release_contract"]["release_target"],
        target_baseline=target_baseline,
        artifact_id=old["artifact"]["id"],
        revision=old["artifact"]["revision"] + 1,
        release_items=release_items,
        confirmations=confirmations,
        rls_work_item_references=old["release_contract"].get(
            "rls_work_item_references", []
        ),
    )


def revise(
    old: dict,
    candidate,
    *,
    target: str,
    target_baseline,
    retry: bool = False,
) -> dict:
    release_contract = old["release_contract"]
    if candidate.scope_reference != release_contract["scope_reference"]:
        raise_scope = False
        require(raise_scope, "RLS_SCOPE_MISMATCH", "Scope change must return upstream")
    if set(candidate.result_references) != set(release_contract["result_references"]):
        raise_results = False
        require(raise_results, "RLS_RESULT_MISMATCH", "Result Set change must return upstream")
    if target != release_contract["release_target"]:
        return build_provisional(
            candidate,
            release_reference=release_contract["release_reference"],
            release_target=target,
            target_baseline=target_baseline,
        )
    delta = candidate_contract_delta(release_contract, candidate)
    if delta:
        require(old["artifact"]["revision_state"] == "frozen", "RLS_CONTRACT_INVALID",
                "VFY contract changed in open RLS Revision", changed_fields=delta)
        return build_provisional(
            candidate, release_reference=release_contract["release_reference"],
            release_target=target, target_baseline=target_baseline,
            artifact_id=old["artifact"]["id"], revision=old["artifact"]["revision"] + 1,
            rls_work_item_references=release_contract["rls_work_item_references"],
        )
    if retry:
        return retry_revision(old, candidate, target_baseline)
    result = deepcopy(old)
    result.setdefault("warnings", []).append("RLS_NO_CHANGE")
    return result


def abandon_first_write(artifact_id: str, revision: int, error: Exception) -> dict:
    return abandoned_reservation(artifact_id, revision, f"first-write failure: {error}")


def check(artifact: dict, target) -> dict:
    require(
        getattr(target, "target_id", None)
        == artifact["release_contract"]["release_target"],
        "RLS_TARGET_STATE_UNVERIFIED",
        "check target does not match the Release Contract",
    )
    artifact_before = sha256_value(artifact)
    target_before = target.assert_expected_state(
        artifact["release_contract"]["target_baseline"],
        artifact.get("target_snapshot_after"),
    )
    target_digest = sha256_value(target_before)
    result = check_read_only(artifact, target_before)
    require(
        sha256_value(artifact) == artifact_before,
        "RLS_CHECK_MUTATED",
        "check changed Artifact bytes",
    )
    require(
        sha256_value(target.snapshot()) == target_digest,
        "RLS_CHECK_MUTATED",
        "check changed target bytes",
    )
    return result


def auto_operation(candidate, artifact: dict | None) -> str:
    if artifact is None:
        require(candidate is not None, "RLS_VFY_NOT_READY", "VFY candidate is required")
        if candidate.rls_applicability in {"n/a", "waived"}:
            return "complete"
        if candidate.rls_applicability == "pending":
            return "action_required"
        return "create"
    if artifact["artifact"]["revision_state"] == "frozen":
        return "check"
    if any(row["result"] == "pending" for row in artifact["release_items"]):
        return "execute"
    if any(row["result"] == "pending" for row in artifact["confirmations"]):
        return "confirm"
    return "finalize"
