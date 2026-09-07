"""Final RLS confirmation binds an independently readable current payload."""
from tests.skill_rls.final_support import FinalRlsCase
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_runtime.canonical import (compute_control_input_digest, compute_check_set_result_digest,
    parse_canonical_artifact, require_single_table, require_single_row, CHECK_HEADERS, GATE_SUMMARY_HEADERS)

class RlsReviewableConfirmationTests(FinalRlsCase):
    def current(self):
        i,v=self.reference.split('@');return ArtifactStore.open_read_only(self.root).read_revision(i,int(v))
    def test_exact_pending_payload_has_complete_checks_and_current_confirmation_binding(self):
        self.create();self.execute();self.confirm();before=self.current();p=parse_canonical_artifact(before.payload.primary_blob)
        checks=require_single_table(p,CHECK_HEADERS,'checks').rows
        self.assertTrue({f'CORE-G-{i:03d}' for i in range(1,10)} <= {r['Check ID'] for r in checks})
        gate=require_single_row(require_single_table(p,GATE_SUMMARY_HEADERS,'Gate'),'Gate')
        self.assertEqual('pending',gate['Gate Result'])
        requested=self.service.confirmation_requirements(self.reference,self.target)
        self.assertEqual(requested['control_input_digest'],compute_control_input_digest(before.payload.primary_blob))
        self.assertEqual(requested['check_set_result_digest'],compute_check_set_result_digest(p))
        self.freeze();after=self.current()
        self.assertEqual('frozen',after.control.state)
        self.assertEqual(compute_control_input_digest(before.payload.primary_blob),compute_control_input_digest(after.payload.primary_blob))
        self.assertEqual(before.payload.members,after.payload.members)
