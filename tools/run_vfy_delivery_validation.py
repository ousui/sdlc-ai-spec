#!/usr/bin/env python3
"""Fail-closed exact-SHA controller for VFY quick/phase/full/external/attest."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("quick", "phase", "full", "external", "attest")
RETRY_DELAYS = (2, 5)
TRANSIENT_NETWORK = re.compile(
    r"(?:temporary failure in name resolution|name or service not known|"
    r"could not resolve host|nodename nor servname provided|"
    r"the requested url returned error:\s*(?:502|503|504)\b|"
    r"http(?: response)?\s*(?:502|503|504)\b|"
    r"(?:502|503|504)\s+(?:bad gateway|service unavailable|gateway timeout))",
    re.IGNORECASE,
)
EXPECTED_SUBJECT = "feat(vfy): implement deterministic verification phase"


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def git(*arguments: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=60,
        env={
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        },
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(arguments)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


PYTHON_CHECK = r'''
import ast
import importlib.util
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
base, source = sys.argv[1:3]
changed = subprocess.check_output(
    ["git", "diff", "--name-only", f"{base}..{source}"], text=True
).splitlines()
files = [root / name for name in changed if name.endswith(".py")]
for path in files:
    if not path.is_file():
        raise SystemExit(f"missing changed Python path: {path}")
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
scripts = root / "skills/sdlc-500-vfy/scripts"
sys.path[:0] = [str(root), str(scripts)]
for path in sorted(scripts.glob("vfy_*.py")):
    __import__(path.stem)
runtime = scripts / "runtime.py"
spec = importlib.util.spec_from_file_location("vfy_quick_runtime", runtime)
if spec is None or spec.loader is None:
    raise SystemExit("VFY Runtime import spec unavailable")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(f"AST={len(files)} VFY_IMPORTS=PASS")
'''.strip()


JSON_CHECK = r'''
import json
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
base, source = sys.argv[1:3]
changed = subprocess.check_output(
    ["git", "diff", "--name-only", f"{base}..{source}"], text=True
).splitlines()
files = [root / name for name in changed if name.endswith(".json")]
for path in files:
    if not path.is_file():
        raise SystemExit(f"missing changed JSON path: {path}")
    json.loads(path.read_text(encoding="utf-8"))
print(f"JSON={len(files)} PASS")
'''.strip()


PATH_CHECK = r'''
from pathlib import Path
import subprocess
import sys

base, source = sys.argv[1:3]
changed = subprocess.check_output(
    ["git", "diff", "--name-only", f"{base}..{source}"], text=True
).splitlines()
prefixes = (
    "skills/sdlc-500-vfy/",
    "tests/skill_vfy/",
)
exact = {
    "packages/sdlc_lifecycle/query_vfy.py",
    "packages/sdlc_lifecycle/__init__.py",
    "packages/sdlc_lifecycle/models.py",
    "packages/sdlc_lifecycle/CONTRACT.md",
    "skills/sdlc-status/SKILL.md",
    "skills/sdlc-status/references/contract.md",
    "skills/sdlc-status/references/status-result.schema.json",
    "skills/sdlc-status/scripts/runtime.py",
    "skills/sdlc-status/scripts/vfy_projection.py",
    "tests/evals/run_sdlc_500_vfy_eval.py",
    "tests/evals/sdlc_500_vfy_cases.json",
    "tests/evals/test_sdlc_500_vfy_case_coverage.py",
    "tests/evals/vfy_case_harness.py",
    "tests/evals/vfy_case_harness_hardened.py",
    "tests/system_integration/test_external_vfy_integration.py",
    "tests/skill_imp/test_lifecycle.py",
    "tests/skill_status/test_imp.py",
    "tools/validate_sdlc_500_vfy_case_coverage.py",
    "tools/validate_sdlc_500_vfy_source_lock.py",
    "tools/test_sdlc_500_vfy_runtime_independence.py",
    "tools/review_sdlc_500_vfy_implementation.py",
    "tools/run_external_vfy_integration.py",
    "tools/run_vfy_delivery_validation.py",
}
unknown = [name for name in changed if name not in exact and not name.startswith(prefixes)]
forbidden = [
    name for name in changed
    if name.startswith(".github/")
    or "sdlc-600-rls" in name
    or "/skill_rls/" in name
    or name.startswith("tests/skill_rls/")
    or (name.startswith("tools/") and "rls" in Path(name).name.lower())
    or "/evidence/" in name
]
if unknown:
    raise SystemExit("unknown Subject paths: " + ", ".join(unknown))
if forbidden:
    raise SystemExit("forbidden Workflow/RLS/Evidence paths: " + ", ".join(forbidden))
print(f"WHITELIST={len(changed)} NO_WORKFLOW_RLS_EVIDENCE=PASS")
'''.strip()


REVIEW_CHECK = r'''
from pathlib import Path
import sys

path = Path(sys.argv[1])
source, base = sys.argv[2:4]
if not path.is_file():
    raise SystemExit(f"missing independent review: {path}")
text = path.read_text(encoding="utf-8")
required = (
    "VFY_DESIGN_REVIEW = PASS",
    f"Implementation Subject SHA = {source}",
    f"Design Head SHA = {base}",
    "Blocker = 0",
    "Major = 0",
)
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit("independent review is incomplete: " + ", ".join(missing))
print("INDEPENDENT_REVIEW=PASS Blocker=0 Major=0")
'''.strip()


def _spec(name: str, command: Sequence[str], *, retryable: bool = False) -> dict[str, Any]:
    return {"name": name, "command": list(command), "retryable": retryable}


def _quick_plan(source_sha: str, base_sha: str, prefix: str = "") -> list[dict[str, Any]]:
    authority = "docs/plugin-development/work-items/sdlc-500-vfy"
    return [
        _spec(
            prefix + "diff_check",
            ["git", "diff", "--check", f"{base_sha}..{source_sha}"],
        ),
        _spec(
            prefix + "python_syntax_import",
            [sys.executable, "-c", PYTHON_CHECK, base_sha, source_sha],
        ),
        _spec(
            prefix + "json_parse",
            [sys.executable, "-c", JSON_CHECK, base_sha, source_sha],
        ),
        _spec(
            prefix + "skill_interface",
            [sys.executable, "tools/validate_skill_interfaces.py"],
        ),
        _spec(
            prefix + "source_lock_structure",
            [sys.executable, "tools/validate_sdlc_500_vfy_source_lock.py"],
        ),
        _spec(
            prefix + "critical_case_coverage",
            [sys.executable, "tools/validate_sdlc_500_vfy_case_coverage.py"],
        ),
        _spec(
            prefix + "focused_deterministic_tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "tests.skill_vfy.test_runtime",
                "tests.skill_vfy.test_source_lock",
                "tests.evals.test_sdlc_500_vfy_case_coverage",
            ],
        ),
        _spec(
            prefix + "web_review_guard",
            [sys.executable, "tools/review_sdlc_500_vfy_implementation.py"],
        ),
        _spec(
            prefix + "subject_path_whitelist",
            [sys.executable, "-c", PATH_CHECK, base_sha, source_sha],
        ),
        _spec(
            prefix + "design_authority_bytes",
            [
                "git",
                "diff",
                "--quiet",
                f"{base_sha}..{source_sha}",
                "--",
                f"{authority}/DESIGN.md",
                f"{authority}/EVAL-PLAN.md",
                f"{authority}/goal",
            ],
        ),
    ]


def _phase_plan(json_out: Path, prefix: str = "") -> list[dict[str, Any]]:
    fixed = json_out.with_name(json_out.stem + "-fixed-eval.json")
    return [
        _spec(
            prefix + "vfy_suite",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/skill_vfy",
                "-p",
                "test_*.py",
            ],
        ),
        _spec(
            prefix + "fixed_eval_80",
            [
                sys.executable,
                "tests/evals/run_sdlc_500_vfy_eval.py",
                "--json-out",
                str(fixed),
            ],
        ),
        _spec(
            prefix + "lifecycle_status_regression",
            [
                sys.executable,
                "-m",
                "unittest",
                "tests.skill_vfy.test_lifecycle",
                "tests.skill_imp.test_lifecycle",
                "tests.skill_status.test_imp",
            ],
        ),
    ]


def _full_plan(
    source_sha: str,
    base_sha: str,
    prefix: str = "",
) -> list[dict[str, Any]]:
    authority = "docs/plugin-development/work-items/sdlc-500-vfy"
    return [
        _spec(
            prefix + "skill_interface",
            [sys.executable, "tools/validate_skill_interfaces.py"],
        ),
        _spec(
            prefix + "final_source_lock",
            [
                sys.executable,
                "tools/validate_sdlc_500_vfy_source_lock.py",
                "--require-final",
            ],
        ),
        _spec(
            prefix + "installed_runtime_independence",
            [sys.executable, "tools/test_sdlc_500_vfy_runtime_independence.py"],
        ),
        _spec(
            prefix + "runtime_contract_boundary",
            [sys.executable, "tools/validate_runtime_contracts.py"],
        ),
        _spec(
            prefix + "web_review_guard",
            [sys.executable, "tools/review_sdlc_500_vfy_implementation.py"],
        ),
        _spec(
            prefix + "full_repository_regression",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
            ],
        ),
        _spec(
            prefix + "subject_path_whitelist",
            [sys.executable, "-c", PATH_CHECK, base_sha, source_sha],
        ),
        _spec(
            prefix + "design_authority_bytes",
            [
                "git",
                "diff",
                "--quiet",
                f"{base_sha}..{source_sha}",
                "--",
                f"{authority}/DESIGN.md",
                f"{authority}/EVAL-PLAN.md",
                f"{authority}/goal",
            ],
        ),
    ]


def _external_paths(profile: str, json_out: Path) -> tuple[Path, Path]:
    if profile == "external":
        return json_out.with_name("vfy-real-projects.json"), json_out.with_name(
            "vfy-real-projects.log"
        )
    return json_out.with_name(json_out.stem + "-real-projects.json"), json_out.with_name(
        json_out.stem + "-real-projects.log"
    )


def _external_plan(
    profile: str,
    source_sha: str,
    base_sha: str,
    json_out: Path,
    prefix: str = "",
) -> list[dict[str, Any]]:
    external_json, external_log = _external_paths(profile, json_out)
    return [
        _spec(
            prefix + "two_exact_external_projects",
            [
                sys.executable,
                "tools/run_external_vfy_integration.py",
                "--source-sha",
                source_sha,
                "--base-sha",
                base_sha,
                "--json-out",
                str(external_json),
                "--log-out",
                str(external_log),
            ],
            retryable=True,
        )
    ]


def command_plan(
    profile: str,
    *,
    source_sha: str,
    base_sha: str,
    json_out: Path,
) -> list[dict[str, Any]]:
    if profile == "quick":
        return _quick_plan(source_sha, base_sha)
    if profile == "phase":
        return _phase_plan(json_out)
    if profile == "full":
        return _full_plan(source_sha, base_sha)
    if profile == "external":
        return _external_plan(profile, source_sha, base_sha, json_out)
    review = json_out.parent / "vfy-design-review.md"
    return [
        *_quick_plan(source_sha, base_sha, "quick__"),
        *_phase_plan(json_out, "phase__"),
        *_full_plan(source_sha, base_sha, "full__"),
        *_external_plan(profile, source_sha, base_sha, json_out, "external__"),
        _spec(
            "independent_review",
            [sys.executable, "-c", REVIEW_CHECK, str(review), source_sha, base_sha],
        ),
    ]


def _run_process(command: Sequence[str]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=7200,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "NO_COLOR": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_OPTIONAL_LOCKS": "0",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            },
        )
        return completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout or ""
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr or ""
        return 124, stdout, stderr + "\ncommand timed out"


def run_one(
    specification: Mapping[str, Any],
    *,
    logs_dir: Path,
    source_sha: str,
    base_sha: str,
) -> dict[str, Any]:
    name = str(specification["name"])
    command = [str(item) for item in specification["command"]]
    retryable = bool(specification.get("retryable"))
    logs_dir.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 4 if retryable else 2):
        delay = 0 if attempt == 1 else RETRY_DELAYS[attempt - 2]
        if delay:
            time.sleep(delay)
        started_at = utc_now()
        started = time.monotonic()
        exit_code, stdout, stderr = _run_process(command)
        finished_at = utc_now()
        stdout_path = logs_dir / f"{name}-attempt-{attempt}.stdout.log"
        stderr_path = logs_dir / f"{name}-attempt-{attempt}.stderr.log"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        stdout_reference = stdout_path.relative_to(logs_dir.parent).as_posix()
        stderr_reference = stderr_path.relative_to(logs_dir.parent).as_posix()
        combined = stdout + ("\n" if stdout and stderr else "") + stderr
        row = {
            "attempt": attempt,
            "delay_before_seconds": delay,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "exit_code": exit_code,
            "stdout_log": stdout_reference,
            "stdout_sha256": "sha256:"
            + hashlib.sha256(stdout_path.read_bytes()).hexdigest(),
            "stderr_log": stderr_reference,
            "stderr_sha256": "sha256:"
            + hashlib.sha256(stderr_path.read_bytes()).hexdigest(),
            "transient_network_failure": bool(
                exit_code != 0 and retryable and TRANSIENT_NETWORK.search(combined)
            ),
        }
        attempts.append(row)
        if exit_code == 0:
            break
        if not row["transient_network_failure"] or attempt == 3:
            break
    final = attempts[-1]
    return {
        "name": name,
        "command": command,
        "cwd": ".",
        "source_sha": source_sha,
        "base_sha": base_sha,
        "status": "PASS" if final["exit_code"] == 0 else "FAIL",
        "exit_code": final["exit_code"],
        "started_at": attempts[0]["started_at"],
        "finished_at": final["finished_at"],
        "duration_ms": sum(item["duration_ms"] for item in attempts),
        "attempts": attempts,
        "stdout_log": final["stdout_log"],
        "stdout_sha256": final["stdout_sha256"],
        "stderr_log": final["stderr_log"],
        "stderr_sha256": final["stderr_sha256"],
    }


def _full_sha(value: str, name: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError(f"{name} must be a full lowercase commit SHA")


def validate_source(source_sha: str, base_sha: str) -> dict[str, Any]:
    _full_sha(source_sha, "--source-sha")
    _full_sha(base_sha, "--base-sha")
    git("cat-file", "-e", f"{source_sha}^{{commit}}")
    git("cat-file", "-e", f"{base_sha}^{{commit}}")
    head = git("rev-parse", "HEAD")
    if head != source_sha:
        raise ValueError(f"exact source mismatch: expected {source_sha}, got {head}")
    parents = git("rev-list", "--parents", "-n", "1", source_sha).split()
    if parents != [source_sha, base_sha]:
        raise ValueError(
            f"Implementation Subject must have exactly Design Head as parent: {parents}"
        )
    subject = git("show", "-s", "--format=%s", source_sha)
    if subject != EXPECTED_SUBJECT:
        raise ValueError(f"unexpected Implementation Subject: {subject}")
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise ValueError("exact Subject worktree is not clean")
    design_ref = git("rev-parse", "refs/remotes/origin/design/sdlc-500-vfy-goal")
    if design_ref != base_sha:
        raise ValueError(
            f"local origin/design/sdlc-500-vfy-goal drifted: {design_ref}"
        )
    branch = git("branch", "--show-current")
    if branch == "main":
        raise ValueError("validation must not run from main")
    return {
        "head": head,
        "tree": git("rev-parse", f"{source_sha}^{{tree}}"),
        "parent": base_sha,
        "subject": subject,
        "clean": True,
        "branch": branch or "DETACHED",
        "origin_design_head": design_ref,
        "local_main_sha": git("rev-parse", "refs/heads/main"),
        "origin_main_sha": git("rev-parse", "refs/remotes/origin/main"),
    }


def _assert_fixed_eval(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not (
        payload.get("status") == "PASS"
        and payload.get("expected_full_count") == 80
        and payload.get("selected_count") == 80
        and payload.get("passed") == 80
        and payload.get("failed") == 0
        and payload.get("skipped") == 0
        and payload.get("expected_failures") == 0
        and payload.get("complete_fixed_eval") is True
    ):
        raise ValueError(f"fixed Eval is not exact 80/80: {payload}")
    return {
        "path": path.name,
        "status": "PASS",
        "passed": 80,
        "skipped": 0,
        "expected_failures": 0,
        "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def _valid_external_project(
    row: Mapping[str, Any],
    *,
    repository: str,
    expected_sha: str,
) -> bool:
    receipts = row.get("phase_execution_receipts")
    references = row.get("references")
    phases = row.get("phases")
    claim = row.get("imp_claim")
    imp_result = row.get("imp_result")
    subjects = row.get("vfy_subject_set")
    method_results = row.get("method_results")
    evidence = row.get("evidence")
    cleanup = row.get("cleanup_assertions")
    commands = row.get("command_receipts")
    confirmation = row.get("final_confirmation")
    lifecycle = row.get("lifecycle")
    status_projection = row.get("status_projection")
    expected_cleanup = {
        "head_unchanged",
        "refs_unchanged",
        "status_bytes_identical",
        "tracked_untracked_digest_identical",
        "file_mode_identical",
        "sdlc_removed",
        "temporary_authority_removed",
        "temporary_evidence_removed",
    }
    if not (
        isinstance(receipts, list)
        and isinstance(references, Mapping)
        and isinstance(phases, Mapping)
        and isinstance(claim, Mapping)
        and isinstance(imp_result, Mapping)
        and isinstance(subjects, list)
        and isinstance(method_results, list)
        and isinstance(evidence, list)
        and isinstance(cleanup, Mapping)
        and isinstance(commands, list)
        and isinstance(confirmation, Mapping)
        and isinstance(lifecycle, Mapping)
        and isinstance(status_projection, Mapping)
    ):
        return False
    subject_references = {
        item.get("reference") for item in subjects if isinstance(item, Mapping)
    }
    return bool(
        row.get("name")
        and row.get("repository") == repository
        and row.get("expected_sha") == expected_sha
        and row.get("actual_sha") == expected_sha
        and row.get("status") == "PASS"
        and [item.get("phase") for item in receipts if isinstance(item, Mapping)]
        == ["CTX", "REQ", "DSN", "PLN", "IMP", "VFY"]
        and len(receipts) == 6
        and all(
            item.get("exit_code") == 0
            and item.get("execution") == "in_process_runtime_handler"
            and _is_sha256(item.get("output_digest"))
            and item.get("started_at")
            and item.get("finished_at")
            for item in receipts
        )
        and set(references) == {"CTX", "REQ", "DSN", "PLN", "IMP", "VFY"}
        and all(isinstance(value, str) and "@" in value for value in references.values())
        and set(phases) == set(references)
        and claim.get("state") == "completed"
        and claim.get("artifact_reference") == references["IMP"]
        and imp_result.get("result_reference") in subject_references
        and _is_sha256(imp_result.get("result_digest"))
        and len(subjects) >= 1
        and all(
            isinstance(item, Mapping)
            and item.get("current_valid") is True
            and item.get("dependency_chain_valid") is True
            and item.get("claim_state") == "completed"
            and item.get("imp_revision_state") == "frozen"
            and _is_sha256(item.get("result_digest"))
            for item in subjects
        )
        and row.get("method_types") == ["inspection", "analysis"]
        and len(method_results) == 2
        and all(
            isinstance(item, Mapping)
            and item.get("result") == "pass"
            and item.get("evidence_references")
            for item in method_results
        )
        and len(evidence) == 2
        and all(isinstance(item, Mapping) and item.get("result") == "pass" for item in evidence)
        and isinstance(row.get("con_ver"), Mapping)
        and row["con_ver"].get("conclusion") == "pass"
        and isinstance(row.get("con_val"), Mapping)
        and row["con_val"].get("conclusion") == "pass"
        and row.get("product_result") == "pass"
        and row.get("artifact_gate") == "pass"
        and row.get("rls_applicability") == "n/a"
        and row.get("rls_ready") is False
        and row.get("check_read_only") is True
        and confirmation.get("mode") == "delegated"
        and confirmation.get("manual_or_hybrid_evidence") is False
        and lifecycle.get("overall_state") == "complete"
        and isinstance(lifecycle.get("vfy_projection"), Mapping)
        and lifecycle["vfy_projection"].get("artifact_reference") == references["VFY"]
        and status_projection.get("artifact_reference") == references["VFY"]
        and set(cleanup) == expected_cleanup
        and all(value is True for value in cleanup.values())
        and [item.get("kind") for item in commands if isinstance(item, Mapping)]
        == ["clone", "checkout"]
        and len(commands) == 2
        and all(
            item.get("exit_code") == 0
            and item.get("cwd") == "."
            and isinstance(item.get("command"), list)
            and item.get("started_at")
            and item.get("finished_at")
            and isinstance(item.get("duration_ms"), int)
            and _is_sha256(item.get("stdout_sha256"))
            and _is_sha256(item.get("stderr_sha256"))
            for item in commands
        )
        and row.get("remote_writes") == 0
        and row.get("dependency_installations") == 0
        and row.get("commit_push_tag_or_ref_mutations") == 0
    )


def _assert_external(path: Path, source_sha: str, base_sha: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    projects = payload.get("projects")
    expected = [(item["repository"], item["sha"]) for item in (
        {
            "repository": "ousui/springgear",
            "sha": "e855096ff19dcdb303dc4250ba19c30acd743ac7",
        },
        {
            "repository": "flipped-aurora/gin-vue-admin",
            "sha": "a6882210a80bb27e3aa5dff0b4c21aa4afe8988a",
        },
    )]
    actual = [
        (item.get("repository"), item.get("expected_sha"))
        for item in projects or []
        if isinstance(item, Mapping)
    ]
    valid = (
        payload.get("status") == "PASS"
        and payload.get("source_sha") == source_sha
        and payload.get("base_sha") == base_sha
        and actual == expected
        and len(projects or []) == 2
        and all(
            isinstance(row, Mapping)
            and _valid_external_project(
                row,
                repository=repository,
                expected_sha=sha,
            )
            for row, (repository, sha) in zip(projects or [], expected)
        )
        and payload.get("remote_writes") == 0
        and payload.get("dependency_installations") == 0
        and isinstance(payload.get("cross_project"), Mapping)
        and payload["cross_project"].get("status") == "PASS"
        and payload["cross_project"].get("semantic_subjects_distinct") is True
        and isinstance(payload.get("log"), Mapping)
        and payload["log"].get("path") == path.with_suffix(".log").name
        and _is_sha256(payload["log"].get("sha256"))
    )
    if not valid:
        raise ValueError("external evidence is incomplete or not exact-SHA bound")
    return {
        "path": path.name,
        "status": "PASS",
        "project_count": 2,
        "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def artifact_assertions(
    profile: str,
    json_out: Path,
    source_sha: str,
    base_sha: str,
) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    if profile in {"phase", "attest"}:
        assertions.append(
            _assert_fixed_eval(json_out.with_name(json_out.stem + "-fixed-eval.json"))
        )
    if profile in {"external", "attest"}:
        external_path, _ = _external_paths(profile, json_out)
        assertions.append(_assert_external(external_path, source_sha, base_sha))
    return assertions


def run_validation(arguments: argparse.Namespace) -> dict[str, Any]:
    preflight = validate_source(arguments.source_sha, arguments.base_sha)
    started_at = utc_now()
    started = time.monotonic()
    logs_dir = arguments.json_out.parent / (arguments.json_out.stem + "-logs")
    results: list[dict[str, Any]] = []
    first_failure: dict[str, Any] | None = None
    for specification in command_plan(
        arguments.profile,
        source_sha=arguments.source_sha,
        base_sha=arguments.base_sha,
        json_out=arguments.json_out,
    ):
        result = run_one(
            specification,
            logs_dir=logs_dir,
            source_sha=arguments.source_sha,
            base_sha=arguments.base_sha,
        )
        results.append(result)
        if result["status"] != "PASS":
            first_failure = result
            break
    assertions: list[dict[str, Any]] = []
    postflight: dict[str, Any] | None = None
    if first_failure is None:
        try:
            assertions = artifact_assertions(
                arguments.profile,
                arguments.json_out,
                arguments.source_sha,
                arguments.base_sha,
            )
            postflight = validate_source(arguments.source_sha, arguments.base_sha)
            if (
                postflight["tree"] != preflight["tree"]
                or postflight["local_main_sha"] != preflight["local_main_sha"]
                or postflight["origin_main_sha"] != preflight["origin_main_sha"]
            ):
                raise ValueError("source tree or main refs changed during validation")
        except Exception as exc:
            first_failure = {
                "name": "artifact_or_postflight_assertion",
                "status": "FAIL",
                "error": {"type": exc.__class__.__name__, "message": str(exc)},
            }
    status = "PASS" if first_failure is None else "FAIL"
    evidence_digest = "sha256:" + hashlib.sha256(
        json.dumps(
            [
                [item["name"], item["stdout_sha256"], item["stderr_sha256"]]
                for item in results
            ],
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "contract": "sdlc-ai-spec/vfy-delivery-validation/v1",
        "profile": arguments.profile,
        "status": status,
        "source_sha": preflight["head"],
        "source_tree": preflight["tree"],
        "base_sha": arguments.base_sha,
        "integration_mode": "PREMERGE_DIRECT_DESIGN_ANCESTRY",
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_ms": int((time.monotonic() - started) * 1000),
        "preflight": preflight,
        "postflight": postflight,
        "commands": results,
        "command_count": len(results),
        "artifact_assertions": assertions,
        "first_failure": first_failure,
        "evidence_digest": evidence_digest,
        "missing_is_skip": False,
        "github_actions_authority": False,
        "main_modified": False if postflight else None,
        "workflow_created": False,
        "rls_started": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    arguments.json_out = arguments.json_out.expanduser().resolve()
    try:
        arguments.json_out.relative_to(ROOT)
    except ValueError:
        pass
    else:
        parser.error("--json-out must be outside the exact Subject worktree")
    arguments.json_out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = run_validation(arguments)
    except Exception as exc:
        report = {
            "contract": "sdlc-ai-spec/vfy-delivery-validation/v1",
            "profile": arguments.profile,
            "status": "FAIL",
            "source_sha": arguments.source_sha,
            "base_sha": arguments.base_sha,
            "integration_mode": "PREMERGE_DIRECT_DESIGN_ANCESTRY",
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "commands": [],
            "command_count": 0,
            "first_failure": {
                "name": "preflight",
                "status": "FAIL",
                "error": {"type": exc.__class__.__name__, "message": str(exc)},
            },
            "missing_is_skip": False,
            "github_actions_authority": False,
            "workflow_created": False,
            "rls_started": False,
        }
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    arguments.json_out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
