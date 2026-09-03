from pathlib import Path
import tempfile
import unittest

from packages.sdlc_resource import ResourceError, apply_operations, capture_snapshot, restore_snapshot


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "src").mkdir()
        (self.root / "src/app.txt").write_text("before", encoding="utf-8")
        (self.root / ".git").mkdir()
        (self.root / ".git/keep").write_text("git", encoding="utf-8")
        (self.root / ".sdlc").mkdir()
        (self.root / ".sdlc/keep").write_text("runtime", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_excludes_git_and_runtime_and_is_deterministic(self):
        first = capture_snapshot(self.root, "repo")
        second = capture_snapshot(self.root, "repo")
        self.assertEqual(first.reference, second.reference)
        self.assertEqual(first.paths, ("src/app.txt",))

    def test_scoped_write_and_restore(self):
        before = capture_snapshot(self.root, "repo")
        result = apply_operations(
            self.root,
            "repo",
            [{"op": "write_text", "path": "src/app.txt", "content": "after"}],
            allowed_scope=("resource:repo", "path:repo/src"),
        )
        self.assertEqual(result.changed_paths, ("src/app.txt",))
        self.assertNotEqual(result.before.reference, result.after.reference)
        restore_snapshot(self.root, before)
        self.assertEqual((self.root / "src/app.txt").read_text(), "before")
        self.assertEqual((self.root / ".git/keep").read_text(), "git")
        self.assertEqual((self.root / ".sdlc/keep").read_text(), "runtime")

    def test_out_of_scope_and_runtime_paths_are_rejected(self):
        with self.assertRaises(ResourceError):
            apply_operations(self.root, "repo", [{"op":"write_text","path":"other.txt","content":"x"}], allowed_scope=("resource:repo", "path:repo/src"))
        with self.assertRaises(ResourceError):
            apply_operations(self.root, "repo", [{"op":"write_text","path":".sdlc/x","content":"x"}], allowed_scope=("resource:repo",))


if __name__ == "__main__":
    unittest.main()
