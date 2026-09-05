"""Regression test for the VFY Critical Case coverage guard."""
from __future__ import annotations

import unittest

from tools.validate_sdlc_500_vfy_case_coverage import validate
from tests.skill_vfy.sandbox_support import probe_sandbox_capability


class VfyCaseCoverageGuardTest(unittest.TestCase):
    def test_registry_oracle_and_primary_tests_are_exactly_eighty(self) -> None:
        capability = probe_sandbox_capability()
        if not capability["available"]:
            with self.assertRaisesRegex(ValueError, "Critical Case execution requires sandbox capability") as failure:
                validate()
            self.assertIn("VFY_METHOD_NOT_READY", str(failure.exception))
            self.assertIn("action_required", str(failure.exception))
            return
        report = validate()
        self.assertEqual("PASS", report["status"])
        self.assertEqual(80, report["case_count"])
        self.assertEqual(80, report["unique_primary_tests"])
        self.assertEqual(80, report["oracle_branches"])
        self.assertEqual(0, report["skipped"])
        self.assertEqual(0, report["expected_failures"])


if __name__ == "__main__":
    unittest.main()
