"""Physical document roles stay isolated during preparation, apply and recovery."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class TargetRoleTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.init(self.f.a, '--mode', 'local')
        self.f.init(self.f.b, '--mode', 'local')
        self.feature = self.f.feature(self.f.a)
        self.name = 'specs/001-one/plan.md'
        self.target = self.feature / 'plan.md'
        self.target.write_text('original')
        self.control = self.f.b / '.sdlc/feature.json'

    def prepare(self, name=None):
        return self.f.prepare(self.f.a, kind='edit', paths=[name or self.name])

    def interrupted(self, plan, target=None, name=None):
        name = name or self.name
        path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(path.read_text())
        target = target or self.target
        manifest['published'] = {name: storage.changes.publish_data(
            target, b'partial', target.read_bytes() if target.exists() else None)}
        manifest.update(status='applying', after={name: base64.b64encode(b'partial').decode()})
        path.write_text(json.dumps(manifest))

    def unchanged_failure(self, action, plan, target=None):
        target = target or self.target
        before = target.read_bytes(), target.stat().st_mtime_ns
        self.f.runpy('store_changes.py', action, '--transaction', plan['transaction'],
                     project=self.f.a, ok=False)
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
        manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
        self.assertEqual(manifest['status'], 'applying' if action == 'recover' else 'prepared')

    def shell_paths(self, project, feature):
        return subprocess.run(['bash', str(storage.PACKAGE / 'scripts/bash/project-paths.sh'),
                               '--feature', str(feature)], cwd=project, env=self.f.env,
                              capture_output=True, text=True, timeout=30)

    def test_plain_documents_referenced_by_foreign_controls_are_rejected_at_prepare(self):
        names = [self.name, 'templates/overrides/spec-template.md', *storage.store.KNOWLEDGE]
        for name in names:
            with self.subTest(name=name):
                target = self.f.a / '.sdlc' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('original')
                self.control.symlink_to(target)
                before = target.read_bytes(), target.stat().st_mtime_ns
                try:
                    self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', name,
                                 project=self.f.a, ok=False)
                    self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                finally:
                    self.control.unlink()
        self.assertFalse((self.f.a / '.sdlc/transactions').exists())

    def test_plain_control_alias_added_after_prepare_blocks_apply(self):
        for name in (self.name, 'templates/overrides/spec-template.md', *storage.store.KNOWLEDGE):
            with self.subTest(name=name):
                target = self.f.a / '.sdlc' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('original')
                plan = self.prepare(name)
                self.f.replace(plan, name, 'candidate')
                self.control.symlink_to(target)
                try:
                    self.unchanged_failure('apply', plan, target)
                finally:
                    self.control.unlink()

    def test_plain_control_alias_added_before_recovery_blocks_rollback(self):
        for name in (self.name, 'templates/overrides/spec-template.md', *storage.store.KNOWLEDGE):
            with self.subTest(name=name):
                target = self.f.a / '.sdlc' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('original')
                plan = self.prepare(name)
                self.interrupted(plan, target, name)
                self.control.symlink_to(target)
                try:
                    self.unchanged_failure('recover', plan, target)
                finally:
                    self.control.unlink()

    def test_control_role_introduced_under_lock_is_rechecked(self):
        for action in ('apply', 'recover'):
            with self.subTest(action=action):
                plan = self.prepare()
                self.f.replace(plan, self.name, 'candidate')
                if action == 'recover':
                    self.interrupted(plan)
                real = storage.changes.resolve
                calls = 0
                def changed(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        self.control.symlink_to(self.target)
                    return real(*args, **kwargs)
                before = self.target.read_bytes(), self.target.stat().st_mtime_ns
                try:
                    with mock.patch.object(storage.changes, 'resolve', side_effect=changed):
                        with self.assertRaises(ValueError):
                            getattr(storage.changes, action)(self.f.a, Path(plan['transaction']))
                    self.assertEqual((self.target.read_bytes(), self.target.stat().st_mtime_ns), before)
                finally:
                    self.control.unlink(missing_ok=True)

    def test_unrelated_control_alias_and_content_changes_do_not_invalidate_plain_edit(self):
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        other = self.f.base / 'unrelated control target'
        other.write_text('{invalid selector content')
        self.control.symlink_to(other)
        self.f.apply(plan, self.f.a)
        self.assertEqual(self.target.read_text(), 'candidate')
        self.assertEqual(other.read_text(), '{invalid selector content')

    def test_direct_own_control_writes_remain_available_in_local_main_and_shared_modes(self):
        shutil.rmtree(self.f.b / '.sdlc')
        self.f.feature(self.f.main)
        for project in (self.f.a, self.f.main, self.f.b):
            with self.subTest(project=project.name):
                context = self.f.binding(project)
                state = Path(context['SDLC_DIR'])
                selection = Path(context['FEATURE_JSON']).relative_to(state).as_posix()
                options = json.loads((state / 'init-options.json').read_text())
                options['fixture'] = project.name
                candidates = {'README.md': '# Fixture\n', '.gitignore': '# Fixture\n*\n',
                              'init-options.json': json.dumps(options),
                              selection: json.dumps({'feature_directory': '.sdlc/specs/001-one'})}
                plan = self.f.prepare(project, kind='edit', paths=list(candidates))
                for name, text in candidates.items():
                    self.f.replace(plan, name, text)
                self.f.apply(plan, project)
                for name, text in candidates.items():
                    self.assertEqual((state / name).read_text(), text)

    def test_direct_control_targets_referenced_by_other_controls_are_protected(self):
        selection = self.f.a / '.sdlc/feature.json'
        selection.write_text(json.dumps({'feature_directory': '.sdlc/specs/001-one'}))
        for action in ('prepare', 'apply', 'recover'):
            for name in ('README.md', 'init-options.json', 'feature.json'):
                with self.subTest(action=action, name=name):
                    target = self.f.a / '.sdlc' / name
                    original = target.read_bytes()
                    try:
                        if action == 'prepare':
                            self.control.symlink_to(target)
                            self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', name,
                                         project=self.f.a, ok=False)
                        else:
                            plan = self.prepare(name)
                            self.f.replace(plan, name, original.decode() + '\n')
                            if action == 'recover':
                                self.interrupted(plan, target, name)
                            self.control.symlink_to(target)
                            self.unchanged_failure(action, plan, target)
                    finally:
                        self.control.unlink(missing_ok=True)
                        target.write_bytes(original)

    def test_feature_selection_writes_check_target_roles_but_keep_noop(self):
        value = '.sdlc/specs/001-one'
        other = '.sdlc/specs/002-two'
        self.f.feature(self.f.a, '002-two')
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.f.a)
        selection = self.f.a / '.sdlc/feature.json'
        self.control.symlink_to(selection)
        before = selection.read_bytes(), selection.stat().st_mtime_ns
        self.f.runpy('sdlc_store.py', 'feature', '--value', other, project=self.f.a)
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.f.a)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        self.f.runpy('sdlc_store.py', 'feature', '--value', other, '--persist', project=self.f.a, ok=False)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)
        self.control.unlink()
        self.f.runpy('sdlc_store.py', 'feature', '--value', other, '--persist', project=self.f.a)
        self.assertEqual(json.loads(selection.read_text())['feature_directory'], other)

    def test_foreign_alias_of_unedited_control_does_not_expand_edit_scope(self):
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        options = self.f.a / '.sdlc/init-options.json'
        before = options.read_bytes(), options.stat().st_mtime_ns
        self.control.symlink_to(options)
        self.f.apply(plan, self.f.a)
        self.assertEqual(self.target.read_text(), 'candidate')
        self.assertEqual((options.read_bytes(), options.stat().st_mtime_ns), before)

    def test_collection_target_roles_are_checked_during_prepare_apply_and_recover(self):
        name = 'memory/constitution.md'
        target = self.f.main / '.sdlc' / name
        original = target.read_bytes()
        (self.f.a / '.sdlc' / name).write_text('local version')
        for action in ('prepare', 'apply', 'recover'):
            with self.subTest(action=action):
                try:
                    if action == 'prepare':
                        self.control.symlink_to(target)
                        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source',
                                     str(self.f.a / '.sdlc'), project=self.f.main, ok=False)
                        self.assertEqual(target.read_bytes(), original)
                    else:
                        plan = self.f.prepare(self.f.main, sources=[self.f.a / '.sdlc'])
                        self.f.replace(plan, name, 'candidate')
                        if action == 'recover':
                            self.interrupted(plan, target, name)
                        self.control.symlink_to(target)
                        before = target.read_bytes(), target.stat().st_mtime_ns
                        result = self.f.runpy('store_changes.py', action, '--transaction', plan['transaction'],
                                              project=self.f.main, ok=False)
                        self.assertIn('reserved store path', result.stderr)
                        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                finally:
                    self.control.unlink(missing_ok=True)
                    target.write_bytes(original)

    def test_import_recovery_refuses_new_authority_alias_of_its_target(self):
        feature = self.f.feature(self.f.main)
        authority = feature / 'plan.md'
        authority.write_text('authority version')
        plan = self.f.prepare(self.f.a, kind='import', features=['001-one'])
        self.interrupted(plan)
        authority.unlink()
        authority.symlink_to(self.target)
        result = self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'],
                              project=self.f.a, ok=False)
        self.assertIn('authority', result.stderr)
        self.assertEqual(authority.read_text(), 'partial')
        self.assertEqual(self.target.read_text(), 'partial')

    def test_import_recovery_keeps_working_after_authority_disappears(self):
        feature = self.f.feature(self.f.main)
        (feature / 'plan.md').write_text('authority version')
        original = self.target.read_bytes()
        plan = self.f.prepare(self.f.a, kind='import', features=['001-one'])
        self.interrupted(plan)
        shutil.rmtree(self.f.main / '.sdlc')
        result = self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a)
        self.assertEqual(result['status'], 'recovered')
        self.assertEqual(self.target.read_bytes(), original)
        self.assertFalse((self.f.main / '.sdlc').exists())

    def test_private_control_leaf_aliases_are_checked_in_all_transaction_phases(self):
        names = ('transactions/pending/manifest.json', 'transactions/pending/proposal.json',
                 'workspaces/' + 'f' * 24 + '/feature.json', '.write-lock/owner', '.write-lock/pid')
        for action in ('prepare', 'apply', 'recover'):
            for name in names:
                with self.subTest(action=action, name=name):
                    control = self.f.b / '.sdlc' / name
                    control.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        if action == 'prepare':
                            control.symlink_to(self.target)
                            result = self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit',
                                                  '--path', self.name, project=self.f.a, ok=False)
                            self.assertIn('reserved store path', result.stderr)
                        else:
                            plan = self.prepare()
                            self.f.replace(plan, self.name, 'candidate')
                            if action == 'recover':
                                self.interrupted(plan)
                            control.symlink_to(self.target)
                            self.unchanged_failure(action, plan)
                    finally:
                        control.unlink(missing_ok=True)
                        self.target.write_text('original')

    def test_shared_selection_write_checks_unknown_control_aliases_but_keeps_noop(self):
        shutil.rmtree(self.f.b / '.sdlc')
        self.f.feature(self.f.main)
        self.f.feature(self.f.main, '002-two')
        value, other = '.sdlc/specs/001-one', '.sdlc/specs/002-two'
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.f.b)
        selection = Path(self.f.binding(self.f.b)['FEATURE_JSON'])
        unknown = selection.parent.parent / ('f' * 24)
        unknown.mkdir()
        (unknown / 'feature.json').symlink_to(selection)
        before = selection.read_bytes(), selection.stat().st_mtime_ns
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.f.b)
        self.f.runpy('sdlc_store.py', 'feature', '--value', other, project=self.f.b)
        self.f.runpy('sdlc_store.py', 'feature', '--value', other, '--persist', project=self.f.b, ok=False)
        self.assertEqual((selection.read_bytes(), selection.stat().st_mtime_ns), before)

    def test_unrelated_private_control_aliases_and_cycles_do_not_invalidate_edit(self):
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        other = self.f.base / 'unrelated-private-control'
        other.write_text('{invalid control content')
        for name in ('transactions/pending/manifest.json', 'workspaces/' + 'f' * 24 + '/feature.json',
                     '.write-lock/pid'):
            control = self.f.b / '.sdlc' / name
            control.parent.mkdir(parents=True, exist_ok=True)
            control.symlink_to(other)
        namespace = self.f.b / '.sdlc/transactions'
        (namespace / 'cycle').symlink_to(namespace, target_is_directory=True)
        self.f.apply(plan, self.f.a)
        self.assertEqual(self.target.read_text(), 'candidate')
        self.assertEqual(other.read_text(), '{invalid control content')

    def test_broken_main_registry_alias_does_not_block_unrelated_local_edit(self):
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        options = self.f.a / '.sdlc/init-options.json'
        original = options.read_bytes(), options.stat().st_mtime_ns
        (self.f.main / '.sdlc/store.json').symlink_to(options)
        self.f.apply(plan, self.f.a)
        self.assertEqual(self.target.read_text(), 'candidate')
        self.assertEqual((options.read_bytes(), options.stat().st_mtime_ns), original)

    def test_external_authority_artifact_targets_are_rejected_at_prepare(self):
        cases = [('specs/900-authority/plan.md', self.name, False),
                 ('specs/900-authority/contracts/custom.json', 'specs/001-one/notes.md', True),
                 ('templates/overrides/tasks-template.md', 'memory/long-term.md', True)]
        for index, (authority_name, local_name, alias) in enumerate(cases):
            with self.subTest(authority_name=authority_name, local_alias=alias):
                local = self.f.a / '.sdlc' / local_name
                local.parent.mkdir(parents=True, exist_ok=True)
                if alias:
                    actual = self.f.base / ('external-' + str(index))
                    actual.write_text('original')
                    local.unlink(missing_ok=True)
                    local.symlink_to(actual)
                else:
                    actual = local
                authority = self.f.main / '.sdlc' / authority_name
                authority.parent.mkdir(parents=True, exist_ok=True)
                authority.symlink_to(actual)
                before = actual.read_bytes(), actual.stat().st_mtime_ns
                try:
                    self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', local_name,
                                 project=self.f.a, ok=False)
                    if local_name == self.name:
                        self.assertNotEqual(self.shell_paths(self.f.a, self.feature).returncode, 0)
                    self.assertEqual((actual.read_bytes(), actual.stat().st_mtime_ns), before)
                finally:
                    authority.unlink()

    def test_authority_external_alias_added_after_prepare_blocks_apply(self):
        for alias in (False, True):
            with self.subTest(local_alias=alias):
                actual = self.f.base / 'external-plan' if alias else self.target
                actual.write_text('original')
                if alias:
                    self.target.unlink()
                    self.target.symlink_to(actual)
                plan = self.prepare()
                self.f.replace(plan, self.name, 'candidate')
                authority = self.f.main / '.sdlc/specs/900-authority/plan.md'
                authority.parent.mkdir(parents=True, exist_ok=True)
                authority.symlink_to(actual)
                try:
                    self.unchanged_failure('apply', plan, actual)
                finally:
                    authority.unlink()

    def test_authority_external_alias_added_before_recovery_blocks_rollback(self):
        for alias in (False, True):
            with self.subTest(local_alias=alias):
                actual = self.f.base / 'external-plan' if alias else self.target
                actual.write_text('original')
                if alias:
                    self.target.unlink()
                    self.target.symlink_to(actual)
                plan = self.prepare()
                self.interrupted(plan, actual)
                authority = self.f.main / '.sdlc/specs/900-authority/plan.md'
                authority.parent.mkdir(parents=True, exist_ok=True)
                authority.symlink_to(actual)
                try:
                    self.unchanged_failure('recover', plan, actual)
                finally:
                    authority.unlink()

    def test_authority_role_introduced_under_lock_is_rechecked(self):
        authority = self.f.main / '.sdlc/specs/900-authority/plan.md'
        authority.parent.mkdir(parents=True)
        for action in ('apply', 'recover'):
            with self.subTest(action=action):
                plan = self.prepare()
                self.f.replace(plan, self.name, 'candidate')
                if action == 'recover':
                    self.interrupted(plan)
                real = storage.changes.resolve
                calls = 0
                def changed(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        authority.symlink_to(self.target)
                    return real(*args, **kwargs)
                before = self.target.read_bytes(), self.target.stat().st_mtime_ns
                try:
                    with mock.patch.object(storage.changes, 'resolve', side_effect=changed):
                        with self.assertRaises(ValueError):
                            getattr(storage.changes, action)(self.f.a, Path(plan['transaction']))
                    self.assertEqual((self.target.read_bytes(), self.target.stat().st_mtime_ns), before)
                finally:
                    authority.unlink(missing_ok=True)

    def test_authority_directory_aliases_include_nested_escapes_and_missing_targets(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                external = self.f.base / ('future-contracts' if missing else 'contracts')
                actual = external / 'api.json' if missing else self.f.base / 'escaped-api.json'
                if not missing:
                    external.mkdir()
                    actual.write_text('original')
                    (external / 'nested.json').symlink_to(actual)
                self.target.unlink()
                self.target.symlink_to(actual)
                authority = self.f.main / '.sdlc/specs/900-authority/contracts'
                authority.parent.mkdir(parents=True, exist_ok=True)
                authority.symlink_to(external, target_is_directory=True)
                try:
                    self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', self.name,
                                 project=self.f.a, ok=False)
                    self.assertNotEqual(self.shell_paths(self.f.a, self.feature).returncode, 0)
                    if missing:
                        self.assertFalse(external.exists())
                    else:
                        self.assertEqual(actual.read_text(), 'original')
                finally:
                    authority.unlink()

    def test_legal_local_knowledge_and_artifact_aliases_preserve_apply_and_recover(self):
        aliases = {}
        for index, name in enumerate((*storage.store.KNOWLEDGE, self.name)):
            logical = self.f.a / '.sdlc' / name
            actual = self.f.base / ('local-document-' + str(index))
            logical.rename(actual)
            logical.symlink_to(actual)
            aliases[name] = logical, actual, (os.readlink(logical), logical.lstat().st_ino)
        self.assertEqual(self.shell_paths(self.f.a, self.feature).returncode, 0)
        plan = self.f.prepare(self.f.a, kind='edit', paths=list(aliases))
        for name in aliases:
            self.f.replace(plan, name, 'candidate')
        self.f.apply(plan, self.f.a)
        for logical, actual, binding in aliases.values():
            self.assertEqual(actual.read_text(), 'candidate')
            self.assertEqual((os.readlink(logical), logical.lstat().st_ino), binding)
        plan = self.prepare()
        self.interrupted(plan, aliases[self.name][1])
        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a)
        self.assertEqual(aliases[self.name][1].read_text(), 'candidate')
        self.assertTrue(self.target.is_symlink())

    def test_main_and_shared_workspaces_keep_authority_external_alias_writes(self):
        shutil.rmtree(self.f.b / '.sdlc')
        feature = self.f.feature(self.f.main, '900-authority')
        actual = self.f.base / 'authority-external-plan.md'
        actual.write_text('original')
        alias = feature / 'plan.md'
        alias.symlink_to(actual)
        binding = os.readlink(alias), alias.lstat().st_ino
        for project in (self.f.main, self.f.b):
            with self.subTest(shared=project == self.f.b):
                self.assertEqual(self.shell_paths(project, feature).returncode, 0)
                plan = self.f.prepare(project, kind='edit', paths=['specs/900-authority/plan.md'])
                self.f.replace(plan, 'specs/900-authority/plan.md', project.name)
                self.f.apply(plan, project)
                self.assertEqual(actual.read_text(), project.name)
                self.assertEqual((os.readlink(alias), alias.lstat().st_ino), binding)
        self.assertFalse((self.f.b / '.sdlc').exists())

    def test_unrelated_large_files_and_broken_or_cyclic_authority_aliases_do_not_block_local_edit(self):
        feature = self.f.feature(self.f.main, '900-authority')
        with (feature / 'large.bin').open('wb') as stream:
            stream.truncate(storage.changes.MAX_TOTAL + 1)
        (feature / 'cycle').symlink_to(feature, target_is_directory=True)
        (feature / 'broken.md').symlink_to('broken.md')
        other = self.f.base / 'unrelated external file'
        other.write_text('untouched')
        (feature / 'other.md').symlink_to(other)
        before = other.read_bytes(), other.stat().st_mtime_ns
        plan = self.prepare()
        self.f.replace(plan, self.name, 'candidate')
        self.f.apply(plan, self.f.a)
        self.assertEqual(self.target.read_text(), 'candidate')
        self.assertEqual((other.read_bytes(), other.stat().st_mtime_ns), before)


if __name__ == '__main__':
    unittest.main()
