"""Delivery guard failures must be reviewable, never silently skipped."""
from copy import deepcopy
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tools.rls_validation_support import run_step, digest
from tools.run_rls_delivery_validation import validate
from tools.validate_rls_delivery_source import allowed
from tools.run_external_rls_integration import project_snapshot, file_snapshot
from tests.evals.test_sdlc_600_rls_case_coverage import load_case_map, verify_original_oracles
from tests.evals.run_sdlc_600_rls_eval import run


class DeliveryGuardTests(unittest.TestCase):
    def test_external_snapshot_detects_bytes_and_modes_without_index_changes(self):
        with tempfile.TemporaryDirectory(prefix="rls-project-snapshot-") as directory:
            root=Path(directory)
            tracked=root/"tracked.txt";tracked.write_bytes(b"original\n")
            def git(*args):
                subprocess.run(["git","-C",str(root),*args],check=True,capture_output=True)
            git("init","-q");git("add","tracked.txt")
            git("-c","user.name=Snapshot Fixture","-c","user.email=fixture@example.invalid","commit","-qm","fixture")
            untracked=root/"untracked.txt";untracked.write_bytes(b"untracked\n")
            before=project_snapshot(root)
            for path in (tracked,untracked):
                with self.subTest(path=path.name):
                    original=path.read_bytes();mode=path.stat().st_mode
                    path.write_bytes(b"different\n")
                    changed=project_snapshot(root)
                    self.assertEqual(before["tracked"],changed["tracked"])
                    key="tracked_bytes_modes" if path==tracked else "untracked_bytes_modes"
                    self.assertNotEqual(before[key],changed[key])
                    path.write_bytes(original);os.chmod(path,mode ^ 0o100)
                    self.assertNotEqual(before[key],project_snapshot(root)[key])
                    os.chmod(path,mode)
            self.assertEqual(before,project_snapshot(root))

    def test_external_snapshot_hashes_symlink_itself_without_following_source(self):
        with tempfile.TemporaryDirectory(prefix="rls-symlink-snapshot-") as directory:
            root=Path(directory);outside=root/"outside";outside.write_bytes(b"private sentinel")
            scope=root/"scope";scope.mkdir();(scope/"link").symlink_to(outside)
            before=file_snapshot(scope)
            outside.write_bytes(b"different sentinel")
            self.assertEqual(before,file_snapshot(scope))
            self.assertEqual("symlink",before["files"]["link"]["kind"])

    def test_missing_process_records_real_exit_and_stream_digests(self):
        with tempfile.TemporaryDirectory(prefix="rls-receipt-test-") as directory:
            path=Path(directory)
            result=run_step(path,"missing",[str(path/"no-such-command")],path/"logs",track_source=False)
            self.assertFalse(result["success"]);self.assertEqual(127,result["exit_code"])
            self.assertEqual(digest(Path(result["stderr_log"]).read_bytes()),result["stderr_sha256"])
            self.assertEqual(result,json.loads((path/"logs/missing-attempt-1.receipt.json").read_bytes()))

    def test_wrong_exact_source_still_outputs_failure_json(self):
        with tempfile.TemporaryDirectory(prefix="rls-source-failure-") as directory:
            output=Path(directory)/"result.json"
            result=validate("quick","0"*40,output)
            self.assertFalse(result["success"]);self.assertTrue(result["error"])
            self.assertEqual(result,json.loads(output.read_bytes()))

    def test_changed_original_expected_is_rejected(self):
        cases=deepcopy(load_case_map()["cases"]);cases[0]["expected"]="weaker expectation"
        with self.assertRaises(AssertionError): verify_original_oracles(cases)

    def test_skipped_execution_is_never_a_fixed_eval_pass(self):
        class Skipped(unittest.TestCase):
            @unittest.skip("injected unavailable capability")
            def test_rls_e001_final(self): pass
        with patch("tests.evals.run_sdlc_600_rls_eval.build_suite",return_value=unittest.defaultTestLoader.loadTestsFromTestCase(Skipped)):
            result=run()
        self.assertFalse(result["success"]);self.assertEqual(1,result["skipped"])

    def test_missing_primary_writes_failure_json(self):
        with tempfile.TemporaryDirectory(prefix="rls-primary-failure-") as directory:
            output=Path(directory)/"failed.json"
            with patch("tests.evals.run_sdlc_600_rls_eval.build_suite",side_effect=RuntimeError("missing primary")):
                result=run(output)
            self.assertFalse(result["success"]);self.assertEqual(0,result["tests_run"])
            self.assertEqual("missing primary",json.loads(output.read_bytes())["error"])

    def test_source_whitelist_has_no_wildcard_tools_or_vfy_mutations(self):
        for path in ("tools/unrelated.py","skills/sdlc-500-vfy/scripts/vfy_handler.py","packages/sdlc_artifact_store/sqlite_store.py",".github/workflows/rls.yml"):
            self.assertFalse(allowed(path))
        self.assertTrue(allowed("packages/sdlc_lifecycle/query_rls.py"))
