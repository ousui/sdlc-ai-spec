"""Domain verifier for deterministic late-phase Artifacts."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable, Sequence

from packages.sdlc_artifact_store import DomainVerification, IntegrityError, StoredRevision
from packages.sdlc_runtime import FrozenArtifactAuthorityVerifier, parse_canonical_artifact


class StructuredPhaseVerificationError(IntegrityError):
    code = "PHASE_AUTHORITY_INVALID"


class StructuredPhaseVerifier:
    def __init__(
        self,
        project_root: Path | str,
        *,
        phase: str,
        required_headings: Sequence[str] = (),
        semantic_validator: Callable | None = None,
    ):
        self.project_root = Path(project_root).expanduser().resolve()
        self.phase = phase
        self.required_headings = tuple(required_headings)
        self.semantic_validator = semantic_validator

    def verify(self, reference: str, revision: StoredRevision) -> DomainVerification:
        try:
            if revision.payload.artifact_type != self.phase:
                raise StructuredPhaseVerificationError(
                    f"expected {self.phase} Artifact, found {revision.payload.artifact_type}"
                )
            parsed = parse_canonical_artifact(revision.payload.primary_blob)
            for heading in self.required_headings:
                if parsed.text.count(heading) != 1:
                    raise StructuredPhaseVerificationError(
                        f"required heading must occur exactly once: {heading}"
                    )
            if self.semantic_validator is not None:
                self.semantic_validator(parsed, revision)
            authority_revision = revision
            if revision.control.state == "open":
                # ArtifactStore calls the domain verifier before the atomic
                # open -> frozen transition. Verify the exact prospective
                # frozen authority without weakening the persisted checks.
                authority_revision = replace(
                    revision, control=replace(revision.control, state="frozen")
                )
            base = FrozenArtifactAuthorityVerifier(self.project_root).verify(
                reference, authority_revision
            )
        except StructuredPhaseVerificationError:
            raise
        except Exception as exc:
            raise StructuredPhaseVerificationError(str(exc)) from exc
        return DomainVerification(
            reference=reference,
            payload_binding=base.payload_binding,
            approved=True,
            message=f"{self.phase} Domain Contract and Final Confirmation are valid",
        )
