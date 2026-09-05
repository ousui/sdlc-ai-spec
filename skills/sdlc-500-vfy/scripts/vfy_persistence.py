"""Shared ArtifactStore adapter for canonical VFY state."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from packages.sdlc_artifact_store import (
    ArtifactStore,
    CanonicalRevisionPayload,
    compute_sha256,
)
from packages.sdlc_phasekit import manifest
from vfy_builder import canonical_members, final_confirmation_from_payload, render_markdown
from vfy_canonical import validate_primary_against_state
from vfy_common import exact_artifact_reference, require
from vfy_domain_verifier import VfyDomainVerifier

STATE_MEMBER_ID = "VFY-STATE"


def build_payload(state: Mapping[str, Any]) -> CanonicalRevisionPayload:
    artifact = state["artifact"]
    ordered_members = canonical_members(state)
    primary = render_markdown(state, members=ordered_members).encode("utf-8")
    validate_primary_against_state(
        primary,
        state,
        member_ids=[item.member_id for item in ordered_members],
        members=ordered_members,
    )
    return CanonicalRevisionPayload(
        artifact_id=artifact["id"],
        artifact_type="VFY",
        revision=int(artifact["revision"]),
        artifact_status=str(artifact["artifact_status"]),
        primary_blob=primary,
        primary_media_type="text/markdown",
        primary_sha256=compute_sha256(primary),
        members=ordered_members,
        manifest=manifest(ordered_members),
    )


def _state_from_stored(stored: Any) -> dict[str, Any]:
    matches = [
        item for item in stored.payload.members if item.member_id == STATE_MEMBER_ID
    ]
    require(
        len(matches) == 1,
        "VFY_CONTRACT_INVALID",
        "Stored VFY Revision must contain exactly one VFY-STATE member",
    )
    state = json.loads(matches[0].raw_bytes.decode("utf-8"))
    state["final_confirmation"] = final_confirmation_from_payload(
        stored.payload.primary_blob, state
    )
    state["artifact"]["revision_state"] = stored.control.state
    state["artifact"]["artifact_status"] = stored.payload.artifact_status
    validate_primary_against_state(
        stored.payload.primary_blob,
        state,
        member_ids=[item.member_id for item in stored.payload.members],
        members=stored.payload.members,
    )
    return state


def create_revision(
    project_root: Path,
    state: Mapping[str, Any],
    *,
    base_revision: int | None = None,
) -> tuple[dict[str, Any], int]:
    store = ArtifactStore.open_read_write(project_root)
    store.initialize()
    output = deepcopy(dict(state))
    if output["artifact"].get("id") and output["artifact"].get("allocated"):
        artifact_id = str(output["artifact"]["id"])
    else:
        allocation = store.allocate_artifact("VFY")
        artifact_id = allocation.artifact_id
        output["artifact"]["id"] = artifact_id
    control = store.allocate_revision(artifact_id, base_revision=base_revision)
    output["artifact"].update(
        {
            "revision": control.revision,
            "reference": f"{artifact_id}@{control.revision}",
            "base_revision": control.base_revision,
            "revision_state": control.state,
            "allocated": True,
        }
    )
    stored = store.write_open_revision(
        build_payload(output),
        expected_generation=control.generation,
    )
    return _state_from_stored(stored), stored.control.generation


def write_open_revision(
    project_root: Path,
    state: Mapping[str, Any],
    *,
    expected_generation: int,
) -> tuple[dict[str, Any], int]:
    store = ArtifactStore.open_read_write(project_root)
    stored = store.write_open_revision(
        build_payload(state),
        expected_generation=expected_generation,
    )
    return _state_from_stored(stored), stored.control.generation


def read_revision(project_root: Path, reference: str) -> tuple[dict[str, Any], int]:
    exact = exact_artifact_reference(reference, "VFY")
    artifact_id, revision_text = exact.rsplit("@", 1)
    store = ArtifactStore.open_read_only(project_root)
    stored = store.read_revision(artifact_id, int(revision_text))
    state = _state_from_stored(stored)
    if stored.control.state == "frozen":
        domain = VfyDomainVerifier(project_root).verify(exact, stored)
        require(
            domain.approved,
            "VFY_CONTRACT_INVALID",
            domain.message,
        )
    return state, stored.control.generation


def freeze_revision(project_root: Path, reference: str) -> dict[str, Any]:
    exact = exact_artifact_reference(reference, "VFY")
    artifact_id, revision_text = exact.rsplit("@", 1)
    store = ArtifactStore.open_read_write(project_root)
    store.freeze_revision(
        artifact_id,
        int(revision_text),
        verifier=VfyDomainVerifier(project_root),
    )
    state, _ = read_revision(project_root, exact)
    return state


def abandon_revision(project_root: Path, reference: str, reason: str) -> None:
    exact = exact_artifact_reference(reference, "VFY")
    artifact_id, revision_text = exact.rsplit("@", 1)
    store = ArtifactStore.open_read_write(project_root)
    store.abandon_revision(artifact_id, int(revision_text), reason=reason)
