from contextlib import closing, ExitStack
from dataclasses import replace
import sqlite3
from unittest.mock import patch

from tests.skill_imp.support import ImpFixture, OWNER, tree_bytes
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_claim_provider import AcquireRequest, ClaimProvider, ClaimProviderError
from packages.sdlc_lifecycle import LifecycleQueryError, LifecycleQueryService
from packages.sdlc_phasekit import CheckOutcome, PhaseInputs, render_phase_artifact


class ImpLifecycleTests(ImpFixture):
    def query(self, service=None):
        return (service or LifecycleQueryService(self.root)).inspect_requirement(
            self.requirement_reference
        )

    def current(self, projection, binding=None):
        return next(item for item in projection.current_claims
                    if item.binding_reference == (binding or self.binding))

    def assert_not_ready(self, projection):
        self.assertEqual(projection.vfy_inputs, ())
        self.assertEqual(projection.vfy_results, ())
        self.assertFalse(any(item.vfy_ready for item in projection.current_claims))
        self.assertFalse(any(action.phase in {"VFY", "RLS"}
                             for action in projection.next_actions))

    def chain_plan(self, count=2):
        candidate = self.plan(second_imp=True)
        if count == 3:
            third = dict(candidate["work_items"][1])
            third.update(id="WI-003", depends_on=["WI-002"],
                         outcome="Apply the third local change",
                         completion_criteria="Third immutable result exists")
            candidate["work_items"].insert(2, third)
            candidate["work_items"][-1].update(id="WI-004", depends_on=["WI-003"])
        result = self.execute_pln(operation="revise", reference=self.pln_reference,
                                  plan=candidate)
        self.assertTrue(result["ok"], result)
        self.pln_reference = result["artifact"]["reference"]
        self.binding = self.pln_reference + "#WI-001"
        return self.pln_reference

    def completed_chain(self, count=2):
        plan = self.chain_plan(count)
        results = [self.finish(self.create_open())]
        before = "after"
        for index in range(2, count + 1):
            after = f"step{index}"
            results.append(self.finish(self.create_open(
                binding=plan + f"#WI-{index:03d}",
                implementation=self.implementation(before=before, after=after),
            )))
            before = after
        return results

    def test_plan_without_claim_store_stays_read_only(self):
        before = tree_bytes(self.root)
        projection = self.query()
        self.assertEqual(projection.current_claims, ())
        self.assertEqual(projection.next_actions[0].code, "START_WORK_ITEM")
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_active_open_claim_shows_owner_attempt_and_imp_frontier(self):
        opened = self.create_open()
        projection = self.query()
        current = self.current(projection)
        self.assertEqual((current.owner, current.attempt, current.claim_state),
                         (OWNER, 1, "active"))
        self.assertEqual(current.revision_state, "open")
        self.assertFalse(current.completed)
        self.assertEqual(projection.frontier, (opened["artifact"]["reference"],))
        self.assertTrue(any(edge.declared_reference == self.binding and edge.relation == "control_input"
                            and edge.target_reference == opened["artifact"]["reference"] for edge in projection.edges))
        self.assert_not_ready(projection)

    def test_claim_before_materialization_is_not_an_artifact(self):
        claim = ClaimProvider.open_read_write(self.root).acquire(AcquireRequest(
            self.binding, OWNER, ("resource:repo", "path:repo/integration"),
        ))
        before = tree_bytes(self.root)
        projection = self.query()
        current = self.current(projection)
        self.assertEqual(current.artifact_reference, f"{claim.artifact_id}@{claim.revision}")
        self.assertFalse(current.materialized)
        self.assertNotIn(current.artifact_reference, {node.reference for node in projection.nodes})
        self.assertEqual(projection.overall_state, "action_required")
        self.assert_not_ready(projection)
        self.assertEqual(tree_bytes(self.root), before)

    def test_frozen_with_active_claim_cannot_enter_vfy(self):
        opened = self.create_open()
        with patch.object(ClaimProvider, "complete", side_effect=ClaimProviderError("temporary failure")):
            failed = self.invoke("revise", binding=False, reference=opened["artifact"]["reference"],
                                 final=self.confirmation(opened))
        self.assertEqual(failed["artifact"]["revision_state"], "frozen", failed)
        projection = self.query()
        self.assertEqual(self.current(projection).claim_state, "active")
        self.assertFalse(self.current(projection).completed)
        self.assertEqual(projection.next_actions[0].phase, "IMP")
        self.assert_not_ready(projection)

    def test_frozen_completed_result_is_ready_and_installed_vfy_is_explicit(self):
        completed = self.finish(self.create_open())
        projection = self.query()
        current = self.current(projection)
        self.assertTrue(current.completed)
        self.assertTrue(current.vfy_ready)
        self.assertEqual(projection.vfy_inputs, (completed["artifact"]["reference"],))
        self.assertEqual(current.results[0]["result_reference"], self.info(completed)["results"][0])
        action = projection.next_actions[0]
        self.assertEqual(action.phase, "VFY")
        self.assertTrue(action.skill_available)
        self.assertIn("/sdlc-500-vfy create", action.command)

    def test_abandoned_claim_requires_explicit_retry_or_rework(self):
        opened = self.create_open()
        self.assertTrue(self.invoke("abandon", binding=False,
                                    reference=opened["artifact"]["reference"])["ok"])
        projection = self.query()
        self.assertEqual(projection.overall_state, "action_required")
        self.assertEqual(projection.next_actions[0].code, "RETRY_OR_REWORK_IMP")
        self.assertEqual(self.current(projection).claim_state, "abandoned")
        self.assert_not_ready(projection)

    def test_abandoned_history_does_not_block_completed_retry(self):
        first = self.create_open()
        self.invoke("abandon", binding=False, reference=first["artifact"]["reference"])
        second = self.invoke("revise", binding=False, reference=first["artifact"]["reference"],
                             implementation=self.implementation(before="after", after="retried"),
                             inputs={"retry_abandoned": True})
        completed = self.finish(second)
        projection = self.query()
        self.assertTrue(self.current(projection).completed)
        self.assertEqual(self.current(projection).attempt, 2)
        self.assertEqual(projection.frontier, (completed["artifact"]["reference"],))
        self.assertIn(first["artifact"]["reference"], {node.reference for node in projection.nodes})
        self.assertFalse(projection.blockers)

    def test_rework_excludes_old_completed_revision_and_return_from_frontier(self):
        first = self.finish(self.create_open())
        returned = self.vfy_return(first)
        second = self.invoke("revise", binding=False, reference=first["artifact"]["reference"],
                             implementation=self.implementation(before="after", after="reworked"),
                             inputs={"input_references": [returned]})
        self.assertIsNotNone(second["artifact"], second)
        projection = self.query()
        self.assertEqual(len(projection.current_claims), 1)
        self.assertEqual(self.current(projection).attempt, 2)
        self.assertEqual(projection.frontier, (second["artifact"]["reference"],))
        self.assert_not_ready(projection)

    def test_query_reuse_reads_current_claim_after_completion(self):
        opened = self.create_open()
        service = LifecycleQueryService(self.root)
        self.assert_not_ready(self.query(service))
        completed = self.finish(opened)
        self.assertEqual(self.query(service).vfy_inputs, (completed["artifact"]["reference"],))

    def test_direct_req_binding_has_current_claim_and_vfy_input(self):
        self.requirement_reference = self.create_requirement(
            self.context_reference, dsn_disposition="n/a", pln_disposition="n/a",
        )
        self.binding = self.requirement_reference
        completed = self.finish(self.create_open())
        projection = self.query()
        self.assertTrue(self.current(projection).completed)
        self.assertEqual(projection.vfy_inputs, (completed["artifact"]["reference"],))

    def test_existing_downstream_artifact_keeps_its_lifecycle_frontier(self):
        completed = self.finish(self.create_open())
        authority = self._authority("downstream-projection")
        def produce(identity, revision):
            return render_phase_artifact(
                artifact_id=identity, phase="VFY", revision=revision, status="ready", profile="full",
                phase_inputs=PhaseInputs(self.context_reference, (completed["artifact"]["reference"],)),
                title="Canonical downstream query fixture", sections=(),
                checks={f"CORE-G-{index:03d}": CheckOutcome("pass", "Fixture authority") for index in range(1, 10)},
                open_items=(), evidence=(), exceptions=(), lifecycle_applicability=(),
                final_confirmation={"mode": "human", "confirmer": "fixture-owner", "role": "Fixture Authority",
                                    "authority_reference": authority, "confirmed_at": "2026-09-03T10:00:00Z"},
                gate_result="pass", evaluation_contract_set="fixture-downstream@sha256:" + "d" * 64,
                evaluator="Fixture producer",
            )
        downstream = self._source("VFY", produce)
        projection = self.query()
        self.assertEqual(projection.frontier, (downstream,))
        self.assertFalse(any(action.phase == "VFY" for action in projection.next_actions))
        self.assertEqual(projection.next_actions[0].phase, "RLS")

    def test_new_plan_revision_does_not_rebind_an_active_claim(self):
        self.create_open()
        new_plan = self.revise_plan()
        projection = self.query()
        self.assert_not_ready(projection)
        decision = next(action for action in projection.next_actions if action.code == "RESOLVE_IMP_BINDING")
        self.assertIn(new_plan + "#WI-001", decision.reason)
        self.assertIsNone(decision.command)

    def test_claim_change_during_query_fails_closed(self):
        self.finish(self.create_open())
        claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        original = ClaimProvider.resolve
        def resolve(provider, reference):
            if reference == claim.binding_lineage:
                return replace(claim, attempt=claim.attempt + 1)
            return original(provider, reference)
        before = tree_bytes(self.root)
        with patch.object(ClaimProvider, "resolve", resolve), self.assertRaises(LifecycleQueryError) as raised:
            self.query()
        self.assertEqual(raised.exception.code, "IMP_CLAIM_CHANGED")
        self.assertEqual(tree_bytes(self.root), before)

    def test_completed_claim_with_missing_exact_revision_does_not_fall_back(self):
        self.finish(self.create_open())
        claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        missing = replace(claim, revision=claim.revision + 1)
        with patch.object(ClaimProvider, "resolve", return_value=missing), \
             patch.object(ClaimProvider, "resolve_artifact", return_value=missing):
            projection = self.query()
        self.assert_not_ready(projection)
        self.assertIn("IMP_REVISION_MISSING", {item["code"] for item in projection.blockers})

    def test_failed_local_gate_is_a_visible_blocker(self):
        method = self.implementation()
        method["checks"][0]["expected"] = "a different result"
        result = self.invoke(implementation=method)
        self.assertIsNotNone(result["artifact"], result)
        projection = self.query()
        self.assertEqual(projection.overall_state, "blocked")
        self.assertIn("IMP_GATE_FAILED", {item["code"] for item in projection.blockers})
        self.assert_not_ready(projection)

    def test_independent_resources_keep_both_terminal_vfy_inputs(self):
        candidate = self.plan(second_imp=True)
        candidate["work_items"][0]["execution_scope"] = ["resource:repo"]
        candidate["work_items"][1].update(execution_scope=["resource:aux"], depends_on=[])
        candidate["work_items"][2]["depends_on"] = ["WI-001", "WI-002"]
        candidate["delivery_scope"].append({
            "scope_token": "resource:aux", "source_references": [self.dsn_reference + "#CHG-001"],
            "outcome": "Deliver the independent auxiliary result",
        })
        plan = self.execute_pln(operation="revise", reference=self.pln_reference, plan=candidate)
        self.assertTrue(plan["ok"], plan)
        self.pln_reference = plan["artifact"]["reference"]
        self.binding = self.pln_reference + "#WI-001"
        method = self.implementation()
        method["resources"] = [{"id": "repo", "root": "integration"}]
        method["steps"][0]["target"] = ["resource:repo"]
        method["operations"][0]["path"] = method["checks"][0]["path"] = "app.txt"
        first = self.finish(self.create_open(implementation=method))
        method = self.implementation()
        method["resources"] = [{"id": "aux", "root": "aux"}]
        method["steps"][0]["target"] = ["resource:aux"]
        method["operations"] = [{"resource": "aux", "path": "second.txt", "step": "STEP-001",
                                 "op": "write_text", "content": "independent", "expected_sha256": "absent"}]
        method["checks"][0].update(resource="aux", path="second.txt", expected="independent")
        second = self.finish(self.create_open(binding=self.pln_reference + "#WI-002", implementation=method))
        projection = self.query()
        self.assertEqual(set(projection.vfy_inputs), {first["artifact"]["reference"], second["artifact"]["reference"]})
        self.assertTrue(all(item.completed and item.vfy_ready for item in projection.current_claims))

    def test_vfy_selects_terminal_result_per_resource_in_multi_resource_artifact(self):
        candidate = self.plan(second_imp=True)
        candidate["work_items"][0]["execution_scope"] = ["resource:repo", "resource:aux"]
        candidate["work_items"][1]["execution_scope"] = ["resource:repo"]
        candidate["delivery_scope"].append({
            "scope_token": "resource:aux", "source_references": [self.dsn_reference + "#CHG-001"],
            "outcome": "Retain the auxiliary resource as part of the atomic result",
        })
        plan = self.execute_pln(operation="revise", reference=self.pln_reference, plan=candidate)
        self.assertTrue(plan["ok"], plan)
        self.pln_reference = plan["artifact"]["reference"]
        self.binding = self.pln_reference + "#WI-001"
        (self.root / "aux").mkdir()
        (self.root / "aux/retained.txt").write_text("retained auxiliary content")
        method = self.implementation()
        method["resources"] = [{"id": "repo", "root": "integration"}, {"id": "aux", "root": "aux"}]
        method["steps"][0]["target"] = ["resource:repo"]
        method["operations"][0]["path"] = method["checks"][0]["path"] = "app.txt"
        first = self.finish(self.create_open(implementation=method))
        method = self.implementation(before="after", after="second")
        method["resources"] = [{"id": "repo", "root": "integration"}]
        method["steps"][0]["target"] = ["resource:repo"]
        method["operations"][0]["path"] = method["checks"][0]["path"] = "app.txt"
        second = self.finish(self.create_open(binding=self.pln_reference + "#WI-002", implementation=method))
        projection = self.query()
        selected = {row["resource"]: row for row in projection.vfy_results}
        self.assertEqual(set(selected), {"repo", "aux"})
        self.assertEqual(selected["repo"]["artifact_reference"], second["artifact"]["reference"])
        self.assertEqual(selected["aux"]["artifact_reference"], first["artifact"]["reference"])
        self.assertEqual(selected["repo"]["result_reference"], self.info(second)["results"][0])

    def test_occupied_resource_is_not_offered_as_a_start_candidate(self):
        self.create_open()
        other = self.execute_pln()
        self.assertTrue(other["ok"], other)
        projection = self.query()
        self.assertFalse(any(action.code == "START_WORK_ITEM" for action in projection.next_actions))
        self.assertEqual(projection.next_actions[0].code, "RESUME_IMP")

    def test_missing_claim_store_does_not_make_frozen_imp_usable(self):
        self.finish(self.create_open())
        with closing(sqlite3.connect(self.root / ".sdlc/store.sqlite3")) as connection:
            connection.execute("DELETE FROM imp_claims")
            connection.commit()
        before = tree_bytes(self.root)
        projection = self.query()
        self.assertEqual(projection.overall_state, "blocked")
        self.assertIn("IMP_CLAIM_MISSING", {item["code"] for item in projection.blockers})
        self.assert_not_ready(projection)
        self.assertEqual(tree_bytes(self.root), before)

    def test_corrupt_claim_store_fails_closed_without_repair(self):
        self.finish(self.create_open())
        with closing(sqlite3.connect(self.root / ".sdlc/store.sqlite3")) as connection:
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute("UPDATE imp_claims SET state='bogus'")
            connection.commit()
        before = tree_bytes(self.root)
        with self.assertRaises(LifecycleQueryError) as raised:
            self.query()
        self.assertEqual(raised.exception.code, "IMP_CLAIM_STORE_INVALID")
        self.assertEqual(tree_bytes(self.root), before)

    def test_claim_identity_mismatch_is_not_completed(self):
        self.finish(self.create_open())
        claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        for changed in (replace(claim, owner="another-owner"), replace(claim, attempt=2),
                        replace(claim, execution_scope=("resource:other",))):
            with self.subTest(claim=changed), \
                 patch.object(ClaimProvider, "resolve", return_value=changed), \
                 patch.object(ClaimProvider, "resolve_artifact", return_value=changed):
                projection = self.query()
                self.assertFalse(self.current(projection).completed)
                self.assertIn("IMP_CLAIM_MISMATCH", {item["code"] for item in projection.blockers})
                self.assert_not_ready(projection)

    def test_completed_claim_cannot_authorize_open_revision(self):
        self.create_open()
        claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        with patch.object(ClaimProvider, "resolve", return_value=replace(claim, state="completed")), \
             patch.object(ClaimProvider, "resolve_artifact", return_value=replace(claim, state="completed")):
            projection = self.query()
        self.assertEqual(projection.overall_state, "blocked")
        self.assertFalse(self.current(projection).completed)
        self.assert_not_ready(projection)

    def test_missing_immutable_result_member_is_not_completed(self):
        completed = self.finish(self.create_open())
        stored = self.stored(completed)
        result_member = self.info(completed)["results"][0].split("/", 1)[1]
        broken = replace(stored, payload=replace(stored.payload, members=tuple(
            item for item in stored.payload.members if item.member_id != result_member
        )))
        original = ArtifactStore.read_revision
        def read(store, artifact_id, revision):
            if (artifact_id, revision) == (stored.control.artifact_id, stored.control.revision):
                return broken
            return original(store, artifact_id, revision)
        with patch.object(ArtifactStore, "read_revision", read):
            projection = self.query()
        self.assertFalse(self.current(projection).completed)
        self.assert_not_ready(projection)

    def test_predecessor_completion_enables_next_imp_work_item_before_vfy(self):
        plan = self.chain_plan()
        self.finish(self.create_open())
        projection = self.query()
        self.assert_not_ready(projection)
        self.assertTrue(any(action.code == "START_WORK_ITEM" and action.phase == "IMP"
                            and plan + "#WI-002" in (action.command or "")
                            for action in projection.next_actions))

    def test_same_resource_chain_uses_only_current_completed_terminal(self):
        first, second = self.completed_chain()
        projection = self.query()
        self.assertTrue(all(item.completed for item in projection.current_claims))
        self.assertEqual(projection.vfy_inputs, (second["artifact"]["reference"],))
        self.assertFalse(self.current(projection).vfy_ready)
        self.assertTrue(self.current(projection, self.pln_reference + "#WI-002").vfy_ready)
        self.assertNotIn(first["artifact"]["reference"], projection.frontier)

    def test_new_predecessor_attempt_invalidates_all_transitive_successors(self):
        results = self.completed_chain(3)
        self.git("add", "integration/app.txt")
        self.git("-c", "user.name=IMP Fixture", "-c", "user.email=imp-fixture@example.invalid",
                 "commit", "-qm", "record isolated completed chain")
        returned = self.vfy_return(results[0])
        rework = self.invoke("revise", binding=False, reference=results[0]["artifact"]["reference"],
                             implementation=self.implementation(before="step3", after="reworked"),
                             inputs={"input_references": [returned]})
        self.assertIsNotNone(rework["artifact"], rework)
        projection = self.query()
        self.assert_not_ready(projection)
        for item in ("WI-002", "WI-003"):
            successor = self.current(projection, self.pln_reference + "#" + item)
            self.assertFalse(successor.completed)
            self.assertIn("IMP_DEPENDENCY_CHANGED", {blocker["code"] for blocker in successor.blockers})

    def test_unordered_completed_results_for_one_resource_are_ambiguous(self):
        self.finish(self.create_open())
        self.git("add", "integration/app.txt")
        self.git("-c", "user.name=IMP Fixture", "-c", "user.email=imp-fixture@example.invalid",
                 "commit", "-qm", "record isolated first result")
        other = self.execute_pln()
        self.assertTrue(other["ok"], other)
        binding = other["artifact"]["reference"] + "#WI-001"
        self.finish(self.create_open(binding=binding,
                                      implementation=self.implementation(before="after", after="other")))
        projection = self.query()
        self.assertEqual(projection.overall_state, "blocked")
        self.assertIn("IMP_RESULT_AMBIGUOUS", {item["code"] for item in projection.blockers})
        self.assert_not_ready(projection)

    def test_query_does_not_call_write_apis_or_change_bytes_or_mtime(self):
        self.finish(self.create_open())
        before = {path.relative_to(self.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.root.rglob("*") if path.is_file()}
        with ExitStack() as guard:
            for owner, names in (
                (ArtifactStore, ("open_read_write", "initialize", "write_open_revision",
                                 "freeze_revision", "abandon_revision")),
                (ClaimProvider, ("open_read_write", "initialize", "acquire", "complete", "abandon")),
            ):
                for name in names:
                    guard.enter_context(patch.object(owner, name, side_effect=AssertionError(name)))
            projection = self.query()
        self.assertTrue(self.current(projection).completed)
        after = {path.relative_to(self.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
