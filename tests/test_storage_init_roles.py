"""INIT checks physical ownership for new, completed and resumed data writes."""
from __future__ import annotations

import importlib.util
from contextlib import contextmanager
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage

spec = importlib.util.spec_from_file_location('role_initializer', storage.SCRIPTS / 'init_project.py')
initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)


class InitRoleTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.init(self.f.b, '--mode', 'local')
        self.state = self.f.a / '.sdlc'
        self.control = self.f.b / '.sdlc/workspaces' / ('f' * 24) / 'feature.json'
        self.control.parent.mkdir(parents=True)
        self.args = SimpleNamespace(project=self.f.a, discover=False, mode='local', seed='knowledge',
                                    feature=[], feature_numbering=None, dry_run=False)
        self.environment = mock.patch.dict(os.environ, self.f.env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def run_init(self, **values):
        return initializer.initialize_selected(SimpleNamespace(**(vars(self.args) | values)))

    def interrupt(self, name='memory/long-term.md'):
        publish = initializer.publish
        def stop(path, data, expected):
            if path == self.state / name:
                raise OSError('synthetic interrupted import')
            return publish(path, data, expected)
        with mock.patch.object(initializer, 'publish', side_effect=stop):
            with self.assertRaisesRegex(OSError, 'synthetic interrupted import'):
                self.run_init()
        self.assertTrue((self.state / '.init-pending.json').is_file())

    def test_first_import_checks_knowledge_and_selected_requirement_targets_before_creating_store(self):
        feature = self.f.feature(self.f.main)
        for name in ('memory/constitution.md', 'specs/001-one/spec.md'):
            with self.subTest(name=name):
                self.control.symlink_to(self.state / name)
                try:
                    with self.assertRaisesRegex(ValueError, 'reserved store path'):
                        self.run_init(feature=['001-one'])
                    self.assertFalse(self.state.exists())
                    self.assertFalse(self.control.exists())
                    self.assertTrue(self.control.is_symlink())
                    self.assertTrue((feature / 'spec.md').is_file())
                finally:
                    self.control.unlink()

    def test_completion_checks_options_rewrite_without_changing_existing_bytes(self):
        self.run_init()
        options = self.state / 'init-options.json'
        options.write_text('{"script":"sh"}\n')
        self.control.symlink_to(options)
        before = options.read_bytes(), options.stat().st_mtime_ns
        with self.assertRaisesRegex(ValueError, 'reserved store path'):
            self.run_init()
        self.assertEqual((options.read_bytes(), options.stat().st_mtime_ns), before)

    def test_blank_initialization_checks_external_authority_ownership_before_creating_store(self):
        alias = self.f.main / '.sdlc/specs/900-main/contracts/external.txt'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(self.state / 'memory/constitution.md')
        with self.assertRaisesRegex(ValueError, 'authority data through an alias'):
            self.run_init(seed='none')
        self.assertFalse(self.state.exists())

    def test_completion_checks_missing_directory_even_when_documents_are_preserved(self):
        self.run_init()
        target = self.state / 'specs'
        target.rmdir()
        alias = self.f.main / '.sdlc/specs/900-main/contracts'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(target, target_is_directory=True)
        before = storage.files(self.state)
        with self.assertRaisesRegex(ValueError, 'authority data through an alias'):
            self.run_init()
        self.assertFalse(target.exists())
        self.assertEqual(storage.files(self.state), before)

    def test_completion_rejects_missing_file_owned_by_external_authority_alias(self):
        self.run_init()
        target = self.state / 'memory/constitution.md'
        target.unlink()
        alias = self.f.main / '.sdlc/specs/900-main/contracts/external.txt'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'authority data through an alias'):
            self.run_init()
        self.assertFalse(target.exists())
        self.assertTrue(alias.is_symlink())

    def test_pending_retry_rechecks_foreign_control_alias_and_retains_saved_bytes(self):
        self.interrupt()
        pending = self.state / '.init-pending.json'
        before = pending.read_bytes(), pending.stat().st_mtime_ns
        target = self.state / 'memory/long-term.md'
        self.control.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'reserved store path'):
            self.run_init()
        self.assertFalse(target.exists())
        self.assertEqual((pending.read_bytes(), pending.stat().st_mtime_ns), before)
        self.control.unlink()
        (self.f.main / '.sdlc/memory/long-term.md').write_text('new authority bytes')
        result = self.run_init()
        self.assertEqual(target.read_text(), 'Shared project fact\n')
        self.assertIn('memory/long-term.md', result['imported'])
        self.assertFalse(pending.exists())

    def test_pending_retry_rechecks_new_authority_alias_without_requiring_source_snapshot(self):
        self.interrupt()
        target = self.state / 'memory/long-term.md'
        pending = self.state / '.init-pending.json'
        before = pending.read_bytes(), pending.stat().st_mtime_ns
        alias = self.f.main / '.sdlc/specs/900-main/contracts/external.txt'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'authority data through an alias'):
            self.run_init()
        self.assertFalse(target.exists())
        self.assertEqual((pending.read_bytes(), pending.stat().st_mtime_ns), before)
        alias.unlink()
        self.assertEqual(self.run_init()['status'], 'completed')

    def test_first_import_and_completion_recheck_roles_under_lock(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                if existing:
                    self.run_init()
                    (self.state / 'memory/constitution.md').unlink()
                target = self.state / 'memory/constitution.md'
                pending = self.state / '.init-pending.json'
                before = storage.files(self.state)
                original_lock = storage.store.write_lock
                @contextmanager
                def changed(state):
                    with original_lock(state) as token:
                        self.control.symlink_to(target)
                        yield token
                try:
                    with mock.patch.object(storage.store, 'write_lock', changed):
                        with self.assertRaisesRegex(ValueError, 'reserved store path'):
                            self.run_init()
                    self.assertFalse(target.exists())
                    if existing:
                        self.assertFalse(pending.exists())
                        self.assertEqual(storage.files(self.state), before)
                    else:
                        # New import intent is visible before the lock. A role
                        # conflict must retain it without publishing business data.
                        self.assertEqual(set(storage.files(self.state)), {'.init-pending.json'})
                        self.assertTrue(pending.is_file())
                finally:
                    self.control.unlink(missing_ok=True)
                if not existing:
                    source = self.f.main / '.sdlc/memory/constitution.md'
                    original = source.read_bytes()
                    source.write_bytes(b'changed authority after conflict')
                    try:
                        result = self.run_init(mode='auto')
                        self.assertIn('memory/constitution.md', result['imported'])
                        self.assertEqual(target.read_bytes(), original)
                        self.assertFalse(pending.exists())
                    finally:
                        source.write_bytes(original)

    def test_preserved_files_do_not_add_role_dependencies_or_change_noop(self):
        self.run_init()
        constitution = self.state / 'memory/constitution.md'
        self.control.symlink_to(constitution)
        (self.state / 'README.md').unlink()
        before = constitution.read_bytes(), constitution.stat().st_mtime_ns
        self.assertEqual(self.run_init()['status'], 'completed')
        self.assertEqual(self.run_init()['status'], 'unchanged')
        self.assertEqual((constitution.read_bytes(), constitution.stat().st_mtime_ns), before)

    def test_target_roles_are_checked_again_between_business_file_publications(self):
        publish = initializer.publish
        target = self.state / 'memory/constitution.md'
        def changed(path, data, expected):
            result = publish(path, data, expected)
            if path == self.state / 'init-options.json':
                self.control.symlink_to(target)
            return result
        with mock.patch.object(initializer, 'publish', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'reserved store path'):
                self.run_init()
        self.assertFalse(target.exists())
        self.assertTrue((self.state / '.init-pending.json').is_file())
        self.control.unlink()
        self.assertIn('memory/constitution.md', self.run_init()['imported'])

    def test_pending_cleanup_does_not_remove_another_controls_alias_target(self):
        publish = initializer.publish
        pending = self.state / '.init-pending.json'
        def changed(path, data, expected):
            result = publish(path, data, expected)
            if path == self.state / 'memory/long-term.md':
                self.control.symlink_to(pending)
            return result
        with mock.patch.object(initializer, 'publish', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'reserved store path'):
                self.run_init()
        self.assertTrue(pending.is_file())
        before = (self.state / 'memory/long-term.md').stat().st_mtime_ns
        self.control.unlink()
        self.run_init()
        self.assertFalse(pending.exists())
        self.assertEqual((self.state / 'memory/long-term.md').stat().st_mtime_ns, before)

    def test_optional_provenance_role_failure_does_not_block_constitution_creation(self):
        self.run_init()
        constitution = self.state / 'memory/constitution.md'
        provenance = self.state / 'memory/.constitution-template.json'
        constitution.unlink()
        provenance.unlink()
        self.control.symlink_to(provenance)
        result = self.run_init()
        self.assertTrue(constitution.is_file())
        self.assertFalse(provenance.exists())
        self.assertEqual(result['constitution_provenance'], 'unavailable')
        self.assertTrue(any('reserved store path' in warning for warning in result['warnings']))


if __name__ == '__main__':
    unittest.main()
