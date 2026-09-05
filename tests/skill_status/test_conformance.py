"""Status boundary regressions and primary oracles for its unchanged Eval Plan."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from tests.skill_status.test_runtime import RUNTIME, FakeService
from packages.sdlc_lifecycle import LifecycleProjection, NextAction, ProjectOverview, RequirementCandidate

REF = "REQ-20260905000000-01@1"


def candidate(reference=REF):
    identity, revision = reference.split("@")
    return RequirementCandidate(reference, identity, int(revision), "frozen", "ready", "pass", "valid", 0, True)


def projection(reference=REF, state="ready_for_next_phase"):
    return LifecycleProjection(reference, state, (), (), (reference,), (),
        (NextAction("START_NEXT_PHASE", "DSN", "sdlc-200-dsn", True, "Confirmed requirement", "/sdlc-200-dsn", False),))


class StatusConformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="status-conformance-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.stat().st_mode, p.read_bytes())
                for p in self.root.rglob("*") if p.is_file()}

    def test_ctx_only_recommends_req_without_writes(self):
        action = NextAction("START_NEXT_PHASE", "REQ", "sdlc-100-req", True,
                            "Confirmed Context", "/sdlc-100-req", False)
        overview = ProjectOverview("context_only", (), (), None, (action,))
        service = FakeService(self.root, overview=overview)
        before = self.snapshot()
        result = RUNTIME.run_status([], cwd=self.root, service_factory=lambda *a, **k: service)
        self.assertTrue(result["ok"], result)
        self.assertEqual("context_only", result["state"])
        self.assertEqual("REQ", result["next_action"]["phase"])
        self.assertEqual(before, self.snapshot())

    def test_exact_inspect_preserves_projection_and_read_only_state(self):
        service = FakeService(self.root, projection=projection())
        before = self.snapshot()
        result = RUNTIME.run_status(["inspect", "-r", REF], cwd=self.root, service_factory=lambda *a, **k: service)
        self.assertEqual(REF, result["projection"]["root_reference"])
        for key in ("nodes", "edges", "frontier", "blockers", "next_actions"):
            self.assertIn(key, result["projection"])
        self.assertEqual("deny", result["effective_write_policy"])
        self.assertEqual(before, self.snapshot())

    def test_symbolic_member_wrong_phase_rejected_before_store(self):
        factory = Mock(side_effect=AssertionError("Store must not be opened"))
        for command in ("auto", "inspect"):
            for ref in ("latest", "current", REF + "#AC-001", "VFY-20260905000000-01@1", "REQ-20260905000000-01@0"):
                with self.subTest(command=command, ref=ref):
                    result = RUNTIME.run_status([command, "-r", ref], cwd=self.root, service_factory=factory)
                    self.assertFalse(result["ok"])
                    self.assertEqual("LIFECYCLE_REFERENCE_INVALID", result["errors"][0]["code"])
        factory.assert_not_called()
        self.assertEqual({}, self.snapshot())

    def test_auto_exact_missing_store_is_not_a_successful_overview(self):
        # STS-E02: an unbound overview still returns not_started with zero writes.
        # Exact references are a separate, stricter obligation, never a fallback.
        for arguments in ([], ["auto"], ["list"]):
            result = RUNTIME.run_status(arguments, cwd=self.root)
            self.assertTrue(result["ok"], result)
            self.assertEqual("not_started", result["state"])
            self.assertEqual("START_PROJECT_CONTEXT", result["next_action"]["code"])
            self.assertEqual([], list(self.root.iterdir()))
        for command in ("auto", "inspect"):
            result = RUNTIME.run_status([command, "-r", REF], cwd=self.root)
            self.assertFalse(result["ok"], result)
            self.assertEqual("store_unavailable", result["state"])
            self.assertIsNone(result["overview"])
        self.assertFalse((self.root / ".sdlc").exists())

    def test_aliases_normalize_to_one_exact_inspection(self):
        service = FakeService(self.root, projection=projection())
        for prefix in (["inspect"], ["--operation=inspect"], ["-o", "inspect"],
                       ["--command", "inspect"], ["-c=inspect"], ["cmd=inspect"], ["--inspect"]):
            with self.subTest(prefix=prefix):
                result = RUNTIME.run_status([*prefix, "--reference", REF], cwd=self.root,
                                            service_factory=lambda *a, **k: service)
                self.assertEqual(REF, result["projection"]["root_reference"])
                self.assertEqual("inspect", result["command"])
                self.assertEqual("deny", result["effective_write_policy"])

    def test_summary_json_debug_describe_same_projection(self):
        service = FakeService(self.root, projection=projection())
        observed = []
        for mode in ("summary", "json", "debug"):
            result = RUNTIME.run_status(["inspect", "-r", REF, "-f", mode], cwd=self.root,
                                       service_factory=lambda *a, **k: service)
            observed.append(result["projection"])
            stream = io.StringIO()
            with redirect_stdout(stream): RUNTIME.emit(result, mode)
            if mode == "summary": self.assertIn(REF, stream.getvalue())
            else: self.assertEqual(result, json.loads(stream.getvalue()))
        self.assertEqual(observed[0], observed[1]); self.assertEqual(observed[1], observed[2])

    def test_meta_json_emits_one_json_document_without_project_access(self):
        factory = Mock(side_effect=AssertionError("meta must not access Store"))
        for command in ("help", "version", "commands", "examples"):
            result = RUNTIME.run_status([command, "--output=json"], cwd=self.root/"absent", service_factory=factory)
            stream = io.StringIO()
            with redirect_stdout(stream): RUNTIME.emit(result, "json")
            self.assertEqual("meta", json.loads(stream.getvalue())["state"])
            self.assertIsNone(result["project_root"])
        factory.assert_not_called()

    def test_debug_does_not_echo_user_prose_or_invalid_reference(self):
        marker = "SYNTHETIC-STATUS-PROBE"
        for args in (["--", "password=" + marker], ["-r", marker]):
            result = RUNTIME.run_status(["--output=debug", *args], cwd=self.root)
            self.assertNotIn(marker, json.dumps(result))

    def test_exception_text_and_details_never_become_result(self):
        from packages.sdlc_lifecycle import LifecycleQueryError
        marker = "SYNTHETIC-STATUS-PROBE"
        for exc in (RuntimeError(marker), LifecycleQueryError(marker, code="STORE_BAD", details={"password": marker})):
            result = RUNTIME.run_status([], cwd=self.root, service_factory=Mock(side_effect=exc))
            self.assertFalse(result["ok"])
            self.assertNotIn(marker, json.dumps(result))
            self.assertRegex(result["errors"][0]["code"], r"^[A-Z][A-Z0-9_]+$")

    def test_unknown_argument_uses_complete_failure_envelope_without_echo(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = RUNTIME.main(["--SYNTHETIC-STATUS-PROBE"])
        result = json.loads(stream.getvalue())
        self.assertEqual(2, code)
        self.assertNotIn("SYNTHETIC-STATUS-PROBE", stream.getvalue())
        self.assertEqual("deny", result["effective_write_policy"])
        self.assertEqual("failed", result["status"])
        self.assertIn("next_action", result)

    def test_auto_selection_required_matches_explicit_inspection(self):
        overview = ProjectOverview("single_requirement", (), (candidate(),), REF, ())
        service = FakeService(self.root, overview=overview, projection=projection(state="selection_required"))
        results = [RUNTIME.run_status(args, cwd=self.root, service_factory=lambda *a, **k: service)
                   for args in ([], ["inspect", "-r", REF])]
        self.assertEqual(["action_required", "action_required"], [r["status"] for r in results])

    def test_multi_target_summary_keeps_every_candidate_without_success_inference(self):
        view = projection().to_dict()
        view["rls_projection"] = {"next_action": "SELECT_RLS_TARGET", "targets": [
            {"release_target":"sandbox-a", "artifact_reference":"RLS-20260905000000-01@1", "release_conclusion":"partial", "artifact_gate":"pass"},
            {"release_target":"sandbox-b", "artifact_reference":"RLS-20260905000000-02@1", "release_conclusion":"failed", "artifact_gate":"pass"},
        ]}
        text = RUNTIME.render_summary({"state":"action_required", "projection":view})
        for token in ("sandbox-a", "sandbox-b", "partial", "failed", "Artifact Gate=pass"):
            self.assertIn(token, text)
        self.assertNotIn("Release Conclusion=success", text)


if __name__ == "__main__": unittest.main()
