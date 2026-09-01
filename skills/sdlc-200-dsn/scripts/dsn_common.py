#!/usr/bin/env python3
"""Deterministic create/revise/check runtime for sdlc-200-dsn."""

from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
for candidate in (PLUGIN_ROOT, PLUGIN_ROOT / "packages", SCRIPT_DIR):
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
    StoreNotFoundError,
    compute_sha256,
)
from packages.sdlc_runtime import (  # noqa: E402
    ControlInputError,
    ControlInputResolver,
    FrozenArtifactAuthorityVerifier,
    INTERFACE_CONTRACT,
    RESULT_CONTRACT,
    SkillArgumentError,
    authority_reference,
    compute_check_set_result_digest,
    compute_control_input_digest,
    exact_artifact_reference,
    execute_phase,
    load_skill_interface,
    parse_canonical_artifact,
    parse_front_matter,
    parse_reference_set,
    render_commands,
    render_examples,
    render_help,
    render_version,
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
from packages.sdlc_runtime.skill_inputs import (  # noqa: E402
    SkillCommandWithInputs,
    parse_skill_command_with_inputs,
)

from domain_catalog import (  # noqa: E402
    COMPOSITE_SUBDOMAINS,
    DOMAIN_BY_CODE,
    DOMAIN_CATALOG,
    DOMAIN_ORDER,
    DomainContractError,
    aggregate_composite_disposition,
    normalize_composite_rows,
    normalize_domain_rows,
)

DSN_CONTRACT = "sdlc-ai-spec/artifact/v1"
DSN_PHASE = "DSN"
ARTIFACT_TYPE = "DSN"
PROFILE_VALUES = frozenset({"full", "lite", "hotfix"})
CHANGE_TYPES = frozenset({"new", "incremental", "reuse"})
CHANGE_VALUES = frozenset({"add", "modify", "remove", "reuse"})
DISPOSITIONS = frozenset({"required", "n/a", "waived", "pending"})
LIFECYCLE_PHASES = ("PLN", "IMP", "VFY", "RLS")
EXCEPTION_STATES = frozenset({"active", "carried", "resolved", "superseded"})
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
SECRET_RE = re.compile(
    r"(?i)(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:password|passwd|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*[^\s|]{6,})"
)

BASELINE_HEADERS = (
    "Change Type",
    "Current Baseline References",
    "Target State Summary",
    "Impact Summary",
)
CHANGE_HEADERS = (
    "Change ID",
    "Object or Boundary",
    "Change",
    "Baseline References",
    "Baseline State",
    "Target State",
    "Affected Domains",
)
TRACE_HEADERS = (
    "Source References",
    "Design Item or Member References",
    "Decision References",
    "VFY Point or Objective References",
    "N/A Reason",
)
DECISION_HEADERS = (
    "ID",
    "Requirement or Constraint References",
    "决策问题 Decision Question",
    "候选方案 Options",
    "选择结果 Decision",
    "选择依据 Rationale",
    "影响 Domain Affected Domains",
)
MATRIX_HEADERS = (
    "分组 Group",
    "设计领域 Design Domain",
    "处置 Disposition",
    "完成状态 Completion",
    "责任角色 Responsible Role",
    "内容引用 Content Reference",
    "适用性依据引用 Applicability Basis References",
    "不适用或豁免说明 N/A or Waiver Reason",
)
COMPOSITE_HEADERS = (
    "复合 Domain 分类码 Composite Domain Catalog Code",
    "子领域 Subdomain",
    "Disposition",
    "Applicability Basis References",
    "不适用、豁免或待确认说明 N/A, Waiver or Pending Reason",
    "Exception References",
)
MANIFEST_HEADERS = (
    "Member ID",
    "Type",
    "Domain",
    "Domain Spec Reference or Digest",
    "Path or Reference",
    "Media Type",
    "Purpose",
    "SHA-256 Digest",
    "Empty Reason",
)
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
REQ_HEADERS = (
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

CORE_CHECKS = tuple(f"CORE-G-{index:03d}" for index in range(1, 10))
DSN_CHECKS = tuple(f"DSN-G-{index:03d}" for index in range(1, 11))

SPEC_HASHES = {
    "core-spec.md": "1eefa7a138f2d221140137a5fac0f5429b7f847273fe9d70e891ace6c3b7a89b",
    "artifact-store-spec.md": "b340ca2a38dfe0f7409acaa8f9ac559e8872bed44725037889528e3d167d4764",
    "200-dsn-spec.md": "998b76ebf72714706bca045d22f2b5b09ac655404f324cb904edcc241bc4f0ee",
    "200-dsn-domains/110-workflow-state.md": "816a9c5144fa2980e5d9675c6b74bed74a7bb07c9cacab655a9ce57c64790f0c",
    "200-dsn-domains/120-ux-interaction.md": "dd46d3f9ab07702e65b776ef1e1a2036e8bf1413f36487334f85b7b525b21ca6",
    "200-dsn-domains/130-ui-content.md": "97c0733673fc7141dd704b6e254929ec08d2ba96d8e6818b69782e7160991386",
    "200-dsn-domains/140-accessibility-i18n.md": "60a881cd1c69fbda8a02befb641f4dd8ab510c6147e02e892c3f9ba530319e01",
    "200-dsn-domains/210-system-architecture.md": "84a62b6f15542663e7ecf93cd6e12d96b1453e9a52a64cdd1f510a9076400eef",
    "200-dsn-domains/220-components-modules.md": "67d238cd54eccd896ad99111db2692676a5f504fd3c0114c1b296be4fa9dcd6c",
    "200-dsn-domains/230-interfaces-integration.md": "db196e684b4d86ff6d1343633a368c34059b285524703dacebf47c23738af842",
    "200-dsn-domains/240-data-design.md": "0d6383f895b1a43349c38a9fd22e5704451c451e66c3b4063938c098c22f4fef",
    "200-dsn-domains/310-security-privacy-compliance.md": "9b9c2764f57d96e0861ed7a5c841f622bc19f6ac1125ac538a6337978696d105",
    "200-dsn-domains/320-performance-capacity.md": "28928cb2d6dd99ccb98cb68e85a7c990e55c6590e5e6fa04207d8fa8df6bebc6",
    "200-dsn-domains/330-reliability-recovery.md": "7d3196dad795838f906f351aa462b06637f0c377cf5dd70c866a278b91db8a10",
    "200-dsn-domains/340-compatibility-migration.md": "46ae3ddea5bd98930a065431e201e67bb81f404f42867a015bf0db8738430cb1",
    "200-dsn-domains/350-maintainability-extensibility.md": "c419d0da292d36dbd1531d3305f753bfe2e67cc9750bcbe5db403d66d1555619",
    "200-dsn-domains/410-deployment-configuration.md": "8d5968912851696706c894c93c4319e122a0f527aa5035439ce33ac01d5b0291",
    "200-dsn-domains/420-observability-operability.md": "92b19fd4a50fe1e887f64a69d13c9713fdf64198e2bd9c6ef2f9da9456579c34",
    "200-dsn-domains/510-verifiability-vfy-strategy.md": "30cea8dec4a69793a5bcc10ae9a6d4fa420fbff1b81e85bc4fe3f6450ba640f6",
}


class DsnRuntimeError(ValueError):
    code = "DSN_RUNTIME_ERROR"


@dataclass(frozen=True)
class CheckOutcome:
    result: str
    note: str


@dataclass(frozen=True)
class UpstreamScope:
    context_reference: str
    scope_references: tuple[str, ...]
    control_references: tuple[str, ...]
    requirement_items: tuple[str, ...]
    acceptance_items: tuple[str, ...]


@dataclass(frozen=True)
class DsnAnalysis:
    checks: Mapping[str, CheckOutcome]
    open_items: tuple[Mapping[str, str], ...]
    active_exceptions: tuple[str, ...]
    normalized: Mapping[str, Any]
    domain_rows: tuple[Mapping[str, Any], ...]
    composite_rows: tuple[Mapping[str, str], ...]


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
    subject_digest: str


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
    return (
        str(value)
        .replace("|", "&#124;")
        .replace("\r", " ")
        .replace("\n", "<br>")
        .strip()
    )


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        if len(row) != len(headers):
            raise DsnRuntimeError("table row width does not match headers")
        output.append("| " + " | ".join(_cell(value) for value in row) + " |")
    return "\n".join(output)


def _text(value: Any, name: str, *, allow_na: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DsnRuntimeError(f"{name} must be a non-empty string")
    result = value.strip()
    if not allow_na and result in {"N/A", "None", "Pending"}:
        raise DsnRuntimeError(f"{name} must contain a concrete value")
    return result


def _rows(value: Any, name: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise DsnRuntimeError(f"{name} must be an array of objects")
    return [dict(item) for item in value]


def _refs(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if value is None:
        values: list[str] = []
    elif isinstance(value, str):
        values = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values = [str(item).strip() for item in value if str(item).strip()]
    else:
        raise DsnRuntimeError(f"{name} must be a reference array")
    if required and not values:
        raise DsnRuntimeError(f"{name} must not be empty")
    if len(values) != len(set(values)):
        raise DsnRuntimeError(f"{name} contains duplicate references")
    return tuple(values)


def _exact_base(reference: str, phase: str | None = None) -> tuple[str, int]:
    artifact_id, revision = exact_artifact_reference(reference)
    if reference != f"{artifact_id}@{revision}":
        raise DsnRuntimeError("operation requires an exact base Artifact Reference")
    if phase is not None and not artifact_id.startswith(phase + "-"):
        raise DsnRuntimeError(f"Reference must target {phase}")
    return artifact_id, revision


def _evaluation_contract_set() -> str:
    return ", ".join(
        f"docs/v1.1/{name}@sha256:{digest}"
        for name, digest in SPEC_HASHES.items()
    )


def _subject_digest(
    design: Mapping[str, Any],
    context_reference: str,
    scope_inputs: Sequence[str],
    control_inputs: Sequence[str],
) -> str:
    raw = json.dumps(
        {
            "context_reference": context_reference,
            "scope_inputs": list(scope_inputs),
            "control_inputs": list(control_inputs),
            "design": design,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(raw)


def _authority_file(project_root: Path, reference: str) -> bytes:
    relative, digest = authority_reference(reference)
    target = (project_root / relative).resolve()
    try:
        target.relative_to(project_root)
    except ValueError as exc:
        raise DsnRuntimeError("Authority Reference escapes project root") from exc
    if not target.is_file():
        raise DsnRuntimeError("Authority Reference file does not exist")
    raw = target.read_bytes()
    if sha256_bytes(raw) != digest:
        raise DsnRuntimeError("Authority Reference digest does not match")
    return raw


def _write_authorized(invocation: Mapping[str, Any]) -> bool:
    policy = invocation.get("options", {}).get("write_policy")
    if policy == "auto":
        return True
    if policy == "deny":
        return False
    return any(
        item.get("type") == "artifact_store_write" and item.get("approved") is True
        for item in invocation.get("confirmations", [])
    )


def _decode_supporting_member(item: Mapping[str, Any], index: int) -> CanonicalMember:
    member_id = str(item.get("member_id") or f"SUP-{index:03d}")
    if not re.fullmatch(r"SUP-[0-9]{3}", member_id):
        raise DsnRuntimeError(f"invalid Supporting Member ID: {member_id}")
    canonical_name = _text(item.get("canonical_name"), "canonical_name")
    media_type = _text(item.get("media_type"), "media_type")
    content = item.get("content", "")
    if not isinstance(content, str):
        raise DsnRuntimeError("supporting member content must be a string")
    encoding = item.get("encoding", "utf-8")
    if encoding == "utf-8":
        raw = content.encode("utf-8")
    elif encoding == "base64":
        try:
            raw = base64.b64decode(content, validate=True)
        except ValueError as exc:
            raise DsnRuntimeError("invalid base64 supporting member") from exc
    else:
        raise DsnRuntimeError("supporting member encoding must be utf-8 or base64")
    if SECRET_RE.search(raw.decode("utf-8", errors="ignore")):
        raise DsnRuntimeError("supporting member appears to contain a Secret")
    return CanonicalMember(
        member_id=member_id,
        canonical_name=canonical_name,
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


def _domain_member(
    *,
    definition,
    artifact_id: str,
    revision: int,
    scope_references: Sequence[str],
    decisions: Sequence[str],
    row: Mapping[str, Any],
) -> CanonicalMember:
    lines = [
        f"# {definition.display_name}",
        "",
        _table(
            ("关联项 Relation", "值 Value"),
            (
                ("父 DSN ID Parent DSN ID", artifact_id),
                ("Parent Revision", revision),
                ("Requirement References", ", ".join(scope_references)),
                ("Decision References", ", ".join(decisions) if decisions else "None"),
            ),
        ),
        "",
        row["design_result_markdown"].strip(),
        "",
        "## 约束与影响 Constraints and Impact",
        "",
    ]
    constraints = list(row["constraints_impacts"])
    if constraints:
        lines.append(
            _table(
                (
                    "ID",
                    "类型 Type",
                    "内容 Content",
                    "影响的下游 Phase Affected Downstream Phase",
                    "Reference",
                ),
                [
                    (
                        item.get("id")
                        or f"CIM-{definition.code.split('-')[1]}-{index:03d}",
                        item.get("type"),
                        item.get("content"),
                        item.get("affected_phase"),
                        item.get("reference") or "N/A",
                    )
                    for index, item in enumerate(constraints, start=1)
                ],
            )
        )
    else:
        lines.append("None — no additional constraint or impact.")
    if definition.code != "DOM-510":
        lines.extend(["", "## VFY 要点 VFY Points", ""])
        lines.append(
            _table(
                (
                    "ID",
                    "Requirement, AC or Design References",
                    "验证对象 Verification Object",
                    "可观察结果 Observable Result",
                    "预期 Evidence Expected Evidence",
                ),
                [
                    (
                        item.get("id")
                        or f"VFP-{definition.code.split('-')[1]}-{index:03d}",
                        ", ".join(_refs(item.get("references"), "vfy references", required=True)),
                        _text(item.get("verification_object"), "verification_object"),
                        _text(item.get("observable_result"), "observable_result"),
                        _text(item.get("expected_evidence"), "expected_evidence"),
                    )
                    for index, item in enumerate(row["vfy_points"], start=1)
                ],
            )
        )
    lines.extend(["", "## 证据引用 Evidence References", ""])
    evidence = list(row["evidence_references"])
    if evidence:
        lines.append(
            _table(
                ("Evidence or Member Reference", "Supports Item References", "Purpose"),
                [
                    (
                        _text(item.get("reference"), "evidence reference"),
                        ", ".join(_refs(item.get("supports"), "evidence supports", required=True)),
                        _text(item.get("purpose"), "evidence purpose"),
                    )
                    for item in evidence
                ],
            )
        )
    else:
        lines.append(
            _table(
                ("Evidence or Member Reference", "Supports Item References", "Purpose"),
                (("None", "N/A", "No domain-specific Evidence references"),),
            )
        )
    raw = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    if SECRET_RE.search(raw.decode("utf-8", errors="ignore")):
        raise DsnRuntimeError(f"{definition.code} member appears to contain a Secret")
    return CanonicalMember(
        member_id=definition.code,
        canonical_name=definition.canonical_name,
        media_type="text/markdown",
        raw_bytes=raw,
        sha256=compute_sha256(raw),
    )


__all__ = tuple(name for name in globals() if not name.startswith("__"))
