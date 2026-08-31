"""Local SQLite implementation of the v1.1 logical Artifact Store operations."""

import hashlib
import re
import sqlite3
import subprocess
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Optional, Sequence
from urllib.parse import quote

from .errors import (
    ArtifactStoreError,
    ConflictError,
    ControlReservationError,
    DatabaseError,
    IntegrityError,
    InvalidInputError,
    InvalidStateError,
    NotFoundError,
    ReadOnlyError,
    ReferenceError,
    SchemaError,
    SchemaVersionMismatchError,
    StaleVerificationError,
    StoreNotFoundError,
    TrackedRuntimeContentError,
    VerificationFailedError,
    VerifierRequiredError,
)
from .models import (
    ArtifactAllocation,
    CanonicalManifest,
    CanonicalMember,
    CanonicalRevisionPayload,
    ClaimReservation,
    DigestVerification,
    DomainVerifier,
    ManifestMember,
    ResolvedReference,
    RevisionControlRecord,
    StoredRevision,
)


SCHEMA_VERSION = 1
SQLITE_BUSY_TIMEOUT_MS = 5000
STORE_RELATIVE_PATH = Path(".sdlc") / "store.sqlite3"
ARTIFACT_TYPES = frozenset({"CTX", "REQ", "DSN", "PLN", "IMP", "VFY", "RLS"})
ARTIFACT_STATUSES = frozenset(
    {"draft", "waiting_input", "failed", "ready", "ready_with_exception"}
)
REVISION_STATES = frozenset({"open", "frozen", "abandoned"})
ARTIFACT_ID_RE = re.compile(
    r"^(CTX|REQ|DSN|PLN|IMP|VFY|RLS)-([0-9]{14})-([0-9]{2,})$"
)
REFERENCE_RE = re.compile(
    r"^(?P<artifact>(?:CTX|REQ|DSN|PLN|IMP|VFY|RLS)-[0-9]{14}-[0-9]{2,})"
    r"@(?P<revision>[1-9][0-9]*)(?:(?P<kind>[#/])(?P<target>[A-Za-z0-9._:+%-]+))?$"
)
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUIRED_TABLES = frozenset(
    {"schema_metadata", "artifacts", "revisions", "payloads", "members", "manifest_members"}
)
REQUIRED_COLUMNS = {
    "schema_metadata": {"key", "value"},
    "artifacts": {
        "artifact_id",
        "artifact_type",
        "created_at",
        "claim_binding_lineage",
        "claim_attempt",
        "claim_owner",
    },
    "revisions": {
        "artifact_id",
        "revision",
        "state",
        "base_revision",
        "allocated_at",
        "frozen_at",
        "abandon_reason",
        "generation",
        "materialized",
        "claim_binding_lineage",
        "claim_attempt",
        "claim_owner",
    },
    "payloads": {
        "artifact_id",
        "revision",
        "artifact_type",
        "artifact_status",
        "primary_blob",
        "primary_media_type",
        "primary_sha256",
        "manifest_blob",
        "manifest_media_type",
    },
    "members": {
        "artifact_id",
        "revision",
        "member_id",
        "canonical_name",
        "media_type",
        "raw_bytes",
        "sha256",
    },
    "manifest_members": {
        "artifact_id",
        "revision",
        "member_id",
        "canonical_name",
        "media_type",
        "sha256",
    },
}
REQUIRED_INDEXES = frozenset(
    {"one_open_revision_per_artifact", "one_claim_attempt_reservation"}
)


SCHEMA_SQL = """
CREATE TABLE schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    claim_binding_lineage TEXT UNIQUE,
    claim_attempt TEXT,
    claim_owner TEXT,
    CHECK (artifact_type IN ('CTX', 'REQ', 'DSN', 'PLN', 'IMP', 'VFY', 'RLS')),
    CHECK (
        (claim_binding_lineage IS NULL AND claim_attempt IS NULL AND claim_owner IS NULL)
        OR
        (artifact_type = 'IMP' AND claim_binding_lineage IS NOT NULL
         AND claim_attempt IS NOT NULL AND claim_owner IS NOT NULL)
    )
);

CREATE TABLE revisions (
    artifact_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    state TEXT NOT NULL CHECK (state IN ('open', 'frozen', 'abandoned')),
    base_revision INTEGER,
    allocated_at TEXT NOT NULL,
    frozen_at TEXT,
    abandon_reason TEXT,
    generation INTEGER NOT NULL DEFAULT 0 CHECK (generation >= 0),
    materialized INTEGER NOT NULL DEFAULT 0 CHECK (materialized IN (0, 1)),
    claim_binding_lineage TEXT,
    claim_attempt TEXT,
    claim_owner TEXT,
    PRIMARY KEY (artifact_id, revision),
    FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id),
    FOREIGN KEY (artifact_id, base_revision) REFERENCES revisions(artifact_id, revision),
    CHECK (base_revision IS NULL OR base_revision < revision),
    CHECK (
        (claim_binding_lineage IS NULL AND claim_attempt IS NULL AND claim_owner IS NULL)
        OR
        (claim_binding_lineage IS NOT NULL AND claim_attempt IS NOT NULL AND claim_owner IS NOT NULL)
    )
);

CREATE UNIQUE INDEX one_open_revision_per_artifact
ON revisions(artifact_id) WHERE state = 'open';

CREATE UNIQUE INDEX one_claim_attempt_reservation
ON revisions(claim_binding_lineage, claim_attempt)
WHERE claim_binding_lineage IS NOT NULL;

CREATE TABLE payloads (
    artifact_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    artifact_type TEXT NOT NULL,
    artifact_status TEXT NOT NULL,
    primary_blob BLOB NOT NULL,
    primary_media_type TEXT NOT NULL,
    primary_sha256 TEXT NOT NULL,
    manifest_blob BLOB NOT NULL,
    manifest_media_type TEXT NOT NULL,
    PRIMARY KEY (artifact_id, revision),
    FOREIGN KEY (artifact_id, revision) REFERENCES revisions(artifact_id, revision)
);

CREATE TABLE members (
    artifact_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    member_id TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    raw_bytes BLOB NOT NULL,
    sha256 TEXT NOT NULL,
    PRIMARY KEY (artifact_id, revision, member_id),
    UNIQUE (artifact_id, revision, canonical_name),
    FOREIGN KEY (artifact_id, revision) REFERENCES payloads(artifact_id, revision) ON DELETE CASCADE
);

CREATE TABLE manifest_members (
    artifact_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    member_id TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    PRIMARY KEY (artifact_id, revision, member_id),
    UNIQUE (artifact_id, revision, canonical_name),
    FOREIGN KEY (artifact_id, revision) REFERENCES payloads(artifact_id, revision) ON DELETE CASCADE
);
"""

