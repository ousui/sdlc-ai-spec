from copy import deepcopy
from unittest.mock import patch

from tests.skill_imp.support import ImpFixture, OWNER, tree_bytes
from packages.sdlc_artifact_store import ArtifactStore, compute_sha256
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_claim_provider import ClaimProvider, ClaimProviderError
from packages.sdlc_runtime.authority import (
    DELEGATED_AUTHORITY_HEADERS, DELEGATED_EXCLUDED_AUTHORITY,
    DELEGATED_INDEPENDENCE,
)
from imp_result import read_state


class StateMachineTests(ImpFixture):
    def delegated_confirmation(self, opened, *, reviewer="reviewer-run-02",
                               reviewed=OWNER, variant="valid"):
        bindings = self.info(opened)["final_confirmation_bindings"]
        authority_dir = self.root / ".sdlc/authority"
        basis = authority_dir / "imp-delegation.txt"
        basis.write_text("reviewer-run-02 may confirm IMP contract compliance\n")
        basis_ref = basis.relative_to(self.root).as_posix() + "@" + compute_sha256(
            basis.read_bytes()
        )
        values = [
            basis_ref,
            reviewer,
            "Delegated Independent Reviewer",
            reviewed,
            DELEGATED_INDEPENDENCE,
            bindings["control_input_digest"],
            bindings["evaluation_contract_set"],
            bindings["check_set_result_digest"],
            DELEGATED_EXCLUDED_AUTHORITY,
        ]
        if variant == "digest_mismatch":
            values[7] = "sha256:" + "0" * 64
        lines = [
            "---",
            "contract: sdlc-ai-spec/final-confirmation-authority/v1",
            f"artifact: {opened['artifact']['reference']}",
            "decision: approved",
            "decided_at: 2026-09-03T10:00:00Z",
            "---",
            "",
            "| " + " | ".join(DELEGATED_AUTHORITY_HEADERS) + " |",
            "|" + "|".join("---" for _ in DELEGATED_AUTHORITY_HEADERS) + "|",
            "| " + " | ".join(values) + " |",
        ]
        if variant == "missing_decided_at":
            lines.pop(4)
        elif variant == "invalid_decided_at":
            lines[4] = "decided_at: 2026-09-03T10:00:00+99:99"
        elif variant == "missing_row":
            lines.pop()
        raw = ("\n".join(lines) + "\n").encode()
        authority = authority_dir / f"delegated-{variant}-{reviewer}.md"
        authority.write_bytes(raw)
        return {
            "mode": "delegated",
            "confirmer": reviewer,
            "role": "Delegated Independent Reviewer",
            "reviewed_executor": reviewed,
            "authority_reference": authority.relative_to(self.root).as_posix()
            + "@" + compute_sha256(raw),
            "accepted_exception_references": [],
            "confirmed_at": "2026-09-03T10:00:00Z",
            "subject_digest": self.info(opened)["subject_digest"],
            **bindings,
        }

    def test_same_active_request_is_idempotent_without_empty_revision(self):
        method = self.implementation()
        first = self.create_open(implementation=method)
        old = self.stored(first)
        second = self.invoke(implementation=method)
        self.assertEqual(second["artifact"], first["artifact"])
        self.assertEqual(self.stored(second).control.generation, old.control.generation)
        self.assertEqual(len(ArtifactCatalog(ArtifactStore.open_read_only(self.root)).list_revisions(old.control.artifact_id)), 1)

    def test_active_open_revise_stays_on_the_same_revision(self):
        opened = self.create_open()
        original = self.stored(opened)
        revised = self.invoke(
            "revise", binding=False, reference=opened["artifact"]["reference"],
        )
        self.assertEqual(revised["artifact"]["reference"], opened["artifact"]["reference"])
        self.assertEqual(self.info(revised)["attempt"], 1)
        self.assertEqual(self.stored(revised).control.generation, original.control.generation)

    def test_active_revision_cannot_remove_an_already_executed_operation(self):
        opened = self.create_open()
        before = tree_bytes(self.root)
        original_state = read_state(self.stored(opened))
        method = deepcopy(original_state["method"])
        method["operations"] = []
        rejected = self.invoke(
            "revise", binding=False, reference=opened["artifact"]["reference"],
            implementation=method,
        )
        self.assertEqual(rejected["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertEqual(tree_bytes(self.root), before)
        self.assertEqual(read_state(self.stored(opened)), original_state)

    def test_active_revision_cannot_insert_before_the_executed_prefix(self):
        opened = self.create_open()
        before = tree_bytes(self.root)
        original_state = read_state(self.stored(opened))
        method = deepcopy(original_state["method"])
        method["operations"].insert(0, {
            "resource": "repo", "path": "integration/early.txt", "step": "STEP-001",
            "op": "write_text", "content": "must not run\n", "expected_sha256": "absent",
        })
        rejected = self.invoke(
            "revise", binding=False, reference=opened["artifact"]["reference"],
            implementation=method,
        )
        self.assertEqual(rejected["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertEqual(tree_bytes(self.root), before)
        self.assertEqual(read_state(self.stored(opened)), original_state)

    def test_active_owner_and_input_mismatch_are_rejected(self):
        result = self.create_open()
        before = tree_bytes(self.root)
        owner = self.invoke("revise", reference=result["artifact"]["reference"], owner="other-owner")
        self.assertEqual(owner["errors"][0]["code"], "IMP_OWNER_MISMATCH")
        inputs = self.invoke("revise", reference=result["artifact"]["reference"],
                             inputs={"input_references": [self.dsn_reference]})
        self.assertEqual(inputs["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertEqual(tree_bytes(self.root), before)

    def test_different_lineage_resource_conflict_fails_closed(self):
        self.create_open()
        other = self.execute_pln()
        method = self.implementation()
        method["operations"] = [{
            "resource": "repo", "path": "integration/other.txt", "step": "STEP-001",
            "op": "write_text", "content": "other", "expected_sha256": "absent",
        }]
        method["checks"][0].update(path="integration/other.txt", expected="other")
        result = self.invoke(binding=other["artifact"]["reference"] + "#WI-001", implementation=method, owner="other-owner")
        self.assertEqual(result["errors"][0]["code"], "IMP_RESOURCE_CONFLICT", result)
        self.assertFalse((self.root / "integration/other.txt").exists())
        self.assertEqual(len(ArtifactCatalog(ArtifactStore.open_read_only(self.root)).list_artifacts("IMP")), 1)

    def test_check_is_absolutely_read_only_and_never_executes_checks(self):
        result = self.create_open()
        before = tree_bytes(self.root)
        with patch.object(ArtifactStore, "open_read_write", side_effect=AssertionError("Store write")), \
             patch.object(ClaimProvider, "open_read_write", side_effect=AssertionError("Claim write")), \
             patch("imp_handler.execute", side_effect=AssertionError("product execution")), \
             patch("imp_handler.execute_checks", side_effect=AssertionError("Check execution")):
            checked = self.invoke("check", binding=False, owner=None, reference=result["artifact"]["reference"])
        self.assertEqual(checked["status"], "action_required", checked)
        self.assertEqual(tree_bytes(self.root), before)

    def test_missing_and_stale_final_confirmation_keep_open(self):
        result = self.create_open()
        self.assertEqual(self.stored(result).payload.artifact_status, "waiting_input")
        stale = self.confirmation(result)
        stale["subject_digest"] = "sha256:" + "0" * 64
        with patch.object(ClaimProvider, "complete", side_effect=AssertionError("premature complete")), \
             patch.object(ArtifactStore, "freeze_revision", side_effect=AssertionError("premature freeze")):
            checked = self.invoke("revise", binding=False, reference=result["artifact"]["reference"], final=stale)
        self.assertEqual(checked["errors"][0]["code"], "IMP_FINAL_CONFIRMATION_STALE", checked)
        self.assertEqual(checked["artifact"]["revision_state"], "open")
        self.assertEqual(self.stored(checked).payload.artifact_status, "waiting_input")

    def test_stale_final_confirmation_does_not_freeze(self):
        opened = self.create_open()
        stale = self.confirmation(opened)
        stale["subject_digest"] = "sha256:" + "0" * 64
        checked = self.invoke(
            "revise", binding=False, reference=opened["artifact"]["reference"],
            final=stale,
        )
        self.assertEqual(checked["errors"][0]["code"], "IMP_FINAL_CONFIRMATION_STALE")
        self.assertEqual(checked["artifact"]["revision_state"], "open")
        self.assertEqual(self.stored(checked).payload.artifact_status, "waiting_input")

    def test_delegated_confirmation_requires_exact_independent_authority(self):
        opened = self.create_open()
        for variant, reviewer, reviewed in (
            ("valid", OWNER, OWNER),
            ("valid", "reviewer-run-02", "another-executor"),
            ("missing_decided_at", "reviewer-run-02", OWNER),
            ("invalid_decided_at", "reviewer-run-02", OWNER),
            ("missing_row", "reviewer-run-02", OWNER),
            ("digest_mismatch", "reviewer-run-02", OWNER),
        ):
            with self.subTest(variant=variant):
                confirmation = self.delegated_confirmation(
                    opened, reviewer=reviewer, reviewed=reviewed, variant=variant
                )
                rejected = self.invoke(
                    "revise",
                    binding=False,
                    reference=opened["artifact"]["reference"],
                    final=confirmation,
                )
                self.assertFalse(rejected["ok"], rejected)
                self.assertEqual(
                    rejected["errors"][0]["code"],
                    "IMP_FINAL_CONFIRMATION_STALE",
                )
                self.assertEqual(rejected["artifact"]["revision_state"], "open")

        accepted = self.invoke(
            "revise",
            binding=False,
            reference=opened["artifact"]["reference"],
            final=self.delegated_confirmation(opened),
        )
        self.assertTrue(accepted["ok"], accepted)
        self.assertEqual(accepted["artifact"]["revision_state"], "frozen")

    def test_freeze_always_precedes_claim_complete(self):
        first = self.create_open()
        original = ClaimProvider.complete
        calls = []
        def complete(provider, lineage, **kwargs):
            stored = ArtifactStore.open_read_only(self.root).read_revision(kwargs["artifact_id"], kwargs["revision"])
            self.assertEqual(stored.control.state, "frozen")
            self.assertEqual(stored.payload.artifact_status, "ready")
            calls.append(lineage)
            return original(provider, lineage, **kwargs)
        with patch.object(ClaimProvider, "complete", new=complete):
            result = self.finish(first)
        self.assertEqual(len(calls), 1)
        self.assertTrue(self.info(result)["vfy_ready"])

    def test_complete_transient_failure_retries_without_rewriting_frozen_artifact(self):
        opened = self.create_open()
        with patch.object(ClaimProvider, "complete", side_effect=ClaimProviderError("temporary provider failure")):
            failed = self.invoke("revise", binding=False, reference=opened["artifact"]["reference"],
                                 final=self.confirmation(opened))
        self.assertEqual(failed["errors"][0]["code"], "IMP_COMPLETE_FAILED", failed)
        self.assertEqual(failed["artifact"]["revision_state"], "frozen")
        frozen = self.stored(failed)
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(self.binding).state, "active")
        with patch.object(ArtifactStore, "write_open_revision", side_effect=AssertionError("frozen rewrite")), \
             patch.object(ArtifactStore, "freeze_revision", side_effect=AssertionError("second freeze")):
            retried = self.invoke("revise", binding=False, reference=failed["artifact"]["reference"])
        self.assertTrue(retried["ok"], retried)
        self.assertEqual(self.stored(retried).payload, frozen.payload)
        self.assertEqual(self.stored(retried).control.generation, frozen.control.generation)

    def test_completed_without_rework_does_not_allocate_another_attempt(self):
        result = self.finish(self.create_open())
        before = tree_bytes(self.root)
        checked = self.invoke("revise", binding=False, reference=result["artifact"]["reference"])
        self.assertTrue(checked["ok"], checked)
        self.assertEqual(self.info(checked)["attempt"], 1)
        self.assertEqual(tree_bytes(self.root), before)

    def test_completed_handler_retry_requires_the_current_owner(self):
        result = self.finish(self.create_open())
        before = tree_bytes(self.root)
        rejected = self.invoke(owner="different-owner")
        self.assertFalse(rejected["ok"], rejected)
        self.assertEqual(rejected["errors"][0]["code"], "IMP_OWNER_MISMATCH")
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(self.binding).attempt, 1)
        self.assertEqual(tree_bytes(self.root), before)

    def test_rework_revision_cannot_repurpose_stable_method_identities(self):
        first = self.finish(self.create_open())
        binding = self.revise_plan() + "#WI-001"

        def step_semantics(method):
            method["steps"][0]["purpose"] = "Perform an unrelated semantic action"

        def block_semantics(method):
            method["steps"][0]["blocks"][0]["resource_or_effect"] = "An unrelated effect"

        def check_semantics(method):
            method["checks"][0].update(
                kind="project_command", path=None, cwd=".",
                command=["python", "-m", "compileall", "integration"],
            )

        for mutate in (step_semantics, block_semantics, check_semantics):
            method = self.implementation(binding=binding, before="after", after="reworked")
            mutate(method)
            before = tree_bytes(self.root)
            with self.subTest(mutation=mutate.__name__):
                rejected = self.invoke(
                    "revise", reference=first["artifact"]["reference"], binding=binding,
                    implementation=method, inputs={"input_references": [binding]},
                )
                self.assertFalse(rejected["ok"], rejected)
                self.assertEqual(rejected["errors"][0]["code"], "IMP_BINDING_MISMATCH")
                self.assertEqual(
                    ClaimProvider.open_read_only(self.root).resolve(binding).attempt, 1
                )
                self.assertEqual(tree_bytes(self.root), before)

    def test_updated_exact_binding_with_rework_creates_stable_artifact_new_attempt(self):
        first = self.finish(self.create_open())
        binding = self.revise_plan() + "#WI-001"
        method = self.implementation(binding=binding, before="after", after="reworked")
        second = self.invoke("revise", reference=first["artifact"]["reference"], binding=binding,
                             implementation=method, inputs={"input_references": [binding]})
        self.assertEqual(second["artifact"]["id"], first["artifact"]["id"], second)
        self.assertEqual(second["artifact"]["revision"], 2)
        self.assertEqual(self.info(second)["attempt"], 2)
        self.assertEqual(read_state(self.stored(second))["claim"]["rework_references"], [binding])
        self.assertEqual((self.root / "integration/app.txt").read_text(), "version=reworked\n")

    def test_completed_binding_change_without_complete_rework_set_is_rejected(self):
        first = self.finish(self.create_open())
        binding = self.revise_plan() + "#WI-001"
        result = self.invoke("revise", reference=first["artifact"]["reference"], binding=binding)
        self.assertEqual(result["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(binding).attempt, 1)

    def test_abandon_validates_owner_attempt_and_revision_before_any_write(self):
        result = self.create_open()
        reference = result["artifact"]["reference"]
        before = tree_bytes(self.root)
        for kwargs in (
            {"owner": "other-owner"},
            {"inputs": {"expected_attempt": 99}},
            {"reference": reference.split("@")[0] + "@99"},
        ):
            arguments = {"reference": reference, **kwargs}
            rejected = self.invoke("abandon", binding=False, **arguments)
            self.assertFalse(rejected["ok"], rejected)
        self.assertEqual(tree_bytes(self.root), before)
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(self.binding).state, "active")

    def test_abandon_revision_then_claim_with_matching_reason(self):
        result = self.create_open()
        original = ClaimProvider.abandon
        def abandon(provider, lineage, **kwargs):
            stored = ArtifactStore.open_read_only(self.root).read_revision(kwargs["artifact_id"], kwargs["revision"])
            self.assertEqual(stored.control.state, "abandoned")
            self.assertEqual(stored.control.abandon_reason, kwargs["reason"])
            return original(provider, lineage, **kwargs)
        with patch.object(ClaimProvider, "abandon", new=abandon):
            abandoned = self.invoke("abandon", binding=False, reference=result["artifact"]["reference"])
        self.assertTrue(abandoned["ok"], abandoned)
        self.assertEqual(self.info(abandoned)["claim_state"], "abandoned")

    def test_claim_termination_failure_keeps_active_and_can_resume_abandon(self):
        result = self.create_open()
        with patch.object(ClaimProvider, "abandon", side_effect=ClaimProviderError("temporary terminal failure")):
            failed = self.invoke("abandon", binding=False, reference=result["artifact"]["reference"])
        self.assertFalse(failed["ok"])
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(self.binding).state, "active")
        self.assertEqual(self.stored(result).control.state, "abandoned")
        retried = self.invoke("abandon", binding=False, reference=result["artifact"]["reference"])
        self.assertTrue(retried["ok"], retried)

    def test_ordinary_abandon_cannot_cancel_frozen_history(self):
        result = self.finish(self.create_open())
        before = tree_bytes(self.root)
        abandoned = self.invoke("abandon", binding=False, reference=result["artifact"]["reference"])
        self.assertFalse(abandoned["ok"])
        self.assertEqual(tree_bytes(self.root), before)
