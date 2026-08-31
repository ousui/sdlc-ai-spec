from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from packages.sdlc_artifact_store import (
    ArtifactStore,
    CanonicalManifest,
    CanonicalRevisionPayload,
    compute_sha256,
)
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from skill_req.test_review_fixes import ReviewFixTests, runtime


class RequirementCriticalEvalCompletionTests(ReviewFixTests):
    """Critical cases that were not independently asserted by the original suite."""

    def test_frozen_effective_revise_allocates_next_revision(self):
        created = runtime.execute_phase(self.handler, self.request())
        changed = deepcopy(self.requirement())
        changed["summary"] = "允许已授权用户导出当前筛选结果，并记录审计原因。"
        revised = runtime.execute_phase(
            self.handler,
            self.request(
                operation="revise",
                reference=created["artifact"]["reference"],
                requirement=changed,
            ),
        )
        self.assertTrue(revised["ok"])
        self.assertEqual(revised["artifact"]["revision"], 2)
        self.assertEqual(revised["artifact"]["revision_state"], "frozen")
        stored = self.store.read_revision(revised["artifact"]["id"], 2)
        self.assertEqual(stored.control.base_revision, 1)

    def test_acceptance_criteria_gap_fails_req_g_006(self):
        value = deepcopy(self.requirement())
        value["requirements"].append(
            {
                "type": "rule",
                "source_references": ["SRC-001", "GOAL-001"],
                "statement": "导出请求必须记录审计原因。",
            }
        )
        result = runtime.execute_phase(
            self.handler,
            self.request(requirement=value, final=False),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("REQ-G-006", result["gate"]["failed_checks"])
        self.assertEqual(result["artifact"]["artifact_status"], "failed")
        self.assertEqual(result["artifact"]["revision_state"], "open")

    def test_stale_final_confirmation_persists_core_g_009_failure(self):
        request = self.request()
        request["inputs"]["final_confirmation"]["subject_digest"] = (
            "sha256:" + "0" * 64
        )
        result = runtime.execute_phase(self.handler, request)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("CORE-G-009", result["gate"]["failed_checks"])
        self.assertEqual(result["artifact"]["revision_state"], "open")
        self.assertEqual(result["artifact"]["artifact_status"], "failed")
        stored = self.store.read_revision(
            result["artifact"]["id"], result["artifact"]["revision"]
        )
        self.assertEqual(stored.control.state, "open")
        self.assertEqual(stored.payload.artifact_status, "failed")

    def test_non_frozen_ctx_fails_without_fallback_or_req_allocation(self):
        allocation = self.store.allocate_artifact(
            "CTX", now=datetime(2026, 8, 31, 3, 1, tzinfo=timezone.utc)
        )
        control = self.store.allocate_revision(
            allocation.artifact_id,
            now=datetime(2026, 8, 31, 3, 1, tzinfo=timezone.utc),
        )
        raw = b"open context candidate"
        self.store.write_open_revision(
            CanonicalRevisionPayload(
                artifact_id=allocation.artifact_id,
                artifact_type="CTX",
                revision=1,
                artifact_status="ready",
                primary_blob=raw,
                primary_media_type="text/markdown",
                primary_sha256=compute_sha256(raw),
                members=(),
                manifest=CanonicalManifest(
                    raw_bytes=b'{"local_members":[]}',
                    media_type="application/json",
                    local_members=(),
                ),
            ),
            expected_generation=control.generation,
        )
        catalog = ArtifactCatalog(ArtifactStore.open_read_only(self.root))
        before = len(catalog.list_artifacts("REQ"))
        request = self.request()
        request["inputs"]["context_reference"] = allocation.artifact_id + "@1"
        result = runtime.execute_phase(self.handler, request)
        after = len(
            ArtifactCatalog(ArtifactStore.open_read_only(self.root)).list_artifacts(
                "REQ"
            )
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(before, after)
        self.assertIsNone(result["artifact"])


if __name__ == "__main__":
    import unittest

    unittest.main()
