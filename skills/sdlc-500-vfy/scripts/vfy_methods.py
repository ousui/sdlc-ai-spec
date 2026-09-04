"""VFY Method Contract normalization and complete obligation coverage."""
from __future__ import annotations

from typing import Any, Mapping

from vfy_common import (
    DISPOSITIONS,
    EXECUTION_MODES,
    METHOD_TYPES,
    PURPOSES,
    VFY_METHOD_RE,
    exact_item_reference,
    immutable_locator,
    require,
    safe_project_path,
    stable_unique,
)
from vfy_targets import target_by_reference

_ALLOWED_PROCEDURES = frozenset(
    {
        "file_exists",
        "file_not_exists",
        "json_field_equals",
        "sha256_equals",
        "command",
        "manual_observation",
        "evidence_review",
    }
)
_COMMAND_POLICY = "deterministic-test-v1"


def _normalize_reference(value: str) -> str:
    text = str(value).strip()
    if text.startswith("IMP-") and "/RES-" in text:
        return immutable_locator(text)
    if text.startswith("IMP-") and "/RESULT-RES-" in text:
        return immutable_locator(text)
    return exact_item_reference(text)


def _purpose_compatible(target_purpose: str, method_purpose: str) -> bool:
    if target_purpose == "verification":
        return method_purpose in {"verification", "both"}
    if target_purpose == "validation":
        return method_purpose in {"validation", "both"}
    return method_purpose in PURPOSES


