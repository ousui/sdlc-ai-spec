"""Copy snapshots and recovery bind equivalent names to one actual destination."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import shutil
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


NAME = 'specs/001-one/caf\u00e9.md'
ALIASES = ('specs/001-one/cafe\u0301.md', 'specs/001-one/CAF\u00c9.MD', 'specs/001-one/CAFE\u0301.MD')


class CopyIdentityTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        probe = self.f.base / 'caf\u00e9'
        probe.write_text('probe')
        insensitive = (self.f.base / 'CAFE\u0301').exists()
        probe.unlink()
        if not insensitive:
            self.skipTest('Requires case-insensitive and normalization-insensitive lookup')
        self.f.init(self.f.a, '--mode', 'local')
        self.f.feature(self.f.main)
        self.f.feature(self.f.a)

    def plan(self, kind, alias, content='candidate'):
        project, source = (self.f.a, self.f.main) if kind == 'import' else (self.f.main, self.f.a)
        target = project / '.sdlc' / NAME
        other = source / '.sdlc' / alias
        target.unlink(missing_ok=True)
        other.unlink(missing_ok=True)
        target.write_text('original')
        other.write_text(content)
        plan = self.f.prepare(project, kind=kind, sources=[source / '.sdlc'] if kind == 'collect' else [],
                              features=['001-one'])
        return project, source, target, plan

    def manifest(self, plan):
        path = Path(plan['transaction']) / 'manifest.json'
        return path, json.loads(path.read_text())

    def interrupted(self, plan, name, content, legacy=False):
        path, manifest = self.manifest(plan)
        if manifest['status'] == 'prepared':
            target = Path(manifest['target']) / (manifest.get('copy_targets') or {}).get(name, name)
            manifest['published'] = {name: storage.changes.publish_data(
                target, content.encode(), target.read_bytes() if target.exists() else None)}
        manifest.update(status='applying', after={name: base64.b64encode(content.encode()).decode()})
        if legacy:
            manifest.pop('copy_targets', None)
        path.write_text(json.dumps(manifest))

    def choose(self, plan, name, source):
        proposal = Path(plan['proposal'])
        data = json.loads(proposal.read_text())
        data[name] = {'action': 'copy', 'source': str(source / '.sdlc')}
        proposal.write_text(json.dumps(data))

    def test_equivalent_existing_names_with_identical_bytes_are_noop_in_both_directions(self):
        for kind in ('import', 'collect'):
            for alias in ALIASES:
                with self.subTest(kind=kind, alias=alias):
                    project, source, target, plan = self.plan(kind, alias, 'original')
                    before = target.read_bytes(), target.stat().st_mtime_ns
                    self.assertEqual(plan['files'], [])
                    self.assertEqual(plan['changed_sources'], [])
                    self.assertEqual(self.f.apply(plan, project)['written'], [])
                    self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                    self.assertIn(target.name, [p.name for p in target.parent.iterdir()])

    def test_equivalent_existing_names_have_one_conflict_and_preserve_the_original_snapshot(self):
        for kind in ('import', 'collect'):
            for alias in ALIASES:
                with self.subTest(kind=kind, alias=alias):
                    project, source, target, plan = self.plan(kind, alias)
                    self.assertEqual(plan['unresolved'], [alias])
                    _, manifest = self.manifest(plan)
                    self.assertEqual(manifest['copy_targets'][alias], NAME)
                    self.assertEqual(base64.b64decode(manifest['before'][NAME]), b'original')
                    self.f.apply(plan, project, ok=False)
                    self.assertEqual(target.read_text(), 'original')
                    self.choose(plan, alias, source)
                    self.f.apply(plan, project)
                    self.assertEqual(target.read_text(), 'candidate')
                    self.assertIn('caf\u00e9.md', [p.name for p in target.parent.iterdir()])

    def test_replacing_a_conflict_with_original_bytes_preserves_noop(self):
        for kind in ('import', 'collect'):
            with self.subTest(kind=kind):
                project, _, target, plan = self.plan(kind, ALIASES[0])
                before = target.read_bytes(), target.stat().st_mtime_ns
                self.f.replace(plan, ALIASES[0], 'original')
                self.assertEqual(self.f.apply(plan, project)['written'], [])
                self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)

    def test_publication_failure_before_write_cannot_delete_an_equivalent_existing_file(self):
        for kind in ('import', 'collect'):
            with self.subTest(kind=kind):
                project, source, target, plan = self.plan(kind, ALIASES[0])
                self.choose(plan, ALIASES[0], source)
                with mock.patch.object(storage.changes, 'publish_data', side_effect=OSError('publication failure')):
                    with self.assertRaisesRegex(OSError, 'publication failure'):
                        storage.changes.apply(project, Path(plan['transaction']))
                self.assertEqual(target.read_text(), 'original')
                self.assertEqual(self.manifest(plan)[1]['status'], 'recovered')

    def test_recovery_restores_original_bytes_and_rejects_later_edits(self):
        for kind in ('import', 'collect'):
            for alias in ALIASES:
                with self.subTest(kind=kind, alias=alias):
                    project, _, target, plan = self.plan(kind, alias)
                    self.interrupted(plan, alias, 'partial')
                    target.write_text('later edit')
                    before = target.read_bytes(), target.stat().st_mtime_ns
                    self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project, ok=False)
                    self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                    target.write_text('partial')
                    self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project, ok=False)
                    target.write_text('original')
                    self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)
                    self.assertEqual(target.read_text(), 'original')
                    self.assertIn('caf\u00e9.md', [p.name for p in target.parent.iterdir()])

    def multi_source(self, same=False):
        self.f.init(self.f.b, '--mode', 'local')
        self.f.feature(self.f.b)
        # Existing metadata establishes normalization lookup for missing names.
        (self.f.main / '.sdlc/specs/001-one/caf\u00e9-probe').write_text('lookup evidence')
        (self.f.a / '.sdlc' / NAME).write_text('A')
        (self.f.b / '.sdlc' / ALIASES[0]).write_text('A' if same else 'B')
        return self.f.prepare(self.f.main, kind='collect', sources=[self.f.a / '.sdlc', self.f.b / '.sdlc'],
                              features=['001-one'])

    def test_multiple_sources_with_identical_equivalent_names_create_one_file(self):
        plan = self.multi_source(same=True)
        self.assertEqual(len(plan['files']), 1)
        self.assertEqual(plan['unresolved'], [])
        self.assertTrue(plan['multiple_sources'])
        result = self.f.apply(plan)
        self.assertEqual(len(result['written']), 1)
        self.assertEqual((self.f.main / '.sdlc' / NAME).read_text(), 'A')

    def test_multiple_sources_with_conflicting_equivalent_names_require_one_decision(self):
        plan = self.multi_source()
        self.assertEqual(len(plan['unresolved']), 1)
        name = plan['unresolved'][0]
        self.assertEqual(len(self.manifest(plan)[1]['variants'][name]), 2)
        self.f.apply(plan, ok=False)
        self.assertFalse((self.f.main / '.sdlc' / NAME).exists())
        self.choose(plan, name, self.f.b)
        self.f.apply(plan)
        self.assertEqual((self.f.main / '.sdlc' / NAME).read_text(), 'B')
        self.assertEqual((self.f.a / '.sdlc' / NAME).read_text(), 'A')

    def test_missing_equivalent_target_recovery_removes_only_the_new_file(self):
        plan = self.multi_source(same=True)
        name = plan['files'][0]
        target = self.f.main / '.sdlc' / NAME
        self.interrupted(plan, name, 'partial')
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'])
        self.assertFalse(target.exists())
        self.assertEqual((self.f.a / '.sdlc' / NAME).read_text(), 'A')

    def test_equivalent_existing_and_planned_parent_directories_use_one_spelling(self):
        self.f.init(self.f.b, '--mode', 'local')
        self.f.feature(self.f.b)
        for existing in (False, True):
            with self.subTest(existing=existing):
                component = 'existing' if existing else 'missing'
                if existing:
                    (self.f.main / '.sdlc/specs/001-one' / component).mkdir()
                for source, spelling, filename in ((self.f.a, component.upper(), 'a.md'),
                                                   (self.f.b, component, 'b.md')):
                    path = source / '.sdlc/specs/001-one' / spelling / filename
                    path.parent.mkdir()
                    path.write_text(filename)
                plan = self.f.prepare(sources=[self.f.a / '.sdlc', self.f.b / '.sdlc'], features=['001-one'])
                self.f.apply(plan)
                for filename in ('a.md', 'b.md'):
                    self.assertEqual((self.f.main / '.sdlc/specs/001-one' / component / filename).read_text(), filename)

    def test_a_single_source_cannot_offer_two_different_files_for_one_destination(self):
        source = self.f.a / '.sdlc'
        snapshot = storage.changes.snapshot
        def colliding(root, paths=None):
            result = snapshot(root, paths)
            if root == source:
                result.update({NAME: base64.b64encode(b'A').decode(), ALIASES[0]: base64.b64encode(b'B').decode()})
            return result
        (self.f.main / '.sdlc/specs/001-one/caf\u00e9-probe').write_text('lookup evidence')
        before = storage.files(self.f.main / '.sdlc')
        with mock.patch.object(storage.changes, 'snapshot', side_effect=colliding):
            with self.assertRaisesRegex(ValueError, 'multiple files'):
                storage.changes.prepare(self.f.main, 'collect', [source], ['001-one'], [])
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)

    def test_file_directory_collisions_stop_before_any_copy_is_published(self):
        self.f.init(self.f.b, '--mode', 'local')
        self.f.feature(self.f.b)
        (self.f.a / '.sdlc/specs/001-one/contracts').write_text('file')
        directory = self.f.b / '.sdlc/specs/001-one/CONTRACTS'
        directory.mkdir()
        (directory / 'api.md').write_text('nested')
        before = storage.files(self.f.main / '.sdlc')
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--feature', '001-one',
                     '--source', str(self.f.a / '.sdlc'), '--source', str(self.f.b / '.sdlc'), ok=False)
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)

    def test_ambiguous_legacy_copy_transactions_cannot_apply_or_delete_during_recovery(self):
        for kind in ('import', 'collect'):
            for action in ('apply', 'recover'):
                with self.subTest(kind=kind, action=action):
                    project, source, target, plan = self.plan(kind, ALIASES[0])
                    path, manifest = self.manifest(plan)
                    manifest.pop('copy_targets', None)
                    manifest['variants'][ALIASES[0]] = {str(source / '.sdlc'): base64.b64encode(b'original').decode()}
                    if action == 'recover':
                        manifest.update(status='applying', after={ALIASES[0]: base64.b64encode(b'original').decode()})
                    path.write_text(json.dumps(manifest))
                    self.choose(plan, ALIASES[0], source)
                    before = target.read_bytes(), target.stat().st_mtime_ns
                    self.f.runpy('store_changes.py', action, '--transaction', plan['transaction'], project=project, ok=False)
                    self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                    self.assertEqual(self.manifest(plan)[1]['status'], 'applying' if action == 'recover' else 'prepared')

    def test_unambiguous_legacy_copy_transactions_still_apply_and_recover(self):
        project, source, target, plan = self.plan('import', NAME)
        path, manifest = self.manifest(plan)
        manifest.pop('copy_targets', None)
        path.write_text(json.dumps(manifest))
        self.choose(plan, NAME, source)
        self.f.apply(plan, project)
        self.assertEqual(target.read_text(), 'candidate')
        self.interrupted(plan, NAME, 'candidate', legacy=True)
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)
        self.assertEqual(target.read_text(), 'original')

    def test_copy_source_spelling_change_after_prepare_is_still_stale(self):
        project, source, target, plan = self.plan('import', NAME)
        self.choose(plan, NAME, source)
        original = source / '.sdlc' / NAME
        original.rename(source / '.sdlc' / ALIASES[0])
        self.f.apply(plan, project, ok=False)
        self.assertEqual(target.read_text(), 'original')

    def test_partial_publication_rolls_back_equivalent_existing_target_without_deleting_it(self):
        for kind in ('import', 'collect'):
            with self.subTest(kind=kind):
                project, source = (self.f.a, self.f.main) if kind == 'import' else (self.f.main, self.f.a)
                target = project / '.sdlc' / NAME
                target.unlink(missing_ok=True)
                target.write_text('original')
                source_file = source / '.sdlc' / ALIASES[0]
                source_file.unlink(missing_ok=True)
                source_file.write_text('candidate')
                second = project / '.sdlc/specs/001-one/z.md'
                second.unlink(missing_ok=True)
                (source / '.sdlc/specs/001-one/z.md').write_text('new file')
                plan = self.f.prepare(project, kind=kind, sources=[source / '.sdlc'] if kind == 'collect' else [],
                                      features=['001-one'])
                self.choose(plan, ALIASES[0], source)
                publish = storage.changes.publish_data
                called = []
                def fail_second(path, data, old):
                    called.append(path)
                    if path == second:
                        raise OSError('second publication failure')
                    return publish(path, data, old)
                with mock.patch.object(storage.changes, 'publish_data', side_effect=fail_second):
                    with self.assertRaisesRegex(OSError, 'second publication failure'):
                        storage.changes.apply(project, Path(plan['transaction']))
                self.assertEqual(called, [target, second])
                self.assertEqual(target.read_text(), 'original')
                self.assertFalse(second.exists())
                self.assertEqual(self.manifest(plan)[1]['status'], 'recovered')

    def test_equivalent_import_recovery_does_not_need_authority_online(self):
        project, source, target, plan = self.plan('import', ALIASES[0])
        self.interrupted(plan, ALIASES[0], 'partial')
        shutil.rmtree(source / '.sdlc')
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)
        self.assertEqual(target.read_text(), 'original')

    def test_normalized_new_name_after_publication_is_verified_and_remains_noop(self):
        source = self.f.a / '.sdlc' / NAME
        source.write_text('new file')
        target = self.f.main / '.sdlc' / NAME
        normalized = self.f.main / '.sdlc' / ALIASES[0]
        plan = self.f.prepare(sources=[self.f.a / '.sdlc'], features=['001-one'])
        publish = storage.changes.publish_data
        def normalize_after_creation(path, data, old):
            identity = publish(path, data, old)
            if path == target:
                path.rename(normalized)
            return identity
        with mock.patch.object(storage.changes, 'publish_data', side_effect=normalize_after_creation):
            self.assertEqual(storage.changes.apply(self.f.main, Path(plan['transaction']))['status'], 'applied')
        self.assertIn(normalized.name, [p.name for p in target.parent.iterdir()])
        before = target.read_bytes(), target.stat().st_mtime_ns
        again = self.f.prepare(sources=[self.f.a / '.sdlc'], features=['001-one'])
        self.assertEqual(again['files'], [])
        self.assertEqual(self.f.apply(again)['written'], [])
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)

    def test_missing_aliases_stop_when_lookup_rules_cannot_be_observed(self):
        target = self.f.main / '.sdlc'
        before = storage.files(target)
        with self.assertRaisesRegex(ValueError, 'normalization'):
            storage.changes.copy_targets(target, [NAME, ALIASES[0]])
        self.assertEqual(storage.files(target), before)

    def test_equivalent_knowledge_directory_copies_provenance_and_recovers(self):
        for kind in ('import', 'collect'):
            with self.subTest(kind=kind):
                project, source = (self.f.a, self.f.main) if kind == 'import' else (self.f.main, self.f.a)
                memory = project / '.sdlc/memory'
                original = storage.files(source / '.sdlc/memory')
                for name in ('constitution.md', '.constitution-template.json', 'long-term.md'):
                    (memory / name).unlink()
                memory.rename(memory.with_name('MEMORY'))
                plan = self.f.prepare(project, kind=kind,
                                      sources=[source / '.sdlc'] if kind == 'collect' else [])
                self.f.apply(plan, project)
                self.assertEqual(storage.files(memory), original)
                self.assertIn('MEMORY', [path.name for path in memory.parent.iterdir()])
                path, manifest = self.manifest(plan)
                manifest['status'] = 'applying'
                path.write_text(json.dumps(manifest))
                self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)
                self.assertEqual(storage.files(memory), {})
                again = self.f.prepare(project, kind=kind,
                                       sources=[source / '.sdlc'] if kind == 'collect' else [])
                self.f.apply(again, project)
                before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in memory.iterdir()}
                noop = self.f.prepare(project, kind=kind,
                                      sources=[source / '.sdlc'] if kind == 'collect' else [])
                self.assertEqual(self.f.apply(noop, project)['written'], [])
                self.assertEqual({p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in memory.iterdir()}, before)
                memory.with_name('MEMORY').rename(memory)

    def test_sensitive_lookup_rules_keep_distinct_missing_destinations(self):
        target = self.f.main / '.sdlc'
        with mock.patch.object(storage.store, 'case_sensitive', return_value=True), \
                mock.patch.object(storage.store, 'normalization_sensitive', return_value=True):
            names = [NAME, *ALIASES]
            self.assertEqual(storage.changes.copy_targets(target, names), {name: name for name in names})


if __name__ == '__main__':
    unittest.main()
