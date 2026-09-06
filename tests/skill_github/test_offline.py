"""Fixed deterministic oracle: all 32 mappings and adverse execution paths."""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from mcp import types
from jsonschema import Draft202012Validator
from packages.sdlc_github.service import GithubService, pagination
from packages.sdlc_github.models import GithubError, digest, canonical, MAX_RESULT, MAX_TEXT, redact
from packages.sdlc_github.operations import TOOLS, READS, WRITES, tool_schema, validate_request
from packages.sdlc_github.targets import parse_url, merge_target, repository_from_remotes
from packages.sdlc_github.transport import OfficialTransport, classify
from .fake_backend import Backend, FakeTransport, envelope, definitions
from .oracle import CASES, WRITES as ORACLE_WRITES, request, expected_mapping, REPO

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'skills/_shared/schemas/github-result.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
SPEC = importlib.util.spec_from_file_location('github_skill_compiler', ROOT/'skills/sdlc-github/scripts/runtime.py')
COMPILER = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(COMPILER)


class SimulatedCrash(BaseException):
    pass


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve(strict=True)
        self.backend = Backend()
        self.transport = FakeTransport(self.backend)
        self.service = GithubService(self.root, transport=self.transport)

    def tearDown(self):
        self.temp.cleanup()

    async def invoke(self, operation, **updates):
        tool, payload = request(operation)
        payload.update(updates)
        value = await self.service.handle(tool, payload)
        VALIDATOR.validate(value)
        return value

    async def test_status_catalog_and_no_startup_effect(self):
        self.assertEqual(self.transport.connections, 0)
        self.assertEqual(list(self.root.iterdir()), [])
        r = await self.service.handle('sdlc_github_status', {})
        self.assertTrue(r['ok']); self.assertEqual(len(r['data']['capabilities']), 32)
        self.assertEqual(set(TOOLS), {'sdlc_github_status', 'sdlc_github_read', 'sdlc_github_operation_status', *('sdlc_github_' + x.replace('.', '_') for x in ORACLE_WRITES)})
        self.assertEqual(len(READS), 27); self.assertEqual(len(WRITES), 5)
        self.assertEqual(list(self.root.iterdir()), [])

    async def test_missing_token_is_offline(self):
        with patch.dict(os.environ, {'SDLC_GITHUB_TOKEN': ''}):
            service = GithubService(self.root)
        with patch('socket.socket.connect', side_effect=AssertionError('unexpected network')):
            r = await service.handle('sdlc_github_status', {})
        self.assertEqual(r['errors'][0]['code'], 'AUTH_REQUIRED')

    async def test_token_snapshot_does_not_switch(self):
        with patch.dict(os.environ, {'SDLC_GITHUB_TOKEN': 'fixture-alpha'}):
            t = OfficialTransport()
        with patch.dict(os.environ, {'SDLC_GITHUB_TOKEN': 'fixture-beta'}):
            self.assertEqual(t._token, 'fixture-alpha')

    async def test_wrong_actor_is_zero_write(self):
        r = await self.invoke('issue.create', expected_actor_id=202)
        self.assertEqual(r['errors'][0]['code'], 'ACTOR_MISMATCH'); self.assertEqual(len(self.backend.writes), 0)
        self.assertEqual(list(self.root.iterdir()), [])

    async def test_policy_deny_is_zero_network(self):
        r = await self.invoke('issue.create', write_policy='deny')
        self.assertEqual(r['errors'][0]['code'], 'WRITE_DENIED')
        self.assertEqual(self.transport.connections, 0); self.assertEqual(list(self.root.iterdir()), [])

    async def test_dry_run_all_writes_no_intent(self):
        for name in ORACLE_WRITES:
            with self.subTest(name=name):
                r = await self.invoke(name, dry_run=True)
                self.assertTrue(r['ok']); self.assertEqual(r['effect'], 'none')
                self.assertEqual(len(self.backend.writes), 0); self.assertEqual(list(self.root.iterdir()), [])

    async def test_duplicate_returns_persisted_receipt(self):
        first = await self.invoke('issue.create')
        self.service = GithubService(self.root, transport=self.transport)
        second = await self.invoke('issue.create')
        self.assertEqual(first, second); self.assertEqual(len(self.backend.writes), 1)

    async def test_conflicting_id_never_replays(self):
        await self.invoke('issue.create')
        r = await self.invoke('issue.create', body='different')
        self.assertEqual(r['errors'][0]['code'], 'REQUEST_CONFLICT'); self.assertEqual(len(self.backend.writes), 1)

    async def test_actor_namespaces_are_isolated(self):
        await self.invoke('issue.create')
        self.backend.actor = 202
        r = await self.invoke('issue.create', expected_actor_id=202)
        self.assertTrue(r['ok']); self.assertEqual(len(self.backend.writes), 2)
        self.assertEqual(len(list((self.root/'.local/github').iterdir())), 2)

    async def test_local_receipt_requires_verified_instance_identity(self):
        r = await self.invoke('issue.create')
        payload = {'repository': REPO, 'expected_actor_id':101, 'request_id':r['receipt']['request_id']}
        self.service = GithubService(self.root, transport=self.transport)
        absent = await self.service.handle('sdlc_github_operation_status', payload)
        self.assertEqual(absent['errors'][0]['code'], 'IDENTITY_REQUIRED')
        await self.service.handle('sdlc_github_status', {})
        before = len(self.backend.calls)
        read = await self.service.handle('sdlc_github_operation_status', payload)
        self.assertTrue(read['ok']); self.assertEqual(len(self.backend.calls), before)
        self.assertEqual(read['operation'], 'operation_status')

    async def test_issue_update_rejects_pr_number(self):
        r = await self.invoke('issue.update', number=2)
        self.assertEqual(r['errors'][0]['code'], 'TARGET_MISMATCH'); self.assertFalse(self.backend.writes)

    async def test_pr_update_rejects_issue_number(self):
        r = await self.invoke('pr.update', number=1)
        self.assertEqual(r['errors'][0]['code'], 'TARGET_MISMATCH'); self.assertFalse(self.backend.writes)

    async def test_comment_pr_target(self):
        r = await self.invoke('comment.create', subject_type='pr', number=2)
        self.assertTrue(r['ok']); self.assertIn('/pull/2#issuecomment-', r['receipt']['url'])

    async def test_comment_past_first_page_without_metadata(self):
        self.backend.page_metadata = False
        self.backend.comments[1] = [{'id':n, 'body':'earlier', 'html_url':f'https://github.com/example/project/issues/1#issuecomment-{n}'} for n in range(1, 151)]
        r = await self.invoke('comment.create')
        self.assertTrue(r['ok']); self.assertTrue(any(a.get('page') == 2 for t,a in self.backend.calls if t == 'issue_read'))

    async def test_omitted_body_kept_explicit_empty_clears(self):
        self.backend.issue['body'] = 'keep this'
        tool, p = request('issue.update'); p.pop('body'); p.pop('state')
        r = await self.service.handle(tool, p)
        self.assertTrue(r['ok']); self.assertEqual(self.backend.issue['body'], 'keep this')
        r = await self.invoke('issue.update', request_id=str(uuid4()), body='')
        self.assertTrue(r['ok']); self.assertEqual(self.backend.issue['body'], '')

    async def test_branches_must_exist_and_differ(self):
        r = await self.invoke('pr.create', head='not-present')
        self.assertFalse(r['ok']); self.assertFalse(self.backend.writes)
        r = await self.invoke('pr.create', head='main')
        self.assertEqual(r['errors'][0]['code'], 'ARGUMENT_INVALID')

    async def test_pr_cannot_set_draft_false_or_reviewers(self):
        for extra in ({'draft':False}, {'maintainer_can_modify':True}, {'reviewers':['someone']}, {'endpoint':'https://example.invalid'}):
            r = await self.invoke('pr.create', **extra)
            self.assertEqual(r['errors'][0]['code'], 'ARGUMENT_INVALID')
        self.assertFalse(self.backend.writes)

    async def test_write_response_only_message_is_unknown(self):
        self.backend.replacements['issue_write:create'] = {'message':'created'}
        r = await self.invoke('issue.create')
        self.assertEqual(r['effect'], 'unknown'); self.assertFalse(r['ok'])
        await self.invoke('issue.create'); self.assertEqual(len(self.backend.writes), 1)

    async def test_write_response_wrong_url_is_unknown(self):
        self.backend.replacements['issue_write:create'] = {'id':'3', 'url':'https://github.com/other/repo/issues/3'}
        r = await self.invoke('issue.create')
        self.assertEqual(r['effect'], 'unknown'); self.assertFalse(r['ok'])

    async def test_readback_failure_preserves_confirmed_effect(self):
        self.backend.failures['issue_read:get'] = 403
        r = await self.invoke('issue.create')
        self.assertEqual((r['status'], r['effect']), ('partial','confirmed'))
        self.assertFalse(r['receipt']['readback_verified'])
        self.backend.failures.clear()
        out = await self.service.handle('sdlc_github_operation_status', {'repository':REPO, 'expected_actor_id':101, 'request_id':r['receipt']['request_id'], 'reconcile':True})
        self.assertTrue(out['ok']); self.assertEqual(len(self.backend.writes), 1)
        self.assertEqual(len(list(self.root.rglob('observation-*.json'))), 1)

    async def test_disconnect_after_write_never_replays(self):
        self.backend.after_write_error = 'DISCONNECTED'
        r = await self.invoke('issue.create')
        self.assertEqual((r['status'],r['effect']), ('unknown','unknown'))
        self.backend.after_write_error = None
        await self.invoke('issue.create'); self.assertEqual(len(self.backend.writes), 1)
        out = await self.service.handle('sdlc_github_operation_status', {'repository':REPO, 'expected_actor_id':101, 'request_id':r['receipt']['request_id'], 'reconcile':True})
        self.assertTrue(out['ok']); self.assertEqual(len(self.backend.writes), 1)

    async def test_context_cleanup_cannot_erase_effect(self):
        base = self.transport
        class CleanupFailure:
            _token = 'synthetic-credential'
            @asynccontextmanager
            async def connect(inner):
                async with base.connect() as c:
                    yield c
                raise GithubError('DISCONNECTED')
        self.service = GithubService(self.root, transport=CleanupFailure())
        r = await self.invoke('issue.create')
        self.assertEqual(r['effect'], 'confirmed'); self.assertTrue(r['ok'])
        self.assertEqual(r['warnings'][0]['code'], 'DISCONNECTED')

    async def test_receipt_storage_failure_keeps_intent_and_effect(self):
        with patch.object(self.service.records, 'save_receipt', side_effect=GithubError('STORAGE_FAILED')):
            r = await self.invoke('issue.create')
        self.assertEqual((r['status'],r['effect']), ('partial','confirmed'))
        self.assertEqual(len(list(self.root.rglob('intent.json'))), 1)
        again = await self.invoke('issue.create'); self.assertEqual(again['effect'], 'unknown')
        self.assertEqual(len(self.backend.writes), 1)

    async def test_unknown_marker_missing_or_multiple_stays_unknown(self):
        for scenario in ('missing','multiple','incomplete'):
            with self.subTest(scenario=scenario):
                rid = str(uuid4());self.backend.after_write_error = 'DISCONNECTED'
                r = await self.invoke('issue.create', request_id=rid)
                self.backend.after_write_error = None
                obj = self.backend.objects[self.backend.next_number-1]
                if scenario == 'missing':obj['body'] = 'removed'
                if scenario == 'multiple':
                    duplicate = deepcopy(obj); n=self.backend.next_number;self.backend.next_number+=1
                    duplicate.update({'number':n,'id':10000+n,'html_url':f'https://github.com/example/project/issues/{n}'})
                    self.backend.objects[n]=duplicate
                self.backend.page_metadata = scenario != 'incomplete'
                before = len(self.backend.writes)
                out = await self.service.handle('sdlc_github_operation_status', {'repository':REPO,'expected_actor_id':101,'request_id':rid,'reconcile':True})
                self.assertEqual(out['effect'], 'unknown');self.assertEqual(len(self.backend.writes), before)

    async def test_update_reconciliation_is_state_observation(self):
        self.backend.after_write_error='DISCONNECTED'
        r=await self.invoke('issue.update');self.backend.after_write_error=None
        out=await self.service.handle('sdlc_github_operation_status',{'repository':REPO,'expected_actor_id':101,'request_id':r['receipt']['request_id'],'reconcile':True})
        self.assertTrue(out['ok']);self.assertEqual(out['warnings'][0]['code'],'STATE_OBSERVATION_ONLY')

    async def test_all_crash_windows(self):
        for point in ('before_intent','after_intent_before_send','after_send','after_success_before_readback','before_receipt','after_receipt'):
            with self.subTest(point=point):
                rid=str(uuid4()); before=len(self.backend.writes)
                def fault(p):
                    if p==point:raise SimulatedCrash()
                self.service=GithubService(self.root,transport=self.transport,fault=fault)
                with self.assertRaises(SimulatedCrash):await self.invoke('issue.create',request_id=rid)
                self.service=GithubService(self.root,transport=self.transport)
                if point=='before_intent':
                    self.assertEqual(len(self.backend.writes),before)
                    continue
                out=await self.invoke('issue.create',request_id=rid)
                self.assertEqual(len(self.backend.writes), before+(0 if point=='after_intent_before_send' else 1))
                self.assertEqual(out['status'], 'completed' if point=='after_receipt' else 'unknown')

    async def test_corrupt_record_blocks_replay(self):
        await self.invoke('issue.create')
        path=next(self.root.rglob('intent.json'));path.write_text('{"partial":')
        r=await self.invoke('issue.create')
        self.assertEqual(r['errors'][0]['code'],'RECORD_CORRUPT');self.assertEqual(len(self.backend.writes),1)

    async def test_empty_claim_after_crash_blocks_replay(self):
        tool,p=request('issue.create');d=self.root.joinpath(*self.service.records._key(101,REPO,p['request_id']))
        d.mkdir(parents=True,mode=0o700)
        for parent in d.parents:
            if parent==self.root:break
            parent.chmod(0o700)
        r=await self.invoke('issue.create')
        self.assertEqual(r['effect'],'unknown');self.assertFalse(self.backend.writes)

    async def test_symlink_namespace_blocks_before_write(self):
        outside=self.root/'outside';outside.mkdir()
        (self.root/'.local').symlink_to(outside,target_is_directory=True)
        r=await self.invoke('issue.create')
        self.assertEqual(r['errors'][0]['code'],'STORAGE_UNSAFE');self.assertFalse(self.backend.writes)

    async def test_symlink_root_rejected(self):
        link=self.root/'root-link';link.symlink_to(self.root,target_is_directory=True)
        self.service=GithubService(link,transport=self.transport)
        r=await self.invoke('issue.create')
        self.assertEqual(r['errors'][0]['code'],'STORAGE_UNSAFE');self.assertFalse(self.backend.writes)

    async def test_hardlink_receipt_is_rejected(self):
        await self.invoke('issue.create')
        receipt=next(self.root.rglob('receipt.json'));os.link(receipt,self.root/'copy')
        r=await self.invoke('issue.create')
        self.assertEqual(r['errors'][0]['code'],'STORAGE_UNSAFE');self.assertEqual(len(self.backend.writes),1)

    async def test_fifo_receipt_cannot_block(self):
        await self.invoke('issue.create')
        receipt=next(self.root.rglob('receipt.json'));receipt.unlink();os.mkfifo(receipt,0o600)
        r=await self.invoke('issue.create')
        self.assertEqual(r['errors'][0]['code'],'STORAGE_UNSAFE');self.assertEqual(len(self.backend.writes),1)

    async def test_private_modes_and_content_minimization(self):
        body='private-body-that-is-not-to-be-cached'
        await self.invoke('issue.create',body=body)
        for path in (self.root/'.local').rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o077,0)
            if path.is_file():self.assertNotIn(body,path.read_text())

    async def test_readonly_disk_is_zero_write(self):
        with patch.object(self.service.records,'claim',side_effect=GithubError('STORAGE_FAILED')):
            r=await self.invoke('issue.create')
        self.assertEqual(r['errors'][0]['code'],'STORAGE_FAILED');self.assertFalse(self.backend.writes)

    async def test_cache_deletion_preserves_receipt(self):
        first=await self.invoke('issue.create')
        cache=self.root/'.cache/github';cache.mkdir(parents=True);(cache/'temporary').write_text('rebuildable')
        before={str(p.relative_to(self.root)):p.read_bytes() for p in (self.root/'.local').rglob('*') if p.is_file()}
        shutil.rmtree(self.root/'.cache')
        self.service=GithubService(self.root,transport=self.transport)
        self.assertEqual(first,await self.invoke('issue.create'))
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes() for p in (self.root/'.local').rglob('*') if p.is_file()})

    async def test_unknown_pagination_not_inferred_from_short_or_empty_page(self):
        for branches in ([],['main']):
            self.backend.branches=branches;self.backend.page_metadata=False
            r=await self.invoke('repo.branches')
            self.assertTrue(r['ok']);self.assertEqual(r['pagination']['has_more'],'unknown');self.assertEqual(r['completeness'],'unknown')

    async def test_cursor_and_page_bounds(self):
        for kwargs in ({'per_page':101},{'per_page':0},{'page':0},{'page':True}):
            r=await self.invoke('repo.branches',**kwargs);self.assertEqual(r['errors'][0]['code'],'ARGUMENT_INVALID')
        r=await self.invoke('issue.list',page=1);self.assertEqual(r['errors'][0]['code'],'ARGUMENT_INVALID')
        self.backend.objects.update({n:self.backend.object(n,'issue') for n in range(3,8)})
        r=await self.invoke('issue.list',per_page=2)
        self.assertTrue(r['pagination']['has_more']);self.assertIsNotNone(r['pagination']['next_cursor'])

    async def test_truncated_diff_and_log_are_partial(self):
        self.backend.replacements['pull_request_read:get_diff']=types.CallToolResult(content=[types.TextContent(type='text',text='diff --git a/x b/x\n'+'+'*(MAX_TEXT+100))])
        r=await self.invoke('pr.diff');self.assertEqual(r['status'],'partial');self.assertLess(len(canonical(r)),MAX_TEXT)
        self.backend.replacements['get_job_logs']={'job_id':101,'logs_content':'x'*(MAX_TEXT+100),'original_length':MAX_TEXT+100}
        r=await self.invoke('actions.logs');self.assertEqual(r['status'],'partial');self.assertTrue(r['data']['tail_truncated'])
        self.assertLess(len(canonical(r)),MAX_TEXT)

    async def test_resource_link_is_partial_never_downloaded(self):
        self.backend.replacements['get_file_contents']=types.CallToolResult(content=[types.ResourceLink(type='resource_link',uri='repo://example/project/sha/'+'a'*40+'/contents/README.md',name='README.md')])
        r=await self.invoke('repo.files')
        self.assertEqual(r['status'],'partial');self.assertEqual([t for t,a in self.backend.calls],['get_me','get_file_contents'])

    async def test_secrets_redacted_from_output_and_rejected_in_input(self):
        secret='github_pat_'+'S'*45
        r=await self.invoke('issue.create',body=secret)
        self.assertEqual(r['errors'][0]['code'],'SECRET_IN_INPUT');self.assertFalse(self.backend.writes)
        self.backend.issue['body']=secret
        r=await self.invoke('issue.get')
        self.assertNotIn(secret,json.dumps(r));self.assertIn('[REDACTED]',r['data']['body'])
        self.assertEqual(list(self.root.iterdir()),[])

    async def test_unrelated_new_upstream_tool_not_exposed(self):
        self.backend.tools['delete_repository']=types.Tool(name='delete_repository',inputSchema={'type':'object','properties':{}})
        r=await self.service.handle('sdlc_github_status',{})
        self.assertEqual(len(r['data']['capabilities']),32);self.assertEqual(len(TOOLS),8)
        r=await self.service.handle('sdlc_github_delete_repository',{})
        self.assertFalse(r['ok']);self.assertFalse(self.backend.writes)

    async def test_schema_external_ref_is_never_resolved(self):
        self.backend.tools['list_branches'].inputSchema['properties']['page']={'$ref':'https://example.invalid/schema'}
        with patch('socket.socket.connect',side_effect=AssertionError('network')):
            r=await self.invoke('repo.branches')
        self.assertEqual(r['errors'][0]['code'],'CAPABILITY_UNAVAILABLE')

    async def test_large_workspace_no_scan_or_code_pollution(self):
        work=self.root/'project';work.mkdir()
        for n in range(10000):(work/f'file-{n:05d}').write_text('synthetic\n')
        before=[(p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in sorted(work.iterdir())]
        await self.invoke('issue.create')
        self.assertEqual(before,[(p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in sorted(work.iterdir())])
        self.assertFalse((work/'.local').exists());self.assertFalse((work/'.sdlc').exists())


def mapping_test(name):
    async def test(self):
        r=await self.invoke(name)
        self.assertTrue(r['ok'],r)
        expected=expected_mapping(name)
        self.assertEqual(sum(row==expected for row in self.backend.calls),1)
        self.assertEqual(len(self.backend.writes),1 if name in ORACLE_WRITES else 0)
        self.assertEqual(r['effect'],'confirmed' if name in ORACLE_WRITES else 'none')
    return test


def error_test(name,code):
    async def test(self):
        tool,method,_,_=CASES[name]
        self.backend.failures[tool+':'+(method or '')]=code
        r=await self.invoke(name)
        self.assertFalse(r['ok']);self.assertEqual(r['errors'][0]['code'],'PERMISSION_DENIED' if code==403 else 'UPSTREAM_FAILED')
        self.assertEqual(len(self.backend.writes),1 if name in ORACLE_WRITES else 0)
        self.assertEqual(r['effect'],'unknown' if code==500 and name in ORACLE_WRITES else 'none')
    return test


def capability_test(name):
    async def test(self):
        tool=CASES[name][0];self.backend.tools[tool].inputSchema['required'].append('new_required_parameter')
        r=await self.invoke(name)
        self.assertEqual(r['errors'][0]['code'],'CAPABILITY_UNAVAILABLE');self.assertFalse(self.backend.writes)
    return test


for op in CASES:
    suffix=op.replace('.','_').replace('-','_')
    setattr(RuntimeTests,'test_mapping_'+suffix,mapping_test(op))
    setattr(RuntimeTests,'test_permission_'+suffix,error_test(op,403))
    setattr(RuntimeTests,'test_failure_'+suffix,error_test(op,500))
    setattr(RuntimeTests,'test_drift_'+suffix,capability_test(op))


class CompilerAndTargetTests(unittest.TestCase):
    def test_meta_commands_and_aliases(self):
        for text in ('help','--help','-h','version','-V','--version','commands','--commands','--list-commands','examples','--examples'):
            with self.subTest(text=text):
                r=COMPILER.compile_invocation(text)
                self.assertTrue(r['ok']);self.assertEqual(r['effects'],[])

    def test_bare_auto_status(self):
        self.assertEqual(COMPILER.compile_invocation('')['tool'],'sdlc_github_status')
        self.assertEqual(COMPILER.compile_invocation('auto -- create an issue')['status'],'action_required')

    def test_shared_command_aliases(self):
        for text in ('status','--status','command status','cmd status','command=status','--command=status','-c status','-c=status','operation status','op status','operation=status','--operation=status','-o status','-o=status'):
            with self.subTest(text=text):self.assertEqual(COMPILER.compile_invocation(text)['tool'],'sdlc_github_status')

    def test_parser_failures(self):
        for text in ('read --repo','status --bad','status read','read --repo x/y --kind repo.branches --per-page 101','issue-create --repo x/y --title hi --body x --body-file /missing','help --body-file /must-not-read','read --repo x/y --repo a/b','"unclosed'):
            with self.subTest(text=text):
                with self.assertRaises((GithubError,ValueError)):COMPILER.compile_invocation(text)

    def test_parser_all_operation_invocations(self):
        import shlex
        for name in CASES:
            tool,p=request(name)
            command='read' if name not in ORACLE_WRITES else {'comment.create':'comment'}.get(name,name.replace('.','-'))
            args=[command]
            for k,v in p.items():
                option={'operation':'kind','repository':'repo'}.get(k,k.replace('_','-'))
                args.extend(['--'+option,str(v)])
            result=COMPILER.compile_invocation(args)
            self.assertEqual(result['tool'],tool)

    def test_body_file_and_leading_dash_body(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d).resolve(strict=True)/'body';file.write_text('explicit body')
            text=['issue-create','--repo','example/project','--title','test','--body-file',str(file),'--expected-actor-id','101']
            r=COMPILER.compile_invocation(text);self.assertEqual(r['arguments']['body'],'explicit body')
            file.unlink();file.symlink_to('/etc/passwd')
            with self.assertRaises(GithubError):COMPILER.compile_invocation(text)
        r=COMPILER.compile_invocation('issue-create --repo example/project --title test --body=--literal --expected-actor-id 101')
        self.assertEqual(r['arguments']['body'],'--literal')

    def test_request_id_generated_and_can_be_reused(self):
        text='issue-create --repo example/project --title test --expected-actor-id 101'
        r=COMPILER.compile_invocation(text);rid=r['arguments']['request_id']
        self.assertEqual(COMPILER.compile_invocation(text+' --request-id '+rid)['arguments']['request_id'],rid)

    def test_unique_remote_only(self):
        self.assertEqual(repository_from_remotes(['git@github.com:example/project.git','https://github.com/example/project']),'example/project')
        for remotes in ([],['https://github.com/a/b','https://github.com/c/d'],['ssh://internal.invalid/a/b']):
            with self.assertRaises(GithubError):repository_from_remotes(remotes)

    def test_standard_urls(self):
        fixtures=[('https://github.com/example/project',{'repository':REPO}),('https://github.com/example/project/issues/1',{'repository':REPO,'subject_type':'issue','number':1}),('https://github.com/example/project/pull/2',{'repository':REPO,'subject_type':'pr','number':2}),('https://github.com/example/project/actions/runs/100',{'repository':REPO,'run_id':100}),('https://github.com/example/project/releases/tag/v1.0.0',{'repository':REPO,'tag':'v1.0.0'})]
        for url,expected in fixtures:self.assertEqual(parse_url(url),expected)

    def test_url_escapes_conflicts_and_ambiguous_refs(self):
        for url in ('http://github.com/a/b','https://evil.invalid/a/b','https://u@github.com/a/b','https://github.com:443/a/b','https://github.com/a/%2e%2e','https://github.com/a/b/blob/feature/topic/file','https://github.com/a/b?x=1','https://github.com/a/b/issues/0'):
            with self.assertRaises(GithubError):parse_url(url)
        with self.assertRaises(GithubError):merge_target({'repository':'a/b'},{'repository':'x/y'})
        r=parse_url('https://github.com/a/b/blob/feature/topic/file',ref='feature/topic',path='file')
        self.assertEqual((r['ref'],r['path']),('feature/topic','file'))

    def test_error_classification(self):
        for msg,expected in [('401','AUTH_FAILED'),('403','PERMISSION_DENIED'),('404','NOT_FOUND_OR_INACCESSIBLE'),('429','RATE_LIMITED'),('500','UPSTREAM_FAILED')]:
            self.assertEqual(classify(msg),expected)
        self.assertEqual(classify(TimeoutError()),'TIMEOUT')

    def test_schema_shapes(self):
        for name in TOOLS:Draft202012Validator.check_schema(tool_schema(name))
        Draft202012Validator.check_schema(SCHEMA)


def process_worker(root, event, queue):
    async def run():
        backend=Backend();service=GithubService(root,transport=FakeTransport(backend))
        event.wait(10)
        tool,p=request('issue.create');r=await service.handle(tool,p)
        queue.put((r['status'],len(backend.writes)))
    asyncio.run(run())


class ConcurrentProcessTests(unittest.TestCase):
    def test_two_processes_one_claim(self):
        context=multiprocessing.get_context('spawn')
        with tempfile.TemporaryDirectory() as d:
            event=context.Event();queue=context.Queue()
            workers=[context.Process(target=process_worker,args=(str(Path(d).resolve(strict=True)),event,queue)) for _ in range(2)]
            for worker in workers:worker.start()
            event.set();results=[queue.get(timeout=30) for _ in workers]
            for worker in workers:worker.join(30);self.assertEqual(worker.exitcode,0)
            self.assertEqual(sum(r[1] for r in results),1)
            self.assertTrue(all(r[0] in {'completed','unknown'} for r in results))
