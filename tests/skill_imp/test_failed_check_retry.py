"""An explicit revise retries failed checks without replaying source operations."""
from unittest.mock import patch
from tests.skill_imp.support import ImpFixture
import imp_handler
import json
from imp_result import member

class FailedCheckRetryTests(ImpFixture):
    def test_retry_failed_environment_check_reuses_exact_completed_effects(self):
        actual=imp_handler.execute_checks
        def fail_once(*args,**kwargs):
            rows,members=actual(*args,**kwargs)
            rows[0]['result']='fail'
            evidence=json.loads(members[0].raw_bytes)
            evidence.update(exit_code=1,result='fail',stdout='',stderr='Injected test environment failure')
            members[0]=member(members[0].member_id,evidence)
            return rows,members
        with patch.object(imp_handler,'execute_checks',side_effect=fail_once):
            opened=self.invoke(implementation=self.implementation())
        self.assertFalse(opened['ok']);self.assertEqual('fail',opened['gate']['result'])
        path=self.root/'integration/app.txt';before=path.read_bytes();mtime=path.stat().st_mtime_ns
        with patch.object(imp_handler,'execute_checks',wraps=actual) as rerun:
            result=self.invoke('revise',reference=opened['artifact']['reference'])
        self.assertEqual(1,rerun.call_count);self.assertEqual('pending',result['gate']['result'])
        self.assertEqual(before,path.read_bytes());self.assertEqual(mtime,path.stat().st_mtime_ns)
        self.assertEqual(opened['artifact']['id'],result['artifact']['id'])
