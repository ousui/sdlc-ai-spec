"""DSN-aware lifecycle projection layered on the generic read-only graph."""

from __future__ import annotations

from typing import Any, Mapping

from packages.sdlc_artifact_store import ArtifactStoreError
from packages.sdlc_runtime import parse_canonical_artifact
from packages.sdlc_runtime.canonical import CanonicalFormatError, find_tables

from .models import LifecycleNode, NextAction, PHASE_SKILLS
from .query import LifecycleQueryService as BaseLifecycleQueryService, READY_STATUSES

APPLICABILITY_HEADERS = ("Phase", "Disposition", "Host", "判断依据 Basis")
DSN_PHASES = ("PLN", "IMP", "VFY", "RLS")
DISPOSITIONS = frozenset({"required", "n/a", "waived", "pending"})


class LifecycleQueryService(BaseLifecycleQueryService):
    """Preserve generic graph behavior and add deterministic DSN routing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dsn_applicability: dict[
            str, tuple[Mapping[str, str], ...] | Mapping[str, Any]
        ] = {}

    def _read_dsn_applicability(
        self, node: LifecycleNode
    ) -> tuple[Mapping[str, str], ...] | Mapping[str, Any]:
        cached = self._dsn_applicability.get(node.reference)
        if cached is not None:
            return cached
        try:
            stored = self.store.read_revision(node.artifact_id, node.revision)
            parsed = parse_canonical_artifact(stored.payload.primary_blob)
            matches = find_tables(parsed, APPLICABILITY_HEADERS)
            if len(matches) != 1:
                raise CanonicalFormatError(
                    "DSN Lifecycle Applicability must appear exactly once"
                )
            rows = matches[0].rows
            if tuple(row["Phase"] for row in rows) != DSN_PHASES:
                raise CanonicalFormatError(
                    "DSN Lifecycle Applicability Phase order is invalid"
                )
            normalized: list[Mapping[str, str]] = []
            for row in rows:
                disposition = row["Disposition"]
                basis = row["判断依据 Basis"].strip()
                if disposition not in DISPOSITIONS or not basis:
                    raise CanonicalFormatError(
                        "DSN Lifecycle Applicability row is invalid"
                    )
                normalized.append(
                    {
                        "phase": row["Phase"],
                        "disposition": disposition,
                        "host": row["Host"],
                        "basis": basis,
                    }
                )
            if next(
                item for item in normalized if item["phase"] == "VFY"
            )["disposition"] != "required":
                raise CanonicalFormatError("DSN VFY Disposition must be required")
            result: tuple[Mapping[str, str], ...] | Mapping[str, Any] = tuple(
                normalized
            )
        except (ArtifactStoreError, CanonicalFormatError) as exc:
            result = {
                "code": getattr(exc, "code", "DSN_APPLICABILITY_INVALID"),
                "message": str(exc),
                "reference": node.reference,
            }
        self._dsn_applicability[node.reference] = result
        return result

    def _dsn_next_action(self, node: LifecycleNode, reason: str) -> NextAction:
        applicability = self._read_dsn_applicability(node)
        if isinstance(applicability, Mapping):
            return NextAction(
                code="RESOLVE_LIFECYCLE_APPLICABILITY",
                phase="DSN",
                skill=PHASE_SKILLS["DSN"],
                skill_available=self.skill_available(PHASE_SKILLS["DSN"]),
                reason=applicability["message"],
                command=(
                    f"/{PHASE_SKILLS['DSN']} revise --reference {node.reference}"
                    if self.skill_available(PHASE_SKILLS["DSN"])
                    else None
                ),
                requires_user=True,
            )
        by_phase = {item["phase"]: item for item in applicability}
        pln = by_phase["PLN"]["disposition"]
        imp = by_phase["IMP"]["disposition"]
        if pln == "required":
            next_phase = "PLN"
        elif pln in {"n/a", "waived"} and imp == "required":
            next_phase = "IMP"
        else:
            return NextAction(
                code="RESOLVE_LIFECYCLE_APPLICABILITY",
                phase="DSN",
                skill=PHASE_SKILLS["DSN"],
                skill_available=self.skill_available(PHASE_SKILLS["DSN"]),
                reason=(
                    "DSN 必须明确进入 PLN，或在 PLN=n/a/waived 且 IMP=required 时直接进入 IMP"
                ),
                command=(
                    f"/{PHASE_SKILLS['DSN']} revise --reference {node.reference}"
                    if self.skill_available(PHASE_SKILLS["DSN"])
                    else None
                ),
                requires_user=True,
            )
        skill = PHASE_SKILLS[next_phase]
        available = self.skill_available(skill)
        return NextAction(
            code="START_NEXT_PHASE",
            phase=next_phase,
            skill=skill,
            skill_available=available,
            reason=reason,
            command=(
                f"/{skill} create --input {node.reference}" if available else None
            ),
            requires_user=not available,
        )

    def _next_action_for(
        self, node: LifecycleNode, *, reason: str
    ) -> NextAction | None:
        if node.artifact_type != "DSN":
            return super()._next_action_for(node, reason=reason)
        if node.revision_state == "abandoned":
            return super()._next_action_for(node, reason=reason)
        if (
            node.revision_state == "open"
            or node.artifact_status not in READY_STATUSES
            or node.gate_result not in {"pass", "pass_with_exception"}
            or node.authority_state != "valid"
            or node.open_items
        ):
            return super()._next_action_for(node, reason=reason)
        return self._dsn_next_action(node, reason)


__all__ = ("LifecycleQueryService",)
