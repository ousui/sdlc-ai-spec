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

from run_external_imp_integration import compare_projects, run_integration


class ExternalImpIntegrationTests(unittest.TestCase):
    def make_project(self, files: dict[str, str]) -> tuple[Path, str]:
        temporary = tempfile.TemporaryDirectory(prefix="external-imp-system-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.name", "External IMP Fixture"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.invalid"],
            cwd=root,
            check=True,
        )
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "external IMP fixture"],
            cwd=root,
            check=True,
        )
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return root, sha

    def test_two_distinct_projects_complete_real_imp_and_restore_git(self):
        maven_root, maven_sha = self.make_project(
            {
                "pom.xml": (
                    "<project><groupId>example</groupId><artifactId>spring-probe</artifactId>"
                    "<modules><module>core</module></modules></project>\n"
                ),
                "core/pom.xml": "<project><artifactId>core</artifactId></project>\n",
                "README.md": "# Spring probe\n\nA compact Maven fixture.\n",
                "docs/README.md": "# Spring resource\n\nA narrow Maven resource.\n",
            }
        )
        go_vue_root, go_vue_sha = self.make_project(
            {
                "server/go.mod": "module example.invalid/go-vue-probe\n\ngo 1.24\n",
                "web/package.json": json.dumps(
                    {"name": "go-vue-probe", "private": True}, sort_keys=True
                )
                + "\n",
                "README.md": "# Go Vue probe\n\nA separate frontend/backend fixture.\n",
                "aiDoc/README.md": "# Go Vue resource\n\nA narrow mixed-stack resource.\n",
                "server/config.yaml": "password: public-example-value\n",
            }
        )
        initial_readmes = {
            maven_root: (maven_root / "docs/README.md").read_bytes(),
            go_vue_root: (go_vue_root / "aiDoc/README.md").read_bytes(),
        }

        maven = run_integration(maven_root, "fixture/spring-probe", maven_sha)
        go_vue = run_integration(go_vue_root, "fixture/go-vue-probe", go_vue_sha)
        cross = compare_projects((maven, go_vue))

        for result in (maven, go_vue):
            self.assertTrue(result["ok"])
            self.assertEqual(list(result["references"]), ["CTX", "REQ", "DSN", "PLN", "IMP"])
            self.assertEqual(result["binding"], result["references"]["PLN"] + "#WI-001")
            self.assertEqual(result["claim"]["state"], "completed")
            self.assertEqual(result["phases"]["IMP"]["revision_state"], "frozen")
            self.assertEqual(result["phases"]["IMP"]["artifact_status"], "ready")
            self.assertTrue(result["result"]["digest_reproducible"])
            self.assertTrue(result["check_read_only"])
            self.assertTrue(result["context_matches_plan"])
            self.assertTrue(result["vfy_ready"])
            self.assertTrue(all(result["cleanup"].values()))
            self.assertEqual(result["lifecycle"]["overall_state"], "ready_for_next_phase")
            self.assertIn(
                {"code": "START_VFY", "phase": "VFY"},
                result["lifecycle"]["next_actions"],
            )

        self.assertTrue(cross["ok"])
        self.assertTrue(cross["artifact_structure_signature_equal"])
        self.assertTrue(cross["artifact_id_patterns_equal"])
        self.assertTrue(cross["revision_semantics_equal"])
        self.assertTrue(cross["manifest_structure_equal"])
        self.assertTrue(cross["gate_structure_equal"])
        self.assertTrue(cross["lifecycle_relationship_equal"])
        self.assertTrue(
            all(cross["semantic_content_digests_different"].values())
        )
        self.assertEqual(maven["resource_root"], "docs")
        self.assertEqual(go_vue["resource_root"], "aiDoc")
        for result, root in ((maven, maven_root), (go_vue, go_vue_root)):
            readme = initial_readmes[root]
            self.assertEqual((root / result["target_path"]).read_bytes(), readme)
            self.assertFalse((root / ".sdlc").exists())
            self.assertEqual(
                subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout,
                "",
            )
        self.assertEqual(
            (go_vue_root / "server/config.yaml").read_text(encoding="utf-8"),
            "password: public-example-value\n",
        )


if __name__ == "__main__":
    unittest.main()
