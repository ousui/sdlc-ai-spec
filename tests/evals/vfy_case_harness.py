"""Executable Oracle for VFY-E001..VFY-E080.

Each Case invokes a distinct behavior or invariant. A Case passes only when its
expected positive result or exact fail-closed error is observed.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Callable
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "sdlc-500-vfy" / "scripts"
for entry in (ROOT, SCRIPTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

_RUNTIME_SPEC = importlib.util.spec_from_file_location(
    "vfy_case_runtime", SCRIPTS / "runtime.py"
)
if _RUNTIME_SPEC is None or _RUNTIME_SPEC.loader is None:
    raise RuntimeError("cannot load VFY Runtime for the Case Oracle")
_RUNTIME = importlib.util.module_from_spec(_RUNTIME_SPEC)
_RUNTIME_SPEC.loader.exec_module(_RUNTIME)

from tests.skill_vfy.support import (  # noqa: E402
    CTX,
    IMP,
    PLN,
    RESULT_DIGEST,
    SUBJECT,
    VFO_VAL,
    VFO_VER,
    VFP_VAL,
    VFP_VER,
    WI,
    delegated_confirmation,
    fixture_subject_snapshot,
    open_state,
    passing_state,
    persistent_authority_candidate,
    prepare_workspace,
    valid_candidate,
)
from packages.sdlc_lifecycle.query_vfy import project_vfy_state  # noqa: E402
from vfy_builder import build_state, normalize_candidate  # noqa: E402
from vfy_common import (  # noqa: E402
    VfyError,
    canonical_bytes,
    redact_text,
    sha256_bytes,
    sha256_value,
)
from vfy_conclusions import aggregate_values  # noqa: E402
from vfy_executor import execute_method  # noqa: E402
from vfy_handler import VfyHandler  # noqa: E402
import vfy_handler as handler_module  # noqa: E402
from vfy_methods import normalize_methods  # noqa: E402
from vfy_results import build_evidence, record_result, verify_evidence  # noqa: E402
from vfy_returns import normalize_returns  # noqa: E402
from vfy_scope import require_single_scope  # noqa: E402
from vfy_subject import assert_subjects_still_current, normalize_subjects  # noqa: E402
from vfy_targets import normalize_targets  # noqa: E402
from vfy_verifier import verify_state  # noqa: E402


@contextmanager
def workspace():
    with tempfile.TemporaryDirectory(prefix="vfy-case-") as directory:
        root = Path(directory)
        prepare_workspace(root)
        yield root


def expect_error(code: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except VfyError as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}: {exc}") from exc
        return {"error": exc.code, "message": str(exc)}
    raise AssertionError(f"expected {code}, operation succeeded")


def assert_true(value: Any, message: str) -> None:
    if not value:
        raise AssertionError(message)


def fallback_candidate() -> dict[str, Any]:
    candidate = valid_candidate()
    candidate["scope"] = {
        "reference": "DSN-20260904100500-01@1",
        "disposition": "n/a",
        "disposition_basis": "PLN is authoritatively not applicable for this complete Scope",
        "delivery_scope": ["resource:app"],
        "input_references": [CTX],
        "imp_work_items": [],
    }
    candidate["target_fallback_allowed"] = True
    candidate["targets"] = [
        {
            "reference": "REQ-20260904100200-01@1#AC-001",
            "purpose": "verification",
            "summary": "Acceptance criterion",
            "source_kind": "ac",
            "obligation_references": [],
        },
        {
            "reference": "REQ-20260904100200-01@1#GOAL-001",
            "purpose": "validation",
            "summary": "Intended outcome",
            "source_kind": "goal",
            "obligation_references": [],
        },
    ]
    candidate["methods"][0]["target_references"] = [candidate["targets"][0]["reference"]]
    candidate["methods"][0]["obligation_references"] = [candidate["targets"][0]["reference"]]
    candidate["methods"][1]["target_references"] = [candidate["targets"][1]["reference"]]
    candidate["methods"][1]["obligation_references"] = [candidate["targets"][1]["reference"]]
    candidate["required_obligation_references"] = [
        candidate["targets"][0]["reference"],
        candidate["targets"][1]["reference"],
    ]
    return candidate


def return_for(method_id: str, return_id: str = "RET-001", phase: str = "IMP") -> dict[str, Any]:
    value = {
        "id": return_id,
        "return_phase": phase,
        "target_references": [VFO_VER if method_id == "VFM-001" else VFO_VAL],
        "method_references": [method_id],
        "subject_references": [SUBJECT],
        "observed_gap": f"{method_id} observed the required product result is absent",
        "required_outcome": "Restore the declared Target outcome for the exact current Scope",
        "evidence_references": ["placeholder-overridden-by-handler"],
        "status": "open",
    }
    if phase == "IMP":
        value["imp_binding_reference"] = WI
        value["imp_binding_lineage"] = WI
    else:
        value["imp_binding_reference"] = "N/A"
        value["imp_binding_lineage"] = "N/A"
    return value


def failing_state(root: Path, *, early_stop: bool = False) -> dict[str, Any]:
    candidate = valid_candidate()
    state = build_state(candidate)
    (root / "README.md").unlink(missing_ok=True)
    handler = VfyHandler(root)
    methods = ["VFM-001"] if early_stop else ["VFM-001", "VFM-002"]
    returns = {"VFM-001": return_for("VFM-001", "RET-001")}
    if not early_stop:
        returns["VFM-002"] = return_for("VFM-002", "RET-002")
    early_basis = None
    if early_stop:
        early_basis = {
            "failure_method_references": ["VFM-001"],
            "return_references": [f"{state['artifact']['reference']}#RET-001"],
            "pending_facts_cannot_change_failure_or_attribution": True,
        }
    result = handler.run_state(
        state,
        method_ids=methods,
        allow_commands=False,
        failure_returns=returns,
        early_stop_basis=early_basis,
        finalize=False,
    )
    finalized = handler.run_state(
        result["state"],
        method_ids=[],
        allow_commands=False,
        finalize=True,
        confirmation=delegated_confirmation(root, result["state"]),
    )
    return finalized["state"]


def _case(case_id: str, root: Path) -> dict[str, Any]:
    number = int(case_id[-3:])

    if number == 1:
        result = VfyHandler(root).auto({"candidate": valid_candidate(), "persist": False})
        assert_true(result["state"]["artifact"]["reference"].startswith("VFY-"), "auto did not create VFY")
    elif number == 2:
        candidate = valid_candidate()
        candidate["scope_candidates"] = [candidate["scope"], deepcopy(candidate["scope"])]
        result = expect_error("VFY_SCOPE_AMBIGUOUS", lambda: build_state(candidate))
    elif number == 3:
        state = build_state(valid_candidate())
        assert_true(PLN in state["input_references"] and IMP in state["input_references"], "input classification incomplete")
        result = {"inputs": state["input_references"]}
    elif number == 4:
        state = open_state(root)
        result = VfyHandler(root).run_state(state, method_ids=["VFM-001"], allow_commands=False)
        values = {row["method_id"]: row["result"] for row in result["state"]["method_results"]}
        assert_true(values == {"VFM-001": "pass", "VFM-002": "pending"}, "run did not isolate selected Method")
    elif number == 5:
        old = passing_state(root)
        candidate = valid_candidate()
        candidate["subjects"][0]["result_digest"] = "sha256:" + "2" * 64
        result = VfyHandler(root).revise(old, candidate, persist=False)
        assert_true(result["status"] == "revised" and result["state"]["artifact"]["revision"] == 2, "revision missing")
    elif number == 6:
        state = passing_state(root)
        before = canonical_bytes(state)
        result = VfyHandler(root).check(state=state)
        assert_true(before == canonical_bytes(state), "check mutated bytes")
    elif number == 7:
        result, _ = _RUNTIME.run_cli(["--help"])
        assert_true(result["state"] == "meta" and result["effects"] == [], "meta command caused scan/effect")
    elif number == 8:
        state = open_state(root)
        result = expect_error(
            "VFY_METHOD_NOT_READY",
            lambda: VfyHandler(root).run_state(state, method_ids=["VFM-999"], allow_commands=False),
        )
    elif number == 9:
        state = open_state(root)
        result = VfyHandler(root).run_state(
            state,
            method_ids=["VFM-001", "VFM-001", "VFM-002"],
            allow_commands=False,
        )
        assert_true(result["executed_methods"] == ["VFM-001", "VFM-002"], "Method order/dedup failed")
    elif number == 10:
        scope = require_single_scope(valid_candidate())
        assert_true(scope["reference"] == PLN and len(scope["imp_work_items"]) == 1, "PLN Scope not complete")
        result = scope
    elif number == 11:
        state = build_state(fallback_candidate())
        assert_true(state["scope"]["phase"] == "DSN", "fallback Scope was not selected")
        result = state["scope"]
    elif number == 12:
        candidate = valid_candidate()
        candidate["scope_candidates"] = [candidate["scope"], {**candidate["scope"], "reference": "PLN-20260904101001-01@1"}]
        result = expect_error("VFY_SCOPE_AMBIGUOUS", lambda: normalize_candidate(candidate))
    elif number == 13:
        candidate = valid_candidate()
        candidate["subjects"][0]["claim_state"] = "abandoned"
        result = expect_error("VFY_SUBJECT_NOT_CURRENT", lambda: normalize_subjects(candidate))
    elif number == 14:
        candidate = valid_candidate()
        candidate["subjects"][0]["claim_state"] = "active"
        result = expect_error("VFY_SUBJECT_NOT_CURRENT", lambda: build_state(candidate))
    elif number == 15:
        subjects = normalize_subjects(valid_candidate())
        assert_true(subjects[0]["claim_state"] == "completed" and subjects[0]["dependency_chain_valid"], "current chain rejected")
        result = subjects[0]
    elif number == 16:
        candidate = valid_candidate()
        candidate["subjects"][0]["dependency_chain_valid"] = False
        result = expect_error("VFY_DEPENDENCY_CHAIN_INVALID", lambda: build_state(candidate))
    elif number == 17:
        candidate = valid_candidate()
        candidate["subjects"][0]["reference"] = "refs/heads/main"
        result = expect_error("VFY_SUBJECT_NOT_CURRENT", lambda: build_state(candidate))
    elif number == 18:
        candidate = valid_candidate()
        candidate["scope"]["delivery_scope"].append("resource:database")
        candidate["scope"]["imp_work_items"][0]["resource_ids"].append("database")
        result = expect_error("VFY_SUBJECT_SET_INCOMPLETE", lambda: build_state(candidate))
    elif number == 19:
        state = passing_state(root)
        snapshot = {"subjects": deepcopy(state["subjects"])}
        snapshot["subjects"][0]["result_digest"] = "sha256:" + "3" * 64
        result = expect_error(
            "VFY_SUBJECT_NOT_CURRENT",
            lambda: verify_state(state, finalizing=True, current_subject_snapshot=snapshot),
        )
    elif number == 20:
        targets = normalize_targets(valid_candidate())
        assert_true(all(item["source_kind"] == "vfo" for item in targets), "VFO authority not preserved")
        result = {"targets": len(targets)}
    elif number == 21:
        targets = normalize_targets(fallback_candidate())
        assert_true({item["source_kind"] for item in targets} == {"ac", "goal"}, "AC/Goal fallback invalid")
        result = {"targets": len(targets)}
    elif number == 22:
        candidate = valid_candidate()
        third = deepcopy(candidate["targets"][0])
        third["reference"] = "DSN-20260904100501-01@1#VFO-001"
        third["summary"] = candidate["targets"][0]["summary"]
        candidate["targets"].append(third)
        method = deepcopy(candidate["methods"][0])
        method["id"] = "VFM-003"
        method["target_references"] = [third["reference"]]
        candidate["methods"].append(method)
        state = build_state(candidate)
        assert_true(len(state["targets"]) == 3, "different exact references were text-merged")
        result = {"targets": 3}
    elif number == 23:
        candidate = valid_candidate()
        candidate["targets"] = []
        result = expect_error("VFY_TARGET_SET_INVALID", lambda: build_state(candidate))
    elif number == 24:
        candidate = valid_candidate()
        candidate["targets"][0]["source_kind"] = "requirement"
        result = expect_error("VFY_TARGET_SET_INVALID", lambda: build_state(candidate))
    elif number == 25:
        candidate = valid_candidate()
        candidate["targets"] = [{**candidate["targets"][0], "purpose": "both"}]
        candidate["methods"] = [{**candidate["methods"][0], "target_references": [candidate["targets"][0]["reference"]]}]
        result = expect_error("VFY_PURPOSE_MISMATCH", lambda: build_state(candidate))
    elif number in {26, 27, 28, 29}:
        method_type = {26: "inspection", 27: "analysis", 28: "demonstration", 29: "test"}[number]
        candidate = valid_candidate()
        candidate["methods"][0]["method_type"] = method_type
        state = build_state(candidate)
        assert_true(state["methods"][0]["method_type"] == method_type, "fixed Method Type rejected")
        result = {"method_type": method_type}
    elif number == 30:
        candidate = valid_candidate()
        candidate["methods"][0]["method_type"] = "security"
        result = expect_error("VFY_METHOD_NOT_READY", lambda: build_state(candidate))
    elif number == 31:
        candidate = valid_candidate()
        candidate["methods"] = [candidate["methods"][0]]
        result = expect_error("VFY_METHOD_COVERAGE_INCOMPLETE", lambda: build_state(candidate))
    elif number == 32:
        candidate = valid_candidate()
        candidate["methods"][0]["subject_references"] = []
        result = expect_error("VFY_METHOD_COVERAGE_INCOMPLETE", lambda: build_state(candidate))
    elif number == 33:
        candidate = valid_candidate()
        candidate["methods"][0]["purpose"] = "validation"
        result = expect_error("VFY_PURPOSE_MISMATCH", lambda: build_state(candidate))
    elif number in {34, 35, 36}:
        candidate = valid_candidate()
        missing = {
            34: "DSN-20260904100500-01@1#VEC-999",
            35: PLN + "#WI-999",
            36: "VFY-20260904120000-01@1#RET-999",
        }[number]
        candidate["required_obligation_references"].append(missing)
        result = expect_error("VFY_METHOD_COVERAGE_INCOMPLETE", lambda: build_state(candidate))
    elif number == 37:
        candidate = valid_candidate()
        candidate["methods"][0]["pass_criteria"] = ""
        result = expect_error("VFY_METHOD_NOT_READY", lambda: build_state(candidate))
    elif number == 38:
        candidate = valid_candidate()
        candidate["methods"][0].update(disposition="n/a", n_a_basis="tool unavailable")
        result = expect_error("VFY_METHOD_NOT_READY", lambda: build_state(candidate))
    elif number == 39:
        candidate = valid_candidate()
        candidate["methods"][0].update(disposition="waived", exception_reference=None)
        result = expect_error("VFY_METHOD_NOT_READY", lambda: build_state(candidate))
    elif number == 40:
        candidate = valid_candidate()
        candidate["methods"][0]["method_type"] = "automated"
        result = expect_error("VFY_METHOD_NOT_READY", lambda: build_state(candidate))
    elif number == 41:
        state = VfyHandler(root).run_state(open_state(root), method_ids=["VFM-001"], allow_commands=False)["state"]
        row = next(item for item in state["method_results"] if item["method_id"] == "VFM-001")
        assert_true(row["result"] == "pass" and row["evidence_references"], "automated Method lacks Evidence")
        result = row
    elif number == 42:
        candidate = valid_candidate()
        candidate["methods"][0]["procedure"] = {"kind": "command", "argv": ["pip", "install", "x"]}
        state = build_state(candidate)
        method = state["methods"][0]
        result = expect_error(
            "VFY_METHOD_NOT_READY",
            lambda: execute_method(method, project_root=root, evidence_sequence=1, allow_commands=True),
        )
    elif number == 43:
        candidate = valid_candidate()
        candidate["methods"][0].update(execution_mode="manual", method_type="demonstration")
        state = build_state(candidate)
        run = VfyHandler(root).run_state(state, method_ids=["VFM-001"], allow_commands=False)
        assert_true(run["waiting_methods"] == ["VFM-001"], "manual Method was fabricated")
        result = {"waiting": run["waiting_methods"]}
    elif number == 44:
        candidate = valid_candidate()
        candidate["methods"][0].update(execution_mode="manual", method_type="demonstration")
        state = build_state(candidate)
        result = expect_error(
            "VFY_EVIDENCE_INSUFFICIENT",
            lambda: VfyHandler(root).run_state(
                state,
                method_ids=["VFM-001"],
                allow_commands=False,
                manual_observations={
                    "VFM-001": {
                        "decision": "pass",
                        "evaluator_identity": "human-1",
                        "observed": "感觉正常",
                    }
                },
            ),
        )
    elif number == 45:
        method = build_state(valid_candidate())["methods"][0]
        result = expect_error(
            "VFY_SUBJECT_NOT_CURRENT",
            lambda: record_result(
                method,
                result="pass",
                actual_result="ok",
                evidence_references=["EVD"],
                actual_subject_references=["vcs:git:" + "9" * 40],
            ),
        )
    elif number == 46:
        candidate = valid_candidate()
        candidate["methods"][0]["procedure"] = {
            "kind": "command",
            "argv": [sys.executable, "-c", "raise SystemExit(7)"],
            "timeout_seconds": 30,
        }
        method = build_state(candidate)["methods"][0]
        row, evidence = execute_method(method, project_root=root, evidence_sequence=1, allow_commands=True)
        assert_true(row["result"] == "fail" and evidence["result"] == "fail", "exit failure was hidden")
        result = row
    elif number == 47:
        method = build_state(valid_candidate())["methods"][0]
        result = expect_error(
            "VFY_SECRET_REJECTED",
            lambda: build_evidence(
                evidence_id="EVD-001",
                method=method,
                result="pass",
                observed={"password": "secret"},
                actual_subject_references=method["subject_references"],
                environment={
                    "project_root": ".",
                    "path_basis": "invocation_project_root",
                },
            ),
        )
        assert_true("[REDACTED]" in redact_text("sk-abcdefghijklmnop"), "transient redaction failed")
    elif number == 48:
        state = passing_state(root)
        state["evidence"][0]["observed"] = {"tampered": True}
        result = expect_error("VFY_EVIDENCE_INSUFFICIENT", lambda: verify_state(state, finalizing=True))
    elif number == 49:
        state = passing_state(root)
        evidence = deepcopy(state["evidence"][0])
        evidence["environment"] = {}
        base = {key: value for key, value in evidence.items() if key not in {"sha256", "reference"}}
        evidence["sha256"] = sha256_bytes(canonical_bytes(base))
        evidence["reference"] = f"{evidence['id']}@{evidence['sha256']}"
        result = expect_error("VFY_EVIDENCE_INSUFFICIENT", lambda: verify_evidence(evidence))
    elif number == 50:
        candidate = valid_candidate()
        candidate["methods"][0]["disposition"] = "embedded"
        candidate["methods"][0]["procedure"] = {
            "kind": "evidence_review",
            "subject_references": [SUBJECT],
            "candidate_evidence": {
                "immutable": True,
                "digest": "sha256:" + "4" * 64,
                "subject_references": [SUBJECT],
            },
        }
        method = build_state(candidate)["methods"][0]
        row, _ = execute_method(method, project_root=root, evidence_sequence=1)
        assert_true(row["result"] == "pass", "matching upstream Evidence was not reviewable")
        result = row
    elif number == 51:
        candidate = valid_candidate()
        candidate["methods"][0]["disposition"] = "embedded"
        candidate["methods"][0]["procedure"] = {
            "kind": "evidence_review",
            "subject_references": [SUBJECT],
            "candidate_evidence": {
                "immutable": True,
                "digest": "sha256:" + "4" * 64,
                "subject_references": ["vcs:git:" + "8" * 40],
            },
        }
        method = build_state(candidate)["methods"][0]
        row, _ = execute_method(method, project_root=root, evidence_sequence=1)
        assert_true(row["result"] == "fail", "stale upstream Evidence was reused")
        result = row
    elif number == 52:
        state = passing_state(root)
        assert_true(state["product_result"] == "pass" and state["rls_ready"], "all-pass aggregation failed")
        result = {"product": state["product_result"]}
    elif number == 53:
        state = failing_state(root)
        assert_true(state["product_result"] == "fail" and state["artifact_gate"] == "pass", "product fail and Artifact Gate were conflated")
        result = {"product": state["product_result"], "gate": state["artifact_gate"]}
    elif number == 54:
        state = passing_state(root)
        state["pre_execution_contract_digest"] = "sha256:" + "0" * 64
        result = expect_error("VFY_FINAL_CONFIRMATION_STALE", lambda: verify_state(state, finalizing=True))
    elif number == 55:
        candidate = valid_candidate()
        candidate["targets"] = [{**candidate["targets"][0], "purpose": "both"}]
        candidate["methods"] = [{**candidate["methods"][0], "target_references": [candidate["targets"][0]["reference"]]}]
        result = expect_error("VFY_PURPOSE_MISMATCH", lambda: build_state(candidate))
    elif number in {56, 57, 58, 59}:
        phase = {56: "IMP", 57: "REQ", 58: "DSN", 59: "PLN"}[number]
        raw = return_for("VFM-001", phase=phase)
        rows = normalize_returns([raw], subject_lineages={SUBJECT: WI})
        assert_true(rows[0]["return_phase"] == phase, "Return was routed to wrong Phase")
        result = rows[0]
    elif number == 60:
        raw = return_for("VFM-001")
        raw["required_outcome"] = ""
        result = expect_error(
            "VFY_RETURN_INVALID",
            lambda: normalize_returns([raw], subject_lineages={SUBJECT: WI}),
        )
    elif number == 61:
        raw = return_for("VFM-001")
        raw["received_by_upstream"] = True
        row = normalize_returns([raw], subject_lineages={SUBJECT: WI})[0]
        assert_true(row["status"] == "open", "Return receipt was treated as resolution")
        result = row
    elif number == 62:
        raw = return_for("VFM-001")
        raw["status"] = "resolved"
        raw["resolution_references"] = ["VFY-20260904130000-01@2#VFM-001"]
        row = normalize_returns([raw], subject_lineages={SUBJECT: WI})[0]
        assert_true(row["status"] == "resolved" and row["resolution_references"], "later VFY proof did not resolve Return")
        result = row
    elif number == 63:
        raw = return_for("VFM-001")
        raw["imp_binding_lineage"] = PLN + "#WI-999"
        result = expect_error(
            "VFY_RETURN_INVALID",
            lambda: normalize_returns([raw], subject_lineages={SUBJECT: WI}),
        )
    elif number == 64:
        candidate = valid_candidate()
        issue = "RLS-20260904140000-01@1#RLI-001"
        candidate["control_inputs"] = [issue]
        candidate["methods"][0]["obligation_references"].append(issue)
        candidate["required_obligation_references"].append(issue)
        state = build_state(candidate)
        assert_true(issue in state["control_inputs"], "RLS product-correction Issue not carried")
        result = {"control": issue}
    elif number == 65:
        state = failing_state(root, early_stop=True)
        assert_true(state["early_stop"] and state["artifact_gate"] == "pass", "legal early stop did not freeze")
        result = {"early_stop": True}
    elif number == 66:
        state = open_state(root)
        (root / "README.md").unlink(missing_ok=True)
        early = {
            "failure_method_references": ["VFM-001"],
            "return_references": [f"{state['artifact']['reference']}#RET-001"],
            "pending_facts_cannot_change_failure_or_attribution": False,
        }
        result = expect_error(
            "VFY_EARLY_STOP_INVALID",
            lambda: VfyHandler(root).run_state(
                state,
                method_ids=["VFM-001"],
                allow_commands=False,
                failure_returns={"VFM-001": return_for("VFM-001")},
                early_stop_basis=early,
                finalize=False,
            ),
        )
    elif number == 67:
        state = failing_state(root, early_stop=True)
        pending = [item for item in state["method_results"] if item["result"] == "pending"]
        assert_true(len(pending) == 1 and pending[0]["return_references"], "early-stop pending result was disguised")
        result = pending[0]
    elif number == 68:
        state = failing_state(root, early_stop=True)
        assert_true(not state["rls_ready"] and project_vfy_state(state).next_phase != "RLS", "early-stop entered RLS")
        result = {"next": project_vfy_state(state).next_phase}
    elif number == 69:
        state = failing_state(root, early_stop=True)
        state["open_items"] = [{"id": "OPI-001", "status": "resolved", "affects_failure_validity_or_attribution": True}]
        result = expect_error("VFY_EARLY_STOP_INVALID", lambda: verify_state(state, finalizing=True))
    elif number == 70:
        state = failing_state(root)
        state["product_result"] = "pass"
        state["final_confirmation"]["product_result"] = "pass"
        result = expect_error("VFY_CONCLUSION_INCONSISTENT", lambda: verify_state(state, finalizing=True))
    elif number == 71:
        state = open_state(root)
        reference = state["artifact"]["reference"]
        updated = VfyHandler(root).run_state(state, method_ids=["VFM-001"], allow_commands=False)["state"]
        assert_true(updated["artifact"]["reference"] == reference, "run allocated another open Revision")
        result = {"reference": reference}
    elif number == 72:
        old = passing_state(root)
        candidate = valid_candidate()
        candidate["subjects"][0]["result_digest"] = "sha256:" + "7" * 64
        revised = VfyHandler(root).revise(old, candidate, persist=False)
        assert_true(revised["state"]["artifact"]["revision"] == 2, "new Subject did not create new Revision")
        result = revised
    elif number == 73:
        old = passing_state(root)
        same = VfyHandler(root).revise(old, valid_candidate(), persist=False)
        assert_true(same["status"] == "NO_CHANGE", "no-change revise created an empty Revision")
        result = {"status": same["status"]}
    elif number == 74:
        state = passing_state(root)
        state["final_confirmation"]["contract_digest"] = "sha256:" + "9" * 64
        result = expect_error("VFY_FINAL_CONFIRMATION_STALE", lambda: verify_state(state, finalizing=True))
    elif number == 75:
        candidate = persistent_authority_candidate(root)

        def reserve(_root, state, **_kwargs):
            return state, 0

        with patch.object(
            handler_module, "create_revision", side_effect=reserve
        ), patch.object(
            handler_module, "write_open_revision", side_effect=RuntimeError("first write failed")
        ), patch.object(handler_module, "abandon_revision") as abandoned:
            try:
                VfyHandler(root).create(candidate, persist=True, run_automated=False)
            except RuntimeError:
                pass
            else:
                raise AssertionError("first-write failure was hidden")
            assert_true(abandoned.called, "failed reservation was not abandoned")
        result = {"abandoned": True}
    elif number == 76:
        state = passing_state(root)
        before = hashlib.sha256(canonical_bytes(state)).hexdigest()
        checked = VfyHandler(root).check(state=state)
        after = hashlib.sha256(canonical_bytes(state)).hexdigest()
        assert_true(before == after == hashlib.sha256(canonical_bytes(checked["state"])).hexdigest(), "check changed bytes")
        result = {"digest": before}
    elif number == 77:
        state = passing_state(root)
        projection = project_vfy_state(state)
        assert_true(projection.next_phase == "RLS" and projection.rls_ready, "passing required VFY did not enter RLS")
        result = projection.to_dict()
    elif number == 78:
        state = failing_state(root)
        projection = project_vfy_state(state)
        assert_true(projection.next_phase == "IMP" and projection.next_action == "RETURN_UPSTREAM", "failed VFY did not return accurately")
        result = projection.to_dict()
    elif number == 79:
        candidate = valid_candidate()
        candidate["rls_applicability"] = "n/a"
        handler = VfyHandler(root)
        opened = handler.create(
            candidate,
            persist=False,
            run_automated=True,
            finalize=False,
        )["state"]
        state = handler.run_state(
            opened,
            method_ids=[],
            allow_commands=False,
            finalize=True,
            confirmation=delegated_confirmation(root, opened),
        )["state"]
        projection = project_vfy_state(state)
        assert_true(projection.next_phase is None and projection.next_action == "LIFECYCLE_COMPLETE", "RLS n/a created empty downstream work")
        result = projection.to_dict()
    elif number == 80:
        state = failing_state(root)
        status = {
            "artifact_status": state["artifact"]["artifact_status"],
            "artifact_gate": state["artifact_gate"],
            "product_result": state["product_result"],
        }
        assert_true(status == {"artifact_status": "ready", "artifact_gate": "pass", "product_result": "fail"}, "status conflated record trust and product result")
        result = status
    else:
        raise AssertionError(f"unknown Case: {case_id}")

    return {"case_id": case_id, "status": "PASS", "result": result}


def run_case(case_id: str) -> dict[str, Any]:
    if not isinstance(case_id, str) or not case_id.startswith("VFY-E"):
        raise ValueError("invalid Case ID")
    with workspace() as root:
        return _case(case_id, root)
