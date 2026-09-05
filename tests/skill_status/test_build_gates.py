"""Utility source-lock and installed-copy gates; no native Client certification."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from tools.test_sdlc_status_runtime_independence import verify
from tools.validate_sdlc_status_source_lock import ROOT, LOCK, sources, validate
from packages.sdlc_runtime import SourceLockError


class StatusInstalledTests(unittest.TestCase):
    def test_docs_free_installed_copy_is_read_only(self):
        result = verify()
        self.assertTrue(result["success"])
        self.assertEqual(12, len(result["commands"]))
        self.assertEqual(0, result["project_writes_during_query"])
        self.assertEqual("NOT_RUN", result["native_client_behavior"])


class StatusSourceLockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="status-lock-"); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for relative in [row.resource for row in sources(ROOT)] + [LOCK]:
            dst = self.root / relative; dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, dst)

    def test_complete_lock_passes(self): self.assertTrue(validate(self.root)["success"])

    def test_missing_entry_fails(self):
        p = self.root / LOCK; data = json.loads(p.read_bytes()); data["contracts"].pop(); p.write_text(json.dumps(data))
        with self.assertRaises(SourceLockError): validate(self.root)

    def test_changed_runtime_bytes_fail(self):
        p = self.root / "skills/sdlc-status/scripts/runtime.py"; p.write_bytes(p.read_bytes() + b"\n# drift\n")
        with self.assertRaises(SourceLockError): validate(self.root)

    def test_new_unlocked_runtime_dependency_fails(self):
        (self.root / "packages/sdlc_lifecycle/new_query.py").write_text("# new runtime dependency\n")
        with self.assertRaises(SourceLockError): validate(self.root)

    def test_duplicate_and_out_of_order_entries_fail(self):
        p = self.root / LOCK; data = json.loads(p.read_bytes()); data["contracts"].reverse(); p.write_text(json.dumps(data))
        with self.assertRaises(SourceLockError): validate(self.root)
        data["contracts"] = [data["contracts"][0]] * 2; p.write_text(json.dumps(data))
        with self.assertRaises(SourceLockError): validate(self.root)

    def test_symlinked_lock_fails_without_reading_target(self):
        p = self.root / LOCK; p.unlink(); p.symlink_to(self.root / "nonexistent")
        with self.assertRaises(SourceLockError): validate(self.root)
