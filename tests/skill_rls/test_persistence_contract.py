from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tests.skill_rls.support import artifact
from rls_persistence import (
    build_payload,
    create_revision,
    read_revision,
    write_open_revision,
)


class RlsPersistenceContractTests(unittest.TestCase):
    def test_build_payload_is_canonical_and_store_neutral(self):
        value = artifact()
        payload = build_payload(value)
        self.assertEqual("RLS", payload.artifact_type)
        self.assertEqual(value["artifact"]["id"], payload.artifact_id)
        self.assertEqual(value["artifact"]["revision"], payload.revision)
        from packages.sdlc_runtime import parse_canonical_artifact
        parsed = parse_canonical_artifact(payload.primary_blob)
        self.assertEqual(value["context_reference"], parsed.front_matter["context"])
        self.assertEqual("draft", payload.artifact_status)
        self.assertTrue(payload.primary_blob.startswith(b"---\ncontract: sdlc-ai-spec/artifact/v1"))
        self.assertEqual("RLS-STATE", payload.members[0].member_id)

    def test_create_and_exact_readback_use_shared_store(self):
        with tempfile.TemporaryDirectory(prefix="rls-store-") as directory:
            root = Path(directory)
            stored, generation = create_revision(root, artifact())
            reference = stored["artifact"]["reference"]
            read_back, observed_generation = read_revision(root, reference)
        self.assertGreaterEqual(generation, 1)
        self.assertEqual(generation, observed_generation)
        self.assertEqual(reference, read_back["artifact"]["reference"])
        self.assertEqual(stored["release_contract"], read_back["release_contract"])
        self.assertEqual("open", read_back["artifact"]["revision_state"])

    def test_stale_generation_cannot_overwrite_open_revision(self):
        with tempfile.TemporaryDirectory(prefix="rls-store-") as directory:
            root = Path(directory)
            stored, generation = create_revision(root, artifact())
            changed = deepcopy(stored)
            changed["warnings"].append("first update")
            _updated, next_generation = write_open_revision(
                root,
                changed,
                expected_generation=generation,
            )
            changed["warnings"].append("stale update")
            with self.assertRaises(Exception):
                write_open_revision(
                    root,
                    changed,
                    expected_generation=generation,
                )
        self.assertGreater(next_generation, generation)

    def test_readback_requires_exact_numeric_rls_reference(self):
        with tempfile.TemporaryDirectory(prefix="rls-store-") as directory:
            with self.assertRaises(Exception) as caught:
                read_revision(Path(directory), "latest")
        self.assertEqual("RLS_REFERENCE_NOT_EXACT", getattr(caught.exception, "code", None))

    def test_terminal_state_requires_explicit_staging_mode(self):
        with tempfile.TemporaryDirectory(prefix="rls-store-") as directory:
            root = Path(directory)
            stored, generation = create_revision(root, artifact())
            stored["artifact"]["revision_state"] = "frozen"
            stored["final_confirmation"] = {
                "confirmer_identity": "test",
                "digest": "not-authoritative",
            }
            with self.assertRaises(Exception) as caught:
                write_open_revision(
                    root,
                    stored,
                    expected_generation=generation,
                )
        self.assertEqual("RLS_CONTRACT_INVALID", getattr(caught.exception, "code", None))


if __name__ == "__main__":
    unittest.main()
