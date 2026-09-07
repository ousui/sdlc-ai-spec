"""Real SDK stdio -> production Service/Transport -> loopback HTTP MCP."""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from jsonschema import Draft202012Validator
from packages.sdlc_github.models import canonical
from packages.sdlc_github.operations import TOOLS
from tools.install_sdlc_github import install
from .oracle import CASES, WRITES, REPO, request, expected_mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA=json.loads((ROOT/'skills/_shared/schemas/github-result.schema.json').read_text())


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.path=Path(self.temporary.name).resolve()
        self.data=self.path/'stable';self.data.mkdir()
        self.log=(self.path/'http.log').open('w')
        self.rows=[]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        self.process=subprocess.Popen([sys.executable,'-B',str(ROOT/'tests/skill_github/fake_http.py'),'--port',str(self.port),'--state-file',str(self.path/'state.json')],stdout=self.log,stderr=self.log,
                                      env={**{k:v for k,v in os.environ.items() if k!='SDLC_GITHUB_TOKEN'},'PYTHONDONTWRITEBYTECODE':'1'})
        for _ in range(200):
            if self.process.poll() is not None:
                self.fail('Fake HTTP process terminated during setup')
            try:
                with socket.create_connection(('127.0.0.1',self.port),.1):break
            except OSError:await asyncio.sleep(.05)
        else:self.fail('Fake HTTP did not become ready')

    async def asyncTearDown(self):
        self.process.terminate()
        try:self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.log.close()
        evidence=os.environ.get('SDLC_GITHUB_TEST_EVIDENCE')
        if evidence:
            target=Path(evidence);target.mkdir(parents=True,exist_ok=True)
            # Only synthetic fixture arguments/results are retained.
            payload={'case':self._testMethodName,'rows':self.rows,'upstream':self.state(),
                     'http_stderr':(self.path/'http.log').read_text()}
            (target/(self._testMethodName+'.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
        self.temporary.cleanup()

    def state(self):
        path=self.path/'state.json'
        return json.loads(path.read_text()) if path.exists() else {'calls':[],'writes':0}

    @asynccontextmanager
    async def client(self, *, plugin=ROOT, data=None, token='fixture-alpha', crash=None, production=False):
        arguments=[str(plugin/'scripts/sdlc_github_mcp.py'),'--data-root',str(data or self.data)] if production else [str(ROOT/'tests/skill_github/stdio_bridge.py'),'--plugin',str(plugin),'--data-root',str(data or self.data),'--endpoint',f'http://127.0.0.1:{self.port}/mcp']
        if crash:arguments+=['--crash-point',crash]
        params=StdioServerParameters(command=sys.executable,args=arguments,
                                    env={'SDLC_GITHUB_TOKEN':token,'PYTHONDONTWRITEBYTECODE':'1'})
        with (self.path/('stdio-'+str(uuid4())+'.log')).open('w') as stderr:
            async with stdio_client(params,errlog=stderr) as (read,write):
                async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=30)) as session:
                    await session.initialize()
                    yield session

    async def call(self, client, tool, payload):
        reply=await client.call_tool(tool,payload)
        result=reply.structuredContent
        Draft202012Validator(SCHEMA).validate(result)
        self.assertEqual(len(reply.content),1)
        self.assertEqual(json.loads(reply.content[0].text),result)
        self.assertEqual(reply.isError,result['status'] in {'failed','blocked','unknown'})
        self.rows.append({'tool':tool,'arguments':payload,'result':result})
        return result

    async def test_all_32_operations_and_annotations(self):
        async with self.client() as client:
            listing=await client.list_tools()
            self.assertEqual({x.name for x in listing.tools},set(TOOLS))
            for tool in listing.tools:
                self.assertEqual(tool.outputSchema,SCHEMA)
                self.assertEqual(tool.annotations.readOnlyHint,tool.name not in ['sdlc_github_'+x.replace('.','_') for x in WRITES])
            self.assertEqual(self.state()['calls'],[])
            status=await self.call(client,'sdlc_github_status',{})
            self.assertTrue(status['ok']);self.assertTrue(all(status['data']['capabilities'].values()))
            for operation in CASES:
                with self.subTest(operation=operation):
                    tool,payload=request(operation,request_id=str(uuid4()))
                    value=await self.call(client,tool,payload)
                    self.assertTrue(value['ok'],value)
                    self.assertEqual(value['effect'],'confirmed' if operation in WRITES else 'none')
                    mapping=expected_mapping(operation,payload.get('request_id','11111111-1111-4111-8111-111111111111'))
                    self.assertIn([mapping[0],mapping[1]],self.state()['calls'])
                    if operation in WRITES:self.assertTrue(value['receipt']['readback_verified'])
            self.assertEqual(self.state()['writes'],5)

    async def test_restart_cache_clear_and_token_identity(self):
        tool,payload=request('issue.create',request_id=str(uuid4()))
        async with self.client() as first:
            original=await self.call(first,tool,payload)
        cache=self.data/'.cache';cache.mkdir();(cache/'garbage').write_text('rebuildable');shutil.rmtree(cache)
        async with self.client() as restarted:
            again=await self.call(restarted,tool,payload)
            self.assertEqual(original,again)
            self.assertEqual(self.state()['writes'],1)
            local=await self.call(restarted,'sdlc_github_operation_status',{'repository':REPO,'expected_actor_id':101,'request_id':payload['request_id']})
            self.assertTrue(local['ok'])
        async with self.client(token='fixture-beta') as second:
            status=await self.call(second,'sdlc_github_status',{})
            self.assertEqual(status['actor']['id'],202)
            denied=await self.call(second,tool,payload)
            self.assertEqual(denied['errors'][0]['code'],'ACTOR_MISMATCH')
            self.assertEqual(self.state()['writes'],1)

    async def test_real_process_crash_no_replay_and_readonly_reconcile(self):
        tool,payload=request('issue.create',request_id=str(uuid4()))
        with self.assertRaises(BaseException):
            async with self.client(crash='after_success_before_readback') as dead:
                await dead.call_tool(tool,payload)
        self.assertEqual(self.state()['writes'],1)
        async with self.client() as restarted:
            unknown=await self.call(restarted,tool,payload)
            self.assertEqual(unknown['effect'],'unknown')
            recovered=await self.call(restarted,'sdlc_github_operation_status',{'repository':REPO,'expected_actor_id':101,'request_id':payload['request_id'],'reconcile':True})
            self.assertTrue(recovered['ok'],recovered)
            self.assertEqual(self.state()['writes'],1)

    async def test_installed_copy_three_sequential_host_configs(self):
        for host in ('codex','cursor','claude-code'):
            with self.subTest(host=host):
                data=self.path/(host+'-data')
                plugin=self.path/(host+'-plugin')
                receipt=install(host,plugin,data,Path(sys.executable))
                self.assertEqual(receipt['native_status'],'NOT_RUN')
                for forbidden in ('docs','tests','AGENTS.md','CLAUDE.md','tools','.local','.cache'):
                    self.assertFalse((plugin/forbidden).exists())
                before={p.relative_to(plugin).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in plugin.rglob('*') if p.is_file()}
                async with self.client(plugin=plugin,data=data) as c:
                    self.assertTrue((await self.call(c,'sdlc_github_status',{}))['ok'])
                    tool,payload=request('issue.create',request_id=str(uuid4()))
                    self.assertTrue((await self.call(c,tool,payload))['ok'])
                relocated=self.path/(host+'-relocated');plugin.rename(relocated)
                async with self.client(plugin=relocated,data=data) as c:
                    self.assertTrue((await self.call(c,tool,payload))['ok'])
                after={p.relative_to(relocated).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in relocated.rglob('*') if p.is_file()}
                self.assertEqual(before,after)
        self.assertEqual(self.state()['writes'],3)

    async def test_production_discovery_missing_auth_and_invalid_args_offline(self):
        async with self.client(production=True,token='') as c:
            self.assertEqual(len((await c.list_tools()).tools),8)
            r=await self.call(c,'sdlc_github_status',{})
            self.assertEqual(r['errors'][0]['code'],'AUTH_REQUIRED')
            r=await self.call(c,'sdlc_github_issue_create',{'repository':REPO,'extra':'forbidden'})
            self.assertEqual(r['effect'],'none')
        self.assertEqual(self.state()['calls'],[])
        self.assertEqual(list(self.data.iterdir()),[])

    async def test_wire_auth_error_does_not_echo_credential(self):
        async with self.client(token='fixture-invalid-secret') as c:
            r=await self.call(c,'sdlc_github_status',{})
            self.assertEqual(r['errors'][0]['code'],'AUTH_FAILED')
            self.assertNotIn('fixture-invalid-secret',canonical(r).decode())
        self.assertEqual(self.state()['writes'],0)


if __name__=='__main__':unittest.main()
