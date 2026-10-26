"""Control-file isolation and ordinary knowledge aliases on disposable projects."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class ControlKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def shell_paths(self, project, feature=None):
        args = ['--feature', str(feature)] if feature is not None else []
        return subprocess.run(['bash', str(storage.PACKAGE / 'scripts/bash/project-paths.sh'), *args],
                              cwd=project, env=self.f.env, capture_output=True, text=True, timeout=30)

    def local_feature(self):
        self.f.init(self.f.a, '--mode', 'local')
        return self.f.feature(self.f.a)

    def knowledge_alias(self, name, *, shared=False, internal=False):
        if not shared:
            self.f.init(self.f.a, '--mode', 'local')
        state = Path(self.f.binding(self.f.a)['SDLC_DIR'])
        logical = state / name
        target = state / 'specs/knowledge-current.md' if internal else self.f.base / 'knowledge-current.md'
        logical.rename(target)
        logical.symlink_to(target)
        return logical, target

    def test_external_control_aliases_are_blocked_before_shell_or_transaction_writes(self):
        authority = self.f.base / 'authority'
        (self.f.main / '.sdlc').rename(authority)
        self.f.runpy('sdlc_store.py', 'register', '--authority', str(authority))
        feature = self.local_feature()
        self.f.init(self.f.b, '--mode', 'local')
        own = self.f.a / '.sdlc'
        other = self.f.b / '.sdlc'
        alias = feature / 'plan.md'
        targets = [self.f.main / '.sdlc/store.json', self.f.main / '.sdlc/feature.json',
                   other / 'feature.json', other / 'init-options.json', other / '.init-pending.json',
                   other / 'workspaces/another/feature.json', other / 'transactions/one/manifest.json',
                   other / 'memory/.constitution-template.json']
        before = storage.files(self.f.main), storage.files(other)
        for target in targets:
            with self.subTest(target=target.relative_to(self.f.base)):
                alias.symlink_to(target)
                try:
                    self.assertNotEqual(self.shell_paths(self.f.a, feature).returncode, 0)
                    self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit',
                                 '--path', 'specs/001-one/plan.md', project=self.f.a, ok=False)
                finally:
                    alias.unlink()
                self.assertEqual((storage.files(self.f.main), storage.files(other)), before)
        self.assertFalse((own / 'transactions').exists())

    def test_dangling_alias_cannot_create_another_workspaces_selection(self):
        feature = self.local_feature()
        target = self.f.b / '.sdlc/feature.json'
        (feature / 'plan.md').symlink_to(target)
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path',
                     'specs/001-one/plan.md', project=self.f.a, ok=False)
        self.assertNotEqual(self.shell_paths(self.f.a, feature).returncode, 0)
        self.assertFalse((self.f.b / '.sdlc').exists())

    def test_registered_source_controls_remain_protected_when_source_disappears(self):
        feature = self.local_feature()
        source = self.f.base / 'registered source'
        source.mkdir()
        self.f.runpy('sdlc_store.py', 'register', '--source', str(source))
        source.rmdir()
        (feature / 'plan.md').symlink_to(source / 'feature.json')
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path',
                     'specs/001-one/plan.md', project=self.f.a, ok=False)
        self.assertFalse(source.exists())

    def test_apply_and_recover_recheck_newly_registered_control_scope(self):
        feature = self.local_feature()
        external = self.f.base / 'newly registered store'
        external.mkdir()
        target = external / 'feature.json'
        target.write_text('old')
        name = 'specs/001-one/plan.md'
        (feature / 'plan.md').symlink_to(target)
        for action in ('apply', 'recover'):
            with self.subTest(action=action):
                plan = self.f.prepare(self.f.a, kind='edit', paths=[name])
                self.f.replace(plan, name, 'candidate')
                if action == 'recover':
                    manifest_path = Path(plan['transaction']) / 'manifest.json'
                    manifest = json.loads(manifest_path.read_text())
                    manifest['published'] = {name: storage.changes.publish_data(target, b'candidate', target.read_bytes())}
                    manifest.update(status='applying', after={name: base64.b64encode(b'candidate').decode()})
                    manifest_path.write_text(json.dumps(manifest))
                before_context = storage.store.resolve(self.f.a, missing=True)
                after_context = dict(before_context, sources=[*before_context['sources'], str(external)])
                before = target.read_bytes()
                with mock.patch.object(storage.changes, 'resolve', side_effect=[before_context, after_context]):
                    with self.assertRaises(ValueError):
                        getattr(storage.changes, action)(self.f.a, Path(plan['transaction']))
                self.assertEqual(target.read_bytes(), before)

    def test_external_plain_document_named_like_a_control_file_remains_editable(self):
        feature = self.local_feature()
        external = self.f.base / 'feature.json'
        external.write_text('ordinary external document')
        (feature / 'plan.md').symlink_to(external)
        name = 'specs/001-one/plan.md'
        plan = self.f.prepare(self.f.a, kind='edit', paths=[name])
        self.f.replace(plan, name, 'candidate')
        self.f.apply(plan, self.f.a)
        self.assertEqual(external.read_text(), 'candidate')

    def test_control_file_and_directory_aliases_protect_their_physical_targets(self):
        feature = self.local_feature()
        self.f.init(self.f.b, '--mode', 'local')
        external = self.f.base / 'external controls'
        external.mkdir()
        selection = external / 'selection.txt'
        selection.write_text('selection')
        transaction = external / 'recovery-data.txt'
        transaction.write_text('recovery')
        (self.f.b / '.sdlc/feature.json').symlink_to(selection)
        (self.f.b / '.sdlc/transactions').symlink_to(external, target_is_directory=True)
        alias = feature / 'plan.md'
        for target in (selection, transaction):
            with self.subTest(target=target.name):
                alias.symlink_to(target)
                try:
                    self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path',
                                 'specs/001-one/plan.md', project=self.f.a, ok=False)
                    self.assertNotEqual(self.shell_paths(self.f.a, feature).returncode, 0)
                finally:
                    alias.unlink()
        self.assertEqual(selection.read_text(), 'selection')
        self.assertEqual(transaction.read_text(), 'recovery')

    def test_shared_selection_child_alias_is_identified_without_reading_its_content(self):
        feature = self.local_feature()
        external = self.f.base / 'shared selection'
        external.mkdir()
        target = external / 'feature.json'
        target.write_text('{invalid selection content')
        key = hashlib.sha256(str(self.f.b).encode()).hexdigest()[:24]
        workspace = self.f.main / '.sdlc/workspaces' / key
        workspace.parent.mkdir()
        workspace.symlink_to(external, target_is_directory=True)
        (feature / 'plan.md').symlink_to(target)
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path',
                     'specs/001-one/plan.md', project=self.f.a, ok=False)
        self.assertEqual(target.read_text(), '{invalid selection content')

    def test_control_alias_added_after_preparation_blocks_publication_and_recovery(self):
        feature = self.local_feature()
        self.f.init(self.f.b, '--mode', 'local')
        external = self.f.base / 'external document'
        external.write_text('old')
        name = 'specs/001-one/plan.md'
        (feature / 'plan.md').symlink_to(external)
        plan = self.f.prepare(self.f.a, kind='edit', paths=[name])
        self.f.replace(plan, name, 'candidate')
        (self.f.b / '.sdlc/feature.json').symlink_to(external)
        self.f.apply(plan, self.f.a, ok=False)
        self.assertEqual(external.read_text(), 'old')
        manifest_path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['published'] = {name: storage.changes.publish_data(external, b'candidate', external.read_bytes())}
        manifest.update(status='applying', after={name: base64.b64encode(b'candidate').decode()})
        manifest_path.write_text(json.dumps(manifest))
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a, ok=False)
        self.assertEqual(external.read_text(), 'candidate')

    def test_legal_knowledge_aliases_allow_reads_edits_and_preserve_links(self):
        for name in ('memory/constitution.md', 'memory/long-term.md'):
            for shared in (False, True):
                with self.subTest(name=name, shared=shared):
                    if (self.f.a / '.sdlc').exists():
                        shutil.rmtree(self.f.a / '.sdlc')
                    logical, actual = self.knowledge_alias(name, shared=shared)
                    try:
                        link = os.readlink(logical), logical.lstat().st_ino
                        self.assertEqual(self.shell_paths(self.f.a).returncode, 0)
                        before = actual.read_bytes(), actual.stat().st_mtime_ns
                        self.f.runpy('project_status.py', project=self.f.a)
                        self.assertEqual((actual.read_bytes(), actual.stat().st_mtime_ns), before)
                        plan = self.f.prepare(self.f.a, kind='edit', paths=[name])
                        self.f.replace(plan, name, 'knowledge candidate')
                        self.f.apply(plan, self.f.a)
                        self.assertEqual(actual.read_text(), 'knowledge candidate')
                        self.assertEqual((os.readlink(logical), logical.lstat().st_ino), link)
                    finally:
                        # Restore the shared authority before the next case's INIT.
                        if shared:
                            logical.unlink()
                            actual.rename(logical)

    def test_internal_knowledge_alias_and_explicit_selection_override_remain_valid(self):
        logical, actual = self.knowledge_alias('memory/constitution.md', internal=True)
        feature = self.f.feature(self.f.a)
        (self.f.a / '.sdlc/feature.json').write_text('{invalid')
        value = '.sdlc/specs/001-one'
        selected = self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.f.a)
        self.assertEqual(Path(selected['FEATURE_DIR']).resolve(), feature)
        selection = self.f.a / '.sdlc/feature.json'
        before = selection.read_bytes(), selection.stat().st_mtime_ns
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.f.a)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        plan = self.f.prepare(self.f.a, kind='edit', paths=['memory/constitution.md'])
        self.f.replace(plan, 'memory/constitution.md', 'internal knowledge')
        self.f.apply(plan, self.f.a)
        self.assertTrue(logical.is_symlink())
        self.assertEqual(actual.read_text(), 'internal knowledge')

    def test_knowledge_alias_rebinding_blocks_apply_and_recovery(self):
        logical, actual = self.knowledge_alias('memory/constitution.md')
        other = self.f.base / 'other.md'
        other.write_bytes(actual.read_bytes())
        plan = self.f.prepare(self.f.a, kind='edit', paths=['memory/constitution.md'])
        self.f.replace(plan, 'memory/constitution.md', 'candidate')
        logical.unlink()
        logical.symlink_to(other)
        self.f.apply(plan, self.f.a, ok=False)
        self.assertNotEqual(actual.read_text(), 'candidate')
        manifest_path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest.update(status='applying', after={'memory/constitution.md': base64.b64encode(b'candidate').decode()})
        manifest_path.write_text(json.dumps(manifest))
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a, ok=False)
        self.assertEqual(other.read_bytes(), actual.read_bytes())

    def test_writing_helpers_keep_explicit_selection_and_no_persist_with_knowledge_alias(self):
        logical, actual = self.knowledge_alias('memory/constitution.md')
        feature = self.f.feature(self.f.a)
        selection = self.f.a / '.sdlc/feature.json'
        selection.write_text('{invalid')
        before = selection.read_bytes(), selection.stat().st_mtime_ns
        constitution = actual.read_bytes(), logical.lstat().st_ino
        env = dict(self.f.env, SDLC_INIT_DIR=str(self.f.a),
                   SDLC_FEATURE_DIRECTORY='.sdlc/specs/001-one', SDLC_FEATURE_NO_PERSIST='1')
        for script in ('setup-plan.sh', 'setup-tasks.sh'):
            with self.subTest(script=script):
                result = subprocess.run(['bash', str(storage.PACKAGE / 'scripts/bash' / script), '--json'],
                    cwd=self.f.a, env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(Path(json.loads(result.stdout)['FEATURE_DIR']).resolve(), feature)
                self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        env.pop('SDLC_FEATURE_DIRECTORY')
        result = subprocess.run(['bash', str(storage.PACKAGE / 'scripts/bash/create-new-feature.sh'),
                                 '--json', '--number', '2', '--short-name', 'next', 'Next feature'],
            cwd=self.f.a, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        self.assertEqual((actual.read_bytes(), logical.lstat().st_ino), constitution)

    def test_knowledge_aliases_still_reject_authority_plugin_and_control_targets(self):
        self.f.init(self.f.a, '--mode', 'local')
        for name in ('memory/constitution.md', 'memory/long-term.md'):
            logical = self.f.a / '.sdlc' / name
            original = logical.read_bytes()
            for actual in (self.f.main / '.sdlc/memory/long-term.md',
                           storage.PACKAGE / 'templates/constitution-template.md',
                           self.f.a / '.sdlc/feature.json'):
                with self.subTest(name=name, actual=actual.name):
                    logical.unlink()
                    logical.symlink_to(actual)
                    self.assertNotEqual(self.shell_paths(self.f.a).returncode, 0)
                    self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', name,
                                 project=self.f.a, ok=False)
                    logical.unlink()
                    logical.write_bytes(original)

    def test_external_authority_knowledge_alias_targets_remain_protected_from_local_writes(self):
        feature = self.local_feature()
        alias = feature / 'plan.md'
        for name in ('memory/constitution.md', 'memory/long-term.md'):
            with self.subTest(name=name):
                authority_file = self.f.main / '.sdlc' / name
                target = self.f.base / ('authority-' + authority_file.name)
                authority_file.rename(target)
                authority_file.symlink_to(target)
                alias.symlink_to(target)
                original = target.read_bytes()
                try:
                    self.assertNotEqual(self.shell_paths(self.f.a, feature).returncode, 0)
                    self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path',
                                 'specs/001-one/plan.md', project=self.f.a, ok=False)
                    self.f.runpy('sdlc_store.py', 'feature', '--value', str(target), '--persist',
                                 project=self.f.a, ok=False)
                    self.assertEqual(target.read_bytes(), original)
                finally:
                    alias.unlink()
                    authority_file.unlink()
                    target.rename(authority_file)

    def test_collection_and_init_copy_sources_remain_strict_about_knowledge_aliases(self):
        self.knowledge_alias('memory/constitution.md')
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source',
                     str(self.f.a / '.sdlc'), project=self.f.main, ok=False)
        authority_file = self.f.main / '.sdlc/memory/constitution.md'
        external = self.f.base / 'authority-current.md'
        authority_file.rename(external)
        authority_file.symlink_to(external)
        self.f.runpy('init_project.py', '--mode', 'local', project=self.f.b, ok=False)
        self.assertFalse((self.f.b / '.sdlc').exists())

    def test_explicit_feature_import_requires_authority_before_creating_local_store(self):
        shutil.rmtree(self.f.main / '.sdlc')
        before = storage.files(self.f.main)
        for preview in (False, True):
            with self.subTest(preview=preview):
                args = ['--mode', 'local', '--feature', '001-requested']
                if preview:
                    args.append('--dry-run')
                self.f.runpy('init_project.py', *args, project=self.f.a, ok=False)
                self.assertFalse((self.f.a / '.sdlc').exists())
                self.assertEqual(storage.files(self.f.main), before)
        self.assertEqual(self.f.init(self.f.a, '--mode', 'local')['status'], 'initialized')

    def test_designated_missing_authority_does_not_silently_skip_selected_requirement(self):
        authority = self.f.base / 'designated authority'
        (self.f.main / '.sdlc').rename(authority)
        self.f.runpy('sdlc_store.py', 'register', '--authority', str(authority))
        shutil.rmtree(authority)
        marker = storage.files(self.f.main)
        self.f.runpy('init_project.py', '--mode', 'local', '--feature', '001-requested', project=self.f.a, ok=False)
        self.assertFalse((self.f.a / '.sdlc').exists())
        self.assertEqual(storage.files(self.f.main), marker)

    def test_saved_import_can_resume_after_authority_directory_disappears(self):
        try:
            from tests import test_storage_init_retry as retry
        except ImportError:
            import test_storage_init_retry as retry
        case = retry.InitRetryTests('runTest')
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.interrupt()
        original = (case.fixture.main / '.sdlc/specs/001-one/spec.md').read_bytes()
        shutil.rmtree(case.fixture.main / '.sdlc')
        result = case.run_init()
        self.assertEqual((case.state / 'specs/001-one/spec.md').read_bytes(), original)
        self.assertIn('specs/001-one/spec.md', result['imported'])
        self.assertFalse(case.pending.exists())

    def test_authority_disappearing_during_discovery_cannot_turn_import_into_blank_init(self):
        try:
            from tests import test_storage_init_retry as retry
        except ImportError:
            import test_storage_init_retry as retry
        self.f.feature(self.f.main, '001-requested')
        before = storage.store.resolve(self.f.a, missing=True)
        local = self.f.a / '.sdlc'
        after = dict(before, SDLC_DIR=str(local), FEATURE_JSON=str(local / 'feature.json'),
                     mode='local', local_exists=True)
        args = SimpleNamespace(project=self.f.a, discover=False, mode='local', seed='knowledge',
                               feature=['001-requested'], feature_numbering=None, dry_run=False)
        real = Path.is_dir
        calls = 0
        authority = self.f.main / '.sdlc'
        def disappears(path):
            nonlocal calls
            if path == authority:
                calls += 1
                return calls == 1
            return real(path)
        with mock.patch.object(storage.store, 'resolve', side_effect=[before, after, after]), \
                mock.patch.object(Path, 'is_dir', disappears):
            with self.assertRaises(ValueError):
                retry.initializer.initialize_selected(args)
        self.assertFalse(local.exists())


if __name__ == '__main__':
    unittest.main()
