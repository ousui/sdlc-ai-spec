"""Exact v1.1 VFY primary renderer and semantic primary/state validator."""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from packages.sdlc_phasekit import table
from packages.sdlc_runtime import parse_canonical_artifact
from packages.sdlc_runtime.canonical import require_single_table

from vfy_common import VfyError, require

INPUT_HEADERS = (
    "ID",
    "角色 Role",
    "引用 Reference",
    "纳入范围 Included Scope",
    "选择依据 Selection Basis",
)
TARGET_HEADERS = (
    "目标引用 Target Reference",
    "目标摘要 Target Summary",
    "Purpose",
    "Conclusion",
    "依据引用 Basis References",
    "Exception Reference",
)
METHOD_HEADERS = (
    "ID",
    "Purpose",
    "Target References",
    "Subject References",
    "义务引用 Obligation References",
    "Method Type",
    "Disposition",
    "依据或原因 Basis Reference or Reason",
)
RESULT_HEADERS = (
    "Method ID",
    "Result",
    "实际结果 Actual Result",
    "依据引用 Basis References",
    "Return References",
)
CONCLUSION_HEADERS = (
    "ID",
    "Dimension",
    "Conclusion",
    "Target References",
    "Basis References",
    "Exception References",
)
RETURN_HEADERS = (
    "ID",
    "Return Phase",
    "IMP Binding Reference",
    "Target References",
    "Method References",
    "Subject References",
    "已观察缺口 Observed Gap",
    "必须达到的结果 Required Outcome",
    "Evidence References",
)
REQUIRED_SECTION_HEADINGS = (
    "## 摘要 Summary",
    "## 范围 Scope",
    "## 输入与结果集 Input and Result Set",
    "## 追踪与覆盖 Traceability and Coverage",
    "## VFY 方法 VFY Methods",
    "## 方法结果 Method Results",
    "## VFY 结论 VFY Conclusions",
    "## 失败与返回 Failures and Returns",
    "## 待确认项 Open Items",
    "## 证据 Evidence",
    "## Supporting Artifact Manifest",
    "## 豁免 Exceptions",
    "## 生命周期适用性 Lifecycle Applicability",
    "## 门禁 Gate",
)


def _cell(value: Any, *, empty: str = "None") -> str:
    if value is None:
        return empty
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value) or empty
    text = " ".join(str(value).splitlines()).strip()
    return text or empty


def owner_artifact_inputs(state: Mapping[str, Any]) -> tuple[str, ...]:
    """Return every direct owner Revision referenced by the primary objects."""

    values = {
        str(state["scope"]["reference"]),
        *(str(item["imp_revision_reference"]) for item in state["subjects"]),
    }
    values.update(str(item) for item in state.get("owner_artifact_inputs", []))
    for collection, keys in (
        (state.get("targets", []), ("reference", "obligation_references")),
        (state.get("methods", []), ("target_references", "obligation_references")),
        (state.get("returns", []), ("target_references", "evidence_references")),
    ):
        for item in collection:
            for key in keys:
                raw = item.get(key, []) if isinstance(item, Mapping) else []
                refs = raw if isinstance(raw, list) else [raw]
                for reference in refs:
                    text = str(reference)
                    if "@" in text:
                        values.add(text.split("#", 1)[0].split("/", 1)[0])
    for reference in state.get("control_inputs", []):
        values.add(str(reference).split("#", 1)[0])
    for item in state.get("exceptions", []):
        values.add(str(item["origin_reference"]).split("#", 1)[0])
    return tuple(sorted(item for item in values if item and "@" in item))


def input_rows(state: Mapping[str, Any]) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = [
        (
            "VIN-001",
            "scope_source",
            str(state["scope"]["reference"]),
            _cell(state["scope"]["delivery_scope"]),
            "Current complete authoritative Delivery Scope",
        )
    ]
    for index, subject in enumerate(state["subjects"], 2):
        rows.append(
            (
                f"VIN-{index:03d}",
                "subject",
                str(subject["reference"]),
                _cell(
                    [
                        f"resource:{subject['resource_id']}",
                        *subject.get("cumulative_changed_scope", []),
                    ]
                ),
                (
                    f"Current completed Claim {subject['binding_lineage']} "
                    f"Attempt {subject['attempt']}; Result Digest {subject['result_digest']}"
                ),
            )
        )
    return rows


