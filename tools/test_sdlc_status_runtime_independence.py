#!/usr/bin/env python3
"""Run only installed Status/shared code from another cwd, without development files."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition: raise ValueError(message)


def verify(root: Path = ROOT):
    commands = []
    with tempfile.TemporaryDirectory(prefix="status-installed-") as directory:
        base = Path(directory)
        plugin, project, outside = base / "plugin", base / "project", base / "outside"
        project.mkdir(); outside.mkdir(); (plugin / "skills").mkdir(parents=True)
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "AGENTS.md", "CLAUDE.md")
        shutil.copytree(root / "packages", plugin / "packages", ignore=ignore)
        for name in ("_shared", "sdlc-status"):
            shutil.copytree(root / "skills" / name, plugin / "skills" / name, ignore=ignore)
        require(not any((plugin / name).exists() for name in ("docs", "tests", "tools", "AGENTS.md", "CLAUDE.md")), 'validation assertion failed: tools/test_sdlc_status_runtime_independence.py:25')
        require(sorted(p.name for p in (plugin / "skills").iterdir()) == ["_shared", "sdlc-status"], 'validation assertion failed: tools/test_sdlc_status_runtime_independence.py:26')
        runtime = plugin / "skills/sdlc-status/scripts/runtime.py"
        ref = "REQ-20260905000000-01@1"
        matrix = [([command], 0, "meta") for command in ("help", "version", "commands", "examples")]
        matrix += [([], 0, "not_started"), (["list"], 0, "not_started"),
                   (["inspect", "-r", ref], 2, "store_unavailable"),
                   (["auto", "-r", ref], 2, "store_unavailable"),
                   (["auto", "-r", "latest"], 2, "invalid_reference"),
                   (["inspect", "-r", ref + "#AC-001"], 2, "invalid_reference"),
                   (["auto", "--write-policy=auto"], 0, "not_started")]
        for arguments, code, state in matrix:
            target_options = [] if state == "meta" else ["-p", str(project)]
            command = [sys.executable, "-I", "-B", str(runtime), *arguments, *target_options, "-f", "json"]
            completed = subprocess.run(command, cwd=outside, input=b"", capture_output=True, timeout=20)
            require(completed.returncode == code, (arguments, completed.returncode, completed.stdout, completed.stderr))
            value = json.loads(completed.stdout)
            require(value["state"] == state and value["effective_write_policy"] == "deny", value)
            require(not list(project.iterdir()), "installed query modified the empty project")
            commands.append({"arguments": arguments, "exit_code": code, "state": state})
        (project / ".sdlc").mkdir()
        database = project / ".sdlc/store.sqlite3"
        database.write_bytes(b"intentionally-invalid-sqlite")
        before = {str(p.relative_to(project)): (p.stat().st_mode, p.read_bytes()) for p in project.rglob("*") if p.is_file()}
        completed = subprocess.run([sys.executable, "-I", "-B", str(runtime), "-p", str(project), "-f", "json"],
                                   cwd=outside, input=b"", capture_output=True, timeout=20)
        value = json.loads(completed.stdout)
        require(completed.returncode == 2 and value["ok"] is False and value["state"] == "query_failed", value)
        after = {str(p.relative_to(project)): (p.stat().st_mode, p.read_bytes()) for p in project.rglob("*") if p.is_file()}
        require(before == after and len(after) == 1, "corrupt Store or sidecar files changed")
        commands.append({"arguments": ["auto", "corrupt-store-fixture"], "exit_code": 2, "state": "query_failed"})
    return {"success": True, "commands": commands, "docs_copied": 0, "tests_copied": 0,
            "sibling_skills_copied": 0, "project_writes_during_query": 0, "native_client_behavior": "NOT_RUN"}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--json-out", type=Path); args = parser.parse_args()
    try: result = verify()
    except Exception as exc: result = {"success": False, "error": type(exc).__name__, "message": str(exc)}
    if args.json_out:
        from tools.rls_validation_support import write_json
        write_json(args.json_out, result)
    print("sdlc-status runtime independence: " + ("PASS" if result["success"] else "FAIL"))
    print("commands:", len(result.get("commands", [])))
    print("native Client behavior: NOT_RUN")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT)); raise SystemExit(main())
