"""Generic observed-effect recovery and iterative-edit regressions."""
from copy import deepcopy
from unittest.mock import patch
from tests.skill_imp.support import ImpFixture
from packages.sdlc_artifact_store import compute_sha256
from packages.sdlc_runtime import compute_control_input_digest
from imp_result import read_state

class RealflowRecoveryTests(ImpFixture):
    def test_check_exception_returns_current_identity_and_observed_snapshot(self):
        method = self.implementation()
        with patch('imp_handler.execute_checks', side_effect=RuntimeError('injected check startup failure')):
            failed = self.invoke(implementation=method)
        self.assertFalse(failed['ok'])
        self.assertIsNotNone(failed['artifact'])
        self.assertEqual('applied', read_state(self.stored(failed))['stage'])
        before = (self.root/'integration/app.txt').read_bytes()
        resumed = self.invoke('revise', reference=failed['artifact']['reference'], implementation=method)
        self.assertEqual('executed', read_state(self.stored(resumed))['stage'])
        self.assertEqual(before, (self.root/'integration/app.txt').read_bytes())
        self.assertEqual(failed['artifact']['id'], resumed['artifact']['id'])
        self.finish(resumed)

    def test_later_write_failure_retains_first_observed_effect(self):
        method = self.implementation()
        second = dict(method['operations'][0], path='integration/second.txt', op='write_text',
                      content='second actual outcome\n', expected_sha256='absent')
        second.pop('before'); second.pop('after'); method['operations'].append(second)
        from imp_executor import apply_operations
        calls=[]
        def operation(*args, **kwargs):
            calls.append(args)
            if len(calls) == 2: raise OSError('injected later write failure')
            return apply_operations(*args, **kwargs)
        with patch('imp_executor.apply_operations', side_effect=operation):
            failed=self.invoke(implementation=method)
        self.assertIsNotNone(failed['artifact'])
        self.assertEqual(1,len(read_state(self.stored(failed))['completed_operations']))
        resumed=self.invoke('revise',reference=failed['artifact']['reference'],implementation=method)
        self.assertEqual(2,len(read_state(self.stored(resumed))['completed_operations']))
        self.finish(resumed)

    def test_same_file_can_be_appended_without_changing_completed_prefix(self):
        method=self.implementation();opened=self.create_open(implementation=method)
        changed=deepcopy(method)
        changed['operations'].append(dict(method['operations'][0], before='after', after='verified',
                                         expected_sha256=compute_sha256((self.root/'integration/app.txt').read_bytes())))
        changed['checks'][0]['expected']='version=verified\n'
        revised=self.invoke('revise',reference=opened['artifact']['reference'],implementation=changed)
        self.assertEqual('executed',read_state(self.stored(revised))['stage'])
        self.assertEqual(2,len(read_state(self.stored(revised))['completed_operations']))
        self.finish(revised)

    def test_external_drift_after_check_failure_is_not_overwritten(self):
        method=self.implementation()
        with patch('imp_handler.execute_checks',side_effect=RuntimeError('injected')):
            failed=self.invoke(implementation=method)
        target=self.root/'integration/app.txt';target.write_text('external concurrent change\n')
        resumed=self.invoke('revise',reference=failed['artifact']['reference'],implementation=method)
        self.assertFalse(resumed['ok']);self.assertEqual('external concurrent change\n',target.read_text())

    def test_python_syntax_check_needs_no_expected_argument(self):
        method=self.implementation(after='1')
        method['checks']=[dict(method['checks'][0],kind='python_syntax')]
        method['checks'][0].pop('expected')
        self.finish(self.create_open(implementation=method))

    def test_json_check_needs_no_expected_argument(self):
        method=self.implementation();op=method['operations'][0]
        op.update(op='write_text',content='{"enabled": true}\n');op.pop('before');op.pop('after')
        method['checks']=[dict(method['checks'][0],kind='json')];method['checks'][0].pop('expected')
        self.finish(self.create_open(implementation=method))

    def test_final_confirmation_binding_matches_readable_unsigned_content(self):
        opened=self.create_open()
        self.assertEqual(compute_control_input_digest(self.stored(opened).payload.primary_blob),
                         self.info(opened)['final_confirmation_bindings']['control_input_digest'])
