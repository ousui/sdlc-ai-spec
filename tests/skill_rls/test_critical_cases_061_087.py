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

class RlsCriticalCases061087(unittest.TestCase):

    def assert_code(self, expected, callable_, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(getattr(caught.exception, 'code', None), expected, caught.exception)
        return caught.exception

    def test_historical_e061_conclusion(self):
        self.assertEqual(compute_conclusion(artifact()), 'pending')

    def test_historical_e062_conclusion(self):
        value = artifact()
        value['release_items'][0]['result'] = 'fail'
        value['confirmations'][0]['result'] = 'not_run'
        self.assertEqual(compute_conclusion(value), 'failed')

    def test_historical_e063_conclusion(self):
        value = artifact()
        with sandbox() as target:
            result = cancel(value, target)
        self.assertEqual(result['release_conclusion'], 'cancelled')

    def test_historical_e064_conclusion(self):
        value = artifact()
        with sandbox() as target:
            result = complete_success(value, target)
        self.assertEqual((result['release_conclusion'], result['artifact_gate']), ('success', 'pass'))

    def test_historical_e065_conclusion(self):
        value = two_item_artifact()
        with sandbox() as target:
            run_authorized(value, target, ['RLI-001', 'RLI-002'], {'RLI-001': 'success', 'RLI-002': 'partial'})
            confirm(value, target, ['RCF-001'])
        self.assertEqual(compute_conclusion(value), 'partial')

    def test_historical_e066_conclusion(self):
        value = artifact()
        value['release_items'][0]['result'] = 'fail'
        value['confirmations'][0]['result'] = 'not_run'
        self.assertEqual(compute_follow_up(value, 'failed'), 'retry_rls')

    def test_historical_e067_conclusion(self):
        value = artifact()
        with sandbox() as target:
            value = complete_failure_before_effect(value, target)
        projection = provisional_lifecycle_projection(value)
        self.assertEqual((projection['next_phase'], projection['next_action']), ('RLS', 'RETRY_RLS'))

    def test_historical_e068_conclusion(self):
        reference = issue_reference('RLS-20260904110000-01@1', 'return_dsn')
        self.assertEqual(reference, 'RLS-20260904110000-01@1#RLS-ISSUE-DSN-001')

    def test_historical_e069_conclusion(self):
        self.assertEqual(normalize_return_phase('return_imp', unique_imp_lineage=False), 'return_pln')
        self.assertEqual(normalize_return_phase('return_imp', unique_imp_lineage=True), 'return_imp')

    def test_historical_e070_conclusion(self):
        value = artifact()
        with sandbox() as target:
            result = complete_failure_before_effect(value, target)
        self.assertEqual(result['artifact_gate'], 'pass')
        self.assertEqual(result['release_conclusion'], 'failed')

    def test_historical_e071_conclusion(self):
        value = artifact()
        value['release_items'][0]['result'] = 'success'
        value['confirmations'][0]['result'] = 'pass'
        value['release_conclusion'] = 'success'
        self.assert_code('RLS_EVIDENCE_TAMPERED', verify, value, finalizing=True)
        self.assertEqual(value['artifact']['revision_state'], 'open')

    def test_historical_e072_revision(self):
        value = artifact()
        original = value['artifact']['reference']
        with sandbox() as target:
            run_authorized(value, target)
            self.assertEqual(value['artifact']['reference'], original)
            confirm(value, target, ['RCF-001'])
            self.assertEqual(value['artifact']['reference'], original)

    def test_historical_e073_revision(self):
        value = artifact()
        with sandbox() as target:
            frozen = cancel(value, target)
            retried = retry_revision(frozen, candidate(), {'version': '0.9.0'})
        self.assertEqual(retried['artifact']['revision'], 2)
        self.assertIsNone(retried['effect_authorization'])
        self.assertEqual(retried['release_contract']['target_baseline'], {'version': '0.9.0'})

    def test_historical_e074_revision(self):
        value = artifact()
        changed_scope = dataclass_replace(candidate(), scope_reference='PLN-OTHER@1')
        self.assert_code('RLS_SCOPE_MISMATCH', revise, value, changed_scope, target='sandbox-a', target_baseline='N/A — Initial Release')
        changed_results = dataclass_replace(candidate(), result_references=('IMP-OTHER@1/RES-001',), subject_references=('IMP-OTHER@1/RES-001',))
        self.assert_code('RLS_RESULT_MISMATCH', revise, value, changed_results, target='sandbox-a', target_baseline='N/A — Initial Release')

    def test_historical_e075_revision(self):
        value = artifact()
        changed = revise(value, candidate(), target='sandbox-b', target_baseline='N/A — Initial Release')
        self.assertNotEqual(changed['artifact']['id'], value['artifact']['id'])
        self.assertEqual(changed['release_contract']['release_target'], 'sandbox-b')

    def test_historical_e076_revision(self):
        value = artifact()
        auth = authorize(value)
        with sandbox() as target:
            before = target.snapshot()
            execute(value, target, ['RLI-001'], auth, behaviors={'RLI-001': 'no-op'}, now='2026-09-04T04:05:00Z')
            after = target.snapshot()
        self.assertEqual(before, after)
        self.assertFalse(value['target_effect'])
        self.assertEqual(value['evidence'][0]['event']['behavior'], 'no-op')

    def test_historical_e077_revision(self):
        result = abandon_first_write('RLS-20260904110000-01', 1, RuntimeError('write failed'))
        self.assertEqual(result['artifact']['revision_state'], 'abandoned')
        self.assertFalse(result['target_effect'])

    def test_historical_e078_revision(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
            confirm(value, target, ['RCF-001'])
        value['release_conclusion'] = 'success'
        value['follow_up'] = 'none'
        value['final_confirmation'] = {'digest': 'stale'}
        self.assert_code('RLS_FINAL_CONFIRMATION_STALE', verify, value, finalizing=True)
        self.assertEqual(value['artifact']['revision_state'], 'open')

    def test_historical_e079_revision(self):
        value = artifact()
        with sandbox() as target:
            run_authorized(value, target)
            value['evidence'][0]['event']['result'] = 'fail'
            self.assert_code('RLS_EVIDENCE_TAMPERED', check, value, target)

    def test_historical_e080_revision(self):
        value = artifact()
        with sandbox() as target:
            before_artifact = sha256_value(value)
            before_target = sha256_value(target.snapshot())
            result = check(value, target)
            self.assertTrue(result['pending'])
            self.assertEqual(sha256_value(value), before_artifact)
            self.assertEqual(sha256_value(target.snapshot()), before_target)

    def test_historical_e081_lifecycle(self):
        projection = provisional_lifecycle_projection(artifact())
        self.assertEqual((projection['next_phase'], projection['next_action']), ('RLS', 'CONTINUE_RLS'))

    def test_historical_e082_lifecycle(self):
        value = artifact()
        with sandbox() as target:
            value = complete_success(value, target)
        projection = provisional_lifecycle_projection(value)
        self.assertIsNone(projection['next_phase'])
        self.assertEqual(projection['next_action'], 'LIFECYCLE_COMPLETE')

    def test_historical_e083_lifecycle(self):
        value = artifact()
        with sandbox() as target:
            value = complete_failure_before_effect(value, target)
        projection = provisional_lifecycle_projection(value)
        self.assertEqual((projection['next_phase'], projection['next_action']), ('RLS', 'RETRY_RLS'))

    def test_historical_e084_lifecycle(self):
        value = artifact()
        value['artifact']['revision_state'] = 'frozen'
        value.update(release_conclusion='partial', follow_up='return_imp', artifact_gate='pass', target_effect=True)
        projection = provisional_lifecycle_projection(value)
        self.assertEqual((projection['next_phase'], projection['next_action']), ('IMP', 'RETURN_TO_IMP'))

    def test_historical_e085_lifecycle(self):
        for follow_up, phase in (('return_req', 'REQ'), ('return_dsn', 'DSN'), ('return_pln', 'PLN')):
            value = artifact()
            value['artifact']['revision_state'] = 'frozen'
            value.update(release_conclusion='failed', follow_up=follow_up, artifact_gate='pass')
            projection = provisional_lifecycle_projection(value)
            with self.subTest(follow_up=follow_up):
                self.assertEqual((projection['next_phase'], projection['next_action']), (phase, f'RETURN_TO_{phase}'))

    def test_historical_e086_lifecycle(self):
        value = artifact()
        with sandbox() as target:
            value = cancel(value, target)
        projection = provisional_lifecycle_projection(value)
        self.assertEqual(projection['next_action'], 'LIFECYCLE_COMPLETE')
        self.assertFalse(projection['target_effect'])

    def test_historical_e087_lifecycle(self):
        value = artifact()
        with sandbox() as target:
            value = complete_failure_before_effect(value, target)
        self.assertEqual(value['artifact_gate'], 'pass')
        self.assertNotEqual(value['release_conclusion'], 'success')

if __name__ == "__main__":
    unittest.main()
