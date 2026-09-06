"""Registry structure is cheap; actual strict execution belongs to the one suite run."""
import unittest
from unittest.mock import patch
from tools.validate_sdlc_500_vfy_case_coverage import validate

class VfyCaseCoverageGuardTest(unittest.TestCase):
    def test_registry_oracle_and_primary_tests_are_exactly_eighty(self):
        report = validate(execute=False)
        self.assertEqual("STRUCTURE_ONLY", report["status"])
        self.assertEqual(80, report["case_count"])
        self.assertEqual(80, report["unique_primary_tests"])
        self.assertEqual(0, report["executed_primary_tests"])

    def test_formal_guard_rejects_unavailable_os_sandbox(self):
        unavailable = {"available": False, "error": {"code": "VFY_METHOD_NOT_READY", "status": "action_required"}}
        with patch("tests.skill_vfy.sandbox_support.probe_sandbox_capability", return_value=unavailable):
            with self.assertRaisesRegex(ValueError, "Critical Case execution requires sandbox capability"):
                validate()
