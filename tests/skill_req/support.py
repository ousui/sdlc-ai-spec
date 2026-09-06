from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "skills/sdlc-100-req/scripts"
for candidate in (ROOT, ROOT / "packages", SCRIPT_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

spec = importlib.util.spec_from_file_location(
    "sdlc_100_req_runtime_final", SCRIPT_DIR / "runtime_final.py"
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
from packages.sdlc_runtime import parse_canonical_artifact  # noqa: E402
from req_semantics import (  # noqa: E402
    RequirementSemanticError,
    SOURCE_HEADERS,
    validate_persisted_requirement,
)
from packages.sdlc_runtime.canonical import find_tables  # noqa: E402

FIXED = datetime(2026, 8, 31, 3, 0, tzinfo=timezone.utc)


class PassingVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="fixture authority",
        )


class RequirementFixture:
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ArtifactStore.open_read_write(self.root, clock=lambda: FIXED)
        self.store.initialize()
        allocation = self.store.allocate_artifact("CTX", now=FIXED)
        control = self.store.allocate_revision(allocation.artifact_id, now=FIXED)
        raw = b"fixture context"
        self.store.write_open_revision(
            CanonicalRevisionPayload(
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
            ),
            expected_generation=control.generation,
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
        authority = authority_dir / "req-approval.md"
        authority.write_text("Approved by product-owner-1\n", encoding="utf-8")
        self.authority_reference = (
            authority.relative_to(self.root).as_posix()
            + "@"
            + runtime.base.sha256_bytes(authority.read_bytes())
        )
        self.handler = runtime.RequirementHandler(
            self.root,
            clock=lambda: FIXED,
            authority_factory=lambda _: PassingVerifier(),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def requirement(self):
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
                {"phase": "DSN", "disposition": "required", "host": "N/A", "basis": "需要定义导出边界"},
                {"phase": "PLN", "disposition": "required", "host": "N/A", "basis": "需要实施与验证计划"},
                {"phase": "IMP", "disposition": "required", "host": "N/A", "basis": "存在产品修改"},
                {"phase": "VFY", "disposition": "required", "host": "N/A", "basis": "VFY 为固定控制点"},
                {"phase": "RLS", "disposition": "n/a", "host": "N/A", "basis": "Fixture 不执行发版"},
            ],
            "open_items": [],
            "evidence": [],
            "supporting_members": [],
            "exceptions": [],
        }

    def request(self, *, operation="create", reference=None, requirement=None, final=True):
        confirmation = None
        if final:
            confirmation = {
                "mode": "human",
                "confirmer": "product-owner-1",
                "role": "Product Owner",
                "authority_reference": self.authority_reference,
                "confirmed_at": "2026-08-31T03:00:00Z",
            }
        return {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": operation,
            "project_root": str(self.root),
            "artifact_reference": reference,
            "inputs": {
                "context_reference": self.context,
                "requirement": requirement or self.requirement(),
                "control_inputs": [],
                "final_confirmation": confirmation,
            },
            "confirmations": [
                {"type": "artifact_store_write", "approved": True}
            ],
            "options": {"dry_run": False},
        }

