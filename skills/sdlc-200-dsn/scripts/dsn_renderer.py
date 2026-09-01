"""Deterministic primary DSN Markdown renderer."""

from dsn_common import *


class DsnRenderer:
    @staticmethod
    def render(
        *,
        artifact_id: str,
        revision: int,
        status: str,
        upstream: UpstreamScope,
        analysis: DsnAnalysis,
        checks: Mapping[str, CheckOutcome],
        open_items: Sequence[Mapping[str, str]],
        members: Sequence[CanonicalMember],
        final_confirmation: Mapping[str, Any] | None,
        gate_result: str,
    ) -> bytes:
        design = analysis.normalized
        all_inputs = tuple(
            dict.fromkeys(
                (*upstream.scope_references, *(
                    f"{exact_artifact_reference(item)[0]}@{exact_artifact_reference(item)[1]}"
                    for item in upstream.control_references
                ))
            )
        )
        front = [
            "---",
            f"contract: {DSN_CONTRACT}",
            f"phase: {DSN_PHASE}",
            f"id: {artifact_id}",
            f"revision: {revision}",
            f"status: {status}",
            f"context: {upstream.context_reference}",
            f"profile: {design.get('profile', 'full')}",
            "inputs:",
            *(f"  - {item}" for item in all_inputs),
            "---",
        ]
        change_rows = []
        for index, item in enumerate(design["changes"], start=1):
            change_rows.append(
                (
                    item.get("id") or f"CHG-{index:03d}",
                    item.get("object_or_boundary"),
                    item.get("change"),
                    ", ".join(_refs(item.get("baseline_references"), "change baseline")) or "N/A",
                    item.get("baseline_state") or "N/A",
                    item.get("target_state"),
                    ", ".join(item.get("affected_domains", [])),
                )
            )
        trace_rows = []
        for item in design["traceability"]:
            trace_rows.append(
                (
                    ", ".join(_refs(item.get("source_references"), "trace sources")),
                    ", ".join(_refs(item.get("design_references"), "trace design")) or "N/A",
                    ", ".join(_refs(item.get("decision_references"), "trace decisions")) or "None",
                    ", ".join(_refs(item.get("vfy_references"), "trace vfy")) or "N/A",
                    item.get("na_reason") or "N/A",
                )
            )
        decision_rows = []
        for index, item in enumerate(design["decisions"], start=1):
            decision_rows.append(
                (
                    item.get("id") or f"DEC-{index:03d}",
                    ", ".join(_refs(item.get("requirement_references"), "decision refs")),
                    item.get("question"),
                    item.get("options"),
                    item.get("decision"),
                    item.get("rationale"),
                    ", ".join(item.get("affected_domains", [])),
                )
            )
        if not decision_rows:
            decision_rows = (
                (
                    "None",
                    "N/A",
                    design.get("decision_none_reason") or "No design decision required",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                ),
            )

        matrix_rows = []
        member_by_id = {item.member_id: item for item in members}
        for row in analysis.domain_rows:
            definition = row["definition"]
            content_ref = (
                f"{artifact_id}@{revision}/{definition.code}"
                if definition.code in member_by_id
                else "N/A"
            )
            matrix_rows.append(
                (
                    definition.group,
                    definition.display_name,
                    row["disposition"],
                    row["completion"],
                    row["responsible_role"] or "N/A",
                    content_ref,
                    ", ".join(row["basis_references"]) or "None",
                    row["reason"] or "N/A",
                )
            )

        manifest_rows = []
        for member in sorted(members, key=lambda item: item.member_id):
            domain = DOMAIN_BY_CODE.get(member.member_id)
            manifest_rows.append(
                (
                    member.member_id,
                    "domain" if domain else "supporting",
                    domain.display_name if domain else "Multiple",
                    (
                        _spec_reference("200-dsn-domains/" + domain.filename)
                        if domain
                        else "N/A"
                    ),
                    member.canonical_name,
                    member.media_type,
                    "Domain Design" if domain else "Supporting Artifact",
                    member.sha256,
                    "N/A",
                )
            )
        if not manifest_rows:
            manifest_rows = (
                ("None", "N/A", "N/A", "N/A", "N/A", "N/A", "No members", "N/A", "No members"),
            )

        evidence_rows = []
        for index, item in enumerate(design["evidence"], start=1):
            evidence_rows.append(
                (
                    item.get("id") or f"EVD-{index:03d}",
                    item.get("type") or "artifact",
                    ", ".join(_refs(item.get("supports_references"), "evidence supports")),
                    item.get("source") or "Runtime",
                    item.get("reference"),
                    item.get("digest") or "N/A",
                    item.get("produced_at") or "N/A",
                    item.get("sensitivity") or "internal",
                    "N/A",
                )
            )
        if not evidence_rows:
            evidence_rows = (
                ("None", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "No Evidence supplied"),
            )

        exception_rows = []
        for index, item in enumerate(design["exceptions"], start=1):
            exception_rows.append(
                (
                    item.get("id") or f"EX-{index:03d}",
                    item.get("state"),
                    item.get("origin_reference") or "N/A",
                    item.get("scope"),
                    item.get("reason"),
                    item.get("known_risk"),
                    item.get("compensating_control"),
                    item.get("approval"),
                    item.get("revisit_condition"),
                    item.get("downstream_obligation"),
                    item.get("resolution_reference") or "N/A",
                )
            )
        if not exception_rows:
            exception_rows = (
                ("None", "N/A", "N/A", "N/A", "No exceptions", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"),
            )

        applicability_rows = [
            (
                item.get("phase"),
                item.get("disposition"),
                item.get("host") or "N/A",
                item.get("basis"),
            )
            for item in design["lifecycle_applicability"]
        ]
        check_rows = [
            (check_id, check_id, outcome.result, outcome.note)
            for check_id, outcome in sorted(checks.items())
        ]

        lines = [
            *front,
            f"# {design['title']}",
            "",
            "## 摘要 Summary",
            "",
            design["summary"],
            "",
            "## 范围 Scope",
            "",
            _table(
                ("Scope Item", "Value"),
                (
                    ("Design Boundary", design["boundary"]),
                    ("Requirement Scope Inputs", ", ".join(upstream.scope_references)),
                    ("Control Inputs", ", ".join(upstream.control_references) or "None"),
                ),
            ),
            "",
            "## 设计基线与变更 Design Baseline and Change",
            "",
            _table(
                BASELINE_HEADERS,
                (
                    (
                        design["change_type"],
                        ", ".join(design["baseline_references"]) or "N/A",
                        design["target_state_summary"],
                        design["impact_summary"] or "N/A",
                    ),
                ),
            ),
            "",
            _table(CHANGE_HEADERS, change_rows),
            "",
            "## 需求追踪 Requirement Traceability",
            "",
            _table(TRACE_HEADERS, trace_rows),
            "",
            "## 设计决策 Design Decisions",
            "",
            _table(DECISION_HEADERS, decision_rows),
            "",
            "## 设计总纲 Design Index",
            "",
            _table(MATRIX_HEADERS, matrix_rows),
            "",
            "### 复合 Domain 子领域适用性 Composite Domain Subdomain Applicability",
            "",
            _table(
                COMPOSITE_HEADERS,
                [
                    (
                        row["domain_code"],
                        row["subdomain"],
                        row["disposition"],
                        row["basis_references"],
                        row["reason"],
                        row["exception_references"],
                    )
                    for row in analysis.composite_rows
                ],
            ),
            "",
            "## 产物集清单 Artifact Set Manifest",
            "",
            _table(MANIFEST_HEADERS, manifest_rows),
            "",
            "## 待确认项 Open Items",
            "",
            _table(
                OPEN_ITEM_HEADERS,
                [
                    (
                        item["id"],
                        item["needed"],
                        item["expected_source"],
                        item["blocked_references"],
                        item["state"],
                        item["resolution"],
                    )
                    for item in open_items
                ]
                or (("None", "No open items", "N/A", "N/A", "none", "N/A"),),
            ),
            "",
            "## 证据 Evidence",
            "",
            _table(EVIDENCE_HEADERS, evidence_rows),
            "",
            "## 豁免 Exceptions",
            "",
            _table(EXCEPTION_HEADERS, exception_rows),
            "",
            "## 生命周期适用性 Lifecycle Applicability",
            "",
            _table(APPLICABILITY_HEADERS, applicability_rows),
            "",
            "## 门禁 Gate",
            "",
            _table(CHECK_HEADERS, check_rows),
            "",
        ]
        pre_confirmation = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
        control_digest = compute_control_input_digest(pre_confirmation)
        check_digest = "N/A"
        if not any(item[2] == "pending" for item in check_rows):
            try:
                check_digest = compute_check_set_result_digest(
                    parse_canonical_artifact(pre_confirmation)
                )
            except CanonicalFormatError:
                check_digest = "N/A"
        accepted = (
            ", ".join(
                f"{artifact_id}@{revision}#{item}"
                for item in analysis.active_exceptions
            )
            or "None"
        )
        if final_confirmation is None:
            confirmation_row = (
                revision,
                control_digest,
                _evaluation_contract_set(),
                check_digest,
                "pending",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                accepted,
                "N/A",
            )
        else:
            confirmation_row = (
                revision,
                control_digest,
                _evaluation_contract_set(),
                check_digest,
                "approved",
                final_confirmation["mode"],
                final_confirmation["confirmer"],
                final_confirmation["role"],
                final_confirmation["authority_reference"],
                accepted,
                final_confirmation["confirmed_at"],
            )
        lines.extend(
            [
                _table(FINAL_CONFIRMATION_HEADERS, (confirmation_row,)),
                "",
                _table(
                    GATE_SUMMARY_HEADERS,
                    (
                        (
                            revision,
                            control_digest,
                            _evaluation_contract_set(),
                            check_digest,
                            gate_result,
                            accepted,
                            "sdlc-200-dsn",
                            _iso(),
                        ),
                    ),
                ),
                "",
            ]
        )
        return "\n".join(lines).encode("utf-8")


__all__ = ("DsnRenderer",)
