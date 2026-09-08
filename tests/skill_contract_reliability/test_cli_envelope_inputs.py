"""One shared shape matrix, plus each affected formal CLI dispatch boundary."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from packages.sdlc_runtime.envelopes import cli_payload_fields, EnvelopeValidationError, validate_result

ROOT = Path(__file__).resolve().parents[2]


class CliEnvelopeInputTests(unittest.TestCase):
    def test_shared_cli_shapes_preserve_optional_null_and_reject_coercions(self):
        for payload in (None, {}, {"inputs": None, "confirmations": None}, {"inputs": {}, "confirmations": []}):
            self.assertEqual(({}, []), cli_payload_fields(payload))
        for payload, path in (([], "payload"), ({"inputs": False}, "inputs"),
                              ({"inputs": [["key", "value"]]}, "inputs"),
                              ({"inputs": ""}, "inputs"), ({"confirmations": {}}, "confirmations"),
                              ({"confirmations": False}, "confirmations"),
                              ({"confirmations": [{}, "bad"]}, "confirmations[1]")):
            with self.subTest(payload=payload):
                with self.assertRaises(EnvelopeValidationError) as caught:
                    cli_payload_fields(payload)
                self.assertEqual(path, caught.exception.details["path"])
        inputs, confirmations = cli_payload_fields({"inputs": {"extension": {"arbitrary": True}},
                                                    "confirmations": [{"type": "fixture", "approved": False}]})
        self.assertTrue(inputs["extension"]["arbitrary"])
        self.assertFalse(confirmations[0]["approved"])

    def test_affected_formal_clis_return_indexed_errors_without_store_or_traceback(self):
        for skill in ("sdlc-200-dsn", "sdlc-300-pln", "sdlc-400-imp"):
            for payload, path in (({"inputs": ["bad"]}, "inputs"),
                                  ({"confirmations": [{}, "bad"]}, "confirmations[1]")):
                with self.subTest(skill=skill, path=path), tempfile.TemporaryDirectory(prefix="cli-shape-") as temp:
                    result = subprocess.run([sys.executable, "-B", str(ROOT / "skills" / skill / "scripts/runtime.py"),
                                             "create", "--project-root", temp, "--output", "json"],
                                            input=json.dumps(payload), capture_output=True, text=True, cwd=temp, timeout=15)
                    self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                    self.assertEqual("", result.stderr)
                    body = validate_result(json.loads(result.stdout))
                    self.assertEqual("INVALID_ENVELOPE", body["errors"][0]["code"])
                    self.assertEqual(path, body["errors"][0]["details"]["path"])
                    self.assertFalse(body["next_action"]["requires_user"])
                    self.assertEqual([], list(Path(temp).iterdir()))
