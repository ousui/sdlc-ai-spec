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

class RlsCriticalCases001030(unittest.TestCase):

    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(getattr(caught.exception, 'code', None), expected, caught.exception)
        return caught.exception

    def test_historical_e001_interface(self):
        from tests.skill_rls.legacy_runtime import run_cli
        payload = fixture_payload('pass')
        payload.update(release_reference='1.0.0', target_baseline='N/A — Initial Release')
        result, _ = run_cli(['auto', '--target', 'sandbox-a', '--release-reference', '1.0.0'], payload)
        self.assertTrue(result['ok'])
        self.assertEqual(result['artifact']['status'], 'contract_ready')
        self.assertFalse(result['artifact']['target_effect'])

    def test_historical_e002_interface(self):
        self.assert_code('RLS_TARGET_REQUIRED', artifact, release_target='sandbox-a,sandbox-b')

    def test_historical_e003_interface(self):
        value = artifact()
        self.assertEqual(value['artifact']['revision_state'], 'open')
        self.assertEqual(value['status'], 'contract_ready')
        self.assertFalse(value['target_effect'])

    def test_historical_e004_interface(self):
        value = artifact()
        with sandbox() as target:
            before = target.snapshot()
            self.assert_code('RLS_EFFECT_AUTHORIZATION_REQUIRED', execute, value, target, ['RLI-001'], None)
            self.assertEqual(target.snapshot(), before)

    def test_historical_e005_interface(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
            confirm(value, target, ['RCF-001'])
            self.assertEqual(value['confirmations'][0]['result'], 'pass')
            self.assertTrue(value['target_effect'])

    def test_historical_e006_interface(self):
        value = artifact()
        no_change = revise(value, candidate(), target='sandbox-a', target_baseline='N/A — Initial Release')
        self.assertIn('RLS_NO_CHANGE', no_change['warnings'])
        with sandbox() as target:
            checked = check(value, target)
            self.assertTrue(checked['pending'])
            cancelled = cancel(value, target)
            self.assertEqual(cancelled['release_conclusion'], 'cancelled')

    def test_historical_e007_interface(self):
        from tests.skill_rls.legacy_runtime import run_cli
        result, _ = run_cli(['help'])
        self.assertEqual(result['state'], 'meta')
        self.assertEqual(result['effects'], [])
        self.assertEqual(result['real_target_effects'], 0)

    def test_historical_e008_interface(self):
        value = artifact()
        with sandbox() as target:
            self.assert_code('RLS_REFERENCE_NOT_EXACT', confirm, value, target, ['RLI-001'])

    def test_historical_e009_interface(self):
        value = artifact()
        auth = authorize(value, ['RLI-001', 'RLI-001'])
        with sandbox() as target:
            execute(value, target, ['RLI-001', 'RLI-001'], auth, now='2026-09-04T04:05:00Z')
        self.assertIn('duplicate RLI-001 ignored', value['warnings'])

    def test_historical_e010_applicability(self):
        result = create(candidate(), release_reference='1.0.0', release_target='sandbox-a', target_baseline='N/A — Initial Release')
        self.assertIsNotNone(result['artifact'])

    def test_historical_e011_applicability(self):
        result = create(candidate('n/a'))
        self.assertEqual(result['status'], 'completed')
        self.assertIsNone(result['artifact'])
        self.assertFalse(result['target_effect'])

    def test_historical_e012_applicability(self):
        result = create(candidate('waived'))
        self.assertEqual(result['rls_applicability'], 'waived')
        self.assertIsNone(result['artifact'])
        self.assertFalse(result['target_effect'])

    def test_historical_e013_applicability(self):
        self.assert_code('RLS_APPLICABILITY_PENDING', create, candidate('applicability_pending'))

    def test_historical_e014_applicability(self):
        value = artifact()
        value['target_effect'] = True
        value['target_snapshot_before'] = {'version': None}
        value['target_snapshot_after'] = {'version': '1.0.0'}
        self.assert_code('RLS_NOT_REQUIRED', assert_no_effect_disposition, value, 'n/a')

    def test_historical_e015_applicability(self):
        self.assert_code('RLS_VFY_NOT_READY', adapt_vfy_payload, fixture_payload('not_frozen'))

    def test_historical_e016_applicability(self):
        self.assert_code('RLS_VFY_NOT_READY', adapt_vfy_payload, fixture_payload('early_stop'))

    def test_historical_e017_applicability(self):
        self.assert_code('RLS_VFY_NOT_READY', adapt_vfy_payload, fixture_payload('pending'))

    def test_historical_e018_applicability(self):
        self.assert_code('RLS_VFY_NOT_READY', adapt_vfy_payload, fixture_payload('fail_without_exception'))

    def test_historical_e019_applicability(self):
        value = candidate('fail_with_exception')
        self.assertEqual(value.product_result, 'fail')
        self.assertEqual(value.artifact_gate, 'pass_with_exception')

    def test_historical_e020_applicability(self):
        self.assert_code('RLS_SCOPE_MISMATCH', bind_scope, candidate(), requested_scope='PLN-OTHER@1')

    def test_historical_e021_applicability(self):
        payload = fixture_payload('pass')
        payload['result_references'] = ['IMP-OTHER@1/RES-001']
        self.assert_code('RLS_RESULT_MISMATCH', adapt_vfy_payload, payload)

    def test_historical_e022_applicability(self):
        self.assert_code('RLS_TARGET_REQUIRED', build_provisional, candidate(), release_reference='1.0.0', release_target='a,b', target_baseline='N/A — Initial Release')

    def test_historical_e023_applicability(self):
        self.assert_code('RLS_BASELINE_UNRESOLVED', build_provisional, candidate(), release_reference='1.0.0', release_target='sandbox-a', target_baseline=None)

    def test_historical_e024_applicability(self):
        value = artifact(target_baseline='N/A — Initial Release')
        self.assertEqual(value['release_contract']['target_baseline'], 'N/A — Initial Release')

    def test_historical_e025_contract(self):
        self.assert_code('RLS_RELEASE_REFERENCE_REQUIRED', build_provisional, candidate(), release_reference='', release_target='sandbox-a', target_baseline='N/A — Initial Release')

    def test_historical_e026_contract(self):
        value = artifact()
        self.assertEqual(value['release_contract']['approval_or_trigger_reference'], 'None — no separate approval defined')
        with sandbox() as target:
            self.assert_code('RLS_EFFECT_AUTHORIZATION_REQUIRED', execute, value, target, ['RLI-001'], None)

    def test_historical_e027_contract(self):
        value = artifact(rls_work_item_references=['PLN-20260904070000-01@1#WI-001'])
        self.assert_code('RLS_WORK_ITEM_COVERAGE_INCOMPLETE', verify, value)

    def test_historical_e028_contract(self):
        unrelated = [{'id': 'RCF-001', 'source_references': ['VFY-OTHER@1'], 'confirmation': 'target version', 'expected': '1.0.0', 'evidence_requirement': 'snapshot', 'result': 'pending', 'follow_up': 'none', 'evidence_references': []}]
        value = artifact(confirmations=unrelated)
        self.assert_code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE', verify, value)

    def test_historical_e029_contract(self):
        value = artifact()
        value['confirmations'][0]['expected'] = 'weaker expectation'
        self.assert_code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE', verify, value)

    def test_historical_e030_contract(self):
        value = artifact()
        auth = authorize(value)
        value['release_contract']['release_reference'] = '1.0.1'
        self.assert_code('RLS_EFFECT_AUTHORIZATION_STALE', validate_authorization, value, auth, ['RLI-001'], now='2026-09-04T04:05:00Z')

if __name__ == "__main__":
    unittest.main()
