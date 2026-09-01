"""Reviewed DSN handler that closes newly allocated failed revisions."""

from __future__ import annotations

from typing import Any, Mapping

from packages.sdlc_artifact_store import ArtifactStore, ArtifactStoreError
from packages.sdlc_artifact_store.catalog import ArtifactCatalog

from dsn_handler import DsnHandler as BaseDsnHandler, INTERFACE_PATH


class DsnHandler(BaseDsnHandler):
    """Add deterministic cleanup without changing successful DSN behavior."""

    def _revision_snapshot(self) -> dict[str, tuple[int, ...]]:
        try:
            store = ArtifactStore.open_read_only(self.project_root)
            catalog = ArtifactCatalog(store)
        except ArtifactStoreError:
            return {}
        return {
            item.artifact_id: tuple(
                record.revision
                for record in catalog.list_revisions(item.artifact_id)
            )
            for item in catalog.list_artifacts("DSN")
        }

    def _abandon_new_open_revisions(
        self,
        before: Mapping[str, tuple[int, ...]],
        result: Mapping[str, Any],
        operation: str,
    ) -> None:
        if result.get("ok") or result.get("artifact") is not None:
            return
        try:
            read_store = ArtifactStore.open_read_only(self.project_root)
            catalog = ArtifactCatalog(read_store)
            candidates: list[tuple[str, int]] = []
            for item in catalog.list_artifacts("DSN"):
                known = set(before.get(item.artifact_id, ()))
                for record in catalog.list_revisions(item.artifact_id):
                    if record.revision not in known and record.state == "open":
                        candidates.append((item.artifact_id, record.revision))
            if not candidates:
                return
            errors = result.get("errors") or []
            reason = (
                errors[0].get("message", "unknown deterministic build failure")
                if errors
                else "unknown deterministic build failure"
            )
            write_store = ArtifactStore.open_read_write(self.project_root)
            for artifact_id, revision in candidates:
                write_store.abandon_revision(
                    artifact_id,
                    revision,
                    reason=f"DSN {operation} failed: {reason[:400]}",
                )
        except ArtifactStoreError:
            return

    def create(self, invocation):
        before = self._revision_snapshot()
        result = super().create(invocation)
        self._abandon_new_open_revisions(before, result, "create")
        return result

    def revise(self, invocation):
        before = self._revision_snapshot()
        result = super().revise(invocation)
        self._abandon_new_open_revisions(before, result, "revise")
        return result


__all__ = ("DsnHandler", "INTERFACE_PATH")
