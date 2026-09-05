#!/usr/bin/env python3
"""Run fixed VFY-E001..VFY-E080 evaluation with hardened no-skip semantics."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import traceback
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.evals.vfy_case_harness_hardened import run_case  # noqa: E402

CASES_PATH = Path(__file__).resolve().with_name("sdlc_500_vfy_cases.json")


def require_command_execution(case_id: str, actual: dict[str, Any]) -> None:
    """E041/E046 require real command Evidence, never a capability-test PASS."""
    if case_id not in {"VFY-E041", "VFY-E046"}:
        return
    row = actual.get("result") or {}
    observed = json.loads(row.get("actual_result") or "{}")
    expected = "pass" if case_id == "VFY-E041" else "fail"
    if not (
        row.get("result") == expected and row.get("evidence_references")
        and observed.get("kind") == "command"
        and observed.get("containment") == "os-sandbox"
        and observed.get("network") == "disabled"
        and observed.get("timed_out") is False
        and type(observed.get("exit_code")) is int
        and ((observed["exit_code"] == 0) == (expected == "pass"))
        and observed.get("source_before")
        and observed["source_before"] == observed.get("source_after")
        and "Ran 1 test" in observed.get("stderr", "")
    ):
        raise AssertionError(f"{case_id} requires actual sandbox command execution and Evidence")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_cases() -> list[dict[str, Any]]:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if payload.get("contract") != "sdlc-ai-spec/fixed-eval-cases/v1":
        raise ValueError("unsupported fixed eval registry contract")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 80:
        raise ValueError("VFY fixed eval registry must contain exactly 80 Cases")
    expected = [f"VFY-E{index:03d}" for index in range(1, 81)]
    actual = [str(item.get("id")) for item in cases]
    if actual != expected or len(set(actual)) != 80:
        raise ValueError("VFY fixed eval IDs must be unique ordered VFY-E001..VFY-E080")
    return cases


def run(selected: set[str] | None = None) -> dict[str, Any]:
    cases = load_cases()
    if selected is not None:
        unknown = selected - {str(item["id"]) for item in cases}
        if unknown:
            raise ValueError(f"unknown Case IDs: {sorted(unknown)}")
        cases = [item for item in cases if item["id"] in selected]
    results: list[dict[str, Any]] = []
    for item in cases:
        case_id = str(item["id"])
        try:
            actual = run_case(case_id)
            require_command_execution(case_id, actual)
            status = "PASS" if actual.get("status") == "PASS" else "FAIL"
            results.append({"case_id": case_id, "status": status, "result": actual.get("result"), "error": None})
        except Exception as exc:
            results.append(
                {
                    "case_id": case_id,
                    "status": "FAIL",
                    "result": None,
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                        "code": getattr(exc, "code", None),
                        "status": getattr(exc, "status", None),
                    },
                }
            )
    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = len(results) - passed
    return {
        "contract": "sdlc-ai-spec/vfy-fixed-eval-result/v1",
        "generated_at": utc_now(),
        "registry": str(CASES_PATH.relative_to(ROOT)),
        "selected_count": len(results),
        "expected_full_count": 80,
        "passed": passed,
        "failed": failed,
        "status": "PASS" if failed == 0 and (selected is not None or len(results) == 80) else "FAIL",
        "complete_fixed_eval": selected is None and len(results) == 80 and failed == 0,
        "skipped": 0,
        "expected_failures": 0,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--json-out", type=Path)
    arguments = parser.parse_args(argv)
    try:
        report = run(set(arguments.case) if arguments.case else None)
    except Exception as exc:
        report = {
            "contract": "sdlc-ai-spec/vfy-fixed-eval-result/v1",
            "generated_at": utc_now(),
            "status": "FAIL",
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "expected_failures": 0,
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
            "results": [],
        }
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if arguments.json_out:
        arguments.json_out.parent.mkdir(parents=True, exist_ok=True)
        arguments.json_out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
