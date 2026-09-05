"""Real filesystem conflicts are failures, not a successful empty overview."""
from __future__ import annotations

import json
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_lifecycle import LifecycleStoreUnavailable
from tests.skill_status.test_runtime import RUNTIME

REF = "REQ-20260905000000-01@1"


def snapshot(root: Path):
    rows = []
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        data = path.read_bytes() if stat.S_ISREG(mode) else (
            str(path.readlink()) if stat.S_ISLNK(mode) else None
        )
        rows.append((path.relative_to(root).as_posix(), mode, data))
    return rows


class StatusStoreAbsenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="status-absence-")
        self.addCleanup(temporary.cleanup)
        self.lab = Path(temporary.name).resolve()
        self.root = self.lab / "project"
        self.root.mkdir()

    def assert_invalid_store(self):
        before = snapshot(self.lab)
        for args in ([], ["list"], ["auto", "-r", REF], ["inspect", "-r", REF]):
            with self.subTest(args=args):
                result = RUNTIME.run_status(args, cwd=self.root)
                self.assertFalse(result["ok"], result)
                self.assertEqual("failed", result["status"])
                self.assertEqual("query_failed", result["state"])
                self.assertEqual("LIFECYCLE_STORE_PATH_INVALID", result["errors"][0]["code"])
                self.assertIsNone(result["overview"])
                self.assertIsNone(result["projection"])
                self.assertIsNone(result["next_action"])
                self.assertEqual("deny", result["effective_write_policy"])
                self.assertEqual(before, snapshot(self.lab))

    def test_runtime_file_is_not_a_successful_not_started_view(self):
        (self.root / ".sdlc").write_bytes(b"conflicting existing content")
        self.assert_invalid_store()

    def test_database_directory_is_not_a_successful_not_started_view(self):
        (self.root / ".sdlc/store.sqlite3").mkdir(parents=True)
        (self.root / ".sdlc/store.sqlite3/canary").write_bytes(b"preserve")
        self.assert_invalid_store()

    def test_dangling_runtime_link_is_not_an_absent_store(self):
        (self.root / ".sdlc").symlink_to(self.lab / "absent-target")
        self.assert_invalid_store()

    def test_dangling_database_link_is_not_an_absent_store(self):
        (self.root / ".sdlc").mkdir()
        (self.root / ".sdlc/store.sqlite3").symlink_to(self.lab / "absent-target")
        self.assert_invalid_store()

    def test_live_link_to_wrong_runtime_type_is_invalid(self):
        target = self.lab / "target-file"
        target.write_bytes(b"preserve link target")
        (self.root / ".sdlc").symlink_to(target)
        self.assert_invalid_store()

    def test_legitimate_absence_preserves_bare_auto_and_list(self):
        for empty_directory in (False, True):
            if empty_directory:
                (self.root / ".sdlc").mkdir()
            before = snapshot(self.lab)
            for args in ([], ["auto"], ["list"]):
                result = RUNTIME.run_status(args, cwd=self.root)
                self.assertTrue(result["ok"], result)
                self.assertEqual("not_started", result["state"])
                self.assertEqual("START_PROJECT_CONTEXT", result["next_action"]["code"])
                self.assertEqual(before, snapshot(self.lab))

    def test_exact_reference_still_fails_when_store_is_genuinely_absent(self):
        before = snapshot(self.lab)
        for args in (["auto", "-r", REF], ["inspect", "-r", REF]):
            result = RUNTIME.run_status(args, cwd=self.root)
            self.assertFalse(result["ok"])
            self.assertEqual("store_unavailable", result["state"])
            self.assertEqual(before, snapshot(self.lab))

    def test_reference_failure_precedes_conflicting_store_path(self):
        (self.root / ".sdlc").write_bytes(b"preserve")
        factory = Mock(side_effect=AssertionError("no Store access for invalid reference"))
        for args in (["auto", "-r", "latest"], ["inspect", "-r", REF + "#AC-001"]):
            result = RUNTIME.run_status(args, cwd=self.root, service_factory=factory)
            self.assertEqual("invalid_reference", result["state"])
        factory.assert_not_called()

    def test_meta_commands_do_not_run_store_diagnostics(self):
        with patch.object(RUNTIME, "_store_is_genuinely_absent", side_effect=AssertionError("meta has no project access")) as probe:
            for command in ("help", "version", "commands", "examples"):
                result = RUNTIME.run_status([command, "--output=json"], cwd=self.lab / "absent")
                self.assertTrue(result["ok"])
                self.assertEqual("meta", result["state"])
        probe.assert_not_called()

    def test_inspection_error_is_bounded_and_not_an_absence_fallback(self):
        before = snapshot(self.lab)
        marker = "SYNTHETIC-PRIVATE-ERROR"
        factory = Mock(side_effect=LifecycleStoreUnavailable(marker))
        with patch.object(Path, "lstat", side_effect=PermissionError(marker)):
            result = RUNTIME.run_status([], cwd=self.root, service_factory=factory)
        self.assertFalse(result["ok"])
        self.assertEqual("query_failed", result["state"])
        self.assertNotIn(marker, json.dumps(result))
        self.assertIsNone(result["next_action"])
        factory.assert_called_once()
        self.assertEqual(before, snapshot(self.lab))

    def test_present_valid_database_after_unavailable_never_downgrades(self):
        # Construct a real shared Store; do not use direct SQL or a private schema.
        ArtifactStore.open_read_write(self.root).initialize()
        before = snapshot(self.lab)
        factory = Mock(side_effect=LifecycleStoreUnavailable("unavailable observation"))
        result = RUNTIME.run_status([], cwd=self.root, service_factory=factory)
        self.assertFalse(result["ok"])
        self.assertEqual("query_failed", result["state"])
        self.assertIsNone(result["overview"])
        factory.assert_called_once()
        self.assertEqual(before, snapshot(self.lab))

    def test_live_directory_link_retains_the_shared_backend_policy(self):
        target = self.lab / "runtime-target"
        target.mkdir()
        (self.root / ".sdlc").symlink_to(target, target_is_directory=True)
        before = snapshot(self.lab)
        result = RUNTIME.run_status([], cwd=self.root)
        self.assertTrue(result["ok"], result)
        self.assertEqual("not_started", result["state"])
        self.assertEqual(before, snapshot(self.lab))

    def test_installed_copy_rejects_conflict_without_siblings_or_development_files(self):
        plugin = self.lab / "installed"
        (plugin / "skills").mkdir(parents=True)
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "AGENTS.md", "CLAUDE.md")
        shutil.copytree(RUNTIME.PLUGIN_ROOT / "packages", plugin / "packages", ignore=ignore)
        for name in ("_shared", "sdlc-status"):
            shutil.copytree(RUNTIME.PLUGIN_ROOT / "skills" / name, plugin / "skills" / name, ignore=ignore)
        self.assertEqual(["_shared", "sdlc-status"], sorted(p.name for p in (plugin / "skills").iterdir()))
        for name in ("docs", "tests", "tools"):
            self.assertFalse((plugin / name).exists())
        (self.root / ".sdlc/store.sqlite3").mkdir(parents=True)
        before = snapshot(self.root)
        process = subprocess.run(
            [sys.executable, "-I", "-B", str(plugin / "skills/sdlc-status/scripts/runtime.py"),
             "-p", str(self.root), "-f", "json"], cwd=self.lab,
            input=b"", capture_output=True, timeout=30,
        )
        result = json.loads(process.stdout)
        self.assertEqual(2, process.returncode)
        self.assertEqual(b"", process.stderr)
        self.assertEqual("LIFECYCLE_STORE_PATH_INVALID", result["errors"][0]["code"])
        self.assertEqual(before, snapshot(self.root))

    def test_real_cli_json_reports_path_conflict_with_nonzero_exit(self):
        (self.root / ".sdlc").write_bytes(b"preserve")
        before = snapshot(self.lab)
        process = subprocess.run(
            [sys.executable, "-I", "-B", RUNTIME.__file__, "-p", str(self.root), "-f", "json"],
            input=b"", capture_output=True, timeout=30,
        )
        result = json.loads(process.stdout)
        self.assertEqual(2, process.returncode)
        self.assertEqual(b"", process.stderr)
        self.assertFalse(result["ok"])
        self.assertEqual("LIFECYCLE_STORE_PATH_INVALID", result["errors"][0]["code"])
        self.assertEqual(before, snapshot(self.lab))


if __name__ == "__main__":
    unittest.main()
