"""R06-R10 regressions using disposable projects and the supported file operations."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
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
    return {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns)
            for path in root.rglob('*') if path.is_file() and not path.is_symlink()}


class FollowupReviewTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def implicit(self, script, *arguments, cwd):
        command = (['bash', str(storage.PACKAGE / 'scripts/bash' / script)] if script.endswith('.sh')
                   else [sys.executable, '-I', '-B', str(storage.SCRIPTS / script)])
        return subprocess.run([*command, *arguments], cwd=cwd, env=self.f.env,
                              capture_output=True, text=True, timeout=30)

    def test_shared_dangling_module_marker_never_selects_or_writes_parent(self):
        main = self.f.main / 'module'
        work = self.f.a / 'module'
        main.mkdir()
        work.mkdir()
        self.f.init(main)
        parent_before = snapshot(self.f.main / '.sdlc')
        for script, arguments in (('sdlc_store.py', ['resolve']), ('project-paths.sh', [])):
            result = self.implicit(script, *arguments, cwd=work)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['PROJECT_ROOT'], str(work))
        marker, saved = main / '.sdlc', self.f.base / 'saved-module'
        marker.rename(saved)
        missing = self.f.base / 'missing-module'
        marker.symlink_to(missing, target_is_directory=True)
        for script, arguments in (('sdlc_store.py', ['resolve']), ('project-paths.sh', []),
                                  ('create-new-feature.sh', ['--short-name', 'module-request', '--json', 'Module request'])):
            with self.subTest(script=script):
                result = self.implicit(script, *arguments, cwd=work)
                self.assertNotEqual(result.returncode, 0, result.stdout)
        explicit = self.f.runpy('sdlc_store.py', 'resolve', project=work, ok=False)
        self.assertIn('No initialized .sdlc', explicit.stderr)
        status = self.implicit('project_status.py', '--json', cwd=work)
        report = json.loads(status.stdout)
        self.assertEqual(report['binding']['PROJECT_ROOT'], str(work))
        self.assertEqual(report['status'], 'uninitialized')
        self.assertEqual(snapshot(self.f.main / '.sdlc'), parent_before)
        self.assertFalse(missing.exists())
        marker.unlink()
        saved.rename(marker)
        created = self.implicit('create-new-feature.sh', '--short-name', 'module-request', '--json', 'Module request', cwd=work)
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertTrue(Path(json.loads(created.stdout)['SPEC_FILE']).is_relative_to(marker))
        self.assertEqual(snapshot(self.f.main / '.sdlc'), parent_before)

    def test_empty_registry_is_invalid_for_main_shared_and_local(self):
        main = self.f.base / 'registry-main'
        main.mkdir()
        self.f.git('init', '-q', str(main))
        self.f.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                   'commit', '-qm', 'fixture', '--allow-empty', cwd=main)
        shared, local = self.f.base / 'registry-shared', self.f.base / 'registry-local'
        for project in (shared, local):
            self.f.git('worktree', 'add', '-q', '-b', project.name, str(project), cwd=main)
        authority = self.f.base / 'designated-authority'
        self.f.runpy('sdlc_store.py', 'register', '--authority', str(authority), project=main)
        self.f.init(main)
        (authority / 'memory/long-term.md').write_text('Designated knowledge\n')
        self.f.init(local, '--mode', 'local')
        registry = main / '.sdlc/store.json'
        valid = registry.read_bytes()
        authority_before, local_before = snapshot(authority), snapshot(local / '.sdlc')
        registry.unlink()
        for project in (main, shared, local):
            context = self.f.binding(project)
            self.assertEqual(context['AUTHORITY_DIR'], str(main / '.sdlc'))
            self.assertIsNone(context['authority_error'])
        for data in ({}, {'schema': 2}, {'schema': True}):
            with self.subTest(registry=data):
                registry.write_text(json.dumps(data))
                before = snapshot(main / '.sdlc')
                for project in (main, shared):
                    result = self.f.runpy('sdlc_store.py', 'resolve', project=project, ok=False)
                    self.assertIn('Unsupported store registry', result.stderr)
                    self.f.runpy('init_project.py', project=project, ok=False)
                context = self.f.binding(local)
                self.assertIsNone(context['AUTHORITY_DIR'])
                self.assertIn('Unsupported store registry', context['authority_error'])
                self.assertEqual(self.f.init(local)['status'], 'unchanged')
                self.assertEqual(snapshot(main / '.sdlc'), before)
                self.assertEqual(snapshot(authority), authority_before)
                self.assertEqual(snapshot(local / '.sdlc'), local_before)
        registry.write_bytes(valid)
        for project in (main, shared, local):
            self.assertEqual(self.f.binding(project)['AUTHORITY_DIR'], str(authority))

    def test_ancestor_edit_targets_are_rejected_in_both_orders_and_through_aliases(self):
        feature = self.f.feature(self.f.main)
        state = self.f.main / '.sdlc'
        for aliases in (False, True):
            parent = 'specs/001-one/document' if not aliases else 'specs/001-one/parent-alias'
            child = parent + '/details.md' if not aliases else 'specs/001-one/child-alias'
            if aliases:
                actual = self.f.base / 'overlap-file'
                (state / parent).symlink_to(actual)
                (state / child).symlink_to(actual / 'details.md')
            for ordered in ([parent, child], [child, parent]):
                with self.subTest(aliases=aliases, ordered=ordered):
                    before = snapshot(state)
                    result = self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit',
                        '--path', 'memory/long-term.md', '--path', ordered[0], '--path', ordered[1], ok=False)
                    self.assertIn('destinations', result.stderr)
                    self.assertEqual(snapshot(state), before)
                    self.assertFalse((state / 'transactions').exists())
        self.assertTrue(feature.is_dir())

    def test_old_overlap_transactions_stop_before_apply_or_recovery_writes(self):
        self.f.feature(self.f.main)
        names = ['memory/long-term.md', 'specs/001-one/document', 'specs/001-one/document/details.md']
        def old_bindings(context, target, paths):
            return {name: storage.changes.edit_binding(context, target, name) for name in sorted(set(paths))}
        with mock.patch.dict(os.environ, self.f.env, clear=True), \
                mock.patch.object(storage.changes, 'edit_bindings', side_effect=old_bindings):
            plan = storage.changes.prepare(self.f.main, 'edit', [], [], names)
        for name in names:
            self.f.replace(plan, name, 'Candidate ' + name)
        path = Path(plan['transaction']) / 'manifest.json'
        before = snapshot(self.f.main / '.sdlc/memory')
        self.f.apply(plan, ok=False)
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest['status'], 'prepared')
        self.assertEqual(snapshot(self.f.main / '.sdlc/memory'), before)
        # A legacy record just before its first write must retain its log and backup.
        manifest.update(status='applying', after={names[0]: base64.b64encode(b'Candidate memory').decode()}, published={})
        path.write_text(json.dumps(manifest))
        recorded = path.read_bytes()
        for _ in range(2):
            self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], ok=False)
            self.assertEqual(path.read_bytes(), recorded)
            self.assertEqual(snapshot(self.f.main / '.sdlc/memory'), before)

    def test_sibling_edit_files_continue_to_apply(self):
        self.f.feature(self.f.main)
        names = ['memory/long-term.md', 'specs/001-one/document.md', 'specs/001-one/details.md']
        plan = self.f.prepare(kind='edit', paths=names)
        for name in names:
            self.f.replace(plan, name, 'Candidate ' + name)
        self.assertEqual(self.f.apply(plan)['status'], 'applied')
        for name in names:
            self.assertEqual((self.f.main / '.sdlc' / name).read_text(), 'Candidate ' + name)

    def interrupted_import(self, project, relative):
        args = SimpleNamespace(project=project, discover=False, mode='local', seed='knowledge',
                               feature=['001-one'], feature_numbering=None, dry_run=False)
        original = initializer.publish
        def fail_seed(path, data, expected):
            if path == project / '.sdlc' / relative:
                raise OSError('Interrupted selected seed')
            return original(path, data, expected)
        with mock.patch.dict(os.environ, self.f.env, clear=True), \
                mock.patch.object(initializer, 'publish', side_effect=fail_seed):
            with self.assertRaisesRegex(OSError, 'Interrupted selected seed'):
                initializer.initialize_selected(args)

    def test_seed_directories_keep_pending_and_resume_original_bytes(self):
        self.f.feature(self.f.main)
        authority = self.f.main / '.sdlc'
        number = 0
        for relative in ('memory/long-term.md', 'specs/001-one/spec.md'):
            for mode in ('auto', 'local'):
                for unavailable in (False, True):
                    with self.subTest(relative=relative, mode=mode, offline=unavailable):
                        number += 1
                        project = self.f.base / ('seed-' + str(number))
                        self.f.git('worktree', 'add', '-q', '-b', project.name, str(project))
                        expected = (authority / relative).read_bytes()
                        self.interrupted_import(project, relative)
                        state = project / '.sdlc'
                        pending = state / '.init-pending.json'
                        intent = pending.read_bytes()
                        target = state / relative
                        target.mkdir()
                        identity = target.stat().st_ino
                        (state / 'memory/constitution.md').write_text('User principles\n')
                        offline = self.f.base / 'offline-authority'
                        if unavailable:
                            authority.rename(offline)
                        else:
                            (authority / relative).write_bytes(b'Changed source after interruption')
                        try:
                            before = snapshot(state)
                            self.f.runpy('init_project.py', '--mode', mode, '--feature', '001-one', project=project, ok=False)
                            self.assertTrue(target.is_dir())
                            self.assertEqual(target.stat().st_ino, identity)
                            self.assertEqual(pending.read_bytes(), intent)
                            self.assertEqual(snapshot(state), before)
                            target.rmdir()
                            result = self.f.init(project, '--mode', mode, '--feature', '001-one')
                            self.assertFalse(pending.exists())
                            self.assertEqual(target.read_bytes(), expected)
                            self.assertIn(relative, result['imported'])
                            self.assertEqual((state / 'memory/constitution.md').read_text(), 'User principles\n')
                            self.assertIn('memory/constitution.md', result['preserved_imports'])
                        finally:
                            if unavailable:
                                offline.rename(authority)
                            else:
                                (authority / relative).write_bytes(expected)

    def test_seed_parent_files_stop_preview_and_preserve_intent(self):
        self.f.feature(self.f.main)
        for number, mode in enumerate(('auto', 'local')):
            with self.subTest(mode=mode):
                project = self.f.base / ('seed-parent-' + str(number))
                self.f.git('worktree', 'add', '-q', '-b', project.name, str(project))
                relative = 'specs/001-one/spec.md'
                self.interrupted_import(project, relative)
                state = project / '.sdlc'
                pending = state / '.init-pending.json'
                target = state / 'specs/001-one'
                target.rmdir()
                target.write_text('User file where a directory is required')
                before = snapshot(state)
                for flags in (['--dry-run'], []):
                    self.f.runpy('init_project.py', '--mode', mode, '--feature', '001-one', *flags, project=project, ok=False)
                    self.assertEqual(snapshot(state), before)
                    self.assertTrue(pending.is_file())
                target.unlink()
                self.f.init(project, '--mode', mode, '--feature', '001-one')
                self.assertEqual((state / relative).read_bytes(), (self.f.main / '.sdlc' / relative).read_bytes())
                self.assertFalse(pending.exists())

    def test_candidate_numbering_uses_same_legacy_fallback_and_modern_priority(self):
        cases = [({}, 'sequential'), ({'branch_numbering': 'timestamp'}, 'timestamp'),
                 ({'branch_numbering': 'unsupported'}, None), ({'branch_numbering': None}, None),
                 ({'feature_numbering': 'timestamp', 'branch_numbering': 'unsupported'}, 'timestamp'),
                 ({'feature_numbering': 'unsupported', 'branch_numbering': 'timestamp'}, None),
                 ({'feature_numbering': None, 'branch_numbering': 'timestamp'}, None),
                 ({'feature_numbering': '', 'branch_numbering': 'timestamp'}, None)]
        for number, (selected, expected) in enumerate(cases):
            with self.subTest(settings=selected):
                project = self.f.base / ('options-' + str(number))
                project.mkdir()
                self.f.init(project)
                config = project / '.sdlc/init-options.json'
                plan = self.f.prepare(project, kind='edit', paths=['init-options.json'])
                candidate = dict(script='sh', sdlc_layout=1, **selected)
                self.f.replace(plan, 'init-options.json', json.dumps(candidate))
                before = config.read_bytes(), config.stat().st_mode, config.stat().st_mtime_ns
                result = self.f.apply(plan, project, ok=expected is not None)
                if expected is None:
                    self.assertIn('unsupported initialization settings', result.stderr)
                    self.assertEqual((config.read_bytes(), config.stat().st_mode, config.stat().st_mtime_ns), before)
                    self.assertEqual(json.loads((Path(plan['transaction']) / 'manifest.json').read_text())['status'], 'prepared')
                else:
                    self.assertEqual(result['status'], 'applied')
                    self.f.binding(project)
                    self.f.prepare(project, kind='edit', paths=['init-options.json'])
                    self.f.init(project)
                    self.assertEqual(json.loads(config.read_text())['feature_numbering'], expected)
