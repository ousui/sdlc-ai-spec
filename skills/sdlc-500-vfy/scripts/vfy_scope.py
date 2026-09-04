"""Complete Delivery Scope normalization for VFY."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from vfy_common import (
    exact_artifact_reference,
    exact_item_reference,
    require,
    stable_unique,
)


_SCOPE_PHASES = ("PLN", "DSN", "REQ")


def normalize_scope(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Return one exact, complete Scope without selecting partial work items."""

    raw = candidate.get("scope")
    require(
        isinstance(raw, Mapping),
        "VFY_SCOPE_REQUIRED",
        "Candidate must contain one complete scope object",
        action="RETURN_TO_PLAN",
    )
    reference = str(raw.get("reference", "")).strip()
    phase = next((item for item in _SCOPE_PHASES if reference.startswith(item + "-")), None)
    require(
        phase is not None,
        "VFY_SCOPE_REQUIRED",
        "Scope reference must identify an exact REQ, DSN or PLN Revision",
        action="RETURN_TO_PLAN",
    )
    exact_artifact_reference(reference, phase)

    disposition = str(raw.get("disposition", "required")).strip()
    require(
        disposition in {"required", "n/a", "waived"},
        "VFY_SCOPE_REQUIRED",
        "Scope source disposition is invalid",
        action="RETURN_TO_PLAN",
    )
    if phase == "PLN":
        require(
            disposition == "required",
            "VFY_SCOPE_REQUIRED",
            "PLN Scope can only be selected when PLN is required",
            action="RETURN_TO_PLAN",
        )
    else:
        require(
            disposition in {"n/a", "waived", "required"},
            "VFY_SCOPE_REQUIRED",
            "Fallback Scope disposition is invalid",
            action="RETURN_TO_PLAN",
        )

    tokens = stable_unique(raw.get("delivery_scope", []), field="delivery_scope")
    require(
        bool(tokens),
        "VFY_SCOPE_REQUIRED",
        "Complete Delivery Scope cannot be empty",
        action="RETURN_TO_PLAN",
    )
    require(
        all(not item.lower().startswith(("partial:", "selected:")) for item in tokens),
        "VFY_SCOPE_REQUIRED",
        "VFY cannot select a partial Delivery Scope",
        action="RETURN_TO_PLAN",
    )

    source_inputs = tuple(
        exact_artifact_reference(str(item)) for item in raw.get("input_references", [])
    )
    if phase != "PLN":
        basis = raw.get("disposition_basis")
        require(
            disposition == "required" or isinstance(basis, str) and bool(basis.strip()),
            "VFY_SCOPE_REQUIRED",
            "REQ/DSN fallback requires the authoritative PLN disposition basis",
            action="RETURN_TO_PLAN",
        )

    imp_work_items = []
    for index, item in enumerate(raw.get("imp_work_items", []), 1):
        require(
            isinstance(item, Mapping),
            "VFY_SCOPE_REQUIRED",
            "IMP Work Item entries must be objects",
            action="RETURN_TO_PLAN",
        )
        work_reference = exact_item_reference(str(item.get("reference", "")))
        require(
            work_reference.startswith("PLN-") and "#WI-" in work_reference,
            "VFY_SCOPE_REQUIRED",
            "IMP Work Item requires an exact PLN Work Item reference",
            action="RETURN_TO_PLAN",
        )
        target_phase = str(item.get("target_phase", "IMP")).strip().upper()
        require(
            target_phase == "IMP",
            "VFY_SCOPE_REQUIRED",
            "imp_work_items may only contain Target Phase IMP",
            action="RETURN_TO_PLAN",
        )
        imp_work_items.append(
            {
                "reference": work_reference,
                "target_phase": "IMP",
                "binding_reference": exact_item_reference(
                    str(item.get("binding_reference", work_reference))
                ),
                "resource_ids": list(
                    stable_unique(item.get("resource_ids", []), field="resource_id")
                ),
                "depends_on": list(
                    stable_unique(item.get("depends_on", []), field="dependency")
                ),
            }
        )

    if phase == "PLN":
        require(
            bool(imp_work_items),
            "VFY_SCOPE_REQUIRED",
            "A required PLN Scope must expose its complete IMP Work Item set",
            action="RETURN_TO_PLAN",
        )

    return {
        "reference": reference,
        "phase": phase,
        "disposition": disposition,
        "delivery_scope": list(tokens),
        "input_references": list(source_inputs),
        "disposition_basis": raw.get("disposition_basis"),
        "imp_work_items": imp_work_items,
        "scope_digest": raw.get("scope_digest"),
        "raw": deepcopy(dict(raw)),
    }


def require_single_scope(candidate: Mapping[str, Any]) -> dict[str, Any]:
    candidates = candidate.get("scope_candidates")
    if candidates is not None:
        require(
            isinstance(candidates, list) and len(candidates) == 1,
            "VFY_SCOPE_AMBIGUOUS",
            "Exactly one complete Delivery Scope must be selected",
            status="action_required",
            details={"candidate_count": len(candidates) if isinstance(candidates, list) else None},
        )
        merged = dict(candidate)
        merged["scope"] = candidates[0]
        return normalize_scope(merged)
    return normalize_scope(candidate)


def scope_resource_ids(scope: Mapping[str, Any]) -> tuple[str, ...]:
    resources: list[str] = []
    for item in scope.get("imp_work_items", []):
        for resource in item.get("resource_ids", []):
            if resource not in resources:
                resources.append(resource)
    if resources:
        return tuple(resources)
    for token in scope.get("delivery_scope", []):
        if token.startswith("resource:"):
            resource = token.split(":", 1)[1]
            if resource not in resources:
                resources.append(resource)
    return tuple(resources)


def validate_scope_subject_coverage(
    scope: Mapping[str, Any], subjects: tuple[Mapping[str, Any], ...]
) -> None:
    expected = scope_resource_ids(scope)
    actual = tuple(dict.fromkeys(str(item["resource_id"]) for item in subjects))
    if expected:
        require(
            set(expected) == set(actual),
            "VFY_SUBJECT_SET_INCOMPLETE",
            "Subject resources must exactly cover the complete Delivery Scope",
            details={"expected": list(expected), "actual": list(actual)},
        )
