"""Pure additive VFY lifecycle projection and exact current-subject readback."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import shlex
from typing import Any, Mapping

from packages.sdlc_artifact_store import ArtifactStoreError

from .errors import LifecycleArtifactError, LifecycleQueryError
from .models import LifecycleProjection, NextAction
from .query import _error
from .query_imp import LifecycleQueryService as ImpLifecycleQueryService


@dataclass(frozen=True)
class VfyProjection:
    artifact_reference: str | None
    revision_state: str
    artifact_status: str
    product_result: str
    artifact_gate: str
    early_stop: bool
    unresolved_returns: tuple[str, ...]
    unresolved_controls: tuple[str, ...]
    rls_applicability: str
    rls_ready: bool
    next_phase: str | None
    next_action: str
    return_phase: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def project_vfy_state(state: Mapping[str, Any] | None) -> VfyProjection:
    if not state:
        return VfyProjection(
            artifact_reference=None,
            revision_state="absent",
            artifact_status="absent",
            product_result="unknown",
            artifact_gate="unknown",
            early_stop=False,
            unresolved_returns=(),
            unresolved_controls=(),
            rls_applicability="pending",
            rls_ready=False,
            next_phase="VFY",
            next_action="CREATE_VFY",
            return_phase=None,
        )

    artifact = state.get("artifact") or {}
    unresolved = tuple(
        str(item.get("id"))
        for item in state.get("returns", [])
        if isinstance(item, Mapping) and item.get("status") != "resolved"
    )
    phases = tuple(
        str(item.get("return_phase"))
        for item in state.get("returns", [])
        if isinstance(item, Mapping) and item.get("status") != "resolved"
    )
    controls = {str(item) for item in state.get("control_inputs", [])}
    resolved_controls = {
        str(item.get("control_reference"))
        for item in state.get("control_resolutions", [])
        if isinstance(item, Mapping) and item.get("status") == "resolved"
    }
    unresolved_controls = tuple(sorted(controls - resolved_controls))
    revision_state = str(artifact.get("revision_state", "unknown"))
    product = str(state.get("product_result", "unknown"))
    gate = str(state.get("artifact_gate", "unknown"))
    early_stop = bool(state.get("early_stop"))
    applicability = str(state.get("rls_applicability", "pending"))
    ready = bool(state.get("rls_ready"))

    if revision_state != "frozen":
        next_phase, action, return_phase = "VFY", "CONTINUE_VFY", None
    elif early_stop:
        return_phase = phases[0] if phases else None
        next_phase = return_phase or "VFY"
        action = "RETURN_UPSTREAM" if return_phase else "REVISE_VFY"
        ready = False
    elif unresolved or product == "fail" and not ready:
        return_phase = phases[0] if phases else None
        next_phase = return_phase or "VFY"
        action = "RETURN_UPSTREAM" if return_phase else "RESOLVE_VFY_FAILURE"
        ready = False
    elif unresolved_controls:
        next_phase, action, return_phase = "VFY", "RESOLVE_CONTROL_INPUT", None
        ready = False
    elif gate not in {"pass", "pass_with_exception"}:
        next_phase, action, return_phase = "VFY", "REPAIR_VFY_ARTIFACT", None
        ready = False
    elif applicability == "required" and ready:
        next_phase, action, return_phase = "RLS", "CREATE_RLS", None
    elif applicability in {"n/a", "waived"} and product in {"pass", "waived", "n/a"}:
        next_phase, action, return_phase = None, "LIFECYCLE_COMPLETE", None
        ready = False
    else:
        next_phase, action, return_phase = "VFY", "RESOLVE_RLS_APPLICABILITY", None
        ready = False

    return VfyProjection(
        artifact_reference=artifact.get("reference"),
        revision_state=revision_state,
        artifact_status=str(artifact.get("artifact_status", "unknown")),
        product_result=product,
        artifact_gate=gate,
        early_stop=early_stop,
        unresolved_returns=unresolved,
        unresolved_controls=unresolved_controls,
        rls_applicability=applicability,
        rls_ready=ready,
        next_phase=next_phase,
        next_action=action,
        return_phase=return_phase,
    )


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise LifecycleArtifactError(message, code=code)


class LifecycleQueryService(ImpLifecycleQueryService):
    """Compose VFY readback without changing the stable IMP query module."""

    def _result_digest(self, reference: str) -> str | None:
        if reference == "N/A":
            return None
        base, separator, member_id = reference.partition("/")
        _require(
            bool(separator and member_id and "/" not in member_id),
            "VFY_SUBJECT_NOT_CURRENT",
            "IMP Result Reference does not select one immutable Member",
        )
        artifact_id, revision_text = base.split("@", 1)
        stored = self.store.read_revision(artifact_id, int(revision_text))
        matches = [
            member for member in stored.payload.members if member.member_id == member_id
        ]
        _require(
            len(matches) == 1,
            "VFY_SUBJECT_NOT_CURRENT",
            "IMP Result Member is missing or duplicated",
        )
        return matches[0].sha256

    def _with_result_digests(
        self, projection: LifecycleProjection
    ) -> LifecycleProjection:
        digests: dict[str, str | None] = {}
        views = []
        for view in projection.current_claims:
            results = []
            for raw in view.results:
                row = dict(raw)
                reference = str(row["result_reference"])
                row["result_digest"] = self._result_digest(reference)
                digests[reference] = row["result_digest"]
                results.append(row)
            views.append(replace(view, results=tuple(results)))
        vfy_results = []
        for raw in projection.vfy_results:
            row = dict(raw)
            reference = str(row["result_reference"])
            _require(
                reference in digests and digests[reference] is not None,
                "VFY_SUBJECT_NOT_CURRENT",
                "Current terminal IMP Result Digest is unavailable",
            )
            row["result_digest"] = digests[reference]
            vfy_results.append(row)
        return replace(
            projection,
            current_claims=tuple(views),
            vfy_results=tuple(vfy_results),
        )

    def _vfy_state(self, node) -> dict[str, Any] | None:
        stored = self.store.read_revision(node.artifact_id, node.revision)
        matches = [
            item for item in stored.payload.members if item.member_id == "VFY-STATE"
        ]
        if not matches:
            return None
        _require(len(matches) == 1, "VFY_STATE_INVALID", "VFY-STATE Member is duplicated")
        state = json.loads(matches[0].raw_bytes)
        _require(
            isinstance(state, dict)
            and state.get("contract") == "sdlc-ai-spec/vfy-state/v1"
            and isinstance(state.get("artifact"), dict),
            "VFY_STATE_INVALID",
            "VFY-STATE Member Contract is invalid",
        )
        state["artifact"]["revision_state"] = stored.control.state
        state["artifact"]["artifact_status"] = stored.payload.artifact_status
        _require(
            state["artifact"].get("reference") == node.reference
            and state.get("artifact_gate") == node.gate_result,
            "VFY_STATE_INVALID",
            "VFY state identity or Gate differs from canonical authority",
        )
        return state

    def _assert_vfy_subjects_current(
        self,
        state: Mapping[str, Any],
        projection: LifecycleProjection,
    ) -> None:
        current: dict[str, dict[str, Any]] = {}
        for view in projection.current_claims:
            for result in view.results:
                reference = result.get("result_reference")
                if reference == "N/A":
                    continue
                current[str(reference)] = {
                    "resource_id": result["resource"],
                    "imp_revision_reference": view.artifact_reference,
                    "binding_lineage": view.binding_lineage,
                    "attempt": str(view.attempt),
                    "claim_state": view.claim_state,
                    "imp_revision_state": view.revision_state,
                    "baseline_reference": result["baseline_reference"],
                    "result_digest": result["result_digest"],
                    "cumulative_changed_scope": list(result["changed_scope"]),
                    "dependency_result_references": list(view.dependency_results),
                }
        selected = {str(item["result_reference"]) for item in projection.vfy_results}
        subjects = state.get("subjects")
        _require(
            isinstance(subjects, list)
            and {item.get("reference") for item in subjects if isinstance(item, Mapping)} == selected,
            "VFY_SUBJECT_NOT_CURRENT",
            "VFY Subject Set differs from the complete current terminal IMP Results",
        )
        for subject in subjects:
            expected = current.get(str(subject.get("reference")))
            _require(
                expected is not None
                and all(subject.get(key) == value for key, value in expected.items())
                and subject.get("current_valid") is True
                and subject.get("dependency_chain_valid") is True,
                "VFY_SUBJECT_NOT_CURRENT",
                "VFY Subject binding differs from the current Claim and Result",
            )

    def _vfy_action(self, projection: VfyProjection, reference: str) -> NextAction:
        if projection.next_action == "CREATE_RLS":
            return self._action(
                "START_RLS",
                "RLS",
                "VFY Artifact 可验证，产品结果与 RLS 适用性允许进入发布",
                f"create --reference {shlex.quote(reference)}",
                requires_user=False,
            )
        if projection.next_action == "LIFECYCLE_COMPLETE":
            return NextAction(
                "LIFECYCLE_COMPLETE",
                None,
                None,
                False,
                "VFY 已冻结且 RLS 合法不适用；生命周期完成",
                None,
                False,
            )
        if projection.next_action == "RETURN_UPSTREAM" and projection.return_phase:
            return self._action(
                "RETURN_FROM_VFY",
                projection.return_phase,
                f"VFY 产品失败或未解决 Return 必须返回 {projection.return_phase}",
            )
        return self._action(
            "RESOLVE_VFY",
            "VFY",
            f"VFY 当前状态要求 {projection.next_action}",
            f"check --reference {shlex.quote(reference)}",
        )

    def inspect_requirement(self, requirement_reference: str) -> LifecycleProjection:
        projection = self._with_result_digests(
            super().inspect_requirement(requirement_reference)
        )
        current_vfy = [
            node
            for node in projection.nodes
            if node.artifact_type == "VFY" and node.reference in projection.frontier
        ]
        if not current_vfy or not projection.vfy_results:
            return projection
        try:
            states = [(node, self._vfy_state(node)) for node in current_vfy]
            states = [(node, state) for node, state in states if state is not None]
            _require(
                len(states) <= 1,
                "VFY_STATE_AMBIGUOUS",
                "Multiple current VFY state authorities require explicit selection",
            )
            if not states:
                return projection
            node, state = states[0]
            self._assert_vfy_subjects_current(state, projection)
            current = project_vfy_state(state)
            for claim in tuple(self._claims.values()):
                _require(
                    self._claim_read("resolve", claim.binding_lineage) == claim
                    and self._claim_read("resolve_artifact", claim.artifact_id) == claim,
                    "IMP_CLAIM_CHANGED",
                    "Current Claim changed during VFY readback; inspect again",
                )
            return replace(
                projection,
                next_actions=(self._vfy_action(current, node.reference),),
                overall_state=(
                    "complete"
                    if current.next_action == "LIFECYCLE_COMPLETE"
                    else "ready_for_next_phase"
                    if current.next_action == "CREATE_RLS"
                    else "action_required"
                ),
                vfy_projection=current.to_dict(),
            )
        except (
            LifecycleQueryError,
            ArtifactStoreError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            blocker = _error(
                getattr(exc, "code", "VFY_STATE_INVALID"),
                str(exc),
                current_vfy[0].reference,
            )
            action = self._action(
                "RESOLVE_VFY",
                "VFY",
                "VFY 状态或当前 Subject 无法形成可信生命周期投影",
                f"check --reference {shlex.quote(current_vfy[0].reference)}",
            )
            return replace(
                projection,
                blockers=(*projection.blockers, blocker),
                next_actions=(action,),
                overall_state="blocked",
                vfy_projection=None,
            )


__all__ = ("LifecycleQueryService", "VfyProjection", "project_vfy_state")
