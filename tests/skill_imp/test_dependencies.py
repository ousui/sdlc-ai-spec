from copy import deepcopy
from unittest.mock import patch

from tests.skill_imp.support import ImpFixture, tree_bytes
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_claim_provider import ClaimProvider, ClaimProviderError
from imp_result import read_state


class DependencyTests(ImpFixture):
    def chain(self, *, separate_resources=False):
        plan = self.plan(second_imp=True)
        if separate_resources:
            plan["work_items"][0]["execution_scope"] = ["resource:repo"]
            plan["work_items"][1]["execution_scope"] = ["resource:aux"]
            plan["delivery_scope"].append({
                "scope_token": "resource:aux", "source_references": [self.dsn_reference + "#CHG-001"],
                "outcome": "Apply the dependent local result",
            })
        result = self.execute_pln(plan=plan)
        self.assertTrue(result["ok"], result)
        reference = result["artifact"]["reference"]
        return reference, plan

    def test_missing_predecessor_prevents_acquisition(self):
        plan, _ = self.chain()
        before = tree_bytes(self.root)
        result = self.invoke(binding=plan + "#WI-002", implementation=self.implementation())
        self.assertEqual(result["errors"][0]["code"], "IMP_DEPENDENCY_INCOMPLETE", result)
        self.assertEqual(tree_bytes(self.root), before)

    def test_same_resource_successor_inherits_baseline_and_can_resume_to_complete(self):
        plan, _ = self.chain()
        predecessor = self.finish(self.create_open(binding=plan + "#WI-001"))
        method = self.implementation(before="after", after="second")
        successor = self.create_open(binding=plan + "#WI-002", implementation=method)
        state = read_state(self.stored(successor))
        self.assertEqual(state["request"]["dependencies"], [predecessor["artifact"]["reference"]])
        self.assertEqual(state["resources"][0]["baseline_reference"], self.info(predecessor)["results"][0])
        self.assertIn(predecessor["artifact"]["reference"], state["request"]["artifact_inputs"])
        complete = self.finish(successor)
        self.assertTrue(self.info(complete)["vfy_ready"])

    def test_successor_rejects_workspace_that_does_not_match_predecessor_result(self):
        plan, _ = self.chain()
        self.finish(self.create_open(binding=plan + "#WI-001"))
        (self.root / "user-note.txt").write_text("new user work after the predecessor\n")
        before = tree_bytes(self.root)
        result = self.invoke(binding=plan + "#WI-002",
                             implementation=self.implementation(before="after", after="second"))
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED", result)
        self.assertIsNone(ClaimProvider.open_read_only(self.root).resolve(plan + "#WI-002"))
        self.assertEqual(tree_bytes(self.root), before)

    def test_frozen_complete_retry_abandons_on_permanent_dependency_failure(self):
        plan, candidate = self.chain(separate_resources=True)
        method = self.implementation()
        method["resources"] = [{"id": "repo", "root": "integration"}]
        method["steps"][0]["target"] = ["resource:repo"]
        method["operations"][0]["path"] = method["checks"][0]["path"] = "app.txt"
        predecessor = self.finish(self.create_open(binding=plan + "#WI-001", implementation=method))
        second = deepcopy(method)
        second["resources"] = [{"id": "aux", "root": "aux"}]
        second["steps"][0]["target"] = ["resource:aux"]
        second["operations"] = [{"resource": "aux", "path": "second.txt", "step": "STEP-001",
                                 "op": "write_text", "content": "dependent", "expected_sha256": "absent"}]
        second["checks"][0].update(resource="aux", path="second.txt", expected="dependent")
        opened = self.create_open(binding=plan + "#WI-002", implementation=second)
        with patch.object(ClaimProvider, "complete", side_effect=ClaimProviderError("temporary transport failure")):
            failed = self.invoke("revise", binding=False, reference=opened["artifact"]["reference"],
                                 final=self.confirmation(opened))
        self.assertEqual(failed["artifact"]["revision_state"], "frozen", failed)
        frozen = self.stored(failed)
        candidate["summary"] = "An approved clarification changes the predecessor"
        revised = self.execute_pln(operation="revise", reference=plan, plan=candidate)
        self.assertTrue(revised["ok"], revised)
        rework_binding = revised["artifact"]["reference"] + "#WI-001"
        rework = self.implementation(before="after", after="new-predecessor")
        rework["resources"] = [{"id": "repo", "root": "integration"}]
        rework["steps"][0]["target"] = ["resource:repo"]
        rework["operations"][0]["path"] = rework["checks"][0]["path"] = "app.txt"
        advanced = self.invoke("revise", reference=predecessor["artifact"]["reference"], binding=rework_binding,
                               implementation=rework, inputs={"input_references": [rework_binding]})
        self.assertIsNotNone(advanced["artifact"], advanced)
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(rework_binding).state, "active")
        with patch.object(ArtifactStore, "write_open_revision", side_effect=AssertionError("frozen rewrite")), \
             patch.object(ArtifactStore, "freeze_revision", side_effect=AssertionError("second freeze")):
            recovered = self.invoke("revise", binding=False, reference=failed["artifact"]["reference"])
        self.assertEqual(recovered["errors"][0]["code"], "IMP_COMPLETE_FAILED", recovered)
        claim = ClaimProvider.open_read_only(self.root).resolve(plan + "#WI-002")
        self.assertEqual(claim.state, "abandoned")
        self.assertTrue(claim.abandon_reason.startswith("complete:CLAIM_MISMATCH:"))
        self.assertEqual(self.stored(recovered).payload, frozen.payload)
        self.assertEqual(self.stored(recovered).control.generation, frozen.control.generation)
