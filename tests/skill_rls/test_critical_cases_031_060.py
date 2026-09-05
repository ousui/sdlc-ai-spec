from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from tests.skill_rls.support import ROOT, artifact, authorize, candidate, complete_failure_before_effect, complete_success, dataclass_replace, fixture_payload, rewrite_evidence_event, run_authorized, sandbox, two_item_artifact
from rls_authorization import issue_authorization, validate_authorization
from rls_builder import build_provisional
from rls_common import RlsError, sha256_value
from rls_conclusion import compute_conclusion, compute_follow_up, issue_reference, normalize_return_phase, provisional_lifecycle_projection
from rls_confirmation import exception_resolution_state
from rls_contract import assert_no_effect_disposition
from rls_handler import abandon_first_write, cancel, check, confirm, create, execute, finalize, mark_not_run_before_effect, revise, retry_revision
from rls_items import normalize_items
from rls_scope import bind_scope
from rls_target import SandboxReleaseTarget
from rls_verifier import verify
from rls_vfy_adapter import adapt_vfy_payload

class RlsCriticalCases031060(unittest.TestCase):

    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(getattr(caught.exception, 'code', None), expected, caught.exception)
        return caught.exception

    def test_historical_e031_contract(self):
        value = two_item_artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
            retried = retry_revision(frozen, candidate(), 'N/A — Initial Release')
        self.assertEqual([x['id'] for x in retried['release_items']], ['RLI-001', 'RLI-002'])
        self.assertEqual([x['id'] for x in retried['confirmations']], ['RCF-001'])

    def test_historical_e032_authorization(self):
        value = artifact()
        self.assertIsNone(value['effect_authorization'])
        self.assertFalse(value['target_effect'])

    def test_historical_e033_authorization(self):
        value = artifact()
        with sandbox() as target:
            before = target.snapshot()
            self.assert_code('RLS_EFFECT_AUTHORIZATION_REQUIRED', execute, value, target, ['RLI-001'], None)
            self.assertEqual(target.snapshot(), before)
            self.assertFalse(target.state_path.exists())
            self.assertFalse(target.evidence_dir.exists())

    def test_historical_e034_authorization(self):
        value = artifact()
        auth = authorize(value)
        auth['revision'] = 2
        self.assert_code('RLS_EFFECT_AUTHORIZATION_STALE', validate_authorization, value, auth, ['RLI-001'], now='2026-09-04T04:05:00Z')

    def test_historical_e035_authorization(self):
        value = two_item_artifact()
        auth = authorize(value, ['RLI-001'])
        with sandbox() as target:
            self.assert_code('RLS_EFFECT_AUTHORIZATION_STALE', execute, value, target, ['RLI-002'], auth, now='2026-09-04T04:05:00Z')

    def test_historical_e036_authorization(self):
        value = artifact()
        auth = authorize(value)
        mutations = [('release_target', 'sandbox-b'), ('target_baseline', {'version': '0.9.0'}), ('result_references', ['IMP-OTHER@1/RES-001'])]
        for key, replacement in mutations:
            changed = deepcopy(value)
            changed['release_contract'][key] = replacement
            with self.subTest(field=key):
                self.assert_code('RLS_EFFECT_AUTHORIZATION_STALE', validate_authorization, changed, auth, ['RLI-001'], now='2026-09-04T04:05:00Z')

    def test_historical_e037_authorization(self):
        from tests.skill_rls.legacy_runtime import run_cli
        value = artifact()
        with sandbox() as target:
            payload = {'artifact': value, 'sandbox_root': str(target.root), 'items': ['RLI-001']}
            self.assert_code('RLS_EFFECT_AUTHORIZATION_REQUIRED', run_cli, ['execute', '--write-policy', 'auto'], payload)
            self.assertFalse(target.state_path.exists())
            self.assertFalse(target.evidence_dir.exists())

    def test_historical_e038_authorization(self):
        value = two_item_artifact()
        auth = authorize(value, ['RLI-001'])
        with sandbox() as target:
            execute(value, target, ['RLI-001'], auth, now='2026-09-04T04:05:00Z')
        self.assertEqual(value['release_items'][0]['result'], 'success')
        self.assertEqual(value['release_items'][1]['result'], 'pending')

    def test_historical_e039_authorization(self):
        self.assert_code('RLS_SECRET_REJECTED', artifact, release_target='sk-' + 'abcdefghijklmnop1234')

    def test_historical_e040_authorization(self):
        value = artifact()
        self.assert_code('RLS_CONTRACT_INVALID', issue_authorization, value, ['RLI-999'], 'test-authorizer')

    def test_historical_e041_releaseitem(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
        row = value['release_items'][0]
        self.assertEqual(row['result'], 'success')
        self.assertTrue(row['evidence_references'])
        self.assertEqual(value['evidence'][0]['locator'].split('/')[0], 'evidence')

    def test_historical_e042_releaseitem(self):
        value = two_item_artifact()
        with sandbox() as target:
            run_authorized(value, target, ['RLI-002'], {'RLI-002': 'partial'})
        row = value['release_items'][1]
        self.assertEqual((row['result'], row['follow_up']), ('partial', 'retry_rls'))
        self.assertTrue(row['evidence_references'])

    def test_historical_e043_releaseitem(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target, ['RLI-001'], {'RLI-001': 'failure'})
        row = value['release_items'][0]
        self.assertEqual((row['result'], row['follow_up']), ('fail', 'retry_rls'))
        self.assertFalse(value['target_effect'])

    def test_historical_e044_releaseitem(self):
        value = artifact()
        with sandbox() as target:
            result = cancel(value, target)
        self.assertEqual(result['release_conclusion'], 'cancelled')
        self.assertEqual(result['artifact']['revision_state'], 'frozen')
        self.assertFalse(result['target_effect'])

    def test_historical_e045_releaseitem(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
            self.assert_code('RLS_CANCEL_NOT_ALLOWED', cancel, value, target)

    def test_historical_e046_releaseitem(self):
        value = artifact()
        value['release_items'][0]['result'] = 'waived'
        self.assert_code('RLS_CONTRACT_INVALID', verify, value)

    def test_historical_e047_releaseitem(self):
        value = artifact()
        self.assert_code('RLS_CONCLUSION_INCONSISTENT', finalize, value)
        self.assertEqual(value['artifact']['revision_state'], 'open')

    def test_historical_e048_releaseitem(self):
        rows = [{'id': 'RLI-001', 'action': 'two independent actions', 'source_references': ['RES-1'], 'independent_result_count': 2, 'result': 'pending', 'follow_up': 'none', 'evidence_references': []}]
        self.assert_code('RLS_CONTRACT_INVALID', normalize_items, rows, 'rli')

    def test_historical_e049_releaseitem(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
        reference = value['release_items'][0]['evidence_references'][0]
        rewrite_evidence_event(value, reference, executor='different-executor')
        self.assert_code('RLS_EVIDENCE_TAMPERED', verify, value)

    def test_historical_e050_releaseitem(self):
        value = artifact()
        value['release_items'][0]['prerequisite_satisfied'] = False
        auth = authorize(value)
        with sandbox() as target:
            before = target.snapshot()
            self.assert_code('RLS_EXECUTION_FAILED', execute, value, target, ['RLI-001'], auth, now='2026-09-04T04:05:00Z')
            self.assertEqual(target.snapshot(), before)

    def test_historical_e051_confirmation(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
            self.assert_code('RLS_TARGET_STATE_UNVERIFIED', confirm, value, target, ['RCF-001'], pipeline_only=True)

    def test_historical_e052_confirmation(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
            confirm(value, target, ['RCF-001'])
        self.assertEqual(value['confirmations'][0]['result'], 'pass')
        self.assertIsInstance(value['confirmations'][0]['observed'], dict)

    def test_historical_e053_confirmation(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
            confirm(value, target, ['RCF-001'], force_fail=True)
        row = value['confirmations'][0]
        self.assertEqual((row['result'], row['follow_up']), ('fail', 'retry_rls'))

    def test_historical_e054_confirmation(self):
        value = artifact()
        value['confirmations'][0]['result'] = 'n/a'
        self.assert_code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE', verify, value)

    def test_historical_e055_confirmation(self):
        value = artifact()
        with sandbox() as target:
            result = complete_failure_before_effect(value, target)
        self.assertEqual(result['confirmations'][0]['result'], 'not_run')
        self.assertEqual(result['release_conclusion'], 'failed')
        self.assertFalse(result['target_effect'])

    def test_historical_e056_confirmation(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
        value['confirmations'][0].update(result='not_run', observed='not run', evidence_references=value['release_items'][0]['evidence_references'])
        self.assert_code('RLS_TARGET_STATE_UNVERIFIED', verify, value)

    def test_historical_e057_confirmation(self):
        value = artifact()
        value['confirmations'][0].update(result='n/a', objective_na_reason='claimed not applicable')
        self.assert_code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE', verify, value)

    def test_historical_e058_confirmation(self):
        value = artifact()
        value['confirmations'][0]['subjective'] = True
        with sandbox() as target:
            run_authorized(value, target)
            self.assert_code('RLS_TARGET_STATE_UNVERIFIED', confirm, value, target, ['RCF-001'])

    def test_historical_e059_confirmation(self):
        rows = [{'result': 'pass'}, {'result': 'fail'}]
        self.assertEqual(exception_resolution_state(rows), 'resolved')

    def test_historical_e060_confirmation(self):
        rows = [{'result': 'waived'}]
        self.assert_code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE', exception_resolution_state, rows)
        self.assertEqual(exception_resolution_state(rows, current_active_exception=True), 'superseded')

if __name__ == "__main__":
    unittest.main()
