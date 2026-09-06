"""Requirement semantics and failure recovery using a non-TestCase fixture."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tests.skill_req.support import (RequirementFixture, runtime,
    RequirementSemanticError, validate_persisted_requirement,
    parse_canonical_artifact, SOURCE_HEADERS, find_tables)


class ReviewFixTests(RequirementFixture, unittest.TestCase):
    def test_context_is_not_duplicated_in_front_inputs(self):
        result = runtime.execute_phase(self.handler, self.request())
        stored = self.store.read_revision(
            result["artifact"]["id"], result["artifact"]["revision"]
        )
        parsed = parse_canonical_artifact(stored.payload.primary_blob)
        self.assertEqual(parsed.front_matter["context"], self.context)
        self.assertEqual(parsed.front_matter["inputs"], [])
        validate_persisted_requirement(parsed)

    def test_frozen_no_change_does_not_allocate_new_revision(self):
        created = runtime.execute_phase(self.handler, self.request())
        reference = created["artifact"]["reference"]
        revised = runtime.execute_phase(
            self.handler,
            self.request(operation="revise", reference=reference),
        )
        self.assertTrue(revised["ok"])
        self.assertEqual(revised["artifact"]["revision"], 1)
        self.assertEqual(revised["warnings"][0]["code"], "NO_CHANGE")
        connection = self.store._connect()
        try:
            count = connection.execute(
                "SELECT COUNT(*) AS n FROM revisions WHERE artifact_id = ?",
                (created["artifact"]["id"],),
            ).fetchone()["n"]
        finally:
            connection.close()
        self.assertEqual(count, 1)

    def test_semantic_check_rejects_context_in_inputs(self):
        result = runtime.execute_phase(self.handler, self.request())
        stored = self.store.read_revision(
            result["artifact"]["id"], result["artifact"]["revision"]
        )
        text = stored.payload.primary_blob.decode("utf-8")
        tampered = text.replace("inputs:\n---", f"inputs:\n  - {self.context}\n---")
        with self.assertRaises(RequirementSemanticError):
            validate_persisted_requirement(
                parse_canonical_artifact(tampered.encode("utf-8"))
            )

    def test_semantic_check_rejects_unrooted_requirement(self):
        result = runtime.execute_phase(self.handler, self.request())
        stored = self.store.read_revision(
            result["artifact"]["id"], result["artifact"]["revision"]
        )
        text = stored.payload.primary_blob.decode("utf-8")
        tampered = text.replace(
            "| R-001 | behavior | SRC-001, GOAL-001 |",
            "| R-001 | behavior | R-001 |",
        )
        with self.assertRaises(RequirementSemanticError):
            validate_persisted_requirement(
                parse_canonical_artifact(tampered.encode("utf-8"))
            )

    def test_failed_build_abandons_allocated_revision(self):
        value = self.requirement()
        value["supporting_members"] = [
            {"media_type": "text/plain", "content": "missing name"}
        ]
        result = runtime.execute_phase(
            self.handler, self.request(requirement=value, final=False)
        )
        self.assertFalse(result["ok"])
        connection = self.store._connect()
        try:
            rows = connection.execute(
                "SELECT state FROM revisions r JOIN artifacts a USING(artifact_id) WHERE a.artifact_type='REQ'"
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual([row["state"] for row in rows], ["abandoned"])


if __name__ == "__main__":
    unittest.main()
