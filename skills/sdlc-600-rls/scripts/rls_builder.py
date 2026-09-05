"""Pure provisional RLS Artifact builder; persistence remains a shared-store concern."""
from __future__ import annotations

from datetime import datetime, timezone

_LAST_ID_STAMP: str | None = None
_LAST_ID_SEQUENCE = 0

from rls_common import assert_no_secret, require, sha256_value
from rls_contract import pre_execution_checklist
from rls_items import default_items, normalize_items
from rls_scope import bind_scope


def _artifact_id(now=None) -> str:
    """Return a process-unique, valid stable RLS identity without external state."""
    global _LAST_ID_STAMP, _LAST_ID_SEQUENCE
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d%H%M%S")
    if stamp == _LAST_ID_STAMP:
        _LAST_ID_SEQUENCE += 1
    else:
        _LAST_ID_STAMP = stamp
        _LAST_ID_SEQUENCE = 1
    require(
        _LAST_ID_SEQUENCE <= 99,
        "RLS_CONTRACT_INVALID",
        "too many RLS identities in one second",
    )
    return f"RLS-{stamp}-{_LAST_ID_SEQUENCE:02d}"


def _interface_warnings(candidate) -> list[str]:
    warnings = ["PROVISIONAL_VFY_INTERFACE"] if not candidate.authority_verified else []
    if candidate.interface_mode == "VFY_FINAL_SHAPE_SHADOW":
        warnings.append("VFY_FINAL_SHAPE_SHADOW")
    return warnings


def no_artifact_result(candidate) -> dict:
    require(
        candidate.rls_applicability in {"n/a", "waived"},
        "RLS_APPLICABILITY_PENDING",
        "no-artifact result requires n/a or waived applicability",
    )
    return {
        "contract": "sdlc-ai-spec/rls-result/v1" if candidate.authority_verified else "sdlc-ai-spec/rls-provisional-result/v1",
        "provisional": not candidate.authority_verified,
        "status": "completed",
        "artifact": None,
        "rls_applicability": candidate.rls_applicability,
        "vfy_reference": candidate.vfy_reference,
        "vfy_source_digest": candidate.source_digest,
        "vfy_candidate_digest": candidate.candidate_digest,
        "target_effect": False,
        "warnings": _interface_warnings(candidate),
    }


def abandoned_reservation(artifact_id: str, revision: int, reason: str) -> dict:
    return {
        "artifact": {
            "id": artifact_id,
            "revision": revision,
            "reference": f"{artifact_id}@{revision}",
            "revision_state": "abandoned",
        },
        "reason": reason,
        "target_effect": False,
    }


def build_provisional(
    candidate,
    *,
    release_reference: str,
    release_target: str,
    target_baseline,
    artifact_id: str | None = None,
    revision: int = 1,
    release_items=None,
    confirmations=None,
    rls_work_item_references=None,
) -> dict:
    require(
        candidate.rls_applicability == "required" and candidate.rls_ready is True,
        "RLS_NOT_REQUIRED"
        if candidate.rls_applicability in {"n/a", "waived"}
        else "RLS_APPLICABILITY_PENDING",
        "RLS applicability/readiness does not permit an RLS Artifact",
    )
    require(
        isinstance(release_reference, str) and release_reference.strip(),
        "RLS_RELEASE_REFERENCE_REQUIRED",
        "Release Reference is required",
    )
    require(
        isinstance(release_target, str)
        and release_target.strip()
        and "," not in release_target,
        "RLS_TARGET_REQUIRED",
        "one unique Release Target is required",
    )
    require(
        target_baseline is not None and target_baseline != "",
        "RLS_BASELINE_UNRESOLVED",
        "Target Baseline is required",
    )
    scope = bind_scope(candidate)
    if release_items is None or confirmations is None:
        default_rli, default_rcf = default_items(candidate)
        release_items = default_rli if release_items is None else release_items
        confirmations = default_rcf if confirmations is None else confirmations
    release_items = normalize_items(list(release_items), "rli")
    confirmations = normalize_items(list(confirmations), "rcf")
    artifact_id = artifact_id or _artifact_id()
    require(revision >= 1, "RLS_CONTRACT_INVALID", "Revision must be positive")
    release_contract = {
        "release_reference": release_reference.strip(),
        "scope_reference": scope["scope_reference"],
        "result_references": scope["result_references"],
        "vfy_reference": candidate.vfy_reference,
        "vfy_conclusions": {
            "con_ver": candidate.con_ver,
            "con_val": candidate.con_val,
            "product_result": candidate.product_result,
            "artifact_status": candidate.artifact_status,
            "artifact_gate": candidate.artifact_gate,
        },
        "vfy_candidate_provisional": candidate.provisional,
        "vfy_rls_ready": candidate.rls_ready,
        "vfy_source_digest": candidate.source_digest,
        "vfy_candidate_digest": candidate.candidate_digest,
        "vfy_exception_references": list(candidate.exception_references),
        "rls_work_item_references": list(candidate.rls_work_item_references if rls_work_item_references is None else rls_work_item_references),
        "release_target_obligations": [
            dict(row) for row in candidate.release_target_obligations
        ],
        "release_target": release_target.strip(),
        "target_baseline": target_baseline,
        "approval_or_trigger_reference": "None — no separate approval defined",
    }
    if candidate.authority_verified:
        release_contract["obligation_source_references"] = list(candidate.obligation_sources)
    artifact = {
        "contract": "sdlc-ai-spec/rls-result/v1" if candidate.authority_verified else "sdlc-ai-spec/rls-provisional-result/v1",
        "provisional": not candidate.authority_verified,
        "status": "contract_ready",
        "artifact": {
            "id": artifact_id,
            "revision": revision,
            "reference": f"{artifact_id}@{revision}",
            "revision_state": "open",
        },
        "release_contract": release_contract,
        "release_items": release_items,
        "confirmations": confirmations,
        "pre_execution_checklist": {},
        "pre_execution_checklist_digest": "",
        "effect_authorization": None,
        "effect_authorization_history": [],
        "evidence": [],
        "target_effect": False,
        "target_snapshot_before": None,
        "target_snapshot_after": None,
        "release_conclusion": "pending",
        "follow_up": "none",
        "artifact_gate": "pending",
        "final_confirmation": None,
        "cancel_requested": False,
        "errors": [],
        "warnings": _interface_warnings(candidate),
    }
    if candidate.authority_verified:
        artifact.update(context_reference=candidate.context_reference, profile=candidate.profile,
                        input_references=list(candidate.input_references),
                        upstream_exceptions=list(candidate.authority_exceptions), active_exceptions=[])
        from rls_exceptions import derive_exceptions
        artifact["exceptions"] = derive_exceptions(artifact)
    artifact["pre_execution_checklist"] = pre_execution_checklist(
        release_contract, release_items, confirmations
    )
    artifact["pre_execution_checklist_digest"] = sha256_value(
        artifact["pre_execution_checklist"]
    )
    assert_no_secret(artifact)
    return artifact
