"""Focused VFY Runtime and projection tests outside the numbered Oracle."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from packages.sdlc_lifecycle.query_vfy import project_vfy_state
from tests.skill_vfy.support import passing_state, prepare_workspace, valid_candidate
from vfy_builder import build_state
from vfy_handler import VfyHandler


_RUNTIME_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "sdlc-500-vfy"
    / "scripts"
    / "runtime.py"
)
_RUNTIME_SPEC = importlib.util.spec_from_file_location("sdlc_500_vfy_runtime", _RUNTIME_PATH)
if _RUNTIME_SPEC is None or _RUNTIME_SPEC.loader is None:
    raise RuntimeError(f"cannot load VFY Runtime: {_RUNTIME_PATH}")
_RUNTIME = importlib.util.module_from_spec(_RUNTIME_SPEC)
_RUNTIME_SPEC.loader.exec_module(_RUNTIME)
parse_command = _RUNTIME.parse_command
run_cli = _RUNTIME.run_cli


class VfyRuntimeTest(unittest.TestCase):
    def test_meta_commands_have_no_effects(self) -> None:
        for command in ("--help", "version", "commands", "examples"):
            result, _ = run_cli([command])
            self.assertTrue(result["ok"])
            self.assertEqual("meta", result["state"])
            self.assertEqual([], result["effects"])

    def test_repeatable_method_preserves_first_order(self) -> None:
        _, command, _, methods = parse_command(
            ["run", "-r", "VFY-20260904120000-01@1", "-m", "VFM-002", "-m", "VFM-001", "-m", "VFM-002"]
        )
        self.assertEqual("run", command.command)
        self.assertEqual(["VFM-002", "VFM-001"], methods)

    def test_dry_run_create_executes_safe_methods(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-runtime-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            result, _ = run_cli(
                ["create", "--project-root", str(root), "--output", "json"],
                {"candidate": valid_candidate(), "persist": False},
            )
            self.assertTrue(result["ok"])
            self.assertEqual("pass", result["product_result"])
            self.assertEqual([], result["effects"])

    def test_manual_method_remains_waiting_without_human_evidence(self) -> None:
        candidate = valid_candidate()
        candidate["methods"][0]["execution_mode"] = "manual"
        candidate["methods"][0]["method_type"] = "demonstration"
        with tempfile.TemporaryDirectory(prefix="vfy-manual-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            state = build_state(candidate)
            result = VfyHandler(root).run_state(
                state,
                method_ids=["VFM-001"],
                allow_commands=False,
            )
            self.assertEqual(["VFM-001"], result["waiting_methods"])
            row = next(
                item
                for item in result["state"]["method_results"]
                if item["method_id"] == "VFM-001"
            )
            self.assertEqual("pending", row["result"])

    def test_product_and_artifact_projection_are_independent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-projection-") as directory:
            state = passing_state(Path(directory))
            projection = project_vfy_state(state)
            self.assertEqual("pass", projection.product_result)
            self.assertEqual("pass", projection.artifact_gate)
            self.assertTrue(projection.rls_ready)
            self.assertEqual("RLS", projection.next_phase)


if __name__ == "__main__":
    unittest.main()
