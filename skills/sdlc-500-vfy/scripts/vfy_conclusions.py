"""Deterministic Method → Target → CON-VER/CON-VAL aggregation."""
from __future__ import annotations

from typing import Any, Mapping

from vfy_common import RESULTS, require
from vfy_results import method_result_index


_PRECEDENCE = ("fail", "pending", "waived", "pass", "n/a")


def aggregate_values(values: list[str]) -> str:
    require(bool(values), "VFY_CONCLUSION_INCONSISTENT", "No values to aggregate")
    require(
        all(value in RESULTS for value in values),
        "VFY_CONCLUSION_INCONSISTENT",
        "Unknown Method or Target result",
        details={"values": values},
    )
    for result in _PRECEDENCE:
        if result in values:
            if result == "pass":
                if all(value in {"pass", "n/a"} for value in values):
                    return "pass"
                continue
            if result == "n/a":
                return "n/a"
            return result
    raise AssertionError("unreachable aggregation state")


def _method_supports_dimension(method: Mapping[str, Any], dimension: str) -> bool:
    purpose = str(method["purpose"])
    return purpose == dimension or purpose == "both"


def aggregate_target_conclusions(
    targets: tuple[Mapping[str, Any], ...],
    methods: tuple[Mapping[str, Any], ...],
    method_results: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result_index = method_result_index(method_results)
    output: list[dict[str, Any]] = []
    for target in targets:
        reference = str(target["reference"])
        related = [
            method for method in methods if reference in method["target_references"]
        ]
        require(
            bool(related),
            "VFY_METHOD_COVERAGE_INCOMPLETE",
            "Target has no Method coverage",
            details={"target": reference},
        )
        dimensions = (
            ("verification", "validation")
            if target["purpose"] == "both"
            else (str(target["purpose"]),)
        )
        projections: dict[str, str] = {}
        basis: list[str] = []
        for dimension in dimensions:
            dimension_methods = [
                method for method in related if _method_supports_dimension(method, dimension)
            ]
            require(
                bool(dimension_methods),
                "VFY_PURPOSE_MISMATCH",
                "Target has no compatible Method for one required dimension",
                details={"target": reference, "dimension": dimension},
            )
            values: list[str] = []
            for method in dimension_methods:
                result = result_index.get(str(method["id"]))
                require(
                    result is not None,
                    "VFY_CONCLUSION_INCONSISTENT",
                    "Method Result is missing",
                    details={"method_id": method["id"]},
                )
                values.append(str(result["result"]))
                basis.append(str(method["id"]))
                basis.extend(str(item) for item in result["evidence_references"])
            projections[dimension] = aggregate_values(values)

        conclusion = aggregate_values(list(projections.values()))
        output.append(
            {
                "target_reference": reference,
                "purpose": target["purpose"],
                "conclusion": conclusion,
                "dimension_projections": projections,
                "basis_references": list(dict.fromkeys(basis)),
                "exception_reference": None,
            }
        )
    return output


def aggregate_fixed_conclusions(
    targets: tuple[Mapping[str, Any], ...],
    target_conclusions: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    conclusion_index = {
        str(row["target_reference"]): row for row in target_conclusions
    }
    output: list[dict[str, Any]] = []
    for conclusion_id, dimension in (("CON-VER", "verification"), ("CON-VAL", "validation")):
        values: list[str] = []
        target_refs: list[str] = []
        basis: list[str] = []
        for target in targets:
            if target["purpose"] not in {dimension, "both"}:
                continue
            row = conclusion_index[str(target["reference"])]
            if target["purpose"] == "both":
                value = str(row["dimension_projections"][dimension])
            else:
                value = str(row["conclusion"])
            values.append(value)
            target_refs.append(str(target["reference"]))
            basis.extend(str(item) for item in row["basis_references"])
        result = aggregate_values(values) if values else "n/a"
        output.append(
            {
                "id": conclusion_id,
                "dimension": dimension,
                "conclusion": result,
                "target_references": target_refs,
                "basis_references": list(dict.fromkeys(basis)),
                "exception_references": [],
            }
        )
    return output


def product_result(fixed_conclusions: list[Mapping[str, Any]]) -> str:
    values = [str(item["conclusion"]) for item in fixed_conclusions]
    return aggregate_values(values)
