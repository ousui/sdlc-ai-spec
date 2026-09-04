from contextlib import closing, ExitStack
import importlib.util
import json
import sqlite3
import subprocess
import sys
from unittest.mock import patch

from tests.skill_imp.support import ImpFixture, OWNER, ROOT, tree_bytes
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_claim_provider import ClaimProvider


ENTRY = ROOT / "skills/sdlc-status/scripts/runtime.py"
SPEC = importlib.util.spec_from_file_location("status_imp_test", ENTRY)
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class ImpStatusTests(ImpFixture):
    def status(self, arguments=()):
        return RUNTIME.run_status(arguments, cwd=self.root)

    def test_auto_and_inspect_show_current_claim_and_read_only_policy(self):
        self.create_open()
        before = tree_bytes(self.root)
        for arguments in ([], ["inspect", "-r", self.requirement_reference]):
            with self.subTest(arguments=arguments):
                result = self.status(arguments)
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["effective_write_policy"], "deny")
                claim = result["projection"]["current_claims"][0]
                self.assertEqual((claim["owner"], claim["attempt"], claim["claim_state"]),
                                 (OWNER, 1, "active"))
                self.assertFalse(claim["vfy_ready"])
                summary = RUNTIME.render_summary(result)
                self.assertIn(self.binding, summary)
                self.assertIn("Owner=" + OWNER, summary)
                self.assertIn("Attempt=1", summary)
                self.assertIn("VFY 就绪：否", summary)
        self.assertEqual(tree_bytes(self.root), before)

    def test_completed_summary_separates_vfy_readiness_and_installed_skill(self):
        completed = self.finish(self.create_open())
        result = self.status()
        summary = RUNTIME.render_summary(result)
        self.assertIn("当前实施完成：是", summary)
        self.assertIn("VFY 就绪：是", summary)
        self.assertIn("命令：/sdlc-500-vfy create", summary)
        self.assertIn(self.info(completed)["results"][0], summary)
        self.assertIn("/sdlc-500-vfy create", result["next_action"]["command"])

    def test_corrupt_claim_store_reports_stable_error_and_remains_unchanged(self):
        self.finish(self.create_open())
        with closing(sqlite3.connect(self.root / ".sdlc/store.sqlite3")) as connection:
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute("UPDATE imp_claims SET state='bogus'")
            connection.commit()
        before = tree_bytes(self.root)
        result = self.status()
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["errors"][0]["code"], "IMP_CLAIM_STORE_INVALID")
        self.assertEqual(tree_bytes(self.root), before)

    def test_status_uses_no_artifact_or_claim_mutation_api(self):
        self.finish(self.create_open())
        before = tree_bytes(self.root)
        with ExitStack() as guard:
            for owner, names in (
                (ArtifactStore, ("open_read_write", "initialize", "freeze_revision", "write_open_revision")),
                (ClaimProvider, ("open_read_write", "initialize", "acquire", "complete", "abandon")),
            ):
                for name in names:
                    guard.enter_context(patch.object(owner, name, side_effect=AssertionError(name)))
            result = self.status(["auto", "--write-policy", "auto"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["effective_write_policy"], "deny")
        self.assertEqual(tree_bytes(self.root), before)

    def test_cli_json_includes_current_claim_and_exact_vfy_input(self):
        completed = self.finish(self.create_open())
        before = tree_bytes(self.root)
        process = subprocess.run([sys.executable, "-B", str(ENTRY), "inspect", "-p", str(self.root),
                                  "-r", self.requirement_reference, "-f", "json"],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["projection"]["vfy_inputs"], [completed["artifact"]["reference"]])
        self.assertEqual(result["projection"]["current_claims"][0]["claim_state"], "completed")
        self.assertEqual(tree_bytes(self.root), before)

    def test_multiple_actions_remain_visible_without_choosing_first(self):
        self.create_open()
        candidate = self.plan()
        candidate["work_items"][0]["execution_scope"] = ["resource:aux"]
        candidate["delivery_scope"].append({
            "scope_token": "resource:aux", "source_references": [self.dsn_reference + "#CHG-001"],
            "outcome": "Deliver an independent auxiliary result",
        })
        other = self.execute_pln(plan=candidate)
        self.assertTrue(other["ok"], other)
        result = self.status()
        self.assertEqual(result["next_action"]["code"], "SELECT_NEXT_ACTION")
        self.assertIsNone(result["next_action"]["command"])
        summary = RUNTIME.render_summary(result)
        for action in result["projection"]["next_actions"]:
            self.assertIn(action["reason"], summary)
