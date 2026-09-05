"""Negative oracles found by the fresh source/Contract review."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

from tests.skill_vfy.support import (
    passing_state, persistent_authority_candidate, valid_candidate,
)
from tests.skill_vfy.sandbox_support import assert_command_unavailable, probe_sandbox_capability
from vfy_authority import compile_candidate
from vfy_builder import build_state
from vfy_canonical import validate_primary_against_state
from vfy_common import VfyError
from vfy_executor import execute_method
from vfy_persistence import build_payload


class FreshReviewBoundariesTest(unittest.TestCase):
    def test_candidate_cannot_replace_frozen_applicability_or_vfo_semantics(self):
        with tempfile.TemporaryDirectory(prefix="vfy-authority-review-") as directory:
            root = Path(directory)
            original = persistent_authority_candidate(root)
            refs = [original["scope"]["reference"], original["subjects"][0]["reference"]]
            self.assertEqual("n/a", compile_candidate(root, refs, original)["rls_applicability"])
            for key, value in (("purpose", "verification"), ("summary", "caller outcome"),
                               ("obligation_references", [])):
                candidate = deepcopy(original)
                candidate["targets"][0][key] = value
                with self.subTest(field=key), self.assertRaises(VfyError):
                    compile_candidate(root, refs, candidate)
            candidate = deepcopy(original)
            candidate["rls_applicability"] = "required"
            with self.assertRaises(VfyError):
                compile_candidate(root, refs, candidate)
            candidate = deepcopy(original)
            candidate["scope"]["reference"] = original["targets"][0]["reference"].split("#")[0]
            candidate["scope"].update(disposition="n/a", disposition_basis="caller bypass")
            refs[0] = candidate["scope"]["reference"]
            with self.assertRaises(VfyError):
                compile_candidate(root, refs, candidate)

    def test_canonical_detail_values_cannot_diverge_from_state(self):
        with tempfile.TemporaryDirectory(prefix="vfy-primary-review-") as directory:
            state = passing_state(Path(directory))
            payload = build_payload(state)
            raw = payload.primary_blob.replace(
                b"README.md exists in the exact Subject workspace", b"always succeeds"
            )
            self.assertNotEqual(raw, payload.primary_blob)
            with self.assertRaises(VfyError):
                validate_primary_against_state(
                    raw, state, member_ids=[member.member_id for member in payload.members]
                )

    def test_command_network_and_outside_write_are_denied_by_os(self):
        with tempfile.TemporaryDirectory(prefix="vfy-sandbox-review-") as directory:
            parent = Path(directory)
            root = parent / "project"
            root.mkdir()
            outside = parent / "outside.txt"
            (root / "test_boundary.py").write_text(
                "import socket, unittest\nfrom pathlib import Path\n"
                "class Boundary(unittest.TestCase):\n"
                " def test_network(self):\n"
                "  with socket.socket() as sock:\n"
                "   with self.assertRaises(OSError): sock.bind(('127.0.0.1', 0))\n"
                " def test_outside_write(self):\n"
                f"  with self.assertRaises(OSError): Path({str(outside)!r}).write_text('outside')\n",
                encoding="utf-8",
            )
            candidate = valid_candidate()
            candidate["methods"][0]["procedure"] = {
                "kind": "command", "argv": ["python3", "-m", "unittest", "test_boundary"],
                "policy": "deterministic-test-v1", "workspace": "isolated-copy",
                "network": "disabled",
            }
            method = build_state(candidate)["methods"][0]
            capability = probe_sandbox_capability()
            if capability["available"]:
                result, evidence = execute_method(
                    method, project_root=root, evidence_sequence=1, allow_commands=True,
                )
                self.assertEqual("pass", result["result"], evidence)
                self.assertEqual("os-sandbox", evidence["observed"]["containment"])
                self.assertEqual(0, evidence["observed"]["exit_code"])
                self.assertIn("Ran 2 tests", evidence["observed"]["stderr"])
            else:
                assert_command_unavailable(self, method, root, capability)
            self.assertFalse(outside.exists())
