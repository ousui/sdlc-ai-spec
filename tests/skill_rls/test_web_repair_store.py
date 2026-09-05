"""RLS-WEB-001/002 service regressions. Real accepted VFY and shared Store only.

Fixtures below alter newly built inputs before they freeze, not current authority,
oracles, the VFY runtime, or the persisted results being verified.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from tests.skill_rls.final_support import FinalRlsCase, RlsService, read_vfy_candidate, default_items, snapshot
from rls_common import utc_now, canonical_json, sha256_bytes
from rls_human_evidence import TrustedHumanObservations
from rls_confirmation_policy import STATE_CONFIRMATION, STATE_EVIDENCE, STATE_EXPECTATION, CAPABILITY_ERROR
from rls_verifier import verify


class RlsWebRepairStoreTests(FinalRlsCase):
    def prepare_human(self):
        _,rows=default_items(self.candidate)
        rows[0].update(subjective=True,scenario='SCN-RLS-WEB-002',max_observation_age_seconds=900)
        self.create(confirmations=rows)
        self.execute()
        return rows[0]

    def observation(self,result='pass'):
        row=self.state['confirmations'][0]
        return TrustedHumanObservations(self.root).record(self.state,row['id'],self.target,
            evaluator=row['executor'],observed_at=utc_now(),result=result,
            observation='Synthetic host-recorded acceptance test; no real product approval',
            source_bytes=b'Synthetic human scenario observation for regression only.\n',attested=True)

    def inherited(self,obligation):
        from tools import rls_fixture_chain as producer
        directory=tempfile.TemporaryDirectory(prefix='rls-web-carried-')
        self.addCleanup(directory.cleanup)
        original=producer._candidate_from_lifecycle
        def build(*args,**kwargs):
            candidate=original(*args,**kwargs)
            candidate['release_target_obligations'][0].update(obligation)
            return candidate
        # This seam prepares a new scenario before real VFY construction/freeze.
        with patch.object(producer,'_candidate_from_lifecycle',side_effect=build):
            self.root=Path(directory.name).resolve()
            self.chain=producer.build_chain(self.root)
        self.candidate=read_vfy_candidate(self.root,self.chain['vfy'],expected_candidate=self.chain['candidate'])
        self.service=RlsService(self.root)

    def test_inherited_unsupported_expected_leaves_real_rcf_pending(self):
        self.inherited({'confirmation':'Check target health','expected':'health == healthy',
                        'evidence_requirement':'Immutable health observation'})
        self.create(); self.execute()
        before=snapshot(self.root); target_before=snapshot(self.target.root)
        self.code(CAPABILITY_ERROR,self.service.confirm,self.reference,self.target,['RCF-001'])
        self.assertEqual(before,snapshot(self.root)); self.assertEqual(target_before,snapshot(self.target.root))
        read,generation=self.service.read(self.reference)
        self.assertEqual('pending',read['confirmations'][0]['result'])
        self.assertEqual(self.generation,generation)
        self.code('RLS_CONCLUSION_INCONSISTENT',self.service.confirmation_requirements,self.reference,self.target)

    def test_inherited_supported_health_failure_is_not_version_pass(self):
        state=self.target._default_state(); state['health']='unhealthy'; self.target._write_state(state)
        self.inherited({'confirmation':STATE_CONFIRMATION,'expected':json.dumps({'contract':STATE_EXPECTATION,
                        'equals':{'health':'healthy','version':'1.0.0'}}),'evidence_requirement':STATE_EVIDENCE})
        self.create(); self.execute(); self.confirm()
        row=self.state['confirmations'][0]
        self.assertEqual('fail',row['result']); self.assertEqual('unhealthy',row['observed']['health'])
        self.freeze()
        self.assertEqual('pass',self.state['artifact_gate'])
        self.assertNotEqual('success',self.state['release_conclusion'])
        self.assertEqual(self.state,self.service.read(self.reference)[0])

    def test_actual_human_fail_survives_service_store_and_freeze(self):
        self.prepare_human(); record=self.observation('fail')
        self.confirm(human_evidence=record)
        self.assertEqual('fail',self.state['confirmations'][0]['result'])
        self.freeze(); self.assertNotEqual('success',self.state['release_conclusion'])
        self.assertEqual('pass',self.state['artifact_gate'])
        self.assertEqual(self.state,self.service.read(self.reference)[0])

    def test_host_human_pass_has_exact_readback(self):
        self.prepare_human(); self.confirm(human_evidence=self.observation())
        self.freeze()
        self.assertEqual('success',self.state['release_conclusion'])
        self.assertTrue(self.service.check(self.reference,self.target)['ok'])

    def test_naked_human_json_cannot_create_pass_or_evidence(self):
        self.prepare_human(); before=snapshot(self.root); target_before=snapshot(self.target.root)
        self.code('RLS_HUMAN_EVIDENCE_INVALID',self.service.confirm,self.reference,self.target,['RCF-001'],
            human_evidence={'evaluator':'someone-else','observed_at':'not-a-timestamp','observation':'unusable','result':'fail'})
        self.assertEqual(before,snapshot(self.root)); self.assertEqual(target_before,snapshot(self.target.root))
        self.assertEqual('pending',self.service.read(self.reference)[0]['confirmations'][0]['result'])

    def test_wrong_rcf_binding_rejected_before_store_or_evidence_change(self):
        self.prepare_human(); record=self.observation(); record['binding']['rcf_id']='RCF-002'
        before=snapshot(self.root); target_before=snapshot(self.target.root)
        self.code('RLS_HUMAN_EVIDENCE_INVALID',self.service.confirm,self.reference,self.target,['RCF-001'],human_evidence=record)
        self.assertEqual(before,snapshot(self.root)); self.assertEqual(target_before,snapshot(self.target.root))

    def test_later_unsupported_rcf_is_rejected_before_first_write(self):
        _,rows=default_items(self.candidate)
        extra=deepcopy(rows[0]); extra.update(id='RCF-002',source_references=[self.candidate.vfy_reference],expected='unsupported health goal')
        self.create(confirmations=[*rows,extra]); self.execute()
        before=snapshot(self.root); target_before=snapshot(self.target.root)
        self.code(CAPABILITY_ERROR,self.service.confirm,self.reference,self.target,['RCF-001','RCF-002'])
        self.assertEqual(before,snapshot(self.root)); self.assertEqual(target_before,snapshot(self.target.root))
        self.assertEqual(['pending','pending'],[r['result'] for r in self.service.read(self.reference)[0]['confirmations']])

    def test_second_observation_io_failure_preserves_first_store_result(self):
        _,rows=default_items(self.candidate)
        extra=deepcopy(rows[0]); extra['id']='RCF-002'
        self.create(confirmations=[*rows,extra]); self.execute()
        original=self.target._evidence
        def evidence(event):
            if event['item']=='RCF-002': raise OSError('simulated second observation I/O failure')
            return original(event)
        with patch.object(self.target,'_evidence',side_effect=evidence):
            with self.assertRaises(OSError): self.service.confirm(self.reference,self.target,['RCF-001','RCF-002'])
        read,_=self.service.read(self.reference)
        self.assertEqual(['pass','pending'],[r['result'] for r in read['confirmations']])
        self.assertEqual(2,len(read['evidence']))  # one RLI + the first RCF

    def test_rehashed_human_pass_forgery_rejected_by_domain_semantics(self):
        self.prepare_human(); self.confirm(human_evidence=self.observation('fail'))
        changed=deepcopy(self.state); row=changed['confirmations'][0]; row['result']='pass'
        evidence=next(e for e in changed['evidence'] if e['event']['item']==row['id'])
        evidence['event']['result']='pass'; evidence['event']['confirmation_evaluation']['result']='pass'
        raw=(canonical_json(evidence['event'])+'\n').encode(); digest=sha256_bytes(raw)
        evidence.update(sha256=digest,reference='SANDBOX-EVD-'+digest); row['evidence_references']=[evidence['reference']]
        self.code('RLS_EVIDENCE_TAMPERED',verify,changed)
        self.assertEqual(self.state,self.service.read(self.reference)[0])

    def test_frozen_human_record_requires_original_source_bytes(self):
        self.prepare_human(); record=self.observation(); self.confirm(human_evidence=record); self.freeze()
        host=TrustedHumanObservations(self.root)
        source=host.sources.path/(record['source_digest'][7:]+'.txt')
        source.write_bytes(b'synthetic changed source\n')
        self.code('RLS_CONTRACT_INVALID',self.service.read,self.reference)
