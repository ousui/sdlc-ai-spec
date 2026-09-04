"""Pure VFY → RLS release-candidate projection."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from vfy_common import require, sha256_value
from vfy_exceptions import active_failure_exception
from vfy_verifier import verify_state

RELEASE_CANDIDATE_CONTRACT = "sdlc-ai-spec/vfy-release-candidate/v1"


def _fixed(state: Mapping[str, Any], identity: str) -> str:
    matches = [
        str(item.get("conclusion"))
        for item in state.get("fixed_conclusions", [])
        if item.get("id") == identity
    ]
    require(
        len(matches) == 1,
        "VFY_RLS_NOT_ALLOWED",
        f"Missing fixed Conclusion {identity}",
    )
    return matches[0]


def build_release_candidate(state: Mapping[str, Any]) -> dict[str, Any]:
    artifact = state.get("artifact") or {}
    require(
        artifact.get("revision_state") == "frozen",
        "VFY_RLS_NOT_ALLOWED",
        "Only frozen VFY can project an RLS candidate",
    )
    projection = verify_state(state, finalizing=True)
    pending = [
        str(item["method_id"])
        for item in state.get("method_results", [])
        if item.get("result") == "pending"
    ]
    pending += [
        str(item["target_reference"])
        for item in state.get("target_conclusions", [])
        if item.get("conclusion") == "pending"
    ]
    pending += [
        str(item["id"])
        for item in state.get("fixed_conclusions", [])
        if item.get("conclusion") == "pending"
    ]
    unresolved = [
        f"{artifact.get('reference')}#{item['id']}"
        for item in state.get("returns", [])
        if item.get("status") != "resolved"
    ]
    unresolved += list(projection.get("unresolved_controls", []))
    exception = active_failure_exception(state.get("exceptions", []))
    candidate = {
        "contract": RELEASE_CANDIDATE_CONTRACT,
        "provisional": False,
        "vfy_reference": artifact.get("reference"),
        "revision_state": artifact.get("revision_state"),
        "artifact_status": artifact.get("artifact_status"),
        "artifact_gate": projection["artifact_gate"],
        "early_stop": bool(state.get("early_stop")),
        "pending_fields": pending,
        "scope_reference": state.get("scope", {}).get("reference"),
        "subject_references": [
            str(item["reference"]) for item in state.get("subjects", [])
        ],
        "result_references": [
            str(item["reference"]) for item in state.get("subjects", [])
        ],
        "subject_current_valid": all(
            item.get("current_valid") is True for item in state.get("subjects", [])
        ),
        "imp_chain_current_valid": all(
            item.get("dependency_chain_valid") is True
            for item in state.get("subjects", [])
        ),
        "con_ver": _fixed(state, "CON-VER"),
        "con_val": _fixed(state, "CON-VAL"),
        "product_result": state.get("product_result"),
        "unresolved_returns": unresolved,
        "rls_applicability": state.get("rls_applicability"),
        "release_target_obligations": deepcopy(
            list(state.get("release_target_obligations", []))
        ),
        "evidence_references": [
            str(item["reference"]) for item in state.get("evidence", [])
        ],
        "exception": deepcopy(dict(exception)) if exception is not None else None,
        "exception_references": [
            str(item["origin_reference"])
            for item in state.get("exceptions", [])
        ],
        "source_digest": sha256_value(state),
        "rls_ready": bool(projection["rls_ready"]),
    }
    require(
        candidate["artifact_gate"] in {"pass", "pass_with_exception"},
        "VFY_RLS_NOT_ALLOWED",
        "VFY Artifact Gate is not downstream-usable",
    )
    require(
        candidate["artifact_status"] in {"ready", "ready_with_exception"},
        "VFY_RLS_NOT_ALLOWED",
        "VFY Artifact Status is not downstream-usable",
    )
    require(
        not candidate["early_stop"] and not pending and not unresolved,
        "VFY_RLS_NOT_ALLOWED",
        "Early-stop, pending or unresolved recovery blocks RLS",
    )
    require(
        candidate["subject_current_valid"] and candidate["imp_chain_current_valid"],
        "VFY_RLS_NOT_ALLOWED",
        "Stale Subject/IMP chain blocks RLS",
    )
    require(
        candidate["rls_applicability"] in {"required", "n/a", "waived"},
        "VFY_RLS_NOT_ALLOWED",
        "RLS applicability is unresolved",
    )
    if candidate["product_result"] == "fail":
        require(
            exception is not None,
            "VFY_RLS_NOT_ALLOWED",
            "Product fail requires an active scoped Exception",
        )
    else:
        require(
            candidate["product_result"] in {"pass", "waived", "n/a"},
            "VFY_RLS_NOT_ALLOWED",
            "Product result is not downstream-eligible",
        )
    if candidate["artifact_gate"] == "pass_with_exception":
        require(
            bool(candidate["exception_references"]),
            "VFY_RLS_NOT_ALLOWED",
            "pass_with_exception requires exact Exception closure",
        )
    if candidate["rls_applicability"] == "required":
        require(
            candidate["rls_ready"] is True,
            "VFY_RLS_NOT_ALLOWED",
            "Required RLS candidate is not RLS-ready",
        )
    return candidate
