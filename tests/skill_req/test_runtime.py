from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "skills/sdlc-100-req/scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(SCRIPT_DIR))

spec = importlib.util.spec_from_file_location(
    "sdlc_100_req_runtime_entry", SCRIPT_DIR / "runtime_entry.py"
)
runtime = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(runtime)

from packages.sdlc_artifact_store import (  # noqa: E402
    ArtifactStore,
    CanonicalManifest,
    CanonicalRevisionPayload,
    DomainVerification,
    compute_sha256,
)

FIXED = datetime(2026, 8, 31, 2, 30, tzinfo=timezone.utc)


class PassingVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="fixture authority",
        )


class RequirementRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ArtifactStore.open_read_write(
            self.root, clock=lambda: FIXED
        )
        self.store.initialize()
        allocation = self.store.allocate_artifact("CTX", now=FIXED)
        control = self.store.allocate_revision(allocation.artifact_id, now=FIXED)
        raw = b"fixture context"
        payload = CanonicalRevisionPayload(
            artifact_id=allocation.artifact_id,
            artifact_type="CTX",
            revision=1,
            artifact_status="ready",
            primary_blob=raw,
            primary_media_type="text/markdown",
            primary_sha256=compute_sha256(raw),
            members=(),
            manifest=CanonicalManifest(
                raw_bytes=b'{"local_members":[]}',
                media_type="application/json",
                local_members=(),
            ),
        )
        self.store.write_open_revision(
            payload, expected_generation=control.generation
        )
        self.store.freeze_revision(
            allocation.artifact_id,
            1,
            verifier=PassingVerifier(),
            now=FIXED,
        )
        self.context = allocation.artifact_id + "@1"
        authority_dir = self.root / ".sdlc" / "authority"
        authority_dir.mkdir()
        self.authority = authority_dir / "req-approval.md"
        self.authority.write_text("Approved by product-owner-1\n", encoding="utf-8")
        self.authority_reference = (
            self.authority.relative_to(self.root).as_posix()
            + "@"
            + runtime.base.sha256_bytes(self.authority.read_bytes())
        )
        self.handler = runtime.RequirementHandler(
            self.root,
            clock=lambda: FIXED,
            authority_factory=lambda _: PassingVerifier(),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _requirement(self):
        return {
            "title": "支持批量导出",
            "summary": "允许已授权用户导出当前筛选结果。",
            "sources": [
                {
                    "type": "text",
                    "content": "需要导出筛选后的结果",
                    "evidence_reference": "N/A",
                }
            ],
            "goals": [
                {
                    "problem": "当前只能逐页复制",
                    "outcome": "授权用户可下载筛选结果",
                    "success_condition": "导出内容与筛选结果一致",
                }
            ],
            "in_scope": ["当前列表筛选结果"],
            "out_of_scope": ["后台定时导出"],
            "affected_parties": [
                {"party": "运营人员", "impact": "减少手工复制"}
            ],
            "requirements": [
                {
                    "type": "behavior",
                    "source_references": ["SRC-001", "GOAL-001"],
                    "statement": "系统允许已授权用户导出当前筛选结果。",
                }
            ],
            "acceptance_criteria": [
                {
                    "requirement_references": ["R-001"],
                    "condition": "用户具有导出权限并应用筛选条件",
                    "expected_result": "下载文件中的记录与筛选结果一致",
                }
            ],
            "dependencies": [],
            "profile": "full",
            "profile_basis": "行为变化且需要完整验证",
            "lifecycle_applicability": [
                {
                    "phase": "DSN",
                    "disposition": "required",
                    "host": "N/A",
                    "basis": "需要定义导出边界",
                },
                {
                    "phase": "PLN",
                    "disposition": "required",
                    "host": "N/A",
                    "basis": "需要实施与验证计划",
                },
                {
                    "phase": "IMP",
                    "disposition": "required",
                    "host": "N/A",
                    "basis": "存在产品修改",
                },
                {
                    "phase": "VFY",
                    "disposition": "required",
                    "host": "N/A",
                    "basis": "VFY 为固定控制点",
                },
                {
                    "phase": "RLS",
                    "disposition": "n/a",
                    "host": "N/A",
                    "basis": "本 Fixture 不执行正式发版",
                },
            ],
            "open_items": [],
            "evidence": [],
            "supporting_members": [],
            "exceptions": [],
        }

    def _request(self, requirement=None, *, final=True, authorized=True):
        final_confirmation = None
        if final:
            final_confirmation = {
                "mode": "human",
                "confirmer": "product-owner-1",
                "role": "Product Owner",
                "authority_reference": self.authority_reference,
                "confirmed_at": "2026-08-31T02:30:00Z",
            }
        return {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": "create",
            "project_root": str(self.root),
            "artifact_reference": None,
            "inputs": {
                "context_reference": self.context,
                "requirement": requirement or self._requirement(),
                "control_inputs": [],
                "final_confirmation": final_confirmation,
            },
            "confirmations": (
                [{"type": "artifact_store_write", "approved": True}]
                if authorized
                else []
            ),
            "options": {"dry_run": False},
        }

    def test_complete_create_freezes_ready_requirement(self):
        result = runtime.execute_phase(self.handler, self._request())
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["gate"]["result"], "pass")
        self.assertEqual(result["artifact"]["revision_state"], "frozen")
        self.assertEqual(result["artifact"]["artifact_status"], "ready")

    def test_missing_content_persists_waiting_input(self):
        result = runtime.execute_phase(
            self.handler,
            self._request(requirement={"profile": "full"}, final=False),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(result["artifact"]["revision_state"], "open")
        self.assertEqual(result["artifact"]["artifact_status"], "waiting_input")
        self.assertTrue(result["open_items"])

    def test_missing_write_authorization_creates_no_req(self):
        before = self.store._connect().execute(
            "SELECT COUNT(*) AS n FROM artifacts WHERE artifact_type='REQ'"
        ).fetchone()["n"]
        result = runtime.execute_phase(
            self.handler, self._request(authorized=False)
        )
        after = self.store._connect().execute(
            "SELECT COUNT(*) AS n FROM artifacts WHERE artifact_type='REQ'"
        ).fetchone()["n"]
        self.assertEqual(before, after)
        self.assertEqual(result["status"], "action_required")
        self.assertEqual(result["errors"][0]["code"], "WRITE_AUTHORIZATION_REQUIRED")

    def test_cycle_fails_requirement_gate(self):
        value = self._requirement()
        value["requirements"] = [
            {
                "type": "behavior",
                "source_references": ["R-002"],
                "statement": "A",
            },
            {
                "type": "rule",
                "source_references": ["R-001"],
                "statement": "B",
            },
        ]
        value["acceptance_criteria"] = [
            {
                "requirement_references": ["R-001", "R-002"],
                "condition": "执行",
                "expected_result": "满足",
            }
        ]
        result = runtime.execute_phase(
            self.handler, self._request(requirement=value, final=False)
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("REQ-G-005", result["gate"]["failed_checks"])
        self.assertEqual(result["artifact"]["artifact_status"], "failed")

    def test_frozen_check_is_read_only_and_complete(self):
        created = runtime.execute_phase(self.handler, self._request())
        request = {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": "check",
            "project_root": str(self.root),
            "artifact_reference": created["artifact"]["reference"],
            "inputs": {},
        }
        result = runtime.execute_phase(self.handler, request)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["gate"]["result"], "pass")

    def test_open_revision_is_revised_in_place(self):
        first = runtime.execute_phase(
            self.handler, self._request(final=False)
        )
        reference = (
            first["artifact"]["id"] + "@" + str(first["artifact"]["revision"])
        )
        request = self._request(final=True)
        request["operation"] = "revise"
        request["artifact_reference"] = reference
        result = runtime.execute_phase(self.handler, request)
        self.assertTrue(result["ok"])
        self.assertEqual(result["artifact"]["revision"], 1)
        self.assertEqual(result["artifact"]["revision_state"], "frozen")

    def test_check_missing_store_does_not_create_runtime(self):
        other = Path(self.temporary.name) / "missing"
        other.mkdir()
        handler = runtime.RequirementHandler(
            other, authority_factory=lambda _: PassingVerifier()
        )
        request = {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": "check",
            "project_root": str(other),
            "artifact_reference": "REQ-20260831023000-01@1",
            "inputs": {},
        }
        result = runtime.execute_phase(handler, request)
        self.assertEqual(result["errors"][0]["code"], "STORE_NOT_FOUND")
        self.assertFalse((other / ".sdlc").exists())


if __name__ == "__main__":
    unittest.main()
