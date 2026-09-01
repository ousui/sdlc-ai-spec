#!/usr/bin/env python3
"""Run the sdlc-status Skill against a real SpringGear CTX/REQ Store."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "packages"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from tools.test_springgear_lifecycle_query import (  # noqa: E402
    create_context,
    create_requirement,
    prepare_project,
    snapshot,
)

STATUS_PATH = ROOT / "skills/sdlc-status/scripts/runtime.py"
SPEC = importlib.util.spec_from_file_location("springgear_status_runtime", STATUS_PATH)
assert SPEC is not None and SPEC.loader is not None
STATUS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STATUS
SPEC.loader.exec_module(STATUS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    if not source.is_dir():
        raise SystemExit("SpringGear source directory does not exist")

    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "springgear"
        commit = prepare_project(source, project)
        context_reference = create_context(project, commit)
        requirement_reference = create_requirement(project, context_reference)
        before = snapshot(project)

        auto = STATUS.run_status([], cwd=project)
        listed = STATUS.run_status(["list"], cwd=project)
        inspected = STATUS.run_status(
            ["inspect", "--reference", requirement_reference], cwd=project
        )
        # Meta commands are intentionally incompatible with execution options. The
        # unrelated CWD proves help does not resolve or inspect a project target.
        help_result = STATUS.run_status(["--help"], cwd=Path(temporary))
        json_cli = subprocess.run(
            [
                sys.executable,
                str(STATUS_PATH),
                "inspect",
                "--reference",
                requirement_reference,
                "--project-root",
                str(project),
                "--output=json",
            ],
            cwd=Path(temporary),
            text=True,
            capture_output=True,
            check=False,
        )
        after = snapshot(project)

        if before != after:
            raise AssertionError("sdlc-status changed the SpringGear project")
        if auto["state"] != "ready_for_next_phase":
            raise AssertionError(auto)
        if auto["projection"]["root_reference"] != requirement_reference:
            raise AssertionError(auto)
        if listed["overview"]["requirement_candidates"][0]["reference"] != requirement_reference:
            raise AssertionError(listed)
        if inspected["next_action"]["phase"] != "DSN":
            raise AssertionError(inspected)
        if inspected["next_action"]["skill_available"]:
            raise AssertionError("DSN must remain unavailable in this baseline")
        if help_result["state"] != "meta" or help_result["project_root"] is not None:
            raise AssertionError(help_result)
        if json_cli.returncode != 0:
            raise AssertionError(json_cli.stdout + json_cli.stderr)
        parsed = json.loads(json_cli.stdout)
        if parsed["state"] != "ready_for_next_phase":
            raise AssertionError(parsed)
        if parsed["effective_write_policy"] != "deny":
            raise AssertionError(parsed)

        print("springgear sdlc-status: PASS")
        print("source commit:", commit)
        print("context:", context_reference)
        print("requirement:", requirement_reference)
        print("bare invocation:", auto["state"])
        print("list candidates:", len(listed["overview"]["requirement_candidates"]))
        print("inspect next phase:", inspected["next_action"]["phase"])
        print("project mutation after status:", 0)
        print("remote springgear writes:", 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
