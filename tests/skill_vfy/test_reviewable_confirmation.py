"""Independent readback must bind the bytes actually available before review."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from tests.skill_vfy.support import persistent_authority_candidate, delegated_confirmation
from vfy_handler import VfyHandler
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_runtime.canonical import (parse_canonical_artifact, compute_control_input_digest,
    compute_check_set_result_digest)

class ReviewableConfirmationTests(TestCase):
    def prepare(self, root):
        handler=VfyHandler(root)
        opened=handler.create(persistent_authority_candidate(root),persist=True,run_automated=False)['state']
        ref=opened['artifact']['reference']
        executed=handler.run(reference=ref,state=None,store_generation=None,persist=True,
            method_ids=None,allow_commands=False,finalize=False)['state']
        i,v=ref.split('@');stored=ArtifactStore.open_read_only(root).read_revision(i,int(v))
        return handler,executed,stored
    def test_confirmation_matches_actual_persisted_bytes_and_nonfinal_checks(self):
        with TemporaryDirectory() as d:
            h,state,stored=self.prepare(Path(d));actual=stored.payload.primary_blob
            requested=h.confirmation_requirements(state)
            self.assertEqual(requested['control_input_digest'],compute_control_input_digest(actual))
            self.assertEqual(requested['check_set_result_digest'],compute_check_set_result_digest(parse_canonical_artifact(actual)))
    def test_finalization_preserves_business_material_and_old_draft_is_not_authority(self):
        with TemporaryDirectory() as d:
            root=Path(d);h,state,stored=self.prepare(root)
            self.assertEqual('open',stored.control.state)
            final=h.run(reference=state['artifact']['reference'],state=None,store_generation=None,persist=True,
                method_ids=[],allow_commands=False,finalize=True,
                confirmation=delegated_confirmation(root,state,reviewer='independent-test-reviewer',reviewed_executor='external-vfy-executor'))['state']
            i,v=final['artifact']['reference'].split('@');after=ArtifactStore.open_read_only(root).read_revision(i,int(v))
            self.assertEqual('frozen',after.control.state)
            self.assertEqual(compute_control_input_digest(stored.payload.primary_blob),compute_control_input_digest(after.payload.primary_blob))
            self.assertEqual([(m.member_id,m.raw_bytes) for m in stored.payload.members],[(m.member_id,m.raw_bytes) for m in after.payload.members])
