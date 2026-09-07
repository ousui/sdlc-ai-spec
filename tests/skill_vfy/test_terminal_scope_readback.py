"""A terminal resource result is not the set of all intermediate results."""
from types import SimpleNamespace as S
from unittest import TestCase
from unittest.mock import patch
from tests.skill_vfy.support import VfyHandler
from vfy_authority import _authoritative_scope

class TerminalScopeTests(TestCase):
    def projections(self):
        old='IMP-20260907000001-01@1';new='IMP-20260907000002-01@1';plan='PLN-20260907000000-01@1'
        claims=[]
        for i,ref in enumerate((old,new),1):
            claims.append(S(artifact_reference=ref,completed=True,vfy_ready=True,claim_state='completed',revision_state='frozen',binding_reference=plan+f'#WI-{i:03d}',binding_lineage=plan+f'#WI-{i:03d}',attempt=1,dependency_results=() if i==1 else (old,),execution_scope=('resource:app',),results=({'result_reference':ref+'/RESULT-RES-001','resource':'app','baseline_reference':'vcs:app@'+'a'*40,'result_digest':'sha256:'+str(i)*64,'changed_scope':['path:app/main.py']},)))
        p=S(nodes=[S(reference=plan,artifact_type='PLN')],current_claims=claims,vfy_results=(claims[1].results[0],))
        return plan,old,new,p
    def test_terminal_readback_accepts_one_current_result_not_both(self):
        plan,old,new,p=self.projections()
        service=S(list_requirements=lambda:[S(lineage_head=True,revision_state='frozen',reference='REQ-20260907000000-01@1')],inspect_requirement=lambda ref:p)
        with patch('vfy_handler.LifecycleQueryService',return_value=service):
            result=VfyHandler('.')._current_subject_snapshot({'scope':{'reference':plan},'subjects':[{'reference':new+'/RESULT-RES-001'}]})
        self.assertEqual([r['reference'] for r in result['subjects']],[new+'/RESULT-RES-001'])
    def test_old_or_partial_result_set_is_not_current(self):
        from vfy_common import VfyError
        plan,old,new,p=self.projections()
        service=S(list_requirements=lambda:[S(lineage_head=True,revision_state='frozen',reference='REQ-20260907000000-01@1')],inspect_requirement=lambda ref:p)
        with patch('vfy_handler.LifecycleQueryService',return_value=service):
            for refs in ([old+'/RESULT-RES-001'],[old+'/RESULT-RES-001',new+'/RESULT-RES-001']):
                with self.subTest(refs=refs),self.assertRaises(VfyError):
                    VfyHandler('.')._current_subject_snapshot({'scope':{'reference':plan},'subjects':[{'reference':r} for r in refs]})
    def test_scope_keeps_complete_predecessor_work_items(self):
        plan,old,new,p=self.projections()
        with patch('vfy_authority._phase_disposition',return_value={'Disposition':'required'}):
            scope=_authoritative_scope(plan,p,[{'reference':new+'/RESULT-RES-001','imp_revision_reference':new}],{},None)
        self.assertEqual([w['reference'] for w in scope['imp_work_items']],[plan+'#WI-001',plan+'#WI-002'])
        self.assertEqual(scope['delivery_scope'],['resource:app'])
    def test_missing_predecessor_is_not_silently_dropped(self):
        from vfy_common import VfyError
        plan,old,new,p=self.projections();p.current_claims=p.current_claims[1:]
        with patch('vfy_authority._phase_disposition',return_value={'Disposition':'required'}),self.assertRaises(VfyError):
            _authoritative_scope(plan,p,[{'reference':new+'/RESULT-RES-001','imp_revision_reference':new}],{},None)
