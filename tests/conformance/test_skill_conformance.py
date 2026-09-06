"""Negative evidence guards; these tests never certify a real Client."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import validate_skill_conformance as gate


class SkillConformanceTests(unittest.TestCase):
    def ledger(self): return json.loads((gate.ROOT / gate.LEDGER).read_bytes())

    def test_eight_skills_and_forty_native_cells_are_present(self):
        result = gate.validate()
        self.assertTrue(result["success"], result)
        self.assertEqual(8, len(result["skills"]))
        self.assertEqual(40, result["native"]["total"])
        self.assertLessEqual(result["native"]["verified"], 40)

    def test_required_native_target_remains_unverified(self):
        value = self.ledger()
        for row in value["skills"]:
            for cell in row["surfaces"]: cell.update(status="NOT_RUN", receipt=None)
        result = gate.validate_ledger(gate.ROOT, value, required_surface="codex-cli")
        self.assertEqual(8, len(result["required_native_missing"]))

    def test_missing_and_duplicate_skill_fail(self):
        for duplicate in (False, True):
            value = self.ledger()
            if duplicate: value["skills"][1] = deepcopy(value["skills"][0])
            else: value["skills"].pop()
            with self.assertRaises(ValueError): gate.validate_ledger(gate.ROOT, value)

    def test_missing_and_duplicate_surface_fail(self):
        for duplicate in (False, True):
            value = self.ledger()
            if duplicate: value["skills"][0]["surfaces"][1] = deepcopy(value["skills"][0]["surfaces"][0])
            else: value["skills"][0]["surfaces"].pop()
            with self.assertRaises(ValueError): gate.validate_ledger(gate.ROOT, value)

    def test_verified_without_receipt_fails(self):
        value = self.ledger(); value["skills"][0]["surfaces"][0]["status"] = "VERIFIED"
        with self.assertRaises(ValueError): gate.validate_ledger(gate.ROOT, value)

    def test_historical_ctx_report_cannot_certify_current_req(self):
        value = self.ledger(); cell = value["skills"][1]["surfaces"][0]
        cell.update(status="VERIFIED", receipt=value["skills"][0]["historical_evidence"][0]["path"])
        with self.assertRaises((ValueError, json.JSONDecodeError)): gate.validate_ledger(gate.ROOT, value)

    def test_changed_historical_report_digest_fails(self):
        value = self.ledger(); value["skills"][0]["historical_evidence"][0]["sha256"] = "0"*64
        with self.assertRaises(ValueError): gate.validate_ledger(gate.ROOT, value)

    def test_receipt_paths_cannot_escape_or_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); (root / "file").write_text("data"); (root / "link").symlink_to(root / "file")
            for relative in ("../file", "/etc/passwd", "link", "missing", "a/../file"):
                with self.assertRaises(ValueError): gate.file_path(root, relative)

    def test_wrong_client_or_skill_receipt_fails_before_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); path = root / "receipt.json"
            path.write_text(json.dumps({"contract":"sdlc-ai-spec/native-skill-receipt/v1", "observation_source":"native_host", "skill":"sdlc-000-ctx", "surface":"cursor-ide"}))
            with self.assertRaises(ValueError): gate.verify_native_receipt(root, "receipt.json", "sdlc-100-req", "codex-cli")

    def test_static_python_receipt_is_not_native_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); path = root / "receipt.json"
            path.write_text(json.dumps({"contract":"sdlc-ai-spec/native-skill-receipt/v1", "observation_source":"portable_python"}))
            with self.assertRaises(ValueError): gate.verify_native_receipt(root, "receipt.json", "sdlc-000-ctx", "codex-cli")

    def test_fingerprint_is_specific_to_skill_and_surface(self):
        ctx = gate.runtime_snapshot(gate.ROOT, "sdlc-000-ctx", "codex-cli")
        self.assertEqual(64, len(ctx))
        self.assertNotEqual(ctx, gate.runtime_snapshot(gate.ROOT, "sdlc-100-req", "codex-cli"))
        self.assertNotEqual(ctx, gate.runtime_snapshot(gate.ROOT, "sdlc-000-ctx", "cursor-ide"))

    def test_unreviewed_receipt_cannot_hide_in_not_run_cell(self):
        value = self.ledger(); value["skills"][0]["surfaces"][0]["receipt"] = "claim.json"
        with self.assertRaises(ValueError): gate.validate_ledger(gate.ROOT, value)

    def test_human_table_cannot_drift_or_duplicate_machine_cells(self):
        value = self.ledger()
        text = (gate.ROOT / "docs/plugin-development/COMPATIBILITY.md").read_text()
        gate.verify_summary(text, value)
        value["skills"][0]["surfaces"][0]["status"] = "VERIFIED"
        with self.assertRaises(ValueError): gate.verify_summary(text, value)
        value = self.ledger()
        line = next(line for line in text.splitlines() if line.startswith("| sdlc-000-ctx |"))
        with self.assertRaises(ValueError): gate.verify_summary(text + "\n" + line, value)


class NativeReceiptBindingTests(unittest.TestCase):
    """Synthetic receipt fixtures test validation only; not real Client evidence."""
    def setUp(self):
        import subprocess
        tmp = tempfile.TemporaryDirectory(prefix="native-binding-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        for directory in ("packages", "scripts", "skills/_shared", "skills/sdlc-000-ctx", ".codex-plugin", ".agents/plugins"):
            path = self.root / directory / "binding.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(directory + " synthetic fixture\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.DEVNULL, text=True).strip()
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "synthetic native binding fixture")
        self.source = git("rev-parse", "HEAD")
        trace = self.root / "trace.txt"
        trace.write_text("Synthetic guard fixture only. Does not certify a Client.\n")
        self.value = {
            "contract": "sdlc-ai-spec/native-skill-receipt/v1", "observation_source": "native_host",
            "skill": "sdlc-000-ctx", "surface": "codex-cli", "source_sha": self.source,
            "client_version": "fixture-only", "observed_at": "2026-09-05T00:00:00Z", "operator": "fixture-operator",
            "runtime_snapshot_sha256": gate.runtime_snapshot(self.root, "sdlc-000-ctx", "codex-cli"),
            "independent_review": {"verdict": "ACCEPTED", "reviewer": "fixture-reviewer"},
            "checks": [{"id": name, "result": "PASS", "evidence": [{"path": "trace.txt", "sha256": gate.digest(trace)}]} for name in gate.DIMENSIONS],
        }

    def verify(self):
        (self.root / "candidate.json").write_text(json.dumps(self.value))
        return gate.verify_native_receipt(self.root, "candidate.json", "sdlc-000-ctx", "codex-cli")

    def test_complete_synthetic_binding_is_parseable_not_real_certification(self):
        self.assertEqual(self.source, self.verify()["source_sha"])

    def test_stale_runtime_with_recomputed_digest_cannot_claim_old_source(self):
        (self.root / "packages/binding.txt").write_text("new source\n")
        self.value["runtime_snapshot_sha256"] = gate.runtime_snapshot(self.root, "sdlc-000-ctx", "codex-cli")
        with self.assertRaises(ValueError): self.verify()

    def test_raw_log_tamper_is_rejected(self):
        (self.root / "trace.txt").write_text("modified fixture\n")
        with self.assertRaises(ValueError): self.verify()

    def test_self_review_and_missing_native_dimension_are_rejected(self):
        self.value["independent_review"]["reviewer"] = self.value["operator"]
        with self.assertRaises(ValueError): self.verify()
        self.value["independent_review"]["reviewer"] = "fixture-reviewer"
        self.value["checks"].pop()
        with self.assertRaises(ValueError): self.verify()
