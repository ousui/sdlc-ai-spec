import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.skill_imp.support import ENTRY, ImpFixture, OWNER, cli, tree_bytes
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_claim_provider import ClaimProvider
from packages.sdlc_runtime import SkillArgumentError
from imp_common import ImpError, resolve_owner
from imp_result import read_state


class MetaTests(unittest.TestCase):
    def test_meta_commands_do_not_scan_resolve_owner_or_access_stores(self):
        for command in ("help", "version", "commands", "examples", "--help", "-V", "--commands", "--examples"):
            with self.subTest(command=command), \
                 patch.object(Path, "cwd", side_effect=AssertionError("project scan")), \
                 patch.object(ArtifactStore, "open_read_only", side_effect=AssertionError("Store read")), \
                 patch.object(ArtifactStore, "open_read_write", side_effect=AssertionError("Store write")), \
                 patch.object(ClaimProvider, "acquire", side_effect=AssertionError("Claim")), \
                 patch("imp_common.resolve_owner", side_effect=AssertionError("Owner")):
                result, _ = cli.run_cli([command], {"inputs": {"owner": ["ambiguous"]}})
                self.assertTrue(result["ok"])
                self.assertEqual(result["effects"], [])
                self.assertEqual(result["state"], "meta")

    def test_formal_entry_meta_ignores_stdin_and_has_zero_project_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = tree_bytes(root)
            for command in ("help", "version", "commands", "examples"):
                process = subprocess.run([sys.executable, str(ENTRY), command, "-f", "json"],
                                         cwd=root, input="{not valid business JSON", text=True, capture_output=True)
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                self.assertEqual(json.loads(process.stdout)["state"], "meta")
            self.assertEqual(tree_bytes(root), before)

    def test_shared_extensions_honor_equals_conflicts_and_free_text_boundary(self):
        _, command, values = cli.parse_command("create -b=PLN-20260903090000-01@1#WI-001 --owner=stable -- --owner ignored")
        self.assertEqual(values["owner"], "stable")
        self.assertEqual(command.request_text, "--owner ignored")
        for arguments in (
            ["create", "-b", "a", "--binding", "b"],
            ["create", "--owner", "a", "--owner", "b"],
            ["create", "--binding"],
            ["create", "--owner", "--input", "a"],
            ["help", "--binding", "a"],
            ["create", "--unknown"],
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SkillArgumentError):
                cli.parse_command(arguments)

    def test_owner_conflicting_candidates_require_action_and_explicit_wins(self):
        with self.assertRaises(ImpError) as caught:
            resolve_owner(environment={}, candidates=("executor-a", "executor-b"))
        self.assertEqual(caught.exception.status, "action_required")
        self.assertEqual(resolve_owner("explicit", environment={"SDLC_EXECUTOR_TOKEN": "env"},
                                       candidates=("a", "b")), "explicit")

    def test_owner_uses_the_core_identity_token_alphabet(self):
        self.assertEqual(resolve_owner("runner%42+#part"), "runner%42+#part")
        with self.assertRaises(ImpError):
            resolve_owner("runner~42")


class CliTests(ImpFixture):
    def test_binding_long_and_short_enter_the_same_formal_runtime(self):
        method = self.implementation()
        results = []
        for flag in ("--binding", "-b"):
            arguments = ["create", "-p", str(self.root), flag, self.binding, "--owner", OWNER, "--write-policy", "deny"]
            result, _ = cli.run_cli(arguments, {"inputs": {"implementation": method}})
            results.append(result)
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.claim_count(), 0)

    def test_repeatable_input_aliases_preserve_first_occurrence_order(self):
        arguments = ["create", "-p", str(self.root), "-b", self.binding, "--owner", OWNER,
                     "-i", self.dsn_reference, "--input", self.requirement_reference, "-i", self.dsn_reference]
        result, _ = cli.run_cli(arguments, {"inputs": {"implementation": self.implementation()}})
        self.assertEqual(read_state(self.stored(result))["request"]["input_references"],
                         [self.dsn_reference, self.requirement_reference])

    def test_explicit_owner_has_priority_over_environment(self):
        with patch.dict(os.environ, {"SDLC_EXECUTOR_TOKEN": "environment-owner"}):
            result = self.create_open(owner="explicit-owner")
        self.assertEqual(self.info(result)["owner"], "explicit-owner")

    def test_environment_owner_is_stable_across_runtime_calls(self):
        method = self.implementation()
        with patch.dict(os.environ, {"SDLC_EXECUTOR_TOKEN": "environment-owner"}):
            first = self.create_open(owner=None, implementation=method)
            second = self.invoke(owner=None, implementation=method)
        self.assertEqual(self.info(first)["owner"], self.info(second)["owner"])
        self.assertEqual(self.info(first)["attempt"], self.info(second)["attempt"])
        self.assertEqual(self.stored(first).control.generation, self.stored(second).control.generation)

    def test_missing_owner_requires_action_without_claim_allocation(self):
        with patch.dict(os.environ, {}, clear=True):
            result = self.invoke(owner=None, implementation=self.implementation())
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(result["errors"][0]["code"], "IMP_OWNER_MISMATCH")
        self.assertEqual(self.claim_count(), 0)

    def test_formal_subprocess_entry_modifies_only_the_declared_product(self):
        payload = {"inputs": {"implementation": self.implementation()}}
        result = subprocess.run([
            sys.executable, str(ENTRY), "create", "-p", str(self.root), "-b", self.binding,
            "--owner", OWNER, "-f", "json",
        ], cwd=self.root, input=json.dumps(payload), text=True, capture_output=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)  # Final Confirmation is still missing.
        data = json.loads(result.stdout)
        self.assertEqual(data["artifact"]["revision_state"], "open", data)
        self.assertEqual(read_state(self.stored(data))["stage"], "executed")
        self.assertEqual((self.root / "integration/app.txt").read_text(), "version=after\n")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.original_head)

    def test_auto_uses_the_unique_exact_work_item(self):
        result = self.invoke("auto", binding=False, implementation=self.implementation())
        self.assertEqual(self.info(result)["binding"], self.binding)
        self.assertEqual(result["artifact"]["revision_state"], "open")
