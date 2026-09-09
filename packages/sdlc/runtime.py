"""Public application boundary: durable diagnostics, scope, receipts and transactions."""
from __future__ import annotations

import mimetypes
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from . import content, delivery, engine, execution, transfer, verification
from .common import API, VERSION, Fault, atomic_write, canonical, digest, file_lock, loads, now, redact, require, safe_path, uid
from .protocol import EFFECT_COMMANDS, READ_COMMANDS, contract, validate_payload, validate_request
from .storage import Store, insert, one


def failure(exc, operation_id=None, run_id=None):
    error = exc.record()
    error['message'] = redact(error['message'])
    if 'details' in error:
        error['details'] = redact(error['details'])
    return {'api_version': API, 'ok': False, 'status': exc.status, 'operation_id': operation_id,
            'run_id': run_id, 'errors': [error], 'next_actions': [
                {'action': 'correct_input' if exc.status == 'invalid_input' else 'inspect', 'error_code': exc.code}]}


def success(data, operation_id=None, run_id=None):
    return {'api_version': API, 'ok': True, 'status': 'completed', 'operation_id': operation_id,
            'run_id': run_id, 'errors': [], 'next_actions': data.get('next_actions', []), 'data': data}


def head_commit(root):
    try:
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, timeout=5, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


class Runtime:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.store = None

    def invoke(self, request):
        op_id, run_id = None, None
        try:
            validate_request(request)
            request = dict(request)
            command = request['command']
            if command == 'workspace.discover':
                validate_payload(request)
                return success({'candidates': transfer.discover(self.root)})
            if command in READ_COMMANDS:
                validate_payload(request)
                self.store = Store(self.root)
                config = self.store.config()
                with self.store.read() as con:
                    project, workspace = self.binding(con, config, request)
                    data = self.read_command(con, project, request)
                return success(data, request.get('operation_id'), request.get('run_id'))
            op_id = request.setdefault('operation_id', uid())
            request_hash = digest(request)
            self.store = Store(self.root)
            if command == 'workspace.init':
                validate_payload(request)
                self.store.initialize(request['payload']['name'])
            config = self.store.config()
            with file_lock(self.store.home/'.command.lock'):
                with self.store.read() as con:
                    project, workspace = self.binding(con, config, request)
                    replay = con.execute('SELECT * FROM operations WHERE operation_id=?', (op_id,)).fetchone()
                    replay_run = con.execute('SELECT * FROM runs WHERE run_id=?', (replay['run_id'],)).fetchone() if replay else None
                if replay:
                    require(replay['origin_kind'] == 'local', 'OPERATION_IMPORTED', 'Imported operation receipts are history; use a new local operation identity', status='blocked')
                    require(replay['project_id'] == project and replay['request_digest'] == request_hash,
                            'OPERATION_CONFLICT', 'The same operation_id was used for a different request', '/operation_id', status='conflict')
                    response = loads(replay['response_json'])
                    rebound_here = command == 'workspace.rebind' and response.get('data', {}).get('config', {}).get('store_id') == config['store_id']
                    require(replay_run and replay_run['origin_kind'] == 'local' and (replay_run['workspace_id'] == workspace or rebound_here),
                            'OPERATION_WORKSPACE', 'Copied operation history cannot execute in this workspace', status='blocked')
                    transfer.apply_config(self.store, command, response)
                    return response
                with self.store.read() as con:
                    pending_config = con.execute("SELECT o.operation_id FROM operations o JOIN runs r USING(run_id) WHERE r.workspace_id=? AND r.origin_kind='local' AND o.origin_kind='local' AND o.command IN ('workspace.bind','workspace.rebind') AND o.status='succeeded' AND o.config_applied_at IS NULL", (workspace,)).fetchall()
                    require(not pending_config, 'CONFIG_TRANSITION_PENDING', 'Replay the committed configuration operation before further mutations', status='blocked', details=[r[0] for r in pending_config])
                # This independent transaction precedes payload validation and formal phase outputs.
                run_id = self.open_run(project, workspace, request)
                trace = safe_path(self.store.home, f'runs/{run_id}/{op_id}')
                self.write_trace(trace/'request.json', request)
                self.write_trace(trace/'bindings.json', {'project_id': project, 'workspace_id': workspace,
                                 'change_id': request.get('change_id'), 'run_id': run_id, 'runtime_version': VERSION,
                                 'runtime_digest': runtime_digest(), 'request_digest': request_hash})
                try:
                    if command in EFFECT_COMMANDS:
                        response = self.execute_effect(project, run_id, request, request_hash, trace/'work')
                    else:
                        with self.store.transaction() as con:
                            validate_payload(request)
                            data = self.write_command(con, project, workspace, run_id, request)
                            response = self.data_response(data, op_id, run_id)
                            self.record_operation(con, project, run_id, request, request_hash, response)
                except (Fault, sqlite3.DatabaseError, OSError, ValueError) as exc:
                    fault = as_fault(exc)
                    response = failure(fault, op_id, run_id)
                    with self.store.transaction() as con:
                        if command == 'phase.submit' and fault.status == 'invalid_input':
                            con.execute('UPDATE runs SET format_attempts=format_attempts+1 WHERE run_id=?', (run_id,))
                            budget = one(con, 'SELECT format_attempts,max_format_attempts FROM runs WHERE run_id=?', (run_id,))
                            if budget['format_attempts'] >= budget['max_format_attempts']:
                                response['status'] = 'blocked'
                                response['errors'].append({'code': 'FORMAT_BUDGET', 'message': 'Inspect the failed field and configure a higher format budget before retrying'})
                                response['next_actions'] = [{'action': 'run.configure', 'error_code': 'FORMAT_BUDGET'}]
                        existing = con.execute('SELECT status FROM operations WHERE operation_id=?', (op_id,)).fetchone()
                        if existing and existing['status'] == 'unknown':
                            response['status'] = 'unknown'
                            response['next_actions'] = [{'action': 'operation.reconcile', 'operation_id': op_id}]
                            con.execute('UPDATE operations SET response_json=? WHERE operation_id=?', (canonical(response).decode(), op_id))
                        else:
                            self.record_operation(con, project, run_id, request, request_hash, response)
                        con.execute('UPDATE runs SET status=?,error_code=?,error_message=? WHERE run_id=?',
                                    ('interrupted' if response['status'] == 'unknown' else 'blocked' if fault.status in {'blocked', 'conflict'} else 'failed', fault.code, response['errors'][0]['message'], run_id))
                transfer.apply_config(self.store, command, response)
                # Rendering/trace failures cannot undo or retry a committed operation.
                try:
                    self.write_trace(trace/'response.json', response)
                    from .rendering import render_run
                    render_run(self.store, run_id)
                except (Fault, OSError, sqlite3.DatabaseError) as exc:
                    response = {**response, 'warnings': [{'code': 'VIEW_FAILED', 'message': str(exc),
                                'next_action': 'render', 'business_receipt_committed': True}]}
                return response
        except (Fault, sqlite3.DatabaseError, OSError, ValueError) as exc:
            response = failure(as_fault(exc), op_id, run_id)
            if run_id and self.store:
                try:
                    with self.store.transaction() as con:
                        con.execute("UPDATE runs SET status='failed',error_code=?,error_message=? WHERE run_id=?",
                                    (response['errors'][0]['code'], response['errors'][0]['message'], run_id))
                        if op_id and not con.execute('SELECT 1 FROM operations WHERE operation_id=?', (op_id,)).fetchone():
                            self.record_operation(con, project, run_id, request, request_hash, response)
                except (Fault, OSError, sqlite3.DatabaseError):
                    pass  # Bootstrap is the final diagnostic path when the Store itself is unavailable.
            # A failed read never changes business data; startup failures still retain separate diagnostics.
            response['diagnostic_path'] = self.bootstrap(request, response)
            return response

    def binding(self, con, config, request):
        project = request.get('project_id', config['project_id'])
        workspace = request.get('workspace_id', config['workspace_id'])
        row = one(con, 'SELECT * FROM workspaces WHERE project_id=? AND workspace_id=?', (project, workspace), code='WORKSPACE_SCOPE')
        if request['command'] not in READ_COMMANDS and request['command'] != 'workspace.rebind':
            require(config.get('root_path') == str(self.root), 'WORKSPACE_MOVED',
                    'Workspace path changed; explicitly rebind the copied or moved directory', status='blocked')
        require(request['command'] == 'workspace.rebind' or row['instance_id'] == config['instance_id'], 'WORKSPACE_INSTANCE', 'Rebind the copied workspace before writing', '/workspace_id', status='blocked')
        return project, workspace

    def open_run(self, project, workspace, request):
        supplied = request.get('run_id')
        with self.store.transaction() as con:
            if supplied:
                row = one(con, 'SELECT * FROM runs WHERE project_id=? AND workspace_id=? AND run_id=?', (project, workspace, supplied), code='RUN_SCOPE')
                require(row['origin_kind'] == 'local', 'RUN_IMPORTED', 'Imported Runs are history; start a new local Run', status='blocked')
                require(row['change_id'] == request.get('change_id'), 'RUN_SCOPE', 'Run belongs to a different change', '/run_id')
                require(row['status'] not in {'completed', 'cancelled'}, 'RUN_CLOSED', 'Start a new run for further work', '/run_id', status='blocked')
                return supplied
            change = request.get('change_id')
            adopted = None
            if change:
                row = con.execute('SELECT active_revision_id FROM changes WHERE project_id=? AND change_id=?', (project, change)).fetchone()
                if row:
                    adopted = row[0]
                else:
                    change = None  # Unbound diagnostic Run; invalid scope is rejected in dispatch.
            payload = request.get('payload', {})
            actor = payload.get('actor_id', 'current-agent')
            review_mode = payload.get('review_mode', 'auto')
            if not isinstance(actor, str) or not actor.strip():
                actor = 'current-agent'
            if review_mode not in {'auto', 'assisted'}:
                review_mode = 'auto'
            value = uid()
            prior = con.execute("SELECT * FROM runs WHERE project_id=? AND change_id=? AND workspace_id=? AND origin_kind='local' AND current_phase IS NOT NULL ORDER BY rowid DESC LIMIT 1", (project, change, workspace)).fetchone() if change else None
            continuation = {key: prior[key] for key in ('current_phase', 'repair_round', 'no_progress_rounds', 'last_progress_digest',
                            'max_repair_rounds', 'no_progress_limit', 'max_format_attempts', 'format_attempts')} if prior else {}
            insert(con, 'runs', {'run_id': value, 'project_id': project, 'change_id': change,
                   'workspace_id': workspace, 'input_revision_id': adopted, 'status': 'running',
                   'actor_id': actor, 'current_phase': 'REQ' if request['command'] == 'change.create' else None, 'runtime_version': VERSION, 'contract_version': API,
                   'skill_version': VERSION, 'review_mode': review_mode, 'started_at': now(), **continuation})
            return value

    def record_operation(self, con, project, run, request, hashed, response):
        insert(con, 'operations', {'operation_id': request['operation_id'], 'project_id': project, 'run_id': run,
               'command': request['command'], 'request_digest': hashed, 'status': 'succeeded' if response['ok'] else 'rejected',
               'response_json': canonical(response).decode(), 'created_at': now()})

    def read_command(self, con, project, request):
        command, payload, change = request['command'], request.get('payload', {}), request.get('change_id')
        if command == 'workspace.inspect':
            return {'config': self.store.config(), 'schema_version': con.execute('SELECT max(version) FROM schema_migrations').fetchone()[0],
                    'projects': [dict(r) for r in con.execute('SELECT * FROM projects')], 'contract': contract()}
        if command == 'run.get':
            require(request.get('run_id'), 'RUN_REQUIRED', 'Specify run_id', '/run_id')
            run = dict(one(con, 'SELECT * FROM runs WHERE project_id=? AND run_id=?', (project, request['run_id']), code='RUN_SCOPE'))
            require(not request.get('change_id') or run['change_id'] == request['change_id'], 'RUN_SCOPE', 'Run belongs to a different change', '/change_id')
            require(run['workspace_id'] == request.get('workspace_id', self.store.config()['workspace_id']), 'RUN_SCOPE', 'Run belongs to a different workspace', '/workspace_id')
            return {'run': run,
                    'steps': [dict(r) for r in con.execute('SELECT * FROM steps WHERE project_id=? AND run_id=? ORDER BY started_at', (project, request['run_id']))]}
        if command == 'status':
            result = {'changes': [dict(r) for r in con.execute('SELECT * FROM changes WHERE project_id=? ORDER BY slug', (project,))],
                      'runs': [dict(r) for r in con.execute('SELECT * FROM runs WHERE project_id=? ORDER BY started_at', (project,))]}
            if change:
                result['selected'] = content.prepare(self.store, con, project, change)
            return result
        if command == 'delivery.get':
            content.change_row(con, project, change)
            return {'delivery': dict(delivery.row(con, project, change, payload['delivery_id']))}
        if command in {'task.next', 'check.evaluate', 'finding.list'}:
            content.change_row(con, project, change)
            require(request.get('run_id'), 'RUN_REQUIRED', 'Use a bound Run', '/run_id')
            engine.run_row(con, project, change, request['run_id'])
            if command == 'task.next':
                return engine.task_next(self.store, con, project, change, request['run_id'], payload['revision_id'], payload.get('environment'))
            if command == 'check.evaluate':
                engine.adopted(con, project, change, payload['revision_id'])
                return verification.evaluate(self.store, con, project, change, payload['revision_id'], payload.get('environment'))
            return {'findings': [dict(r) for r in con.execute('SELECT * FROM findings WHERE project_id=? AND change_id=?', (project, change))]}
        if command in {'change.get', 'phase.prepare'}:
            current = engine.phase(con, project, change, request['run_id']) if request.get('run_id') else None
            return content.prepare(self.store, con, project, change, payload.get('phase'), execution_phase=current)
        raise Fault('UNKNOWN_COMMAND', 'Command is not implemented', '/command')

    def write_command(self, con, project, workspace, run, request):
        command, payload, change = request['command'], request.get('payload', {}), request.get('change_id')
        generation = request.get('expected_generation')
        if command == 'workspace.init':
            data = {'config': self.store.config(), 'next_actions': [{'action': 'context.commit', 'phase': 'CTX'}]}
            self.step(con, project, None, run, 'INIT', 'workspace.init')
            con.execute("UPDATE runs SET status='completed',finished_at=? WHERE run_id=?", (now(), run))
            return data
        if command in {'workspace.bind', 'workspace.collect', 'workspace.rebind'} and self.store.config().get('root_path') == str(self.root):
            pending = con.execute("SELECT o.operation_id FROM operations o JOIN runs r USING(run_id) WHERE r.workspace_id=? AND r.origin_kind='local' AND o.origin_kind='local' AND o.status='unknown'", (workspace,)).fetchall()
            require(not pending, 'UNRESOLVED_EFFECT', 'Reconcile pending effects before changing workspace bindings or adopting imported inputs', status='blocked')
            busy = con.execute("SELECT run_id FROM runs WHERE workspace_id=? AND origin_kind='local' AND lease_id IS NOT NULL", (workspace,)).fetchone()
            require(not busy, 'WORKSPACE_BUSY', 'Finish or cancel the local execution lease before changing workspace bindings or collecting', status='blocked')
        if command == 'workspace.clone':
            return transfer.clone(self.store, con, payload, request['operation_id'])
        if command == 'workspace.export':
            return transfer.export(self.store, con, project, payload['change_id'])
        if command == 'workspace.collect':
            return transfer.collect(self.store, con, project, payload)
        if command in {'workspace.bind', 'workspace.rebind'}:
            return transfer.bindings(self.store, con, project, payload, rebind=command == 'workspace.rebind')
        if command == 'project.create':
            new_project, new_workspace = uid(), uid()
            insert(con, 'projects', {'project_id': new_project, 'name': payload['name'], 'created_at': now()})
            insert(con, 'workspaces', {'workspace_id': new_workspace, 'project_id': new_project, 'label': self.root.name,
                   'instance_id': self.store.config()['instance_id'], 'created_at': now()})
            con.execute("UPDATE runs SET status='completed',finished_at=? WHERE run_id=?", (now(), run))
            return {'project_id': new_project, 'workspace_id': new_workspace}
        if command == 'context.commit':
            require(change is None, 'CONTEXT_SCOPE', 'CTX is project-scoped', '/change_id')
            data = content.context_commit(con, project, payload)
            self.step(con, project, None, run, 'CTX', 'context.commit')
            con.execute("UPDATE runs SET status='completed',finished_at=? WHERE run_id=?", (now(), run))
            return data
        if command == 'change.create':
            require(change is None, 'CHANGE_SCOPE', 'Creation allocates the change identity', '/change_id')
            data = content.create_change(con, project, payload, head_commit(self.root), workspace)
            con.execute('UPDATE runs SET change_id=?,input_revision_id=?,actor_id=?,review_mode=? WHERE run_id=?',
                        (data['change_id'], data['revision_id'], data['actor_id'], data['review_mode'], run))
            return data
        ch = content.change_row(con, project, change)
        pending = [r[0] for r in con.execute("SELECT o.operation_id FROM operations o JOIN runs r USING(run_id) WHERE r.change_id=? AND r.workspace_id=? AND r.origin_kind='local' AND o.origin_kind='local' AND o.status='unknown'", (change, workspace))]
        require(not pending, 'UNRESOLVED_EFFECT', 'Reconcile unknown operations before further mutations', status='blocked', details=pending)
        if command == 'authorization.grant':
            state = engine.run_row(con, project, change, run)
            return content.grant(con, project, change, workspace, state['actor_id'], payload['authorizations'])
        if command == 'change.resolve':
            require(not con.execute("SELECT 1 FROM steps s JOIN runs r USING(run_id) WHERE s.change_id=? AND r.workspace_id=? AND r.origin_kind='local' AND s.status='running'", (change, workspace)).fetchone(),
                    'ATTEMPT_RUNNING', 'Finish active local work before merging content snapshots', status='blocked')
            require(payload['phase'] in {'REQ', 'DSN', 'PLN'}, 'PHASE_OWNERSHIP', 'Resolve into a content phase')
            parent = content.revision_row(con, project, change)
            require(parent['state'] == 'committed', 'DRAFT_PENDING', 'Checkpoint the target draft before resolving', status='blocked')
            source = one(con, "SELECT * FROM revisions WHERE project_id=? AND change_id=? AND revision_id=? AND state='committed'",
                         (project, change, payload['source_revision_id']), code='REVISION_SCOPE')
            require(source['revision_id'] != parent['revision_id'], 'MERGE_SOURCE', 'Select a different source revision')
            rev = content.child_revision(con, parent, payload['phase'])
            con.execute('UPDATE revisions SET merged_from_id=? WHERE revision_id=?', (source['revision_id'], rev))
            con.execute('UPDATE runs SET current_phase=? WHERE run_id=?', (payload['phase'], run))
            return {'revision_id': rev, 'parent_id': parent['revision_id'], 'merged_from_id': source['revision_id'], 'generation': 0}
        if command == 'run.configure':
            state = engine.run_row(con, project, change, run)
            allowed = ('max_repair_rounds', 'no_progress_limit', 'max_format_attempts')
            values = {key: payload.get(key, state[key]) for key in allowed}
            require(all(0 < value <= 100 for value in values.values()), 'BUDGET_LIMIT', 'Configured budgets must be between 1 and 100', '/payload')
            con.execute('UPDATE runs SET max_repair_rounds=?,no_progress_limit=?,max_format_attempts=? WHERE run_id=?', (*values.values(), run))
            return {**values, 'reason': redact(payload['reason']), 'actor_id': state['actor_id']}
        if command == 'run.start':
            return {'change_id': change, 'revision_id': ch['active_revision_id']}
        if command == 'run.acquire':
            return engine.acquire(con, project, change, run)
        if command in {'run.resume', 'run.cancel'}:
            pending = con.execute("SELECT operation_id FROM operations WHERE run_id=? AND origin_kind='local' AND status='unknown'", (run,)).fetchall()
            require(not pending, 'UNRESOLVED_EFFECT', 'Reconcile unknown operations before resuming/cancelling', status='blocked', details=[r[0] for r in pending])
            con.execute("UPDATE steps SET status='interrupted',outcome='unknown',finished_at=? WHERE run_id=? AND status='running'", (now(), run))
            con.execute('UPDATE runs SET lease_id=NULL,status=?,finished_at=? WHERE run_id=?', ('cancelled' if command == 'run.cancel' else 'running', now() if command == 'run.cancel' else None, run))
            if command == 'run.resume':
                return {**engine.acquire(con, project, change, run), 'resumed': True}
            return {'cancelled': True}
        if command == 'task.start':
            return engine.task_start(self.store, con, project, change, run, payload)
        if command == 'task.finish':
            return engine.task_finish(self.store, con, project, change, run, payload)
        if command == 'check.record_review':
            return engine.record_review(self.store, con, project, change, run, payload)
        if command == 'check.reuse':
            return engine.reuse_check(self.store, con, project, change, run, payload)
        if command == 'delivery.prepare':
            return delivery.prepare(self.store, con, project, change, run, payload)
        if command in {'finding.address', 'finding.resolve'}:
            return engine.finding_action(self.store, con, project, change, run, command, payload)
        if command == 'phase.submit':
            state = engine.run_row(con, project, change, run)
            require(state['format_attempts'] < state['max_format_attempts'], 'FORMAT_BUDGET', 'Inspect the failed submission and configure a higher format budget', status='blocked')
            data = content.phase_submit(con, project, change, payload, generation)
            con.execute('UPDATE runs SET format_attempts=0 WHERE run_id=?', (run,))
            return data
        if command == 'phase.complete':
            if payload['phase'] in {'IMP', 'VFY', 'RLS'}:
                return engine.complete_phase(self.store, con, project, change, run, payload)
            data = content.phase_complete(self.store, con, project, change, payload, generation)
            con.execute('UPDATE runs SET current_phase=? WHERE run_id=?', (data['next_actions'][0]['phase'], run))
            self.step(con, project, change, run, payload['phase'], 'phase.complete:'+payload['phase'],
                      payload['revision_id'], data['committed_revision_id'])
            return data
        if command == 'change.revise':
            require(not con.execute("SELECT 1 FROM steps s JOIN runs r USING(run_id) WHERE s.change_id=? AND r.workspace_id=? AND r.origin_kind='local' AND s.status='running'", (change, workspace)).fetchone(),
                    'ATTEMPT_RUNNING', 'Finish or explicitly interrupt active work before revising its inputs', status='blocked')
            require(payload['phase'] in {'REQ', 'DSN', 'PLN'}, 'PHASE_OWNERSHIP', 'Revise REQ/DSN/PLN', '/payload/phase')
            parent = content.revision_row(con, project, change)
            if payload.get('context_id'):
                one(con, "SELECT 1 FROM contexts WHERE project_id=? AND context_id=? AND state='committed'", (project, payload['context_id']), code='CONTEXT_SCOPE')
            if parent['state'] == 'draft':
                content.cas(con, parent['revision_id'], generation)
                hashed = self.store.content_digest(con, parent['revision_id'])
                con.execute("UPDATE revisions SET state='abandoned',digest=? WHERE revision_id=?", (hashed, parent['revision_id']))
                parent = one(con, 'SELECT * FROM revisions WHERE revision_id=?', (parent['revision_id'],))
            rev = content.child_revision(con, parent, payload['phase'], context_id=payload.get('context_id'))
            con.execute('UPDATE runs SET current_phase=? WHERE run_id=?', (payload['phase'], run))
            return {'change_id': change, 'revision_id': rev, 'generation': 0, 'reason': payload['reason']}
        if command == 'asset.add':
            row = content.revision_row(con, project, change)
            require(row['state'] == 'draft', 'IMMUTABLE_REVISION', 'Attach content to a draft', '/payload/owner_id')
            content.cas(con, row['revision_id'], generation)
            owner_table = {'source': ('sources', 'source_id'), 'design': ('designs', 'design_id')}
            require(payload['owner_type'] in owner_table, 'INVALID_ENUM', 'Expected source/design', '/payload/owner_type')
            table, col = owner_table[payload['owner_type']]
            one(con, f'SELECT 1 FROM {table} WHERE revision_id=? AND {col}=?', (row['revision_id'], payload['owner_id']), code='ASSET_OWNER_SCOPE')
            path = safe_path(self.root, payload['path'])
            require(path.is_file() and path.stat().st_size <= 64*1024*1024, 'ASSET_LIMIT', 'Asset must be a file of at most 64 MiB', '/payload/path')
            asset = self.store.put_asset(con, project, path.read_bytes(), payload.get('media_type') or mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            value = uid()
            insert(con, 'asset_links', {'project_id': project, 'link_id': value, 'asset_id': asset,
                   'revision_id': row['revision_id'], col: payload['owner_id'], 'original_name': payload.get('original_name', path.name),
                   'purpose': payload['purpose'], 'ordinal': payload.get('ordinal', 0)})
            return {'asset_id': asset, 'link_id': value, 'generation': generation+1}
        if command == 'render':
            # Called separately from the business transaction by the CLI after its receipt.
            if not request.get('run_id'):
                con.execute("UPDATE runs SET status='completed',finished_at=? WHERE run_id=?", (now(), run))
            return {'change_id': change, 'render_requested': True}
        raise Fault('NOT_IMPLEMENTED', 'Command not implemented yet', '/command', status='blocked')

    def data_response(self, data, operation_id, run_id):
        if data.get('control_status'):
            response = failure(Fault(data['error_code'], 'Verification requires the returned next action', status=data['control_status']), operation_id, run_id)
            response.update(data=data, next_actions=data['next_actions'])
            return response
        return success(data, operation_id, run_id)

    def execute_effect(self, project, run, request, hashed, work):
        command, payload, change = request['command'], request.get('payload', {}), request.get('change_id')
        work.mkdir(parents=True, exist_ok=True)
        if command == 'operation.reconcile':
            validate_payload(request)
            data = self.reconcile_effect(project, change, run, payload['operation_id'])
            response = success(data, request['operation_id'], run)
            with self.store.transaction() as con:
                self.record_operation(con, project, run, request, hashed, response)
            return response
        with self.store.transaction() as con:
            validate_payload(request)
            unknown = con.execute("SELECT operation_id FROM operations WHERE run_id=? AND origin_kind='local' AND status='unknown'", (run,)).fetchall()
            require(not unknown, 'UNRESOLVED_EFFECT', 'Reconcile an earlier uncertain effect first', status='blocked', details=[r[0] for r in unknown])
            if command == 'task.write':
                intent = engine.prepare_write(self.store, con, project, change, run, payload, work)
            elif command == 'delivery.execute':
                intent = delivery.prepare_effect(self.store, con, project, change, run, payload, work)
            else:
                intent = engine.prepare_check(self.store, con, project, change, run, payload, work)
            pending = failure(Fault('EFFECT_UNKNOWN', 'Effect intent recorded; reconcile before retrying', status='unknown'), request['operation_id'], run)
            insert(con, 'operations', {'operation_id': request['operation_id'], 'project_id': project, 'run_id': run,
                   'command': command, 'request_digest': hashed, 'status': 'unknown', 'response_json': canonical(pending).decode(),
                   'intent_json': canonical(intent).decode(), 'created_at': now()})
        # External tools and product writes never run inside a SQLite transaction.
        if command == 'task.write':
            evidence = engine.apply_write(self.store, project, intent)
        elif command == 'delivery.execute':
            evidence = delivery.execute(self.store, project, intent, work)
        else:
            evidence = execution.run_command(intent['argv'], self.root, work, intent['writable'],
                        env=intent['environment'], timeout=intent['timeout_seconds'])
        atomic_write(work/'result.json', canonical(evidence)+b'\n')
        # A separate collector receipt survives a crash before business finalization.
        # An orphan result file without this digest cannot assert PASS on recovery.
        with self.store.transaction() as con:
            con.execute('UPDATE operations SET result_digest=? WHERE operation_id=?', (digest(evidence), request['operation_id']))
        with self.store.transaction() as con:
            data = evidence if command == 'task.write' else (delivery.finish if command == 'delivery.execute' else engine.finish_check)(self.store, con, project, change, run, intent, evidence)
            response = success(data, request['operation_id'], run)
            if data.get('outcome') == 'blocked':
                response = failure(Fault(data.get('error_code') or 'CHECK_BLOCKED', 'Check could not execute', status='blocked'), request['operation_id'], run)
                response['data'] = data
                con.execute("UPDATE runs SET status='blocked',error_code=?,error_message=? WHERE run_id=?", (response['errors'][0]['code'], response['errors'][0]['message'], run))
            con.execute('UPDATE operations SET status=?,response_json=? WHERE operation_id=?', ('succeeded' if response['ok'] else 'rejected', canonical(response).decode(), request['operation_id']))
        return response

    def reconcile_effect(self, project, change, run, original):
        with self.store.read() as con:
            engine.run_row(con, project, change, run)
            operation = one(con, 'SELECT * FROM operations WHERE project_id=? AND run_id=? AND operation_id=?', (project, run, original), code='OPERATION_SCOPE')
            require(operation['origin_kind'] == 'local', 'OPERATION_IMPORTED', 'Imported effects cannot be reconciled in this workspace', status='blocked')
            if operation['status'] != 'unknown':
                return {'original_receipt': loads(operation['response_json']), 'already_reconciled': True}
        work = safe_path(self.store.home, f'runs/{run}/{original}/work')
        require(operation['intent_json'], 'EFFECT_INTENT_MISSING', 'Original intent is unavailable; inspect retained diagnostics', status='blocked')
        intent = loads(operation['intent_json'])
        require(intent['kind'] == operation['command'] and canonical(intent) == canonical(loads((work/'intent.json').read_bytes())),
                'EFFECT_INTEGRITY', 'Retained intent differs from its durable operation', status='blocked')
        if intent['kind'] == 'task.write':
            data = engine.apply_write(self.store, project, intent)
            response = success(data, original, run)
            with self.store.transaction() as con:
                con.execute("UPDATE operations SET status='succeeded',response_json=? WHERE operation_id=?", (canonical(response).decode(), original))
            return {'original_receipt': response, 'reconciled': True}
        result_path = work/'result.json'
        if result_path.exists() and operation['result_digest']:
            evidence = loads(result_path.read_bytes())
            require(digest(evidence) == operation['result_digest'], 'EFFECT_INTEGRITY', 'Collector result digest differs', status='blocked')
        else:
            process_path = work/'process.json'
            if process_path.exists():
                import os
                pid = loads(process_path.read_bytes())['pid']
                try:
                    os.killpg(pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    raise Fault('TOOL_STILL_RUNNING', 'Original tool process still exists; do not duplicate it', status='blocked')
            if intent['kind'] == 'delivery.execute':
                path = delivery.destination(self.store, intent['target'], intent['sha256'])
                evidence = delivery.execute(self.store, project, intent, work/'recheck'/uid(), write=not path.exists())
            else:
                evidence = {'status': 'unknown', 'summary': 'Interrupted before a durable result; retained logs are not PASS', 'exit_code': None}
        with self.store.transaction() as con:
            finish = delivery.finish if intent['kind'] == 'delivery.execute' else engine.finish_check
            data = finish(self.store, con, project, change, run, intent, evidence)
            response = success(data, original, run)
            con.execute("UPDATE operations SET status='succeeded',response_json=? WHERE operation_id=?", (canonical(response).decode(), original))
        return {'original_receipt': response, 'reconciled': True, 'next_action': 'check.run' if data['outcome'] == 'unknown' else 'inspect'}

    def step(self, con, project, change, run, phase, key, input_rev=None, output_rev=None):
        value = uid()
        attempt = con.execute('SELECT coalesce(max(attempt),0)+1 FROM steps WHERE run_id=? AND step_key=?', (run, key)).fetchone()[0]
        insert(con, 'steps', {'step_id': value, 'project_id': project, 'change_id': change, 'run_id': run,
               'phase': phase, 'step_key': key, 'attempt': attempt, 'input_revision_id': input_rev,
               'output_revision_id': output_rev, 'status': 'completed', 'outcome': 'pass', 'started_at': now(), 'finished_at': now()})
        return value

    def write_trace(self, path, value):
        atomic_write(path, canonical(redact(value))+b'\n')

    def bootstrap(self, request, response):
        try:
            if self.store is None and self.root.is_dir():
                self.store = Store(self.root)
            if self.store:
                home = safe_path(self.store.home, 'runs/bootstrap-'+uid())
                # Ignore before diagnostics so failed first initialization also stays outside VCS.
                if not (self.store.home/'.gitignore').exists():
                    atomic_write(self.store.home/'.gitignore', b'*\n')
            else:
                home = Path(tempfile.mkdtemp(prefix='sdlc-v2-bootstrap-'))
            self.write_trace(home/'request.json', request)
            self.write_trace(home/'response.json', response)
            return str(home)
        except (OSError, Fault):
            return None


def as_fault(exc):
    if isinstance(exc, Fault):
        return exc
    if isinstance(exc, sqlite3.IntegrityError):
        return Fault('DATA_CONSTRAINT', 'Relational constraint rejected the write', status='invalid_input')
    if isinstance(exc, sqlite3.DatabaseError):
        return Fault('STORE_FAILURE', str(exc), status='runtime_error')
    return Fault('RUNTIME_IO', str(exc), status='runtime_error')


def runtime_digest():
    root = Path(__file__).parent
    return digest({p.name: digest(p.read_text()) for p in sorted(root.iterdir()) if p.suffix in {'.py', '.sql'}})
