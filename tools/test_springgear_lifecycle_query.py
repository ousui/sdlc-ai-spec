#!/usr/bin/env python3
"""End-to-end CTX -> REQ -> lifecycle-query test on a SpringGear snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "packages"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from packages.sdlc_lifecycle import LifecycleQueryService  # noqa: E402

FIXED = datetime(2026, 8, 31, 19, 0, tzinfo=timezone.utc)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CTX = load_module(
    "springgear_ctx_runtime",
    ROOT / "skills/sdlc-000-ctx/scripts/runtime.py",
)
REQ = load_module(
    "springgear_req_runtime",
    ROOT / "skills/sdlc-100-req/scripts/runtime_final.py",
)


def sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def evidence_row(
    item_id: str,
    kind: str,
    supports: list[str],
    producer: str,
    reference: str,
    digest: str,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": kind,
        "supports_references": supports,
        "source_or_producer": producer,
        "reference": reference,
        "integrity_or_digest": digest,
        "produced_at": "2026-08-31T19:00:00Z",
        "sensitivity_or_access": "public",
    }


def fact(value: str, basis: str, *references: str) -> dict[str, Any]:
    return {
        "value": value,
        "basis": basis,
        "basis_references": list(references),
    }


def none_section() -> dict[str, Any]:
    return {
        "none": {
            "basis": "confirmed",
            "basis_references": ["EVD-001"],
        }
    }


def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        result[relative] = sha256(path.read_bytes())
    return result


def source_commit(source: Path) -> str:
    process = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return process.stdout.strip() if process.returncode == 0 else "snapshot-without-git"


def prepare_project(source: Path, destination: Path) -> str:
    commit = source_commit(source)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".git", ".sdlc", "target", "__pycache__"),
    )
    return commit


def create_context(project: Path, commit: str) -> str:
    authority_dir = project / "target/sdlc-integration"
    authority_dir.mkdir(parents=True, exist_ok=True)
    boundary = (
        "SpringGear 当前仓库内的 Maven 多模块 Java/Spring Framework 源码、"
        "文档、构建定义和测试资产；不包含外部依赖仓库、部署实例或其他产品仓库。"
    )
    boundary_file = authority_dir / "project-boundary.txt"
    boundary_file.write_text(boundary + "\n", encoding="utf-8")
    boundary_ref = (
        boundary_file.relative_to(project).as_posix()
        + "@"
        + sha256(boundary_file.read_bytes())
    )

    readme = project / "README.md"
    pom = project / "pom.xml"
    readme_ref = "README.md@" + sha256(readme.read_bytes())
    pom_ref = "pom.xml@" + sha256(pom.read_bytes())
    baseline = f"vcs:github.com/ousui/springgear@{commit}"

    context = {
        "summary": "SpringGear 是基于 Spring Framework 的辅助型多模块 Java 框架。",
        "project_identity": {
            "project_name": fact("SpringGear Framework", "observed", "EVD-002"),
            "purpose": fact(
                "为 Spring 开发提供高效、可控、流程清晰的扩展框架，减少重复劳动。",
                "observed",
                "EVD-002",
            ),
            "boundary": fact(boundary, "confirmed", "EVD-001"),
            "primary_resource_reference": fact(
                "RSC-001", "observed", "EVD-002", "EVD-003"
            ),
            "authoritative_references": fact(
                "README.md, pom.xml", "referenced", "EVD-002", "EVD-003"
            ),
        },
        "resources": [
            {
                "id": "RSC-001",
                "type": "repository",
                "name": "ousui/springgear",
                "role": "primary",
                "locator": baseline,
                "baseline_reference": baseline,
                "basis": "observed",
                "basis_references": ["EVD-002", "EVD-003"],
            }
        ],
        "technologies": [
            {
                "id": "TEC-001",
                "category": "language",
                "name": "Java",
                "version_or_constraint": "Maven compiler configuration",
                "purpose": "Framework implementation",
                "basis": "observed",
                "basis_references": ["EVD-003"],
            },
            {
                "id": "TEC-002",
                "category": "framework",
                "name": "Spring Framework",
                "version_or_constraint": "5.x baseline described by the project",
                "purpose": "IOC, AOP and framework integration",
                "basis": "observed",
                "basis_references": ["EVD-002", "EVD-003"],
            },
            {
                "id": "TEC-003",
                "category": "build",
                "name": "Apache Maven",
                "version_or_constraint": "multi-module pom.xml",
                "purpose": "Build and dependency management",
                "basis": "observed",
                "basis_references": ["EVD-003"],
            },
        ],
        "engineering_entries": [
            {
                "id": "ENG-001",
                "purpose": "build",
                "command_or_entry_point": "mvn -q -DskipTests package",
                "working_scope": "Project Root",
                "preconditions": "JDK and Maven available",
                "basis": "observed",
                "basis_references": ["EVD-003"],
            },
            {
                "id": "ENG-002",
                "purpose": "test",
                "command_or_entry_point": "mvn test",
                "working_scope": "Project Root",
                "preconditions": "JDK and Maven available",
                "basis": "observed",
                "basis_references": ["EVD-003"],
            },
        ],
        "components": [
            {
                "id": "CMP-001",
                "name": "springgear-core",
                "type": "module",
                "resource_reference": "RSC-001",
                "responsibility": "Core workflow, context and engine implementation",
                "entry_point": "springgear-core/src/main/java/org/springgear",
                "depends_on": "None",
                "authority_reference": readme_ref,
                "basis": "observed",
                "basis_references": ["EVD-002", "EVD-003"],
            },
            {
                "id": "CMP-002",
                "name": "springgear-bom",
                "type": "module",
                "resource_reference": "RSC-001",
                "responsibility": "Dependency version bill of materials",
                "entry_point": "springgear-bom/pom.xml",
                "depends_on": "None",
                "authority_reference": pom_ref,
                "basis": "observed",
                "basis_references": ["EVD-002", "EVD-003"],
            },
        ],
        "rules": none_section(),
        "environments": none_section(),
        "constraints": none_section(),
        "exceptions": [],
    }
    evidence = [
        evidence_row(
            "EVD-001",
            "confirmation",
            ["CTX-G-002", "CTX-G-004"],
            "springgear repository owner",
            boundary_ref,
            sha256(boundary_file.read_bytes()),
        ),
        evidence_row(
            "EVD-002",
            "observation",
            ["CTX-G-002", "CTX-G-003", "CTX-G-004"],
            "README.md",
            readme_ref,
            sha256(readme.read_bytes()),
        ),
        evidence_row(
            "EVD-003",
            "observation",
            ["CTX-G-003", "CTX-G-004"],
            "pom.xml",
            pom_ref,
            sha256(pom.read_bytes()),
        ),
    ]
    create = {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create",
        "project_root": str(project),
        "artifact_reference": None,
        "inputs": {
            "context": context,
            "evidence": evidence,
            "supporting_members": [],
        },
        "confirmations": [
            {"type": "write", "approved": True},
            {
                "type": "project_boundary",
                "value": boundary,
                "authority_reference": "EVD-001",
            },
        ],
        "options": {"dry_run": False},
    }
    created = CTX.invoke(create, clock=lambda: FIXED)
    if created.get("artifact") is None:
        raise AssertionError(f"CTX create failed: {created}")
    reference = f"{created['artifact']['id']}@{created['artifact']['revision']}"
    refresh = {
        "base_revision": None,
        "observed_at": "2026-08-31T19:00:00Z",
        "observation_baseline": baseline,
        "refresh_reason": "complete SpringGear integration baseline",
        "effective_change_references": "None",
        "evidence_references": ["EVD-001", "EVD-002", "EVD-003"],
    }
    preview = {
        **create,
        "operation": "revise",
        "artifact_reference": reference,
        "inputs": {**create["inputs"], "refresh": refresh},
        "options": {"dry_run": True},
        "confirmations": [],
    }
    preview_result = CTX.invoke(preview, clock=lambda: FIXED)
    bindings = next(
        item["details"]
        for item in preview_result["warnings"]
        if item["code"] == "FINAL_CONFIRMATION_BINDINGS"
    )
    final_file = authority_dir / "ctx-final-confirmation.txt"
    final_file.write_text(
        "\n".join(
            [
                f"artifact: {reference}",
                f"control: {bindings['control_input_digest']}",
                f"contracts: {bindings['evaluation_contract_set']}",
                f"checks: {bindings['check_set_result_digest']}",
                "decision: approved",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    final_ref = (
        final_file.relative_to(project).as_posix()
        + "@"
        + sha256(final_file.read_bytes())
    )
    revise = {
        **preview,
        "options": {"dry_run": False},
        "confirmations": [
            {"type": "write", "approved": True},
            {
                "type": "final_confirmation",
                "result": "approved",
                "mode": "human",
                "confirmer": "springgear-owner",
                "role": "Project Maintainer",
                "authority_reference": final_ref,
                "accepted_exception_references": [],
                "confirmed_at": "2026-08-31T19:00:00Z",
                **bindings,
            },
        ],
    }
    completed = CTX.invoke(revise, clock=lambda: FIXED)
    if not completed.get("ok"):
        raise AssertionError(f"CTX finalization failed: {completed}")
    return completed["artifact"]["reference"]


def create_requirement(project: Path, context_reference: str) -> str:
    authority_dir = project / "target/sdlc-integration"
    authority_file = authority_dir / "req-final-confirmation.txt"
    authority_file.write_text(
        "Approved SpringGear requirement fixture by repository owner\n",
        encoding="utf-8",
    )
    authority_ref = (
        authority_file.relative_to(project).as_posix()
        + "@"
        + sha256(authority_file.read_bytes())
    )
    requirement = {
        "title": "提供 SpringGear 生命周期状态查询",
        "summary": "允许维护者只读查看当前需求所处阶段、阻塞项和下一动作。",
        "sources": [
            {
                "type": "document",
                "content": "README.md",
                "evidence_reference": "README.md@" + sha256((project / "README.md").read_bytes()),
            }
        ],
        "goals": [
            {
                "problem": "当前无法从本地 ArtifactStore 直接了解需求流转状态。",
                "outcome": "维护者可以查询准确 REQ Revision 的生命周期图和下一动作。",
                "success_condition": "状态查询严格只读并正确返回 CTX→REQ 前沿。",
            }
        ],
        "in_scope": ["Lifecycle Query Graph", "Read-only status projection"],
        "out_of_scope": ["自动执行下一阶段", "修改 SpringGear 产品代码"],
        "affected_parties": [
            {
                "party": "SpringGear maintainer",
                "impact": "减少手工检查 Artifact 的成本",
            }
        ],
        "requirements": [
            {
                "type": "behavior",
                "source_references": ["SRC-001", "GOAL-001"],
                "statement": "系统应只读展示准确需求 Revision 的当前阶段、阻塞项和下一动作。",
            },
            {
                "type": "constraint",
                "source_references": ["GOAL-001"],
                "statement": "状态查询不得初始化或修改 ArtifactStore。",
            },
        ],
        "acceptance_criteria": [
            {
                "requirement_references": ["R-001"],
                "condition": "项目存在一个 frozen ready REQ",
                "expected_result": "查询返回 CTX→REQ 图、REQ 前沿和 DSN 下一阶段",
            },
            {
                "requirement_references": ["R-002"],
                "condition": "查询前后比较项目文件摘要",
                "expected_result": "项目文件无任何变化",
            },
        ],
        "dependencies": [],
        "profile": "full",
        "profile_basis": "跨阶段状态能力需要设计和验证",
        "lifecycle_applicability": [
            {
                "phase": "DSN",
                "disposition": "required",
                "host": "N/A",
                "basis": "需要定义生命周期图和状态推导",
            },
            {
                "phase": "PLN",
                "disposition": "required",
                "host": "N/A",
                "basis": "需要实施计划",
            },
            {
                "phase": "IMP",
                "disposition": "required",
                "host": "N/A",
                "basis": "需要实现共享查询包和 Skill",
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
                "basis": "本集成 Fixture 不执行发布",
            },
        ],
        "open_items": [],
        "evidence": [],
        "supporting_members": [],
        "exceptions": [],
    }
    handler = REQ.RequirementHandler(project, clock=lambda: FIXED)
    request = {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create",
        "project_root": str(project),
        "artifact_reference": None,
        "inputs": {
            "context_reference": context_reference,
            "requirement": requirement,
            "control_inputs": [],
            "final_confirmation": {
                "mode": "human",
                "confirmer": "springgear-owner",
                "role": "Product Owner",
                "authority_reference": authority_ref,
                "confirmed_at": "2026-08-31T19:00:00Z",
            },
        },
        "confirmations": [
            {"type": "artifact_store_write", "approved": True}
        ],
        "options": {"dry_run": False},
    }
    result = REQ.execute_phase(handler, request)
    if not result.get("ok"):
        raise AssertionError(f"REQ create failed: {result}")
    return result["artifact"]["reference"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    if not source.is_dir():
        raise SystemExit("SpringGear source directory does not exist")

    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "springgear"
        commit = prepare_project(source, project)
        context_reference = create_context(project, commit)
        requirement_reference = create_requirement(project, context_reference)
        before = snapshot(project)

        service = LifecycleQueryService(project, plugin_root=ROOT)
        overview = service.project_overview()
        candidates = service.list_requirements()
        projection = service.inspect_requirement(requirement_reference)

        after = snapshot(project)
        if before != after:
            raise AssertionError("Lifecycle query changed the SpringGear project")
        if overview.state != "single_requirement":
            raise AssertionError(overview.to_dict())
        if overview.selected_requirement != requirement_reference:
            raise AssertionError(overview.to_dict())
        if len(candidates) != 1 or candidates[0].reference != requirement_reference:
            raise AssertionError([item.to_dict() for item in candidates])
        if projection.overall_state != "ready_for_next_phase":
            raise AssertionError(projection.to_dict())
        if {item.artifact_type for item in projection.nodes} != {"CTX", "REQ"}:
            raise AssertionError(projection.to_dict())
        if not any(item.relation == "context" for item in projection.edges):
            raise AssertionError(projection.to_dict())
        if projection.next_actions[0].phase != "DSN":
            raise AssertionError(projection.to_dict())
        if projection.next_actions[0].skill_available:
            raise AssertionError("DSN must remain unavailable in this baseline")

        print("springgear lifecycle query: PASS")
        print("source commit:", commit)
        print("context:", context_reference)
        print("requirement:", requirement_reference)
        print("projection:", projection.overall_state)
        print("project mutation after query: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
