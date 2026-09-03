from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from packages.sdlc_artifact_store import ArtifactStore, DatabaseError
from packages.sdlc_phasekit import ArtifactPhaseHandler, PhaseInputs
from packages.sdlc_runtime import execute_phase


class _FailingBuilder:
    def build(self, **kwargs):
        raise ValueError("deterministic build failure")


class _Verifier:
    def verify(self, reference, revision):
        raise AssertionError("verifier must not run")


class PhaseKitCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        ArtifactStore.open_read_write(self.root).initialize()
        self.handler = ArtifactPhaseHandler(
            self.root,
            artifact_type="PLN",
            skill_name="sdlc-300-pln",
            builder=_FailingBuilder(),
            verifier=_Verifier(),
            input_resolver=lambda store, inputs: PhaseInputs(
                "CTX-20260901000000-01@1", ("DSN-20260901000000-01@1",)
            ),
            candidate_key="plan",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _invocation(self):
        return {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": "create",
            "project_root": str(self.root),
            "artifact_reference": None,
            "inputs": {"plan": {}},
            "confirmations": [],
            "options": {"dry_run": False, "write_policy": "auto"},
        }

    def test_cleanup_failure_is_reported_instead_of_silently_hidden(self):
        with patch.object(
            ArtifactStore,
            "abandon_revision",
            side_effect=DatabaseError("cleanup database unavailable"),
        ):
            result = execute_phase(self.handler, self._invocation())
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["code"], "PLN_CLEANUP_FAILED")
        self.assertIn("deterministic build failure", result["errors"][0]["message"])
        self.assertIn("cleanup database unavailable", result["errors"][0]["message"])

    def test_normal_build_failure_closes_the_new_revision(self):
        result = execute_phase(self.handler, self._invocation())
        self.assertFalse(result["ok"])
        store = ArtifactStore.open_read_only(self.root)
        connection = store._connect()
        try:
            states = [row["state"] for row in connection.execute(
                "SELECT state FROM revisions ORDER BY artifact_id, revision"
            ).fetchall()]
        finally:
            connection.close()
        self.assertEqual(states, ["abandoned"])


if __name__ == "__main__":
    unittest.main()
