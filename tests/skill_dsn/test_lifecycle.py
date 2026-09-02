from __future__ import annotations

from pathlib import Path

from packages.sdlc_lifecycle import LifecycleQueryService

from . import support_patch  # noqa: F401
from .support import DsnRuntimeFixture, PassingVerifier


class DsnLifecycleTests(DsnRuntimeFixture):
    def service(self):
        return LifecycleQueryService(
            self.root,
            plugin_root=Path(__file__).resolve().parents[2],
            verifier_factory=lambda _: PassingVerifier(),
        )

    def test_ready_dsn_creates_req_to_dsn_edge_and_routes_to_pln(self):
        created = self.execute(self.invocation())
        self.assertTrue(created["ok"])
        projection = self.service().inspect_requirement(self.requirement_reference)
        self.assertEqual(projection.frontier, (created["artifact"]["reference"],))
        self.assertTrue(
            any(
                edge.source_reference == self.requirement_reference
                and edge.target_reference == created["artifact"]["reference"]
                and edge.relation == "scope_input"
                for edge in projection.edges
            )
        )
        self.assertEqual(len(projection.next_actions), 1)
        action = projection.next_actions[0]
        self.assertEqual(action.phase, "PLN")
        self.assertEqual(action.skill, "sdlc-300-pln")
        self.assertTrue(action.skill_available)
        self.assertIsNotNone(action.command)

    def test_pln_skipped_and_imp_required_routes_directly_to_imp(self):
        design = self.complete_design()
        design["lifecycle_applicability"] = [
            {
                "phase": "PLN",
                "disposition": "n/a",
                "host": "N/A",
                "basis": "Single versioned resource can be implemented directly",
            },
            {
                "phase": "IMP",
                "disposition": "required",
                "host": "N/A",
                "basis": "Product code must change",
            },
            {
                "phase": "VFY",
                "disposition": "required",
                "host": "N/A",
                "basis": "VFY is the mandatory control point",
            },
            {
                "phase": "RLS",
                "disposition": "n/a",
                "host": "N/A",
                "basis": "Fixture does not execute release",
            },
        ]
        created = self.execute(self.invocation(design=design))
        self.assertTrue(created["ok"])
        action = self.service().inspect_requirement(
            self.requirement_reference
        ).next_actions[0]
        self.assertEqual(action.phase, "IMP")
        self.assertEqual(action.skill, "sdlc-400-imp")
        self.assertFalse(action.skill_available)
        self.assertIsNone(action.command)

    def test_open_dsn_stays_on_current_phase(self):
        created = self.execute(self.invocation(final=False))
        self.assertFalse(created["ok"])
        projection = self.service().inspect_requirement(self.requirement_reference)
        self.assertEqual(projection.frontier, (created["artifact"]["id"] + "@1",))
        action = projection.next_actions[0]
        self.assertEqual(action.code, "RESOLVE_CURRENT_PHASE")
        self.assertEqual(action.phase, "DSN")
        self.assertEqual(action.skill, "sdlc-200-dsn")
        self.assertTrue(action.skill_available)
        self.assertIn("revise", action.command)

    def test_invalid_dsn_applicability_does_not_guess_next_phase(self):
        created = self.execute(self.invocation())
        self.assertTrue(created["ok"])
        service = self.service()
        node = service.read_node(created["artifact"]["reference"])
        service._dsn_applicability[node.reference] = {
            "code": "DSN_APPLICABILITY_INVALID",
            "message": "invalid applicability fixture",
            "reference": node.reference,
        }
        action = service._next_action_for(node, reason="fixture")
        self.assertEqual(action.code, "RESOLVE_LIFECYCLE_APPLICABILITY")
        self.assertEqual(action.phase, "DSN")
        self.assertNotIn("sdlc-300-pln", action.command or "")
        self.assertNotIn("sdlc-400-imp", action.command or "")


if __name__ == "__main__":
    import unittest

    unittest.main()
