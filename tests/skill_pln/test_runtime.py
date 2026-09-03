from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_runtime import parse_canonical_artifact

from .support import PlnFixture


class PlnRuntimeTests(PlnFixture):
    def test_create_freezes_complete_plan(self):
        result=self.execute_pln()
        self.assertTrue(result["ok"]); self.assertEqual(result["gate"]["result"],"pass")
        self.assertEqual(result["artifact"]["revision_state"],"frozen")
        stored=self.store.read_revision(result["artifact"]["id"],1)
        parsed=parse_canonical_artifact(stored.payload.primary_blob)
        work=next(table for table in parsed.tables if "目标 Phase Target Phase" in table.headers)
        self.assertEqual(tuple(row["ID"] for row in work.rows),("WI-001","WI-002"))

    def test_missing_confirmation_persists_open_revision(self):
        result=self.execute_pln(final=False)
        self.assertFalse(result["ok"]); self.assertEqual(result["status"],"action_required")
        self.assertEqual(result["artifact"]["revision_state"],"open")

    def test_non_required_and_pending_do_not_allocate(self):
        for disposition in ("n/a", "waived"):
            scope = self.create_scope_with_pln_disposition(disposition)
            before = self.catalog().list_artifacts("PLN")
            result = self.execute_pln(
                scope=(scope,), plan=self.plan(disposition=disposition)
            )
            after = self.catalog().list_artifacts("PLN")
            self.assertTrue(result["ok"])
            self.assertIsNone(result["artifact"])
            self.assertEqual(before, after)
        before = self.catalog().list_artifacts("PLN")
        result = self.execute_pln(plan=self.plan(disposition="pending"), final=False)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["artifact"])
        self.assertEqual(before, self.catalog().list_artifacts("PLN"))

    def test_candidate_cannot_override_upstream_pln_applicability(self):
        result = self.execute_pln(plan=self.plan(disposition="n/a"))
        self.assertFalse(result["ok"])
        self.assertIn("does not match", result["errors"][0]["message"])

    def test_same_resource_work_items_require_dependency_chain(self):
        plan=self.plan(second_imp=True); plan["work_items"][1]["depends_on"]=[]
        result=self.execute_pln(plan=plan,final=False)
        self.assertFalse(result["ok"]); self.assertIn("PLN-G-004",result["gate"]["failed_checks"])

    def test_dependency_cycle_and_later_phase_fail(self):
        plan=self.plan(); plan["work_items"][0]["depends_on"]=["WI-002"]
        result=self.execute_pln(plan=plan,final=False)
        self.assertFalse(result["ok"]); self.assertIn("PLN-G-004",result["gate"]["failed_checks"])

    def test_open_revise_frozen_no_change_and_change(self):
        opened=self.execute_pln(final=False); ref=opened["artifact"]["id"]+"@1"
        finalized=self.execute_pln(operation="revise",reference=ref)
        self.assertTrue(finalized["ok"]); self.assertEqual(finalized["artifact"]["revision"],1)
        no_change=self.execute_pln(operation="revise",reference=finalized["artifact"]["reference"])
        self.assertEqual(no_change["warnings"][0]["code"],"NO_CHANGE")
        changed=self.plan(); changed["summary"]="Updated plan summary"
        revised=self.execute_pln(operation="revise",reference=finalized["artifact"]["reference"],plan=changed)
        self.assertTrue(revised["ok"]); self.assertEqual(revised["artifact"]["revision"],2)

    def test_check_is_read_only(self):
        result=self.execute_pln(); path=self.root/".sdlc/store.sqlite3"; before=path.read_bytes()
        checked=self.execute_pln(operation="check",reference=result["artifact"]["reference"])
        self.assertTrue(checked["ok"]); self.assertEqual(before,path.read_bytes())
