from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = ROOT / "skills/sdlc-status/scripts/runtime.py"
SPEC = importlib.util.spec_from_file_location("sdlc_status_runtime_test", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)

from packages.sdlc_lifecycle import (  # noqa: E402
    LifecycleProjection,
    NextAction,
    ProjectOverview,
    RequirementCandidate,
)


class FakeService:
    def __init__(self, root, *, plugin_root=None, overview=None, projection=None, candidates=()):
        self.root = root
        self._overview = overview
        self._projection = projection
        self._candidates = tuple(candidates)

    def project_overview(self):
        return self._overview

    def list_requirements(self):
        return self._candidates

    def inspect_requirement(self, reference):
        if self._projection.root_reference != reference:
            raise AssertionError(reference)
        return self._projection


class StatusRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def factory(self, overview, projection=None, candidates=()):
        return lambda root, plugin_root=None: FakeService(
            root,
            plugin_root=plugin_root,
            overview=overview,
            projection=projection,
            candidates=candidates,
        )

    def candidate(self, reference, *, head=True):
        artifact_id, revision = reference.split("@")
        return RequirementCandidate(
            reference=reference,
            artifact_id=artifact_id,
            revision=int(revision),
            revision_state="frozen",
            artifact_status="ready",
            gate_result="pass",
            authority_state="valid",
            open_item_count=0,
            lineage_head=head,
        )

    def projection(self, reference):
        return LifecycleProjection(
            root_reference=reference,
            overall_state="ready_for_next_phase",
            nodes=(),
            edges=(),
            frontier=(reference,),
            blockers=(),
            next_actions=(
                NextAction(
                    code="START_NEXT_PHASE",
                    phase="DSN",
                    skill="sdlc-200-dsn",
                    skill_available=False,
                    reason="REQ is ready",
                    command=None,
                    requires_user=True,
                ),
            ),
        )

    def test_meta_commands_do_not_resolve_project(self):
        missing = Path(self.temp.name) / "does-not-exist"
        for command in ("--help", "--version", "--commands", "--examples"):
            result = RUNTIME.run_status([command], cwd=missing)
            self.assertTrue(result["ok"])
            self.assertEqual(result["state"], "meta")
            self.assertIsNone(result["project_root"])
            self.assertFalse((missing / ".sdlc").exists())

    def test_bare_missing_store_is_not_started_and_writes_nothing(self):
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        result = RUNTIME.run_status([], cwd=self.root)
        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "not_started")
        self.assertEqual(before, after)
        self.assertFalse((self.root / ".sdlc").exists())

    def test_auto_inspects_single_requirement(self):
        reference = "REQ-20260831190000-01@1"
        candidate = self.candidate(reference)
        overview = ProjectOverview(
            state="single_requirement",
            context_candidates=(),
            requirement_candidates=(candidate,),
            selected_requirement=reference,
            next_actions=(),
        )
        result = RUNTIME.run_status(
            [],
            cwd=self.root,
            service_factory=self.factory(overview, self.projection(reference), (candidate,)),
        )
        self.assertEqual(result["state"], "ready_for_next_phase")
        self.assertEqual(result["projection"]["root_reference"], reference)
        self.assertEqual(result["effective_write_policy"], "deny")

    def test_multiple_requirements_require_user_selection(self):
        first = self.candidate("REQ-20260831190000-01@1")
        second = self.candidate("REQ-20260831190000-02@1")
        overview = ProjectOverview(
            state="selection_required",
            context_candidates=(),
            requirement_candidates=(first, second),
            selected_requirement=None,
            next_actions=(
                NextAction(
                    code="SELECT_REQUIREMENT",
                    phase="REQ",
                    skill=None,
                    skill_available=False,
                    reason="multiple",
                    command=None,
                    requires_user=True,
                ),
            ),
        )
        result = RUNTIME.run_status(
            [], cwd=self.root, service_factory=self.factory(overview, candidates=(first, second))
        )
        self.assertEqual(result["state"], "selection_required")
        self.assertEqual(result["status"], "action_required")
        self.assertIsNone(result["projection"])

    def test_list_keeps_exact_revisions(self):
        first = self.candidate("REQ-20260831190000-01@1", head=False)
        second = self.candidate("REQ-20260831190000-01@2")
        overview = ProjectOverview(
            state="single_requirement",
            context_candidates=(),
            requirement_candidates=(first, second),
            selected_requirement=second.reference,
            next_actions=(),
        )
        result = RUNTIME.run_status(
            ["list"], cwd=self.root, service_factory=self.factory(overview, candidates=(first, second))
        )
        refs = [item["reference"] for item in result["overview"]["requirement_candidates"]]
        self.assertEqual(refs, [first.reference, second.reference])

    def test_inspect_requires_exact_reference(self):
        result = RUNTIME.run_status(["inspect"], cwd=self.root)
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "reference_required")

    def test_write_policy_is_forced_deny_and_preserved_without_store(self):
        result = RUNTIME.run_status(["--write-policy=auto"], cwd=self.root)
        self.assertEqual(result["effective_write_policy"], "deny")
        self.assertTrue(any(item["code"] == "WRITE_POLICY_FORCED_DENY" for item in result["warnings"]))

    def test_corrupt_store_fails_closed_without_modification(self):
        runtime_dir = self.root / ".sdlc"
        runtime_dir.mkdir()
        database = runtime_dir / "store.sqlite3"
        original = b"not-a-sqlite-database"
        database.write_bytes(original)
        result = RUNTIME.run_status([], cwd=self.root)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["state"], "query_failed")
        self.assertEqual(database.read_bytes(), original)

    def test_debug_output_contains_resolution_without_changing_project(self):
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        result = RUNTIME.run_status(["--output=debug"], cwd=self.root)
        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        self.assertIn("resolved", result)
        self.assertEqual(result["resolved"]["command"], "auto")
        self.assertEqual(before, after)

    def test_cli_json_is_one_document(self):
        completed = subprocess.run(
            [sys.executable, str(RUNTIME_PATH), "--output=json"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        value = json.loads(completed.stdout)
        self.assertEqual(value["contract"], "sdlc-ai-spec/status-result/v1")
        self.assertFalse((self.root / ".sdlc").exists())

    def test_skill_has_no_sibling_invocation(self):
        text = (ROOT / "skills/sdlc-status/SKILL.md").read_text(encoding="utf-8")
        runtime = RUNTIME_PATH.read_text(encoding="utf-8")
        for token in ("invoke_skill", "subprocess.*sdlc-000", "subprocess.*sdlc-100"):
            self.assertNotIn(token, text + runtime)


if __name__ == "__main__":
    unittest.main()
