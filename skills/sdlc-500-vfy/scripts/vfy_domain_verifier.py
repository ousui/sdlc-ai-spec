"""ArtifactStore DomainVerifier for exact canonical VFY revisions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.sdlc_artifact_store import DomainVerification
from packages.sdlc_phasekit import StructuredPhaseVerifier

from vfy_builder import final_confirmation_from_payload
from vfy_canonical import validate_primary_against_state
from vfy_verifier import verify_state


class VfyDomainVerifier:
    """Recompute domain, primary/state and manifest integrity before freeze."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).expanduser().resolve()

    def verify(self, reference: str, revision: Any) -> DomainVerification:
        try:
            members = [
                item
                for item in revision.payload.members
                if item.member_id == "VFY-STATE"
            ]
            if len(members) != 1:
                raise ValueError(
                    f"VFY-STATE must appear exactly once; found {len(members)}"
                )
            state = json.loads(members[0].raw_bytes.decode("utf-8"))
            state["final_confirmation"] = final_confirmation_from_payload(
                revision.payload.primary_blob, state
            )
            state["artifact"]["revision_state"] = revision.control.state
            state["artifact"]["artifact_status"] = revision.payload.artifact_status
            projection = verify_state(state, finalizing=True)
            validate_primary_against_state(
                revision.payload.primary_blob,
                state,
                member_ids=[item.member_id for item in revision.payload.members],
                members=revision.payload.members,
            )
            has_exception = bool(state.get("exceptions"))
            expected_status = "ready_with_exception" if has_exception else "ready"
            expected_gate = "pass_with_exception" if has_exception else "pass"
            approved = (
                state["artifact"]["reference"] == reference
                and state["artifact"]["revision_state"] in {"open", "frozen"}
                and revision.payload.artifact_status == expected_status
                and projection["artifact_gate"] == expected_gate
            )
            canonical = StructuredPhaseVerifier(
                self.project_root,
                phase="VFY",
                required_headings=(
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
                ),
            ).verify(reference, revision)
            return DomainVerification(
                reference=reference,
                payload_binding=canonical.payload_binding,
                approved=approved,
                message=(
                    "VFY primary/state/manifest verification passed"
                    if approved
                    else "VFY canonical status/gate mismatch"
                ),
            )
        except Exception as exc:  # DomainVerifier must fail closed as a value.
            return DomainVerification(
                reference=reference,
                payload_binding=revision.verification_binding,
                approved=False,
                message=f"VFY domain verification failed: {exc}",
            )
