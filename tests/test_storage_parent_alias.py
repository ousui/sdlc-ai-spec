"""An unreadable symlink prefix cannot disappear when later parents are resolved."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
    from tests import test_storage_init_retry as retry
except ImportError:
    import test_storage as storage
    import test_storage_init_retry as retry


class ParentAliasTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.init(self.f.a, '--mode', 'local')
        self.f.init(self.f.b, '--mode', 'local')
        self.sequence = 0

    def identity(self, path):
        if not path.exists():
            return None
        metadata = path.stat()
        return path.read_bytes(), metadata.st_ino, metadata.st_mtime_ns

    def state(self, root):
        return {str(path.relative_to(root)): self.identity(path)
                for path in root.rglob('*') if not path.is_symlink() and path.is_file()}

    @contextmanager
    def parent_alias(self, control, target, anchor):
        """Keep the real target accessible while an intermediate lookup fails."""
        hidden = self.f.base / 'unsearchable-parent'
        hidden.mkdir()
        nested = anchor / 'alias-inner/deep'
        nested.mkdir(parents=True)
        bounce = hidden / 'bounce'
        bounce.symlink_to(nested, target_is_directory=True)
        control.parent.mkdir(parents=True, exist_ok=True)
        control.symlink_to(str(bounce) + '/../../' + str(target.relative_to(anchor)),
                           target_is_directory=target.is_dir())
        try:
            self.assertEqual(control.resolve(), target)
            yield hidden
        finally:
            hidden.chmod(0o755)
            control.unlink()
            bounce.unlink()
            hidden.rmdir()
            nested.rmdir()
            nested.parent.rmdir()

    @contextmanager
    def inaccessible(self, hidden, control):
        mode = stat.S_IMODE(hidden.stat().st_mode)
        hidden.chmod(0)
        try:
            if os.access(hidden, os.X_OK):
                self.skipTest('Directory search permission is not enforced for this user')
            with self.assertRaises(PermissionError):
                control.stat()
            yield
        finally:
            hidden.chmod(mode)

    def case(self, kind, existing):
        self.sequence += 1
        feature = '001-parent-' + str(self.sequence)
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
        return project, name, target, args

    def prepared(self, project, name, args, phase):
        if phase == 'prepare':
            return None
        plan = self.f.runpy('store_changes.py', *args, project=project)
        self.f.replace(plan, name, 'candidate')
        if phase == 'recover':
            self.f.apply(plan, project)
            manifest = Path(plan['transaction']) / 'manifest.json'
            data = json.loads(manifest.read_text())
            self.assertTrue(data['published'])
            data['status'] = 'applying'
            manifest.write_text(json.dumps(data))
        return plan

    def transaction_case(self, kind, phase, existing, role):
        project, name, target, args = self.case(kind, existing)
        plan = self.prepared(project, name, args, phase)
        if role == 'leaf':
            control, alias_target = self.f.b / '.sdlc/feature.json', target
        elif role == 'directory':
            control, alias_target = self.f.b / '.sdlc/workspaces/private-alias', target.parent
        else:
            control, alias_target = self.f.main / '.sdlc/specs/external-alias', target.parent
        before = self.state(project / '.sdlc')
        call = args if phase == 'prepare' else [phase, '--transaction', plan['transaction']]
        with self.parent_alias(control, alias_target, project) as hidden:
            with self.inaccessible(hidden, control):
                result = self.f.runpy('store_changes.py', *call, project=project, ok=False)
                self.assertIn('Cannot inspect store alias ownership', result.stderr)
                self.assertEqual(self.state(project / '.sdlc'), before)
            # Restoring traversal reveals the protected role; it is not permission
            # failure alone that makes this alias invalid for the transaction.
            result = self.f.runpy('store_changes.py', *call, project=project, ok=False)
            self.assertRegex(result.stderr, 'reserved store path|authority data')
            self.assertEqual(self.state(project / '.sdlc'), before)
        # Removing only the foreign alias makes the original operation usable.
        # Recovery restores the saved bytes or removes only our own new file.
        if plan is None:
            plan = self.f.runpy('store_changes.py', *args, project=project)
            self.f.replace(plan, name, 'candidate')
            self.f.apply(plan, project)
        else:
            self.f.runpy('store_changes.py', phase, '--transaction', plan['transaction'], project=project)
        expected = (b'original' if existing else None) if phase == 'recover' else b'candidate'
        self.assertEqual(target.read_bytes() if target.exists() else None, expected)
        for relative, identity in before.items():
            if relative != name and not relative.startswith('transactions/'):
                self.assertEqual(self.identity(project / '.sdlc' / relative), identity)

    def test_inaccessible_parents_block_control_leaf_prepare(self):
        for kind in ('edit', 'import', 'collect'):
            for existing in (False, True):
                with self.subTest(kind=kind, existing=existing):
                    self.transaction_case(kind, 'prepare', existing, 'leaf')

    def test_inaccessible_parents_block_control_leaf_apply_and_recover(self):
        for kind in ('edit', 'import', 'collect'):
            for phase in ('apply', 'recover'):
                for existing in (False, True):
                    with self.subTest(kind=kind, phase=phase, existing=existing):
                        self.transaction_case(kind, phase, existing, 'leaf')

    def test_inaccessible_parents_block_control_subdirectory_aliases(self):
        for kind in ('edit', 'import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                with self.subTest(kind=kind, phase=phase):
                    self.transaction_case(kind, phase, phase != 'prepare', 'directory')

    def test_inaccessible_parents_block_authority_external_artifacts(self):
        for phase in ('prepare', 'apply', 'recover'):
            for existing in (False, True):
                with self.subTest(phase=phase, existing=existing):
                    self.transaction_case('edit', phase, existing, 'authority')

    def init_case(self, phase, role):
        project = self.f.base / ('init-' + phase + '-' + role)
        self.f.git('worktree', 'add', '-q', '-b', project.name, str(project))
        state = project / '.sdlc'
        target = state / 'memory/constitution.md'
        pending = state / '.init-pending.json'
        authority = self.f.main / '.sdlc/memory/constitution.md'
        expected = authority.read_bytes()
        if phase == 'completion':
            self.f.init(project, '--mode', 'local')
            target.unlink()
        elif phase == 'resume':
            publish = retry.initializer.publish

            def interrupt(path, data, previous):
                if path == target:
                    raise OSError('synthetic interrupted import')
                return publish(path, data, previous)

            args = SimpleNamespace(project=project, discover=False, mode='local', seed='knowledge',
                                   feature=[], feature_numbering=None, dry_run=False)
            with mock.patch.dict(os.environ, self.f.env, clear=True):
                with mock.patch.object(retry.initializer, 'publish', side_effect=interrupt):
                    with self.assertRaisesRegex(OSError, 'synthetic interrupted import'):
                        retry.initializer.initialize_selected(args)
            self.assertTrue(pending.is_file())
            authority.write_bytes(b'Authority changed after the interrupted snapshot\n')
        if phase != 'first':
            (state / 'memory').mkdir(parents=True, exist_ok=True)
            (state / 'memory/user-note.md').write_bytes(b'preserve intervening user work')
        control = (self.f.b / '.sdlc/feature.json' if role == 'leaf' else
                   self.f.b / '.sdlc/workspaces/private-alias')
        alias_target = target if role == 'leaf' else target.parent
        before = self.state(state)
        existed = state.exists()
        with self.parent_alias(control, alias_target, project) as hidden:
            with self.inaccessible(hidden, control):
                result = self.f.runpy('init_project.py', '--mode', 'local', project=project, ok=False)
                self.assertIn('Cannot inspect store alias ownership', result.stderr)
                self.assertEqual(state.exists(), existed)
                self.assertEqual(self.state(state), before)
            result = self.f.runpy('init_project.py', '--mode', 'local', project=project, ok=False)
            self.assertIn('reserved store path', result.stderr)
            self.assertEqual(self.state(state), before)
        self.f.init(project, '--mode', 'local')
        self.assertTrue(target.is_file())
        if phase in ('first', 'resume'):
            self.assertEqual(target.read_bytes(), expected)
        self.assertFalse(pending.exists())
        for relative, identity in before.items():
            if relative != '.init-pending.json':
                self.assertEqual(self.identity(state / relative), identity)
        completed = self.state(state)
        self.assertEqual(self.f.init(project, '--mode', 'local')['status'], 'unchanged')
        self.assertEqual(self.state(state), completed)
        authority.write_bytes(expected)

    def test_init_first_import_rejects_inaccessible_parent_aliases(self):
        for role in ('leaf', 'directory'):
            with self.subTest(role=role):
                self.init_case('first', role)

    def test_init_completion_and_saved_intent_resume_reject_parent_aliases(self):
        for phase in ('completion', 'resume'):
            for role in ('leaf', 'directory'):
                with self.subTest(phase=phase, role=role):
                    self.init_case(phase, role)

    def test_multilevel_parent_alias_preserves_permission_errors_and_missing_targets(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                project, _, target, _ = self.case('edit', existing)
                control = self.f.b / '.sdlc/feature.json'
                forward = self.f.base / 'forwarded-alias'
                context = self.f.binding(project)
                before = self.identity(target)
                with self.parent_alias(control, target, project) as hidden:
                    control.rename(forward)
                    control.symlink_to(forward)
                    try:
                        self.assertEqual(control.resolve(), target)
                        with self.inaccessible(hidden, control):
                            with self.assertRaisesRegex(ValueError, 'Cannot inspect store alias ownership'):
                                storage.store.resolve_alias(control)
                            with self.assertRaisesRegex(ValueError, 'Cannot inspect store alias ownership'):
                                storage.store.document_path(context, target)
                        # An existing traversal prefix can safely identify a
                        # missing leaf; a future publication is still protected.
                        self.assertEqual(storage.store.resolve_alias(control), target)
                        with self.assertRaisesRegex(ValueError, 'reserved store path'):
                            storage.store.document_path(context, target)
                        self.assertEqual(self.identity(target), before)
                    finally:
                        forward.unlink()
                self.assertEqual(storage.store.document_path(context, target), target)

    def test_broken_parent_prefix_becoming_traversable_is_rechecked_before_apply(self):
        project, name, target, args = self.case('edit', True)
        control = self.f.b / '.sdlc/feature.json'
        missing = self.f.base / 'not-yet-created'
        try:
            with self.parent_alias(control, target, project) as hidden:
                control.unlink()
                control.symlink_to(str(missing) + '/../' + hidden.name + '/bounce/../../' +
                                   str(target.relative_to(project)))
                with self.inaccessible(hidden, hidden / 'bounce'):
                    # The kernel stops at this missing prefix, before reaching
                    # the unreadable directory. It is not yet a usable alias.
                    with self.assertRaises(FileNotFoundError):
                        control.stat()
                    plan = self.f.runpy('store_changes.py', *args, project=project)
                    self.f.replace(plan, name, 'candidate')
                    before = self.state(project / '.sdlc')
                    missing.mkdir()
                    with self.assertRaises(PermissionError):
                        control.stat()
                    result = self.f.apply(plan, project, ok=False)
                    self.assertIn('Cannot inspect store alias ownership', result.stderr)
                    self.assertEqual(self.state(project / '.sdlc'), before)
                self.assertEqual(control.resolve(), target)
                result = self.f.apply(plan, project, ok=False)
                self.assertIn('reserved store path', result.stderr)
                self.assertEqual(self.state(project / '.sdlc'), before)
            self.f.apply(plan, project)
            self.assertEqual(target.read_bytes(), b'candidate')
        finally:
            if missing.exists():
                missing.rmdir()

    def test_legal_parent_links_and_unrelated_broken_cycles_remain_usable(self):
        nested = self.f.a / 'alias-inner/deep'
        nested.mkdir(parents=True)
        external = self.f.a / 'external'
        external.mkdir()
        actual = external / 'long-term.md'
        actual.write_bytes(b'original')
        logical = self.f.a / '.sdlc/memory/long-term.md'
        logical.unlink()
        logical.symlink_to(str(nested) + '/../../external/long-term.md')
        link_identity = os.readlink(logical), logical.lstat().st_ino
        controls = self.f.b / '.sdlc/workspaces'
        controls.mkdir()
        (controls / 'broken').symlink_to(self.f.base / 'missing')
        (controls / 'cycle').symlink_to(controls / 'cycle')
        unrelated = external / 'unrelated.md'
        unrelated.write_bytes(b'independent data')
        (controls / 'valid-parent').symlink_to(str(nested) + '/../../external/unrelated.md')
        self.assertEqual(storage.store.resolve_alias(logical), actual)
        self.assertEqual(storage.store.resolve_alias(controls / 'valid-parent'), unrelated)
        before = self.identity(actual)
        self.f.runpy('project_status.py', project=self.f.a)
        self.assertEqual(self.identity(actual), before)
        plan = self.f.prepare(self.f.a, kind='edit', paths=['memory/long-term.md'])
        self.f.replace(plan, 'memory/long-term.md', 'candidate')
        self.f.apply(plan, self.f.a)
        self.assertEqual(actual.read_bytes(), b'candidate')
        self.assertEqual((os.readlink(logical), logical.lstat().st_ino), link_identity)
        before = self.identity(actual)
        plan = self.f.prepare(self.f.a, kind='edit', paths=['memory/long-term.md'])
        self.f.replace(plan, 'memory/long-term.md', 'candidate')
        self.f.apply(plan, self.f.a)
        self.assertEqual(self.identity(actual), before)
        self.assertEqual(unrelated.read_bytes(), b'independent data')


if __name__ == '__main__':
    unittest.main()
