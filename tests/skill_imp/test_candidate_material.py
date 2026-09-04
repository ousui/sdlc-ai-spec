"""IMP-E041: pre-Claim material is replayed from an exact declared Baseline."""
from unittest.mock import patch

from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_claim_provider import ClaimProvider
from tests.skill_imp.support import ImpFixture, tree_bytes
from imp_candidate import _snapshot_digest
from imp_result import capture, read_state, retained_result_snapshot


class CandidateMaterialTests(ImpFixture):
    def material(self, *, path="integration/app.txt", content="version=after\n"):
        # This unrelated user edit exists before the proposed candidate and is
        # therefore part of both complete snapshots, never replayed as IMP work.
        (self.root / "user-note.txt").write_text("retained user work\n")
        baseline = capture(self.root, "repo")
        (self.root / path).write_text(content)
        candidate = capture(self.root, "repo")
        material = {
            "resource": "repo",
            "baseline_reference": f"vcs:repo@{self.original_head}",
            "changed_paths": [path],
            "candidate_digest": _snapshot_digest(candidate),
        }
        return baseline, candidate, material

    def method_from(self, baseline, *, after="after"):
        method = self.implementation(before="before", after=after)
        entry = next(
            row for row in baseline["entries"] if row["path"] == "integration/app.txt"
        )
        method["operations"][0]["expected_sha256"] = "sha256:" + entry["sha256"]
        return method

    def test_candidate_is_persisted_then_replayed_from_declared_baseline(self):
        baseline, candidate, material = self.material()
        observed = []
        from imp_candidate import restore_declared_baselines

        def after_open_readback(root, roots, records, guard):
            claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
            stored = ArtifactStore.open_read_only(self.root).read_revision(
                claim.artifact_id, claim.revision,
            )
            state = read_state(stored)
            observed.append((
                claim.state,
                stored.control.state,
                state["stage"],
                bool(state["pre_execution"]),
                "EVD-PRE" in {item.member_id for item in stored.payload.members},
                (self.root / "integration/app.txt").read_text(),
            ))
            return restore_declared_baselines(root, roots, records, guard)

        with patch("imp_handler.restore_declared_baselines", after_open_readback):
            opened = self.invoke(
                implementation=self.method_from(baseline),
                inputs={"candidate_material": [material]},
            )
        self.assertEqual(observed, [(
            "active", "open", "prepared", True, True, "version=after\n",
        )])
        self.assertEqual(opened["status"], "action_required", opened)
        stored = self.stored(opened)
        state = read_state(stored)
        self.assertEqual(state["candidate_material"][0]["changed_paths"], ["integration/app.txt"])
        self.assertEqual(retained_result_snapshot(stored, state["resources"][0]), candidate)
        self.assertEqual((self.root / "user-note.txt").read_text(), "retained user work\n")
        completed = self.finish(opened)
        self.assertTrue(self.info(completed)["vfy_ready"])

    def test_preexisting_patch_without_candidate_evidence_cannot_be_backdated(self):
        self.material()
        before = tree_bytes(self.root)
        result = self.invoke(implementation=self.implementation(before="before", after="after"))
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED")
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_candidate_current_state_must_match_the_immutable_evidence(self):
        baseline, candidate, material = self.material()
        (self.root / "integration/app.txt").write_text("version=third-party-drift\n")
        before = tree_bytes(self.root)
        result = self.invoke(
            implementation=self.method_from(baseline),
            inputs={"candidate_material": [material]},
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED")
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_candidate_delta_outside_path_scope_is_rejected_before_claim(self):
        baseline = capture(self.root, "repo")
        (self.root / "user-note.txt").write_text("candidate outside planned path\n")
        candidate = capture(self.root, "repo")
        before = tree_bytes(self.root)
        result = self.invoke(
            implementation=self.method_from(baseline),
            inputs={"candidate_material": [{
                "resource": "repo",
                "baseline_reference": f"vcs:repo@{self.original_head}",
                "changed_paths": ["user-note.txt"],
                "candidate_digest": _snapshot_digest(candidate),
            }]},
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_SCOPE_VIOLATION")
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_method_must_reproduce_the_declared_candidate_result(self):
        baseline, candidate, material = self.material()
        method = self.method_from(baseline, after="different")
        result = self.invoke(
            implementation=method,
            inputs={"candidate_material": [material]},
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_RESULT_INCOMPLETE")
        claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        self.assertEqual(claim.state, "active")

    def test_caller_supplied_snapshot_cannot_fabricate_candidate_baseline(self):
        baseline, candidate, material = self.material()
        fabricated = {
            "resource": "repo", "baseline": baseline, "candidate": candidate,
        }
        before = tree_bytes(self.root)
        result = self.invoke(
            implementation=self.method_from(baseline),
            inputs={"candidate_material": [fabricated]},
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_READINESS_FAILED")
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_candidate_baseline_must_be_the_current_immutable_head(self):
        baseline, _, material = self.material()
        material["baseline_reference"] = "vcs:repo@" + "0" * 40
        before = tree_bytes(self.root)
        result = self.invoke(
            implementation=self.method_from(baseline),
            inputs={"candidate_material": [material]},
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED")
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_candidate_cannot_hide_a_new_unversioned_directory(self):
        baseline = capture(self.root, "repo")
        target = self.root / "integration/generated/product.txt"
        target.parent.mkdir()
        target.write_text("candidate product\n")
        candidate = capture(self.root, "repo")
        method = self.implementation()
        method["operations"] = [{
            "resource": "repo", "path": "integration/generated/product.txt",
            "step": "STEP-001", "op": "write_text",
            "content": "candidate product\n", "expected_sha256": "absent",
        }]
        method["checks"][0].update(
            path="integration/generated/product.txt", expected="candidate product\n",
        )
        result = self.invoke(
            implementation=method,
            inputs={"candidate_material": [{
                "resource": "repo",
                "baseline_reference": f"vcs:repo@{self.original_head}",
                "changed_paths": ["integration/generated/product.txt"],
                "candidate_digest": _snapshot_digest(candidate),
            }]},
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED")
        self.assertEqual(self.claim_count(), 0)
        self.assertNotEqual(baseline, candidate)

    def test_candidate_cannot_remove_a_tracked_parent_before_claim(self):
        baseline = capture(self.root, "repo")
        method = self.method_from(baseline)
        target = self.root / "integration/app.txt"
        target.unlink()
        target.parent.rmdir()
        candidate = capture(self.root, "repo")
        before = tree_bytes(self.root)
        result = self.invoke(
            implementation=method,
            inputs={"candidate_material": [{
                "resource": "repo",
                "baseline_reference": f"vcs:repo@{self.original_head}",
                "changed_paths": ["integration/app.txt"],
                "candidate_digest": _snapshot_digest(candidate),
            }]},
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED")
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(len(
            ArtifactCatalog(ArtifactStore.open_read_only(self.root)).list_artifacts("IMP")
        ), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_candidate_resource_root_must_exist_in_immutable_head(self):
        plan = self.plan()
        plan["work_items"][0]["execution_scope"] = ["resource:repo"]
        upstream = self.execute_pln(plan=plan)
        self.assertTrue(upstream["ok"], upstream)
        binding = upstream["artifact"]["reference"] + "#WI-001"
        target = self.root / "generated/product.txt"
        target.parent.mkdir()
        target.write_text("candidate product\n")
        candidate = capture(target.parent, "repo")
        method = self.implementation(binding=binding)
        method["steps"][0]["target"] = ["resource:repo"]
        method["resources"] = [{"id": "repo", "root": "generated"}]
        method["operations"] = [{
            "resource": "repo", "path": "product.txt", "step": "STEP-001",
            "op": "write_text", "content": "candidate product\n",
            "expected_sha256": "absent",
        }]
        method["checks"][0].update(
            path="product.txt", expected="candidate product\n",
        )
        result = self.invoke(
            implementation=method,
            binding=binding,
            inputs={"candidate_material": [{
                "resource": "repo",
                "baseline_reference": f"vcs:repo@{self.original_head}",
                "changed_paths": ["product.txt"],
                "candidate_digest": _snapshot_digest(candidate),
            }]},
        )
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED")

    def test_candidate_directory_mode_delta_is_not_a_vcs_proven_change(self):
        target = self.root / "integration"
        original_mode = target.stat().st_mode & 0o7777
        try:
            target.chmod(0o700)
            candidate = capture(self.root, "repo")
            result = self.invoke(
                implementation=self.implementation(),
                inputs={"candidate_material": [{
                    "resource": "repo",
                    "baseline_reference": f"vcs:repo@{self.original_head}",
                    "changed_paths": ["integration"],
                    "candidate_digest": _snapshot_digest(candidate),
                }]},
            )
        finally:
            target.chmod(original_mode)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["errors"][0]["code"], "IMP_BASELINE_UNRESOLVED")
        self.assertEqual(self.claim_count(), 0)


if __name__ == "__main__":
    import unittest
    unittest.main()
