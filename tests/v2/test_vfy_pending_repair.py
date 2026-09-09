"""Portable regression candidate for tests/v2; actual native command results."""
import sys
import tempfile
import unittest
from pathlib import Path

from test_runtime import Session


class VerificationCompletionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='sdlc-vfy-completion-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.session = Session(self.root)
        self.session.initialize()
        self.session.new_change()
        self.req = self.session.req()
        self.dsn = self.session.dsn(self.req)
        operations = []
        for key, phase, kind in (
            ('implement', 'IMP', 'implement'),
            ('verify', 'VFY', 'verify'),
            ('review', 'VFY', 'review'),
        ):
            operations.append({
                'op': 'create_task', 'client_key': key,
                'target_phase': phase, 'kind': kind, 'title': key,
                'description': 'Execute the declared '+key+' responsibility',
                'completion_text': 'Applicable required checks pass before completion',
                'scope_paths': [{'resource': 'main', 'path': '.',
                                 'access': 'write' if key == 'implement' else 'read'}],
                'designs': [{'id': self.dsn['design']}],
                'criteria': [{'id': self.req['ac']}],
            })
        operations.extend([
            {'op': 'add_task_dependency', 'task': {'client_key': 'verify'},
             'predecessor': {'client_key': 'implement'}, 'reason': 'Verify actual implementation'},
            {'op': 'add_task_dependency', 'task': {'client_key': 'review'},
             'predecessor': {'client_key': 'verify'}, 'reason': 'Review completed verification'},
            {'op': 'update_check', 'id': self.dsn['test'],
             'task': {'client_key': 'verify'}, 'argv': [sys.executable, 'test_product.py']},
            {'op': 'update_check', 'id': self.dsn['review'], 'task': {'client_key': 'review'}},
        ])
        for task, check in (('verify', 'test'), ('review', 'review')):
            operations.append({
                'op': 'create_precondition', 'consumer_task': {'client_key': task},
                'producer_task': {'client_key': task}, 'check': {'id': self.dsn[check]},
                'enforce_at': 'complete', 'reason': 'Actual pass is required at completion',
            })
        self.tasks = self.session.submit('PLN', operations)['ids']
        self.revision = self.session.complete('PLN')['revision_id']
        self.lease = self.session.ok('run.acquire')['lease_id']
        self.original_implementation = self.start('implement')
        self.session.ok('task.write', self.payload(
            task_id=self.tasks['implement'], step_id=self.original_implementation,
            files=[
                {'path': 'product.py', 'content': 'def count(values):\n    return 1\n'},
                {'path': 'test_product.py', 'content':
                 'from product import count\nassert count([]) == 0\n'
                 'assert count([1, 2]) == 2\nprint("actual assertions passed")\n'},
            ]))
        self.finish('implement', self.original_implementation)
        self.session.ok('phase.complete', self.payload(phase='IMP'))
        self.original_verifier = self.start('verify')

    def payload(self, **values):
        return {'revision_id': self.revision, 'lease_id': self.lease, **values}

    def start(self, task):
        return self.session.ok('task.start', self.payload(task_id=self.tasks[task]))['step_id']

    def finish(self, task, step):
        return self.session.ok('task.finish', self.payload(
            task_id=self.tasks[task], step_id=step, summary='Actual declared task work completed'))

    def assert_blocked(self, code, command, payload):
        response = self.session.send(command, payload)
        self.assertFalse(response['ok'], response)
        self.assertEqual(code, response['errors'][0]['code'], response)
        return response

    def test_missing_results_do_not_interrupt_tasks_or_consume_repair_round(self):
        response = self.assert_blocked(
            'VERIFICATION_PENDING', 'phase.complete', self.payload(phase='VFY'))
        evaluation = response['errors'][0]['details']
        self.assertEqual([], evaluation['failed_checks'])
        self.assertEqual([], evaluation['blocking_findings'])
        self.assertTrue(evaluation['missing_checks'])
        self.assertIn(self.tasks['verify'], evaluation['pending_tasks'])
        state = self.session.ok('run.get')
        self.assertEqual(('VFY', 0), (state['run']['current_phase'], state['run']['repair_round']))
        original = next(step for step in state['steps'] if step['step_id'] == self.original_verifier)
        self.assertEqual('running', original['status'])
        self.assertIsNone(original['finished_at'])

    def test_failed_completion_condition_returns_to_repair_with_unchanged_plan(self):
        before = self.session.ok('phase.prepare', {'phase': 'VFY'})['content']
        red = self.session.ok('check.run', self.payload(check_id=self.dsn['test']))
        self.assertEqual(('fail', 1), (red['outcome'], red['exit_code']))
        self.assert_blocked('TASK_BLOCKED', 'task.finish', self.payload(
            task_id=self.tasks['verify'], step_id=self.original_verifier,
            summary='Attempt ended but its required check failed'))
        self.assert_blocked('TASK_BLOCKED', 'task.start', self.payload(task_id=self.tasks['review']))
        returned = self.session.send('phase.complete', self.payload(phase='VFY'))
        self.assertEqual('needs_work', returned['status'], returned)
        self.assertEqual(('IMP', [self.tasks['implement']]),
                         (returned['next_actions'][0]['phase'], returned['next_actions'][0]['task_ids']))
        state = self.session.ok('run.get')
        attempts = {step['step_id']: step for step in state['steps']}
        self.assertEqual(('interrupted', 'unknown'),
                         (attempts[self.original_verifier]['status'], attempts[self.original_verifier]['outcome']))
        self.assertEqual('completed', attempts[self.original_implementation]['status'])
        self.assertEqual(1, state['run']['repair_round'])
        tasks = self.session.ok('task.next', {'revision_id': self.revision})['tasks']
        self.assertEqual([(self.tasks['implement'], True)],
                         [(row['task']['task_id'], row['runnable']) for row in tasks])
        repair = self.start('implement')
        self.assertNotEqual(self.original_implementation, repair)
        self.session.ok('task.write', self.payload(
            task_id=self.tasks['implement'], step_id=repair,
            files=[{'path': 'product.py', 'content': 'def count(values):\n    return len(values)\n'}]))
        self.finish('implement', repair)
        self.session.ok('finding.address', {'finding_id': red['finding_id'], 'lease_id': self.lease})
        self.session.ok('phase.complete', self.payload(phase='IMP'))
        new_verifier = self.start('verify')
        self.assertNotEqual(self.original_verifier, new_verifier)
        green = self.session.ok('check.run', self.payload(check_id=self.dsn['test']))
        self.assertEqual(('pass', 0), (green['outcome'], green['exit_code']))
        self.assertNotEqual(red['result_id'], green['result_id'])
        self.session.ok('finding.resolve', {
            'finding_id': red['finding_id'], 'result_id': green['result_id'], 'lease_id': self.lease})
        self.finish('verify', new_verifier)
        review = self.start('review')
        self.session.ok('check.record_review', self.payload(
            check_id=self.dsn['review'], status='pass',
            observations='Fixture review: exact length implementation now satisfies retained assertions; '
                         'real pass follows original failure, with unchanged requirements and conditions.'))
        self.finish('review', review)
        final = self.session.ok('phase.complete', self.payload(phase='VFY'))
        self.assertTrue(final['converged'])
        after = self.session.ok('phase.prepare', {'phase': 'RLS'})['content']
        self.assertEqual(before, after, 'Repair must not alter the committed snapshot or its conditions/dependencies')
        state = self.session.ok('run.get')
        self.assertEqual(('RLS', 1), (state['run']['current_phase'], state['run']['repair_round']))
        findings = self.session.ok('finding.list')['findings']
        finding = next(row for row in findings if row['finding_id'] == red['finding_id'])
        self.assertEqual(('resolved', red['result_id'], green['result_id']),
                         (finding['status'], finding['result_id'], finding['resolution_result_id']))


if __name__ == '__main__':
    unittest.main()
