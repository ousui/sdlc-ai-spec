"""One executable unittest entry per VFY Critical Case."""
from __future__ import annotations

import unittest

from tests.skill_vfy.case_module import exercise_case


class VfyCriticalCases(unittest.TestCase):
    maxDiff = None


def _case_test(case_id: str):
    def test(self: VfyCriticalCases) -> None:
        exercise_case(self, case_id)

    test.__name__ = "test_" + case_id.lower().replace("-", "_")
    test.__doc__ = f"Execute {case_id} against its concrete Oracle."
    return test


for sequence in range(1, 81):
    identifier = f"VFY-E{sequence:03d}"
    setattr(VfyCriticalCases, f"test_vfy_e{sequence:03d}", _case_test(identifier))


if __name__ == "__main__":
    unittest.main()
