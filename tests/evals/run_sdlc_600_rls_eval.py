#!/usr/bin/env python3
"""Execute every mapped final RLS Critical Case exactly once."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rls_validation_support import REDACTION_POLICY, redact_receipt, write_json

from tests.evals.test_sdlc_600_rls_case_coverage import load_case_map, test_functions, verify_original_oracles, EXPECTED_IDS


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def build_suite() -> unittest.TestSuite:
    case_map = load_case_map()
    verify_original_oracles(case_map["cases"])
    if [row["case_id"] for row in case_map["cases"]] != EXPECTED_IDS:
        raise RuntimeError("missing, duplicate or out-of-order Case IDs")
    functions = test_functions()
    discovered = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests/skill_rls"),
        pattern="test_critical_cases_*.py",
        top_level_dir=str(ROOT),
    )
    by_method = {}
    for test in _flatten(discovered):
        method = test._testMethodName
        if method in by_method:
            raise RuntimeError(f"duplicate executable primary test: {method}")
        by_method[method] = test
    suite = unittest.TestSuite()
    for row in case_map["cases"]:
        method = row["primary_test"]
        if method not in functions or method not in by_method:
            raise RuntimeError(f"mapped primary test does not exist: {method}")
        suite.addTest(by_method[method])
    return suite


class OrderedResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.executed.append(test._testMethodName)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed = []


def run(json_out: Path | None = None) -> dict:
    stream = io.StringIO()
    payload = dict(contract="sdlc-ai-spec/rls-final-eval-result/v1", provisional=False,
                   fixture_authority="REAL_PERSISTED_ACCEPTED_VFY", success=False,
                   tests_run=0, failures=0, errors=0, skipped=0, expected_failures=0, unexpected_successes=0)
    try:
        expected = [row["primary_test"] for row in load_case_map()["cases"]]
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=OrderedResult).run(build_suite())
        payload.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                       skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
                       unexpected_successes=len(result.unexpectedSuccesses), executed_primary_tests=result.executed,
                       executed_case_ids=["RLS-E" + name.split("_")[2][1:] for name in result.executed],
                       success=result.wasSuccessful() and result.testsRun == 87 and result.executed == expected
                       and len(set(result.executed)) == 87 and not result.skipped
                       and not result.expectedFailures and not result.unexpectedSuccesses)
    except Exception as exc:
        payload.update(error_type=type(exc).__name__, error=str(exc))
        stream.write(str(exc))
    payload["log"] = stream.getvalue()
    payload["redaction_policy"] = REDACTION_POLICY
    payload = redact_receipt(payload)
    if json_out:
        write_json(json_out, payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    payload = run(args.json_out)
    if payload["success"]:
        print("RLS_FIXED_EVAL = 87/87 PASS")
        return 0
    print(payload["log"], file=sys.stderr)
    print(
        f"RLS_FIXED_EVAL = FAIL "
        f"({payload['tests_run']} run, {payload['failures']} failures, "
        f"{payload['errors']} errors, {payload['skipped']} skipped)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
