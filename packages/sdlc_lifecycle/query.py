"""Strictly read-only lifecycle graph and status projections."""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from packages.sdlc_artifact_store import (
    ArtifactStore,
    ArtifactStoreError,
    DomainVerifier,
    RevisionControlRecord,
    StoredRevision,
    StoreNotFoundError,
)
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_runtime import (
    FrozenArtifactAuthorityVerifier,
    exact_artifact_reference,
    parse_canonical_artifact,
)
from packages.sdlc_runtime.canonical import (
    CanonicalFormatError,
    GATE_SUMMARY_HEADERS,
    find_tables,
)

from .errors import (
    LifecycleArtifactError,
    LifecycleQueryError,
    LifecycleReferenceError,
    LifecycleStoreUnavailable,
)
from .models import (
    LifecycleEdge,
    LifecycleNode,
    LifecycleProjection,
    NextAction,
    OpenItemProjection,
    PHASE_ORDER,
    PHASE_SKILLS,
    NEXT_PHASE,
    ProjectOverview,
    RequirementCandidate,
)

READY_STATUSES = frozenset({"ready", "ready_with_exception"})
TERMINAL_BAD_STATES = frozenset({"abandoned"})
OPEN_ITEM_ID_PREFIX = "OPI-"


def _error(code: str, message: str, reference: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"code": code, "message": message}
    if reference is not None:
        result["reference"] = reference
    return result


def _base_reference(value: str) -> str:
    try:
        artifact_id, revision = exact_artifact_reference(value)
    except (CanonicalFormatError, TypeError) as exc:
        raise LifecycleReferenceError(
            "Reference must contain an exact Artifact ID and numeric Revision",
            details={"reference": value},
        ) from exc
    return f"{artifact_id}@{revision}"


def _exact_base_reference(value: str) -> str:
    base = _base_reference(value)
    if value != base:
        raise LifecycleReferenceError(
            "Lifecycle node selection must use a base Artifact@Revision Reference",
            details={"reference": value, "base_reference": base},
        )
    return base


def _input_relation(reference: str) -> str:
    if "#RET-" in reference:
        return "return"
    if "#RLI-" in reference or "#RCF-" in reference:
        return "issue"
    if "#" in reference or "/" in reference.split("@", 1)[-1]:
        return "control_input"
    return "scope_input"


def _gate_result(parsed) -> tuple[str, tuple[Mapping[str, Any], ...]]:
    matches = find_tables(parsed, GATE_SUMMARY_HEADERS)
    if len(matches) != 1 or len(matches[0].rows) != 1:
        return (
            "unknown",
            (
                _error(
                    "GATE_SUMMARY_INVALID",
                    "Gate Summary must appear exactly once with one current row",
                ),
            ),
        )
    value = matches[0].rows[0].get("Gate Result", "")
    if value not in {"pending", "pass", "pass_with_exception", "fail"}:
        return (
            "unknown",
            (_error("GATE_RESULT_INVALID", f"Unsupported Gate Result: {value}"),),
        )
    return value, ()


def _find_open_items(parsed) -> tuple[OpenItemProjection, ...]:
    items: list[OpenItemProjection] = []
    for table in parsed.tables:
        if "ID" not in table.headers:
            continue
        state_keys = tuple(
            key for key in table.headers if key == "State" or "状态 State" in key
        )
        if len(state_keys) != 1:
            continue
        state_key = state_keys[0]
        needed_key = next(
            (
                key
                for key in table.headers
                if "Needed Input" in key
                or "所需输入" in key
                or key == "Needed"
            ),
            None,
        )
        source_key = next(
            (
                key
                for key in table.headers
                if "Expected Source" in key or "预期来源" in key
            ),
            None,
        )
        blocked_key = next(
            (
                key
                for key in table.headers
                if "Blocked References" in key or "被阻塞项" in key
            ),
            None,
        )
        resolution_key = next(
            (
                key
                for key in table.headers
                if "Resolution" in key or "解决" in key
            ),
            None,
        )
        for row in table.rows:
            item_id = row.get("ID", "").strip()
            if not item_id.startswith(OPEN_ITEM_ID_PREFIX):
                continue
            state = row.get(state_key, "").strip().lower()
            if state != "open":
                continue
            blocked_raw = row.get(blocked_key, "") if blocked_key else ""
            blocked = tuple(
                part.strip()
                for part in blocked_raw.split(",")
                if part.strip() and part.strip() not in {"None", "N/A"}
            )
            items.append(
                OpenItemProjection(
                    item_id=item_id,
                    state=state,
                    needed=(row.get(needed_key) if needed_key else None),
                    expected_source=(row.get(source_key) if source_key else None),
                    blocked_references=blocked,
                    resolution=(row.get(resolution_key) if resolution_key else None),
                )
            )
    return tuple(sorted(items, key=lambda item: item.item_id))


