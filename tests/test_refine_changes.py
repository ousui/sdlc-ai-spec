"""Real synthetic artifact deletion, recovery and continuation; no LLM simulation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class RefineChangesTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.main / '.sdlc'
        self.feature = self.f.feature(self.f.main)
        self.prefix = 'specs/001-one/'
        self.obsolete = self.feature / 'obsolete.md'
        self.obsolete.write_text('Approved obsolete API\n')
        self.obsolete.chmod(0o600)

    def plan(self, decisions, project=None):
        plan = self.f.prepare(project, kind='edit', paths=list(decisions))
        Path(plan['proposal']).write_text(json.dumps(decisions))
        return plan

    def delete_plan(self):
        return self.plan({self.prefix+'obsolete.md': {'action': 'delete'},
                          self.prefix+'spec.md': {'action': 'replace', 'text': 'Valid scope\n'}})

    def interrupt(self, plan, *, deferred=False, recreate=False):
        publish = storage.changes.publish_data
        def fail(path, data, expected):
            if path.name == 'spec.md':
                if recreate:
                    self.obsolete.write_text('Later manual work\n')
                raise OSError('fixture publication interrupted')
            return publish(path, data, expected)
        with mock.patch.object(storage.changes, 'publish_data', side_effect=fail):
            if deferred:
                with mock.patch.object(storage.changes, 'rollback', side_effect=OSError('fixture process stopped')):
                    with self.assertRaises(OSError):
                        storage.changes.apply(self.f.main, Path(plan['transaction']))
            else:
                with self.assertRaises(OSError):
                    storage.changes.apply(self.f.main, Path(plan['transaction']))

    def recover(self, plan, ok=True):
        return self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], ok=ok)

    def numbering(self):
        return self.f.runpy('task_ids.py', '--feature', str(self.feature))

    def tasks(self, text):
        return self.plan({self.prefix+'tasks.md': {'action': 'replace', 'text': text}})

    def test_delete_and_rewrite_references_and_create_merged_document(self):
        (self.feature/'spec.md').write_text('[Old API](obsolete.md)\nKeep valid scope\n')
        other = self.f.feature(self.f.main, '002-two')
        decisions = {self.prefix+'obsolete.md': {'action': 'delete'},
                     self.prefix+'spec.md': {'action': 'replace', 'text': 'Keep valid scope\n'},
                     'specs/002-two/merged.md': {'action': 'replace', 'text': 'Consolidated active contract\n'}}
        plan = self.plan(decisions)
        result = self.f.apply(plan)
        self.assertEqual(result['deleted'], [self.prefix+'obsolete.md'])
        self.assertFalse(os.path.lexists(self.obsolete))
        self.assertEqual((self.feature/'spec.md').read_text(), 'Keep valid scope\n')
        self.assertTrue((other/'merged.md').is_file())
        self.assertEqual(self.f.apply(plan)['status'], 'already_applied')
        self.assertEqual(json.loads((Path(plan['transaction'])/'manifest.json').read_text())['schema'], 2)

    def test_empty_replacement_is_not_deletion_and_absent_delete_is_noop(self):
        self.f.apply(self.plan({self.prefix+'obsolete.md': {'action': 'replace', 'text': ''}}))
        self.assertTrue(self.obsolete.is_file())
        self.assertEqual(self.obsolete.stat().st_size, 0)
        self.f.apply(self.delete_plan())
        self.assertEqual(self.f.apply(self.delete_plan())['deleted'], [])

    def test_shared_and_local_delete_use_effective_store(self):
        self.f.apply(self.plan({self.prefix+'obsolete.md': {'action': 'delete'}}, self.f.a), self.f.a)
        self.assertFalse(self.obsolete.exists())
        self.f.init(self.f.a, '--mode', 'local')
        local = self.f.feature(self.f.a)
        (local/'obsolete.md').write_text('Local')
        self.obsolete.write_text('Authority')
        self.f.apply(self.plan({self.prefix+'obsolete.md': {'action': 'delete'}}, self.f.a), self.f.a)
        self.assertFalse((local/'obsolete.md').exists())
        self.assertEqual(self.obsolete.read_text(), 'Authority')

    def test_controls_leaf_aliases_and_copy_deletion_are_rejected(self):
        for name in ('init-options.json', 'feature.json', 'README.md'):
            with self.subTest(name=name):
                before = (self.root/name).read_bytes() if (self.root/name).exists() else None
                plan = self.plan({name: {'action': 'delete'}})
                self.f.apply(plan, ok=False)
                self.assertEqual((self.root/name).read_bytes() if (self.root/name).exists() else None, before)
        alias = self.feature/'alias.md'
        alias.symlink_to(self.obsolete.name)
        self.f.apply(self.plan({self.prefix+'alias.md': {'action': 'delete'}}), ok=False)
        self.assertTrue(alias.is_symlink())
        self.assertTrue(self.obsolete.is_file())
        alias.unlink()
        self.f.init(self.f.a, '--mode', 'local')
        (self.f.feature(self.f.a)/'spec.md').write_text('Local variant')
        for kind, project, sources in (('import', self.f.a, []), ('collect', self.f.main, [self.f.a/'.sdlc'])):
            with self.subTest(kind=kind):
                plan = self.f.prepare(project, kind=kind, sources=sources, features=['001-one'])
                proposal = json.loads(Path(plan['proposal']).read_text())
                proposal = {name: {'action': 'delete'} for name in proposal}
                self.assertTrue(proposal)
                Path(plan['proposal']).write_text(json.dumps(proposal))
                self.f.apply(plan, project, ok=False)

    def test_changed_target_prevents_any_delete(self):
        plan = self.delete_plan()
        self.obsolete.write_text('New manual decision\n')
        self.f.apply(plan, ok=False)
        self.assertEqual(self.obsolete.read_text(), 'New manual decision\n')

    def test_partial_failure_restores_deleted_file_bytes_mode_and_other_files(self):
        original = (self.feature/'spec.md').read_bytes()
        self.interrupt(self.delete_plan())
        self.assertEqual(self.obsolete.read_text(), 'Approved obsolete API\n')
        self.assertEqual(self.obsolete.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.feature/'spec.md').read_bytes(), original)

    def test_deferred_recovery_restores_and_is_idempotent(self):
        plan = self.delete_plan()
        self.interrupt(plan, deferred=True)
        self.assertFalse(self.obsolete.exists())
        self.assertEqual(self.recover(plan)['status'], 'recovered')
        self.assertEqual(self.obsolete.read_text(), 'Approved obsolete API\n')
        self.assertEqual(self.recover(plan)['status'], 'already_recovered')

    def test_manual_recreation_blocks_immediate_and_deferred_recovery(self):
        plan = self.delete_plan()
        self.interrupt(plan, recreate=True)
        self.recover(plan, ok=False)
        self.assertEqual(self.obsolete.read_text(), 'Later manual work\n')

    def test_recreation_racing_with_recovery_is_not_overwritten(self):
        plan = self.delete_plan()
        self.interrupt(plan, deferred=True)
        restore = storage.changes.restore_deleted
        def recreate(path, data, mode):
            path.write_text('Concurrent manual work\n')
            restore(path, data, mode)
        with mock.patch.object(storage.changes, 'restore_deleted', side_effect=recreate):
            with self.assertRaises(FileExistsError):
                storage.changes.recover(self.f.main, Path(plan['transaction']))
        self.assertEqual(self.obsolete.read_text(), 'Concurrent manual work\n')

    def test_unrecorded_deletion_does_not_claim_recovery_ownership(self):
        plan = self.delete_plan()
        self.interrupt(plan, deferred=True)
        path = Path(plan['transaction'])/'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['published'] = {}
        path.write_text(json.dumps(manifest))
        self.assertIn('deletion ownership', self.recover(plan, ok=False).stderr)
        self.assertFalse(self.obsolete.exists())

    def test_remove_highest_task_then_implement_and_append_without_reuse(self):
        tasks = self.feature/'tasks.md'
        tasks.write_text('- [x] T049 Keep valid work\n- [ ] T050 Approved retired obligation\n')
        self.f.apply(self.tasks('- [x] T049 Keep valid work\n'))
        before = storage.files(self.f.main)
        self.assertEqual(self.numbering()['next_id'], 'T051')
        self.assertEqual(storage.files(self.f.main), before)
        self.assertNotIn('retired obligation', tasks.read_text())
        self.f.apply(self.tasks('- [x] T049 Keep valid work\n- [ ] T050 Different work\n'), ok=False)
        self.f.apply(self.tasks('- [x] T049 Keep valid work\n- [ ] T051 New gap\n'))
        self.f.apply(self.tasks('- [x] T049 Keep valid work\n- [x] T051 New gap\n'))
        self.assertEqual(self.numbering()['next_id'], 'T052')

    def test_nested_task_alias_retires_id_with_the_real_tasks_file(self):
        tasks = self.feature/'tasks.md'
        tasks.write_text('- [x] T049 Valid\n- [ ] T050 Retired\n')
        contracts = self.feature/'contracts'
        contracts.mkdir()
        alias = contracts/'task-view.md'
        alias.symlink_to('../tasks.md')
        name = self.prefix+'contracts/task-view.md'
        plan = self.plan({name: {'action': 'replace', 'text': '- [x] T049 Valid\n'}})
        self.assertEqual(plan['task_histories'], {name: self.prefix+'.task-ids.json'})
        self.f.apply(plan)
        self.assertTrue(alias.is_symlink())
        self.assertEqual(self.numbering()['next_id'], 'T051')
        self.assertTrue((self.feature/'.task-ids.json').is_file())
        self.assertIn('Retired task IDs cannot be reused',
                      self.f.apply(self.tasks('- [x] T049 Valid\n- [ ] T050 Different\n'), ok=False).stderr)

    def test_nested_history_alias_cannot_lower_numbering(self):
        (self.feature/'tasks.md').write_text('- [x] T049 Valid\n- [ ] T050 Retired\n')
        self.f.apply(self.tasks('- [x] T049 Valid\n'))
        history = self.feature/'.task-ids.json'
        original = history.read_bytes()
        contracts = self.feature/'contracts'
        contracts.mkdir()
        alias = contracts/'history.json'
        alias.symlink_to('../.task-ids.json')
        name = self.prefix+'contracts/history.json'
        result = self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', name, ok=False)
        self.assertIn('Task ID history is maintained with tasks', result.stderr)
        self.assertEqual(history.read_bytes(), original)
        self.assertEqual(self.numbering()['next_id'], 'T051')

    def test_direct_task_body_edit_observes_other_requirements_task_entry(self):
        other = self.f.feature(self.f.main, '002-two')
        contracts = other/'contracts'
        contracts.mkdir()
        body = contracts/'task-body.md'
        body.write_text('- [x] T049 Valid\n- [ ] T050 Retired\n')
        (self.feature/'tasks.md').symlink_to('../002-two/contracts/task-body.md')
        self.assertEqual(self.numbering()['next_id'], 'T051')

        name = 'specs/002-two/contracts/task-body.md'
        plan = self.plan({name: {'action': 'replace', 'text': '- [x] T049 Valid\n'}})
        self.f.apply(plan)
        self.assertEqual(self.numbering()['next_id'], 'T051')
        self.assertEqual(plan['task_histories'], {name: self.prefix+'.task-ids.json'})
        self.assertIn('Retired task IDs cannot be reused',
                      self.f.apply(self.tasks('- [x] T049 Valid\n- [ ] T050 Different\n'), ok=False).stderr)

    def test_direct_history_body_edit_cannot_lower_other_requirements_record(self):
        other = self.f.feature(self.f.main, '002-two')
        contracts = other/'contracts'
        contracts.mkdir()
        history = contracts/'history.json'
        (self.feature/'.task-ids.json').symlink_to('../002-two/contracts/history.json')
        (self.feature/'tasks.md').write_text('- [x] T049 Valid\n- [ ] T050 Retired\n')
        self.f.apply(self.tasks('- [x] T049 Valid\n'))
        original = history.read_bytes()
        self.assertEqual(self.numbering()['next_id'], 'T051')

        name = 'specs/002-two/contracts/history.json'
        try:
            plan = self.f.prepare(kind='edit', paths=[name])
        except AssertionError as error:
            self.assertIn('Task ID history is maintained with tasks', str(error))
        else:
            Path(plan['proposal']).write_text(json.dumps({name: {
                'action': 'replace', 'text': '{"schema":1,"high_water":0}'}}))
            self.f.apply(plan, ok=False)
        self.assertEqual(history.read_bytes(), original)
        self.assertEqual(self.numbering()['next_id'], 'T051')

    def test_unrelated_looped_task_entry_does_not_block_document_edit(self):
        other = self.f.feature(self.f.main, '002-two')
        (other/'tasks.md').symlink_to('tasks.md')
        name = self.prefix+'spec.md'
        self.f.apply(self.plan({name: {'action': 'replace', 'text': 'Revised scope\n'}}))
        self.assertEqual((self.feature/'spec.md').read_text(), 'Revised scope\n')

    def test_external_requirement_task_alias_uses_the_requirement_history(self):
        external = self.f.base/'external feature'
        contracts = external/'contracts'
        contracts.mkdir(parents=True)
        (external/'tasks.md').write_text('- [x] T049 Valid\n- [ ] T050 Retired\n')
        (contracts/'task-view.md').symlink_to('../tasks.md')
        (self.root/'specs/002-external').symlink_to(external, target_is_directory=True)
        name = 'specs/002-external/contracts/task-view.md'
        plan = self.plan({name: {'action': 'replace', 'text': '- [x] T049 Valid\n'}})
        self.assertEqual(plan['task_histories'], {name: 'specs/002-external/.task-ids.json'})
        self.f.apply(plan)
        self.assertTrue((contracts/'task-view.md').is_symlink())
        self.assertTrue((external/'.task-ids.json').is_file())
        self.assertEqual(self.f.runpy('task_ids.py', '--feature', str(external))['next_id'], 'T051')

    def test_history_alias_to_another_requirement_is_protected(self):
        other = self.f.feature(self.f.main, '002-two')
        (other/'tasks.md').write_text('- [ ] T050 Retired\n')
        self.f.apply(self.plan({'specs/002-two/tasks.md': {'action': 'replace', 'text': ''}}))
        original = (other/'.task-ids.json').read_bytes()
        contracts = self.feature/'contracts'
        contracts.mkdir()
        (contracts/'other-history.json').symlink_to('../../002-two/.task-ids.json')
        name = self.prefix+'contracts/other-history.json'
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', name, ok=False)
        self.assertEqual((other/'.task-ids.json').read_bytes(), original)

    def test_task_alias_failure_restores_tasks_and_history_together(self):
        tasks = self.feature/'tasks.md'
        tasks.write_text('- [ ] T050 Retired\n')
        contracts = self.feature/'contracts'
        contracts.mkdir()
        alias = contracts/'task-view.md'
        alias.symlink_to('../tasks.md')
        name = self.prefix+'contracts/task-view.md'
        plan = self.plan({name: {'action': 'replace', 'text': ''},
                          self.prefix+'spec.md': {'action': 'replace', 'text': 'Unpublished\n'}})
        original_spec = (self.feature/'spec.md').read_text()
        publish = storage.changes.publish_data
        def fail(path, data, expected):
            if path.name == '.task-ids.json':
                raise OSError('fixture interruption')
            return publish(path, data, expected)
        with mock.patch.object(storage.changes, 'publish_data', side_effect=fail):
            with self.assertRaises(OSError):
                storage.changes.apply(self.f.main, Path(plan['transaction']))
        self.assertEqual(tasks.read_text(), '- [ ] T050 Retired\n')
        self.assertEqual((self.feature/'spec.md').read_text(), original_spec)
        self.assertFalse((self.feature/'.task-ids.json').exists())
        self.assertTrue(alias.is_symlink())

    def test_delete_entire_task_file_preserves_numbers_and_other_requirements_are_independent(self):
        (self.feature/'tasks.md').write_text('- [ ] T050 Retired\n')
        self.f.apply(self.plan({self.prefix+'tasks.md': {'action': 'delete'}}))
        self.assertFalse((self.feature/'tasks.md').exists())
        self.assertEqual(self.numbering()['next_id'], 'T051')
        self.f.apply(self.tasks('- [ ] T001 Reused\n'), ok=False)
        self.f.apply(self.tasks('- [ ] T051 New\n'))
        other = self.f.feature(self.f.main, '002-two')
        self.assertEqual(self.f.runpy('task_ids.py', '--feature', str(other))['next_id'], 'T001')
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'edit', '--path', self.prefix+'.task-ids.json', ok=False)

    def test_history_is_watched_and_invalid_history_is_not_reset(self):
        (self.feature/'tasks.md').write_text('- [ ] T050 Old\n')
        self.f.apply(self.tasks(''))
        plan = self.tasks('- [ ] T051 Next\n')
        history = self.feature/'.task-ids.json'
        history.write_text('{"schema":1,"high_water":80}')
        self.f.apply(plan, ok=False)
        self.assertEqual(self.numbering()['next_id'], 'T081')
        history.write_text('{invalid')
        self.f.runpy('task_ids.py', '--feature', str(self.feature), ok=False)
        self.f.apply(self.tasks('- [ ] T081 Next\n'), ok=False)
        self.assertEqual(history.read_text(), '{invalid')

    def test_task_failure_rolls_back_history_and_deletion_together(self):
        tasks = self.feature/'tasks.md'
        tasks.write_text('- [ ] T050 Old\n')
        plan = self.plan({self.prefix+'tasks.md': {'action': 'delete'}})
        with mock.patch.object(storage.changes, 'publish_data', side_effect=OSError('history interrupted')):
            with self.assertRaises(OSError):
                storage.changes.apply(self.f.main, Path(plan['transaction']))
        self.assertEqual(tasks.read_text(), '- [ ] T050 Old\n')
        self.assertFalse((self.feature/'.task-ids.json').exists())

    def test_fresh_tasks_do_not_create_history_and_examples_do_not_reserve_numbers(self):
        text = '- [ ] T001 Active\n\n```markdown\n- [ ] T999 Example\n```\n'
        self.f.apply(self.tasks(text))
        self.assertFalse((self.feature/'.task-ids.json').exists())
        self.assertEqual(self.numbering()['next_id'], 'T002')
        self.f.apply(self.tasks(text.replace('[ ] T001', '[x] T001')))
        self.assertFalse((self.feature/'.task-ids.json').exists())

    def test_import_cannot_lower_existing_task_reservation(self):
        (self.feature/'tasks.md').write_text('- [ ] T050 Old\n')
        self.f.apply(self.tasks(''))
        self.f.init(self.f.a, '--mode', 'local')
        local = self.f.feature(self.f.a)
        (local/'.task-ids.json').write_text('{"schema":1,"high_water":80}')
        plan = self.f.prepare(self.f.a, kind='import', features=['001-one'])
        self.f.replace(plan, self.prefix+'.task-ids.json', '{"schema":1,"high_water":50}')
        self.assertIn('history cannot decrease', self.f.apply(plan, self.f.a, ok=False).stderr)
        self.assertEqual(json.loads((local/'.task-ids.json').read_text())['high_water'], 80)

    def test_task_and_convergence_consumers_load_numbering_adapter_for_each_host(self):
        # Exercise the distributed loader: a record without a consuming workflow
        # is insufficient. The raw upstream workflow remains separately verified.
        import load_workflow
        for host in ('codex', 'claude', 'cursor'):
            for skill in ('sdlc-300-task', 'sdlc-500-conv'):
                with self.subTest(host=host, skill=skill):
                    text = load_workflow.load(storage.PACKAGE, host, skill)
                    self.assertIn('/scripts/python/task_ids.py', text)
                    self.assertIn('`high_water`', text)
                    self.assertIn('`next_id`', text)


if __name__ == '__main__':
    unittest.main()
