"""Native case-sensitive directories keep distinct files and conservative rules."""
import json
import os
from pathlib import Path
import tempfile
import unittest

try:
    from tests import test_storage_target_lookup as lookup
except ImportError:
    import test_storage_target_lookup as lookup

storage = lookup.storage


class SensitiveFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.case = lookup.TargetLookupTests('runTest')
        self.case.setUp()
        with tempfile.TemporaryDirectory(prefix='sdlc-case-capability-') as folder:
            probe = Path(folder) / 'case-sensitive-probe'
            probe.write_bytes(b'capability')
            sensitive = not probe.with_name(probe.name.upper()).exists()
        if not sensitive:
            self.skipTest('Requires a native case-sensitive filesystem')

    def test_distinct_existing_files_survive_edit_import_collect_and_offline_recovery(self):
        for kind in ('edit', 'import', 'collect'):
            with self.subTest(kind=kind), self.case.helper.fixture() as f:
                project, source, sources, name, target = self.case.setup_case(f, kind, existing=True)
                alternate = target.with_name(target.name.upper())
                alternate.write_bytes(b'Distinct existing uppercase file')
                self.assertFalse(os.path.samefile(target, alternate))
                names = [name, str(Path(name).with_name(alternate.name))]
                if source:
                    (source / names[1]).write_bytes(b'Uppercase source candidate')
                before = self.case.helper.identities(project / '.sdlc')
                if kind == 'edit' and storage.store.sys.platform != 'darwin':
                    # Different current inodes do not prove namespace rules.
                    with self.assertRaisesRegex(ValueError, 'Cannot verify case-distinct'):
                        storage.changes.prepare(project, kind, sources, [], names)
                    self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                    continue
                plan = storage.changes.prepare(project, kind, sources,
                    ['001-one'] if kind != 'edit' else [], names if kind == 'edit' else [])
                folder = Path(plan['transaction'])
                Path(plan['proposal']).write_text(json.dumps({n: {'action': 'replace', 'text': 'Candidate-' + str(i)} for i,n in enumerate(names)}))
                storage.changes.apply(project, folder)
                self.assertEqual(target.read_bytes(), b'Candidate-0')
                self.assertEqual(alternate.read_bytes(), b'Candidate-1')
                manifest = json.loads((folder / 'manifest.json').read_text())
                manifest['status'] = 'applying'
                (folder / 'manifest.json').write_text(json.dumps(manifest))
                with self.case.offline(source):
                    storage.changes.recover(project, folder)
                self.assertEqual(self.case.helper.identities(project / '.sdlc').keys(), before.keys())
                self.assertEqual(target.read_bytes(), b'Existing protected data')
                self.assertEqual(alternate.read_bytes(), b'Distinct existing uppercase file')

    def test_non_equivalent_knowledge_name_is_not_silently_treated_as_canonical(self):
        with self.case.helper.fixture() as f:
            source = f.main / '.sdlc'
            alternate = source / 'memory/CONSTITUTION.MD'
            alternate.write_bytes(b'Case-distinct document, not canonical knowledge')
            raw = storage.changes.source_snapshot(source)
            self.assertIn('memory/CONSTITUTION.MD', raw)
            if storage.store.sys.platform != 'darwin':
                with self.assertRaisesRegex(ValueError, 'Cannot verify case-distinct'):
                    storage.changes.source_files(source, raw, [])
            else:
                selected = storage.changes.source_files(source, raw, [])
                self.assertEqual(selected['memory/constitution.md'], raw['memory/constitution.md'])
                self.assertNotIn('memory/CONSTITUTION.MD', selected)
                self.case.helper.init(f)
                self.assertEqual((f.a / '.sdlc/memory/constitution.md').read_bytes(), (source / 'memory/constitution.md').read_bytes())
                self.assertFalse((f.a / '.sdlc/memory/CONSTITUTION.MD').exists())


if __name__ == '__main__':
    unittest.main()
