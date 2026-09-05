"""Additive, strictly read-only RLS lifecycle projection over frozen authority."""
from dataclasses import replace
import json
from typing import Mapping
from packages.sdlc_runtime import parse_canonical_artifact
from packages.sdlc_runtime.canonical import parse_reference_set, require_single_table
from packages.sdlc_runtime.control_inputs import RLS_ITEM_HEADERS, RLS_CONFIRMATION_HEADERS
from .query_vfy import LifecycleQueryService as VfyLifecycleQueryService, project_vfy_state
from .query import _error
from .models import NextAction
from .errors import LifecycleArtifactError


def _require(value, message):
    if not value:
        raise LifecycleArtifactError(message, code="RLS_STATE_INVALID")


def project_rls_state(state: Mapping | None, *, applicability="required", vfy_ready=False):
    artifact = (state or {}).get("artifact", {})
    revision_state = artifact.get("revision_state", "absent")
    gate = (state or {}).get("artifact_gate", "unknown")
    conclusion = (state or {}).get("release_conclusion", "pending")
    follow = (state or {}).get("follow_up", "none")
    phase, action = "RLS", "CREATE_RLS"
    if not state:
        if applicability in {"n/a", "waived"}:
            phase, action = None, "LIFECYCLE_COMPLETE"
        elif applicability != "required" or not vfy_ready:
            phase, action = "VFY", "RESOLVE_RLS_APPLICABILITY"
    elif state.get("effect_uncertain"):
        action = "RECOVER_RLS_EFFECT"
    elif revision_state == "abandoned":
        action = "CREATE_RLS_REVISION"
    elif revision_state != "frozen":
        if any(x["result"] == "pending" for x in state.get("release_items", [])):
            action = "AUTHORIZE_RLS_EFFECT"
        elif any(x["result"] == "pending" for x in state.get("confirmations", [])):
            action = "CONFIRM_RLS_TARGET"
        else:
            action = "FINALIZE_RLS"
    elif gate not in {"pass", "pass_with_exception"}:
        action = "REPAIR_RLS_ARTIFACT"
    elif follow in {"return_req", "return_dsn", "return_pln", "return_imp"}:
        phase = follow.removeprefix("return_").upper()
        action = "RETURN_TO_" + phase
    elif follow == "retry_rls" or conclusion in {"partial", "failed"}:
        action = "RETRY_RLS"
    elif conclusion in {"success", "cancelled"}:
        phase, action = None, "LIFECYCLE_COMPLETE"
    else:
        action = "REPAIR_RLS_ARTIFACT"
    issues = [artifact.get("reference", "") + "#" + row["id"]
              for row in (state or {}).get("release_items", []) + (state or {}).get("confirmations", [])
              if row.get("follow_up", "").startswith("return_")]
    return {"artifact_reference": artifact.get("reference"), "revision_state": revision_state,
            "artifact_status": ("ready_with_exception" if gate == "pass_with_exception" else "ready") if revision_state == "frozen" and gate in {"pass", "pass_with_exception"} else "draft" if state else "absent",
            "release_conclusion": conclusion, "artifact_gate": gate, "follow_up": follow,
            "rls_applicability": applicability, "release_target": (state or {}).get("release_contract", {}).get("release_target"),
            "target_effect": bool((state or {}).get("target_effect")), "effect_uncertain": bool((state or {}).get("effect_uncertain")),
            "issue_references": issues, "next_phase": phase, "next_action": action}


