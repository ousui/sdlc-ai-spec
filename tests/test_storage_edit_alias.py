"""Ordinary document edits retain aliases and their storage boundaries."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class EditAliasTests(unittest.TestCase):
    def setUp(self):
        # Compose the disposable Git fixture without inheriting its test methods.
        self.fixture = storage.StorageTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.f.init(self.f.a, '--mode', 'local')
        self.feature = self.f.feature(self.f.a)
        self.name = 'specs/001-one/plan.md'

    def prepare(self, names=None):
        return self.f.prepare(self.f.a, kind='edit', paths=names or [self.name])

    def local_alias(self):
        actual = self.feature / 'plan-current.md'
        actual.write_text('original')
        alias = self.feature / 'plan.md'
        alias.symlink_to(actual.name)
        return alias, actual

    def applying(self, plan, text='candidate'):
        manifest_path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        target = Path(manifest['edit_bindings'][self.name]['path'])
        manifest['published'] = {self.name: storage.changes.publish_data(target, text.encode(), target.read_bytes())}
        manifest.update(status='applying', after={self.name: base64.b64encode(text.encode()).decode()})
        manifest_path.write_text(json.dumps(manifest))

    def test_same_store_alias_edits_target_and_retains_link(self):
        alias, actual = self.local_alias()
        link = (os.readlink(alias), alias.lstat().st_ino)
        before_main = storage.files(self.f.main)
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        self.f.apply(plan, self.f.a)
        self.assertEqual(actual.read_text(), 'candidate')
        self.assertEqual((os.readlink(alias), alias.lstat().st_ino), link)
        self.assertEqual(storage.files(self.f.main), before_main)

    def test_parent_and_external_alias_chain_allow_missing_artifact(self):
        external = self.f.base / 'external documents'
        external.mkdir()
        intermediate = self.f.base / 'document alias'
        intermediate.symlink_to(external, target_is_directory=True)
        alias = self.feature / 'contracts'
        alias.symlink_to(intermediate, target_is_directory=True)
        name = 'specs/001-one/contracts/api.json'
        plan = self.prepare([name])
        self.f.replace(plan, name, '{"openapi":"3.1.0"}')
        self.f.apply(plan, self.f.a)
        self.assertEqual((external / 'api.json').read_text(), '{"openapi":"3.1.0"}')
        self.assertTrue(alias.is_symlink())
        self.assertTrue(intermediate.is_symlink())
        manifest_path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['status'] = 'applying'
        manifest_path.write_text(json.dumps(manifest))
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a)
        self.assertFalse((external / 'api.json').exists())
        self.assertTrue(alias.is_symlink())
        self.assertTrue(intermediate.is_symlink())

    def test_shared_workspace_edits_authority_artifact_alias(self):
        feature = self.f.feature(self.f.main)
        actual = feature / 'plan-current.md'
        actual.write_text('shared original')
        alias = feature / 'plan.md'
        alias.symlink_to(actual.name)
        plan = self.f.prepare(self.f.b, kind='edit', paths=[self.name])
        self.f.replace(plan, self.name, 'shared candidate')
        self.f.apply(plan, self.f.b)
        self.assertEqual(actual.read_text(), 'shared candidate')
        self.assertTrue(alias.is_symlink())
        self.assertFalse((self.f.b / '.sdlc').exists())

    def test_alias_rebinding_rejected_even_with_identical_target_bytes(self):
        alias, actual = self.local_alias()
        other = self.feature / 'other.md'
        other.write_text(actual.read_text())
        for replacement in (other, actual):
            with self.subTest(replacement=replacement.name):
                alias.unlink()
                alias.symlink_to(actual.name)
                plan = self.prepare()
                self.f.replace(plan, self.name, 'candidate')
                alias.unlink()
                alias.symlink_to(replacement.name)
                result = self.f.apply(plan, self.f.a, ok=False)
                self.assertIn('binding changed', result.stderr)
                self.assertEqual(actual.read_text(), 'original')
                self.assertEqual(other.read_text(), 'original')

    def test_normal_path_cannot_become_alias_after_prepare(self):
        path = self.feature / 'plan.md'
        path.write_text('original')
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        other = self.feature / 'other.md'
        path.rename(other)
        path.symlink_to(other.name)
        self.f.apply(plan, self.f.a, ok=False)
        self.assertEqual(other.read_text(), 'original')

    def test_alias_cannot_erase_missing_or_non_directory_traversal(self):
        alias, actual = self.local_alias()
        for value in ('missing/../plan-current.md', 'plan-current.md/../plan-current.md',
                      'plan-current.md/.', 'plan-current.md/'):
            with self.subTest(value=value):
                alias.unlink()
                alias.symlink_to(value)
                self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', self.name,
                             project=self.f.a, ok=False)
                self.assertEqual(actual.read_text(), 'original')

    def test_alias_target_changes_invalidate_only_watched_edit(self):
        alias, actual = self.local_alias()
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        actual.write_text('later user edit')
        self.f.apply(plan, self.f.a, ok=False)
        self.assertEqual(alias.read_text(), 'later user edit')
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        (self.feature / 'unrelated.md').write_text('independent')
        self.f.apply(plan, self.f.a)
        self.assertEqual(actual.read_text(), 'candidate')

    def test_duplicate_actual_targets_and_reserved_store_destinations_rejected(self):
        alias, actual = self.local_alias()
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', self.name,
                     '--path', 'specs/001-one/plan-current.md', project=self.f.a, ok=False)
        state = self.f.a / '.sdlc'
        for name in ('feature.json', 'init-options.json', 'store.json',
                     'workspaces/another/feature.json', 'transactions/fake/manifest.json',
                     'memory/.constitution-template.json'):
            with self.subTest(name=name):
                alias.unlink()
                alias.symlink_to(state / name)
                self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', self.name,
                             project=self.f.a, ok=False)

    def test_authority_plugin_hardlink_and_unknown_authority_external_aliases_rejected(self):
        alias, actual = self.local_alias()
        hardlink = self.f.base / 'hardlink.md'
        os.link(actual, hardlink)
        for destination in (self.f.main / '.sdlc/memory/long-term.md',
                            storage.PACKAGE / 'templates/plan-template.md', hardlink):
            with self.subTest(destination=destination.name):
                alias.unlink()
                alias.symlink_to(destination)
                self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', self.name,
                             project=self.f.a, ok=False)
        hardlink.unlink()
        external = self.f.base / 'external.md'
        external.write_text('external')
        alias.unlink()
        alias.symlink_to(external)
        (self.f.main / '.sdlc/store.json').write_text('{broken')
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', self.name,
                     project=self.f.a, ok=False)
        alias.unlink()
        alias.symlink_to(actual.name)
        plan = self.prepare()
        self.f.replace(plan, self.name, 'local works without registry')
        self.f.apply(plan, self.f.a)
        self.assertEqual(actual.read_text(), 'local works without registry')

    def test_edit_alias_rollback_preserves_link_and_existing_target(self):
        alias, actual = self.local_alias()
        second = 'specs/001-one/tasks.md'
        (self.feature / 'tasks.md').write_text('old tasks')
        plan = self.prepare([self.name, second])
        self.f.replace(plan, self.name, 'candidate')
        self.f.replace(plan, second, 'candidate tasks')
        publish = storage.changes.publish_data
        def failure(path, data, expected):
            if path.name == 'tasks.md':
                raise OSError('fixture interrupted publication')
            return publish(path, data, expected)
        with mock.patch.object(storage.changes, 'publish_data', side_effect=failure):
            with self.assertRaises(OSError):
                storage.changes.apply(self.f.a, Path(plan['transaction']))
        self.assertTrue(alias.is_symlink())
        self.assertEqual(actual.read_text(), 'original')
        self.assertEqual((self.feature / 'tasks.md').read_text(), 'old tasks')

    def test_recovery_preserves_alias_and_refuses_rebinding_or_later_target_edit(self):
        alias, actual = self.local_alias()
        plan = self.prepare()
        self.applying(plan)
        other = self.feature / 'other.md'
        other.write_text('candidate')
        alias.unlink()
        alias.symlink_to(other.name)
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'],
                     project=self.f.a, ok=False)
        self.assertEqual(other.read_text(), 'candidate')
        # A fresh preparation records the new alias; late edits still block recovery.
        plan = self.prepare()
        self.applying(plan, 'new candidate')
        other.write_text('later user edit')
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'],
                     project=self.f.a, ok=False)
        other.write_text('new candidate')
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a, ok=False)
        other.write_text('candidate')
        result = self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'],
                              project=self.f.a)
        self.assertEqual(result['status'], 'recovered')
        self.assertEqual(other.read_text(), 'candidate')
        self.assertTrue(alias.is_symlink())

    def test_collection_still_rejects_alias_sources(self):
        self.local_alias()
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source',
                     str(self.f.a / '.sdlc'), project=self.f.main, ok=False)

    def test_apply_and_recovery_use_authority_rechecked_under_lock(self):
        external = self.f.base / 'external store'
        external.mkdir()
        actual = external / 'plan.md'
        actual.write_text('original')
        (self.feature / 'plan.md').symlink_to(actual)
        changes = storage.changes
        before_context = storage.store.resolve(self.f.a, missing=True)
        after_context = dict(before_context, AUTHORITY_DIR=str(external))
        for action in ('apply', 'recover'):
            with self.subTest(action=action):
                plan = self.prepare()
                self.f.replace(plan, self.name, 'candidate')
                if action == 'recover':
                    self.applying(plan)
                before = actual.read_bytes()
                with mock.patch.object(changes, 'resolve', side_effect=[before_context, after_context]):
                    with self.assertRaisesRegex(ValueError, 'authority'):
                        getattr(changes, action)(self.f.a, Path(plan['transaction']))
                self.assertEqual(actual.read_bytes(), before)

    def test_selection_candidate_is_rechecked_against_current_authority(self):
        external = self.f.base / 'external store'
        external.mkdir()
        plan = self.prepare(['feature.json'])
        self.f.replace(plan, 'feature.json', json.dumps({'feature_directory': str(external / 'specs/001-one')}))
        before_context = storage.store.resolve(self.f.a, missing=True)
        after_context = dict(before_context, AUTHORITY_DIR=str(external))
        with mock.patch.object(storage.changes, 'resolve', side_effect=[before_context, after_context]):
            with self.assertRaisesRegex(ValueError, 'authority'):
                storage.changes.apply(self.f.a, Path(plan['transaction']))
        self.assertFalse((self.f.a / '.sdlc/feature.json').exists())


if __name__ == '__main__':
    unittest.main()
