"""System proof for the real CTX→REQ→DSN→PLN→IMP→VFY runner."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from tools import run_external_vfy_integration as external


class ExternalVfyIntegrationTest(unittest.TestCase):
    def _git(self, root: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        return completed.stdout.strip()

    def _repository(self, root: Path, name: str) -> tuple[Path, str]:
        repo = root / name
        repo.mkdir()
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.email", "vfy@example.invalid")
        self._git(repo, "config", "user.name", "VFY Fixture")
        (repo / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        self._git(repo, "add", "README.md")
        self._git(repo, "commit", "-q", "-m", "fixture")
        return repo, self._git(repo, "rev-parse", "HEAD")

    def test_two_repositories_execute_full_chain_and_restore_exactly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-external-system-") as directory:
            root = Path(directory)
            log = external.Log(root / "external.log")
            projects = []
            for name in ("springgear", "gin-vue-admin"):
                repo, sha = self._repository(root, name)
                projects.append(
                    external.run_project(
                        repo,
                        name=name,
                        repository=f"fixture/{name}",
                        expected_sha=sha,
                        log=log,
                    )
                )

            cross = external.compare_projects(projects)
            self.assertEqual("PASS", cross["status"])
            for project in projects:
                self.assertEqual(
                    ["CTX", "REQ", "DSN", "PLN", "IMP", "VFY"],
                    [item["phase"] for item in project["phase_execution_receipts"]],
                )
                self.assertEqual(["inspection", "analysis"], project["method_types"])
                self.assertEqual("pass", project["product_result"])
                self.assertEqual("pass", project["artifact_gate"])
                self.assertFalse(project["rls_ready"])
                self.assertTrue(project["check_read_only"])
                self.assertTrue(all(project["cleanup_assertions"].values()))
                self.assertEqual(
                    "",
                    self._git(
                        root / project["name"],
                        "status",
                        "--porcelain=v1",
                        "--untracked-files=all",
                    ),
                )


if __name__ == "__main__":
    unittest.main()
