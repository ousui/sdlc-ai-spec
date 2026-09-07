"""A caller can obtain required subject bindings without private builder access."""
from .support import PlnFixture
from packages.sdlc_runtime import execute_phase

class ConfirmationBindingResultTests(PlnFixture):
    def test_pending_result_exposes_exact_binding_without_approving(self):
        request=self.pln_invocation(final=False)
        result=self.execute_pln(final=False)
        reference=result['artifact']['id']+'@1'
        hints=[w['details'] for w in result['warnings'] if w['code']=='FINAL_CONFIRMATION_BINDINGS']
        self.assertEqual(1,len(hints))
        self.assertEqual(reference,hints[0]['artifact_reference'])
        self.assertRegex(hints[0]['subject_digest'],r'^sha256:[0-9a-f]{64}$')
        self.assertFalse(result['ok'])
        self.assertEqual('open',result['artifact']['revision_state'])
        approved=self.pln_invocation(operation='revise',reference=reference)
        self.assertEqual(approved['inputs']['final_confirmation']['subject_digest'],hints[0]['subject_digest'])
        # This test uses an explicit fixture authority; real scenario review runs separately.
        final=execute_phase(self.pln_handler,approved)
        self.assertTrue(final['ok'],final)
        self.assertFalse(any(w['code']=='FINAL_CONFIRMATION_BINDINGS' for w in final['warnings']))

    def test_input_change_invalidates_previous_hint(self):
        request=self.pln_invocation(final=False)
        result=self.execute_pln(final=False)
        reference=result['artifact']['id']+'@1'
        previous=next(w['details']['subject_digest'] for w in result['warnings'] if w['code']=='FINAL_CONFIRMATION_BINDINGS')
        changed=self.pln_invocation(operation='revise',reference=reference)
        changed['inputs']['plan']['summary']='Different legitimate project detail requiring a new exact approval'
        result=execute_phase(self.pln_handler,changed)
        self.assertFalse(result['ok'])
        current=next(w['details']['subject_digest'] for w in result['warnings'] if w['code']=='FINAL_CONFIRMATION_BINDINGS')
        self.assertNotEqual(previous,current)
        self.assertEqual('open',result['artifact']['revision_state'])
