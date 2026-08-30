"""Strictly read-only Artifact catalog projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .errors import InvalidInputError
from .models import RevisionControlRecord
from .sqlite_store import ARTIFACT_TYPES, ArtifactStore


@dataclass(frozen=True)
class ArtifactSummary:
    artifact_id: str
    artifact_type: str
    created_at: str


class ArtifactCatalog:
    """List Artifact lineages and Revision controls without providing Authority."""

    def __init__(self, store: ArtifactStore):
        if not isinstance(store, ArtifactStore):
            raise InvalidInputError("store must be an ArtifactStore")
        if not store.read_only:
            raise InvalidInputError("ArtifactCatalog requires a read-only ArtifactStore")
        self.store = store

    def list_artifacts(
        self, artifact_type: Optional[str] = None
    ) -> Tuple[ArtifactSummary, ...]:
        if artifact_type is not None and artifact_type not in ARTIFACT_TYPES:
            raise InvalidInputError(f"Unsupported Artifact Type: {artifact_type}")
        connection = self.store._connect()
        try:
            self.store._validate_schema(connection)
            if artifact_type is None:
                rows = connection.execute(
                    """
                    SELECT artifact_id, artifact_type, created_at
                    FROM artifacts
                    ORDER BY created_at, artifact_id
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT artifact_id, artifact_type, created_at
                    FROM artifacts
                    WHERE artifact_type = ?
                    ORDER BY created_at, artifact_id
                    """,
                    (artifact_type,),
                ).fetchall()
            return tuple(
                ArtifactSummary(
                    artifact_id=row["artifact_id"],
                    artifact_type=row["artifact_type"],
                    created_at=row["created_at"],
                )
                for row in rows
            )
        finally:
            connection.close()

    def list_revisions(self, artifact_id: str) -> Tuple[RevisionControlRecord, ...]:
        self.store._validate_artifact_id(artifact_id)
        connection = self.store._connect()
        try:
            self.store._validate_schema(connection)
            rows = connection.execute(
                """
                SELECT * FROM revisions
                WHERE artifact_id = ?
                ORDER BY revision
                """,
                (artifact_id,),
            ).fetchall()
            return tuple(self.store._control_from_row(row) for row in rows)
        finally:
            connection.close()
