#!/usr/bin/env python3
"""Run a temporary CTX -> REQ -> DSN -> lifecycle integration on any Git project.

The target project is test input only. This harness writes only its temporary
``.sdlc`` runtime directory, removes it before exit, and never commits or pushes.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DSN_SCRIPTS = ROOT / "skills/sdlc-200-dsn/scripts"
for candidate in (ROOT, ROOT / "packages", DSN_SCRIPTS):
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
from packages.sdlc_lifecycle import LifecycleQueryService  # noqa: E402
from packages.sdlc_runtime import execute_phase, sha256_bytes  # noqa: E402
from domain_catalog import COMPOSITE_SUBDOMAINS, DOMAIN_CATALOG  # noqa: E402
from dsn_analyzer import DsnAnalyzer  # noqa: E402
from dsn_common import _subject_digest  # noqa: E402
from dsn_handler_final import DsnHandler  # noqa: E402

FIXED = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


class PassingVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="external integration fixture authority",
        )


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _snapshot(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or relative.parts[0] in {".git", ".sdlc"}:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _gate_summary(revision: int = 1) -> str:
    return (
        "## 门禁 Gate\n\n"
        "| Evaluated Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Gate Result | Exception References | Evaluator | Evaluated At |\n"
        "|---|---|---|---|---|---|---|---|\n"
        f"| {revision} | sha256:{'a' * 64} | integration@sha256:{'b' * 64} | sha256:{'c' * 64} | pass | None | integration | 2026-09-01T10:00:00Z |\n"
    )


def _write_frozen(store: ArtifactStore, artifact_type: str, raw: bytes) -> str:
    allocation = store.allocate_artifact(artifact_type, now=FIXED)
    control = store.allocate_revision(allocation.artifact_id, now=FIXED)
    store.write_open_revision(
        CanonicalRevisionPayload(
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
        ),
        expected_generation=control.generation,
    )
    store.freeze_revision(
        allocation.artifact_id,
        1,
        verifier=PassingVerifier(),
        now=FIXED,
    )
    return allocation.artifact_id + "@1"


def _create_upstream(store: ArtifactStore) -> tuple[str, str]:
    context_id = "CTX-20260901100000-01"
    context = _write_frozen(
        store,
        "CTX",
        (
            "---\n"
            "contract: sdlc-ai-spec/project-context/v1\n"
            f"id: {context_id}\n"
            "revision: 1\n"
            "status: ready\n"
            "---\n"
            "# External Project Context\n\n"
            + _gate_summary()
        ).encode("utf-8"),
    )
    requirement_id = "REQ-20260901100000-01"
    requirement = _write_frozen(
        store,
        "REQ",
        (
            "---\n"
            "contract: sdlc-ai-spec/artifact/v1\n"
            "phase: REQ\n"
            f"id: {requirement_id}\n"
            "revision: 1\n"
            "status: ready\n"
            f"context: {context}\n"
            "profile: full\n"
            "inputs: []\n"
            "---\n"
            "# External Project Integration Requirement\n\n"
            "| ID | 类型 Type | 来源或父项引用 Source or Parent References | 需求描述 Requirement Statement |\n"
            "|---|---|---|---|\n"
            "| R-001 | constraint | SRC-001 | 当前项目的模块与构建边界必须形成可实施、可验证的设计 |\n\n"
            "| ID | 关联需求 Requirement References | 条件 Condition | 预期结果 Expected Result |\n"
            "|---|---|---|---|\n"
            "| AC-001 | R-001 | 对当前项目执行设计阶段 | 生成完整 DSN Artifact Set 并得到下一阶段 Projection |\n\n"
            "| Phase | Disposition | Host | 判断依据 Basis |\n"
            "|---|---|---|---|\n"
            "| DSN | required | N/A | 项目模块和构建边界需要设计确认 |\n"
            "| PLN | required | N/A | 需要后续计划 |\n"
            "| IMP | required | N/A | 后续实施需要修改或验证工程资源 |\n"
            "| VFY | required | N/A | VFY 是固定控制点 |\n"
            "| RLS | n/a | N/A | 本次只执行设计集成测试 |\n\n"
            + _gate_summary()
        ).encode("utf-8"),
    )
    return context, requirement


def _modules(root: Path) -> list[str]:
    result = [
        child.name
        for child in root.iterdir()
        if child.is_dir() and (child / "pom.xml").is_file()
    ]
    return sorted(result) or [root.name]


def _design(root: Path, requirement: str) -> dict[str, Any]:
    modules = _modules(root)
    requirement_item = requirement + "#R-001"
    acceptance_item = requirement + "#AC-001"
    module_text = ", ".join(modules)
    domains: dict[str, dict[str, Any]] = {}
    for definition in DOMAIN_CATALOG:
        if definition.code == "DOM-210":
            domains[definition.code] = {
                "disposition": "required",
                "completion": "complete",
                "responsible_role": "System Architect",
                "basis_references": [requirement_item],
                "reason": "The external project has an observable multi-module build boundary",
                "design_result_markdown": (
                    "## 设计结果 Design Result\n\n"
                    "### System Boundary\n\n"
                    "| System | Responsibility | Modules |\n|---|---|---|\n"
                    f"| {root.name} | Spring-oriented library and integration boundary | {module_text} |"
                ),
                "constraints_impacts": [],
                "vfy_points": [{
                    "id": "VFP-210-001",
                    "references": [requirement_item],
                    "verification_object": "system and module boundary",
                    "observable_result": "declared modules remain addressable from the root build",
                    "expected_evidence": "root and child build descriptors",
                }],
                "evidence_references": [],
            }
        elif definition.code == "DOM-220":
            domains[definition.code] = {
                "disposition": "required",
                "completion": "complete",
                "responsible_role": "Module Architect",
                "basis_references": [requirement_item],
                "reason": "The project exposes stable module responsibilities",
                "design_result_markdown": (
                    "## 设计结果 Design Result\n\n"
                    "### Components and Modules\n\n"
                    "| Module | Responsibility | Change |\n|---|---|---|\n"
                    + "\n".join(
                        f"| {name} | Preserve the existing module boundary | reused |"
                        for name in modules
                    )
                ),
                "constraints_impacts": [],
                "vfy_points": [{
                    "id": "VFP-220-001",
                    "references": [requirement_item],
                    "verification_object": "module catalog",
                    "observable_result": "every detected Maven module is represented once",
                    "expected_evidence": "module pom.xml files",
                }],
                "evidence_references": [],
            }
        elif definition.code == "DOM-510":
            domains[definition.code] = {
                "disposition": "required",
                "completion": "complete",
                "responsible_role": "Verification Architect",
                "basis_references": [acceptance_item],
                "reason": "Every DSN requires a VFY strategy",
                "design_result_markdown": (
                    "## 设计结果 Design Result\n\n"
                    "### VFY 目标 VFY Objectives\n\n"
                    "| ID | Source References | Objective | Observable Result |\n|---|---|---|---|\n"
                    f"| OBJ-001 | {acceptance_item} | 验证项目设计边界 | DSN Artifact Set 与模块事实一致 |\n\n"
                    "### 方法选择 VFY Methods\n\n"
                    "| Objective | Method | Rationale |\n|---|---|---|\n"
                    "| OBJ-001 | inspection | 设计期不执行产品发布 |\n\n"
                    "### 通过条件 Pass Criteria\n\n"
                    "| Objective | Pass Criteria |\n|---|---|\n"
                    "| OBJ-001 | 全部必需 Member、摘要和生命周期 Projection 一致 |\n\n"
                    "### Evidence Contract\n\n"
                    "| Objective | Evidence |\n|---|---|\n"
                    "| OBJ-001 | 项目文件摘要、DSN Manifest 和 Query Projection |"
                ),
                "constraints_impacts": [],
                "vfy_points": [],
                "evidence_references": [],
            }
        else:
            domains[definition.code] = {
                "disposition": "n/a",
                "completion": "not_applicable",
                "basis_references": [requirement_item],
                "reason": "The integration probe introduces no obligation in this domain",
            }

    composite = [
        {
            "domain_code": code,
            "subdomain": name,
            "disposition": "n/a",
            "basis_references": [requirement_item],
            "reason": "The integration probe introduces no obligation",
            "exception_references": [],
        }
        for code, name in COMPOSITE_SUBDOMAINS
    ]
    pom = root / "pom.xml"
    supporting = []
    if pom.is_file():
        supporting.append(
            {
                "member_id": "SUP-001",
                "canonical_name": "baseline/pom.xml",
                "media_type": "application/xml",
                "encoding": "base64",
                "content": base64.b64encode(pom.read_bytes()).decode("ascii"),
            }
        )
    return {
        "title": f"{root.name} 工程边界设计",
        "summary": "依据外部项目的真实构建文件验证 DSN 复合 Artifact Set。",
        "boundary": f"{root.name} 根构建与模块边界",
        "profile": "full",
        "change_type": "reuse",
        "baseline_references": ["git:HEAD"],
        "target_state_summary": "保持现有模块边界并形成可验证设计记录",
        "impact_summary": "仅写入临时 ArtifactStore，不修改工程源码",
        "changes": [{
            "id": "CHG-001",
            "object_or_boundary": f"resource:{root.name}",
            "change": "reuse",
            "baseline_references": ["git:HEAD"],
            "baseline_state": module_text,
            "target_state": "现有模块边界被准确记录并可验证",
            "affected_domains": ["DOM-210", "DOM-220", "DOM-510"],
        }],
        "traceability": [{
            "source_references": [requirement_item, acceptance_item],
            "design_references": ["DOM-210", "DOM-220", "DOM-510"],
            "decision_references": [],
            "vfy_references": ["OBJ-001"],
            "na_reason": "N/A",
        }],
        "decisions": [],
        "decision_none_reason": "Existing build descriptors determine the reused module boundary",
        "domains": domains,
        "composite_subdomains": composite,
        "cross_domain_conflicts": [],
        "scope_expansion": False,
        "simplicity_rationale": "Reuse the existing Maven boundaries without introducing new architecture",
        "lifecycle_applicability": [
            {"phase": "PLN", "disposition": "required", "host": "N/A", "basis": "Further delivery requires a plan"},
            {"phase": "IMP", "disposition": "required", "host": "N/A", "basis": "Implementation follows planning"},
            {"phase": "VFY", "disposition": "required", "host": "N/A", "basis": "VFY is the mandatory control point"},
            {"phase": "RLS", "disposition": "n/a", "host": "N/A", "basis": "External integration stops after design"},
        ],
        "evidence": [{
            "id": "EVD-001",
            "type": "repository",
            "supports_references": [requirement_item, "DOM-210", "DOM-220"],
            "source": "external project checkout",
            "reference": "git:HEAD",
            "digest": "N/A",
            "produced_at": "2026-09-01T10:00:00Z",
            "sensitivity": "public",
        }],
        "supporting_members": supporting,
        "open_items": [],
        "exceptions": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-label", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    if not (root / ".git").is_dir():
        raise SystemExit("external project must be a Git checkout")

    before_status = _git(root, "status", "--porcelain")
    before_snapshot = _snapshot(root)
    runtime_dir = root / ".sdlc"
    if runtime_dir.exists():
        raise SystemExit("external project already contains .sdlc")

    try:
        store = ArtifactStore.open_read_write(root, clock=lambda: FIXED)
        store.initialize()
        context, requirement = _create_upstream(store)
        authority_dir = runtime_dir / "authority"
        authority_dir.mkdir(exist_ok=True)
        authority = authority_dir / "dsn-approval.md"
        authority.write_text(
            f"Approved external integration design for {args.project_label}\n",
            encoding="utf-8",
        )
        authority_reference = (
            authority.relative_to(root).as_posix()
            + "@"
            + sha256_bytes(authority.read_bytes())
        )
        design = _design(root, requirement)
        normalized = DsnAnalyzer().analyze(
            design,
            __import__("dsn_common").UpstreamScope(
                context_reference=context,
                scope_references=(requirement,),
                control_references=(),
                requirement_items=(requirement + "#R-001",),
                acceptance_items=(requirement + "#AC-001",),
            ),
        ).normalized
        confirmation = {
            "mode": "human",
            "confirmer": "external-integration-authority",
            "role": "Design Authority",
            "authority_reference": authority_reference,
            "confirmed_at": "2026-09-01T10:00:00Z",
            "subject_digest": _subject_digest(
                normalized,
                context,
                (requirement,),
                (),
            ),
        }
        invocation = {
            "contract": "sdlc-ai-spec/runtime-invocation/v1",
            "operation": "create",
            "project_root": str(root),
            "artifact_reference": None,
            "inputs": {
                "scope_inputs": [requirement],
                "control_inputs": [],
                "design": design,
                "final_confirmation": confirmation,
            },
            "confirmations": [],
            "options": {"dry_run": False, "write_policy": "auto"},
        }
        result = execute_phase(
            DsnHandler(
                root,
                clock=lambda: FIXED,
                upstream_verifier_factory=lambda _: PassingVerifier(),
            ),
            invocation,
        )
        if not result.get("ok") or result["artifact"]["revision_state"] != "frozen":
            raise RuntimeError("external DSN create did not freeze: " + json.dumps(result, ensure_ascii=False))
        stored = store.read_revision(result["artifact"]["id"], 1)
        if tuple(item.member_id for item in stored.payload.members) != (
            "DOM-210", "DOM-220", "DOM-510", "SUP-001"
        ):
            raise RuntimeError("external DSN member closure is unexpected")
        projection = LifecycleQueryService(
            root,
            plugin_root=ROOT,
            verifier_factory=lambda _: PassingVerifier(),
        ).inspect_requirement(requirement)
        if projection.frontier != (result["artifact"]["reference"],):
            raise RuntimeError("external lifecycle frontier is not the DSN")
        if not projection.next_actions or projection.next_actions[0].phase != "PLN":
            raise RuntimeError("external lifecycle did not route DSN to PLN")
        output = {
            "contract": "sdlc-ai-spec/external-dsn-integration/v1",
            "ok": True,
            "project": args.project_label,
            "project_commit": _git(root, "rev-parse", "HEAD"),
            "modules": _modules(root),
            "context_reference": context,
            "requirement_reference": requirement,
            "design_reference": result["artifact"]["reference"],
            "design_members": [item.member_id for item in stored.payload.members],
            "lifecycle_state": projection.overall_state,
            "lifecycle_frontier": list(projection.frontier),
            "next_phase": projection.next_actions[0].phase,
            "source_snapshot_unchanged": before_snapshot == _snapshot(root),
        }
        if not output["source_snapshot_unchanged"]:
            raise RuntimeError("external project source files changed during integration")
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    finally:
        shutil.rmtree(runtime_dir, ignore_errors=True)

    after_status = _git(root, "status", "--porcelain")
    after_snapshot = _snapshot(root)
    if before_status != after_status or before_snapshot != after_snapshot:
        raise SystemExit("external project was not restored to its original Git state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
