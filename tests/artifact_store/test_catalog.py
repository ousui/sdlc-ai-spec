import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from packages.sdlc_artifact_store import ArtifactStore, InvalidInputError
from packages.sdlc_artifact_store.catalog import ArtifactCatalog


class ArtifactCatalogTests(unittest.TestCase):
    def test_catalog_lists_artifacts_and_revisions_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            writer = ArtifactStore.open_read_write(root)
            writer.initialize()
            allocation = writer.allocate_artifact(
                "REQ",
                now=datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc),
            )
            writer.allocate_revision(allocation.artifact_id)
            reader = ArtifactStore.open_read_only(root)
            catalog = ArtifactCatalog(reader)
            self.assertEqual(
                [item.artifact_id for item in catalog.list_artifacts("REQ")],
                [allocation.artifact_id],
            )
            self.assertEqual(
                [item.revision for item in catalog.list_revisions(allocation.artifact_id)],
                [1],
            )

    def test_catalog_requires_read_only_store(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            writer = ArtifactStore.open_read_write(root)
            writer.initialize()
            with self.assertRaises(InvalidInputError):
                ArtifactCatalog(writer)


if __name__ == "__main__":
    unittest.main()
