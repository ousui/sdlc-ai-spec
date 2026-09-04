"""Immutable public claim records for IMP execution authority."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimRecord:
    binding_lineage: str
    binding_reference: str
    artifact_id: str
    revision: int
    attempt: int
    owner: str
    execution_scope: tuple[str, ...]
    dependency_results: tuple[str, ...]
    rework_references: tuple[str, ...]
    state: str
    created_at: str
    updated_at: str
    generation: int
    completed_at: str | None = None
    abandoned_by: str | None = None
    abandoned_at: str | None = None
    abandon_reason: str | None = None

    @property
    def attempt_token(self) -> str:
        return str(self.attempt)

    @property
    def acquired_at(self) -> str:
        """Compatibility alias for the original pre-Foundation field name."""
        return self.created_at


@dataclass(frozen=True)
class AcquireRequest:
    binding_reference: str
    owner: str
    execution_scope: tuple[str, ...]
    dependency_results: tuple[str, ...] = ()
    rework_references: tuple[str, ...] = ()
    retry_abandoned: bool = False


__all__ = ("AcquireRequest", "ClaimRecord")
