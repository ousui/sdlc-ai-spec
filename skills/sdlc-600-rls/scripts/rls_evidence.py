"""Immutable RLS Evidence creation and row-to-event binding verification."""
from __future__ import annotations

from typing import Any

from rls_common import canonical_json, require, sha256_bytes, stable_unique, utc_now

CANCEL_EVENT_ITEM = "CANCEL-BEFORE-EFFECT"


def build_cancel_evidence(
    artifact: dict,
    target_snapshot: Any,
    affected_items,
) -> dict:
    """Build one content-addressed controller event covering exact pending rows."""
    affected = stable_unique(affected_items)
    require(
        bool(affected),
        "RLS_CANCEL_NOT_ALLOWED",
        "cancel requires at least one pending RLI or RCF",
    )
    event = {
        "kind": "cancel_before_effect",
        "item": CANCEL_EVENT_ITEM,
        "artifact_reference": artifact["artifact"]["reference"],
        "release_reference": artifact["release_contract"]["release_reference"],
        "target": artifact["release_contract"]["release_target"],
        "affected_items": affected,
        "result": "cancelled",
        "target_snapshot": target_snapshot,
        "target_effect": False,
        "observed_at": utc_now(),
        "executor": "rls-controller",
    }
    payload = (canonical_json(event) + "\n").encode("utf-8")
    digest = sha256_bytes(payload)
    return {
        "reference": f"SANDBOX-EVD-{digest}",
        "sha256": digest,
        "locator": f"evidence/{digest}.json",
        "event": event,
    }


def _events_for(row: dict, evidence_by_ref: dict[str, dict]) -> list[dict]:
    output: list[dict] = []
    for reference in row.get("evidence_references", []):
        require(
            reference in evidence_by_ref,
            "RLS_EVIDENCE_TAMPERED",
            "row Evidence is missing",
            item=row.get("id"),
            reference=reference,
        )
        output.append(evidence_by_ref[reference]["event"])
    return output


def _direct_event(
    row: dict,
    events: list[dict],
    artifact: dict,
    allowed_results: set[str],
) -> bool:
    expected_artifact = artifact["artifact"]["reference"]
    expected_release = artifact["release_contract"]["release_reference"]
    expected_target = artifact["release_contract"]["release_target"]
    return any(
        event.get("item") == row["id"]
        and event.get("result") in allowed_results
        and event.get("executor") == row.get("executor")
        and event.get("artifact_reference") == expected_artifact
        and event.get("release_reference") == expected_release
        and event.get("target") == expected_target
        for event in events
    )


def _cancel_event_covers(
    row: dict,
    events: list[dict],
    artifact: dict,
) -> bool:
    expected_artifact = artifact["artifact"]["reference"]
    expected_release = artifact["release_contract"]["release_reference"]
    expected_target = artifact["release_contract"]["release_target"]
    return any(
        event.get("kind") == "cancel_before_effect"
        and event.get("item") == CANCEL_EVENT_ITEM
        and event.get("artifact_reference") == expected_artifact
        and event.get("release_reference") == expected_release
        and event.get("target") == expected_target
        and event.get("target_effect") is False
        and event.get("executor") == "rls-controller"
        and row["id"] in event.get("affected_items", [])
        for event in events
    )


def _causative_no_effect_event(
    events: list[dict],
    artifact: dict,
) -> bool:
    release_ids = {row["id"] for row in artifact["release_items"]}
    expected_artifact = artifact["artifact"]["reference"]
    expected_release = artifact["release_contract"]["release_reference"]
    expected_target = artifact["release_contract"]["release_target"]
    return any(
        event.get("item") in release_ids
        and event.get("result") in {"fail", "cancelled"}
        and event.get("target_effect") is False
        and event.get("artifact_reference") == expected_artifact
        and event.get("release_reference") == expected_release
        and event.get("target") == expected_target
        for event in events
    )


def validate_evidence(artifact: dict) -> None:
    evidence = artifact.get("evidence")
    require(
        isinstance(evidence, list),
        "RLS_EVIDENCE_TAMPERED",
        "Evidence must be an array",
    )
    evidence_by_ref: dict[str, dict] = {}
    for row in evidence:
        require(
            isinstance(row, dict)
            and isinstance(row.get("reference"), str)
            and isinstance(row.get("event"), dict),
            "RLS_EVIDENCE_TAMPERED",
            "Evidence is incomplete",
        )
        reference = row["reference"]
        require(
            reference not in evidence_by_ref,
            "RLS_EVIDENCE_TAMPERED",
            "Evidence references must be unique",
        )
        payload = (canonical_json(row["event"]) + "\n").encode("utf-8")
        require(
            row.get("sha256") == sha256_bytes(payload)
            and reference == f"SANDBOX-EVD-{row['sha256']}",
            "RLS_EVIDENCE_TAMPERED",
            "Evidence digest or reference does not match immutable bytes",
        )
        evidence_by_ref[reference] = row

    referenced: set[str] = set()
    for row in artifact["release_items"] + artifact["confirmations"]:
        referenced.update(row.get("evidence_references", []))
    require(
        set(evidence_by_ref) <= referenced,
        "RLS_EVIDENCE_TAMPERED",
        "unreferenced Evidence cannot enter the RLS record",
        references=sorted(set(evidence_by_ref) - referenced),
    )

    for row in artifact["release_items"]:
        result = row["result"]
        events = _events_for(row, evidence_by_ref)
        if result in {"success", "partial", "fail"}:
            require(
                bool(events)
                and _direct_event(row, events, artifact, {result}),
                "RLS_EVIDENCE_TAMPERED",
                "terminal RLI needs directly bound result Evidence",
                item=row["id"],
            )
        elif result == "cancelled":
            require(
                bool(events) and _cancel_event_covers(row, events, artifact),
                "RLS_EVIDENCE_TAMPERED",
                "cancelled RLI is not covered by exact controller Evidence",
                item=row["id"],
            )
        elif result == "waived":
            require(
                row.get("exception_reference"),
                "RLS_CONTRACT_INVALID",
                "waived RLI needs an Exception",
            )

    for row in artifact["confirmations"]:
        result = row["result"]
        events = _events_for(row, evidence_by_ref)
        if result in {"pass", "fail"}:
            require(
                bool(events)
                and _direct_event(row, events, artifact, {result}),
                "RLS_EVIDENCE_TAMPERED",
                "terminal RCF needs directly bound target Evidence",
                item=row["id"],
            )
            if not artifact.get("provisional", True):
                from rls_confirmation_policy import verify_confirmation_event
                require(len(events) == 1, "RLS_EVIDENCE_TAMPERED", "one RCF requires one unambiguous observation")
                verify_confirmation_event(artifact, row, events[0])
        elif result == "not_run":
            require(
                bool(events)
                and (
                    _cancel_event_covers(row, events, artifact)
                    if artifact.get("cancel_requested")
                    else _causative_no_effect_event(events, artifact)
                ),
                "RLS_EVIDENCE_TAMPERED",
                "RCF not_run lacks exact cancel/failure-before-effect Evidence",
                item=row["id"],
            )
        elif result == "n/a":
            require(
                row.get("objective_na_reason"),
                "RLS_CONTRACT_INVALID",
                "RCF n/a needs an objective reason",
            )
        elif result == "waived":
            require(
                row.get("exception_reference"),
                "RLS_CONTRACT_INVALID",
                "waived RCF needs an active Exception",
            )
