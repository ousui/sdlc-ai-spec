"""Interrupted local INIT retains its explicit import intent on disposable worktrees."""
from __future__ import annotations

import importlib.util
from contextlib import contextmanager
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from tests import test_storage
except ImportError:
    import test_storage

spec = importlib.util.spec_from_file_location('sdlc_retry_initializer', test_storage.SCRIPTS / 'init_project.py')
initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)


class InitRetryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_storage.StorageTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.feature = self.fixture.feature(self.fixture.main)
        self.args = SimpleNamespace(project=self.fixture.a, discover=False, mode='local',
                                    seed='knowledge', feature=['001-one'], feature_numbering=None, dry_run=False)
        self.state = self.fixture.a / '.sdlc'
        self.pending = self.state / '.init-pending.json'
        self.env = mock.patch.dict(os.environ, self.fixture.env, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_init(self, **overrides):
        return initializer.initialize_selected(SimpleNamespace(**(vars(self.args) | overrides)))

    def interrupt(self, relative='README.md'):
        real_publish = initializer.publish
        def interrupted(path, data, expected):
            if path == self.state / relative:
                raise OSError('synthetic publication failure')
            return real_publish(path, data, expected)
        with mock.patch.object(initializer, 'publish', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'synthetic publication failure'):
                self.run_init()

    def assert_imported(self, result):
        for name in ('memory/constitution.md', 'memory/long-term.md', 'specs/001-one/spec.md'):
            self.assertEqual((self.state / name).read_bytes(), (self.fixture.main / '.sdlc' / name).read_bytes())
            self.assertIn(name, result['imported'] + result['preserved_imports'])
        provenance = 'memory/.constitution-template.json'
        if (self.state / provenance).exists():
            self.assertEqual((self.state / provenance).read_bytes(), (self.fixture.main / '.sdlc' / provenance).read_bytes())
        else:
            self.assertTrue(any('origin cannot be asserted' in warning for warning in result['warnings']))
        self.assertFalse(self.pending.exists())
        self.assertFalse((self.state / 'feature.json').exists())

    def test_failure_before_intent_publication_leaves_no_false_local_store(self):
        before = test_storage.files(self.fixture.main)
        with mock.patch.object(initializer, 'publish', side_effect=OSError('first publication failed')):
            with self.assertRaisesRegex(OSError, 'first publication failed'):
                self.run_init()
        self.assertFalse(self.state.exists())
        self.assert_imported(self.run_init())
        self.assertEqual(test_storage.files(self.fixture.main), before)

    def test_first_and_partial_business_publication_failures_resume_all_selected_data(self):
        before = test_storage.files(self.fixture.main)
        for index, relative in enumerate(('init-options.json', 'memory/constitution.md', 'README.md',
                                          'memory/long-term.md', 'specs/001-one/spec.md')):
            with self.subTest(relative=relative):
                project = self.fixture.base / ('retry-' + str(index))
                self.fixture.git('worktree', 'add', '-q', '-b', 'retry-' + str(index), str(project))
                self.args.project = project
                self.state = project / '.sdlc'
                self.pending = self.state / '.init-pending.json'
                self.interrupt(relative)
                self.assertTrue(self.pending.is_file())
                self.assert_imported(self.run_init(mode='auto'))
        self.assertEqual(test_storage.files(self.fixture.main), before)

    def test_retry_uses_saved_source_bytes_and_preserves_intervening_user_files(self):
        self.interrupt()
        old_memory = (self.fixture.main / '.sdlc/memory/long-term.md').read_bytes()
        old_spec = (self.feature / 'spec.md').read_bytes()
        (self.fixture.main / '.sdlc/memory/long-term.md').write_text('new authority memory')
        (self.feature / 'spec.md').write_text('new authority feature')
        (self.state / 'memory/constitution.md').write_text('user-edited local constitution')
        before = test_storage.files(self.fixture.main)
        result = self.run_init()
        self.assertEqual((self.state / 'memory/long-term.md').read_bytes(), old_memory)
        self.assertEqual((self.state / 'specs/001-one/spec.md').read_bytes(), old_spec)
        self.assertEqual((self.state / 'memory/constitution.md').read_text(), 'user-edited local constitution')
        self.assertIn('.sdlc/memory/constitution.md', result['preserved'])
        self.assertNotIn('memory/constitution.md', result['imported'])
        self.assertEqual(result['constitution_source'], 'preserved')
        self.assertEqual(result['constitution_provenance'], 'not_recorded')
        self.assertFalse((self.state / 'memory/.constitution-template.json').exists())
        self.assertEqual(test_storage.files(self.fixture.main), before)
        self.assertFalse(self.pending.exists())

    def test_changed_choices_and_authority_require_explicit_inspection(self):
        self.interrupt()
        before = test_storage.files(self.state)
        for overrides in ({'feature': []}, {'seed': 'none', 'feature': []}, {'feature_numbering': 'timestamp'}):
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, 'Interrupted initialization'):
                self.run_init(**overrides)
            self.assertEqual(test_storage.files(self.state), before)
        alternate = self.fixture.base / 'new authority'
        alternate.mkdir()
        (self.fixture.main / '.sdlc/store.json').write_text(json.dumps({'schema': 1, 'authority': str(alternate), 'sources': []}))
        with self.assertRaisesRegex(ValueError, 'Interrupted initialization'):
            self.run_init()
        self.assertEqual(test_storage.files(self.state), before)
        self.assertEqual(list(alternate.iterdir()), [])

    def test_dry_run_preserves_pending_intent_and_completed_store_does_not_reimport(self):
        self.interrupt()
        before = test_storage.files(self.state)
        result = self.run_init(dry_run=True)
        self.assertTrue(result['dry_run'])
        self.assertEqual(test_storage.files(self.state), before)
        self.assert_imported(self.run_init())
        (self.state / 'memory/long-term.md').unlink()
        (self.state / 'specs/001-one/spec.md').unlink()
        self.assertEqual(self.run_init()['imported'], [])
        self.assertFalse((self.state / 'memory/long-term.md').exists())
        self.assertFalse((self.state / 'specs/001-one/spec.md').exists())

    def test_failed_marker_cleanup_is_retryable_without_republishing_business_files(self):
        real_unlink = Path.unlink
        def interrupted_unlink(path, *args, **kwargs):
            if path == self.pending:
                raise OSError('synthetic intent cleanup failure')
            return real_unlink(path, *args, **kwargs)
        with mock.patch.object(Path, 'unlink', interrupted_unlink):
            with self.assertRaisesRegex(OSError, 'intent cleanup failure'):
                self.run_init()
        before = {str(p.relative_to(self.state)): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.state.rglob('*') if p.is_file() and p != self.pending}
        self.assert_imported(self.run_init())
        after = {str(p.relative_to(self.state)): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.state.rglob('*') if p.is_file()}
        self.assertEqual(after, before)

    def test_failed_intent_write_never_removes_concurrently_created_files(self):
        def interrupted_publish(path, data, expected):
            self.state.mkdir()
            (self.state / 'user-note').write_text('keep')
            raise OSError('synthetic intent failure')
        with mock.patch.object(initializer, 'publish', interrupted_publish):
            with self.assertRaisesRegex(OSError, 'synthetic intent failure'):
                self.run_init()
        self.assertEqual((self.state / 'user-note').read_text(), 'keep')

    def test_failed_intent_write_does_not_remove_replacement_empty_directory(self):
        replacement = self.fixture.a / 'original-empty-state'
        real_publish = initializer.publish
        def interrupted_publish(path, data, expected):
            if path != self.state / 'init-options.json':
                return real_publish(path, data, expected)
            self.state.rename(replacement)
            self.state.mkdir()
            (replacement / '.write-lock').rename(self.state / '.write-lock')
            raise OSError('synthetic intent failure')
        with mock.patch.object(initializer, 'publish', interrupted_publish):
            with self.assertRaisesRegex(OSError, 'synthetic intent failure'):
                self.run_init()
        self.assertTrue(self.state.is_dir())
        self.assertEqual(list(self.state.iterdir()), [])
        self.assertTrue((replacement / '.init-pending.json').is_file())

    def test_authority_binding_is_rechecked_under_target_lock(self):
        alternate = self.fixture.base / 'changed authority'
        alternate.mkdir()
        original_lock = test_storage.store.write_lock
        registry = self.fixture.main / '.sdlc/store.json'
        original_registry = registry.read_bytes() if registry.exists() else None
        @contextmanager
        def changed_binding(state):
            with original_lock(state) as token:
                (self.fixture.main / '.sdlc/store.json').write_text(json.dumps({
                    'schema': 1, 'authority': str(alternate), 'sources': []}))
                yield token
        with mock.patch.object(test_storage.store, 'write_lock', changed_binding):
            with self.assertRaisesRegex(ValueError, 'Storage binding changed'):
                self.run_init()
        # The store became visible together with its intent, before acquiring the
        # lock. Keep that intent, but publish no business data under a new binding.
        self.assertTrue(self.pending.is_file())
        self.assertFalse((self.state / 'init-options.json').exists())
        self.assertEqual(list(alternate.iterdir()), [])
        if original_registry is None:
            registry.unlink()
        else:
            registry.write_bytes(original_registry)
        self.assert_imported(self.run_init())

    def test_concurrent_completed_local_store_is_never_seeded_by_earlier_preview(self):
        original_snapshot = test_storage.changes.snapshot
        count = 0
        def snapshot_then_initialize(root, *args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                self.run_init(seed='none', feature=[])
            return original_snapshot(root, *args, **kwargs)
        with mock.patch.object(test_storage.changes, 'snapshot', snapshot_then_initialize):
            with self.assertRaises(FileExistsError):
                self.run_init()
        self.assertTrue((self.state / 'init-options.json').exists())
        self.assertFalse((self.state / 'memory/long-term.md').exists())
        self.assertFalse((self.state / 'specs/001-one').exists())
        self.assertFalse(self.pending.exists())

    def test_staged_intent_rechecks_source_and_target_roles_before_becoming_visible(self):
        real_publish = initializer.publish
        control = self.fixture.main / '.sdlc/workspaces'
        control.mkdir()
        source = self.fixture.main / '.sdlc/memory/long-term.md'
        original = source.read_bytes()
        real_scandir = os.scandir
        for change in ('source', 'target-role', 'unreadable-source'):
            with self.subTest(change=change):
                staged = False
                def scandir(path):
                    if staged and change == 'unreadable-source':
                        if isinstance(path, int):
                            info, expected = os.fstat(path), source.parent.stat()
                            same = (info.st_dev, info.st_ino) == (expected.st_dev, expected.st_ino)
                        else:
                            same = Path(path) == source.parent
                        if same:
                            raise PermissionError('source enumeration failed')
                    return real_scandir(path)
                def publish_then_change(path, data, expected):
                    nonlocal staged
                    receipt = real_publish(path, data, expected)
                    if path.name == '.init-pending.json':
                        staged = True
                        if change == 'source':
                            source.write_bytes(b'new source')
                        elif change == 'target-role':
                            (control / 'new-role').symlink_to(self.state, target_is_directory=True)
                    return receipt
                try:
                    with mock.patch.object(initializer, 'publish', side_effect=publish_then_change), \
                            mock.patch.object(os, 'scandir', side_effect=scandir):
                        with self.assertRaises((ValueError, OSError)):
                            self.run_init()
                    self.assertFalse(self.state.exists())
                    self.assertEqual(list(self.fixture.a.glob('.sdlc-init-*')), [])
                finally:
                    source.write_bytes(original)
                    (control / 'new-role').unlink(missing_ok=True)
        self.assert_imported(self.run_init())

    def test_manual_constitution_after_interruption_does_not_gain_source_provenance(self):
        self.interrupt('init-options.json')
        constitution = self.state / 'memory/constitution.md'
        constitution.write_text('Manual principles')
        before = constitution.stat().st_mtime_ns
        result = self.run_init()
        self.assertEqual(constitution.read_text(), 'Manual principles')
        self.assertEqual(constitution.stat().st_mtime_ns, before)
        self.assertFalse((self.state / 'memory/.constitution-template.json').exists())
        self.assertEqual(result['constitution_source'], 'preserved')
        self.assertEqual(result['constitution_provenance'], 'not_recorded')
        self.assertNotIn('memory/constitution.md', result['imported'])
        self.assertIn('memory/constitution.md', result['preserved_imports'])

    def test_concurrent_constitution_after_preview_is_preserved_and_not_reported_as_imported(self):
        original_lock = test_storage.store.write_lock
        @contextmanager
        def create_constitution(state):
            with original_lock(state) as token:
                (state / 'memory').mkdir()
                (state / 'memory/constitution.md').write_text('Concurrent local principles')
                yield token
        with mock.patch.object(test_storage.store, 'write_lock', create_constitution):
            result = self.run_init()
        self.assertEqual((self.state / 'memory/constitution.md').read_text(), 'Concurrent local principles')
        self.assertNotIn('.sdlc/memory/constitution.md', result['created'])
        self.assertNotIn('memory/constitution.md', result['imported'])
        self.assertEqual(result['constitution_source'], 'preserved')
        self.assertFalse((self.state / 'memory/.constitution-template.json').exists())

    def test_pending_snapshot_cannot_drop_selected_requirement_or_orphan_provenance(self):
        self.interrupt()
        original = json.loads(self.pending.read_text())
        for removed in ('specs/001-one/spec.md', 'memory/constitution.md'):
            manifest = json.loads(json.dumps(original))
            manifest['seeds'].pop(removed)
            self.pending.write_text(json.dumps(manifest))
            with self.subTest(removed=removed), self.assertRaisesRegex(ValueError, 'Incomplete interrupted'):
                self.run_init()
            self.assertTrue(self.pending.exists())

    def test_invalid_pending_seed_path_stops_before_writing_outside_store(self):
        self.interrupt()
        manifest = json.loads(self.pending.read_text())
        manifest['seeds']['specs/001-one/../../../escaped'] = 'ZXNjYXBl'
        self.pending.write_text(json.dumps(manifest))
        before = test_storage.files(self.state)
        with self.assertRaisesRegex(ValueError, 'seed path'):
            self.run_init()
        self.assertEqual(test_storage.files(self.state), before)
        self.assertFalse((self.fixture.a / 'escaped').exists())


if __name__ == '__main__':
    unittest.main()
