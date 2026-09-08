"""Actual installed CLI, valid upstream Authority and public Store readback."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools import run_external_imp_integration as fixture
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_runtime import FrozenArtifactAuthorityVerifier
from packages.sdlc_runtime.envelopes import validate_result

ROOT = Path(__file__).resolve().parents[2]


class DsnInstalledInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install_temp = tempfile.TemporaryDirectory(prefix="dsn-installed-")
        cls.addClassCleanup(cls.install_temp.cleanup)
        cls.plugin = Path(cls.install_temp.name) / "plugin"
        for name in ("skills", "packages", "scripts"):
            shutil.copytree(ROOT / name, cls.plugin / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "AGENTS.md"))
        # Whole Plugin shared resources remain, but no private sibling Skill can rescue DSN.
        for directory in (cls.plugin / "skills").iterdir():
            if directory.is_dir() and directory.name not in {"_shared", "sdlc-200-dsn"}:
                shutil.rmtree(directory)
        cls.entry = cls.plugin / "skills/sdlc-200-dsn/scripts/runtime.py"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dsn-real-upstream-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "README.md").write_text("Nested-input upstream fixture.\n")
        for args in (("init", "-q"), ("add", "README.md"),
                     ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        self.sha = fixture._git(self.root, "rev-parse", "HEAD")
        self.ctx, _ = fixture._create_context(self.root, "fixture/nested-input", self.sha,
                                            fixture._git_state(self.root)["workspace"]["sha256"])
        self.req, _ = fixture._create_requirement(self.root, self.ctx, "fixture/nested-input", self.sha, ".")
        self.store = ArtifactStore.open_read_only(self.root)
        for ref in (self.ctx, self.req):
            resolved = self.store.resolve_exact_reference(ref, verifier=FrozenArtifactAuthorityVerifier(self.root))
            self.assertEqual("frozen", resolved.revision.control.state)

    def state(self):
        catalog = ArtifactCatalog(ArtifactStore.open_read_only(self.root))
        return {item.artifact_id: [asdict(row) for row in catalog.list_revisions(item.artifact_id)]
                for item in catalog.list_artifacts()}

    def snapshot(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob("*") if p.is_file()}

    def cli(self, payload, operation="create", reference=None, dry=False):
        args = [sys.executable, "-B", str(self.entry), operation,
                "--project-root", str(self.root), "--output", "json", "--input", self.req]
        if reference: args += ["--reference", reference]
        if dry: args.append("--dry-run")
        result = subprocess.run(args, input=json.dumps(payload), capture_output=True, text=True,
                                cwd=self.root, timeout=20)
        self.assertEqual("", result.stderr, result.stderr)
        body = validate_result(json.loads(result.stdout))
        self.assertEqual(0 if body["ok"] else 2, result.returncode, result.stdout)
        return body

    def example(self):
        text = (self.plugin / "skills/sdlc-200-dsn/references/input-example.json").read_text()
        self.assertIn("${REQ_REFERENCE}", text)
        return json.loads(text.replace("${REQ_REFERENCE}", self.req))

    def full_request(self):
        design = fixture._design_candidate(self.root, self.req, "fixture/nested-input", self.sha,
                                            (self.root / "README.md").read_bytes(), ".")
        upstream = fixture.UpstreamScope(context_reference=self.ctx, scope_references=(self.req,),
                                        control_references=(), requirement_items=(self.req + "#R-001",),
                                        acceptance_items=(self.req + "#AC-001",))
        normalized = fixture.DsnAnalyzer().analyze(design, upstream).normalized
        confirmation = {"mode": "human", "confirmer": "fixture-design-authority", "role": "Design Authority",
                        "authority_reference": fixture._authority_reference(self.root, "dsn-input-test.md", "Fixture approval only.\n"),
                        "confirmed_at": fixture.FIXED_TEXT,
                        "subject_digest": fixture.dsn_subject_digest(normalized, self.ctx, (self.req,), ())}
        return {"inputs": {"design": design, "final_confirmation": confirmation}}

    def test_contract_only_example_is_executable_without_development_docs(self):
        self.assertFalse((self.plugin / "docs").exists())
        self.assertFalse((self.plugin / "tests").exists())
        self.assertFalse((self.plugin / "skills/sdlc-100-req").exists())
        request = self.example()
        before, bytes_before = self.state(), self.snapshot()
        result = self.cli(request, dry=True)
        self.assertTrue(result["ok"], result)
        self.assertIsNone(result["artifact"])
        self.assertEqual([], result["errors"])
        self.assertEqual(before, self.state()); self.assertEqual(bytes_before, self.snapshot())
        # A valid but intentionally incomplete example persists as open, not false PASS.
        result = self.cli(request)
        self.assertEqual("action_required", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual("open", result["artifact"]["revision_state"])
        stored = self.store.read_revision(result["artifact"]["id"], 1)
        member = next(item for item in stored.payload.members if item.member_id == "DOM-210")
        self.assertIn(request["inputs"]["design"]["domains"]["DOM-210"]["evidence_references"][0]["purpose"],
                      member.raw_bytes.decode())

    def test_real_cli_bad_nested_input_is_side_effect_free_then_retry_freezes(self):
        good = self.full_request()
        domain = next(code for code, row in good["inputs"]["design"]["domains"].items()
                      if code != "DOM-510" and row["disposition"] == "required")
        original_upstream = self.state()
        for field in ("evidence_references", "constraints_impacts", "vfy_points"):
            for dry in (True, False):
                bad = deepcopy(good); bad["inputs"]["design"]["domains"][domain][field] = ["wrong"]
                before, bytes_before = self.state(), self.snapshot()
                result = self.cli(bad, dry=dry)
                self.assertFalse(result["ok"])
                self.assertIsNone(result["artifact"])
                self.assertEqual(f"inputs.design.domains.{domain}.{field}[0]", result["errors"][0]["details"]["path"])
                self.assertEqual(before, self.state()); self.assertEqual(bytes_before, self.snapshot())
        success = self.cli(good)
        self.assertTrue(success["ok"], success)
        ref = success["artifact"]["reference"]
        stored = self.store.read_revision(success["artifact"]["id"], 1)
        self.assertEqual("frozen", stored.control.state)
        for dry in (True, False):
            bad = deepcopy(good); bad["inputs"]["design"]["domains"][domain]["evidence_references"] = ["wrong"]
            before, bytes_before = self.state(), self.snapshot()
            result = self.cli(bad, operation="revise", reference=ref, dry=dry)
            self.assertFalse(result["ok"]); self.assertIsNone(result["artifact"])
            self.assertEqual(before, self.state()); self.assertEqual(bytes_before, self.snapshot())
        before, bytes_before = self.state(), self.snapshot()
        same = self.cli(good, operation="revise", reference=ref)
        self.assertTrue(same["ok"], same)
        self.assertIn("NO_CHANGE", [row["code"] for row in same["warnings"]])
        checked = self.cli({}, operation="check", reference=ref)
        self.assertTrue(checked["ok"], checked)
        self.assertEqual(before, self.state()); self.assertEqual(bytes_before, self.snapshot())
        self.assertEqual(original_upstream, {k: v for k, v in self.state().items() if k in original_upstream})