class LifecycleQueryService(VfyLifecycleQueryService):
    def _rls_state(self, node):
        _require(not node.projection_errors and (node.revision_state != "frozen" or node.authority_state == "valid"),
                 "RLS Core authority or digest validation failed")
        stored = self.store.read_revision(node.artifact_id, node.revision)
        members = [x for x in stored.payload.members if x.member_id == "RLS-STATE"]
        _require(len(members) == 1, "RLS requires one persisted state Member")
        state = json.loads(members[0].raw_bytes)
        _require(state.get("state_contract") == "sdlc-ai-spec/rls-state/v1"
                 and state.get("contract") == "sdlc-ai-spec/rls-result/v1" and state.get("provisional") is False,
                 "RLS state is not a final persisted contract")
        parsed = parse_canonical_artifact(stored.payload.primary_blob)
        _require(state["artifact"]["reference"] == node.reference
                 and state["artifact_gate"] == node.gate_result
                 and state["context_reference"] == parsed.front_matter.get("context")
                 and state["input_references"] == parsed.front_matter.get("inputs"), "RLS canonical identity or authority differs")
        for key, headers in (("release_items", RLS_ITEM_HEADERS), ("confirmations", RLS_CONFIRMATION_HEADERS)):
            rows = require_single_table(parsed, headers, key).rows
            _require(len(rows) == len(state[key]), "RLS item coverage differs")
            for row, item in zip(rows, state[key]):
                _require(row["ID"] == item["id"] and row["结果 Result"] == item["result"]
                         and row["Follow-up Disposition"] == item["follow_up"]
                         and list(parse_reference_set(row["来源引用 Source References"])) == item["source_references"]
                         and list(parse_reference_set(row["证据引用 Evidence References"])) == item["evidence_references"],
                         "RLS Primary and state outcomes differ")
        summary = [row for table in parsed.tables for row in table.rows if row.get("Field") == "Conclusion"]
        _require(len(summary) == 1 and summary[0]["Value"] == state["release_conclusion"], "RLS Release Conclusion differs from Primary")
        state["artifact"]["revision_state"] = stored.control.state
        # Incomplete pre-effect intents are visible without writing or importing private RLS code.
        directory = self.project_root / ".sdlc/rls-execution" / node.reference
        if directory.is_dir():
            _require(not directory.is_symlink(), "RLS execution journal cannot be a symlink")
            records = []
            for path in sorted(directory.glob("*.json")):
                _require(not path.is_symlink(), "RLS execution record cannot be a symlink")
                records.append(json.loads(path.read_bytes()))
            pending = {x["attempt"] for x in records if x["stage"] == "intent"} - {x["attempt"] for x in records if x["stage"] == "persisted"}
            state["effect_uncertain"] = bool(state.get("effect_uncertain") or pending)
        return state

    def inspect_rls(self, reference):
        from packages.sdlc_runtime.canonical import exact_artifact_reference
        from packages.sdlc_artifact_store.catalog import ArtifactCatalog
        identity, revision = exact_artifact_reference(reference)
        _require(identity.startswith("RLS-"), "exact RLS reference is required")
        controls = [row for row in ArtifactCatalog(self.store).list_revisions(identity) if row.revision == revision]
        if len(controls) == 1 and controls[0].state == "abandoned" and not controls[0].materialized:
            return project_rls_state({"artifact": {"reference": reference, "revision_state": "abandoned"}, "artifact_gate": "pending"})
        node = self.read_node(reference)
        _require(node.artifact_type == "RLS", "exact RLS reference is required")
        return project_rls_state(self._rls_state(node))

    def inspect_requirement(self, requirement_reference):
        projection = super().inspect_requirement(requirement_reference)
        nodes = [node for node in projection.nodes if node.artifact_type == "RLS"]
        if not nodes:
            vfy = projection.vfy_projection
            if vfy is None:
                return projection
            return replace(projection, rls_projection=project_rls_state(None,
                applicability=vfy["rls_applicability"], vfy_ready=vfy["rls_ready"]))
        try:
            # A new Revision replaces its own Artifact lineage only; distinct targets
            # remain distinct and require explicit selection rather than silent reuse.
            latest = {}
            for node in nodes:
                if node.artifact_id not in latest or node.revision > latest[node.artifact_id].revision:
                    latest[node.artifact_id] = node
            states = [(node, self._rls_state(node)) for node in latest.values()]
            views = []
            vfy_view = projection.vfy_projection
            for node, state in states:
                vfy_reference = state["release_contract"]["vfy_reference"]
                vfy_node = self.read_node(vfy_reference)
                vfy_state = self._vfy_state(vfy_node)
                self._assert_vfy_subjects_current(vfy_state, projection)
                _require(state["release_contract"]["result_references"] == [x["reference"] for x in vfy_state["subjects"]]
                         and state["release_contract"]["scope_reference"] == vfy_state["scope"]["reference"], "RLS upstream Scope/Result binding is stale")
                vfy_view = project_vfy_state(vfy_state).to_dict()
                views.append(project_rls_state(state, applicability=vfy_state["rls_applicability"], vfy_ready=vfy_state["rls_ready"]))
            if len(views) != 1:
                action = self._action("SELECT_RLS_TARGET", "RLS", "多个 Release Target 需要明确选择", requires_user=True)
                return replace(projection, next_actions=(action,), overall_state="action_required",
                               rls_projection={"next_action": "SELECT_RLS_TARGET", "targets": views}, vfy_projection=vfy_view)
            current = views[0]
            action = NextAction("LIFECYCLE_COMPLETE", None, None, False,
                                "RLS 已冻结，Release Conclusion 与后续处置已确定", None, False) if current["next_phase"] is None else self._action(
                current["next_action"], current["next_phase"], "RLS 当前发布结论要求此唯一后续动作",
                "check --reference " + current["artifact_reference"])
            return replace(projection, next_actions=(action,), overall_state="complete" if current["next_phase"] is None else "action_required",
                           rls_projection=current, vfy_projection=vfy_view)
        except Exception as exc:
            return replace(projection, blockers=(*projection.blockers, _error(getattr(exc, "code", "RLS_STATE_INVALID"), "RLS authority or current upstream cannot be verified")),
                           overall_state="blocked", next_actions=(self._action("RESOLVE_RLS", "RLS", "RLS 精确状态读回失败"),), rls_projection=None)
