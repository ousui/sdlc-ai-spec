"""DSN ArtifactStore operation handler."""

from dsn_common import *
from dsn_builder import DsnBuilder
from dsn_verifier import DsnVerifier


class DsnHandler:
    def __init__(
        self,
        project_root: Path | str,
        *,
        clock: Callable[[], datetime] | None = None,
        upstream_verifier_factory: Callable[[Path], Any] | None = None,
    ):
        self.project_root = Path(project_root).expanduser().resolve()
        self.clock = clock or _now
        self.builder = DsnBuilder(self.project_root)
        self.upstream_verifier_factory = (
            upstream_verifier_factory or FrozenArtifactAuthorityVerifier
        )

    def _resolve_inputs(
        self,
        store: ArtifactStore,
        inputs: Mapping[str, Any],
    ) -> UpstreamScope:
        raw_scope = inputs.get("scope_inputs", [])
        raw_control = inputs.get("control_inputs", [])
        scope = _refs(raw_scope, "scope_inputs", required=True)
        controls = _refs(raw_control, "control_inputs")
        verifier = self.upstream_verifier_factory(self.project_root)
        context: str | None = None
        req_items: list[str] = []
        ac_items: list[str] = []
        for reference in scope:
            artifact_id, revision = _exact_base(reference, "REQ")
            resolved = store.resolve_exact_reference(reference, verifier=verifier)
            parsed = parse_canonical_artifact(resolved.revision.payload.primary_blob)
            candidate_context = parsed.front_matter.get("context")
            if not isinstance(candidate_context, str):
                raise DsnRuntimeError("REQ is missing its CTX Reference")
            if context is None:
                context = candidate_context
            elif context != candidate_context:
                raise DsnRuntimeError("DSN Scope Inputs belong to different CTX revisions")
            for table in find_tables(parsed, REQ_HEADERS):
                for row in table.rows:
                    if row["ID"].startswith("R-"):
                        req_items.append(f"{artifact_id}@{revision}#{row['ID']}")
            for table in find_tables(parsed, AC_HEADERS):
                for row in table.rows:
                    if row["ID"].startswith("AC-"):
                        ac_items.append(f"{artifact_id}@{revision}#{row['ID']}")
        if context is None:
            raise DsnRuntimeError("DSN requires at least one REQ Scope Input")
        resolver = ControlInputResolver(self.project_root)
        for reference in controls:
            resolver.resolve_for_phase(store, reference, "DSN")
        return UpstreamScope(
            context_reference=context,
            scope_references=scope,
            control_references=controls,
            requirement_items=tuple(req_items),
            acceptance_items=tuple(ac_items),
        )

    def _payload(
        self,
        control,
        build: BuildResult,
    ) -> CanonicalRevisionPayload:
        return CanonicalRevisionPayload(
            artifact_id=control.artifact_id,
            artifact_type="DSN",
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
        build: BuildResult | None = None,
        ok: bool,
        status: str,
        warnings: Sequence[Mapping[str, Any]] = (),
        errors: Sequence[Mapping[str, Any]] = (),
        next_action: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        artifact = None
        gate = "pending"
        failed: list[str] = []
        open_items: list[Mapping[str, Any]] = []
        if stored is not None:
            artifact = {
                "id": stored.control.artifact_id,
                "type": "DSN",
                "revision": stored.control.revision,
                "revision_state": stored.control.state,
                "artifact_status": stored.payload.artifact_status,
                "reference": (
                    f"{stored.control.artifact_id}@{stored.control.revision}"
                    if stored.control.state == "frozen"
                    else None
                ),
            }
        if build is not None:
            gate = build.gate_result
            failed = list(build.failed_checks)
            open_items = [dict(item) for item in build.open_items]
        return {
            "contract": RESULT_CONTRACT,
            "ok": ok,
            "operation": invocation["operation"],
            "status": status,
            "artifact": artifact,
            "gate": {"result": gate, "failed_checks": failed},
            "open_items": open_items,
            "warnings": [dict(item) for item in warnings],
            "errors": [dict(item) for item in errors],
            "next_action": dict(next_action) if next_action else None,
        }

    def _error(self, invocation, exc: Exception, *, code: str | None = None):
        error_code = code or getattr(exc, "code", "DSN_RUNTIME_ERROR")
        status = "blocked" if isinstance(exc, ConflictError) else "failed"
        return self._result(
            invocation,
            ok=False,
            status=status,
            errors=({"code": error_code, "message": str(exc)},),
            next_action={
                "code": "RESOLVE_DSN_INPUT",
                "message": "修正 DSN 输入或 Store 状态后重试",
                "requires_user": True,
                "command": None,
            },
        )

    def _write(
        self,
        invocation,
        store: ArtifactStore,
        control,
        upstream: UpstreamScope,
    ):
        design = invocation["inputs"].get("design")
        if not isinstance(design, Mapping):
            raise DsnRuntimeError("inputs.design must be an object")
        build = self.builder.build(
            artifact_id=control.artifact_id,
            revision=control.revision,
            upstream=upstream,
            design=design,
            final_confirmation=invocation["inputs"].get("final_confirmation"),
        )
        stored = store.write_open_revision(
            self._payload(control, build),
            expected_generation=control.generation,
        )
        if build.status in {"ready", "ready_with_exception"}:
            store.freeze_revision(
                control.artifact_id,
                control.revision,
                verifier=DsnVerifier(self.project_root),
                now=self.clock(),
            )
            stored = store.read_revision(control.artifact_id, control.revision)
        ok = stored.payload.artifact_status in {"ready", "ready_with_exception"}
        status = (
            "completed"
            if ok
            else (
                "action_required"
                if stored.payload.artifact_status == "waiting_input"
                else "failed"
            )
        )
        next_action = None
        if not ok:
            next_action = {
                "code": (
                    "COMPLETE_DSN_INPUT"
                    if stored.payload.artifact_status == "waiting_input"
                    else "CORRECT_DSN"
                ),
                "message": (
                    "补充设计内容、决策或 Final Confirmation"
                    if stored.payload.artifact_status == "waiting_input"
                    else "修正失败的 DSN Check"
                ),
                "requires_user": True,
                "command": (
                    f"/sdlc-200-dsn revise --reference "
                    f"{control.artifact_id}@{control.revision}"
                ),
            }
        return self._result(
            invocation,
            stored=stored,
            build=build,
            ok=ok,
            status=status,
            next_action=next_action,
        )

    def create(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        if invocation.get("artifact_reference"):
            return self._error(
                invocation,
                DsnRuntimeError("create does not accept artifact_reference"),
                code="ARTIFACT_REFERENCE_INVALID",
            )
        if not _write_authorized(invocation) and not invocation["options"].get(
            "dry_run"
        ):
            return self._result(
                invocation,
                ok=False,
                status="action_required",
                errors=(
                    {
                        "code": "WRITE_AUTHORIZATION_REQUIRED",
                        "message": "当前 write_policy 不允许 DSN Store 写入",
                    },
                ),
                next_action={
                    "code": "AUTHORIZE_STANDARD_WRITE",
                    "message": "允许标准项目内 ArtifactStore 写入，或使用 dry-run",
                    "requires_user": True,
                    "command": None,
                },
            )
        try:
            read_store = ArtifactStore.open_read_only(self.project_root)
            upstream = self._resolve_inputs(read_store, invocation["inputs"])
            design = invocation["inputs"].get("design")
            if not isinstance(design, Mapping):
                raise DsnRuntimeError("inputs.design must be an object")
            if not str(design.get("boundary") or "").strip():
                return self._result(
                    invocation,
                    ok=False,
                    status="action_required",
                    errors=(
                        {
                            "code": "DESIGN_BOUNDARY_REQUIRED",
                            "message": (
                                "Design Boundary must be decided before DSN allocation"
                            ),
                        },
                    ),
                    next_action={
                        "code": "DECIDE_DESIGN_BOUNDARY",
                        "message": (
                            "确认当前 REQ 应共享一个 DSN 还是拆分为多个独立设计边界"
                        ),
                        "requires_user": True,
                        "command": None,
                    },
                )
            if invocation["options"].get("dry_run"):
                preview = self.builder.build(
                    artifact_id="DSN-20990101000000-01",
                    revision=1,
                    upstream=upstream,
                    design=design,
                    final_confirmation=invocation["inputs"].get(
                        "final_confirmation"
                    ),
                )
                return self._result(
                    invocation,
                    build=preview,
                    ok=True,
                    status="completed",
                    warnings=(
                        {
                            "code": "DRY_RUN",
                            "message": "未分配 Artifact 或修改 Store",
                        },
                    ),
                )
            store = ArtifactStore.open_read_write(
                self.project_root, clock=self.clock
            )
            allocation = store.allocate_artifact("DSN", now=self.clock())
            control = store.allocate_revision(allocation.artifact_id, now=self.clock())
            try:
                return self._write(invocation, store, control, upstream)
            except Exception as exc:
                try:
                    current = store.read_revision(
                        control.artifact_id, control.revision
                    ).control
                    if current.state == "open" and not current.materialized:
                        store.abandon_revision(
                            control.artifact_id,
                            control.revision,
                            reason="DSN build failed: " + str(exc)[:400],
                        )
                except ArtifactStoreError:
                    pass
                raise
        except (
            ArtifactStoreError,
            ControlInputError,
            CanonicalFormatError,
            DsnRuntimeError,
        ) as exc:
            return self._error(invocation, exc)

    def revise(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        reference = invocation.get("artifact_reference")
        if not reference:
            return self._error(
                invocation,
                DsnRuntimeError("revise requires an exact DSN Reference"),
                code="ARTIFACT_REFERENCE_REQUIRED",
            )
        if not _write_authorized(invocation) and not invocation["options"].get(
            "dry_run"
        ):
            return self._error(
                invocation,
                DsnRuntimeError("write authorization is required"),
                code="WRITE_AUTHORIZATION_REQUIRED",
            )
        try:
            artifact_id, revision_number = _exact_base(reference, "DSN")
            read_store = ArtifactStore.open_read_only(self.project_root)
            upstream = self._resolve_inputs(read_store, invocation["inputs"])
            existing = read_store.read_revision(artifact_id, revision_number)
            if existing.control.state == "abandoned":
                raise InvalidStateError("abandoned Revision cannot be revised")
            design = invocation["inputs"].get("design")
            if not isinstance(design, Mapping):
                raise DsnRuntimeError("inputs.design must be an object")
            preview = self.builder.build(
                artifact_id=artifact_id,
                revision=revision_number,
                upstream=upstream,
                design=design,
                final_confirmation=invocation["inputs"].get("final_confirmation"),
            )
            same = (
                compute_control_input_digest(preview.raw_bytes)
                == compute_control_input_digest(existing.payload.primary_blob)
                and preview.manifest.raw_bytes
                == existing.payload.manifest.raw_bytes
                and tuple((item.member_id, item.sha256) for item in preview.members)
                == tuple(
                    (item.member_id, item.sha256)
                    for item in existing.payload.members
                )
            )
            if existing.control.state == "frozen" and same:
                return self._result(
                    invocation,
                    stored=existing,
                    build=preview,
                    ok=True,
                    status="completed",
                    warnings=(
                        {
                            "code": "NO_CHANGE",
                            "message": (
                                "候选设计与 frozen Revision 相同，未创建空 Revision"
                            ),
                        },
                    ),
                )
            if invocation["options"].get("dry_run"):
                return self._result(
                    invocation,
                    build=preview,
                    ok=True,
                    status="completed",
                    warnings=(
                        {
                            "code": "DRY_RUN",
                            "message": "未修改 DSN Revision",
                        },
                    ),
                )
            store = ArtifactStore.open_read_write(
                self.project_root, clock=self.clock
            )
            allocated_new = False
            if existing.control.state == "open":
                control = existing.control
            else:
                control = store.allocate_revision(
                    artifact_id,
                    base_revision=revision_number,
                    now=self.clock(),
                )
                allocated_new = True
            try:
                return self._write(invocation, store, control, upstream)
            except Exception as exc:
                if allocated_new:
                    try:
                        current = store.read_revision(
                            control.artifact_id, control.revision
                        ).control
                        if current.state == "open":
                            store.abandon_revision(
                                control.artifact_id,
                                control.revision,
                                reason="DSN revise failed: " + str(exc)[:400],
                            )
                    except ArtifactStoreError:
                        pass
                raise
        except (
            ArtifactStoreError,
            ControlInputError,
            CanonicalFormatError,
            DsnRuntimeError,
        ) as exc:
            return self._error(invocation, exc)

    def check(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        reference = invocation.get("artifact_reference")
        if not reference:
            return self._error(
                invocation,
                DsnRuntimeError("check requires an exact DSN Reference"),
                code="ARTIFACT_REFERENCE_REQUIRED",
            )
        try:
            artifact_id, revision_number = _exact_base(reference, "DSN")
            store = ArtifactStore.open_read_only(self.project_root)
            stored = store.read_revision(artifact_id, revision_number)
            store.verify_digest(artifact_id, revision_number)
            verifier = DsnVerifier(self.project_root)
            verifier.verify(reference, stored)
            parsed = parse_canonical_artifact(stored.payload.primary_blob)
            summary = require_single_row(
                require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate Summary"),
                "Gate Summary",
            )
            gate = summary["Gate Result"]
            build_stub = BuildResult(
                raw_bytes=stored.payload.primary_blob,
                status=stored.payload.artifact_status,
                gate_result=gate,
                failed_checks=(),
                open_items=(),
                active_exceptions=(),
                final_confirmation_valid=stored.payload.artifact_status
                in {"ready", "ready_with_exception"},
                members=stored.payload.members,
                manifest=stored.payload.manifest,
                subject_digest="N/A",
            )
            ok = stored.control.state == "frozen" and stored.payload.artifact_status in {
                "ready",
                "ready_with_exception",
            }
            return self._result(
                invocation,
                stored=stored,
                build=build_stub,
                ok=ok,
                status="completed" if ok else "action_required",
                next_action=(
                    None
                    if ok
                    else {
                        "code": "REVISE_DSN",
                        "message": "当前 DSN 尚未形成可用 Authority",
                        "requires_user": True,
                        "command": (
                            f"/sdlc-200-dsn revise --reference {reference}"
                        ),
                    }
                ),
            )
        except (ArtifactStoreError, CanonicalFormatError, DsnRuntimeError) as exc:
            return self._error(invocation, exc)


INTERFACE_PATH = Path(__file__).resolve().parents[1] / "references/interface.json"


__all__ = tuple(name for name in globals() if not name.startswith("__"))
