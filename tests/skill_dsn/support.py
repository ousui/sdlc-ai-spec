from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "skills/sdlc-200-dsn/scripts"
for candidate in (ROOT, ROOT / "packages", SCRIPT_DIR):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from packages.sdlc_artifact_store import (  # noqa: E402
    ArtifactStore,
    CanonicalManifest,
    CanonicalRevisionPayload,
    DomainVerification,
    compute_sha256,
)
from packages.sdlc_artifact_store.catalog import ArtifactCatalog  # noqa: E402
from packages.sdlc_runtime import execute_phase, sha256_bytes  # noqa: E402
from domain_catalog import COMPOSITE_SUBDOMAINS, DOMAIN_CATALOG  # noqa: E402
from dsn_analyzer import DsnAnalyzer  # noqa: E402
from dsn_common import UpstreamScope, _subject_digest  # noqa: E402
from dsn_handler import DsnHandler  # noqa: E402

FIXED = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


class PassingVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="fixture authority",
        )


def _gate_summary(revision: int = 1, result: str = "pass") -> str:
    return (
        "## 门禁 Gate\n\n"
        "| Evaluated Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Gate Result | Exception References | Evaluator | Evaluated At |\n"
        "|---|---|---|---|---|---|---|---|\n"
        f"| {revision} | sha256:{'a' * 64} | fixture@sha256:{'b' * 64} | sha256:{'c' * 64} | {result} | None | fixture | 2026-09-01T09:00:00Z |\n"
    )


class DsnRuntimeFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ArtifactStore.open_read_write(self.root, clock=lambda: FIXED)
        self.store.initialize()
        self.context_reference = self._create_context()
        self.requirement_reference = self.create_requirement(self.context_reference)
        self.req_id = self.requirement_reference.split("@", 1)[0]
        self.req_item = self.requirement_reference + "#R-001"
        self.ac_item = self.requirement_reference + "#AC-001"
        authority_dir = self.root / ".sdlc" / "authority"
        authority_dir.mkdir(exist_ok=True)
        self.authority_file = authority_dir / "dsn-approval.md"
        self.authority_file.write_text(
            "Approved DSN by design-authority-1\n", encoding="utf-8"
        )
        self.authority_reference = (
            self.authority_file.relative_to(self.root).as_posix()
            + "@"
            + sha256_bytes(self.authority_file.read_bytes())
        )
        self.handler = DsnHandler(
            self.root,
            clock=lambda: FIXED,
            upstream_verifier_factory=lambda _: PassingVerifier(),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _write_frozen(self, artifact_type: str, raw: bytes) -> str:
        allocation = self.store.allocate_artifact(artifact_type, now=FIXED)
        control = self.store.allocate_revision(allocation.artifact_id, now=FIXED)
        payload = CanonicalRevisionPayload(
            artifact_id=allocation.artifact_id,
            artifact_type=artifact_type,
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
        return allocation.artifact_id + "@1"

    def _create_context(self) -> str:
        artifact_id = "CTX-20260901090000-01"
        raw = (
            "---\n"
            "contract: sdlc-ai-spec/project-context/v1\n"
            f"id: {artifact_id}\n"
            "revision: 1\n"
            "status: ready\n"
            "---\n"
            "# Fixture Context\n\n"
            + _gate_summary()
        ).encode("utf-8")
        return self._write_frozen("CTX", raw)

    def create_requirement(self, context_reference: str) -> str:
        next_number = len(ArtifactCatalog(self.store).list_artifacts("REQ")) + 1
        artifact_id = f"REQ-20260901090000-{next_number:02d}"
        raw = (
            "---\n"
            "contract: sdlc-ai-spec/artifact/v1\n"
            "phase: REQ\n"
            f"id: {artifact_id}\n"
            "revision: 1\n"
            "status: ready\n"
            f"context: {context_reference}\n"
            "profile: full\n"
            "inputs: []\n"
            "---\n"
            "# Fixture Requirement\n\n"
            "| ID | 类型 Type | 来源或父项引用 Source or Parent References | 需求描述 Requirement Statement |\n"
            "|---|---|---|---|\n"
            "| R-001 | behavior | SRC-001 | 已授权用户可以导出当前筛选结果 |\n\n"
            "| ID | 关联需求 Requirement References | 条件 Condition | 预期结果 Expected Result |\n"
            "|---|---|---|---|\n"
            "| AC-001 | R-001 | 用户具有权限并应用筛选条件 | 导出记录与筛选结果一致 |\n\n"
            + _gate_summary()
        ).encode("utf-8")
        return self._write_frozen("REQ", raw)

    def complete_design(
        self,
        *,
        scope_references: tuple[str, ...] | None = None,
        requirement_items: tuple[str, ...] | None = None,
        acceptance_items: tuple[str, ...] | None = None,
        require_workflow: bool = False,
    ):
        scopes = scope_references or (self.requirement_reference,)
        req_items = requirement_items or (self.req_item,)
        ac_items = acceptance_items or (self.ac_item,)
        basis = req_items[0]
        domains = {}
        for definition in DOMAIN_CATALOG:
            if definition.code == "DOM-510":
                domains[definition.code] = {
                    "disposition": "required",
                    "completion": "complete",
                    "responsible_role": "Verification Architect",
                    "basis_references": [basis],
                    "reason": "VFY strategy is mandatory for every DSN",
                    "design_result_markdown": (
                        "## 设计结果 Design Result\n\n"
                        "### VFY 目标 VFY Objectives\n\n"
                        "| ID | Source References | Objective | Observable Result |\n"
                        "|---|---|---|---|\n"
                        f"| OBJ-001 | {', '.join(ac_items)} | 验证导出设计 | 导出结果与筛选一致 |\n\n"
                        "### 方法选择 VFY Methods\n\n"
                        "| Objective | Method | Rationale |\n|---|---|---|\n"
                        "| OBJ-001 | integration | 覆盖端到端行为 |\n\n"
                        "### 通过条件 Pass Criteria\n\n"
                        "| Objective | Pass Criteria |\n|---|---|\n"
                        "| OBJ-001 | 全部筛选记录准确导出 |\n\n"
                        "### Evidence Contract\n\n"
                        "| Objective | Evidence |\n|---|---|\n"
                        "| OBJ-001 | 可复核导出文件与查询快照 |"
                    ),
                    "constraints_impacts": [],
                    "vfy_points": [],
                    "evidence_references": [],
                }
            elif definition.code == "DOM-110" and require_workflow:
                domains[definition.code] = {
                    "disposition": "required",
                    "completion": "complete",
                    "responsible_role": "Backend Architect",
                    "basis_references": [basis],
                    "reason": "Export introduces an explicit processing flow",
                    "design_result_markdown": (
                        "## 设计结果 Design Result\n\n"
                        "### 流程 Flow\n\n"
                        "| ID | Trigger | Result |\n|---|---|---|\n"
                        "| FLW-001 | export request | file generated |"
                    ),
                    "constraints_impacts": [],
                    "vfy_points": [
                        {
                            "id": "VFP-110-001",
                            "references": [basis],
                            "verification_object": "export workflow",
                            "observable_result": "request reaches terminal success",
                            "expected_evidence": "workflow trace",
                        }
                    ],
                    "evidence_references": [],
                }
            else:
                domains[definition.code] = {
                    "disposition": "n/a",
                    "completion": "not_applicable",
                    "basis_references": [basis],
                    "reason": "Current fixture scope introduces no obligation in this domain",
                }

        composite = [
            {
                "domain_code": code,
                "subdomain": name,
                "disposition": "n/a",
                "basis_references": [basis],
                "reason": "Current fixture scope introduces no obligation",
                "exception_references": [],
            }
            for code, name in COMPOSITE_SUBDOMAINS
        ]
        trace_sources = [*req_items, *ac_items]
        return {
            "title": "批量导出设计",
            "summary": "为筛选结果提供受控、可验证的导出设计。",
            "boundary": "当前列表筛选结果的同步导出链路",
            "profile": "full",
            "change_type": "new",
            "baseline_references": [],
            "target_state_summary": "已授权用户可以获取准确的筛选结果文件",
            "impact_summary": "新增导出处理与可验证结果",
            "changes": [
                {
                    "id": "CHG-001",
                    "object_or_boundary": "resource:springgear-export",
                    "change": "add",
                    "baseline_references": [],
                    "baseline_state": "N/A",
                    "target_state": "提供受控导出能力",
                    "affected_domains": ["DOM-510"]
                    + (["DOM-110"] if require_workflow else []),
                }
            ],
            "traceability": [
                {
                    "source_references": trace_sources,
                    "design_references": ["DOM-510"],
                    "decision_references": [],
                    "vfy_references": ["OBJ-001"],
                    "na_reason": "N/A",
                }
            ],
            "decisions": [],
            "decision_none_reason": "Requirement and fixed constraints determine one direct design",
            "domains": domains,
            "composite_subdomains": composite,
            "cross_domain_conflicts": [],
            "scope_expansion": False,
            "simplicity_rationale": "Use the minimum synchronous export flow required by the Requirement",
            "lifecycle_applicability": [
                {
                    "phase": "PLN",
                    "disposition": "required",
                    "host": "N/A",
                    "basis": "Implementation spans design and verification work",
                },
                {
                    "phase": "IMP",
                    "disposition": "required",
                    "host": "N/A",
                    "basis": "Product code must change",
                },
                {
                    "phase": "VFY",
                    "disposition": "required",
                    "host": "N/A",
                    "basis": "VFY is the mandatory control point",
                },
                {
                    "phase": "RLS",
                    "disposition": "n/a",
                    "host": "N/A",
                    "basis": "Fixture does not include release execution",
                },
            ],
            "evidence": [
                {
                    "id": "EVD-001",
                    "type": "artifact",
                    "supports_references": [basis],
                    "source": "fixture",
                    "reference": scopes[0],
                    "digest": "N/A",
                    "produced_at": "2026-09-01T09:00:00Z",
                    "sensitivity": "internal",
                }
            ],
            "supporting_members": [],
            "open_items": [],
            "exceptions": [],
        }

    def upstream(
        self,
        *,
        scope_references: tuple[str, ...] | None = None,
        requirement_items: tuple[str, ...] | None = None,
        acceptance_items: tuple[str, ...] | None = None,
    ) -> UpstreamScope:
        return UpstreamScope(
            context_reference=self.context_reference,
            scope_references=scope_references or (self.requirement_reference,),
            control_references=(),
            requirement_items=requirement_items or (self.req_item,),
            acceptance_items=acceptance_items or (self.ac_item,),
        )

    def final_confirmation(self, design, upstream: UpstreamScope | None = None):
        value = upstream or self.upstream()
        normalized = DsnAnalyzer().analyze(design, value).normalized
        return {
            "mode": "human",
            "confirmer": "design-authority-1",
            "role": "Design Authority",
            "authority_reference": self.authority_reference,
            "confirmed_at": "2026-09-01T09:00:00Z",
            "subject_digest": _subject_digest(
                normalized,
                value.context_reference,
                value.scope_references,
                value.control_references,
            ),
        }

    def invocation(
        self,
        *,
        operation: str = "create",
        reference: str | None = None,
        design=None,
        final: bool = True,
        scope_inputs: tuple[str, ...] | None = None,
    ):
        scopes = scope_inputs or (self.requirement_reference,)
        req_items = tuple(
            reference + "#R-001" for reference in scopes
        )
        ac_items = tuple(
            reference + "#AC-001" for reference in scopes
        )
        candidate = design or self.complete_design(
            scope_references=scopes,
            requirement_items=req_items,
            acceptance_items=ac_items,
        )
        upstream = self.upstream(
            scope_references=scopes,
            requirement_items=req_items,
            acceptance_items=ac_items,
        )
        confirmation = self.final_confirmation(candidate, upstream) if final else None
        return {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": operation,
            "project_root": str(self.root),
            "artifact_reference": reference,
            "inputs": {
                "scope_inputs": list(scopes),
                "control_inputs": [],
                "design": candidate,
                "final_confirmation": confirmation,
            },
            "confirmations": [],
            "options": {"dry_run": False, "write_policy": "auto"},
        }

    def execute(self, invocation):
        return execute_phase(self.handler, invocation)
