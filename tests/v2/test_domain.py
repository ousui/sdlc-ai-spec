"""Approved contract counterexamples; fixtures use Store solely to isolate the domain."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from packages.sdlc.common import Fault, now, uid
from packages.sdlc.domain import batch, fields, task_fingerprint, validate_complete
from packages.sdlc.storage import Store, insert
from packages.sdlc.protocol import contract, operation_schema


class PublicScopeSchemaTests(unittest.TestCase):
    def test_resource_map_schema_requires_main_in_complete_replacement(self):
        commands = contract()['commands']
        for name in ('workspace.bind', 'workspace.rebind'):
            resources = commands[name]['payload']['properties']['resources']
            self.assertEqual(['main'], resources['required'])
            self.assertEqual({'const': '.'}, resources['properties']['main'])
            self.assertEqual({'type': 'string', 'minLength': 1}, resources['additionalProperties'])

    def test_check_read_dependencies_and_task_write_permissions_have_distinct_schema(self):
        operations = {r['properties']['op']['const']: r for r in operation_schema('PLN')['items']['oneOf']}
        for verb in ('create', 'update'):
            read_access = operations[verb+'_check']['properties']['input_paths']['items']['properties']['access']['enum']
            task_access = operations[verb+'_task']['properties']['scope_paths']['items']['properties']['access']['enum']
            self.assertEqual(['read'], read_access)
            self.assertEqual(['read', 'write'], task_access)


def ref(key):
    return {'client_key': key}


def task(key='prep', phase='IMP'):
    return {'op': 'create_task', 'client_key': key, 'target_phase': phase,
            'kind': 'prepare', 'title': key, 'description': 'Prepare isolated data',
            'completion_text': 'Preparation attempted',
            'scope_paths': [{'resource': 'main', 'path': 'tests/**', 'access': 'write'}]}


def check(key='probe', owner='prep'):
    return {'op': 'create_check', 'client_key': key, 'task': ref(owner) if owner else None,
            'purpose': 'precondition', 'method': 'test', 'executor': 'command',
            'description': 'Check isolation', 'expected_result': 'Probe assertions pass',
            'argv': ['python3', 'tests/probe.py'], 'required': True}


def condition(consumer='test', producer='prep', moment='execute'):
    return {'op': 'create_precondition', 'consumer_task': ref(consumer),
            'producer_task': ref(producer) if producer else None,
            'check': ref('probe'), 'enforce_at': moment, 'reason': 'Actual isolation required'}


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.config = self.store.initialize('domain')
        self.project = self.config['project_id']
        self.context, self.change, self.revision = uid(), uid(), uid()
        with self.store.transaction() as con:
            insert(con, 'contexts', {'context_id': self.context, 'project_id': self.project,
                   'summary': 'test', 'state': 'committed', 'digest': 'fixture', 'created_at': now()})
            insert(con, 'changes', {'change_id': self.change, 'project_id': self.project,
                   'slug': 'fixture', 'state': 'active', 'delivery_mode': 'local',
                   'delivery_target': 'exports', 'created_at': now()})
            insert(con, 'revisions', {'revision_id': self.revision, 'project_id': self.project,
                   'change_id': self.change, 'context_id': self.context, 'created_phase': 'PLN',
                   'state': 'draft', 'title': 'test', 'summary': 'test', 'goal': 'test',
                   'in_scope': 'test', 'out_of_scope': 'remote', 'created_at': now()})

    def tearDown(self):
        self.temp.cleanup()

    def submit(self, operations, phase='PLN'):
        with self.store.transaction() as con:
            return batch(con, self.revision, phase, operations)

    def rejects(self, operations, code, path=None):
        with self.assertRaises(Fault) as caught:
            self.submit(operations)
        self.assertEqual(code, caught.exception.code)
        if path is not None:
            self.assertEqual(path, caught.exception.path)

    def test_legal_preparation_and_completion_self_check(self):
        self.submit([task(), task('test', 'VFY'), check(), condition(), condition('prep', 'prep', 'complete')])

    def test_complete_condition_and_start_dependency_form_cycle(self):
        self.rejects([task('a'), task('b'), check(owner='b'), condition('a', 'b', 'complete'),
                      {'op': 'add_task_dependency', 'task': ref('b'), 'predecessor': ref('a'), 'reason': 'after a'}],
                     'DEPENDENCY_CYCLE')

    def test_complete_condition_cannot_depend_on_future_phase(self):
        self.rejects([task(), task('test', 'RLS'), check(owner='test'), condition('prep', 'test', 'complete')],
                     'DEPENDENCY_PHASE_ORDER')

    def test_check_owner_cannot_hide_self_dependency(self):
        self.rejects([task(), check(), condition('prep', None, 'start')], 'TASK_SELF_DEPENDENCY')

    def test_explicit_self_start_has_field_error(self):
        self.rejects([task(), check(), condition('prep', 'prep', 'start')], 'TASK_SELF_DEPENDENCY')

    def test_wrong_producer_is_rejected(self):
        self.rejects([task(), task('test'), check(), condition('test', 'test')], 'CHECK_PRODUCER')

    def test_three_node_cycle(self):
        ops = [task('a'), task('b'), task('c')]
        ops += [{'op': 'add_task_dependency', 'task': ref(a), 'predecessor': ref(b), 'reason': 'order'}
                for a, b in [('a', 'b'), ('b', 'c'), ('c', 'a')]]
        self.rejects(ops, 'DEPENDENCY_CYCLE')

    def test_update_forward_reference(self):
        ids = self.submit([check(owner=None)])
        self.submit([{'op': 'update_check', 'id': ids['probe'], 'task': ref('prep')}, task()])

    def test_null_is_not_omission(self):
        ids = self.submit([check(owner=None)])
        self.rejects([{'op': 'update_check', 'id': ids['probe'], 'required': None}], 'INVALID_TYPE',
                     '/payload/operations/0/required')

    def test_unknown_nested_field(self):
        op = task()
        op['scope_paths'][0]['required_state'] = 'created and tested'
        self.rejects([op], 'UNKNOWN_FIELD', '/payload/operations/0/scope_paths/0/required_state')

    def test_unknown_key_and_wrong_type(self):
        self.rejects([check()], 'UNKNOWN_CLIENT_KEY', '/payload/operations/0/task/client_key')
        self.rejects([check(owner=None), {**task(), 'criteria': [ref('probe')]}], 'REFERENCE_TYPE',
                     '/payload/operations/1/criteria/0')

    def test_reference_path_contains_only_actual_fields(self):
        self.rejects([{**task(), 'criteria': [{'id': 'bad'}]}], 'INVALID_ID', '/payload/operations/0/criteria/0/id')

    def test_scope_cannot_cross_revisions(self):
        self.rejects([{**task(), 'criteria': [{'id': uid()}]}], 'REFERENCE_SCOPE', '/payload/operations/0/criteria/0/id')

    def test_enum_is_validated_before_sql(self):
        self.rejects([task(phase='IMP and VFY')], 'INVALID_ENUM', '/payload/operations/0/target_phase')

    def test_review_cannot_claim_command_test(self):
        self.rejects([{**check(owner=None), 'executor': 'agent', 'argv': None}], 'CHECK_EXECUTOR')

    def test_batch_failure_rolls_back_even_if_caller_catches(self):
        with self.store.transaction() as con:
            try:
                batch(con, self.revision, 'PLN', [task(), task('b'), check(), condition('prep', None, 'start')])
            except Fault:
                pass
            self.assertEqual(0, con.execute('SELECT count(*) FROM tasks').fetchone()[0])
        self.assertEqual({}, self.submit([]))

    def test_fingerprint_includes_producer_and_entire_check(self):
        ids = self.submit([task(), task('test', 'VFY'), check(), condition()])
        def fp():
            with self.store.read() as con:
                return task_fingerprint(con, self.revision, ids['test'])
        previous = fp()
        for op in [{'op': 'update_task', 'id': ids['prep'], 'description': 'different preparation'},
                   {'op': 'update_check', 'id': ids['probe'], 'method': 'inspection'},
                   {'op': 'update_check', 'id': ids['probe'], 'required': False},
                   {'op': 'update_check', 'id': ids['probe'], 'timeout_seconds': 1}]:
            self.submit([op])
            current = fp()
            self.assertNotEqual(previous, current)
            previous = current

    def test_committed_snapshot_is_immutable(self):
        ids = self.submit([task()])
        with self.store.transaction() as con:
            con.execute("UPDATE revisions SET state='committed',digest='fixture' WHERE revision_id=?", (self.revision,))
        self.rejects([task('new')], 'IMMUTABLE_REVISION')
        with self.store.transaction() as con:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute('UPDATE tasks SET title=? WHERE task_id=?', ('bad', ids['prep']))

    def test_read_only_empty_phase_is_not_complete(self):
        with self.store.read() as con:
            with self.assertRaises(Fault) as caught:
                validate_complete(con, self.revision, 'PLN')
            self.assertEqual('PHASE_INCOMPLETE', caught.exception.code)


if __name__ == '__main__':
    unittest.main()
