from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.skill_rls.support import artifact, authorize, sandbox, two_item_artifact
from rls_handler import cancel, confirm, execute
from rls_target import SandboxReleaseTarget


class SandboxTargetTests(unittest.TestCase):
    def test_historical_execution_scenario_retains_health_with_version(self):
        with sandbox() as target:
            state = target.snapshot()
            state["health"] = "unhealthy"
            target._write_state(state)
            value = artifact(target_baseline=target.baseline())
            execute(value, target, ["RLI-001"], authorize(value), now="2026-09-04T04:05:00Z")
            confirm(value, target, ["RCF-001"])
            self.assertEqual("1.0.0", target.snapshot()["version"])
            self.assertEqual("unhealthy", value["confirmations"][0]["observed"]["health"])
            self.assertEqual("fail", value["confirmations"][0]["result"])

    def test_original_prose_fixture_remains_unsupported(self):
        from tests.skill_rls.support import fixture_payload
        from rls_vfy_adapter import adapt_vfy_payload
        from rls_items import default_items
        from rls_confirmation_policy import CAPABILITY_ERROR, compile_confirmation
        row = default_items(adapt_vfy_payload(fixture_payload()))[1][0]
        self.assertEqual("target version and basic availability", row["confirmation"])
        self.assertEqual("release 1.0.0 is observable", row["expected"])
        with self.assertRaises(Exception) as caught:
            compile_confirmation(row, "1.0.0")
        self.assertEqual(CAPABILITY_ERROR, getattr(caught.exception, "code", None))

    def test_initial_baseline_is_read_only_and_does_not_materialize(self):
        with tempfile.TemporaryDirectory(prefix="rls-target-") as parent:
            root = Path(parent) / "target"
            target = SandboxReleaseTarget(root, "sandbox-a")
            self.assertEqual(target.baseline(), "N/A — Initial Release")
            self.assertFalse(root.exists())

    def test_success_writes_exact_version(self):
        value = artifact()
        with sandbox() as target:
            execute(value, target, ["RLI-001"], authorize(value), now="2026-09-04T04:05:00Z")
            self.assertEqual(target.snapshot()["version"], "1.0.0")

    def test_no_op_preserves_target_state(self):
        value = artifact()
        with sandbox() as target:
            before = target.snapshot()
            execute(value, target, ["RLI-001"], authorize(value), behaviors={"RLI-001":"no-op"}, now="2026-09-04T04:05:00Z")
            self.assertEqual(target.snapshot(), before)
            self.assertFalse(value["target_effect"])

    def test_partial_records_partial_effect(self):
        value = artifact()
        with sandbox() as target:
            execute(value, target, ["RLI-001"], authorize(value), behaviors={"RLI-001":"partial"}, now="2026-09-04T04:05:00Z")
            self.assertEqual(target.snapshot()["partial"], ["RLI-001"])
            self.assertTrue(value["target_effect"])

    def test_failure_has_evidence_but_no_target_effect(self):
        value = artifact()
        with sandbox() as target:
            execute(value, target, ["RLI-001"], authorize(value), behaviors={"RLI-001":"failure"}, now="2026-09-04T04:05:00Z")
            self.assertFalse(value["target_effect"])
            self.assertEqual(value["evidence"][0]["event"]["result"], "fail")

    def test_evidence_is_content_addressed_and_readable(self):
        value = artifact()
        with sandbox() as target:
            execute(value, target, ["RLI-001"], authorize(value), now="2026-09-04T04:05:00Z")
            reference = value["evidence"][0]["reference"]
            event = json.loads(target.evidence_bytes(reference))
            self.assertEqual(event["item"], "RLI-001")

    def test_evidence_tamper_is_detected(self):
        value = artifact()
        with sandbox() as target:
            execute(value, target, ["RLI-001"], authorize(value), now="2026-09-04T04:05:00Z")
            reference = value["evidence"][0]["reference"]
            digest = reference.removeprefix("SANDBOX-EVD-")
            (target.evidence_dir / f"{digest}.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(Exception) as caught:
                target.evidence_bytes(reference)
            self.assertEqual(getattr(caught.exception, "code", None), "RLS_EVIDENCE_TAMPERED")

    def test_cleanup_removes_only_dedicated_temp_target(self):
        with tempfile.TemporaryDirectory(prefix="rls-target-") as parent:
            root = Path(parent) / "target"
            target = SandboxReleaseTarget(root, "sandbox-a")
            target._write_state(target._default_state())
            self.assertTrue(root.exists())
            target.cleanup()
            self.assertFalse(root.exists())

    def test_execute_rejects_baseline_drift_before_new_effect_or_evidence(self):
        value = artifact()
        auth = authorize(value)
        with sandbox() as target:
            target._write_state(
                {"target": "sandbox-a", "version": "0.9.0", "applied": [], "partial": []}
            )
            before_state = target.snapshot()
            before_evidence = sorted(target.evidence_dir.glob("*.json"))
            with self.assertRaises(Exception) as caught:
                execute(value, target, ["RLI-001"], auth, now="2026-09-04T04:05:00Z")
            self.assertEqual(getattr(caught.exception, "code", None), "RLS_EFFECT_AUTHORIZATION_STALE")
            self.assertEqual(target.snapshot(), before_state)
            self.assertEqual(sorted(target.evidence_dir.glob("*.json")), before_evidence)
            self.assertEqual(value["effect_authorization_history"], [])

    def test_initial_baseline_detects_partial_state_without_a_version(self):
        value = artifact()
        auth = authorize(value)
        with sandbox() as target:
            target._write_state(
                {"target": "sandbox-a", "version": None, "applied": [], "partial": ["RLI-999"]}
            )
            before = target.snapshot()
            self.assertEqual(target.baseline(), before)
            with self.assertRaises(Exception) as caught:
                execute(value, target, ["RLI-001"], auth, now="2026-09-04T04:05:00Z")
            self.assertEqual(getattr(caught.exception, "code", None), "RLS_EFFECT_AUTHORIZATION_STALE")
            self.assertEqual(target.snapshot(), before)

    def test_execute_rejects_drift_from_last_observed_rls_snapshot(self):
        value = two_item_artifact()
        with sandbox() as target:
            execute(
                value,
                target,
                ["RLI-001"],
                authorize(value, ["RLI-001"]),
                now="2026-09-04T04:05:00Z",
            )
            target._write_state(
                {
                    "target": "sandbox-a",
                    "version": "9.9.9",
                    "applied": ["RLI-001"],
                    "partial": [],
                }
            )
            before_state = target.snapshot()
            before_evidence = sorted(target.evidence_dir.glob("*.json"))
            auth = authorize(value, ["RLI-002"])
            with self.assertRaises(Exception) as caught:
                execute(value, target, ["RLI-002"], auth, now="2026-09-04T04:05:00Z")
            self.assertEqual(getattr(caught.exception, "code", None), "RLS_EFFECT_AUTHORIZATION_STALE")
            self.assertEqual(target.snapshot(), before_state)
            self.assertEqual(sorted(target.evidence_dir.glob("*.json")), before_evidence)
            self.assertEqual(len(value["effect_authorization_history"]), 1)

    def test_complete_effect_authorization_is_preserved_as_audit_history(self):
        value = artifact()
        with sandbox() as target:
            execute(value, target, ["RLI-001"], authorize(value), now="2026-09-04T04:05:00Z")
        current = value["effect_authorization"]
        self.assertEqual(value["effect_authorization_history"], [current])
        for field in (
            "authorization_id",
            "rls_artifact_id",
            "revision",
            "release_reference",
            "scope_reference",
            "result_references",
            "vfy_reference",
            "release_target",
            "target_baseline_digest",
            "rli_ids",
            "action_summaries",
            "pre_execution_checklist_digest",
            "authorizer_identity",
            "authorized_at",
            "valid_until",
            "effect_digest",
        ):
            self.assertIn(field, current)

    def test_secret_is_rejected_before_human_confirmation_evidence_is_written(self):
        value = artifact()
        value["confirmations"][0]["subjective"] = True
        with sandbox() as target:
            execute(value, target, ["RLI-001"], authorize(value), now="2026-09-04T04:05:00Z")
            before_evidence = sorted(target.evidence_dir.glob("*.json"))
            with self.assertRaises(Exception) as caught:
                confirm(
                    value,
                    target,
                    ["RCF-001"],
                    human_evidence={
                        "evaluator": "human-a",
                        "observed_at": "2026-09-04T04:06:00Z",
                        "observation": "sk-abcdefghijklmnop1234",
                    },
                )
            self.assertEqual(getattr(caught.exception, "code", None), "RLS_SECRET_REJECTED")
            self.assertEqual(sorted(target.evidence_dir.glob("*.json")), before_evidence)
            self.assertEqual(value["confirmations"][0]["result"], "pending")

    def test_target_identity_mismatch_is_rejected_before_effect(self):
        value = artifact()
        auth = authorize(value)
        with tempfile.TemporaryDirectory(prefix="rls-target-mismatch-") as parent:
            target = SandboxReleaseTarget(Path(parent) / "target", "sandbox-b")
            with self.assertRaises(Exception) as caught:
                execute(value, target, ["RLI-001"], auth, now="2026-09-04T04:05:00Z")
            self.assertEqual(getattr(caught.exception, "code", None), "RLS_EFFECT_AUTHORIZATION_STALE")
            self.assertFalse(target.root.exists())

    def test_cancel_rejects_out_of_band_target_drift(self):
        value = artifact()
        with sandbox() as target:
            target._write_state(
                {"target": "sandbox-a", "version": "0.9.0", "applied": [], "partial": []}
            )
            with self.assertRaises(Exception) as caught:
                cancel(value, target)
            self.assertEqual(getattr(caught.exception, "code", None), "RLS_TARGET_STATE_DRIFT")
            self.assertEqual(value["artifact"]["revision_state"], "open")
            self.assertEqual([], value["evidence"])
            self.assertFalse(value["cancel_requested"])


if __name__ == "__main__":
    unittest.main()
