"""Immutable Evidence and VFY Method Result helpers."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from packages.sdlc_runtime.authority import IDENTITY_TOKEN_RE, is_rfc3339

from vfy_common import (
    DIGEST_RE,
    RESULTS,
    canonical_bytes,
    reject_secrets,
    require,
    sha256_bytes,
    utc_now,
)


def _source_evidence(value: Mapping[str, Any] | None) -> dict[str, str] | None:
    if value is None:
        return None
    require(
        isinstance(value, Mapping)
        and set(value) == {"reference", "sha256"}
        and isinstance(value.get("reference"), str)
        and bool(str(value["reference"]).strip())
        and DIGEST_RE.fullmatch(str(value.get("sha256", ""))) is not None,
        "VFY_EVIDENCE_INSUFFICIENT",
        "Manual/hybrid Evidence source requires exact reference and SHA-256 digest",
    )
    return {"reference": str(value["reference"]), "sha256": str(value["sha256"])}


def build_evidence(
    *,
    evidence_id: str,
    method: Mapping[str, Any],
    result: str,
    observed: Any,
    actual_subject_references: list[str] | tuple[str, ...],
    environment: Mapping[str, Any] | None = None,
    executor_identity: str | None = None,
    observed_at: str | None = None,
    source_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    require(
        result in {"pass", "fail"},
        "VFY_EVIDENCE_INSUFFICIENT",
        "Only an observed pass or fail can create execution Evidence",
    )
    require(
        isinstance(observed, (str, dict, list)) and bool(observed),
        "VFY_EVIDENCE_INSUFFICIENT",
        "Observed facts are required",
        details={"method_id": method.get("id")},
    )
    executor = executor_identity or str(method["executor_identity"])
    timestamp = observed_at or utc_now()
    require(
        IDENTITY_TOKEN_RE.fullmatch(executor) is not None,
        "VFY_EVIDENCE_INSUFFICIENT",
        "Evidence Executor identity is invalid",
        details={"method_id": method.get("id")},
    )
    require(
        is_rfc3339(timestamp),
        "VFY_EVIDENCE_INSUFFICIENT",
        "Evidence observation time must be RFC 3339",
        details={"method_id": method.get("id")},
    )
    actual_subjects = list(actual_subject_references)
    require(
        actual_subjects == list(method["subject_references"]),
        "VFY_SUBJECT_NOT_CURRENT",
        "Evidence Subject differs from the frozen Method Contract",
        details={"method_id": method.get("id")},
    )
    evidence = {
        "id": evidence_id,
        "method_id": method["id"],
        "target_references": list(method["target_references"]),
        "subject_references": actual_subjects,
        "result": result,
        "observed": deepcopy(observed),
        "environment": deepcopy(dict(environment or method.get("environment") or {})),
        "executor_identity": executor,
        "observed_at": timestamp,
        "evidence_requirement": method["evidence_requirement"],
        "source_evidence": _source_evidence(source_evidence),
    }
    require(
        bool(evidence["environment"]),
        "VFY_EVIDENCE_INSUFFICIENT",
        "Evidence requires the frozen Method environment/data contract",
        details={"method_id": method.get("id")},
    )
    reject_secrets(evidence)
    evidence["sha256"] = sha256_bytes(canonical_bytes(evidence))
    evidence["reference"] = f"{evidence_id}@{evidence['sha256']}"
    return evidence


def verify_evidence(
    evidence: Mapping[str, Any],
    method: Mapping[str, Any] | None = None,
) -> None:
    require(
        isinstance(evidence, Mapping),
        "VFY_EVIDENCE_INSUFFICIENT",
        "Evidence must be an object",
    )
    required = {
        "id",
        "method_id",
        "target_references",
        "subject_references",
        "result",
        "observed",
        "environment",
        "executor_identity",
        "observed_at",
        "evidence_requirement",
        "source_evidence",
        "sha256",
        "reference",
    }
    require(
        set(evidence) == required,
        "VFY_EVIDENCE_INSUFFICIENT",
        "Evidence fields are incomplete or contain extras",
        details={"missing": sorted(required - set(evidence)), "extra": sorted(set(evidence) - required)},
    )
    require(
        isinstance(evidence["id"], str)
        and bool(evidence["id"].strip())
        and isinstance(evidence["method_id"], str)
        and bool(evidence["method_id"].strip())
        and isinstance(evidence["target_references"], list)
        and bool(evidence["target_references"])
        and isinstance(evidence["subject_references"], list)
        and bool(evidence["subject_references"])
        and evidence["result"] in {"pass", "fail"}
        and isinstance(evidence["observed"], (str, dict, list))
        and bool(evidence["observed"])
        and isinstance(evidence["environment"], Mapping)
        and bool(evidence["environment"])
        and IDENTITY_TOKEN_RE.fullmatch(str(evidence["executor_identity"])) is not None
        and is_rfc3339(str(evidence["observed_at"]))
        and isinstance(evidence["evidence_requirement"], str)
        and bool(evidence["evidence_requirement"].strip()),
        "VFY_EVIDENCE_INSUFFICIENT",
        "Evidence requires Method, Target, Subject, result, observation, environment, executor, time and requirement metadata",
    )
    if evidence["source_evidence"] is not None:
        _source_evidence(evidence["source_evidence"])
    clone = dict(evidence)
    digest = clone.pop("sha256")
    reference = clone.pop("reference")
    expected = sha256_bytes(canonical_bytes(clone))
    require(
        digest == expected and reference == f"{clone['id']}@{expected}",
        "VFY_EVIDENCE_INSUFFICIENT",
        "Evidence digest or immutable reference does not match canonical bytes",
        details={"evidence_id": clone.get("id")},
    )
    if method is not None:
        require(
            evidence["method_id"] == method["id"]
            and list(evidence["target_references"]) == list(method["target_references"])
            and list(evidence["subject_references"]) == list(method["subject_references"])
            and evidence["executor_identity"] == method["executor_identity"]
            and evidence["evidence_requirement"] == method["evidence_requirement"]
            and dict(evidence["environment"]) == dict(method.get("environment") or evidence["environment"]),
            "VFY_EVIDENCE_INSUFFICIENT",
            "Evidence differs from its frozen Method Contract",
            details={"method_id": method.get("id")},
        )
        if method["execution_mode"] in {"manual", "hybrid"}:
            require(
                evidence["source_evidence"] is not None,
                "VFY_EVIDENCE_INSUFFICIENT",
                "Manual/hybrid Evidence requires an immutable source attachment/reference",
                details={"method_id": method["id"]},
            )
    reject_secrets(evidence)


def pending_result(method: Mapping[str, Any]) -> dict[str, Any]:
    disposition = str(method["disposition"])
    if disposition == "n/a":
        return {
            "method_id": method["id"],
            "result": "n/a",
            "actual_result": str(method.get("n_a_basis") or "authoritatively not applicable"),
            "actual_subject_references": list(method["subject_references"]),
            "evidence_references": [],
            "return_references": [],
        }
    if disposition == "waived":
        return {
            "method_id": method["id"],
            "result": "waived",
            "actual_result": "Execution waived by the exact active Exception",
            "actual_subject_references": list(method["subject_references"]),
            "evidence_references": [str(method["exception_reference"])],
            "return_references": [],
        }
    return {
        "method_id": method["id"],
        "result": "pending",
        "actual_result": "Not executed",
        "actual_subject_references": list(method["subject_references"]),
        "evidence_references": [],
        "return_references": [],
    }


def record_result(
    method: Mapping[str, Any],
    *,
    result: str,
    actual_result: str,
    evidence_references: list[str] | tuple[str, ...],
    actual_subject_references: list[str] | tuple[str, ...] | None = None,
    return_references: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    require(
        result in RESULTS,
        "VFY_METHOD_EXECUTION_FAILED",
        "Method Result value is invalid",
        details={"method_id": method.get("id")},
    )
    actual_subjects = list(actual_subject_references or method["subject_references"])
    require(
        actual_subjects == list(method["subject_references"]),
        "VFY_SUBJECT_NOT_CURRENT",
        "Actual Method Subject differs from the frozen Method Contract",
        details={"method_id": method.get("id")},
    )
    if result in {"pass", "fail"}:
        require(
            bool(actual_result.strip()) and bool(evidence_references),
            "VFY_EVIDENCE_INSUFFICIENT",
            "Observed pass/fail requires actual facts and immutable Evidence",
            details={"method_id": method.get("id")},
        )
    return {
        "method_id": method["id"],
        "result": result,
        "actual_result": actual_result,
        "actual_subject_references": actual_subjects,
        "evidence_references": list(evidence_references),
        "return_references": list(return_references),
    }


def method_result_index(rows: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        method_id = str(row.get("method_id", ""))
        require(
            method_id and method_id not in output,
            "VFY_CONCLUSION_INCONSISTENT",
            "Each Method must have exactly one Current Result",
            details={"method_id": method_id},
        )
        output[method_id] = row
    return output
