"""Recomputed provisional RLS Gate and strictly read-only integrity checks."""
from __future__ import annotations

from copy import deepcopy

from rls_authorization import authorization_binding_diff
from rls_common import (
    assert_no_secret,
    canonical_json,
    digest_reference,
    exact_exception_reference,
    exact_reference,
    exact_scope_reference,
    parse_time,
    require,
    sha256_bytes,
    sha256_value,
    stable_unique,
)
from rls_conclusion import compute_conclusion, compute_follow_up
from rls_evidence import validate_evidence as _validate_evidence
from rls_contract import (
    final_confirmation_digest,
    pre_execution_checklist,
    validate_contract_coverage,
)


_RELEASE_CONTRACT_FIELDS = {
    "release_reference",
    "scope_reference",
    "result_references",
    "vfy_reference",
    "vfy_conclusions",
    "vfy_candidate_provisional",
    "vfy_rls_ready",
    "vfy_source_digest",
    "vfy_candidate_digest",
    "vfy_exception_references",
    "rls_work_item_references",
    "release_target_obligations",
    "release_target",
    "target_baseline",
    "approval_or_trigger_reference",
}
_VFY_CONCLUSION_FIELDS = {
    "con_ver",
    "con_val",
    "product_result",
    "artifact_status",
    "artifact_gate",
}
_AUTHORIZATION_FIELDS = {
    "contract",
    "authorization_id",
    "rls_artifact_id",
    "rls_artifact_reference",
    "revision",
    "release_reference",
    "scope_reference",
    "result_references",
    "vfy_reference",
    "vfy_source_digest",
    "vfy_candidate_digest",
    "release_target",
    "target_baseline_digest",
    "release_contract_digest",
    "rli_ids",
    "action_summaries",
    "selected_rli_contract_digest",
    "release_item_set_digest",
    "confirmation_set_digest",
    "pre_execution_checklist_digest",
    "authorizer_identity",
    "authorized_at",
    "valid_until",
    "effect_digest",
}


def _validate_release_contract(artifact: dict) -> None:
    contract = artifact.get("release_contract")
    required_fields = _RELEASE_CONTRACT_FIELDS | ({"target_locator", "obligation_source_references"} if not artifact.get("provisional", True) else set())
    require(
        isinstance(contract, dict) and set(contract) == required_fields,
        "RLS_CONTRACT_INVALID",
        "Release Contract fields are missing or unexpected",
        missing=sorted(_RELEASE_CONTRACT_FIELDS - set(contract or {})),
        extra=sorted(set(contract or {}) - _RELEASE_CONTRACT_FIELDS),
    )
    exact_reference(contract.get("vfy_reference", ""), "VFY")
    exact_scope_reference(contract.get("scope_reference", ""))
    digest_reference(contract.get("vfy_source_digest", ""))
    digest_reference(contract.get("vfy_candidate_digest", ""))
    require(
        isinstance(contract.get("release_reference"), str)
        and contract["release_reference"].strip(),
        "RLS_RELEASE_REFERENCE_REQUIRED",
        "Release Reference is required",
    )
    require(
        isinstance(contract.get("release_target"), str)
        and contract["release_target"].strip()
        and "," not in contract["release_target"],
        "RLS_TARGET_REQUIRED",
        "one unique Release Target is required",
    )
    require(
        contract.get("target_baseline") is not None
        and contract.get("target_baseline") != "",
        "RLS_BASELINE_UNRESOLVED",
        "Target Baseline is required",
    )
    result_references = contract.get("result_references")
    require(
        isinstance(result_references, list)
        and result_references
        and stable_unique(result_references) == result_references,
        "RLS_RESULT_MISMATCH",
        "Release Result Set must be non-empty, ordered and duplicate-free",
    )
    require(
        isinstance(contract.get("vfy_candidate_provisional"), bool)
        and contract.get("vfy_rls_ready") is True,
        "RLS_VFY_NOT_READY",
        "RLS Artifact must bind a ready VFY candidate",
    )
    conclusions = contract.get("vfy_conclusions")
    require(
        isinstance(conclusions, dict)
        and set(conclusions) == _VFY_CONCLUSION_FIELDS,
        "RLS_VFY_NOT_READY",
        "VFY conclusion binding is incomplete",
    )
    require(
        conclusions.get("con_ver") in {"pass", "fail", "waived", "n/a"}
        and conclusions.get("con_val") in {"pass", "fail", "waived", "n/a"}
        and conclusions.get("product_result")
        in {"pass", "fail", "waived", "n/a"},
        "RLS_VFY_NOT_READY",
        "VFY conclusions are not terminal",
    )
    require(
        (conclusions.get("artifact_gate") == "pass"
         and conclusions.get("artifact_status") == "ready")
        or (
            conclusions.get("artifact_gate") == "pass_with_exception"
            and conclusions.get("artifact_status") == "ready_with_exception"
        ),
        "RLS_VFY_NOT_READY",
        "VFY Artifact Status and Gate are inconsistent",
    )
    exception_references = contract.get("vfy_exception_references")
    require(
        isinstance(exception_references, list)
        and stable_unique(exception_references) == exception_references,
        "RLS_VFY_NOT_READY",
        "VFY Exception references must be an ordered unique array",
    )
    if not contract["vfy_candidate_provisional"]:
        for reference in exception_references:
            exact_exception_reference(reference)
        if conclusions["artifact_gate"] == "pass_with_exception":
            require(
                bool(exception_references),
                "RLS_VFY_NOT_READY",
                "pass_with_exception requires exact VFY Exception closure",
            )


