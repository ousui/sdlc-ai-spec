"""Storage contracts on disposable real Git worktrees; no agent or business data."""
from __future__ import annotations

import importlib.util
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'dist'
SCRIPTS = PACKAGE / 'scripts/python'
sys.path.insert(0, str(SCRIPTS))
import sdlc_store as store
import store_changes as changes


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and not p.is_symlink() and '.git' not in p.parts and 'transactions' not in p.parts}


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-storage-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.main = self.base / 'main project'
        self.main.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('SDLC_', 'GIT_'))}
        self.git('init', '-q', str(self.main), cwd=self.base)
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'fixture', '--allow-empty')
        self.a, self.b = self.base / 'worktree a', self.base / 'worktree b'
        self.git('worktree', 'add', '-q', '-b', 'a', str(self.a))
        self.git('worktree', 'add', '-q', '-b', 'b', str(self.b))
        self.init(self.main)
        (self.main / '.sdlc/memory/constitution.md').write_text('Main principles\n')
        (self.main / '.sdlc/memory/long-term.md').write_text('Shared project fact\n')

    def git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.main, env=self.env,
                              capture_output=True, text=True, check=True)

    def runpy(self, name, *args, project=None, cwd=None, ok=True):
        project = project or self.main
        command = [sys.executable, '-I', '-B', str(SCRIPTS / name), *args, '--project', str(project)]
        if name in ('init_project.py', 'project_status.py'):
            command.append('--json')
        result = subprocess.run(command, cwd=cwd or project, env=self.env, text=True, capture_output=True, timeout=30)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def init(self, project, *args):
        return self.runpy('init_project.py', *args, project=project)

    def binding(self, project):
        return self.runpy('sdlc_store.py', 'resolve', project=project)

    def prepare(self, project=None, kind='collect', sources=(), features=(), paths=()):
        args = ['prepare', '--kind', kind]
        for option, values in (('--source', sources), ('--feature', features), ('--path', paths)):
            for value in values:
                args.extend((option, str(value)))
        return self.runpy('store_changes.py', *args, project=project)

    def apply(self, plan, project=None, ok=True):
        return self.runpy('store_changes.py', 'apply', '--transaction', plan['transaction'], project=project, ok=ok)

    def replace(self, plan, name, text):
        path = Path(plan['proposal'])
        proposal = json.loads(path.read_text())
        proposal[name] = {'action': 'replace', 'text': text}
        path.write_text(json.dumps(proposal))

    def feature(self, project, name='001-one'):
        state = Path(self.binding(project)['SDLC_DIR'])
        feature = state / 'specs' / name
        feature.mkdir(parents=True, exist_ok=True)
        (feature / 'spec.md').write_text('Feature ' + name)
        return feature

    def test_shared_default_discovery_requires_choice_and_is_read_only(self):
        before = files(self.main)
        result = self.init(self.a)
        self.assertEqual(result['status'], 'needs_choice')
        self.assertEqual(result['AUTHORITY_DIR'], str(self.main / '.sdlc'))
        self.assertFalse((self.a / '.sdlc').exists())
        self.assertEqual(files(self.main), before)
        self.init(self.a, '--mode', 'shared')
        self.assertFalse((self.a / '.sdlc').exists())

    def test_shared_normal_edit_writes_main_without_collect_permission(self):
        plan = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'Shared update')
        self.apply(plan, self.a)
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'Shared update')
        self.assertFalse((self.a / '.sdlc').exists())
        self.assertFalse(self.binding(self.a)['can_collect'])

    def test_local_default_import_only_knowledge_and_preserves_provenance(self):
        self.feature(self.main)
        (self.main / '.sdlc/feature.json').write_text('{"feature_directory":".sdlc/specs/001-one"}')
        (self.main / '.sdlc/memory/private.md').write_text('not shared')
        result = self.init(self.a, '--mode', 'local')
        state = self.a / '.sdlc'
        self.assertEqual((state / 'memory/constitution.md').read_bytes(), (self.main / '.sdlc/memory/constitution.md').read_bytes())
        self.assertEqual((state / 'memory/.constitution-template.json').read_bytes(), (self.main / '.sdlc/memory/.constitution-template.json').read_bytes())
        self.assertFalse((state / 'memory/private.md').exists())
        self.assertFalse((state / 'feature.json').exists())
        self.assertEqual(list((state / 'specs').iterdir()), [])
        self.assertEqual(result['constitution_source'], 'authority-import')
        before = files(state)
        self.init(self.a)
        self.assertEqual(files(state), before)

    def test_selected_requirement_import_preserves_artifacts_without_selection(self):
        feature = self.feature(self.main)
        (feature / 'tasks.md').write_text('- [x] T001 Worktree evidence only')
        (feature / 'contracts').mkdir()
        (feature / 'contracts/api.json').write_text('{}')
        self.init(self.a, '--mode', 'local', '--feature', '001-one')
        self.assertEqual(files(feature), files(self.a / '.sdlc/specs/001-one'))
        self.assertFalse((self.a / '.sdlc/feature.json').exists())

    def test_local_has_priority_and_never_falls_back(self):
        self.init(self.a, '--mode', 'local', '--seed', 'none')
        self.assertEqual(self.binding(self.a)['SDLC_DIR'], str(self.a / '.sdlc'))
        (self.a / '.sdlc/init-options.json').write_text('{invalid')
        before = files(self.main)
        self.runpy('sdlc_store.py', 'resolve', project=self.a, ok=False)
        self.assertEqual(files(self.main), before)
        self.runpy('init_project.py', '--mode', 'shared', project=self.a, ok=False)

    def test_local_cannot_select_authority_feature_or_collect(self):
        feature = self.feature(self.main)
        self.init(self.a, '--mode', 'local')
        self.runpy('sdlc_store.py', 'feature', '--value', str(feature), '--persist', project=self.a, ok=False)
        self.runpy('sdlc_store.py', 'resolve', project=self.main, cwd=self.a, ok=False)
        self.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source', str(self.a / '.sdlc'), project=self.a, ok=False)
        self.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source', str(self.a / '.sdlc'), project=self.main, cwd=self.a, ok=False)

    def test_shared_feature_selections_are_isolated_and_status_is_read_only(self):
        self.feature(self.main, '001-one')
        self.feature(self.main, '002-two')
        for root, name in ((self.main, '001-one'), (self.a, '002-two')):
            self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/' + name, '--persist', project=root)
        before = files(self.main)
        a = self.runpy('project_status.py', project=self.a)
        b = self.runpy('project_status.py', project=self.b)
        self.assertTrue(a['selection']['path'].endswith('002-two'))
        self.assertEqual(b['selection']['state'], 'not_selected')
        self.assertEqual(a['project']['root'], str(self.a))
        self.assertEqual(files(self.main), before)

    def test_shell_writers_use_authority_and_keep_code_root(self):
        self.feature(self.main)
        env = dict(self.env, SDLC_INIT_DIR=str(self.a), SDLC_FEATURE_DIRECTORY='.sdlc/specs/001-one')
        result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/setup-plan.sh'), '--json'],
                                cwd=self.a, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.main / '.sdlc/specs/001-one/plan.md').exists())
        self.assertFalse((self.a / '.sdlc').exists())
        self.assertEqual(self.binding(self.a)['PROJECT_ROOT'], str(self.a))
        self.assertFalse((self.main / '.sdlc/.write-lock').exists())

    def test_nested_project_maps_to_same_module_in_main(self):
        for root in (self.main, self.a):
            (root / 'module').mkdir()
        self.init(self.main / 'module')
        self.assertEqual(self.binding(self.a / 'module')['SDLC_DIR'], str(self.main / 'module/.sdlc'))

    def test_designated_authority_and_registered_source(self):
        project = self.base / 'standalone'; project.mkdir()
        authority = self.base / 'central-data'
        source = self.a / '.sdlc'
        self.init(self.a, '--mode', 'local')
        self.runpy('sdlc_store.py', 'register', '--authority', str(authority), '--source', str(source), project=project)
        self.init(project, '--mode', 'shared')
        self.assertTrue((authority / 'memory/constitution.md').exists())
        binding = self.binding(project)
        self.assertEqual(binding['SDLC_DIR'], str(authority))
        self.assertIn(str(source), binding['sources'])
        self.runpy('sdlc_store.py', 'register', '--authority', str(self.base / 'other'), project=project, ok=False)

    def test_registration_rejects_file_authority_without_leaving_a_registry(self):
        target = self.base / 'existing-document.md'
        target.write_bytes(b'Preserve this document\n')
        before = target.read_bytes(), target.stat().st_mode, target.stat().st_mtime_ns
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run):
                project = self.base / ('register-' + str(dry_run))
                project.mkdir()
                args = ['--dry-run'] if dry_run else []
                result = self.runpy('sdlc_store.py', 'register', '--authority', str(target),
                                    *args, project=project, ok=False)
                self.assertIn('Authority must be a directory', result.stderr)
                self.assertFalse((project / '.sdlc').exists())
                self.assertEqual((target.read_bytes(), target.stat().st_mode, target.stat().st_mtime_ns), before)
                # A rejected path must not poison the next valid registration.
                authority = self.base / ('valid-authority-' + str(dry_run))
                self.runpy('sdlc_store.py', 'register', '--authority', str(authority), project=project)
                self.init(project, '--mode', 'shared')
                self.assertEqual(self.binding(project)['SDLC_DIR'], str(authority))

    def test_registration_accepts_an_existing_authority_directory(self):
        project = self.base / 'existing-authority-project'
        project.mkdir()
        authority = self.base / 'existing-authority'
        (authority / 'memory').mkdir(parents=True)
        constitution = authority / 'memory/constitution.md'
        constitution.write_bytes(b'Existing designated principles\n')
        self.runpy('sdlc_store.py', 'register', '--authority', str(authority), project=project)
        self.init(project, '--mode', 'shared')
        self.assertEqual(self.binding(project)['SDLC_DIR'], str(authority))
        self.assertEqual(constitution.read_bytes(), b'Existing designated principles\n')

    def test_worktree_can_initialize_blank_authority_without_import(self):
        shutil.rmtree(self.main / '.sdlc')
        self.init(self.a, '--mode', 'shared')
        self.assertTrue((self.main / '.sdlc/memory/constitution.md').exists())
        self.assertFalse((self.a / '.sdlc').exists())

    def test_main_missing_authority_offers_collect_and_can_bootstrap(self):
        self.init(self.a, '--mode', 'local')
        shutil.rmtree(self.main / '.sdlc')
        self.assertEqual(self.init(self.main)['status'], 'needs_choice')
        plan = self.prepare(sources=[self.a / '.sdlc'])
        self.apply(plan)
        self.init(self.main)
        self.assertEqual((self.main / '.sdlc/memory/constitution.md').read_text(), 'Main principles\n')

    def test_collect_conflict_requires_candidate_and_preserves_sources(self):
        self.init(self.a, '--mode', 'local')
        (self.a / '.sdlc/memory/constitution.md').write_text('Alternate principle')
        before = files(self.a)
        plan = self.prepare(sources=[self.a / '.sdlc'])
        self.apply(plan, ok=False)
        self.assertEqual((self.main / '.sdlc/memory/constitution.md').read_text(), 'Main principles\n')
        self.replace(plan, 'memory/constitution.md', 'Reviewed combined principle')
        self.apply(plan)
        self.assertEqual(files(self.a), before)
        self.assertEqual(self.apply(plan)['status'], 'already_applied')

    def test_count_only_sources_with_actual_selected_differences(self):
        for root in (self.a, self.b):
            self.init(root, '--mode', 'local')
        (self.a / '.sdlc/memory/long-term.md').write_text('a')
        plan = self.prepare(sources=[self.a / '.sdlc', self.b / '.sdlc'])
        self.assertFalse(plan['multiple_sources'])
        (self.b / '.sdlc/memory/long-term.md').write_text('b')
        plan = self.prepare(sources=[self.a / '.sdlc', self.b / '.sdlc'])
        self.assertTrue(plan['multiple_sources'])
        self.assertEqual(len(plan['changed_sources']), 2)

    def test_source_and_target_changes_invalidate_candidate(self):
        self.init(self.a, '--mode', 'local')
        (self.a / '.sdlc/memory/long-term.md').write_text('source version')
        plan = self.prepare(sources=[self.a / '.sdlc'])
        self.replace(plan, 'memory/long-term.md', 'merged')
        (self.a / '.sdlc/memory/long-term.md').write_text('new source')
        self.assertIn('Source changed', self.apply(plan, ok=False).stderr)
        plan = self.prepare(sources=[self.a / '.sdlc'])
        self.replace(plan, 'memory/long-term.md', 'merged')
        (self.main / '.sdlc/memory/long-term.md').write_text('new authority')
        self.assertIn('Target changed', self.apply(plan, ok=False).stderr)

    def test_absence_does_not_delete_and_requirements_are_opt_in(self):
        self.init(self.a, '--mode', 'local')
        self.feature(self.a)
        (self.a / '.sdlc/memory/long-term.md').unlink()
        plan = self.prepare(sources=[self.a / '.sdlc'])
        self.apply(plan)
        self.assertTrue((self.main / '.sdlc/memory/long-term.md').exists())
        self.assertFalse((self.main / '.sdlc/specs/001-one').exists())
        plan = self.prepare(sources=[self.a / '.sdlc'], features=['001-one'])
        self.apply(plan)
        self.assertTrue((self.main / '.sdlc/specs/001-one/spec.md').exists())

    def test_import_prepare_requires_local_store_without_switching_shared_binding(self):
        self.feature(self.main)
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=self.a)
        binding = self.binding(self.a)
        state = self.main / '.sdlc'
        before = files(state)
        metadata = {p: (p.stat().st_mode, p.stat().st_mtime_ns) for p in (state, *state.rglob('*'))}
        result = self.runpy('store_changes.py', 'prepare', '--kind', 'import', project=self.a, ok=False)
        self.assertIn('existing local store', result.stderr)
        self.assertFalse((self.a / '.sdlc').exists())
        self.assertEqual(self.binding(self.a), binding)
        self.assertEqual(files(state), before)
        self.assertEqual({p: (p.stat().st_mode, p.stat().st_mtime_ns) for p in (state, *state.rglob('*'))}, metadata)
        # First import still uses INIT's saved-intent publication, not a blank store.
        initialized = self.init(self.a, '--mode', 'local')
        self.assertEqual(initialized['constitution_source'], 'authority-import')
        self.assertEqual((self.a / '.sdlc/memory/constitution.md').read_bytes(), before['memory/constitution.md'])

    def test_import_refresh_is_authority_to_local_only(self):
        self.init(self.a, '--mode', 'local')
        (self.main / '.sdlc/memory/long-term.md').write_text('new authority')
        main_before = files(self.main)
        plan = self.prepare(self.a, kind='import')
        self.replace(plan, 'memory/long-term.md', 'new authority')
        self.apply(plan, self.a)
        self.assertEqual(files(self.main), main_before)
        self.assertEqual((self.a / '.sdlc/memory/long-term.md').read_text(), 'new authority')

    def test_unregistered_and_symlink_sources_are_rejected(self):
        foreign = self.base / 'foreign'; foreign.mkdir()
        self.runpy('store_changes.py', 'prepare', '--source', str(foreign), ok=False)
        self.init(self.a, '--mode', 'local')
        (self.a / '.sdlc/memory/long-term.md').unlink()
        (self.a / '.sdlc/memory/long-term.md').symlink_to(self.main / '.sdlc/memory/long-term.md')
        self.runpy('store_changes.py', 'prepare', '--source', str(self.a / '.sdlc'), ok=False)

    def test_proposal_cannot_escape_scope_or_change_local_authority_selection(self):
        plan = self.prepare(kind='edit', paths=['memory/long-term.md'])
        Path(plan['proposal']).write_text(json.dumps({'../escape': {'action': 'replace', 'text': 'bad'}}))
        self.apply(plan, ok=False)
        self.assertFalse((self.main / 'escape').exists())
        self.init(self.a, '--mode', 'local')
        feature = self.feature(self.main)
        plan = self.prepare(self.a, kind='edit', paths=['feature.json'])
        self.replace(plan, 'feature.json', json.dumps({'feature_directory': str(feature)}))
        self.apply(plan, self.a, ok=False)

    def test_write_lock_rejects_simultaneous_script_and_transaction_writes(self):
        plan = self.prepare(kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'candidate')
        with store.write_lock(self.main / '.sdlc'):
            self.assertIn('write lock', self.apply(plan, ok=False).stderr)
        self.apply(plan)

    def test_failed_publication_rolls_back_without_touching_source(self):
        plan = self.prepare(kind='edit', paths=['memory/long-term.md', 'memory/constitution.md'])
        self.replace(plan, 'memory/long-term.md', 'candidate memory')
        self.replace(plan, 'memory/constitution.md', 'candidate constitution')
        before = files(self.main)
        publish = changes.publish_data
        fired = False
        def fail_once(path, data, expected):
            nonlocal fired
            if path == self.main / '.sdlc/memory/constitution.md' and not fired:
                fired = True
                raise OSError('fixture failure')
            return publish(path, data, expected)
        with mock.patch.object(changes, 'publish_data', side_effect=fail_once):
            with self.assertRaises(OSError):
                changes.apply(self.main, Path(plan['transaction']))
        self.assertEqual(files(self.main), before)
        self.assertEqual(json.loads((Path(plan['transaction']) / 'manifest.json').read_text())['status'], 'recovered')

    def test_recovery_refuses_to_overwrite_later_edits(self):
        plan = self.prepare(kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'candidate')
        self.apply(plan)
        manifest_path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(manifest_path.read_text()); manifest['status'] = 'applying'
        manifest_path.write_text(json.dumps(manifest))
        (self.main / '.sdlc/memory/long-term.md').write_text('later user edit')
        result = self.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], ok=False)
        self.assertIn('later edit', result.stderr)
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'later user edit')

    def test_contract_json_edit_is_not_misread_as_workspace_selection(self):
        plan = self.prepare(kind='edit', paths=['specs/001-api/contracts/api.json'])
        self.replace(plan, 'specs/001-api/contracts/api.json', '{"openapi":"3.1.0"}')
        self.apply(plan)
        self.assertEqual(json.loads((self.main / '.sdlc/specs/001-api/contracts/api.json').read_text()), {'openapi': '3.1.0'})

    def test_missing_local_requirement_is_not_read_from_authority(self):
        self.feature(self.main)
        self.init(self.a, '--mode', 'local')
        result = self.runpy('project_status.py', '--feature', '.sdlc/specs/001-one', project=self.a, ok=False)
        report = json.loads(result.stdout)
        self.assertEqual(report['selection']['state'], 'missing')
        self.assertTrue(report['selection']['path'].startswith(str(self.a)))

    def test_interrupted_application_can_be_recovered(self):
        plan = self.prepare(kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'candidate')
        self.apply(plan)
        manifest_path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(manifest_path.read_text()); manifest['status'] = 'applying'
        manifest_path.write_text(json.dumps(manifest))
        lock = self.main / '.sdlc/.write-lock'
        lock.mkdir(); (lock / 'owner').write_text('dead-owner'); (lock / 'pid').write_text('2147483647')
        result = self.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'])
        self.assertEqual(result['status'], 'recovered')
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'Shared project fact\n')
        self.assertFalse(lock.exists())

    def test_forged_lock_token_does_not_bypass_script_lock(self):
        self.feature(self.main)
        env = dict(self.env, SDLC_INIT_DIR=str(self.main), SDLC_FEATURE_DIRECTORY='.sdlc/specs/001-one', SDLC_STORE_LOCK_TOKEN='not-issued')
        result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/setup-plan.sh'), '--json'], cwd=self.main,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.main / '.sdlc/specs/001-one/plan.md').exists())

    def test_blank_init_dry_run_and_missing_requirement_do_not_write(self):
        before = files(self.main)
        self.init(self.a, '--mode', 'local', '--dry-run')
        self.assertFalse((self.a / '.sdlc').exists())
        self.runpy('init_project.py', '--mode', 'local', '--feature', 'missing', project=self.a, ok=False)
        self.assertFalse((self.a / '.sdlc').exists())
        self.assertEqual(files(self.main), before)

    def test_text_discovery_and_choice_are_successful_read_only_results(self):
        before = files(self.main)
        for flags, expected in ((['--discover'], 'discovered:'), ([], 'needs_choice:')):
            result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'init_project.py'),
                                     '--project', str(self.a), *flags], cwd=self.a, env=self.env,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(expected, result.stdout)
        self.assertFalse((self.a / '.sdlc').exists())
        self.assertEqual(files(self.main), before)

    def test_new_local_import_rejects_invalid_authority(self):
        (self.main / '.sdlc/init-options.json').write_text('{invalid')
        self.runpy('init_project.py', '--mode', 'local', project=self.a, ok=False)
        self.assertFalse((self.a / '.sdlc').exists())

    def test_collection_recovery_survives_removed_source_worktree(self):
        self.init(self.a, '--mode', 'local')
        (self.a / '.sdlc/memory/long-term.md').write_text('source update')
        plan = self.prepare(sources=[self.a / '.sdlc'])
        self.replace(plan, 'memory/long-term.md', 'reviewed update')
        self.apply(plan)
        manifest_path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['status'] = 'applying'
        manifest_path.write_text(json.dumps(manifest))
        self.git('worktree', 'remove', '--force', str(self.a))
        result = self.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'])
        self.assertEqual(result['status'], 'recovered')
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'Shared project fact\n')

    def test_ordinary_edit_ignores_unrelated_large_artifact(self):
        archived = self.feature(self.main, '002-archive') / 'large-contract.json'
        content = b'{"description":"' + b'x' * (8 * 1024 * 1024) + b'"}'
        archived.write_bytes(content)
        plan = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'Small reviewed edit')
        self.apply(plan, self.a)
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'Small reviewed edit')
        self.assertEqual(archived.read_bytes(), content)
        manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
        self.assertNotIn('specs/002-archive/large-contract.json', manifest['before'])

    def test_disjoint_edits_and_other_workspace_selection_do_not_conflict(self):
        self.feature(self.main)
        first = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
        self.replace(first, 'memory/long-term.md', 'First workspace update')
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=self.b)
        second = self.prepare(self.b, kind='edit', paths=['specs/001-one/spec.md'])
        self.replace(second, 'specs/001-one/spec.md', 'Second workspace update')
        self.apply(first, self.a)
        self.apply(second, self.b)
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'First workspace update')
        self.assertEqual((self.main / '.sdlc/specs/001-one/spec.md').read_text(), 'Second workspace update')

    def test_ordinary_edit_still_rejects_a_changed_target(self):
        first = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
        second = self.prepare(self.b, kind='edit', paths=['memory/long-term.md'])
        self.replace(first, 'memory/long-term.md', 'First update')
        self.replace(second, 'memory/long-term.md', 'Stale update')
        self.apply(first, self.a)
        self.assertIn('Target changed', self.apply(second, self.b, ok=False).stderr)
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'First update')

    def test_ordinary_edit_still_checks_its_own_selection_and_options(self):
        self.feature(self.main)
        for binding in ('selection', 'options'):
            with self.subTest(binding=binding):
                plan = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
                self.replace(plan, 'memory/long-term.md', 'Stale update')
                if binding == 'selection':
                    self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=self.a)
                else:
                    path = self.main / '.sdlc/init-options.json'
                    data = json.loads(path.read_text())
                    data['feature_numbering'] = 'timestamp'
                    path.write_text(json.dumps(data))
                self.assertIn('Target changed', self.apply(plan, self.a, ok=False).stderr)
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'Shared project fact\n')

    def test_shared_edit_and_import_ignore_main_selection(self):
        self.feature(self.main)
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=self.a)
        (self.main / '.sdlc/feature.json').write_text('{invalid')
        self.assertEqual(self.binding(self.a)['mode'], 'shared')
        plan = self.prepare(self.a, kind='edit', paths=['specs/001-one/spec.md'])
        self.replace(plan, 'specs/001-one/spec.md', 'Worktree-specific edit')
        self.apply(plan, self.a)
        self.assertEqual((self.main / '.sdlc/specs/001-one/spec.md').read_text(), 'Worktree-specific edit')
        self.assertEqual((self.main / '.sdlc/feature.json').read_text(), '{invalid')
        self.init(self.b, '--mode', 'local')
        self.assertFalse((self.b / '.sdlc/feature.json').exists())
        self.assertEqual((self.b / '.sdlc/memory/constitution.md').read_text(), 'Main principles\n')

    def test_local_operations_survive_invalid_main_registry(self):
        self.init(self.a, '--mode', 'local')
        feature = self.feature(self.a)
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=self.a)
        for invalid in ('{invalid', '{"schema":99}', '{"schema":1,"sources":[1]}'):
            with self.subTest(registry=invalid):
                (self.main / '.sdlc/store.json').write_text(invalid)
                main_before = files(self.main)
                binding = self.binding(self.a)
                self.assertEqual(binding['SDLC_DIR'], str(self.a / '.sdlc'))
                self.assertIsNone(binding['AUTHORITY_DIR'])
                self.assertTrue(binding['authority_error'])
                plan = self.prepare(self.a, kind='edit', paths=['specs/001-one/spec.md'])
                self.replace(plan, 'specs/001-one/spec.md', 'Local update ' + invalid)
                self.apply(plan, self.a)
                self.assertEqual(feature.joinpath('spec.md').read_text(), 'Local update ' + invalid)
                self.init(self.a)
                report = self.runpy('project_status.py', project=self.a)
                self.assertEqual(report['selection']['path'], str(feature))
                self.assertEqual(files(self.main), main_before)

    def test_local_candidate_survives_main_registry_failure_and_repair(self):
        self.init(self.a, '--mode', 'local')
        registry = self.main / '.sdlc/store.json'
        for text in ('{invalid', None):
            plan = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
            self.replace(plan, 'memory/long-term.md', 'Local update ' + str(text))
            if text is None:
                registry.unlink()
            else:
                registry.write_text(text)
            self.apply(plan, self.a)
            self.assertEqual((self.a / '.sdlc/memory/long-term.md').read_text(), 'Local update ' + str(text))

    def test_unknown_authority_does_not_allow_import_or_external_feature_targets(self):
        self.init(self.a, '--mode', 'local')
        external = self.base / 'designated-authority'
        shutil.copytree(self.main / '.sdlc', external)
        (self.main / '.sdlc/store.json').write_text('{invalid')
        before = files(external)
        for target in (self.main / '.sdlc/specs/001-one', external / 'specs/001-one'):
            self.runpy('sdlc_store.py', 'feature', '--value', str(target), '--persist', project=self.a, ok=False)
        (self.a / '.sdlc/specs/alias').symlink_to(external / 'specs', target_is_directory=True)
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/alias', '--persist', project=self.a, ok=False)
        self.runpy('store_changes.py', 'prepare', '--kind', 'import', project=self.a, ok=False)
        self.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source', str(self.a / '.sdlc'), project=self.a, ok=False)
        self.runpy('sdlc_store.py', 'resolve', project=self.main, cwd=self.a, ok=False)
        self.runpy('sdlc_store.py', 'resolve', project=self.b, ok=False)
        self.assertEqual(files(external), before)
        self.assertFalse((self.a / '.sdlc/feature.json').exists())

    def test_unknown_authority_cannot_be_hidden_behind_a_local_root_alias(self):
        (self.main / '.sdlc/store.json').write_text('{invalid')
        (self.a / '.sdlc').symlink_to(self.main / '.sdlc', target_is_directory=True)
        self.runpy('sdlc_store.py', 'resolve', project=self.a, ok=False)

    def test_local_store_cannot_alias_an_authority_subdirectory(self):
        self.init(self.a, '--mode', 'local')
        local = self.a / '.sdlc'
        nested = self.main / '.sdlc/specs/001-archive/local-copy'
        nested.parent.mkdir()
        local.rename(nested)
        local.symlink_to(nested, target_is_directory=True)
        before = files(self.main)
        self.runpy('sdlc_store.py', 'resolve', project=self.a, ok=False)
        self.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', 'memory/long-term.md', project=self.a, ok=False)
        self.runpy('init_project.py', project=self.a, ok=False)
        self.assertEqual(files(self.main), before)

    def test_local_edit_rechecks_overlap_before_apply(self):
        self.init(self.a, '--mode', 'local')
        plan = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'Must not reach authority')
        local = self.a / '.sdlc'
        nested = self.main / '.sdlc/specs/local-copy'
        local.rename(nested)
        local.symlink_to(nested, target_is_directory=True)
        before = files(self.main)
        self.apply(plan, self.a, ok=False)
        self.assertEqual(files(self.main), before)

    def test_authority_cannot_be_nested_inside_independent_local_storage(self):
        self.init(self.a, '--mode', 'local')
        nested = self.a / '.sdlc/specs/central'
        shutil.copytree(self.main / '.sdlc', nested)
        (self.main / '.sdlc/store.json').write_text(json.dumps({'schema': 1, 'authority': str(nested)}))
        before = files(self.a)
        self.runpy('store_changes.py', 'prepare', '--kind', 'edit',
                   '--path', 'specs/central/memory/long-term.md', project=self.a, ok=False)
        self.assertEqual(files(self.a), before)

    def test_disjoint_local_store_alias_still_allows_local_edit(self):
        self.init(self.a, '--mode', 'local')
        local = self.a / '.sdlc'
        external = self.base / 'independent-data'
        local.rename(external)
        local.symlink_to(external, target_is_directory=True)
        before = files(self.main)
        plan = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'Independent update')
        self.apply(plan, self.a)
        self.assertEqual((external / 'memory/long-term.md').read_text(), 'Independent update')
        self.assertEqual(files(self.main), before)

    def test_shared_init_validates_own_selection_without_reading_main_selection(self):
        self.feature(self.main)
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=self.a)
        pointer = Path(self.binding(self.a)['FEATURE_JSON'])
        selection = pointer.read_bytes()
        main_pointer = self.main / '.sdlc/feature.json'
        main_pointer.write_text('{invalid')
        (self.main / '.sdlc/README.md').unlink()
        self.assertEqual(self.init(self.a, '--mode', 'shared')['status'], 'completed')
        self.assertEqual(pointer.read_bytes(), selection)
        self.assertEqual(main_pointer.read_text(), '{invalid')
        self.assertFalse((self.a / '.sdlc').exists())

    def test_shared_init_rejects_invalid_own_selection_before_writing(self):
        pointer = Path(self.binding(self.a)['FEATURE_JSON'])
        pointer.parent.mkdir(parents=True)
        pointer.write_text('{invalid')
        (self.main / '.sdlc/README.md').unlink()
        before = files(self.main)
        self.runpy('init_project.py', '--mode', 'shared', project=self.a, ok=False)
        self.assertEqual(files(self.main), before)

    def test_init_checks_local_feature_target_with_the_common_resolver(self):
        self.init(self.a, '--mode', 'local')
        target = self.feature(self.main)
        (self.a / '.sdlc/feature.json').write_text(json.dumps({'feature_directory': str(target)}))
        before = files(self.main)
        self.runpy('init_project.py', project=self.a, ok=False)
        self.assertEqual(files(self.main), before)

    def test_explicit_edit_and_selection_can_replace_malformed_old_selection(self):
        feature = self.feature(self.main)
        pointer = Path(self.binding(self.a)['FEATURE_JSON'])
        pointer.parent.mkdir(parents=True)
        pointer.write_text('{invalid')
        plan = self.prepare(self.a, kind='edit', paths=['specs/001-one/spec.md'])
        self.replace(plan, 'specs/001-one/spec.md', 'Explicit feature update')
        self.apply(plan, self.a)
        self.assertEqual((feature / 'spec.md').read_text(), 'Explicit feature update')
        self.assertEqual(pointer.read_text(), '{invalid')
        before = pointer.read_bytes(), pointer.stat().st_mtime_ns
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', project=self.a)
        self.assertEqual((pointer.read_bytes(), pointer.stat().st_mtime_ns), before)
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=self.a)
        self.assertEqual(json.loads(pointer.read_text()), {'feature_directory': '.sdlc/specs/001-one'})

    def test_unused_selection_does_not_hide_invalid_feature_or_store(self):
        self.init(self.a, '--mode', 'local')
        local_feature = self.feature(self.a)
        authority_feature = self.feature(self.main)
        (self.a / '.sdlc/feature.json').write_text('{invalid')
        before = files(self.main)
        self.runpy('sdlc_store.py', 'feature', project=self.a, ok=False)
        self.runpy('sdlc_store.py', 'feature', '--value', str(authority_feature), '--persist', project=self.a, ok=False)
        (self.a / '.sdlc/init-options.json').write_text('{invalid')
        self.runpy('sdlc_store.py', 'feature', '--value', str(local_feature), '--persist', project=self.a, ok=False)
        self.assertEqual(files(self.main), before)

    def test_current_directory_feature_is_valid_and_status_does_not_persist_it(self):
        (self.a / 'spec.md').write_text('# Worktree root feature')
        (self.a / 'plan.md').write_text('# Plan')
        before = files(self.main)
        for value in ('.', './'):
            with self.subTest(value=value):
                result = self.runpy('sdlc_store.py', 'feature', '--value', value, project=self.a)
                self.assertEqual(Path(result['FEATURE_DIR']).resolve(), self.a)
                report = self.runpy('project_status.py', '--feature', value, project=self.a)
                self.assertEqual(report['selection']['path'], str(self.a))
        self.assertEqual(files(self.main), before)
        self.assertFalse((self.a / '.sdlc').exists())

    def test_local_plan_cannot_follow_an_artifact_link_into_authority(self):
        self.init(self.a, '--mode', 'local')
        local = self.feature(self.a)
        authority = self.feature(self.main)
        for exists in (False, True):
            with self.subTest(target_exists=exists):
                target = authority / 'plan.md'
                if exists:
                    target.write_text('Main plan must survive')
                (local / 'plan.md').unlink(missing_ok=True)
                (local / 'plan.md').symlink_to(target)
                before = files(self.main)
                result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/setup-plan.sh'), '--json'],
                    cwd=self.a, env=dict(self.env, SDLC_FEATURE_DIRECTORY='.sdlc/specs/001-one'),
                    capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(files(self.main), before)
                self.assertFalse((self.a / '.sdlc/feature.json').exists())
                (local / 'plan.md').unlink()

    def test_local_path_guard_checks_each_artifact_target(self):
        self.init(self.a, '--mode', 'local')
        local = self.feature(self.a)
        authority = self.feature(self.main)
        (local / 'spec.md').unlink()
        before = files(self.main)
        for name in ('spec.md', 'plan.md', 'tasks.md', 'research.md', 'data-model.md',
                     'quickstart.md', 'contracts', 'checklists'):
            with self.subTest(artifact=name):
                link = local / name
                link.symlink_to(authority / name)
                try:
                    result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/project-paths.sh'),
                                             '--feature', '.sdlc/specs/001-one'], cwd=self.a, env=self.env,
                                            capture_output=True, text=True, timeout=30)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                finally:
                    link.unlink()
        self.assertEqual(files(self.main), before)

    def test_local_spec_creation_cannot_follow_an_artifact_link_into_authority(self):
        self.init(self.a, '--mode', 'local')
        local = self.feature(self.a)
        authority = self.feature(self.main)
        (local / 'spec.md').unlink()
        (authority / 'spec.md').unlink()
        (local / 'spec.md').symlink_to(authority / 'spec.md')
        before = files(self.main)
        result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/create-new-feature.sh'),
            '--json', '--allow-existing-branch', '--number', '1', '--short-name', 'one', 'A feature'],
            cwd=self.a, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(files(self.main), before)
        self.assertFalse((self.a / '.sdlc/feature.json').exists())

    def test_disjoint_artifact_alias_remains_usable_but_unknown_authority_stops(self):
        self.init(self.a, '--mode', 'local')
        local = self.feature(self.a)
        external = self.base / 'external-plan.md'
        (local / 'plan.md').symlink_to(external)
        command = ['bash', str(PACKAGE / 'scripts/bash/setup-plan.sh'), '--json']
        env = dict(self.env, SDLC_FEATURE_DIRECTORY='.sdlc/specs/001-one')
        before = files(self.main)
        result = subprocess.run(command, cwd=self.a, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(external.is_file())
        self.assertEqual(files(self.main), before)
        external.unlink()
        (self.main / '.sdlc/store.json').write_text('{invalid')
        result = subprocess.run(command, cwd=self.a, env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse(external.exists())

    def test_shared_selection_directory_alias_cannot_read_or_change_other_workspace(self):
        self.feature(self.main, '001-main')
        self.feature(self.main, '002-other')
        for project, name in ((self.main, '001-main'), (self.b, '002-other')):
            self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/' + name, '--persist', project=project)
        own = Path(self.binding(self.a)['FEATURE_JSON'])
        other = Path(self.binding(self.b)['FEATURE_JSON'])
        main = self.main / '.sdlc/feature.json'
        for target in (main.parent, other.parent, self.base / 'absent-selection'):
            with self.subTest(target=target.name):
                own.parent.unlink(missing_ok=True)
                own.parent.symlink_to(target, target_is_directory=True)
                before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (main, other)]
                self.runpy('sdlc_store.py', 'feature', project=self.a, ok=False)
                self.runpy('project_status.py', project=self.a, ok=False)
                self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/002-other',
                           '--persist', project=self.a, ok=False)
                result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/setup-plan.sh'), '--json'],
                    cwd=self.a, env=dict(self.env, SDLC_FEATURE_DIRECTORY='.sdlc/specs/002-other'),
                    capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual([(p.read_bytes(), p.stat().st_mtime_ns) for p in (main, other)], before)
                self.assertFalse((self.main / '.sdlc/specs/002-other/plan.md').exists())
                own.parent.unlink()
        self.assertFalse((self.base / 'absent-selection').exists())

    def test_shared_selection_leaf_alias_is_rejected_without_breaking_valid_selection(self):
        self.feature(self.main)
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist')
        own = Path(self.binding(self.a)['FEATURE_JSON'])
        own.parent.mkdir(parents=True)
        own.symlink_to(self.main / '.sdlc/feature.json')
        self.runpy('project_status.py', project=self.a, ok=False)
        result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/check-prerequisites.sh'),
            '--json', '--paths-only'], cwd=self.a, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        own.unlink()
        self.runpy('sdlc_store.py', 'feature', '--value', '.sdlc/specs/001-one', '--persist', project=self.a)
        main = self.main / '.sdlc/feature.json'
        before = main.read_bytes(), main.stat().st_mtime_ns
        report = self.runpy('project_status.py', project=self.a)
        self.assertTrue(report['selection']['path'].endswith('001-one'))
        self.assertEqual((main.read_bytes(), main.stat().st_mtime_ns), before)

    def test_selection_alias_introduced_before_publication_is_rechecked(self):
        self.feature(self.main)
        main = self.main / '.sdlc/feature.json'
        main.write_text('{"feature_directory":"previous"}')
        own = Path(self.binding(self.a)['FEATURE_JSON'])
        before = main.read_bytes(), main.stat().st_mtime_ns
        @contextmanager
        def changed_parent(state):
            own.parent.parent.mkdir(parents=True, exist_ok=True)
            own.parent.symlink_to(main.parent, target_is_directory=True)
            yield 'fixture-lock'
        argv = ['sdlc_store.py', 'feature', '--project', str(self.a), '--value',
                '.sdlc/specs/001-one', '--persist']
        with mock.patch.object(store, 'write_lock', changed_parent), mock.patch.object(sys, 'argv', argv):
            self.assertEqual(store.main(), 1)
        self.assertEqual((main.read_bytes(), main.stat().st_mtime_ns), before)

    def test_shared_edit_rejects_selection_alias_added_after_preparation(self):
        plan = self.prepare(self.a, kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'Must not publish')
        own = Path(self.binding(self.a)['FEATURE_JSON'])
        own.parent.parent.mkdir(parents=True, exist_ok=True)
        own.parent.symlink_to(self.main / '.sdlc', target_is_directory=True)
        before = files(self.main)
        self.apply(plan, self.a, ok=False)
        self.assertEqual(files(self.main), before)

    def test_selection_parent_is_rechecked_before_creating_directories(self):
        self.feature(self.main)
        own = Path(self.binding(self.a)['FEATURE_JSON'])
        external = self.base / 'external-selections'
        external.mkdir()
        @contextmanager
        def changed_parent(state):
            own.parent.parent.symlink_to(external, target_is_directory=True)
            yield 'fixture-lock'
        argv = ['sdlc_store.py', 'feature', '--project', str(self.a), '--value',
                '.sdlc/specs/001-one', '--persist']
        with mock.patch.object(store, 'write_lock', changed_parent), mock.patch.object(sys, 'argv', argv):
            self.assertEqual(store.main(), 1)
        self.assertEqual(list(external.iterdir()), [])

    def test_shared_absolute_store_addresses_keep_the_same_feature_after_persistence(self):
        feature = self.feature(self.main)
        alias = self.base / 'worktree alias'
        alias.symlink_to(self.a, target_is_directory=True)
        own = Path(self.binding(self.a)['FEATURE_JSON'])
        for prefix in (self.a, alias):
            for suffix in ('', '/.', '//'):
                with self.subTest(prefix=prefix.name, suffix=suffix):
                    value = str(prefix / '.sdlc/specs/001-one') + suffix
                    env = dict(self.env, SDLC_FEATURE_DIRECTORY=value)
                    result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/setup-plan.sh'), '--json'],
                        cwd=self.a, env=env, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(Path(json.loads(result.stdout)['FEATURE_DIR']).resolve(), feature)
                    self.assertTrue((feature / 'plan.md').is_file())
                    self.assertFalse((self.a / '.sdlc').exists())
                    before = own.read_bytes(), own.stat().st_mtime_ns
                    followup = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/check-prerequisites.sh'),
                        '--json', '--paths-only'], cwd=self.a, env=self.env, capture_output=True, text=True, timeout=30)
                    self.assertEqual(followup.returncode, 0, followup.stderr)
                    self.assertEqual(Path(json.loads(followup.stdout)['FEATURE_DIR']).resolve(), feature)
                    self.assertEqual((own.read_bytes(), own.stat().st_mtime_ns), before)
                    status = self.runpy('project_status.py', project=self.a)
                    self.assertEqual(Path(status['selection']['resolved_path']), feature)

    def test_designated_authority_maps_absolute_marker_without_writing_the_registry_directory(self):
        project = self.base / 'designated project'
        project.mkdir()
        authority = self.base / 'designated authority'
        self.runpy('sdlc_store.py', 'register', '--authority', str(authority), project=project)
        self.init(project)
        feature = self.feature(project)
        alias = self.base / 'designated project alias'
        alias.symlink_to(project, target_is_directory=True)
        before = files(project / '.sdlc')
        for prefix in (project, alias):
            with self.subTest(prefix=prefix.name):
                value = str(prefix / '.sdlc/specs/001-one') + '/.'
                result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash/setup-plan.sh'), '--json'],
                    cwd=project, env=dict(self.env, SDLC_FEATURE_DIRECTORY=value),
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(Path(json.loads(result.stdout)['FEATURE_DIR']).resolve(), feature)
                self.assertEqual(json.loads(result.stdout)['BRANCH'], '.')
                status = self.runpy('project_status.py', project=project)
                self.assertEqual(Path(status['selection']['resolved_path']), feature)
                self.assertEqual(files(project / '.sdlc'), before)

    def test_absolute_local_and_external_addresses_do_not_bypass_authority_isolation(self):
        self.init(self.a, '--mode', 'local')
        local = self.feature(self.a)
        authority = self.feature(self.main)
        alias = self.base / 'main alias'
        alias.symlink_to(self.main, target_is_directory=True)
        before = files(self.main)
        self.runpy('sdlc_store.py', 'feature', '--value', str(alias / '.sdlc/specs/001-one') + '/.',
                   '--persist', project=self.a, ok=False)
        self.assertEqual(files(self.main), before)
        external = self.base / 'external feature'
        external.mkdir()
        for target in (local, external):
            with self.subTest(target=target.name):
                value = str(target) + '/.'
                result = self.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.a)
                self.assertEqual(Path(result['FEATURE_DIR']).resolve(), target)
                followup = self.runpy('sdlc_store.py', 'feature', project=self.a)
                self.assertEqual(Path(followup['FEATURE_DIR']).resolve(), target)
        self.assertEqual(files(self.main), before)

    def test_same_absolute_alias_selection_keeps_prepared_edits_valid(self):
        feature = self.feature(self.main)
        (feature / 'plan.md').write_text('Existing plan')
        alias = self.base / 'main alias'
        alias.symlink_to(self.main, target_is_directory=True)
        value = str(alias / '.sdlc/specs/001-one') + '/.'
        pointer = self.main / '.sdlc/feature.json'
        pointer.write_text(json.dumps({'feature_directory': value}) + '\n')
        plan = self.prepare(kind='edit', paths=['memory/long-term.md'])
        self.replace(plan, 'memory/long-term.md', 'Reviewed local change')
        before = pointer.read_bytes(), pointer.stat().st_mtime_ns
        for script in ('check-prerequisites.sh', 'setup-plan.sh'):
            result = subprocess.run(['bash', str(PACKAGE / 'scripts/bash' / script), '--json'],
                cwd=self.main, env=dict(self.env, SDLC_FEATURE_DIRECTORY=value),
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((pointer.read_bytes(), pointer.stat().st_mtime_ns), before)
        self.runpy('sdlc_store.py', 'feature', '--value', value, '--persist')
        self.assertEqual((pointer.read_bytes(), pointer.stat().st_mtime_ns), before)
        self.apply(plan)
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), 'Reviewed local change')

    def test_status_reports_overlapping_local_alias_without_reading_authority_as_local(self):
        authority = self.main / '.sdlc'
        child = authority / 'archive'
        (child / 'memory').mkdir(parents=True)
        (child / 'specs').mkdir()
        for name in ('init-options.json', 'memory/constitution.md'):
            shutil.copy2(authority / name, child / name)
        for target in (authority, child, self.base):
            with self.subTest(target=target.name):
                link = self.a / '.sdlc'
                link.symlink_to(target, target_is_directory=True)
                before = files(self.main)
                try:
                    result = self.runpy('project_status.py', project=self.a, ok=False)
                    report = json.loads(result.stdout)
                    self.assertEqual(report['status'], 'error')
                    self.assertTrue(any('overlap authority' in w.get('message', '') for w in report['warnings']))
                    self.assertEqual(report['artifacts'], [])
                    self.assertEqual(files(self.main), before)
                finally:
                    link.unlink()

    def test_status_keeps_disjoint_local_store_alias_readable(self):
        target = self.base / 'independent data'
        shutil.copytree(self.main / '.sdlc', target)
        (self.a / '.sdlc').symlink_to(target, target_is_directory=True)
        before = files(target), files(self.main)
        report = self.runpy('project_status.py', project=self.a)
        self.assertEqual(report['status'], 'no_active_feature')
        self.assertEqual(report['binding']['mode'], 'local')
        self.assertEqual(report['warnings'], [])
        self.assertEqual((files(target), files(self.main)), before)


if __name__ == '__main__':
    unittest.main()
