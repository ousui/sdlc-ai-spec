"""Synthetic checks for the real-connection batch and native evidence validator.

These do not execute a native host or certify a real PAT.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from mcp import types
from packages.sdlc_github.models import canonical, GithubError
from packages.sdlc_github.operations import READS,WRITES,TOOLS
from packages.sdlc_github.service import GithubService
from tests.skill_github.client import LiveBatch, fixture_config, evidence_summary, run_live, run_identity
from tests.skill_github.native_evidence import validate_native,template,CHECKS,HOSTS
from tests.skill_github.fake_backend import Backend,FakeTransport
from tests.skill_github.oracle import REPO


class Session:
    def __init__(self,service):self.service=service
    async def call_tool(self,tool,arguments):
        value=await self.service.handle(tool,arguments)
        return types.CallToolResult(content=[types.TextContent(type='text',text=canonical(value).decode())],structuredContent=value)


class ClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.data=self.root/'data';self.data.mkdir()
        self.backend=Backend();self.session=Session(GithubService(self.data,transport=FakeTransport(self.backend)))
        self.fixture={'repository':REPO,'head':'fixture/topic','base':'main','file_path':'README.md','sha':'a'*40,
                      'tag':'v1.0.0','workflow_id':'99','run_id':100,'job_id':101}
    def tearDown(self):self.temp.cleanup()

    async def test_full_live_controller_against_synthetic_service_all32(self):
        report=await LiveBatch(self.session,self.fixture,self.root/'out',allow_writes=True).run()
        self.assertEqual(report['status'],'PASS',[(x['operation'],x.get('response',{}).get('errors')) for x in report['rows'] if x['status']!='PASS'])
        self.assertEqual(set(READS)|set(WRITES),{r['operation'] for r in report['rows'] if r['operation']!='status'})
        self.assertEqual(len(self.backend.writes),5)
        self.assertEqual(self.backend.issue['state'],'open')  # pre-existing Issue untouched
        self.assertEqual(self.backend.pr['state'],'open')     # pre-existing PR untouched
        own=[o for n,o in self.backend.objects.items() if n>2]
        self.assertTrue(all(x['state']=='closed' for x in own))

    async def test_resume_batch_reuses_request_ids_without_new_writes(self):
        await LiveBatch(self.session,self.fixture,self.root/'out',allow_writes=True).run()
        report=await LiveBatch(self.session,self.fixture,self.root/'out',allow_writes=True).run()
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(len(self.backend.writes),5)

    async def test_no_write_flag_means_zero_mutations(self):
        report=await LiveBatch(self.session,self.fixture,self.root/'out').run()
        self.assertEqual(report['status'],'BLOCKED');self.assertEqual(len(self.backend.writes),0)
        self.assertTrue(all(x['status']=='BLOCKED' for x in report['rows'] if x['operation'] in WRITES))

    async def test_unknown_effect_stops_all_subsequent_writes(self):
        self.backend.after_write_error=GithubError('DISCONNECTED')
        report=await LiveBatch(self.session,self.fixture,self.root/'out',allow_writes=True).run()
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(len(self.backend.writes),1)
        state=json.loads((self.root/'out/run-state.json').read_text())
        self.assertEqual(set(state['requests']),{'issue.create'})

    async def test_different_fixture_cannot_reuse_batch(self):
        await LiveBatch(self.session,self.fixture,self.root/'out').run()
        with self.assertRaises(ValueError):LiveBatch(self.session,{**self.fixture,'base':'other'},self.root/'out')

    async def test_missing_live_token_does_not_start_process(self):
        path=self.root/'fixture.json';path.write_text(json.dumps(self.fixture))
        with patch.dict(os.environ,{'SDLC_GITHUB_TOKEN':''}),patch('tests.skill_github.client.stdio_client',side_effect=AssertionError('must not start')):
            report=await run_live(path,self.root/'out',data_root=self.data)
        self.assertEqual(report['status'],'BLOCKED')

    async def test_identity_missing_second_token_never_starts_a_process(self):
        with patch.dict(os.environ,{"SDLC_GITHUB_TOKEN":"fixture-alpha","SDLC_GITHUB_TOKEN_B":""}),patch("tests.skill_github.client.stdio_client",side_effect=AssertionError("must not start")):
            report=await run_identity(self.root/"identity",data_root=self.data,repository=REPO)
        self.assertEqual(report["status"],"BLOCKED")

    async def test_missing_release_fixture_is_blocked_not_empty_list_pass(self):
        fixture={**self.fixture,'tag':None}
        self.backend.replacements['list_tags']=types.CallToolResult(content=[types.TextContent(type='text',text='[]')])
        report=await LiveBatch(self.session,fixture,self.root/'out').run()
        for name in ('repo.tag','release.get'):
            self.assertEqual(next(x for x in report['rows'] if x['operation']==name)['status'],'BLOCKED')

    async def test_private_body_not_archived(self):
        private='PRIVATE-README-CONTENT-NOT-FOR-EVIDENCE'
        response={'ok':True,'data':{'body':private,'logs_content':private,'text':private},'operation':'repo.files'}
        self.assertNotIn(private,json.dumps(evidence_summary(response)))

    async def test_fixture_secrets_rejected(self):
        path=self.root/'fixture.json';path.write_text(json.dumps({**self.fixture,'head':'github_pat_'+'A'*40}))
        with self.assertRaises(GithubError):fixture_config(path)


class NativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.sha='a'*40;self.lock='b'*64
    def tearDown(self):self.temp.cleanup()

    def test_missing_native_hosts_is_blocked(self):
        report=validate_native(self.root,self.sha,self.lock)
        self.assertEqual(report['status'],'BLOCKED');self.assertEqual(len(report['hosts']),3)

    def test_not_run_templates_cannot_pass(self):
        for host in HOSTS:(self.root/(host+'.json')).write_text(json.dumps(template(host,self.sha,self.lock)))
        self.assertNotEqual(validate_native(self.root,self.sha,self.lock)['status'],'PASS')

    def test_declared_pass_without_original_trace_fails(self):
        for host in HOSTS:
            value=template(host,self.sha,self.lock);value['host_version']='synthetic checker fixture'
            for check in value['checks'].values():check.update(status='PASS',trace='missing.json',trace_sha256='c'*64)
            (self.root/(host+'.json')).write_text(json.dumps(value))
        self.assertEqual(validate_native(self.root,self.sha,self.lock)['status'],'FAIL')

    def test_runtime_binding_mismatch_rejected(self):
        value=template('codex','c'*40,self.lock)
        (self.root/'codex.json').write_text(json.dumps(value))
        self.assertEqual(validate_native(self.root,self.sha,self.lock)['hosts'][0]['status'],'FAIL')


if __name__=='__main__':unittest.main()
