"""Persisted DSN Artifact Set verifier."""

from dsn_common import *


class DsnVerifier:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def verify(self, reference: str, revision) -> DomainVerification:
        artifact_id, revision_number = _exact_base(reference, "DSN")
        if artifact_id != revision.control.artifact_id or revision_number != revision.control.revision:
            raise DsnRuntimeError("DSN verifier reference does not match payload")
        parsed = parse_canonical_artifact(revision.payload.primary_blob)
        front = parsed.front_matter
        if front.get("contract") != DSN_CONTRACT or front.get("phase") != "DSN":
            raise DsnRuntimeError("DSN Contract or phase is invalid")
        if front.get("id") != artifact_id or front.get("revision") != revision_number:
            raise DsnRuntimeError("DSN Front Matter identity is invalid")
        if front.get("status") != revision.payload.artifact_status:
            raise DsnRuntimeError("DSN Front Matter status is stale")
        for heading in (
            "## 摘要 Summary",
            "## 范围 Scope",
            "## 设计基线与变更 Design Baseline and Change",
            "## 需求追踪 Requirement Traceability",
            "## 设计总纲 Design Index",
            "## 产物集清单 Artifact Set Manifest",
            "## 待确认项 Open Items",
            "## 证据 Evidence",
            "## 豁免 Exceptions",
            "## 生命周期适用性 Lifecycle Applicability",
            "## 门禁 Gate",
        ):
            if heading not in parsed.text:
                raise DsnRuntimeError(f"DSN fixed heading is missing: {heading}")
        matrix = require_single_table(parsed, MATRIX_HEADERS, "Design Matrix")
        if len(matrix.rows) != 16:
            raise DsnRuntimeError("Design Matrix must contain 16 rows")
        expected = tuple(item.display_name for item in DOMAIN_CATALOG)
        if tuple(row["设计领域 Design Domain"] for row in matrix.rows) != expected:
            raise DsnRuntimeError("Design Matrix order or names are invalid")
        required_ids = {
            DOMAIN_CATALOG[index].code
            for index, row in enumerate(matrix.rows)
            if row["处置 Disposition"] == "required"
        }
        member_ids = {item.member_id for item in revision.payload.members}
        if any(item.startswith("DOM-") and item not in required_ids for item in member_ids):
            raise DsnRuntimeError("non-required Domain Member exists")
        if "DOM-510" not in required_ids:
            raise DsnRuntimeError("DOM-510 must be required")
        if revision.payload.artifact_status in {"ready", "ready_with_exception"}:
            if not required_ids.issubset(member_ids):
                raise DsnRuntimeError("ready DSN is missing a required Domain Member")
            confirmation = require_single_row(
                require_single_table(
                    parsed, FINAL_CONFIRMATION_HEADERS, "Final Confirmation"
                ),
                "Final Confirmation",
            )
            summary = require_single_row(
                require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate Summary"),
                "Gate Summary",
            )
            if confirmation["Result"] != "approved":
                raise DsnRuntimeError("ready DSN requires approved Final Confirmation")
            control_digest = compute_control_input_digest(revision.payload.primary_blob)
            check_digest = compute_check_set_result_digest(parsed)
            if confirmation["Control Input Digest"] != control_digest:
                raise DsnRuntimeError("Final Confirmation Control Input Digest is stale")
            if summary["Control Input Digest"] != control_digest:
                raise DsnRuntimeError("Gate Summary Control Input Digest is stale")
            if confirmation["Check Set Result Digest"] != check_digest:
                raise DsnRuntimeError("Final Confirmation Check Set Digest is stale")
            if summary["Check Set Result Digest"] != check_digest:
                raise DsnRuntimeError("Gate Summary Check Set Digest is stale")
            expected_gate = (
                "pass"
                if revision.payload.artifact_status == "ready"
                else "pass_with_exception"
            )
            if summary["Gate Result"] != expected_gate:
                raise DsnRuntimeError("DSN Status and Gate are inconsistent")
            authority_raw = _authority_file(
                self.project_root, confirmation["Authority Reference"]
            )
            if confirmation["Mode"] == "delegated":
                authority_front, _ = parse_front_matter(
                    authority_raw.decode("utf-8")
                )
                if authority_front.get("contract") != (
                    "sdlc-ai-spec/final-confirmation-authority/v1"
                ):
                    raise DsnRuntimeError("Delegated Authority Contract is invalid")
                if authority_front.get("artifact") != reference:
                    raise DsnRuntimeError(
                        "Delegated Authority is bound to another Artifact"
                    )
                if authority_front.get("decision") != "approved":
                    raise DsnRuntimeError(
                        "Delegated Authority decision is not approved"
                    )
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="DSN payload satisfies its bundled Runtime Contract",
        )


__all__ = tuple(name for name in globals() if not name.startswith("__"))
