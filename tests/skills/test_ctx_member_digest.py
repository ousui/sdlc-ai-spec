"""WEB-RF-001: verify the external digest contract, not renderer self-consistency."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import unittest
from tests.skills import test_sdlc_000_ctx as fixture

class CtxMemberDigestTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.CtxRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.raw = 'SpringGear JDK21 observation\n'
        self.hex = hashlib.sha256(self.raw.encode()).hexdigest()
        self.request = self.fixture.invocation()
        self.request['inputs']['supporting_members'] = [{
            'member_id': 'SUP-001', 'canonical_name': 'observation.md',
            'media_type': 'text/markdown', 'purpose': 'Reproducible observation',
            'content': self.raw,
        }]
    def build(self, request=None):
        return fixture.runtime.build_payload(request or self.request,
            artifact_id='CTX-20260907000000-01', revision=1,
            base_revision=None, now=fixture.FIXED_TIME)
    def test_rendered_manifest_has_exactly_one_algorithm_prefix(self):
        product = self.build()
        self.assertFalse(product.errors, product.errors)
        raw = product.payload.primary_blob.decode()
        self.assertNotIn('sha256:sha256:', raw)
        row = next(line for line in raw.splitlines() if line.startswith('| SUP-001 |'))
        self.assertEqual(row.split('|')[6].strip(), 'sha256:' + self.hex)
    def test_explicit_bare_digest_is_accepted(self):
        request = deepcopy(self.request)
        request['inputs']['supporting_members'][0]['sha256'] = self.hex
        self.assertFalse(self.build(request).errors)
    def test_explicit_prefixed_digest_is_accepted(self):
        request = deepcopy(self.request)
        request['inputs']['supporting_members'][0]['sha256'] = 'sha256:' + self.hex
        self.assertFalse(self.build(request).errors)
    def test_explicit_double_prefix_is_rejected(self):
        request = deepcopy(self.request)
        request['inputs']['supporting_members'][0]['sha256'] = 'sha256:sha256:' + self.hex
        self.assertTrue(self.build(request).errors)
    def test_actual_stored_projection_passes_readonly_check(self):
        created = self.fixture.invoke(self.request)
        a = created['artifact']
        self.assertIsNotNone(a, created)
        checked = self.fixture.invoke(self.fixture.invocation('check', reference=f"{a['id']}@{a['revision']}"))
        self.assertTrue(checked['ok'], checked)
        self.assertEqual(checked['gate']['result'], 'pending')
    def test_verifier_rejects_double_prefix_even_if_payload_digest_is_recomputed(self):
        created = self.fixture.invoke(self.request)
        a = created['artifact']
        store = fixture.runtime.ArtifactStore.open_read_only(self.fixture.project_root)
        stored = store.read_revision(a['id'], a['revision'])
        old = stored.payload.primary_blob
        new = old.replace(('sha256:' + self.hex).encode(), ('sha256:sha256:' + self.hex).encode())
        self.assertNotEqual(old, new)
        payload = replace(stored.payload, primary_blob=new, primary_sha256=fixture.runtime.compute_sha256(new))
        errors, _, _ = fixture.runtime.validate_stored_revision(replace(stored, payload=payload))
        self.assertIn('CORE-G-003', errors)
    def test_wrong_member_digest_still_rejected(self):
        request = deepcopy(self.request)
        request['inputs']['supporting_members'][0]['sha256'] = 'sha256:' + '0' * 64
        self.assertTrue(self.build(request).errors)
