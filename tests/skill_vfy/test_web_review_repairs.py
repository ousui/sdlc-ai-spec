"""Regression tests for independent Web Review findings VFY-WEB-001..006."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/sdlc-500-vfy/scripts"
for entry in (ROOT, SCRIPTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from tests.skill_vfy.support import (  # noqa: E402
    SUBJECT,
    VFO_VER,
    WI,
    delegated_confirmation,
    human_confirmation,
    passing_state,
    prepare_workspace,
    valid_candidate,
)
from vfy_builder import build_state, state_contract_digest  # noqa: E402
from vfy_canonical import validate_primary_against_state  # noqa: E402
from vfy_common import VfyError  # noqa: E402
from vfy_executor import execute_method  # noqa: E402
from vfy_handler import VfyHandler  # noqa: E402
from vfy_persistence import build_payload  # noqa: E402
from vfy_returns import normalize_returns  # noqa: E402
from vfy_verifier import verify_state  # noqa: E402


def load_runtime():
    path = SCRIPTS / "runtime.py"
    spec = importlib.util.spec_from_file_location("vfy_repair_runtime", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WebReviewRepairsTest(unittest.TestCase):
    def test_interface_version_and_skill_bindings(self) -> None:
        interface = json.loads(
            (ROOT / "skills/sdlc-500-vfy/references/interface.json").read_text()
        )
        self.assertEqual("0.3.0", interface["skill_version"])
        skill = (ROOT / "skills/sdlc-500-vfy/SKILL.md").read_text()
        for token in (
            "scripts/sdlc_skill_interface.py",
            "references/interface.json",
            "decision_policy",
            "write_policy",
        ):
            self.assertIn(token, skill)

    def test_persistent_create_requires_repeatable_exact_inputs(self) -> None:
        runtime = load_runtime()
        with tempfile.TemporaryDirectory(prefix="vfy-input-gate-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            with self.assertRaises(VfyError) as error:
                runtime.run_cli(
                    ["create", "--project-root", str(root)],
                    {"candidate": valid_candidate(), "persist": True},
                )
            self.assertEqual("VFY_INPUT_REQUIRED", error.exception.code)

    def test_production_check_rejects_in_memory_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-check-gate-") as directory:
            root = Path(directory)
            state = passing_state(root)
            with self.assertRaises(VfyError) as error:
                VfyHandler(root).check(state=state)
            self.assertEqual("VFY_REFERENCE_REQUIRED", error.exception.code)

    def test_command_policy_rejects_shell_and_inline_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-command-gate-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            commands = (
                ["sh", "-c", "touch /tmp/out"],
                ["bash", "-c", "exit 0"],
                [sys.executable, "-c", "print(1)"],
            )
            for argv in commands:
                candidate = valid_candidate()
                candidate["methods"][0]["procedure"] = {
                    "kind": "command",
                    "argv": argv,
                    "policy": "deterministic-test-v1",
                    "workspace": "isolated-copy",
                    "network": "disabled",
                }
                method = build_state(candidate)["methods"][0]
                with self.assertRaises(VfyError) as error:
                    execute_method(
                        method,
                        project_root=root,
                        evidence_sequence=1,
                        allow_commands=True,
                    )
                self.assertEqual("VFY_METHOD_NOT_READY", error.exception.code)

    def test_builtin_path_check_accepts_a_symlinked_project_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-symlink-root-") as directory:
            parent = Path(directory)
            real_root = parent / "real"
            prepare_workspace(real_root)
            alias_root = parent / "alias"
            alias_root.symlink_to(real_root, target_is_directory=True)
            candidate = valid_candidate()
            candidate["methods"][0]["procedure"] = {
                "kind": "file_exists",
                "path": "missing-required-result.txt",
            }
            method = build_state(candidate)["methods"][0]
            result, evidence = execute_method(
                method,
                project_root=alias_root,
                evidence_sequence=1,
            )
            self.assertEqual("fail", result["result"])
            self.assertEqual("fail", evidence["result"])

    def test_manual_evidence_binds_evaluator_and_immutable_source(self) -> None:
        candidate = valid_candidate()
        candidate["methods"][0].update(
            execution_mode="manual",
            method_type="demonstration",
        )
        with tempfile.TemporaryDirectory(prefix="vfy-manual-gate-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            method = build_state(candidate)["methods"][0]
            observation = {
                "decision": "pass",
                "evaluator_identity": "different-evaluator",
                "observed": "visible",
                "scenario": "open the exact product entry",
                "expected": "entry is visible",
                "scope": "resource:app",
                "observed_at": "2026-09-04T12:00:00Z",
                "evidence": {
                    "reference": "evidence/screen.png",
                    "sha256": "sha256:" + "1" * 64,
                },
            }
            with self.assertRaises(VfyError):
                execute_method(
                    method,
                    project_root=root,
                    evidence_sequence=1,
                    manual_observation=observation,
                )
            observation["evaluator_identity"] = method["executor_identity"]
            observation["evidence"] = "yes"
            with self.assertRaises(VfyError):
                execute_method(
                    method,
                    project_root=root,
                    evidence_sequence=1,
                    manual_observation=observation,
                )

    def test_caller_cannot_mark_return_resolved(self) -> None:
        raw = {
            "id": "RET-001",
            "return_phase": "IMP",
            "target_references": [VFO_VER],
            "method_references": ["VFM-001"],
            "subject_references": [SUBJECT],
            "observed_gap": "exact observed gap",
            "required_outcome": "restore exact outcome",
            "evidence_references": ["EVD-001@sha256:" + "0" * 64],
            "imp_binding_reference": WI,
            "imp_binding_lineage": WI,
            "status": "resolved",
            "resolution_references": ["VFY-20260904130000-01@2#VFM-001"],
        }
        with self.assertRaises(VfyError) as error:
            normalize_returns([raw], subject_lineages={SUBJECT: WI})
        self.assertEqual("VFY_RETURN_INVALID", error.exception.code)

    def test_failure_return_uses_observed_evidence(self) -> None:
        candidate = valid_candidate()
        candidate["methods"][0]["procedure"] = {
            "kind": "file_exists",
            "path": "missing-required-result.txt",
        }
        state = build_state(candidate)
        raw_return = {
            "id": "RET-001",
            "return_phase": "IMP",
            "target_references": [VFO_VER],
            "method_references": ["VFM-001"],
            "subject_references": [SUBJECT],
            "observed_gap": "the required result is absent",
            "required_outcome": "restore the exact required result",
            "evidence_references": ["caller-supplied-placeholder"],
            "imp_binding_reference": WI,
            "imp_binding_lineage": WI,
        }
        with tempfile.TemporaryDirectory(prefix="vfy-return-evidence-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            updated = VfyHandler(root).run_state(
                state,
                method_ids=["VFM-001"],
                allow_commands=False,
                failure_returns={"VFM-001": raw_return},
            )["state"]
        result = next(
            item for item in updated["method_results"] if item["method_id"] == "VFM-001"
        )
        self.assertEqual(result["evidence_references"], updated["returns"][0]["evidence_references"])
        self.assertNotIn("caller-supplied-placeholder", updated["returns"][0]["evidence_references"])

    def test_imp_return_accepts_exact_binding_revision_for_stable_lineage(self) -> None:
        candidate = valid_candidate()
        stable_lineage = WI.split("@", 1)[0] + "#WI-001"
        candidate["subjects"][0]["binding_lineage"] = stable_lineage
        with tempfile.TemporaryDirectory(prefix="vfy-real-binding-lineage-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            state = build_state(candidate)
            (root / "README.md").unlink()
            result = VfyHandler(root).run_state(
                state,
                method_ids=["VFM-001"],
                allow_commands=False,
                failure_returns={
                    "VFM-001": {
                        "return_phase": "IMP",
                        "imp_binding_reference": WI,
                        "imp_binding_lineage": stable_lineage,
                        "observed_gap": "the current result lacks the required file",
                        "required_outcome": "restore the exact required file",
                    }
                },
            )["state"]
        self.assertEqual(WI, result["returns"][0]["imp_binding_reference"])
        self.assertEqual(stable_lineage, result["returns"][0]["imp_binding_lineage"])

    def test_verifier_accepts_an_empty_control_input_set(self) -> None:
        state = build_state(valid_candidate())
        projection = verify_state(state, finalizing=False)
        self.assertEqual([], projection["unresolved_controls"])

    def test_canonical_primary_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-primary-gate-") as directory:
            root = Path(directory)
            state = passing_state(root)
            payload = build_payload(state)
            primary = payload.primary_blob.replace(
                b"VFY Methods", b"VFY Methods tampered", 1
            )
            with self.assertRaises(VfyError):
                validate_primary_against_state(
                    primary,
                    state,
                    member_ids=[item.member_id for item in payload.members],
                )

    def test_pass_with_exception_is_not_plain_pass(self) -> None:
        candidate = valid_candidate()
        candidate["exceptions"] = [
            {
                "id": "EX-001",
                "state": "active",
                "origin_reference": "REQ-20260904100000-01@1#EX-001",
                "scope": ["product_result:fail"],
                "reason": "explicit bounded exception",
                "known_risk": "known residual risk",
                "compensating_control": "monitor exact release target",
                "approval": "Owner at 2026-09-04T12:00:00Z",
                "revisit_condition": "next release",
                "downstream_obligation": "RLS records the accepted risk",
                "resolution_references": [],
                "authority_verified": True,
                "accepts_product_failure": True,
            }
        ]
        with tempfile.TemporaryDirectory(prefix="vfy-exception-gate-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            handler = VfyHandler(root)
            opened = handler.create(
                candidate,
                persist=False,
                run_automated=True,
                finalize=False,
            )["state"]
            confirmation = human_confirmation(root, opened)
            final = handler.run_state(
                opened,
                method_ids=[],
                allow_commands=False,
                finalize=True,
                confirmation=confirmation,
            )["state"]
            self.assertEqual("pass_with_exception", final["artifact_gate"])
            self.assertEqual("ready_with_exception", final["artifact"]["artifact_status"])

    def test_delegated_confirmation_cannot_accept_an_exception(self) -> None:
        candidate = valid_candidate()
        candidate["exceptions"] = [
            {
                "id": "EX-001",
                "state": "active",
                "origin_reference": "REQ-20260904100000-01@1#EX-001",
                "scope": ["product_result:fail"],
                "reason": "explicit bounded exception",
                "known_risk": "known residual risk",
                "compensating_control": "monitor exact release target",
                "approval": "Owner at 2026-09-04T12:00:00Z",
                "revisit_condition": "next release",
                "downstream_obligation": "RLS records the accepted risk",
                "resolution_references": [],
                "authority_verified": True,
                "accepts_product_failure": True,
            }
        ]
        with tempfile.TemporaryDirectory(prefix="vfy-delegated-exception-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            handler = VfyHandler(root)
            opened = handler.create(
                candidate,
                persist=False,
                run_automated=True,
                finalize=False,
            )["state"]
            confirmation = delegated_confirmation(root, opened)
            confirmation["accepted_exception_references"] = [
                f"{opened['artifact']['reference']}#EX-001"
            ]
            with self.assertRaises(VfyError) as error:
                handler.run_state(
                    opened,
                    method_ids=[],
                    allow_commands=False,
                    finalize=True,
                    confirmation=confirmation,
                )
            self.assertEqual("VFY_FINAL_CONFIRMATION_STALE", error.exception.code)

    def test_exception_outside_current_vfy_scope_is_rejected(self) -> None:
        candidate = valid_candidate()
        candidate["exceptions"] = [
            {
                "id": "EX-001",
                "state": "active",
                "origin_reference": "REQ-20260904100000-01@1#EX-001",
                "scope": ["resource:unrelated"],
                "reason": "unrelated exception",
                "known_risk": "unrelated risk",
                "compensating_control": "unrelated control",
                "approval": "Owner at 2026-09-04T12:00:00Z",
                "revisit_condition": "next release",
                "downstream_obligation": "unrelated obligation",
                "resolution_references": [],
                "authority_verified": True,
                "accepts_product_failure": False,
            }
        ]
        with self.assertRaises(VfyError) as error:
            build_state(candidate)
        self.assertEqual("VFY_EXCEPTION_INVALID", error.exception.code)

    def test_pre_execution_digest_includes_exception_boundary(self) -> None:
        state = build_state(valid_candidate())
        original = state["pre_execution_contract_digest"]
        state["exceptions"] = []
        self.assertEqual(original, state_contract_digest(state))


if __name__ == "__main__":
    unittest.main()
