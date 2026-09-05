"""Canonical RLS Primary, State and Supporting Member construction."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from packages.sdlc_artifact_store import CanonicalMember, compute_sha256

from rls_common import canonical_json, exact_reference, require, sha256_bytes
from packages.sdlc_runtime import parse_canonical_artifact, compute_control_input_digest, compute_check_set_result_digest
from packages.sdlc_runtime.canonical import CHECK_HEADERS, FINAL_CONFIRMATION_HEADERS, GATE_SUMMARY_HEADERS, require_single_table, require_single_row, parse_reference_set
from packages.sdlc_runtime.control_inputs import RLS_ITEM_HEADERS, RLS_CONFIRMATION_HEADERS

STATE_MEMBER_ID = "RLS-STATE"
STATE_CONTRACT = "sdlc-ai-spec/rls-state/v1"


def _state_bytes(state: Mapping[str, Any]) -> bytes:
    value = deepcopy(state)
    if not value.get("provisional", True):
        value["final_confirmation"] = None
        value["artifact"]["revision_state"] = "open"
    value.setdefault("state_contract", STATE_CONTRACT)
    return (canonical_json(value) + "\n").encode("utf-8")


def _event_bytes(event: Mapping[str, Any]) -> bytes:
    return (canonical_json(dict(event)) + "\n").encode("utf-8")


def canonical_members(state: Mapping[str, Any]) -> tuple[CanonicalMember, ...]:
    """Build deterministic local members and verify embedded Evidence digests."""
    state_raw = _state_bytes(state)
    members: list[CanonicalMember] = [
        CanonicalMember(
            member_id=STATE_MEMBER_ID,
            canonical_name="rls-state.json",
            media_type="application/json",
            raw_bytes=state_raw,
            sha256=compute_sha256(state_raw),
        )
    ]
    seen_references: set[str] = set()
    for index, evidence in enumerate(state.get("evidence", []), start=1):
        require(
            isinstance(evidence, Mapping)
            and isinstance(evidence.get("event"), Mapping),
            "RLS_EVIDENCE_TAMPERED",
            "canonical Evidence entry is incomplete",
        )
        reference = str(evidence.get("reference", ""))
        require(
            reference and reference not in seen_references,
            "RLS_EVIDENCE_TAMPERED",
            "canonical Evidence references must be unique",
        )
        seen_references.add(reference)
        raw = _event_bytes(evidence["event"])
        digest = sha256_bytes(raw)
        require(
            evidence.get("sha256") == digest
            and reference == f"SANDBOX-EVD-{digest}",
            "RLS_EVIDENCE_TAMPERED",
            "Evidence bytes do not match the RLS state projection",
            reference=reference,
        )
        members.append(
            CanonicalMember(
                member_id=f"RLS-EVD-{index:03d}",
                canonical_name=f"evidence/{digest}.json",
                media_type="application/json",
                raw_bytes=raw,
                sha256=compute_sha256(raw),
            )
        )
    return tuple(members)


def _cell(value: Any) -> str:
    text = (", ".join(value) or "None") if isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value) else value if isinstance(value, str) else canonical_json(value)
    return str(text).replace("|", "\\|").replace("\n", "<br>")


def _table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> list[str]:
    header = list(headers)
    output = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    for row in rows:
        output.append("| " + " | ".join(_cell(value) for value in row) + " |")
    return output


def canonical_status(state: Mapping[str, Any]) -> str:
    return ("ready_with_exception" if state.get("artifact_gate") == "pass_with_exception" else "ready") if state.get("final_confirmation") and state.get("artifact_gate") in {"pass", "pass_with_exception"} else "draft"


def render_markdown(
    state: Mapping[str, Any],
    *,
    members: Iterable[CanonicalMember] | None = None,
) -> bytes:
    """Render the fixed RLS report from state; byte equality is the primary parser."""
    artifact = state["artifact"]
    contract = state["release_contract"]
    members = tuple(members or canonical_members(state))
    context = exact_reference(state.get("context_reference", ""), "CTX")
    profile = state.get("profile")
    require(isinstance(profile, str) and bool(profile.strip()), "RLS_CONTRACT_INVALID", "accurate CTX profile is required")
    inputs = state.get("input_references")
    require(isinstance(inputs, list) and contract["vfy_reference"] in inputs, "RLS_CONTRACT_INVALID", "accurate direct upstream inputs are required")
    lines = [
        "---",
        "contract: sdlc-ai-spec/artifact/v1",
        "phase: RLS",
        f"id: {artifact['id']}",
        f"revision: {artifact['revision']}",
        f"status: {canonical_status(state)}",
        f"context: {context}",
        f"profile: {profile}",
        "inputs:",
        *[f"  - {reference}" for reference in inputs],
        "---",
        "",
        f"# Release {contract['release_reference']}",
        "",
        "## 摘要 Summary",
        "",
        *_table(
            ("Field", "Value"),
            (
                ("RLS Reference", artifact["reference"]),
                ("Release Target", contract["release_target"]),
                ("Release Conclusion", state.get("release_conclusion")),
                ("Artifact Gate", state.get("artifact_gate")),
                ("Target Effect", bool(state.get("target_effect"))),
            ),
        ),
        "",
        "## 范围 Scope",
        "",
        *_table(
            ("Field", "Value"),
            (
                ("Scope Reference", contract["scope_reference"]),
                ("Result References", contract["result_references"]),
                ("VFY Reference", contract["vfy_reference"]),
            ),
        ),
        "",
        "## 发版合约 Release Contract",
        "",
        *_table(
            ("Field", "Value"),
            ((key, contract[key]) for key in sorted(contract)),
        ),
        "",
        "## 发版项 Release Items",
        "",
        *_table(
            RLS_ITEM_HEADERS,
            (
                (
                    row["id"],
                    row["action"],
                    row["source_references"],
                    row.get("prerequisite"),
                    row.get("executor"),
                    row["result"],
                    row.get("follow_up"),
                    row.get("evidence_references", []),
                )
                for row in state["release_items"]
            ),
        ),
        "",
        "## 上线后确认 Post-release Confirmation",
        "",
        *_table(
            RLS_CONFIRMATION_HEADERS,
            (
                (
                    row["id"],
                    row["source_references"],
                    row["confirmation"],
                    row["expected"],
                    row.get("executor"),
                    row["evidence_requirement"],
                    row.get("observed"),
                    row["result"],
                    row.get("follow_up"),
                    row.get("evidence_references", []),
                )
                for row in state["confirmations"]
            ),
        ),
        "",
        "## 发版结论 Release Conclusion",
        "",
        *_table(
            ("Field", "Value"),
            (
                ("Conclusion", state.get("release_conclusion")),
                ("Follow-up", state.get("follow_up")),
                ("Target Snapshot Before", state.get("target_snapshot_before")),
                ("Target Snapshot After", state.get("target_snapshot_after")),
            ),
        ),
        "",
        "## 待确认项 Open Items",
        "",
        *_table(
            ("Type", "ID", "State"),
            [
                ("RLI", row["id"], row["result"])
                for row in state["release_items"]
                if row["result"] == "pending"
            ]
            + [
                ("RCF", row["id"], row["result"])
                for row in state["confirmations"]
                if row["result"] == "pending"
            ]
            or [("None", "None", "None")],
        ),
        "",
        "## 证据 Evidence",
        "",
        *_table(
            ("Reference", "SHA-256", "Locator", "Item", "Result", "Target Effect"),
            (
                (
                    row["reference"],
                    row["sha256"],
                    row.get("locator"),
                    row["event"].get("item"),
                    row["event"].get("result"),
                    row["event"].get("target_effect"),
                )
                for row in state.get("evidence", [])
            ),
        ),
        "",
        "## 支撑产物清单 Supporting Artifact Manifest",
        "",
        *_table(
            ("Member ID", "Canonical Name", "Media Type", "Purpose", "SHA-256 Digest"),
            (
                (
                    member.member_id,
                    member.canonical_name,
                    member.media_type,
                    "RLS state or immutable target observation",
                    member.sha256,
                )
                for member in members
            ),
        ),
        "",
        "## 豁免 Exceptions",
        "",
        *_table(
            ("ID", "State", "Origin Reference", "Scope", "Reason", "Known Risk", "Compensating Control", "Approval", "Revisit Condition", "Downstream Obligation", "Resolution References"),
            ((row["id"], row["state"], row["origin_reference"], row["scope"], row["reason"], row["known_risk"], row["compensating_control"], row["approval"], row["revisit_condition"], row["downstream_obligation"], row.get("resolution_references", [])) for row in state.get("exceptions", [])),
        ),
        "",
    ]
    gate = state.get("artifact_gate", "pending")
    terminal = gate in {"pass", "pass_with_exception"} and not state.get("effect_uncertain")
    confirmation = state.get("final_confirmation") or {}
    checks = [("CORE-G-009", "Current Final Confirmation", "pass" if confirmation else "pending", "Exact current authority binding")]
    checks.extend((f"RLS-G-{index:03d}", label, "pass" if terminal else "pending", "Recomputed by RLS domain verifier")
                  for index, label in enumerate(("Current context, VFY, immutable contract, authorized baseline and pre-execution readback", "Complete RLI, RLS Work Item, RCF, evidence and exception coverage", "Accurate target state, Release Conclusion and unique Follow-up"), 1))
    lines.extend(["## 门禁 Gate", "", *_table(CHECK_HEADERS, checks), ""])
    prefix = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    control_digest = compute_control_input_digest(prefix)
    check_digest = compute_check_set_result_digest(parse_canonical_artifact(prefix)) if terminal else "N/A"
    evaluation = evaluation_contract_set()
    from rls_exceptions import unresolved_exception_references
    exception_refs = unresolved_exception_references(state)
    final = (
        artifact["revision"], control_digest, evaluation, check_digest,
        "approved" if confirmation else "pending", confirmation.get("mode", "N/A"),
        confirmation.get("confirmer", confirmation.get("confirmer_identity", "N/A")),
        confirmation.get("role", "N/A"), confirmation.get("authority_reference", "N/A"),
        confirmation.get("accepted_exception_references", []), confirmation.get("confirmed_at", "N/A"),
    )
    summary = (artifact["revision"], control_digest, evaluation, check_digest, gate,
               exception_refs, "rls-domain-verifier", confirmation.get("confirmed_at", "N/A"))
    return prefix + ("## 最终确认 Final Confirmation\n\n" + "\n".join(_table(FINAL_CONFIRMATION_HEADERS, (final,)))
        + "\n\n## Artifact Gate Summary\n\n" + "\n".join(_table(GATE_SUMMARY_HEADERS, (summary,))) + "\n").encode("utf-8")


def evaluation_contract_set():
    path = Path(__file__).resolve().parents[1] / "references/contract.md"
    return "sdlc-ai-spec/rls-runtime-contract/v1@" + compute_sha256(path.read_bytes())


def confirmation_from_primary(primary, state):
    row = require_single_row(require_single_table(parse_canonical_artifact(primary), FINAL_CONFIRMATION_HEADERS, "Final Confirmation"), "Final Confirmation")
    if row["Result"] != "approved":
        return None
    from rls_contract import final_confirmation_digest
    return dict(mode=row["Mode"], confirmer=row["Confirmer"], confirmer_identity=row["Confirmer"],
                role=row["Role"], authority_reference=row["Authority Reference"],
                confirmed_at=row["Confirmed At"], control_input_digest=row["Control Input Digest"],
                check_set_result_digest=row["Check Set Result Digest"],
                evaluation_contract_set=row["Evaluation Contract Set"], digest=final_confirmation_digest(state),
                accepted_exception_references=list(parse_reference_set(row["Accepted Exception References"])))


def validate_primary_against_state(
    primary: bytes,
    state: Mapping[str, Any],
    *,
    members: Iterable[CanonicalMember],
) -> None:
    parsed = parse_canonical_artifact(primary)
    require(parsed.front_matter.get("context") == state["context_reference"]
            and parsed.front_matter.get("profile") == state["profile"]
            and parsed.front_matter.get("status") == canonical_status(state)
            and parsed.front_matter.get("inputs") == state["input_references"],
            "RLS_CONTRACT_INVALID", "Core Front Matter differs from exact RLS authority")
    expected = render_markdown(state, members=tuple(members))
    require(
        primary == expected,
        "RLS_CONTRACT_INVALID",
        "RLS Primary differs from canonical RLS-STATE and Supporting Members",
    )


def load_state_member(raw_bytes: bytes) -> dict[str, Any]:
    try:
        state = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("RLS-STATE is not canonical UTF-8 JSON") from exc
    require(
        isinstance(state, dict)
        and state.get("state_contract") == STATE_CONTRACT,
        "RLS_CONTRACT_INVALID",
        "RLS-STATE contract is invalid",
    )
    return state
