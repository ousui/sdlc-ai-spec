"""Build canonical PLN Artifacts from normalized candidates."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from packages.sdlc_phasekit import (
    PhaseBuild,
    PhaseInputs,
    contains_secret,
    decode_supporting_member,
    manifest,
    refs,
    render_phase_artifact,
    rows,
    subject_digest,
    table,
    validate_final_confirmation,
)

from pln_analyzer import _analyze, _outcome
from pln_common import (
    APPLICABILITY_HEADERS,
    DELIVERY_HEADERS,
    EVAL_SET,
    OBLIGATION_HEADERS,
    WORK_HEADERS,
    PlnError,
)

class PlnBuilder:
    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root).resolve()

    def build(
        self,
        *,
        artifact_id: str,
        revision: int,
        phase_inputs: PhaseInputs,
        candidate: Mapping[str, Any],
        final_confirmation: Mapping[str, Any] | None,
    ) -> PhaseBuild:
        value, checks, open_items, active_exceptions = _analyze(candidate, phase_inputs)
        subject = subject_digest(value, {
            "context": phase_inputs.context_reference,
            "scope": phase_inputs.scope_references,
            "control": phase_inputs.control_references,
        })
        final_valid = validate_final_confirmation(self.project_root, final_confirmation, subject)
        checks["CORE-G-009"] = _outcome(
            "pass" if final_valid else "pending",
            "Final Confirmation binds the current Plan" if final_valid else "Final Confirmation is required",
        )
        if not final_valid:
            open_items.append({
                "id": f"OPI-{len(open_items)+1:03d}",
                "needed": "Confirm the current Plan Artifact",
                "expected_source": "Plan Authority",
                "blocked_references": "CORE-G-009",
                "state": "open",
                "resolution": "N/A",
            })
        failed = tuple(sorted(key for key, outcome in checks.items() if outcome.result == "fail"))
        pending = tuple(sorted(key for key, outcome in checks.items() if outcome.result == "pending"))
        if failed:
            status, gate = "failed", "fail"
        elif pending or any(item.get("state") == "open" for item in open_items):
            status, gate = "waiting_input", "pending"
        elif active_exceptions:
            status, gate = "ready_with_exception", "pass_with_exception"
        else:
            status, gate = "ready", "pass"

        work_rows = [(
            item["id"], item["target_phase"], item["outcome"],
            ", ".join(item["execution_scope"]),
            ", ".join(item["source_references"]),
            ", ".join(item["constraint_references"]) or "None",
            ", ".join(item["depends_on"]) or "None",
            item["completion_criteria"], item["expected_evidence"],
            item["responsible_role"] or "N/A",
        ) for item in value["work_items"]] or [
            ("None", "N/A", "No Work Item for non-required Plan", "N/A", "N/A", "None", "None", "N/A", "N/A", "N/A")
        ]
        delivery_rows = [(
            item.get("scope_token"),
            ", ".join(refs(item.get("source_references"), "delivery source")) or "None",
            item.get("outcome") or "N/A",
        ) for item in value["delivery_scope"]] or [("None", "None", "No delivery scope")]
        aggregate_rows = [(
            item.get("phase"), item.get("disposition"), item.get("host") or "N/A", item.get("basis") or "N/A"
        ) for item in value["aggregated_applicability"]] or [
            (item["phase"], item["disposition"], item["host"], item["basis"])
            for item in phase_inputs.metadata.get("aggregated_applicability", ())
        ]
        covered_by: dict[str, list[str]] = {}
        for item in value["work_items"]:
            for reference in item["source_references"]:
                covered_by.setdefault(reference, []).append(item["id"])
        obligation_rows = [
            (reference, ", ".join(covered_by.get(reference, ())) or "None")
            for reference in value["obligations"]
        ] or [("None", "None")]
        members = tuple(
            decode_supporting_member(item, index)
            for index, item in enumerate(rows(value.get("supporting_members"), "supporting_members"), start=1)
        )
        sections = (
            ("## 摘要 Summary", str(value.get("summary") or "Plan the authoritative delivery scope.")),
            ("## 范围 Scope", table(("Field", "Value"), (
                ("Scope Inputs", ", ".join(phase_inputs.scope_references)),
                ("Control Inputs", ", ".join(phase_inputs.control_references) or "None"),
                ("PLN Disposition", value.get("pln_disposition")),
            ))),
            ("## 交付范围 Delivery Scope", table(DELIVERY_HEADERS, delivery_rows)),
            ("## 聚合适用性 Aggregated Applicability", table(APPLICABILITY_HEADERS, aggregate_rows)),
            ("## 义务覆盖 Obligations", table(OBLIGATION_HEADERS, obligation_rows)),
            ("## 工作项 Work Items", table(WORK_HEADERS, work_rows)),
        )
        raw = render_phase_artifact(
            artifact_id=artifact_id,
            phase="PLN",
            revision=revision,
            status=status,
            profile=str(value.get("profile") or "full"),
            phase_inputs=phase_inputs,
            title=str(value.get("title") or "Delivery Plan"),
            sections=sections,
            checks=checks,
            open_items=open_items,
            evidence=rows(value.get("evidence"), "evidence"),
            exceptions=value["exceptions"],
            lifecycle_applicability=value["lifecycle_applicability"],
            final_confirmation=final_confirmation if final_valid else None,
            gate_result=gate,
            evaluation_contract_set=EVAL_SET,
            evaluator="sdlc-300-pln",
            members=members,
        )
        if contains_secret(raw):
            raise PlnError("PLN primary Blob appears to contain a Secret")
        return PhaseBuild(
            raw, status, gate, failed, tuple(open_items), active_exceptions,
            final_valid, members, manifest(members), subject,
        )
