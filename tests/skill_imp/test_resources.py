from dataclasses import replace
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from tests.skill_imp.support import ImpFixture, tree_bytes
from packages.sdlc_artifact_store import ArtifactStore, compute_sha256
from packages.sdlc_claim_provider import ClaimProvider
from packages.sdlc_resource import apply_operations
from imp_common import ImpError, canonical
from imp_executor import PRE_EXECUTION_CONTRACT, verify_pre_execution_readback
from imp_result import read_member, read_state, snapshot_from_member, snapshot_reference


class ResourceTests(ImpFixture):
    def _multiple_resource_result(self):
        (self.root / "stable").mkdir()
        (self.root / "stable/notes.txt").write_text("uncommitted user notes\n")
        plan = self.plan()
        plan["work_items"][0]["execution_scope"] = ["resource:repo", "resource:stable"]
        plan["delivery_scope"].append({
            "scope_token": "resource:stable", "source_references": [self.dsn_reference + "#CHG-001"],
            "outcome": "Preserve the referenced local companion resource",
        })
        upstream = self.execute_pln(plan=plan)
        self.assertTrue(upstream["ok"], upstream)
        method = self.implementation()
        method["resources"] = [{"id": "repo", "root": "integration"}, {"id": "stable", "root": "stable"}]
        method["steps"][0]["target"] = ["resource:repo"]
        method["operations"][0]["path"] = method["checks"][0]["path"] = "app.txt"
        result = self.create_open(binding=upstream["artifact"]["reference"] + "#WI-001", implementation=method)
        records = read_state(self.stored(result))["resources"]
        return result, records

    def test_multiple_resources_include_unchanged_row_without_losing_user_content(self):
        result, records = self._multiple_resource_result()
        self.assertEqual([row["resource"] for row in records], ["repo", "stable"])
        self.assertEqual((self.root / "stable/notes.txt").read_text(), "uncommitted user notes\n")
        self.assertTrue(self.finish(result)["ok"])

    def test_unchanged_resource_uses_baseline_as_result_and_none_changed_scope(self):
        result, records = self._multiple_resource_result()
        unchanged = records[1]
        self.assertEqual(unchanged["baseline_reference"], unchanged["result_reference"])
        self.assertEqual(unchanged["changed_scope"], [])
        self.assertEqual(unchanged["change_reference"], "N/A")
        self.assertEqual(unchanged["steps"], [])
        self.assertTrue(self.finish(result)["ok"])

    def test_result_ids_are_never_reused_after_a_resource_leaves_scope(self):
        for resource in ("a", "b", "c"):
            (self.root / resource).mkdir()
        (self.root / "a/app.txt").write_text("version=before\n")
        (self.root / "b/notes.txt").write_text("historical resource\n")
        (self.root / "c/notes.txt").write_text("later resource\n")
        self.git("add", "a", "b", "c")
        self.git(
            "-c", "user.name=IMP Fixture",
            "-c", "user.email=imp-fixture@example.invalid",
            "commit", "-qm", "seed resource identity history",
        )

        def revise_plan(reference, resources):
            plan = self.plan()
            plan["work_items"][0]["execution_scope"] = [
                f"resource:{resource}" for resource in resources
            ]
            plan["delivery_scope"] = [
                {
                    "scope_token": f"resource:{resource}",
                    "source_references": [self.dsn_reference + "#CHG-001"],
                    "outcome": f"Deliver resource {resource}",
                }
                for resource in resources
            ]
            result = self.execute_pln(
                operation="revise", reference=reference, plan=plan
            )
            self.assertTrue(result["ok"], result)
            return result["artifact"]["reference"]

        def method(binding, resources, before, after):
            value = self.implementation(
                binding=binding, before=before, after=after
            )
            value["resources"] = [
                {"id": resource, "root": resource} for resource in resources
            ]
            value["steps"][0]["target"] = ["resource:a"]
            value["operations"][0].update(
                resource="a",
                path="app.txt",
                expected_sha256=compute_sha256(
                    (self.root / "a/app.txt").read_bytes()
                ),
            )
            value["checks"][0].update(resource="a", path="app.txt")
            return value

        plan_one = revise_plan(self.pln_reference, ("a", "b"))
        binding_one = plan_one + "#WI-001"
        first = self.finish(self.create_open(
            binding=binding_one,
            implementation=method(binding_one, ("a", "b"), "before", "one"),
        ))
        first_ids = {
            row["resource"]: row["id"]
            for row in read_state(self.stored(first))["resources"]
        }

        plan_two = revise_plan(plan_one, ("a",))
        binding_two = plan_two + "#WI-001"
        second = self.finish(self.create_open(
            command="revise",
            reference=first["artifact"]["reference"],
            binding=binding_two,
            implementation=method(binding_two, ("a",), "one", "two"),
            inputs={"input_references": [binding_two]},
        ))

        plan_three = revise_plan(plan_two, ("a", "c"))
        binding_three = plan_three + "#WI-001"
        third = self.create_open(
            command="revise",
            reference=second["artifact"]["reference"],
            binding=binding_three,
            implementation=method(binding_three, ("a", "c"), "two", "three"),
            inputs={"input_references": [binding_three]},
        )
        third_ids = {
            row["resource"]: row["id"]
            for row in read_state(self.stored(third))["resources"]
        }
        self.assertEqual(first_ids, {"a": "RES-001", "b": "RES-002"})
        self.assertEqual(third_ids, {"a": "RES-001", "c": "RES-003"})

    def test_acquire_and_complete_payload_readback_precede_first_product_write(self):
        observed = []
        def real_write(*args, **kwargs):
            claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
            self.assertEqual(claim.state, "active")
            stored = ArtifactStore.open_read_only(self.root).read_revision(claim.artifact_id, claim.revision)
            self.assertEqual(stored.control.state, "open")
            state = read_state(stored)
            self.assertEqual(state["stage"], "prepared")
            self.assertTrue(state["pre_execution"])
            self.assertIn("EVD-PRE", [item.member_id for item in stored.payload.members])
            evidence = json.loads(read_member(stored, "EVD-PRE").raw_bytes)
            self.assertEqual(evidence["contract"], PRE_EXECUTION_CONTRACT)
            self.assertEqual(evidence["artifact_reference"], f"{claim.artifact_id}@{claim.revision}")
            self.assertEqual(evidence["executor"], claim.owner)
            self.assertEqual(evidence["checklist"]["claim_identity"], state["claim"])
            self.assertEqual(evidence["checklist"]["implementation_binding"], state["binding"])
            self.assertEqual(evidence["checklist"]["implementation_method_contract"], state["method"])
            self.assertEqual(
                len(evidence["checklist"]["input_readiness_check_set"]), 6,
            )
            self.assertTrue(all(
                row["result"] == "pass"
                for row in evidence["checklist"]["input_readiness_check_set"]
            ))
            verify_pre_execution_readback(stored, state)
            self.assertTrue(state["resources"][0]["baseline_reference"].startswith(claim.artifact_id))
            observed.append(claim)
            return apply_operations(*args, **kwargs)
        with patch("imp_executor.apply_operations", side_effect=real_write):
            result = self.create_open()
        self.assertEqual(len(observed), 1)
        self.assertEqual(self.info(result)["attempt"], 1)

    def test_pre_execution_checklist_semantic_tamper_is_rejected(self):
        result = self.create_open()
        stored = self.stored(result)
        state = read_state(stored)
        evidence = read_member(stored, "EVD-PRE")
        value = json.loads(evidence.raw_bytes)
        value["checklist"]["execution_scope"].append("resource:forged")
        value["checklist_digest"] = compute_sha256(canonical(value["checklist"]))
        evidence_raw = canonical(value)
        tampered_evidence = replace(
            evidence,
            raw_bytes=evidence_raw,
            sha256=compute_sha256(evidence_raw),
        )
        tampered_state = json.loads(canonical(state))
        tampered_state["pre_execution"].update(
            evidence_sha256=tampered_evidence.sha256,
            checklist_digest=value["checklist_digest"],
        )
        state_member = read_member(stored, "IMP-STATE")
        state_raw = canonical(tampered_state)
        tampered_state_member = replace(
            state_member,
            raw_bytes=state_raw,
            sha256=compute_sha256(state_raw),
        )
        members = tuple(
            tampered_evidence if item.member_id == "EVD-PRE" else
            tampered_state_member if item.member_id == "IMP-STATE" else item
            for item in stored.payload.members
        )
        tampered = replace(stored, payload=replace(stored.payload, members=members))
        with self.assertRaisesRegex(ImpError, "does not match the current fixed Checklist"):
            verify_pre_execution_readback(tampered, tampered_state)

    def test_dirty_workspace_baseline_contains_staged_unstaged_and_untracked_user_bytes(self):
        (self.root / "user-note.txt").write_text("user staged\n")
        self.git("add", "user-note.txt")
        (self.root / "user-note.txt").write_text("user staged\nuser unstaged\n")
        (self.root / "untracked.txt").write_text("untracked user content\n")
        index = (self.root / ".git/index").read_bytes()
        result = self.create_open()
        stored = self.stored(result)
        row = read_state(stored)["resources"][0]
        baseline = snapshot_from_member(stored, row["baseline_member"], "repo")
        entries = {item["path"]: bytes.fromhex(item["content_hex"]) for item in baseline["entries"]}
        self.assertEqual(entries["user-note.txt"], b"user staged\nuser unstaged\n")
        self.assertEqual(entries["untracked.txt"], b"untracked user content\n")
        self.assertEqual(entries["integration/app.txt"], b"version=before\n")
        self.assertEqual((self.root / "user-note.txt").read_bytes(), entries["user-note.txt"])
        self.assertEqual((self.root / ".git/index").read_bytes(), index)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.original_head)

    def test_existing_user_changes_in_target_are_not_overwritten(self):
        (self.root / "integration/app.txt").write_text("version=before\nuser edit\n")
        before = tree_bytes(self.root)
        result = self.invoke(implementation=self.implementation())
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED")
        self.assertEqual(tree_bytes(self.root), before)

    def test_write_policy_deny_has_no_project_writes(self):
        before = tree_bytes(self.root)
        result = self.invoke(implementation=self.implementation(), policy="deny")
        self.assertEqual(result["next_action"]["code"], "IMP_WRITE_DENIED")
        self.assertEqual(tree_bytes(self.root), before)

    def test_confirm_stops_before_acquire_then_accepts_only_the_exact_preview(self):
        method = self.implementation()
        before = tree_bytes(self.root)
        preview = self.invoke(implementation=method, policy="confirm")
        self.assertEqual(preview["next_action"]["code"], "CONFIRM_IMP_PRODUCT_WRITE")
        self.assertEqual(tree_bytes(self.root), before)
        record = next(item for item in preview["warnings"] if item["code"] == "IMP_PRODUCT_CONFIRMATION")
        confirmation = {"kind": "product_write", "decision": "approved", "subject_digest": record["subject_digest"]}
        result = self.invoke(implementation=method, policy="confirm", confirmations=[confirmation])
        self.assertEqual(result["artifact"]["revision_state"], "open", result)
        self.assertEqual((self.root / "integration/app.txt").read_text(), "version=after\n")

    def test_stale_product_confirmation_does_not_authorize_a_changed_method(self):
        method = self.implementation()
        preview = self.invoke(implementation=method, policy="confirm")
        digest = next(item["subject_digest"] for item in preview["warnings"] if item["code"] == "IMP_PRODUCT_CONFIRMATION")
        method["operations"][0]["after"] = "different"
        before = tree_bytes(self.root)
        result = self.invoke(implementation=method, policy="confirm",
                             confirmations=[{"kind": "product_write", "decision": "approved", "subject_digest": digest}])
        self.assertEqual(result["next_action"]["code"], "CONFIRM_IMP_PRODUCT_WRITE")
        self.assertEqual(tree_bytes(self.root), before)

    def test_entire_operation_batch_is_validated_before_any_scope_write(self):
        method = self.implementation()
        method["operations"].append({
            "resource": "repo", "path": "outside.txt", "step": "STEP-001",
            "op": "write_text", "content": "outside", "expected_sha256": "absent",
        })
        before = tree_bytes(self.root)
        result = self.invoke(implementation=method)
        self.assertEqual(result["errors"][0]["code"], "IMP_SCOPE_VIOLATION")
        self.assertEqual(tree_bytes(self.root), before)

    def test_symlink_escape_is_rejected_without_reading_or_writing_external_product(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / "sentinel"
            target.write_text("external sentinel")
            (self.root / "integration/link").symlink_to(target)
            result = self.invoke(implementation=self.implementation())
            self.assertFalse(result["ok"])
            self.assertEqual(target.read_text(), "external sentinel")
            self.assertEqual(self.claim_count(), 0)

    def test_full_immutable_result_remains_readable_after_live_workspace_changes(self):
        result = self.finish(self.create_open())
        stored = self.stored(result)
        row = read_state(stored)["resources"][0]
        before = stored.payload
        (self.root / "integration/app.txt").write_text("later user work\n")
        snapshot = snapshot_reference(ArtifactStore.open_read_only(self.root), row["result_reference"], "repo", local=stored)
        entry = next(item for item in snapshot["entries"] if item["path"] == "integration/app.txt")
        self.assertEqual(bytes.fromhex(entry["content_hex"]), b"version=after\n")
        checked = self.invoke("check", binding=False, owner=None, reference=result["artifact"]["reference"])
        self.assertTrue(checked["ok"], checked)
        self.assertEqual(self.stored(checked).payload, before)

    def test_one_resource_many_files_still_has_one_result_row(self):
        method = self.implementation()
        method["operations"].append({
            "resource": "repo", "path": "integration/new.txt", "step": "STEP-001",
            "op": "write_text", "content": "new product\n", "expected_sha256": "absent",
        })
        result = self.create_open(implementation=method)
        rows = read_state(self.stored(result))["resources"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["changed_paths"], ["integration/app.txt", "integration/new.txt"])
        self.assertEqual(rows[0]["changed_scope"], ["resource:repo", "path:repo/integration"])

    def test_tampered_context_is_rejected_on_readback_with_no_repair(self):
        result = self.create_open()
        stored = self.stored(result)
        raw = stored.payload.primary_blob.replace(
            ("context: " + self.context_reference).encode(),
            ("context: " + self.pln_reference).encode(), 1,
        )
        writer = ArtifactStore.open_read_write(self.root)
        writer.write_open_revision(replace(stored.payload, primary_blob=raw, primary_sha256=compute_sha256(raw)),
                                   expected_generation=stored.control.generation)
        before = tree_bytes(self.root)
        checked = self.invoke("check", reference=result["artifact"]["reference"])
        self.assertFalse(checked["ok"])
        self.assertEqual(checked["errors"][0]["code"], "IMP_BINDING_MISMATCH")
        self.assertEqual(tree_bytes(self.root), before)

    def test_no_git_commit_push_or_ref_side_effects(self):
        controls = {path.relative_to(self.root / ".git").as_posix(): path.read_bytes()
                    for path in (self.root / ".git").rglob("*") if path.is_file()}
        result = self.finish(self.create_open())
        self.assertTrue(result["ok"])
        after = {path.relative_to(self.root / ".git").as_posix(): path.read_bytes()
                 for path in (self.root / ".git").rglob("*") if path.is_file()}
        self.assertEqual(after, controls)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.original_head)
