from __future__ import annotations

from dataclasses import replace
import unittest

from tests.skill_rls.support import artifact, candidate, sandbox
from rls_handler import cancel, revise


class RlsRevisionCandidateBindingTests(unittest.TestCase):
    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(expected, getattr(caught.exception, "code", None))
        return caught.exception

    def test_exact_same_candidate_is_no_change(self):
        value = artifact()
        result = revise(
            value,
            candidate(),
            target="sandbox-a",
            target_baseline="N/A — Initial Release",
        )
        self.assertIsNot(result, value)
        self.assertIn("RLS_NO_CHANGE", result["warnings"])
        self.assertEqual(value["artifact"]["reference"], result["artifact"]["reference"])

    def test_open_revision_rejects_vfy_contract_delta(self):
        changed = replace(
            candidate(),
            vfy_reference="VFY-20260904170001-02@2",
            source_digest="sha256:" + "d" * 64,
            candidate_digest="sha256:" + "e" * 64,
        )
        error = self.assert_code(
            "RLS_CONTRACT_INVALID",
            revise,
            artifact(),
            changed,
            target="sandbox-a",
            target_baseline="N/A — Initial Release",
        )
        self.assertIn("vfy_reference", error.details["changed_fields"])
        self.assertIn("vfy_source_digest", error.details["changed_fields"])

    def test_frozen_revision_turns_vfy_delta_into_new_revision(self):
        value = artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
            changed = replace(
                candidate(),
                vfy_reference="VFY-20260904170001-02@2",
                source_digest="sha256:" + "d" * 64,
                candidate_digest="sha256:" + "e" * 64,
            )
            revised = revise(
                frozen,
                changed,
                target="sandbox-a",
                target_baseline=target.baseline(),
            )
        self.assertEqual(frozen["artifact"]["id"], revised["artifact"]["id"])
        self.assertEqual(2, revised["artifact"]["revision"])
        self.assertEqual(changed.vfy_reference, revised["release_contract"]["vfy_reference"])
        self.assertEqual(changed.source_digest, revised["release_contract"]["vfy_source_digest"])
        self.assertIsNone(revised["effect_authorization"])

    def test_changed_vfy_obligation_rebuilds_confirmation_contract(self):
        value = artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
            obligation = {
                "reference": "VFY-20260904090000-01@1#VFM-099",
                "confirmation": "new target-side invariant",
                "expected": "new invariant is observable",
                "evidence_requirement": "new immutable target snapshot",
            }
            changed = replace(
                candidate(),
                release_target_obligations=(obligation,),
                candidate_digest="sha256:" + "f" * 64,
            )
            revised = revise(
                frozen,
                changed,
                target="sandbox-a",
                target_baseline=target.baseline(),
            )
        self.assertEqual([obligation["reference"]], revised["confirmations"][0]["source_references"])
        self.assertEqual(obligation["confirmation"], revised["confirmations"][0]["confirmation"])
        self.assertEqual(obligation["expected"], revised["confirmations"][0]["expected"])

    def test_explicit_retry_reacquires_baseline_and_authorization(self):
        value = artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
            retried = revise(
                frozen,
                candidate(),
                target="sandbox-a",
                target_baseline={"target": "sandbox-a", "version": "0.9.0", "applied": [], "partial": []},
                retry=True,
            )
        self.assertEqual(2, retried["artifact"]["revision"])
        self.assertEqual(
            {"target": "sandbox-a", "version": "0.9.0", "applied": [], "partial": []},
            retried["release_contract"]["target_baseline"],
        )
        self.assertIsNone(retried["effect_authorization"])
        self.assertEqual([], retried["effect_authorization_history"])

    def test_target_change_creates_distinct_artifact(self):
        value = artifact()
        changed = revise(
            value,
            candidate(),
            target="sandbox-b",
            target_baseline="N/A — Initial Release",
        )
        self.assertNotEqual(value["artifact"]["id"], changed["artifact"]["id"])
        self.assertEqual("sandbox-b", changed["release_contract"]["release_target"])


if __name__ == "__main__":
    unittest.main()
