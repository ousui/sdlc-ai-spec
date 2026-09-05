#!/usr/bin/env python3
"""Single fail-closed Web/provisional validation entry point for sdlc-600-rls."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
EXACT_SHA = re.compile(r"^[0-9a-f]{40}$")
SECRET = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._~+/=-]{16,})"
)


def now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def redact(text: str) -> str:
    return SECRET.sub("[REDACTED]", text)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_step(root: Path, name: str, argv: list[str], log_dir: Path) -> dict:
    started_at = now()
    start = time.monotonic()
    completed = subprocess.run(
        argv,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
        env={
            **dict(__import__("os").environ),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(root),
        },
    )
    duration = round(time.monotonic() - start, 6)
    output = redact(completed.stdout)
    log_path = log_dir / f"{name}.log"
    log_path.write_text(output, encoding="utf-8")
    return {
        "name": name,
        "argv": argv,
        "cwd": str(root),
        "started_at": started_at,
        "duration_seconds": duration,
        "exit_code": completed.returncode,
        "log_path": str(log_path),
        "log_sha256": digest(output),
        "result": "PASS" if completed.returncode == 0 else "FAIL",
    }


def static_scan(root: Path, log_dir: Path) -> dict:
    started_at = now()
    start = time.monotonic()
    allowed_roots = [
        root / "skills/sdlc-600-rls",
        root / "tests/skill_rls",
        root / "tests/evals/sdlc_600_rls_cases.json",
        root / "tests/evals/test_sdlc_600_rls_case_coverage.py",
        root / "tests/evals/run_sdlc_600_rls_eval.py",
        root / "tools/validate_sdlc_600_rls_source_lock.py",
        root / "tools/test_sdlc_600_rls_runtime_independence.py",
        root / "tools/run_rls_provisional_validation.py",
    ]
    files: list[Path] = []
    for path in allowed_roots:
        if path.is_dir():
            files.extend(
                item
                for item in path.rglob("*")
                if item.is_file() and "__pycache__" not in item.parts
            )
        elif path.is_file():
            files.append(path)
    failures: list[str] = []
    forbidden_runtime = re.compile(
        r"\b(requests|httpx|boto3|paramiko)\b|urllib\.request|socket\.|"
        r"subprocess\.|os\.system\(|git\s+(?:push|tag)|gh\s+release|"
        r"github\s+release",
        re.IGNORECASE,
    )
    absolute_machine = re.compile(
        r"/(?:Users|home|private/tmp)/[A-Za-z0-9._-]+/"
    )
    for path in files:
        if path.suffix not in {".py", ".md", ".json", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        if SECRET.search(text):
            failures.append(f"secret-like literal: {relative}")
        if absolute_machine.search(text):
            failures.append(f"absolute machine path: {relative}")
        if (
            relative.startswith("skills/sdlc-600-rls/scripts/")
            and forbidden_runtime.search(text)
        ):
            failures.append(
                f"network/process/release capability in Runtime: {relative}"
            )
        if (
            ("docs/" in text or "docs\\" in text)
            and relative.startswith("skills/sdlc-600-rls/scripts/")
        ):
            failures.append(
                f"Runtime reads or names development docs: {relative}"
            )
    required = [
        "skills/sdlc-600-rls/scripts/rls_vfy_adapter.py",
        "skills/sdlc-600-rls/scripts/rls_authorization.py",
        "skills/sdlc-600-rls/scripts/rls_target.py",
        "skills/sdlc-600-rls/references/vfy-release-candidate-v1.schema.json",
        "tests/skill_rls/fixtures/vfy-release-candidate-final-shadow-v1.json",
        "tests/skill_rls/preweb_review.py",
        "tests/skill_rls/test_preweb_review.py",
        "tests/evals/sdlc_600_rls_cases.json",
    ]
    for relative in required:
        if not (root / relative).is_file():
            failures.append(f"missing required file: {relative}")
    output = (
        "\n".join(failures)
        if failures
        else f"scanned {len(files)} allowed RLS files; no violations\n"
    )
    path = log_dir / "static_scan.log"
    path.write_text(output, encoding="utf-8")
    return {
        "name": "static_scan",
        "argv": ["internal:static_scan"],
        "cwd": str(root),
        "started_at": started_at,
        "duration_seconds": round(time.monotonic() - start, 6),
        "exit_code": 1 if failures else 0,
        "log_path": str(path),
        "log_sha256": digest(output),
        "result": "FAIL" if failures else "PASS",
        "violations": failures,
    }


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed: {redact(completed.stderr.strip())}"
        )
    return completed.stdout.strip()


def _tests_run(log_path: Path) -> int:
    if not log_path.is_file():
        return 0
    match = re.search(
        r"Ran\s+(\d+)\s+tests?",
        log_path.read_text(encoding="utf-8"),
    )
    return int(match.group(1)) if match else 0


def validate(
    profile: str,
    root: Path,
    source_sha: str,
    json_out: Path,
) -> dict:
    root = root.resolve()
    json_out = json_out.resolve()
    if not EXACT_SHA.fullmatch(source_sha):
        raise AssertionError(
            "--source-sha must be an exact lowercase 40-hex commit SHA"
        )
    observed_source_sha = _git(root, "rev-parse", "--verify", "HEAD")
    if source_sha != observed_source_sha:
        raise AssertionError(
            "source SHA mismatch: "
            f"requested={source_sha}, observed={observed_source_sha}"
        )
    source_tree = _git(root, "rev-parse", "HEAD^{tree}")
    tracked_status_before = _git(
        root, "status", "--porcelain", "--untracked-files=no"
    )
    if tracked_status_before:
        raise AssertionError(
            "tracked worktree changes make source attestation ambiguous"
        )

    log_dir = json_out.with_suffix("")
    log_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    steps = [
        (
            "compileall",
            [
                python,
                "-m",
                "compileall",
                "-q",
                "skills/sdlc-600-rls",
                "tests/skill_rls",
                "tests/evals",
                "tools/validate_sdlc_600_rls_source_lock.py",
                "tools/test_sdlc_600_rls_runtime_independence.py",
                "tools/run_rls_provisional_validation.py",
            ],
        ),
        (
            "private_tests",
            [
                python,
                "-m",
                "unittest",
                "-v",
                "tests.skill_rls.test_critical_cases_001_030",
                "tests.skill_rls.test_critical_cases_031_060",
                "tests.skill_rls.test_critical_cases_061_087",
                "tests.skill_rls.test_fake_target",
                "tests.skill_rls.test_runtime",
                "tests.skill_rls.test_vfy_adapter_shadow",
                "tests.skill_rls.test_authorization_binding",
                "tests.skill_rls.test_verifier_authorization_history",
                "tests.skill_rls.test_preweb_review",
            ],
        ),
        (
            "case_coverage",
            [
                python,
                "-m",
                "unittest",
                "-v",
                "tests.evals.test_sdlc_600_rls_case_coverage",
            ],
        ),
        (
            "source_lock",
            [
                python,
                "tools/validate_sdlc_600_rls_source_lock.py",
                "--root",
                str(root),
            ],
        ),
        (
            "preweb_review",
            [
                python,
                "tests/skill_rls/preweb_review.py",
                "--profile",
                "provisional",
                "--root",
                str(root),
                "--json-out",
                str(log_dir / "preweb_review.json"),
            ],
        ),
    ]
    if profile == "provisional":
        steps.extend(
            [
                (
                    "provisional_eval",
                    [
                        python,
                        "tests/evals/run_sdlc_600_rls_eval.py",
                        "--json-out",
                        str(log_dir / "provisional_eval.json"),
                    ],
                ),
                (
                    "runtime_independence",
                    [
                        python,
                        "tools/test_sdlc_600_rls_runtime_independence.py",
                        "--root",
                        str(root),
                        "--json-out",
                        str(log_dir / "runtime_independence.json"),
                    ],
                ),
            ]
        )

    results = [
        run_step(root, name, argv, log_dir)
        for name, argv in steps
    ]
    results.append(static_scan(root, log_dir))
    success = all(row["exit_code"] == 0 for row in results)
    tests_run = _tests_run(log_dir / "private_tests.log")
    tests_run += _tests_run(log_dir / "case_coverage.log")

    tracked_status_after = _git(
        root, "status", "--porcelain", "--untracked-files=no"
    )
    if tracked_status_after:
        success = False
        results.append(
            {
                "name": "tracked_worktree_unchanged",
                "argv": [
                    "git",
                    "status",
                    "--porcelain",
                    "--untracked-files=no",
                ],
                "cwd": str(root),
                "started_at": now(),
                "duration_seconds": 0.0,
                "exit_code": 1,
                "log_path": None,
                "log_sha256": digest(tracked_status_after),
                "result": "FAIL",
                "details": redact(tracked_status_after),
            }
        )

    preweb_payload = {}
    preweb_path = log_dir / "preweb_review.json"
    if preweb_path.is_file():
        preweb_payload = json.loads(
            preweb_path.read_text(encoding="utf-8")
        )

    payload = {
        "contract": "sdlc-ai-spec/rls-provisional-delivery-validation/v1",
        "profile": profile,
        "provisional": True,
        "source_sha": source_sha,
        "observed_source_sha": observed_source_sha,
        "source_tree": source_tree,
        "source_binding": "EXACT_GIT_HEAD",
        "generated_at": now(),
        "success": success,
        "steps": results,
        "web_tests_run": tests_run,
        "preweb_review": (
            "PASS"
            if preweb_payload.get("success") is True
            else "HARD_BLOCKED"
        ),
        "final_requirements": preweb_payload.get(
            "final_requirements", []
        ),
        "critical_cases": (
            "87/87 PASS"
            if success and profile == "provisional"
            else "NOT_FULLY_EXECUTED"
            if profile == "quick"
            else "HARD_BLOCKED"
        ),
        "fixed_eval": "NOT CLAIMED",
        "closed_loop": "NOT CLAIMED",
        "real_target_effects": 0,
    }
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=("quick", "provisional"),
        required=True,
    )
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    try:
        payload = validate(
            args.profile,
            args.root,
            args.source_sha,
            args.json_out,
        )
    except Exception as exc:
        print(
            f"RLS_PROVISIONAL_VALIDATION = HARD_BLOCKED: {exc}",
            file=sys.stderr,
        )
        return 1
    if payload["success"]:
        print(
            f"RLS_PROVISIONAL_VALIDATION = PASS ({args.profile})"
        )
        print(f"WEB_TESTS = {payload['web_tests_run']}")
        print(f"RLS_PREWEB_REVIEW = {payload['preweb_review']}")
        if args.profile == "provisional":
            print("RLS_PROVISIONAL_CASES = 87/87")
        print("RLS_CLOSED_LOOP = NOT CLAIMED")
        print("REAL_TARGET_EFFECTS = 0")
        return 0
    failed = [
        row["name"]
        for row in payload["steps"]
        if row["exit_code"] != 0
    ]
    print(
        "RLS_PROVISIONAL_VALIDATION = HARD_BLOCKED",
        file=sys.stderr,
    )
    print("FAILED_STEPS = " + ",".join(failed), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
