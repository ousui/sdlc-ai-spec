"""Domain VFP identities must survive the DSN/PLN to IMP boundary."""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'skills/sdlc-400-imp/scripts')]
from imp_binding import _lineage
from packages.sdlc_runtime.canonical import parse_markdown_tables


class DomainVfpLineageTests(TestCase):
    reference = 'DSN-20260907000000-01@1'
    context = 'CTX-20260907000000-01@1'

    def lineage(self, identity, *, in_member=False):
        raw = f'| ID | Meaning |\n|---|---|\n| {identity} | Actual verification point |\n'
        tables = parse_markdown_tables(raw)
        member = SimpleNamespace(member_id='DOM-220', media_type='text/markdown', raw_bytes=raw.encode())
        parsed = SimpleNamespace(front_matter={'context':self.context,'inputs':[]}, tables=() if in_member else tables)
        stored = SimpleNamespace(payload=SimpleNamespace(
            manifest=SimpleNamespace(raw_bytes=b'{}'), members=(member,) if in_member else ()))
        with patch('imp_binding.read_authority', return_value=(stored, parsed)):
            return _lineage(object(), self.reference, self.context)[1]

    def test_domain_point_in_primary_is_preserved(self):
        self.assertIn(self.reference+'#VFP-220-001', self.lineage('VFP-220-001'))

    def test_domain_point_in_member_has_both_supported_locators(self):
        basis = self.lineage('VFP-510-012', in_member=True)
        self.assertIn(self.reference+'#VFP-510-012', basis)
        self.assertIn(self.reference+'/DOM-220#VFP-510-012', basis)

    def test_single_segment_identity_is_unchanged(self):
        self.assertIn(self.reference+'#VFP-001', self.lineage('VFP-001'))

    def test_change_identity_is_unchanged(self):
        self.assertIn(self.reference+'#CHG-001', self.lineage('CHG-001'))

    def test_malformed_or_unregistered_multisegment_identity_is_not_added(self):
        for identity in ('VFP-220--001','VFP-220-1','VFP-../001','VFP-220-001-extra','CHG-220-001','None'):
            with self.subTest(identity=identity):
                self.assertNotIn(self.reference+'#'+identity,self.lineage(identity, in_member=True))

    def test_undeclared_domain_point_is_not_invented(self):
        self.assertNotIn(self.reference+'#VFP-310-001',self.lineage('VFP-220-001',in_member=True))
