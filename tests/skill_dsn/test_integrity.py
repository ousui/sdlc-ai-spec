from __future__ import annotations

from dataclasses import replace

from packages.sdlc_artifact_store import CanonicalManifest

from . import support_patch  # noqa: F401
from .support import DsnRuntimeFixture

from dsn_verifier import DsnVerifier
from dsn_common import DsnRuntimeError


class DsnIntegrityTests(DsnRuntimeFixture):
    def test_stale_final_confirmation_does_not_freeze(self):
        invocation = self.invocation()
        invocation["inputs"]["final_confirmation"]["subject_digest"] = (
            "sha256:" + "0" * 64
        )
        result = self.execute(invocation)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(result["artifact"]["revision_state"], "open")
        self.assertEqual(result["artifact"]["artifact_status"], "waiting_input")
        self.assertTrue(
            any(
                item["blocked_references"] == "CORE-G-009"
                for item in result["open_items"]
            )
        )

    def test_incomplete_required_domain_remains_open(self):
        design = self.complete_design()
        design["domains"]["DOM-110"] = {
            "disposition": "required",
            "completion": "in_progress",
            "responsible_role": "Backend Architect",
            "basis_references": [self.req_item],
            "reason": "Workflow details are still being completed",
            "design_result_markdown": (
                "## 设计结果 Design Result\n\n"
                "### Draft Flow\n\n"
                "The flow boundary is known, but transitions remain incomplete."
            ),
            "constraints_impacts": [],
            "vfy_points": [],
            "evidence_references": [],
        }
        result = self.execute(self.invocation(design=design, final=False))
        self.assertFalse(result["ok"])
        self.assertEqual(result["artifact"]["revision_state"], "open")
        self.assertEqual(result["artifact"]["artifact_status"], "waiting_input")
        self.assertIn("DSN-G-006", result["open_items"][0]["blocked_references"])

    def test_verifier_rejects_missing_required_member(self):
        created = self.execute(self.invocation())
        stored = self.store.read_revision(created["artifact"]["id"], 1)
        tampered_payload = replace(
            stored.payload,
            members=(),
            manifest=CanonicalManifest(
                raw_bytes=b'{"local_members":[]}',
                media_type="application/json",
                local_members=(),
            ),
        )
        tampered = replace(stored, payload=tampered_payload)
        with self.assertRaises(DsnRuntimeError):
            DsnVerifier(self.root).verify(created["artifact"]["reference"], tampered)

    def test_verifier_rejects_status_mismatch(self):
        created = self.execute(self.invocation())
        stored = self.store.read_revision(created["artifact"]["id"], 1)
        tampered = replace(
            stored,
            payload=replace(stored.payload, artifact_status="ready_with_exception"),
        )
        with self.assertRaises(DsnRuntimeError):
            DsnVerifier(self.root).verify(created["artifact"]["reference"], tampered)


if __name__ == "__main__":
    import unittest

    unittest.main()
