"""Cleanup newly allocated REQ revisions after failed deterministic builds."""

from __future__ import annotations

from packages.sdlc_artifact_store.catalog import ArtifactCatalog


def apply_cleanup_fix(base) -> None:
    original_create = base.RequirementHandler.create
    original_revise = base.RequirementHandler.revise

    def req_snapshot(project_root):
        try:
            read_store = base.ArtifactStore.open_read_only(project_root)
            catalog = ArtifactCatalog(read_store)
            return {
                item.artifact_id: tuple(
                    revision.revision
                    for revision in catalog.list_revisions(item.artifact_id)
                )
                for item in catalog.list_artifacts("REQ")
            }
        except base.ArtifactStoreError:
            return {}

    def cleanup(project_root, before, reason):
        try:
            read_store = base.ArtifactStore.open_read_only(project_root)
            catalog = ArtifactCatalog(read_store)
            candidates = []
            for item in catalog.list_artifacts("REQ"):
                known = set(before.get(item.artifact_id, ()))
                for revision in catalog.list_revisions(item.artifact_id):
                    if revision.revision not in known and revision.state == "open":
                        candidates.append((item.artifact_id, revision.revision))
            if not candidates:
                return
            write_store = base.ArtifactStore.open_read_write(project_root)
            for artifact_id, revision in candidates:
                write_store.abandon_revision(
                    artifact_id,
                    revision,
                    reason="REQ build failed: " + reason[:400],
                )
        except base.ArtifactStoreError:
            return

    def create_with_cleanup(self, invocation):
        before = req_snapshot(self.project_root)
        result = original_create(self, invocation)
        if not result.get("ok") and result.get("artifact") is None:
            errors = result.get("errors") or []
            reason = errors[0].get("message", "unknown error") if errors else "unknown error"
            cleanup(self.project_root, before, reason)
        return result

    def revise_with_cleanup(self, invocation):
        before = req_snapshot(self.project_root)
        result = original_revise(self, invocation)
        if not result.get("ok") and result.get("artifact") is None:
            errors = result.get("errors") or []
            reason = errors[0].get("message", "unknown error") if errors else "unknown error"
            cleanup(self.project_root, before, reason)
        return result

    base.RequirementHandler.create = create_with_cleanup
    base.RequirementHandler.revise = revise_with_cleanup
