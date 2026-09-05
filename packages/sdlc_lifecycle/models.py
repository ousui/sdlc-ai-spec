"""Immutable projection models for SDLC lifecycle queries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

LIFECYCLE_STATUS_CONTRACT = "sdlc-ai-spec/lifecycle-status/v1"
PHASE_ORDER = ("CTX", "REQ", "DSN", "PLN", "IMP", "VFY", "RLS")
NEXT_PHASE = {
    "CTX": "REQ",
    "REQ": "DSN",
    "DSN": "PLN",
    "PLN": "IMP",
    "IMP": "VFY",
    "VFY": "RLS",
    "RLS": None,
}
PHASE_SKILLS = {
    "CTX": "sdlc-000-ctx",
    "REQ": "sdlc-100-req",
    "DSN": "sdlc-200-dsn",
    "PLN": "sdlc-300-pln",
    "IMP": "sdlc-400-imp",
    "VFY": "sdlc-500-vfy",
    "RLS": "sdlc-600-rls",
}


@dataclass(frozen=True)
class OpenItemProjection:
    item_id: str
    state: str
    needed: str | None = None
    expected_source: str | None = None
    blocked_references: tuple[str, ...] = ()
    resolution: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LifecycleNode:
    reference: str
    artifact_id: str
    artifact_type: str
    revision: int
    revision_state: str
    artifact_status: str | None
    materialized: bool
    allocated_at: str
    frozen_at: str | None
    gate_result: str
    authority_state: str
    authority_error: Mapping[str, Any] | None
    context_reference: str | None
    input_references: tuple[str, ...]
    open_items: tuple[OpenItemProjection, ...]
    projection_errors: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["open_items"] = [item.to_dict() for item in self.open_items]
        result["input_references"] = list(self.input_references)
        result["projection_errors"] = [dict(item) for item in self.projection_errors]
        result["authority_error"] = (
            dict(self.authority_error) if self.authority_error is not None else None
        )
        return result


@dataclass(frozen=True)
class LifecycleEdge:
    source_reference: str
    target_reference: str
    relation: str
    declared_reference: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RequirementCandidate:
    reference: str
    artifact_id: str
    revision: int
    revision_state: str
    artifact_status: str | None
    gate_result: str
    authority_state: str
    open_item_count: int
    lineage_head: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NextAction:
    code: str
    phase: str | None
    skill: str | None
    skill_available: bool
    reason: str
    command: str | None
    requires_user: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImpClaimProjection:
    binding_reference: str
    binding_lineage: str
    artifact_reference: str
    owner: str
    attempt: int
    claim_state: str
    execution_scope: tuple[str, ...]
    dependency_results: tuple[str, ...]
    revision_state: str | None = None
    materialized: bool = False
    outcome: str | None = None
    results: tuple[Mapping[str, Any], ...] = ()
    completed: bool = False
    vfy_ready: bool = False
    blockers: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for name in ("execution_scope", "dependency_results", "results", "blockers"):
            result[name] = list(result[name])
        return result


@dataclass(frozen=True)
class LifecycleProjection:
    root_reference: str
    overall_state: str
    nodes: tuple[LifecycleNode, ...]
    edges: tuple[LifecycleEdge, ...]
    frontier: tuple[str, ...]
    blockers: tuple[Mapping[str, Any], ...]
    next_actions: tuple[NextAction, ...]
    current_claims: tuple[ImpClaimProjection, ...] = ()
    vfy_inputs: tuple[str, ...] = ()
    vfy_results: tuple[Mapping[str, Any], ...] = ()
    vfy_projection: Mapping[str, Any] | None = None
    rls_projection: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": LIFECYCLE_STATUS_CONTRACT,
            "root_reference": self.root_reference,
            "overall_state": self.overall_state,
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "frontier": list(self.frontier),
            "blockers": [dict(item) for item in self.blockers],
            "next_actions": [item.to_dict() for item in self.next_actions],
            "current_claims": [item.to_dict() for item in self.current_claims],
            "vfy_inputs": list(self.vfy_inputs),
            "vfy_results": [dict(item) for item in self.vfy_results],
            "rls_projection": dict(self.rls_projection) if self.rls_projection is not None else None,
            "vfy_projection": (
                dict(self.vfy_projection)
                if self.vfy_projection is not None
                else None
            ),
        }


@dataclass(frozen=True)
class ProjectOverview:
    state: str
    context_candidates: tuple[LifecycleNode, ...]
    requirement_candidates: tuple[RequirementCandidate, ...]
    selected_requirement: str | None
    next_actions: tuple[NextAction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": LIFECYCLE_STATUS_CONTRACT,
            "state": self.state,
            "context_candidates": [item.to_dict() for item in self.context_candidates],
            "requirement_candidates": [
                item.to_dict() for item in self.requirement_candidates
            ],
            "selected_requirement": self.selected_requirement,
            "next_actions": [item.to_dict() for item in self.next_actions],
        }
