"""Independent provenance regressions retained after actual red cases."""
import io
import json
from pathlib import Path
import unittest
import zipfile
import test_transfer as fixture
from test_runtime import Session
from packages.sdlc import transfer

class IndependentProjectionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.TransferTests()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)

    def fork_bundle(self):
        f = self.f
        copied, shared = f.fork_mutable_revision()
        copied.submit('PLN', [{'op':'update_task','id':f.fixture.task,'title':'Independent source frozen variant'}])
        copied.complete('PLN')
        f.revise(copied, 'Independent source child')
        f.s.ok('change.revise', {'phase':'PLN','reason':'Independent target draft'},
               expected_generation=f.s.ok('phase.prepare')['generation'])
        return f.archive(f.copy)

    def preserve(self, archive):
        response = self.f.public.send('workspace.collect', {'path':archive['path'], 'conflict_policy':'preserve_revision_versions'})
        self.assertTrue(response.get('data', {}).get('rows_imported'), response)
        return response['data']

    def test_same_logical_bundle_reencoding_cannot_overwrite_original_failed_archive(self):
        archive = self.fork_bundle()
        old = self.f.collect(archive)
        self.assertEqual(old['relation'], 'row_conflict')
        original = Path(old['archive']).read_bytes()
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as target:
            for name in source.namelist():
                target.writestr(name, source.read(name))
        altered = output.getvalue()
        self.assertNotEqual(original, altered)
        alternate = Path(self.f.temp.name)/'same-logical-different-zip.zip'
        alternate.write_bytes(altered)
        self.assertEqual(transfer.unpack(alternate)[3], archive['bundle_digest'])
        response = self.f.public.send('workspace.collect', {'path':str(alternate), 'conflict_policy':'preserve_revision_versions'})
        # Either retain the original and reject this encoding, or store a distinct
        # original-byte variant; silently overwriting the old receipt's file fails.
        self.assertEqual(Path(old['archive']).read_bytes(), original,
                         'Explicit retry overwrote archive bytes referenced by prior failure; response=' + json.dumps(response))
        self.assertFalse(response['ok'])
        self.assertEqual('ARCHIVE_CONFLICT', response['errors'][0]['code'])
        restored = self.preserve(archive)
        self.assertTrue(restored['rows_imported'], restored)
        self.assertEqual(original, Path(restored['archive']).read_bytes())

    def test_provenance_remains_portable_after_collect_and_second_export(self):
        f = self.f
        third = Path(f.temp.name)/'third-store'
        third.mkdir()
        f.public.ok('workspace.clone', {'target':str(third)})
        original_archive = self.fork_bundle()
        restored = self.preserve(original_archive)
        self.assertTrue(restored['rows_imported'], restored)
        outbound = f.archive(f.root)
        _, _, first_files, _ = transfer.unpack(Path(outbound['path']))
        original_name = 'imports/'+original_archive['bundle_digest']+'.zip'
        self.assertIn(original_name, first_files)
        third_session = Session(third)
        received = third_session.ok('workspace.collect', {'path':outbound['path']})
        self.assertTrue(received['rows_imported'], received)
        onward = third_session.ok('workspace.export', {'change_id':f.change})
        _, _, onward_files, _ = transfer.unpack(Path(onward['path']))
        # Opaque nested archive retention is fine; source material may remain
        # direct or inside a carried original ZIP, but it cannot disappear.
        original_bytes = Path(original_archive['path']).read_bytes()
        def contains_original(files):
            for name, raw in files.items():
                if name.startswith('imports/') and name.endswith('.zip'):
                    if raw == original_bytes:
                        return True
                    with zipfile.ZipFile(io.BytesIO(raw)) as nested:
                        if contains_original({n:nested.read(n) for n in nested.namelist()}):
                            return True
            return False
        self.assertTrue(contains_original(onward_files),
                        'Provenance original ZIP/mapping vanished after a successful logical receive and re-export; imports entries=' + str([n for n in onward_files if n.startswith('imports/')]))
