#!/usr/bin/env python3
"""Verify installed late-phase runtimes without development documents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PHASES = {
    "PLN": ("sdlc-300-pln", "PLN-20990101000000-01@1"),
    "IMP": ("sdlc-400-imp", "IMP-20990101000000-01@1"),
    "VFY": ("sdlc-500-vfy", "VFY-20990101000000-01@1"),
    "RLS": ("sdlc-600-rls", "RLS-20990101000000-01@1"),
}


def run(command, *, cwd, payload=None):
    return subprocess.run(
        command,
        cwd=cwd,
        input=json.dumps(payload or {}, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )


def parsed(completed):
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"stdout is not one JSON document: {completed.stdout!r}; stderr={completed.stderr!r}"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=tuple(PHASES))
    args = parser.parse_args()
    skill, reference = PHASES[args.phase]
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        plugin = workspace / "plugin"
        project = workspace / "project"
        outside = workspace / "cwd"
        project.mkdir()
        outside.mkdir()
        (plugin / "skills").mkdir(parents=True)
        shutil.copytree(ROOT / "packages", plugin / "packages", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / "scripts", plugin / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / "skills/_shared", plugin / "skills/_shared", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / f"skills/{skill}", plugin / f"skills/{skill}", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for forbidden in ("docs", "tests", "AGENTS.md", "CLAUDE.md"):
            if (plugin / forbidden).exists():
                raise RuntimeError(f"development resource copied: {forbidden}")
        for base in (plugin / "packages", plugin / "scripts", plugin / "skills"):
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".md", ".json", ".yaml", ".yml"}:
                    continue
                text = path.read_text(encoding="utf-8")
                if "docs/v1." in text or "docs/plugin-development/" in text:
                    raise RuntimeError(f"development path in installed runtime: {path.relative_to(plugin)}")
        runtime = plugin / f"skills/{skill}/scripts/runtime.py"
        for command in ("--help", "--version", "--commands", "--examples"):
            completed = run([sys.executable, str(runtime), command, "--output=json"], cwd=outside)
            result = parsed(completed)
            if completed.returncode != 0 or not result.get("ok") or result.get("effects") != []:
                raise RuntimeError(f"meta command failed: {command}: {result}")
        before = tuple(sorted(path.relative_to(project).as_posix() for path in project.rglob("*")))
        completed = run(
            [
                sys.executable,
                str(runtime),
                "check",
                "--reference",
                reference,
                "--project-root",
                str(project),
                "--output=json",
            ],
            cwd=outside,
            payload={"inputs": {}},
        )
        result = parsed(completed)
        after = tuple(sorted(path.relative_to(project).as_posix() for path in project.rglob("*")))
        if completed.returncode == 0 or result.get("ok") is not False:
            raise RuntimeError(f"missing-store check did not fail closed: {result}")
        if before != after or (project / ".sdlc").exists():
            raise RuntimeError("read-only check modified the project")
    print(f"sdlc-{args.phase.lower()} runtime independence: PASS")
    print("development docs copied: 0")
    print("external dependencies installed: 0")
    print("project writes during read-only check: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
