"""RLS persistence through the real shared ArtifactStore API."""
from copy import deepcopy
from pathlib import Path

from packages.sdlc_artifact_store import ArtifactStore, CanonicalRevisionPayload, ConflictError, compute_sha256
from packages.sdlc_phasekit import manifest
from rls_canonical import canonical_members, canonical_status, render_markdown
from rls_common import exact_reference, require
from rls_domain_verifier import RlsDomainVerifier, state_from_stored


def build_payload(state):
    artifact = state["artifact"]
    exact_reference(artifact["reference"], "RLS")
    members = canonical_members(state)
    primary = render_markdown(state, members=members)
    return CanonicalRevisionPayload(
        artifact_id=artifact["id"], artifact_type="RLS", revision=artifact["revision"],
        artifact_status=canonical_status(state), primary_blob=primary,
        primary_media_type="text/markdown", primary_sha256=compute_sha256(primary),
        members=members, manifest=manifest(members),
    )


def create_revision(project_root, state, *, base_revision=None, expected_generation=None):
    root = Path(project_root).resolve()
    store = ArtifactStore.open_read_write(root)
    store.initialize()
    work = deepcopy(state)
    artifact = work["artifact"]
    if not artifact.get("allocated"):
        artifact["id"] = store.allocate_artifact("RLS").artifact_id
    control = store.allocate_revision(artifact["id"], base_revision=base_revision)
    artifact.update(revision=control.revision, reference=f"{artifact['id']}@{control.revision}",
                    base_revision=control.base_revision, revision_state="open", allocated=True)
    try:
        if expected_generation is not None and expected_generation != control.generation:
            raise ConflictError("RLS allocation generation differs from expected generation")
        stored = store.write_open_revision(build_payload(work), expected_generation=control.generation)
    except Exception:
        store.abandon_revision(artifact["id"], control.revision, reason="RLS first write failed before target effect")
        raise
    return state_from_stored(stored), stored.control.generation


def write_open_revision(project_root, state, *, expected_generation,
                        allow_terminal_staging=False):
    artifact = state["artifact"]
    exact_reference(artifact["reference"], "RLS")
    require(artifact.get("revision_state") == "open" or
            (allow_terminal_staging and artifact.get("revision_state") == "frozen"
             and isinstance(state.get("final_confirmation"), dict)),
            "RLS_CONTRACT_INVALID", "only open or explicit terminal staging can be written")
    store = ArtifactStore.open_read_write(Path(project_root).resolve())
    from rls_contract import effect_digest
    current = state_from_stored(store.read_revision(artifact["id"], artifact["revision"]))
    require(effect_digest(current) == effect_digest(state), "RLS_EFFECT_AUTHORIZATION_STALE", "immutable contract changed within a Revision")
    history = current.get("effect_authorization_history", [])
    require(state.get("effect_authorization_history", [])[:len(history)] == history,
            "RLS_EFFECT_AUTHORIZATION_STALE", "authorization history cannot be rewritten")
    stored = store.write_open_revision(build_payload(state), expected_generation=expected_generation)
    return state_from_stored(stored), stored.control.generation


def read_revision(project_root, reference):
    root = Path(project_root).resolve()
    exact = exact_reference(reference, "RLS")
    identity, revision = exact.split("@")
    store = ArtifactStore.open_read_only(root)
    stored = store.read_revision(identity, int(revision))
    state = state_from_stored(stored)
    if stored.control.state == "frozen":
        domain = RlsDomainVerifier(root).verify(exact, stored)
        require(domain.approved and domain.reference == exact
                and domain.payload_binding == stored.verification_binding,
                "RLS_CONTRACT_INVALID", domain.message)
    return state, stored.control.generation


def freeze_revision(project_root, reference, *, expected_generation):
    root = Path(project_root).resolve()
    exact = exact_reference(reference, "RLS")
    identity, revision = exact.split("@")
    store = ArtifactStore.open_read_write(root)
    store.freeze_revision(identity, int(revision),
                          verifier=RlsDomainVerifier(root, expected_generation=expected_generation))
    return read_revision(root, exact)


def abandon_revision(project_root, reference, *, expected_generation, reason="RLS abandoned before effect"):
    root = Path(project_root).resolve()
    exact = exact_reference(reference, "RLS")
    identity, revision = exact.split("@")
    store = ArtifactStore.open_read_write(root)
    stored = store.read_revision(identity, int(revision))
    require(stored.control.generation == expected_generation, "RLS_CONTRACT_INVALID", "stale abandon generation")
    state = state_from_stored(stored)
    require(not state.get("target_effect") and not state.get("effect_uncertain"),
            "RLS_CANCEL_NOT_ALLOWED", "cannot abandon a Revision with possible target effects")
    return store.abandon_revision(identity, int(revision), reason=reason).generation
