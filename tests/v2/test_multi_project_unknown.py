"""Unknown Check receipts use each bound workspace, including project B.

All mutations go through public Runtime Session requests. Only the in-memory
finish_check callback is interrupted, after the real command worker has exited.
No SQLite or fabricated Check PASS results are used by this fixture.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_runtime import Session
from packages.sdlc import engine


class MultiProjectUnknownTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-multi-project-unknown-')
        self.root = Path(self.temp.name)
        self.a = Session(self.root)
        self.a.initialize()
        config = self.a.ok('workspace.inspect')['config']
        self.a.bindings = {key: config[key] for key in ('project_id', 'workspace_id')}
        other = self.a.ok('project.create', {'name': 'Second project unknown-result fixture'})
        self.b = Session(self.root)
        self.b.bindings = other
        self.b.context = self.b.ok('context.commit', {
            'summary': 'Independent project B in the same disposable Store',
            'entries': [{'kind': 'resource', 'name': 'main', 'content': 'Current fixture root',
                         'settings': {'resource': 'main'}}],
        })['context_id']
        self.assertNotEqual(self.a.bindings['project_id'], self.b.bindings['project_id'])
        self.assertNotEqual(self.a.bindings['workspace_id'], self.b.bindings['workspace_id'])

    def tearDown(self):
        self.temp.cleanup()

    def prepare_vfy(self, session, label):
        session.new_change('unknown-'+label)
        requirement = session.req()
        design = session.dsn(requirement)
        read_paths = [{'resource': 'main', 'path': label, 'access': 'read'}]
        planned = session.submit('PLN', [
            {'op': 'create_task', 'client_key': 'implement', 'target_phase': 'IMP', 'kind': 'implement',
             'title': 'Implement isolated count', 'description': 'Write the bounded count program and real assertions',
             'completion_text': 'Source and tests saved',
             'scope_paths': [{'resource': 'main', 'path': label, 'access': 'write'}],
             'designs': [{'id': design['design']}], 'criteria': [{'id': requirement['ac']}]},
            {'op': 'update_check', 'id': design['test'], 'task': {'client_key': 'implement'},
             'argv': [sys.executable, '-B', label+'/test_count.py'], 'input_paths': read_paths},
            {'op': 'update_check', 'id': design['review'], 'input_paths': read_paths},
        ])['ids']
        revision = session.complete('PLN')['revision_id']
        lease = session.ok('run.acquire')['lease_id']
        scope = {'revision_id': revision, 'lease_id': lease}
        task = {'task_id': planned['implement'], **scope}
        step = session.ok('task.start', task)['step_id']
        session.ok('task.write', {**task, 'step_id': step, 'files': [
            {'path': label+'/count.py', 'content': 'def count(values):\n    return len(values)\n'},
            {'path': label+'/test_count.py', 'content': 'from count import count\nassert count([]) == 0\nassert count([1, 2]) == 2\nprint("actual isolated count assertions passed")\n'},
        ]})
        session.ok('task.finish', {**task, 'step_id': step, 'summary': 'Actual source and assertions saved'})
        session.ok('phase.complete', {**scope, 'phase': 'IMP'})
        checked = session.ok('check.run', {**scope, 'check_id': design['test']})
        self.assertEqual(('pass', 0), (checked['outcome'], checked['exit_code']))
        session.ok('check.record_review', {**scope, 'check_id': design['review'], 'status': 'pass',
            'observations': 'Deterministic fixture self-review: exact implementation and actual empty/nonempty count assertions inspected.'})
        before = session.ok('check.evaluate', {'revision_id': revision})
        self.assertTrue(before['converged'], before)
        self.assertEqual([], before['unknown_operations'])
        return scope, design['test']

    def test_both_projects_expose_unknown_and_require_reconcile_before_vfy(self):
        for label, session in [('a', self.a), ('b', self.b)]:
            with self.subTest(project=label):
                scope, check = self.prepare_vfy(session, label)
                operation = label+'-unknown-check-receipt'
                with patch.object(engine, 'finish_check', side_effect=OSError(
                        'Isolated interruption after actual worker, before business result save')):
                    unknown = session.send('check.run', {**scope, 'check_id': check}, operation_id=operation)
                self.assertEqual('unknown', unknown['status'], unknown)
                work = self.root/'.sdlc/runs'/session.bindings['run_id']/operation/'work'
                actual = json.loads((work/'result.json').read_text())
                self.assertEqual(('command', 'pass', 0),
                                 (actual['source_kind'], actual['status'], actual['exit_code']))
                self.assertIn('actual isolated count assertions passed', actual['stdout'])

                evaluation = session.ok('check.evaluate', {'revision_id': scope['revision_id']})
                # Try the mutation even if the read-only diagnostic is wrong, so
                # a failure still records whether phase advancement was blocked.
                blocked = session.send('phase.complete', {**scope, 'phase': 'VFY'})
                self.assertFalse(blocked['ok'], blocked)
                self.assertEqual('UNRESOLVED_EFFECT', blocked['errors'][0]['code'])
                self.assertEqual([operation], blocked['errors'][0]['details'])
                self.assertFalse(evaluation['converged'], evaluation)
                self.assertEqual([operation], evaluation['unknown_operations'])

                recovered = session.ok('operation.reconcile', {'operation_id': operation})
                self.assertEqual('pass', recovered['original_receipt']['data']['outcome'])
                after = session.ok('check.evaluate', {'revision_id': scope['revision_id']})
                self.assertTrue(after['converged'], after)
                self.assertEqual([], after['unknown_operations'])
                advanced = session.ok('phase.complete', {**scope, 'phase': 'VFY'})
                self.assertTrue(advanced['converged'], advanced)
                self.assertEqual('RLS', advanced['next_actions'][0]['phase'])
                session.ok('run.cancel', {'reason': 'Bounded unknown receipt regression complete; no delivery requested.'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
