"""Corresponding Git projects and optional INIT directories use real fixtures."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
    from tests.test_storage_init_retry import initializer
except ImportError:
    import test_storage as storage
    from test_storage_init_retry import initializer


def snapshot(root):
    result = {}
    for path in root.rglob('*'):
        info = path.lstat()
        name = path.relative_to(root).as_posix()
        result[name] = (('file', path.read_bytes(), info.st_mode, info.st_mtime_ns)
                        if path.is_file() else ('directory', info.st_mode))
    return result


class AuthorityInitReviewTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def command(self, project, script, *arguments, explicit=False):
        env = self.f.env
        if script.endswith('.sh'):
            command = ['bash', str(storage.PACKAGE / 'scripts/bash' / script), *arguments]
            if explicit:
                env = dict(env, SDLC_INIT_DIR=str(project))
        else:
            command = [sys.executable, '-I', '-B', str(storage.SCRIPTS / script), *arguments]
            if explicit:
                command.extend(('--project', str(project)))
        return subprocess.run(command, cwd=project, env=env, capture_output=True,
                              text=True, timeout=30)

    def modules(self, name='module'):
        main, work = self.f.main / name, self.f.a / name
        main.mkdir()
        work.mkdir()
        return main, work

    def foreign(self, project):
        self.f.git('init', '-q', str(project))
        self.f.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                   'commit', '-qm', 'independent repository', '--allow-empty', cwd=project)

    def assert_foreign_rejected(self, main, work):
        before = snapshot(main / '.sdlc')
        parent_before = snapshot(self.f.main / '.sdlc')
        for explicit in (False, True):
            for script, arguments in (
                    ('sdlc_store.py', ['resolve']), ('project-paths.sh', []),
                    ('project_status.py', ['--json']),
                    ('create-new-feature.sh', ['--json', '--short-name', 'foreign', 'Foreign request'])):
                with self.subTest(explicit=explicit, script=script):
                    process = self.command(work, script, *arguments, explicit=explicit)
                    self.assertNotEqual(process.returncode, 0, process.stdout)
                    self.assertIn('main project', process.stderr + process.stdout)
                    self.assertEqual(snapshot(main / '.sdlc'), before)
                    self.assertEqual(snapshot(self.f.main / '.sdlc'), parent_before)
        for dry_run in (False, True):
            self.f.runpy('init_project.py', '--mode', 'shared',
                         *(['--dry-run'] if dry_run else []), project=work, ok=False)
            self.assertEqual(snapshot(main / '.sdlc'), before)
        self.assertFalse((work / '.sdlc').exists())

    def test_preexisting_independent_main_module_cannot_supply_authority(self):
        main, work = self.modules()
        self.foreign(main)
        self.f.init(main)
        (main / '.sdlc/memory/long-term.md').write_text('Independent repository knowledge\n')
        self.assertNotEqual(storage.store.git_identity(main)[1], storage.store.git_identity(work)[1])
        self.assert_foreign_rejected(main, work)

    def test_main_module_takeover_stops_shared_apply_without_changing_transaction(self):
        main, work = self.modules()
        self.f.init(main)
        memory = main / '.sdlc/memory/long-term.md'
        memory.write_text('Original module knowledge\n')
        self.assertEqual(self.f.binding(work)['SDLC_DIR'], str(main / '.sdlc'))
        plan = self.f.prepare(work, kind='edit', paths=['memory/long-term.md'])
        self.f.replace(plan, 'memory/long-term.md', 'Reviewed module knowledge\n')
        self.foreign(main)
        self.assert_foreign_rejected(main, work)
        before = snapshot(main / '.sdlc')
        self.f.apply(plan, work, ok=False)
        self.assertEqual(snapshot(main / '.sdlc'), before)
        manifest = Path(plan['transaction']) / 'manifest.json'
        self.assertEqual(json.loads(manifest.read_text())['status'], 'prepared')
        shutil.rmtree(main / '.git')  # Remove only the nested repository made by this fixture.
        self.assertEqual(self.f.apply(plan, work)['status'], 'applied')
        self.assertEqual(memory.read_text(), 'Reviewed module knowledge\n')

    def test_independent_local_store_remains_usable_after_main_module_takeover(self):
        main, work = self.modules()
        self.f.init(main)
        (main / '.sdlc/memory/long-term.md').write_text('Module knowledge\n')
        self.f.init(work, '--mode', 'local')
        self.foreign(main)
        before = snapshot(main / '.sdlc')
        context = self.f.binding(work)
        self.assertEqual(context['mode'], 'local')
        self.assertIsNone(context['AUTHORITY_DIR'])
        self.assertIsNone(context['authority_exists'])
        self.assertIn('main project', context['authority_error'])
        self.assertEqual(self.f.init(work)['status'], 'unchanged')
        process = self.command(work, 'create-new-feature.sh', '--json', '--short-name', 'local',
                               'Local request', explicit=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(Path(json.loads(process.stdout)['SPEC_FILE']).is_relative_to(work / '.sdlc'))
        plan = self.f.prepare(work, kind='edit', paths=['memory/long-term.md'])
        self.f.replace(plan, 'memory/long-term.md', 'Local knowledge\n')
        self.assertEqual(self.f.apply(plan, work)['status'], 'applied')
        self.assertEqual(snapshot(main / '.sdlc'), before)

    def test_unverifiable_corresponding_main_project_stops_shared_resolution(self):
        main, work = self.modules()
        self.f.init(main)
        (main / '.git').write_text('gitdir: missing-git-directory\n')
        self.assertIsNone(storage.store.git_identity(main))
        self.assert_foreign_rejected(main, work)

    def test_same_repository_module_keeps_explicit_external_authority(self):
        main, work = self.modules()
        external = self.f.base / 'external repository'
        external.mkdir()
        self.foreign(external)
        self.f.init(external)
        authority = external / '.sdlc'
        self.f.runpy('sdlc_store.py', 'register', '--authority', str(authority), project=main)
        self.assertEqual(self.f.binding(work)['AUTHORITY_DIR'], str(authority))
        for explicit in (False, True):
            process = self.command(work, 'create-new-feature.sh', '--json', '--short-name', 'valid',
                                   'Valid shared request', explicit=explicit)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertTrue(Path(json.loads(process.stdout)['SPEC_FILE']).is_relative_to(authority))

    def selected_init(self, project, **overrides):
        args = dict(project=project, discover=False, mode='local', seed='knowledge',
                    feature=['001-one'], feature_numbering=None, dry_run=False)
        args.update(overrides)
        previous = Path.cwd()
        try:
            os.chdir(project)
            with mock.patch.dict(os.environ, self.f.env, clear=True):
                return initializer.initialize_selected(SimpleNamespace(**args))
        finally:
            os.chdir(previous)

    def interrupted_import(self, project):
        original = initializer.publish
        hits = []
        def publish(path, data, expected):
            if path == project / '.sdlc/memory/long-term.md':
                hits.append(path)
                raise OSError('selected seed publication interrupted')
            return original(path, data, expected)
        with mock.patch.object(initializer, 'publish', publish):
            with self.assertRaisesRegex(OSError, 'selected seed publication interrupted'):
                self.selected_init(project)
        self.assertEqual(len(hits), 1)
        self.assertTrue((project / '.sdlc/.init-pending.json').is_file())

    def test_control_directory_files_reject_preview_completion_and_unchanged(self):
        for name in ('workspaces', 'transactions'):
            for partial in (False, True):
                with self.subTest(name=name, partial=partial):
                    project = self.f.base / ('control-' + name + str(partial))
                    project.mkdir()
                    self.f.init(project)
                    state = project / '.sdlc'
                    if partial:
                        (state / 'README.md').unlink()
                    control = state / name
                    control.write_bytes(b'Preserve this user object\n')
                    control.chmod(0o640)
                    before = snapshot(state)
                    for preview in (True, False):
                        process = self.f.runpy('init_project.py',
                                              *(['--dry-run'] if preview else []), project=project, ok=False)
                        self.assertIn(str(control), process.stderr)
                        self.assertEqual(snapshot(state), before)
                    control.unlink()
                    # Optional directories need not be created by a successful INIT.
                    self.assertEqual(self.f.init(project)['status'], 'completed' if partial else 'unchanged')
                    self.assertFalse(control.exists())
                    control.mkdir()
                    self.assertEqual(self.f.init(project)['status'], 'unchanged')
                    self.f.binding(project)

    def test_control_directory_files_preserve_pending_until_corrected_resume(self):
        self.f.feature(self.f.main)
        for name in ('workspaces', 'transactions'):
            for mode in ('auto', 'local'):
                with self.subTest(name=name, mode=mode):
                    project = self.f.base / ('pending-' + name + mode)
                    self.f.git('worktree', 'add', '-q', '-b', project.name, str(project))
                    self.interrupted_import(project)
                    state = project / '.sdlc'
                    control = state / name
                    control.write_bytes(b'Preserve pending and this user file\n')
                    control.chmod(0o640)
                    before = snapshot(state)
                    for preview in (True, False):
                        process = self.f.runpy('init_project.py', '--mode', mode, '--feature', '001-one',
                                              *(['--dry-run'] if preview else []), project=project, ok=False)
                        self.assertIn(str(control), process.stderr)
                        self.assertEqual(snapshot(state), before)
                    control.unlink()
                    control.mkdir()
                    self.f.init(project, '--mode', mode, '--feature', '001-one')
                    self.assertFalse((state / '.init-pending.json').exists())
                    for relative in ('memory/constitution.md', 'memory/long-term.md', 'specs/001-one/spec.md'):
                        self.assertEqual((state / relative).read_bytes(), (self.f.main / '.sdlc' / relative).read_bytes())
                    self.f.binding(project)

    def test_control_directory_types_are_rechecked_after_lock_before_writes(self):
        self.f.feature(self.f.main)
        for name in ('workspaces', 'transactions'):
            for pending in (False, True):
                with self.subTest(name=name, pending=pending):
                    project = self.f.base / ('locked-' + name + str(pending))
                    self.f.git('worktree', 'add', '-q', '-b', project.name, str(project))
                    if pending:
                        self.interrupted_import(project)
                    else:
                        self.f.init(project, '--mode', 'local', '--seed', 'none')
                        (project / '.sdlc/README.md').unlink()
                    state = project / '.sdlc'
                    control = state / name
                    before = snapshot(state)
                    original = storage.store.write_lock
                    @contextmanager
                    def changed(target):
                        with original(target) as token:
                            control.write_bytes(b'Concurrent user file\n')
                            yield token
                    with mock.patch.object(storage.store, 'write_lock', changed):
                        with self.assertRaisesRegex(ValueError, str(control)):
                            self.selected_init(project, **({} if pending else {'seed': 'none', 'feature': []}))
                    after = snapshot(state)
                    self.assertEqual(after.pop(name)[1], b'Concurrent user file\n')
                    self.assertEqual(after, before)
                    control.unlink()
                    self.selected_init(project, **({} if pending else {'seed': 'none', 'feature': []}))
                    self.assertFalse(control.exists())
                    self.assertFalse((state / '.init-pending.json').exists())
                    self.f.binding(project)


if __name__ == '__main__':
    unittest.main()
