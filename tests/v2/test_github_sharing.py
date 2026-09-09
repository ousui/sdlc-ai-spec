"""Issue projection and durable publishing protocol; fake API is explicitly isolated."""
import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from test_runtime import Session
from packages.sdlc import github_sharing as gh, rendering
from packages.sdlc.common import Fault
from packages.sdlc.storage import Store

ISSUE='https://github.com/example/lab/issues/7'


class FakeAPI:
    def __init__(self):
        self.posts=0; self.comments=[]; self.lose=False; self.actor=77; self.invalid=False; self.full=False
    def api(self,method,endpoint,payload=None):
        if endpoint=='graphql': return {'data':{'viewer':{'databaseId':self.actor,'login':'fixture-actor'}}}
        if endpoint=='repos/example/lab/issues/7': return {'html_url':ISSUE,'locked':False}
        if method=='POST':
            self.posts+=1
            row={'id':self.posts,'body':payload['body'],'user':{'id':self.actor},
                 'issue_url':'https://api.github.com/repos/example/lab/issues/7',
                 'html_url':ISSUE+'#issuecomment-'+str(self.posts)}
            self.comments.append(row)
            if self.lose: raise Fault('LOST','Simulated lost remote reply',status='blocked')
            return row
        if 'per_page=' in endpoint:
            return [{'body':'other'}]*100 if self.full else copy.deepcopy(self.comments)
        if '/issues/comments/' in endpoint:
            row=copy.deepcopy(self.comments[-1])
            if self.invalid: row['body']='externally edited'
            return row
        raise AssertionError((method,endpoint))


class GithubSharingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.s=Session(self.root);self.s.initialize();self.s.new_change();self.s.req()
        self.store=Store(self.root);self.project=self.store.config()['project_id'];self.change=self.s.bindings['change_id']
        self.api=FakeAPI()
    def tearDown(self): self.tmp.cleanup()
    def request(self,command,payload):
        return {'api_version':'2','command':command,'change_id':self.change,'payload':payload}
    def preview(self): return gh.invoke(self.root,self.request('github.preview',{'issue_url':ISSUE,'phase':'REQ'}),self.api)['data']
    def publish(self,**extra):
        p=self.preview()
        return gh.invoke(self.root,self.request('github.publish',{'issue_url':ISSUE,'phase':'REQ','preview_digest':p['preview_digest'],'confirmed':True,**extra}),self.api)
    def test_phase_projection_is_readable_and_exact_not_json_dump(self):
        p=self.preview();self.assertIn('## 需求与验收',p['body']);self.assertIn('Accurate length',p['body'])
        self.assertNotIn('"requirements": [',p['body']);self.assertEqual(0,self.api.posts)
        path=rendering.render_change(self.store,self.project,self.change)
        self.assertIn('<table>',path.read_text());self.assertIn('spec.md',[p.name for p in path.parent.iterdir()])
        self.assertIn('需求-001',(path.parent/'spec.md').read_text())
    def test_post_readback_and_duplicate_are_separate_from_business_run(self):
        with self.store.read() as con: before=[tuple(r) for r in con.execute('SELECT * FROM runs')]
        first=self.publish();second=self.publish()
        self.assertEqual(1,self.api.posts);self.assertTrue(first['ok']);self.assertTrue(second['data']['idempotent'])
        with self.store.read() as con:
            self.assertEqual(before,[tuple(r) for r in con.execute('SELECT * FROM runs')])
            self.assertIsNone(con.execute("SELECT run_id FROM operations WHERE command='github.publish'").fetchone()[0])
        p=gh.invoke(self.root,self.request('github.preview',{'phase':'REQ'}),self.api)['data']
        self.assertEqual(ISSUE,p['issue_url'])
    def test_uncertain_response_reconciles_without_second_post(self):
        self.api.lose=True;first=self.publish();self.assertEqual('unknown',first['status'])
        self.assertEqual('unknown',self.publish()['status']);self.assertEqual(1,self.api.posts)
        value=gh.invoke(self.root,self.request('github.reconcile',{'publication_id':first['operation_id']}),self.api)
        self.assertTrue(value['ok']);self.assertEqual(1,self.api.posts)
    def test_remote_edit_or_wrong_identity_never_overwrites_human_content(self):
        first=self.publish();self.api.comments[0]['body']='edited by human '+self.api.comments[0]['body']
        value=gh.invoke(self.root,self.request('github.reconcile',{'publication_id':first['operation_id']}),self.api)
        self.assertEqual('conflict',value['status']);self.assertEqual(1,self.api.posts)
    def test_incomplete_pagination_does_not_prove_absence_or_resend(self):
        self.api.lose=True;first=self.publish();self.api.full=True
        value=gh.invoke(self.root,self.request('github.reconcile',{'publication_id':first['operation_id']}),self.api)
        self.assertEqual('unknown',value['status']);self.assertEqual(1,self.api.posts)
    def test_stale_preview_and_confirmation_are_rejected(self):
        with self.assertRaises(Fault): self.publish(preview_digest='stale')
        with self.assertRaises(Fault): self.publish(confirmed=False)
        self.assertEqual(0,self.api.posts)
    def test_scope_and_target_are_strict(self):
        with self.assertRaises(Fault): gh.target('https://github.com/example/lab/pull/7')
        with self.assertRaises(Fault): gh.target('https://evil.invalid/example/lab/issues/7')
        with self.assertRaises(Fault): gh.invoke(self.root,self.request('github.preview',{}),self.api)
    def test_public_cli_dispatch_uses_existing_protocol(self):
        with patch.object(gh,'GhTransport',return_value=self.api):
            p=self.s.ok('github.preview',{'issue_url':ISSUE,'phase':'REQ'})
            result=self.s.send('github.publish',{'issue_url':ISSUE,'phase':'REQ','preview_digest':p['preview_digest'],'confirmed':True})
        self.assertTrue(result['ok']);self.assertIsNone(result['run_id']);self.assertEqual(1,self.api.posts)
    def test_sharing_receipts_travel_with_change_archive(self):
        self.publish()
        exported=Session(self.root).ok('workspace.export',{'change_id':self.change})
        with zipfile.ZipFile(exported['path']) as z:
            rows=json.loads(z.read('database.json'))
        self.assertEqual(1,len([r for r in rows['operations'] if r['command']=='github.publish']))
    def test_caller_operation_key_cannot_be_reused_for_different_preview(self):
        preview=self.preview();req=self.request('github.publish',{'issue_url':ISSUE,'phase':'REQ','preview_digest':preview['preview_digest'],'confirmed':True});req['operation_id']='explicit-share'
        self.assertTrue(gh.invoke(self.root,req,self.api)['ok'])
        req['payload']['phase']='ALL';req['payload']['preview_digest']=gh.invoke(self.root,self.request('github.preview',{'issue_url':ISSUE}),self.api)['data']['preview_digest']
        with self.assertRaises(Fault): gh.invoke(self.root,req,self.api)
        self.assertEqual(1,self.api.posts)


if __name__=='__main__': unittest.main()
