from tests.skill_imp.support import ImpFixture, tree_bytes
from packages.sdlc_claim_provider import ClaimProvider
from imp_result import read_state


class ReworkTests(ImpFixture):
    def test_return_evidence_item_resolves_its_immutable_member_and_digest(self):
        first = self.finish(self.create_open())
        returned = self.vfy_return(first, evidence_item=True)
        opened = self.invoke("revise", binding=False, reference=first["artifact"]["reference"],
                             implementation=self.implementation(before="after", after="reworked"),
                             inputs={"input_references": [returned]})
        self.assertIsNotNone(opened["artifact"], opened)
        self.assertTrue(self.finish(opened)["ok"])

    def test_frozen_return_starts_one_sequence_and_resumes_against_original_subject(self):
        first = self.finish(self.create_open())
        returned = self.vfy_return(first)
        second = self.invoke("revise", binding=False, reference=first["artifact"]["reference"],
                             implementation=self.implementation(before="after", after="reworked"),
                             inputs={"input_references": [returned]})
        self.assertIsNotNone(second["artifact"], second)
        self.assertEqual(second["artifact"]["revision"], 2)
        self.assertEqual(self.info(second)["attempt"], 2)
        state = read_state(self.stored(second))
        self.assertEqual(state["request"]["rework_subjects"], {returned: first["artifact"]["reference"]})
        complete = self.finish(second)
        before = tree_bytes(self.root)
        repeated = self.invoke("revise", binding=False, reference=complete["artifact"]["reference"],
                               inputs={"input_references": [returned]})
        self.assertTrue(repeated["ok"], repeated)
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(self.binding).attempt, 2)
        self.assertEqual(tree_bytes(self.root), before)

    def test_return_with_a_different_binding_or_context_cannot_start_an_attempt(self):
        first = self.finish(self.create_open())
        other = self.execute_pln()
        wrong_binding = self.vfy_return(first, binding=other["artifact"]["reference"] + "#WI-001")
        wrong_context = self.vfy_return(first, context=self._create_context())
        before = tree_bytes(self.root)
        for reference in (wrong_binding, wrong_context):
            with self.subTest(reference=reference):
                result = self.invoke("revise", binding=False, reference=first["artifact"]["reference"],
                                     implementation=self.implementation(before="after", after="reworked"),
                                     inputs={"input_references": [reference]})
                self.assertEqual(result["errors"][0]["code"], "IMP_BINDING_MISMATCH", result)
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(self.binding).attempt, 1)
        self.assertEqual(tree_bytes(self.root), before)

    def test_explicit_abandoned_retry_preserves_artifact_and_creates_next_attempt(self):
        first = self.create_open()
        stopped = self.invoke("abandon", binding=False, reference=first["artifact"]["reference"])
        self.assertTrue(stopped["ok"], stopped)
        second = self.invoke("revise", binding=False, reference=first["artifact"]["reference"],
                             implementation=self.implementation(before="after", after="retried"),
                             inputs={"retry_abandoned": True})
        self.assertIsNotNone(second["artifact"], second)
        self.assertEqual(second["artifact"]["id"], first["artifact"]["id"])
        self.assertEqual(second["artifact"]["revision"], 2)
        self.assertEqual(self.info(second)["attempt"], 2)
        self.assertTrue(self.finish(second)["ok"])

    def test_explicit_abandoned_retry_may_transfer_current_claim_authority(self):
        first = self.create_open()
        stopped = self.invoke(
            "abandon", binding=False, reference=first["artifact"]["reference"],
        )
        self.assertTrue(stopped["ok"], stopped)
        replacement = "replacement-executor"
        second = self.invoke(
            "revise", binding=False, reference=first["artifact"]["reference"],
            owner=replacement,
            implementation=self.implementation(before="after", after="retried"),
            inputs={"retry_abandoned": True},
        )
        self.assertEqual(self.info(second)["attempt"], 2)
        current = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        self.assertEqual((current.owner, current.state), (replacement, "active"))
        completed = self.invoke(
            "revise", binding=False, reference=second["artifact"]["reference"],
            owner=replacement, final=self.confirmation(second),
        )
        self.assertTrue(completed["ok"], completed)
        self.assertEqual(
            ClaimProvider.open_read_only(self.root).resolve(self.binding).owner,
            replacement,
        )

    def test_abandoned_same_return_sequence_cannot_allocate_without_retry(self):
        first = self.finish(self.create_open())
        returned = self.vfy_return(first)
        second = self.invoke(
            "revise", binding=False, reference=first["artifact"]["reference"],
            implementation=self.implementation(before="after", after="reworked"),
            inputs={"input_references": [returned]},
        )
        stopped = self.invoke(
            "abandon", binding=False, reference=second["artifact"]["reference"],
        )
        self.assertTrue(stopped["ok"], stopped)
        rejected = self.invoke(
            "revise", binding=False, reference=second["artifact"]["reference"],
            implementation=self.implementation(before="reworked", after="retried"),
            inputs={"input_references": [returned]},
        )
        self.assertEqual(rejected["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(self.binding).attempt, 2)
        retried = self.invoke(
            "revise", binding=False, reference=second["artifact"]["reference"],
            implementation=self.implementation(before="reworked", after="retried"),
            inputs={"input_references": [returned], "retry_abandoned": True},
        )
        self.assertEqual(self.info(retried)["attempt"], 3)
