"""Generic ArtifactStore handler for PLN/VFY and structurally similar phases."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from packages.sdlc_artifact_store import (
    ArtifactStore,
    ArtifactStoreError,
    CanonicalRevisionPayload,
    ConflictError,
    InvalidStateError,
    compute_sha256,
)
from packages.sdlc_runtime import (
    RESULT_CONTRACT,
    compute_control_input_digest,
    exact_artifact_reference,
    parse_canonical_artifact,
)
from packages.sdlc_runtime.canonical import GATE_SUMMARY_HEADERS, require_single_row, require_single_table

from .common import PhaseKitError
from .models import PhaseBuild, PhaseInputs

READY_STATUSES = {"ready", "ready_with_exception"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactPhaseHandler:
    def __init__(
        self,
        project_root: Path | str,
        *,
        artifact_type: str,
        skill_name: str,
        builder: Any,
        verifier: Any,
        input_resolver: Callable[[ArtifactStore, Mapping[str, Any]], PhaseInputs],
        candidate_key: str,
        clock: Callable[[], datetime] | None = None,
    ):
        self.project_root = Path(project_root).expanduser().resolve()
        self.artifact_type = artifact_type
        self.skill_name = skill_name
        self.builder = builder
        self.verifier = verifier
        self.input_resolver = input_resolver
        self.candidate_key = candidate_key
        self.clock = clock or _utcnow

    def _exact(self, reference: str) -> tuple[str, int]:
        artifact_id, revision = exact_artifact_reference(reference)
        if not artifact_id.startswith(self.artifact_type + "-"):
            raise PhaseKitError(f"expected exact {self.artifact_type} Reference")
        suffix = reference.split("@", 1)[1]
        if "#" in suffix or "/" in suffix:
            raise PhaseKitError(f"expected base {self.artifact_type} Reference")
        return artifact_id, revision

    def _write_allowed(self, invocation: Mapping[str, Any]) -> bool:
        return str(invocation.get("options", {}).get("write_policy", "auto")) != "deny"

    def _payload(self, control, build: PhaseBuild) -> CanonicalRevisionPayload:
        return CanonicalRevisionPayload(
            artifact_id=control.artifact_id,
            artifact_type=self.artifact_type,
            revision=control.revision,
            artifact_status=build.status,
            primary_blob=build.raw_bytes,
            primary_media_type="text/markdown",
            primary_sha256=compute_sha256(build.raw_bytes),
            members=build.members,
            manifest=build.manifest,
        )

    def _result(
        self,
        invocation: Mapping[str, Any],
        *,
        stored=None,
        build: PhaseBuild | None = None,
        ok: bool,
        status: str,
        warnings: Sequence[Mapping[str, Any]] = (),
        errors: Sequence[Mapping[str, Any]] = (),
        next_action: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        artifact = None
        if stored is not None:
            artifact = {
                "id": stored.control.artifact_id,
                "type": self.artifact_type,
                "revision": stored.control.revision,
                "revision_state": stored.control.state,
                "artifact_status": stored.payload.artifact_status,
                "reference": (
                    f"{stored.control.artifact_id}@{stored.control.revision}"
                    if stored.control.state == "frozen"
                    else None
                ),
            }
        return {
            "contract": RESULT_CONTRACT,
            "ok": ok,
            "operation": invocation["operation"],
            "status": status,
            "artifact": artifact,
            "gate": {
                "result": build.gate_result if build else "pending",
                "failed_checks": list(build.failed_checks) if build else [],
            },
            "open_items": [dict(item) for item in (build.open_items if build else ())],
            "warnings": [dict(item) for item in warnings],
            "errors": [dict(item) for item in errors],
            "next_action": dict(next_action) if next_action else None,
        }

    def _error(
        self,
        invocation: Mapping[str, Any],
        exc: Exception,
        *,
        code: str | None = None,
        build: PhaseBuild | None = None,
    ) -> dict[str, Any]:
        return self._result(
            invocation,
            build=build,
            ok=False,
            status="blocked" if isinstance(exc, ConflictError) else "failed",
            errors=({
                "code": code or getattr(exc, "code", f"{self.artifact_type}_RUNTIME_ERROR"),
                "message": str(exc),
            },),
            next_action={
                "code": f"RESOLVE_{self.artifact_type}_INPUT",
                "message": f"修正 {self.artifact_type} 输入或 Store 状态后重试",
                "requires_user": True,
                "command": None,
            },
        )

    def _candidate(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        value = invocation["inputs"].get(self.candidate_key)
        if not isinstance(value, Mapping):
            raise PhaseKitError(f"inputs.{self.candidate_key} must be an object")
        return value

    def _build(self, control, phase_inputs: PhaseInputs, invocation: Mapping[str, Any]) -> PhaseBuild:
        return self.builder.build(
            artifact_id=control.artifact_id,
            revision=control.revision,
            phase_inputs=phase_inputs,
            candidate=self._candidate(invocation),
            final_confirmation=invocation["inputs"].get("final_confirmation"),
        )

    def _persist(self, invocation, store, control, phase_inputs):
        build = self._build(control, phase_inputs, invocation)
        stored = store.write_open_revision(
            self._payload(control, build), expected_generation=control.generation
        )
        if build.status in READY_STATUSES:
            store.freeze_revision(
                control.artifact_id,
                control.revision,
                verifier=self.verifier,
                now=self.clock(),
            )
            stored = store.read_revision(control.artifact_id, control.revision)
        ok = stored.control.state == "frozen" and stored.payload.artifact_status in READY_STATUSES
        status = "completed" if ok else (
            "action_required" if stored.payload.artifact_status == "waiting_input" else "failed"
        )
        next_action = None if ok else {
            "code": f"COMPLETE_{self.artifact_type}" if status == "action_required" else f"CORRECT_{self.artifact_type}",
            "message": f"补充或修正 {self.artifact_type} 内容、决策或 Final Confirmation",
            "requires_user": True,
            "command": f"/{self.skill_name} revise --reference {control.artifact_id}@{control.revision}",
        }
        return self._result(invocation, stored=stored, build=build, ok=ok, status=status, next_action=next_action)

    def _cleanup_reservation(self, store, control, primary: Exception, *, prefix: str):
        try:
            # abandon_revision supports both unmaterialized Control
            # Reservations and materialized open Revisions. Reading an
            # unmaterialized reservation first would itself fail and hide the
            # primary build error.
            store.abandon_revision(
                control.artifact_id,
                control.revision,
                reason=f"{self.artifact_type} {prefix} failed: {str(primary)[:400]}",
            )
        except Exception as cleanup:
            raise PhaseKitError(
                f"{primary}; cleanup failed: {cleanup}"
            ) from cleanup

    def create(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        if invocation.get("artifact_reference"):
            return self._error(invocation, PhaseKitError("create does not accept artifact_reference"), code="ARTIFACT_REFERENCE_INVALID")
        if not self._write_allowed(invocation) and not invocation["options"].get("dry_run"):
            return self._error(invocation, PhaseKitError("write authorization is required"), code="WRITE_AUTHORIZATION_REQUIRED")
        try:
            read_store = ArtifactStore.open_read_only(self.project_root)
            phase_inputs = self.input_resolver(read_store, invocation["inputs"])
            if invocation["options"].get("dry_run"):
                class Preview:
                    artifact_id=f"{self.artifact_type}-20990101000000-01"; revision=1
                build = self._build(Preview, phase_inputs, invocation)
                return self._result(invocation, build=build, ok=True, status="completed", warnings=({"code":"DRY_RUN","message":"未分配 Artifact 或修改 Store"},))
            store = ArtifactStore.open_read_write(self.project_root, clock=self.clock)
            allocation = store.allocate_artifact(self.artifact_type, now=self.clock())
            control = store.allocate_revision(allocation.artifact_id, now=self.clock())
            try:
                return self._persist(invocation, store, control, phase_inputs)
            except Exception as exc:
                try:
                    self._cleanup_reservation(store, control, exc, prefix="create")
                except Exception as cleanup_exc:
                    return self._error(
                        invocation,
                        PhaseKitError(f"{exc}; {cleanup_exc}"),
                        code=f"{self.artifact_type}_CLEANUP_FAILED",
                    )
                raise
        except Exception as exc:
            return self._error(invocation, exc)

    def revise(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        reference = invocation.get("artifact_reference")
        if not reference:
            return self._error(invocation, PhaseKitError(f"revise requires an exact {self.artifact_type} Reference"), code="ARTIFACT_REFERENCE_REQUIRED")
        if not self._write_allowed(invocation) and not invocation["options"].get("dry_run"):
            return self._error(invocation, PhaseKitError("write authorization is required"), code="WRITE_AUTHORIZATION_REQUIRED")
        try:
            artifact_id, revision_number = self._exact(reference)
            read_store = ArtifactStore.open_read_only(self.project_root)
            existing = read_store.read_revision(artifact_id, revision_number)
            if existing.control.state == "abandoned":
                raise InvalidStateError("abandoned Revision cannot be revised")
            phase_inputs = self.input_resolver(read_store, invocation["inputs"])
            class ExistingControl:
                pass
            preview_control = ExistingControl()
            preview_control.artifact_id=artifact_id; preview_control.revision=revision_number
            preview = self._build(preview_control, phase_inputs, invocation)
            same = (
                compute_control_input_digest(preview.raw_bytes)
                == compute_control_input_digest(existing.payload.primary_blob)
                and preview.manifest.raw_bytes == existing.payload.manifest.raw_bytes
                and tuple((item.member_id,item.sha256) for item in preview.members)
                == tuple((item.member_id,item.sha256) for item in existing.payload.members)
            )
            if existing.control.state == "frozen" and same:
                return self._result(invocation, stored=existing, build=preview, ok=True, status="completed", warnings=({"code":"NO_CHANGE","message":"候选内容与 frozen Revision 相同，未创建空 Revision"},))
            if invocation["options"].get("dry_run"):
                return self._result(invocation, build=preview, ok=True, status="completed", warnings=({"code":"DRY_RUN","message":f"未修改 {self.artifact_type} Revision"},))
            store = ArtifactStore.open_read_write(self.project_root, clock=self.clock)
            allocated_new = existing.control.state == "frozen"
            control = (
                store.allocate_revision(artifact_id, base_revision=revision_number, now=self.clock())
                if allocated_new else existing.control
            )
            try:
                return self._persist(invocation, store, control, phase_inputs)
            except Exception as exc:
                if allocated_new:
                    try:
                        self._cleanup_reservation(store, control, exc, prefix="revise")
                    except Exception as cleanup_exc:
                        return self._error(invocation, PhaseKitError(f"{exc}; {cleanup_exc}"), code=f"{self.artifact_type}_CLEANUP_FAILED")
                raise
        except Exception as exc:
            return self._error(invocation, exc)

    def check(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        reference = invocation.get("artifact_reference")
        if not reference:
            return self._error(invocation, PhaseKitError(f"check requires an exact {self.artifact_type} Reference"), code="ARTIFACT_REFERENCE_REQUIRED")
        try:
            artifact_id, revision_number = self._exact(reference)
            store = ArtifactStore.open_read_only(self.project_root)
            stored = store.read_revision(artifact_id, revision_number)
            store.verify_digest(artifact_id, revision_number)
            self.verifier.verify(reference, stored)
            parsed = parse_canonical_artifact(stored.payload.primary_blob)
            gate = require_single_row(require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate Summary"), "Gate Summary")["Gate Result"]
            build = PhaseBuild(
                stored.payload.primary_blob,
                stored.payload.artifact_status,
                gate,
                (), (), (),
                stored.payload.artifact_status in READY_STATUSES,
                stored.payload.members,
                stored.payload.manifest,
                "N/A",
            )
            ok = stored.control.state == "frozen" and stored.payload.artifact_status in READY_STATUSES
            return self._result(
                invocation, stored=stored, build=build, ok=ok,
                status="completed" if ok else "action_required",
                next_action=None if ok else {
                    "code": f"REVISE_{self.artifact_type}",
                    "message": f"当前 {self.artifact_type} 尚未形成可用 Authority",
                    "requires_user": True,
                    "command": f"/{self.skill_name} revise --reference {reference}",
                },
            )
        except Exception as exc:
            return self._error(invocation, exc)