def _validate_checklist(artifact: dict) -> None:
    expected = pre_execution_checklist(
        artifact["release_contract"],
        artifact["release_items"],
        artifact["confirmations"],
    )
    require(
        artifact.get("pre_execution_checklist") == expected,
        "RLS_CONTRACT_INVALID",
        "Pre-execution Checklist no longer matches the immutable contracts",
    )
    require(
        artifact.get("pre_execution_checklist_digest")
        == sha256_value(expected),
        "RLS_CONTRACT_INVALID",
        "Pre-execution Checklist digest mismatch",
    )


def _validate_effect_authorizations(artifact: dict) -> None:
    history = artifact.get("effect_authorization_history", [])
    current = artifact.get("effect_authorization")
    require(
        isinstance(history, list),
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "Effect Authorization history must be an array",
    )
    if current is None:
        require(
            not history,
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "Effect Authorization history exists without a current record",
        )
    else:
        require(
            isinstance(current, dict) and history and history[-1] == current,
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "current Effect Authorization must equal the latest audit record",
        )

    authorization_ids: set[str] = set()
    authorized_rli_ids: set[str] = set()
    for record in history:
        require(
            isinstance(record, dict)
            and set(record) == _AUTHORIZATION_FIELDS
            and record.get("contract")
            == "sdlc-ai-spec/effect-authorization/v1",
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "Effect Authorization audit record is incomplete or has extra fields",
        )
        authorization_id = record["authorization_id"]
        require(
            isinstance(authorization_id, str)
            and authorization_id
            and authorization_id not in authorization_ids,
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "Effect Authorization ID must be unique within a Revision",
        )
        authorization_ids.add(authorization_id)
        rli_ids = record.get("rli_ids")
        require(
            isinstance(rli_ids, list)
            and rli_ids
            and stable_unique(rli_ids) == rli_ids,
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "Effect Authorization must bind an ordered unique RLI set",
        )
        differences = authorization_binding_diff(artifact, record, rli_ids)
        require(
            not differences,
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "persisted Effect Authorization no longer matches immutable contracts",
            changed_fields=differences,
        )
        require(
            parse_time(record["authorized_at"])
            < parse_time(record["valid_until"]),
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "Effect Authorization validity interval is invalid",
        )
        authorized_rli_ids.update(rli_ids)

    executed_rli_ids = {
        row["id"]
        for row in artifact["release_items"]
        if row["result"] in {"success", "partial", "fail"}
    }
    require(
        executed_rli_ids <= authorized_rli_ids,
        "RLS_EFFECT_AUTHORIZATION_REQUIRED",
        "terminal executed RLI lacks persisted exact Effect Authorization",
        missing=sorted(executed_rli_ids - authorized_rli_ids),
    )


