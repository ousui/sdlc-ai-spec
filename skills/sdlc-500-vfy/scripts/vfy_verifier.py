"""Pure, fail-closed VFY integrity, recovery and Gate verifier."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from vfy_builder import (
    STATE_CONTRACT,
    confirmation_subject_digest,
    state_contract_digest,
)
from vfy_common import reject_secrets, require, sha256_value
from vfy_conclusions import (
    aggregate_fixed_conclusions,
    aggregate_target_conclusions,
    product_result,
)
from vfy_exceptions import (
    active_failure_exception,
    validate_exception_bindings,
)
from vfy_methods import validate_method_coverage
from vfy_results import method_result_index, verify_evidence
from vfy_returns import (
    derive_control_resolutions,
    unresolved_returns,
    validate_failed_results_have_returns,
    validate_returns,
)
from vfy_scope import validate_scope_subject_coverage
from vfy_subject import assert_subjects_still_current, subject_set_digest


def _evidence_index(
    state: Mapping[str, Any], methods: Mapping[str, Mapping[str, Any]]
) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for item in state.get("evidence", []):
        method_id = str(item.get("method_id", ""))
        require(
            method_id in methods,
            "VFY_EVIDENCE_INSUFFICIENT",
            "Evidence references an unknown Method",
            details={"method_id": method_id},
        )
        verify_evidence(item, methods[method_id])
        reference = str(item["reference"])
        require(
            reference not in output,
            "VFY_EVIDENCE_INSUFFICIENT",
            "Evidence reference is duplicated",
            details={"reference": reference},
        )
        output[reference] = item
    return output


def _verify_results(
    state: Mapping[str, Any],
    methods: Mapping[str, Mapping[str, Any]],
    evidence: Mapping[str, Mapping[str, Any]],
) -> None:
    results = method_result_index(list(state["method_results"]))
    require(
        set(results) == set(methods),
        "VFY_CONCLUSION_INCONSISTENT",
        "Method Result Set must exactly match the Method Contract Set",
        details={
            "missing": sorted(set(methods) - set(results)),
            "extra": sorted(set(results) - set(methods)),
        },
    )
    for method_id, result in results.items():
        method = methods[method_id]
        require(
            list(result["actual_subject_references"])
            == list(method["subject_references"]),
            "VFY_SUBJECT_NOT_CURRENT",
            "Method Result Subject differs from the frozen Method Contract",
            details={"method_id": method_id},
        )
        value = str(result["result"])
        disposition = str(method["disposition"])
        if value in {"pass", "fail"}:
            refs = list(result.get("evidence_references", []))
            require(
                bool(refs) and all(reference in evidence for reference in refs),
                "VFY_EVIDENCE_INSUFFICIENT",
                "Observed Method Result lacks resolvable immutable Evidence",
                details={"method_id": method_id},
            )
            for reference in refs:
                item = evidence[reference]
                require(
                    item["method_id"] == method_id
                    and item["result"] == value
                    and list(item["target_references"])
                    == list(method["target_references"])
                    and list(item["subject_references"])
                    == list(method["subject_references"])
                    and item["executor_identity"] == method["executor_identity"]
                    and item["evidence_requirement"] == method["evidence_requirement"],
                    "VFY_EVIDENCE_INSUFFICIENT",
                    "Evidence Result, Method, Target, Subject, executor or requirement binding is inconsistent",
                    details={"method_id": method_id, "evidence": reference},
                )
        elif value == "n/a":
            require(
                disposition == "n/a" and bool(method.get("n_a_basis")),
                "VFY_EVIDENCE_INSUFFICIENT",
                "n/a Result must inherit an authoritative n/a Method basis",
                details={"method_id": method_id},
            )
        elif value == "waived":
            require(
                disposition == "waived" and bool(method.get("exception_reference")),
                "VFY_EVIDENCE_INSUFFICIENT",
                "waived Result requires the Method's current active Exception",
                details={"method_id": method_id},
            )
        else:
            require(
                value == "pending" and disposition in {"required", "embedded"},
                "VFY_CONCLUSION_INCONSISTENT",
                "Pending Result is incompatible with Method Disposition",
                details={"method_id": method_id},
            )


def _verify_early_stop(state: Mapping[str, Any]) -> None:
    results = list(state["method_results"])
    if not state.get("early_stop"):
        return
    failed = [item for item in results if item["result"] == "fail"]
    pending = [item for item in results if item["result"] == "pending"]
    require(
        bool(failed),
        "VFY_EARLY_STOP_INVALID",
        "Failure-checkpoint early stop requires at least one confirmed fail",
    )
    basis = state.get("early_stop_basis")
    require(
        isinstance(basis, Mapping)
        and bool(basis.get("failure_method_references"))
        and bool(basis.get("return_references"))
        and basis.get("pending_facts_cannot_change_failure_or_attribution") is True,
        "VFY_EARLY_STOP_INVALID",
        "Early-stop basis must prove failure validity and Return attribution",
    )
    expected_returns = set(str(item) for item in basis["return_references"])
    require(
        set(str(item["method_id"]) for item in failed)
        >= set(str(item) for item in basis["failure_method_references"]),
        "VFY_EARLY_STOP_INVALID",
        "Early-stop failure Method set is not present in confirmed failures",
    )
    for item in pending:
        require(
            expected_returns <= set(item.get("return_references", [])),
            "VFY_EARLY_STOP_INVALID",
            "Every pending Method must identify the fail/Return that stopped execution",
            details={"method_id": item["method_id"]},
        )
    require(
        not any(
            item.get("affects_failure_validity_or_attribution")
            for item in state.get("open_items", [])
        ),
        "VFY_EARLY_STOP_INVALID",
        "An open fact can still change failure validity or Return attribution",
    )


def _expected_projection(state: Mapping[str, Any]) -> dict[str, Any]:
    targets = tuple(state["targets"])
    methods = tuple(state["methods"])
    target_conclusions = aggregate_target_conclusions(
        targets, methods, list(state["method_results"])
    )
    fixed = aggregate_fixed_conclusions(targets, target_conclusions)
    return {
        "target_conclusions": target_conclusions,
        "fixed_conclusions": fixed,
        "product_result": product_result(fixed),
    }


def verify_state(
    state: Mapping[str, Any],
    *,
    finalizing: bool = False,
    current_subject_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify without mutating state and return the recomputed Gate projection."""

    require(
        state.get("contract") == STATE_CONTRACT,
        "VFY_CONTRACT_INVALID",
        "Unsupported stored VFY state contract",
    )
    reject_secrets(state)
    require(
        state["subject_set_digest"] == subject_set_digest(tuple(state["subjects"])),
        "VFY_SUBJECT_NOT_CURRENT",
        "Subject Set Digest does not match the canonical Subject Set",
    )
    require(
        state["pre_execution_contract_digest"] == state_contract_digest(state),
        "VFY_FINAL_CONFIRMATION_STALE",
        "Pre-execution Contract changed after it was frozen",
    )
    validate_scope_subject_coverage(state["scope"], tuple(state["subjects"]))
    assert_subjects_still_current(tuple(state["subjects"]), current_subject_snapshot)
    methods = {str(item["id"]): item for item in state["methods"]}
    validate_method_coverage(
        tuple(state["methods"]),
        tuple(state["targets"]),
        {
            "required_obligation_references": list(
                dict.fromkeys(
                    reference
                    for method in state["methods"]
                    for reference in method["obligation_references"]
                )
            )
        },
    )
    validate_exception_bindings(
        tuple(state["methods"]),
        tuple(state.get("exceptions", [])),
        rls_applicability=str(state["rls_applicability"]),
        scope_tokens=tuple(state["scope"]["delivery_scope"]),
    )
    evidence = _evidence_index(state, methods)
    _verify_results(state, methods, evidence)
    _verify_early_stop(state)
    validate_returns(state)

    failure_exception = active_failure_exception(state.get("exceptions", []))
    accepted_failure_methods = (
        {
            str(item["method_id"])
            for item in state["method_results"]
            if item["result"] == "fail"
        }
        if failure_exception is not None
        else set()
    )
    validate_failed_results_have_returns(
        state["method_results"],
        state["returns"],
        accepted_failure_methods=accepted_failure_methods,
    )

    expected = _expected_projection(state)
    require(
        list(state["target_conclusions"]) == expected["target_conclusions"]
        and list(state["fixed_conclusions"]) == expected["fixed_conclusions"]
        and state["product_result"] == expected["product_result"],
        "VFY_CONCLUSION_INCONSISTENT",
        "Stored Target or fixed Conclusion differs from deterministic aggregation",
    )
    unresolved = unresolved_returns(list(state["returns"]))
    control_refs = tuple(str(item) for item in state.get("control_inputs", []))
    control_set = set(control_refs)
    resolutions: list[dict[str, Any]] = []
    if control_set:
        resolutions = derive_control_resolutions(state)
    unresolved_controls = tuple(
        sorted(
            control_set
            - {str(item["control_reference"]) for item in resolutions}
        )
    )

    failed_methods = [item for item in state["method_results"] if item["result"] == "fail"]
    if failed_methods and failure_exception is None:
        require(
            bool(state["returns"]),
            "VFY_RETURN_INVALID",
            "Confirmed product failure requires exact upstream Returns or a scoped active Exception",
        )

    pending = [
        item["method_id"]
        for item in state["method_results"]
        if item["result"] == "pending"
    ]
    if finalizing:
        require(
            not pending or state.get("early_stop") is True,
            "VFY_CONCLUSION_INCONSISTENT",
            "Normal finalization cannot retain pending Method Results",
            details={"pending": pending},
        )
        require(
            not unresolved_controls,
            "VFY_CONTROL_INVALID",
            "Final VFY Revision cannot leave a Control Input unresolved",
            details={"unresolved_controls": list(unresolved_controls)},
        )
        require(
            state.get("final_confirmation") is not None,
            "VFY_FINAL_CONFIRMATION_STALE",
            "Fresh Final Confirmation is required",
        )
        confirmation = state["final_confirmation"]
        expected_exceptions = [
            f"{state['artifact']['reference']}#{item['id']}"
            for item in state.get("exceptions", [])
            if item.get("state") in {"active", "carried"}
        ]
        require(
            isinstance(confirmation, Mapping)
            and confirmation.get("subject_digest") == confirmation_subject_digest(state)
            and confirmation.get("contract_digest") == state["pre_execution_contract_digest"]
            and confirmation.get("subject_set_digest") == state["subject_set_digest"]
            and confirmation.get("product_result") == state["product_result"]
            and confirmation.get("method_result_digest") == sha256_value(state["method_results"])
            and confirmation.get("return_digest") == sha256_value(state["returns"]),
            "VFY_FINAL_CONFIRMATION_STALE",
            "Final Confirmation does not bind Contract, Subject, Result, Return and product boundary",
        )
        require(
            confirmation.get("accepted_exception_references") == expected_exceptions
            and (
                confirmation.get("mode") != "delegated"
                or not expected_exceptions
            ),
            "VFY_FINAL_CONFIRMATION_STALE",
            "Final Confirmation does not bind the exact current Exception Reference Set",
        )

    gate_checks = [
        {"id": "VFY-G-001", "result": "pass", "note": "Scope and current terminal Subject Set are exact."},
        {"id": "VFY-G-002", "result": "pass", "note": "Authoritative Target Set is complete."},
        {"id": "VFY-G-003", "result": "pass", "note": "Method Purpose, obligations and frozen contract are complete."},
        {"id": "VFY-G-004", "result": "pass", "note": "Method Results bind actual Subjects and immutable Evidence."},
        {"id": "VFY-G-005", "result": "pass", "note": "Target, CON-VER and CON-VAL aggregation is deterministic."},
        {"id": "VFY-G-006", "result": "pass", "note": "Returns and Control recovery preserve owning authority."},
        {"id": "VFY-G-007", "result": "pass", "note": "Evidence and Exception closure are valid."},
        {"id": "VFY-G-008", "result": "pass", "note": "Product result and downstream applicability remain distinct."},
    ]
    has_exception = bool(state.get("exceptions"))
    artifact_gate = (
        ("pass_with_exception" if has_exception else "pass")
        if finalizing
        else ("pending" if pending or unresolved_controls else "pass")
    )
    product_downstream_eligible = state["product_result"] in {"pass", "waived", "n/a"} or (
        state["product_result"] == "fail" and failure_exception is not None
    )
    rls_ready = (
        artifact_gate in {"pass", "pass_with_exception"}
        and finalizing
        and not state.get("early_stop")
        and not unresolved
        and not unresolved_controls
        and not pending
        and product_downstream_eligible
        and state["rls_applicability"] == "required"
    )
    if state.get("early_stop"):
        next_action = "RETURN_UPSTREAM"
    elif unresolved or state["product_result"] == "fail" and failure_exception is None:
        phases = [
            item["return_phase"]
            for item in state["returns"]
            if item["status"] != "resolved"
        ]
        next_action = "RETURN_TO_" + (phases[0] if phases else "UPSTREAM")
    elif unresolved_controls:
        next_action = "RESOLVE_CONTROL_INPUT"
    elif pending:
        next_action = "RUN_PENDING_METHOD"
    elif state["rls_applicability"] == "required" and rls_ready:
        next_action = "ENTER_RLS"
    elif state["rls_applicability"] in {"n/a", "waived"} and product_downstream_eligible:
        next_action = "LIFECYCLE_COMPLETE"
    else:
        next_action = "RESOLVE_RLS_APPLICABILITY"

    return {
        "ok": True,
        "artifact_reference": state["artifact"]["reference"],
        "artifact_gate": artifact_gate,
        "gate_checks": gate_checks,
        "product_result": state["product_result"],
        "pending_methods": pending,
        "unresolved_returns": list(unresolved),
        "unresolved_controls": list(unresolved_controls),
        "control_resolutions": resolutions,
        "early_stop": bool(state.get("early_stop")),
        "rls_ready": rls_ready,
        "next_action": next_action,
        "verification_digest": sha256_value(
            {
                "contract": state["pre_execution_contract_digest"],
                "subjects": state["subject_set_digest"],
                "methods": state["method_results"],
                "targets": expected["target_conclusions"],
                "fixed": expected["fixed_conclusions"],
                "returns": state["returns"],
                "controls": resolutions,
                "exceptions": state.get("exceptions", []),
                "gate_checks": gate_checks,
            }
        ),
    }


def apply_projection(
    state: Mapping[str, Any], projection: Mapping[str, Any], *, freeze: bool
) -> dict[str, Any]:
    """Return a new state with a verified projection; never mutate caller bytes."""

    output = deepcopy(dict(state))
    output["artifact_gate"] = projection["artifact_gate"]
    output["gate_checks"] = deepcopy(list(projection["gate_checks"]))
    output["control_resolutions"] = deepcopy(list(projection.get("control_resolutions", [])))
    output["rls_ready"] = bool(projection["rls_ready"])
    output["next_action"] = str(projection["next_action"])
    if freeze:
        output["artifact"]["revision_state"] = "frozen"
        output["artifact"]["artifact_status"] = (
            "ready_with_exception" if output.get("exceptions") else "ready"
        )
    elif projection["pending_methods"] or projection.get("unresolved_controls"):
        output["artifact"]["artifact_status"] = "waiting_input"
    else:
        output["artifact"]["artifact_status"] = "draft"
    return output