def normalize_methods(
    candidate: Mapping[str, Any],
    targets: tuple[Mapping[str, Any], ...],
    subject_references: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    rows = candidate.get("methods")
    require(
        isinstance(rows, list) and bool(rows),
        "VFY_METHOD_COVERAGE_INCOMPLETE",
        "VFY Method Set is required",
    )
    target_index = target_by_reference(targets)
    subject_set = set(subject_references)
    output: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index, raw in enumerate(rows, 1):
        require(
            isinstance(raw, Mapping),
            "VFY_METHOD_COVERAGE_INCOMPLETE",
            "Method entries must be objects",
            details={"index": index},
        )
        method_id = str(raw.get("id", "")).strip()
        require(
            VFY_METHOD_RE.fullmatch(method_id) is not None and method_id not in seen,
            "VFY_METHOD_COVERAGE_INCOMPLETE",
            "Method ID must be unique and use VFM-NNN",
            details={"method_id": method_id},
        )
        seen.add(method_id)
        purpose = str(raw.get("purpose", "")).strip()
        method_type = str(raw.get("method_type", "")).strip()
        disposition = str(raw.get("disposition", "required")).strip()
        mode = str(raw.get("execution_mode", "")).strip()
        require(
            purpose in PURPOSES,
            "VFY_PURPOSE_MISMATCH",
            "Method Purpose is invalid",
            details={"method_id": method_id},
        )
        require(
            method_type in METHOD_TYPES,
            "VFY_METHOD_NOT_READY",
            "Method Type must be inspection, analysis, demonstration or test",
            details={"method_id": method_id, "method_type": method_type},
        )
        require(
            disposition in DISPOSITIONS,
            "VFY_METHOD_NOT_READY",
            "Method Disposition is invalid",
            details={"method_id": method_id},
        )
        require(
            mode in EXECUTION_MODES,
            "VFY_METHOD_NOT_READY",
            "Execution Mode must be automated, manual or hybrid",
            details={"method_id": method_id},
        )

        target_refs = tuple(
            exact_item_reference(item)
            for item in stable_unique(raw.get("target_references", []), field="target")
        )
        method_subjects = tuple(
            immutable_locator(item)
            for item in stable_unique(raw.get("subject_references", []), field="subject")
        )
        obligations = tuple(
            _normalize_reference(item)
            for item in stable_unique(
                raw.get("obligation_references", []), field="obligation"
            )
        )
        require(
            bool(target_refs) and bool(method_subjects),
            "VFY_METHOD_COVERAGE_INCOMPLETE",
            "Every Method requires Target and Subject references",
            details={"method_id": method_id},
        )
        require(
            all(item in target_index for item in target_refs),
            "VFY_METHOD_COVERAGE_INCOMPLETE",
            "Method references an unknown Target",
            details={"method_id": method_id},
        )
        require(
            set(method_subjects) <= subject_set,
            "VFY_SUBJECT_NOT_CURRENT",
            "Method references a Subject outside the frozen Subject Set",
            details={"method_id": method_id},
        )
        for target_ref in target_refs:
            require(
                _purpose_compatible(str(target_index[target_ref]["purpose"]), purpose),
                "VFY_PURPOSE_MISMATCH",
                "Method Purpose is incompatible with its Target",
                details={"method_id": method_id, "target": target_ref},
            )

        exception_reference = raw.get("exception_reference")
        if disposition == "waived":
            require(
                isinstance(exception_reference, str) and bool(exception_reference.strip()),
                "VFY_METHOD_NOT_READY",
                "A waived Method requires an exact active Exception reference",
                details={"method_id": method_id},
            )
            exception_reference = exact_item_reference(exception_reference)
            require(
                "#EX-" in exception_reference,
                "VFY_METHOD_NOT_READY",
                "Waived Method Exception reference must select EX-NNN",
                details={"method_id": method_id},
            )
        else:
            exception_reference = None

        n_a_basis = raw.get("n_a_basis")
        if disposition == "n/a":
            require(
                isinstance(n_a_basis, str)
                and bool(n_a_basis.strip())
                and not any(
                    word in n_a_basis.lower()
                    for word in ("unavailable", "missing tool", "no person", "not run")
                ),
                "VFY_METHOD_NOT_READY",
                "n/a requires objective non-applicability, not execution unavailability",
                details={"method_id": method_id},
            )

        procedure = raw.get("procedure")
        pass_criteria = str(raw.get("pass_criteria", "")).strip()
        evidence_requirement = str(raw.get("evidence_requirement", "")).strip()
        executor_identity = str(raw.get("executor_identity", "")).strip()
        environment = raw.get("environment") or {
            "project_root": ".",
            "data_contract": "current exact Subject workspace",
        }
        require(
            isinstance(environment, Mapping) and bool(environment),
            "VFY_METHOD_NOT_READY",
            "Method Environment/Data contract is required",
            details={"method_id": method_id},
        )
        if disposition in {"required", "embedded"}:
            require(
                isinstance(procedure, Mapping)
                and str(procedure.get("kind", "")) in _ALLOWED_PROCEDURES,
                "VFY_METHOD_NOT_READY",
                "Required/embedded Method needs a supported frozen procedure",
                details={"method_id": method_id},
            )
            require(
                bool(pass_criteria) and bool(evidence_requirement),
                "VFY_METHOD_NOT_READY",
                "Method requires pass criteria and Evidence requirement",
                details={"method_id": method_id},
            )
            require(
                bool(executor_identity),
                "VFY_METHOD_NOT_READY",
                "Method requires a stable executor identity",
                details={"method_id": method_id},
            )
        else:
            procedure = dict(procedure or {})

        procedure = dict(procedure or {})
        if "path" in procedure:
            procedure["path"] = safe_project_path(str(procedure["path"]))
        if procedure.get("kind") == "command":
            argv = procedure.get("argv")
            require(
                isinstance(argv, list)
                and bool(argv)
                and all(isinstance(item, str) and item for item in argv),
                "VFY_METHOD_NOT_READY",
                "Command procedure requires a non-empty argument vector",
                details={"method_id": method_id},
            )
            require(
                procedure.get("policy") == _COMMAND_POLICY
                and procedure.get("workspace") == "isolated-copy"
                and procedure.get("network") == "disabled",
                "VFY_METHOD_NOT_READY",
                "Command procedure requires deterministic-test-v1, isolated-copy and disabled network",
                details={"method_id": method_id},
            )
            timeout = procedure.get("timeout_seconds", 120)
            max_output = procedure.get("max_output_bytes", 262144)
            require(
                isinstance(timeout, int) and 1 <= timeout <= 300,
                "VFY_METHOD_NOT_READY",
                "Command timeout must be between 1 and 300 seconds",
                details={"method_id": method_id},
            )
            require(
                isinstance(max_output, int) and 1024 <= max_output <= 1048576,
                "VFY_METHOD_NOT_READY",
                "Command output budget must be between 1 KiB and 1 MiB",
                details={"method_id": method_id},
            )
            procedure["timeout_seconds"] = timeout
            procedure["max_output_bytes"] = max_output
            if "cwd" in procedure:
                procedure["cwd"] = safe_project_path(str(procedure["cwd"]))

        output.append(
            {
                "id": method_id,
                "title": str(raw.get("title", method_id)).strip(),
                "purpose": purpose,
                "target_references": list(target_refs),
                "subject_references": list(method_subjects),
                "obligation_references": list(obligations),
                "method_type": method_type,
                "disposition": disposition,
                "execution_mode": mode,
                "executor_identity": executor_identity,
                "environment": dict(environment),
                "procedure": procedure,
                "pass_criteria": pass_criteria,
                "evidence_requirement": evidence_requirement,
                "exception_reference": exception_reference,
                "n_a_basis": n_a_basis,
            }
        )

    validate_method_coverage(output, targets, candidate)
    return tuple(output)


def validate_method_coverage(
    methods: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    targets: tuple[Mapping[str, Any], ...],
    candidate: Mapping[str, Any],
) -> None:
    target_coverage: dict[str, list[Mapping[str, Any]]] = {
        str(target["reference"]): [] for target in targets
    }
    covered_obligations: set[str] = set()
    for method in methods:
        for target_ref in method["target_references"]:
            target_coverage[target_ref].append(method)
        covered_obligations.update(method["obligation_references"])
    require(
        all(target_coverage.values()),
        "VFY_METHOD_COVERAGE_INCOMPLETE",
        "Every authoritative Target must be covered by at least one Method",
        details={"missing": [key for key, value in target_coverage.items() if not value]},
    )
    for target in targets:
        related = target_coverage[str(target["reference"])]
        mapped = {reference for method in related for reference in method["obligation_references"]}
        require(set(target.get("obligation_references", [])) <= mapped,
                "VFY_METHOD_COVERAGE_INCOMPLETE",
                "Target obligations must be covered by Methods of that exact Target")
        if target["purpose"] != "both":
            continue
        related = target_coverage[str(target["reference"])]
        purposes = {str(item["purpose"]) for item in related}
        require(
            "both" in purposes or {"verification", "validation"} <= purposes,
            "VFY_PURPOSE_MISMATCH",
            "A both Target requires proof for verification and validation dimensions",
            details={"target": target["reference"]},
        )
    for method in methods:
        allowed_vfp = {ref for target in targets
                       if target["reference"] in method["target_references"]
                       for ref in target.get("obligation_references", []) if "#VFP-" in ref}
        require({ref for ref in method["obligation_references"] if "#VFP-" in ref} <= allowed_vfp,
                "VFY_METHOD_COVERAGE_INCOMPLETE",
                "Method VFP references exceed its Target VFO mapping")

    required_obligations = set(
        stable_unique(candidate.get("required_obligation_references", []), field="obligation")
    )
    require(
        required_obligations <= covered_obligations,
        "VFY_METHOD_COVERAGE_INCOMPLETE",
        "One or more upstream VFY obligations are not mapped to a Method",
        details={"missing": sorted(required_obligations - covered_obligations)},
    )
