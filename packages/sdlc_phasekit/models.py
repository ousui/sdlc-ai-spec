"""Value objects shared by deterministic late-phase runtimes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from packages.sdlc_artifact_store import CanonicalManifest, CanonicalMember


@dataclass(frozen=True)
class CheckOutcome:
    result: str
    message: str


@dataclass(frozen=True)
class PhaseInputs:
    context_reference: str
    scope_references: tuple[str, ...]
    control_references: tuple[str, ...] = ()
    subject_references: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhaseBuild:
    raw_bytes: bytes
    status: str
    gate_result: str
    failed_checks: tuple[str, ...]
    open_items: tuple[Mapping[str, Any], ...]
    active_exceptions: tuple[str, ...]
    final_confirmation_valid: bool
    members: tuple[CanonicalMember, ...]
    manifest: CanonicalManifest
    subject_digest: str
    final_confirmation_bindings: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PhaseAnalysis:
    """Optional normalized analysis carrier used by phase-specific builders."""

    normalized: Mapping[str, Any]
    checks: Mapping[str, CheckOutcome]
    open_items: tuple[Mapping[str, Any], ...] = ()
    active_exceptions: tuple[str, ...] = ()
