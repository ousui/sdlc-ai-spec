from copy import deepcopy

from tests.skill_imp.support import ImpFixture
from imp_common import CONSIDERATIONS, ImpError
from imp_method import validate_stable_identities
from imp_result import read_state


class MethodTests(ImpFixture):
    def test_fixed_consideration_order_and_stable_block_ids_are_persisted(self):
        result = self.create_open()
        method = read_state(self.stored(result))["method"]
        self.assertEqual(tuple(row["name"] for row in method["considerations"]), CONSIDERATIONS)
        self.assertEqual(method["steps"][0]["blocks"][0]["id"], "EFF-001")

    def test_required_na_waived_and_pending_dispositions_are_enforced(self):
        cases = []
        method = self.implementation()
        method["considerations"][-1]["steps"] = []
        cases.append(method)
        method = self.implementation()
        method["considerations"][0]["basis"] = ""
        cases.append(method)
        method = self.implementation()
        method["considerations"][0].update(disposition="waived", exception="EX-999")
        cases.append(method)
        method = self.implementation()
        method["considerations"][0]["disposition"] = "pending"
        cases.append(method)
        method = self.implementation()
        method["steps"][0]["blocks"] = []
        cases.append(method)
        for candidate in cases:
            with self.subTest(candidate=candidate):
                result = self.invoke(implementation=candidate)
                self.assertFalse(result["ok"])
                self.assertEqual(self.claim_count(), 0)
                self.assertEqual((self.root / "integration/app.txt").read_text(), "version=before\n")

    def test_na_consideration_requires_an_objective_basis(self):
        method = self.implementation()
        method["considerations"][0]["basis"] = ""
        result = self.invoke(implementation=method)
        self.assertFalse(result["ok"], result)
        self.assertEqual(self.claim_count(), 0)

    def test_waived_consideration_requires_an_approved_exception(self):
        method = self.implementation()
        method["considerations"][0].update(disposition="waived", exception="EX-999")
        result = self.invoke(implementation=method)
        self.assertFalse(result["ok"], result)
        self.assertEqual(self.claim_count(), 0)

    def test_pending_consideration_cannot_reach_the_gate(self):
        method = self.implementation()
        method["considerations"][0]["disposition"] = "pending"
        result = self.invoke(implementation=method)
        self.assertFalse(result["ok"], result)
        self.assertEqual(self.claim_count(), 0)

    def test_step_file_decomposition_and_mixed_failure_boundaries_are_rejected(self):
        method = self.implementation()
        method["steps"][0]["split_by"] = "file"
        first = self.invoke(implementation=method)
        self.assertEqual(first["next_action"]["code"], "RETURN_TO_PLAN")
        method = self.implementation()
        method["steps"][0]["failure_boundaries"] = ["database transaction", "external message"]
        second = self.invoke(implementation=method)
        self.assertFalse(second["ok"])
        self.assertEqual(self.claim_count(), 0)

    def test_file_decomposed_step_returns_to_plan(self):
        method = self.implementation()
        method["steps"][0]["split_by"] = "file"
        result = self.invoke(implementation=method)
        self.assertEqual(result["next_action"]["code"], "RETURN_TO_PLAN", result)
        self.assertEqual(self.claim_count(), 0)

    def test_mixed_transaction_or_failure_boundaries_require_split_steps(self):
        method = self.implementation()
        method["steps"][0]["failure_boundaries"] = [
            "database transaction", "external message",
        ]
        result = self.invoke(implementation=method)
        self.assertFalse(result["ok"], result)
        self.assertEqual(self.claim_count(), 0)

    def test_new_public_abstraction_without_dsn_decision_returns_upstream(self):
        for field in ("new_public_abstraction", "new_dependency", "cross_module_interface"):
            method = self.implementation()
            method[field] = True
            result = self.invoke(implementation=method)
            self.assertEqual(result["next_action"]["code"], "RETURN_TO_DESIGN", result)
            self.assertEqual(self.claim_count(), 0)

    def test_failed_local_check_cannot_freeze_or_claim_vfy_ready(self):
        method = self.implementation()
        method["checks"][0]["expected"] = "wrong local expectation"
        result = self.invoke(implementation=method)
        self.assertEqual(result["gate"]["result"], "fail", result)
        self.assertEqual(result["artifact"]["revision_state"], "open")
        self.assertFalse(self.info(result)["vfy_ready"])

    def test_external_effect_or_arbitrary_command_check_is_never_executed(self):
        method = self.implementation()
        method["external_effects"] = ["remote target"]
        external = self.invoke(implementation=method)
        self.assertFalse(external["ok"])
        method = self.implementation()
        method["checks"][0].update(kind="shell", command=["git", "push"])
        shell = self.invoke(implementation=method)
        self.assertFalse(shell["ok"])
        self.assertEqual(self.claim_count(), 0)

    def test_project_check_id_cannot_change_its_bounded_command_role(self):
        previous = self.implementation()
        previous["checks"][0].update(
            kind="project_command",
            path=None,
            cwd=".",
            command=["npm", "run", "test"],
        )
        current = deepcopy(previous)
        current["checks"][0]["command"] = ["npm", "run", "lint"]
        with self.assertRaisesRegex(ImpError, "new semantics"):
            validate_stable_identities(previous, current)
