from __future__ import annotations

from copy import deepcopy
import unittest

from tests.skill_rls.support import artifact, rewrite_evidence_event, sandbox
from rls_evidence import validate_evidence
from rls_handler import cancel


class RlsEvidenceBindingTests(unittest.TestCase):
    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(expected, getattr(caught.exception, "code", None))
        return caught.exception

    def test_cancel_event_binds_exact_artifact_target_and_rows(self):
        value = artifact()
        with sandbox() as target:
            result = cancel(value, target)
        validate_evidence(result)
        event = result["evidence"][0]["event"]
        self.assertEqual("cancel_before_effect", event["kind"])
        self.assertEqual(result["artifact"]["reference"], event["artifact_reference"])
        self.assertEqual("1.0.0", event["release_reference"])
        self.assertEqual("sandbox-a", event["target"])
        self.assertEqual(["RLI-001", "RCF-001"], event["affected_items"])
        self.assertFalse(event["target_effect"])

    def test_rehashed_cancel_event_cannot_drop_one_rli_binding(self):
        value = artifact()
        with sandbox() as target:
            result = cancel(value, target)
        reference = result["evidence"][0]["reference"]
        rewrite_evidence_event(result, reference, affected_items=["RCF-001"])
        self.assert_code("RLS_EVIDENCE_TAMPERED", validate_evidence, result)

    def test_rehashed_cancel_event_cannot_change_artifact_identity(self):
        value = artifact()
        with sandbox() as target:
            result = cancel(value, target)
        reference = result["evidence"][0]["reference"]
        rewrite_evidence_event(
            result,
            reference,
            artifact_reference="RLS-20260905010000-99@1",
        )
        self.assert_code("RLS_EVIDENCE_TAMPERED", validate_evidence, result)

    def test_rehashed_cancel_event_cannot_change_target(self):
        value = artifact()
        with sandbox() as target:
            result = cancel(value, target)
        reference = result["evidence"][0]["reference"]
        rewrite_evidence_event(result, reference, target="sandbox-b")
        self.assert_code("RLS_EVIDENCE_TAMPERED", validate_evidence, result)

    def test_unreferenced_evidence_is_rejected(self):
        value = artifact()
        with sandbox() as target:
            result = cancel(value, target)
        extra = deepcopy(result["evidence"][0])
        extra["event"]["observed_at"] = "2026-09-05T01:02:03Z"
        from rls_common import canonical_json, sha256_bytes

        payload = (canonical_json(extra["event"]) + "\n").encode("utf-8")
        digest = sha256_bytes(payload)
        extra.update(
            reference=f"SANDBOX-EVD-{digest}",
            sha256=digest,
            locator=f"evidence/{digest}.json",
        )
        result["evidence"].append(extra)
        self.assert_code("RLS_EVIDENCE_TAMPERED", validate_evidence, result)

    def test_second_cancel_has_no_pending_rows_and_is_rejected(self):
        value = artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
            self.assert_code("RLS_CANCEL_NOT_ALLOWED", cancel, frozen, target)

    def test_cancel_rejects_out_of_band_target_drift(self):
        value = artifact()
        with sandbox() as target:
            target._write_state(
                {
                    "target": "sandbox-a",
                    "version": "out-of-band",
                    "applied": [],
                    "partial": [],
                }
            )
            self.assert_code("RLS_TARGET_STATE_DRIFT", cancel, value, target)
        self.assertFalse(value["cancel_requested"])
        self.assertEqual([], value["evidence"])


if __name__ == "__main__":
    unittest.main()
