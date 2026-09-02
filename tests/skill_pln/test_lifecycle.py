from __future__ import annotations

from pathlib import Path

from packages.sdlc_lifecycle import LifecycleQueryService
from tests.skill_dsn.support import PassingVerifier

from .support import PlnFixture


class PlnLifecycleTests(PlnFixture):
    def service(self):
        return LifecycleQueryService(
            self.root,
            plugin_root=Path(__file__).resolve().parents[2],
            verifier_factory=lambda _: PassingVerifier(),
        )

    def test_ready_plan_projects_exact_imp_binding(self):
        plan = self.execute_pln()
        self.assertTrue(plan["ok"])
        projection = self.service().inspect_requirement(self.requirement_reference)
        self.assertEqual(projection.frontier, (plan["artifact"]["reference"],))
        self.assertEqual(len(projection.next_actions), 1)
        action = projection.next_actions[0]
        self.assertEqual(action.code, "START_WORK_ITEM")
        self.assertEqual(action.phase, "IMP")
        self.assertEqual(action.skill, "sdlc-400-imp")
        self.assertIn(plan["artifact"]["reference"] + "#WI-001", action.command or "")

    def test_parallel_earliest_work_items_are_all_projected(self):
        candidate = self.plan()
        first = candidate["work_items"][0]
        verification = candidate["work_items"][1]
        second = dict(first)
        second.update(
            {
                "id": "WI-002",
                "outcome": "Implement the independent supporting resource",
                "execution_scope": ["resource:repo-support", "path:repo-support/integration"],
                "depends_on": [],
                "completion_criteria": "An immutable supporting implementation result exists",
                "expected_evidence": "Supporting snapshot and local check evidence",
            }
        )
        verification = dict(verification)
        verification.update({"id": "WI-003", "depends_on": ["WI-001", "WI-002"]})
        candidate["work_items"] = [first, second, verification]
        candidate["delivery_scope"].append(
            {
                "scope_token": "resource:repo-support",
                "source_references": [self.dsn_reference + "#CHG-001"],
                "outcome": "Deliver the independent supporting resource",
            }
        )
        result = self.execute_pln(plan=candidate)
        self.assertTrue(result["ok"], result)
        projection = self.service().inspect_requirement(self.requirement_reference)
        self.assertEqual(len(projection.next_actions), 2)
        self.assertEqual(projection.overall_state, "parallel")
        commands = tuple(action.command or "" for action in projection.next_actions)
        self.assertTrue(any("#WI-001" in command for command in commands))
        self.assertTrue(any("#WI-002" in command for command in commands))
        self.assertTrue(all(action.phase == "IMP" for action in projection.next_actions))


if __name__ == "__main__":
    import unittest

    unittest.main()
