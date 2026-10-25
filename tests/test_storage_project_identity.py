"""Filesystem-equivalent project addresses retain one workspace and raw selection semantics."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unicodedata
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class ProjectIdentityTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        probe = self.f.base / 'CaseProbe'
        probe.write_text('probe')
        insensitive = (self.f.base / 'caseprobe').exists()
        probe.unlink()
        if not insensitive:
            self.skipTest('Requires a case-insensitive filesystem')

    def alias(self, project):
        return project.with_name(project.name.upper())

    def shell(self, project, value, *, no_persist=False, paths_only=False):
        env = dict(self.f.env, SDLC_INIT_DIR=str(project))
        if value is not None:
            env['SDLC_FEATURE_DIRECTORY'] = value
        if no_persist:
            env['SDLC_FEATURE_NO_PERSIST'] = '1'
        script = 'check-prerequisites.sh' if paths_only else 'setup-plan.sh'
        result = subprocess.run(['bash', str(storage.PACKAGE / 'scripts/bash' / script), '--json',
                                 *(['--paths-only'] if paths_only else [])], cwd=project,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_case_equivalent_main_local_and_shared_entries_resolve_to_one_project(self):
        self.f.init(self.f.a, '--mode', 'local')
        for project, mode, can_collect in ((self.f.main, 'authority', True),
                                            (self.f.a, 'local', False), (self.f.b, 'shared', False)):
            with self.subTest(mode=mode):
                normal = self.f.binding(project)
                other = self.f.binding(self.alias(project))
                self.assertEqual(other, normal)
                self.assertEqual(other['PROJECT_ROOT'], str(project))
                self.assertEqual(other['mode'], mode)
                self.assertEqual(other['can_collect'], can_collect)
                self.assertTrue(project.samefile(self.alias(project)))

    def test_standalone_project_identity_is_read_only_without_subprocesses(self):
        project = self.f.base / 'standalone'
        project.mkdir()
        for platform in (storage.store.sys.platform, 'metadata-only-test'):
            with self.subTest(platform=platform), mock.patch.object(storage.store.sys, 'platform', platform), \
                    mock.patch.object(subprocess, 'run', side_effect=AssertionError('no subprocess')), \
                    mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('no process')):
                normal = storage.store.resolve(project, missing=True, cwd=project, env={})
                other = storage.store.resolve(self.alias(project), missing=True, cwd=project, env={})
                self.assertEqual(normal, other)
                self.assertEqual(normal['PROJECT_ROOT'], str(project))
        self.assertEqual(list(project.iterdir()), [])

    def test_case_equivalent_init_first_import_completion_and_noop_use_same_target(self):
        self.f.feature(self.f.main)
        result = self.f.init(self.alias(self.f.a), '--mode', 'local', '--feature', '001-one')
        self.assertEqual(result['binding']['PROJECT_ROOT'], str(self.f.a))
        self.assertIn('specs/001-one/spec.md', result['imported'])
        self.assertEqual(Path(result['SDLC_DIR']), self.f.a / '.sdlc')
        (self.f.a / '.sdlc/README.md').unlink()
        self.assertEqual(self.f.init(self.alias(self.f.a))['status'], 'completed')
        before = {str(p.relative_to(self.f.a)): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in (self.f.a / '.sdlc').rglob('*') if p.is_file()}
        self.assertEqual(self.f.init(self.alias(self.f.a))['status'], 'unchanged')
        self.assertEqual(before, {str(p.relative_to(self.f.a)): (p.read_bytes(), p.stat().st_mtime_ns)
                                 for p in (self.f.a / '.sdlc').rglob('*') if p.is_file()})

    def check_shared_module(self, designated=False, unicode=False):
        name = 'caf\u00e9-module' if unicode else 'module'
        for workspace in (self.f.main, self.f.a):
            (workspace / name).mkdir()
        main, project = self.f.main / name, self.f.a / name
        alias = project.with_name(unicodedata.normalize('NFD', name.upper()))
        if not alias.is_dir():
            self.skipTest('Requires normalization-insensitive directory lookup')
        self.f.init(main)
        if designated:
            authority = self.f.base / 'designated authority'
            (main / '.sdlc').rename(authority)
            self.f.runpy('sdlc_store.py', 'register', '--authority', str(authority), project=main)
        self.f.feature(main)
        normal = self.f.binding(project)
        other = self.f.binding(alias)
        self.assertEqual(other, normal)
        selection = Path(normal['FEATURE_JSON'])
        value = '.sdlc/specs/001-one/.'
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=project)
        before = selection.read_bytes(), selection.stat().st_mtime_ns
        selected = self.f.runpy('sdlc_store.py', 'feature', project=alias)
        self.assertIsNotNone(selected['FEATURE_DIR'])
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=alias)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        workspaces = selection.parents[1]
        self.assertEqual([p.name for p in workspaces.iterdir()], [selection.parent.name])
        self.assertFalse((project / '.sdlc').exists())

    def test_shared_subproject_case_alias_reuses_selection_and_keeps_noop(self):
        self.check_shared_module()

    def test_designated_authority_keeps_same_selection_for_case_equivalent_subproject(self):
        self.check_shared_module(designated=True)

    def test_unicode_equivalent_project_names_reuse_one_shared_selection(self):
        self.check_shared_module(unicode=True)

    def test_explicit_priority_no_persist_and_noop_survive_case_equivalent_project_override(self):
        self.f.init(self.f.a, '--mode', 'local')
        for project in (self.f.a, self.f.b):
            with self.subTest(local=project == self.f.a):
                feature = self.f.feature(project)
                (feature / 'plan.md').write_text('existing plan')
                selection = Path(self.f.binding(project)['FEATURE_JSON'])
                selection.parent.mkdir(parents=True, exist_ok=True)
                selection.write_text('{invalid saved selection\n')
                value = '.sdlc/specs/001-one/.'
                before = selection.read_bytes(), selection.stat().st_mtime_ns
                self.assertEqual(self.shell(self.alias(project), value, no_persist=True)['BRANCH'], '.')
                self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
                self.shell(self.alias(project), value)
                self.assertEqual(json.loads(selection.read_text())['feature_directory'], value)
                before = selection.read_bytes(), selection.stat().st_mtime_ns
                self.shell(project, value)
                self.shell(self.alias(project), value)
                result = self.shell(project, None, paths_only=True)
                self.assertEqual(Path(result['FEATURE_DIR']), feature)
                self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
                if project == self.f.b:
                    self.assertFalse((project / '.sdlc').exists())

    def test_absolute_selection_keeps_literal_project_prefix_rules_for_case_aliases(self):
        self.f.init(self.f.a, '--mode', 'local')
        feature = self.f.feature(self.f.a)
        (feature / 'plan.md').write_text('existing plan')
        selection = self.f.a / '.sdlc/feature.json'
        for override in (self.f.a, self.alias(self.f.a)):
            for prefix in (self.f.a, self.alias(self.f.a)):
                with self.subTest(override=override.name, prefix=prefix.name):
                    value = str(prefix) + '/.sdlc/specs/001-one/.'
                    expected = '.sdlc/specs/001-one/.' if prefix == override else value
                    self.shell(override, value)
                    self.assertEqual(json.loads(selection.read_text())['feature_directory'], expected)
                    before = selection.read_bytes(), selection.stat().st_mtime_ns
                    self.shell(override, value)
                    self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)

    def test_init_pending_retries_accept_case_equivalent_project_address(self):
        self.f.feature(self.f.main)
        spec = importlib.util.spec_from_file_location('identity_initializer', storage.SCRIPTS / 'init_project.py')
        initializer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(initializer)
        state = self.f.a / '.sdlc'
        args = SimpleNamespace(project=self.alias(self.f.a), discover=False, mode='local', seed='knowledge',
                               feature=['001-one'], feature_numbering=None, dry_run=False)
        publish = initializer.publish
        def interrupted(path, data, expected):
            if path == state / 'memory/long-term.md':
                raise OSError('synthetic case-address interruption')
            return publish(path, data, expected)
        with mock.patch.dict(os.environ, self.f.env, clear=True), mock.patch.object(initializer, 'publish', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'synthetic case-address interruption'):
                initializer.initialize_selected(args)
        pending = state / '.init-pending.json'
        self.assertEqual(json.loads(pending.read_text())['project'], str(self.f.a))
        self.f.init(self.f.a, '--mode', 'local', '--feature', '001-one')
        self.assertEqual((state / 'memory/long-term.md').read_text(), 'Shared project fact\n')
        self.assertFalse(pending.exists())

    def test_case_equivalent_local_transaction_address_supports_apply_and_recover(self):
        self.f.init(self.f.a, '--mode', 'local')
        name = 'memory/long-term.md'
        target = self.f.a / '.sdlc' / name
        plan = self.f.prepare(self.f.a, kind='edit', paths=[name])
        self.f.replace(plan, name, 'candidate')
        self.f.apply(plan, self.alias(self.f.a))
        self.assertEqual(target.read_text(), 'candidate')
        plan = self.f.prepare(self.alias(self.f.a), kind='edit', paths=[name])
        manifest = Path(plan['transaction']) / 'manifest.json'
        data = json.loads(manifest.read_text())
        data['published'] = {name: storage.changes.publish_data(target, b'partial', target.read_bytes())}
        data.update(status='applying', after={name: base64.b64encode(b'partial').decode()})
        manifest.write_text(json.dumps(data))
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.alias(self.f.a))
        self.assertEqual(target.read_text(), 'candidate')

    def test_case_equivalent_main_override_cannot_bypass_local_store_or_collect_from_worktree(self):
        self.f.init(self.f.a, '--mode', 'local')
        before = storage.files(self.f.main / '.sdlc')
        self.f.runpy('sdlc_store.py', 'resolve', project=self.alias(self.f.main), cwd=self.f.a, ok=False)
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source', str(self.f.a / '.sdlc'),
                     project=self.alias(self.f.main), cwd=self.f.a, ok=False)
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)


class GitPathWhitespaceTests(unittest.TestCase):
    git = storage.StorageTests.git
    runpy = storage.StorageTests.runpy
    init = storage.StorageTests.init
    binding = storage.StorageTests.binding
    prepare = storage.StorageTests.prepare
    apply = storage.StorageTests.apply
    replace = storage.StorageTests.replace
    feature = storage.StorageTests.feature

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-git-whitespace-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.main = self.base / ' main project '
        self.common = self.main / '.git'
        self.main.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('SDLC_', 'GIT_'))}
        self.git('init', '-q', str(self.main), cwd=self.base)
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'fixture', '--allow-empty')
        self.a, self.b = self.base / ' worktree a ', self.base / ' worktree b '
        self.git('worktree', 'add', '-q', '-b', 'a', str(self.a))
        self.git('worktree', 'add', '-q', '-b', 'b', str(self.b))

    def test_main_init_and_git_identity_preserve_path_whitespace(self):
        self.assertEqual(self.init(self.main, '--dry-run')['status'], 'initialized')
        self.assertFalse((self.main / '.sdlc').exists())
        self.assertEqual(self.init(self.main)['status'], 'initialized')
        result = self.binding(self.main)
        self.assertEqual(result['PROJECT_ROOT'], str(self.main))
        self.assertEqual(result['AUTHORITY_DIR'], str(self.main / '.sdlc'))
        self.assertTrue(result['can_collect'])
        self.assertEqual(storage.store.git_identity(self.main), (self.main, self.common))
        project, metadata = self.base / 'separate project ', self.base / ' git metadata '
        project.mkdir()
        self.git('init', '-q', '--separate-git-dir', str(metadata), str(project), cwd=self.base)
        self.assertEqual(storage.store.git_identity(project), (project, metadata))
        # Git adds one LF even when a legal POSIX pathname itself ends in LF.
        for suffix in ('\t', '\n'):
            with self.subTest(suffix=repr(suffix)):
                project = self.base / ('project' + suffix)
                project.mkdir()
                self.git('init', '-q', str(project), cwd=self.base)
                actual = storage.store.resolve(project, missing=True, cwd=project, env={})
                self.assertEqual(actual['PROJECT_ROOT'], str(project))
                self.assertEqual(storage.store.git_identity(project), (project, project / '.git'))

    def test_linked_worktree_sources_and_collection_preserve_path_whitespace(self):
        self.init(self.main)
        name = 'memory/long-term.md'
        (self.main / '.sdlc' / name).write_text('Authority knowledge')
        self.init(self.a, '--mode', 'local')
        source = self.a / '.sdlc'
        (source / name).write_text('Collected knowledge')
        local = self.binding(self.a)
        shared = self.binding(self.b)
        self.assertEqual(local['PROJECT_ROOT'], str(self.a))
        self.assertEqual(local['mode'], 'local')
        self.assertEqual(shared['PROJECT_ROOT'], str(self.b))
        self.assertEqual(shared['mode'], 'shared')
        self.assertFalse(local['can_collect'])
        self.assertFalse(shared['can_collect'])
        self.assertTrue(storage.store.registered_workspace(self.a, self.common))
        self.assertIn(str(source), self.binding(self.main)['sources'])
        before = storage.files(source)
        plan = self.prepare(sources=[source])
        self.replace(plan, name, 'Collected knowledge')
        self.assertEqual(self.apply(plan)['status'], 'applied')
        self.assertEqual((self.main / '.sdlc' / name).read_text(), 'Collected knowledge')
        self.assertEqual(storage.files(source), before)

    def test_shared_selection_explicit_priority_and_noop_preserve_path_whitespace(self):
        self.init(self.main)
        self.feature(self.main)
        second = self.feature(self.main, '002-two')
        value = '.sdlc/specs/001-one/.'
        self.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.b)
        selection = Path(self.binding(self.b)['FEATURE_JSON'])
        before = selection.read_bytes(), selection.stat().st_mtime_ns
        self.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.b)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        env = dict(self.env, SDLC_INIT_DIR=str(self.b),
                   SDLC_FEATURE_DIRECTORY='.sdlc/specs/002-two', SDLC_FEATURE_NO_PERSIST='1')
        result = subprocess.run(['bash', str(storage.PACKAGE / 'scripts/bash/check-prerequisites.sh'),
                                 '--json', '--paths-only'], cwd=self.b, env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout)['FEATURE_DIR']), second)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        self.assertFalse((self.b / '.sdlc').exists())


if __name__ == '__main__':
    unittest.main()
