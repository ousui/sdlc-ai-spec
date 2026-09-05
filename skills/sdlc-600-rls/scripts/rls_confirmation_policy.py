"""Bounded RCF predicates. Unknown prose is not an executable PASS criterion."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re
from typing import Any

from rls_common import assert_no_secret, canonical_json, exact_reference, exact_scope_reference, require, sha256_value
from rls_contract import confirmation_contract

POLICY = "sdlc-ai-spec/rls-confirmation-policy/v1"
VERSION_CONTRACT = {
    "confirmation": "Observe the authorized local Sandbox release",
    "expected": "The target version equals the bound release reference",
    "evidence_requirement": "Immutable target-side snapshot after the selected RLI",
}
STATE_CONFIRMATION = "Compare the declared Sandbox state fields"
STATE_EVIDENCE = "Immutable target-side snapshot and per-field equality results"
STATE_EXPECTATION = "sdlc-ai-spec/sandbox-state-expectation/v1"
CAPABILITY_ERROR = "RLS_CONFIRMATION_CAPABILITY_UNAVAILABLE"


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, CAPABILITY_ERROR, "duplicate predicate field")
        result[key] = value
    return result


def contract_digest(row: dict) -> str:
    return "sha256:" + sha256_value(confirmation_contract(row))


def compile_confirmation(row: dict, release_reference: str) -> dict:
    """Exact, documented grammars only; never infer predicates from keywords."""
    assert_no_secret(row)
    for field in ("confirmation", "expected", "evidence_requirement", "executor"):
        require(isinstance(row.get(field), str) and 0 < len(row[field]) <= 8192,
                CAPABILITY_ERROR, "RCF has no complete supported observation contract")
    require(type(row.get("subjective", False)) is bool, CAPABILITY_ERROR, "subjective must be boolean")
    if row.get("subjective", False):
        require(isinstance(row.get("scenario"), str) and 0 < len(row["scenario"]) <= 1024,
                "RLS_TARGET_STATE_UNVERIFIED", "human RCF requires an immutable scenario before execution")
        age = row.get("max_observation_age_seconds", 900)
        require(type(age) is int and 1 <= age <= 3600, CAPABILITY_ERROR, "invalid human observation age bound")
        return {"kind": "human", "max_age_seconds": age}
    if all(row[field] == value for field, value in VERSION_CONTRACT.items()):
        return {"kind": "sandbox_state_equals", "equals": {"version": release_reference}}
    require(row["confirmation"] == STATE_CONFIRMATION and row["evidence_requirement"] == STATE_EVIDENCE,
            CAPABILITY_ERROR, "unsupported RCF; preserve Expected and supply a supported observation contract")
    try:
        expected = json.loads(row["expected"], object_pairs_hook=_object,
                              parse_constant=lambda _: require(False, CAPABILITY_ERROR, "non-finite JSON is forbidden"))
    except (ValueError, TypeError, RecursionError):
        require(False, CAPABILITY_ERROR, "Expected must be the declared bounded JSON predicate")
    require(isinstance(expected, dict) and set(expected) == {"contract", "equals"}
            and expected["contract"] == STATE_EXPECTATION, CAPABILITY_ERROR, "unknown Expected grammar")
    fields = expected["equals"]
    require(isinstance(fields, dict) and 1 <= len(fields) <= 16, CAPABILITY_ERROR, "Expected must bind 1..16 fields")
    for key, value in fields.items():
        require(isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key) is not None,
                CAPABILITY_ERROR, "only literal top-level Sandbox fields are supported")
        require(value is None or type(value) in {bool, int, float, str}, CAPABILITY_ERROR, "Expected values must be JSON scalars")
        require(not isinstance(value, str) or len(value) <= 4096, CAPABILITY_ERROR, "Expected value exceeds its bound")
        require(not isinstance(value, float) or math.isfinite(value), CAPABILITY_ERROR, "non-finite Expected")
    return {"kind": "sandbox_state_equals", "equals": deepcopy(fields)}


def observation_binding(artifact: dict, row: dict, snapshot: dict) -> dict:
    """Bind current authoritative objects, not the caller's description of them."""
    contract = artifact["release_contract"]
    exact_reference(artifact["artifact"]["reference"], "RLS")
    exact_reference(row["id"], "RCF")
    exact_scope_reference(contract["scope_reference"])
    require(isinstance(snapshot, dict) and snapshot.get("target") == contract["release_target"],
            "RLS_TARGET_STATE_UNVERIFIED", "observed target identity differs")
    return {
        "rls_reference": artifact["artifact"]["reference"], "rcf_id": row["id"],
        "release_reference": contract["release_reference"], "scope_reference": contract["scope_reference"],
        "result_references": list(contract["result_references"]), "vfy_reference": contract["vfy_reference"],
        "vfy_source_digest": contract["vfy_source_digest"], "vfy_candidate_digest": contract["vfy_candidate_digest"],
        "release_target": contract["release_target"], "target_locator": contract.get("target_locator"),
        "release_contract_digest": "sha256:" + sha256_value(contract),
        "rcf_contract_digest": contract_digest(row), "scenario": row.get("scenario"),
        "executor": row["executor"], "target_snapshot_digest": "sha256:" + sha256_value(snapshot),
    }


