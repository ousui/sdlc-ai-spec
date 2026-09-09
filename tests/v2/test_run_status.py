"""Current Run projection recovers on real progress, not unrelated success.

Fixture mutations use public Runtime Session requests. Check recovery interrupts
only finish_check after actual worker execution; no SQL or invented PASS is used.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_runtime import Session
import test_execution as execution_fixture
import test_delivery as delivery_fixture
from packages.sdlc import engine


def current(session):
    return session.ok('run.get')['run']


def diagnostic(run):
    return tuple(run[key] for key in ('status', 'error_code', 'error_message', 'current_phase'))


class RunStatusTests(unittest.TestCase):
    def assert_running(self, session):
        run = current(session)
        self.assertEqual(('running', None, None),
                         (run['status'], run['error_code'], run['error_message']))
        return run

    def test_corrected_content_mutations_restore_current_run_and_keep_old_receipt(self):
        for command in ('phase.submit', 'change.revise'):
            with self.subTest(command=command), tempfile.TemporaryDirectory(prefix='sdlc-run-status-') as temp:
                session = Session(Path(temp))
                session.initialize()
                created = session.new_change('corrected-content')
                payload = ({'phase': 'REQ', 'revision_id': created['revision_id'],
                            'operations': [{'op': 'create_source', 'kind': 'text',
                                            'original_text': 'Actual corrected fixture source'}]}
                           if command == 'phase.submit' else
                           {'phase': 'REQ', 'reason': 'Explicit revision retains the original fixture source'})
                failed = session.send(command, payload)
                self.assertEqual('GENERATION_REQUIRED', failed['errors'][0]['code'])
                before = current(session)
                self.assertEqual('failed', before['status'])
                session.ok('phase.prepare', {'phase': 'REQ'})
                session.ok('render')
                self.assertEqual(diagnostic(before), diagnostic(current(session)))
                generation = session.ok('phase.prepare', {'phase': 'REQ'})['generation']
                session.ok(command, payload, expected_generation=generation)
                self.assert_running(session)
                original = (Path(temp)/'.sdlc/runs'/session.bindings['run_id']/failed['operation_id']/'response.json')
                self.assertEqual(failed, json.loads(original.read_text()))
                session.ok('run.cancel', {'reason': 'Corrected input regression complete'})

    def test_unknown_stays_interrupted_until_actual_reconcile(self):
        fixture = execution_fixture.ExecutionFlowTests()
        try:
            fixture.setUp()
            s, scope = fixture.s, {'revision_id': fixture.rev, 'lease_id': fixture.lease}
            step = fixture.start()
            fixture.write(step, True)
            fixture.finish(step)
            s.ok('phase.complete', {**scope, 'phase': 'IMP'})
            self.assertEqual('pass', fixture.check()['data']['outcome'])
            with patch.object(engine, 'finish_check', side_effect=OSError(
                    'Isolated interruption after actual Check worker, before result save')):
                unknown = fixture.check(operation_id='run-status-unknown')
            self.assertEqual('unknown', unknown['status'])
            before = current(s)
            self.assertEqual('interrupted', before['status'])
            actual = json.loads((fixture.root/'.sdlc/runs'/s.bindings['run_id']/'run-status-unknown/work/result.json').read_text())
            self.assertEqual(('command', 'pass', 0), (actual['source_kind'], actual['status'], actual['exit_code']))
            s.ok('phase.prepare', {'phase': 'VFY'})
            s.ok('workspace.export', {'change_id': s.bindings['change_id']})
            self.assertEqual(diagnostic(before), diagnostic(current(s)))
            recovered = s.ok('operation.reconcile', {'operation_id': 'run-status-unknown'})
            self.assertEqual('pass', recovered['original_receipt']['data']['outcome'])
            self.assert_running(s)
            failed = s.send('phase.complete', {'phase': 'VFY', 'revision_id': fixture.rev})
            self.assertEqual('LEASE_STALE', failed['errors'][0]['code'])
            before = current(s)
            historic = s.ok('operation.reconcile', {'operation_id': 'run-status-unknown'})
            self.assertTrue(historic['already_reconciled'])
            self.assertEqual(diagnostic(before), diagnostic(current(s)))
            s.ok('run.resume', {'reason': 'Explicitly resume after inspecting the missing lease'})
            self.assert_running(s)
            s.ok('run.cancel', {'reason': 'Actual unknown recovery regression complete'})
        finally:
            fixture.tearDown()

    def test_pending_input_survives_successful_render_export_and_reads(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-run-pending-') as temp:
            s = Session(Path(temp))
            s.initialize()
            created = s.new_change('pending-input')
            asked = s.send('run.request_input', {'revision_id': created['revision_id'],
                'question': 'Which count boundary is intended?', 'conflict': 'Synthetic contradictory fixture requirement'})
            self.assertEqual('needs_input', asked['status'])
            before = current(s)
            self.assertEqual(('blocked', 'CLARIFICATION_REQUIRED'), (before['status'], before['error_code']))
            s.ok('phase.prepare', {'phase': 'REQ'})
            s.ok('render')
            s.ok('workspace.export', {'change_id': s.bindings['change_id']})
            self.assertEqual(diagnostic(before), diagnostic(current(s)))
            self.assertEqual(1, len(s.ok('run.get')['pending_inputs']))
            refused = s.send('run.configure', {'reason': 'Unrelated format setting', 'max_format_attempts': 4})
            self.assertEqual('needs_input', refused['status'])
            s.ok('run.answer_input', {'question_step_id': asked['data']['question_step_id'],
                'answer': 'Preserve the declared count behavior.', 'basis_text': 'Synthetic fixture response; no real human identity claimed.'})
            self.assert_running(s)
            s.ok('run.cancel', {'reason': 'Pending-input regression complete'})

    def test_exhausted_repair_budget_survives_unrelated_successful_management(self):
        fixture = execution_fixture.ExecutionFlowTests()
        try:
            fixture.setUp()
            s, scope = fixture.s, {'revision_id': fixture.rev, 'lease_id': fixture.lease}
            s.ok('run.configure', {'reason': 'One real failing round for this regression', 'max_repair_rounds': 1})
            step = fixture.start()
            fixture.write(step, False)
            fixture.finish(step)
            s.ok('phase.complete', {**scope, 'phase': 'IMP'})
            self.assertEqual('fail', fixture.check()['data']['outcome'])
            s.ok('check.record_review', {**scope, 'check_id': fixture.dsn['review'], 'status': 'pass',
                'observations': 'Deterministic budget fixture review; the actual failed command remains authoritative for behavior.'})
            budget = s.send('phase.complete', {**scope, 'phase': 'VFY'})
            self.assertEqual('blocked', budget['status'])
            self.assertEqual('REPAIR_BUDGET', budget['data']['error_code'])
            before = current(s)
            self.assertEqual(('blocked', 1, 1), (before['status'], before['repair_round'], before['max_repair_rounds']))
            s.ok('render')
            s.ok('run.configure', {'reason': 'Unrelated format limit', 'max_format_attempts': 4})
            s.ok('workspace.export', {'change_id': s.bindings['change_id']})
            after = current(s)
            self.assertEqual(diagnostic(before), diagnostic(after))
            self.assertEqual((1, 1), (after['repair_round'], after['max_repair_rounds']))
            blocked = s.send('task.start', {**scope, 'task_id': fixture.task})
            self.assertEqual('REPAIR_BUDGET', blocked['errors'][0]['code'])
            s.ok('run.cancel', {'reason': 'Exhausted-budget regression complete'})
        finally:
            fixture.tearDown()

    def test_answering_input_does_not_clear_an_exhausted_format_budget(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-run-format-') as temp:
            s = Session(Path(temp))
            s.initialize()
            created = s.new_change('format-and-input')
            for unused in range(3):
                failed = s.send('phase.submit', {'phase': 'REQ', 'revision_id': created['revision_id'],
                    'operations': [{'op': 'create_source', 'kind': 'text', 'original_text': 'Fixture source'}]})
                self.assertFalse(failed['ok'])
            self.assertEqual(3, current(s)['format_attempts'])
            asked = s.send('run.request_input', {'revision_id': created['revision_id'],
                'question': 'Which count boundary is intended?', 'conflict': 'Synthetic input ambiguity'})
            self.assertEqual('needs_input', asked['status'])
            s.ok('run.answer_input', {'question_step_id': asked['data']['question_step_id'],
                'answer': 'Preserve the declared boundary.', 'basis_text': 'Explicit synthetic fixture answer'})
            run = current(s)
            self.assertEqual(('blocked', 'FORMAT_BUDGET', 3),
                             (run['status'], run['error_code'], run['format_attempts']))
            self.assertEqual([], s.ok('run.get')['pending_inputs'])
            refused = s.send('phase.submit', {'phase': 'REQ', 'revision_id': created['revision_id'],
                'operations': []}, expected_generation=0)
            self.assertEqual('FORMAT_BUDGET', refused['errors'][0]['code'])
            s.ok('run.cancel', {'reason': 'Combined input and format-budget regression complete'})

    def test_successful_rls_closure_clears_current_error_and_stays_closed(self):
        fixture = delivery_fixture.DeliveryTests()
        try:
            fixture.setUp()
            prepared = fixture.prepare()
            self.assertTrue(fixture.execute(prepared)['ok'])
            failed = fixture.s.send('phase.complete', {'phase': 'RLS', 'revision_id': fixture.rev})
            self.assertEqual('LEASE_STALE', failed['errors'][0]['code'])
            self.assertTrue(fixture.complete()['ok'])
            closed = current(fixture.s)
            self.assertEqual(('completed', None, None),
                             (closed['status'], closed['error_code'], closed['error_message']))
            manager = Session(fixture.root)
            manager.ok('workspace.export', {'change_id': fixture.s.bindings['change_id']})
            self.assertEqual(diagnostic(closed), diagnostic(current(fixture.s)))
        finally:
            fixture.tearDown()

    def test_cancelled_run_is_not_reopened_by_read_or_export(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-run-cancelled-') as temp:
            s = Session(Path(temp))
            s.initialize()
            s.new_change('cancelled')
            s.ok('run.cancel', {'reason': 'Explicit fixture cancellation'})
            before = current(s)
            self.assertEqual('cancelled', before['status'])
            manager = Session(Path(temp))
            manager.ok('workspace.export', {'change_id': s.bindings['change_id']})
            self.assertEqual(diagnostic(before), diagnostic(current(s)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
