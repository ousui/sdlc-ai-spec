#!/usr/bin/env python3
"""Execute sdlc-status from an installed-runtime copy without docs."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        plugin = base / "plugin"
        project = base / "project"
        outside = base / "outside"
        project.mkdir()
        outside.mkdir()
        (plugin / "skills").mkdir(parents=True)
        shutil.copytree(ROOT / "packages", plugin / "packages")
        shutil.copytree(ROOT / "skills/_shared", plugin / "skills/_shared")
        shutil.copytree(ROOT / "skills/sdlc-status", plugin / "skills/sdlc-status")
        if (plugin / "docs").exists():
            raise AssertionError("docs were copied")
        runtime = plugin / "skills/sdlc-status/scripts/runtime.py"
        completed = subprocess.run(
            [sys.executable, str(runtime), "--project-root", str(project), "--output=json"],
            cwd=outside,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout + completed.stderr)
        if '"state": "not_started"' not in completed.stdout:
            raise AssertionError(completed.stdout)
        if (project / ".sdlc").exists():
            raise AssertionError("status Runtime created project state")
    print("sdlc-status runtime independence: PASS")
    print("docs copied: 0")
    print("project writes: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