def evaluate_automatic(row: dict, release_reference: str, snapshot: dict, *, force_fail: bool = False) -> dict:
    plan = compile_confirmation(row, release_reference)
    require(plan["kind"] != "human", CAPABILITY_ERROR, "human RCF is not an automated version check")
    require(type(force_fail) is bool, CAPABILITY_ERROR, "fault injection must be boolean")
    checks = []
    for field, expected in sorted(plan["equals"].items()):
        present = field in snapshot
        actual = snapshot.get(field)
        # JSON equality is type-sensitive: True is not the integer 1.
        matched = present and canonical_json(actual) == canonical_json(expected)
        checks.append({"field": field, "present": present, "expected": expected,
                       "actual": actual, "matched": matched})
    return {"policy": POLICY, "kind": plan["kind"], "rcf_contract_digest": contract_digest(row),
            "checks": checks, "fault_injected": force_fail,
            "result": "pass" if all(item["matched"] for item in checks) and not force_fail else "fail"}


def human_evaluation(row: dict, record: dict) -> dict:
    return {"policy": POLICY, "kind": "human", "rcf_contract_digest": contract_digest(row),
            "observation_id": record["observation_id"], "source_digest": record["source_digest"],
            "result": record["result"], "fault_injected": False}


def verify_confirmation_event(artifact: dict, row: dict, event: dict) -> None:
    """Recompute persisted outcomes; valid hashes do not make an invalid PASS true."""
    contract = artifact["release_contract"]
    snapshot = event.get("observed")
    require(isinstance(snapshot, dict) and row.get("observed") == snapshot,
            "RLS_EVIDENCE_TAMPERED", "RCF Observed differs from its Evidence")
    binding = observation_binding(artifact, row, snapshot)
    require(event.get("confirmation_binding") == binding and event.get("item") == row["id"]
            and event.get("artifact_reference") == binding["rls_reference"]
            and event.get("release_reference") == binding["release_reference"]
            and event.get("target") == binding["release_target"] and event.get("executor") == row["executor"],
            "RLS_EVIDENCE_TAMPERED", "confirmation Evidence is not bound to the current immutable RCF")
    plan = compile_confirmation(row, contract["release_reference"])
    if plan["kind"] == "human":
        from rls_human_evidence import validate_record
        record = event.get("human_evidence")
        validate_record(record, binding, max_age_seconds=plan["max_age_seconds"], at=event["observed_at"])
        expected = human_evaluation(row, record)
    else:
        require(event.get("human_evidence") is None, "RLS_EVIDENCE_TAMPERED", "automated RCF has ambiguous human Evidence")
        evaluation = event.get("confirmation_evaluation") or {}
        expected = evaluate_automatic(row, contract["release_reference"], snapshot,
                                      force_fail=evaluation.get("fault_injected", False))
    require(event.get("confirmation_evaluation") == expected and event.get("result") == expected["result"]
            and row.get("result") == expected["result"],
            "RLS_EVIDENCE_TAMPERED", "RCF result is inconsistent with its actual observation and Expected")
