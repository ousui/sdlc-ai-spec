"""Delivery-only criteria: public CLI fixture, not actual business acceptance.

Mutations and execution use test_runtime.Session(cli=True). SQLite is read only
and used solely to prove no premature result and the actual native result source.
"""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from test_runtime import Session
from packages.sdlc.storage import Store


class ReleaseCriteriaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-release-criteria-')
        self.root = Path(self.temp.name)
        self.s = Session(self.root, cli=True)
        self.s.initialize()
        self.s.new_change('release-criteria')
        self.req = self.s.submit('REQ', [
            {'op': 'create_source', 'client_key': 'release_source', 'kind': 'text',
             'original_text': 'Deterministic fixture: deliver this counted-values program as a local package and independently read back its exact bytes.'},
            {'op': 'create_requirement', 'client_key': 'product', 'kind': 'behavior',
             'statement': 'Count empty and nonempty collections', 'sources': [{'id': self.s.source}]},
            {'op': 'create_requirement', 'client_key': 'release', 'kind': 'constraint',
             'statement': 'Actually write and independently read back the local package',
             'sources': [{'client_key': 'release_source'}]},
            {'op': 'create_criterion', 'client_key': 'product_ac',
             'condition_text': 'Empty and nonempty collections', 'expected_result': 'Their exact lengths are returned',
             'requirements': [{'client_key': 'product'}]},
            {'op': 'create_criterion', 'client_key': 'release_ac',
             'condition_text': 'RLS local delivery', 'expected_result': 'The written package and manifest pass independent native readback',
             'requirements': [{'client_key': 'release'}]},
        ])['ids']
        self.s.complete('REQ')

    def tearDown(self):
        self.temp.cleanup()

    def design(self, **readback_changes):
        readback = {
            'op': 'create_check', 'client_key': 'readback', 'purpose': 'release_readback',
            'method': 'test', 'executor': 'command', 'description': 'Independently verify the local package',
            'expected_result': 'Actual target bytes match the exact prepared package and manifest',
            'argv': ['@runtime', 'delivery.readback'], 'required': True,
            'criteria': [{'id': self.req['release_ac']}],
        }
        readback.update(readback_changes)
        if readback.get('argv') is None:
            readback.pop('argv')
        designs = [
            {'op': 'create_design', 'client_key': key, 'domain': 'components', 'title': title,
             'decision': decision, 'rationale': 'Minimal deterministic fixture', 'alternatives': 'No remote target',
             'detail': detail, 'requirements': [{'id': self.req[requirement]}]}
            for key, title, decision, detail, requirement in [
                ('product_design', 'Collection length', 'Use len(values)', 'Test empty and nonempty collections', 'product'),
                ('release_design', 'Local package', 'Use native delivery and independent readback', 'Evaluate after converged VFY in RLS', 'release'),
            ]
        ]
        self.dsn = self.s.submit('DSN', designs + [
            {'op': 'create_check', 'client_key': 'test', 'purpose': 'acceptance', 'method': 'test',
             'executor': 'command', 'description': 'Execute actual count assertions', 'expected_result': 'Both assertions pass',
             'argv': [sys.executable, 'test_product.py'], 'required': True,
             'criteria': [{'id': self.req['product_ac']}]},
            {'op': 'create_check', 'client_key': 'review', 'purpose': 'convergence', 'method': 'inspection',
             'executor': 'agent', 'description': 'Inspect deterministic fixture scope',
             'expected_result': 'No unresolved product gaps; actual delivery is still pending RLS', 'required': True},
            readback,
        ])['ids']

    def assert_coverage_rejected(self, **readback_changes):
        self.design(**readback_changes)
        prepared = self.s.ok('phase.prepare', {'phase': 'DSN'})
        response = self.s.send('phase.complete', {
            'phase': 'DSN', 'revision_id': prepared['content']['revision']['revision_id'],
        }, expected_generation=prepared['generation'])
        self.assertFalse(response['ok'], response)
        self.assertEqual('PHASE_INCOMPLETE', response['errors'][0]['code'])
        self.assertEqual([{
            'code': 'COVERAGE_MISSING', 'table': 'criteria', 'id': self.req['release_ac'],
            'relationship': 'check_criteria',
        }], response['errors'][0]['details'])

    def test_optional_native_readback_cannot_cover_delivery_criterion(self):
        self.assert_coverage_rejected(required=False)

    def test_agent_readback_cannot_cover_delivery_criterion(self):
        self.assert_coverage_rejected(executor='agent', method='inspection', argv=None)

    def test_arbitrary_command_readback_cannot_cover_delivery_criterion(self):
        self.assert_coverage_rejected(argv=['/bin/sh', '-c', 'exit 0'])

    def test_delivery_only_criterion_advances_then_requires_actual_rls_readback(self):
        self.design()
        self.s.complete('DSN')
        planned = self.s.submit('PLN', [
            {'op': 'create_task', 'client_key': 'implement', 'target_phase': 'IMP', 'kind': 'implement',
             'title': 'Implement count', 'description': 'Write the fixture program and actual assertions',
             'completion_text': 'Program and assertions saved',
             'scope_paths': [{'resource': 'main', 'path': '.', 'access': 'write'}],
             'designs': [{'id': self.dsn['product_design']}], 'criteria': [{'id': self.req['product_ac']}]},
            {'op': 'create_task', 'client_key': 'deliver', 'target_phase': 'RLS', 'kind': 'deliver',
             'title': 'Deliver local package', 'description': 'Prepare, write and independently read back the exact local package',
             'completion_text': 'Actual native package readback succeeded',
             'scope_paths': [{'resource': 'main', 'path': '.', 'access': 'read'}],
             'designs': [{'id': self.dsn['release_design']}], 'criteria': [{'id': self.req['release_ac']}]},
            {'op': 'update_check', 'id': self.dsn['test'], 'task': {'client_key': 'implement'}},
            {'op': 'update_check', 'id': self.dsn['readback'], 'task': {'client_key': 'deliver'}},
        ])['ids']
        revision = self.s.complete('PLN')['revision_id']
        lease = self.s.ok('run.acquire')['lease_id']
        scope = {'revision_id': revision, 'lease_id': lease}
        step = self.s.ok('task.start', {**scope, 'task_id': planned['implement']})['step_id']
        self.s.ok('task.write', {**scope, 'task_id': planned['implement'], 'step_id': step, 'files': [
            {'path': 'product.py', 'content': 'def count(values):\n    return len(values)\n'},
            {'path': 'test_product.py', 'content': 'from product import count\nassert count([]) == 0\nassert count([1, 2]) == 2\nprint("two actual count assertions passed")\n'},
        ]})
        self.s.ok('task.finish', {**scope, 'task_id': planned['implement'], 'step_id': step,
                                 'summary': 'Actual fixture source and assertions saved'})
        self.s.ok('phase.complete', {**scope, 'phase': 'IMP'})
        result = self.s.ok('check.run', {**scope, 'check_id': self.dsn['test']})
        self.assertEqual(('pass', 0), (result['outcome'], result['exit_code']))
        self.s.ok('check.record_review', {**scope, 'check_id': self.dsn['review'], 'status': 'pass',
            'observations': 'Deterministic fixture self-review: exact len implementation and both actual count assertions inspected. Local release has not yet occurred.'})
        evaluation = self.s.ok('check.evaluate', {'revision_id': revision})
        self.assertTrue(evaluation['converged'], evaluation)
        self.assertNotIn(self.dsn['readback'], [row['check_id'] for row in evaluation['checks']])
        vfy = self.s.ok('phase.complete', {**scope, 'phase': 'VFY'})
        self.assertEqual('RLS', vfy['next_actions'][0]['phase'])
        with Store(self.root).read() as con:
            self.assertEqual(0, con.execute('SELECT count(*) FROM check_results WHERE check_id=?',
                                           (self.dsn['readback'],)).fetchone()[0])
        pending = self.s.send('phase.complete', {**scope, 'phase': 'RLS'})
        self.assertEqual('DELIVERY_PENDING', pending['errors'][0]['code'])
        release_step = self.s.ok('task.start', {**scope, 'task_id': planned['deliver']})['step_id']
        prepared = self.s.ok('delivery.prepare', {**scope, 'usage': 'Run test_product.py with the recorded Python interpreter.'})
        target = self.root/prepared['package_path']
        self.assertFalse(target.exists())
        pending = self.s.send('phase.complete', {**scope, 'phase': 'RLS'})
        self.assertEqual('DELIVERY_PENDING', pending['errors'][0]['code'])
        delivered = self.s.ok('delivery.execute', {'delivery_id': prepared['delivery_id'], 'lease_id': lease})
        self.assertEqual(('succeeded', 'pass'), (delivered['status'], delivered['outcome']))
        self.assertEqual(prepared['package_sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
        with zipfile.ZipFile(target) as archive:
            self.assertEqual('def count(values):\n    return len(values)\n', archive.read('code/main/product.py').decode())
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(revision, manifest['revision_id'])
        self.s.ok('task.finish', {**scope, 'task_id': planned['deliver'], 'step_id': release_step,
                                 'summary': 'Exact local package was written and independently read back'})
        closed = self.s.ok('phase.complete', {**scope, 'phase': 'RLS'})
        self.assertEqual('completed', closed['status'])
        self.assertEqual(delivered['result_id'], closed['readback_result_id'])
        with Store(self.root).read() as con:
            results = con.execute('SELECT result_id,source_kind,status FROM check_results WHERE check_id=?',
                                  (self.dsn['readback'],)).fetchall()
            self.assertEqual([(delivered['result_id'], 'command', 'pass')], [tuple(row) for row in results])


if __name__ == '__main__':
    unittest.main(verbosity=2)
