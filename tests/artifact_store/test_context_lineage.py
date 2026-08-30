import hashlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from packages.sdlc_artifact_store import ArtifactStore, InvalidInputError, ReadOnlyError
from packages.sdlc_artifact_store.context_lineage import ContextLineageRegistry


def boundary_key(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


class ContextLineageTests(unittest.TestCase):
    def test_read_only_find_does_not_create_extension_table(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            writer = ArtifactStore.open_read_write(root)
            writer.initialize()
            before = {p.name for p in (root / ".sdlc").iterdir()}
            reader = ArtifactStore.open_read_only(root)
            self.assertIsNone(ContextLineageRegistry(reader).find(boundary_key("a")))
            after = {p.name for p in (root / ".sdlc").iterdir()}
            self.assertEqual(before, after)

    def test_reserve_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = ArtifactStore.open_read_write(root)
            store.initialize()
            registry = ContextLineageRegistry(store)
            now = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
            first = registry.reserve(boundary_key("project-a"), now=now)
            second = registry.reserve(boundary_key("project-a"), now=now)
            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertEqual(first.artifact_id, second.artifact_id)

    def test_different_boundaries_receive_different_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = ArtifactStore.open_read_write(root)
            store.initialize()
            registry = ContextLineageRegistry(store)
            now = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
            first = registry.reserve(boundary_key("a"), now=now)
            second = registry.reserve(boundary_key("b"), now=now)
            self.assertNotEqual(first.artifact_id, second.artifact_id)

    def test_concurrent_reserve_returns_one_lineage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            setup = ArtifactStore.open_read_write(root)
            setup.initialize()
            key = boundary_key("same")
            now = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

            def reserve():
                store = ArtifactStore.open_read_write(root)
                return ContextLineageRegistry(store).reserve(key, now=now).artifact_id

            with ThreadPoolExecutor(max_workers=2) as executor:
                ids = list(executor.map(lambda _: reserve(), range(2)))
            self.assertEqual(len(set(ids)), 1)

    def test_invalid_boundary_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = ArtifactStore.open_read_write(root)
            store.initialize()
            with self.assertRaises(InvalidInputError):
                ContextLineageRegistry(store).reserve("project-a")

    def test_read_only_reserve_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            writer = ArtifactStore.open_read_write(root)
            writer.initialize()
            reader = ArtifactStore.open_read_only(root)
            with self.assertRaises(ReadOnlyError):
                ContextLineageRegistry(reader).reserve(boundary_key("a"))


if __name__ == "__main__":
    unittest.main()
