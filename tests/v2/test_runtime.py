"""Public Runtime/CLI behavior, separate from actual Agent/project acceptance."""
import copy
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from packages.sdlc.common import uid
from packages.sdlc.runtime import Runtime
from packages.sdlc.storage import Store

CLI = Path(__file__).resolve().parents[2]/'scripts/sdlc.py'


class Session:
    def __init__(self, root, cli=False):
        self.root, self.cli = Path(root), cli
        self.bindings = {}

    def send(self, command, payload=None, **extra):
        request = {'api_version': '2', 'command': command, 'payload': payload or {}, **self.bindings, **extra}
        if self.cli:
            result = subprocess.run([sys.executable, '-B', str(CLI), '--root', str(self.root)],
                                    input=json.dumps(request), capture_output=True, text=True)
            response = json.loads(result.stdout)
            expected = 0 if response['ok'] else (2 if response['status'] in {'invalid_input', 'conflict'} else 3 if response['status'] in {'blocked', 'needs_input', 'needs_work', 'unknown'} else 4)
            assert result.returncode == expected, result.stderr
            return response
        return Runtime(self.root).invoke(request)

    def ok(self, command, payload=None, **extra):
        response = self.send(command, payload, **extra)
        assert response['ok'], response
        return response['data']

    def initialize(self):
        self.ok('workspace.init', {'name': 'example'})
        self.context = self.ok('context.commit', {'summary': 'Small existing program',
            'entries': [{'kind': 'resource', 'name': 'main', 'content': 'Current project', 'settings': {'resource': 'main'}}]})['context_id']

    def new_change(self, slug='example'):
        response = self.send('change.create', {'slug': slug, 'context_id': self.context,
            'title': 'Count values', 'summary': 'Preserve a clear original requirement',
            'goal': 'Count a collection', 'in_scope': 'Local code and tests', 'out_of_scope': 'Remote writes',
            'delivery_mode': 'local', 'delivery_target': '.sdlc/exports/'+slug,
            'original_text': 'Return the number of input values, including empty input.',
            'authorizations': [{'action': action, 'target': 'main' if action != 'package_local' else '.sdlc/exports/'+slug,
                'issued_by': 'user', 'basis_text': 'Explicit local fixture authorization'}
                for action in ['edit_local', 'run_check', 'package_local']]})
        assert response['ok'], response
        data = response['data']
        self.bindings.update(change_id=data['change_id'], run_id=response['run_id'])
        self.source = data['source_id']
        return data

    def submit(self, phase, operations):
        data = self.ok('phase.prepare', {'phase': phase})
        return self.ok('phase.submit', {'phase': phase, 'revision_id': data['content']['revision']['revision_id'],
                       'operations': operations}, expected_generation=data['generation'])

    def complete(self, phase):
        data = self.ok('phase.prepare', {'phase': phase})
        return self.ok('phase.complete', {'phase': phase, 'revision_id': data['content']['revision']['revision_id']},
                       expected_generation=data['generation'])

    def req(self):
        ids = self.submit('REQ', [
            {'op': 'create_requirement', 'client_key': 'req', 'kind': 'behavior', 'statement': 'Count values', 'sources': [{'id': self.source}]},
            {'op': 'create_criterion', 'client_key': 'ac', 'condition_text': 'Empty and nonempty sequences', 'expected_result': 'Accurate length', 'requirements': [{'client_key': 'req'}]}])['ids']
        self.complete('REQ')
        return ids

    def dsn(self, ids):
        values = self.submit('DSN', [
            {'op': 'create_design', 'client_key': 'design', 'domain': 'components', 'title': 'Collection size',
             'decision': 'Use standard length', 'rationale': 'No custom algorithm necessary', 'alternatives': 'Iteration adds complexity',
             'detail': 'Preserve iterable boundary', 'requirements': [{'id': ids['req']}]},
            {'op': 'create_check', 'client_key': 'test', 'purpose': 'acceptance', 'method': 'test', 'executor': 'command',
             'description': 'Test length', 'expected_result': 'Assertions pass', 'argv': [sys.executable, '-c', 'assert len([])==0'],
             'required': True, 'criteria': [{'id': ids['ac']}]},
            {'op': 'create_check', 'client_key': 'review', 'purpose': 'convergence', 'method': 'inspection', 'executor': 'agent',
             'description': 'Review full scope for gaps', 'expected_result': 'No unresolved gaps', 'required': True}])['ids']
        self.complete('DSN')
        return values


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.session = Session(self.root)
        self.session.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_public_cli_req_dsn_pln_and_render(self):
        s = Session(self.root, cli=True)
        s.context = self.session.context
        s.new_change()
        req = s.req()
        dsn = s.dsn(req)
        s.submit('PLN', [{'op': 'create_task', 'client_key': 'implement', 'target_phase': 'IMP', 'kind': 'implement',
            'title': 'Implement length', 'description': 'Edit program and tests', 'completion_text': 'Source and tests saved',
            'scope_paths': [{'resource': 'main', 'path': '.', 'access': 'write'}], 'designs': [{'id': dsn['design']}],
            'criteria': [{'id': req['ac']}]},
            {'op': 'update_check', 'id': dsn['test'], 'task': {'client_key': 'implement'}}])
        result = s.complete('PLN')
        self.assertEqual('IMP', result['next_actions'][0]['phase'])
        page = s.ok('render')['path']
        self.assertIn('Count values', Path(page).read_text())
        with Store(self.root).read() as con:
            self.assertEqual([], con.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(['REQ', 'DSN', 'PLN'], [r[0] for r in con.execute("SELECT phase FROM steps WHERE run_id=? ORDER BY started_at", (s.bindings['run_id'],))])
            self.assertEqual(3, con.execute("SELECT count(*) FROM revisions WHERE state='committed'").fetchone()[0])

    def test_idempotent_receipt_and_conflicting_key(self):
        key = uid()
        one = self.session.send('context.commit', {'summary': 'First', 'entries': []}, operation_id=key)
        same = self.session.send('context.commit', {'summary': 'First', 'entries': []}, operation_id=key)
        self.assertEqual(one, same)
        different = self.session.send('context.commit', {'summary': 'Second', 'entries': []}, operation_id=key)
        self.assertEqual('OPERATION_CONFLICT', different['errors'][0]['code'])
        with Store(self.root).read() as con:
            self.assertEqual(2, con.execute('SELECT count(*) FROM contexts').fetchone()[0])

    def test_stale_generation_cannot_overwrite(self):
        data = self.session.new_change()
        p = {'phase': 'REQ', 'revision_id': data['revision_id'], 'operations': []}
        self.session.ok('phase.submit', p, expected_generation=0)
        result = self.session.send('phase.submit', p, expected_generation=0)
        self.assertEqual('GENERATION_CONFLICT', result['errors'][0]['code'])
        current = self.session.ok('phase.prepare')
        self.assertEqual(1, current['generation'])

    def test_failed_batch_has_run_and_no_content_side_effect(self):
        data = self.session.new_change()
        result = self.session.send('phase.submit', {'phase': 'REQ', 'revision_id': data['revision_id'], 'operations': [
            {'op': 'create_requirement', 'kind': 'behavior', 'statement': 'Valid'},
            {'op': 'create_criterion', 'condition_text': 'Fail', 'expected_result': 'Fail', 'requirements': [{'id': uid()}]}]}, expected_generation=0)
        self.assertFalse(result['ok'])
        current = self.session.ok('phase.prepare')
        self.assertEqual([], current['content']['requirements'])
        self.assertEqual(0, current['generation'])
        run = self.session.ok('run.get')
        self.assertEqual('failed', run['run']['status'])
        self.assertTrue((self.root/'.sdlc/runs'/result['run_id']/result['operation_id']/'request.json').is_file())

    def test_invalid_scope_has_unbound_early_diagnostic_run(self):
        result = self.session.send('phase.complete', {'phase': 'IMP', 'revision_id': uid()}, change_id=uid(), expected_generation=0)
        self.assertEqual('CHANGE_SCOPE', result['errors'][0]['code'])
        with Store(self.root).read() as con:
            row = con.execute('SELECT * FROM runs WHERE run_id=?', (result['run_id'],)).fetchone()
            self.assertIsNone(row['change_id'])
            self.assertEqual('CHANGE_SCOPE', row['error_code'])

    def test_committed_snapshot_and_attachment_links_unchanged(self):
        s = self.session
        data = s.new_change()
        (self.root/'design.txt').write_text('Original source attachment')
        asset = s.ok('asset.add', {'path': 'design.txt', 'owner_type': 'source', 'owner_id': data['source_id'], 'purpose': 'original input'}, expected_generation=0)
        s.req()
        with Store(self.root).read() as con:
            link = con.execute('SELECT * FROM assets WHERE asset_id=?', (asset['asset_id'],)).fetchone()
            h = link['sha256']
            self.assertEqual('Original source attachment', (self.root/f'.sdlc/assets/{h[:2]}/{h[2:4]}/{h}').read_text())
        with Store(self.root).transaction() as con:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute('UPDATE asset_links SET original_name=? WHERE revision_id=?', ('bad', data['revision_id']))

    def test_cross_project_context_is_rejected(self):
        s = self.session
        other = s.ok('project.create', {'name': 'Other'})
        s.bindings.update(other)
        response = s.send('change.create', {'slug': 'bad', 'context_id': s.context, 'title': 'bad', 'summary': 'bad',
            'goal': 'bad', 'in_scope': 'bad', 'out_of_scope': 'remote', 'delivery_mode': 'local', 'delivery_target': 'out',
            'original_text': 'bad', 'authorizations': []})
        self.assertEqual('CONTEXT_SCOPE', response['errors'][0]['code'])
        with Store(self.root).read() as con:
            self.assertEqual(0, con.execute('SELECT count(*) FROM changes').fetchone()[0])

    def test_high_risk_authority_not_inherited_from_auto(self):
        s = self.session
        response = s.send('change.create', {'slug': 'bad', 'context_id': s.context, 'title': 'bad', 'summary': 'bad',
            'goal': 'bad', 'in_scope': 'bad', 'out_of_scope': 'remote', 'delivery_mode': 'deployment', 'delivery_target': 'production',
            'original_text': 'local only', 'authorizations': [{'action': 'deploy', 'target': 'production', 'issued_by': 'agent', 'basis_text': 'auto'}]})
        self.assertEqual('AUTHORIZATION_SCOPE', response['errors'][0]['code'])

    def test_valid_reads_do_not_mutate_database_or_files(self):
        s = self.session
        s.new_change()
        def snapshot():
            return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        for command in ('workspace.inspect', 'status', 'change.get', 'phase.prepare', 'run.get'):
            s.ok(command)
        self.assertEqual(before, snapshot())

    def test_corrupt_database_preserved_and_bootstrap_diagnostic(self):
        path = self.root/'.sdlc/store.sqlite3'
        path.write_bytes(b'not a sqlite file')
        result = self.session.send('workspace.inspect')
        self.assertFalse(result['ok'])
        self.assertEqual(b'not a sqlite file', path.read_bytes())
        self.assertTrue((Path(result['diagnostic_path'])/'response.json').exists())

    def test_unknown_nested_context_field_is_not_sql_error(self):
        result = self.session.send('context.commit', {'summary': 'Bad', 'entries': [
            {'kind': 'command', 'name': 'test', 'content': 'Local test', 'settings': {'argv': ['python3'], 'resource': 'main', 'password': 'synthetic-test-value'}}]})
        self.assertEqual('/payload/entries/0/settings/password', result['errors'][0]['path'])
        raw = (self.root/'.sdlc/runs'/result['run_id']/result['operation_id']/'request.json').read_text()
        self.assertNotIn('synthetic-test-value', raw)

    def test_abandoned_draft_preserved_when_returning_to_req(self):
        s = self.session
        first = s.new_change()
        s.req()
        data = s.ok('phase.prepare')
        draft = data['content']['revision']['revision_id']
        with Store(self.root).read() as con:
            self.assertEqual(first['revision_id'], con.execute('SELECT active_revision_id FROM changes').fetchone()[0])
        revised = s.ok('change.revise', {'phase': 'REQ', 'reason': 'Correct original scope interpretation'}, expected_generation=data['generation'])
        with Store(self.root).read() as con:
            self.assertEqual('abandoned', con.execute('SELECT state FROM revisions WHERE revision_id=?', (draft,)).fetchone()[0])
            self.assertEqual(first['revision_id'], con.execute('SELECT active_revision_id FROM changes').fetchone()[0])
            self.assertEqual(draft, con.execute('SELECT parent_id FROM revisions WHERE revision_id=?', (revised['revision_id'],)).fetchone()[0])
        s.complete('REQ')

    def test_identity_mapping_survives_receipt_redaction(self):
        s = self.session
        data = s.new_change()
        payload = {'phase': 'REQ', 'revision_id': data['revision_id'], 'operations': [
            {'op': 'create_requirement', 'client_key': 'token_cache', 'kind': 'behavior', 'statement': 'Cache opaque test objects'}]}
        extra = {'operation_id': uid(), 'expected_generation': 0}
        first = s.send('phase.submit', payload, **extra)
        second = s.send('phase.submit', payload, **extra)
        self.assertTrue(first['ok'], first)
        self.assertEqual(first, second)
        self.assertNotEqual('[REDACTED]', second['data']['ids']['token_cache'])

    def test_trace_failure_marks_run_failed_and_saves_receipt(self):
        from unittest.mock import patch
        with patch.object(Runtime, 'write_trace', side_effect=OSError('synthetic trace failure')):
            result = self.session.send('context.commit', {'summary': 'Trace failure', 'entries': []})
        self.assertFalse(result['ok'])
        with Store(self.root).read() as con:
            self.assertEqual('failed', con.execute('SELECT status FROM runs WHERE run_id=?', (result['run_id'],)).fetchone()[0])
            self.assertEqual('rejected', con.execute('SELECT status FROM operations WHERE operation_id=?', (result['operation_id'],)).fetchone()[0])

    def test_invalid_config_array_and_deep_json_have_protocol_errors(self):
        path = self.root/'.sdlc/config.json'
        path.write_text('[]')
        response = self.session.send('status')
        self.assertEqual('STORE_CONFIG', response['errors'][0]['code'])
        raw = '['*1500 + '0' + ']'*1500
        result = subprocess.run([sys.executable, '-B', str(CLI), '--root', str(self.root)], input=raw, capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_read_binding_and_future_phase_rejected(self):
        s = self.session
        s.new_change()
        self.assertEqual('RUN_SCOPE', s.send('run.get', change_id=uid())['errors'][0]['code'])
        self.assertEqual('PHASE_ORDER', s.send('phase.prepare', {'phase': 'RLS'})['errors'][0]['code'])

    def test_context_refresh_preserves_entry_identity(self):
        s = self.session
        refreshed = s.ok('context.commit', {'summary': 'Refreshed', 'parent_id': s.context,
            'entries': [{'kind': 'resource', 'name': 'main', 'content': 'Same logical resource', 'settings': {'resource': 'main'}}]})
        with Store(self.root).read() as con:
            entries = [r[0] for r in con.execute('SELECT entry_id FROM context_entries WHERE context_id IN (?,?)', (s.context, refreshed['context_id']))]
            self.assertEqual(2, len(entries))
            self.assertEqual(entries[0], entries[1])

    def test_error_message_is_redacted_in_database_and_html(self):
        s = self.session
        data = s.new_change()
        synthetic = 'SYNTHETIC-P2-ERROR-DO-NOT-USE'
        result = s.send('phase.submit', {'phase': 'REQ', 'revision_id': data['revision_id'],
            'operations': [{'op': 'password='+synthetic}]}, expected_generation=0)
        self.assertFalse(result['ok'])
        with Store(self.root).read() as con:
            message = con.execute('SELECT error_message FROM runs WHERE run_id=?', (result['run_id'],)).fetchone()[0]
            self.assertNotIn(synthetic, message)
        page = self.root/'.sdlc/runs'/result['run_id']/'index.html'
        self.assertNotIn(synthetic, page.read_text())

    def test_nine_cross_design_criteria_cannot_disappear(self):
        s = self.session
        s.new_change()
        operations = [{'op': 'create_requirement', 'client_key': 'req', 'kind': 'behavior',
                       'statement': 'Nine obligations', 'sources': [{'id': s.source}]}]
        operations += [{'op': 'create_criterion', 'client_key': 'ac'+str(i), 'condition_text': 'Scenario '+str(i),
                        'expected_result': 'Expected '+str(i), 'requirements': [{'client_key': 'req'}]} for i in range(9)]
        ids = s.submit('REQ', operations)['ids']
        s.complete('REQ')
        operations = [{'op': 'create_design', 'client_key': 'd'+str(i), 'domain': 'components', 'title': 'Design '+str(i),
             'decision': 'Explicit disposition', 'rationale': 'Cover related obligations', 'alternatives': 'No change misses requirement',
             'detail': 'Implementation boundary '+str(i), 'requirements': [{'id': ids['req']}]} for i in range(3)]
        operations += [{'op': 'create_check', 'client_key': 'k'+str(i), 'purpose': 'acceptance', 'method': 'test',
            'executor': 'command', 'description': 'Case '+str(i), 'expected_result': 'Assertions pass',
            'argv': [sys.executable, '-c', 'assert True'], 'required': True, 'criteria': [{'id': ids['ac'+str(i)]}]} for i in range(8)]
        operations += [{'op': 'create_check', 'purpose': 'convergence', 'method': 'inspection', 'executor': 'agent',
                        'description': 'Review nine obligations', 'expected_result': 'No gaps', 'required': True}]
        s.submit('DSN', operations)
        data = s.ok('phase.prepare')
        denied = s.send('phase.complete', {'phase': 'DSN', 'revision_id': data['content']['revision']['revision_id']}, expected_generation=data['generation'])
        self.assertEqual('PHASE_INCOMPLETE', denied['errors'][0]['code'])
        missing = denied['errors'][0]['details']
        self.assertTrue(any(x.get('id') == ids['ac8'] for x in missing))
        s.submit('DSN', [{'op': 'create_check', 'purpose': 'acceptance', 'method': 'test', 'executor': 'command',
            'description': 'Ninth case', 'expected_result': 'Assertions pass', 'argv': [sys.executable, '-c', 'assert True'],
            'required': True, 'criteria': [{'id': ids['ac8']}]}])
        s.complete('DSN')
        current = s.ok('phase.prepare')
        self.assertEqual(9, len(current['content']['criteria']))
        self.assertEqual(9, len(current['content']['check_criteria']))
        designs = [r['design_id'] for r in current['content']['designs']]
        def planned_task(i):
            return {'op': 'create_task', 'target_phase': 'IMP', 'kind': 'implement',
                'title': 'Obligation '+str(i), 'description': 'Bounded disposition of this criterion',
                'completion_text': 'Implementation attempt recorded',
                'scope_paths': [{'resource': 'main', 'path': 'case'+str(i)+'.py', 'access': 'write'}],
                'criteria': [{'id': ids['ac'+str(i)]}], 'designs': [{'id': designs[i % 3]}]}
        s.submit('PLN', [planned_task(i) for i in range(8)])
        current = s.ok('phase.prepare')
        denied = s.send('phase.complete', {'phase': 'PLN', 'revision_id': current['content']['revision']['revision_id']}, expected_generation=current['generation'])
        self.assertEqual('PHASE_INCOMPLETE', denied['errors'][0]['code'])
        self.assertTrue(any(r.get('id') == ids['ac8'] for r in denied['errors'][0]['details']))
        s.submit('PLN', [planned_task(8)])
        s.complete('PLN')
        adopted = s.ok('change.get')['content']
        expected = {ids['ac'+str(i)] for i in range(9)}
        self.assertEqual(expected, {r['criterion_id'] for r in adopted['task_criteria']})
        self.assertEqual(expected, {r['criterion_id'] for r in adopted['check_criteria']})
        self.assertEqual(9, len(adopted['tasks']))


if __name__ == '__main__':
    unittest.main()
