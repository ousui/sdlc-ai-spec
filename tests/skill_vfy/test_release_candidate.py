"""VFY → RLS release-candidate contract tests."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tests.evals.vfy_case_harness import failing_state
from tests.skill_vfy.support import passing_state
from vfy_common import VfyError
from vfy_release import build_release_candidate


class VfyReleaseCandidateTest(unittest.TestCase):
    def test_frozen_pass_projects_exact_non_provisional_candidate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-release-pass-") as directory:
            state = passing_state(Path(directory))
            candidate = build_release_candidate(state)
            self.assertEqual("sdlc-ai-spec/vfy-release-candidate/v1", candidate["contract"])
            self.assertFalse(candidate["provisional"])
            self.assertEqual(state["artifact"]["reference"], candidate["vfy_reference"])
            self.assertEqual(candidate["subject_references"], candidate["result_references"])
            self.assertEqual("pass", candidate["artifact_gate"])
            self.assertTrue(candidate["rls_ready"])

    def test_early_stop_never_projects_to_rls(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-release-stop-") as directory:
            root = Path(directory)
            root.mkdir(exist_ok=True)
            state = failing_state(root, early_stop=True)
            with self.assertRaises(VfyError) as error:
                build_release_candidate(state)
            self.assertEqual("VFY_RLS_NOT_ALLOWED", error.exception.code)

    def test_unresolved_product_failure_never_projects_to_rls(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-release-fail-") as directory:
            root = Path(directory)
            root.mkdir(exist_ok=True)
            state = failing_state(root)
            with self.assertRaises(VfyError) as error:
                build_release_candidate(state)
            self.assertEqual("VFY_RLS_NOT_ALLOWED", error.exception.code)


if __name__ == "__main__":
    unittest.main()
