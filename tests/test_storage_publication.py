"""Recovery only reverts files whose successful publication is recorded."""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.init(self.f.a, '--mode', 'local')
        self.sequence = 0

    def plan(self, kind, alias=False, existing=False, second=False):
        self.sequence += 1
        feature = '001-case-' + str(self.sequence)
        self.f.feature(self.f.main, feature)
        self.f.feature(self.f.a, feature)
        project, source = (self.f.main, self.f.a) if kind == 'collect' else (self.f.a, self.f.main)
        name = 'specs/' + feature + ('/cafe\u0301.md' if alias else '/new.md')
        target = project / '.sdlc' / name
        if existing:
            target.write_bytes(b'original')
        names = [name]
        if second:
            names.append('specs/' + feature + '/z.md')
        if kind == 'edit':
            plan = self.f.prepare(project, kind=kind, paths=names)
        else:
            for value in names:
                (source / '.sdlc' / value).write_bytes(b'candidate')
            plan = self.f.prepare(project, kind=kind, features=[feature],
                                  sources=[source / '.sdlc'] if kind == 'collect' else [])
        for value in names:
            self.f.replace(plan, value, 'candidate')
        return project, target, plan

    def manifest(self, plan):
        path = Path(plan['transaction']) / 'manifest.json'
        return path, json.loads(path.read_text())

    def concurrent(self, alias):
        if alias:
            probe = self.f.base / 'caf\u00e9'
            probe.touch()
            insensitive = (self.f.base / 'CAFE\u0301').exists()
            probe.unlink()
            if not insensitive:
                self.skipTest('Requires equivalent Unicode and case lookup')
        for kind in ('edit', 'import', 'collect'):
            for deferred in (False, True):
                for identical in (False, True):
                    with self.subTest(kind=kind, deferred=deferred, identical=identical):
                        project, target, plan = self.plan(kind, alias=alias)
                        foreign = target.with_name('CAF\u00c9.MD') if alias else target
                        publish = storage.changes.publish_data
                        observed = []
                        def concurrent_create(path, data, expected):
                            self.assertEqual(path, target)
                            self.assertIsNone(expected)
                            foreign.write_bytes(data if identical else b'foreign edit')
                            observed.append((foreign.read_bytes(), foreign.stat().st_ino, foreign.stat().st_mtime_ns))
                            return publish(path, data, expected)
                        with mock.patch.object(storage.changes, 'publish_data', side_effect=concurrent_create):
                            if deferred:
                                with mock.patch.object(storage.changes, 'rollback', side_effect=OSError('interrupted')):
                                    with self.assertRaises(FileExistsError):
                                        storage.changes.apply(project, Path(plan['transaction']))
                            else:
                                with self.assertRaises(FileExistsError):
                                    storage.changes.apply(project, Path(plan['transaction']))
                        self.assertEqual((foreign.read_bytes(), foreign.stat().st_ino, foreign.stat().st_mtime_ns), observed[0])
                        result = self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'],
                                              project=project, ok=False)
                        self.assertIn('publication ownership', result.stderr)
                        self.assertEqual((foreign.read_bytes(), foreign.stat().st_ino, foreign.stat().st_mtime_ns), observed[0])
                        self.assertEqual(self.manifest(plan)[1]['published'], {})
                        self.assertEqual(self.manifest(plan)[1]['status'], 'applying')

    def test_concurrent_new_files_are_preserved_by_rollback_and_recover(self):
        self.concurrent(False)

    def test_equivalent_concurrent_new_files_are_preserved_by_rollback_and_recover(self):
        self.concurrent(True)

    def test_successfully_published_new_and_existing_files_still_recover(self):
        for kind in ('edit', 'import', 'collect'):
            for existing in (False, True):
                for deferred in (False, True):
                    with self.subTest(kind=kind, existing=existing, deferred=deferred):
                        project, target, plan = self.plan(kind, existing=existing, second=True)
                        publish = storage.changes.publish_data
                        def fail_second(path, data, expected):
                            if path.name == 'z.md':
                                raise OSError('second file failed')
                            return publish(path, data, expected)
                        with mock.patch.object(storage.changes, 'publish_data', side_effect=fail_second):
                            if deferred:
                                with mock.patch.object(storage.changes, 'rollback', side_effect=OSError('interrupted')):
                                    with self.assertRaises(OSError):
                                        storage.changes.apply(project, Path(plan['transaction']))
                            else:
                                with self.assertRaises(OSError):
                                    storage.changes.apply(project, Path(plan['transaction']))
                        if deferred:
                            self.assertEqual(target.read_bytes(), b'candidate')
                            self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)
                        self.assertEqual(target.read_bytes() if target.exists() else None, b'original' if existing else None)
                        self.assertFalse(target.with_name('z.md').exists())
                        self.assertEqual(self.manifest(plan)[1]['status'], 'recovered')

    def test_interruption_before_receipt_persistence_preserves_unverified_output(self):
        project, target, plan = self.plan('collect')
        manifest_path, _ = self.manifest(plan)
        atomic = storage.changes.atomic
        def fail_receipt(path, data):
            if path == manifest_path and json.loads(data).get('published'):
                raise OSError('receipt persistence interrupted')
            return atomic(path, data)
        with mock.patch.object(storage.changes, 'atomic', side_effect=fail_receipt), \
                mock.patch.object(storage.changes, 'rollback', side_effect=OSError('interrupted')):
            with self.assertRaisesRegex(OSError, 'receipt persistence'):
                storage.changes.apply(project, Path(plan['transaction']))
        before = target.read_bytes(), target.stat().st_mtime_ns
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project, ok=False)
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
        self.assertEqual(self.manifest(plan)[1]['published'], {})

    def test_same_bytes_later_replacement_and_rewrite_are_not_owned(self):
        for existing in (False, True):
            for replacement in (False, True):
                with self.subTest(existing=existing, replacement=replacement):
                    project, target, plan = self.plan('edit', existing=existing)
                    self.f.apply(plan, project)
                    path, manifest = self.manifest(plan)
                    manifest['status'] = 'applying'
                    path.write_text(json.dumps(manifest))
                    if replacement:
                        temporary = target.with_name('replacement.md')
                        temporary.write_bytes(target.read_bytes())
                        temporary.replace(target)
                    else:
                        info = target.stat()
                        os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000000))
                    before = target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns
                    self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project, ok=False)
                    self.assertEqual((target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns), before)

    def test_legacy_unknown_ownership_is_preserved_but_original_bytes_are_noop(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                project, target, plan = self.plan('import', existing=existing)
                self.f.apply(plan, project)
                path, manifest = self.manifest(plan)
                manifest.update(status='applying')
                manifest.pop('published')
                path.write_text(json.dumps(manifest))
                before = target.read_bytes(), target.stat().st_mtime_ns
                self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project, ok=False)
                self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                if existing:
                    target.write_bytes(b'original')
                    original = target.stat().st_mtime_ns
                else:
                    target.unlink()
                self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)
                self.assertEqual(target.stat().st_mtime_ns if existing else target.exists(), original if existing else False)


if __name__ == '__main__':
    unittest.main()
