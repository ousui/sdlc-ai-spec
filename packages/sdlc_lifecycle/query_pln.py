"""PLN-aware lifecycle projection layered on deterministic DSN routing."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from packages.sdlc_artifact_store import ArtifactStoreError
from packages.sdlc_runtime import parse_canonical_artifact
from packages.sdlc_runtime.canonical import CanonicalFormatError, find_tables

from .models import LifecycleNode, LifecycleProjection, NextAction, PHASE_ORDER, PHASE_SKILLS
from .query import READY_STATUSES
from .query_dsn import LifecycleQueryService as DsnLifecycleQueryService

WORK_ITEM_HEADERS = (
    "ID",
    "目标 Phase Target Phase",
    "结果 Outcome",
    "执行范围 Execution Scope",
    "来源引用 Source References",
    "约束引用 Constraint References",
    "依赖 Depends On",
    "完成条件 Completion Criteria",
    "预期证据 Expected Evidence",
    "责任角色 Responsible Role",
)
TARGET_PHASES = ("IMP", "VFY", "RLS")
_NONE = frozenset({"", "None", "N/A", "none", "n/a"})


@dataclass(frozen=True)
class PlanWorkItem:
    item_id: str
    target_phase: str
    depends_on: tuple[str, ...]

    @property
    def binding_reference_suffix(self) -> str:
        return f"#{self.item_id}"


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token.strip()
        for token in value.split(",")
        if token.strip() not in _NONE
    )


class LifecycleQueryService(DsnLifecycleQueryService):
    """Preserve the read-only graph and project exact PLN Work Item bindings."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pln_work_items: dict[
            str, tuple[PlanWorkItem, ...] | Mapping[str, Any]
        ] = {}

    def _read_pln_work_items(
        self, node: LifecycleNode
    ) -> tuple[PlanWorkItem, ...] | Mapping[str, Any]:
        cached = self._pln_work_items.get(node.reference)
        if cached is not None:
            return cached
        try:
            stored = self.store.read_revision(node.artifact_id, node.revision)
            parsed = parse_canonical_artifact(stored.payload.primary_blob)
            matches = find_tables(parsed, WORK_ITEM_HEADERS)
            if len(matches) != 1:
                raise CanonicalFormatError(
                    "PLN Work Items must appear exactly once"
                )
            rows = matches[0].rows
            if not rows:
                raise CanonicalFormatError(
                    "Frozen ready PLN must contain at least one Work Item"
                )
            items: list[PlanWorkItem] = []
            seen: set[str] = set()
            for index, row in enumerate(rows, start=1):
                item_id = row["ID"].strip()
                expected_id = f"WI-{index:03d}"
                target_phase = row["目标 Phase Target Phase"].strip()
                depends_on = _tokens(row["依赖 Depends On"])
                if item_id != expected_id or item_id in seen:
                    raise CanonicalFormatError(
                        "PLN Work Item IDs must be unique sequential WI-NNN values"
                    )
                if target_phase not in TARGET_PHASES:
                    raise CanonicalFormatError(
                        f"PLN Work Item Target Phase is invalid: {item_id}"
                    )
                if any(dependency not in seen for dependency in depends_on):
                    raise CanonicalFormatError(
                        f"PLN Work Item dependency is not an earlier Work Item: {item_id}"
                    )
                seen.add(item_id)
                items.append(
                    PlanWorkItem(
                        item_id=item_id,
                        target_phase=target_phase,
                        depends_on=depends_on,
                    )
                )
            result: tuple[PlanWorkItem, ...] | Mapping[str, Any] = tuple(items)
        except (ArtifactStoreError, CanonicalFormatError) as exc:
            result = {
                "code": getattr(exc, "code", "PLN_WORK_ITEMS_INVALID"),
                "message": str(exc),
                "reference": node.reference,
            }
        self._pln_work_items[node.reference] = result
        return result

    def _resolve_plan_action(
        self, node: LifecycleNode, problem: Mapping[str, Any]
    ) -> NextAction:
        skill = PHASE_SKILLS["PLN"]
        available = self.skill_available(skill)
        return NextAction(
            code="RESOLVE_PLAN_WORK_ITEMS",
            phase="PLN",
            skill=skill,
            skill_available=available,
            reason=str(problem["message"]),
            command=(
                f"/{skill} revise --reference {node.reference}" if available else None
            ),
            requires_user=True,
        )

    def _pln_start_actions(
        self, node: LifecycleNode, *, reason: str
    ) -> tuple[NextAction, ...]:
        work_items = self._read_pln_work_items(node)
        if isinstance(work_items, Mapping):
            return (self._resolve_plan_action(node, work_items),)

        # At the PLN-only checkpoint no downstream execution authority exists yet.
        # Project every dependency-free Work Item in the earliest target Phase and
        # retain all parallel candidates instead of silently selecting one.
        eligible = tuple(item for item in work_items if not item.depends_on)
        if not eligible:
            return (
                self._resolve_plan_action(
                    node,
                    {
                        "message": (
                            "PLN has no dependency-free Work Item from which execution can start"
                        )
                    },
                ),
            )
        earliest_rank = min(PHASE_ORDER.index(item.target_phase) for item in eligible)
        candidates = tuple(
            item
            for item in eligible
            if PHASE_ORDER.index(item.target_phase) == earliest_rank
        )
        actions: list[NextAction] = []
        for item in candidates:
            skill = PHASE_SKILLS[item.target_phase]
            available = self.skill_available(skill)
            binding = node.reference + item.binding_reference_suffix
            actions.append(
                NextAction(
                    code="START_WORK_ITEM",
                    phase=item.target_phase,
                    skill=skill,
                    skill_available=available,
                    reason=f"{reason}: {item.item_id}",
                    command=f"/{skill} create --input {binding}",
                    requires_user=not available,
                )
            )
        return tuple(actions)

    def _next_action_for(
        self, node: LifecycleNode, *, reason: str
    ) -> NextAction | None:
        if node.artifact_type != "PLN":
            return super()._next_action_for(node, reason=reason)
        if (
            node.revision_state != "frozen"
            or node.artifact_status not in READY_STATUSES
            or node.gate_result not in {"pass", "pass_with_exception"}
            or node.authority_state != "valid"
            or node.open_items
        ):
            return super()._next_action_for(node, reason=reason)
        return self._pln_start_actions(node, reason=reason)[0]

    def inspect_requirement(self, requirement_reference: str) -> LifecycleProjection:
        projection = super().inspect_requirement(requirement_reference)
        nodes = {node.reference: node for node in projection.nodes}
        plan_frontier = tuple(
            nodes[reference]
            for reference in projection.frontier
            if reference in nodes
            and nodes[reference].artifact_type == "PLN"
            and nodes[reference].revision_state == "frozen"
            and nodes[reference].artifact_status in READY_STATUSES
            and nodes[reference].gate_result in {"pass", "pass_with_exception"}
            and nodes[reference].authority_state == "valid"
            and not nodes[reference].open_items
        )
        if not plan_frontier:
            return projection

        actions: list[NextAction] = []
        for node in plan_frontier:
            actions.extend(
                self._pln_start_actions(
                    node,
                    reason="当前 Plan 已通过，可执行最早且依赖已满足的 Work Item",
                )
            )
        overall = "parallel" if len(actions) > 1 else projection.overall_state
        return replace(
            projection,
            overall_state=overall,
            next_actions=tuple(actions),
        )


__all__ = ("LifecycleQueryService", "PlanWorkItem")
