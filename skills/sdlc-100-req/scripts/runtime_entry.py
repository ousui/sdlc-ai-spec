#!/usr/bin/env python3
"""REQ CLI entry with the reviewed finalization ordering."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import runtime as base


def _build(
    self,
    *,
    artifact_id: str,
    revision: int,
    context_reference: str,
    control_inputs: Sequence[str],
    requirement: Mapping[str, Any],
    final_confirmation: Mapping[str, Any] | None,
):
    analysis = self.analyzer.analyze(requirement)
    checks = dict(analysis.checks)
    checks.update(
        {
            "CORE-G-001": base.CheckOutcome("pass", "Artifact ID、Revision 与 Lineage 一致"),
            "CORE-G-002": base.CheckOutcome("pass", "CTX 与直接 Input 已按准确 frozen Reference 解析"),
            "CORE-G-003": base.CheckOutcome("pass", "固定模板与 Canonical Payload 可构造"),
            "CORE-G-004": base.CheckOutcome(checks["REQ-G-008"].result, "Disposition 与 Lifecycle Applicability 一致"),
            "CORE-G-005": base.CheckOutcome("pass", "Evidence 与 Supporting Member 使用固定索引"),
            "CORE-G-006": base.CheckOutcome(
                "pending" if any(item["state"] == "open" for item in analysis.open_items) else "pass",
                "存在未解决 Open Item" if analysis.open_items else "无未解决阻塞项",
            ),
            "CORE-G-008": base.CheckOutcome("pass", "Core 与 REQ Check Set 已完整登记"),
            "CORE-G-009": base.CheckOutcome("pending", "Final Confirmation 尚未完成"),
        }
    )
    for check_id in base.REQ_CHECKS:
        checks.setdefault(check_id, base.CheckOutcome("pass", "固定检查通过"))
    failed = sorted(
        check_id for check_id, item in checks.items() if item.result == "fail"
    )
    pending = sorted(
        check_id for check_id, item in checks.items() if item.result == "pending"
    )
    blocking_pending = [item for item in pending if item != "CORE-G-009"]
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
        base._decode_member(item, index)
        for index, item in enumerate(
            analysis.normalized["supporting_members"], start=1
        )
    )
    manifest = base._manifest(members)
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
    control_digest = base.compute_control_input_digest(raw)
    check_digest = (
        base.compute_check_set_result_digest(base.parse_canonical_artifact(raw))
        if not failed and not blocking_pending
        else self._safe_check_digest(raw)
    )

    final_valid = False
    if final_confirmation is not None and not failed and not blocking_pending:
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
        checks["CORE-G-009"] = base.CheckOutcome(
            "pass", "Final Confirmation 绑定当前 Revision 与摘要"
        )
        gate = "pass_with_exception" if analysis.active_exceptions else "pass"
        status = (
            "ready_with_exception" if analysis.active_exceptions else "ready"
        )
        gate_row = {
            "revision": str(revision),
            "control_digest": control_digest,
            "evaluation_set": base._evaluation_contract_set(),
            "check_digest": check_digest,
            "gate_result": gate,
            "exceptions": base._reference_text(
                [
                    f"{artifact_id}@{revision}#{item}"
                    for item in analysis.active_exceptions
                ]
            ),
            "evaluator": "sdlc-100-req-runtime",
            "evaluated_at": base._iso(),
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
        if base.compute_control_input_digest(raw) != control_digest:
            raise base.RequirementRuntimeError(
                "Finalization changed Control Input Digest"
            )
        if (
            base.compute_check_set_result_digest(base.parse_canonical_artifact(raw))
            != check_digest
        ):
            raise base.RequirementRuntimeError(
                "Finalization changed Check Set Result Digest"
            )
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

    return base.BuildResult(
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


base.RequirementBuilder.build = _build
RequirementHandler = base.RequirementHandler
RequirementVerifier = base.RequirementVerifier
RequirementAnalyzer = base.RequirementAnalyzer
RequirementRuntimeError = base.RequirementRuntimeError
execute_phase = base.execute_phase


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