class LifecycleQueryService:
    """Read exact Artifact revisions and compute non-authoritative projections."""

    def __init__(
        self,
        project_root: Path | str,
        *,
        plugin_root: Path | str | None = None,
        verifier_factory: Callable[[Path], DomainVerifier] | None = None,
    ) -> None:
        root = Path(project_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise LifecycleStoreUnavailable(
                f"Project root is not an existing directory: {root}"
            )
        self.project_root = root
        self.plugin_root = (
            Path(plugin_root).expanduser().resolve()
            if plugin_root is not None
            else Path(__file__).resolve().parents[2]
        )
        try:
            self.store = ArtifactStore.open_read_only(root)
        except StoreNotFoundError as exc:
            raise LifecycleStoreUnavailable(str(exc)) from exc
        self.catalog = ArtifactCatalog(self.store)
        self.verifier = (
            verifier_factory(root)
            if verifier_factory is not None
            else FrozenArtifactAuthorityVerifier(root)
        )
        self._node_cache: dict[str, LifecycleNode] = {}

    def skill_available(self, skill_name: str | None) -> bool:
        if not skill_name:
            return False
        return (self.plugin_root / "skills" / skill_name / "SKILL.md").is_file()

    def _projection_failure_node(
        self,
        stored: StoredRevision,
        reference: str,
        errors: Sequence[Mapping[str, Any]],
    ) -> LifecycleNode:
        return LifecycleNode(
            reference=reference,
            artifact_id=stored.control.artifact_id,
            artifact_type=stored.payload.artifact_type,
            revision=stored.control.revision,
            revision_state=stored.control.state,
            artifact_status=stored.payload.artifact_status,
            materialized=stored.control.materialized,
            allocated_at=stored.control.allocated_at,
            frozen_at=stored.control.frozen_at,
            gate_result="unknown",
            authority_state="invalid",
            authority_error=_error(
                "ARTIFACT_PROJECTION_INVALID",
                "Artifact bytes cannot produce a trustworthy lifecycle projection",
                reference,
            ),
            context_reference=None,
            input_references=(),
            open_items=(),
            projection_errors=tuple(dict(item) for item in errors),
        )

    def read_node(self, reference: str) -> LifecycleNode:
        base = _exact_base_reference(reference)
        cached = self._node_cache.get(base)
        if cached is not None:
            return cached
        artifact_id, revision = exact_artifact_reference(base)
        try:
            stored = self.store.read_revision(artifact_id, revision)
        except ArtifactStoreError as exc:
            raise LifecycleArtifactError(
                str(exc),
                code=getattr(exc, "code", "LIFECYCLE_ARTIFACT_INVALID"),
                details={"reference": base},
            ) from exc
        if not stored.control.materialized:
            raise LifecycleArtifactError(
                "Revision is only a Control Reservation and has no Artifact payload",
                code="CONTROL_RESERVATION",
                details={"reference": base},
            )

        projection_errors: list[Mapping[str, Any]] = []
        try:
            self.store.verify_digest(artifact_id, revision)
        except ArtifactStoreError as exc:
            projection_errors.append(
                _error(
                    getattr(exc, "code", "DIGEST_INVALID"),
                    str(exc),
                    base,
                )
            )
        try:
            parsed = parse_canonical_artifact(stored.payload.primary_blob)
        except CanonicalFormatError as exc:
            projection_errors.append(_error(exc.code, str(exc), base))
            node = self._projection_failure_node(stored, base, projection_errors)
            self._node_cache[base] = node
            return node

        front = parsed.front_matter
        if front.get("id") != artifact_id:
            projection_errors.append(
                _error("ARTIFACT_ID_MISMATCH", "Front Matter id does not match Store", base)
            )
        if front.get("revision") != revision:
            projection_errors.append(
                _error(
                    "ARTIFACT_REVISION_MISMATCH",
                    "Front Matter revision does not match Store",
                    base,
                )
            )
        if front.get("status") != stored.payload.artifact_status:
            projection_errors.append(
                _error(
                    "ARTIFACT_STATUS_MISMATCH",
                    "Front Matter status does not match Store",
                    base,
                )
            )
        expected_type = (
            "CTX"
            if front.get("contract") == "sdlc-ai-spec/project-context/v1"
            else front.get("phase")
        )
        if expected_type != stored.payload.artifact_type:
            projection_errors.append(
                _error(
                    "ARTIFACT_TYPE_MISMATCH",
                    "Front Matter contract/phase does not match Store Artifact Type",
                    base,
                )
            )

        gate, gate_errors = _gate_result(parsed)
        projection_errors.extend(gate_errors)
        context_reference = front.get("context")
        if not isinstance(context_reference, str):
            context_reference = None
        else:
            try:
                context_reference = _exact_base_reference(context_reference)
            except LifecycleQueryError as exc:
                projection_errors.append(exc.to_dict())
                context_reference = None

        raw_inputs = front.get("inputs", [])
        input_references: list[str] = []
        if raw_inputs is None:
            raw_inputs = []
        if not isinstance(raw_inputs, list) or any(
            not isinstance(item, str) for item in raw_inputs
        ):
            projection_errors.append(
                _error(
                    "ARTIFACT_INPUTS_INVALID",
                    "Front Matter inputs must be an array of exact References",
                    base,
                )
            )
        else:
            for item in raw_inputs:
                try:
                    _base_reference(item)
                except LifecycleQueryError as exc:
                    projection_errors.append(exc.to_dict())
                else:
                    input_references.append(item)

        authority_state = "not_applicable"
        authority_error: Mapping[str, Any] | None = None
        if (
            stored.control.state == "frozen"
            and stored.payload.artifact_status in READY_STATUSES
        ):
            try:
                self.store.resolve_exact_reference(base, verifier=self.verifier)
            except ArtifactStoreError as exc:
                authority_state = "invalid"
                authority_error = _error(
                    getattr(exc, "code", "AUTHORITY_INVALID"),
                    str(exc),
                    base,
                )
            else:
                authority_state = "valid"

        node = LifecycleNode(
            reference=base,
            artifact_id=artifact_id,
            artifact_type=stored.payload.artifact_type,
            revision=revision,
            revision_state=stored.control.state,
            artifact_status=stored.payload.artifact_status,
            materialized=stored.control.materialized,
            allocated_at=stored.control.allocated_at,
            frozen_at=stored.control.frozen_at,
            gate_result=gate,
            authority_state=authority_state,
            authority_error=authority_error,
            context_reference=context_reference,
            input_references=tuple(input_references),
            open_items=_find_open_items(parsed),
            projection_errors=tuple(dict(item) for item in projection_errors),
        )
        self._node_cache[base] = node
        return node

    def _controls(
        self, artifact_type: str | None = None
    ) -> tuple[RevisionControlRecord, ...]:
        records: list[RevisionControlRecord] = []
        for summary in self.catalog.list_artifacts(artifact_type):
            records.extend(self.catalog.list_revisions(summary.artifact_id))
        return tuple(records)

    def all_materialized_nodes(
        self, artifact_type: str | None = None
    ) -> tuple[LifecycleNode, ...]:
        nodes: list[LifecycleNode] = []
        for control in self._controls(artifact_type):
            if not control.materialized:
                continue
            nodes.append(
                self.read_node(f"{control.artifact_id}@{control.revision}")
            )
        return tuple(
            sorted(
                nodes,
                key=lambda item: (
                    PHASE_ORDER.index(item.artifact_type),
                    item.artifact_id,
                    item.revision,
                ),
            )
        )

    def list_requirements(self) -> tuple[RequirementCandidate, ...]:
        controls_by_artifact: dict[str, list[RevisionControlRecord]] = defaultdict(list)
        for control in self._controls("REQ"):
            controls_by_artifact[control.artifact_id].append(control)
        result: list[RequirementCandidate] = []
        for artifact_id, controls in controls_by_artifact.items():
            materialized = [item for item in controls if item.materialized]
            head_revision = max((item.revision for item in materialized), default=None)
            for control in materialized:
                node = self.read_node(f"{artifact_id}@{control.revision}")
                result.append(
                    RequirementCandidate(
                        reference=node.reference,
                        artifact_id=node.artifact_id,
                        revision=node.revision,
                        revision_state=node.revision_state,
                        artifact_status=node.artifact_status,
                        gate_result=node.gate_result,
                        authority_state=node.authority_state,
                        open_item_count=len(node.open_items),
                        lineage_head=node.revision == head_revision,
                    )
                )
        return tuple(
            sorted(
                result,
                key=lambda item: (item.artifact_id, item.revision),
            )
        )

    def _edges_for(self, node: LifecycleNode) -> tuple[LifecycleEdge, ...]:
        edges: list[LifecycleEdge] = []
        if node.context_reference:
            edges.append(
                LifecycleEdge(
                    source_reference=node.context_reference,
                    target_reference=node.reference,
                    relation="context",
                    declared_reference=node.context_reference,
                )
            )
        for declared in node.input_references:
            edges.append(
                LifecycleEdge(
                    source_reference=_base_reference(declared),
                    target_reference=node.reference,
                    relation=_input_relation(declared),
                    declared_reference=declared,
                )
            )
        return tuple(edges)

    def build_graph(
        self, requirement_reference: str
    ) -> tuple[
        tuple[LifecycleNode, ...],
        tuple[LifecycleEdge, ...],
        tuple[Mapping[str, Any], ...],
    ]:
        root_reference = _exact_base_reference(requirement_reference)
        root = self.read_node(root_reference)
        if root.artifact_type != "REQ":
            raise LifecycleReferenceError(
                "Lifecycle inspection root must be a REQ Artifact",
                details={"reference": root_reference, "artifact_type": root.artifact_type},
            )

        all_nodes = {item.reference: item for item in self.all_materialized_nodes()}
        all_nodes[root.reference] = root
        all_edges = tuple(
            edge for node in all_nodes.values() for edge in self._edges_for(node)
        )
        incoming: dict[str, list[LifecycleEdge]] = defaultdict(list)
        outgoing: dict[str, list[LifecycleEdge]] = defaultdict(list)
        for edge in all_edges:
            incoming[edge.target_reference].append(edge)
            outgoing[edge.source_reference].append(edge)

        descendants: set[str] = {root_reference}
        queue: deque[str] = deque([root_reference])
        while queue:
            current = queue.popleft()
            for edge in outgoing.get(current, ()):
                if edge.target_reference not in descendants:
                    descendants.add(edge.target_reference)
                    queue.append(edge.target_reference)

        included = set(descendants)
        queue = deque(descendants)
        while queue:
            current = queue.popleft()
            for edge in incoming.get(current, ()):
                if edge.source_reference in all_nodes and edge.source_reference not in included:
                    included.add(edge.source_reference)
                    queue.append(edge.source_reference)

        missing: list[Mapping[str, Any]] = []
        selected_edges: list[LifecycleEdge] = []
        for edge in all_edges:
            if edge.target_reference not in included:
                continue
            if edge.source_reference not in all_nodes:
                missing.append(
                    _error(
                        "DEPENDENCY_MISSING",
                        f"Declared {edge.relation} dependency cannot be read",
                        edge.declared_reference,
                    )
                )
                selected_edges.append(edge)
                continue
            if edge.source_reference in included:
                selected_edges.append(edge)

        selected_nodes = tuple(
            sorted(
                (all_nodes[reference] for reference in included),
                key=lambda item: (
                    PHASE_ORDER.index(item.artifact_type),
                    item.artifact_id,
                    item.revision,
                ),
            )
        )
        return (
            selected_nodes,
            tuple(
                sorted(
                    selected_edges,
                    key=lambda item: (
                        item.target_reference,
                        item.relation,
                        item.source_reference,
                    ),
                )
            ),
            tuple(missing),
        )

    def _next_action_for(
        self, node: LifecycleNode, *, reason: str
    ) -> NextAction | None:
        if node.revision_state == "abandoned":
            return NextAction(
                code="SELECT_USABLE_REVISION",
                phase=node.artifact_type,
                skill=PHASE_SKILLS.get(node.artifact_type),
                skill_available=self.skill_available(PHASE_SKILLS.get(node.artifact_type)),
                reason=reason,
                command=None,
                requires_user=True,
            )
        if (
            node.revision_state == "open"
            or node.artifact_status in {"draft", "waiting_input", "failed"}
            or node.gate_result in {"pending", "fail", "unknown"}
            or node.open_items
        ):
            skill = PHASE_SKILLS.get(node.artifact_type)
            available = self.skill_available(skill)
            command = (
                f"/{skill} revise --reference {node.reference}"
                if skill and available
                else None
            )
            return NextAction(
                code="RESOLVE_CURRENT_PHASE",
                phase=node.artifact_type,
                skill=skill,
                skill_available=available,
                reason=reason,
                command=command,
                requires_user=True,
            )

        next_phase = NEXT_PHASE.get(node.artifact_type)
        if next_phase is None:
            return None
        skill = PHASE_SKILLS[next_phase]
        available = self.skill_available(skill)
        return NextAction(
            code="START_NEXT_PHASE",
            phase=next_phase,
            skill=skill,
            skill_available=available,
            reason=reason,
            command=(
                f"/{skill} create --reference {node.reference}" if available else None
            ),
            requires_user=not available,
        )

    def inspect_requirement(self, requirement_reference: str) -> LifecycleProjection:
        root_reference = _exact_base_reference(requirement_reference)
        nodes, edges, missing = self.build_graph(root_reference)
        by_reference = {item.reference: item for item in nodes}
        root = by_reference[root_reference]
        blockers: list[Mapping[str, Any]] = [dict(item) for item in missing]
        hard_blocker = bool(missing)

        for node in nodes:
            if node.projection_errors:
                hard_blocker = True
            blockers.extend(dict(item) for item in node.projection_errors)
            if node.authority_state == "invalid" and node.authority_error:
                hard_blocker = True
                blockers.append(dict(node.authority_error))
            if node.revision_state in TERMINAL_BAD_STATES:
                hard_blocker = True
                blockers.append(
                    _error(
                        "REVISION_ABANDONED",
                        "Abandoned Revision cannot provide lifecycle authority",
                        node.reference,
                    )
                )
            if node.artifact_status == "failed" or node.gate_result == "fail":
                hard_blocker = True
                blockers.append(
                    _error(
                        "PHASE_FAILED",
                        "Artifact or Gate is failed",
                        node.reference,
                    )
                )
            for item in node.open_items:
                blockers.append(
                    _error(
                        "OPEN_ITEM",
                        f"Open Item {item.item_id} requires resolution",
                        node.reference,
                    )
                )

        outgoing: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            if edge.source_reference in by_reference and edge.target_reference in by_reference:
                outgoing[edge.source_reference].append(edge.target_reference)
        descendants = {
            item.reference
            for item in nodes
            if item.reference == root_reference or item.artifact_type != "CTX"
        }
        frontier = tuple(
            sorted(
                reference
                for reference in descendants
                if not any(target in descendants for target in outgoing.get(reference, ()))
            )
        )

        next_actions: list[NextAction] = []
        for reference in frontier:
            node = by_reference[reference]
            action = self._next_action_for(
                node,
                reason=(
                    "当前前沿尚未满足进入下一阶段的条件"
                    if (
                        node.revision_state != "frozen"
                        or node.artifact_status not in READY_STATUSES
                        or node.gate_result not in {"pass", "pass_with_exception"}
                        or node.authority_state != "valid"
                    )
                    else "当前前沿已通过，可进入下一阶段"
                ),
            )
            if action is not None:
                next_actions.append(action)

        if hard_blocker:
            overall = "blocked"
        elif any(
            by_reference[reference].revision_state != "frozen"
            or by_reference[reference].artifact_status not in READY_STATUSES
            or by_reference[reference].gate_result not in {"pass", "pass_with_exception"}
            for reference in frontier
        ):
            overall = "action_required"
        elif frontier and all(by_reference[item].artifact_type == "RLS" for item in frontier):
            overall = "complete"
        elif len(frontier) > 1:
            overall = "parallel"
        elif any(
            item.reference != root_reference and item.artifact_type != "CTX"
            for item in nodes
        ):
            overall = "in_progress"
        else:
            overall = "ready_for_next_phase"

        return LifecycleProjection(
            root_reference=root_reference,
            overall_state=overall,
            nodes=nodes,
            edges=edges,
            frontier=frontier,
            blockers=tuple(blockers),
            next_actions=tuple(next_actions),
        )

    def project_overview(self) -> ProjectOverview:
        contexts = self.all_materialized_nodes("CTX")
        requirements = self.list_requirements()
        active = tuple(
            item
            for item in requirements
            if item.lineage_head and item.revision_state != "abandoned"
        )

        if not contexts and not requirements:
            skill = PHASE_SKILLS["CTX"]
            return ProjectOverview(
                state="not_started",
                context_candidates=(),
                requirement_candidates=(),
                selected_requirement=None,
                next_actions=(
                    NextAction(
                        code="START_PROJECT_CONTEXT",
                        phase="CTX",
                        skill=skill,
                        skill_available=self.skill_available(skill),
                        reason="项目尚无 CTX 或 REQ Artifact",
                        command=f"/{skill}" if self.skill_available(skill) else None,
                        requires_user=not self.skill_available(skill),
                    ),
                ),
            )
        if not active:
            valid_contexts = tuple(
                item
                for item in contexts
                if item.revision_state == "frozen"
                and item.artifact_status in READY_STATUSES
                and item.authority_state == "valid"
            )
            skill = PHASE_SKILLS["REQ"]
            return ProjectOverview(
                state="context_only" if valid_contexts else "context_action_required",
                context_candidates=contexts,
                requirement_candidates=requirements,
                selected_requirement=None,
                next_actions=(
                    NextAction(
                        code=(
                            "START_REQUIREMENT"
                            if len(valid_contexts) == 1
                            else "RESOLVE_PROJECT_CONTEXT"
                        ),
                        phase="REQ" if len(valid_contexts) == 1 else "CTX",
                        skill=skill if len(valid_contexts) == 1 else PHASE_SKILLS["CTX"],
                        skill_available=self.skill_available(
                            skill if len(valid_contexts) == 1 else PHASE_SKILLS["CTX"]
                        ),
                        reason=(
                            "唯一有效 CTX 已就绪"
                            if len(valid_contexts) == 1
                            else "需要先形成唯一有效 CTX Authority"
                        ),
                        command=(
                            f"/{skill} create --reference {valid_contexts[0].reference}"
                            if len(valid_contexts) == 1 and self.skill_available(skill)
                            else None
                        ),
                        requires_user=len(valid_contexts) != 1,
                    ),
                ),
            )
        if len(active) == 1:
            return ProjectOverview(
                state="single_requirement",
                context_candidates=contexts,
                requirement_candidates=requirements,
                selected_requirement=active[0].reference,
                next_actions=(),
            )
        return ProjectOverview(
            state="selection_required",
            context_candidates=contexts,
            requirement_candidates=requirements,
            selected_requirement=None,
            next_actions=(
                NextAction(
                    code="SELECT_REQUIREMENT",
                    phase="REQ",
                    skill=None,
                    skill_available=False,
                    reason="项目中存在多个活跃 REQ，需要选择准确 Revision",
                    command=None,
                    requires_user=True,
                ),
            ),
        )
