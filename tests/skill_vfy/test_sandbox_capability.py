"""VFY-WEB-007: portable unittests must not weaken Formal Fixed Eval."""
import io
import unittest
from unittest.mock import patch

from tests.evals import run_sdlc_500_vfy_eval as formal
from tests.skill_vfy.sandbox_support import probe_sandbox_capability
from tests.skill_vfy import test_critical_cases as critical
from tests.skill_vfy import test_executor_evidence as executor_cases
from tests.skill_vfy import test_fresh_review_boundaries as boundaries
from tools.validate_sdlc_500_vfy_case_coverage import validate
from vfy_common import VfyError


class SandboxCapabilityTest(unittest.TestCase):
    def test_missing_linux_backend_is_portable_but_never_fixed_eval_pass(self):
        suite = unittest.TestSuite([
            critical.VfyCriticalCases("test_vfy_e041"), critical.VfyCriticalCases("test_vfy_e046"),
            executor_cases.VfyExecutorEvidenceCases("test_vfy_e041"),
            executor_cases.VfyExecutorEvidenceCases("test_vfy_e046"),
            boundaries.FreshReviewBoundariesTest("test_command_network_and_outside_write_are_denied_by_os"),
        ])
        with patch("vfy_executor.sys.platform", "linux"), \
             patch("vfy_executor.shutil.which", return_value=None), \
             patch("vfy_executor.subprocess.Popen", side_effect=AssertionError("No process without backend")) as spawn:
            capability = probe_sandbox_capability()
            self.assertFalse(capability["available"])
            self.assertIsNone(capability["backend"])
            stream = io.StringIO()
            ordinary = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
            self.assertTrue(ordinary.wasSuccessful(), stream.getvalue())
            self.assertEqual(5, ordinary.testsRun)
            self.assertEqual([], ordinary.skipped)
            self.assertEqual([], ordinary.expectedFailures)
            self.assert_formal_unavailable(formal.run({"VFY-E041", "VFY-E046"}))
            with self.assertRaisesRegex(ValueError, "Critical Case execution requires sandbox capability"):
                validate()
            spawn.assert_not_called()  # No Method/network execution, fallback or installation.

    def assert_formal_unavailable(self, report):
        self.assertEqual("FAIL", report["status"])
        self.assertFalse(report["complete_fixed_eval"])
        self.assertEqual(0, report["passed"])
        self.assertEqual(2, report["failed"])
        self.assertEqual(0, report["skipped"])
        self.assertEqual(0, report["expected_failures"])
        self.assertEqual(["VFY-E041", "VFY-E046"], [row["case_id"] for row in report["results"]])
        for row in report["results"]:
            self.assertEqual("FAIL", row["status"])
            self.assertIsNone(row["result"])
            self.assertEqual("VFY_METHOD_NOT_READY", row["error"]["code"])
            self.assertEqual("action_required", row["error"]["status"])

    def test_formal_execution_observes_actual_host_capability(self):
        capability = probe_sandbox_capability()
        report = formal.run({"VFY-E041", "VFY-E046"})
        if not capability["available"]:
            self.assert_formal_unavailable(report)
            return
        self.assertEqual("PASS", report["status"], report)
        self.assertEqual(2, report["passed"])
        self.assertEqual(["pass", "fail"], [row["result"]["result"] for row in report["results"]])
        for row in report["results"]:
            formal.require_command_execution(row["case_id"], {"result": row["result"]})

    def test_formal_rejects_capability_only_pass(self):
        with patch.object(formal, "run_case", return_value={
            "status": "PASS", "result": {"status": "action_required", "evidence_references": []},
        }):
            report = formal.run({"VFY-E041", "VFY-E046"})
        self.assertEqual("FAIL", report["status"])
        self.assertEqual(0, report["passed"])
        self.assertEqual(2, report["failed"])
        for row in report["results"]:
            self.assertIn("requires actual sandbox command execution", row["error"]["message"])

    def test_present_backend_must_also_activate(self):
        unavailable = VfyError("VFY_METHOD_NOT_READY", "OS sandbox could not be activated",
                               status="action_required")
        with patch("vfy_executor._sandbox_argv", return_value=["/fixture/bwrap"]), \
             patch("vfy_executor._bounded_process", side_effect=unavailable):
            capability = probe_sandbox_capability()
        self.assertFalse(capability["available"])
        self.assertEqual("/fixture/bwrap", capability["backend"])
        self.assertEqual(unavailable.to_dict(), capability["error"])

    def test_unexpected_probe_failure_is_not_capability_unavailable(self):
        with patch("vfy_executor._sandbox_argv", return_value=["/fixture/bwrap"]):
            for outcome in ((1, "", "unrelated error", False), (0, "", "", True)):
                with self.subTest(outcome=outcome), \
                     patch("vfy_executor._bounded_process", return_value=outcome), \
                     self.assertRaises(AssertionError):
                    probe_sandbox_capability()
            unrelated = VfyError("VFY_METHOD_EXECUTION_FAILED", "unexpected")
            with patch("vfy_executor._bounded_process", side_effect=unrelated), self.assertRaises(VfyError):
                probe_sandbox_capability()
