"""Canonical late-phase Artifact renderer."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Mapping, Sequence

from packages.sdlc_artifact_store import CanonicalManifest, CanonicalMember, ManifestMember
from packages.sdlc_runtime import (
    compute_check_set_result_digest,
    compute_control_input_digest,
    parse_canonical_artifact,
)
from packages.sdlc_runtime.canonical import (
    CHECK_HEADERS,
    FINAL_CONFIRMATION_HEADERS,
    GATE_SUMMARY_HEADERS,
)

from .common import refs, rows, table
from .models import CheckOutcome, PhaseInputs

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
    "Canonical Name",
    "Media Type",
    "Purpose",
    "SHA-256 Digest",
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


def manifest(members: Sequence[CanonicalMember]) -> CanonicalManifest:
    ordered = tuple(sorted(members, key=lambda item: (item.member_id, item.canonical_name)))
    ids = [item.member_id for item in ordered]
    names = [item.canonical_name for item in ordered]
    if len(ids) != len(set(ids)) or len(names) != len(set(names)):
        raise ValueError("member IDs and canonical names must be unique")
    payload = {
        "contract": "sdlc-ai-spec/artifact-manifest/v1",
        "local_members": [
            {
                "member_id": item.member_id,
                "canonical_name": item.canonical_name,
                "media_type": item.media_type,
                "sha256": item.sha256,
            }
            for item in ordered
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return CanonicalManifest(
        raw_bytes=raw,
        media_type="application/json",
        local_members=tuple(
            ManifestMember(item.member_id, item.canonical_name, item.media_type, item.sha256)
            for item in ordered
        ),
    )


def _open_item_rows(items: Sequence[Mapping[str, Any]]):
    result = []
    for index, item in enumerate(items, start=1):
        result.append((
            item.get("id") or f"OPI-{index:03d}",
            item.get("needed") or item.get("decision") or "N/A",
            item.get("expected_source") or "N/A",
            item.get("blocked_references") or "N/A",
            item.get("state") or "open",
            item.get("resolution") or "N/A",
        ))
    return result or [("None", "No open items", "N/A", "N/A", "closed", "N/A")]


def _evidence_rows(items: Sequence[Mapping[str, Any]]):
    result = []
    for index, item in enumerate(items, start=1):
        result.append((
            item.get("id") or f"EVD-{index:03d}",
            item.get("type") or "reference",
            ", ".join(refs(item.get("supports_references"), "evidence supports")) or "None",
            item.get("source") or item.get("producer") or "N/A",
            item.get("reference") or "N/A",
            item.get("integrity") or item.get("digest") or "N/A",
            item.get("produced_at") or "N/A",
            item.get("sensitivity") or item.get("access") or "normal",
            item.get("empty_reason") or "N/A",
        ))
    return result or [("None", "N/A", "None", "N/A", "N/A", "N/A", "N/A", "normal", "No external evidence")]


def _exception_rows(items: Sequence[Mapping[str, Any]]):
    result = []
    for index, item in enumerate(items, start=1):
        result.append((
            item.get("id") or f"EX-{index:03d}",
            item.get("state") or "active",
            item.get("origin_reference") or item.get("origin_exception_reference") or "N/A",
            item.get("scope") or item.get("skipped_obligation") or "N/A",
            item.get("reason") or "N/A",
            item.get("known_risk") or "N/A",
            item.get("compensating_control") or "N/A",
            item.get("approval") or "N/A",
            item.get("revisit_condition") or "N/A",
            item.get("downstream_obligation") or "N/A",
            item.get("resolution_references") or "None",
        ))
    return result or [("None", "N/A", "N/A", "No exception", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "None")]


def _applicability_rows(items: Sequence[Mapping[str, Any]]):
    return [
        (
            item.get("phase") or "N/A",
            item.get("disposition") or "pending",
            item.get("host") or "N/A",
            item.get("basis") or "N/A",
        )
        for item in items
    ] or [("N/A", "pending", "N/A", "No lifecycle applicability supplied")]


def render_phase_artifact(
    *,
    artifact_id: str,
    phase: str,
    revision: int,
    status: str,
    profile: str,
    phase_inputs: PhaseInputs,
    title: str,
    sections: Sequence[tuple[str, str]],
    checks: Mapping[str, CheckOutcome],
    open_items: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    exceptions: Sequence[Mapping[str, Any]],
    lifecycle_applicability: Sequence[Mapping[str, Any]],
    final_confirmation: Mapping[str, Any] | None,
    gate_result: str,
    evaluation_contract_set: str,
    evaluator: str,
    members: Sequence[CanonicalMember] = (),
) -> bytes:
    all_inputs = tuple(dict.fromkeys((*phase_inputs.scope_references, *phase_inputs.control_references)))
    front = [
        "---",
        "contract: sdlc-ai-spec/artifact/v1",
        f"phase: {phase}",
        f"id: {artifact_id}",
        f"revision: {revision}",
        f"status: {status}",
        f"context: {phase_inputs.context_reference}",
        f"profile: {profile}",
        "inputs:",
        *(f"  - {item}" for item in all_inputs),
        "---",
        f"# {title}",
        "",
    ]
    lines = list(front)
    for heading, body in sections:
        lines.extend([heading, "", body.rstrip(), ""])
    lines.extend([
        "## 待确认项 Open Items", "", table(OPEN_ITEM_HEADERS, _open_item_rows(open_items)), "",
        "## 证据 Evidence", "", table(EVIDENCE_HEADERS, _evidence_rows(evidence)), "",
        "## Supporting Artifact Manifest", "", table(
            MANIFEST_HEADERS,
            [
                (item.member_id, item.canonical_name, item.media_type, "Supporting phase evidence", item.sha256)
                for item in sorted(members, key=lambda member: member.member_id)
            ] or [("None", "N/A", "N/A", "No local members", "N/A")],
        ), "",
        "## 豁免 Exceptions", "", table(EXCEPTION_HEADERS, _exception_rows(exceptions)), "",
        "## 生命周期适用性 Lifecycle Applicability", "", table(APPLICABILITY_HEADERS, _applicability_rows(lifecycle_applicability)), "",
        "## 门禁 Gate", "",
    ])
    check_rows = [
        (check_id, check_id, outcome.result, outcome.message)
        for check_id, outcome in sorted(checks.items())
    ]
    lines.extend([table(CHECK_HEADERS, check_rows), ""])
    pre_confirmation = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    control_digest = compute_control_input_digest(pre_confirmation)
    if any(outcome.result == "pending" and check_id != "CORE-G-009" for check_id, outcome in checks.items()):
        check_digest = "N/A"
    else:
        check_digest = compute_check_set_result_digest(parse_canonical_artifact(pre_confirmation))
    exception_refs = ", ".join(
        f"{artifact_id}@{revision}#{item.get('id')}"
        for item in exceptions
        if item.get("state") in {"active", "carried"} and item.get("id")
    ) or "None"
    if final_confirmation is None:
        confirmation = (
            revision, control_digest, evaluation_contract_set, check_digest,
            "pending", "N/A", "N/A", "N/A", "N/A", exception_refs, "N/A",
        )
        evaluated_at = "N/A"
    else:
        confirmation = (
            revision, control_digest, evaluation_contract_set, check_digest,
            "approved", final_confirmation["mode"], final_confirmation["confirmer"],
            final_confirmation["role"], final_confirmation["authority_reference"],
            exception_refs, final_confirmation["confirmed_at"],
        )
        evaluated_at = str(final_confirmation["confirmed_at"])
    summary = (
        revision, control_digest, evaluation_contract_set, check_digest,
        gate_result, exception_refs, evaluator, evaluated_at,
    )
    suffix = (
        "### Final Confirmation\n\n"
        + table(FINAL_CONFIRMATION_HEADERS, (confirmation,))
        + "\n\n### Artifact Gate Summary\n\n"
        + table(GATE_SUMMARY_HEADERS, (summary,))
        + "\n"
    )
    return pre_confirmation + suffix.encode("utf-8")
