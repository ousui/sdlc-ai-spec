"""Canonical IMP producer; no Claim, Resource or ArtifactStore mutations."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from packages.sdlc_phasekit import (
    CheckOutcome, PhaseBuild, PhaseInputs, evaluation_contract_set, manifest,
    render_phase_artifact, subject_digest, table,
    validate_delegated_final_confirmation, validate_final_confirmation,
)
from packages.sdlc_runtime import (
    compute_check_set_result_digest, compute_control_input_digest,
    parse_canonical_artifact,
)
from packages.sdlc_runtime.canonical import (
    FINAL_CONFIRMATION_HEADERS, require_single_row, require_single_table,
)

from imp_common import (
    BINDING_HEADERS, LOCAL_CHECK_HEADERS, MATRIX_HEADERS, RESULT_HEADERS,
    READINESS, STATE_MEMBER, reject_secrets,
)
from imp_method import BLOCKS, BLOCK_TABLES
from imp_result import member

def final_confirmation_from_payload(raw, state, subject):
    """Recover the canonical confirmation without retaining it in a Member."""
    row = require_single_row(
        require_single_table(
            parse_canonical_artifact(raw), FINAL_CONFIRMATION_HEADERS,
            "Final Confirmation",
        ),
        "Final Confirmation",
    )
    if row["Result"] != "approved":
        return None
    confirmation = {
        "mode": row["Mode"],
        "confirmer": row["Confirmer"],
        "role": row["Role"],
        "authority_reference": row["Authority Reference"],
        "confirmed_at": row["Confirmed At"],
        "subject_digest": subject,
        "control_input_digest": row["Control Input Digest"],
        "evaluation_contract_set": row["Evaluation Contract Set"],
        "check_set_result_digest": row["Check Set Result Digest"],
    }
    if row["Mode"] == "delegated":
        confirmation["reviewed_executor"] = state["claim"]["owner"]
        confirmation["accepted_exception_references"] = []
    return confirmation


def _approach(method):
    lines = []
    for step in method["steps"]:
        lines.extend([
            f"#### {step['id']} {step['purpose']}", "",
            f"- 顺序 Order: {step['order']}",
            f"- 目标位置 Target: {', '.join(step['target'])}",
            f"- 依据引用 Basis References: {', '.join(step['basis_references'])}",
            f"- 适用考量项 Considerations: {', '.join(step['considerations']) or 'None'}",
            f"- 预期结果 Expected Result: {step['expected_result']}",
            f"- Transaction Boundary: {step['transaction_boundary']}",
            f"- Failure Boundary: {step['failure_boundary']}", "", "实施逻辑：", "",
            *(f"{index}. {text}" for index, text in enumerate(step["logic"], start=1)), "",
        ])
        for block in step.get("blocks", []):
            name = block["consideration"]
            lines.extend([f"##### {block['id']} {name}", ""])
            fields = BLOCKS[name][1]
            if name in BLOCK_TABLES:
                columns = BLOCK_TABLES[name]
                lines.append(table(columns, [tuple(row[key] for key in columns) for row in block[fields[0]]]))
            else:
                lines.extend(f"- {field}: {block[field]}" for field in fields)
            lines.append("")
    return "\n".join(lines)


class ImpBuilder:
    def __init__(self, project_root):
        self.project_root = Path(project_root)

    def build(self, *, artifact_id, revision, state, members, final_confirmation=None,
              _candidate_only=False):
        value = deepcopy(state)
        value.pop("final_confirmation", None)
        supporting = tuple(sorted((item for item in members if item.member_id != STATE_MEMBER), key=lambda item: item.member_id))
        subject = subject_digest(value, {
            "artifact": f"{artifact_id}@{revision}",
            "members": [(item.member_id, item.canonical_name, item.sha256) for item in supporting],
        })
        # Candidate reconstruction checks the old intrinsic subject binding,
        # never the availability of its former external Authority. This private
        # mode is used only by the frozen candidate reader, never to finalize.
        base_valid = (
            bool(final_confirmation and final_confirmation.get("subject_digest") == subject)
            if _candidate_only
            else validate_final_confirmation(
                self.project_root, final_confirmation, subject
            )
        )
        # Final Confirmation remains only in the canonical primary Artifact.
        # Retaining its Authority Reference in IMP-STATE would indirectly put
        # that record in the Supporting Manifest and create a digest cycle.
        all_members = tuple(sorted((*supporting, member(STATE_MEMBER, value)), key=lambda item: item.member_id))
        executed = value["stage"] == "executed"
        local = value.get("checks", [])
        local_pass = bool(local) and all(item["result"] == "pass" for item in local)
        failure = value.get("failure")
        exceptions = value["method"].get("exceptions", [])
        active = tuple(item["id"] for item in exceptions if item["state"] in {"active", "carried"})
        pre_execution = value.get("pre_execution")
        pre_execution_ready = (
            isinstance(pre_execution, dict)
            and set(pre_execution) == {
                "contract", "evidence_member", "evidence_sha256", "observed_at",
                "evaluation_contract_set", "checklist_digest",
            }
            and pre_execution.get("contract") == "sdlc-ai-spec/imp-pre-execution-readback/v1"
            and pre_execution.get("evidence_member") == "EVD-PRE"
            and all(
                isinstance(pre_execution.get(key), str) and pre_execution[key]
                for key in (
                    "evidence_sha256", "observed_at", "evaluation_contract_set",
                    "checklist_digest",
                )
            )
        )

        def project(authority_valid):
            checks = {
                f"CORE-G-{index:03d}": CheckOutcome(
                    "pass", "Canonical records and immutable closure are checked"
                )
                for index in range(1, 9)
            }
            checks["CORE-G-009"] = CheckOutcome(
                "pass" if authority_valid else "pending",
                "Current Final Confirmation"
                if authority_valid
                else "Final Confirmation is required",
            )
            checks.update({
                "IMP-G-001": CheckOutcome("pass", "Exact Context, Binding, Claim and current Dependency chain"),
                "IMP-G-002": CheckOutcome("pass", "One atomic Outcome and unchanged Claim Scope"),
                "IMP-G-003": CheckOutcome("pass" if pre_execution_ready else "pending", "Method and persisted pre-execution readback"),
                "IMP-G-004": CheckOutcome("fail" if failure else "pass" if executed else "pending", "Immutable Result readback and exact Changed Scope"),
                "IMP-G-005": CheckOutcome("pass" if local_pass else "fail" if local else "pending", "Applicable local Checks only; VFY readiness"),
                "IMP-G-006": CheckOutcome("fail" if failure else "pass" if executed and local_pass else "pending", "Result, Evidence and open obligations"),
            })
            open_items = list(value["method"].get("open_items", []))
            if not authority_valid:
                open_items.append({
                    "id": "OPI-FINAL",
                    "needed": "Confirm the current Method, Result, Checks and Claim",
                    "expected_source": "Implementation Authority",
                    "blocked_references": "CORE-G-009",
                    "state": "open",
                    "resolution": "N/A",
                })
            failed = tuple(
                key for key, check in checks.items() if check.result == "fail"
            )
            pending = any(check.result == "pending" for check in checks.values()) or any(
                item.get("state") == "open" for item in open_items
            )
            status, gate = (
                ("failed", "fail")
                if failed
                else ("waiting_input", "pending")
                if pending
                else ("ready_with_exception", "pass_with_exception")
                if active
                else ("ready", "pass")
            )
            return checks, open_items, failed, status, gate

        binding, claim, request = value["binding"], value["claim"], value["request"]
        reference = f"{artifact_id}@{revision}"
        context_rows = [
            ("PLN Reference", binding["plan_reference"] or "N/A"),
            ("WI Binding", binding["reference"] if binding["wi_id"] else "N/A"),
            ("Context Reference", binding["context_reference"]),
            ("Lineage", ", ".join(binding["lineage_references"])),
        ]
        result_rows = [
            (row["id"], row["resource"], row["baseline_reference"], row["change_reference"],
             row["result_reference"], ", ".join(row["changed_scope"]) or "None",
             ", ".join(row["steps"]) or "None") for row in value["resources"]
        ]
        check_rows = [
            (row["id"], row["name"], f"resource:{row['resource']}", row["result"],
             f"{reference}/{row['evidence_member']}") for row in local
        ] or [("None", "Await implementation", "N/A", "pending", "No local Check has run")]
        sections = (
            ("## 摘要 Summary", str(value["method"].get("summary") or binding["outcome"])),
            ("## 范围 Scope", f"- 结果 Outcome: {binding['outcome']}\n"
             f"- 执行范围 Execution Scope: {', '.join(binding['execution_scope'])}\n"
             "- 排除项 Exclusions: Claim Scope 外资源、上游决策、完整 VFY 与发布"),
            ("## 实施控制 Implementation Control", table(("Relationship", "Reference"), context_rows)),
            ("### 实施绑定 Implementation Binding", table(BINDING_HEADERS, [(
                binding["reference"], binding["lineage"], claim["attempt"], claim["owner"],
                ", ".join(claim["rework_references"]) or "None",
            )])),
            ("### 输入就绪检查 Input Readiness Check Set", table(
                ("Check ID", "检查项 Check", "Result", "Evidence or Notes"),
                [(f"IMP-RDY-{index:03d}", name, "pass", binding["reference"])
                 for index, name in enumerate(READINESS, 1)],
            )),
            ("## 实施方法合约 Implementation Method Contract", "仅落实准确上游决定；公共抽象、依赖和跨模块接口必须有 DSN Decision。"),
            ("### 实施考量矩阵 Implementation Consideration Matrix", table(MATRIX_HEADERS, [
                (row["name"], row["disposition"], row["basis"], ", ".join(row.get("steps", [])) or "None",
                 row.get("exception") or "None") for row in value["method"]["considerations"]
            ])),
            ("### 实施步骤 Implementation Approach", _approach(value["method"])),
            ("## 实施结果 Implementation Result", table(RESULT_HEADERS, result_rows)),
            ("## 实施检查 Implementation Checks", table(LOCAL_CHECK_HEADERS, check_rows)),
        )
        evidence = [
            {"id": item.member_id, "type": "snapshot" if item.canonical_name.startswith("snapshots/") else "execution",
             "supports_references": [binding["reference"]], "source": "IMP Runtime",
             "reference": f"{reference}/{item.member_id}", "integrity": item.sha256,
             "produced_at": "N/A", "sensitivity": "project-local"}
            for item in supporting
        ]
        contract_set = evaluation_contract_set(
            Path(__file__).resolve().parents[1] / "references/source-lock.json",
            ("sdlc-ai-spec/spec/core/v1.1", "sdlc-ai-spec/spec/artifact-store/v1.1",
             "sdlc-ai-spec/spec/implementation/v1.1"),
        )
        phase_inputs = PhaseInputs(
            binding["context_reference"],
            (binding["upstream_reference"],),
            tuple(
                item
                for item in request["artifact_inputs"]
                if item != binding["upstream_reference"]
            ),
        )
        title = str(value["method"].get("title") or "Implementation")

        # Calculate the exact prospective authority bindings with CORE-G-009
        # closed but without embedding Final Confirmation itself. The control
        # digest is therefore stable and the delegated file cannot self-bind.
        prospective = project(True)
        prospective_raw = render_phase_artifact(
            artifact_id=artifact_id,
            phase="IMP",
            revision=revision,
            status=prospective[3],
            profile=str(value["method"].get("profile", "full")),
            phase_inputs=phase_inputs,
            title=title,
            sections=sections,
            checks=prospective[0],
            open_items=prospective[1],
            evidence=evidence,
            exceptions=exceptions,
            lifecycle_applicability=binding["lifecycle_applicability"],
            final_confirmation=None,
            gate_result=prospective[4],
            evaluation_contract_set=contract_set,
            evaluator="sdlc-400-imp",
            members=all_members,
        )
        binding_check_digest = (
            "N/A"
            if any(
                outcome.result == "pending" and check_id != "CORE-G-009"
                for check_id, outcome in prospective[0].items()
            )
            else compute_check_set_result_digest(parse_canonical_artifact(prospective_raw))
        )
        bindings = {
            "control_input_digest": compute_control_input_digest(prospective_raw),
            "evaluation_contract_set": contract_set,
            "check_set_result_digest": binding_check_digest,
        }
        valid = base_valid
        if valid and final_confirmation.get("mode") == "delegated" and not _candidate_only:
            eligible = (
                not prospective[2]
                and prospective[3] == "ready"
                and not active
            )
            valid = eligible and validate_delegated_final_confirmation(
                self.project_root,
                final_confirmation,
                artifact_reference=reference,
                reviewed_executor=claim["owner"],
                **bindings,
            )
        checks, open_items, failed, status, gate = project(valid)
        raw = render_phase_artifact(
            artifact_id=artifact_id, phase="IMP", revision=revision, status=status,
            profile=str(value["method"].get("profile", "full")),
            phase_inputs=phase_inputs,
            title=title,
            sections=sections, checks=checks, open_items=open_items, evidence=evidence,
            exceptions=exceptions,
            lifecycle_applicability=binding["lifecycle_applicability"],
            final_confirmation=final_confirmation if valid else None, gate_result=gate,
            evaluation_contract_set=contract_set, evaluator="sdlc-400-imp", members=all_members,
        )
        reject_secrets(raw)
        return PhaseBuild(raw, status, gate, failed, tuple(open_items), active, valid,
                          all_members, manifest(all_members), subject, bindings)