def target_rows(state: Mapping[str, Any]) -> list[tuple[str, ...]]:
    contracts = {str(item["reference"]): item for item in state["targets"]}
    rows = []
    for conclusion in state["target_conclusions"]:
        reference = str(conclusion["target_reference"])
        contract = contracts[reference]
        rows.append(
            (
                reference,
                str(contract["summary"]),
                str(conclusion["purpose"]),
                str(conclusion["conclusion"]),
                _cell(conclusion.get("basis_references")),
                _cell(conclusion.get("exception_reference")),
            )
        )
    return rows


def method_rows(state: Mapping[str, Any]) -> list[tuple[str, ...]]:
    rows = []
    for method in state["methods"]:
        basis = method.get("exception_reference") or method.get("n_a_basis") or "Frozen Method Detail below"
        rows.append(
            (
                str(method["id"]),
                str(method["purpose"]),
                _cell(method["target_references"]),
                _cell(method["subject_references"]),
                _cell(method["obligation_references"]),
                str(method["method_type"]),
                str(method["disposition"]),
                str(basis),
            )
        )
    return rows


def method_details(state: Mapping[str, Any]) -> str:
    blocks = []
    for method in state["methods"]:
        if method["disposition"] not in {"required", "embedded", "waived"}:
            continue
        blocks.append(
            "\n".join(
                (
                    f"### {method['id']} {method.get('title') or method['id']}",
                    "",
                    f"- Executor Identity: {_cell(method.get('executor_identity'), empty='N/A')}",
                    (
                        "- Method Detail: "
                        f"Type={method['method_type']}; "
                        f"Execution Mode={method['execution_mode']}; "
                        "Environment/Data=" + json.dumps(
                            method.get("environment") or {"project_root": "."},
                            ensure_ascii=False, sort_keys=True,
                        )
                    ),
                    "- Procedure or Basis: "
                    + json.dumps(method.get("procedure") or {}, ensure_ascii=False, sort_keys=True),
                    f"- Pass Criteria or References: {_cell(method.get('pass_criteria'), empty='N/A')}",
                    f"- Evidence Requirement: {_cell(method.get('evidence_requirement'), empty='N/A')}",
                )
            )
        )
    return "\n\n".join(blocks)


def result_rows(state: Mapping[str, Any]) -> list[tuple[str, ...]]:
    return [
        (
            str(item["method_id"]),
            str(item["result"]),
            str(item["actual_result"]),
            _cell(item.get("evidence_references")),
            _cell(item.get("return_references")),
        )
        for item in state["method_results"]
    ]


def conclusion_rows(state: Mapping[str, Any]) -> list[tuple[str, ...]]:
    return [
        (
            str(item["id"]),
            str(item["dimension"]),
            str(item["conclusion"]),
            _cell(item.get("target_references")),
            _cell(item.get("basis_references")),
            _cell(item.get("exception_references")),
        )
        for item in state["fixed_conclusions"]
    ]


def return_rows(state: Mapping[str, Any]) -> list[tuple[str, ...]]:
    if not state["returns"]:
        return [
            (
                "None",
                "N/A",
                "N/A",
                "None",
                "None",
                "None",
                "No upstream Return required",
                "N/A",
                "None",
            )
        ]
    return [
        (
            str(item["id"]),
            str(item["return_phase"]),
            str(item["imp_binding_reference"]),
            _cell(item["target_references"]),
            _cell(item["method_references"]),
            _cell(item["subject_references"]),
            str(item["observed_gap"]),
            str(item["required_outcome"]),
            _cell(item["evidence_references"]),
        )
        for item in state["returns"]
    ]


