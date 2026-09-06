"""Packaging, narrow network boundary, byte limits and hostile journal cases."""
import asyncio
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from uuid import uuid4
from mcp import types
from packages.sdlc_github.models import canonical, digest, MAX_RESULT, MAX_TEXT, GithubError
from packages.sdlc_github.service import bounded_data, GithubService
from packages.sdlc_github.transport import Upstream, classify
from tools.install_sdlc_github import install, render_config, runtime_files
from tools.test_late_phase_runtime_independence import scan_runtime
from .fake_backend import Backend, FakeTransport
from .oracle import request
import sys
ROOT=Path(__file__).resolve().parents[2]


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
    def tearDown(self):self.tmp.cleanup()

    def test_config_three_native_grammars_and_unique_registration(self):
        for host,folder in (('codex','.codex-plugin'),('cursor','.cursor-plugin'),('claude-code','.claude-plugin')):
            with self.subTest(host=host):
                receipt=install(host,self.root/(host+' code'),self.root/(host+' data'),Path(sys.executable))
                root=Path(receipt['plugin'])
                manifest=json.loads((root/folder/'plugin.json').read_text())
                config=json.loads((root/manifest['mcpServers']).read_text())
                self.assertEqual(set(config['mcpServers']),{'sdlc_github'})
                self.assertEqual(config,render_config(host,Path(sys.executable),root,Path(receipt['data_root'])))
                serialized=json.dumps(config)
                self.assertNotIn('/ABS/',serialized)
                if host=='codex':
                    self.assertEqual(tomllib.loads((root/'config/github/codex.standalone.toml').read_text())['mcp_servers'],config['mcpServers'])
                else:self.assertIn('${',serialized)

    def test_installer_never_reads_or_expands_token(self):
        with patch.dict(os.environ,{'SDLC_GITHUB_TOKEN':'github_pat_'+'K'*60}):
            receipt=install('codex',self.root/'code',self.root/'data',Path(sys.executable))
        for file in Path(receipt['plugin']).rglob('*'):
            if file.is_file():self.assertNotIn(b'K'*60,file.read_bytes())

    def test_data_and_cache_excluded_from_distribution(self):
        paths=list(runtime_files(ROOT))
        self.assertTrue(paths)
        self.assertFalse(any(p.name in {'AGENTS.md','CLAUDE.md','HANDOFF.md'} or '.local' in p.parts or '.cache' in p.parts or 'docs' in p.parts or 'tests' in p.parts for p in paths))

    def test_refuses_existing_code_and_overlapping_roots(self):
        (self.root/'code').mkdir()
        for code,data in ((self.root/'code',self.root/'data'),(self.root/'new',self.root/'new/data'),(self.root/'data/code',self.root/'data')):
            with self.assertRaises(ValueError):install('codex',code,data,Path(sys.executable))

    def test_refuses_symlink_destination(self):
        (self.root/'linked').symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):install('cursor',self.root/'linked/code',self.root/'data',Path(sys.executable))

    def test_narrow_transport_exception_does_not_allow_other_httpx(self):
        allowed=self.root/'packages/sdlc_github/transport.py';allowed.parent.mkdir(parents=True)
        allowed.write_text('import httpx\n')
        scan_runtime(self.root)
        forbidden=self.root/'packages/sdlc_github/other.py';forbidden.write_text('import httpx\n')
        with self.assertRaises(RuntimeError):scan_runtime(self.root)

    def test_phase_may_not_import_optin_github_service(self):
        path=self.root/'packages/sdlc_phasekit/unwanted.py';path.parent.mkdir(parents=True)
        path.write_text('from packages.sdlc_github import service\n')
        with self.assertRaises(RuntimeError):scan_runtime(self.root)

    def test_network_transport_cannot_import_arbitrary_socket(self):
        path=self.root/'packages/sdlc_github/transport.py';path.parent.mkdir(parents=True)
        path.write_text('import socket\n')
        with self.assertRaises(RuntimeError):scan_runtime(self.root)

    def test_limits_count_json_escapes(self):
        for operation,value,maximum in (
            ('pr.diff','diff --git a/a b/a\n'+'\x00"\\'*500000,MAX_TEXT),
            ('actions.logs',{'job_id':1,'logs_content':'\x00"\\'*500000},MAX_TEXT),
            ('issue.get',{'body':'\x00"\\'*500000},MAX_RESULT)):
            with self.subTest(operation=operation):
                bounded,partial=bounded_data(operation,value)
                self.assertTrue(partial);self.assertLess(len(canonical(bounded)),maximum-4096)

    def test_http_exception_classification_is_not_disconnection(self):
        import httpx
        for status,expected in ((401,"AUTH_FAILED"),(403,"PERMISSION_DENIED"),(404,"NOT_FOUND_OR_INACCESSIBLE"),(429,"RATE_LIMITED"),(500,"UPSTREAM_FAILED"),(503,"UPSTREAM_FAILED")):
            with self.subTest(status=status):
                request=httpx.Request("POST","https://example.invalid/mcp/")
                response=httpx.Response(status,request=request)
                with self.assertRaises(httpx.HTTPStatusError) as caught:response.raise_for_status()
                self.assertEqual(classify(caught.exception),expected)

    def test_http_status_cannot_be_confused_with_a_number_in_the_url(self):
        import httpx
        request=httpx.Request("POST","https://example.invalid/issues/401")
        response=httpx.Response(500,request=request)
        with self.assertRaises(httpx.HTTPStatusError) as caught:response.raise_for_status()
        self.assertEqual(classify(caught.exception),"UPSTREAM_FAILED")

    def test_invalid_upstream_schema_fails_closed(self):
        item=types.Tool(name='get_me',inputSchema={'type':'object','properties':{},'required':['x','x']})
        with self.assertRaises(GithubError) as caught:Upstream(None,{'get_me':item}).check('get_me',{})
        self.assertEqual(caught.exception.code,'CAPABILITY_UNAVAILABLE')

    def test_malformed_intent_cannot_be_replayed(self):
        async def case():
            backend=Backend();service=GithubService(self.root,transport=FakeTransport(backend))
            tool,payload=request('issue.create')
            await service.handle(tool,payload)
            intent=next(self.root.rglob('intent.json'))
            original=json.loads(intent.read_text())
            for key,wrong in (('actor',[]),('operation',[]),('expected_hashes',[]),('target','string')):
                value=deepcopy(original);value['payload'][key]=wrong;value['sha256']=digest(value['payload'])
                intent.write_text(json.dumps(value))
                response=await service.handle(tool,payload)
                self.assertEqual(response['effect'],'unknown')
                self.assertEqual(response['errors'][0]['code'],'RECORD_CORRUPT')
                self.assertEqual(len(backend.writes),1)
        asyncio.run(case())


if __name__=='__main__':unittest.main()
