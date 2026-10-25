"""Knowledge aliases are recognized at sources without folding snapshot names."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
    from tests import test_storage_init_retry as retry
except ImportError:
    import test_storage as storage
    import test_storage_init_retry as retry


class KnowledgeSourceTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        probe = self.f.base / 'Probe'
        probe.touch()
        insensitive = (self.f.base / 'PROBE').exists()
        probe.unlink()
        if not insensitive:
            self.skipTest('Requires case-insensitive lookup')

    def alias(self, source, variant):
        memory = source / '.sdlc/memory'
        if variant == 'directory':
            memory.rename(memory.with_name('MEMORY'))
        else:
            for name in ('constitution.md', 'long-term.md', '.constitution-template.json'):
                path = memory / name
                if path.exists():
                    path.rename(path.with_name(name.upper()))
        return memory

    def args(self):
        return SimpleNamespace(project=self.f.a, discover=False, mode='local', seed='knowledge',
                               feature=[], feature_numbering=None, dry_run=False)

    def test_equivalent_sources_produce_conflicts_preserve_raw_snapshots_and_keep_noop(self):
        self.f.init(self.f.a, '--mode', 'local')
        for kind in ('import', 'collect'):
            for variant in ('directory', 'files'):
                with self.subTest(kind=kind, variant=variant):
                    project, source = (self.f.a, self.f.main) if kind == 'import' else (self.f.main, self.f.a)
                    memory = source / '.sdlc/memory'
                    for name in ('constitution.md', 'long-term.md'):
                        (memory / name).write_text(kind + variant + name)
                    self.alias(source, variant)
                    before = storage.files(source / '.sdlc')
                    plan = self.f.prepare(project, kind=kind, sources=[source / '.sdlc'] if kind == 'collect' else [])
                    self.assertEqual(set(plan['unresolved']), set(storage.store.KNOWLEDGE))
                    manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
                    self.assertEqual(set(manifest['sources'][str(source / '.sdlc')]), set(before))
                    self.f.apply(plan, project, ok=False)
                    proposal = {name: {'action': 'copy', 'source': str(source / '.sdlc')} for name in plan['files']}
                    Path(plan['proposal']).write_text(json.dumps(proposal))
                    self.f.apply(plan, project)
                    target = project / '.sdlc/memory'
                    for name in ('constitution.md', 'long-term.md'):
                        self.assertEqual((target / name).read_bytes(), (memory / name).read_bytes())
                    actual = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}
                    again = self.f.prepare(project, kind=kind, sources=[source / '.sdlc'] if kind == 'collect' else [])
                    self.assertEqual(again['files'], [])
                    self.assertEqual(again['changed_sources'], [])
                    self.assertEqual(self.f.apply(again, project)['written'], [])
                    self.assertEqual({p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}, actual)
                    self.assertEqual(storage.files(source / '.sdlc'), before)

    def new_constitution(self, kind):
        self.f.init(self.f.a, '--mode', 'local')
        project, origin = (self.f.main, self.f.a) if kind == 'collect' else (self.f.a, self.f.main)
        self.alias(origin, 'directory')
        self.alias(origin, 'files')
        source = origin / '.sdlc'
        target = project / '.sdlc/memory'
        before_source = storage.files(source)
        for name in ('constitution.md', '.constitution-template.json', 'long-term.md'):
            (target / name).unlink()
        plan = self.f.prepare(project, kind=kind, sources=[source] if kind == 'collect' else [])
        self.f.apply(plan, project)
        for name in ('constitution.md', '.constitution-template.json', 'long-term.md'):
            self.assertEqual((target / name).read_bytes(), (source / 'memory' / name).read_bytes())
        self.assertEqual(storage.files(source), before_source)
        path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['status'] = 'applying'
        path.write_text(json.dumps(manifest))
        shutil.rmtree(source)
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)
        self.assertEqual(list(target.iterdir()), [])

    def test_collected_equivalent_source_provenance_and_recovery(self):
        self.new_constitution('collect')

    def test_imported_equivalent_source_provenance_and_recovery(self):
        self.new_constitution('import')

    def test_multiple_equivalent_knowledge_sources_require_one_explicit_conflict_decision(self):
        for project, variant in ((self.f.a, 'directory'), (self.f.b, 'files')):
            self.f.init(project, '--mode', 'local')
            (project / '.sdlc/memory/constitution.md').write_text(project.name)
            self.alias(project, variant)
        before = storage.files(self.f.main / '.sdlc')
        plan = self.f.prepare(sources=[self.f.a / '.sdlc', self.f.b / '.sdlc'])
        self.assertEqual(plan['files'], ['memory/constitution.md'])
        self.assertEqual(plan['unresolved'], plan['files'])
        self.assertTrue(plan['multiple_sources'])
        self.f.apply(plan, ok=False)
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)
        Path(plan['proposal']).write_text(json.dumps({'memory/constitution.md':
                                                    {'action': 'copy', 'source': str(self.f.b / '.sdlc')}}))
        self.f.apply(plan)
        self.assertEqual((self.f.main / '.sdlc/memory/constitution.md').read_text(), self.f.b.name)
        self.assertEqual((self.f.main / '.sdlc/memory/.constitution-template.json').read_bytes(),
                         before['memory/.constitution-template.json'])

    def test_first_init_imports_equivalent_knowledge_and_history_without_selecting_requirements(self):
        self.f.feature(self.f.main)
        self.alias(self.f.main, 'directory')
        self.alias(self.f.main, 'files')
        before = storage.files(self.f.main / '.sdlc')
        result = self.f.init(self.f.a, '--mode', 'local')
        target = self.f.a / '.sdlc'
        for name in (*storage.store.KNOWLEDGE, 'memory/.constitution-template.json'):
            self.assertEqual((target / name).read_bytes(), (self.f.main / '.sdlc' / name).read_bytes())
        self.assertEqual(result['constitution_source'], 'authority-import')
        self.assertEqual(result['constitution_provenance'], 'imported')
        self.assertFalse((target / 'feature.json').exists())
        self.assertEqual(list((target / 'specs').iterdir()), [])
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)
        state = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in target.rglob('*') if p.is_file()}
        self.assertEqual(self.f.init(self.f.a)['status'], 'unchanged')
        self.assertEqual({str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in target.rglob('*') if p.is_file()}, state)

    def test_interrupted_init_keeps_canonical_seed_intent_and_preserves_intervening_files(self):
        self.alias(self.f.main, 'directory')
        self.alias(self.f.main, 'files')
        memory = self.f.main / '.sdlc/memory'
        expected = (memory / 'long-term.md').read_bytes()
        state = self.f.a / '.sdlc'
        publish = retry.initializer.publish
        def interrupt(path, data, old):
            if path == state / 'README.md':
                raise OSError('interrupted init')
            return publish(path, data, old)
        with mock.patch.dict(os.environ, self.f.env, clear=True), \
                mock.patch.object(retry.initializer, 'publish', side_effect=interrupt):
            with self.assertRaisesRegex(OSError, 'interrupted init'):
                retry.initializer.initialize_selected(self.args())
        pending = json.loads((state / '.init-pending.json').read_text())
        self.assertEqual(set(pending['seeds']), {*storage.store.KNOWLEDGE, 'memory/.constitution-template.json'})
        (state / 'memory/constitution.md').write_text('local decision')
        (memory / 'long-term.md').write_text('changed authority')
        result = self.f.init(self.f.a, '--mode', 'local')
        self.assertEqual((state / 'memory/constitution.md').read_text(), 'local decision')
        self.assertEqual((state / 'memory/long-term.md').read_bytes(), expected)
        self.assertNotIn('memory/constitution.md', result['imported'])
        self.assertFalse((state / '.init-pending.json').exists())

    def test_source_spelling_change_after_prepare_remains_stale(self):
        self.f.init(self.f.a, '--mode', 'local')
        (self.f.a / '.sdlc/memory/long-term.md').write_text('candidate')
        plan = self.f.prepare(sources=[self.f.a / '.sdlc'])
        self.f.replace(plan, 'memory/long-term.md', 'candidate')
        self.alias(self.f.a, 'directory')
        before = storage.files(self.f.main / '.sdlc')
        self.assertIn('Source changed', self.f.apply(plan, ok=False).stderr)
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)


class KnowledgeRoleTests(unittest.TestCase):
    def test_scope_does_not_fold_unrelated_or_case_sensitive_names(self):
        source = Path('/synthetic-source')
        data = {'MEMORY/CONSTITUTION.MD': 'alias', 'memory/constitution.md': 'canonical',
                'memory/private.md': 'private', 'specs/001-X/spec.md': 'explicit',
                'SPECS/001-x/spec.md': 'unselected'}
        with mock.patch.object(storage.changes, 'same_path', side_effect=lambda a, b, *, strict=False: a == b):
            self.assertEqual(storage.changes.source_files(source, data, ['001-X']),
                             {'memory/constitution.md': 'canonical', 'specs/001-X/spec.md': 'explicit'})


if __name__ == '__main__':
    unittest.main()
