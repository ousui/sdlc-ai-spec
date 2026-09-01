from __future__ import annotations

from packages.sdlc_runtime import parse_canonical_artifact

from . import support_patch  # noqa: F401
from .support import DsnRuntimeFixture


class DsnRuntimeTests(DsnRuntimeFixture):
    def test_complete_create_freezes_ready_artifact_set(self):
        result = self.execute(self.invocation())
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["gate"]["result"], "pass")
        self.assertEqual(result["artifact"]["revision_state"], "frozen")
        stored = self.store.read_revision(
            result["artifact"]["id"], result["artifact"]["revision"]
        )
        self.assertEqual(
            tuple(item.member_id for item in stored.payload.members),
            ("DOM-510",),
        )
        self.assertEqual(
            tuple(item.member_id for item in stored.payload.manifest.local_members),
            ("DOM-510",),
        )
        self.store.verify_digest(
            result["artifact"]["id"], result["artifact"]["revision"]
        )

    def test_missing_final_confirmation_persists_waiting_input(self):
        result = self.execute(self.invocation(final=False))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(result["artifact"]["revision_state"], "open")
        self.assertEqual(result["artifact"]["artifact_status"], "waiting_input")
        self.assertTrue(
            any(item["blocked_references"] == "CORE-G-009" for item in result["open_items"])
        )

    def test_boundary_is_required_before_allocation(self):
        design = self.complete_design()
        design.pop("boundary")
        before = self.catalog().list_artifacts("DSN")
        result = self.execute(self.invocation(design=design, final=False))
        after = self.catalog().list_artifacts("DSN")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(result["errors"][0]["code"], "DESIGN_BOUNDARY_REQUIRED")
        self.assertEqual(before, after)

    def test_open_revision_is_revised_in_place(self):
        first = self.execute(self.invocation(final=False))
        reference = first["artifact"]["id"] + "@1"
        result = self.execute(
            self.invocation(operation="revise", reference=reference)
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["artifact"]["revision"], 1)
        self.assertEqual(result["artifact"]["revision_state"], "frozen")

    def test_frozen_no_change_does_not_allocate_revision(self):
        first = self.execute(self.invocation())
        reference = first["artifact"]["reference"]
        result = self.execute(
            self.invocation(operation="revise", reference=reference)
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["artifact"]["revision"], 1)
        self.assertEqual(result["warnings"][0]["code"], "NO_CHANGE")
        revisions = self.catalog().list_revisions(first["artifact"]["id"])
        self.assertEqual(tuple(item.revision for item in revisions), (1,))

    def test_frozen_change_creates_next_revision(self):
        first = self.execute(self.invocation())
        design = self.complete_design()
        design["summary"] = "为筛选结果提供异步、可验证的导出设计。"
        design["target_state_summary"] = "用户获得异步生成的准确导出文件"
        design["changes"][0]["target_state"] = "提供异步导出能力"
        result = self.execute(
            self.invocation(
                operation="revise",
                reference=first["artifact"]["reference"],
                design=design,
            )
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["artifact"]["revision"], 2)
        self.assertEqual(result["artifact"]["revision_state"], "frozen")

    def test_check_is_strictly_read_only(self):
        created = self.execute(self.invocation())
        store_path = self.root / ".sdlc" / "store.sqlite3"
        before = store_path.read_bytes()
        result = self.execute(
            self.invocation(
                operation="check",
                reference=created["artifact"]["reference"],
            )
        )
        after = store_path.read_bytes()
        self.assertTrue(result["ok"])
        self.assertEqual(before, after)

    def test_multiple_requirements_from_same_context_are_supported(self):
        second = self.create_requirement(self.context_reference)
        scopes = (self.requirement_reference, second)
        result = self.execute(self.invocation(scope_inputs=scopes))
        self.assertTrue(result["ok"])
        stored = self.store.read_revision(result["artifact"]["id"], 1)
        front = parse_canonical_artifact(stored.payload.primary_blob).front_matter
        self.assertEqual(tuple(front["inputs"]), scopes)

    def test_requirements_from_different_contexts_fail_before_allocation(self):
        second_context = "CTX-20260901090000-99@1"
        second = self.create_requirement(second_context)
        before = self.catalog().list_artifacts("DSN")
        result = self.execute(
            self.invocation(scope_inputs=(self.requirement_reference, second))
        )
        after = self.catalog().list_artifacts("DSN")
        self.assertFalse(result["ok"])
        self.assertIn("different CTX", result["errors"][0]["message"])
        self.assertEqual(before, after)

    def test_only_required_domains_create_members(self):
        design = self.complete_design(require_workflow=True)
        result = self.execute(self.invocation(design=design))
        self.assertTrue(result["ok"])
        stored = self.store.read_revision(result["artifact"]["id"], 1)
        self.assertEqual(
            tuple(item.member_id for item in stored.payload.members),
            ("DOM-110", "DOM-510"),
        )

    def test_secret_supporting_member_fails_and_abandons_reservation(self):
        design = self.complete_design()
        design["supporting_members"] = [
            {
                "canonical_name": "assets/unsafe.txt",
                "media_type": "text/plain",
                "content": "api_key=abcdef123456",
            }
        ]
        result = self.execute(self.invocation(design=design, final=False))
        self.assertFalse(result["ok"])
        revisions = []
        catalog = self.catalog()
        for item in catalog.list_artifacts("DSN"):
            revisions.extend(catalog.list_revisions(item.artifact_id))
        self.assertEqual(tuple(item.state for item in revisions), ("abandoned",))

    def test_matrix_has_fixed_sixteen_rows(self):
        result = self.execute(self.invocation())
        stored = self.store.read_revision(result["artifact"]["id"], 1)
        parsed = parse_canonical_artifact(stored.payload.primary_blob)
        matrix = next(
            table
            for table in parsed.tables
            if "设计领域 Design Domain" in table.headers
        )
        self.assertEqual(len(matrix.rows), 16)

    def test_na_or_waived_scope_does_not_allocate_empty_dsn(self):
        for disposition in ("n/a", "waived"):
            with self.subTest(disposition=disposition):
                reference = self.create_requirement(
                    self.context_reference, disposition
                )
                before = self.catalog().list_artifacts("DSN")
                result = self.execute(
                    self.invocation(scope_inputs=(reference,))
                )
                after = self.catalog().list_artifacts("DSN")
                self.assertTrue(result["ok"])
                self.assertEqual(result["status"], "completed")
                self.assertIsNone(result["artifact"])
                self.assertEqual(result["warnings"][0]["code"], "DSN_NOT_REQUIRED")
                self.assertEqual(before, after)

    def test_pending_req_applicability_blocks_before_allocation(self):
        reference = self.create_requirement(self.context_reference, "pending")
        before = self.catalog().list_artifacts("DSN")
        result = self.execute(self.invocation(scope_inputs=(reference,)))
        after = self.catalog().list_artifacts("DSN")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(
            result["errors"][0]["code"],
            "REQ_DSN_APPLICABILITY_PENDING",
        )
        self.assertEqual(before, after)

    def test_required_scope_dominates_na_scope(self):
        optional = self.create_requirement(self.context_reference, "n/a")
        result = self.execute(
            self.invocation(
                scope_inputs=(self.requirement_reference, optional)
            )
        )
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["artifact"])


if __name__ == "__main__":
    import unittest

    unittest.main()