def _validate_target_semantics(artifact: dict) -> None:
    if artifact.get("target_effect"):
        require(
            not artifact.get("cancel_requested"),
            "RLS_CANCEL_NOT_ALLOWED",
            "cancelled cannot describe an RLS that produced target effects",
        )
        confirmation_results = [
            row["result"] for row in artifact["confirmations"]
        ]
        require(
            not confirmation_results
            or any(
                result in {"pass", "fail", "pending"}
                for result in confirmation_results
            ),
            "RLS_TARGET_STATE_UNVERIFIED",
            "target effect requires an actual target-side Confirmation",
        )
        require(
            not confirmation_results
            or not all(result == "not_run" for result in confirmation_results),
            "RLS_TARGET_STATE_UNVERIFIED",
            "all Confirmations cannot be not_run after target effect",
        )


def _verify_mutable(work: dict, *, finalizing: bool) -> dict:
    assert_no_secret(work)
    require(
        work.get("contract") in {"sdlc-ai-spec/rls-provisional-result/v1", "sdlc-ai-spec/rls-result/v1"},
        "RLS_CONTRACT_INVALID",
        "wrong RLS result contract",
    )
    _validate_release_contract(work)
    # Preserve domain-specific error precedence for incomplete Work Item/RCF
    # coverage before reporting the derived Checklist mismatch.
    validate_contract_coverage(work)
    _validate_checklist(work)
    _validate_target_semantics(work)
    _validate_evidence(work)
    _validate_effect_authorizations(work)
    from rls_exceptions import derive_exceptions, unresolved_exception_references
    if not work.get("provisional", True):
        work["exceptions"] = derive_exceptions(work)
    conclusion = compute_conclusion(work)
    follow_up = compute_follow_up(work, conclusion)
    stored_conclusion = work.get("release_conclusion", "pending")
    if stored_conclusion != "pending":
        require(
            stored_conclusion == conclusion,
            "RLS_CONCLUSION_INCONSISTENT",
            "stored Release Conclusion is inconsistent with item results",
        )
    stored_follow = work.get("follow_up", "none")
    if stored_follow != "none":
        require(
            stored_follow == follow_up,
            "RLS_FOLLOW_UP_INVALID",
            "stored Follow-up is inconsistent with item results",
        )
    work["release_conclusion"] = conclusion
    work["follow_up"] = follow_up
    pending = any(
        row["result"] == "pending"
        for row in work["release_items"] + work["confirmations"]
    )
    gate = "pending" if pending else "pass_with_exception" if unresolved_exception_references(work) else "pass"
    if finalizing:
        require(not work.get("effect_uncertain"), "RLS_EXECUTION_UNCERTAIN", "unresolved execution journal prevents freeze")
        require(
            not pending,
            "RLS_CONCLUSION_INCONSISTENT",
            "pending item cannot be finalized",
        )
        final_confirmation = work.get("final_confirmation")
        require(
            isinstance(final_confirmation, dict),
            "RLS_FINAL_CONFIRMATION_STALE",
            "Final Confirmation is required",
        )
        require(
            final_confirmation.get("digest")
            == final_confirmation_digest(work),
            "RLS_FINAL_CONFIRMATION_STALE",
            "Final Confirmation does not bind the terminal RLS state",
        )
        work["artifact"]["revision_state"] = "frozen"
        work["status"] = "ready_with_exception" if gate == "pass_with_exception" else "ready"
    work["artifact_gate"] = gate
    return {
        "ok": True,
        "release_conclusion": conclusion,
        "follow_up": follow_up,
        "artifact_gate": gate,
        "pending": pending,
    }


def verify(artifact: dict, *, finalizing: bool = False) -> dict:
    return _verify_mutable(artifact, finalizing=finalizing)


def check_read_only(artifact: dict, target_snapshot=None) -> dict:
    artifact_before = sha256_value(artifact)
    target_before = (
        sha256_value(target_snapshot) if target_snapshot is not None else None
    )
    work = deepcopy(artifact)
    result = _verify_mutable(work, finalizing=False)
    require(
        artifact_before == sha256_value(artifact),
        "RLS_CHECK_MUTATED",
        "check mutated the source Artifact",
    )
    if target_snapshot is not None:
        require(
            target_before == sha256_value(target_snapshot),
            "RLS_CHECK_MUTATED",
            "check mutated the target snapshot",
        )
    return result
