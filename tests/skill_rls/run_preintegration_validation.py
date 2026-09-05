#!/usr/bin/env python3
"""Local, non-Actions RLS pre-integration validation and checkpoint report."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.evals.run_sdlc_600_rls_eval import run as run_case_eval
from tests.skill_rls.preweb_review import review as run_preweb_review

EXACT_SHA = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_FINAL_DEFERRED = [
    "RLS-FINAL-001",
    "RLS-FINAL-002",
    "RLS-FINAL-003",
    "RLS-FINAL-004",
    "RLS-FINAL-005",
]


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(arguments)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _suite() -> unittest.TestSuite:
    private = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests/skill_rls"),
        pattern="test_*.py",
        top_level_dir=str(ROOT),
    )
    coverage = unittest.defaultTestLoader.loadTestsFromName(
        "tests.evals.test_sdlc_600_rls_case_coverage"
    )
    suite = unittest.TestSuite()
    suite.addTests(private)
    suite.addTests(coverage)
    return suite


def validate(root: Path, source_sha: str | None = None) -> dict:
    root = root.resolve()
    observed_sha = None
    source_tree = None
    if source_sha is not None:
        if not EXACT_SHA.fullmatch(source_sha):
            raise AssertionError("--source-sha must be exact lowercase 40-hex")
        observed_sha = _git(root, "rev-parse", "--verify", "HEAD")
        if observed_sha != source_sha:
            raise AssertionError(
                f"source SHA mismatch: requested={source_sha}, observed={observed_sha}"
            )
        source_tree = _git(root, "rev-parse", "HEAD^{tree}")
        if _git(root, "status", "--porcelain", "--untracked-files=no"):
            raise AssertionError("tracked worktree must be clean")

    stream = io.StringIO()
    unit = unittest.TextTestRunner(
        stream=stream,
        verbosity=2,
        failfast=False,
    ).run(_suite())
    case_eval = run_case_eval()
    provisional = run_preweb_review(root, "provisional")
    final = run_preweb_review(root, "final")
    deferred = [
        row["id"]
        for row in final["final_requirements"]
        if row["status"] != "PASS"
    ]
    success = bool(
        unit.wasSuccessful()
        and not unit.skipped
        and not unit.expectedFailures
        and not unit.unexpectedSuccesses
        and case_eval.get("success") is True
        and case_eval.get("tests_run") == 87
        and case_eval.get("skipped") == 0
        and case_eval.get("expected_failures") == 0
        and provisional.get("success") is True
        and final.get("success") is False
        and deferred == EXPECTED_FINAL_DEFERRED
    )
    if source_sha is not None:
        if _git(root, "status", "--porcelain", "--untracked-files=no"):
            success = False

    return {
        "contract": "sdlc-ai-spec/rls-preintegration-validation/v1",
        "provisional": True,
        "source_sha": source_sha,
        "observed_source_sha": observed_sha,
        "source_tree": source_tree,
        "source_binding": "EXACT_GIT_HEAD" if source_sha else "UNBOUND_LOCAL_WORKTREE",
        "success": success,
        "private_and_guard_tests": {
            "tests_run": unit.testsRun,
            "failures": len(unit.failures),
            "errors": len(unit.errors),
            "skipped": len(unit.skipped),
            "expected_failures": len(unit.expectedFailures),
            "unexpected_successes": len(unit.unexpectedSuccesses),
            "success": unit.wasSuccessful(),
            "log": stream.getvalue(),
        },
        "critical_cases": {
            "tests_run": case_eval.get("tests_run"),
            "failures": case_eval.get("failures"),
            "errors": case_eval.get("errors"),
            "skipped": case_eval.get("skipped"),
            "expected_failures": case_eval.get("expected_failures"),
            "success": case_eval.get("success"),
            "authority": "PROVISIONAL_VFY_INTERFACE",
        },
        "preweb_provisional": provisional,
        "preweb_final": {
            "success": final.get("success"),
            "deferred": deferred,
            "expected_deferred": EXPECTED_FINAL_DEFERRED,
        },
        "fixed_eval": "NOT CLAIMED",
        "closed_loop": "NOT CLAIMED",
        "real_target_effects": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source-sha")
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate(args.root, args.source_sha)
    except Exception as exc:
        print(f"RLS_PREINTEGRATION_VALIDATION = HARD_BLOCKED: {exc}", file=sys.stderr)
        return 1
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not result["success"]:
        print("RLS_PREINTEGRATION_VALIDATION = HARD_BLOCKED", file=sys.stderr)
        return 1
    print("RLS_PREINTEGRATION_VALIDATION = PASS")
    print(
        "PRIVATE_AND_GUARD_TESTS = "
        f"{result['private_and_guard_tests']['tests_run']} PASS"
    )
    print("RLS_PROVISIONAL_CASES = 87/87")
    print("RLS_FINAL_DEFERRED = " + ",".join(EXPECTED_FINAL_DEFERRED))
    print("RLS_CLOSED_LOOP = NOT CLAIMED")
    print("REAL_TARGET_EFFECTS = 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
