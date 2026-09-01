"""Reviewed DSN handler with upstream applicability and cleanup guards."""

from __future__ import annotations

from typing import Any, Mapping

from packages.sdlc_artifact_store import ArtifactStore, ArtifactStoreError
from packages.sdlc_artifact_store.catalog import ArtifactCatalog

from dsn_common import (
    APPLICABILITY_HEADERS,
    CanonicalFormatError,
    DsnRuntimeError,
    _exact_base,
    _refs,
    find_tables,
    parse_canonical_artifact,
)
from dsn_handler import DsnHandler as BaseDsnHandler, INTERFACE_PATH


class DsnHandler(BaseDsnHandler):
    """Add deterministic pre-allocation and failure-cleanup behavior."""

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

    def _upstream_applicability_result(self, invocation):
        inputs = invocation.get("inputs") or {}
        try:
            scope = _refs(inputs.get("scope_inputs"), "scope_inputs", required=True)
            store = ArtifactStore.open_read_only(self.project_root)
            verifier = self.upstream_verifier_factory(self.project_root)
            dispositions: list[str] = []
            for reference in scope:
                _exact_base(reference, "REQ")
                resolved = store.resolve_exact_reference(reference, verifier=verifier)
                parsed = parse_canonical_artifact(
                    resolved.revision.payload.primary_blob
                )
                tables = find_tables(parsed, APPLICABILITY_HEADERS)
                if len(tables) != 1:
                    raise DsnRuntimeError(
                        "REQ Lifecycle Applicability must appear exactly once"
                    )
                rows = [row for row in tables[0].rows if row["Phase"] == "DSN"]
                if len(rows) != 1:
                    raise DsnRuntimeError(
                        "REQ Lifecycle Applicability must contain exactly one DSN row"
                    )
                disposition = rows[0]["Disposition"]
                basis = rows[0]["判断依据 Basis"].strip()
                if disposition not in {"required", "n/a", "waived", "pending"}:
                    raise DsnRuntimeError(
                        f"REQ DSN Disposition is invalid: {disposition}"
                    )
                if not basis:
                    raise DsnRuntimeError("REQ DSN Applicability Basis is empty")
                dispositions.append(disposition)
        except (ArtifactStoreError, CanonicalFormatError, DsnRuntimeError) as exc:
            return self._error(
                invocation,
                exc,
                code=getattr(exc, "code", "REQ_APPLICABILITY_INVALID"),
            )

        if any(value == "pending" for value in dispositions):
            return self._result(
                invocation,
                ok=False,
                status="action_required",
                errors=(
                    {
                        "code": "REQ_DSN_APPLICABILITY_PENDING",
                        "message": "至少一个 Scope REQ 的 DSN Applicability 仍为 pending",
                    },
                ),
                next_action={
                    "code": "RESOLVE_REQUIREMENT_APPLICABILITY",
                    "message": "先修订对应 REQ，确认 DSN 是否适用",
                    "requires_user": True,
                    "command": None,
                },
            )
        if dispositions and all(
            value in {"n/a", "waived"} for value in dispositions
        ):
            return self._result(
                invocation,
                ok=True,
                status="completed",
                warnings=(
                    {
                        "code": "DSN_NOT_REQUIRED",
                        "message": "全部 Scope REQ 已以准确 Basis 将 DSN 标记为 n/a 或 waived，未分配空 DSN",
                    },
                ),
                next_action={
                    "code": "CONTINUE_AFTER_DSN",
                    "message": "使用 sdlc-status 查询准确下一阶段",
                    "requires_user": False,
                    "command": "/sdlc-status",
                },
            )
        return None

    def create(self, invocation):
        applicability_result = self._upstream_applicability_result(invocation)
        if applicability_result is not None:
            return applicability_result
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
