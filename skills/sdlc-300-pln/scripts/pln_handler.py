"""ArtifactStore command handler for the PLN Skill."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_phasekit import ArtifactPhaseHandler, StructuredPhaseVerifier
from packages.sdlc_runtime import FrozenArtifactAuthorityVerifier

from pln_builder import PlnBuilder
from pln_common import PlnError
from pln_scope import resolve_inputs
from pln_verifier import semantic_validate

class PlnHandler(ArtifactPhaseHandler):
    def __init__(
        self,
        root: Path | str,
        *,
        upstream_verifier_factory=FrozenArtifactAuthorityVerifier,
        **kwargs,
    ):
        root = Path(root).resolve()
        verifier = StructuredPhaseVerifier(
            root,
            phase="PLN",
            required_headings=(
                "## 摘要 Summary",
                "## 范围 Scope",
                "## 交付范围 Delivery Scope",
                "## 聚合适用性 Aggregated Applicability",
                "## 义务覆盖 Obligations",
                "## 工作项 Work Items",
                "## 待确认项 Open Items",
                "## 证据 Evidence",
                "## Supporting Artifact Manifest",
                "## 豁免 Exceptions",
                "## 生命周期适用性 Lifecycle Applicability",
                "## 门禁 Gate",
            ),
            semantic_validator=semantic_validate,
        )
        input_resolver = lambda store, inputs: resolve_inputs(store, inputs, upstream_verifier_factory)
        super().__init__(
            root,
            artifact_type="PLN",
            skill_name="sdlc-300-pln",
            builder=PlnBuilder(root),
            verifier=verifier,
            input_resolver=input_resolver,
            candidate_key="plan",
            **kwargs,
        )

    def create(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        # Applicability is decided before allocation. This prevents placeholder
        # Plan Artifacts for n/a/waived/pending cases.
        try:
            read_store = ArtifactStore.open_read_only(self.project_root)
            phase_inputs = self.input_resolver(read_store, invocation["inputs"])
            plan = invocation["inputs"].get("plan")
            if not isinstance(plan, Mapping):
                raise PlnError("inputs.plan must be an object")
            candidate = str(plan.get("pln_disposition") or "")
            authoritative = str(phase_inputs.metadata.get("pln_disposition"))
            if candidate == "pending":
                return self._result(
                    invocation,
                    ok=False,
                    status="action_required",
                    errors=({"code":"PLN_APPLICABILITY_PENDING","message":"PLN applicability remains pending; no Artifact was allocated"},),
                    next_action={"code":"RESOLVE_PLN_APPLICABILITY","message":"Resolve PLN applicability before creating a Plan","requires_user":True,"command":None},
                )
            if candidate != authoritative:
                raise PlnError(f"candidate PLN disposition {candidate!r} does not match authoritative Scope disposition {authoritative!r}")
            if authoritative in {"n/a", "embedded", "waived"}:
                return self._result(
                    invocation,
                    ok=True,
                    status="completed",
                    warnings=({"code":"PLN_NOT_REQUIRED","message":f"PLN is {authoritative}; no Plan Artifact was created"},),
                )
        except Exception as exc:
            return self._error(invocation, exc)
        return super().create(invocation)
