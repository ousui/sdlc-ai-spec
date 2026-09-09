"""Public intent edits, clarification application and exact downstream projections.

These are deterministic fixtures, not a native Agent or live GitHub certification.
Only the explicit failure-injection test substitutes an internal validator.
"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import test_runtime
from test_runtime import Session
from packages.sdlc.common import Fault, uid
from packages.sdlc.domain import task_fingerprint
from packages.sdlc.protocol import contract
from packages.sdlc.storage import Store
from packages.sdlc.verification import check_fingerprint
from tools.build_plugin import build, verify

OLD_SCOPE = '网站列表及相关前端；是否覆盖详情子页等待明确。'
ANSWER = '仅实现 /sites 列表及页内交互；不改详情子页，详情入口复用现有页面。'
NEW_SCOPE = '/sites 列表及页内交互，详情入口复用现有页面。'
NEW_OUT = '不改看板、统计、日志、设置、删除等详情子页；不部署生产。'


class RevisionTextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sdlc-intent-')
        self.root = Path(self.tmp.name)
        self.s = Session(self.root)
        self.s.initialize()
        self.created = self.s.new_change()

    def tearDown(self):
        self.tmp.cleanup()

    def text(self):
        return self.s.ok('change.get')['content']['revision']

    def clarify(self, field_path='/revision/in_scope'):
        current = self.s.ok('phase.prepare')
        asked = self.s.send('run.request_input', {'revision_id': current['content']['revision']['revision_id'],
            'field_path': field_path, 'question': '是否覆盖详情子页？', 'conflict': '列表范围与详情范围未确定'})
        self.assertEqual('needs_input', asked['status'], asked)
        answered = self.s.ok('run.answer_input', {'question_step_id': asked['data']['question_step_id'],
            'answer': ANSWER, 'basis_text': 'Synthetic user answer; not a human review certificate'})
        self.assertFalse(answered['content_applied'])
        return asked['data']['question_step_id']

    def entries(self):
        return [
            {'op': 'create_source', 'client_key': 'clarified_source', 'kind': 'text', 'original_text': ANSWER},
            {'op': 'create_requirement', 'client_key': 'list_req', 'kind': 'behavior', 'statement': ANSWER,
             'sources': [{'client_key': 'clarified_source'}]},
            {'op': 'create_criterion', 'client_key': 'list_ac', 'condition_text': '打开列表、执行页内交互并进入详情',
             'expected_result': '列表正常且详情复用现有页面，没有详情子页改版',
             'requirements': [{'client_key': 'list_req'}]}]

    def test_installed_cli_clarification_updates_scope_and_all_views(self):
        installed = self.root/'plugin'
        build(installed)
        with patch.object(test_runtime, 'CLI', installed/'scripts/sdlc.py'):
            self.s.cli = True
            self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': OLD_SCOPE}])
            question = self.clarify('/in_scope')
            before = self.s.ok('phase.prepare')
            self.assertEqual(OLD_SCOPE, before['content']['revision']['in_scope'])
            self.assertEqual([], before['pending_inputs'])
            self.assertEqual(question, before['pending_applications'][0]['question_step_id'])
            revised = self.s.ok('change.revise', {'phase': 'REQ', 'reason': 'Apply actual scope answer'},
                                expected_generation=before['generation'])
            receipt = self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': NEW_SCOPE,
                'out_of_scope': NEW_OUT}, *self.entries()])
            self.assertEqual([{'question_step_id': question, 'field': 'in_scope'}], receipt['applied_inputs'])
            self.assertEqual(NEW_SCOPE, receipt['revision_text']['in_scope'])
            completed = self.s.complete('REQ')
            dsn = self.s.ok('phase.prepare', {'phase': 'DSN'})
            self.assertEqual(NEW_SCOPE, dsn['content']['revision']['in_scope'])
            self.assertEqual(NEW_OUT, dsn['content']['revision']['out_of_scope'])
            self.assertEqual([], dsn['pending_applications'])
            page = Path(self.s.ok('render')['path'])
            self.assertIn(NEW_SCOPE, page.read_text())
            self.assertIn(NEW_SCOPE, (page.parent/'spec.md').read_text())
            preview = self.s.ok('github.preview', {'issue_url': 'https://github.com/example/lab/issues/7', 'phase': 'REQ'})
            self.assertIn(NEW_SCOPE, preview['body'])
            self.assertNotIn(OLD_SCOPE, preview['body'])
            self.assertIn(ANSWER, preview['body'])
            with Store(self.root).read() as con:
                old = dict(con.execute('SELECT * FROM revisions WHERE revision_id=?',
                                       (self.created['revision_id'],)).fetchone())
                self.assertEqual('abandoned', old['state'])
                self.assertEqual(OLD_SCOPE, old['in_scope'])
                new = con.execute('SELECT * FROM revisions WHERE revision_id=?', (revised['revision_id'],)).fetchone()
                self.assertEqual(completed['digest'], new['digest'])
            archive = self.s.ok('workspace.export', {'change_id': self.s.bindings['change_id']})
            with zipfile.ZipFile(archive['path']) as z:
                data = json.loads(z.read('database.json'))
            exported = next(r for r in data['revisions'] if r['revision_id'] == revised['revision_id'])
            self.assertEqual(NEW_SCOPE, exported['in_scope'])
            self.assertTrue(any('applied_inputs' in r['response_json'] for r in data['operations']))
            self.assertFalse((installed/'docs').exists())
            verify(installed)

    def test_answered_field_blocks_completion_until_explicitly_written(self):
        self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': OLD_SCOPE}])
        question = self.clarify()
        self.s.submit('REQ', self.entries())
        before = self.s.ok('phase.prepare')
        result = self.s.send('phase.complete', {'phase': 'REQ', 'revision_id': self.created['revision_id']},
                             expected_generation=before['generation'])
        self.assertEqual('CLARIFICATION_NOT_APPLIED', result['errors'][0]['code'])
        after = self.s.ok('phase.prepare')
        self.assertEqual(before['generation'], after['generation'])
        self.assertEqual('draft', after['content']['revision']['state'])
        self.assertEqual(question, after['pending_applications'][0]['question_step_id'])
        self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': NEW_SCOPE, 'out_of_scope': NEW_OUT}])
        self.s.complete('REQ')
        self.assertEqual([], self.s.ok('phase.prepare')['pending_applications'])

    def test_all_five_fields_partial_edits_and_idempotency(self):
        original = self.text()
        for name in ('title', 'summary', 'goal', 'in_scope', 'out_of_scope'):
            prepared = self.s.ok('phase.prepare')
            payload = {'phase': 'REQ', 'revision_id': self.created['revision_id'],
                       'operations': [{'op': 'update_revision_text', name: 'New '+name}]}
            extra = {'expected_generation': prepared['generation'], 'operation_id': 'update-'+name}
            a = self.s.send('phase.submit', payload, **extra)
            self.assertTrue(a['ok'], a)
            self.assertEqual(a, self.s.send('phase.submit', payload, **extra))
            changed = self.text()
            self.assertEqual('New '+name, changed[name])
            for other in ('title', 'summary', 'goal', 'in_scope', 'out_of_scope'):
                if other != name:
                    self.assertEqual(original[other], changed[other])
            original = changed
        self.assertEqual(5, self.text()['generation'])

    def test_stale_generation_rejects_text_and_does_not_overwrite(self):
        self.s.submit('REQ', [{'op': 'update_revision_text', 'goal': 'New goal'}])
        result = self.s.send('phase.submit', {'phase': 'REQ', 'revision_id': self.created['revision_id'],
            'operations': [{'op': 'update_revision_text', 'goal': 'Stale overwrite'}]}, expected_generation=0)
        self.assertEqual('GENERATION_CONFLICT', result['errors'][0]['code'])
        self.assertEqual('New goal', self.text()['goal'])

    def test_bad_relation_rolls_back_entire_batch_and_generation(self):
        before = self.s.ok('change.get')['content']
        result = self.s.send('phase.submit', {'phase': 'REQ', 'revision_id': self.created['revision_id'],
            'operations': [{'op': 'update_revision_text', 'in_scope': NEW_SCOPE},
                {'op': 'create_requirement', 'kind': 'behavior', 'statement': ANSWER, 'sources': [{'id': uid()}]}]},
            expected_generation=0)
        self.assertEqual('REFERENCE_SCOPE', result['errors'][0]['code'])
        self.assertEqual(before, self.s.ok('change.get')['content'])

    def test_post_write_fault_rolls_back_text_items_and_generation(self):
        question = self.clarify('/revision/goal')
        before = self.s.ok('change.get')['content']
        with patch('packages.sdlc.domain.validate_graph', side_effect=Fault('TEST_INJECTED', 'After all domain writes')):
            result = self.s.send('phase.submit', {'phase': 'REQ', 'revision_id': self.created['revision_id'],
                'operations': [{'op': 'update_revision_text', 'goal': 'Must roll back'}, *self.entries()]},
                expected_generation=0)
        self.assertEqual('TEST_INJECTED', result['errors'][0]['code'])
        self.assertEqual(before, self.s.ok('change.get')['content'])
        self.assertEqual(question, self.s.ok('phase.prepare')['pending_applications'][0]['question_step_id'])
        self.s.submit('REQ', [{'op': 'update_revision_text', 'goal': ANSWER}, *self.entries()])
        self.assertEqual([], self.s.ok('phase.prepare')['pending_applications'])

    def test_rejects_empty_null_blank_and_forbidden_fields(self):
        self.s.ok('run.configure', {'reason': 'Four distinct invalid-payload probes', 'max_format_attempts': 6})
        for update, code in [({}, 'EMPTY_UPDATE'), ({'goal': None}, 'INVALID_TYPE'),
                             ({'goal': '   '}, 'INVALID_TYPE'), ({'state': 'committed'}, 'UNKNOWN_FIELD')]:
            with self.subTest(update=update):
                result = self.s.send('phase.submit', {'phase': 'REQ', 'revision_id': self.created['revision_id'],
                    'operations': [{'op': 'update_revision_text', **update}]}, expected_generation=0)
                self.assertEqual(code, result['errors'][0]['code'])
                self.assertEqual(0, self.text()['generation'])

    def test_duplicate_text_operation_rejected_as_ambiguous(self):
        result = self.s.send('phase.submit', {'phase': 'REQ', 'revision_id': self.created['revision_id'],
            'operations': [{'op': 'update_revision_text', 'title': 'First'},
                           {'op': 'update_revision_text', 'title': 'Second'}]}, expected_generation=0)
        self.assertEqual('DUPLICATE_UPDATE', result['errors'][0]['code'])
        self.assertEqual('Count values', self.text()['title'])

    def test_committed_and_other_phase_cannot_be_modified(self):
        self.s.req()
        with Store(self.root).read() as con:
            old = dict(con.execute('SELECT * FROM revisions WHERE revision_id=?', (self.created['revision_id'],)).fetchone())
        result = self.s.send('phase.submit', {'phase': 'REQ', 'revision_id': old['revision_id'],
            'operations': [{'op': 'update_revision_text', 'goal': 'Corrupt history'}]}, expected_generation=old['generation'])
        self.assertEqual('STALE_REVISION', result['errors'][0]['code'])
        dsn = self.s.ok('phase.prepare')
        result = self.s.send('phase.submit', {'phase': 'DSN', 'revision_id': dsn['content']['revision']['revision_id'],
            'operations': [{'op': 'update_revision_text', 'goal': 'Wrong owner'}]}, expected_generation=dsn['generation'])
        self.assertEqual('PHASE_OWNERSHIP', result['errors'][0]['code'])
        self.s.ok('change.revise', {'phase': 'REQ', 'reason': 'Correct intent'}, expected_generation=dsn['generation'])
        self.s.submit('REQ', [{'op': 'update_revision_text', 'goal': 'Correct revised goal'}])
        self.s.complete('REQ')
        with Store(self.root).read() as con:
            self.assertEqual(old, dict(con.execute('SELECT * FROM revisions WHERE revision_id=?', (old['revision_id'],)).fetchone()))

    def test_different_change_cannot_be_targeted(self):
        other = Session(self.root)
        other.context = self.s.context
        other.new_change('other')
        result = other.send('phase.submit', {'phase': 'REQ', 'revision_id': self.created['revision_id'],
            'operations': [{'op': 'update_revision_text', 'title': 'Wrong change'}]}, expected_generation=0)
        self.assertEqual('REVISION_SCOPE', result['errors'][0]['code'])
        self.assertEqual('Count values', self.text()['title'])

    def test_unapplied_answer_follows_clone_and_new_run(self):
        self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': OLD_SCOPE}])
        question = self.clarify()
        self.s.submit('REQ', self.entries())
        copy_root = tempfile.TemporaryDirectory(prefix='sdlc-intent-copy-')
        self.addCleanup(copy_root.cleanup)
        target = Path(copy_root.name)
        self.s.ok('workspace.clone', {'target': str(target)})
        copied = Session(target)
        copied.bindings = {'change_id': self.s.bindings['change_id']}
        state = copied.send('run.start', {'actor_id': 'current-agent'})
        self.assertTrue(state['ok'], state)
        copied.bindings['run_id'] = state['run_id']
        prepared = copied.ok('phase.prepare')
        self.assertEqual(question, prepared['pending_applications'][0]['question_step_id'])
        copied.submit('REQ', [{'op': 'update_revision_text', 'in_scope': NEW_SCOPE}])
        copied.complete('REQ')
        self.assertEqual([], copied.ok('phase.prepare')['pending_applications'])
        # The source is an independent workspace; the copy cannot clear it remotely.
        self.assertEqual(1, len(self.s.ok('phase.prepare')['pending_applications']))

    def test_updated_field_does_not_resolve_another_question(self):
        self.clarify('/revision/in_scope')
        self.s.submit('REQ', [{'op': 'update_revision_text', 'summary': 'Only a summary edit'}])
        self.assertEqual(1, len(self.s.ok('phase.prepare')['pending_applications']))
        self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': NEW_SCOPE}])
        self.assertEqual([], self.s.ok('phase.prepare')['pending_applications'])
        self.clarify('/revision/in_scope')
        self.assertEqual(1, len(self.s.ok('phase.prepare')['pending_applications']))
        self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': NEW_SCOPE}])
        self.assertEqual([], self.s.ok('phase.prepare')['pending_applications'])

    def test_no_natural_language_keyword_gate_or_implicit_question_target(self):
        # This is intentionally descriptive historical text, not a machine state.
        self.s.submit('REQ', [{'op': 'update_revision_text', 'summary': '历史原文含等待明确，现决定仅改列表。'}])
        asked = self.s.send('run.request_input', {'revision_id': self.created['revision_id'],
            'question': 'Which behavior?', 'conflict': 'Ambiguous description with no exact target field'})
        self.assertEqual('/', asked['data']['field_path'])
        self.s.ok('run.answer_input', {'question_step_id': asked['data']['question_step_id'],
            'answer': 'Count values', 'basis_text': 'Explicit synthetic response'})
        self.assertEqual([], self.s.ok('phase.prepare')['pending_applications'])
        self.s.req()
        self.assertIn('等待明确', self.text()['summary'])

    def plan(self):
        req = self.s.req()
        checks = self.s.dsn(req)
        task = self.s.submit('PLN', [{'op': 'create_task', 'client_key': 'task', 'target_phase': 'IMP',
            'kind': 'implement', 'title': 'Count', 'description': 'Implement count', 'completion_text': 'Tests pass',
            'scope_paths': [{'resource': 'main', 'path': '.', 'access': 'write'}],
            'designs': [{'id': checks['design']}], 'criteria': [{'id': req['ac']}]}])['ids']['task']
        self.s.complete('PLN')
        return task, checks

    def fingerprints(self, task, checks):
        rev = self.text()['revision_id']
        with Store(self.root).read() as con:
            return (task_fingerprint(con, rev, task), check_fingerprint(con, rev, checks['test']),
                    check_fingerprint(con, rev, checks['review']))

    def test_scope_changes_invalidate_task_check_and_convergence_definitions(self):
        task, checks = self.plan()
        before = self.fingerprints(task, checks)
        self.s.ok('change.revise', {'phase': 'REQ', 'reason': 'Change scope'})
        self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': 'Updated acceptance scope'}])
        after = self.fingerprints(task, checks)
        self.assertTrue(all(a != b for a, b in zip(before, after)))

    def test_title_only_preserves_business_fingerprints_but_refreshes_full_review(self):
        task, checks = self.plan()
        before = self.fingerprints(task, checks)
        self.s.ok('change.revise', {'phase': 'REQ', 'reason': 'Improve display title'})
        self.s.submit('REQ', [{'op': 'update_revision_text', 'title': 'Count with a clearer title'}])
        after = self.fingerprints(task, checks)
        self.assertEqual(before[:2], after[:2])
        self.assertNotEqual(before[2], after[2])

    def test_scope_only_edit_rejects_reuse_of_prior_review_result(self):
        task, checks = self.plan()
        lease = self.s.ok('run.acquire')['lease_id']
        revision = self.text()['revision_id']
        result = self.s.ok('check.record_review', {'revision_id': revision, 'check_id': checks['review'],
            'lease_id': lease, 'status': 'pass', 'observations': 'Synthetic applicability fixture: inspected the original scope only.'})
        self.assertEqual('agent', result['source_kind'])
        self.s.ok('change.revise', {'phase': 'REQ', 'reason': 'Change only the effective scope'})
        self.s.submit('REQ', [{'op': 'update_revision_text', 'in_scope': 'Additional scope that the old review did not inspect'}])
        for phase in ('REQ', 'DSN', 'PLN'):
            self.s.complete(phase)
        attempted = self.s.send('check.reuse', {'revision_id': self.text()['revision_id'],
            'check_id': checks['review'], 'lease_id': lease})
        self.assertEqual('REUSE_INAPPLICABLE', attempted['errors'][0]['code'])

    def test_machine_schema_uses_same_five_fields_and_req_ownership(self):
        spec = contract()['operations']
        update = next(item for item in spec['REQ']['items']['oneOf']
                      if item['properties']['op']['const'] == 'update_revision_text')
        self.assertEqual({'op', 'title', 'summary', 'goal', 'in_scope', 'out_of_scope'}, set(update['properties']))
        self.assertEqual(5, len(update['anyOf']))
        self.assertFalse(update['additionalProperties'])
        for phase in ('DSN', 'PLN'):
            self.assertFalse(any(item['properties']['op']['const'] == 'update_revision_text'
                                 for item in spec[phase]['items']['oneOf']))


if __name__ == '__main__':
    unittest.main()