def sections(state: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    method_body = table(METHOD_HEADERS, method_rows(state))
    details = method_details(state)
    if details:
        method_body += "\n\n" + details
    return (
        (
            "## 摘要 Summary",
            f"- VFY: `{state['artifact']['reference']}`\n"
            f"- Product Result: `{state['product_result']}`\n"
            f"- Artifact Gate: `{state['artifact_gate']}`\n"
            f"- RLS ready: `{'yes' if state['rls_ready'] else 'no'}`",
        ),
        (
            "## 范围 Scope",
            f"- Scope Reference: `{state['scope']['reference']}`\n"
            f"- Delivery Scope: {_cell(state['scope']['delivery_scope'])}",
        ),
        ("## 输入与结果集 Input and Result Set", table(INPUT_HEADERS, input_rows(state))),
        ("## 追踪与覆盖 Traceability and Coverage", table(TARGET_HEADERS, target_rows(state))),
        ("## VFY 方法 VFY Methods", method_body),
        ("## 方法结果 Method Results", table(RESULT_HEADERS, result_rows(state))),
        ("## VFY 结论 VFY Conclusions", table(CONCLUSION_HEADERS, conclusion_rows(state))),
        ("## 失败与返回 Failures and Returns", table(RETURN_HEADERS, return_rows(state))),
    )


def _actual_rows(parsed: Any, headers: Sequence[str], name: str) -> list[tuple[str, ...]]:
    current = require_single_table(parsed, headers, name)
    return [tuple(str(row[key]) for key in headers) for row in current.rows]


def validate_primary_against_state(
    raw: bytes,
    state: Mapping[str, Any],
    *,
    member_ids: Sequence[str],
    members: Sequence[Any] | None = None,
) -> None:
    """Prove canonical primary, VFY-STATE and Manifest object equality."""

    try:
        parsed = parse_canonical_artifact(raw)
        require(
            parsed.front_matter.get("phase") == "VFY"
            and parsed.front_matter.get("id") == state["artifact"]["id"]
            and parsed.front_matter.get("revision") == state["artifact"]["revision"]
            and parsed.front_matter.get("status") == state["artifact"]["artifact_status"]
            and parsed.front_matter.get("context") == state["context_reference"],
            "VFY_CANONICAL_MISMATCH",
            "Canonical Front Matter differs from VFY-STATE",
        )
        require(
            tuple(parsed.front_matter.get("inputs") or ()) == owner_artifact_inputs(state),
            "VFY_CANONICAL_MISMATCH",
            "Canonical Front Matter does not register every exact owner Revision",
            details={
                "expected": list(owner_artifact_inputs(state)),
                "actual": list(parsed.front_matter.get("inputs") or ()),
            },
        )
        for heading in REQUIRED_SECTION_HEADINGS:
            require(
                len(re.findall(rf"(?m)^{re.escape(heading)}$", parsed.text)) == 1,
                "VFY_CANONICAL_MISMATCH",
                "Canonical VFY section heading is missing or duplicated",
                details={"heading": heading},
            )
        expected_tables = (
            (INPUT_HEADERS, input_rows(state), "VFY Input and Result Set"),
            (TARGET_HEADERS, target_rows(state), "VFY Target Set"),
            (METHOD_HEADERS, method_rows(state), "VFY Method Index"),
            (RESULT_HEADERS, result_rows(state), "VFY Method Results"),
            (CONCLUSION_HEADERS, conclusion_rows(state), "VFY Conclusions"),
            (RETURN_HEADERS, return_rows(state), "VFY Returns"),
        )
        for headers, expected, name in expected_tables:
            require(
                _actual_rows(parsed, headers, name) == [tuple(map(str, row)) for row in expected],
                "VFY_CANONICAL_MISMATCH",
                f"Canonical {name} differs from VFY-STATE",
            )
        for method in state["methods"]:
            if method["disposition"] not in {"required", "embedded", "waived"}:
                continue
            heading = rf"(?m)^### {re.escape(str(method['id']))} "
            require(
                len(re.findall(heading, parsed.text)) == 1,
                "VFY_CANONICAL_MISMATCH",
                "Required Method Detail must occur exactly once",
                details={"method_id": method["id"]},
            )
        expected_members = {"VFY-STATE"} | {
            f"VFY-EVIDENCE-{index:03d}"
            for index, _ in enumerate(state.get("evidence", []), 1)
        }
        require(
            set(member_ids) == expected_members and len(member_ids) == len(expected_members),
            "VFY_CANONICAL_MISMATCH",
            "Supporting Manifest differs from VFY-STATE Evidence closure",
            details={"expected": sorted(expected_members), "actual": sorted(member_ids)},
        )
        # Lazy import avoids the renderer/compiler module dependency cycle.
        from vfy_builder import canonical_members, render_markdown
        canonical = canonical_members(state)
        actual_members = canonical if members is None else members
        expected_evidence = {item.member_id: item.raw_bytes for item in canonical
                             if item.member_id != "VFY-STATE"}
        require(all(item.raw_bytes == expected_evidence[item.member_id]
                    for item in actual_members if item.member_id != "VFY-STATE"),
                "VFY_CANONICAL_MISMATCH", "Evidence Supporting Member differs from VFY-STATE")
        require(raw == render_markdown(state, members=actual_members).encode("utf-8"),
                "VFY_CANONICAL_MISMATCH",
                "Primary Detail, Evidence, Exception, Gate or Manifest differs from VFY-STATE")
    except VfyError:
        raise
    except Exception as exc:
        raise VfyError(
            "VFY_CANONICAL_MISMATCH",
            f"Canonical VFY primary validation failed: {exc}",
        ) from exc
