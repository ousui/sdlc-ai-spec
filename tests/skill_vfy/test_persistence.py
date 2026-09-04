"""Shared ArtifactStore persistence and Revision lineage tests for VFY."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from tests.skill_vfy.support import (
    delegated_confirmation,
    persistent_authority_candidate,
    persistent_passing_fixture,
    persistent_passing_state,
    prepare_workspace,
)
from vfy_handler import VfyHandler


def digest_tree(root: Path) -> str:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(path.relative_to(root).as_posix().encode("utf-8"))
        rows.append(hashlib.sha256(path.read_bytes()).digest())
    return hashlib.sha256(b"\0".join(rows)).hexdigest()


class VfyPersistenceTest(unittest.TestCase):
    def test_exact_reference_failed_run_can_freeze_return(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-store-return-sequence-") as directory:
            root = Path(directory)
            candidate = persistent_authority_candidate(root)
            candidate["methods"][0]["procedure"]["path"] = "MISSING.md"
            handler = VfyHandler(root)
            opened = handler.create(
                candidate,
                persist=True,
                run_automated=False,
            )["state"]
            reference = opened["artifact"]["reference"]
            binding = candidate["scope"]["imp_work_items"][0]["binding_reference"]
            lineage = candidate["subjects"][0]["binding_lineage"]
            executed = handler.run(
                reference=reference,
                state=None,
                store_generation=None,
                persist=True,
                method_ids=None,
                allow_commands=False,
                automated_only=False,
                manual_observations=None,
                failure_returns={
                    "VFM-001": {
                        "return_phase": "IMP",
                        "imp_binding_reference": binding,
                        "imp_binding_lineage": lineage,
                        "observed_gap": "the current result lacks the required file",
                        "required_outcome": "restore the exact required file",
                    }
                },
                early_stop_basis=None,
                finalize=False,
                confirmation=None,
            )["state"]
            finalized = handler.run(
                reference=reference,
                state=None,
                store_generation=None,
                persist=True,
                method_ids=[],
                allow_commands=False,
                automated_only=False,
                manual_observations=None,
                failure_returns=None,
                early_stop_basis=None,
                finalize=True,
                confirmation=delegated_confirmation(
                    root,
                    executed,
                    reviewer="vfy-return-sequence-reviewer",
                    reviewed_executor="external-vfy-executor",
                ),
            )["state"]
            self.assertEqual("frozen", finalized["artifact"]["revision_state"])
            self.assertEqual("fail", finalized["product_result"])
            self.assertEqual(1, len(finalized["returns"]))

    def test_exact_reference_run_can_finalize_after_intermediate_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-store-run-sequence-") as directory:
            root = Path(directory)
            candidate = persistent_authority_candidate(root)
            handler = VfyHandler(root)
            opened = handler.create(
                candidate,
                persist=True,
                run_automated=False,
            )["state"]
            reference = opened["artifact"]["reference"]
            executed = handler.run(
                reference=reference,
                state=None,
                store_generation=None,
                persist=True,
                method_ids=None,
                allow_commands=False,
                automated_only=False,
                manual_observations=None,
                failure_returns=None,
                early_stop_basis=None,
                finalize=False,
                confirmation=None,
            )["state"]
            finalized = handler.run(
                reference=reference,
                state=None,
                store_generation=None,
                persist=True,
                method_ids=[],
                allow_commands=False,
                automated_only=False,
                manual_observations=None,
                failure_returns=None,
                early_stop_basis=None,
                finalize=True,
                confirmation=delegated_confirmation(
                    root,
                    executed,
                    reviewer="vfy-sequence-reviewer",
                    reviewed_executor="external-vfy-executor",
                ),
            )["state"]
            self.assertEqual("frozen", finalized["artifact"]["revision_state"])

    def test_persistent_create_finalizes_and_freezes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-store-create-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            state = persistent_passing_state(root)
            self.assertEqual("frozen", state["artifact"]["revision_state"])
            self.assertEqual("ready", state["artifact"]["artifact_status"])
            self.assertEqual("pass", state["artifact_gate"])
            self.assertFalse(state["rls_ready"])
            self.assertEqual("LIFECYCLE_COMPLETE", state["next_action"])
            self.assertTrue((root / ".sdlc/store.sqlite3").is_file())

    def test_check_of_persisted_revision_is_byte_read_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-store-check-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            handler = VfyHandler(root)
            state = persistent_passing_state(root)
            before = digest_tree(root)
            checked = handler.check(
                reference=state["artifact"]["reference"],
            )
            after = digest_tree(root)
            self.assertEqual(before, after)
            self.assertEqual("pass", checked["projection"]["artifact_gate"])

    def test_revise_reuses_artifact_id_and_allocates_next_revision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-store-revise-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            handler = VfyHandler(root)
            first, candidate = persistent_passing_fixture(root)
            candidate["methods"][0]["pass_criteria"] = (
                "README.md remains observable in the exact IMP product state"
            )
            second = handler.revise(first, candidate, persist=True)["state"]
            self.assertEqual(first["artifact"]["id"], second["artifact"]["id"])
            self.assertEqual(1, first["artifact"]["revision"])
            self.assertEqual(2, second["artifact"]["revision"])
            self.assertEqual(1, second["artifact"]["base_revision"])
            self.assertEqual("open", second["artifact"]["revision_state"])

    def test_no_change_does_not_allocate_revision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vfy-store-no-change-") as directory:
            root = Path(directory)
            prepare_workspace(root)
            handler = VfyHandler(root)
            first, candidate = persistent_passing_fixture(root)
            before = digest_tree(root)
            result = handler.revise(first, candidate, persist=True)
            after = digest_tree(root)
            self.assertEqual("NO_CHANGE", result["status"])
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
