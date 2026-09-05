from __future__ import annotations

from copy import deepcopy
import unittest

from tests.skill_rls.support import artifact, authorize, two_item_artifact
from rls_authorization import (
    authorization_binding_diff,
    issue_authorization,
    validate_authorization,
)


class RlsAuthorizationCompleteBindingTests(unittest.TestCase):
    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(expected, getattr(caught.exception, "code", None))
        return caught.exception

    def validate_stale(self, value, authorization, ids=("RLI-001",)):
        return self.assert_code(
            "RLS_EFFECT_AUTHORIZATION_STALE",
            validate_authorization,
            value,
            authorization,
            list(ids),
            now="2026-09-04T04:05:00Z",
        )

    def test_authorization_contains_complete_contract_digests(self):
        value = artifact()
        authorization = authorize(value)
        for field in (
            "rls_artifact_reference",
            "release_contract_digest",
            "selected_rli_contract_digest",
            "release_item_set_digest",
            "confirmation_set_digest",
            "vfy_source_digest",
            "vfy_candidate_digest",
        ):
            with self.subTest(field=field):
                self.assertIn(field, authorization)
        self.assertTrue(
            validate_authorization(
                value,
                authorization,
                ["RLI-001"],
                now="2026-09-04T04:05:00Z",
            )
        )

    def test_every_release_contract_field_is_digest_bound(self):
        changes = {
            "vfy_source_digest": "sha256:" + "d" * 64,
            "vfy_candidate_digest": "sha256:" + "e" * 64,
            "approval_or_trigger_reference": "APPROVAL-CHANGED",
            "release_target_obligations": [],
            "rls_work_item_references": ["PLN-CHANGED"],
            "vfy_conclusions": {
                "con_ver": "fail",
                "con_val": "pass",
                "product_result": "fail",
                "artifact_status": "ready_with_exception",
                "artifact_gate": "pass_with_exception",
            },
        }
        for field, replacement in changes.items():
            value = artifact()
            authorization = authorize(value)
            value["release_contract"][field] = replacement
            with self.subTest(field=field):
                self.validate_stale(value, authorization)

    def test_selected_rli_source_or_prerequisite_drift_invalidates(self):
        for field, replacement in (
            ("source_references", ["IMP-CHANGED@1/RES-001"]),
            ("prerequisite", "changed prerequisite"),
            ("executor", "different-executor"),
            ("action", "different action"),
        ):
            value = artifact()
            authorization = authorize(value)
            value["release_items"][0][field] = replacement
            with self.subTest(field=field):
                self.validate_stale(value, authorization)

    def test_unselected_rli_drift_also_invalidates_current_authorization(self):
        value = two_item_artifact()
        authorization = authorize(value, ("RLI-001",))
        value["release_items"][1]["action"] = "changed unselected action"
        self.validate_stale(value, authorization)

    def test_confirmation_contract_drift_invalidates_current_authorization(self):
        value = artifact()
        authorization = authorize(value)
        value["confirmations"][0]["expected"] = "different target state"
        self.validate_stale(value, authorization)

    def test_item_result_transition_invalidates_reuse_of_old_authorization(self):
        value = artifact()
        authorization = authorize(value)
        value["release_items"][0]["result"] = "success"
        self.validate_stale(value, authorization)

    def test_historical_authorization_survives_only_legal_outcome_fields(self):
        value = artifact()
        authorization = authorize(value)
        value["release_items"][0].update(
            result="success",
            follow_up="none",
            evidence_references=["SANDBOX-EVD-" + "a" * 64],
        )
        self.assertEqual(
            [],
            authorization_binding_diff(
                value, authorization, ["RLI-001"]
            ),
        )

    def test_historical_authorization_still_detects_contract_drift(self):
        value = artifact()
        authorization = authorize(value)
        value["release_items"][0]["result"] = "success"
        value["release_items"][0]["action"] = "changed contract action"
        self.assertIn(
            "selected_rli_contract_digest",
            authorization_binding_diff(
                value, authorization, ["RLI-001"]
            ),
        )

    def test_invalid_validity_window_is_rejected_at_issue_time(self):
        value = artifact()
        self.assert_code(
            "RLS_EFFECT_AUTHORIZATION_STALE",
            issue_authorization,
            value,
            ["RLI-001"],
            "test-authorizer",
            authorized_at="2026-09-04T04:10:00Z",
            valid_until="2026-09-04T04:05:00Z",
        )

    def test_terminal_rli_cannot_receive_new_authorization(self):
        value = artifact()
        value["release_items"][0]["result"] = "success"
        self.assert_code(
            "RLS_EFFECT_AUTHORIZATION_STALE",
            issue_authorization,
            value,
            ["RLI-001"],
            "test-authorizer",
        )


if __name__ == "__main__":
    unittest.main()
