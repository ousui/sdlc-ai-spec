"""Real ArtifactStore/Claim/Lifecycle projection tests for frozen VFY."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from packages.sdlc_lifecycle import LifecycleQueryService
from tests.skill_vfy.support import persistent_passing_fixture


ROOT = Path(__file__).resolve().parents[2]
STATUS_ENTRY = ROOT / "skills/sdlc-status/scripts/runtime.py"
STATUS_SPEC = importlib.util.spec_from_file_location("vfy_status_test", STATUS_ENTRY)
STATUS_RUNTIME = importlib.util.module_from_spec(STATUS_SPEC)
assert STATUS_SPEC is not None and STATUS_SPEC.loader is not None
STATUS_SPEC.loader.exec_module(STATUS_RUNTIME)


class VfyLifecycleTest(unittest.TestCase):
    def test_lifecycle_projects_frozen_vfy_without_conflating_product_and_gate(self):
        with tempfile.TemporaryDirectory(prefix="vfy-lifecycle-") as directory:
            root = Path(directory)
            state, _ = persistent_passing_fixture(root)
            service = LifecycleQueryService(root)
            requirements = service.list_requirements()
            self.assertEqual(1, len(requirements))
            projection = service.inspect_requirement(requirements[0].reference)
            self.assertEqual(projection.frontier, (state["artifact"]["reference"],))
            self.assertEqual(projection.vfy_projection["product_result"], "pass")
            self.assertEqual(projection.vfy_projection["artifact_gate"], "pass")
            self.assertFalse(projection.vfy_projection["rls_ready"])
            self.assertEqual("LIFECYCLE_COMPLETE", projection.vfy_projection["next_action"])
            self.assertEqual("complete", projection.overall_state)

    def test_status_renders_vfy_product_gate_and_rls_readiness_read_only(self):
        with tempfile.TemporaryDirectory(prefix="vfy-status-") as directory:
            root = Path(directory)
            state, _ = persistent_passing_fixture(root)
            service = LifecycleQueryService(root)
            requirement = service.list_requirements()[0].reference
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file() and ".git" not in path.relative_to(root).parts
            }
            result = STATUS_RUNTIME.run_status(["inspect", "-r", requirement], cwd=root)
            summary = STATUS_RUNTIME.render_summary(result)
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file() and ".git" not in path.relative_to(root).parts
            }
            self.assertEqual(
                result["projection"]["vfy_projection"]["artifact_reference"],
                state["artifact"]["reference"],
            )
            self.assertIn("Product Result：pass", summary)
            self.assertIn("Artifact Gate：pass", summary)
            self.assertIn("RLS ready：否", summary)
            self.assertEqual(before, after)


if __name__ == "__main__":
    import unittest
    unittest.main()
