"""Independent semantic checks for persisted REQ canonical Markdown."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from packages.sdlc_runtime import parse_reference_set
from packages.sdlc_runtime.canonical import (
    CHECK_HEADERS,
    FINAL_CONFIRMATION_HEADERS,
    GATE_SUMMARY_HEADERS,
    CanonicalFormatError,
    ParsedCanonicalArtifact,
    find_tables,
    require_single_row,
    require_single_table,
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
OPEN_ITEM_HEADERS = (
    "ID",
    "所需输入或待确认决策 Needed Input or Decision",
    "预期来源 Expected Source",
    "被阻塞项 Blocked References",
    "状态 State",
    "解决结果或证据 Resolution or Evidence",
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
REQUIRED_HEADINGS = (
    "## 摘要 Summary",
    "## 原始输入 Source Input",
    "## 目标与成功条件 Goal and Success",
    "## 范围 Scope",
    "## 影响对象 Affected Parties",
    "## 需求项 Requirements",
    "## 验收条件 Acceptance Criteria",
    "## 依赖 Dependencies",
    "## 生命周期配置 Lifecycle Profile",
    "## 待确认项 Open Items",
    "## 证据 Evidence",
    "## 支撑产物清单 Supporting Artifact Manifest",
    "## 豁免 Exceptions",
    "## 生命周期适用性 Lifecycle Applicability",
    "## 门禁 Gate",
)
LIFECYCLE_PHASES = ("DSN", "PLN", "IMP", "VFY", "RLS")
DISPOSITIONS = frozenset({"required", "embedded", "n/a", "waived", "pending"})
REQ_TYPES = frozenset({"behavior", "rule", "quality", "constraint"})
SOURCE_TYPES = frozenset(
    {"text", "document", "conversation", "incident", "artifact", "other"}
)


class RequirementSemanticError(CanonicalFormatError):
    code = "REQ_SEMANTIC_INVALID"


def _rows(artifact: ParsedCanonicalArtifact, headers, name):
    return require_single_table(artifact, headers, name).rows


def _sequential(rows, prefix: str, *, allow_none: bool = False):
    if allow_none and len(rows) == 1 and rows[0]["ID"] == "None":
        return
    expected = tuple(f"{prefix}-{number:03d}" for number in range(1, len(rows) + 1))
    actual = tuple(row["ID"] for row in rows)
    if actual != expected:
        raise RequirementSemanticError(
            f"{prefix} IDs must be consecutive and stable; got {actual}"
        )


def _base_reference(value: str) -> str:
    base = value.split("#", 1)[0].split("/", 1)[0]
    if "@" not in base:
        raise RequirementSemanticError(f"Artifact Source is not an exact Reference: {value}")
    return base


def validate_persisted_requirement(artifact: ParsedCanonicalArtifact) -> None:
    front = artifact.front_matter
    if front.get("contract") != "sdlc-ai-spec/artifact/v1":
        raise RequirementSemanticError("REQ Contract is invalid")
    if front.get("phase") != "REQ":
        raise RequirementSemanticError("REQ Phase is invalid")
    context = front.get("context")
    if not isinstance(context, str) or not context.startswith("CTX-") or "@" not in context:
        raise RequirementSemanticError("REQ Context Reference is invalid")
    inputs = front.get("inputs")
    if not isinstance(inputs, list) or any(not isinstance(item, str) for item in inputs):
        raise RequirementSemanticError("REQ Front Matter inputs must be an array")
    if context in inputs:
        raise RequirementSemanticError("CTX belongs in context, not Front Matter inputs")
    if len(inputs) != len(set(inputs)):
        raise RequirementSemanticError("REQ Front Matter inputs contain duplicates")

    positions = []
    for heading in REQUIRED_HEADINGS:
        position = artifact.text.find(heading)
        if position < 0:
            raise RequirementSemanticError(f"REQ fixed heading is missing: {heading}")
        positions.append(position)
    if positions != sorted(positions):
        raise RequirementSemanticError("REQ fixed headings are out of order")

    sources = _rows(artifact, SOURCE_HEADERS, "Source Input")
    goals = _rows(artifact, GOAL_HEADERS, "Goal")
    affected = _rows(artifact, AFFECTED_HEADERS, "Affected Parties")
    requirements = _rows(artifact, REQUIREMENT_HEADERS, "Requirements")
    criteria = _rows(artifact, AC_HEADERS, "Acceptance Criteria")
    open_items = _rows(artifact, OPEN_ITEM_HEADERS, "Open Items")
    exceptions = _rows(artifact, EXCEPTION_HEADERS, "Exceptions")
    applicability = _rows(artifact, APPLICABILITY_HEADERS, "Lifecycle Applicability")

    _sequential(sources, "SRC", allow_none=True)
    _sequential(goals, "GOAL", allow_none=True)
    _sequential(affected, "AP", allow_none=True)
    _sequential(requirements, "R", allow_none=True)
    _sequential(criteria, "AC", allow_none=True)
    _sequential(open_items, "OPI", allow_none=True)
    _sequential(exceptions, "EX", allow_none=True)

    source_ids = {row["ID"] for row in sources if row["ID"] != "None"}
    goal_ids = {row["ID"] for row in goals if row["ID"] != "None"}
    affected_ids = {row["ID"] for row in affected if row["ID"] != "None"}
    req_ids = {row["ID"] for row in requirements if row["ID"] != "None"}
    roots = source_ids | goal_ids | affected_ids

    artifact_sources: set[str] = set()
    for row in sources:
        if row["ID"] == "None":
            continue
        if row["Type"] not in SOURCE_TYPES:
            raise RequirementSemanticError(f"Invalid Source Type: {row['Type']}")
        content = row["Content or Immutable Reference"].strip()
        if not content:
            raise RequirementSemanticError(f"Source {row['ID']} is empty")
        if row["Type"] == "artifact":
            artifact_sources.add(_base_reference(content))
            if row["Evidence Reference"] != "N/A":
                raise RequirementSemanticError(
                    f"Artifact Source {row['ID']} must use Evidence Reference=N/A"
                )
    if set(inputs) != artifact_sources:
        raise RequirementSemanticError(
            "Front Matter inputs and artifact Source rows are not a complete exact set"
        )

    graph: dict[str, tuple[str, ...]] = {}
    for row in requirements:
        if row["ID"] == "None":
            continue
        if row["类型 Type"] not in REQ_TYPES:
            raise RequirementSemanticError(f"Invalid Requirement Type: {row['类型 Type']}")
        if not row["需求描述 Requirement Statement"].strip():
            raise RequirementSemanticError(f"Requirement {row['ID']} is empty")
        refs = parse_reference_set(row["来源或父项引用 Source or Parent References"])
        if not refs or any(ref not in roots | req_ids for ref in refs):
            raise RequirementSemanticError(
                f"Requirement {row['ID']} has an invalid source graph"
            )
        graph[row["ID"]] = refs

    visiting: set[str] = set()
    proven: set[str] = set()

    def reaches_root(node: str) -> bool:
        if node in roots:
            return True
        if node in visiting:
            raise RequirementSemanticError("Requirement source graph contains a cycle")
        if node in proven:
            return True
        visiting.add(node)
        values = graph.get(node, ())
        result = bool(values) and all(reaches_root(value) for value in values)
        visiting.remove(node)
        if result:
            proven.add(node)
        return result

    if req_ids and not all(reaches_root(item) for item in req_ids):
        raise RequirementSemanticError("Requirement source graph is not rooted")

    covered: set[str] = set()
    for row in criteria:
        if row["ID"] == "None":
            continue
        refs = parse_reference_set(row["关联需求 Requirement References"])
        if not refs or any(ref not in req_ids for ref in refs):
            raise RequirementSemanticError(
                f"Acceptance Criterion {row['ID']} has invalid Requirement References"
            )
        if not row["条件 Condition"].strip() or not row["预期结果 Expected Result"].strip():
            raise RequirementSemanticError(f"Acceptance Criterion {row['ID']} is incomplete")
        covered.update(refs)
    if req_ids - covered:
        raise RequirementSemanticError(
            "Acceptance Criteria do not cover: " + ", ".join(sorted(req_ids - covered))
        )

    phases = tuple(row["Phase"] for row in applicability)
    if phases != LIFECYCLE_PHASES:
        raise RequirementSemanticError("Lifecycle Applicability Phase order is invalid")
    for row in applicability:
        if row["Disposition"] not in DISPOSITIONS or not row["判断依据 Basis"].strip():
            raise RequirementSemanticError("Lifecycle Applicability row is invalid")
    if next(row for row in applicability if row["Phase"] == "VFY")["Disposition"] != "required":
        raise RequirementSemanticError("REQ VFY Disposition must be required")

    open_refs = [row for row in open_items if row["ID"] != "None" and row["状态 State"] == "open"]
    active = [row["ID"] for row in exceptions if row["ID"] != "None" and row["State"] in {"active", "carried"}]
    status = front.get("status")
    confirmation = require_single_row(
        require_single_table(artifact, FINAL_CONFIRMATION_HEADERS, "Final Confirmation"),
        "Final Confirmation",
    )
    summary = require_single_row(
        require_single_table(artifact, GATE_SUMMARY_HEADERS, "Gate Summary"),
        "Gate Summary",
    )
    accepted = parse_reference_set(confirmation["Accepted Exception References"])
    summarized = parse_reference_set(summary["Exception References"])
    artifact_id = str(front.get("id"))
    revision = front.get("revision")
    expected_exceptions = tuple(f"{artifact_id}@{revision}#{item}" for item in active)
    if accepted != expected_exceptions or summarized != expected_exceptions:
        raise RequirementSemanticError(
            "Exception rows, Final Confirmation and Gate Summary are inconsistent"
        )

    gate_result = summary["Gate Result"]
    if status == "ready" and (gate_result != "pass" or open_refs or active):
        raise RequirementSemanticError("ready REQ has inconsistent Gate/Open Item/Exception state")
    if status == "ready_with_exception" and (
        gate_result != "pass_with_exception" or open_refs or not active
    ):
        raise RequirementSemanticError(
            "ready_with_exception REQ has inconsistent control state"
        )
    if status == "waiting_input" and (gate_result != "pending" or not open_refs):
        raise RequirementSemanticError("waiting_input REQ must have pending Gate and open items")
    if status == "failed" and gate_result != "fail":
        raise RequirementSemanticError("failed REQ must have fail Gate")
    if status == "draft" and gate_result != "pending":
        raise RequirementSemanticError("draft REQ must have pending Gate")

    check_tables = find_tables(artifact, CHECK_HEADERS)
    check_ids = [row["Check ID"] for table in check_tables for row in table.rows]
    required_checks = {f"CORE-G-{number:03d}" for number in range(1, 10)} | {
        f"REQ-G-{number:03d}" for number in range(1, 9)
    }
    if set(check_ids) != required_checks or len(check_ids) != len(required_checks):
        raise RequirementSemanticError("REQ Check Set is incomplete or duplicated")
