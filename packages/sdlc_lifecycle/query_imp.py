"""Read-only Current Claim, immutable IMP Result and VFY input projections."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import PurePosixPath
import re
import shlex
from typing import Mapping

from packages.sdlc_artifact_store import ArtifactStoreError, ControlReservationError, NotFoundError
from packages.sdlc_claim_provider import ClaimNotFoundError, ClaimProvider, binding_lineage
from packages.sdlc_runtime import parse_canonical_artifact
from packages.sdlc_runtime.canonical import require_single_row, require_single_table

from .errors import LifecycleArtifactError, LifecycleQueryError
from .models import ImpClaimProjection, LifecycleEdge, NextAction, PHASE_SKILLS
from .query import READY_STATUSES, _base_reference, _error, _exact_base_reference
from .query_pln import LifecycleQueryService as PlnLifecycleQueryService, WORK_ITEM_HEADERS, _tokens

BINDING_HEADERS = (
    "IMP Binding Reference", "Binding Lineage Key", "Attempt", "Owner", "Rework References",
)
RESULT_HEADERS = (
    "ID", "Resource", "Baseline Reference", "Change Reference", "Result Reference",
    "Changed Scope", "Approach Step References",
)
CLAIM_FIELDS = (
    "binding_lineage", "binding_reference", "artifact_id", "revision", "attempt",
    "owner", "execution_scope", "dependency_results", "rework_references",
)
EXACT_BINDING = re.compile(
    r"(?:(?:REQ|DSN)-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*"
    r"|PLN-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*#WI-[0-9]{3})"
)
ACTION_BLOCKERS = frozenset({"OPEN_ITEM", "IMP_REVISION_PENDING"})


def _require(condition, code, message):
    if not condition:
        raise LifecycleArtifactError(message, code=code)


def _ready(node):
    return (node.revision_state == "frozen" and node.artifact_status in READY_STATUSES
            and node.gate_result in {"pass", "pass_with_exception"}
            and node.authority_state == "valid" and not node.projection_errors and not node.open_items)


def _reference(claim):
    return f"{claim.artifact_id}@{claim.revision}"


class LifecycleQueryService(PlnLifecycleQueryService):
    """Keep canonical history visible; only Current Claims grant completion."""

    def _next_action_for(self, node, *, reason):
        # Generic frozen-Artifact routing cannot authorize IMP -> VFY.
        if node.artifact_type == "IMP":
            return None
        return super()._next_action_for(node, reason=reason)

    def _claim_read(self, operation, value):
        if self._provider is None:
            return None
        try:
            return getattr(self._provider, operation)(value)
        except Exception as exc:
            raise LifecycleQueryError(str(exc), code="IMP_CLAIM_STORE_INVALID") from exc

    def _remember(self, claim):
        if claim is not None:
            previous = self._claims.get(claim.artifact_id)
            _require(previous is None or previous == claim, "IMP_CLAIM_CHANGED",
                     "Current Claim changed during the query; inspect again")
            self._claims[claim.artifact_id] = claim
        return claim

    def _member(self, stored, identity):
        matches = [item for item in stored.payload.members if item.member_id == identity]
        _require(len(matches) == 1, "IMP_RESULT_INCOMPLETE", f"Immutable Member is missing or duplicated: {identity}")
        return matches[0]

    def _snapshot(self, stored, identity, resource):
        value = json.loads(self._member(stored, identity).raw_bytes)
        _require(isinstance(value, dict) and value.get("contract") == "sdlc-ai-spec/imp-resource-snapshot/v1"
                 and value.get("resource") == resource, "IMP_RESULT_INCOMPLETE", "Snapshot Resource or Contract mismatch")
        _require(isinstance(value.get("existed"), bool) and isinstance(value.get("entries"), list)
                 and isinstance(value.get("directories"), list), "IMP_RESULT_INCOMPLETE", "Incomplete immutable Snapshot")
        paths = []
        for item in value["entries"]:
            path = PurePosixPath(item["path"])
            _require(not path.is_absolute() and str(path) != "."
                     and not {"..", ".git", ".sdlc"}.intersection(path.parts),
                     "IMP_RESULT_INCOMPLETE", "Snapshot path is outside product resources")
            _require(hashlib.sha256(bytes.fromhex(item["content_hex"])).hexdigest() == item["sha256"],
                     "IMP_RESULT_INCOMPLETE", "Snapshot content does not match its digest")
            paths.append(item["path"])
        _require(paths == sorted(set(paths)), "IMP_RESULT_INCOMPLETE", "Snapshot paths are duplicated or unsorted")
        return value

    def _snapshot_reference(self, reference, resource, local):
        base, separator, member = reference.partition("/")
        _require(separator and member and "/" not in member and "#" not in member
                 and base.startswith("IMP-"), "IMP_RESULT_INCOMPLETE", "Result requires an exact immutable IMP Member")
        _exact_base_reference(base)
        if base == f"{local.control.artifact_id}@{local.control.revision}":
            stored = local
        else:
            node = self.read_node(base)
            _require(_ready(node), "IMP_RESULT_INCOMPLETE", "External Snapshot Authority is not frozen and ready")
            stored = self.store.read_revision(node.artifact_id, node.revision)
        return self._snapshot(stored, member, resource)

    def _results(self, stored, state, claim, parsed):
        rows = require_single_table(parsed, RESULT_HEADERS, "IMP Result Set").rows
        records = state["resources"]
        resources = sorted(token[9:] for token in claim.execution_scope if token.startswith("resource:"))
        _require(resources and len(set(resources)) == len(resources)
                 and [row["resource"] for row in records] == resources
                 and len(rows) == len(resources) and len({row["ID"] for row in rows}) == len(rows),
                 "IMP_RESULT_INCOMPLETE", "Result Set must contain one row per Claim Resource")
        result = []
        for row, record in zip(rows, records):
            resource = record["resource"]
            expected = (
                record["id"], resource, record["baseline_reference"], record["change_reference"],
                record["result_reference"], ", ".join(record["changed_scope"]) or "None",
                ", ".join(record["steps"]) or "None",
            )
            _require(tuple(row[key] for key in RESULT_HEADERS) == expected,
                     "IMP_RESULT_INCOMPLETE", "Canonical Result Set differs from retained immutable records")
            before = self._snapshot(stored, record["baseline_member"], resource)
            baseline = record["baseline_reference"]
            if baseline == "N/A":
                _require(not before["existed"], "IMP_RESULT_INCOMPLETE", "Existing Resource has no Baseline")
            else:
                _require(self._snapshot_reference(baseline, resource, stored) == before,
                         "IMP_RESULT_INCOMPLETE", "Baseline readback differs from retained Snapshot")
            if state["stage"] == "prepared":
                _require(record["result_reference"] == "N/A", "IMP_RESULT_INCOMPLETE", "Prepared IMP claims a Result")
            else:
                after = self._snapshot_reference(record["result_reference"], resource, stored)
                old, new = ({item["path"]: item for item in snapshot["entries"]} for snapshot in (before, after))
                paths = sorted(path for path in old.keys() | new.keys() if old.get(path) != new.get(path))
                prefix = f"path:{resource}/"
                scopes = [token for token in claim.execution_scope if token.startswith(prefix)]
                _require(all(not scopes or any(path == token[len(prefix):].rstrip("/")
                         or path.startswith(token[len(prefix):].rstrip("/") + "/") for token in scopes)
                         for path in paths), "IMP_RESULT_INCOMPLETE", "Result exceeds the Claim path Scope")
                changed_scope = [f"resource:{resource}", *(token for token in scopes if any(
                    path == token[len(prefix):].rstrip("/") or path.startswith(token[len(prefix):].rstrip("/") + "/")
                    for path in paths))] if paths else []
                _require(record["changed_paths"] == paths and record["changed_scope"] == changed_scope,
                         "IMP_RESULT_INCOMPLETE", "Changed Scope differs from immutable Result readback")
                if not paths:
                    _require(baseline == record["result_reference"] and record["change_reference"] == "N/A"
                             and not record["steps"], "IMP_RESULT_INCOMPLETE", "Unchanged Resource must retain Baseline=Result")
                else:
                    change = json.loads(self._member(stored, record["change_member"]).raw_bytes)
                    _require(record["change_reference"] == _reference(claim) + "/" + record["change_member"]
                             and change == {"resource": resource, "changed_paths": paths} and record["steps"],
                             "IMP_RESULT_INCOMPLETE", "Change Reference does not match immutable Evidence")
            result.append({
                "resource": resource, "baseline_reference": baseline,
                "result_reference": record["result_reference"], "changed_scope": record["changed_scope"],
            })
        return tuple(result)

    def _upstream_dependencies(self, claim, state, node):
        base = _base_reference(claim.binding_reference)
        _require(base in self._selected_references, "IMP_BINDING_MISMATCH",
                 "Current Binding is outside the selected exact requirement graph")
        upstream = self.read_node(base)
        _require(_ready(upstream) and node.context_reference == upstream.context_reference
                 and node.context_reference is not None and _ready(self.read_node(node.context_reference)),
                 "IMP_BINDING_MISMATCH", "IMP must preserve its exact ready upstream and real Context")
        binding = state["binding"]
        _require(binding["reference"] == claim.binding_reference and binding["lineage"] == claim.binding_lineage
                 and binding["context_reference"] == node.context_reference
                 and binding["execution_scope"] == list(claim.execution_scope)
                 and base in node.input_references, "IMP_BINDING_MISMATCH", "Retained Binding or input relationship differs")
        expected = ()
        if upstream.artifact_type == "PLN":
            parsed = parse_canonical_artifact(self.store.read_revision(upstream.artifact_id, upstream.revision).payload.primary_blob)
            rows = require_single_table(parsed, WORK_ITEM_HEADERS, "PLN Work Items").rows
            matches = [row for row in rows if row["ID"] == claim.binding_reference.split("#")[1]]
            _require(len(matches) == 1 and matches[0]["目标 Phase Target Phase"] == "IMP",
                     "IMP_BINDING_MISMATCH", "Binding must select one exact IMP Work Item")
            work = matches[0]
            _require(_tokens(work["执行范围 Execution Scope"]) == claim.execution_scope,
                     "IMP_BINDING_MISMATCH", "Claim Scope differs from the exact Work Item")
            expected = tuple(base + "#" + item for item in _tokens(work["依赖 Depends On"]))
        _require(binding["dependencies"] == list(expected), "IMP_DEPENDENCY_CHANGED", "Retained Work Item dependencies differ")
        dependencies = []
        for reference in expected:
            current = self._remember(self._claim_read("resolve", reference))
            _require(current is not None and current.binding_reference == reference and current.state == "completed",
                     "IMP_DEPENDENCY_CHANGED", "Predecessor is not the exact Current completed Binding")
            dependencies.append(_reference(current))
        _require(tuple(dependencies) == claim.dependency_results
                 and state["request"]["dependencies"] == dependencies
                 and set(dependencies).issubset(node.input_references),
                 "IMP_DEPENDENCY_CHANGED", "IMP references a superseded or incomplete predecessor Result")
        return tuple(dependencies)

    def _ancestors(self, reference, seen=frozenset()):
        if reference in seen:
            return set()
        record = next((claim for claim in self._claims.values() if _reference(claim) == reference), None)
        if record is None:
            return set()
        result = set(record.dependency_results)
        for dependency in record.dependency_results:
            result.update(self._ancestors(dependency, seen | {reference}))
        return result

    def _terminals(self, views):
        return tuple(view for view in views if not any(
            view.artifact_reference in self._ancestors(other.artifact_reference)
            for other in views if other.artifact_reference != view.artifact_reference
        ))

    def _project_claim(self, claim, stack=()):
        reference = _reference(claim)
        _require(reference not in stack, "IMP_DEPENDENCY_CHANGED", "Current Claim dependency graph contains a cycle")
        if reference in self._views:
            return self._views[reference]
        view = ImpClaimProjection(
            claim.binding_reference, claim.binding_lineage, reference, claim.owner, claim.attempt,
            claim.state, claim.execution_scope, claim.dependency_results,
        )
        blockers = []
        try:
            _require(EXACT_BINDING.fullmatch(claim.binding_reference) and claim.artifact_id.startswith("IMP-")
                     and binding_lineage(claim.binding_reference) == claim.binding_lineage
                     and claim.attempt > 0 and claim.revision > 0 and bool(claim.owner)
                     and claim.state in {"active", "completed", "abandoned"},
                     "IMP_CLAIM_MISMATCH", "Current Claim identity or State is invalid")
            stored = self.store.read_revision(claim.artifact_id, claim.revision)
            node = self.read_node(reference)
            view = replace(view, revision_state=node.revision_state, materialized=True)
            _require(not node.projection_errors and node.authority_state != "invalid",
                     "IMP_AUTHORITY_INVALID", "IMP digest, Gate or frozen Authority is invalid")
            _require(claim.state == "abandoned" or (node.artifact_status != "failed" and node.gate_result != "fail"),
                     "IMP_GATE_FAILED", "IMP contains failed local Checks or Gate")
            state = json.loads(self._member(stored, "IMP-STATE").raw_bytes)
            _require(isinstance(state, dict) and state.get("contract") == "sdlc-ai-spec/imp-state/v1",
                     "IMP_RESULT_INCOMPLETE", "IMP state Member is missing or invalid")
            identity = {key: value for key, value in asdict(claim).items() if key in CLAIM_FIELDS}
            _require(state["claim"] == json.loads(json.dumps(identity)),
                     "IMP_CLAIM_MISMATCH", "Artifact Snapshot differs from the Current Claim")
            reservation = stored.control.claim
            _require(reservation is not None and (reservation.binding_lineage, reservation.attempt, reservation.owner)
                     == (claim.binding_lineage, str(claim.attempt), claim.owner),
                     "IMP_CLAIM_MISMATCH", "Artifact Reservation differs from Current Owner or Attempt")
            parsed = parse_canonical_artifact(stored.payload.primary_blob)
            binding = require_single_row(require_single_table(parsed, BINDING_HEADERS, "IMP Binding"), "IMP Binding")
            _require(tuple(binding[key] for key in BINDING_HEADERS) == (
                claim.binding_reference, claim.binding_lineage, str(claim.attempt), claim.owner,
                ", ".join(claim.rework_references) or "None",
            ), "IMP_CLAIM_MISMATCH", "Canonical Binding differs from the Current Claim")
            _require(state["request"]["artifact_inputs"] == list(node.input_references),
                     "IMP_BINDING_MISMATCH", "Canonical inputs differ from retained request")
            _require(state["request"]["rework"] == list(claim.rework_references),
                     "IMP_CLAIM_MISMATCH", "Retained Rework differs from the Current Claim")
            dependencies = self._upstream_dependencies(claim, state, node)
            for dependency in dependencies:
                predecessor = self._remember(self._claim_read("resolve_artifact", dependency.split("@", 1)[0]))
                _require(predecessor is not None and _reference(predecessor) == dependency
                         and self._project_claim(predecessor, (*stack, reference)).completed,
                         "IMP_DEPENDENCY_CHANGED", "A transitive predecessor is no longer Current completed")
            _require(state["stage"] in {"prepared", "executed"}, "IMP_RESULT_INCOMPLETE", "Unsupported IMP execution state")
            results = self._results(stored, state, claim, parsed)
            view = replace(view, outcome=state["binding"]["outcome"], results=results)
            for row in results:
                predecessors = [item for key, item in self._views.items() if key in self._ancestors(reference)
                                and any(result["resource"] == row["resource"] for result in item.results)]
                terminals = self._terminals(predecessors)
                _require(len(terminals) <= 1, "IMP_DEPENDENCY_CHANGED", "Resource predecessors have no unique terminal Result")
                if terminals:
                    previous = next(result for result in terminals[0].results if result["resource"] == row["resource"])
                    _require(row["baseline_reference"] == previous["result_reference"],
                             "IMP_DEPENDENCY_CHANGED", "Successor Baseline does not absorb its Current predecessor Result")
            if claim.state == "completed":
                _require(_ready(node) and state["stage"] == "executed", "IMP_REVISION_NOT_READY",
                         "Completed Claim requires a frozen ready IMP with immutable Results")
                view = replace(view, completed=True)
            elif claim.state == "active":
                _require(node.revision_state in {"open", "frozen"}, "IMP_CLAIM_MISMATCH", "Active Claim has no usable Revision")
                blockers.extend(_error("OPEN_ITEM", f"Open Item {item.item_id} requires resolution", reference)
                                for item in node.open_items)
            # Abandoned is a recoverable execution state, not current completion.
        except (ControlReservationError, NotFoundError) as exc:
            blockers.append(_error("IMP_REVISION_PENDING" if claim.state == "active" else "IMP_REVISION_MISSING",
                                   str(exc), reference))
        except (LifecycleQueryError, ArtifactStoreError, ValueError, KeyError, TypeError) as exc:
            blockers.append(_error(getattr(exc, "code", "IMP_RESULT_INCOMPLETE"), str(exc), reference))
        view = replace(view, completed=view.completed and not blockers, blockers=tuple(blockers))
        self._views[reference] = view
        return view

    def _action(self, code, phase, reason, arguments=None, *, requires_user=True):
        skill = PHASE_SKILLS[phase]
        available = self.skill_available(skill)
        return NextAction(code, phase, skill, available, reason,
                          f"/{skill} {arguments}" if available and arguments else None,
                          requires_user or not available)

    def _claim_action(self, view):
        if view.claim_state == "abandoned":
            return self._action("RETRY_OR_REWORK_IMP", "IMP",
                                f"{view.binding_reference} 已放弃；需要明确重试或提供合法 Rework")
        if view.completed:
            return None
        reference = shlex.quote(view.artifact_reference)
        if any(item["code"] not in ACTION_BLOCKERS for item in view.blockers):
            return self._action("RESOLVE_IMP_CLAIM", "IMP",
                                f"{view.binding_reference} 的 Claim、Result 或依赖需处理",
                                f"check --reference {reference}")
        arguments = (f"revise --reference {reference}" if view.materialized else
                     f"auto --binding {shlex.quote(view.binding_reference)}")
        return self._action("RESUME_IMP", "IMP",
                            f"{view.binding_reference} 由 {view.owner} 继续 Attempt {view.attempt}",
                            arguments + f" --owner {shlex.quote(view.owner)}")

    def inspect_requirement(self, requirement_reference):
        # A service may be reused after a producer advances an open Revision or Claim.
        self._node_cache.clear()
        self._dsn_applicability.clear()
        self._pln_work_items.clear()
        self._claims, self._views = {}, {}
        try:
            self._provider = ClaimProvider.open_read_only(self.project_root)
        except ClaimNotFoundError:
            self._provider = None
        except Exception as exc:
            raise LifecycleQueryError(str(exc), code="IMP_CLAIM_STORE_INVALID") from exc
        projection = super().inspect_requirement(requirement_reference)
        self._selected_references = {node.reference for node in projection.nodes}
        missing = []
        plans = []
        for node in projection.nodes:
            if node.artifact_type == "IMP":
                if self._remember(self._claim_read("resolve_artifact", node.artifact_id)) is None:
                    missing.append(_error("IMP_CLAIM_MISSING", "IMP has no readable Current Claim", node.reference))
            elif node.artifact_type in {"REQ", "DSN"}:
                self._remember(self._claim_read("resolve", node.reference))
            elif node.artifact_type == "PLN" and _ready(node):
                items = self._read_pln_work_items(node)
                if not isinstance(items, Mapping):
                    plans.append((node, items))
                    for item in items:
                        if item.target_phase == "IMP":
                            self._remember(self._claim_read("resolve", node.reference + "#" + item.item_id))
        if not self._claims and not missing:
            return projection
        for claim in tuple(self._claims.values()):
            self._project_claim(claim)
        views = tuple(sorted(self._views.values(), key=lambda view: view.binding_reference))
        historical_imp = {node.reference for node in projection.nodes if node.artifact_type == "IMP"}
        superseded_plans = {node.reference for node, _ in plans if any(
            claim.binding_reference.startswith(node.artifact_id + "@")
            and int(_base_reference(claim.binding_reference).split("@")[1]) > node.revision
            for claim in self._claims.values()
        )}
        blockers = [dict(item) for item in projection.blockers
                    if item.get("reference") not in historical_imp | superseded_plans]
        blockers.extend(missing)
        blockers.extend(dict(item) for view in views for item in view.blockers)
        actions = [action for view in views if (action := self._claim_action(view)) is not None]
        pending_imp = any(not view.completed for view in views) or bool(missing)
        vfy_work = []
        occupied_resources = {token for view in views if view.claim_state == "active"
                              for token in view.execution_scope if token.startswith("resource:")}
        for node, items in plans:
            if node.reference in superseded_plans:
                continue
            parsed = parse_canonical_artifact(self.store.read_revision(node.artifact_id, node.revision).payload.primary_blob)
            scopes = {row["ID"]: set(_tokens(row["执行范围 Execution Scope"]))
                      for row in require_single_table(parsed, WORK_ITEM_HEADERS, "PLN Work Items").rows}
            complete = {item.item_id for item in items if any(
                view.binding_reference == node.reference + "#" + item.item_id and view.completed for view in views
            )}
            for item in items:
                binding = node.reference + "#" + item.item_id
                if item.target_phase == "IMP" and item.item_id not in complete:
                    pending_imp = True
                    existing = self._claim_read("resolve", binding)
                    if (existing is None and set(item.depends_on).issubset(complete)
                            and not scopes[item.item_id].intersection(occupied_resources)):
                        actions.append(self._action("START_WORK_ITEM", "IMP", f"依赖已满足，可执行 {binding}",
                                                    f"create --binding {shlex.quote(binding)}", requires_user=False))
                    elif existing is not None and existing.binding_reference != binding:
                        if existing.state == "active":
                            actions.append(self._action("RESOLVE_IMP_BINDING", "IMP",
                                f"{binding} 与 active Claim 不同；需先明确当前 Attempt 的继续或放弃决定"))
                        else:
                            actions.append(self._action("REWORK_IMP_BINDING", "IMP", f"{binding} 需要吸收准确的新 Binding",
                                f"revise --reference {shlex.quote(_reference(existing))} --binding {shlex.quote(binding)} "
                                f"--input {shlex.quote(binding)} --owner {shlex.quote(existing.owner)}"))
                elif item.target_phase == "VFY" and set(item.depends_on).issubset(complete):
                    vfy_work.append(binding)

        candidates = []
        for resource in sorted({row["resource"] for view in views for row in view.results}):
            terminals = self._terminals([view for view in views if view.completed
                                        and any(row["resource"] == resource for row in view.results)])
            if len(terminals) > 1:
                blockers.append(_error("IMP_RESULT_AMBIGUOUS", f"Resource {resource} has multiple unordered completed Results"))
            elif terminals:
                result = next(row for row in terminals[0].results if row["resource"] == resource)
                candidates.append({"resource": resource, "artifact_reference": terminals[0].artifact_reference,
                                   "result_reference": result["result_reference"]})
        hard_blocker = any(item["code"] not in ACTION_BLOCKERS for item in blockers)
        vfy_results = tuple(candidates) if not pending_imp and not hard_blocker else ()
        vfy_inputs = tuple(sorted({item["artifact_reference"] for item in vfy_results}))
        views = tuple(replace(view, vfy_ready=view.artifact_reference in vfy_inputs) for view in views)
        if vfy_inputs:
            inputs = " ".join(f"--input {shlex.quote(reference)}" for reference in vfy_inputs)
            for binding in vfy_work or (None,):
                reason = "当前 IMP Claim、冻结 Result 和依赖链有效，可进入 VFY"
                if binding:
                    reason += f"：{binding}"
                arguments = f"create {inputs}" + (f" --input {shlex.quote(binding)}" if binding else "")
                actions.append(self._action("START_VFY", "VFY", reason, arguments, requires_user=False))
        elif not actions and hard_blocker:
            actions.append(self._action("RESOLVE_IMP_CLAIM", "IMP", "处理当前 Claim 或 Result 阻塞后重新查询"))

        edges = set(projection.edges)
        for claim in self._claims.values():
            target = _reference(claim)
            if target not in {node.reference for node in projection.nodes}:
                continue
            edges.add(LifecycleEdge(_base_reference(claim.binding_reference), target,
                                    "control_input" if "#" in claim.binding_reference else "scope_input",
                                    claim.binding_reference))
            for dependency in claim.dependency_results:
                edges.add(LifecycleEdge(dependency, target, "scope_input", dependency))
            for control in claim.rework_references:
                if control.startswith(("VFY-", "RLS-")):
                    edges.add(LifecycleEdge(_base_reference(control), target,
                                            "return" if control.startswith("VFY-") else "issue", control))
        controls = {_base_reference(reference) for claim in self._claims.values()
                    for reference in claim.rework_references if reference.startswith(("VFY-", "RLS-"))}
        effective = {node.reference for node in projection.nodes if node.artifact_type != "CTX"
                     and node.reference not in superseded_plans | controls
                     and (node.artifact_type != "IMP" or node.reference in self._views)}
        frontier = tuple(sorted(reference for reference in effective if not any(
            edge.source_reference == reference and edge.target_reference in effective for edge in edges
        )))
        overall = ("blocked" if hard_blocker else "action_required" if pending_imp
                   else "parallel" if len(vfy_inputs) > 1 else "ready_for_next_phase")
        downstream = [node for node in projection.nodes if node.reference in frontier
                      and node.artifact_type in {"VFY", "RLS"}]
        if downstream and len(downstream) == len(frontier) and not pending_imp:
            # Preserve existing later-phase routing only when its ancestry
            # actually consumes all current terminal IMP inputs.
            ancestors = set(frontier)
            pending = list(frontier)
            while pending:
                target = pending.pop()
                for edge in edges:
                    if edge.target_reference == target and edge.source_reference not in ancestors:
                        ancestors.add(edge.source_reference)
                        pending.append(edge.source_reference)
            terminals = {item["artifact_reference"] for item in candidates}
            if terminals and terminals.issubset(ancestors):
                actions = [action for node in downstream if (action := self._next_action_for(
                    node, reason="当前后续 Artifact 已引用准确 IMP 输入，继续处理其生命周期前沿",
                )) is not None]
                overall = projection.overall_state
        for claim in tuple(self._claims.values()):
            _require(self._claim_read("resolve", claim.binding_lineage) == claim
                     and self._claim_read("resolve_artifact", claim.artifact_id) == claim,
                     "IMP_CLAIM_CHANGED", "Current Claim changed during the query; inspect again")
        return replace(
            projection, current_claims=views, vfy_inputs=vfy_inputs, vfy_results=vfy_results, frontier=frontier,
            edges=tuple(sorted(edges, key=lambda edge: (edge.target_reference, edge.relation, edge.declared_reference))),
            blockers=tuple(blockers), next_actions=tuple(dict.fromkeys(actions)),
            overall_state=overall,
        )


__all__ = ("LifecycleQueryService",)
