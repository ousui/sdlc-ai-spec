from __future__ import annotations

from copy import deepcopy
import unittest

from tests.skill_rls.support import artifact, authorize
from rls_contract import final_confirmation_digest
from rls_verifier import (
    _validate_checklist,
    _validate_effect_authorizations,
)


class RlsVerifierAuthorizationHistoryTests(unittest.TestCase):
    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(expected, getattr(caught.exception, "code", None))

    def authorized_history(self):
        value = artifact()
        authorization = authorize(value)
        value["effect_authorization"] = deepcopy(authorization)
        value["effect_authorization_history"] = [deepcopy(authorization)]
        return value

    def test_legal_execution_outcome_does_not_self_invalidate_history(self):
        value = self.authorized_history()
        value["release_items"][0].update(
            result="success",
            follow_up="none",
            evidence_references=["SANDBOX-EVD-" + "a" * 64],
        )
        _validate_effect_authorizations(value)

    def test_post_authorization_item_contract_drift_is_rejected(self):
        value = self.authorized_history()
        value["release_items"][0]["result"] = "success"
        value["release_items"][0]["action"] = "changed after authorization"
        self.assert_code(
            "RLS_EFFECT_AUTHORIZATION_STALE",
            _validate_effect_authorizations,
            value,
        )

    def test_checklist_ignores_outcomes_but_binds_item_contract(self):
        value = artifact()
        value["release_items"][0].update(
            result="success",
            follow_up="none",
            evidence_references=["SANDBOX-EVD-" + "b" * 64],
        )
        _validate_checklist(value)
        value["release_items"][0]["prerequisite"] = "changed"
        self.assert_code("RLS_CONTRACT_INVALID", _validate_checklist, value)

    def test_final_confirmation_digest_is_stable_across_freeze_transition(self):
        value = artifact()
        before = final_confirmation_digest(value)
        value["artifact"]["revision_state"] = "frozen"
        self.assertEqual(before, final_confirmation_digest(value))


if __name__ == "__main__":
    unittest.main()
