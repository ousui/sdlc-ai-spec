"""Preconfirmation must refer to bytes available to the independent reader."""
import hashlib
import re
import unittest
from tests.skills import test_sdlc_000_ctx as fixture

class CtxPreconfirmationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.CtxRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
    def prepared(self, request=None):
        request=request or self.fixture.invocation()
        request['options']['prepare_confirmation']=True
        result=self.fixture.invoke(request)
        a=result['artifact']
        reader=fixture.runtime.ArtifactStore.open_read_only(self.fixture.project_root)
        return result,reader.read_revision(a['id'],a['revision'])
    def test_review_draft_binds_actual_persisted_control_bytes(self):
        result,stored=self.prepared()
        text=stored.payload.primary_blob.decode()
        content=re.sub(r'(?m)^status: .*\n','',text).split('## 门禁 Gate\n')[0]
        computed='sha256:'+hashlib.sha256(content.encode()).hexdigest()
        binding=next(w['details'] for w in result['warnings'] if w['code']=='FINAL_CONFIRMATION_BINDINGS')
        self.assertEqual(binding['control_input_digest'],computed)
        self.assertEqual(stored.payload.artifact_status,'draft')
        self.assertEqual(stored.control.state,'open')
        self.assertFalse(result['ok'])
        self.assertEqual(result['status'],'action_required')
        self.assertEqual(result['gate']['result'],'pending')
    def test_review_draft_closes_actual_checks_other_than_final_confirmation(self):
        result,stored=self.prepared()
        text=stored.payload.primary_blob.decode()
        rows=[l for l in text.splitlines() if re.match(r'^\| (CORE|CTX)-G-\d{3} \|',l)]
        non_final=[l for l in rows if not l.startswith('| CORE-G-009 |')]
        self.assertTrue(non_final)
        self.assertTrue(all(l.split('|')[3].strip()=='pass' for l in non_final))
        computed='sha256:'+hashlib.sha256(('\n'.join(non_final)+'\n').encode()).hexdigest()
        binding=next(w['details'] for w in result['warnings'] if w['code']=='FINAL_CONFIRMATION_BINDINGS')
        self.assertEqual(computed,binding['check_set_result_digest'])
        self.assertEqual(fixture.runtime.validate_stored_revision(stored)[:2],([], 'pending'))
    def test_prepare_cannot_hide_missing_domain_facts(self):
        request=self.fixture.invocation()
        request['inputs']['context']['project_identity'].pop('purpose')
        result,stored=self.prepared(request)
        self.assertNotEqual(stored.payload.artifact_status,'ready')
        self.assertEqual(stored.control.state,'open')
        self.assertIn('OPI-',stored.payload.primary_blob.decode())
        self.assertFalse(any(w['code']=='FINAL_CONFIRMATION_BINDINGS' for w in result['warnings']))
    def test_prepared_check_is_read_only_and_not_authority(self):
        result,stored=self.prepared()
        before=(self.fixture.project_root/'.sdlc/store.sqlite3').read_bytes()
        checked=self.fixture.invoke(self.fixture.invocation('check',reference=f'{stored.payload.artifact_id}@1'))
        self.assertTrue(checked['ok'],checked)
        self.assertEqual(checked['gate']['result'],'pending')
        self.assertIsNone(checked['artifact']['reference'])
        self.assertEqual(before,(self.fixture.project_root/'.sdlc/store.sqlite3').read_bytes())
    def test_invalid_option_cannot_approve(self):
        request=self.fixture.invocation()
        request['options']['prepare_confirmation']='true'
        result=self.fixture.invoke(request)
        self.assertFalse(result['ok'])
        self.assertEqual(result['gate'], {'result': 'pending', 'failed_checks': []})
        self.assertTrue(any(e['code']=='INVALID_PREPARE_CONFIRMATION' for e in result['errors']))
        self.assertIsNone(result['artifact'])
        self.assertFalse((self.fixture.project_root / '.sdlc').exists())
