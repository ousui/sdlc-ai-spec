"""A real Agent decision is required, recorded and recoverable without SQL edits."""
import tempfile
import json
import unittest
from pathlib import Path

from test_runtime import Session
import test_execution as execution_fixture
from packages.sdlc.storage import Store


class ClarificationTests(unittest.TestCase):
    def test_conflict_paths_are_redacted_in_receipts_and_durable_diagnostics(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-v2-question-secret-') as temp:
            root = Path(temp)
            s = Session(root, cli=True)
            s.initialize()
            created = s.new_change('path-redaction')
            secret = 'SYNTHETIC-PATH-SECRET'
            asked = s.send('run.request_input', {'revision_id': created['revision_id'],
                'question': 'Which value is intended?', 'conflict': 'Conflicting input',
                'field_path': '/requirements/password='+secret})
            self.assertEqual('needs_input', asked['status'])
            self.assertNotIn(secret, json.dumps(asked))
            self.assertIn('[REDACTED]', asked['errors'][0]['path'])
            self.assertNotIn(secret, json.dumps(s.ok('run.get')))
            refused = s.send('run.resume', {'reason': 'Still no answer'})
            self.assertNotIn(secret, json.dumps(refused))
            for path in (root/'.sdlc/runs').rglob('*'):
                if path.is_file() and path.suffix in {'.json', '.html', '.log'}:
                    self.assertNotIn(secret, path.read_text(), str(path))

    def test_conflict_preserves_source_blocks_progress_and_records_actual_answer(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-v2-question-') as temp:
            root = Path(temp)
            s = Session(root, cli=True)
            s.initialize()
            created = s.new_change('conflicting-goals')
            before = s.ok('change.get')['content']
            question = {'revision_id': created['revision_id'], 'question': 'Should empty input return zero or be rejected?',
                        'conflict': 'The two supplied goals prescribe different empty-input behavior.', 'field_path': '/revision/goal'}
            asked = s.send('run.request_input', question, operation_id='question-1')
            self.assertEqual('needs_input', asked['status'])
            self.assertEqual('/revision/goal', asked['errors'][0]['path'])
            self.assertEqual('ask_user', asked['next_actions'][0]['action'])
            self.assertEqual(asked, s.send('run.request_input', question, operation_id='question-1'))
            self.assertEqual('OPERATION_CONFLICT', s.send('run.request_input', {**question, 'question': 'Different question'}, operation_id='question-1')['errors'][0]['code'])
            saved = s.ok('run.get')
            self.assertEqual(asked['data']['question_step_id'], saved['pending_inputs'][0]['question_step_id'])
            for command, payload in [('phase.submit', {'phase': 'REQ', 'revision_id': created['revision_id'], 'operations': []}),
                                     ('run.resume', {'reason': 'This is not an answer'})]:
                refused = s.send(command, payload, expected_generation=0)
                self.assertEqual('needs_input', refused['status'])
            newer_run = Session(root, cli=True)
            refused = newer_run.send('run.start', {'actor_id': 'current-agent'}, change_id=created['change_id'])
            self.assertEqual('needs_input', refused['status'])
            self.assertEqual(before, s.ok('change.get')['content'])
            response = {'question_step_id': asked['data']['question_step_id'], 'answer': 'Return zero for empty input.',
                        'basis_text': 'Synthetic user response in this acceptance fixture; no human review is claimed.'}
            answered = s.send('run.answer_input', response, operation_id='answer-1')
            self.assertTrue(answered['ok'], answered)
            self.assertFalse(answered['data']['grants_authority'])
            self.assertEqual('current-agent', answered['data']['recorded_by'])
            self.assertEqual(answered, s.send('run.answer_input', response, operation_id='answer-1'))
            self.assertEqual([], s.ok('phase.prepare', {'phase': 'REQ'})['pending_inputs'])
            self.assertFalse(answered['data']['content_applied'])
            s.submit('REQ', [{'op': 'create_source', 'kind': 'text', 'original_text': response['answer']},
                             {'op': 'update_revision_text', 'goal': response['answer']}])
            s.req()
            with Store(root).read() as con:
                self.assertEqual('auto', con.execute('SELECT review_mode FROM runs WHERE run_id=?', (s.bindings['run_id'],)).fetchone()[0])
                self.assertEqual('completed', con.execute('SELECT status FROM steps WHERE step_id=?', (response['question_step_id'],)).fetchone()[0])
            archive = Session(root, cli=True).ok('workspace.export', {'change_id': created['change_id']})
            self.assertTrue(Path(archive['path']).is_file())

    def test_another_change_cannot_answer_selected_question(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-v2-question-scope-') as temp:
            s = Session(Path(temp), cli=True)
            s.initialize()
            first = s.new_change('first')
            asked = s.send('run.request_input', {'revision_id': first['revision_id'], 'question': 'Which empty-input behavior?', 'conflict': 'Two incompatible choices'})
            other = Session(Path(temp), cli=True)
            other.context = s.context
            other.new_change('second')
            refused = other.send('run.answer_input', {'question_step_id': asked['data']['question_step_id'],
                                 'answer': 'Zero', 'basis_text': 'Synthetic answer for the wrong change'})
            self.assertEqual('INPUT_SCOPE', refused['errors'][0]['code'])
            self.assertEqual(1, len(s.ok('run.get')['pending_inputs']))

    def test_pending_question_blocks_real_product_effects_without_losing_attempt(self):
        fixture = execution_fixture.ExecutionFlowTests()
        try:
            fixture.setUp()
            step = fixture.start()
            asked = fixture.s.send('run.request_input', {'revision_id': fixture.rev,
                'question': 'Which counting behavior is intended?', 'conflict': 'Conflicting requirement found during implementation'})
            self.assertEqual('needs_input', asked['status'])
            refused = fixture.s.send('task.write', {'revision_id': fixture.rev, 'task_id': fixture.task,
                'step_id': step, 'lease_id': fixture.lease, 'files': [{'path': 'product.py', 'content': 'unexpected'}]})
            self.assertEqual('needs_input', refused['status'])
            self.assertFalse((fixture.root/'product.py').exists())
            fixture.s.ok('run.answer_input', {'question_step_id': asked['data']['question_step_id'],
                'answer': 'Return the sequence length.', 'basis_text': 'Synthetic acceptance reply'})
            fixture.write(step, True)
            fixture.finish(step)
            self.assertTrue((fixture.root/'product.py').is_file())
        finally:
            fixture.tearDown()
