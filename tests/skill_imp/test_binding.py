from dataclasses import replace

from tests.skill_imp.support import ImpFixture, FixtureAuthority
from packages.sdlc_artifact_store import ArtifactStore, CanonicalRevisionPayload, compute_sha256
from packages.sdlc_runtime import parse_canonical_artifact
from pln_builder import PlnBuilder
from pln_scope import resolve_inputs
from imp_result import read_state


class BindingTests(ImpFixture):
    def test_artifact_uses_the_real_pln_context_and_full_lineage(self):
        result = self.create_open()
        imp = self.stored(result)
        plan_id, revision = self.pln_reference.split("@")
        plan = ArtifactStore.open_read_only(self.root).read_revision(plan_id, int(revision))
        imp_context = parse_canonical_artifact(imp.payload.primary_blob).front_matter["context"]
        pln_context = parse_canonical_artifact(plan.payload.primary_blob).front_matter["context"]
        self.assertEqual(imp_context, pln_context)
        self.assertEqual(imp_context, self.context_reference)
        self.assertNotEqual(imp_context, self.pln_reference)
        self.assertNotEqual(imp_context, self.binding)
        binding = read_state(imp)["binding"]
        self.assertEqual(binding["plan_reference"], self.pln_reference)
        self.assertEqual(binding["wi_id"], "WI-001")
        self.assertIn(self.context_reference, binding["lineage_references"])

    def test_multiple_work_items_do_not_auto_select_first(self):
        other = self.execute_pln(plan=self.plan(second_imp=True))
        self.assertTrue(other["ok"], other)
        result = self.invoke("auto", binding=False, implementation=self.implementation())
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(result["errors"][0]["code"], "IMP_BINDING_AMBIGUOUS")
        self.assertGreater(len(result["errors"][0]["details"]["candidates"]), 1)
        self.assertEqual(self.claim_count(), 0)

    def test_missing_wi_missing_revision_and_inexact_binding_fail_closed(self):
        for binding in (
            self.pln_reference + "#WI-999",
            self.pln_reference.split("@")[0] + "@99#WI-001",
            self.pln_reference,
            self.pln_reference.split("@")[0] + "@latest#WI-001",
        ):
            with self.subTest(binding=binding):
                result = self.invoke(binding=binding, implementation=self.implementation())
                self.assertFalse(result["ok"], result)
                self.assertEqual(self.claim_count(), 0)

    def test_target_phase_must_be_imp(self):
        result = self.invoke(binding=self.pln_reference + "#WI-002", implementation=self.implementation())
        self.assertEqual(result["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertIn("Target Phase", result["errors"][0]["message"])

    def test_binding_must_match_the_requested_imp_reference(self):
        first = self.create_open()
        other = self.execute_pln()
        result = self.invoke("check", binding=other["artifact"]["reference"] + "#WI-001",
                             reference=first["artifact"]["reference"])
        self.assertEqual(result["errors"][0]["code"], "IMP_BINDING_MISMATCH")

    def test_active_claim_rejects_a_different_exact_binding_revision(self):
        first = self.create_open()
        new_plan = self.revise_plan()
        result = self.invoke("revise", reference=first["artifact"]["reference"],
                             binding=new_plan + "#WI-001")
        self.assertEqual(result["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertEqual(self.info(first)["attempt"], 1)

    def test_complete_req_direct_binding_uses_its_real_context(self):
        direct = self.create_requirement(self.context_reference, dsn_disposition="n/a", pln_disposition="n/a")
        result = self.invoke(binding=direct, implementation=self.implementation(binding=direct))
        self.assertEqual(result["artifact"]["revision_state"], "open", result)
        state = read_state(self.stored(result))
        self.assertIsNone(state["binding"]["wi_id"])
        self.assertEqual(state["binding"]["context_reference"], self.context_reference)

    def test_complete_dsn_direct_binding_requires_pln_not_required(self):
        direct = self.create_scope_with_pln_disposition("n/a")
        method = self.implementation(binding=direct)
        method["steps"][0]["basis_references"] = [direct + "#CHG-001"]
        method["steps"][0]["target"] = ["resource:repo"]
        result = self.invoke(binding=direct, implementation=method)
        self.assertIsNotNone(result["artifact"], result)
        self.assertEqual(result["artifact"]["revision_state"], "open", result)
        self.assertEqual(read_state(self.stored(result))["binding"]["reference"], direct)

    def _invalid_plan_context(self, context):
        writer = ArtifactStore.open_read_write(self.root)
        allocation = writer.allocate_artifact("PLN")
        control = writer.allocate_revision(allocation.artifact_id)
        inputs = resolve_inputs(ArtifactStore.open_read_only(self.root), {"scope_inputs": [self.dsn_reference]})
        inputs = replace(inputs, context_reference=context)
        builder = PlnBuilder(self.root)
        plan = self.plan()
        pending = builder.build(artifact_id=allocation.artifact_id, revision=1,
                                phase_inputs=inputs, candidate=plan, final_confirmation=None)
        final = self.pln_final_confirmation(plan)
        final["subject_digest"] = pending.subject_digest
        build = builder.build(artifact_id=allocation.artifact_id, revision=1, phase_inputs=inputs,
                              candidate=plan, final_confirmation=final)
        writer.write_open_revision(CanonicalRevisionPayload(
            allocation.artifact_id, "PLN", 1, build.status, build.raw_bytes, "text/markdown",
            compute_sha256(build.raw_bytes), build.members, build.manifest,
        ), expected_generation=control.generation)
        writer.freeze_revision(allocation.artifact_id, 1, verifier=FixtureAuthority(self.root))
        return allocation.artifact_id + "@1#WI-001"

    def test_pln_reference_cannot_impersonate_context(self):
        invalid = self._invalid_plan_context(self.pln_reference)
        result = self.invoke(binding=invalid, implementation=self.implementation())
        self.assertFalse(result["ok"])
        self.assertEqual(self.claim_count(), 0)

    def test_inconsistent_upstream_context_fails_closed(self):
        another_context = self._create_context()
        invalid = self._invalid_plan_context(another_context)
        result = self.invoke(binding=invalid, implementation=self.implementation())
        self.assertEqual(result["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertEqual(self.claim_count(), 0)

    def test_missing_pln_context_fails_closed_before_claim(self):
        invalid = self._invalid_plan_context(None)
        result = self.invoke(binding=invalid, implementation=self.implementation())
        self.assertFalse(result["ok"])
        self.assertEqual(self.claim_count(), 0)

    def test_direct_pln_waiver_carries_the_real_exception(self):
        direct = self.create_scope_with_pln_disposition("waived")
        method = self.implementation(binding=direct)
        method["steps"][0]["basis_references"] = [direct + "#CHG-001"]
        method["steps"][0]["target"] = ["resource:repo"]
        opened = self.invoke(binding=direct, implementation=method)
        self.assertIsNotNone(opened["artifact"], opened)
        state = read_state(self.stored(opened))
        self.assertEqual(len(state["method"]["exceptions"]), 1)
        self.assertEqual(state["method"]["exceptions"][0]["state"], "carried")
        self.assertIn("PLN", state["method"]["exceptions"][0]["scope"])
        complete = self.finish(opened)
        self.assertEqual(complete["gate"]["result"], "pass_with_exception")

    def test_lifecycle_applicability_preserves_upstream_fact_without_pending_pass(self):
        result = self.finish(self.create_open())
        state = read_state(self.stored(result))
        rows = state["binding"]["lifecycle_applicability"]
        self.assertEqual([(row["phase"], row["disposition"]) for row in rows], [("VFY", "required"), ("RLS", "n/a")])
        self.assertNotIn("| RLS | pending |", self.stored(result).payload.primary_blob.decode())

    def test_direct_req_dsn_waiver_requires_an_approved_exception(self):
        direct = self.create_requirement(self.context_reference, dsn_disposition="waived", pln_disposition="n/a")
        result = self.invoke(binding=direct, implementation=self.implementation(binding=direct))
        self.assertEqual(result["next_action"]["code"], "RETURN_TO_DESIGN", result)
        self.assertEqual(self.claim_count(), 0)

    def test_direct_dependency_fails_closed_when_current_state_cannot_be_verified(self):
        direct = self.create_requirement(
            self.context_reference, dsn_disposition="n/a", pln_disposition="n/a",
            dependencies=[("DEP-001", "External readiness", "ready", "ready", "unverifiable-state-source")],
        )
        result = self.invoke(binding=direct, implementation=self.implementation(binding=direct))
        self.assertEqual(result["errors"][0]["code"], "IMP_DEPENDENCY_INCOMPLETE", result)
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual((self.root / "integration/app.txt").read_text(), "version=before\n")

    def test_direct_dependency_uses_exact_readback_instead_of_cached_current_state(self):
        direct = self.create_requirement(
            self.context_reference, dsn_disposition="n/a", pln_disposition="n/a",
            dependencies=[("DEP-001", "Immutable Context exists", "frozen", "unknown", self.context_reference)],
        )
        result = self.create_open(binding=direct, implementation=self.implementation(binding=direct))
        self.assertTrue(self.finish(result)["ok"])
