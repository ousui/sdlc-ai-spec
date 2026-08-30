"""Public value objects for the shared ArtifactStore facade."""

from dataclasses import dataclass
from typing import Optional, Protocol, Tuple


@dataclass(frozen=True)
class ClaimReservation:
    """Exact external IMP allocation values supplied by a Claim Provider."""

    binding_lineage: str
    attempt: str
    owner: str


@dataclass(frozen=True)
class ArtifactAllocation:
    artifact_id: str
    artifact_type: str
    created_at: str
    claim: Optional[ClaimReservation] = None


@dataclass(frozen=True)
class RevisionControlRecord:
    artifact_id: str
    revision: int
    state: str
    base_revision: Optional[int]
    allocated_at: str
    frozen_at: Optional[str]
    abandon_reason: Optional[str]
    generation: int
    materialized: bool
    claim: Optional[ClaimReservation] = None


@dataclass(frozen=True)
class CanonicalMember:
    member_id: str
    canonical_name: str
    media_type: str
    raw_bytes: bytes
    sha256: str


@dataclass(frozen=True)
class ManifestMember:
    member_id: str
    canonical_name: str
    media_type: str
    sha256: str


@dataclass(frozen=True)
class CanonicalManifest:
    """Canonical manifest bytes plus its local-member closure projection."""

    raw_bytes: bytes
    media_type: str
    local_members: Tuple[ManifestMember, ...]


@dataclass(frozen=True)
class CanonicalRevisionPayload:
    artifact_id: str
    artifact_type: str
    revision: int
    artifact_status: str
    primary_blob: bytes
    primary_media_type: str
    primary_sha256: str
    members: Tuple[CanonicalMember, ...]
    manifest: CanonicalManifest


@dataclass(frozen=True)
class StoredRevision:
    control: RevisionControlRecord
    payload: CanonicalRevisionPayload
    verification_binding: str


@dataclass(frozen=True)
class DigestVerification:
    artifact_id: str
    revision: int
    primary_verified: bool
    member_count: int
    manifest_member_count: int
    closure_verified: bool


@dataclass(frozen=True)
class DomainVerification:
    """Ephemeral binding result; it is not an Artifact field or stored digest."""

    reference: str
    payload_binding: str
    approved: bool
    message: str = ""


class DomainVerifier(Protocol):
    def verify(
        self, reference: str, revision: StoredRevision
    ) -> DomainVerification:
        """Verify exact domain authority for the supplied current payload."""


@dataclass(frozen=True)
class ResolvedReference:
    reference: str
    revision: StoredRevision
    member: Optional[CanonicalMember] = None
