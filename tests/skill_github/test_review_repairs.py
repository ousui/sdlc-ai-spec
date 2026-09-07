"""Regression oracles from f0c32a0 independent review, never a real write replay."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import patch
from mcp import types
from jsonschema import Draft202012Validator
from packages.sdlc_github.models import GithubError
from packages.sdlc_github.service import GithubService
from packages.sdlc_github.operations import map_upstream, validate_request
from tests.skill_github.fake_backend import Backend, FakeTransport
from tests.skill_github.oracle import request, REPO
FIXTURE=json.loads((Path(__file__).parent/'fixtures/hosted-contracts.json').read_text())


class ReviewRepairs(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.backend=Backend();self.service=GithubService(self.root,transport=FakeTransport(self.backend))
    def tearDown(self):self.temp.cleanup()
    def hosted(self):
        for op,tool in [('issue.list','list_issues'),('comment.create','add_issue_comment')]:
            self.backend.tools[tool]=types.Tool(name=tool,inputSchema=deepcopy(FIXTURE['schemas'][op]))
    async def invoke(self,op,**changes):
        tool,args=request(op,request_id=str(uuid4()));args.update(changes)
        return await self.service.handle(tool,args)
    async def reconcile(self,rid):
        return await self.service.handle('sdlc_github_operation_status',{'repository':REPO,'expected_actor_id':101,'request_id':rid,'reconcile':True})
    async def unknown(self,op='issue.create'):
        rid=str(uuid4());self.backend.after_write_error='DISCONNECTED'
        r=await self.service.handle(*request(op,request_id=rid));self.assertEqual(r['effect'],'unknown');self.backend.after_write_error=None
        return rid

    async def test_r1_all_states_and_capability_use_same_mapping(self):
        self.hosted()
        for state in (None,'open','closed','all'):
            args={'operation':'issue.list','repository':REPO}
            if state is not None:args['state']=state
            op,normalized=validate_request('sdlc_github_read',args);tool,wire=map_upstream(op,normalized)
            with self.subTest(state=state):
                self.assertTrue(Draft202012Validator(FIXTURE['schemas'][op]).is_valid(wire),wire)
                if state in (None,'all'):self.assertNotIn('state',wire)
                else:self.assertEqual(wire['state'],state.upper())
                self.assertTrue((await self.service.handle('sdlc_github_read',args))['ok'])
        status=await self.service.handle('sdlc_github_status',{})
        self.assertTrue(status['ok'],status)

    async def test_r2_nonempty_comment_and_empty_update_are_independent(self):
        self.hosted();result=await self.invoke('comment.create')
        self.assertTrue(result['ok'],result);self.assertEqual(len(self.backend.writes),1)
        self.assertTrue((await self.invoke('issue.update',body=''))['ok'])
        self.assertTrue((await self.invoke('pr.update',body=''))['ok'])
        count=len(self.backend.writes)
        for body in ('','   '):
            result=await self.invoke('comment.create',body=body)
            self.assertEqual(result['errors'][0]['code'],'ARGUMENT_INVALID')
        self.assertEqual(len(self.backend.writes),count)

    async def test_r3_nested_jobs_preserve_inner_pagination(self):
        self.backend.replacements['actions_list:list_workflow_jobs']=deepcopy(FIXTURE['jobs_example'])
        r=await self.invoke('actions.jobs');self.assertTrue(r['ok'],r)
        self.assertEqual(r['data']['total_count'],1);self.assertEqual(r['data']['jobs'][0]['run_id'],100)
        self.assertFalse(r['pagination']['has_more'])
        self.backend.replacements['actions_list:list_workflow_jobs']['jobs']['total_count']=5
        r=await self.invoke('actions.jobs',per_page=1)
        self.assertTrue(r['pagination']['has_more']);self.assertEqual(r['pagination']['next_page'],2)
        r=await self.invoke('actions.jobs',page=5,per_page=1)
        self.assertFalse(r['pagination']['has_more']);self.assertEqual(r['completeness'],'partial')

    async def test_r3_jobs_reject_malformed_envelope_and_wrong_run(self):
        for data in ({'jobs':{'jobs':'not-list'}},{'jobs':{'other':[{'id':101}]}},{'jobs':{'jobs':[{'id':101,'run_id':999}]}},{'jobs':{'jobs':[{'id':True}]}},{'jobs':{'jobs':[],'total_count':True}},{'jobs':{'jobs':[]},'total_count':1},{'jobs':{'jobs':[{'id':101}],'total_count':0}},{'jobs':{'jobs':{'jobs':[]}}}):
            with self.subTest(data=data):
                self.backend.replacements['actions_list:list_workflow_jobs']=data
                r=await self.invoke('actions.jobs');self.assertFalse(r['ok'])
        self.backend.replacements['actions_list:list_workflow_jobs']={'jobs':{'jobs':[{'id':101,'run_id':100}]}}
        r=await self.invoke('actions.jobs');self.assertTrue(r['ok']);self.assertEqual(r['pagination']['has_more'],'unknown')

    async def test_r4_both_tag_forms_and_exact_target(self):
        for key in ('lightweight_tag','annotated_tag'):
            value=deepcopy(FIXTURE[key]);self.backend.replacements['get_tag']=value
            r=await self.invoke('repo.tag');self.assertTrue(r['ok'],r)
            for bad in ({**value,'object':{'sha':'bad','type':'commit'}},{**value,('ref' if key=='lightweight_tag' else 'tag'):'wrong'},{**value,'object':{'sha':'a'*40,'type':'blob'}}):
                self.backend.replacements['get_tag']=bad
                self.assertFalse((await self.invoke('repo.tag'))['ok'])

    async def test_r5_marker_uniqueness_before_attribute_and_author_filters(self):
        for changed in ('title','user'):
            with self.subTest(changed=changed):
                rid=await self.unknown();n=self.backend.next_number-1;dup=deepcopy(self.backend.objects[n]);new=self.backend.next_number;self.backend.next_number+=1
                dup.update(number=new,id=10000+new,html_url=f'https://github.com/example/project/issues/{new}')
                dup[changed]='different' if changed=='title' else {'id':202,'login':'other'}
                self.backend.objects[new]=dup
                # Put the competing marker on the next cursor page.
                original=self.backend.page
                def pages(values,args,key='items',cursor=False):return original(values,{**args,'perPage':1},key,cursor)
                with patch.object(self.backend,'page',side_effect=pages):r=await self.reconcile(rid)
                self.assertEqual((r['status'],r['effect']),('unknown','unknown'),r)
        self.assertEqual(len(self.backend.writes),2)

    async def test_r5_incomplete_range_never_establishes_unique_marker(self):
        rid=await self.unknown();self.backend.page_metadata=False
        r=await self.reconcile(rid);self.assertEqual(r['effect'],'unknown')
        self.assertEqual(len(self.backend.writes),1)

    async def test_r6_confirmed_effect_retained_and_failure_observed(self):
        self.backend.failures['issue_read:get']=403;rid=str(uuid4())
        first=await self.service.handle(*request('issue.create',request_id=rid));self.assertEqual(first['effect'],'confirmed')
        receipt=next(self.root.rglob('receipt.json'));raw=receipt.read_bytes()
        r=await self.reconcile(rid)
        self.assertEqual((r['status'],r['effect']),('partial','confirmed'),r)
        self.assertEqual(r['receipt']['url'],first['receipt']['url']);self.assertEqual(receipt.read_bytes(),raw)
        self.assertEqual(len(list(self.root.rglob('observation-*.json'))),1)
        self.assertEqual(len(self.backend.writes),1)
        self.backend.failures.clear();r=await self.reconcile(rid);self.assertTrue(r['ok'])

    async def test_r6_failed_observation_storage_does_not_erase_confirmation(self):
        self.backend.failures['issue_read:get']=403;rid=str(uuid4())
        await self.service.handle(*request('issue.create',request_id=rid))
        with patch.object(self.service.records,'save_receipt',side_effect=GithubError('STORAGE_FAILED')):
            r=await self.reconcile(rid)
        self.assertEqual((r['status'],r['effect']),('partial','confirmed'),r)
        self.assertEqual(len(self.backend.writes),1)
