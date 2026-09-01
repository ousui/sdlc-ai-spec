#!/usr/bin/env python3
"""Fixed deterministic evaluation runner for sdlc-200-dsn."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


def run_tool(relative: str) -> bool:
    completed = subprocess.run(
        [sys.executable, str(ROOT / relative)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode == 0


def main() -> int:
    gates = (
        "tools/validate_sdlc_200_dsn_source_lock.py",
        "tools/test_sdlc_200_dsn_runtime_independence.py",
    )
    if not all(run_tool(item) for item in gates):
        print("sdlc-200-dsn eval: FAIL: deterministic gate failed", file=sys.stderr)
        return 1

    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests/skill_dsn"),
        pattern="test_*.py",
        top_level_dir=str(ROOT / "tests"),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        print("sdlc-200-dsn eval: FAIL", file=sys.stderr)
        return 1
    print("sdlc-200-dsn eval: PASS")
    print("critical cases:", result.testsRun)
    print("source-lock contracts: 26")
    print("runtime independence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
