"""Shared constants and parsing helpers for the PLN runtime."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Sequence

from packages.sdlc_phasekit import evaluation_contract_set
from packages.sdlc_runtime.canonical import parse_markdown_tables

APPLICABILITY_HEADERS = ("Phase", "Disposition", "Host", "判断依据 Basis")
CHANGE_HEADERS = (
    "Change ID", "Object or Boundary", "Change", "Baseline References",
    "Baseline State", "Target State", "Affected Domains",
)
WORK_HEADERS = (
    "ID",
    "目标 Phase Target Phase",
    "结果 Outcome",
    "执行范围 Execution Scope",
    "来源引用 Source References",
    "约束引用 Constraint References",
    "依赖 Depends On",
    "完成条件 Completion Criteria",
    "预期证据 Expected Evidence",
    "责任角色 Responsible Role",
)
DELIVERY_HEADERS = (
    "Scope Token", "Source References", "Outcome",
)
OBLIGATION_HEADERS = ("Obligation Reference", "Covered By Work Items")
CORE_CHECKS = tuple(f"CORE-G-{index:03d}" for index in range(1, 10))
PLN_CHECKS = tuple(f"PLN-G-{index:03d}" for index in range(1, 8))
PHASE_RANK = {"IMP": 1, "VFY": 2, "RLS": 3}
DISPOSITIONS = {"required", "n/a", "embedded", "waived", "pending"}
WORK_ALLOWED = {
    "id", "target_phase", "outcome", "execution_scope", "source_references",
    "constraint_references", "depends_on", "completion_criteria",
    "expected_evidence", "responsible_role",
}
GENERIC_COMPLETION = {"done", "complete", "completed", "完成", "已完成"}
GENERIC_EVIDENCE = {"evidence", "proof", "证据", "结果"}
ITEM_ID_RE = re.compile(r"^(?:CHG|VFP|OBJ|OBL|EX|R|AC)-[A-Za-z0-9._-]+$")
EVAL_SET = evaluation_contract_set(
    Path(__file__).resolve().parents[1] / "references/source-lock.json",
    (
        "sdlc-ai-spec/spec/core/v1.1",
        "sdlc-ai-spec/spec/artifact-store/v1.1",
        "sdlc-ai-spec/spec/plan/v1.1",
    ),
)


class PlnError(ValueError):
    code = "PLN_RUNTIME_ERROR"


def _base(reference: str) -> str:
    value = reference.split("#", 1)[0].split("/", 1)[0]
    if "@" not in value:
        raise PlnError(f"Scope Input is not an exact Artifact Revision: {reference}")
    return value


def _merge_disposition(values: Sequence[str]) -> str:
    values = tuple(values)
    if not values:
        return "pending"
    if any(value == "pending" for value in values):
        return "pending"
    if any(value == "required" for value in values):
        return "required"
    # An explicit waiver is semantically stronger than n/a/embedded.
    if any(value == "waived" for value in values):
        return "waived"
    if any(value == "embedded" for value in values):
        return "embedded"
    return "n/a"


def _artifact_items(reference: str, parsed, members) -> tuple[str, ...]:
    result: list[str] = []

    def collect(tables):
        for current in tables:
            for row in current.rows:
                identity = row.get("ID") or row.get("Change ID")
                if not isinstance(identity, str) or not ITEM_ID_RE.fullmatch(identity):
                    continue
                if identity.startswith(("CHG-", "VFP-", "OBJ-", "OBL-", "EX-", "R-", "AC-")):
                    result.append(f"{reference}#{identity}")

    collect(parsed.tables)
    for member in members:
        try:
            collect(parse_markdown_tables(member.raw_bytes.decode("utf-8")))
        except (UnicodeError, ValueError):
            continue
    return tuple(dict.fromkeys(result))
