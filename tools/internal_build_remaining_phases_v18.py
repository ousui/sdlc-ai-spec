#!/usr/bin/env python3
"""Build validated stacked IMP, VFY, RLS and integration candidate refs.

Formal refs are not changed here. Each candidate is committed only after its
own deterministic gates and complete repository regression succeed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]).resolve()
RESULT = Path(sys.argv[2]).resolve()
FROZEN_PLN = "a12382c2d0f0dc6ca54021b4fec26d5874eb169f"
WORK_ROOT = Path("/tmp/remaining-phases-v18-work")


def run(command: list[str], cwd: Path, timeout: int = 3600, check: bool = False) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONWARNINGS": "default",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout[-10000:]}\n"
            f"stderr:\n{completed.stderr[-10000:]}"
        )
    return completed


def copy_path(source: Path, destination: Path) -> None:
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    elif destination.is_dir():
        shutil.rmtree(destination)
    elif destination.exists():
        destination.unlink()


def overlay_selected(destination: Path, prefixes: Iterable[str], exact: Iterable[str] = ()) -> None:
    prefixes = tuple(prefixes)
    exact = set(exact)
    source_files = {
        path.relative_to(SOURCE)
        for path in SOURCE.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    destination_files = {
        path.relative_to(destination)
        for path in destination.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    for relative in sorted(source_files | destination_files):
        text = relative.as_posix()
        if text.startswith(".github/workflows/") or text.startswith(".github/patches/"):
            continue
        if text == ".remaining-phases-patch-manifest.json":
            continue
        if text not in exact and not any(text.startswith(prefix) for prefix in prefixes):
            continue
        copy_path(SOURCE / relative, destination / relative)


def restore_workflows(destination: Path, parent: str) -> None:
    run(["git", "restore", f"--source={parent}", "--", ".github/workflows"], destination, check=True)
    for relative in (".github/patches", ".remaining-phases-patch-manifest.json"):
        path = destination / relative
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def phase_required_paths(phase: str) -> tuple[str, ...]:
    index = {"IMP": "400", "VFY": "500", "RLS": "600"}[phase]
    slug = phase.lower()
    return (
        f"skills/sdlc-{index}-{slug}/SKILL.md",
        f"skills/sdlc-{index}-{slug}/scripts/runtime.py",
        f"skills/sdlc-{index}-{slug}/references/source-lock.json",
        f"tools/validate_sdlc_{index}_{slug}_source_lock.py",
        f"tools/test_sdlc_{index}_{slug}_runtime_independence.py",
        f"tests/evals/run_sdlc_{index}_{slug}_eval.py",
    )


def validate_stage(destination: Path, phases: tuple[str, ...], rounds: int = 1) -> list[dict[str, object]]:
    for phase in phases:
        missing = [path for path in phase_required_paths(phase) if not (destination / path).is_file()]
        if missing:
            raise RuntimeError(f"{phase} required paths are missing: {missing}")
    commands: list[list[str]] = [
        ["python3", "-m", "compileall", "-q", "packages", "scripts", "skills"],
        ["python3", "tools/validate_runtime_contracts.py"],
        ["python3", "tools/validate_skill_interfaces.py"],
        ["python3", "tools/validate_lifecycle_query.py"],
        ["python3", "tools/validate_sdlc_status.py"],
        ["python3", "tools/validate_sdlc_300_pln_source_lock.py"],
        ["python3", "tools/test_sdlc_300_pln_runtime_independence.py"],
        ["python3", "tests/evals/run_sdlc_300_pln_eval.py"],
    ]
    for phase in phases:
        index = {"IMP": "400", "VFY": "500", "RLS": "600"}[phase]
        slug = phase.lower()
        commands.extend(
            (
                ["python3", f"tools/validate_sdlc_{index}_{slug}_source_lock.py"],
                ["python3", f"tools/test_sdlc_{index}_{slug}_runtime_independence.py"],
                ["python3", f"tests/evals/run_sdlc_{index}_{slug}_eval.py"],
            )
        )
    logs: list[dict[str, object]] = []
    for round_number in range(1, rounds + 1):
        for command in commands + [["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]]:
            completed = run(command, destination, timeout=7200)
            row = {
                "round": round_number,
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout[-10000:],
                "stderr": completed.stderr[-10000:],
            }
            logs.append(row)
            if completed.returncode != 0:
                raise RuntimeError(json.dumps(row, ensure_ascii=False, indent=2))
    return logs


def prepare_worktree(name: str, parent: str) -> Path:
    destination = WORK_ROOT / name
    if destination.exists():
        run(["git", "worktree", "remove", "--force", str(destination)], ROOT)
        shutil.rmtree(destination, ignore_errors=True)
    run(["git", "worktree", "add", "--detach", str(destination), parent], ROOT, check=True)
    run(["git", "config", "user.name", "SHUAI.W"], destination, check=True)
    run(["git", "config", "user.email", "x@ousui.org"], destination, check=True)
    return destination


def commit_candidate(destination: Path, message: str, branch: str) -> str:
    run(["git", "add", "-A"], destination, check=True)
    changed = run(["git", "diff", "--cached", "--name-only"], destination, check=True).stdout.splitlines()
    if not changed:
        raise RuntimeError(f"{branch} contains no changes")
    workflow_changes = [path for path in changed if path.startswith(".github/workflows/")]
    if workflow_changes:
        raise RuntimeError(f"workflow changes leaked into {branch}: {workflow_changes}")
    run(["git", "diff", "--cached", "--check"], destination, check=True)
    run(["git", "commit", "-m", message], destination, check=True)
    head = run(["git", "rev-parse", "HEAD"], destination, check=True).stdout.strip()
    run(["git", "branch", "-f", branch, head], ROOT, check=True)
    run(["git", "push", "--force", "origin", f"{head}:refs/heads/{branch}"], ROOT, timeout=600, check=True)
    return head


def build_imp() -> tuple[str, list[dict[str, object]]]:
    destination = prepare_worktree("imp", FROZEN_PLN)
    overlay_selected(
        destination,
        prefixes=(
            "packages/sdlc_claim_provider/",
            "packages/sdlc_execution_effects/",
            "packages/sdlc_resource/",
            "packages/sdlc_phasekit/",
            "packages/sdlc_lifecycle/",
            "packages/sdlc_runtime/",
            "skills/_shared/",
            "skills/sdlc-400-imp/",
            "scripts/",
            "tests/late_foundations/",
            "tests/skill_imp/",
            "tests/lifecycle/",
            "tests/runtime/",
        ),
        exact=(
            "tests/__init__.py",
            "tests/evals/__init__.py",
            "tests/evals/late_phase_eval.py",
            "tests/evals/run_sdlc_400_imp_eval.py",
            "tools/validate_late_phase_source_lock.py",
            "tools/test_late_phase_runtime_independence.py",
            "tools/validate_sdlc_400_imp_source_lock.py",
            "tools/test_sdlc_400_imp_runtime_independence.py",
            "tools/validate_runtime_contracts.py",
            "tools/validate_skill_interfaces.py",
            "tools/validate_lifecycle_query.py",
            "tools/validate_sdlc_status.py",
        ),
    )
    restore_workflows(destination, FROZEN_PLN)
    logs = validate_stage(destination, ("IMP",))
    head = commit_candidate(destination, "feat(imp): implement deterministic execution phase", "internal/candidate-imp-v18")
    return head, logs


def build_vfy(parent: str) -> tuple[str, list[dict[str, object]]]:
    destination = prepare_worktree("vfy", parent)
    overlay_selected(
        destination,
        prefixes=("skills/sdlc-500-vfy/", "tests/skill_vfy/", "tests/lifecycle/"),
        exact=(
            "tests/evals/run_sdlc_500_vfy_eval.py",
            "tools/validate_sdlc_500_vfy_source_lock.py",
            "tools/test_sdlc_500_vfy_runtime_independence.py",
        ),
    )
    restore_workflows(destination, parent)
    logs = validate_stage(destination, ("IMP", "VFY"))
    head = commit_candidate(destination, "feat(vfy): implement deterministic verification phase", "internal/candidate-vfy-v18")
    return head, logs


def build_rls(parent: str) -> tuple[str, list[dict[str, object]]]:
    destination = prepare_worktree("rls", parent)
    overlay_selected(
        destination,
        prefixes=("skills/sdlc-600-rls/", "tests/skill_rls/", "tests/lifecycle/"),
        exact=(
            "tests/evals/run_sdlc_600_rls_eval.py",
            "tools/validate_sdlc_600_rls_source_lock.py",
            "tools/test_sdlc_600_rls_runtime_independence.py",
        ),
    )
    restore_workflows(destination, parent)
    logs = validate_stage(destination, ("IMP", "VFY", "RLS"))
    head = commit_candidate(destination, "feat(rls): implement deterministic release phase", "internal/candidate-rls-v18")
    return head, logs


def install_real_project_runner(destination: Path) -> None:
    completed = run(
        ["git", "show", "origin/internal/real-project-validation-v13:tools/real_project_validation_v13.py"],
        ROOT,
    )
    if completed.returncode != 0:
        raise RuntimeError("preserved real-project validator is unavailable")
    path = destination / "tools/run_real_project_validation.py"
    path.write_text(completed.stdout, encoding="utf-8")
    path.chmod(0o755)
    text = path.read_text(encoding="utf-8")
    old = 'if completed.returncode != 0:\n        fallback = ["git", "clone", "--depth", "1"]'
    new = 'if completed.returncode != 0:\n        shutil.rmtree(destination, ignore_errors=True)\n        fallback = ["git", "clone", "--depth", "1"]'
    if old in text:
        text = text.replace(old, new, 1)
    old = '''if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):\n        if not value:\n            return ["<empty>"]\n        return [structural_shape(value[0], key=key)]'''
    new = '''if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):\n        if not value:\n            return ["<empty>"]\n        if key is None:\n            return [structural_shape(item, key=key) for item in value]\n        return [structural_shape(value[0], key=key)]'''
    if old in text:
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    run(["python3", "-m", "py_compile", str(path.relative_to(destination))], destination, check=True)


def validate_real_project_report(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract") != "sdlc-ai-spec/real-project-validation/v1":
        raise RuntimeError("unexpected real-project validation contract")
    if payload.get("result") != "PASS":
        raise RuntimeError("real-project validation did not pass")
    rows = payload.get("projects")
    if not isinstance(rows, list) or len(rows) != 5:
        raise RuntimeError("real-project validation must contain five scenarios")
    projects = {row.get("project") for row in rows}
    if projects != {"SpringGear", "gin-vue-admin", "yudao-cloud"}:
        raise RuntimeError(f"unexpected project set: {projects}")
    yudao = {row.get("scenario") for row in rows if row.get("project") == "yudao-cloud"}
    if yudao != {
        "mariadb-driver-adaptation",
        "one-character-page-hotfix",
        "i18n-scaffold-without-translations",
    }:
        raise RuntimeError(f"unexpected yudao-cloud scenarios: {yudao}")
    if len({row.get("business_digest") for row in rows}) != 5:
        raise RuntimeError("business digests are not scenario-specific")
    return payload


def build_integration(parent: str, stage_heads: dict[str, str]) -> tuple[str, list[dict[str, object]], dict[str, object]]:
    destination = prepare_worktree("integration", parent)
    overlay_selected(destination, prefixes=("tests/system_integration/",))
    install_real_project_runner(destination)
    report_directory = destination / "docs/plugin-development/final-validation"
    report_directory.mkdir(parents=True, exist_ok=True)
    first_path = report_directory / "real-project-validation.json"
    first = run(
        ["python3", "tools/run_real_project_validation.py", "--ci", "--output", str(first_path)],
        destination,
        timeout=10800,
    )
    if first.returncode != 0:
        raise RuntimeError(f"real-project validation failed:\n{first.stdout[-10000:]}\n{first.stderr[-10000:]}")
    first_payload = validate_real_project_report(first_path)
    logs = validate_stage(destination, ("IMP", "VFY", "RLS"), rounds=3)
    second_path = WORK_ROOT / "real-project-validation-repeat.json"
    second = run(
        ["python3", "tools/run_real_project_validation.py", "--ci", "--output", str(second_path)],
        destination,
        timeout=10800,
    )
    if second.returncode != 0:
        raise RuntimeError(f"repeat real-project validation failed:\n{second.stdout[-10000:]}\n{second.stderr[-10000:]}")
    second_payload = validate_real_project_report(second_path)
    if first_payload.get("structure_signature") != second_payload.get("structure_signature"):
        raise RuntimeError("real-project structural signature is unstable")
    main_sha = run(["git", "rev-parse", "origin/main"], ROOT, check=True).stdout.strip()
    if main_sha != "0c38135e3e8bdad0d60d674c93ad42078e880134":
        raise RuntimeError(f"main moved unexpectedly: {main_sha}")
    (report_directory / "remaining-phases-v2.md").write_text(
        "# Remaining Phases V2 — Closed-loop Validation\n\n"
        f"- PLN: `{FROZEN_PLN}`\n"
        f"- IMP: `{stage_heads['imp']}`\n"
        f"- VFY: `{stage_heads['vfy']}`\n"
        f"- RLS: `{stage_heads['rls']}`\n"
        "- deterministic full repository regression: three consecutive passes\n"
        "- repository-grounded acceptance: PASS\n"
        "- SpringGear and gin-vue-admin: independent complete lifecycle runs\n"
        "- yudao-cloud: MariaDB adaptation, one-character hotfix, and i18n scaffold without translations\n"
        f"- main remained `{main_sha}`\n\n"
        "No merge to main was performed.\n",
        encoding="utf-8",
    )
    restore_workflows(destination, parent)
    head = commit_candidate(
        destination,
        "test(integration): close remaining phases with real-project acceptance",
        "internal/candidate-integration-v18",
    )
    evidence = {
        "first_structure_signature": first_payload.get("structure_signature"),
        "second_structure_signature": second_payload.get("structure_signature"),
        "projects": [
            {"project": row.get("project"), "scenario": row.get("scenario"), "business_digest": row.get("business_digest")}
            for row in first_payload["projects"]
        ],
    }
    return head, logs, evidence


def main() -> int:
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    WORK_ROOT.mkdir(parents=True)
    run(["git", "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--prune"], ROOT, timeout=600, check=True)
    if run(["git", "rev-parse", "origin/main"], ROOT, check=True).stdout.strip() != "0c38135e3e8bdad0d60d674c93ad42078e880134":
        raise RuntimeError("main is not the approved frozen SHA")
    if run(["git", "rev-parse", "origin/impl/pln-v2"], ROOT, check=True).stdout.strip() != FROZEN_PLN:
        raise RuntimeError("PLN is not the approved frozen SHA")

    result: dict[str, object] = {"contract": "sdlc-ai-spec/internal-candidate-stack/v18"}
    imp, imp_logs = build_imp()
    result["imp"] = {"sha": imp, "gates": imp_logs}
    vfy, vfy_logs = build_vfy(imp)
    result["vfy"] = {"sha": vfy, "parent": imp, "gates": vfy_logs}
    rls, rls_logs = build_rls(vfy)
    result["rls"] = {"sha": rls, "parent": vfy, "gates": rls_logs}
    integration, integration_logs, evidence = build_integration(
        rls, {"imp": imp, "vfy": vfy, "rls": rls}
    )
    result["integration"] = {
        "sha": integration,
        "parent": rls,
        "gates": integration_logs,
        "real_project": evidence,
    }
    result["result"] = "PASS"
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
