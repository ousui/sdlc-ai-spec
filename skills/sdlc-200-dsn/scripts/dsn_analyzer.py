"""DSN design analysis and Gate input normalization."""

from dsn_common import *


class DsnAnalyzer:
    def analyze(
        self,
        design: Mapping[str, Any],
        upstream: UpstreamScope,
    ) -> DsnAnalysis:
        normalized = deepcopy(dict(design))
        checks: dict[str, CheckOutcome] = {}
        open_items: list[dict[str, str]] = []

        title = design.get("title")
        summary = design.get("summary")
        boundary = design.get("boundary")
        if not isinstance(boundary, str) or not boundary.strip():
            raise DsnRuntimeError(
                "Design Boundary must be confirmed before DSN allocation"
            )
        normalized["boundary"] = boundary.strip()
        if not isinstance(title, str) or not title.strip():
            title = "Pending Design Title"
            open_items.append(self._open("需要设计标题", "Design Authority", "DSN-G-004"))
        if not isinstance(summary, str) or not summary.strip():
            summary = "Pending — design summary required"
            open_items.append(self._open("需要设计摘要", "Design Authority", "DSN-G-004"))
        normalized["title"] = str(title).strip()
        normalized["summary"] = str(summary).strip()

        change_type = design.get("change_type")
        baseline_refs = _refs(design.get("baseline_references"), "baseline_references")
        target_summary = design.get("target_state_summary")
        impact_summary = design.get("impact_summary")
        changes = _rows(design.get("changes"), "changes")
        if change_type not in CHANGE_TYPES:
            checks["DSN-G-002"] = CheckOutcome("fail", "Change Type 无效")
        elif change_type in {"incremental", "reuse"} and not baseline_refs:
            checks["DSN-G-002"] = CheckOutcome(
                "fail", "incremental/reuse 必须引用准确 Baseline"
            )
        elif not isinstance(target_summary, str) or not target_summary.strip():
            open_items.append(
                self._open("需要 Target State Summary", "Design Authority", "DSN-G-002")
            )
            checks["DSN-G-002"] = CheckOutcome("pending", "Target State 未闭合")
        elif not changes:
            open_items.append(
                self._open("需要至少一个 Change Item", "Design Authority", "DSN-G-002")
            )
            checks["DSN-G-002"] = CheckOutcome("pending", "Change Set 尚未提供")
        else:
            invalid_change = any(
                item.get("change") not in CHANGE_VALUES
                or not isinstance(item.get("object_or_boundary"), str)
                or not item.get("object_or_boundary", "").strip()
                or not isinstance(item.get("target_state"), str)
                or not item.get("target_state", "").strip()
                or any(code not in DOMAIN_BY_CODE for code in item.get("affected_domains", []))
                for item in changes
            )
            checks["DSN-G-002"] = CheckOutcome(
                "fail" if invalid_change else "pass",
                "Change Set 字段或 Domain 分类无效"
                if invalid_change
                else "Scope、Baseline、Change 与 Target State 完整",
            )
        normalized.update(
            {
                "change_type": change_type,
                "baseline_references": list(baseline_refs),
                "target_state_summary": str(target_summary or "").strip(),
                "impact_summary": str(impact_summary or "").strip(),
                "changes": changes,
            }
        )

        decisions = _rows(design.get("decisions"), "decisions")
        if not decisions and not str(design.get("decision_none_reason") or "").strip():
            open_items.append(
                self._open(
                    "确认不存在需要记录的 Design Decision，或提供决策",
                    "Design Authority",
                    "DSN-G-004",
                )
            )
        invalid_decision = any(
            not isinstance(item.get("question"), str)
            or not item.get("question", "").strip()
            or not item.get("options")
            or not isinstance(item.get("decision"), str)
            or not item.get("decision", "").strip()
            or not isinstance(item.get("rationale"), str)
            or not item.get("rationale", "").strip()
            or any(code not in DOMAIN_BY_CODE for code in item.get("affected_domains", []))
            for item in decisions
        )
        normalized["decisions"] = decisions
        checks["DSN-G-004"] = CheckOutcome(
            "fail" if invalid_decision else ("pending" if any(
                item["blocked_references"] == "DSN-G-004" for item in open_items
            ) else "pass"),
            "Design Decision 不完整"
            if invalid_decision
            else "Summary、Decision 与 Design Index 可保持单一权威",
        )

        try:
            domain_rows = list(normalize_domain_rows(design.get("domains", {})))
            composite_rows = normalize_composite_rows(
                design.get("composite_subdomains")
            )
        except DomainContractError as exc:
            raise DsnRuntimeError(str(exc)) from exc

        for row in domain_rows:
            if row["disposition"] == "pending":
                open_items.append(
                    self._open(
                        f"确认 {row['definition'].display_name} 的适用性",
                        row["responsible_role"] or "Design Authority",
                        "DSN-G-005",
                    )
                )
                row["reason"] = f"Pending — OPI-{len(open_items):03d}"
            if row["disposition"] == "required" and row["completion"] != "complete":
                open_items.append(
                    self._open(
                        f"完成 {row['definition'].display_name} Domain 设计",
                        row["responsible_role"] or "Design Authority",
                        "DSN-G-006",
                    )
                )
        composite_list = list(composite_rows)
        for row in composite_list:
            if row["disposition"] == "pending":
                open_items.append(
                    self._open(
                        f"确认 {row['subdomain']} 的适用性",
                        "Design Authority",
                        "DSN-G-007",
                    )
                )
                row["reason"] = f"Pending — OPI-{len(open_items):03d}"

        domain_by_code = {row["code"]: row for row in domain_rows}
        composite_ok = True
        for code in ("DOM-140", "DOM-310"):
            if domain_by_code[code]["disposition"] != aggregate_composite_disposition(
                composite_list, code
            ):
                composite_ok = False
        checks["DSN-G-007"] = CheckOutcome(
            "pass" if composite_ok else "fail",
            "Composite Domain 与父 Matrix 一致"
            if composite_ok
            else "Composite Domain 聚合与父 Matrix 不一致",
        )
        pending_domains = [
            row["code"] for row in domain_rows if row["disposition"] == "pending"
        ]
        checks["DSN-G-005"] = CheckOutcome(
            "pending" if pending_domains else "pass",
            "Domain 适用性仍有 pending"
            if pending_domains
            else "16 个 Domain 均已完成适用性判断",
        )

        exceptions = _rows(design.get("exceptions"), "exceptions")
        active_exceptions: list[str] = []
        exception_invalid = False
        for index, item in enumerate(exceptions, start=1):
            state = item.get("state")
            if state not in EXCEPTION_STATES:
                exception_invalid = True
                continue
            exception_id = str(item.get("id") or f"EX-{index:03d}")
            if state in {"active", "carried"}:
                for field in (
                    "scope",
                    "reason",
                    "known_risk",
                    "compensating_control",
                    "approval",
                    "revisit_condition",
                    "downstream_obligation",
                ):
                    if not isinstance(item.get(field), str) or not item.get(field, "").strip():
                        exception_invalid = True
                active_exceptions.append(exception_id)
        normalized["exceptions"] = exceptions

        traceability = _rows(design.get("traceability"), "traceability")
        covered_req: set[str] = set()
        covered_ac: set[str] = set()
        trace_invalid = False
        known_upstream = set(upstream.requirement_items) | set(upstream.acceptance_items)
        for item in traceability:
            sources = _refs(item.get("source_references"), "traceability sources", required=True)
            if any(source not in known_upstream for source in sources):
                trace_invalid = True
            covered_req.update(source for source in sources if "#R-" in source)
            covered_ac.update(source for source in sources if "#AC-" in source)
            design_refs = _refs(item.get("design_references"), "design references")
            vfy_refs = _refs(item.get("vfy_references"), "vfy references")
            na_reason = str(item.get("na_reason") or "").strip()
            if not design_refs and not na_reason:
                trace_invalid = True
            if any("#AC-" in source for source in sources) and not vfy_refs:
                trace_invalid = True
        if set(upstream.requirement_items) - covered_req:
            trace_invalid = True
        if set(upstream.acceptance_items) - covered_ac:
            trace_invalid = True
        checks["DSN-G-003"] = CheckOutcome(
            "fail" if trace_invalid else "pass",
            "Requirement / AC Traceability 不完整"
            if trace_invalid
            else "REQ、AC、Design 与 VFY 双向追踪完整",
        )
        normalized["traceability"] = traceability

        conflicts = _rows(design.get("cross_domain_conflicts"), "cross_domain_conflicts")
        unresolved_conflicts = [
            item for item in conflicts if item.get("state", "open") != "resolved"
        ]
        if unresolved_conflicts:
            checks["DSN-G-008"] = CheckOutcome("fail", "存在未解决的跨 Domain 冲突")
        else:
            checks["DSN-G-008"] = CheckOutcome("pass", "不存在未解决的跨 Domain 冲突")
        normalized["cross_domain_conflicts"] = conflicts

        scope_expansion = design.get("scope_expansion", False)
        simplicity = str(design.get("simplicity_rationale") or "").strip()
        if scope_expansion is True or not simplicity:
            checks["DSN-G-009"] = CheckOutcome(
                "fail", "存在未授权范围扩张或缺少复杂度必要性说明"
            )
        else:
            checks["DSN-G-009"] = CheckOutcome(
                "pass", "设计保持最小充分且复杂度有依据"
            )
        normalized["scope_expansion"] = bool(scope_expansion)
        normalized["simplicity_rationale"] = simplicity

        applicability = _rows(
            design.get("lifecycle_applicability"), "lifecycle_applicability"
        )
        app_pending = False
        app_invalid = False
        if tuple(item.get("phase") for item in applicability) != LIFECYCLE_PHASES:
            app_invalid = True
        for item in applicability:
            if item.get("disposition") not in DISPOSITIONS:
                app_invalid = True
            if not isinstance(item.get("basis"), str) or not item.get("basis", "").strip():
                app_invalid = True
            if item.get("disposition") == "pending":
                app_pending = True
        vfy = next((item for item in applicability if item.get("phase") == "VFY"), None)
        if vfy is None or vfy.get("disposition") != "required":
            app_invalid = True
        checks["DSN-G-010"] = CheckOutcome(
            "fail" if app_invalid else ("pending" if app_pending else "pass"),
            "Lifecycle Applicability 无效"
            if app_invalid
            else ("Lifecycle Applicability 存在 pending" if app_pending else "Lifecycle Applicability 完整"),
        )
        if app_pending:
            open_items.append(
                self._open(
                    "确认后续 Phase Applicability",
                    "Maintainer",
                    "DSN-G-010",
                )
            )
        normalized["lifecycle_applicability"] = applicability

        evidence = _rows(design.get("evidence"), "evidence")
        invalid_evidence = any(
            not isinstance(item.get("reference"), str)
            or not item.get("reference", "").strip()
            or not item.get("supports_references")
            for item in evidence
        )
        normalized["evidence"] = evidence
        normalized["supporting_members"] = _rows(
            design.get("supporting_members"), "supporting_members"
        )
        normalized["open_items"] = _rows(design.get("open_items"), "open_items")
        for item in normalized["open_items"]:
            if item.get("state", "open") == "open":
                open_items.append(
                    self._open(
                        _text(item.get("needed"), "open item needed"),
                        str(item.get("expected_source") or "Design Authority"),
                        str(item.get("blocked_references") or "DSN-G-001"),
                        state="open",
                        resolution=str(item.get("resolution") or "N/A"),
                    )
                )

        checks["DSN-G-001"] = CheckOutcome(
            "pass",
            "至少一个准确 frozen REQ 与适用 Control Input 已解析",
        )
        checks["DSN-G-006"] = CheckOutcome(
            "pending"
            if any(
                row["disposition"] == "required" and row["completion"] != "complete"
                for row in domain_rows
            )
            else "pass",
            "required Domain 尚未全部完成"
            if any(
                row["disposition"] == "required" and row["completion"] != "complete"
                for row in domain_rows
            )
            else "required Domain Member 与 Manifest 可完整构造",
        )

        checks.update(
            {
                "CORE-G-001": CheckOutcome("pass", "Artifact ID、Revision 与 Lineage 一致"),
                "CORE-G-002": CheckOutcome("pass", "CTX、Scope Input 与 Control Input 使用准确 Reference"),
                "CORE-G-003": CheckOutcome("pass", "primary Blob 使用固定 DSN 结构"),
                "CORE-G-004": CheckOutcome("pass", "Member 与 Manifest 由同一 Builder 生成"),
                "CORE-G-005": checks["DSN-G-003"],
                "CORE-G-006": CheckOutcome(
                    "fail" if invalid_evidence else "pass",
                    "Evidence 结构无效" if invalid_evidence else "Evidence 可追踪",
                ),
                "CORE-G-007": CheckOutcome(
                    "fail" if exception_invalid else "pass",
                    "Exception 结构无效" if exception_invalid else "Exception 记录有效",
                ),
                "CORE-G-008": CheckOutcome("pass", "Status、Gate 与 Open Item 由确定性聚合派生"),
                "CORE-G-009": CheckOutcome("pending", "Final Confirmation 尚未验证"),
            }
        )

        for row in domain_rows:
            if row["disposition"] != "required":
                continue
            result = "pass" if row["completion"] == "complete" else "pending"
            for check_id in row["definition"].check_ids:
                checks[check_id] = CheckOutcome(
                    result,
                    f"{row['definition'].display_name} "
                    + ("固定 Contract 已满足" if result == "pass" else "内容尚未完成"),
                )

        numbered = tuple(
            {
                "id": f"OPI-{index:03d}",
                **item,
            }
            for index, item in enumerate(open_items, start=1)
        )
        return DsnAnalysis(
            checks=checks,
            open_items=numbered,
            active_exceptions=tuple(active_exceptions),
            normalized=normalized,
            domain_rows=tuple(domain_rows),
            composite_rows=tuple(composite_list),
        )

    def _open(
        self,
        needed: str,
        source: str,
        blocked: str,
        *,
        state: str = "open",
        resolution: str = "N/A",
    ) -> dict[str, str]:
        return {
            "needed": needed,
            "expected_source": source,
            "blocked_references": blocked,
            "state": state,
            "resolution": resolution,
        }


__all__ = tuple(name for name in globals() if not name.startswith("__"))
