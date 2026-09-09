"""Independent review counterexamples for repair scope and predecessor closure."""
import sys
import tempfile
import unittest
from pathlib import Path

from packages.sdlc.storage import Store
from test_runtime import Session


class RepairClosureTests(unittest.TestCase):
    def test_multi_level_source_task_remains_repairable(self):
        self.run_case('chain')

    def test_check_criteria_exclude_unrelated_completed_predecessor(self):
        self.run_case('branch')

    def test_condition_producer_is_in_the_same_repair_graph(self):
        self.run_case('precondition')

    def run_case(self, mode):
        with tempfile.TemporaryDirectory(prefix='sdlc-v2-repair-') as temp:
            root = Path(temp)
            s = Session(root)
            s.initialize()
            s.new_change(mode)
            req, dsn = s.req(), None
            dsn = s.dsn(req)
            def task(key, phase, path, criteria):
                return {'op': 'create_task', 'client_key': key, 'target_phase': phase,
                    'kind': 'verify' if phase == 'VFY' else 'implement', 'title': key,
                    'description': key+' bounded work', 'completion_text': 'Actual attempt saved',
                    'scope_paths': [{'resource': 'main', 'path': path, 'access': 'read' if phase == 'VFY' else 'write'}],
                    'designs': [{'id': dsn['design']}], 'criteria': [{'id': value} for value in criteria]}
            operations = [task('source', 'IMP', 'product.py', [req['ac']]),
                task('tests', 'IMP', 'test_product.py', [req['ac']]), task('unrelated', 'IMP', 'note.txt', []),
                task('verify', 'VFY', '.', [req['ac']]),
                {'op': 'update_check', 'id': dsn['test'], 'task': {'client_key': 'verify'},
                 'argv': [sys.executable, '-B', 'test_product.py'],
                 'input_paths': [{'resource': 'main', 'path': name, 'access': 'read'} for name in ['product.py', 'test_product.py']]},
                {'op': 'update_check', 'id': dsn['review'], 'task': {'client_key': 'verify'}}]
            edges = [('source', 'tests'), ('tests', 'verify')] if mode == 'chain' else [
                (key, 'verify') for key in (['source', 'tests', 'unrelated'] if mode == 'branch' else ['tests'])]
            operations += [{'op': 'add_task_dependency', 'task': {'client_key': consumer},
                'predecessor': {'client_key': producer}, 'reason': 'Actual execution order'} for producer, consumer in edges]
            if mode == 'precondition':
                operations += [
                    {'op': 'create_check', 'client_key': 'ready', 'task': {'client_key': 'source'},
                     'purpose': 'precondition', 'method': 'test', 'executor': 'command', 'description': 'Source importable',
                     'expected_result': 'Import succeeds', 'argv': [sys.executable, '-B', '-c', 'import product'],
                     'required': False, 'input_paths': [{'resource': 'main', 'path': 'product.py', 'access': 'read'}]},
                    {'op': 'create_precondition', 'consumer_task': {'client_key': 'verify'}, 'producer_task': {'client_key': 'source'},
                     'check': {'client_key': 'ready'}, 'enforce_at': 'start', 'reason': 'Source ready before verification'}]
            ids = s.submit('PLN', operations)['ids']
            revision = s.complete('PLN')['revision_id']
            base = {'revision_id': revision, 'lease_id': s.ok('run.acquire')['lease_id']}
            def start(key):
                return s.ok('task.start', {**base, 'task_id': ids[key]})['step_id']
            def finish(key, step):
                return s.ok('task.finish', {**base, 'task_id': ids[key], 'step_id': step, 'summary': 'Actual attempt saved'})
            def write(key, step, path, text):
                return s.ok('task.write', {**base, 'task_id': ids[key], 'step_id': step, 'files': [{'path': path, 'content': text}]})
            def ready():
                if mode == 'precondition':
                    self.assertEqual('pass', s.ok('check.run', {**base, 'check_id': ids['ready']})['outcome'])
            old = []
            for key, path, text in [('source', 'product.py', 'def count(values):\n    return 1\n'),
                    ('tests', 'test_product.py', 'from product import count\nassert count([]) == 0\nassert count([1,2]) == 2\n'),
                    ('unrelated', 'note.txt', 'independent bytes')]:
                step = start(key)
                write(key, step, path, text)
                if key == 'source':
                    ready()
                finish(key, step)
                old.append(step)
            s.ok('phase.complete', {**base, 'phase': 'IMP'})
            verifier = start('verify')
            red = s.ok('check.run', {**base, 'check_id': dsn['test']})
            self.assertEqual('fail', red['outcome'])
            review = {**base, 'check_id': dsn['review'], 'status': 'pass', 'observations': 'Self review; actual assertions remain authoritative'}
            s.ok('check.record_review', review)
            finish('verify', verifier)
            returned = s.send('phase.complete', {**base, 'phase': 'VFY'})
            self.assertEqual('needs_work', returned['status'])
            self.assertEqual({ids['source'], ids['tests']}, set(returned['next_actions'][0]['task_ids']))
            pending = {r['task']['task_id']: r['runnable'] for r in s.ok('task.next', {'revision_id': revision})['tasks']}
            self.assertEqual({ids['source']: True, ids['tests']: mode != 'chain'}, pending)
            repaired = start('source')
            write('source', repaired, 'product.py', 'def count(values):\n    return len(values)\n')
            ready()
            finish('source', repaired)
            finish('tests', start('tests'))
            s.ok('phase.complete', {**base, 'phase': 'IMP'})
            green = s.ok('check.run', {**base, 'check_id': dsn['test']})
            self.assertEqual('pass', green['outcome'])
            s.ok('finding.address', {'finding_id': red['finding_id'], 'lease_id': base['lease_id']})
            s.ok('finding.resolve', {'finding_id': red['finding_id'], 'result_id': green['result_id'], 'lease_id': base['lease_id']})
            s.ok('check.record_review', review)
            self.assertTrue(s.ok('phase.complete', {**base, 'phase': 'VFY'})['converged'])
            self.assertEqual('independent bytes', (root/'note.txt').read_text())
            with Store(root).read() as con:
                self.assertEqual(['completed']*3, [con.execute('SELECT status FROM steps WHERE step_id=?', (key,)).fetchone()[0] for key in old])
