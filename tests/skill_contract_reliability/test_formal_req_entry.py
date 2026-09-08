"""Exercise the installed, reviewed REQ entry, not only its unwrapped base.

No new protocol or schema: these are existing create/revise requests with
invalid fields. Both normal and preview requests must stop before Store IO.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FormalReqEntryRegressions(unittest.TestCase):
    def test_invalid_input_is_rejected_by_installed_formal_entry_without_store(self):
        with tempfile.TemporaryDirectory(prefix="scr-formal-req-") as directory:
            root = Path(directory)
            installed, project = root / "plugin", root / "project"
            project.mkdir()
            for name in ("skills", "packages", "scripts"):
                shutil.copytree(ROOT / name, installed / name,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "AGENTS.md"))
            self.assertFalse((installed / "docs").exists())
            self.assertFalse((installed / "tests").exists())
            entry = installed / "skills/sdlc-100-req/scripts/runtime_final.py"
            for operation in ("create", "revise"):
                for dry_run in (False, True):
                    with self.subTest(operation=operation, dry_run=dry_run):
                        request = {
                            "contract": "sdlc-ai-spec/runtime-invocation/v1",
                            "operation": operation, "project_root": str(project),
                            "artifact_reference": None,
                            "inputs": {"requirement": {
                                "sources": [{"type": "chatty"}],
                                "requirements": [{"type": []}]}},
                            "options": {"dry_run": dry_run},
                            "confirmations": [{"type": "write", "approved": True}],
                        }
                        result = subprocess.run(
                            [sys.executable, "-B", str(entry)], input=json.dumps(request),
                            capture_output=True, text=True, cwd=project, timeout=15,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""})
                        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                        body = json.loads(result.stdout)
                        self.assertFalse(body["ok"])
                        self.assertEqual("failed", body["status"])
                        self.assertIsNone(body["artifact"])
                        self.assertEqual({"result": "pending", "failed_checks": []}, body["gate"])
                        self.assertEqual("REQ_CONTENT_INVALID", body["errors"][0]["code"])
                        paths = {row["path"] for row in body["errors"][0]["details"]}
                        self.assertEqual({"inputs.requirement.sources[0].type",
                                          "inputs.requirement.requirements[0].type"}, paths)
                        self.assertFalse(body["next_action"]["requires_user"])
                        self.assertEqual([], list(project.iterdir()))
                        self.assertNotIn("Traceback", result.stderr)
