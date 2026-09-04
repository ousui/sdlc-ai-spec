"""Upstream Return construction, exact validation and proof-derived resolution."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from vfy_common import (
    RETURN_ID_RE,
    RETURN_PHASES,
    exact_item_reference,
    immutable_locator,
    require,
    stable_unique,
)


def _normalize_subject_reference(value: str) -> str:
    text = str(value).strip()
    if text.startswith("IMP-") and ("/RES-" in text or "/RESULT-RES-" in text):
        return immutable_locator(text)
    return exact_item_reference(text)


def _binding_lineage_key(value: str) -> tuple[str, str]:
    reference = str(value).strip()
    return (
        reference.split("#", 1)[0].split("@", 1)[0],
        reference.rsplit("#", 1)[-1],
    )


def normalize_returns(
    rows: Any,
    *,
    subject_lineages: Mapping[str, str],
    allow_resolved: bool = False,
) -> list[dict[str, Any]]:
    require(isinstance(rows, list), "VFY_RETURN_INVALID", "Returns must be an array")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        require(isinstance(raw, Mapping), "VFY_RETURN_INVALID", "Return entries must be objects")
        return_id = str(raw.get("id", "")).strip()
        require(
            RETURN_ID_RE.fullmatch(return_id) is not None and return_id not in seen,
            "VFY_RETURN_INVALID",
            "Return ID must be unique and use RET-NNN",
            details={"return_id": return_id},
        )
        seen.add(return_id)
        phase = str(raw.get("return_phase", "")).strip().upper()
        require(
            phase in RETURN_PHASES,
            "VFY_RETURN_INVALID",
            "Return Phase must be REQ, DSN, PLN or IMP",
            details={"return_id": return_id},
        )
        targets = tuple(
            exact_item_reference(item)
            for item in stable_unique(raw.get("target_references", []), field="target")
        )
        methods = tuple(stable_unique(raw.get("method_references", []), field="method"))
        subjects = tuple(
            _normalize_subject_reference(item)
            for item in stable_unique(raw.get("subject_references", []), field="subject")
        )
        evidence = tuple(
            stable_unique(raw.get("evidence_references", []), field="evidence")
        )
        observed_gap = str(raw.get("observed_gap", "")).strip()
        required_outcome = str(raw.get("required_outcome", "")).strip()
        require(
            bool(targets)
            and bool(methods)
            and bool(subjects)
            and bool(evidence)
            and bool(observed_gap)
            and bool(required_outcome),
            "VFY_RETURN_INVALID",
            "Return requires Target, Method, Subject, observed gap, required outcome and Evidence",
            details={"return_id": return_id},
        )
        binding = raw.get("imp_binding_reference")
        binding_lineage = raw.get("imp_binding_lineage")
        if phase == "IMP":
            require(
                isinstance(binding, str) and bool(binding.strip()),
                "VFY_RETURN_INVALID",
                "IMP Return requires exact current IMP Binding reference",
                details={"return_id": return_id},
            )
            binding = exact_item_reference(binding)
            lineages = {subject_lineages.get(reference) for reference in subjects}
            require(
                None not in lineages and len(lineages) == 1,
                "VFY_RETURN_INVALID",
                "IMP Return Subjects must resolve to one Binding Lineage",
                details={"return_id": return_id, "lineages": sorted(str(item) for item in lineages)},
            )
            expected_lineage = next(iter(lineages))
            require(
                str(binding_lineage or expected_lineage) == expected_lineage,
                "VFY_RETURN_INVALID",
                "IMP Return Binding Lineage differs from its Subjects",
                details={"return_id": return_id},
            )
            binding_lineage = expected_lineage
        else:
            require(
                binding in {None, "", "N/A"} and binding_lineage in {None, "", "N/A"},
                "VFY_RETURN_INVALID",
                "Only an IMP Return may bind an IMP Lineage",
                details={"return_id": return_id},
            )
            binding = "N/A"
            binding_lineage = "N/A"

        requested_status = str(raw.get("status", "open")).strip()
        resolution_references = list(
            stable_unique(raw.get("resolution_references", []), field="resolution")
        )
        if not allow_resolved:
            require(
                requested_status in {"", "open"} and not resolution_references,
                "VFY_RETURN_INVALID",
                "Return cannot be caller-marked resolved; later VFY proof must derive resolution",
                details={"return_id": return_id},
            )
            requested_status = "open"
        else:
            require(
                requested_status in {"open", "resolved"},
                "VFY_RETURN_INVALID",
                "Return status must be open or proof-derived resolved",
            )
            if requested_status == "resolved":
                require(
                    bool(resolution_references),
                    "VFY_RETURN_INVALID",
                    "Proof-derived resolved Return requires current VFY proof references",
                )
        output.append(
            {
                "id": return_id,
                "return_phase": phase,
                "imp_binding_reference": binding,
                "imp_binding_lineage": binding_lineage,
                "target_references": list(targets),
                "method_references": list(methods),
                "subject_references": list(subjects),
                "observed_gap": observed_gap,
                "required_outcome": required_outcome,
                "evidence_references": list(evidence),
                "status": requested_status,
                "resolution_references": resolution_references,
            }
        )
    return output


def validate_returns(state: Mapping[str, Any]) -> None:
    targets = {str(item["reference"]) for item in state["targets"]}
    methods = {str(item["id"]): item for item in state["methods"]}
    subjects = {str(item["reference"]): item for item in state["subjects"]}
    evidence = {str(item["reference"]): item for item in state["evidence"]}
    seen: set[str] = set()
    for row in state.get("returns", []):
        identity = str(row.get("id", ""))
        require(
            RETURN_ID_RE.fullmatch(identity) is not None and identity not in seen,
            "VFY_RETURN_INVALID",
            "Stored Return identity is missing or duplicated",
        )
        seen.add(identity)
        require(
            set(row.get("target_references", [])) <= targets
            and set(row.get("method_references", [])) <= set(methods)
            and set(row.get("subject_references", [])) <= set(subjects)
            and set(row.get("evidence_references", [])) <= set(evidence),
            "VFY_RETURN_INVALID",
            "Return references objects outside the current VFY state",
            details={"return_id": identity},
        )
        for method_id in row["method_references"]:
            method = methods[method_id]
            require(
                set(row["target_references"]) <= set(method["target_references"])
                and set(row["subject_references"]) <= set(method["subject_references"]),
                "VFY_RETURN_INVALID",
                "Return Target/Subject does not belong to its failed Method",
                details={"return_id": identity, "method_id": method_id},
            )
        if row["return_phase"] == "IMP":
            lineages = {
                subjects[reference]["binding_lineage"]
                for reference in row["subject_references"]
            }
            require(
                len(lineages) == 1
                and row["imp_binding_lineage"] in lineages
                and _binding_lineage_key(row["imp_binding_reference"])
                == _binding_lineage_key(row["imp_binding_lineage"]),
                "VFY_RETURN_INVALID",
                "IMP Return does not bind one exact current Lineage",
                details={"return_id": identity},
            )
        else:
            require(
                row["imp_binding_reference"] == "N/A"
                and row["imp_binding_lineage"] == "N/A",
                "VFY_RETURN_INVALID",
                "Non-IMP Return contains IMP binding data",
            )
        if row["status"] == "resolved":
            require(
                bool(row["resolution_references"]),
                "VFY_RETURN_INVALID",
                "Resolved Return has no proof references",
            )


def derive_control_resolutions(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Validate and return only proof-complete current control resolutions."""

    controls = {str(item) for item in state.get("control_inputs", [])}
    authorities = {
        str(item.get("reference")): item
        for item in state.get("control_authorities", [])
        if isinstance(item, Mapping)
    }
    methods = {str(item["id"]): item for item in state["methods"]}
    results = {str(item["method_id"]): item for item in state["method_results"]}
    targets = {str(item["target_reference"]): item for item in state["target_conclusions"]}
    current_subjects = {str(item["reference"]) for item in state["subjects"]}
    current_lineages = {
        str(item["binding_lineage"]) for item in state["subjects"]
    }
    evidence = {
        str(item["reference"]): item for item in state["evidence"]
    }
    output = []
    seen_controls: set[str] = set()
    for raw in state.get("control_resolutions", []):
        require(
            isinstance(raw, Mapping),
            "VFY_CONTROL_INVALID",
            "Control resolution entries must be objects",
        )
        control = str(raw.get("control_reference", ""))
        require(
            control not in seen_controls,
            "VFY_CONTROL_INVALID",
            "Control resolution is duplicated",
            details={"control_reference": control},
        )
        seen_controls.add(control)
        authority = authorities.get(control)
        method_ids = list(stable_unique(raw.get("method_references", []), field="control method"))
        target_refs = list(stable_unique(raw.get("target_references", []), field="control target"))
        evidence_refs = list(stable_unique(raw.get("evidence_references", []), field="control evidence"))
        require(
            control in controls
            and authority is not None
            and authority.get("authority_verified") is True
            and bool(method_ids)
            and bool(target_refs)
            and bool(evidence_refs),
            "VFY_CONTROL_INVALID",
            "Control resolution requires exact frozen authority and proof references",
            details={"control_reference": control},
        )
        required_outcome = str(
            authority.get("required_outcome")
            or authority.get("expected")
            or authority.get("statement")
            or ""
        ).strip()
        observed_gap = str(
            authority.get("observed_gap")
            or authority.get("observed")
            or authority.get("statement")
            or ""
        ).strip()
        require(
            bool(required_outcome) and bool(observed_gap),
            "VFY_CONTROL_INVALID",
            "Control authority has no observed gap or required outcome",
        )
        authority_methods = set(authority.get("method_references", []))
        authority_targets = set(authority.get("target_references", []))
        authority_evidence = set(authority.get("evidence_references", []))
        if control.startswith("VFY-"):
            require(
                authority.get("return_phase") in {"REQ", "DSN", "PLN", "IMP"}
                and bool(authority_methods)
                and bool(authority_targets)
                and bool(authority_evidence)
                and set(method_ids) == authority_methods
                and set(target_refs) == authority_targets,
                "VFY_CONTROL_INVALID",
                "VFY Return resolution differs from its frozen Method or Target boundary",
                details={"control_reference": control},
            )
            if authority.get("return_phase") == "IMP":
                binding = str(authority.get("imp_binding_reference", ""))
                binding_key = _binding_lineage_key(binding)
                current_keys = {
                    _binding_lineage_key(lineage)
                    for lineage in current_lineages
                }
                require(
                    len(current_lineages) == 1 and binding_key in current_keys,
                    "VFY_CONTROL_INVALID",
                    "IMP Return resolution differs from the current Binding Lineage",
                    details={"control_reference": control},
                )
        else:
            follow_up = str(authority.get("follow_up_disposition", ""))
            require(
                follow_up in {"return_req", "return_dsn", "return_pln", "return_imp"}
                and bool(authority_evidence),
                "VFY_CONTROL_INVALID",
                "RLS Issue has no exact product-correction route or Evidence",
                details={"control_reference": control},
            )
            if follow_up == "return_imp":
                require(
                    len(current_lineages) == 1,
                    "VFY_CONTROL_INVALID",
                    "RLS return_imp resolution requires one current Binding Lineage",
                    details={"control_reference": control},
                )
        for method_id in method_ids:
            require(
                method_id in methods
                and control in methods[method_id]["obligation_references"]
                and results[method_id]["result"] == "pass"
                and current_subjects == set(results[method_id]["actual_subject_references"]),
                "VFY_CONTROL_INVALID",
                "Control resolution Method does not prove the current Subject outcome",
                details={"control_reference": control, "method_id": method_id},
            )
        require(
            all(
                reference in targets and targets[reference]["conclusion"] == "pass"
                for reference in target_refs
            )
            and set(evidence_refs) <= set(evidence),
            "VFY_CONTROL_INVALID",
            "Control resolution lacks passing Target Conclusion or immutable Evidence",
            details={"control_reference": control},
        )
        for reference in evidence_refs:
            row = evidence[reference]
            require(
                row.get("result") == "pass"
                and str(row.get("method_id")) in method_ids
                and set(row.get("target_references", [])) <= set(target_refs)
                and set(row.get("subject_references", [])) == current_subjects
                and reference
                in set(results[str(row.get("method_id"))].get("evidence_references", [])),
                "VFY_CONTROL_INVALID",
                "Control resolution Evidence does not bind its current Method, Target and Subject",
                details={"control_reference": control, "evidence_reference": reference},
            )
        previous_subjects = set(authority.get("subject_references", []))
        if not previous_subjects:
            previous_subjects = {
                str(item)
                for item in authority.get("source_references", [])
                if str(item).startswith("IMP-")
                and ("/RES-" in str(item) or "/RESULT-RES-" in str(item))
            }
        require(
            not previous_subjects or previous_subjects != current_subjects,
            "VFY_CONTROL_INVALID",
            "Control recovery must use a changed current Subject Set",
            details={"control_reference": control},
        )
        output.append(
            {
                "control_reference": control,
                "required_outcome": required_outcome,
                "method_references": method_ids,
                "target_references": target_refs,
                "evidence_references": evidence_refs,
                "subject_changed": True,
                "status": "resolved",
            }
        )
    return output


def validate_failed_results_have_returns(
    method_results: Sequence[Mapping[str, Any]],
    returns: Sequence[Mapping[str, Any]],
    *,
    accepted_failure_methods: set[str] | None = None,
) -> None:
    accepted = accepted_failure_methods or set()
    return_by_id = {str(item["id"]): item for item in returns}
    for result in method_results:
        method_id = str(result.get("method_id", ""))
        if result.get("result") != "fail" or method_id in accepted:
            continue
        refs = list(result.get("return_references", []))
        require(
            bool(refs),
            "VFY_RETURN_INVALID",
            "Every confirmed product failure that requires rework must identify a Return",
            details={"method_id": method_id},
        )
        for reference in refs:
            return_id = str(reference).rsplit("#", 1)[-1]
            require(
                return_id in return_by_id
                and method_id in return_by_id[return_id]["method_references"],
                "VFY_RETURN_INVALID",
                "Method Result references an unknown or unrelated Return",
                details={"method_id": method_id, "reference": reference},
            )


def unresolved_returns(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(str(item["id"]) for item in rows if item.get("status") != "resolved")
