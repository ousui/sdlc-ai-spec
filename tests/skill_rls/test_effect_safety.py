"""Independent behavioral challenges to the RLS effect boundary."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from tests.skill_rls.final_support import FinalRlsCase, SandboxReleaseTarget, snapshot, run_cli
from rls_authorization import issue_authorization
from rls_execution_journal import ExecutionJournal
from rls_persistence import read_revision
from rls_trusted_effect import TrustedEffectRecords


class RlsEffectSafetyTests(FinalRlsCase):
    def test_forged_json_has_no_host_grant_or_target_effect(self):
        self.create()
        forged = issue_authorization(self.state, ["RLI-001"], "self-described-approver")
        before = snapshot(self.target.root)
        self.code("RLS_EFFECT_AUTHORIZATION_REQUIRED", self.service.execute, self.reference, self.target, ["RLI-001"], forged)
        self.assertEqual(before, snapshot(self.target.root))
        self.assertEqual([], ExecutionJournal(self.root, self.reference).files.names())

    def test_consumed_grant_cannot_replay_even_on_fresh_object(self):
        self.create(); grant = self.grant()
        self.state, self.generation = self.service.execute(self.reference, self.target, ["RLI-001"], grant)
        before = snapshot(self.target.root)
        self.code("RLS_EFFECT_AUTHORIZATION_STALE", self.service.execute, self.reference, self.target, ["RLI-001"], grant)
        self.assertEqual(before, snapshot(self.target.root))

    def test_business_clock_cannot_extend_grant(self):
        self.create(); grant = self.grant()
        self.code("INVALID_ENVELOPE", run_cli, ["execute", "-p", str(self.root), "-r", self.reference, "--item", "RLI-001"],
                  {"sandbox_root": str(self.target.root), "effect_authorization": grant, "now": "2000-01-01T00:00:00Z"})
        self.assertFalse(self.target.state_path.exists())

    def test_target_location_is_part_of_authorized_contract(self):
        self.create(); grant = self.grant()
        with tempfile.TemporaryDirectory(prefix="rls-same-id-other-root-") as directory:
            other = SandboxReleaseTarget(directory, "sandbox-a")
            self.code("RLS_EFFECT_AUTHORIZATION_STALE", self.service.execute, self.reference, other, ["RLI-001"], grant)
            self.assertFalse(other.state_path.exists())

    def test_target_drift_prevents_effect_and_grant_consumption(self):
        self.create(); grant = self.grant()
        drift = self.target._default_state(); drift["version"] = "unrelated"
        self.target._write_state(drift)
        before = snapshot(self.target.root)
        self.code("RLS_EFFECT_AUTHORIZATION_STALE", self.service.execute, self.reference, self.target, ["RLI-001"], grant)
        self.assertEqual(before, snapshot(self.target.root))
        self.assertNotIn(grant["authorization_id"] + ".used.json", TrustedEffectRecords(self.root).files.names())

    def test_second_exception_retains_first_effect_and_blocks_cancel(self):
        self.create(two=True); original = self.target.execute
        def execute(item, release, behavior):
            if item["id"] == "RLI-002":
                raise RuntimeError("second item failed")
            return original(item, release, behavior)
        with patch.object(self.target, "execute", execute):
            self.code("RLS_EXECUTION_UNCERTAIN", self.service.execute, self.reference, self.target,
                      ["RLI-001", "RLI-002"], self.grant(["RLI-001", "RLI-002"]))
        retained, _ = self.service.read(self.reference, recovery=True)
        self.assertEqual("success", retained["release_items"][0]["result"])
        self.assertTrue(retained["evidence"]); self.assertTrue(retained["effect_uncertain"])
        self.assertEqual(["RLI-001"], self.target.snapshot()["applied"])
        self.code("RLS_EXECUTION_UNCERTAIN", self.service.cancel, self.reference, self.target)

    def test_evidence_write_failure_retains_uncertain_target_effect(self):
        self.create(); secret = "sk-abcdefghijklmnop1234"
        with patch.object(self.target, "_evidence", side_effect=OSError(secret)):
            error = self.code("RLS_EXECUTION_UNCERTAIN", self.service.execute, self.reference, self.target, ["RLI-001"], self.grant())
        self.assertNotIn(secret, str(error))
        self.assertEqual("1.0.0", self.target.snapshot()["version"])
        journal = ExecutionJournal(self.root, self.reference)
        self.assertTrue(journal.unresolved())
        records = [journal.files.read(name) for name in journal.files.names()]
        self.assertTrue(any(json.loads(raw)["stage"] == "uncertain" and json.loads(raw)["state"]["target_effect"] for raw in records))
        self.assertFalse(any(secret.encode() in raw for raw in records))
        self.code("RLS_EXECUTION_UNCERTAIN", self.service.cancel, self.reference, self.target)

    def test_effect_then_cas_failure_preserves_recovery_observation(self):
        self.create()
        import rls_service
        original = rls_service.write_open_revision
        calls = 0
        def write(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated post-effect write failure")
            return original(*args, **kwargs)
        with patch.object(rls_service, "write_open_revision", write):
            self.code("RLS_EXECUTION_UNCERTAIN", self.service.execute, self.reference, self.target, ["RLI-001"], self.grant())
        journal = ExecutionJournal(self.root, self.reference)
        records = [json.loads(journal.files.read(name)) for name in journal.files.names()]
        observed = next(x for x in records if x["stage"] == "observed")
        self.assertEqual("success", observed["state"]["release_items"][0]["result"])
        self.assertTrue(observed["state"]["evidence"])
        self.assertEqual("1.0.0", self.target.snapshot()["version"])
        self.code("RLS_EXECUTION_UNCERTAIN", self.service.execute, self.reference, self.target, ["RLI-001"], self.grant())

    def test_symlinked_root_and_path_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rls-escape-") as outside:
            link = self.target.root / "link"; link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError):
                SandboxReleaseTarget(link, "sandbox-a")
            self.code("RLS_PATH_UNSAFE", SandboxReleaseTarget, self.target.root / ".." / "escape", "sandbox-a")
            self.assertEqual([], list(Path(outside).iterdir()))

    def test_symlinked_state_cannot_read_or_modify_outside_file(self):
        self.create()
        with tempfile.TemporaryDirectory(prefix="rls-state-outside-") as directory:
            outside = Path(directory) / "state"; outside.write_text("private outside value")
            self.target.state_path.symlink_to(outside)
            with self.assertRaises(OSError):
                self.service.execute(self.reference, self.target, ["RLI-001"], self.grant())
            self.assertEqual("private outside value", outside.read_text())

    def test_symlinked_evidence_directory_cannot_write_outside(self):
        self.create()
        with tempfile.TemporaryDirectory(prefix="rls-evidence-outside-") as directory:
            self.target.evidence_dir.symlink_to(directory, target_is_directory=True)
            self.code("RLS_EXECUTION_UNCERTAIN", self.service.execute, self.reference, self.target, ["RLI-001"], self.grant())
            self.assertEqual([], list(Path(directory).iterdir()))
            self.assertTrue(ExecutionJournal(self.root, self.reference).unresolved())

    def test_evidence_reference_path_escape_is_rejected(self):
        self.create(); self.execute()
        self.code("RLS_EVIDENCE_TAMPERED", self.target.evidence_bytes, "SANDBOX-EVD-../../private")

    def test_immutable_evidence_rewrite_is_rejected(self):
        self.create(); self.execute()
        evidence = self.state["evidence"][0]
        path = self.target.root / evidence["locator"]
        path.write_bytes(b"tampered")
        self.code("RLS_EVIDENCE_TAMPERED", self.target._evidence, evidence["event"])

    def test_noop_cannot_fabricate_success_on_initial_target(self):
        self.create()
        self.code("RLS_EXECUTION_FAILED", self.service.execute, self.reference, self.target, ["RLI-001"], self.grant(), behaviors={"RLI-001":"no-op"})
        self.assertFalse(self.target.state_path.exists())

    def test_expired_grant_rejected_before_any_new_target_effect(self):
        self.create()
        grant = issue_authorization(self.state, ["RLI-001"], "fixture-host", authorized_at="2020-01-01T00:00:00Z", valid_until="2020-01-01T00:01:00Z")
        records = TrustedEffectRecords(self.root)
        records.files.write(grant["authorization_id"] + ".grant.json", records._raw(grant), exclusive=True)
        self.code("RLS_EFFECT_AUTHORIZATION_STALE", self.service.execute, self.reference, self.target, ["RLI-001"], grant)
        self.assertFalse(self.target.state_path.exists())
