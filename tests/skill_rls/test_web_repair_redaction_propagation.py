"""RLS-WEB-003 composition regressions. All credential values are synthetic."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("rls_propagation_under_test", ROOT / "tools/rls_validation_support.py")
support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(support)


class SensitiveValuePropagationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rls-propagation-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "logs"
        self.canary = "SYNTHETIC_OPAQUE_VALUE_839247"
        self.env_patch = patch.dict(support.os.environ, {}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def assert_safe(self, result, *values):
        values = values or (self.canary,)
        for path in self.output.rglob("*"):
            if path.is_file():
                for value in values:
                    self.assertNotIn(value, path.read_text(), path.name)
        for value in values:
            self.assertNotIn(value, json.dumps(result, ensure_ascii=False))
        for stream in ("stdout", "stderr"):
            raw = Path(result[stream + "_log"]).read_bytes()
            self.assertEqual(raw.decode(), result[stream])
            self.assertEqual(support.digest(raw), result[stream + "_sha256"])
        saved = json.loads(next(self.output.glob("*.receipt.json")).read_bytes())
        self.assertEqual(result, saved)
        self.assertNotIn("secrets", saved)
        self.assertNotIn("sensitive_values", saved)

    def fake(self, stdout=b"", stderr=b"", argv=None, **kwargs):
        with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout, stderr)):
            return support.run_step(self.root, "capture", argv or ["unit"], self.output,
                                    track_source=False, **kwargs)

    def child(self, program, arguments=(), **kwargs):
        return support.run_step(self.root, "child", [sys.executable, "-c", program, *arguments],
                                self.output, track_source=False, **kwargs)

    def test_separate_credential_argument_echoes_in_both_real_streams(self):
        result = self.child("import sys; print(sys.argv[-1]); print(sys.argv[-1],file=sys.stderr)",
                            ["--password", self.canary])
        self.assertEqual(0, result["exit_code"])
        self.assert_safe(result)

    def test_equals_credential_argument_echoes_in_both_real_streams(self):
        result = self.child("import sys; x=sys.argv[-1].split('=',1)[1]; print(x); print(x,file=sys.stderr)",
                            ["--password=" + self.canary])
        self.assertEqual(0, result["exit_code"])
        self.assert_safe(result)

    def test_real_structured_secret_masks_an_earlier_sibling(self):
        program = "import json; x='_'.join(['SYNTHETIC','OPAQUE','VALUE','839247']); print(json.dumps({'diagnostic':x,'password':x}))"
        result = self.child(program)
        self.assert_safe(result)
        self.assertEqual(support.REDACTED, json.loads(result["stdout"])["diagnostic"])

    def test_real_stderr_secret_masks_earlier_stdout(self):
        program = "import sys,json; x='_'.join(['SYNTHETIC','OPAQUE','VALUE','839247']); print(x); print(json.dumps({'password':x}),file=sys.stderr)"
        result = self.child(program)
        self.assert_safe(result)

    def test_real_stdout_secret_masks_stderr(self):
        program = "import sys,json; x='_'.join(['SYNTHETIC','OPAQUE','VALUE','839247']); print(json.dumps({'password':x})); print(x,file=sys.stderr)"
        result = self.child(program)
        self.assert_safe(result)

    def test_environment_argv_and_object_secrets_share_one_context(self):
        b, c = self.canary + "_ARGV", self.canary + "_JSON"
        result = self.fake(json.dumps({"echo": [self.canary, b, c]}).encode(),
                           json.dumps({"password": c}).encode(), argv=["unit", "--token", b],
                           environment={"DEPLOY_SECRET": self.canary})
        self.assert_safe(result, self.canary, b, c)

    def test_secret_in_nested_list_masks_other_stream(self):
        result = self.fake(self.canary.encode(), json.dumps({"items": [{"auth": {"password": self.canary}}]}).encode())
        self.assert_safe(result)

    def test_sensitive_object_masks_its_leaf_values_elsewhere(self):
        raw = {"diagnostic": self.canary, "password": {"nested": [self.canary]}}
        safe = support.redact_value(raw)
        self.assertEqual(support.REDACTED, safe["diagnostic"])
        self.assertEqual(support.REDACTED, safe["password"])
        self.assertEqual(self.canary, raw["password"]["nested"][0])

    def test_nested_encoded_json_masks_outer_sibling(self):
        raw = {"echo": self.canary, "inner": json.dumps({"credential": self.canary})}
        safe = support.redact_receipt(raw)
        self.assertNotIn(self.canary, json.dumps(safe))
        self.assertEqual(support.REDACTED, json.loads(safe["inner"])["credential"])

    def test_json_lines_share_sensitive_values(self):
        lines = json.dumps({"echo": self.canary}) + "\n" + json.dumps({"password": self.canary}) + "\n"
        result = self.fake(lines.encode(), self.canary.encode())
        self.assert_safe(result)
        self.assertEqual(support.REDACTED, json.loads(result["stdout"].splitlines()[0])["echo"])

    def test_json_lines_with_escaped_unicode_quotes_and_newlines(self):
        secret = 'SYNTHETIC_口令"\\\n_SUFFIX'
        lines = json.dumps({"echo": secret}) + "\n" + json.dumps({"password": secret}) + "\n"
        result = self.fake(lines.encode(), json.dumps({"echo": secret}).encode())
        for line in result["stdout"].splitlines():
            self.assertNotIn(secret, json.dumps(json.loads(line), ensure_ascii=False))
        self.assertEqual(support.REDACTED, json.loads(result["stderr"])["echo"])
        self.assert_safe(result, secret)

    def test_mixed_prose_and_json_propagates_without_breaking_json(self):
        text = "begin " + json.dumps({"password": self.canary, "echo": self.canary}) + " end " + self.canary
        result = self.fake(text.encode())
        self.assert_safe(result)
        self.assertIn('"echo": "[REDACTED]"', result["stdout"])

    def test_duplicate_sensitive_keys_do_not_hide_earlier_values(self):
        raw = '{"password":"' + self.canary + '","password":"[REDACTED]"}'
        result = self.fake(raw.encode(), self.canary.encode())
        self.assert_safe(result)
        self.assertEqual(support.REDACTED, json.loads(result["stdout"])["password"])

    def test_assignment_in_stderr_masks_unlabelled_stdout(self):
        result = self.fake(self.canary.encode(), ('password="' + self.canary + '"').encode())
        self.assert_safe(result)

    def test_bearer_header_masks_bare_token_echo(self):
        result = self.fake(self.canary.encode(), ("Authorization: Bearer " + self.canary).encode())
        self.assert_safe(result)

    def test_url_password_masks_bare_password_echo(self):
        result = self.fake(self.canary.encode(), ("https://user:" + self.canary + "@example.invalid/").encode())
        self.assert_safe(result)

    def test_public_argv_redactor_masks_unlabelled_duplicate_argument(self):
        args = ["tool", "--label", self.canary, "--db-password", self.canary]
        self.assertNotIn(self.canary, json.dumps(support.redact_argv(args)))
        self.assertEqual(self.canary, args[-1])

    def test_argument_generator_is_not_consumed_before_execution(self):
        args = [sys.executable, "-c", "import sys; print(sys.argv[-1])", "--password", self.canary]
        result = support.run_step(self.root, "generator", iter(args), self.output, track_source=False)
        self.assertEqual(0, result["exit_code"])
        self.assert_safe(result)

    def test_child_receives_original_argv_and_environment(self):
        argv = ["unit", "--api-key=" + self.canary]
        with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess(argv, 0, self.canary.encode(), b"")) as call:
            result = support.run_step(self.root, "original", argv, self.output, track_source=False,
                                      environment={"DB_PASSWORD": self.canary})
        self.assertEqual(argv, call.call_args.args[0])
        self.assertEqual(self.canary, call.call_args.kwargs["env"]["DB_PASSWORD"])
        self.assertNotIn("DB_PASSWORD", support.os.environ)
        self.assert_safe(result)

    def test_timeout_retains_captured_cross_stream_context(self):
        error = subprocess.TimeoutExpired("unit", 0.1, self.canary.encode(), json.dumps({"password": self.canary}).encode())
        with patch.object(support.subprocess, "run", side_effect=error):
            result = support.run_step(self.root, "timeout", ["unit"], self.output, track_source=False)
        self.assertEqual(124, result["exit_code"])
        self.assertFalse(result["success"])
        self.assert_safe(result)

    def test_real_timeout_argument_echo_is_redacted(self):
        program = "import sys,time; print(sys.argv[-1],flush=True); print(sys.argv[-1],file=sys.stderr,flush=True); time.sleep(3)"
        result = self.child(program, ["--password", self.canary], timeout=0.2)
        self.assertEqual(124, result["exit_code"])
        self.assert_safe(result)

    def test_oserror_uses_credential_argument_context(self):
        with patch.object(support.subprocess, "run", side_effect=OSError("failed " + self.canary)):
            result = support.run_step(self.root, "error", ["unit", "--password", self.canary], self.output, track_source=False)
        self.assertEqual(127, result["exit_code"])
        self.assert_safe(result)

    def test_nonzero_exit_does_not_bypass_propagation(self):
        result = self.child("import sys; print(sys.argv[-1]); sys.exit(7)", ["--token", self.canary])
        self.assertEqual(7, result["exit_code"])
        self.assertFalse(result["success"])
        self.assert_safe(result)

    def test_nested_writer_discovers_across_siblings_before_first_write(self):
        raw = {"earlier": {"stdout": self.canary}, "later": [{"argv": ["unit", "--password", self.canary]}]}
        original = deepcopy(raw)
        path = self.output / "outer.json"
        writes = []
        real_write = Path.write_bytes
        def checked(file, data):
            self.assertNotIn(self.canary.encode(), data)
            writes.append(file)
            return real_write(file, data)
        with patch.object(Path, "write_bytes", checked):
            support.write_json(path, raw)
        self.assertEqual([path], writes)
        self.assertEqual(original, raw)
        self.assertEqual(support.REDACTED, json.loads(path.read_bytes())["earlier"]["stdout"])

    def test_all_process_writes_are_safe_not_postprocessed(self):
        writes = []
        real_write = Path.write_bytes
        def checked(file, data):
            self.assertNotIn(self.canary.encode(), data)
            writes.append(file)
            return real_write(file, data)
        with patch.object(Path, "write_bytes", checked):
            result = self.fake(self.canary.encode(), json.dumps({"password": self.canary}).encode())
        self.assertEqual(3, len(writes))
        self.assert_safe(result)

    def test_repeated_redaction_is_idempotent_with_overlapping_values(self):
        longer = self.canary + "_LONGER"
        raw = {"password": self.canary, "token": longer, "diagnostic": longer + ":" + self.canary}
        first = support.redact_value(raw)
        self.assertEqual(first, support.redact_value(first))
        self.assertNotIn(self.canary, json.dumps(first))
        self.assertEqual("[REDACTED]:[REDACTED]", first["diagnostic"])

    def test_marker_prefix_does_not_hide_a_sensitive_value_suffix(self):
        secret = support.REDACTED + self.canary
        safe = support.redact_value({"password": secret, "echo": secret})
        self.assertEqual(support.REDACTED, safe["echo"])

    def test_context_is_not_shared_between_calls(self):
        support.redact_value({"password": self.canary, "echo": self.canary})
        self.assertEqual(self.canary, support.redact_text(self.canary))

    def test_audit_objects_and_sha_bindings_are_not_credentials(self):
        audit = {"effect_authorization": {"authorization_id": "EA-domain", "effect_digest": "a" * 64},
                 "effect_authorization_history": [{"authorizer_identity": "host"}], "source_sha": "b" * 40}
        raw = {"audit": audit, "password": self.canary, "echo": self.canary}
        safe = support.redact_value(raw)
        self.assertEqual(audit, safe["audit"])
        self.assertEqual(support.REDACTED, safe["echo"])

    def test_explicit_short_value_is_not_excluded_by_entropy_heuristic(self):
        safe = support.redact_value({"password": "qz", "echo": "prefix-qz-suffix"})
        self.assertEqual("prefix-[REDACTED]-suffix", safe["echo"])

    def test_explicit_numeric_sensitive_value_masks_numeric_echo(self):
        safe = support.redact_value({"password": 73219, "echo": 73219, "message": "73219"})
        self.assertEqual({key: support.REDACTED for key in safe}, safe)

    def test_many_context_values_fail_closed_before_any_write(self):
        raw = json.dumps([{"password": "synthetic-" + str(i)} for i in range(2050)]).encode()
        with self.assertRaisesRegex(ValueError, "safe limit"):
            self.fake(raw)
        self.assertFalse(self.output.exists())

    def test_deep_objects_fail_closed_before_any_write(self):
        value = {"password": self.canary}
        for _ in range(140):
            value = {"child": value}
        with self.assertRaisesRegex(ValueError, "safe nesting"):
            support.write_json(self.output / "deep.json", value)
        self.assertFalse(self.output.exists())

    def test_sensitive_locator_is_rejected_instead_of_written_or_lied_about(self):
        with self.assertRaisesRegex(ValueError, "locators"):
            with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"", b"")):
                support.run_step(self.root, self.canary, ["unit", "--password", self.canary], self.output, track_source=False)
        self.assertFalse(self.output.exists())

    def test_source_change_still_fails_after_scrubbing(self):
        before = {"sha": "a" * 40, "status": ""}
        after = {"sha": "a" * 40, "status": "changed"}
        with patch.object(support, "source_state", side_effect=[before, after]), \
             patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, self.canary.encode(), b"")):
            with tempfile.TemporaryDirectory(prefix="rls-external-receipts-") as logs:
                self.output = Path(logs)
                result = support.run_step(self.root, "source", ["unit", "--password", self.canary], self.output)
                self.assertFalse(result["success"])
                self.assertFalse(result["source_unchanged"])
                self.assert_safe(result)

    def test_git_error_combines_both_streams_and_argument_context(self):
        with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], 1,
                json.dumps({"password": self.canary}).encode(), self.canary.encode())):
            with self.assertRaises(RuntimeError) as error:
                support.git(self.root, "status")
        self.assertNotIn(self.canary, str(error.exception))

    def test_escaped_duplicate_secret_is_normalized_not_retained(self):
        escaped = "".join("\\u%04x" % ord(char) for char in self.canary)
        raw = '{"password":"' + escaped + '","password":"[REDACTED]"}'
        result = self.fake(raw.encode(), self.canary.encode())
        self.assert_safe(result)
        self.assertNotIn(escaped, result["stdout"])

    def test_duplicate_parent_does_not_hide_discarded_nested_secret(self):
        raw = '{"box":{"password":"' + self.canary + '"},"box":{}}'
        result = self.fake(raw.encode(), self.canary.encode())
        self.assert_safe(result)

    def test_scalar_json_string_echo_is_redacted_after_decoding(self):
        secret = 'SYNTHETIC_口令"\\\n'
        result = self.fake(json.dumps(secret).encode(), json.dumps({"password": secret}).encode())
        self.assertEqual(support.REDACTED, json.loads(result["stdout"]))
        self.assert_safe(result, secret)

    def test_header_argument_propagates_token_to_real_child_streams(self):
        result = self.child("import sys; print(sys.argv[-1].split()[-1]); print(sys.argv[-1].split()[-1],file=sys.stderr)",
                            ["--header", "Authorization: Bearer " + self.canary])
        self.assert_safe(result)

    def test_json_argument_payload_propagates_to_real_child_streams(self):
        result = self.child("import sys,json; x=json.loads(sys.argv[-1])['password']; print(x); print(x,file=sys.stderr)",
                            ["--config", json.dumps({"password": self.canary})])
        self.assert_safe(result)

    def test_program_variable_name_is_not_treated_as_a_password_value(self):
        raw = {"argv": ["python", "-c", "print({'password':x})"], "cwd": "/tmp/example-x"}
        self.assertEqual(raw["cwd"], support.redact_value(raw)["cwd"])

    def test_context_discovered_in_source_metadata_applies_to_streams(self):
        before = {"sha": "a" * 40, "diagnostic": {"password": self.canary}}
        with tempfile.TemporaryDirectory(prefix="rls-source-meta-") as logs:
            self.output = Path(logs)
            with patch.object(support, "source_state", return_value=before), \
                 patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, self.canary.encode(), b"")):
                result = support.run_step(self.root, "metadata", ["unit"], self.output)
            self.assert_safe(result)
            self.assertTrue(result["success"])

    def test_invalid_utf8_and_cross_stream_credential_still_bind_safe_bytes(self):
        result = self.fake(b"\xff" + self.canary.encode(), json.dumps({"password": self.canary}).encode())
        self.assert_safe(result)
        self.assertIn("\ufffd", result["stdout"])

    def test_nonfinite_nested_output_is_rejected_before_write(self):
        with self.assertRaises(ValueError):
            support.write_json(self.output / "bad.json", {"password": self.canary, "value": float("nan")})
        self.assertFalse(self.output.exists())

    def test_nested_writer_retains_json_and_domain_bindings(self):
        obj = {"password": self.canary, "diagnostic": self.canary,
               "child": {"effect_authorization": {"authorization_id": "EA-safe", "effect_digest": "f" * 64}}}
        support.write_json(self.output / "outer.json", obj)
        parsed = json.loads((self.output / "outer.json").read_bytes())
        self.assertEqual(obj["child"], parsed["child"])
        self.assertEqual(support.REDACTED, parsed["diagnostic"])

    def test_safe_nested_receipt_roundtrip_preserves_archived_hashes(self):
        result = self.fake(self.canary.encode(), json.dumps({"password": self.canary}).encode())
        support.write_json(self.output / "outer.json", {"profile": result})
        self.assertEqual(result, json.loads((self.output / "outer.json").read_bytes())["profile"])
        self.assert_safe(result)

    def test_late_context_cannot_silently_invalidate_previously_bound_receipt(self):
        child = {"stdout": self.canary, "stderr": "", "stdout_sha256": support.digest(self.canary.encode()),
                 "stderr_sha256": support.digest(b""), "stream_hashes_bind": "ARCHIVED_REDACTED_UTF8_BYTES"}
        with self.assertRaisesRegex(ValueError, "before its stream hashes"):
            support.write_json(self.output / "outer.json", {"child": child, "password": self.canary})
        self.assertFalse(self.output.exists())

    def test_before_source_error_is_scrubbed_with_invocation_arguments(self):
        with tempfile.TemporaryDirectory(prefix="rls-before-error-") as logs:
            with patch.object(support, "source_state", side_effect=RuntimeError(self.canary)), \
                 patch.object(support.subprocess, "run") as process:
                with self.assertRaises(RuntimeError) as error:
                    support.run_step(self.root, "before", ["unit", "--password", self.canary], logs)
            self.assertNotIn(self.canary, str(error.exception))
            process.assert_not_called()
            self.assertEqual([], list(Path(logs).iterdir()))

    def test_after_source_error_uses_both_captured_streams(self):
        with tempfile.TemporaryDirectory(prefix="rls-after-error-") as logs:
            with patch.object(support, "source_state", side_effect=[{}, RuntimeError(self.canary)]), \
                 patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess([], 0,
                     json.dumps({"password": self.canary}).encode(), b"")):
                with self.assertRaises(RuntimeError) as error:
                    support.run_step(self.root, "after", ["unit"], logs)
            self.assertNotIn(self.canary, str(error.exception))
            self.assertEqual([], list(Path(logs).iterdir()))

    def test_normal_nested_attest_shape_does_not_hit_depth_limit(self):
        value = {"password": self.canary, "diagnostic": self.canary}
        for _ in range(30):
            value = {"profiles": [{"child": value}]}
        cleaned = support.redact_receipt(value)
        self.assertNotIn(self.canary, json.dumps(cleaned))

    def test_both_existing_streams_and_returned_receipt_remain_identical(self):
        result = self.fake(json.dumps({"password": self.canary, "echo": self.canary}).encode(), self.canary.encode())
        self.assert_safe(result)
        self.assertEqual(result, support.redact_receipt(result))

    def test_real_nested_writer_scrubs_its_own_file_before_parent_capture(self):
        program = (
            "import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);"
            "from tools.rls_validation_support import write_json;"
            "x='_'.join(['SYNTHETIC','OPAQUE','VALUE','839247']);"
            "p=Path(sys.argv[2]);write_json(p,{'diagnostic':x,'nested':{'password':x}});"
            "print(p.read_text())"
        )
        child_output = self.root / "child-output.json"
        result = self.child(program, [str(ROOT), str(child_output)])
        self.assertEqual(0, result["exit_code"])
        self.assertNotIn(self.canary, child_output.read_text())
        self.assertEqual(support.REDACTED, json.loads(child_output.read_bytes())["diagnostic"])
        self.assert_safe(result)

    def test_argument_value_with_embedded_equals_and_spaces_is_preserved_for_execution(self):
        secret = self.canary + "=embedded value"
        result = self.child("import sys; print(sys.argv[-1].split('=',1)[1])", ["--password=" + secret])
        self.assertEqual(0, result["exit_code"])
        self.assert_safe(result, secret)

    def test_unterminated_quoted_credential_does_not_drop_last_character(self):
        result = self.fake(self.canary.encode(), ('password="' + self.canary).encode())
        self.assert_safe(result)

    def test_case_insensitive_credential_argument_and_unlabelled_copy(self):
        result = self.fake(self.canary.encode(), self.canary.encode(), argv=["unit", "--DB-PASSWORD", self.canary])
        self.assert_safe(result)


if __name__ == "__main__":
    unittest.main()