_INITIALIZE_LOCK = threading.Lock()


def compute_sha256(raw_bytes: bytes) -> str:
    """Return the canonical SHA-256 representation used by the domain contract."""

    return "sha256:" + hashlib.sha256(raw_bytes).hexdigest()


class ArtifactStore:
    """Stable facade for the nine logical Artifact Store operations."""

    def __init__(
        self,
        project_root: Path,
        *,
        read_only: bool = False,
        clock: Optional[Callable[[], datetime]] = None,
    ):
        root = Path(project_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise InvalidInputError(f"Project root is not an existing directory: {root}")
        self.project_root = root
        self.store_path = root / STORE_RELATIVE_PATH
        self.read_only = read_only
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @classmethod
    def open_read_write(
        cls, project_root: Path, *, clock: Optional[Callable[[], datetime]] = None
    ) -> "ArtifactStore":
        """Open the create/revise facade; callers explicitly invoke initialize."""

        return cls(project_root, read_only=False, clock=clock)

    @classmethod
    def open_read_only(cls, project_root: Path) -> "ArtifactStore":
        """Open an existing Store without creating any directory, file, or schema."""

        store = cls(project_root, read_only=True)
        if not store.store_path.parent.is_dir():
            raise StoreNotFoundError(
                f"Runtime directory does not exist: {store.store_path.parent}"
            )
        if not store.store_path.is_file():
            raise StoreNotFoundError(f"Artifact Store does not exist: {store.store_path}")
        connection = store._connect()
        try:
            store._validate_schema(connection)
        finally:
            connection.close()
        return store

    def initialize(self) -> int:
        """Create Schema v1 once or validate the existing Store idempotently."""

        with _INITIALIZE_LOCK:
            return self._initialize_locked()

    def _initialize_locked(self) -> int:
        """Serialize first initialization so cleanup cannot race another creator."""

        self._ensure_write()
        tracked = self._tracked_sdlc_paths()
        if tracked:
            joined = ", ".join(tracked)
            raise TrackedRuntimeContentError(
                f".sdlc contains Git-tracked content; index changes require user action: {joined}"
            )

        runtime_dir = self.store_path.parent
        if self.store_path.exists() and not self.store_path.is_file():
            raise ConflictError(f"Artifact Store path is not a file: {self.store_path}")
        database_existed = self.store_path.is_file()
        if database_existed:
            connection = self._connect()
            try:
                self._validate_schema(connection)
            finally:
                connection.close()
            self._ensure_runtime_ignore(runtime_dir)
            return SCHEMA_VERSION

        runtime_created = not runtime_dir.exists()
        runtime_dir.mkdir(parents=False, exist_ok=True)
        try:
            ignore_created = self._ensure_runtime_ignore(runtime_dir)
        except ArtifactStoreError:
            if runtime_created:
                self._cleanup_failed_initialize(
                    runtime_created=True,
                    ignore_created=False,
                    database_created=False,
                )
            raise
        try:
            database_handle = self.store_path.open("xb")
            database_handle.close()
        except FileExistsError as exc:
            raise ConflictError(
                "Artifact Store appeared during initialize; retry only after validating its Schema"
            ) from exc
        except OSError as exc:
            self._cleanup_failed_initialize(
                runtime_created, ignore_created, database_created=False
            )
            raise DatabaseError(f"Cannot reserve Artifact Store path: {exc}") from exc
        connection = None
        try:
            connection = self._connect()
            connection.executescript("BEGIN IMMEDIATE;\n" + SCHEMA_SQL)
            connection.execute(
                "INSERT INTO schema_metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            self._validate_schema(connection)
            connection.commit()
        except ArtifactStoreError:
            if connection is not None:
                connection.rollback()
            self._cleanup_failed_initialize(
                runtime_created, ignore_created, database_created=True
            )
            raise
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            self._cleanup_failed_initialize(
                runtime_created, ignore_created, database_created=True
            )
            raise DatabaseError(f"Failed to initialize SQLite Schema: {exc}") from exc
        finally:
            if connection is not None:
                connection.close()
        return SCHEMA_VERSION

    def allocate_artifact(
        self,
        artifact_type: str,
        *,
        now: Optional[datetime] = None,
        external_artifact_id: Optional[str] = None,
        claim: Optional[ClaimReservation] = None,
    ) -> ArtifactAllocation:
        self._ensure_write()
        artifact_type = self._validate_artifact_type(artifact_type)
        moment = self._resolve_moment(now)
        created_at = moment.isoformat(timespec="seconds")
        self._validate_external_allocation(artifact_type, external_artifact_id, claim)

        with self._transaction() as connection:
            if external_artifact_id is not None:
                row = connection.execute(
                    "SELECT * FROM artifacts WHERE artifact_id = ?",
                    (external_artifact_id,),
                ).fetchone()
                lineage_row = connection.execute(
                    "SELECT * FROM artifacts WHERE claim_binding_lineage = ?",
                    (claim.binding_lineage,),
                ).fetchone()
                if row is not None:
                    existing = self._artifact_from_row(row)
                    if (
                        existing.artifact_type != "IMP"
                        or existing.claim is None
                        or existing.claim.binding_lineage != claim.binding_lineage
                    ):
                        raise ConflictError(
                            "Exact IMP Artifact ID is already bound to different claim values"
                        )
                    if lineage_row["artifact_id"] != external_artifact_id:
                        raise ConflictError(
                            "IMP Binding Lineage is already bound to a different Artifact ID"
                        )
                    return existing
                if lineage_row is not None:
                    raise ConflictError(
                        "IMP Binding Lineage is already bound to a different Artifact ID"
                    )
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        artifact_id, artifact_type, created_at,
                        claim_binding_lineage, claim_attempt, claim_owner
                    ) VALUES (?, 'IMP', ?, ?, ?, ?)
                    """,
                    (
                        external_artifact_id,
                        created_at,
                        claim.binding_lineage,
                        claim.attempt,
                        claim.owner,
                    ),
                )
                artifact_id = external_artifact_id
            else:
                prefix = f"{artifact_type}-{moment.strftime('%Y%m%d%H%M%S')}"
                rows = connection.execute(
                    "SELECT artifact_id FROM artifacts WHERE artifact_id LIKE ?",
                    (prefix + "-%",),
                ).fetchall()
                sequence = 1
                if rows:
                    sequence = max(int(row["artifact_id"].rsplit("-", 1)[1]) for row in rows) + 1
                artifact_id = f"{prefix}-{sequence:02d}"
                connection.execute(
                    "INSERT INTO artifacts(artifact_id, artifact_type, created_at) VALUES (?, ?, ?)",
                    (artifact_id, artifact_type, created_at),
                )

            row = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
            if row is None:
                raise DatabaseError("Artifact allocation could not be read back")
            return self._artifact_from_row(row)

    def allocate_revision(
        self,
        artifact_id: str,
        *,
        base_revision: Optional[int] = None,
        now: Optional[datetime] = None,
        external_revision: Optional[int] = None,
        claim: Optional[ClaimReservation] = None,
    ) -> RevisionControlRecord:
        self._ensure_write()
        self._validate_artifact_id(artifact_id)
        allocated_at = self._timestamp(now)
        if external_revision is not None and claim is None:
            raise InvalidInputError("External Revision Reservation requires exact claim values")
        if external_revision is None and claim is not None:
            raise InvalidInputError("Claim values require an external Revision Reservation")
        if external_revision is not None and (not isinstance(external_revision, int) or external_revision < 1):
            raise InvalidInputError("External Revision Reservation must be a positive integer")

        with self._transaction() as connection:
            artifact_row = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
            if artifact_row is None:
                raise NotFoundError(f"Artifact does not exist: {artifact_id}")
            artifact = self._artifact_from_row(artifact_row)
            if artifact.artifact_type == "IMP" and external_revision is None:
                raise InvalidInputError(
                    "IMP Revision allocation requires an external exact Reservation"
                )
            if external_revision is not None:
                if (
                    artifact.artifact_type != "IMP"
                    or artifact.claim is None
                    or artifact.claim.binding_lineage != claim.binding_lineage
                ):
                    raise ConflictError(
                        "External Revision Reservation does not match the IMP Artifact claim"
                    )

            rows = connection.execute(
                "SELECT * FROM revisions WHERE artifact_id = ? ORDER BY revision",
                (artifact_id,),
            ).fetchall()
            maximum = rows[-1]["revision"] if rows else 0
            expected = maximum + 1

            if external_revision is not None:
                existing = next(
                    (row for row in rows if row["revision"] == external_revision), None
                )
                if existing is not None:
                    record = self._control_from_row(existing)
                    if record.claim != claim:
                        raise ConflictError(
                            "Exact IMP Revision Reservation is bound to different claim values"
                        )
                    return record
                revision = external_revision
                if revision != expected:
                    raise ConflictError(
                        f"Exact IMP Revision Reservation must be {expected}, got {revision}"
                    )
            else:
                revision = expected

            if any(row["state"] == "open" for row in rows):
                raise ConflictError(f"Artifact already has an open Revision: {artifact_id}")
            self._validate_base_revision(rows, revision, base_revision)
            claim_values = (
                (claim.binding_lineage, claim.attempt, claim.owner)
                if claim is not None
                else (None, None, None)
            )
            connection.execute(
                """
                INSERT INTO revisions(
                    artifact_id, revision, state, base_revision, allocated_at,
                    claim_binding_lineage, claim_attempt, claim_owner
                ) VALUES (?, ?, 'open', ?, ?, ?, ?, ?)
                """,
                (artifact_id, revision, base_revision, allocated_at, *claim_values),
            )
            row = connection.execute(
                "SELECT * FROM revisions WHERE artifact_id = ? AND revision = ?",
                (artifact_id, revision),
            ).fetchone()
            if row is None:
                raise DatabaseError("Revision allocation could not be read back")
            return self._control_from_row(row)

    def read_revision(self, artifact_id: str, revision: int) -> StoredRevision:
        self._validate_artifact_id(artifact_id)
        self._validate_revision_number(revision)
        connection = self._connect()
        try:
            self._validate_schema(connection)
            return self._read_revision_conn(connection, artifact_id, revision)
        finally:
            connection.close()

    def write_open_revision(
        self,
        payload: CanonicalRevisionPayload,
        *,
        expected_generation: int,
    ) -> StoredRevision:
        self._ensure_write()
        if not isinstance(expected_generation, int) or expected_generation < 0:
            raise InvalidInputError("expected_generation must be a non-negative integer")
        self._validate_payload(payload)

        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM revisions WHERE artifact_id = ? AND revision = ?",
                (payload.artifact_id, payload.revision),
            ).fetchone()
            if row is None:
                raise NotFoundError(
                    f"Revision does not exist: {payload.artifact_id}@{payload.revision}"
                )
            control = self._control_from_row(row)
            if control.state != "open":
                raise InvalidStateError(
                    f"Only an open Revision can be written; state is {control.state}"
                )
            if control.generation != expected_generation:
                raise ConflictError(
                    f"Revision generation conflict: expected {expected_generation}, current {control.generation}"
                )
            artifact_row = connection.execute(
                "SELECT artifact_type FROM artifacts WHERE artifact_id = ?",
                (payload.artifact_id,),
            ).fetchone()
            if artifact_row is None or artifact_row["artifact_type"] != payload.artifact_type:
                raise IntegrityError("Payload Artifact Type does not match its Artifact Lineage")

            connection.execute(
                "DELETE FROM payloads WHERE artifact_id = ? AND revision = ?",
                (payload.artifact_id, payload.revision),
            )
            connection.execute(
                """
                INSERT INTO payloads(
                    artifact_id, revision, artifact_type, artifact_status,
                    primary_blob, primary_media_type, primary_sha256,
                    manifest_blob, manifest_media_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.artifact_id,
                    payload.revision,
                    payload.artifact_type,
                    payload.artifact_status,
                    payload.primary_blob,
                    payload.primary_media_type,
                    payload.primary_sha256,
                    payload.manifest.raw_bytes,
                    payload.manifest.media_type,
                ),
            )
            connection.executemany(
                """
                INSERT INTO members(
                    artifact_id, revision, member_id, canonical_name,
                    media_type, raw_bytes, sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        payload.artifact_id,
                        payload.revision,
                        member.member_id,
                        member.canonical_name,
                        member.media_type,
                        member.raw_bytes,
                        member.sha256,
                    )
                    for member in payload.members
                ],
            )
            self._insert_manifest_members(connection, payload)
            cursor = connection.execute(
                """
                UPDATE revisions
                SET materialized = 1, generation = generation + 1
                WHERE artifact_id = ? AND revision = ? AND state = 'open' AND generation = ?
                """,
                (payload.artifact_id, payload.revision, expected_generation),
            )
            if cursor.rowcount != 1:
                raise ConflictError("Concurrent Revision update detected")
            return self._read_revision_conn(
                connection, payload.artifact_id, payload.revision
            )

    def freeze_revision(
        self,
        artifact_id: str,
        revision: int,
        *,
        verifier: Optional[DomainVerifier] = None,
        now: Optional[datetime] = None,
    ) -> RevisionControlRecord:
        self._ensure_write()
        stored = self.read_revision(artifact_id, revision)
        if stored.control.state != "open":
            raise InvalidStateError(
                f"Only an open Revision can be frozen; state is {stored.control.state}"
            )
        if stored.payload.artifact_status not in {"ready", "ready_with_exception"}:
            raise InvalidStateError(
                "Only ready or ready_with_exception Payloads can be frozen"
            )
        reference = f"{artifact_id}@{revision}"
        self._verify_domain(reference, stored, verifier)
        frozen_at = self._timestamp(now)

        with self._transaction() as connection:
            current = self._read_revision_conn(connection, artifact_id, revision)
            if current.control.state != "open":
                raise ConflictError("Revision state changed during domain verification")
            if current.control.generation != stored.control.generation:
                raise ConflictError("Revision Payload changed during domain verification")
            cursor = connection.execute(
                """
                UPDATE revisions SET state = 'frozen', frozen_at = ?
                WHERE artifact_id = ? AND revision = ? AND state = 'open' AND generation = ?
                """,
                (frozen_at, artifact_id, revision, stored.control.generation),
            )
            if cursor.rowcount != 1:
                raise ConflictError("Concurrent freeze conflict detected")
            row = connection.execute(
                "SELECT * FROM revisions WHERE artifact_id = ? AND revision = ?",
                (artifact_id, revision),
            ).fetchone()
            return self._control_from_row(row)

    def abandon_revision(
        self, artifact_id: str, revision: int, *, reason: str
    ) -> RevisionControlRecord:
        self._ensure_write()
        self._validate_artifact_id(artifact_id)
        self._validate_revision_number(revision)
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidInputError("Abandon Reason must be a non-empty string")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM revisions WHERE artifact_id = ? AND revision = ?",
                (artifact_id, revision),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"Revision does not exist: {artifact_id}@{revision}")
            if row["state"] != "open":
                raise InvalidStateError(
                    f"Only an open Revision can be abandoned; state is {row['state']}"
                )
            connection.execute(
                """
                UPDATE revisions
                SET state = 'abandoned', abandon_reason = ?, frozen_at = NULL
                WHERE artifact_id = ? AND revision = ? AND state = 'open'
                """,
                (reason.strip(), artifact_id, revision),
            )
            result = connection.execute(
                "SELECT * FROM revisions WHERE artifact_id = ? AND revision = ?",
                (artifact_id, revision),
            ).fetchone()
            return self._control_from_row(result)

    def resolve_exact_reference(
        self, reference: str, *, verifier: Optional[DomainVerifier] = None
    ) -> ResolvedReference:
        match = REFERENCE_RE.fullmatch(reference) if isinstance(reference, str) else None
        if match is None:
            raise ReferenceError(
                "Reference must name an exact numeric Revision; latest/current are not supported"
            )
        artifact_id = match.group("artifact")
        revision_number = int(match.group("revision"))
        stored = self.read_revision(artifact_id, revision_number)
        if stored.control.state != "frozen":
            raise InvalidStateError(
                f"Exact Reference requires a frozen Revision; state is {stored.control.state}"
            )
        if stored.payload.artifact_status not in {"ready", "ready_with_exception"}:
            raise InvalidStateError(
                f"Artifact Status cannot provide Authority: {stored.payload.artifact_status}"
            )
        self._verify_domain(reference, stored, verifier)

        member = None
        if match.group("kind") == "/":
            member_id = match.group("target")
            member = next(
                (item for item in stored.payload.members if item.member_id == member_id),
                None,
            )
            if member is None:
                raise ReferenceError(f"Member does not exist in exact Revision: {member_id}")
        return ResolvedReference(reference=reference, revision=stored, member=member)

    def verify_digest(self, artifact_id: str, revision: int) -> DigestVerification:
        stored = self.read_revision(artifact_id, revision)
        return DigestVerification(
            artifact_id=artifact_id,
            revision=revision,
            primary_verified=True,
            member_count=len(stored.payload.members),
            manifest_member_count=len(stored.payload.manifest.local_members),
            closure_verified=True,
        )

    def _insert_manifest_members(
        self, connection: sqlite3.Connection, payload: CanonicalRevisionPayload
    ) -> None:
        connection.executemany(
            """
            INSERT INTO manifest_members(
                artifact_id, revision, member_id, canonical_name, media_type, sha256
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    payload.artifact_id,
                    payload.revision,
                    member.member_id,
                    member.canonical_name,
                    member.media_type,
                    member.sha256,
                )
                for member in payload.manifest.local_members
            ],
        )

    def _read_revision_conn(
        self, connection: sqlite3.Connection, artifact_id: str, revision: int
    ) -> StoredRevision:
        control_row = connection.execute(
            "SELECT * FROM revisions WHERE artifact_id = ? AND revision = ?",
            (artifact_id, revision),
        ).fetchone()
        if control_row is None:
            raise NotFoundError(f"Revision does not exist: {artifact_id}@{revision}")
        control = self._control_from_row(control_row)
        if not control.materialized:
            raise ControlReservationError(
                f"Revision is only a Control Reservation: {artifact_id}@{revision}"
            )
        payload_row = connection.execute(
            "SELECT * FROM payloads WHERE artifact_id = ? AND revision = ?",
            (artifact_id, revision),
        ).fetchone()
        if payload_row is None:
            raise IntegrityError("Materialized Revision is missing its primary Payload")
        member_rows = connection.execute(
            """
            SELECT * FROM members WHERE artifact_id = ? AND revision = ?
            ORDER BY member_id
            """,
            (artifact_id, revision),
        ).fetchall()
        manifest_rows = connection.execute(
            """
            SELECT * FROM manifest_members WHERE artifact_id = ? AND revision = ?
            ORDER BY member_id
            """,
            (artifact_id, revision),
        ).fetchall()
        members = tuple(
            CanonicalMember(
                member_id=row["member_id"],
                canonical_name=row["canonical_name"],
                media_type=row["media_type"],
                raw_bytes=bytes(row["raw_bytes"]),
                sha256=row["sha256"],
            )
            for row in member_rows
        )
        manifest_members = tuple(
            ManifestMember(
                member_id=row["member_id"],
                canonical_name=row["canonical_name"],
                media_type=row["media_type"],
                sha256=row["sha256"],
            )
            for row in manifest_rows
        )
        payload = CanonicalRevisionPayload(
            artifact_id=payload_row["artifact_id"],
            artifact_type=payload_row["artifact_type"],
            revision=payload_row["revision"],
            artifact_status=payload_row["artifact_status"],
            primary_blob=bytes(payload_row["primary_blob"]),
            primary_media_type=payload_row["primary_media_type"],
            primary_sha256=payload_row["primary_sha256"],
            members=members,
            manifest=CanonicalManifest(
                raw_bytes=bytes(payload_row["manifest_blob"]),
                media_type=payload_row["manifest_media_type"],
                local_members=manifest_members,
            ),
        )
        if payload.artifact_id != control.artifact_id or payload.revision != control.revision:
            raise IntegrityError("Revision Control Record and Payload identity do not match")
        self._validate_payload(payload)
        binding = self._verification_binding(payload, control.generation)
        return StoredRevision(control=control, payload=payload, verification_binding=binding)

    def _validate_payload(self, payload: CanonicalRevisionPayload) -> None:
        if not isinstance(payload, CanonicalRevisionPayload):
            raise InvalidInputError("payload must be a CanonicalRevisionPayload")
        self._validate_artifact_id(payload.artifact_id)
        self._validate_revision_number(payload.revision)
        if payload.artifact_type not in ARTIFACT_TYPES:
            raise InvalidInputError(f"Unsupported Artifact Type: {payload.artifact_type}")
        if not payload.artifact_id.startswith(payload.artifact_type + "-"):
            raise IntegrityError("Payload Artifact ID prefix does not match Artifact Type")
        if payload.artifact_status not in ARTIFACT_STATUSES:
            raise InvalidInputError(f"Unsupported Artifact Status: {payload.artifact_status}")
        self._validate_media_type(payload.primary_media_type, "primary")
        self._validate_media_type(payload.manifest.media_type, "manifest")
        if not isinstance(payload.primary_blob, bytes):
            raise InvalidInputError("primary Canonical Blob must be raw bytes")
        if not isinstance(payload.manifest.raw_bytes, bytes):
            raise InvalidInputError("Canonical Manifest must be raw bytes")
        self._validate_digest(payload.primary_sha256, "primary")
        if compute_sha256(payload.primary_blob) != payload.primary_sha256:
            raise IntegrityError("Primary Blob SHA-256 does not match its raw bytes")

        member_ids = [member.member_id for member in payload.members]
        member_names = [member.canonical_name for member in payload.members]
        manifest_ids = [member.member_id for member in payload.manifest.local_members]
        manifest_names = [member.canonical_name for member in payload.manifest.local_members]
        self._require_unique(member_ids, "Member ID")
        self._require_unique(member_names, "Canonical Member Name")
        self._require_unique(manifest_ids, "Manifest Member ID")
        self._require_unique(manifest_names, "Manifest Canonical Member Name")

        actual = {}
        for member in payload.members:
            self._validate_member_identity(member.member_id, member.canonical_name)
            self._validate_media_type(member.media_type, f"Member {member.member_id}")
            if not isinstance(member.raw_bytes, bytes):
                raise InvalidInputError(f"Member raw bytes are required: {member.member_id}")
            self._validate_digest(member.sha256, f"Member {member.member_id}")
            if compute_sha256(member.raw_bytes) != member.sha256:
                raise IntegrityError(
                    f"Member SHA-256 does not match raw bytes: {member.member_id}"
                )
            actual[member.member_id] = (
                member.canonical_name,
                member.media_type,
                member.sha256,
            )

        declared = {}
        for member in payload.manifest.local_members:
            self._validate_member_identity(member.member_id, member.canonical_name)
            self._validate_media_type(member.media_type, f"Manifest Member {member.member_id}")
            self._validate_digest(member.sha256, f"Manifest Member {member.member_id}")
            declared[member.member_id] = (
                member.canonical_name,
                member.media_type,
                member.sha256,
            )
        if actual != declared:
            missing = sorted(set(declared) - set(actual))
            extra = sorted(set(actual) - set(declared))
            details = []
            if missing:
                details.append("missing=" + ",".join(missing))
            if extra:
                details.append("unregistered=" + ",".join(extra))
            mismatched = sorted(
                member_id
                for member_id in set(actual) & set(declared)
                if actual[member_id] != declared[member_id]
            )
            if mismatched:
                details.append("metadata_mismatch=" + ",".join(mismatched))
            raise IntegrityError(
                "Manifest-Member closure is invalid"
                + (": " + "; ".join(details) if details else "")
            )

    def _verify_domain(
        self,
        reference: str,
        stored: StoredRevision,
        verifier: Optional[DomainVerifier],
    ) -> None:
        if verifier is None:
            raise VerifierRequiredError(
                "A domain verifier bound to the exact Reference and current Payload is required"
            )
        result = verifier.verify(reference, stored)
        if result.reference != reference:
            raise StaleVerificationError("Domain verifier returned a different Reference binding")
        if result.payload_binding != stored.verification_binding:
            raise StaleVerificationError("Domain verifier result is stale for the current Payload")
        if not result.approved:
            raise VerificationFailedError(result.message or "Domain verifier rejected the Revision")

    def _verification_binding(
        self, payload: CanonicalRevisionPayload, generation: int
    ) -> str:
        """Compute an ephemeral verifier token; never persist it as a domain digest."""

        digest = hashlib.sha256()
        for value in (
            payload.artifact_id,
            payload.artifact_type,
            str(payload.revision),
            payload.artifact_status,
            payload.primary_media_type,
            payload.primary_sha256,
            payload.manifest.media_type,
            str(generation),
        ):
            digest.update(value.encode("utf-8"))
            digest.update(b"\0")
        digest.update(payload.primary_blob)
        digest.update(b"\0")
        digest.update(payload.manifest.raw_bytes)
        for member in payload.members:
            for value in (
                member.member_id,
                member.canonical_name,
                member.media_type,
                member.sha256,
            ):
                digest.update(value.encode("utf-8"))
                digest.update(b"\0")
            digest.update(member.raw_bytes)
            digest.update(b"\0")
        return "internal-verifier-binding:" + digest.hexdigest()

    def _artifact_from_row(self, row: sqlite3.Row) -> ArtifactAllocation:
        claim = None
        if row["claim_binding_lineage"] is not None:
            claim = ClaimReservation(
                binding_lineage=row["claim_binding_lineage"],
                attempt=row["claim_attempt"],
                owner=row["claim_owner"],
            )
        return ArtifactAllocation(
            artifact_id=row["artifact_id"],
            artifact_type=row["artifact_type"],
            created_at=row["created_at"],
            claim=claim,
        )

    def _control_from_row(self, row: sqlite3.Row) -> RevisionControlRecord:
        claim = None
        if row["claim_binding_lineage"] is not None:
            claim = ClaimReservation(
                binding_lineage=row["claim_binding_lineage"],
                attempt=row["claim_attempt"],
                owner=row["claim_owner"],
            )
        return RevisionControlRecord(
            artifact_id=row["artifact_id"],
            revision=row["revision"],
            state=row["state"],
            base_revision=row["base_revision"],
            allocated_at=row["allocated_at"],
            frozen_at=row["frozen_at"],
            abandon_reason=row["abandon_reason"],
            generation=row["generation"],
            materialized=bool(row["materialized"]),
            claim=claim,
        )

    def _validate_schema(self, connection: sqlite3.Connection) -> None:
        try:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise SchemaError("SQLite quick_check reported database damage")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if not REQUIRED_TABLES.issubset(tables):
                missing = sorted(REQUIRED_TABLES - tables)
                raise SchemaError("Required SQLite Schema is missing: " + ", ".join(missing))
            for table, required in REQUIRED_COLUMNS.items():
                columns = {
                    row[1]
                    for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
                }
                if not required.issubset(columns):
                    missing = sorted(required - columns)
                    raise SchemaError(
                        f"Required SQLite Schema columns are missing from {table}: "
                        + ", ".join(missing)
                    )
            indexes = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                ).fetchall()
            }
            if not REQUIRED_INDEXES.issubset(indexes):
                missing = sorted(REQUIRED_INDEXES - indexes)
                raise SchemaError(
                    "Required SQLite Schema indexes are missing: " + ", ".join(missing)
                )
            foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_keys:
                raise SchemaError("SQLite foreign_key_check reported inconsistent rows")
            row = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if row is None:
                raise SchemaError("SQLite Schema version marker is missing")
            if row[0] != str(SCHEMA_VERSION):
                raise SchemaVersionMismatchError(
                    f"SQLite Schema version {row[0]} is incompatible with required version {SCHEMA_VERSION}"
                )
        except ArtifactStoreError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseError(f"Cannot validate SQLite Schema: {exc}") from exc

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            self._validate_schema(connection)
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except ArtifactStoreError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError(f"SQLite transaction failed: {exc}") from exc
        finally:
            connection.close()

    def _connect(self, *, allow_create: bool = False) -> sqlite3.Connection:
        if not self.store_path.is_file() and not allow_create:
            raise StoreNotFoundError(f"Artifact Store does not exist: {self.store_path}")
        try:
            if self.read_only:
                uri_path = quote(str(self.store_path), safe="/")
                connection = sqlite3.connect(
                    f"file:{uri_path}?mode=ro",
                    uri=True,
                    isolation_level=None,
                )
                connection.execute("PRAGMA query_only = ON")
            else:
                connection = sqlite3.connect(self.store_path, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
            return connection
        except sqlite3.Error as exc:
            raise DatabaseError(f"Cannot open SQLite Store {self.store_path}: {exc}") from exc

    def _tracked_sdlc_paths(self) -> Sequence[str]:
        try:
            probe = subprocess.run(
                ["git", "-C", str(self.project_root), "rev-parse", "--is-inside-work-tree"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            if probe.returncode != 0 or probe.stdout.strip() != "true":
                return ()
            result = subprocess.run(
                ["git", "-C", str(self.project_root), "ls-files", "--", ".sdlc"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            if (self.project_root / ".git").exists():
                raise DatabaseError(f"Cannot verify Git-tracked .sdlc content: {exc}") from exc
            return ()
        if result.returncode != 0:
            raise DatabaseError(
                "Cannot verify Git-tracked .sdlc content: " + result.stderr.strip()
            )
        return tuple(line for line in result.stdout.splitlines() if line)

    def _ensure_runtime_ignore(self, runtime_dir: Path) -> bool:
        gitignore = runtime_dir / ".gitignore"
        if gitignore.exists():
            try:
                current = gitignore.read_bytes()
            except OSError as exc:
                raise DatabaseError(f"Cannot read {gitignore}: {exc}") from exc
            if current != b"*\n":
                raise ConflictError(
                    f"Existing runtime ignore file does not contain the fixed content '*': {gitignore}"
                )
            return False
        try:
            gitignore.write_bytes(b"*\n")
        except OSError as exc:
            raise DatabaseError(f"Cannot create {gitignore}: {exc}") from exc
        return True

    def _cleanup_failed_initialize(
        self,
        runtime_created: bool,
        ignore_created: bool,
        *,
        database_created: bool,
    ) -> None:
        try:
            if database_created and self.store_path.exists():
                self.store_path.unlink()
            gitignore = self.store_path.parent / ".gitignore"
            if ignore_created and gitignore.exists():
                gitignore.unlink()
            if runtime_created and self.store_path.parent.exists():
                self.store_path.parent.rmdir()
        except OSError as exc:
            raise DatabaseError(
                f"Initialization failed and runtime cleanup was incomplete: {exc}"
            ) from exc

    def _ensure_write(self) -> None:
        if self.read_only:
            raise ReadOnlyError("This ArtifactStore facade is strictly read-only")

    def _validate_artifact_type(self, artifact_type: str) -> str:
        if artifact_type not in ARTIFACT_TYPES:
            raise InvalidInputError(
                "Artifact Type must be one of: " + ", ".join(sorted(ARTIFACT_TYPES))
            )
        return artifact_type

    def _validate_artifact_id(self, artifact_id: str) -> None:
        if not isinstance(artifact_id, str) or ARTIFACT_ID_RE.fullmatch(artifact_id) is None:
            raise InvalidInputError(f"Invalid Artifact ID: {artifact_id!r}")

    def _validate_revision_number(self, revision: int) -> None:
        if not isinstance(revision, int) or revision < 1:
            raise InvalidInputError("Revision must be a positive integer")

    def _validate_external_allocation(
        self,
        artifact_type: str,
        external_artifact_id: Optional[str],
        claim: Optional[ClaimReservation],
    ) -> None:
        if external_artifact_id is None and claim is None:
            if artifact_type == "IMP":
                raise InvalidInputError(
                    "IMP Artifact allocation requires an external exact Artifact ID and claim"
                )
            return
        if artifact_type != "IMP" or external_artifact_id is None or claim is None:
            raise InvalidInputError(
                "Only IMP may adopt an external exact Artifact ID, and all claim values are required"
            )
        self._validate_artifact_id(external_artifact_id)
        if not external_artifact_id.startswith("IMP-"):
            raise InvalidInputError("External IMP Artifact ID must use the IMP prefix")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (claim.binding_lineage, claim.attempt, claim.owner)
        ):
            raise InvalidInputError("Claim lineage, attempt, and owner must be non-empty")

    def _validate_base_revision(
        self, rows: Sequence[sqlite3.Row], revision: int, base_revision: Optional[int]
    ) -> None:
        if revision == 1:
            if base_revision is not None:
                raise InvalidInputError("Revision 1 must use Base Revision None")
            return
        if base_revision is None:
            return
        base = next((row for row in rows if row["revision"] == base_revision), None)
        if base is None or base["state"] != "frozen":
            raise InvalidInputError("Base Revision must exist and be frozen in the same Lineage")

    def _validate_digest(self, digest: str, label: str) -> None:
        if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
            raise InvalidInputError(f"{label} SHA-256 must use sha256:<64 lowercase hex>")

    def _validate_media_type(self, media_type: str, label: str) -> None:
        if not isinstance(media_type, str) or not media_type.strip() or "/" not in media_type:
            raise InvalidInputError(f"{label} Media Type must be a non-empty type/subtype value")

    def _validate_member_identity(self, member_id: str, canonical_name: str) -> None:
        if not isinstance(member_id, str) or not member_id.strip():
            raise InvalidInputError("Member ID must be non-empty")
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            raise InvalidInputError("Canonical Member Name must be non-empty")

    def _require_unique(self, values: Sequence[str], label: str) -> None:
        if len(values) != len(set(values)):
            raise IntegrityError(f"Duplicate {label} is not allowed")

    def _timestamp(self, now: Optional[datetime]) -> str:
        moment = self._resolve_moment(now)
        return moment.isoformat(timespec="seconds")

    def _resolve_moment(self, now: Optional[datetime]) -> datetime:
        moment = now if now is not None else self._clock()
        if not isinstance(moment, datetime) or moment.tzinfo is None:
            raise InvalidInputError("Time source must return a timezone-aware datetime")
        return moment
