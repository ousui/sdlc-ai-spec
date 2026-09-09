"""Real macOS command tests; run outside an already-nested Seatbelt sandbox."""
import json
import os
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import unittest
from pathlib import Path

from packages.sdlc.common import Fault, uid
from packages.sdlc.execution import observe, run_command
from packages.sdlc.storage import Store
from test_runtime import Session


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-v2-collector-')
        self.root = Path(self.temp.name)
        self.product = self.root/'product'
        self.product.mkdir()
        self.work = self.product/'.sdlc/runs/example/work'

    def tearDown(self):
        self.temp.cleanup()

    def command(self, script, **kwargs):
        return run_command([sys.executable, '-c', script], self.product, self.work, [(self.product, '.')], **kwargs)

    def test_actual_exit_and_assertion_failure_are_separate(self):
        good = self.command('print("actual stdout")')
        bad = self.command('assert False, "actual failed assertion"')
        self.assertEqual(('pass', 0), (good['status'], good['exit_code']))
        self.assertEqual(('fail', 1), (bad['status'], bad['exit_code']))
        self.assertIn('actual failed assertion', bad['stderr'])

    def test_command_cannot_write_outside_scope_or_forge_evidence(self):
        outside = self.root/'outside.txt'
        script = 'from pathlib import Path; Path('+repr(str(outside))+').write_text("outside")'
        self.assertEqual('fail', self.command(script)['status'])
        self.assertFalse(outside.exists())
        protected = self.work/'intent.json'
        protected.write_text('protected intent')
        forged = self.command('from pathlib import Path; Path('+repr(str(protected))+').write_text("forged")')
        self.assertEqual('fail', forged['status'])
        self.assertEqual('protected intent', protected.read_text())

    def test_output_is_bounded_and_redacted(self):
        secret = 'SYNTHETIC-COLLECTOR-ONLY'
        data = self.command('print("password='+secret+'")')
        self.assertNotIn(secret, data['stdout'])
        self.assertNotIn(secret, (self.work/'stdout.log').read_text())
        limited = self.command('print("X"*20000)', output_limit=1024)
        self.assertEqual('OUTPUT_LIMIT', limited['error_code'])
        self.assertNotEqual('pass', limited['status'])
        self.assertTrue(limited['truncated'])

    def test_timeout_retains_actual_failure(self):
        data = self.command('import time; time.sleep(5)', timeout=1)
        self.assertEqual('TOOL_TIMEOUT', data['error_code'])
        self.assertEqual('fail', data['status'])
        self.assertLess(data['duration_ms'], 3000)

    def test_closed_streams_still_obey_timeout(self):
        data = self.command('import os,time; os.close(1); os.close(2); time.sleep(8)', timeout=1)
        self.assertEqual(('fail', 'TOOL_TIMEOUT'), (data['status'], data['error_code']))
        self.assertLess(data['duration_ms'], 2500)

    def test_scratch_directory_is_writable_through_macos_tmp_alias(self):
        result = self.command('import tempfile; from pathlib import Path; d=tempfile.mkdtemp(); Path(d,"build.txt").write_text("output")')
        self.assertEqual('pass', result['status'], result['stderr'])

    def test_background_descendant_cannot_outlive_a_pass(self):
        code = 'import time; from pathlib import Path; time.sleep(1); Path("late.txt").write_text("late")'
        data = self.command('import subprocess,sys; subprocess.Popen([sys.executable,"-c",'+repr(code)+'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)')
        self.assertEqual(('fail', 'TOOL_DESCENDANTS'), (data['status'], data['error_code']))
        time.sleep(1.2)
        self.assertFalse((self.product/'late.txt').exists())

    def test_python_dependency_bytes_change_environment_identity(self):
        from packages.sdlc.execution import environment, environment_identity
        dependency = self.root/'dependency'
        dependency.mkdir()
        (dependency/'choice.py').write_text('value=1')
        env = environment({'PYTHONPATH': str(dependency)})
        first = environment_identity(env, [sys.executable])
        (dependency/'choice.py').write_text('value=0')
        second = environment_identity(env, [sys.executable])
        self.assertNotEqual(first, second)

    def test_fork_exec_supported_and_session_escapes_denied(self):
        ordinary = self.command('import subprocess,sys; r=subprocess.run([sys.executable,"-c","print(123)"]); assert r.returncode==0')
        self.assertEqual(('pass', 0), (ordinary['status'], ordinary['exit_code']))
        scripts = [
            'import os; os.setsid()',
            'import subprocess,sys; subprocess.Popen([sys.executable,"-c","pass"], start_new_session=True)',
            'import os,sys; os.posix_spawn(sys.executable,[sys.executable,"-c","pass"],os.environ,setsid=True)',
            'import os,sys; os.posix_spawn(sys.executable,[sys.executable,"-c","pass"],os.environ,setpgroup=0)',
        ]
        for script in scripts:
            result = self.command(script)
            self.assertEqual('fail', result['status'], script)
            self.assertIn('Operation not permitted', result['stderr'])

    def test_dependency_symlink_is_explicitly_blocked(self):
        from packages.sdlc.execution import environment, environment_identity
        dependency = self.root/'dependency'
        dependency.mkdir()
        external = self.root/'external'
        external.mkdir()
        (external/'__init__.py').write_text('value=1')
        (dependency/'package').symlink_to(external, target_is_directory=True)
        with self.assertRaises(Fault) as caught:
            environment_identity(environment({'PYTHONPATH': str(dependency)}), [sys.executable])
        self.assertEqual('DEPENDENCY_SYMLINK', caught.exception.code)

    def test_unrelated_file_does_not_change_subject_but_build_file_does(self):
        (self.product/'app.py').write_text('value = 1\n')
        first = observe(self.product, ['app.py'])
        (self.product/'unrelated.md').write_text('other work')
        second = observe(self.product, ['app.py'])
        self.assertEqual(first['digest'], second['digest'])
        (self.product/'pyproject.toml').write_text('[project]\nname="sample"\n')
        third = observe(self.product, ['app.py'])
        self.assertNotEqual(second['digest'], third['digest'])


class ExecutionFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-v2-flow-')
        self.root = Path(self.temp.name)
        self.s = Session(self.root)
        self.s.initialize()
        self.s.new_change()
        self.req = self.s.req()
        self.dsn = self.s.dsn(self.req)
        prepared = self.s.submit('PLN', [
            {'op': 'create_task', 'client_key': 'implement', 'target_phase': 'IMP', 'kind': 'implement',
             'title': 'Implement value count', 'description': 'Implement the declared collection behavior and assertions',
             'completion_text': 'Code and tests saved', 'scope_paths': [{'resource': 'main', 'path': '.', 'access': 'write'}],
             'designs': [{'id': self.dsn['design']}], 'criteria': [{'id': self.req['ac']}]},
            {'op': 'update_check', 'id': self.dsn['test'], 'task': {'client_key': 'implement'},
             'argv': [sys.executable, 'test_product.py']}])
        self.task = prepared['ids']['implement']
        self.rev = self.s.complete('PLN')['revision_id']
        self.lease = self.s.ok('run.acquire')['lease_id']

    def tearDown(self):
        self.temp.cleanup()

    def start(self):
        return self.s.ok('task.start', {'revision_id': self.rev, 'task_id': self.task, 'lease_id': self.lease})['step_id']

    def write(self, step, correct):
        return self.s.ok('task.write', {'revision_id': self.rev, 'task_id': self.task, 'step_id': step, 'lease_id': self.lease,
            'files': [{'path': 'product.py', 'content': 'def count(values):\n    return '+('len(values)' if correct else '1')+'\n'},
                      {'path': 'test_product.py', 'content': 'from product import count\nassert count([]) == 0\nassert count([1,2]) == 2\nprint("two product assertions passed")\n'}]})

    def finish(self, step):
        return self.s.ok('task.finish', {'revision_id': self.rev, 'task_id': self.task, 'step_id': step, 'lease_id': self.lease, 'summary': 'Actual code and assertions saved'})

    def test_red_green_retest_and_runtime_convergence(self):
        step = self.start()
        self.write(step, False)
        self.finish(step)
        self.s.ok('phase.complete', {'phase': 'IMP', 'revision_id': self.rev, 'lease_id': self.lease})
        red = self.s.ok('check.run', {'revision_id': self.rev, 'check_id': self.dsn['test'], 'lease_id': self.lease})
        self.assertEqual('fail', red['outcome'])
        review = self.s.ok('check.record_review', {'revision_id': self.rev, 'check_id': self.dsn['review'], 'lease_id': self.lease,
                         'status': 'pass', 'observations': 'Fixture self-review; actual command assertion is authoritative for behavior.'})
        return_to_imp = self.s.send('phase.complete', {'phase': 'VFY', 'revision_id': self.rev, 'lease_id': self.lease})
        self.assertEqual('needs_work', return_to_imp['status'])
        self.assertEqual('IMP', return_to_imp['next_actions'][0]['phase'])
        step = self.start()
        self.write(step, True)
        self.finish(step)
        self.s.ok('finding.address', {'finding_id': red['finding_id'], 'lease_id': self.lease})
        self.s.ok('phase.complete', {'phase': 'IMP', 'revision_id': self.rev, 'lease_id': self.lease})
        old_resolution = self.s.send('finding.resolve', {'finding_id': red['finding_id'], 'lease_id': self.lease, 'result_id': review['result_id']})
        self.assertEqual('RETEST_REQUIRED', old_resolution['errors'][0]['code'])
        green = self.s.ok('check.run', {'revision_id': self.rev, 'check_id': self.dsn['test'], 'lease_id': self.lease})
        self.assertEqual(('pass', 0), (green['outcome'], green['exit_code']))
        self.s.ok('finding.resolve', {'finding_id': red['finding_id'], 'lease_id': self.lease, 'result_id': green['result_id']})
        self.s.ok('check.record_review', {'revision_id': self.rev, 'check_id': self.dsn['review'], 'lease_id': self.lease,
                  'status': 'pass', 'observations': 'Current bytes include exact empty/nonempty implementation and assertions.'})
        final = self.s.ok('phase.complete', {'phase': 'VFY', 'revision_id': self.rev, 'lease_id': self.lease})
        self.assertTrue(final['converged'])
        self.assertEqual('RLS', final['next_actions'][0]['phase'])
        with Store(self.root).read() as con:
            rows = con.execute('SELECT status FROM check_results WHERE check_id=? ORDER BY observed_at', (self.dsn['test'],)).fetchall()
            self.assertEqual(['fail', 'pass'], [r[0] for r in rows])
            self.assertEqual([], con.execute('PRAGMA foreign_key_check').fetchall())

    def test_resume_rotates_lease_and_keeps_interrupted_attempt(self):
        step = self.start()
        resumed = self.s.ok('run.resume', {'reason': 'Synthetic interrupted authoring session'})
        self.assertNotEqual(self.lease, resumed['lease_id'])
        rejected = self.s.send('task.finish', {'revision_id': self.rev, 'task_id': self.task, 'step_id': step,
                          'lease_id': self.lease, 'summary': 'Stale executor'})
        self.assertEqual('LEASE_STALE', rejected['errors'][0]['code'])
        with Store(self.root).read() as con:
            self.assertEqual('interrupted', con.execute('SELECT status FROM steps WHERE step_id=?', (step,)).fetchone()[0])

    def replan(self, operations):
        self.s.ok('change.revise', {'phase': 'PLN', 'reason': 'Extend the isolated regression fixture'})
        ids = self.s.submit('PLN', operations)['ids']
        self.rev = self.s.complete('PLN')['revision_id']
        return ids

    def check(self, **extra):
        return self.s.send('check.run', {'revision_id': self.rev, 'check_id': self.dsn['test'], 'lease_id': self.lease}, **extra)

    def evaluation(self):
        return self.s.ok('check.evaluate', {'revision_id': self.rev})

    def test_workspace_lease_prevents_a_second_run(self):
        original = self.s.bindings.copy()
        second = Session(self.root)
        second.bindings = {'change_id': self.s.bindings['change_id']}
        started = second.send('run.start', {'actor_id': 'current-agent'})
        self.assertTrue(started['ok'], started)
        denied = self.s.send('run.acquire', run_id=started['run_id'])
        self.assertEqual('WORKSPACE_BUSY', denied['errors'][0]['code'])
        self.assertEqual(self.lease, self.s.ok('run.acquire')['lease_id'])
        self.assertEqual(original, self.s.bindings)

    def test_format_budget_preserves_original_field_errors_and_draft(self):
        draft = self.s.ok('change.revise', {'phase': 'PLN', 'reason': 'Synthetic format failures'})
        for attempt in range(3):
            result = self.s.send('phase.submit', {'phase': 'PLN', 'revision_id': draft['revision_id'],
                                 'operations': [{'op': 'update_task', 'id': self.task, 'unknown': True}]}, expected_generation=0)
            self.assertEqual('UNKNOWN_FIELD', result['errors'][0]['code'])
        self.assertEqual('blocked', result['status'])
        self.assertEqual('FORMAT_BUDGET', result['errors'][1]['code'])
        self.assertEqual(0, self.s.ok('phase.prepare')['generation'])
        self.s.ok('run.configure', {'reason': 'Explicit extra format attempt', 'max_format_attempts': 4})
        self.s.submit('PLN', [{'op': 'update_task', 'id': self.task, 'title': 'Valid resumed task'}])

    def test_requirement_semantics_invalidate_previous_check_result(self):
        step = self.start()
        self.write(step, True)
        self.assertEqual('pass', self.check()['data']['outcome'])
        self.finish(step)
        self.s.ok('change.revise', {'phase': 'REQ', 'reason': 'Explicit synthetic requirement extension'})
        self.s.submit('REQ', [{'op': 'update_requirement', 'id': self.req['req'], 'statement': 'Count values including duplicates'}])
        self.s.complete('REQ')
        self.s.complete('DSN')
        self.rev = self.s.complete('PLN')['revision_id']
        self.assertTrue(any(r['check_id'] == self.dsn['test'] for r in self.evaluation()['missing_checks']))

    def test_completed_preparation_does_not_satisfy_failed_environment_probe(self):
        ids = self.replan([
            {'op': 'create_task', 'client_key': 'prepare', 'target_phase': 'IMP', 'kind': 'prepare',
             'title': 'Probe environment', 'description': 'Observe prerequisite', 'completion_text': 'Probe attempted',
             'scope_paths': [{'resource': 'main', 'path': '.', 'access': 'read'}]},
            {'op': 'create_check', 'client_key': 'probe', 'task': {'client_key': 'prepare'}, 'purpose': 'precondition',
             'method': 'test', 'executor': 'command', 'description': 'Synthetic unavailable environment',
             'expected_result': 'Environment ready', 'argv': [sys.executable, '-c', 'assert False, "unavailable"'], 'required': False},
            {'op': 'create_precondition', 'client_key': 'gate', 'consumer_task': {'id': self.task},
             'producer_task': {'client_key': 'prepare'}, 'check': {'client_key': 'probe'}, 'enforce_at': 'start', 'reason': 'Actual prerequisite'}])
        step = self.s.ok('task.start', {'revision_id': self.rev, 'task_id': ids['prepare'], 'lease_id': self.lease})['step_id']
        self.s.ok('check.run', {'revision_id': self.rev, 'check_id': ids['probe'], 'lease_id': self.lease})
        self.s.ok('task.finish', {'revision_id': self.rev, 'task_id': ids['prepare'], 'lease_id': self.lease,
                                'step_id': step, 'summary': 'Probe attempted, environment unavailable'})
        result = self.s.send('task.start', {'revision_id': self.rev, 'task_id': self.task, 'lease_id': self.lease})
        self.assertEqual('TASK_BLOCKED', result['errors'][0]['code'])
        self.assertEqual('fail', result['errors'][0]['details'][0]['observed_status'])

    def test_unknown_write_reconciles_intent_without_duplicate_execution(self):
        from packages.sdlc import engine
        step = self.start()
        original = engine.apply_write
        def interrupted(*args):
            original(*args)
            raise OSError('Synthetic crash after product write')
        with patch.object(engine, 'apply_write', side_effect=interrupted):
            response = self.s.send('task.write', {'revision_id': self.rev, 'task_id': self.task, 'step_id': step,
                'lease_id': self.lease, 'files': [{'path': 'empty.py', 'content': ''}]}, operation_id='uncertain-write')
        self.assertEqual('unknown', response['status'])
        blocked = self.s.send('task.finish', {'revision_id': self.rev, 'task_id': self.task, 'step_id': step,
                                            'lease_id': self.lease, 'summary': 'Not reconciled'})
        self.assertEqual('UNRESOLVED_EFFECT', blocked['errors'][0]['code'])
        work = self.root/'.sdlc/runs'/self.s.bindings['run_id']/'uncertain-write/work'
        original_intent = (work/'intent.json').read_bytes()
        (work/'intent.json').write_text('{"kind":"fake"}')
        denied = self.s.send('operation.reconcile', {'operation_id': 'uncertain-write'})
        self.assertEqual('EFFECT_INTEGRITY', denied['errors'][0]['code'])
        (work/'intent.json').write_bytes(original_intent)
        reconciled = self.s.ok('operation.reconcile', {'operation_id': 'uncertain-write'})
        self.assertTrue(reconciled['original_receipt']['ok'])
        self.assertEqual('', (self.root/'empty.py').read_text())
        self.finish(step)

    def test_saved_collector_receipt_recovers_once_and_blocks_old_pass(self):
        from packages.sdlc import engine, execution
        step = self.start()
        self.write(step, True)
        self.assertEqual('pass', self.check()['data']['outcome'])
        with patch.object(engine, 'finish_check', side_effect=OSError('Synthetic failure before business receipt')):
            pending = self.check(operation_id='uncertain-check')
        self.assertEqual('unknown', pending['status'])
        self.assertFalse(self.evaluation()['converged'])
        self.assertIn('uncertain-check', self.evaluation()['unknown_operations'])
        with patch.object(execution, 'run_command', side_effect=AssertionError('Do not repeat the tool')):
            recovered = self.s.ok('operation.reconcile', {'operation_id': 'uncertain-check'})
        self.assertEqual('pass', recovered['original_receipt']['data']['outcome'])
        with Store(self.root).read() as con:
            self.assertEqual(2, con.execute('SELECT count(*) FROM check_results WHERE check_id=?', (self.dsn['test'],)).fetchone()[0])

    def test_command_input_scope_is_distinct_from_write_scope(self):
        self.replan([{'op': 'update_task', 'id': self.task,
                      'scope_paths': [{'resource': 'main', 'path': 'tests', 'access': 'write'}]}])
        (self.root/'product.py').write_text('VALUE=1')
        (self.root/'test_product.py').write_text('from product import VALUE; assert VALUE==1')
        self.start()
        self.assertEqual('pass', self.check()['data']['outcome'])
        (self.root/'product.py').write_text('VALUE=0')
        self.assertTrue(any(row['check_id'] == self.dsn['test'] for row in self.evaluation()['missing_checks']))

    def test_explicit_input_scope_reuses_only_unaffected_bytes(self):
        self.replan([{'op': 'update_check', 'id': self.dsn['test'], 'input_paths': [
            {'resource': 'main', 'path': name, 'access': 'read'} for name in ['product.py', 'test_product.py']]}])
        step = self.start()
        self.write(step, True)
        self.assertEqual('pass', self.check()['data']['outcome'])
        (self.root/'unrelated.md').write_text('Independent documentation')
        self.assertFalse(any(r['check_id'] == self.dsn['test'] for r in self.evaluation()['missing_checks']))
        (self.root/'requirements.lock').write_text('synthetic-dependency==2')
        self.assertTrue(any(r['check_id'] == self.dsn['test'] for r in self.evaluation()['missing_checks']))

    def test_expired_result_is_not_applicable(self):
        self.replan([{'op': 'update_check', 'id': self.dsn['test'], 'max_age_seconds': 0}])
        step = self.start()
        self.write(step, True)
        self.assertEqual('pass', self.check()['data']['outcome'])
        self.assertTrue(any(r['check_id'] == self.dsn['test'] for r in self.evaluation()['missing_checks']))

    def test_explicit_reuse_preserves_original_observation_and_expiry(self):
        self.replan([{'op': 'update_check', 'id': self.dsn['test'], 'max_age_seconds': 3600}])
        step = self.start()
        self.write(step, True)
        original = self.check()['data']['result_id']
        self.finish(step)
        self.s.ok('change.revise', {'phase': 'PLN', 'reason': 'Identical content in a child snapshot'})
        self.rev = self.s.complete('PLN')['revision_id']
        result = self.s.ok('check.reuse', {'revision_id': self.rev, 'check_id': self.dsn['test'], 'lease_id': self.lease})
        self.assertEqual(original, result['reused_from_id'])
        with Store(self.root).read() as con:
            before = con.execute('SELECT * FROM check_results WHERE result_id=?', (original,)).fetchone()
            after = con.execute('SELECT * FROM check_results WHERE result_id=?', (result['result_id'],)).fetchone()
            self.assertEqual((before['observed_at'], before['expires_at']), (after['observed_at'], after['expires_at']))
            self.assertEqual(('reused', self.rev), (after['source_kind'], after['revision_id']))

    def test_findings_keep_distinct_identity_and_escalate_severity(self):
        def review(findings):
            return self.s.ok('check.record_review', {'revision_id': self.rev, 'check_id': self.dsn['review'],
                'lease_id': self.lease, 'status': 'fail', 'observations': 'Synthetic gap identities', 'findings': findings})['finding_ids']
        first = {'description': 'Wording', 'kind': 'missing', 'severity': 'advisory', 'return_phase': 'IMP', 'issue_key': 'wording'}
        second = {'description': 'Missing authorization', 'kind': 'missing', 'severity': 'blocking', 'return_phase': 'IMP', 'issue_key': 'auth'}
        ids = review([first, second])
        self.assertEqual(2, len(set(ids)))
        self.assertEqual([ids[0]], review([{**first, 'severity': 'blocking'}]))
        findings = self.s.ok('finding.list')['findings']
        self.assertEqual(['blocking', 'blocking'], sorted(f['severity'] for f in findings))

    def test_repair_budget_stops_until_explicitly_increased(self):
        self.s.ok('run.configure', {'reason': 'One-round regression budget', 'max_repair_rounds': 1})
        step = self.start()
        self.write(step, False)
        self.finish(step)
        self.s.ok('phase.complete', {'phase': 'IMP', 'revision_id': self.rev, 'lease_id': self.lease})
        self.check()
        self.s.ok('check.record_review', {'revision_id': self.rev, 'check_id': self.dsn['review'], 'lease_id': self.lease,
                                        'status': 'pass', 'observations': 'Fixture inspection distinct from failed assertion'})
        stopped = self.s.send('phase.complete', {'phase': 'VFY', 'revision_id': self.rev, 'lease_id': self.lease})
        self.assertEqual('blocked', stopped['status'])
        self.assertEqual('REPAIR_BUDGET', self.s.send('run.acquire')['errors'][0]['code'])
        self.s.ok('run.configure', {'reason': 'Explicit additional repair allowance', 'max_repair_rounds': 2})
        self.assertEqual(self.lease, self.s.ok('run.acquire')['lease_id'])

    def test_repeated_gap_stops_after_two_rounds_without_progress(self):
        step = self.start()
        self.write(step, False)
        self.assertEqual('fail', self.check()['data']['outcome'])
        self.finish(step)
        self.s.ok('check.record_review', {'revision_id': self.rev, 'check_id': self.dsn['review'], 'lease_id': self.lease,
                                        'status': 'pass', 'observations': 'Stable synthetic review'})
        for expected in ['needs_work', 'needs_work', 'blocked']:
            self.s.ok('phase.complete', {'phase': 'IMP', 'revision_id': self.rev, 'lease_id': self.lease})
            result = self.s.send('phase.complete', {'phase': 'VFY', 'revision_id': self.rev, 'lease_id': self.lease})
            self.assertEqual(expected, result['status'])
        state = self.s.ok('run.get')['run']
        self.assertEqual((3, 2), (state['repair_round'], state['no_progress_rounds']))

    def test_scope_and_forged_command_review_rejected(self):
        step = self.start()
        denied = self.s.send('task.write', {'revision_id': self.rev, 'task_id': self.task, 'step_id': step, 'lease_id': self.lease,
                    'files': [{'path': '../outside.py', 'content': 'bad'}]})
        self.assertFalse(denied['ok'])
        forged = self.s.send('check.record_review', {'revision_id': self.rev, 'check_id': self.dsn['test'], 'lease_id': self.lease,
                         'status': 'pass', 'observations': 'Model claims it passed'})
        self.assertEqual('CHECK_EXECUTOR', forged['errors'][0]['code'])


if __name__ == '__main__':
    unittest.main()
