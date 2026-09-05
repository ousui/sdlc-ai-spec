"""Actual batch/Target/Evidence behavior; persistence callback is a test recorder."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'skills/sdlc-600-rls/scripts'))
from tests.skill_rls import test_web_repair_confirmation as fixtures
from rls_confirmation import confirm_items
from rls_confirmation_policy import CAPABILITY_ERROR, VERSION_CONTRACT
from rls_evidence import validate_evidence
from rls_common import canonical_json, sha256_bytes
from rls_items import default_items


class RlsWebRepairBatchTests(unittest.TestCase):
    setUp = fixtures.RlsWebRepairConfirmationTests.setUp
    code = fixtures.RlsWebRepairConfirmationTests.code
    target_files = fixtures.RlsWebRepairConfirmationTests.target_files
    human = fixtures.RlsWebRepairConfirmationTests.human
    record = fixtures.RlsWebRepairConfirmationTests.record

    def batch(self, ids=None, **kwargs):
        return confirm_items(self.artifact, self.target, ids or ['RCF-001'],
                             trusted_observations=self.host, **kwargs)

    def second(self):
        second = deepcopy(self.row); second['id'] = 'RCF-002'
        self.artifact['confirmations'].append(second)
        return second

    def test_later_unknown_contract_fails_before_any_evidence_or_callback(self):
        self.second()['expected'] = 'unsupported additional health check'
        before = deepcopy(self.artifact); files = self.target_files(); calls = []
        self.code(CAPABILITY_ERROR, self.batch, ['RCF-001','RCF-002'], persist=lambda a: calls.append(a))
        self.assertEqual(before, self.artifact); self.assertEqual(files, self.target_files()); self.assertEqual([], calls)

    def test_later_terminal_row_fails_before_first_evidence(self):
        self.second()['result'] = 'pass'
        before = self.target_files()
        self.code('RLS_TARGET_STATE_UNVERIFIED', self.batch, ['RCF-001','RCF-002'])
        self.assertEqual(before, self.target_files()); self.assertEqual([], self.artifact['evidence'])

    def test_pipeline_success_is_not_observation(self):
        self.code('RLS_TARGET_STATE_UNVERIFIED', self.batch, pipeline_only=True)
        self.assertEqual([], self.artifact['evidence'])
        self.assertFalse(self.target.evidence_dir.exists())

    def test_one_human_record_cannot_satisfy_multiple_rcfs(self):
        self.human(); self.second(); record = self.record()
        self.code('RLS_HUMAN_EVIDENCE_INVALID', self.batch, ['RCF-001','RCF-002'], human_evidence=record)
        self.assertEqual([], self.artifact['evidence'])

    def test_distinct_human_records_cover_exact_batch_and_keep_failure(self):
        self.human(); self.second(); first = self.record()
        second = self.host.record(self.artifact,'RCF-002',self.target,evaluator=self.row['executor'],
            observed_at=first['observed_at'],result='fail',observation='Synthetic explicit failure',
            source_bytes=b'Synthetic second observation failed\n',attested=True)
        self.batch(['RCF-001','RCF-002'],human_evidence={'RCF-001':first,'RCF-002':second})
        self.assertEqual(['pass','fail'],[x['result'] for x in self.artifact['confirmations']])
        self.host.verify_history(self.artifact)

    def test_first_observation_retained_if_second_evidence_io_fails(self):
        self.second(); original = self.target._evidence; persisted = []
        def write(event):
            if event['item'] == 'RCF-002': raise OSError('simulated evidence write failure')
            return original(event)
        with patch.object(self.target,'_evidence',side_effect=write):
            with self.assertRaises(OSError):
                self.batch(['RCF-001','RCF-002'],persist=lambda state: persisted.append(deepcopy(state)))
        self.assertEqual(1,len(persisted))
        self.assertEqual(['pass','pending'],[x['result'] for x in persisted[0]['confirmations']])
        self.assertEqual(1,len(persisted[0]['evidence']))

    def test_final_evidence_verifier_rejects_rehashed_false_pass(self):
        import json
        from rls_confirmation_policy import STATE_CONFIRMATION,STATE_EVIDENCE,STATE_EXPECTATION
        self.row.update(confirmation=STATE_CONFIRMATION,evidence_requirement=STATE_EVIDENCE,
            expected=json.dumps({'contract':STATE_EXPECTATION,'equals':{'health':'healthy'}}))
        self.batch(); self.artifact['release_items'] = []
        self.assertEqual('fail',self.row['result']); validate_evidence(self.artifact)
        event=self.artifact['evidence'][0]['event']; event['result']='pass'
        event['confirmation_evaluation']['result']='pass'; self.row['result']='pass'
        raw=(canonical_json(event)+'\n').encode(); digest=sha256_bytes(raw)
        self.artifact['evidence'][0].update(sha256=digest,reference='SANDBOX-EVD-'+digest)
        self.row['evidence_references']=['SANDBOX-EVD-'+digest]
        self.code('RLS_EVIDENCE_TAMPERED',validate_evidence,self.artifact)

    def test_default_without_obligations_has_precise_version_only_contract(self):
        candidate=SimpleNamespace(result_references=['IMP-result'],rls_work_item_references=[],
              release_target_obligations=[],vfy_reference='VFY-20260905000000-01@1',obligation_sources=[])
        _,rows=default_items(candidate)
        self.assertEqual(VERSION_CONTRACT,{key:rows[0][key] for key in VERSION_CONTRACT})
        candidate.release_target_obligations=[{'reference':candidate.vfy_reference,'confirmation':'unknown',
            'expected':'health must be good','evidence_requirement':'health log'}]
        _,rows=default_items(candidate)
        self.assertEqual('health must be good',rows[0]['expected'])
        self.code(CAPABILITY_ERROR,self.target.confirm,rows[0],'1.0.0')

if __name__=='__main__': unittest.main()
