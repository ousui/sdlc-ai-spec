#!/usr/bin/env python3
"""Deterministic create/revise/check runtime for sdlc-100-req."""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
for candidate in (PLUGIN_ROOT, PLUGIN_ROOT / "packages"):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from packages.sdlc_artifact_store import (  # noqa: E402
    ArtifactStore,
    ArtifactStoreError,
    CanonicalManifest,
    CanonicalMember,
    CanonicalRevisionPayload,
    ConflictError,
    DomainVerification,
    InvalidStateError,
    ManifestMember,
    NotFoundError,
    ReferenceError,
    StoreNotFoundError,
    compute_sha256,
)
from packages.sdlc_runtime import (  # noqa: E402
    ControlInputError,
    ControlInputResolver,
    FrozenArtifactAuthorityVerifier,
    authority_reference,
    compute_check_set_result_digest,
    compute_control_input_digest,
    error_result,
    exact_artifact_reference,
    execute_phase,
    parse_canonical_artifact,
    parse_front_matter,
    parse_reference_set,
    sha256_bytes,
)
from packages.sdlc_runtime.canonical import (  # noqa: E402
    CHECK_HEADERS,
    FINAL_CONFIRMATION_HEADERS,
    GATE_SUMMARY_HEADERS,
    CanonicalFormatError,
    find_tables,
    require_single_row,
    require_single_table,
)

REQ_CONTRACT = "sdlc-ai-spec/artifact/v1"
REQ_PHASE = "REQ"
ARTIFACT_TYPE = "REQ"
PROFILE_VALUES = frozenset({"full", "lite", "hotfix"})
REQ_TYPES = frozenset({"behavior", "rule", "quality", "constraint"})
SOURCE_TYPES = frozenset(
    {"text", "document", "conversation", "incident", "artifact", "other"}
)
DISPOSITIONS = frozenset({"required", "embedded", "n/a", "waived", "pending"})
LIFECYCLE_PHASES = ("DSN", "PLN", "IMP", "VFY", "RLS")
EXCEPTION_STATES = frozenset({"active", "carried", "resolved", "superseded"})
IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@%+#-]*$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

SOURCE_HEADERS = (
    "ID",
    "Type",
    "Content or Immutable Reference",
    "Evidence Reference",
)
GOAL_HEADERS = (
    "ID",
    "当前问题 Current Problem",
    "目标结果与预期用途 Goal, Intended Outcome and Use",
    "成功条件 Success Condition",
)
AFFECTED_HEADERS = ("ID", "对象 Affected Party", "Stakeholder Need or Impact")
REQUIREMENT_HEADERS = (
    "ID",
    "类型 Type",
    "来源或父项引用 Source or Parent References",
    "需求描述 Requirement Statement",
)
AC_HEADERS = (
    "ID",
    "关联需求 Requirement References",
    "条件 Condition",
    "预期结果 Expected Result",
)
DEPENDENCY_HEADERS = (
    "ID",
    "依赖项 Dependency",
    "要求状态 Required State",
    "当前状态 Current State",
    "状态检查引用 State Check Reference",
)
PROFILE_HEADERS = ("Selected Profile", "Basis")
OPEN_ITEM_HEADERS = (
    "ID",
    "所需输入或待确认决策 Needed Input or Decision",
    "预期来源 Expected Source",
    "被阻塞项 Blocked References",
    "状态 State",
    "解决结果或证据 Resolution or Evidence",
)
EVIDENCE_HEADERS = (
    "ID",
    "Type",
    "Supports References",
    "Source or Producer",
    "Reference",
    "Integrity or Digest",
    "Produced At",
    "Sensitivity or Access",
    "Empty Reason",
)
MANIFEST_HEADERS = (
    "Member ID",
    "Type",
    "Path or Reference",
    "Media Type",
    "Purpose",
    "SHA-256 Digest",
    "Empty Reason",
)
EXCEPTION_HEADERS = (
    "ID",
    "State",
    "Origin Exception Reference",
    "作用域或被跳过义务 Scope or Skipped Obligation",
    "原因 Reason",
    "已知风险 Known Risk",
    "补偿措施 Compensating Control",
    "批准记录 Approver, Role and Time",
    "复查条件 Revisit Condition",
    "下游限制 Downstream Obligation",
    "解决或替代引用 Resolution or Superseding References",
)
APPLICABILITY_HEADERS = ("Phase", "Disposition", "Host", "判断依据 Basis")

CORE_CHECKS = (
    "CORE-G-001",
    "CORE-G-002",
    "CORE-G-003",
    "CORE-G-004",
    "CORE-G-005",
    "CORE-G-006",
    "CORE-G-007",
    "CORE-G-008",
    "CORE-G-009",
)
REQ_CHECKS = tuple(f"REQ-G-{number:03d}" for number in range(1, 9))

SPEC_HASHES = {
    "core-spec.md": "1eefa7a138f2d221140137a5fac0f5429b7f847273fe9d70e891ace6c3b7a89b",
    "artifact-store-spec.md": "b340ca2a38dfe0f7409acaa8f9ac559e8872bed44725037889528e3d167d4764",
    "100-req-spec.md": "13907cab3f1a9a5575d0d292901dc532f2a1c15f5b345f4fa8b7e20b137ed3f0",
}


class RequirementRuntimeError(ValueError):
    code = "REQ_RUNTIME_ERROR"


@dataclass(frozen=True)
class CheckOutcome:
    result: str
    note: str


@dataclass(frozen=True)
class RequirementAnalysis:
    checks: Mapping[str, CheckOutcome]
    open_items: tuple[Mapping[str, str], ...]
    active_exceptions: tuple[str, ...]
    normalized: Mapping[str, Any]


@dataclass(frozen=True)
class BuildResult:
    raw_bytes: bytes
    status: str
    gate_result: str
    failed_checks: tuple[str, ...]
    open_items: tuple[Mapping[str, str], ...]
    active_exceptions: tuple[str, ...]
    final_confirmation_valid: bool
    members: tuple[CanonicalMember, ...]
    manifest: CanonicalManifest


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime | None = None) -> str:
    value = moment or _now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(item) for item in value)
    return str(value).replace("|", "&#124;").replace("\r", " ").replace("\n", "<br>").strip()


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RequirementRuntimeError(f"{name} must be a non-empty string")
    return value.strip()


