"""Deterministic Release Conclusion, Follow-up and provisional lifecycle projection."""
from __future__ import annotations

from rls_common import require
from rls_items import FOLLOWUPS


def compute_conclusion(artifact: dict) -> str:
    rli = [row["result"] for row in artifact["release_items"]]
    rcf = [row["result"] for row in artifact["confirmations"]]
    if "pending" in rli or "pending" in rcf:
        return "pending"
    if "fail" in rli or "fail" in rcf:
        return "failed"
    if artifact.get("cancel_requested") and not artifact.get("target_effect"):
        return "cancelled"
    if (
        all(result in {"success", "waived"} for result in rli)
        and any(result == "pass" for result in rcf)
        and all(result in {"pass", "n/a", "waived"} for result in rcf)
    ):
        return "success"
    if artifact.get("target_effect") or "partial" in rli:
        return "partial"
    return "failed"


def compute_follow_up(artifact: dict, conclusion: str | None = None) -> str:
    conclusion = conclusion or compute_conclusion(artifact)
    declared = [
        row.get("follow_up", "none")
        for row in artifact["release_items"] + artifact["confirmations"]
        if row.get("follow_up", "none") != "none"
    ]
    follow_up = declared[0] if declared else "none"
    require(
        all(value == follow_up for value in declared),
        "RLS_FOLLOW_UP_INVALID",
        "multiple follow-up destinations were declared",
    )
    if conclusion in {"partial", "failed"} and follow_up == "none":
        follow_up = "retry_rls"
    require(follow_up in FOLLOWUPS, "RLS_FOLLOW_UP_INVALID", "invalid follow-up")
    return follow_up


def apply_conclusion(artifact: dict) -> tuple[str, str]:
    conclusion = compute_conclusion(artifact)
    follow_up = compute_follow_up(artifact, conclusion)
    artifact["release_conclusion"] = conclusion
    artifact["follow_up"] = follow_up
    return conclusion, follow_up


def normalize_return_phase(requested: str, *, unique_imp_lineage: bool = True) -> str:
    require(requested in FOLLOWUPS, "RLS_FOLLOW_UP_INVALID", "invalid requested return phase")
    if requested == "return_imp" and not unique_imp_lineage:
        return "return_pln"
    return requested


def issue_reference(artifact_reference: str, follow_up: str, sequence: int = 1) -> str:
    require(follow_up.startswith("return_"), "RLS_FOLLOW_UP_INVALID", "return follow-up required")
    phase = follow_up.removeprefix("return_").upper()
    return f"{artifact_reference}#RLS-ISSUE-{phase}-{sequence:03d}"


def provisional_lifecycle_projection(artifact: dict) -> dict:
    conclusion = artifact.get("release_conclusion") or compute_conclusion(artifact)
    follow_up = artifact.get("follow_up") or compute_follow_up(artifact, conclusion)
    gate = artifact.get("artifact_gate", "pending")
    if artifact["artifact"]["revision_state"] == "open" or conclusion == "pending":
        next_phase = "RLS"
        next_action = "CONTINUE_RLS"
    elif follow_up == "retry_rls":
        next_phase = "RLS"
        next_action = "RETRY_RLS"
    elif follow_up.startswith("return_"):
        next_phase = follow_up.removeprefix("return_").upper()
        next_action = f"RETURN_TO_{next_phase}"
    else:
        next_phase = None
        next_action = "LIFECYCLE_COMPLETE"
    return {
        "phase": "RLS",
        "state": artifact["artifact"]["revision_state"],
        "release_conclusion": conclusion,
        "artifact_gate": gate,
        "follow_up": follow_up,
        "next_phase": next_phase,
        "next_action": next_action,
        "target_effect": bool(artifact.get("target_effect")),
        "basis": "provisional private RLS projection; shared query_rls.py deferred",
    }
