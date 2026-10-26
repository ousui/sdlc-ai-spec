"""Unavailable directory metadata must not become an empty ownership/snapshot set."""
from __future__ import annotations

from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import stat
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class UnreadableDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.init(self.f.a, '--mode', 'local')
        self.f.init(self.f.b, '--mode', 'local')
        self.sequence = 0

    @contextmanager
    def opaque(self, directory, permissions=0o111):
        mode = stat.S_IMODE(directory.stat().st_mode)
        directory.chmod(permissions)
        try:
            if os.access(directory, os.R_OK):
                self.skipTest('Directory read permission is not enforced for this user')
            with self.assertRaises(PermissionError):
                list(directory.iterdir())
            yield
        finally:
            directory.chmod(mode)

    def case(self, kind, existing=True):
        self.sequence += 1
        feature = '001-opaque-' + str(self.sequence)
        self.f.feature(self.f.main, feature)
        self.f.feature(self.f.a, feature)
        project, source = (self.f.main, self.f.a) if kind == 'collect' else (self.f.a, self.f.main)
        name = 'specs/' + feature + '/plan.md'
        target = project / '.sdlc' / name
        if existing:
            target.write_bytes(b'original')
        if kind != 'edit':
            (source / '.sdlc' / name).write_bytes(b'candidate')
        args = ['prepare', '--kind', kind]
        if kind == 'edit':
            args += ['--path', name]
        else:
            args += ['--feature', feature]
            if kind == 'collect':
                args += ['--source', str(source / '.sdlc')]
        return project, source, name, target, args

    def identity(self, target):
        return ((target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns)
                if target.exists() else None)

    def partial(self, plan, project):
        self.f.apply(plan, project)
        manifest = Path(plan['transaction']) / 'manifest.json'
        data = json.loads(manifest.read_text())
        self.assertTrue(data['published'])
        data['status'] = 'applying'
        manifest.write_text(json.dumps(data))

    def alias_matrix(self, role):
        kinds = ('edit', 'import', 'collect') if role == 'control' else ('edit', 'import')
        for kind in kinds:
            for phase in ('prepare', 'apply', 'recover'):
                for existing in (False, True):
                    with self.subTest(role=role, kind=kind, phase=phase, existing=existing):
                        project, _, name, target, args = self.case(kind, existing)
                        plan = None
                        if phase != 'prepare':
                            plan = self.f.runpy('store_changes.py', *args, project=project)
                            self.f.replace(plan, name, 'candidate')
                            if phase == 'recover':
                                self.partial(plan, project)
                        owner = (self.f.b / '.sdlc/workspaces' if role == 'control'
                                 else self.f.main / '.sdlc/specs')
                        owner.mkdir(exist_ok=True)
                        alias = owner / 'opaque-reference'
                        alias.symlink_to(target.parent, target_is_directory=True)
                        before = self.identity(target)
                        try:
                            with self.opaque(owner):
                                call = args if phase == 'prepare' else [phase, '--transaction', plan['transaction']]
                                result = self.f.runpy('store_changes.py', *call, project=project, ok=False)
                                # Import snapshots may reject the same directory before
                                # role inspection; neither route may accept a partial view.
                                self.assertTrue('Cannot enumerate store aliases' in result.stderr or
                                                'Permission denied' in result.stderr, result.stderr)
                                self.assertEqual(self.identity(target), before)
                                if plan:
                                    manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
                                    self.assertEqual(manifest['status'], 'applying' if phase == 'recover' else 'prepared')
                        finally:
                            alias.unlink()
                        # The refusal must not consume or corrupt the original transaction.
                        if plan:
                            self.f.runpy('store_changes.py', phase, '--transaction', plan['transaction'], project=project)
                            self.assertEqual(target.read_bytes() if target.exists() else None,
                                             (b'original' if existing else None) if phase == 'recover' else b'candidate')

    def test_unenumerable_control_aliases_protect_prepare_apply_and_recover(self):
        self.alias_matrix('control')

    def test_unenumerable_authority_aliases_protect_prepare_apply_and_recover(self):
        self.alias_matrix('authority')

    def test_alias_metadata_io_errors_are_not_ignored_but_broken_cycles_remain_legal(self):
        control = self.f.b / '.sdlc/workspaces'
        control.mkdir()
        original = Path.resolve
        def fail(path, *args, **kwargs):
            if path == control:
                raise OSError(errno.EIO, 'metadata unavailable')
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'resolve', fail):
            with self.assertRaisesRegex(ValueError, 'Cannot inspect store alias ownership'):
                list(storage.store.alias_targets([control]))
        (control / 'broken').symlink_to(self.f.base / 'absent')
        (control / 'cycle').symlink_to(control / 'cycle')
        project, _, name, target, args = self.case('edit')
        plan = self.f.runpy('store_changes.py', *args, project=project)
        self.f.replace(plan, name, 'candidate')
        self.f.apply(plan, project)
        self.assertEqual(target.read_bytes(), b'candidate')

    def test_control_path_resolution_errors_cannot_bypass_prepare_apply_or_recover(self):
        control = self.f.b / '.sdlc/workspaces'
        original = Path.resolve
        for kind in ('edit', 'import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                for error in (errno.EACCES, errno.EIO):
                    with self.subTest(kind=kind, phase=phase, error=error):
                        project, source, name, target, args = self.case(kind)
                        plan = None
                        if phase != 'prepare':
                            plan = self.f.runpy('store_changes.py', *args, project=project)
                            self.f.replace(plan, name, 'candidate')
                            if phase == 'recover':
                                self.partial(plan, project)
                        before = self.identity(target)
                        def fail(path, *args, **kwargs):
                            if path == control:
                                raise OSError(error, 'control metadata unavailable')
                            return original(path, *args, **kwargs)
                        with mock.patch.object(Path, 'resolve', fail):
                            with self.assertRaisesRegex(ValueError, 'Cannot inspect store alias ownership'):
                                if phase == 'prepare':
                                    storage.changes.prepare(project, kind,
                                        [source / '.sdlc'] if kind == 'collect' else [],
                                        [target.parent.name] if kind != 'edit' else [],
                                        [name] if kind == 'edit' else [])
                                else:
                                    getattr(storage.changes, phase)(project, Path(plan['transaction']))
                        self.assertEqual(self.identity(target), before)
                        if plan:
                            manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
                            self.assertEqual(manifest['status'], 'applying' if phase == 'recover' else 'prepared')

    def test_unavailable_store_root_resolution_is_not_silently_skipped(self):
        context = self.f.binding(self.f.a)
        target = self.f.a / '.sdlc/memory/long-term.md'
        unavailable = self.f.base / 'registered-store'
        context['STORE_DIRS'].append(str(unavailable))
        original = Path.resolve
        for error in (errno.EACCES, errno.EIO):
            with self.subTest(error=error):
                def fail(path, *args, **kwargs):
                    if path == unavailable:
                        raise OSError(error, 'store metadata unavailable')
                    return original(path, *args, **kwargs)
                with mock.patch.object(Path, 'resolve', fail):
                    with self.assertRaisesRegex(ValueError, 'Cannot inspect store alias ownership'):
                        storage.store.document_path(context, target)

    def test_leaf_control_alias_through_unsearchable_parent_blocks_all_transaction_phases(self):
        hidden = self.f.base / 'unsearchable-control-parent'
        hidden.mkdir()
        control = self.f.b / '.sdlc/feature.json'
        for kind in ('edit', 'import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                for existing in (False, True):
                    with self.subTest(kind=kind, phase=phase, existing=existing):
                        project, _, name, target, args = self.case(kind, existing)
                        plan = None
                        if phase != 'prepare':
                            plan = self.f.runpy('store_changes.py', *args, project=project)
                            self.f.replace(plan, name, 'candidate')
                            if phase == 'recover':
                                self.partial(plan, project)
                        indirect = hidden / 'alias'
                        indirect.symlink_to(target.parent, target_is_directory=True)
                        control.symlink_to(indirect / target.name)
                        before = self.identity(target)
                        try:
                            with self.opaque(hidden, permissions=0):
                                call = args if phase == 'prepare' else [phase, '--transaction', plan['transaction']]
                                result = self.f.runpy('store_changes.py', *call, project=project, ok=False)
                                self.assertIn('Cannot inspect store alias ownership', result.stderr)
                                self.assertEqual(self.identity(target), before)
                                if plan:
                                    manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
                                    self.assertEqual(manifest['status'], 'applying' if phase == 'recover' else 'prepared')
                        finally:
                            control.unlink()
                            indirect.unlink()
                        if plan:
                            self.f.runpy('store_changes.py', phase, '--transaction', plan['transaction'], project=project)


    def test_alias_directory_stat_failure_is_not_treated_as_a_nondirectory(self):
        directory = self.f.b / '.sdlc/workspaces'
        directory.mkdir()
        original = Path.stat
        def fail(path, *args, **kwargs):
            if path == directory:
                raise OSError(errno.EIO, 'directory metadata unavailable')
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'stat', fail):
            with self.assertRaisesRegex(ValueError, 'Cannot inspect store alias ownership'):
                list(storage.store.alias_targets([directory]))

    def test_incomplete_source_snapshots_block_prepare_and_apply_but_not_recover(self):
        for kind in ('import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                with self.subTest(kind=kind, phase=phase):
                    project, source, name, target, args = self.case(kind)
                    plan = None
                    if phase != 'prepare':
                        plan = self.f.runpy('store_changes.py', *args, project=project)
                        self.f.replace(plan, name, 'candidate')
                        if phase == 'recover':
                            self.partial(plan, project)
                    before = self.identity(target)
                    memory = source / '.sdlc/memory'
                    with self.opaque(memory):
                        # A directly addressable known file is still readable: only
                        # enumeration is denied, reproducing the false-empty snapshot.
                        self.assertTrue((memory / 'constitution.md').read_bytes())
                        call = args if phase == 'prepare' else [phase, '--transaction', plan['transaction']]
                        result = self.f.runpy('store_changes.py', *call, project=project, ok=phase == 'recover')
                        if phase == 'recover':
                            self.assertEqual(target.read_bytes(), b'original')
                        else:
                            self.assertIn('Permission denied', result.stderr)
                            self.assertEqual(self.identity(target), before)
                            if plan:
                                manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
                                self.assertEqual(manifest['status'], 'prepared')
                    if phase == 'apply':
                        self.f.apply(plan, project)
                        self.assertEqual(target.read_bytes(), b'candidate')

    def test_first_init_does_not_fall_back_to_templates_after_source_enumeration_failure(self):
        project = self.f.base / 'new worktree'
        self.f.git('worktree', 'add', '-q', '-b', 'new-worktree', str(project))
        with self.opaque(self.f.main / '.sdlc/memory'):
            result = self.f.runpy('init_project.py', '--mode', 'local', project=project, ok=False)
            self.assertIn('Permission denied', result.stderr)
            self.assertFalse((project / '.sdlc').exists())
        result = self.f.init(project, '--mode', 'local')
        self.assertEqual(result['constitution_source'], 'authority-import')
        self.assertEqual((project / '.sdlc/memory/long-term.md').read_bytes(),
                         (self.f.main / '.sdlc/memory/long-term.md').read_bytes())

    def test_full_snapshot_io_failure_is_explicit_and_edit_snapshot_stays_scoped(self):
        root = self.f.a / '.sdlc'
        unrelated = root / 'specs/unrelated'
        unrelated.mkdir()
        (unrelated / 'spec.md').write_text('unrelated')
        scandir = os.scandir
        def fail(path):
            info = os.fstat(path) if isinstance(path, int) else None
            expected = unrelated.stat()
            same = ((info.st_dev, info.st_ino) == (expected.st_dev, expected.st_ino)
                    if info is not None else Path(path) == unrelated)
            if same:
                raise OSError(errno.EIO, 'snapshot directory unavailable', str(path))
            return scandir(path)
        with mock.patch.object(os, 'scandir', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'snapshot directory unavailable'):
                storage.changes.snapshot(root)
            self.assertEqual(set(storage.changes.snapshot(root, ['memory/long-term.md'])), {'memory/long-term.md'})
        with self.opaque(unrelated):
            plan = self.f.prepare(self.f.a, kind='edit', paths=['memory/long-term.md'])
            self.f.replace(plan, 'memory/long-term.md', 'ordinary scoped edit')
            self.f.apply(plan, self.f.a)
        self.assertEqual((root / 'memory/long-term.md').read_text(), 'ordinary scoped edit')


if __name__ == '__main__':
    unittest.main()
