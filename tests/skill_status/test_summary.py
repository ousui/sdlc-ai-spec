from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "skills/sdlc-status/scripts/runtime.py"
SPEC = importlib.util.spec_from_file_location("sdlc_status_summary_test", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


class StatusSummaryTests(unittest.TestCase):
    def test_multiple_requirements_show_exact_candidates(self):
        first = "REQ-20260831190000-01@1"
        second = "REQ-20260831190000-02@2"
        result = {
            "state": "selection_required",
            "project_root": "/project",
            "projection": None,
            "overview": {
                "context_candidates": [],
                "requirement_candidates": [
                    {
                        "reference": first,
                        "revision_state": "frozen",
                        "artifact_status": "ready",
                        "gate_result": "pass",
                        "authority_state": "valid",
                        "open_item_count": 0,
                        "lineage_head": True,
                    },
                    {
                        "reference": second,
                        "revision_state": "open",
                        "artifact_status": "waiting_input",
                        "gate_result": "pending",
                        "authority_state": "not_applicable",
                        "open_item_count": 2,
                        "lineage_head": True,
                    },
                ],
                "selected_requirement": None,
            },
            "errors": [],
            "next_action": {
                "code": "SELECT_REQUIREMENT",
                "reason": "请选择准确需求 Revision",
            },
        }
        summary = RUNTIME.render_summary(result)
        self.assertIn(first, summary)
        self.assertIn(second, summary)
        self.assertIn("open/waiting_input", summary)
        self.assertIn("open=2", summary)

    def test_blocked_projection_shows_code_reference_and_message(self):
        reference = "REQ-20260831190000-01@1"
        dependency = "DSN-20260831190000-99@1"
        result = {
            "state": "blocked",
            "project_root": "/project",
            "overview": None,
            "projection": {
                "root_reference": reference,
                "frontier": [reference],
                "blockers": [
                    {
                        "code": "DEPENDENCY_MISSING",
                        "reference": dependency,
                        "message": "Declared dependency cannot be read",
                    }
                ],
            },
            "errors": [],
            "next_action": None,
        }
        summary = RUNTIME.render_summary(result)
        self.assertIn("DEPENDENCY_MISSING", summary)
        self.assertIn(dependency, summary)
        self.assertIn("Declared dependency cannot be read", summary)


if __name__ == "__main__":
    unittest.main()
