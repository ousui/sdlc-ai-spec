"""Current terminal IMP Product Result Subject normalization."""
from __future__ import annotations

from typing import Any, Mapping

from vfy_common import (
    DIGEST_RE,
    exact_artifact_reference,
    exact_item_reference,
    immutable_locator,
    require,
    sha256_value,
    stable_unique,
)


def _normalize_dependency(value: Any) -> str:
    reference = str(value).strip()
    if reference.startswith("IMP-"):
        return exact_item_reference(reference)
    return immutable_locator(reference)


def normalize_subjects(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = candidate.get("subjects")
    require(
        isinstance(rows, list) and bool(rows),
        "VFY_SUBJECT_SET_INCOMPLETE",
        "VFY requires the complete current terminal Subject Set",
    )
    output: list[dict[str, Any]] = []
    seen_references: set[str] = set()
    seen_resources: set[str] = set()

    for index, raw in enumerate(rows, 1):
        require(
            isinstance(raw, Mapping),
            "VFY_SUBJECT_SET_INCOMPLETE",
            "Subject entries must be objects",
            details={"index": index},
        )
        reference = immutable_locator(str(raw.get("reference", "")))
        require(
            reference not in seen_references,
            "VFY_SUBJECT_SET_INCOMPLETE",
            "Duplicate Subject reference",
            details={"reference": reference},
        )
        seen_references.add(reference)

        resource_id = str(raw.get("resource_id", "")).strip()
        require(
            bool(resource_id) and resource_id not in seen_resources,
            "VFY_SUBJECT_SET_INCOMPLETE",
            "Each planned Resource requires one unique terminal Subject",
            details={"resource_id": resource_id},
        )
        seen_resources.add(resource_id)

        imp_reference = exact_artifact_reference(
            str(raw.get("imp_revision_reference", "")), "IMP"
        )
        if reference.startswith("IMP-"):
            require(
                reference.startswith(imp_reference + "/RES-")
                or reference.startswith(imp_reference + "/RESULT-RES-"),
                "VFY_SUBJECT_NOT_CURRENT",
                "IMP Result Member must belong to the declared frozen IMP Revision",
                details={"reference": reference, "imp_revision": imp_reference},
            )

        binding = str(raw.get("binding_lineage", "")).strip()
        attempt = str(raw.get("attempt", "")).strip()
        require(
            bool(binding) and bool(attempt),
            "VFY_SUBJECT_NOT_CURRENT",
            "Subject requires exact IMP Binding Lineage and Attempt",
            details={"reference": reference},
        )
        require(
            raw.get("claim_state") == "completed",
            "VFY_SUBJECT_NOT_CURRENT",
            "Only the Current completed Claim can provide a VFY Subject",
            details={"reference": reference, "claim_state": raw.get("claim_state")},
        )
        require(
            raw.get("imp_revision_state") == "frozen",
            "VFY_SUBJECT_NOT_CURRENT",
            "Subject IMP Revision must be frozen",
            details={"reference": reference},
        )
        require(
            raw.get("current_valid") is True,
            "VFY_SUBJECT_NOT_CURRENT",
            "Subject is stale or no longer current-valid",
            details={"reference": reference},
        )
        require(
            raw.get("dependency_chain_valid") is True,
            "VFY_DEPENDENCY_CHAIN_INVALID",
            "Subject dependency Result chain is not current-valid",
            details={"reference": reference},
        )

        digest = str(raw.get("result_digest", "")).strip()
        require(
            DIGEST_RE.fullmatch(digest) is not None,
            "VFY_SUBJECT_NOT_CURRENT",
            "Subject requires a canonical Result Digest",
            details={"reference": reference},
        )
        baseline_reference = str(raw.get("baseline_reference", "")).strip()
        require(
            bool(baseline_reference),
            "VFY_SUBJECT_SET_INCOMPLETE",
            "Subject requires an immutable Resource Baseline reference",
            details={"reference": reference},
        )
        changed_scope = list(
            stable_unique(raw.get("cumulative_changed_scope", []), field="changed_scope")
        )
        dependencies = tuple(
            _normalize_dependency(item)
            for item in raw.get("dependency_result_references", [])
        )
        output.append(
            {
                "reference": reference,
                "resource_id": resource_id,
                "imp_revision_reference": imp_reference,
                "binding_lineage": binding,
                "attempt": attempt,
                "claim_state": "completed",
                "imp_revision_state": "frozen",
                "baseline_reference": baseline_reference,
                "result_digest": digest,
                "cumulative_changed_scope": changed_scope,
                "dependency_result_references": list(dependencies),
                "current_valid": True,
                "dependency_chain_valid": True,
            }
        )

    return tuple(output)


def subject_references(subjects: tuple[Mapping[str, Any], ...]) -> tuple[str, ...]:
    return tuple(str(item["reference"]) for item in subjects)


def subject_set_digest(subjects: tuple[Mapping[str, Any], ...]) -> str:
    return sha256_value([dict(item) for item in subjects])


def assert_subjects_still_current(
    subjects: tuple[Mapping[str, Any], ...],
    current_snapshot: Mapping[str, Any] | None,
) -> None:
    """Recheck current-valid flags and optional exact readback before Gate."""

    for item in subjects:
        require(
            item.get("current_valid") is True
            and item.get("dependency_chain_valid") is True
            and item.get("claim_state") == "completed"
            and item.get("imp_revision_state") == "frozen",
            "VFY_SUBJECT_NOT_CURRENT",
            "Subject became stale before VFY Gate",
            details={"reference": item.get("reference")},
        )
    if current_snapshot is None:
        return
    expected = {
        str(item["reference"]): (
            str(item["result_digest"]),
            str(item["binding_lineage"]),
            str(item["attempt"]),
        )
        for item in subjects
    }
    actual_rows = current_snapshot.get("subjects")
    require(
        isinstance(actual_rows, list),
        "VFY_SUBJECT_NOT_CURRENT",
        "Current Subject readback is missing",
    )
    actual = {
        str(item.get("reference")): (
            str(item.get("result_digest")),
            str(item.get("binding_lineage")),
            str(item.get("attempt")),
        )
        for item in actual_rows
        if isinstance(item, Mapping)
    }
    require(
        actual == expected,
        "VFY_SUBJECT_NOT_CURRENT",
        "Current Subject readback differs from the frozen VFY Contract",
        details={"expected_digest": sha256_value(expected), "actual_digest": sha256_value(actual)},
    )
