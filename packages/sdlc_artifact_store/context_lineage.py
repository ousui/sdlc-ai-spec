"""Atomic Project Boundary to CTX Artifact Lineage binding."""

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .errors import ArtifactStoreError, DatabaseError, InvalidInputError
from .sqlite_store import ArtifactStore

BOUNDARY_KEY_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ctx_lineage_bindings (
    boundary_key TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id)
);
"""


@dataclass(frozen=True)
class ContextLineageBinding:
    boundary_key: str
    artifact_id: str
    created_at: str
    created: bool


class ContextLineageRegistry:
    """Public CTX identity helper owned by the ArtifactStore package."""

    def __init__(self, store: ArtifactStore):
        if not isinstance(store, ArtifactStore):
            raise InvalidInputError("store must be an ArtifactStore")
        self.store = store

    @staticmethod
    def _validate_boundary_key(boundary_key: str) -> str:
        if not isinstance(boundary_key, str) or not BOUNDARY_KEY_RE.fullmatch(
            boundary_key
        ):
            raise InvalidInputError(
                "boundary_key must be sha256:<64 lowercase hexadecimal characters>"
            )
        return boundary_key

    def find(self, boundary_key: str) -> Optional[ContextLineageBinding]:
        """Read an existing binding without creating any table or persistent state."""

        boundary_key = self._validate_boundary_key(boundary_key)
        connection = self.store._connect()
        try:
            self.store._validate_schema(connection)
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='ctx_lineage_bindings'"
            ).fetchone()
            if table is None:
                return None
            row = connection.execute(
                """
                SELECT binding.boundary_key, binding.artifact_id, binding.created_at
                FROM ctx_lineage_bindings AS binding
                JOIN artifacts AS artifact ON artifact.artifact_id = binding.artifact_id
                WHERE binding.boundary_key = ? AND artifact.artifact_type = 'CTX'
                """,
                (boundary_key,),
            ).fetchone()
            if row is None:
                return None
            return ContextLineageBinding(
                boundary_key=row["boundary_key"],
                artifact_id=row["artifact_id"],
                created_at=row["created_at"],
                created=False,
            )
        finally:
            connection.close()

    def reserve(
        self,
        boundary_key: str,
        *,
        now: Optional[datetime] = None,
    ) -> ContextLineageBinding:
        """Atomically return the existing CTX binding or create exactly one."""

        self.store._ensure_write()
        boundary_key = self._validate_boundary_key(boundary_key)
        moment = self.store._resolve_moment(now)
        created_at = moment.isoformat(timespec="seconds")
        connection = self.store._connect()
        try:
            self.store._validate_schema(connection)
            connection.execute("PRAGMA busy_timeout = 1000")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(_CREATE_TABLE_SQL)
            row = connection.execute(
                """
                SELECT boundary_key, artifact_id, created_at
                FROM ctx_lineage_bindings
                WHERE boundary_key = ?
                """,
                (boundary_key,),
            ).fetchone()
            if row is not None:
                connection.commit()
                return ContextLineageBinding(
                    boundary_key=row["boundary_key"],
                    artifact_id=row["artifact_id"],
                    created_at=row["created_at"],
                    created=False,
                )

            prefix = f"CTX-{moment.strftime('%Y%m%d%H%M%S')}"
            rows = connection.execute(
                "SELECT artifact_id FROM artifacts WHERE artifact_id LIKE ?",
                (prefix + "-%",),
            ).fetchall()
            sequence = 1
            if rows:
                sequence = (
                    max(int(item["artifact_id"].rsplit("-", 1)[1]) for item in rows)
                    + 1
                )
            artifact_id = f"{prefix}-{sequence:02d}"
            connection.execute(
                """
                INSERT INTO artifacts(artifact_id, artifact_type, created_at)
                VALUES (?, 'CTX', ?)
                """,
                (artifact_id, created_at),
            )
            connection.execute(
                """
                INSERT INTO ctx_lineage_bindings(boundary_key, artifact_id, created_at)
                VALUES (?, ?, ?)
                """,
                (boundary_key, artifact_id, created_at),
            )
            result = connection.execute(
                """
                SELECT boundary_key, artifact_id, created_at
                FROM ctx_lineage_bindings
                WHERE boundary_key = ?
                """,
                (boundary_key,),
            ).fetchone()
            if result is None:
                raise DatabaseError("CTX Lineage binding could not be read back")
            connection.commit()
            return ContextLineageBinding(
                boundary_key=result["boundary_key"],
                artifact_id=result["artifact_id"],
                created_at=result["created_at"],
                created=True,
            )
        except ArtifactStoreError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError(f"CTX Lineage reservation failed: {exc}") from exc
        finally:
            connection.close()
