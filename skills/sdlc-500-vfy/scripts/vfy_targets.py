"""Authoritative VFY Target Set normalization and coverage rules."""
from __future__ import annotations

from typing import Any, Mapping

from vfy_common import PURPOSES, exact_item_reference, require, stable_unique


def normalize_targets(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = candidate.get("targets")
    require(
        isinstance(rows, list) and bool(rows),
        "VFY_TARGET_SET_INVALID",
        "Authoritative VFY Target Set is required",
        action="RETURN_TO_DESIGN",
    )
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    source_kinds: set[str] = set()

    for index, raw in enumerate(rows, 1):
        require(
            isinstance(raw, Mapping),
            "VFY_TARGET_SET_INVALID",
            "Target entries must be objects",
            action="RETURN_TO_DESIGN",
        )
        reference = exact_item_reference(str(raw.get("reference", "")))
        require(
            reference not in seen,
            "VFY_TARGET_SET_INVALID",
            "Target reference is duplicated",
            action="RETURN_TO_DESIGN",
            details={"reference": reference},
        )
        seen.add(reference)
        purpose = str(raw.get("purpose", "")).strip()
        require(
            purpose in PURPOSES,
            "VFY_TARGET_SET_INVALID",
            "Target Purpose must be verification, validation or both",
            action="RETURN_TO_DESIGN",
            details={"reference": reference},
        )
        if "#VFO-" in reference:
            inferred_source_kind = "vfo"
        elif "#AC-" in reference:
            inferred_source_kind = "ac"
        elif "#GOAL-" in reference or "#GOL-" in reference:
            inferred_source_kind = "goal"
        elif "#REQ-" in reference:
            inferred_source_kind = "requirement"
        else:
            inferred_source_kind = "other"
        declared_source_kind = str(raw.get("source_kind", "")).strip()
        require(
            not declared_source_kind or declared_source_kind == inferred_source_kind,
            "VFY_TARGET_SET_INVALID",
            "Target source kind conflicts with its exact reference",
            action="RETURN_TO_DESIGN",
            details={
                "reference": reference,
                "declared": declared_source_kind,
                "inferred": inferred_source_kind,
            },
        )
        source_kind = inferred_source_kind
        source_kinds.add(source_kind)
        require(
            source_kind != "requirement",
            "VFY_TARGET_SET_INVALID",
            "Requirements are covered by ACs and cannot be repeated as parallel VFY Targets",
            action="RETURN_TO_REQ",
            details={"reference": reference},
        )
        summary = str(raw.get("summary", "")).strip()
        require(
            bool(summary),
            "VFY_TARGET_SET_INVALID",
            "Target summary is required",
            action="RETURN_TO_DESIGN",
            details={"reference": reference},
        )
        output.append(
            {
                "reference": reference,
                "purpose": purpose,
                "summary": summary,
                "source_kind": source_kind,
                "obligation_references": list(
                    stable_unique(
                        raw.get("obligation_references", []),
                        field="target obligation",
                    )
                ),
            }
        )

    if "vfo" in source_kinds:
        require(
            not ({"ac", "goal"} & source_kinds),
            "VFY_TARGET_SET_INVALID",
            "AC and Goal cannot be repeated as parallel Targets when VFO authority exists",
            action="RETURN_TO_DESIGN",
        )
    else:
        allowed_fallback = candidate.get("target_fallback_allowed") is True
        require(
            allowed_fallback and source_kinds <= {"ac", "goal"},
            "VFY_TARGET_SET_INVALID",
            "Without VFO, only the explicit AC/Goal fallback contract is allowed",
            action="RETURN_TO_REQ",
        )
        require(
            "ac" in source_kinds and "goal" in source_kinds,
            "VFY_TARGET_SET_INVALID",
            "AC/Goal fallback requires both verification ACs and validation Goals",
            action="RETURN_TO_REQ",
        )

    return tuple(output)


def target_references(targets: tuple[Mapping[str, Any], ...]) -> tuple[str, ...]:
    return tuple(str(item["reference"]) for item in targets)


def target_by_reference(
    targets: tuple[Mapping[str, Any], ...]
) -> dict[str, Mapping[str, Any]]:
    return {str(item["reference"]): item for item in targets}
