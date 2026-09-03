import json
from pathlib import Path
import tempfile
import unittest

from packages import sdlc_execution
from packages.sdlc_execution import ExecutionError, manual_evidence, run_command


class ExecutionAndEffectsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_command_evidence_and_secret_rejection(self):
        evidence = run_command(self.root, ["python3", "-c", "print('ok')"])
        self.assertEqual(evidence.result, "pass")
        payload = json.loads(evidence.raw_bytes)
        self.assertEqual(payload["stdout"], "ok\n")
        with self.assertRaises(ExecutionError):
            run_command(self.root, ["echo", "token=abcdef123"])
        with self.assertRaises(ExecutionError):
            run_command(self.root, ["python3", "-V"], cwd="../")

    def test_manual_evidence_is_structured(self):
        evidence = manual_evidence(executor="reviewer", statement="inspect UI", observed="layout is stable", result="pass")
        self.assertTrue(evidence.reference.startswith("manual@sha256:"))
        with self.assertRaises(ExecutionError):
            manual_evidence(executor="", statement="x", observed="y", result="pass")

    def test_execution_foundation_does_not_expose_release_effect_authority(self):
        self.assertFalse(hasattr(sdlc_execution, "verify_effect_authorization"))


if __name__ == "__main__":
    unittest.main()
