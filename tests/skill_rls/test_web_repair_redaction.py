"""RLS-WEB-003: credential sentinels are synthetic; never use actual secrets."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("rls_redaction_under_test", ROOT / "tools/rls_validation_support.py")
support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(support)


class RlsWebRepairRedactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rls-redaction-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "logs"
        self.sentinel = "Bearer " + "SYNTHETIC_NOT_A_SECRET_123456789"

    def check_receipt(self, result, forbidden):
        for path in self.output.rglob("*"):
            if path.is_file():
                raw = path.read_text()
                for text in forbidden:
                    self.assertNotIn(text, raw, path.name)
        for text in forbidden:
            self.assertNotIn(text, json.dumps(result))
        for stream in ("stdout", "stderr"):
            raw = Path(result[stream + "_log"]).read_bytes()
            self.assertEqual(raw.decode(), result[stream])
            self.assertEqual(support.digest(raw), result[stream + "_sha256"])
        receipt = json.loads(next(self.output.glob("*.receipt.json")).read_bytes())
        self.assertEqual(result, receipt)
        self.assertEqual(support.REDACTION_POLICY, result["redaction_policy"])

    def run_fake(self, *, stdout=b"", stderr=b"", code=0, argv=None):
        with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], code, stdout, stderr)):
            return support.run_step(self.root, "case", argv or ["unittest"], self.output, track_source=False)

    def test_stdout_and_stderr_are_redacted_before_write(self):
        result = self.run_fake(stdout=self.sentinel.encode(), stderr=self.sentinel.encode())
        self.check_receipt(result, [self.sentinel])
        self.assertTrue(result["redaction_applied"])
        self.assertTrue(result["success"])

    def test_actual_subprocess_stdout_stderr(self):
        script = "import os,sys; print(os.environ['RLS_TEST_TOKEN']); print(os.environ['RLS_TEST_TOKEN'],file=sys.stderr)"
        result = support.run_step(self.root, "actual", [sys.executable, "-c", script], self.output,
                                  track_source=False, environment={"RLS_TEST_TOKEN": self.sentinel})
        self.check_receipt(result, [self.sentinel])
        self.assertEqual(0, result["exit_code"])

    def test_actual_argv_retained_for_execution_but_not_receipt(self):
        secret = "SYNTHETIC_PASSWORD_ONLY"
        argv = ["unit-tool", "--password", secret, "--token=" + secret]
        with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess(argv, 1, b"", b"")) as call:
            result = support.run_step(self.root, "argv", argv, self.output, track_source=False)
            self.assertEqual(argv, call.call_args.args[0])
        self.check_receipt(result, [secret])
        self.assertFalse(result["success"])
        self.assertEqual(1, result["exit_code"])

    def test_timeout_streams_and_partial_private_key(self):
        private = "-----BEGIN " + "PRIVATE KEY-----\nSYNTHETIC_PARTIAL_KEY"
        with patch.object(support.subprocess, "run", side_effect=subprocess.TimeoutExpired("unit", 1, self.sentinel.encode(), private.encode())):
            result = support.run_step(self.root, "timeout", ["unit"], self.output, track_source=False)
        self.check_receipt(result, [self.sentinel, "SYNTHETIC_PARTIAL_KEY"])
        self.assertEqual(124, result["exit_code"])
        self.assertFalse(result["success"])

    def test_oserror_redacted(self):
        with patch.object(support.subprocess, "run", side_effect=OSError(self.sentinel)):
            result = support.run_step(self.root, "error", ["unit"], self.output, track_source=False)
        self.check_receipt(result, [self.sentinel])
        self.assertEqual(127, result["exit_code"])

    def test_known_secret_environment_value_is_redacted(self):
        secret = "opaque-synthetic-value-without-recognized-prefix"
        with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, secret.encode(), b"")):
            result = support.run_step(self.root, "env", ["unit", secret], self.output,
                                      track_source=False, environment={"DEPLOY_CLIENT_SECRET": secret})
        self.check_receipt(result, [secret])

    def test_nested_json_and_argv_are_redacted(self):
        secret = "synthetic-nested-password"
        payload = {"profiles": [{"password": secret, "argv": ["tool", "--token", secret],
                                  "error": self.sentinel, "stdout": 'password="' + secret + '"'}]}
        self.output.mkdir()
        path = self.output / "nested.json"
        support.write_json(path, payload)
        self.assertNotIn(secret, path.read_text())
        self.assertNotIn(self.sentinel, path.read_text())
        self.assertEqual(secret, payload["profiles"][0]["password"])
        json.loads(path.read_bytes())

    def test_policy_is_idempotent_for_text_and_objects(self):
        values = ['password=value', 'token=[REDACTED]', '"password":"value"',
                  'Authorization: ' + self.sentinel, 'https://u:p@example.invalid/a',
                  '?api_key=value&x=1', 'token="[REDACTED]"', 'cookie=SESSION_VALUE']
        for text in values:
            with self.subTest(text=text):
                first = support.redact_text(text)
                self.assertEqual(first, support.redact_text(first))
        value = {"argv": ["tool", "--password", "synthetic"], "authorization_id": "EA-audit-binding"}
        self.assertEqual(support.redact_value(value), support.redact_value(support.redact_value(value)))

    def test_prefixed_credentials_private_key_and_headers(self):
        samples = ["ghp_" + "x" * 28, "github_pat_" + "x" * 32,
                   "sk-proj-" + "x" * 24, "Basic " + "dGVzdDp0ZXN0", self.sentinel,
                   "-----BEGIN " + "RSA PRIVATE KEY-----\nSYNTHETIC\n-----END RSA PRIVATE KEY-----",
                   "Cookie: session=synthetic_cookie", "https://name:synthetic_password@example.invalid/"]
        for value in samples:
            with self.subTest(kind=value[:10]):
                self.assertNotEqual(value, support.redact_text(value))

    def test_json_output_remains_parseable_and_hashes_stable(self):
        raw = json.dumps({"password": "synthetic", "counter": 2, "source_sha": "a" * 40}).encode()
        result = self.run_fake(stdout=raw)
        self.check_receipt(result, ["synthetic"])
        parsed = json.loads(result["stdout"])
        self.assertEqual(2, parsed["counter"])
        self.assertEqual("a" * 40, parsed["source_sha"])

    def test_nonsecret_authority_digests_and_ordinary_output_preserved(self):
        raw = {"authorization_id": "EA-binding", "authorizer_identity": "host",
               "source_sha": "a" * 40, "stdout_sha256": "sha256:" + "b" * 64}
        self.assertEqual(raw, support.redact_value(raw))
        result = self.run_fake(stdout=b"Ran 87 tests\nOK\n")
        self.check_receipt(result, [])
        self.assertFalse(result["redaction_applied"])

    def test_invalid_utf8_hashes_bind_archived_bytes(self):
        result = self.run_fake(stdout=b"\xff" + self.sentinel.encode())
        self.check_receipt(result, [self.sentinel])

    def test_path_environment_secret_redaction_does_not_leak_nested_result(self):
        secret = "unique_synthetic_env_password"
        with patch.dict(support.os.environ, {"TEST_PASSWORD": secret}):
            self.output.mkdir()
            support.write_json(self.output / "outer.json", {"error": "failed: " + secret,
                                "nested": {"cwd": "/tmp/" + secret}})
        self.assertNotIn(secret, (self.output / "outer.json").read_text())

    def test_timeout_with_text_streams(self):
        with patch.object(support.subprocess, "run", side_effect=subprocess.TimeoutExpired("unit", 1, self.sentinel, self.sentinel)):
            result = support.run_step(self.root, "timeout-text", ["unit"], self.output, track_source=False)
        self.check_receipt(result, [self.sentinel])


    def test_child_test_runner_redacts_before_its_own_json_write(self):
        import contextlib
        import io
        spec = importlib.util.spec_from_file_location("rls_suite_under_test", ROOT / "tools/run_rls_test_suite.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        secret = self.sentinel
        class FailingFixture(unittest.TestCase):
            def runTest(self):
                self.fail(secret)
        capture = io.StringIO()
        output = self.root / "child.json"
        with patch.object(module.unittest.defaultTestLoader, "discover", return_value=unittest.TestSuite([FailingFixture()])), contextlib.redirect_stdout(capture):
            result = module.run("rls", output)
        self.assertFalse(result["success"])
        self.assertEqual(1, result["failures"])
        for text in (output.read_text(), capture.getvalue(), json.dumps(result)):
            self.assertNotIn(secret, text)
        self.assertEqual(result, json.loads(output.read_bytes()))


    def test_domain_effect_authorization_is_not_a_credential_header(self):
        value = {"effect_authorization": {"authorization_id": "EA-domain-binding", "effect_digest": "a" * 64},
                 "effect_authorization_history": [{"authorizer_identity": "fixture-host"}]}
        raw = json.dumps(value)
        self.assertEqual(value, support.redact_value(value))
        self.assertEqual(value, json.loads(support.redact_text(raw)))
        result = self.run_fake(stdout=raw.encode())
        self.check_receipt(result, [])
        self.assertEqual(value, json.loads(result["stdout"]))

    def test_json_object_credential_is_redacted_without_breaking_json(self):
        raw = json.dumps({"password": {"nested": "synthetic-password"}, "keep": 5})
        cleaned = support.redact_text(raw)
        self.assertEqual({"password": "[REDACTED]", "keep": 5}, json.loads(cleaned))
        self.assertEqual(cleaned, support.redact_text(cleaned))


    def test_independence_outer_exception_is_redacted_before_disk_and_stderr(self):
        import contextlib
        import io
        spec = importlib.util.spec_from_file_location("rls_independence_under_test", ROOT / "tools/test_sdlc_600_rls_runtime_independence.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = self.root / "independence.json"
        capture = io.StringIO()
        with patch.object(module, "validate", side_effect=RuntimeError(self.sentinel)), contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            code = module.main(["--json-out", str(output)])
        self.assertEqual(1, code)
        self.assertEqual("FAIL", json.loads(output.read_bytes())["result"])
        self.assertNotIn(self.sentinel, output.read_text())
        self.assertNotIn(self.sentinel, capture.getvalue())


if __name__ == "__main__":
    unittest.main()
