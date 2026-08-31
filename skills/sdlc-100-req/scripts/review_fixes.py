"""Independent-review fixes applied to the REQ runtime entry."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from req_semantics import RequirementSemanticError, validate_persisted_requirement


def _base_reference(base, reference: str) -> str:
    artifact_id, revision = base.exact_artifact_reference(reference)
    return f"{artifact_id}@{revision}"


def _replace_front_inputs(base, raw: bytes, control_inputs: Sequence[str]) -> bytes:
    text = raw.decode("utf-8")
    lines = text.splitlines()
    try:
        start = lines.index("inputs:")
    except ValueError as exc:
        raise base.RequirementRuntimeError("REQ Front Matter inputs field is missing") from exc
    cursor = start + 1
    while cursor < len(lines) and lines[cursor].startswith("  - "):
        cursor += 1
    unique: list[str] = []
    for reference in control_inputs:
        value = _base_reference(base, reference)
        if value not in unique:
            unique.append(value)
    replacement = ["inputs:", *(f"  - {value}" for value in unique)]
    lines[start:cursor] = replacement
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def apply_review_fixes(base) -> None:
    original_build = base.RequirementBuilder.build
    original_render = base.RequirementBuilder._render
    original_verify = base.RequirementVerifier.verify
    original_check = base.RequirementHandler.check

    def render_fixed(self, *args, **kwargs):
        raw = original_render(self, *args, **kwargs)
        controls = kwargs.get("control_inputs", ())
        return _replace_front_inputs(base, raw, controls)

    def build_fixed(
        self,
        *,
        artifact_id: str,
        revision: int,
        context_reference: str,
        control_inputs: Sequence[str],
        requirement: Mapping[str, Any],
        final_confirmation: Mapping[str, Any] | None,
    ):
        candidate = deepcopy(dict(requirement))
        sources = list(candidate.get("sources") or [])
        for reference in control_inputs:
            exists = any(
                isinstance(item, Mapping)
                and item.get("type") == "artifact"
                and item.get("content") == reference
                for item in sources
            )
            if not exists:
                sources.append(
                    {
                        "type": "artifact",
                        "content": reference,
                        "evidence_reference": "N/A",
                    }
                )
        candidate["sources"] = sources
        return original_build(
            self,
            artifact_id=artifact_id,
            revision=revision,
            context_reference=context_reference,
            control_inputs=control_inputs,
            requirement=candidate,
            final_confirmation=final_confirmation,
        )

    def verify_fixed(self, reference, revision):
        result = original_verify(self, reference, revision)
        validate_persisted_requirement(
            base.parse_canonical_artifact(revision.payload.primary_blob)
        )
        return result

    def create_fixed(self, invocation):
        if invocation["options"].get("dry_run"):
            return self._dry_run(invocation)
        if not base._write_authorized(invocation["confirmations"]):
            return self._error(
                invocation,
                "action_required",
                "WRITE_AUTHORIZATION_REQUIRED",
                "创建 REQ 需要当前请求的 Artifact Store 写入授权",
                "AUTHORIZE_ARTIFACT_STORE_WRITE",
                True,
            )
        if invocation.get("artifact_reference"):
            return self._error(
                invocation,
                "action_required",
                "ARTIFACT_REFERENCE_INVALID",
                "create 不接受已有 Artifact Reference",
                "REMOVE_ARTIFACT_REFERENCE",
                True,
            )
        write_store = None
        control = None
        try:
            read_store = base.ArtifactStore.open_read_only(self.project_root)
            context, controls = self._inputs(invocation, read_store)
            write_store = base.ArtifactStore.open_read_write(
                self.project_root, clock=self.clock
            )
            allocation = write_store.allocate_artifact("REQ", now=self.clock())
            control = write_store.allocate_revision(
                allocation.artifact_id, now=self.clock()
            )
            return self._write(
                invocation, write_store, control, context, controls
            )
        except base.StoreNotFoundError as exc:
            return self._exception(invocation, exc, "STORE_NOT_FOUND")
        except (
            base.ArtifactStoreError,
            base.RequirementRuntimeError,
            base.ControlInputError,
        ) as exc:
            _abandon_if_allocated(write_store, control, str(exc))
            return self._exception(invocation, exc)

    def revise_fixed(self, invocation):
        if invocation["options"].get("dry_run"):
            return self._dry_run(invocation)
        if not base._write_authorized(invocation["confirmations"]):
            return self._error(
                invocation,
                "action_required",
                "WRITE_AUTHORIZATION_REQUIRED",
                "修订 REQ 需要当前请求的 Artifact Store 写入授权",
                "AUTHORIZE_ARTIFACT_STORE_WRITE",
                True,
            )
        reference = invocation.get("artifact_reference")
        if not reference:
            return self._error(
                invocation,
                "action_required",
                "ARTIFACT_REFERENCE_REQUIRED",
                "revise 需要准确 REQ Reference",
                "PROVIDE_EXACT_ARTIFACT_REFERENCE",
                True,
            )
        write_store = None
        control = None
        allocated_new = False
        try:
            artifact_id, revision_number = base._exact_base_reference(reference)
            read_store = base.ArtifactStore.open_read_only(self.project_root)
            context, controls = self._inputs(invocation, read_store)
            existing = read_store.read_revision(artifact_id, revision_number)
            if existing.control.state == "abandoned":
                raise base.InvalidStateError("abandoned Revision cannot be revised")
            requirement = base._mapping(
                invocation["inputs"].get("requirement"),
                "inputs.requirement",
            )
            if existing.control.state == "frozen":
                preview = self.builder.build(
                    artifact_id=artifact_id,
                    revision=revision_number,
                    context_reference=context,
                    control_inputs=controls,
                    requirement=requirement,
                    final_confirmation=None,
                )
                same_content = (
                    base.compute_control_input_digest(preview.raw_bytes)
                    == base.compute_control_input_digest(
                        existing.payload.primary_blob
                    )
                    and preview.manifest.raw_bytes
                    == existing.payload.manifest.raw_bytes
                    and tuple(
                        (item.member_id, item.sha256) for item in preview.members
                    )
                    == tuple(
                        (item.member_id, item.sha256)
                        for item in existing.payload.members
                    )
                )
                if same_content:
                    return self._result(
                        invocation,
                        ok=True,
                        status="completed",
                        stored=existing,
                        gate=self._gate_from_blob(existing.payload.primary_blob),
                        open_items=self._open_items_from_blob(
                            existing.payload.primary_blob
                        ),
                        warnings=[
                            {
                                "code": "NO_CHANGE",
                                "message": "候选内容与 frozen Revision 相同，未创建空 Revision",
                            }
                        ],
                        errors=[],
                        next_action=None,
                    )
            write_store = base.ArtifactStore.open_read_write(
                self.project_root, clock=self.clock
            )
            if existing.control.state == "open":
                expected = invocation["inputs"].get(
                    "expected_generation", existing.control.generation
                )
                if expected != existing.control.generation:
                    raise base.ConflictError(
                        "expected_generation does not match current open Revision"
                    )
                control = existing.control
            elif existing.control.state == "frozen":
                control = write_store.allocate_revision(
                    artifact_id,
                    base_revision=revision_number,
                    now=self.clock(),
                )
                allocated_new = True
            else:
                raise base.InvalidStateError("unsupported Revision State")
            return self._write(
                invocation, write_store, control, context, controls
            )
        except (
            base.ArtifactStoreError,
            base.RequirementRuntimeError,
            base.ControlInputError,
        ) as exc:
            if allocated_new:
                _abandon_if_allocated(write_store, control, str(exc))
            return self._exception(invocation, exc)

    def check_fixed(self, invocation):
        reference = invocation.get("artifact_reference")
        if not reference:
            return original_check(self, invocation)
        try:
            artifact_id, revision_number = base._exact_base_reference(reference)
            store = base.ArtifactStore.open_read_only(self.project_root)
            stored = store.read_revision(artifact_id, revision_number)
            validate_persisted_requirement(
                base.parse_canonical_artifact(stored.payload.primary_blob)
            )
        except (
            base.ArtifactStoreError,
            base.RequirementRuntimeError,
            base.CanonicalFormatError,
            RequirementSemanticError,
        ) as exc:
            return self._exception(invocation, exc)
        return original_check(self, invocation)

    def _abandon_if_allocated(store, control, reason: str) -> None:
        if store is None or control is None:
            return
        try:
            current = store.read_revision(
                control.artifact_id, control.revision
            ).control
            if current.state == "open":
                store.abandon_revision(
                    control.artifact_id,
                    control.revision,
                    reason="REQ build failed: " + reason[:400],
                )
        except base.ArtifactStoreError:
            pass

    base.RequirementBuilder._render = render_fixed
    base.RequirementBuilder.build = build_fixed
    base.RequirementVerifier.verify = verify_fixed
    base.RequirementHandler.create = create_fixed
    base.RequirementHandler.revise = revise_fixed
    base.RequirementHandler.check = check_fixed
