#!/usr/bin/env python3
"""Verify installed late-phase runtimes without development documents."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
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


def copy_plugin(plugin, skill):
    for relative in ('packages', 'scripts', 'skills/_shared', f'skills/{skill}'):
        shutil.copytree(ROOT / relative, plugin / relative,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def scan_runtime(plugin):
    """Check executable sources separately from prose describing forbidden actions."""
    forbidden_imports = ('tests', 'requests', 'httpx', 'socket', 'urllib.request', 'http.client', 'pip')
    for path in sorted(plugin.rglob('*')):
        relative = path.relative_to(plugin)
        if any(part in {'docs', 'tests', 'AGENTS.md', 'CLAUDE.md', 'HANDOFF.md'} for part in relative.parts):
            raise RuntimeError(f'development resource copied: {relative}')
        if path.is_symlink():
            raise RuntimeError(f'installed resource is a symlink: {relative}')
        if not path.is_file() or path.suffix not in {'.py', '.md', '.json', '.yaml', '.yml'}:
            continue
        text = path.read_text(encoding='utf-8')
        if re.search(r'docs/v1\.|docs/plugin-development/|/(?:Users|home|tmp|private/tmp|private/var/folders)/|[A-Za-z]:\\Users\\', text):
            raise RuntimeError(f'development path in installed runtime: {relative}')
        if path.suffix != '.py':
            continue
        tree = ast.parse(text, filename=str(relative))
        for node in ast.walk(tree):
            imports = ([item.name for item in node.names] if isinstance(node, ast.Import) else
                       [node.module or '', *(f'{node.module}.{item.name}' for item in node.names)]
                       if isinstance(node, ast.ImportFrom) else [])
            if any(name == prefix or name.startswith(prefix + '.')
                   for name in imports for prefix in forbidden_imports):
                raise RuntimeError(f'forbidden runtime import: {relative}:{node.lineno}')
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and 'api.github.com' in node.value:
                raise RuntimeError(f'GitHub API dependency: {relative}:{node.lineno}')
            if isinstance(node, (ast.List, ast.Tuple)):
                words = [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
                commands = {Path(word).name for word in words}
                if commands & {'curl', 'wget'} or (
                    commands & {'pip', 'pip3', 'npm', 'npx', 'mvn', 'maven', 'gradle'}
                    and commands & {'install', 'ci', 'exec', 'dependency:get', 'dependencies'}
                ) or ('git' in commands and commands & {'commit', 'push', 'merge', 'tag', 'update-ref'}):
                    raise RuntimeError(f'forbidden runtime command: {relative}:{node.lineno}')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=tuple(PHASES))
    args = parser.parse_args(argv)
    if args.phase == 'IMP':
        from test_sdlc_400_imp_runtime_independence import main as imp_main
        return imp_main()
    skill, reference = PHASES[args.phase]
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        plugin = workspace / "plugin"
        project = workspace / "project"
        outside = workspace / "cwd"
        project.mkdir()
        outside.mkdir()
        copy_plugin(plugin, skill)
        scan_runtime(plugin)
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
