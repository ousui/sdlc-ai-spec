"""Shared fixed-eval runner for late Phase Skills."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = {
    "PLN": {
        "suite": "skill_pln",
        "tools": (
            "tools/validate_sdlc_300_pln_source_lock.py",
            "tools/test_sdlc_300_pln_runtime_independence.py",
        ),
    },
    "IMP": {
        "suite": "skill_imp",
        "extra": ("late_foundations",),
        "tools": (
            "tools/validate_sdlc_400_imp_source_lock.py",
            "tools/test_sdlc_400_imp_runtime_independence.py",
        ),
    },
    "VFY": {
        "suite": "skill_vfy",
        "tools": (
            "tools/validate_sdlc_500_vfy_source_lock.py",
            "tools/test_sdlc_500_vfy_runtime_independence.py",
        ),
    },
    "RLS": {
        "suite": "skill_rls",
        "extra": ("lifecycle",),
        "tools": (
            "tools/validate_sdlc_600_rls_source_lock.py",
            "tools/test_sdlc_600_rls_runtime_independence.py",
        ),
    },
}


def run_tool(relative: str) -> bool:
    result = subprocess.run(
        [sys.executable, str(ROOT / relative)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0


def suite_for(directory: str):
    return unittest.defaultTestLoader.discover(
        str(ROOT / "tests" / directory),
        pattern="test_*.py",
        top_level_dir=str(ROOT),
    )


def run_phase(phase: str) -> int:
    config = CONFIG[phase]
    if not all(run_tool(item) for item in config["tools"]):
        print(f"sdlc-{phase.lower()} eval: FAIL: deterministic gate", file=sys.stderr)
        return 1
    suite = unittest.TestSuite()
    suite.addTests(suite_for(config["suite"]))
    for extra in config.get("extra", ()):
        suite.addTests(suite_for(extra))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        print(f"sdlc-{phase.lower()} eval: FAIL", file=sys.stderr)
        return 1
    print(f"sdlc-{phase.lower()} eval: PASS")
    print("critical cases:", result.testsRun)
    print("runtime independence: PASS")
    return 0
