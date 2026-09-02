from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from run_external_pln_integration import run_integration


class ExternalPlnIntegrationTests(unittest.TestCase):
    def make_project(self, files: dict[str, str]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        return root

    def test_maven_project_reaches_exact_imp_binding_without_source_changes(self):
        root = self.make_project(
            {
                "pom.xml": "<project><modules><module>core</module></modules></project>\n",
                "core/pom.xml": "<project/>\n",
                "README.md": "fixture\n",
            }
        )
        result = run_integration(root, "fixture/maven@HEAD")
        self.assertTrue(result["ok"])
        self.assertEqual(result["plan_gate"], "pass")
        self.assertEqual(result["next_actions"][0]["phase"], "IMP")
        self.assertIn("#WI-001", result["next_actions"][0]["command"])
        self.assertTrue(result["source_snapshot_unchanged"])
        self.assertFalse((root / ".sdlc").exists())

    def test_go_vue_project_uses_real_build_descriptors_and_stable_work_items(self):
        root = self.make_project(
            {
                "server/go.mod": "module example.invalid/server\n\ngo 1.23\n",
                "web/package.json": json.dumps({"name": "fixture-web"}) + "\n",
                "README.md": "fixture\n",
            }
        )
        result = run_integration(root, "fixture/go-vue@HEAD")
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["build_descriptors"],
            ["server/go.mod", "web/package.json"],
        )
        self.assertEqual([item["id"] for item in result["work_items"]], ["WI-001", "WI-002"])
        self.assertEqual([item["target_phase"] for item in result["work_items"]], ["IMP", "VFY"])
        self.assertTrue(result["source_status_unchanged"])
        self.assertFalse((root / ".sdlc").exists())


if __name__ == "__main__":
    unittest.main()
