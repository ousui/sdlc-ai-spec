"""Fail-closed RLS Primary/State/Manifest and current-binding verification."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from packages.sdlc_artifact_store import ArtifactStore, DomainVerification
from packages.sdlc_phasekit import manifest
from rls_canonical import STATE_MEMBER_ID, canonical_members, canonical_status, load_state_member, validate_primary_against_state, confirmation_from_primary
from rls_common import exact_reference, require
from rls_verifier import verify


def state_from_stored(revision):
    payload = revision.payload
    reference = f"{payload.artifact_id}@{payload.revision}"
    exact_reference(reference, "RLS")
    matches = [item for item in payload.members if item.member_id == STATE_MEMBER_ID]
    require(payload.artifact_type == "RLS" and len(matches) == 1,
            "RLS_CONTRACT_INVALID", "exactly one RLS-STATE Member is required")
    state = load_state_member(matches[0].raw_bytes)
    artifact = state["artifact"]
    require(artifact.get("id") == payload.artifact_id and artifact.get("revision") == payload.revision
            and artifact.get("reference") == reference, "RLS_CONTRACT_INVALID", "RLS identity mismatch")
    if not state.get("provisional", True):
        require(state.get("final_confirmation") is None, "RLS_CONTRACT_INVALID", "RLS state must not duplicate Primary confirmation")
        state["final_confirmation"] = confirmation_from_primary(payload.primary_blob, state)
    require(canonical_status(state) == payload.artifact_status, "RLS_CONTRACT_INVALID", "RLS Artifact Status mismatch")
    expected = canonical_members(state)
    actual = tuple(sorted(payload.members, key=lambda item: item.member_id))
    require(tuple(sorted(expected, key=lambda item: item.member_id)) == actual
            and manifest(expected) == payload.manifest,
            "RLS_CONTRACT_INVALID", "RLS Supporting Member or Manifest closure mismatch")
    validate_primary_against_state(payload.primary_blob, state, members=expected)
    control = artifact.get("revision_state")
    require(revision.control.state == "abandoned" or control == revision.control.state or
            (control == "frozen" and revision.control.state == "open" and state.get("final_confirmation"))
            or (not state.get("provisional", True) and control == "open" and revision.control.state == "frozen"),
            "RLS_CONTRACT_INVALID", "RLS state disagrees with Store control")
    state["artifact"]["revision_state"] = revision.control.state
    return state


class RlsDomainVerifier:
    def __init__(self, project_root, *, expected_generation=None):
        self.project_root = Path(project_root).resolve()
        self.expected_generation = expected_generation

    def verify(self, reference, revision):
        try:
            exact = exact_reference(reference, "RLS")
            state = state_from_stored(revision)
            require(state["artifact"]["reference"] == exact, "RLS_CONTRACT_INVALID", "wrong exact RLS reference")
            if self.expected_generation is not None:
                require(revision.control.generation == self.expected_generation,
                        "RLS_CONTRACT_INVALID", "stale freeze generation")
            stored_gate = state.get("artifact_gate")
            projection = verify(deepcopy(state), finalizing=True)
            require(stored_gate == projection["artifact_gate"] and stored_gate in {"pass", "pass_with_exception"}
                    and revision.payload.artifact_status == canonical_status(state),
                    "RLS_CONTRACT_INVALID", "stored Gate differs from pure recomputation")
            require(not state.get("provisional", True), "RLS_VFY_NOT_READY", "provisional inputs cannot freeze a final RLS")
            validate_current_upstream(self.project_root, state)
            from rls_trusted_effect import TrustedEffectRecords
            from rls_execution_journal import ExecutionJournal
            TrustedEffectRecords(self.project_root).verify_history(state)
            from rls_human_evidence import TrustedHumanObservations
            TrustedHumanObservations(self.project_root).verify_history(state)
            ExecutionJournal(self.project_root, exact).require_resolved()
            from packages.sdlc_runtime.authority import FrozenArtifactAuthorityVerifier
            canonical_view = replace(revision, control=replace(revision.control, state="frozen"))
            core = FrozenArtifactAuthorityVerifier(self.project_root).verify(exact, canonical_view)
            require(core.approved and core.payload_binding == revision.verification_binding,
                    "RLS_FINAL_CONFIRMATION_STALE", "Core final authority is not approved for current binding")
            return DomainVerification(reference=exact, payload_binding=revision.verification_binding,
                                      approved=True, message="RLS canonical and final confirmation verified")
        except Exception as exc:
            return DomainVerification(reference=reference, payload_binding=revision.verification_binding,
                                      approved=False, message=f"RLS domain verification failed: {exc}")


def verify_persisted_reference(project_root, reference):
    exact = exact_reference(reference, "RLS")
    identity, revision = exact.split("@")
    stored = ArtifactStore.open_read_only(Path(project_root).resolve()).read_revision(identity, int(revision))
    return RlsDomainVerifier(project_root).verify(exact, stored)


def validate_current_upstream(root, state):
    from rls_vfy_adapter import read_vfy_candidate
    from rls_revision import candidate_contract_delta
    candidate = read_vfy_candidate(root, state["release_contract"]["vfy_reference"])
    require(candidate.authority_verified and not candidate_contract_delta(state["release_contract"], candidate)
            and state["release_contract"]["scope_reference"] == candidate.scope_reference
            and state["release_contract"]["result_references"] == list(candidate.result_references)
            and state["context_reference"] == candidate.context_reference and state["profile"] == candidate.profile
            and state["input_references"] == list(candidate.input_references)
            and state["release_contract"]["rls_work_item_references"] == list(candidate.rls_work_item_references),
            "RLS_VFY_NOT_READY", "RLS immutable upstream binding is no longer current")
    from rls_exceptions import verify_current_exceptions
    verify_current_exceptions(root, state, candidate)
    return candidate
