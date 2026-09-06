#!/usr/bin/env python3
"""Execute the original fourteen Status checks; coverage is never inferred from files."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
CASE_MAP = ROOT / "tests/evals/sdlc_status_cases.json"
PLAN = ROOT / "docs/plugin-development/work-items/sdlc-status/EVAL-PLAN.md"
EXPECTED = [f"STS-E{i:02d}" for i in range(1, 15)]


def require(condition, message):
    if not condition: raise ValueError(message)


def load_cases(path: Path = CASE_MAP):
    data = json.loads(path.read_bytes())
    require(data["contract"] == "sdlc-ai-spec/status-fixed-cases/v1" and data["case_count"] == 14, 'validation assertion failed: tests/evals/run_sdlc_status_eval.py:21')
    require(data["oracle_plan_sha256"] == hashlib.sha256(PLAN.read_bytes()).hexdigest(), "original Oracle changed")
    rows = data["cases"]
    require([row["id"] for row in rows] == EXPECTED, "missing, duplicate or reordered case")
    names = [row["primary_test"] for row in rows]
    require(len(set(names)) == 14, "one primary test cannot cover multiple cases")
    for row in rows:
        require(row["requirement"] and row["primary_test"].startswith("tests.skill_status."), 'validation assertion failed: tests/evals/run_sdlc_status_eval.py:28')
    return rows


def build_suite(rows):
    suite = unittest.TestSuite()
    for row in rows:
        loaded = unittest.defaultTestLoader.loadTestsFromName(row["primary_test"])
        values = list(loaded)
        require(len(values) == 1 and values[0].id() == row["primary_test"], "primary test does not exist")
        suite.addTests(loaded)
    return suite


def run(json_out: Path | None = None):
    stream = io.StringIO(); payload = {"contract":"sdlc-ai-spec/status-eval-result/v1", "success":False, "tests_run":0}
    try:
        rows = load_cases(); result = unittest.TextTestRunner(stream=stream, verbosity=2).run(build_suite(rows))
        payload.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                       skipped=len(result.skipped), expected_failures=len(result.expectedFailures), unexpected_successes=len(result.unexpectedSuccesses),
                       success=result.wasSuccessful() and result.testsRun == 14 and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses,
                       executed_primary_tests=[row["primary_test"] for row in rows], case_ids=EXPECTED)
    except Exception as exc: payload["error"] = str(exc)
    payload["log"] = stream.getvalue(); payload["native_client_behavior"] = "NOT_RUN"
    if json_out:
        from tools.rls_validation_support import write_json
        write_json(json_out, payload)
    return payload


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--json-out", type=Path, required=True); args=parser.parse_args()
    result=run(args.json_out); print(result["log"],end="")
    print("STATUS_FIXED_EVAL =", "14/14 PASS" if result["success"] else "FAIL")
    raise SystemExit(0 if result["success"] else 1)
