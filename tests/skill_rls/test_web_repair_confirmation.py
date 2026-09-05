"""RLS-WEB-001/002: real bounded Target and trusted observation modules."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/sdlc-600-rls/scripts"))
from rls_common import RlsError, utc_now
from rls_confirmation_policy import (VERSION_CONTRACT, STATE_CONFIRMATION, STATE_EVIDENCE,
    STATE_EXPECTATION, CAPABILITY_ERROR, compile_confirmation, verify_confirmation_event)
from rls_human_evidence import TrustedHumanObservations, ERROR, MAX_SOURCE_BYTES
from rls_target import SandboxReleaseTarget


class RlsWebRepairConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rls-observation-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = SandboxReleaseTarget(self.root / "target", "sandbox-a")
        state = self.target._default_state()
        state.update(version="1.0.0", health="unhealthy")
        self.target._write_state(state)
        self.row = {"id": "RCF-001", **VERSION_CONTRACT, "source_references": ["VFY-20260905000000-01@1"],
                    "executor": "human-observer", "result": "pending", "follow_up": "none",
                    "observed": None, "subjective": False, "evidence_references": []}
        self.artifact = {"provisional": False,
            "artifact": {"id": "RLS-20260905000000-01", "reference": "RLS-20260905000000-01@1", "revision": 1, "revision_state": "open"},
            "release_contract": {"release_reference": "1.0.0", "scope_reference": "PLN-20260905000000-01@1",
                "result_references": ["IMP-20260905000000-01@1/RESULT-RES-001"],
                "vfy_reference": "VFY-20260905000000-01@1", "vfy_source_digest": "sha256:" + "a" * 64,
                "vfy_candidate_digest": "sha256:" + "b" * 64, "release_target": "sandbox-a",
                "target_locator": str(self.target.root), "target_baseline": self.target.baseline()},
            "target_snapshot_after": self.target.snapshot(), "confirmations": [self.row], "evidence": [], "warnings": []}
        self.host = TrustedHumanObservations(self.root)

    def code(self, expected, function, *args, **kwargs):
        with self.assertRaises(RlsError) as caught:
            function(*args, **kwargs)
        self.assertEqual(expected, caught.exception.code, caught.exception)

    def target_files(self):
        return {p.relative_to(self.target.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.target.root.rglob("*") if p.is_file()}

    def human(self):
        self.row.update(subjective=True, scenario="SCN-ACCEPT-001",
                        confirmation="Check the contracted human acceptance scenario",
                        expected="The specified acceptance scenario is satisfied",
                        evidence_requirement="Original human observation and explicit verdict")

    def record(self, *, result="pass", **changes):
        kwargs = dict(evaluator=self.row["executor"], observed_at=utc_now(), result=result,
                      observation="Explicit synthetic human assessment; not real product acceptance",
                      source_bytes=b"Synthetic immutable human observation for the named scenario.\n", attested=True)
        kwargs.update(changes)
        return self.host.record(self.artifact, self.row["id"], self.target, **kwargs)

    def confirm(self, record=None, **kwargs):
        return self.target.confirm(self.row, "1.0.0", artifact=self.artifact,
                                   trusted_observations=self.host, human_evidence=record, **kwargs)

    def store_outcome(self, result, evidence, observed):
        self.row.update(result=result, observed=observed, evidence_references=[evidence["reference"]])
        self.artifact["evidence"].append(evidence)

    def test_unknown_nonversion_expected_does_not_fall_back_to_version(self):
        self.row.update(confirmation="check target health", expected="health == healthy")
        before = self.target_files()
        self.code(CAPABILITY_ERROR, self.confirm)
        self.assertEqual(before, self.target_files())

    def test_supported_health_mismatch_returns_real_fail(self):
        self.row.update(confirmation=STATE_CONFIRMATION, evidence_requirement=STATE_EVIDENCE,
                        expected=json.dumps({"contract": STATE_EXPECTATION, "equals": {"health": "healthy", "version": "1.0.0"}}))
        result, evidence, observed = self.confirm()
        self.assertEqual("fail", result)
        self.assertEqual("unhealthy", observed["health"])
        self.assertFalse(evidence["event"]["confirmation_evaluation"]["checks"][0]["matched"])
        self.store_outcome(result, evidence, observed)
        verify_confirmation_event(self.artifact, self.row, evidence["event"])

    def test_supported_version_pass_is_limited_to_version_contract(self):
        result, evidence, observed = self.confirm()
        self.assertEqual("pass", result)
        self.assertEqual(["version"], [c["field"] for c in evidence["event"]["confirmation_evaluation"]["checks"]])
        self.store_outcome(result, evidence, observed)
        verify_confirmation_event(self.artifact, self.row, evidence["event"])

    def test_expected_and_evidence_wording_cannot_be_silently_replaced(self):
        for field in VERSION_CONTRACT:
            row = deepcopy(self.row)
            row[field] += " plus additional unsupported checks"
            self.code(CAPABILITY_ERROR, self.target.confirm, row, "1.0.0", artifact=self.artifact)
        self.assertFalse(self.target.evidence_dir.exists())

    def test_all_fields_are_checked_and_missing_field_fails(self):
        self.row.update(confirmation=STATE_CONFIRMATION, evidence_requirement=STATE_EVIDENCE,
                        expected=json.dumps({"contract": STATE_EXPECTATION, "equals": {"missing_field": None, "version": "1.0.0"}}))
        result, evidence, _ = self.confirm()
        self.assertEqual("fail", result)
        self.assertFalse(evidence["event"]["confirmation_evaluation"]["checks"][0]["present"])

    def test_json_boolean_is_not_integer(self):
        state = self.target.snapshot(); state["feature"] = True; self.target._write_state(state)
        self.row.update(confirmation=STATE_CONFIRMATION, evidence_requirement=STATE_EVIDENCE,
                        expected=json.dumps({"contract": STATE_EXPECTATION, "equals": {"feature": 1}}))
        self.assertEqual("fail", self.confirm()[0])

    def test_predicate_parser_rejects_duplicates_nested_paths_and_nonfinite(self):
        self.row.update(confirmation=STATE_CONFIRMATION, evidence_requirement=STATE_EVIDENCE)
        malformed = ['{"contract":"'+STATE_EXPECTATION+'","equals":{"x":1,"x":2}}',
                     json.dumps({"contract": STATE_EXPECTATION, "equals": {"a.b": 1}}),
                     json.dumps({"contract": STATE_EXPECTATION, "equals": {"x": [1]}}),
                     '{"contract":"'+STATE_EXPECTATION+'","equals":{"x":NaN}}']
        for text in malformed:
            self.row["expected"] = text
            self.code(CAPABILITY_ERROR, self.confirm)
        self.assertFalse(self.target.evidence_dir.exists())

    def test_failure_injection_is_explicit_and_not_a_pass_override(self):
        result, evidence, observed = self.confirm(force_fail=True)
        self.assertEqual("fail", result)
        self.assertTrue(evidence["event"]["confirmation_evaluation"]["fault_injected"])
        self.store_outcome(result, evidence, observed)
        verify_confirmation_event(self.artifact, self.row, evidence["event"])

    def test_digest_correct_forged_result_is_rejected(self):
        self.row.update(confirmation=STATE_CONFIRMATION, evidence_requirement=STATE_EVIDENCE,
                        expected=json.dumps({"contract": STATE_EXPECTATION, "equals": {"health": "healthy"}}))
        result, evidence, observed = self.confirm()
        event = deepcopy(evidence["event"]); event["result"] = "pass"
        event["confirmation_evaluation"]["result"] = "pass"
        forged = self.target._evidence(event)
        self.store_outcome("pass", forged, observed)
        self.code("RLS_EVIDENCE_TAMPERED", verify_confirmation_event, self.artifact, self.row, forged["event"])

    def test_bare_human_dict_is_rejected_without_target_evidence(self):
        self.human(); before = self.target_files()
        for record in ({"evaluator": "other", "observed_at": "not-a-timestamp", "observation": "accepted"},
                       {"evaluator": self.row["executor"], "observed_at": utc_now(), "observation": "failed", "result": "fail"}):
            self.code(ERROR, self.confirm, record)
        self.assertEqual(before, self.target_files())

    def test_explicit_human_fail_stays_fail_when_version_matches(self):
        self.human(); record = self.record(result="fail", observation="The acceptance scenario was not satisfied")
        result, evidence, observed = self.confirm(record)
        self.assertEqual("fail", result)
        self.assertEqual("1.0.0", observed["version"])
        self.store_outcome(result, evidence, observed)
        verify_confirmation_event(self.artifact, self.row, evidence["event"])
        self.host.verify_history(self.artifact)

    def test_human_pass_requires_real_host_record_and_source(self):
        self.human(); record = self.record()
        result, evidence, observed = self.confirm(record)
        self.assertEqual("pass", result)
        self.store_outcome(result, evidence, observed)
        verify_confirmation_event(self.artifact, self.row, evidence["event"])
        self.host.verify_history(self.artifact)

    def test_human_scenario_is_required_before_recording(self):
        self.human(); del self.row["scenario"]
        self.code("RLS_TARGET_STATE_UNVERIFIED", self.record)
        self.assertFalse(self.host.records.path.exists())

    def test_human_wrong_executor_rejected_before_host_write(self):
        self.human(); self.code(ERROR, self.record, evaluator="different-person")
        self.assertFalse(self.host.records.path.exists())

    def test_human_invalid_or_future_or_expired_time_rejected_before_write(self):
        self.human()
        times = ["not-a-timestamp", "2026-09-05", "2026-09-05T08:00:00",
                 (datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
                 (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()]
        for value in times:
            self.code(ERROR, self.record, observed_at=value)
        self.assertFalse(self.host.records.path.exists())
        self.assertFalse(self.host.sources.path.exists())

    def test_human_consumption_checks_actual_clock(self):
        self.human(); record = self.record()
        future = (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        with patch("rls_target.utc_now", return_value=future):
            self.code(ERROR, self.confirm, record)
        self.assertFalse(self.target.evidence_dir.exists())

    def test_later_historical_read_does_not_expire_valid_evidence(self):
        self.human(); record = self.record()
        result, evidence, observed = self.confirm(record); self.store_outcome(result, evidence, observed)
        with patch("rls_human_evidence.utc_now", return_value="2099-01-01T00:00:00Z"):
            self.host.verify_history(self.artifact)

    def test_human_wrong_revision_scope_result_target_and_vfy_binding(self):
        self.human(); record = self.record()
        for key, replacement in (("rls_reference", "RLS-20260905000000-02@1"),
             ("rcf_id", "RCF-002"), ("scope_reference", "PLN-20260905000000-02@1"),
             ("result_references", ["different"]), ("release_target", "other"),
             ("target_locator", str(self.root / "other")), ("vfy_source_digest", "sha256:"+"c"*64),
             ("scenario", "other-scenario"), ("executor", "other-person")):
            changed = deepcopy(record); changed["binding"][key] = replacement
            self.code(ERROR, self.confirm, changed)
        self.assertFalse(self.target.evidence_dir.exists())

    def test_human_unknown_or_conflicting_fields_are_rejected(self):
        self.human(); record = self.record()
        for key in ("failed", "extra", "authority"):
            changed = deepcopy(record); changed[key] = True
            self.code(ERROR, self.confirm, changed)
        changed = deepcopy(record); changed["result"] = "accepted"
        self.code(ERROR, self.confirm, changed)

    def test_human_source_missing_or_tampered_is_rejected(self):
        self.human(); record = self.record()
        source = self.host.sources.path / (record["source_digest"][7:]+".txt")
        source.write_bytes(b"changed source")
        self.code(ERROR, self.confirm, record)
        source.unlink(); self.code(ERROR, self.confirm, record)
        self.assertFalse(self.target.evidence_dir.exists())

    def test_human_source_symlink_is_rejected(self):
        self.human(); record = self.record()
        source = self.host.sources.path / (record["source_digest"][7:]+".txt")
        outside = self.root / "outside.txt"; outside.write_bytes(source.read_bytes())
        source.unlink(); source.symlink_to(outside)
        self.code(ERROR, self.confirm, record)
        self.assertFalse(self.target.evidence_dir.exists())

    def test_human_host_record_is_required_not_only_self_consistent_digest(self):
        self.human(); record = self.record()
        (self.host.records.path / (record["observation_id"]+".json")).unlink()
        self.code(ERROR, self.confirm, record)

    def test_secret_rejected_before_human_source_or_record_write(self):
        self.human(); sentinel = ("Bearer " + "SYNTHETIC_DO_NOT_PUBLISH_123456789").encode()
        self.code("RLS_SECRET_REJECTED", self.record, source_bytes=sentinel)
        self.assertFalse(self.host.sources.path.exists())
        self.assertFalse(self.host.records.path.exists())

    def test_oversize_or_binary_human_source_rejected(self):
        self.human()
        self.code(ERROR, self.record, source_bytes=b"x"*(MAX_SOURCE_BYTES+1))
        self.code(ERROR, self.record, source_bytes=b"\xff")
        self.assertFalse(self.host.sources.path.exists())

    def test_human_cannot_be_overridden_by_force_fail_or_used_for_automatic(self):
        self.human(); record = self.record()
        self.code(ERROR, self.confirm, record, force_fail=True)
        self.row.update(subjective=False, **VERSION_CONTRACT)
        self.code(ERROR, self.confirm, record)

    def test_human_record_rejected_after_target_state_drift(self):
        self.human(); record = self.record()
        changed = self.target.snapshot(); changed["health"] = "healthy"; self.target._write_state(changed)
        self.code(ERROR, self.confirm, record)
        self.assertFalse(self.target.evidence_dir.exists())

    def test_human_requires_explicit_host_attestation(self):
        self.human(); self.code(ERROR, self.record, attested=False)
        self.assertFalse(self.host.records.path.exists())

    def test_direct_human_target_call_has_no_untrusted_fast_path(self):
        self.human(); record = self.record()
        self.code(ERROR, self.target.confirm, self.row, "1.0.0", human_evidence=record, artifact=self.artifact)
        self.assertFalse(self.target.evidence_dir.exists())


if __name__ == "__main__":
    unittest.main()
