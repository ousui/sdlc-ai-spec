"""Actual Store and adversarial canonical readback tests for final RLS."""
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch
from tests.skill_rls.final_support import FinalRlsCase, snapshot
from rls_domain_verifier import RlsDomainVerifier, state_from_stored
from rls_persistence import build_payload, write_open_revision
from packages.sdlc_artifact_store import ArtifactStore, DomainVerification, compute_sha256


class RlsFinalStoreTests(FinalRlsCase):
    def stored(self):
        artifact = self.state["artifact"]
        return ArtifactStore.open_read_only(self.root).read_revision(artifact["id"], artifact["revision"])

    def test_primary_state_member_manifest_cross_checks(self):
        self.create(); current = self.stored()
        primary = current.payload.primary_blob.replace(b"Release 1.0.0", b"Release tampered")
        primary_tamper = replace(current.payload, primary_blob=primary, primary_sha256=compute_sha256(primary))
        for payload in (primary_tamper, replace(current.payload, members=()),
                        replace(current.payload, members=(*current.payload.members, current.payload.members[0])),
                        replace(current.payload, manifest=replace(current.payload.manifest, raw_bytes=b"{}"))):
            with self.subTest(payload=payload.primary_sha256):
                with self.assertRaises(Exception):
                    state_from_stored(replace(current, payload=payload))
        self.assertEqual(current, self.stored())

    def test_rehashed_supporting_state_cannot_disagree_with_primary(self):
        self.create(); current = self.stored(); member = current.payload.members[0]
        raw = member.raw_bytes.replace(b'"artifact_gate":"pending"', b'"artifact_gate":"pass"')
        self.assertNotEqual(raw, member.raw_bytes)
        changed = replace(member, raw_bytes=raw, sha256=compute_sha256(raw))
        with self.assertRaises(Exception):
            state_from_stored(replace(current, payload=replace(current.payload, members=(changed,))))

    def test_freeze_cannot_ignore_domain_false(self):
        self.create(); self.execute(); self.confirm()
        from tools.rls_fixture_chain import rls_final_confirmation
        confirmation = rls_final_confirmation(self.root, self.service, self.reference, self.target)
        calls = []
        def reject(verifier, reference, stored):
            calls.append(reference)
            return DomainVerification(reference, stored.verification_binding, False, "rejected")
        with patch.object(RlsDomainVerifier, "verify", reject):
            with self.assertRaises(Exception):
                self.service.finalize(self.reference, self.target, confirmation)
        self.assertEqual([self.reference], calls)
        self.assertEqual("open", self.stored().control.state)

    def test_stale_payload_binding_cannot_freeze(self):
        self.create(); previous = self.stored().verification_binding
        self.execute(); self.confirm()
        from tools.rls_fixture_chain import rls_final_confirmation
        confirmation = rls_final_confirmation(self.root, self.service, self.reference, self.target)
        calls = []
        def stale(verifier, reference, stored):
            calls.append(stored.verification_binding)
            return DomainVerification(reference, previous, True, "stale")
        with patch.object(RlsDomainVerifier, "verify", stale):
            with self.assertRaises(Exception):
                self.service.finalize(self.reference, self.target, confirmation)
        self.assertEqual(1, len(calls)); self.assertNotEqual(previous, calls[0])
        self.assertEqual("open", self.stored().control.state)

    def test_frozen_revision_cannot_be_rewritten(self):
        self.finish(); before = snapshot(self.root)
        with self.assertRaises(Exception):
            ArtifactStore.open_read_write(self.root).write_open_revision(build_payload(self.state), expected_generation=self.generation)
        self.assertEqual(before, snapshot(self.root))

    def test_cas_conflict_preserves_winning_revision(self):
        self.create(); stale = self.generation
        self.state["warnings"].append("first writer")
        self.state, self.generation = write_open_revision(self.root, self.state, expected_generation=stale)
        changed = deepcopy(self.state); changed["warnings"].append("stale second writer")
        with self.assertRaises(Exception):
            write_open_revision(self.root, changed, expected_generation=stale)
        self.assertEqual(self.state, self.service.read(self.reference)[0])

    def test_context_profile_input_and_gate_tamper_cannot_freeze(self):
        self.finish(); current = self.stored()
        for field, value in (("context_reference", "CTX-20000101000000-01@1"), ("profile", "wrong"),
                             ("input_references", [self.chain["vfy"]]), ("artifact_gate", "pending")):
            changed = deepcopy(self.state); changed[field] = value
            from rls_common import RlsError
            try:
                payload = build_payload(changed)
            except RlsError:
                continue
            result = RlsDomainVerifier(self.root).verify(self.reference, replace(current, payload=payload))
            self.assertFalse(result.approved, field)

    def test_authorization_history_cannot_be_rewritten(self):
        self.create(); self.execute()
        self.state["effect_authorization_history"][0]["authorizer_identity"] = "different"
        self.code("RLS_EFFECT_AUTHORIZATION_STALE", write_open_revision, self.root, self.state, expected_generation=self.generation)
