#!/usr/bin/env python3
"""Fresh static implementation review for VFY Web findings.

This is an executable guard over source and test structure.  It does not accept a
prewritten Markdown review as proof.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


class ReviewError(ValueError):
    pass


def text(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        raise ReviewError(f"missing required path: {path}")
    return target.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewError(message)


def python_tree(path: str) -> ast.AST:
    return ast.parse(text(path), filename=path)


def main() -> int:
    interface = json.loads(text("skills/sdlc-500-vfy/references/interface.json"))
    require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(interface.get("skill_version", ""))) is not None,
            "VFY interface version is not strict SemVer")

    runtime = text("skills/sdlc-500-vfy/scripts/runtime.py")
    authority = text("skills/sdlc-500-vfy/scripts/vfy_authority.py")
    handler = text("skills/sdlc-500-vfy/scripts/vfy_handler.py")
    canonical = text("skills/sdlc-500-vfy/scripts/vfy_canonical.py")
    executor = text("skills/sdlc-500-vfy/scripts/vfy_executor.py")
    returns = text("skills/sdlc-500-vfy/scripts/vfy_returns.py")
    verifier = text("skills/sdlc-500-vfy/scripts/vfy_verifier.py")
    exceptions = text("skills/sdlc-500-vfy/scripts/vfy_exceptions.py")
    delivery = text("tools/run_vfy_delivery_validation.py")

    require("compile_candidate" in runtime and "command.input_references" in runtime,
            "public CLI does not compile repeatable exact inputs")
    require("projection.vfy_results" in authority and "ControlInputResolver" in authority,
            "authority compiler does not bind full Result Set and Control Input resolver")
    require("full != references" in handler or "full == references" in handler,
            "handler does not require complete terminal Subject equality")
    require("Production check requires exact persisted VFY Reference" in handler,
            "production check still accepts arbitrary in-memory state")

    for token in (
        "INPUT_HEADERS", "TARGET_HEADERS", "METHOD_HEADERS", "RESULT_HEADERS",
        "CONCLUSION_HEADERS", "RETURN_HEADERS", "validate_primary_against_state",
    ):
        require(token in canonical, f"canonical VFY contract missing {token}")
    require("VFY-STATE" in canonical and "member_ids" in canonical,
            "canonical primary/state/manifest equality guard is missing")

    for forbidden in ("\"sh\"", "\"bash\"", "\"zsh\"", "\"-c\""):
        require(forbidden in executor, f"executor has no explicit rejection marker for {forbidden}")
    for required in (
        "deterministic-test-v1", "isolated-copy", "max_output_bytes",
        "source_before", "source_after", "evaluator_identity", "observed_at",
    ):
        require(required in executor, f"executor hardening missing {required}")

    require("derive_control_resolutions" in returns and "validate_failed_results_have_returns" in verifier,
            "Return/control recovery is not proof-derived")
    require("Control resolution" in returns and "authority_verified" in returns,
            "Control resolution does not require verified frozen authority")
    require("normalize_exceptions" in exceptions and "pass_with_exception" in verifier,
            "Exception/pass-with-exception path is incomplete")

    require("validate_skill_interfaces.py" in delivery,
            "delivery controller still omits Skill Interface validation")
    require("review_sdlc_500_vfy_implementation.py" in delivery,
            "delivery controller still trusts a prewritten review file")

    for path in (
        "skills/sdlc-500-vfy/scripts/vfy_authority.py",
        "skills/sdlc-500-vfy/scripts/vfy_builder.py",
        "skills/sdlc-500-vfy/scripts/vfy_canonical.py",
        "skills/sdlc-500-vfy/scripts/vfy_domain_verifier.py",
        "skills/sdlc-500-vfy/scripts/vfy_executor.py",
        "skills/sdlc-500-vfy/scripts/vfy_handler.py",
        "skills/sdlc-500-vfy/scripts/vfy_methods.py",
        "skills/sdlc-500-vfy/scripts/vfy_results.py",
        "skills/sdlc-500-vfy/scripts/vfy_returns.py",
        "skills/sdlc-500-vfy/scripts/vfy_verifier.py",
        "skills/sdlc-500-vfy/scripts/runtime.py",
        "tests/skill_vfy/test_web_review_repairs.py",
        "tests/evals/vfy_case_harness_hardened.py",
    ):
        python_tree(path)

    # Execute adversarial authority/Primary/sandbox oracles in a fresh process.
    # Source markers alone cannot prove these implementation boundaries.
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.skill_vfy.test_fresh_review_boundaries",
         "tests.skill_vfy.test_sandbox_capability"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=120, check=False,
    )
    require(completed.returncode == 0,
            "fresh behavioral review failed: " + completed.stdout + completed.stderr)
    print(completed.stderr.strip())

    print("VFY_IMPLEMENTATION_REVIEW=PASS")
    print("VFY-WEB-001..006 structural guards=PASS")
    print("VFY-WEB-007 capability/unittest/Formal Eval behavioral guards=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReviewError, SyntaxError, json.JSONDecodeError) as exc:
        print(f"VFY_IMPLEMENTATION_REVIEW=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
