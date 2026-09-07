"""Resume multi-resource creation without treating absence as an exact reference."""
from unittest.mock import patch
from tests.skill_imp.support import ImpFixture
from imp_result import read_state

class AbsentResourceCheckpointTests(ImpFixture):
    def test_resume_keeps_proved_absence_until_that_resource_is_created(self):
        plan=self.plan();plan['work_items'][0]['execution_scope']=['resource:repo','resource:new']
        plan['delivery_scope'].append({'scope_token':'resource:new','source_references':[self.dsn_reference+'#CHG-001'],'outcome':'Create another declared resource'})
        result=self.execute_pln(plan=plan);self.assertTrue(result['ok'],result)
        binding=result['artifact']['reference']+'#WI-001'
        method=self.implementation();method['resources']=[{'id':'repo','root':'integration'},{'id':'new','root':'generated'}]
        method['steps'][0]['target']=['resource:repo','resource:new']
        method['operations'][0]['path']=method['checks'][0]['path']='app.txt'
        method['operations'].append({'resource':'new','path':'product.txt','step':'STEP-001','op':'write_text','content':'new product','expected_sha256':'absent'})
        from imp_executor import apply_operations
        calls=[]
        def apply(*args,**kwargs):
            calls.append(1)
            if len(calls)==2:raise OSError('injected write failure before creating second resource')
            return apply_operations(*args,**kwargs)
        with patch('imp_executor.apply_operations',side_effect=apply):failed=self.invoke(binding=binding,implementation=method)
        self.assertFalse(failed['ok']);self.assertIsNotNone(failed['artifact'])
        self.assertEqual(1,len(read_state(self.stored(failed))['completed_operations']))
        self.assertFalse((self.root/'generated').exists())
        resumed=self.invoke('revise',reference=failed['artifact']['reference'],binding=binding,implementation=method)
        self.assertEqual('action_required',resumed['status'],resumed)
        self.assertEqual('new product',(self.root/'generated/product.txt').read_text())
        self.finish(resumed)
