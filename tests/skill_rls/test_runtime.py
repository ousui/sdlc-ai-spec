from __future__ import annotations

from copy import deepcopy
import tempfile
import unittest

from tests.skill_rls.support import artifact, authorize, fixture_payload
from tests.skill_rls.legacy_runtime import parse_command, run_cli


class RlsRuntimeTests(unittest.TestCase):
    def test_all_meta_commands_are_zero_effect(self):
        for command in ("help", "version", "commands", "examples"):
            result, _ = run_cli([command])
            with self.subTest(command=command):
                self.assertTrue(result["ok"])
                self.assertEqual(result["effects"], [])
                self.assertEqual(result["real_target_effects"], 0)

    def test_interface_declares_required_commands(self):
        _shared, spec, _command, _values = parse_command([])
        self.assertEqual(
            set(spec.command_names),
            {"auto","create","execute","confirm","revise","check","cancel","finalize","help","version","commands","examples"},
        )

    def test_unknown_option_fails_closed(self):
        with self.assertRaises(Exception) as caught:
            parse_command(["create", "--targte", "sandbox-a"])
        self.assertEqual(getattr(caught.exception, "code", None), "ARGUMENT_UNKNOWN")

    def test_create_runtime_never_reports_real_target_effect(self):
        payload = fixture_payload("pass")
        payload["target_baseline"] = "N/A — Initial Release"
        result, _ = run_cli(["create", "--target", "sandbox-a", "--release-reference", "1.0.0", "--output", "json"], payload)
        self.assertEqual(result["real_target_effects"], 0)
        self.assertEqual(result["sandbox_target_effects"], 0)

    def test_n_a_runtime_returns_no_artifact(self):
        result, _ = run_cli(["auto"], fixture_payload("n/a"))
        self.assertTrue(result["ok"])
        self.assertIsNone(result["artifact"])

    def test_pending_applicability_is_action_required(self):
        result, _ = run_cli(["auto"], fixture_payload("applicability_pending"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "action_required")

    def test_execute_runtime_requires_authorization(self):
        value = artifact()
        with tempfile.TemporaryDirectory(prefix="rls-runtime-") as root:
            payload = {"artifact":value, "sandbox_root":root, "items":["RLI-001"]}
            with self.assertRaises(Exception) as caught:
                run_cli(["execute"], payload)
        self.assertEqual(getattr(caught.exception, "code", None), "RLS_EFFECT_AUTHORIZATION_REQUIRED")

    def test_execute_runtime_with_authorization_is_sandbox_only(self):
        value = artifact()
        auth = authorize(value)
        with tempfile.TemporaryDirectory(prefix="rls-runtime-") as root:
            payload = {
                "artifact":value, "sandbox_root":root, "items":["RLI-001"],
                "effect_authorization":auth, "now":"2026-09-04T04:05:00Z",
            }
            result, _ = run_cli(["execute"], payload)
        self.assertTrue(result["artifact"]["target_effect"])
        self.assertEqual(result["real_target_effects"], 0)
        self.assertEqual(result["sandbox_target_effects"], 1)

    def test_check_runtime_is_read_only(self):
        value = artifact()
        before = deepcopy(value)
        with tempfile.TemporaryDirectory(prefix="rls-runtime-") as root:
            result, _ = run_cli(["check"], {"artifact":value, "sandbox_root":root})
        self.assertTrue(result["check"]["pending"])
        self.assertEqual(value, before)

    def test_reference_and_item_are_separate(self):
        _shared, _spec, command, values = parse_command(["execute", "-r", "RLS-20260904110000-01@1", "--item", "RLI-001"])
        self.assertEqual(command.artifact_reference, "RLS-20260904110000-01@1")
        self.assertEqual(values["item"], "RLI-001")
        self.assertEqual(values["items"], ["RLI-001"])

    def test_item_option_is_repeatable_in_stable_order(self):
        _shared, _spec, _command, values = parse_command(
            ["execute", "--item", "RLI-002", "--item=RLI-001", "--item", "RLI-002"]
        )
        self.assertEqual(values["items"], ["RLI-002", "RLI-001", "RLI-002"])

    def test_auto_progresses_existing_artifact_without_vfy_payload(self):
        value = artifact()
        auth = authorize(value)
        with tempfile.TemporaryDirectory(prefix="rls-runtime-auto-") as root:
            executed, _ = run_cli(
                ["auto"],
                {
                    "artifact": value,
                    "sandbox_root": root,
                    "effect_authorization": auth,
                    "now": "2026-09-04T04:05:00Z",
                },
            )
            self.assertEqual(executed["artifact"]["release_items"][0]["result"], "success")
            confirmed, _ = run_cli(
                ["auto"],
                {"artifact": executed["artifact"], "sandbox_root": root},
            )
            self.assertEqual(confirmed["artifact"]["confirmations"][0]["result"], "pass")
            frozen, _ = run_cli(
                ["auto"],
                {"artifact": confirmed["artifact"], "sandbox_root": root},
            )
        self.assertEqual(frozen["artifact"]["artifact"]["revision_state"], "frozen")
        self.assertEqual(frozen["artifact"]["release_conclusion"], "success")

    def test_runtime_rejects_target_override_not_bound_by_authorization(self):
        value = artifact()
        auth = authorize(value)
        with tempfile.TemporaryDirectory(prefix="rls-runtime-target-") as root:
            with self.assertRaises(Exception) as caught:
                run_cli(
                    ["execute", "--target", "sandbox-b", "--item", "RLI-001"],
                    {
                        "artifact": value,
                        "sandbox_root": root,
                        "effect_authorization": auth,
                        "now": "2026-09-04T04:05:00Z",
                    },
                )
        self.assertEqual(getattr(caught.exception, "code", None), "RLS_EFFECT_AUTHORIZATION_STALE")

    def test_runtime_rejects_mismatched_artifact_reference(self):
        value = artifact()
        with tempfile.TemporaryDirectory(prefix="rls-runtime-ref-") as root:
            with self.assertRaises(Exception) as caught:
                run_cli(
                    ["check", "-r", "RLS-20260904110000-99@1"],
                    {"artifact": value, "sandbox_root": root},
                )
        self.assertEqual(getattr(caught.exception, "code", None), "RLS_REFERENCE_NOT_EXACT")

    def test_runtime_binds_input_option_to_adapted_vfy_revision(self):
        payload = fixture_payload("pass")
        payload["target_baseline"] = "N/A — Initial Release"
        with self.assertRaises(Exception) as caught:
            run_cli(
                [
                    "create",
                    "-i",
                    "VFY-20260904090000-99@1",
                    "--target",
                    "sandbox-a",
                    "--release-reference",
                    "1.0.0",
                ],
                payload,
            )
        self.assertEqual(getattr(caught.exception, "code", None), "RLS_VFY_NOT_READY")


if __name__ == "__main__":
    unittest.main()
