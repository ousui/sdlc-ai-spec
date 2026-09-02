from __future__ import annotations

from copy import deepcopy

from .support import PlnFixture


class PlnContractMatrixTests(PlnFixture):
    def assert_gate_failure(self, plan, check_id):
        result = self.execute_pln(plan=plan, final=False)
        self.assertFalse(result["ok"])
        self.assertIn(check_id, result["gate"]["failed_checks"])
        return result

    def test_vfy_is_always_required_and_needs_work_item(self):
        plan = self.plan()
        plan["lifecycle_applicability"][1]["disposition"] = "n/a"
        self.assert_gate_failure(plan, "PLN-G-005")
        plan = self.plan()
        plan["work_items"] = [plan["work_items"][0]]
        self.assert_gate_failure(plan, "PLN-G-005")

    def test_non_required_phase_cannot_have_pseudo_work_item(self):
        plan = self.plan()
        plan["lifecycle_applicability"][2]["disposition"] = "n/a"
        plan["work_items"].append(
            {
                "id": "WI-003",
                "target_phase": "RLS",
                "outcome": "Publish to the formal target",
                "execution_scope": ["environment:production"],
                "source_references": [self.dsn_reference + "#CHG-001"],
                "constraint_references": [],
                "depends_on": ["WI-002"],
                "completion_criteria": "A final Release Conclusion exists",
                "expected_evidence": "Target-side version and availability evidence",
                "responsible_role": "Release Operator",
            }
        )
        self.assert_gate_failure(plan, "PLN-G-005")

    def test_required_rls_work_item_has_exactly_one_environment(self):
        plan = self.plan()
        plan["lifecycle_applicability"][2]["disposition"] = "required"
        plan["work_items"].append(
            {
                "id": "WI-003",
                "target_phase": "RLS",
                "outcome": "Publish the verified result",
                "execution_scope": ["environment:staging", "environment:production"],
                "source_references": [self.dsn_reference + "#CHG-001"],
                "constraint_references": [],
                "depends_on": ["WI-002"],
                "completion_criteria": "The target Release Record is terminal",
                "expected_evidence": "Release Item and target confirmation evidence",
                "responsible_role": "Release Operator",
            }
        )
        self.assert_gate_failure(plan, "PLN-G-003")

    def test_path_token_must_belong_to_declared_resource(self):
        plan = self.plan()
        plan["work_items"][0]["execution_scope"] = [
            "resource:repo",
            "path:other/integration",
        ]
        self.assert_gate_failure(plan, "PLN-G-004")

    def test_unknown_authority_fields_are_rejected(self):
        plan = self.plan()
        plan["work_items"][0]["status"] = "in_progress"
        self.assert_gate_failure(plan, "PLN-G-003")
        plan = self.plan()
        plan["work_items"][0]["parallel"] = True
        self.assert_gate_failure(plan, "PLN-G-003")

    def test_generic_completion_or_evidence_is_not_sufficient(self):
        for field, value in (
            ("completion_criteria", "completed"),
            ("expected_evidence", "evidence"),
        ):
            with self.subTest(field=field):
                plan = self.plan()
                plan["work_items"][0][field] = value
                self.assert_gate_failure(plan, "PLN-G-003")

    def test_missing_responsible_role_remains_action_required(self):
        plan = self.plan()
        plan["work_items"][0]["responsible_role"] = ""
        result = self.execute_pln(plan=plan, final=False)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(result["gate"]["result"], "pending")

    def test_unconfirmed_obligation_and_scope_expansion_fail(self):
        plan = self.plan()
        plan["obligations"].append(self.dsn_reference + "#CHG-999")
        self.assert_gate_failure(plan, "PLN-G-002")
        plan = self.plan()
        plan["work_items"][0]["source_references"] = [
            self.dsn_reference + "#CHG-999"
        ]
        self.assert_gate_failure(plan, "PLN-G-006")

    def test_duplicate_work_item_semantics_are_rejected(self):
        plan = self.plan()
        duplicate = deepcopy(plan["work_items"][0])
        duplicate["id"] = "WI-002"
        plan["work_items"] = [plan["work_items"][0], duplicate]
        plan["lifecycle_applicability"][1]["disposition"] = "n/a"
        self.assert_gate_failure(plan, "PLN-G-003")


if __name__ == "__main__":
    import unittest

    unittest.main()
