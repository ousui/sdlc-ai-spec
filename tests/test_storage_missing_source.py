"""A selected source disappearing is an error, never an empty import snapshot."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage

spec = importlib.util.spec_from_file_location('sdlc_missing_source_initializer', storage.SCRIPTS / 'init_project.py')
initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)


class MissingSourceTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        env = mock.patch.dict(os.environ, self.f.env, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.authority = self.f.main / '.sdlc'

    def init(self, project=None, **overrides):
        args = dict(project=project or self.f.a, discover=False, mode='local', seed='knowledge',
                    feature=[], feature_numbering=None, dry_run=False)
        return initializer.initialize_selected(SimpleNamespace(**(args | overrides)))

    def identities(self, root):
        return {name: (data, (root / name).stat().st_ino, (root / name).stat().st_mtime_ns)
                for name, data in storage.files(root).items()}

    @contextmanager
    def empty_source(self, source):
        saved = source.with_name('saved-source')
        source.rename(saved)
        source.mkdir()
        try:
            yield
        finally:
            shutil.rmtree(source)
            saved.rename(source)

    @contextmanager
    def disappear_at_snapshot(self, source, *, call=1, reappear=False):
        original = storage.changes.snapshot
        saved = source.with_name('disappeared-source')
        count = 0
        def snapshot(root, paths=None):
            nonlocal count
            if root != source:
                return original(root, paths)
            count += 1
            if count != call:
                return original(root, paths)
            source.rename(saved)
            try:
                return original(root, paths)
            finally:
                if reappear:
                    saved.rename(source)
        try:
            with mock.patch.object(storage.changes, 'snapshot', side_effect=snapshot):
                yield
        finally:
            if saved.exists():
                saved.rename(source)

    def test_source_snapshot_requires_real_directory_and_preserves_optional_target(self):
        absent = self.f.base / 'absent-source'
        self.assertEqual(storage.changes.optional_snapshot(absent), {})
        with self.assertRaises(FileNotFoundError):
            storage.changes.source_snapshot(absent)
        absent.write_text('not a directory')
        with self.assertRaisesRegex(ValueError, 'not a directory'):
            storage.changes.source_snapshot(absent)
        absent.unlink()
        absent.symlink_to(self.authority, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'not a directory'):
            storage.changes.source_snapshot(absent)
        with self.empty_source(self.authority):
            self.assertEqual(storage.changes.source_snapshot(self.authority), {})

    def test_first_init_rejects_disappearance_instead_of_falling_back_to_templates(self):
        self.f.feature(self.f.main)
        before = self.identities(self.authority)
        for project, features in ((self.f.a, []), (self.f.b, ['001-one'])):
            for dry_run in (False, True):
                for reappear in (False, True):
                    with self.subTest(features=features, dry_run=dry_run, reappear=reappear):
                        with self.disappear_at_snapshot(self.authority, reappear=reappear):
                            with self.assertRaises(FileNotFoundError):
                                self.init(project, feature=features, dry_run=dry_run)
                        self.assertFalse((project / '.sdlc').exists())
                        self.assertEqual(self.identities(self.authority), before)
            result = self.init(project, feature=features)
            self.assertIn('memory/long-term.md', result['imported'])
            if features:
                self.assertIn('specs/001-one/spec.md', result['imported'])
            self.assertEqual(self.identities(self.authority), before)

    def test_source_present_at_discovery_cannot_become_blank_init(self):
        original = storage.store.resolve
        saved = self.authority.with_name('after-discovery-source')
        def resolve(*args, **kwargs):
            result = original(*args, **kwargs)
            if not saved.exists():
                self.authority.rename(saved)
            return result
        try:
            with mock.patch.object(storage.store, 'resolve', side_effect=resolve):
                with self.assertRaisesRegex(ValueError, 'available authority'):
                    self.init()
            self.assertFalse((self.f.a / '.sdlc').exists())
        finally:
            saved.rename(self.authority)
        self.assertIn('memory/long-term.md', self.init()['imported'])

    def test_init_rechecks_empty_source_before_creation_and_while_locked(self):
        for phase in ('before-creation', 'locked'):
            for mutation in ('disappear', 'new-knowledge'):
                with self.subTest(phase=phase, mutation=mutation), self.empty_source(self.authority):
                    saved = self.authority.with_name('empty-disappeared-source')
                    original_snapshot = storage.changes.snapshot
                    original_lock = storage.store.write_lock
                    count = 0
                    def mutate():
                        if mutation == 'disappear':
                            self.authority.rename(saved)
                        else:
                            (self.authority / 'memory').mkdir()
                            (self.authority / 'memory/long-term.md').write_text('arrived after preview')
                    def snapshot(root, paths=None):
                        nonlocal count
                        if root == self.authority:
                            count += 1
                            if phase == 'before-creation' and count == 2:
                                mutate()
                        return original_snapshot(root, paths)
                    @contextmanager
                    def lock(target):
                        with original_lock(target):
                            if phase == 'locked':
                                mutate()
                            yield
                    try:
                        with mock.patch.object(storage.changes, 'snapshot', side_effect=snapshot), \
                                mock.patch.object(storage.store, 'write_lock', side_effect=lock):
                            with self.assertRaises((FileNotFoundError, ValueError)):
                                self.init()
                        self.assertFalse((self.f.a / '.sdlc').exists())
                    finally:
                        if saved.exists():
                            saved.rename(self.authority)

    def test_empty_or_initially_absent_authority_preserves_blank_init_and_noop(self):
        with self.empty_source(self.authority):
            result = self.init()
            self.assertEqual(result['status'], 'initialized')
            self.assertEqual(result['imported'], [])
            state = self.f.a / '.sdlc'
            before = self.identities(state)
            self.assertEqual(self.init()['status'], 'unchanged')
            self.assertEqual(self.identities(state), before)
            self.assertEqual(list(self.authority.iterdir()), [])
        saved = self.authority.with_name('absent-authority')
        self.authority.rename(saved)
        try:
            result = self.init(self.f.b)
            self.assertEqual(result['status'], 'initialized')
            self.assertEqual(result['imported'], [])
            self.assertFalse(self.authority.exists())
            before = self.identities(self.f.b / '.sdlc')
            self.assertEqual(self.init(self.f.b)['status'], 'unchanged')
            self.assertEqual(self.identities(self.f.b / '.sdlc'), before)
        finally:
            saved.rename(self.authority)

    def test_init_pending_resume_uses_saved_bytes_without_source_online(self):
        self.f.feature(self.f.main)
        state = self.f.a / '.sdlc'
        original_publish = initializer.publish
        def publish(path, data, expected):
            if path == state / 'README.md':
                raise OSError('interrupt after intent publication')
            return original_publish(path, data, expected)
        with mock.patch.object(initializer, 'publish', side_effect=publish):
            with self.assertRaisesRegex(OSError, 'interrupt after intent'):
                self.init(feature=['001-one'])
        self.assertTrue((state / '.init-pending.json').is_file())
        saved = self.authority.with_name('offline-authority')
        self.authority.rename(saved)
        try:
            with mock.patch.object(storage.changes, 'source_snapshot', side_effect=AssertionError('source must stay offline')):
                result = self.init(feature=['001-one'])
            self.assertFalse((state / '.init-pending.json').exists())
            for name in ('memory/long-term.md', 'specs/001-one/spec.md'):
                self.assertEqual((state / name).read_bytes(), (saved / name).read_bytes())
                self.assertIn(name, result['imported'] + result['preserved_imports'])
        finally:
            saved.rename(self.authority)

    def copy_case(self, kind):
        self.f.init(self.f.a, '--mode', 'local')
        project, source = ((self.f.a, self.authority) if kind == 'import'
                           else (self.f.main, self.f.a / '.sdlc'))
        return project, source, [source] if kind == 'collect' else []

    def test_copy_prepare_rejects_missing_and_temporarily_missing_sources(self):
        for kind in ('import', 'collect'):
            project, source, sources = self.copy_case(kind)
            target = project / '.sdlc'
            before = self.identities(target)
            source_before = self.identities(source)
            for reappear in (False, True):
                with self.subTest(kind=kind, reappear=reappear):
                    with self.disappear_at_snapshot(source, reappear=reappear):
                        with self.assertRaises(FileNotFoundError):
                            storage.changes.prepare(project, kind, sources, [], [])
                    self.assertEqual(self.identities(target), before)
                    self.assertEqual(self.identities(source), source_before)
                    self.assertFalse((target / 'transactions').exists())

    def test_copy_apply_rejects_disappearing_empty_source_and_preserves_prepared_record(self):
        for kind in ('import', 'collect'):
            project, source, sources = self.copy_case(kind)
            for empty in (False, True):
                with self.subTest(kind=kind, empty=empty):
                    @contextmanager
                    def selected_source():
                        if empty:
                            with self.empty_source(source):
                                yield
                        else:
                            yield
                    with selected_source():
                        if not empty:
                            (source / 'memory/long-term.md').write_text('candidate from ' + kind)
                        plan = storage.changes.prepare(project, kind, sources, [], [])
                        if not empty:
                            self.f.replace(plan, 'memory/long-term.md', 'candidate from ' + kind)
                        folder = Path(plan['transaction'])
                        manifest = folder / 'manifest.json'
                        record = manifest.read_bytes()
                        before = self.identities(project / '.sdlc')
                        for reappear in (False, True):
                            with self.disappear_at_snapshot(source, reappear=reappear):
                                with self.assertRaises(FileNotFoundError):
                                    storage.changes.apply(project, folder)
                            self.assertEqual(manifest.read_bytes(), record)
                            self.assertEqual(self.identities(project / '.sdlc'), before)
                        result = storage.changes.apply(project, folder)
                        self.assertEqual(result['status'], 'applied')
                        if empty:
                            self.assertEqual(result['written'], [])
                            self.assertEqual(self.identities(project / '.sdlc'), before)

    def test_copy_recovery_requires_no_live_source_snapshot(self):
        for kind in ('import', 'collect'):
            with self.subTest(kind=kind):
                project, source, sources = self.copy_case(kind)
                target = project / '.sdlc/memory/long-term.md'
                previous = target.read_bytes()
                (source / 'memory/long-term.md').write_text('recover candidate from ' + kind)
                plan = storage.changes.prepare(project, kind, sources, [], [])
                self.f.replace(plan, 'memory/long-term.md', 'recover candidate from ' + kind)
                folder = Path(plan['transaction'])
                storage.changes.apply(project, folder)
                manifest = folder / 'manifest.json'
                record = json.loads(manifest.read_text())
                record['status'] = 'applying'
                manifest.write_text(json.dumps(record))
                saved = source.with_name('offline-source')
                source.rename(saved)
                try:
                    with mock.patch.object(storage.changes, 'source_snapshot', side_effect=AssertionError('source must stay offline')):
                        self.assertEqual(storage.changes.recover(project, folder)['status'], 'recovered')
                    self.assertEqual(target.read_bytes(), previous)
                finally:
                    saved.rename(source)


if __name__ == '__main__':
    unittest.main()
