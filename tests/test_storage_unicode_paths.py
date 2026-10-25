"""Unicode lookup aliases preserve store ownership before publication and recovery."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unicodedata
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


NAME = 'specs/001-one/caf\u00e9.md'


def variant(path):
    return path.with_name(unicodedata.normalize('NFD', path.name.upper()))


class UnicodeIsolationTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        probe = self.f.base / 'caf\u00e9-probe'
        probe.write_text('lookup probe')
        equivalent = variant(probe).exists()
        probe.unlink()
        if not equivalent:
            self.skipTest('Requires normalization-insensitive and case-insensitive lookup')
        self.f.init(self.f.b, '--mode', 'local')
        self.control = self.f.b / '.sdlc/transactions/other/proposal.json'
        self.control.parent.mkdir(parents=True)

    def local(self):
        self.f.init(self.f.a, '--mode', 'local')
        self.f.feature(self.f.a)
        self.f.feature(self.f.main)

    def plan(self, kind):
        project = self.f.main if kind == 'collect' else self.f.a
        target = project / '.sdlc' / NAME
        if kind == 'edit':
            return project, target, dict(kind=kind, paths=[NAME])
        source = (self.f.a if kind == 'collect' else self.f.main) / '.sdlc'
        (source / NAME).write_text('source bytes')
        return project, target, dict(kind=kind, features=['001-one'],
                                     sources=[source] if kind == 'collect' else [])

    def interrupted(self, plan, *, target=None):
        manifest = Path(plan['transaction']) / 'manifest.json'
        data = json.loads(manifest.read_text())
        if target is not None:
            data['published'] = {NAME: storage.changes.publish_data(
                target, b'partial', target.read_bytes() if target.exists() else None)}
        data.update(status='applying', after={NAME: base64.b64encode(b'partial').decode()})
        manifest.write_text(json.dumps(data))

    def test_missing_unicode_control_aliases_block_all_transaction_phases(self):
        self.local()
        for kind in ('edit', 'import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                with self.subTest(kind=kind, phase=phase):
                    project, target, arguments = self.plan(kind)
                    target.unlink(missing_ok=True)
                    try:
                        if phase == 'prepare':
                            self.control.symlink_to(variant(target))
                            args = ['prepare', '--kind', kind]
                            for option, values in (('--source', arguments.get('sources', [])),
                                                   ('--feature', arguments.get('features', [])),
                                                   ('--path', arguments.get('paths', []))):
                                for value in values:
                                    args += [option, str(value)]
                            self.f.runpy('store_changes.py', *args, project=project, ok=False)
                        else:
                            plan = self.f.prepare(project, **arguments)
                            self.f.replace(plan, NAME, 'candidate')
                            if phase == 'recover':
                                self.interrupted(plan)
                            self.control.symlink_to(variant(target))
                            self.f.runpy('store_changes.py', phase, '--transaction', plan['transaction'],
                                         project=project, ok=False)
                            state = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
                            self.assertEqual(state['status'], 'applying' if phase == 'recover' else 'prepared')
                        self.assertFalse(target.exists())
                        self.assertFalse(self.control.exists())
                    finally:
                        self.control.unlink(missing_ok=True)
                    if phase == 'recover':
                        self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)

    def test_partial_unicode_targets_remain_untouched_until_control_alias_is_removed(self):
        self.local()
        for kind in ('edit', 'import', 'collect'):
            with self.subTest(kind=kind):
                project, target, arguments = self.plan(kind)
                target.unlink(missing_ok=True)
                plan = self.f.prepare(project, **arguments)
                self.interrupted(plan, target=target)
                self.control.symlink_to(variant(target))
                before = target.read_bytes(), target.stat().st_mtime_ns
                self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project, ok=False)
                self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                self.control.unlink()
                self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=project)
                self.assertFalse(target.exists())

    def test_authority_unicode_alias_blocks_new_local_writes_and_missing_target_recovery(self):
        self.local()
        target = self.f.a / '.sdlc' / NAME
        alias = self.f.main / '.sdlc/specs/900-main/plan.md'
        alias.parent.mkdir(parents=True)
        for phase in ('prepare', 'apply', 'recover'):
            with self.subTest(phase=phase):
                target.unlink(missing_ok=True)
                try:
                    if phase == 'prepare':
                        alias.symlink_to(variant(target))
                        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', NAME,
                                     project=self.f.a, ok=False)
                    else:
                        plan = self.f.prepare(self.f.a, kind='edit', paths=[NAME])
                        self.f.replace(plan, NAME, 'local candidate')
                        if phase == 'recover':
                            self.interrupted(plan)
                        alias.symlink_to(variant(target))
                        self.f.runpy('store_changes.py', phase, '--transaction', plan['transaction'],
                                     project=self.f.a, ok=False)
                    self.assertFalse(target.exists())
                    self.assertFalse(alias.exists())
                finally:
                    alias.unlink(missing_ok=True)

    def test_unicode_directory_aliases_protect_missing_descendants(self):
        self.local()
        directory = self.f.a / '.sdlc/specs/001-one/caf\u00e9'
        self.control.symlink_to(variant(directory), target_is_directory=True)
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path',
                     'specs/001-one/caf\u00e9/api.json', project=self.f.a, ok=False)
        self.assertFalse(directory.exists())

    def test_unicode_duplicate_edit_destinations_are_rejected_before_writing(self):
        self.local()
        feature = self.f.a / '.sdlc/specs/001-one'
        target = feature / 'caf\u00e9.md'
        (feature / 'plan.md').symlink_to(variant(target))
        for observed in (False, True):
            if observed:
                (feature / 'caf\u00e9-probe').write_text('directory lookup evidence')
            for exists in (False, True):
                with self.subTest(observed=observed, exists=exists):
                    if exists:
                        target.write_text('original')
                    self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit',
                                 '--path', NAME, '--path', 'specs/001-one/plan.md', project=self.f.a, ok=False)
                    self.assertEqual(target.read_text() if target.exists() else None, 'original' if exists else None)
                    target.unlink(missing_ok=True)

    def test_legal_unicode_external_links_preserve_apply_and_recover(self):
        self.local()
        target = self.f.base / 'caf\u00e9.md'
        logical = self.f.a / '.sdlc/specs/001-one/plan.md'
        logical.symlink_to(variant(target))
        inode = logical.lstat().st_ino
        for exists in (False, True):
            with self.subTest(exists=exists):
                target.unlink(missing_ok=True)
                if exists:
                    target.write_text('original')
                plan = self.f.prepare(self.f.a, kind='edit', paths=['specs/001-one/plan.md'])
                self.f.replace(plan, 'specs/001-one/plan.md', 'candidate')
                self.f.apply(plan, self.f.a)
                self.assertEqual(target.read_text(), 'candidate')
                plan = self.f.prepare(self.f.a, kind='edit', paths=['specs/001-one/plan.md'])
                manifest = Path(plan['transaction']) / 'manifest.json'
                data = json.loads(manifest.read_text())
                data['published'] = {'specs/001-one/plan.md': storage.changes.publish_data(
                    target, b'partial', target.read_bytes())}
                data.update(status='applying', after={'specs/001-one/plan.md': base64.b64encode(b'partial').decode()})
                manifest.write_text(json.dumps(data))
                self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=self.f.a)
                self.assertEqual(target.read_text(), 'candidate')
                self.assertEqual(logical.lstat().st_ino, inode)
                self.assertEqual(logical.readlink(), variant(target))

    def test_first_init_import_rejects_unicode_control_alias_before_creating_store(self):
        self.f.feature(self.f.main)
        (self.f.main / '.sdlc' / NAME).write_text('authority requirement')
        target = self.f.a / '.sdlc' / NAME
        self.control.symlink_to(variant(target))
        for observed in (False, True):
            with self.subTest(observed=observed):
                if observed:
                    (self.f.a / 'caf\u00e9-probe').write_text('lookup evidence')
                self.f.runpy('init_project.py', '--mode', 'local', '--feature', '001-one', project=self.f.a, ok=False)
                self.assertFalse((self.f.a / '.sdlc').exists())
                self.assertFalse(self.control.exists())

    def test_init_retry_checks_unicode_roles_and_retains_original_pending_snapshot(self):
        self.f.feature(self.f.main)
        source = self.f.main / '.sdlc' / NAME
        source.write_text('original imported requirement')
        target = self.f.a / '.sdlc' / NAME
        spec = importlib.util.spec_from_file_location('unicode_initializer', storage.SCRIPTS / 'init_project.py')
        initializer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(initializer)
        args = SimpleNamespace(project=self.f.a, discover=False, mode='local', seed='knowledge',
                               feature=['001-one'], feature_numbering=None, dry_run=False)
        publish = initializer.publish
        def interrupted(path, data, expected):
            if path == target:
                raise OSError('synthetic interruption before Unicode requirement')
            return publish(path, data, expected)
        with mock.patch.dict(os.environ, self.f.env, clear=True), mock.patch.object(initializer, 'publish', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'synthetic interruption'):
                initializer.initialize_selected(args)
        pending = self.f.a / '.sdlc/.init-pending.json'
        before = pending.read_bytes(), pending.stat().st_mtime_ns
        self.control.symlink_to(variant(target))
        self.f.runpy('init_project.py', '--mode', 'local', '--feature', '001-one', project=self.f.a, ok=False)
        self.assertEqual((pending.read_bytes(), pending.stat().st_mtime_ns), before)
        self.assertFalse(target.exists())
        self.control.unlink()
        source.write_text('changed authority requirement')
        self.f.init(self.f.a, '--mode', 'local', '--feature', '001-one')
        self.assertEqual(target.read_text(), 'original imported requirement')
        self.assertFalse(pending.exists())


class UnicodeLookupTests(unittest.TestCase):
    def test_missing_unicode_names_follow_observed_normalization_rule(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-normalization-') as name:
            root = Path(name).resolve()
            probe = root / 'caf\u00e9-probe'
            probe.write_text('probe')
            counterpart = root / unicodedata.normalize('NFD', probe.name)
            insensitive = counterpart.exists() and probe.samefile(counterpart)
            left, right = root / 'caf\u00e9-new', root / 'cafe\u0301-new'
            self.assertEqual(storage.store.same_path(left, right), insensitive)

    def test_unknown_normalization_rule_stops_only_ambiguous_missing_names(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-normalization-unknown-') as name:
            root = Path(name).resolve()
            (root / 'CaseProbe').write_text('ASCII evidence')
            with self.assertRaisesRegex(ValueError, 'normalization'):
                storage.store.same_path(root / 'caf\u00e9', root / 'cafe\u0301')
            self.assertFalse(storage.store.same_path(root / 'caf\u00e9', root / 'other'))
            self.assertTrue(storage.store.same_path(root / 'caf\u00e9', root / 'caf\u00e9'))

    def test_distinct_unicode_names_remain_distinct_when_lookup_preserves_normalization(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-normalization-sensitive-') as name:
            root = Path(name).resolve()
            with mock.patch.object(storage.store, 'normalization_sensitive', return_value=True):
                self.assertFalse(storage.store.same_path(root / 'caf\u00e9', root / 'cafe\u0301'))

    def test_pure_canonical_letter_aliases_obey_normalization_even_when_casefold_is_equal(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-canonical-letter-') as name:
            root = Path(name).resolve()
            for sensitive in (False, True):
                with self.subTest(sensitive=sensitive), \
                        mock.patch.object(storage.store, 'normalization_sensitive', return_value=sensitive), \
                        mock.patch.object(storage.store, 'case_sensitive', return_value=True):
                    self.assertEqual(storage.store.same_path(root / '\u212b', root / '\u00c5'), not sensitive)

    def test_disappearing_unicode_lookup_evidence_is_not_a_sensitive_filesystem_result(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-normalization-change-') as name:
            root = Path(name).resolve()
            probe = root / 'caf\u00e9-probe'
            probe.write_text('probe')
            original_name = next(root.iterdir()).name
            lstat = Path.lstat
            def disappear(path, *args, **kwargs):
                if path.parent == root and path.name != original_name:
                    probe.unlink(missing_ok=True)
                return lstat(path, *args, **kwargs)
            with mock.patch.object(Path, 'lstat', disappear):
                with self.assertRaisesRegex(ValueError, 'changed during lookup'):
                    storage.store.normalization_sensitive(root)

    def test_disappearing_case_lookup_evidence_is_not_a_sensitive_filesystem_result(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-case-change-') as name:
            root = Path(name).resolve()
            probe = root / 'CaseProbe'
            probe.write_text('probe')
            lstat = Path.lstat
            def disappear(path, *args, **kwargs):
                if path.parent == root and path.name != probe.name:
                    probe.unlink(missing_ok=True)
                return lstat(path, *args, **kwargs)
            with mock.patch.object(Path, 'lstat', disappear), \
                    mock.patch.object(storage.store.sys, 'platform', 'metadata-only-test'):
                with self.assertRaisesRegex(ValueError, 'changed during lookup'):
                    storage.store.case_sensitive(root)


if __name__ == '__main__':
    unittest.main()
