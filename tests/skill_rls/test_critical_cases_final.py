"""Final 87 primary cases: exact real VFY producer, shared Store and local effects."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
from unittest.mock import patch
from tests.skill_rls.final_support import *
from tests.skill_rls.support import rewrite_evidence_event
from rls_authorization import validate_authorization
from rls_builder import build_provisional
from rls_contract import assert_no_effect_disposition
from rls_conclusion import compute_conclusion, compute_follow_up, normalize_return_phase
from rls_confirmation import exception_resolution_state
from rls_scope import bind_scope
from rls_items import normalize_items
from rls_handler import revise
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_lifecycle.query_rls import project_rls_state
from packages.sdlc_runtime.control_inputs import ControlInputResolver


class RlsFinalCriticalCases(FinalRlsCase):

    def test_rls_e001_final(self):
        result, _ = run_cli(['auto','-p',str(self.root),'--target','sandbox-a','--release-reference','1.0.0'], {'sandbox_root':str(self.target.root)})
        self.assertTrue(result['ok'])
        self.assertEqual('contract_ready', result['artifact']['status'])
        self.assertEqual('open', result['artifact']['artifact']['revision_state'])
        self.assertFalse(result['artifact']['target_effect'])
        read, _ = read_revision(self.root, result['artifact']['artifact']['reference'])
        self.assertEqual(result['artifact'], read)

    def test_rls_e002_final(self):
        self.code('RLS_TARGET_REQUIRED', SandboxReleaseTarget, self.target.root, 'sandbox-a,sandbox-b')
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e003_final(self):
        result, _ = run_cli(['create','-p',str(self.root),'-i',self.chain['vfy'],'--target','sandbox-a','--release-reference','1.0.0'], {'sandbox_root':str(self.target.root)})
        self.assertEqual('open', result['artifact']['artifact']['revision_state'])
        self.assertFalse(result['artifact']['target_effect'])
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e004_final(self):
        self.create()
        self.code('RLS_EFFECT_AUTHORIZATION_REQUIRED', self.service.execute, self.reference, self.target, ['RLI-001'], None)
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e005_final(self):
        self.create(); self.execute()
        result, _ = run_cli(['confirm','-p',str(self.root),'-r',self.reference,'--item','RCF-001'], {'sandbox_root':str(self.target.root)})
        self.assertEqual('pass',result['artifact']['confirmations'][0]['result'])
        self.assertEqual(self.reference,result['artifact']['artifact']['reference'])

    def test_rls_e006_final(self):
        self.create()
        unchanged, _ = self.service.revise(self.reference,self.chain['vfy'],self.target)
        self.assertIn('RLS_NO_CHANGE',unchanged['warnings'])
        self.assertTrue(self.service.check(self.reference,self.target)['pending'])
        self.cancelled()
        self.assertEqual('cancelled',self.state['release_conclusion'])

    def test_rls_e007_final(self):
        before = snapshot(self.root)
        with patch('rls_service.RlsService',side_effect=AssertionError('meta scanned Store')):
            for command in ('help','version','commands','examples'):
                result, _ = run_cli([command])
                self.assertEqual('meta',result['state'])
                self.assertEqual([],result['effects'])
        self.assertEqual(before,snapshot(self.root))

    def test_rls_e008_final(self):
        self.create()
        self.code('RLS_REFERENCE_NOT_EXACT',self.service.confirm,self.reference,self.target,['RLI-001'])

    def test_rls_e009_final(self):
        self.create()
        self.execute(['RLI-001','RLI-001'])
        self.assertIn('duplicate RLI-001 ignored',self.state['warnings'])
        self.assertEqual(1,len(self.state['evidence']))

    def test_rls_e010_final(self):
        self.create()
        self.assertIsNotNone(self.state['artifact'])
        self.assertFalse(self.state['provisional'])
        self.assertTrue(self.candidate.authority_verified)

    def test_rls_e011_final(self):
        root, chain, candidate = self.variant(applicability='n/a')
        result, generation = RlsService(root).create(chain['vfy'],self.target,release_reference='1.0.0')
        self.assertIsNone(result['artifact']); self.assertIsNone(generation)
        self.assertEqual('completed',result['status'])
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e012_final(self):
        root, chain, candidate = self.variant(applicability='waived')
        result, _ = RlsService(root).create(chain['vfy'],self.target,release_reference='1.0.0')
        self.assertIsNone(result['artifact']); self.assertEqual('waived',result['rls_applicability'])
        self.assertTrue(candidate.exception_references)
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e013_final(self):
        wire = deepcopy(self.chain['candidate']); wire['rls_applicability']='pending'; wire['rls_ready']=False
        self.code('RLS_APPLICABILITY_PENDING',adapt_vfy_payload,wire,allow_provisional=False)
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e014_final(self):
        self.create(); self.execute()
        self.code('RLS_NOT_REQUIRED',assert_no_effect_disposition,self.state,'n/a')
        self.code('RLS_NOT_REQUIRED',assert_no_effect_disposition,self.state,'waived')

    def test_rls_e015_final(self):
        temp = tempfile.TemporaryDirectory(prefix='rls-open-vfy-'); self.addCleanup(temp.cleanup)
        chain = build_chain(Path(temp.name),finalize_vfy=False)
        with self.assertRaises(Exception):
            read_vfy_candidate(temp.name,chain['vfy'])
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e016_final(self):
        wire = deepcopy(self.chain['candidate']); wire['early_stop']=True
        self.code('RLS_VFY_NOT_READY',adapt_vfy_payload,wire,allow_provisional=False)
        self.code('RLS_VFY_NOT_READY',read_vfy_candidate,self.root,self.chain['vfy'],expected_candidate=wire)

    def test_rls_e017_final(self):
        for field in ('pending_fields','con_ver','con_val'):
            wire = deepcopy(self.chain['candidate']); wire[field]=['VFM-001'] if field=='pending_fields' else 'pending'
            self.code('RLS_VFY_NOT_READY',adapt_vfy_payload,wire,allow_provisional=False)

    def test_rls_e018_final(self):
        for update in ({'product_result':'fail','con_val':'fail'}, {'unresolved_returns':[self.chain['vfy']+'#RET-001']}):
            wire=deepcopy(self.chain['candidate']); wire.update(update)
            self.code('RLS_VFY_NOT_READY',adapt_vfy_payload,wire,allow_provisional=False)

    def test_rls_e019_final(self):
        root, chain, candidate = self.variant(product_failure=True)
        self.assertEqual('fail',candidate.product_result)
        self.assertEqual('pass_with_exception',candidate.artifact_gate)
        state, _ = RlsService(root).create(chain['vfy'],self.target,release_reference='1.0.0')
        self.assertEqual('fail',state['release_contract']['vfy_conclusions']['product_result'])
        self.assertTrue(state['release_contract']['vfy_exception_references'])

    def test_rls_e020_final(self):
        self.code('RLS_SCOPE_MISMATCH',bind_scope,self.candidate,requested_scope='PLN-20000101000000-01@1')

    def test_rls_e021_final(self):
        wire=deepcopy(self.chain['candidate']); wire['result_references']=['IMP-20000101000000-01@1/RESULT-RES-001']
        self.code('RLS_RESULT_MISMATCH',adapt_vfy_payload,wire,allow_provisional=False)

    def test_rls_e022_final(self):
        self.code('RLS_TARGET_REQUIRED',build_provisional,self.candidate,release_reference='1.0.0',release_target='a,b',target_baseline='N/A — Initial Release')

    def test_rls_e023_final(self):
        self.code('RLS_BASELINE_UNRESOLVED',build_provisional,self.candidate,release_reference='1.0.0',release_target='sandbox-a',target_baseline=None)

    def test_rls_e024_final(self):
        self.create()
        self.assertEqual('N/A — Initial Release',self.state['release_contract']['target_baseline'])
        self.assertEqual(self.target._default_state(),self.target.snapshot())

    def test_rls_e025_final(self):
        self.code('RLS_RELEASE_REFERENCE_REQUIRED',self.service.create,self.chain['vfy'],self.target,release_reference=None)
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e026_final(self):
        self.create()
        self.assertTrue(self.state['release_contract']['approval_or_trigger_reference'].startswith('None'))
        self.code('RLS_EFFECT_AUTHORIZATION_REQUIRED',self.service.execute,self.reference,self.target,['RLI-001'],None)

    def test_rls_e027_final(self):
        self.create()
        self.assertTrue(self.state['release_contract']['rls_work_item_references'])
        for row in self.state['release_items']+self.state['confirmations']:
            row['source_references']=[self.candidate.result_references[0]]
        self.code('RLS_WORK_ITEM_COVERAGE_INCOMPLETE',verify,self.state)

    def test_rls_e028_final(self):
        self.create(); self.state['confirmations'][0]['source_references']=[self.chain['vfy']]
        self.code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE',verify,self.state)

    def test_rls_e029_final(self):
        self.create()
        for field in ('confirmation','expected','evidence_requirement'):
            state=deepcopy(self.state); state['confirmations'][0][field]='narrowed'
            self.code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE',verify,state)

    def test_rls_e030_final(self):
        self.create(); grant=self.grant()
        self.state['release_contract']['release_reference']='unapproved-package'
        self.code('RLS_EFFECT_AUTHORIZATION_STALE',validate_authorization,self.state,grant,['RLI-001'])
        self.code('RLS_EFFECT_AUTHORIZATION_STALE',write_open_revision,self.root,self.state,expected_generation=self.generation)

    def test_rls_e031_final(self):
        self.create(two=True); self.cancelled()
        state, _=self.service.revise(self.reference,self.chain['vfy'],self.target,retry=True)
        self.assertEqual(['RLI-001','RLI-002'],[x['id'] for x in state['release_items']])
        self.assertEqual(['RCF-001'],[x['id'] for x in state['confirmations']])

    def test_rls_e032_final(self):
        self.create()
        self.assertIsNone(self.state['effect_authorization'])
        self.assertEqual([],self.state['effect_authorization_history'])
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e033_final(self):
        self.create(); before=snapshot(self.target.root)
        self.code('RLS_EFFECT_AUTHORIZATION_REQUIRED',self.service.execute,self.reference,self.target,['RLI-001'],None)
        self.assertEqual(before,snapshot(self.target.root))

    def test_rls_e034_final(self):
        self.create(); grant=self.grant(); grant['revision']+=1
        self.code('RLS_EFFECT_AUTHORIZATION_STALE',self.service.execute,self.reference,self.target,['RLI-001'],grant)
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e035_final(self):
        self.create(two=True); grant=self.grant(['RLI-001'])
        self.code('RLS_EFFECT_AUTHORIZATION_STALE',self.service.execute,self.reference,self.target,['RLI-002'],grant)
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e036_final(self):
        self.create(); grant=self.grant()
        for field,value in (('release_target','b'),('target_baseline',{'version':'0.9'}),('result_references',['other'])):
            changed=deepcopy(self.state); changed['release_contract'][field]=value
            self.code('RLS_EFFECT_AUTHORIZATION_STALE',validate_authorization,changed,grant,['RLI-001'])

    def test_rls_e037_final(self):
        self.create()
        self.code('RLS_EFFECT_AUTHORIZATION_REQUIRED',run_cli,['execute','-p',str(self.root),'-r',self.reference,'--item','RLI-001','--write-policy','auto'],{'sandbox_root':str(self.target.root)})
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e038_final(self):
        self.create(two=True); self.execute(['RLI-001'])
        self.assertEqual(['success','pending'],[x['result'] for x in self.state['release_items']])
        self.assertEqual(['RLI-001'],self.target.snapshot()['applied'])

    def test_rls_e039_final(self):
        before=snapshot(self.root)
        self.code('RLS_SECRET_REJECTED',run_cli,['create','-p',str(self.root),'-i',self.chain['vfy']],{'sandbox_root':str(self.target.root),'target':'sandbox-a','release_reference':'sk-abcdefghijklmnop1234'})
        self.assertEqual(before,snapshot(self.root))
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e040_final(self):
        self.create()
        self.code('RLS_CONTRACT_INVALID',TrustedEffectRecords(self.root).grant,self.state,['RLI-999'],authorizer_identity='host',approved=True)
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e041_final(self):
        self.create(); self.execute()
        row=self.state['release_items'][0]
        self.assertEqual('success',row['result']); self.assertTrue(row['evidence_references'])
        self.assertTrue(self.target.evidence_bytes(row['evidence_references'][0]))
        self.assertEqual('1.0.0',self.target.snapshot()['version'])

    def test_rls_e042_final(self):
        self.create(two=True); self.execute(['RLI-002'],{'RLI-002':'partial'})
        row=self.state['release_items'][1]
        self.assertEqual(('partial','retry_rls'),(row['result'],row['follow_up']))
        self.assertTrue(row['evidence_references']); self.assertTrue(self.state['target_effect'])

    def test_rls_e043_final(self):
        self.create(); self.execute(behaviors={'RLI-001':'failure'})
        row=self.state['release_items'][0]
        self.assertEqual(('fail','retry_rls'),(row['result'],row['follow_up']))
        self.assertTrue(row['evidence_references']); self.assertFalse(self.state['target_effect'])

    def test_rls_e044_final(self):
        self.cancelled()
        self.assertEqual('cancelled',self.state['release_conclusion'])
        self.assertEqual('frozen',self.state['artifact']['revision_state'])
        self.assertFalse(self.state['target_effect'])

    def test_rls_e045_final(self):
        self.create(); self.execute()
        self.code('RLS_CANCEL_NOT_ALLOWED',self.service.cancel,self.reference,self.target)
        self.assertTrue(self.service.read(self.reference)[0]['target_effect'])

    def test_rls_e046_final(self):
        self.create(); self.state['release_items'][0]['result']='waived'
        self.code('RLS_CONTRACT_INVALID',verify,self.state)

    def test_rls_e047_final(self):
        self.create()
        self.code('RLS_CONCLUSION_INCONSISTENT',self.service.confirmation_requirements,self.reference,self.target)
        self.assertEqual('open',self.service.read(self.reference)[0]['artifact']['revision_state'])

    def test_rls_e048_final(self):
        items, _=default_items(self.candidate); items[0]['independent_result_count']=2
        self.code('RLS_CONTRACT_INVALID',normalize_items,items,'rli')

    def test_rls_e049_final(self):
        self.create(); self.execute()
        reference=self.state['release_items'][0]['evidence_references'][0]
        rewrite_evidence_event(self.state,reference,executor='unapproved-executor')
        self.code('RLS_EVIDENCE_TAMPERED',verify,self.state)

    def test_rls_e050_final(self):
        items, _=default_items(self.candidate); items[0]['prerequisite_satisfied']=False
        self.create(release_items=items)
        self.code('RLS_EXECUTION_FAILED',self.service.execute,self.reference,self.target,['RLI-001'],self.grant())
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e051_final(self):
        self.create(); self.execute()
        self.code('RLS_TARGET_STATE_UNVERIFIED',self.service.confirm,self.reference,self.target,['RCF-001'],pipeline_only=True)
        self.assertEqual('pending',self.service.read(self.reference)[0]['confirmations'][0]['result'])

    def test_rls_e052_final(self):
        self.create(); self.execute(); self.confirm()
        row=self.state['confirmations'][0]
        self.assertEqual('pass',row['result']); self.assertEqual(self.target.snapshot(),row['observed'])
        self.assertTrue(self.target.evidence_bytes(row['evidence_references'][0]))

    def test_rls_e053_final(self):
        self.create(); self.execute(); self.confirm(force_fail=True)
        row=self.state['confirmations'][0]
        self.assertEqual(('fail','retry_rls'),(row['result'],row['follow_up']))
        self.assertTrue(row['evidence_references'])

    def test_rls_e054_final(self):
        self.create(); self.state['confirmations'][0]['result']='n/a'
        self.code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE',verify,self.state)

    def test_rls_e055_final(self):
        self.finish(failure=True)
        self.assertEqual('not_run',self.state['confirmations'][0]['result'])
        self.assertEqual(self.state['release_items'][0]['evidence_references'],self.state['confirmations'][0]['evidence_references'])
        self.assertFalse(self.state['target_effect']); self.assertEqual('failed',self.state['release_conclusion'])

    def test_rls_e056_final(self):
        self.create(); self.execute()
        self.state['confirmations'][0].update(result='not_run',observed='not run',evidence_references=self.state['release_items'][0]['evidence_references'])
        self.code('RLS_TARGET_STATE_UNVERIFIED',verify,self.state)

    def test_rls_e057_final(self):
        self.create(); self.state['confirmations'][0].update(result='n/a',objective_na_reason='unapproved narrowing')
        self.code('RLS_CONFIRMATION_CONTRACT_INCOMPLETE',verify,self.state)

    def test_rls_e058_final(self):
        _, rows=default_items(self.candidate); rows[0]['subjective']=True
        self.create(confirmations=rows); self.execute()
        self.code('RLS_TARGET_STATE_UNVERIFIED',self.service.confirm,self.reference,self.target,['RCF-001'])

    def test_rls_e059_final(self):
        from tests.skill_rls.test_current_exceptions import CurrentRlsExceptionTests
        CurrentRlsExceptionTests.carried(self)
        self.execute(); self.confirm(); self.freeze()
        row=self.state['exceptions'][0]
        self.assertEqual('resolved',row['state'])
        self.assertIn(self.reference+'#RCF-001',row['resolution_references'])
        self.assertTrue(set(self.state['confirmations'][0]['evidence_references']) <= set(row['resolution_references']))

    def test_rls_e060_final(self):
        from tests.skill_rls.test_current_exceptions import CurrentRlsExceptionTests
        from rls_exceptions import TrustedRlsExceptions
        CurrentRlsExceptionTests.carried(self,two=True)
        self.execute(); self.confirm()
        invalid=deepcopy(self.state)
        invalid['confirmations'][1].update(result='waived',exception_reference=self.candidate.exception_references[0])
        self.code('RLS_EXCEPTION_INVALID',verify,invalid)
        risk=TrustedRlsExceptions(self.root).grant(self.state,['RCF-002'],approved=True,authorizer='fixture-risk-owner',
            reason='Explicit current re-waiver',known_risk='Second observation unavailable',compensating_control='Local Sandbox only',
            revisit_condition='next Revision',downstream_obligation='Repeat target observation')
        self.state,self.generation=self.service.waive(self.reference,self.target,risk)
        self.freeze()
        self.assertEqual('superseded',self.state['exceptions'][0]['state'])
        self.assertEqual('pass_with_exception',self.state['artifact_gate'])
        self.assertEqual(self.state,self.service.read(self.reference)[0])

    def test_rls_e061_final(self):
        self.create()
        self.assertEqual('pending',compute_conclusion(self.state))
        self.assertTrue(self.service.check(self.reference,self.target)['pending'])

    def test_rls_e062_final(self):
        self.create(); self.execute(behaviors={'RLI-001':'failure'})
        self.state,self.generation=self.service.mark_not_run(self.reference,self.target)
        self.assertEqual('failed',compute_conclusion(self.state))

    def test_rls_e063_final(self):
        self.cancelled()
        self.assertEqual('cancelled',self.state['release_conclusion']); self.assertFalse(self.state['target_effect'])

    def test_rls_e064_final(self):
        self.finish()
        self.assertEqual(('success','pass'),(self.state['release_conclusion'],self.state['artifact_gate']))
        self.assertEqual('frozen',self.state['artifact']['revision_state'])

    def test_rls_e065_final(self):
        self.finish(partial=True)
        self.assertEqual('partial',self.state['release_conclusion']); self.assertTrue(self.state['target_effect'])

    def test_rls_e066_final(self):
        self.create(); self.execute(behaviors={'RLI-001':'failure'})
        self.state,self.generation=self.service.mark_not_run(self.reference,self.target)
        self.assertEqual('retry_rls',compute_follow_up(self.state,'failed'))

    def test_rls_e067_final(self):
        self.finish(failure=True)
        old=self.reference
        state,_=self.service.revise(old,self.chain['vfy'],self.target,retry=True)
        self.assertEqual(self.state['artifact']['id'],state['artifact']['id'])
        self.assertEqual(2,state['artifact']['revision']); self.assertIsNone(state['effect_authorization'])

    def test_rls_e068_final(self):
        self.finish(failure=True,follow_up='return_dsn')
        view=self.projection(); self.assertEqual([self.reference+'#RLI-001'],view['issue_references'])
        resolved=ControlInputResolver(self.root).resolve_rls_issue(ArtifactStore.open_read_only(self.root),view['issue_references'][0],'return_dsn')
        self.assertEqual(self.reference,resolved.artifact_reference)

    def test_rls_e069_final(self):
        self.create()
        self.assertEqual('return_pln',normalize_return_phase('return_imp',unique_imp_lineage=False))
        self.assertEqual('return_imp',normalize_return_phase('return_imp',unique_imp_lineage=True))

    def test_rls_e070_final(self):
        self.finish(failure=True)
        self.assertEqual('pass',self.state['artifact_gate']); self.assertEqual('failed',self.state['release_conclusion'])
        view=self.projection(); self.assertEqual('failed',view['release_conclusion'])

    def test_rls_e071_final(self):
        self.create(); self.state['release_items'][0]['result']='success'; self.state['confirmations'][0]['result']='pass'
        self.state['release_conclusion']='success'
        self.code('RLS_EVIDENCE_TAMPERED',verify,self.state,finalizing=True)
        self.assertEqual('open',self.service.read(self.reference)[0]['artifact']['revision_state'])

    def test_rls_e072_final(self):
        self.create(); reference=self.reference
        self.execute(); self.assertEqual(reference,self.state['artifact']['reference'])
        self.confirm(); self.assertEqual(reference,self.state['artifact']['reference'])

    def test_rls_e073_final(self):
        self.finish(failure=True)
        old_id=self.state['artifact']['id']; old_grant=self.state['effect_authorization']
        state,_=self.service.revise(self.reference,self.chain['vfy'],self.target,retry=True)
        self.assertEqual(old_id,state['artifact']['id']); self.assertEqual(2,state['artifact']['revision'])
        self.assertEqual(self.target.baseline(),state['release_contract']['target_baseline'])
        self.assertIsNone(state['effect_authorization'])
        self.code('RLS_EFFECT_AUTHORIZATION_STALE',validate_authorization,state,old_grant,['RLI-001'])

    def test_rls_e074_final(self):
        self.create()
        changed=replace(self.candidate,scope_reference='PLN-20000101000000-01@1')
        self.code('RLS_SCOPE_MISMATCH',revise,self.state,changed,target='sandbox-a',target_baseline=self.target.baseline())
        changed=replace(self.candidate,result_references=('IMP-20000101000000-01@1/RESULT-RES-001',))
        self.code('RLS_RESULT_MISMATCH',revise,self.state,changed,target='sandbox-a',target_baseline=self.target.baseline())

    def test_rls_e075_final(self):
        self.create()
        temp=tempfile.TemporaryDirectory(prefix='rls-new-target-'); self.addCleanup(temp.cleanup)
        other=SandboxReleaseTarget(temp.name,'sandbox-b')
        state,_=self.service.revise(self.reference,self.chain['vfy'],other)
        self.assertNotEqual(self.state['artifact']['id'],state['artifact']['id'])
        self.assertEqual('sandbox-b',state['release_contract']['release_target'])
        self.assertIsNone(state['effect_authorization'])

    def test_rls_e076_final(self):
        current=self.target._default_state(); current.update(version='1.0.0',applied=['RLI-001'])
        self.target._write_state(current); self.create()
        before=self.target.snapshot(); self.execute(behaviors={'RLI-001':'no-op'})
        self.assertEqual(before,self.target.snapshot()); self.assertFalse(self.state['target_effect'])
        self.assertEqual('no-op',self.state['evidence'][0]['event']['behavior'])

    def test_rls_e077_final(self):
        with patch.object(ArtifactStore,'write_open_revision',side_effect=OSError('simulated first write failure')):
            with self.assertRaises(OSError):
                self.create()
        catalog=ArtifactCatalog(ArtifactStore.open_read_only(self.root))
        artifacts=catalog.list_artifacts('RLS'); self.assertEqual(1,len(artifacts))
        controls=catalog.list_revisions(artifacts[0].artifact_id)
        self.assertEqual('abandoned',controls[0].state); self.assertFalse(controls[0].materialized)
        self.assertFalse(self.target.state_path.exists())

    def test_rls_e078_final(self):
        self.create(); self.execute(); self.confirm()
        fc=rls_final_confirmation(self.root,self.service,self.reference,self.target); fc['control_input_digest']='sha256:'+'0'*64
        self.code('RLS_FINAL_CONFIRMATION_STALE',self.service.finalize,self.reference,self.target,fc)
        self.assertEqual('open',self.service.read(self.reference)[0]['artifact']['revision_state'])

    def test_rls_e079_final(self):
        self.create(); self.execute()
        for field in ('result','executor','target'):
            changed=deepcopy(self.state); changed['evidence'][0]['event'][field]='tampered'
            self.code('RLS_EVIDENCE_TAMPERED',verify,changed)
        self.assertEqual(self.state,self.service.read(self.reference)[0])

    def test_rls_e080_final(self):
        self.finish(); before=snapshot(self.root); target_before=snapshot(self.target.root)
        result,_=run_cli(['check','-p',str(self.root),'-r',self.reference],{'sandbox_root':str(self.target.root)})
        self.assertTrue(result['check']['ok'])
        self.assertEqual(before,snapshot(self.root)); self.assertEqual(target_before,snapshot(self.target.root))

    def test_rls_e081_final(self):
        self.create(); view=self.projection()
        self.assertEqual(('RLS','AUTHORIZE_RLS_EFFECT'),(view['next_phase'],view['next_action']))

    def test_rls_e082_final(self):
        self.finish(); view=self.projection()
        self.assertIsNone(view['next_phase']); self.assertEqual('LIFECYCLE_COMPLETE',view['next_action'])

    def test_rls_e083_final(self):
        self.finish(failure=True); view=self.projection()
        self.assertEqual(('RLS','RETRY_RLS'),(view['next_phase'],view['next_action']))

    def test_rls_e084_final(self):
        self.finish(partial=True,follow_up='return_imp'); view=self.projection()
        self.assertEqual(('IMP','RETURN_TO_IMP'),(view['next_phase'],view['next_action']))
        for reference in view['issue_references']:
            ControlInputResolver(self.root).resolve_rls_issue(ArtifactStore.open_read_only(self.root),reference,'return_imp')

    def test_rls_e085_final(self):
        self.finish(failure=True,follow_up='return_req'); view=self.projection()
        self.assertEqual(('REQ','RETURN_TO_REQ'),(view['next_phase'],view['next_action']))
        for follow, phase in (('return_dsn','DSN'),('return_pln','PLN')):
            state=deepcopy(self.state); state['follow_up']=follow
            self.assertEqual(phase,project_rls_state(state)['next_phase'])

    def test_rls_e086_final(self):
        self.cancelled(); view=self.projection()
        self.assertEqual('LIFECYCLE_COMPLETE',view['next_action']); self.assertFalse(view['target_effect'])
        self.assertEqual('cancelled',view['release_conclusion'])

    def test_rls_e087_final(self):
        self.finish(failure=True); view=self.projection()
        self.assertEqual('pass',view['artifact_gate']); self.assertEqual('failed',view['release_conclusion'])
        self.assertNotEqual('LIFECYCLE_COMPLETE',view['next_action'])
