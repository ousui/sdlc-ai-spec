"""A caller can obtain required subject bindings without private builder access."""
from . import support_patch
from .support import DsnRuntimeFixture
from packages.sdlc_runtime import execute_phase

class ConfirmationBindingResultTests(DsnRuntimeFixture):
    def test_pending_result_exposes_exact_binding_without_approving(self):
        request=self.invocation(final=False)
        result=self.execute(request)
        reference=result['artifact']['id']+'@1'
        hints=[w['details'] for w in result['warnings'] if w['code']=='FINAL_CONFIRMATION_BINDINGS']
        self.assertEqual(1,len(hints))
        self.assertEqual(reference,hints[0]['artifact_reference'])
        self.assertRegex(hints[0]['subject_digest'],r'^sha256:[0-9a-f]{64}$')
        self.assertFalse(result['ok'])
        self.assertEqual('open',result['artifact']['revision_state'])
        approved=self.invocation(operation='revise', reference=reference)
        self.assertEqual(approved['inputs']['final_confirmation']['subject_digest'],hints[0]['subject_digest'])
        # This test uses an explicit fixture authority; real scenario review runs separately.
        final=execute_phase(self.handler,approved)
        self.assertTrue(final['ok'],final)
        self.assertFalse(any(w['code']=='FINAL_CONFIRMATION_BINDINGS' for w in final['warnings']))

    def test_input_change_invalidates_previous_hint(self):
        request=self.invocation(final=False)
        result=self.execute(request)
        reference=result['artifact']['id']+'@1'
        previous=next(w['details']['subject_digest'] for w in result['warnings'] if w['code']=='FINAL_CONFIRMATION_BINDINGS')
        changed=self.invocation(operation='revise', reference=reference)
        changed['inputs']['design']['summary']='Different legitimate project detail requiring a new exact approval'
        result=execute_phase(self.handler,changed)
        self.assertFalse(result['ok'])
        current=next(w['details']['subject_digest'] for w in result['warnings'] if w['code']=='FINAL_CONFIRMATION_BINDINGS')
        self.assertNotEqual(previous,current)
        self.assertEqual('open',result['artifact']['revision_state'])
