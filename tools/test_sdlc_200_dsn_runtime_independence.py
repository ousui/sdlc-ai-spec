#!/usr/bin/env python3
"""Execute the DSN runtime from an installed Plugin copy without development files."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def _run(command, *, cwd, payload=None, env=None):
    return subprocess.run(
        command,
        input=(json.dumps(payload, ensure_ascii=False) if payload is not None else None),
        text=True,
        cwd=cwd,
        env=env,
        capture_output=True,
        check=False,
    )


def _json_stdout(completed):
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"stdout is not one JSON document: {completed.stdout!r}; stderr={completed.stderr!r}"
        ) from exc


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        plugin = workspace / "plugin"
        project = workspace / "project"
        outside = workspace / "unrelated-cwd"
        project.mkdir()
        outside.mkdir()
        (plugin / "skills").mkdir(parents=True)

        shutil.copytree(ROOT / "packages", plugin / "packages")
        shutil.copytree(ROOT / "scripts", plugin / "scripts")
        shutil.copytree(ROOT / "skills/_shared", plugin / "skills/_shared")
        shutil.copytree(
            ROOT / "skills/sdlc-200-dsn",
            plugin / "skills/sdlc-200-dsn",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        for forbidden in ("docs", "tests", "AGENTS.md", "CLAUDE.md"):
            if (plugin / forbidden).exists():
                print(
                    f"sdlc-200-dsn runtime independence: FAIL: copied {forbidden}",
                    file=sys.stderr,
                )
                return 1

        for root in (plugin / "skills", plugin / "packages", plugin / "scripts"):
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".md", ".json", ".yaml", ".yml"}:
                    continue
                text = path.read_text(encoding="utf-8")
                if "docs/v1." in text or "docs/plugin-development/" in text:
                    print(
                        "sdlc-200-dsn runtime independence: FAIL: development path in "
                        + str(path.relative_to(plugin)),
                        file=sys.stderr,
                    )
                    return 1

        runtime = plugin / "skills/sdlc-200-dsn/scripts/runtime.py"
        for arguments in (("--help", "--output=json"), ("--version", "--output=json")):
            completed = _run(
                [sys.executable, str(runtime), *arguments],
                cwd=outside,
            )
            result = _json_stdout(completed)
            if completed.returncode != 0 or not result.get("ok") or result.get("effects") != []:
                print(
                    f"sdlc-200-dsn runtime independence: FAIL: meta command {arguments}: {result}",
                    file=sys.stderr,
                )
                return 1

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            (
                str(plugin),
                str(plugin / "packages"),
                str(plugin / "skills/sdlc-200-dsn/scripts"),
            )
        )
        builder_code = r'''
import json
from pathlib import Path
from dsn_builder import DsnBuilder
from dsn_common import UpstreamScope

root = Path(__import__("sys").argv[1])
upstream = UpstreamScope(
    context_reference="CTX-20260901090000-01@1",
    scope_references=("REQ-20260901090000-01@1",),
    control_references=(),
    requirement_items=("REQ-20260901090000-01@1#R-001",),
    acceptance_items=("REQ-20260901090000-01@1#AC-001",),
)
design = {
    "title": "Runtime Independence",
    "summary": "Build a self-contained waiting-input DSN candidate.",
    "boundary": "installed runtime fixture",
    "profile": "full",
    "change_type": "new",
    "baseline_references": [],
    "target_state_summary": "self-contained runtime",
    "impact_summary": "none",
    "changes": [{
        "object_or_boundary": "resource:runtime-fixture",
        "change": "add",
        "target_state": "runtime remains executable without development docs",
        "affected_domains": ["DOM-510"],
    }],
    "traceability": [{
        "source_references": [
            "REQ-20260901090000-01@1#R-001",
            "REQ-20260901090000-01@1#AC-001",
        ],
        "design_references": [],
        "decision_references": [],
        "vfy_references": [],
        "na_reason": "Pending Domain design",
    }],
    "decisions": [],
    "decision_none_reason": "No design choice in runtime independence fixture",
    "domains": {},
    "composite_subdomains": None,
    "cross_domain_conflicts": [],
    "scope_expansion": False,
    "simplicity_rationale": "Minimum deterministic fixture",
    "lifecycle_applicability": [
        {"phase": "PLN", "disposition": "pending", "host": "N/A", "basis": "Pending"},
        {"phase": "IMP", "disposition": "pending", "host": "N/A", "basis": "Pending"},
        {"phase": "VFY", "disposition": "required", "host": "N/A", "basis": "Fixed control point"},
        {"phase": "RLS", "disposition": "pending", "host": "N/A", "basis": "Pending"},
    ],
    "evidence": [],
    "supporting_members": [],
    "open_items": [],
    "exceptions": [],
}
result = DsnBuilder(root).build(
    artifact_id="DSN-20990101000000-01",
    revision=1,
    upstream=upstream,
    design=design,
    final_confirmation=None,
)
print(json.dumps({
    "status": result.status,
    "gate": result.gate_result,
    "member_count": len(result.members),
    "primary_size": len(result.raw_bytes),
}))
'''
        completed = _run(
            [sys.executable, "-c", builder_code, str(project)],
            cwd=outside,
            env=env,
        )
        if completed.returncode != 0:
            print(
                "sdlc-200-dsn runtime independence: FAIL: builder import/execution: "
                + completed.stderr,
                file=sys.stderr,
            )
            return 1
        built = _json_stdout(completed)
        if built.get("primary_size", 0) < 100 or built.get("gate") not in {"pending", "fail"}:
            print(
                f"sdlc-200-dsn runtime independence: FAIL: invalid build result {built}",
                file=sys.stderr,
            )
            return 1

        before = tuple(sorted(path.relative_to(project).as_posix() for path in project.rglob("*")))
        completed = _run(
            [
                sys.executable,
                str(runtime),
                "check",
                "--reference",
                "DSN-20990101000000-01@1",
                "--project-root",
                str(project),
                "--output=json",
            ],
            cwd=outside,
            payload={"inputs": {}},
        )
        result = _json_stdout(completed)
        after = tuple(sorted(path.relative_to(project).as_posix() for path in project.rglob("*")))
        if completed.returncode == 0 or result.get("ok") is not False or before != after:
            print(
                f"sdlc-200-dsn runtime independence: FAIL: missing-store check {result}",
                file=sys.stderr,
            )
            return 1

    print("sdlc-200-dsn runtime independence: PASS")
    print("development docs copied: 0")
    print("external dependencies installed: 0")
    print("project writes during read-only check: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
