#!/usr/bin/env python3
"""Fail-closed coverage guard for VFY-E001..VFY-E080."""
from __future__ import annotations

import json
import io
import importlib
from pathlib import Path
import sys
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "tests/evals/sdlc_500_vfy_cases.json"
HARNESS_FILE = ROOT / "tests/evals/vfy_case_harness.py"
EXPECTED_IDS = [f"VFY-E{index:03d}" for index in range(1, 81)]
EXPECTED_TESTS = [f"test_vfy_e{index:03d}" for index in range(1, 81)]
GROUPS = (
    (1, 9, "test_interface", "VfyInterfaceCases"),
    (10, 19, "test_scope_subject", "VfyScopeSubjectCases"),
    (20, 25, "test_targets", "VfyTargetCases"),
    (26, 40, "test_methods", "VfyMethodCases"),
    (41, 51, "test_executor_evidence", "VfyExecutorEvidenceCases"),
    (52, 64, "test_conclusions_returns", "VfyConclusionReturnCases"),
    (65, 70, "test_early_stop", "VfyEarlyStopCases"),
    (71, 80, "test_revision_lifecycle", "VfyRevisionLifecycleCases"),
)


def fail(message: str) -> None:
    raise ValueError(message)


def validate() -> dict[str, Any]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if payload.get("contract") != "sdlc-ai-spec/fixed-eval-cases/v1":
        fail("wrong registry contract")
    if payload.get("skill") != "sdlc-500-vfy":
        fail("wrong registry skill")
    if payload.get("expected_count") != 80:
        fail("expected_count must be 80")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        fail("cases must be an array")
    ids = [str(item.get("id")) for item in cases if isinstance(item, dict)]
    tests = [str(item.get("test")) for item in cases if isinstance(item, dict)]
    expected = [str(item.get("expected")) for item in cases if isinstance(item, dict)]
    if ids != EXPECTED_IDS:
        fail("Case IDs must be complete, unique and ordered VFY-E001..VFY-E080")
    if tests != EXPECTED_TESTS:
        fail("Each Case must map one-to-one to test_vfy_e001..test_vfy_e080")
    if len(set(ids)) != 80 or len(set(tests)) != 80:
        fail("Case IDs and primary tests must be unique")
    if expected != ["PASS"] * 80:
        fail("Every Case Oracle must require PASS")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tests.skill_vfy.sandbox_support import probe_sandbox_capability
    capability = probe_sandbox_capability()
    if not capability["available"]:
        fail("Critical Case execution requires sandbox capability: " + json.dumps(capability["error"]))
    primary_ids: list[str] = []
    suite = unittest.TestSuite()
    module_files: list[str] = []
    for first, last, module_name, class_name in GROUPS:
        path = ROOT / "tests/skill_vfy" / f"{module_name}.py"
        if not path.is_file():
            fail(f"required Critical Case module is missing: {path.relative_to(ROOT)}")
        source = path.read_text(encoding="utf-8")
        if "unittest.skip" in source or "expectedFailure" in source:
            fail(f"skip/expectedFailure is forbidden: {path.relative_to(ROOT)}")
        module = importlib.import_module(f"tests.skill_vfy.{module_name}")
        test_class = getattr(module, class_name, None)
        if not isinstance(test_class, type) or not issubclass(test_class, unittest.TestCase):
            fail(f"collectable TestCase is missing: {module_name}.{class_name}")
        module_files.append(str(path.relative_to(ROOT)))
        for number in range(first, last + 1):
            method_name = f"test_vfy_e{number:03d}"
            method = getattr(test_class, method_name, None)
            if not callable(method) or getattr(method, "__unittest_skip__", False):
                fail(f"collectable unskipped primary test is missing: {module_name}.{method_name}")
            primary = f"tests.skill_vfy.{module_name}.{class_name}.{method_name}"
            primary_ids.append(primary)
            instance = test_class(method_name)
            instance.require_execution = True
            suite.addTest(instance)
    if len(primary_ids) != 80 or len(set(primary_ids)) != 80:
        fail("Primary Tests are duplicated or incomplete")
    execution = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    if execution.testsRun != 80:
        fail(f"Coverage Guard executed {execution.testsRun} tests instead of 80")
    if execution.failures or execution.errors or execution.skipped or execution.expectedFailures:
        fail(
            "Critical primary tests did not all execute and pass: "
            f"failures={len(execution.failures)} errors={len(execution.errors)} "
            f"skipped={len(execution.skipped)} expected_failures={len(execution.expectedFailures)}"
        )

    return {
        "contract": "sdlc-ai-spec/vfy-case-coverage-result/v1",
        "status": "PASS",
        "case_count": 80,
        "unique_case_ids": 80,
        "unique_primary_tests": 80,
        "oracle_branches": len(expected),
        "executed_primary_tests": execution.testsRun,
        "skipped": 0,
        "expected_failures": 0,
        "registry": str(REGISTRY.relative_to(ROOT)),
        "primary_tests": primary_ids,
        "test_modules": module_files,
        "harness": str(HARNESS_FILE.relative_to(ROOT)),
    }


def main() -> int:
    try:
        report = validate()
        code = 0
    except Exception as exc:
        report = {
            "contract": "sdlc-ai-spec/vfy-case-coverage-result/v1",
            "status": "FAIL",
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
        }
        code = 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
