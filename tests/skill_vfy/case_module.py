"""Shared constructor for one concrete hardened Critical Case unittest method."""
from __future__ import annotations

from tests.evals.vfy_case_harness_hardened import _command_method, legacy, run_case
from tests.skill_vfy.sandbox_support import assert_command_unavailable, probe_sandbox_capability


def exercise_case(test, case_id):
    # Portability belongs only to unittest. run_case and Formal Eval stay strict.
    if case_id in {"VFY-E041", "VFY-E046"} and not getattr(test, "require_execution", False):
        capability = probe_sandbox_capability()
        if not capability["available"]:
            with legacy.workspace() as root:
                method = _command_method(root, should_pass=case_id == "VFY-E041")
                assert_command_unavailable(test, method, root, capability)
            return  # Rejection was tested; no Critical Case PASS result is created.
    result = run_case(case_id)
    test.assertEqual("PASS", result["status"], result)
    test.assertEqual(case_id, result["case_id"])


def install_cases(test_class, first: int, last: int) -> None:
    for number in range(first, last + 1):
        case_id = f"VFY-E{number:03d}"

        def execute(self, exact_case=case_id):
            exercise_case(self, exact_case)

        execute.__name__ = f"test_vfy_e{number:03d}"
        execute.__doc__ = f"Execute {case_id} against its hardened concrete Oracle."
        setattr(test_class, execute.__name__, execute)