def _list(value: Any, name: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RequirementRuntimeError(f"{name} must be an array")
    return value


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RequirementRuntimeError(f"{name} must be an object")
    return value


def _reference_text(values: Sequence[str]) -> str:
    return "None" if not values else ", ".join(values)


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        if len(row) != len(headers):
            raise RequirementRuntimeError("table row width does not match headers")
        output.append("| " + " | ".join(_cell(value) for value in row) + " |")
    return "\n".join(output)


def _evaluation_contract_set() -> str:
    root = "docs/" + "v1.1/"
    return ", ".join(
        f"{root}{name}@sha256:{digest}" for name, digest in SPEC_HASHES.items()
    )


def _exact_base_reference(reference: str, phase: str = "REQ") -> tuple[str, int]:
    artifact_id, revision = exact_artifact_reference(reference)
    if "#" in reference or "/" in reference:
        raise RequirementRuntimeError("operation requires a base Artifact Reference")
    if not artifact_id.startswith(phase + "-"):
        raise RequirementRuntimeError(f"Reference must target a {phase} Artifact")
    return artifact_id, revision


def _write_authorized(confirmations: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        item.get("type") == "artifact_store_write" and item.get("approved") is True
        for item in confirmations
    )


def _decode_member(item: Mapping[str, Any], index: int) -> CanonicalMember:
    member_id = item.get("member_id") or f"SUP-{index:03d}"
    if not re.fullmatch(r"SUP-[0-9]{3}", str(member_id)):
        raise RequirementRuntimeError(f"invalid Supporting Member ID: {member_id}")
    name = _required_text(item.get("canonical_name"), "canonical_name")
    media_type = _required_text(item.get("media_type"), "media_type")
    encoding = item.get("encoding", "utf-8")
    content = item.get("content", "")
    if not isinstance(content, str):
        raise RequirementRuntimeError("supporting member content must be a string")
    if encoding == "utf-8":
        raw = content.encode("utf-8")
    elif encoding == "base64":
        try:
            raw = base64.b64decode(content, validate=True)
        except ValueError as exc:
            raise RequirementRuntimeError("invalid base64 supporting member") from exc
    else:
        raise RequirementRuntimeError("supporting member encoding must be utf-8 or base64")
    return CanonicalMember(
        member_id=str(member_id),
        canonical_name=name,
        media_type=media_type,
        raw_bytes=raw,
        sha256=compute_sha256(raw),
    )


def _manifest(members: Sequence[CanonicalMember]) -> CanonicalManifest:
    projections = tuple(
        ManifestMember(
            member_id=item.member_id,
            canonical_name=item.canonical_name,
            media_type=item.media_type,
            sha256=item.sha256,
        )
        for item in sorted(members, key=lambda value: value.member_id)
    )
    raw = json.dumps(
        {
            "local_members": [
                {
                    "member_id": item.member_id,
                    "canonical_name": item.canonical_name,
                    "media_type": item.media_type,
                    "sha256": item.sha256,
                }
                for item in projections
            ]
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return CanonicalManifest(
        raw_bytes=raw,
        media_type="application/json",
        local_members=projections,
    )


def _identity(value: Any, name: str) -> str:
    text = _required_text(value, name)
    if not IDENTITY_RE.fullmatch(text):
        raise RequirementRuntimeError(f"{name} is not a stable identity token")
    return text


def _validate_rfc3339(value: Any, name: str) -> str:
    text = _required_text(value, name)
    if not RFC3339_RE.fullmatch(text):
        raise RequirementRuntimeError(f"{name} must use RFC 3339")
    return text


def _authority_file(project_root: Path, reference: str) -> bytes:
    relative, digest = authority_reference(reference)
    target = (project_root / relative).resolve()
    try:
        target.relative_to(project_root)
    except ValueError as exc:
        raise RequirementRuntimeError("Authority Reference escapes project root") from exc
    if not target.is_file():
        raise RequirementRuntimeError("Authority Reference file does not exist")
    raw = target.read_bytes()
    if sha256_bytes(raw) != digest:
        raise RequirementRuntimeError("Authority Reference digest does not match")
    return raw


def _subject_digest(requirement: Mapping[str, Any], context: str, controls: Sequence[str]) -> str:
    raw = json.dumps(
        {
            "context_reference": context,
            "control_inputs": list(controls),
            "requirement": requirement,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(raw)


class RequirementAnalyzer:
    def analyze(self, requirement: Mapping[str, Any]) -> RequirementAnalysis:
        normalized: dict[str, Any] = {}
        checks: dict[str, CheckOutcome] = {}
        open_items: list[dict[str, str]] = []

        title = requirement.get("title")
        summary = requirement.get("summary")
        if not isinstance(title, str) or not title.strip():
            open_items.append(self._open("需要需求标题", "Maintainer", "REQ-G-002"))
            title = "Pending Requirement Title"
        if not isinstance(summary, str) or not summary.strip():
            open_items.append(self._open("需要需求摘要", "Maintainer", "REQ-G-002"))
            summary = "Pending — summary input required"
        normalized["title"] = str(title).strip()
        normalized["summary"] = str(summary).strip()

        sources = self._rows(requirement.get("sources"), "sources")
        goals = self._rows(requirement.get("goals"), "goals")
        in_scope = [str(item).strip() for item in _list(requirement.get("in_scope"), "in_scope") if str(item).strip()]
        out_scope = [str(item).strip() for item in _list(requirement.get("out_of_scope"), "out_of_scope") if str(item).strip()]
        affected = self._rows(requirement.get("affected_parties"), "affected_parties")
        requirements = self._rows(requirement.get("requirements"), "requirements")
        criteria = self._rows(requirement.get("acceptance_criteria"), "acceptance_criteria")
        dependencies = self._rows(requirement.get("dependencies"), "dependencies")
        applicability = self._rows(requirement.get("lifecycle_applicability"), "lifecycle_applicability")
        evidence = self._rows(requirement.get("evidence"), "evidence")
        exceptions = self._rows(requirement.get("exceptions"), "exceptions")
        provided_open = self._rows(requirement.get("open_items"), "open_items")
        members = self._rows(requirement.get("supporting_members"), "supporting_members")

        if not sources:
            open_items.append(self._open("需要至少一个原始输入", "Requester", "REQ-G-001"))
            checks["REQ-G-001"] = CheckOutcome("pending", "Source Input 尚未提供")
        else:
            source_invalid = any(
                item.get("type") not in SOURCE_TYPES
                or not isinstance(item.get("content"), str)
                or not item.get("content", "").strip()
                for item in sources
            )
            checks["REQ-G-001"] = CheckOutcome(
                "fail" if source_invalid else "pass",
                "Source Input 类型或内容无效" if source_invalid else "原始输入已保留",
            )

        if not goals:
            open_items.append(self._open("需要目标和成功条件", "Product Authority", "REQ-G-002"))
            checks["REQ-G-002"] = CheckOutcome("pending", "Goal 尚未提供")
        else:
            invalid = any(
                not all(isinstance(item.get(field), str) and item.get(field, "").strip() for field in ("problem", "outcome", "success_condition"))
                for item in goals
            )
            checks["REQ-G-002"] = CheckOutcome(
                "fail" if invalid else "pass",
                "Goal 字段不完整" if invalid else "问题、目标与成功条件可判定",
            )

        if not in_scope or not out_scope:
            open_items.append(self._open("需要同时确认 In Scope 与 Out of Scope", "Product Authority", "REQ-G-003"))
            checks["REQ-G-003"] = CheckOutcome("pending", "Scope 尚未闭合")
        else:
            checks["REQ-G-003"] = CheckOutcome("pass", "Scope 与可选对象/依赖使用合法结构")

        if not requirements:
            open_items.append(self._open("需要至少一个 Requirement Item", "Product Authority", "REQ-G-004"))
            checks["REQ-G-004"] = CheckOutcome("pending", "Requirement 尚未提供")
            checks["REQ-G-005"] = CheckOutcome("pending", "来源图尚未形成")
        else:
            invalid_req = any(
                item.get("type") not in REQ_TYPES
                or not isinstance(item.get("statement"), str)
                or not item.get("statement", "").strip()
                for item in requirements
            )
            checks["REQ-G-004"] = CheckOutcome(
                "fail" if invalid_req else "pass",
                "Requirement 类型或描述无效" if invalid_req else "Requirement 原子且使用合法类型",
            )
            graph_ok, graph_note = self._validate_graph(sources, goals, affected, requirements)
            checks["REQ-G-005"] = CheckOutcome("pass" if graph_ok else "fail", graph_note)

        if not criteria:
            open_items.append(self._open("需要 Acceptance Criteria", "Product Authority", "REQ-G-006"))
            checks["REQ-G-006"] = CheckOutcome("pending", "Acceptance Criteria 尚未提供")
        else:
            ac_ok, ac_note = self._validate_criteria(requirements, criteria)
            checks["REQ-G-006"] = CheckOutcome("pass" if ac_ok else "fail", ac_note)

        profile = requirement.get("profile")
        if profile is None:
            open_items.append(self._open("需要确认 Lifecycle Profile", "Maintainer", "REQ-G-007"))
            profile = "full"
            checks["REQ-G-007"] = CheckOutcome("pending", "Profile 尚未确认")
        elif profile not in PROFILE_VALUES:
            checks["REQ-G-007"] = CheckOutcome("fail", "Profile 枚举无效")
        else:
            checks["REQ-G-007"] = CheckOutcome("pass", "Profile 与 Basis 可保存")
        normalized["profile"] = profile

        app_ok, app_pending, app_note = self._validate_applicability(applicability)
        if app_pending:
            open_items.append(self._open("需要确认 Lifecycle Applicability", "Maintainer", "REQ-G-008"))
        checks["REQ-G-008"] = CheckOutcome(
            "pending" if app_pending else ("pass" if app_ok else "fail"), app_note
        )

        for item in provided_open:
            needed = item.get("needed") or item.get("decision")
            if not isinstance(needed, str) or not needed.strip():
                raise RequirementRuntimeError("open item needed text is required")
            open_items.append(
                self._open(
                    needed.strip(),
                    str(item.get("expected_source") or "Maintainer"),
                    str(item.get("blocked_references") or "REQ-G-001"),
                    state=str(item.get("state") or "open"),
                    resolution=str(item.get("resolution") or "N/A"),
                )
            )

        normalized.update(
            {
                "sources": sources,
                "goals": goals,
                "in_scope": in_scope,
                "out_of_scope": out_scope,
                "affected_parties": affected,
                "requirements": requirements,
                "acceptance_criteria": criteria,
                "dependencies": dependencies,
                "lifecycle_applicability": applicability,
                "evidence": evidence,
                "exceptions": exceptions,
                "supporting_members": members,
            }
        )
        active_exceptions: list[str] = []
        for index, item in enumerate(exceptions, start=1):
            state = item.get("state")
            if state not in EXCEPTION_STATES:
                checks["CORE-G-007"] = CheckOutcome("fail", "Exception State 无效")
                break
            if state in {"active", "carried"}:
                active_exceptions.append(f"EX-{index:03d}")
        else:
            checks["CORE-G-007"] = CheckOutcome("pass", "Exception 记录结构有效")

        numbered = tuple(
            {
                "id": f"OPI-{index:03d}",
                **item,
            }
            for index, item in enumerate(open_items, start=1)
        )
        return RequirementAnalysis(
            checks=checks,
            open_items=numbered,
            active_exceptions=tuple(active_exceptions),
            normalized=normalized,
        )

    def _rows(self, value: Any, name: str) -> list[Mapping[str, Any]]:
        rows = _list(value, name)
        return [_mapping(item, f"{name} item") for item in rows]

    def _open(
        self,
        needed: str,
        source: str,
        blocked: str,
        *,
        state: str = "open",
        resolution: str = "N/A",
    ) -> dict[str, str]:
        if state not in {"open", "resolved"}:
            raise RequirementRuntimeError("Open Item state must be open or resolved")
        refs = sorted({item.strip() for item in blocked.split(",") if item.strip()})
        if not refs:
            raise RequirementRuntimeError("Open Item blocked references cannot be empty")
        return {
            "needed": needed,
            "expected_source": source,
            "blocked_references": ", ".join(refs),
            "state": state,
            "resolution": resolution,
        }

    def _validate_graph(self, sources, goals, affected, requirements) -> tuple[bool, str]:
        roots = {f"SRC-{index:03d}" for index in range(1, len(sources) + 1)}
        roots |= {f"GOAL-{index:03d}" for index in range(1, len(goals) + 1)}
        roots |= {f"AP-{index:03d}" for index in range(1, len(affected) + 1)}
        req_ids = {f"R-{index:03d}" for index in range(1, len(requirements) + 1)}
        graph: dict[str, tuple[str, ...]] = {}
        for index, item in enumerate(requirements, start=1):
            req_id = f"R-{index:03d}"
            refs = item.get("source_references", [])
            if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
                return False, f"{req_id} 缺少来源引用"
            values = tuple(ref.strip() for ref in refs if ref.strip())
            if not values or any(ref not in roots | req_ids for ref in values):
                return False, f"{req_id} 包含不存在的来源引用"
            graph[req_id] = values

        visiting: set[str] = set()
        visited: set[str] = set()

        def reaches_root(node: str) -> bool:
            if node in roots:
                return True
            if node in visiting:
                raise RequirementRuntimeError("Requirement 来源图存在循环")
            if node in visited:
                return True
            visiting.add(node)
            values = graph.get(node, ())
            result = bool(values) and all(reaches_root(value) for value in values)
            visiting.remove(node)
            if result:
                visited.add(node)
            return result

        try:
            if not all(reaches_root(node) for node in req_ids):
                return False, "Requirement 来源链未到达稳定根"
        except RequirementRuntimeError:
            return False, "Requirement 来源图存在循环"
        return True, "Requirement 来源图有根、无环且引用可解析"

    def _validate_criteria(self, requirements, criteria) -> tuple[bool, str]:
        req_ids = {f"R-{index:03d}" for index in range(1, len(requirements) + 1)}
        covered: set[str] = set()
        for index, item in enumerate(criteria, start=1):
            refs = item.get("requirement_references", [])
            if not isinstance(refs, list) or not refs:
                return False, f"AC-{index:03d} 缺少 Requirement Reference"
            if any(ref not in req_ids for ref in refs):
                return False, f"AC-{index:03d} 引用不存在的 Requirement"
            if not isinstance(item.get("condition"), str) or not item.get("condition", "").strip():
                return False, f"AC-{index:03d} Condition 为空"
            if not isinstance(item.get("expected_result"), str) or not item.get("expected_result", "").strip():
                return False, f"AC-{index:03d} Expected Result 为空"
            covered.update(refs)
        missing = sorted(req_ids - covered)
        if missing:
            return False, "Acceptance Criteria 未覆盖: " + ", ".join(missing)
        return True, "Acceptance Criteria 覆盖全部 Requirement"

    def _validate_applicability(self, rows) -> tuple[bool, bool, str]:
        if not rows:
            return False, True, "Lifecycle Applicability 尚未提供"
        phases = [item.get("phase") for item in rows]
        if tuple(phases) != LIFECYCLE_PHASES:
            return False, False, "Lifecycle Applicability 必须按固定 Phase 顺序完整登记"
        for item in rows:
            if item.get("disposition") not in DISPOSITIONS:
                return False, False, "Lifecycle Disposition 枚举无效"
            if not isinstance(item.get("basis"), str) or not item.get("basis", "").strip():
                return False, False, "Lifecycle Applicability Basis 为空"
        vfy = next(item for item in rows if item.get("phase") == "VFY")
        if vfy.get("disposition") != "required":
            return False, False, "VFY 必须为 required"
        if any(item.get("disposition") == "pending" for item in rows):
            return False, True, "Lifecycle Applicability 存在 pending"
        return True, False, "Lifecycle Applicability 完整"


class RequirementBuilder:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.analyzer = RequirementAnalyzer()

    def build(
        self,
        *,
        artifact_id: str,
        revision: int,
        context_reference: str,
        control_inputs: Sequence[str],
        requirement: Mapping[str, Any],
        final_confirmation: Mapping[str, Any] | None,
    ) -> BuildResult:
        analysis = self.analyzer.analyze(requirement)
        checks = dict(analysis.checks)
        checks.update(
            {
                "CORE-G-001": CheckOutcome("pass", "Artifact ID、Revision 与 Lineage 一致"),
                "CORE-G-002": CheckOutcome("pass", "CTX 与直接 Input 已按准确 frozen Reference 解析"),
                "CORE-G-003": CheckOutcome("pass", "固定模板与 Canonical Payload 可构造"),
                "CORE-G-004": CheckOutcome(checks["REQ-G-008"].result, "Disposition 与 Lifecycle Applicability 一致"),
                "CORE-G-005": CheckOutcome("pass", "Evidence 与 Supporting Member 使用固定索引"),
                "CORE-G-006": CheckOutcome(
                    "pending" if any(item["state"] == "open" for item in analysis.open_items) else "pass",
                    "存在未解决 Open Item" if analysis.open_items else "无未解决阻塞项",
                ),
                "CORE-G-008": CheckOutcome("pass", "Core 与 REQ Check Set 已完整登记"),
                "CORE-G-009": CheckOutcome("pending", "Final Confirmation 尚未完成"),
            }
        )
        for check_id in REQ_CHECKS:
            checks.setdefault(check_id, CheckOutcome("pass", "固定检查通过"))
        failed = sorted(check_id for check_id, item in checks.items() if item.result == "fail")
        pending = sorted(check_id for check_id, item in checks.items() if item.result == "pending")
        if failed:
            status = "failed"
            gate = "fail"
        elif any(item["state"] == "open" for item in analysis.open_items):
            status = "waiting_input"
            gate = "pending"
        else:
            status = "draft"
            gate = "pending"

        members = tuple(
            _decode_member(item, index)
            for index, item in enumerate(analysis.normalized["supporting_members"], start=1)
        )
        manifest = _manifest(members)
        raw = self._render(
            artifact_id=artifact_id,
            revision=revision,
            status=status,
            context_reference=context_reference,
            control_inputs=control_inputs,
            analysis=analysis,
            checks=checks,
            final_row=None,
            gate_row=None,
            members=members,
        )
        control_digest = compute_control_input_digest(raw)
        check_digest = compute_check_set_result_digest(parse_canonical_artifact(raw)) if not pending or failed else self._safe_check_digest(raw)

        final_valid = False
        if final_confirmation is not None and not failed and not pending:
            final_row = self._final_confirmation(
                artifact_id=artifact_id,
                revision=revision,
                context_reference=context_reference,
                control_inputs=control_inputs,
                requirement=requirement,
                final_confirmation=final_confirmation,
                control_digest=control_digest,
                check_digest=check_digest,
                active_exceptions=analysis.active_exceptions,
            )
            checks["CORE-G-009"] = CheckOutcome("pass", "Final Confirmation 绑定当前 Revision 与摘要")
            gate = "pass_with_exception" if analysis.active_exceptions else "pass"
            status = "ready_with_exception" if analysis.active_exceptions else "ready"
            gate_row = {
                "revision": str(revision),
                "control_digest": control_digest,
                "evaluation_set": _evaluation_contract_set(),
                "check_digest": check_digest,
                "gate_result": gate,
                "exceptions": _reference_text(
                    [f"{artifact_id}@{revision}#{item}" for item in analysis.active_exceptions]
                ),
                "evaluator": "sdlc-100-req-runtime",
                "evaluated_at": _iso(),
            }
            raw = self._render(
                artifact_id=artifact_id,
                revision=revision,
                status=status,
                context_reference=context_reference,
                control_inputs=control_inputs,
                analysis=analysis,
                checks=checks,
                final_row=final_row,
                gate_row=gate_row,
                members=members,
            )
            if compute_control_input_digest(raw) != control_digest:
                raise RequirementRuntimeError("Finalization changed Control Input Digest")
            if compute_check_set_result_digest(parse_canonical_artifact(raw)) != check_digest:
                raise RequirementRuntimeError("Finalization changed Check Set Result Digest")
            final_valid = True
        else:
            raw = self._render(
                artifact_id=artifact_id,
                revision=revision,
                status=status,
                context_reference=context_reference,
                control_inputs=control_inputs,
                analysis=analysis,
                checks=checks,
                final_row=None,
                gate_row=None,
                members=members,
            )

        return BuildResult(
            raw_bytes=raw,
            status=status,
            gate_result=gate,
            failed_checks=tuple(failed),
            open_items=analysis.open_items,
            active_exceptions=analysis.active_exceptions,
            final_confirmation_valid=final_valid,
            members=members,
            manifest=manifest,
        )

    def _safe_check_digest(self, raw: bytes) -> str:
        parsed = parse_canonical_artifact(raw)
        try:
            return compute_check_set_result_digest(parsed)
        except CanonicalFormatError:
            return "sha256:" + "0" * 64

    def _final_confirmation(
        self,
        *,
        artifact_id: str,
        revision: int,
        context_reference: str,
        control_inputs: Sequence[str],
        requirement: Mapping[str, Any],
        final_confirmation: Mapping[str, Any],
        control_digest: str,
        check_digest: str,
        active_exceptions: Sequence[str],
    ) -> Mapping[str, str]:
        mode = final_confirmation.get("mode")
        if mode not in {"human", "delegated"}:
            raise RequirementRuntimeError("Final Confirmation mode must be human or delegated")
        confirmer = _identity(final_confirmation.get("confirmer"), "confirmer")
        role = _required_text(final_confirmation.get("role"), "role")
        authority = _required_text(final_confirmation.get("authority_reference"), "authority_reference")
        confirmed_at = _validate_rfc3339(final_confirmation.get("confirmed_at"), "confirmed_at")
        raw = _authority_file(self.project_root, authority)
        refs = [f"{artifact_id}@{revision}#{item}" for item in active_exceptions]
        if mode == "delegated":
            if active_exceptions:
                raise RequirementRuntimeError("delegated confirmation cannot approve Exceptions")
            if role != "Delegated Independent Reviewer":
                raise RequirementRuntimeError("delegated role must be Delegated Independent Reviewer")
            text = raw.decode("utf-8")
            front, body = parse_front_matter(text)
            if front.get("contract") != "sdlc-ai-spec/final-confirmation-authority/v1":
                raise RequirementRuntimeError("delegated Authority Contract is invalid")
            if front.get("artifact") != f"{artifact_id}@{revision}" or front.get("decision") != "approved":
                raise RequirementRuntimeError("delegated Authority is bound to another Artifact or decision")
            if "| Delegation Basis | Reviewer Identity |" not in body:
                raise RequirementRuntimeError("delegated Authority table is missing")
        accepted = final_confirmation.get("accepted_exception_references")
        if accepted is not None:
            if not isinstance(accepted, list) or any(not isinstance(item, str) for item in accepted):
                raise RequirementRuntimeError("accepted_exception_references must be an array")
            if tuple(accepted) != tuple(refs):
                raise RequirementRuntimeError("accepted Exception set does not match active Exceptions")
        subject = final_confirmation.get("subject_digest")
        expected_subject = _subject_digest(requirement, context_reference, control_inputs)
        if subject is not None and subject != expected_subject:
            raise RequirementRuntimeError("Final Confirmation subject_digest is stale")
        return {
            "revision": str(revision),
            "control_digest": control_digest,
            "evaluation_set": _evaluation_contract_set(),
            "check_digest": check_digest,
            "result": "approved",
            "mode": mode,
            "confirmer": confirmer,
            "role": role,
            "authority": authority,
            "exceptions": _reference_text(refs),
            "confirmed_at": confirmed_at,
        }

    def _render(
        self,
        *,
        artifact_id: str,
        revision: int,
        status: str,
        context_reference: str,
        control_inputs: Sequence[str],
        analysis: RequirementAnalysis,
        checks: Mapping[str, CheckOutcome],
        final_row: Mapping[str, str] | None,
        gate_row: Mapping[str, str] | None,
        members: Sequence[CanonicalMember],
    ) -> bytes:
        value = analysis.normalized
        sources = [
            (f"SRC-{index:03d}", item.get("type", "text"), item.get("content", ""), item.get("evidence_reference", "N/A"))
            for index, item in enumerate(value["sources"], start=1)
        ] or [("None", "none", "No source input", "N/A")]
        goals = [
            (f"GOAL-{index:03d}", item.get("problem", ""), item.get("outcome", ""), item.get("success_condition", ""))
            for index, item in enumerate(value["goals"], start=1)
        ] or [("None", "Pending", "Pending", "Pending")]
        affected = [
            (f"AP-{index:03d}", item.get("party", ""), item.get("impact", ""))
            for index, item in enumerate(value["affected_parties"], start=1)
        ] or [("None", "No distinct affected parties", "N/A")]
        req_rows = [
            (f"R-{index:03d}", item.get("type", ""), _reference_text(item.get("source_references", [])), item.get("statement", ""))
            for index, item in enumerate(value["requirements"], start=1)
        ] or [("None", "behavior", "None", "Pending")]
        ac_rows = [
            (f"AC-{index:03d}", _reference_text(item.get("requirement_references", [])), item.get("condition", ""), item.get("expected_result", ""))
            for index, item in enumerate(value["acceptance_criteria"], start=1)
        ] or [("None", "None", "Pending", "Pending")]
        dep_rows = [
            (f"DEP-{index:03d}", item.get("dependency", ""), item.get("required_state", ""), item.get("current_state", ""), item.get("state_check_reference", ""))
            for index, item in enumerate(value["dependencies"], start=1)
        ] or [("None", "No dependencies", "N/A", "N/A", "N/A")]
        open_rows = [
            (item["id"], item["needed"], item["expected_source"], item["blocked_references"], item["state"], item["resolution"])
            for item in analysis.open_items
        ] or [("None", "No open items", "N/A", "N/A", "none", "N/A")]
        evidence_rows = [
            (
                f"EVD-{index:03d}", item.get("type", "other"), _reference_text(item.get("supports_references", [])), item.get("source", ""), item.get("reference", ""), item.get("integrity", ""), item.get("produced_at", ""), item.get("sensitivity", "internal"), "N/A",
            )
            for index, item in enumerate(value["evidence"], start=1)
        ] or [("None", "none", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "No independent Evidence")]
        manifest_rows = [
            (item.member_id, "supporting", item.canonical_name, item.media_type, "REQ supporting material", item.sha256, "N/A")
            for item in members
        ] or [("None", "none", "N/A", "N/A", "N/A", "N/A", "No supporting artifacts")]
        exception_rows = [
            (
                f"EX-{index:03d}", item.get("state", "active"), item.get("origin", "N/A"), item.get("scope", ""), item.get("reason", ""), item.get("risk", ""), item.get("control", ""), item.get("approval", ""), item.get("revisit", ""), item.get("downstream", ""), item.get("resolution", "N/A"),
            )
            for index, item in enumerate(value["exceptions"], start=1)
        ] or [("None", "none", "N/A", "N/A", "No Exceptions", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A")]
        app_rows = [
            (item.get("phase", ""), item.get("disposition", "pending"), item.get("host", "N/A"), item.get("basis", ""))
            for item in value["lifecycle_applicability"]
        ] or [(phase, "pending", "N/A", "Pending") for phase in LIFECYCLE_PHASES]

        inputs = [context_reference, *control_inputs]
        front = [
            "---",
            f"contract: {REQ_CONTRACT}",
            f"phase: {REQ_PHASE}",
            f"id: {artifact_id}",
            f"revision: {revision}",
            f"status: {status}",
            f"context: {context_reference}",
            f"profile: {value['profile']}",
            "inputs:",
        ]
        front.extend(f"  - {item}" for item in inputs)
        front.append("---")

        sections = [
            "\n".join(front),
            f"# {_cell(value['title'])}",
            "## 摘要 Summary\n\n" + _cell(value["summary"]),
            "## 原始输入 Source Input\n\n" + _table(SOURCE_HEADERS, sources),
            "## 目标与成功条件 Goal and Success\n\n" + _table(GOAL_HEADERS, goals),
            "## 范围 Scope\n\n### 包含 In Scope\n\n" + ("\n".join(f"- {_cell(item)}" for item in value["in_scope"]) or "- Pending") + "\n\n### 不包含 Out of Scope\n\n" + ("\n".join(f"- {_cell(item)}" for item in value["out_of_scope"]) or "- Pending"),
            "## 影响对象 Affected Parties\n\n" + _table(AFFECTED_HEADERS, affected),
            "## 需求项 Requirements\n\n" + _table(REQUIREMENT_HEADERS, req_rows),
            "## 验收条件 Acceptance Criteria\n\n" + _table(AC_HEADERS, ac_rows),
            "## 依赖 Dependencies\n\n" + _table(DEPENDENCY_HEADERS, dep_rows),
            "## 生命周期配置 Lifecycle Profile\n\n" + _table(PROFILE_HEADERS, [(value["profile"], value.get("profile_basis", "Confirmed selection"))]),
            "## 待确认项 Open Items\n\n" + _table(OPEN_ITEM_HEADERS, open_rows),
            "## 证据 Evidence\n\n" + _table(EVIDENCE_HEADERS, evidence_rows),
            "## 支撑产物清单 Supporting Artifact Manifest\n\n" + _table(MANIFEST_HEADERS, manifest_rows),
            "## 豁免 Exceptions\n\n" + _table(EXCEPTION_HEADERS, exception_rows),
            "## 生命周期适用性 Lifecycle Applicability\n\n" + _table(APPLICABILITY_HEADERS, app_rows),
        ]
        core_rows = [(check_id, "Core Contract Integrity", checks[check_id].result, checks[check_id].note) for check_id in CORE_CHECKS]
        req_check_rows = [(check_id, "REQ Contract Integrity", checks[check_id].result, checks[check_id].note) for check_id in REQ_CHECKS]
        gate = [
            "## 门禁 Gate",
            "### Core Checks\n\n" + _table(CHECK_HEADERS, core_rows),
            "### REQ Checks\n\n" + _table(CHECK_HEADERS, req_check_rows),
        ]
        if final_row is None:
            final_values = (revision, "", _evaluation_contract_set(), "", "pending", "", "", "", "None", "None", "")
        else:
            final_values = (
                final_row["revision"], final_row["control_digest"], final_row["evaluation_set"], final_row["check_digest"], final_row["result"], final_row["mode"], final_row["confirmer"], final_row["role"], final_row["authority"], final_row["exceptions"], final_row["confirmed_at"],
            )
        gate.append("### Final Confirmation\n\n" + _table(FINAL_CONFIRMATION_HEADERS, [final_values]))
        if gate_row is None:
            gate_values = (revision, "", _evaluation_contract_set(), "", "pending", "None", "", "")
        else:
            gate_values = (
                gate_row["revision"], gate_row["control_digest"], gate_row["evaluation_set"], gate_row["check_digest"], gate_row["gate_result"], gate_row["exceptions"], gate_row["evaluator"], gate_row["evaluated_at"],
            )
        gate.append("### Artifact Gate Summary\n\n" + _table(GATE_SUMMARY_HEADERS, [gate_values]))
        sections.append("\n\n".join(gate))
        return ("\n\n".join(sections).rstrip() + "\n").encode("utf-8")


class RequirementVerifier:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def verify(self, reference: str, revision) -> DomainVerification:
        try:
            artifact_id, number = _exact_base_reference(reference)
            if artifact_id != revision.control.artifact_id or number != revision.control.revision:
                raise RequirementRuntimeError("Verifier reference does not match Revision")
            parsed = parse_canonical_artifact(revision.payload.primary_blob)
            front = parsed.front_matter
            if front.get("contract") != REQ_CONTRACT or front.get("phase") != REQ_PHASE:
                raise RequirementRuntimeError("REQ Contract or Phase is invalid")
            if front.get("id") != artifact_id or front.get("revision") != number:
                raise RequirementRuntimeError("Front Matter identity is invalid")
            if front.get("status") != revision.payload.artifact_status:
                raise RequirementRuntimeError("Front Matter status does not match Payload")
            checks = {}
            for table in find_tables(parsed, CHECK_HEADERS):
                for row in table.rows:
                    if row["Check ID"] in checks:
                        raise RequirementRuntimeError("duplicate Check ID")
                    checks[row["Check ID"]] = row["结果 Result"]
            expected = set(CORE_CHECKS) | set(REQ_CHECKS)
            if set(checks) != expected or any(checks[item] != "pass" for item in expected):
                raise RequirementRuntimeError("ready REQ requires all Core and REQ Checks pass")
            confirmation = require_single_row(require_single_table(parsed, FINAL_CONFIRMATION_HEADERS, "Final Confirmation"), "Final Confirmation")
            summary = require_single_row(require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate Summary"), "Gate Summary")
            control_digest = compute_control_input_digest(revision.payload.primary_blob)
            check_digest = compute_check_set_result_digest(parsed)
            if confirmation["Control Input Digest"] != control_digest or summary["Control Input Digest"] != control_digest:
                raise RequirementRuntimeError("Control Input Digest is stale")
            if confirmation["Check Set Result Digest"] != check_digest or summary["Check Set Result Digest"] != check_digest:
                raise RequirementRuntimeError("Check Set Result Digest is stale")
            if confirmation["Result"] != "approved":
                raise RequirementRuntimeError("Final Confirmation is not approved")
            if confirmation["Evaluation Contract Set"] != _evaluation_contract_set() or summary["Evaluation Contract Set"] != _evaluation_contract_set():
                raise RequirementRuntimeError("Evaluation Contract Set is invalid")
            expected_gate = "pass_with_exception" if revision.payload.artifact_status == "ready_with_exception" else "pass"
            if summary["Gate Result"] != expected_gate:
                raise RequirementRuntimeError("Gate Result does not match Artifact Status")
            _authority_file(self.project_root, confirmation["Authority Reference"])
        except (CanonicalFormatError, RequirementRuntimeError, UnicodeError, OSError) as exc:
            raise RequirementRuntimeError(str(exc)) from exc
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="REQ Domain Contract and Final Confirmation are valid",
        )


class RequirementHandler:
    def __init__(
        self,
        project_root: Path,
        *,
        clock: Callable[[], datetime] = _now,
        authority_factory: Callable[[Path], Any] = FrozenArtifactAuthorityVerifier,
    ):
        self.project_root = project_root.expanduser().resolve()
        self.clock = clock
        self.authority_factory = authority_factory
        self.builder = RequirementBuilder(self.project_root)

    def create(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        if invocation["options"].get("dry_run"):
            return self._dry_run(invocation)
        if not _write_authorized(invocation["confirmations"]):
            return self._error(invocation, "action_required", "WRITE_AUTHORIZATION_REQUIRED", "创建 REQ 需要当前请求的 Artifact Store 写入授权", "AUTHORIZE_ARTIFACT_STORE_WRITE", True)
        if invocation.get("artifact_reference"):
            return self._error(invocation, "action_required", "ARTIFACT_REFERENCE_INVALID", "create 不接受已有 Artifact Reference", "REMOVE_ARTIFACT_REFERENCE", True)
        try:
            read_store = ArtifactStore.open_read_only(self.project_root)
            context, controls = self._inputs(invocation, read_store)
            write_store = ArtifactStore.open_read_write(self.project_root, clock=self.clock)
            allocation = write_store.allocate_artifact("REQ", now=self.clock())
            control = write_store.allocate_revision(allocation.artifact_id, now=self.clock())
            return self._write(invocation, write_store, control, context, controls)
        except StoreNotFoundError as exc:
            return self._exception(invocation, exc, "STORE_NOT_FOUND")
        except (ArtifactStoreError, RequirementRuntimeError, ControlInputError) as exc:
            return self._exception(invocation, exc)

    def revise(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        if invocation["options"].get("dry_run"):
            return self._dry_run(invocation)
        if not _write_authorized(invocation["confirmations"]):
            return self._error(invocation, "action_required", "WRITE_AUTHORIZATION_REQUIRED", "修订 REQ 需要当前请求的 Artifact Store 写入授权", "AUTHORIZE_ARTIFACT_STORE_WRITE", True)
        reference = invocation.get("artifact_reference")
        if not reference:
            return self._error(invocation, "action_required", "ARTIFACT_REFERENCE_REQUIRED", "revise 需要准确 REQ Reference", "PROVIDE_EXACT_ARTIFACT_REFERENCE", True)
        try:
            artifact_id, revision_number = _exact_base_reference(reference)
            read_store = ArtifactStore.open_read_only(self.project_root)
            context, controls = self._inputs(invocation, read_store)
            existing = read_store.read_revision(artifact_id, revision_number)
            if existing.control.state == "abandoned":
                raise InvalidStateError("abandoned Revision cannot be revised")
            write_store = ArtifactStore.open_read_write(self.project_root, clock=self.clock)
            if existing.control.state == "open":
                expected = invocation["inputs"].get("expected_generation", existing.control.generation)
                if expected != existing.control.generation:
                    raise ConflictError("expected_generation does not match current open Revision")
                control = existing.control
            elif existing.control.state == "frozen":
                control = write_store.allocate_revision(
                    artifact_id,
                    base_revision=revision_number,
                    now=self.clock(),
                )
            else:
                raise InvalidStateError("unsupported Revision State")
            return self._write(invocation, write_store, control, context, controls)
        except (ArtifactStoreError, RequirementRuntimeError, ControlInputError) as exc:
            return self._exception(invocation, exc)

    def check(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        reference = invocation.get("artifact_reference")
        if not reference:
            return self._error(invocation, "action_required", "ARTIFACT_REFERENCE_REQUIRED", "check 需要准确 REQ Reference", "PROVIDE_EXACT_ARTIFACT_REFERENCE", True)
        try:
            artifact_id, revision_number = _exact_base_reference(reference)
            store = ArtifactStore.open_read_only(self.project_root)
            stored = store.read_revision(artifact_id, revision_number)
            verifier = RequirementVerifier(self.project_root)
            if stored.control.state == "frozen":
                verifier.verify(reference, stored)
            else:
                parsed = parse_canonical_artifact(stored.payload.primary_blob)
                if parsed.front_matter.get("id") != artifact_id or parsed.front_matter.get("revision") != revision_number:
                    raise RequirementRuntimeError("open REQ identity is invalid")
            gate = self._gate_from_blob(stored.payload.primary_blob)
            status = "completed" if gate["result"] in {"pass", "pass_with_exception"} else ("failed" if gate["result"] == "fail" else "action_required")
            ok = status == "completed"
            return self._result(
                invocation,
                ok=ok,
                status=status,
                stored=stored,
                gate=gate,
                open_items=self._open_items_from_blob(stored.payload.primary_blob),
                warnings=[],
                errors=[] if ok else [{"code": "REQ_CHECK_NOT_READY", "message": "REQ 尚未形成可供下游使用的 Authority"}],
                next_action=None if ok else {"code": "REVISE_REQUIREMENT", "message": "修订准确 REQ Revision 并重新检查", "requires_user": True, "command": None},
            )
        except StoreNotFoundError as exc:
            return self._exception(invocation, exc, "STORE_NOT_FOUND")
        except (ArtifactStoreError, RequirementRuntimeError, CanonicalFormatError) as exc:
            return self._exception(invocation, exc)

    def _inputs(self, invocation, store):
        inputs = _mapping(invocation["inputs"], "inputs")
        context = _required_text(inputs.get("context_reference"), "context_reference")
        _exact_base_reference(context, "CTX")
        store.resolve_exact_reference(context, verifier=self.authority_factory(self.project_root))
        control_values = _list(inputs.get("control_inputs"), "control_inputs")
        controls: list[str] = []
        resolver = ControlInputResolver(self.project_root)
        for value in control_values:
            reference = _required_text(value, "control input reference")
            resolver.resolve_for_phase(store, reference, "REQ")
            controls.append(reference)
        return context, tuple(controls)

    def _write(self, invocation, store, control, context, controls):
        requirement = _mapping(invocation["inputs"].get("requirement"), "inputs.requirement")
        final = invocation["inputs"].get("final_confirmation")
        if final is not None:
            final = _mapping(final, "final_confirmation")
        built = self.builder.build(
            artifact_id=control.artifact_id,
            revision=control.revision,
            context_reference=context,
            control_inputs=controls,
            requirement=requirement,
            final_confirmation=final,
        )
        payload = CanonicalRevisionPayload(
            artifact_id=control.artifact_id,
            artifact_type="REQ",
            revision=control.revision,
            artifact_status=built.status,
            primary_blob=built.raw_bytes,
            primary_media_type="text/markdown",
            primary_sha256=compute_sha256(built.raw_bytes),
            members=built.members,
            manifest=built.manifest,
        )
        stored = store.write_open_revision(payload, expected_generation=control.generation)
        if built.final_confirmation_valid and built.status in {"ready", "ready_with_exception"}:
            store.freeze_revision(
                control.artifact_id,
                control.revision,
                verifier=RequirementVerifier(self.project_root),
                now=self.clock(),
            )
            stored = store.read_revision(control.artifact_id, control.revision)
        gate = {"result": built.gate_result, "failed_checks": list(built.failed_checks)}
        if built.gate_result == "fail":
            status = "failed"
            ok = False
            errors = [{"code": "REQ_GATE_FAILED", "message": "REQ Gate 存在失败检查", "details": list(built.failed_checks)}]
            next_action = {"code": "REVISE_REQUIREMENT", "message": "修正失败检查后修订当前 REQ", "requires_user": True, "command": None}
        elif built.status in {"waiting_input", "draft"}:
            status = "action_required"
            ok = False
            errors = []
            next_action = {"code": "COMPLETE_REQUIREMENT_INPUT", "message": "补充 Open Item 或 Final Confirmation 后修订当前 REQ", "requires_user": True, "command": None}
        else:
            status = "completed"
            ok = True
            errors = []
            next_action = None
        return self._result(invocation, ok=ok, status=status, stored=stored, gate=gate, open_items=list(built.open_items), warnings=[], errors=errors, next_action=next_action)

    def _dry_run(self, invocation):
        try:
            requirement = _mapping(invocation["inputs"].get("requirement"), "inputs.requirement")
            analysis = RequirementAnalyzer().analyze(requirement)
            failed = sorted(check_id for check_id, item in analysis.checks.items() if item.result == "fail")
            status = "failed" if failed else ("action_required" if analysis.open_items else "completed")
            return self._result(
                invocation,
                ok=status == "completed",
                status=status,
                stored=None,
                gate={"result": "fail" if failed else "pending", "failed_checks": failed},
                open_items=list(analysis.open_items),
                warnings=[{"code": "DRY_RUN", "message": "未执行 Store 初始化、分配、写入或冻结"}],
                errors=[] if not failed else [{"code": "REQ_GATE_FAILED", "message": "候选输入存在失败检查"}],
                next_action=None if status == "completed" else {"code": "COMPLETE_REQUIREMENT_INPUT", "message": "修正候选输入后重新执行", "requires_user": True, "command": None},
            )
        except RequirementRuntimeError as exc:
            return self._exception(invocation, exc)

    def _gate_from_blob(self, raw):
        parsed = parse_canonical_artifact(raw)
        summary = require_single_row(require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate Summary"), "Gate Summary")
        failed = []
        for table in find_tables(parsed, CHECK_HEADERS):
            failed.extend(row["Check ID"] for row in table.rows if row["结果 Result"] == "fail")
        return {"result": summary["Gate Result"], "failed_checks": sorted(failed)}

    def _open_items_from_blob(self, raw):
        parsed = parse_canonical_artifact(raw)
        tables = find_tables(parsed, OPEN_ITEM_HEADERS)
        if len(tables) != 1:
            raise RequirementRuntimeError("Open Items table must appear exactly once")
        return [dict(row) for row in tables[0].rows if row["ID"] != "None"]

    def _result(self, invocation, *, ok, status, stored, gate, open_items, warnings, errors, next_action):
        artifact = None
        if stored is not None:
            artifact = {
                "id": stored.control.artifact_id,
                "type": "REQ",
                "revision": stored.control.revision,
                "revision_state": stored.control.state,
                "artifact_status": stored.payload.artifact_status,
                "reference": f"{stored.control.artifact_id}@{stored.control.revision}" if stored.control.state == "frozen" else None,
            }
        return {
            "contract": "sdlc-ai-spec/runtime-result/v1",
            "ok": ok,
            "operation": invocation["operation"],
            "status": status,
            "artifact": artifact,
            "gate": gate,
            "open_items": [dict(item) for item in open_items],
            "warnings": [dict(item) for item in warnings],
            "errors": [dict(item) for item in errors],
            "next_action": next_action,
        }

    def _error(self, invocation, status, code, message, next_code, requires_user):
        return error_result(
            operation=invocation["operation"],
            status=status,
            code=code,
            message=message,
            next_action_code=next_code,
            next_action_message=message,
            requires_user=requires_user,
        )

    def _exception(self, invocation, exc, code=None):
        if isinstance(exc, ConflictError):
            status = "blocked"
            next_code = "RETRY_AFTER_CONFLICT_REVIEW"
        elif isinstance(exc, StoreNotFoundError):
            status = "failed"
            next_code = "PROVIDE_PROJECT_WITH_EXISTING_STORE"
        else:
            status = "failed"
            next_code = "CORRECT_REQUEST_OR_ARTIFACT"
        value = code or getattr(exc, "code", exc.__class__.__name__.upper())
        return self._error(invocation, status, value, str(exc), next_code, True)


def _load_request(path: str | None) -> Mapping[str, Any]:
    if path:
        text = Path(path).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    if not text.strip():
        raise RequirementRuntimeError("request JSON is empty")
    value = json.loads(text)
    if not isinstance(value, Mapping):
        raise RequirementRuntimeError("request JSON must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="sdlc-100-req deterministic runtime")
    parser.add_argument("--input", help="JSON request file; default stdin")
    args = parser.parse_args(argv)
    try:
        request = _load_request(args.input)
        project_root = Path(_required_text(request.get("project_root"), "project_root"))
        result = execute_phase(RequirementHandler(project_root), request)
    except (json.JSONDecodeError, OSError, RequirementRuntimeError, CanonicalFormatError) as exc:
        operation = "check"
        if "request" in locals() and request.get("operation") in {"create", "revise", "check"}:
            operation = request["operation"]
        result = error_result(
            operation=operation,
            status="failed",
            code=getattr(exc, "code", "INVALID_REQUEST"),
            message=str(exc),
            next_action_code="CORRECT_REQUEST",
            next_action_message="修正标准 JSON 请求后重试",
            requires_user=True,
        )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
