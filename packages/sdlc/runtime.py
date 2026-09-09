"""Public application boundary: durable diagnostics, scope, receipts and transactions."""
from __future__ import annotations

import mimetypes
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from . import content
from .common import API, VERSION, Fault, atomic_write, canonical, digest, file_lock, loads, now, redact, require, safe_path, uid
from .protocol import READ_COMMANDS, contract, validate_payload, validate_request
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
                    if replay:
                        require(replay['project_id'] == project and replay['request_digest'] == request_hash,
                                'OPERATION_CONFLICT', 'The same operation_id was used for a different request', '/operation_id', status='conflict')
                        return loads(replay['response_json'])
                # This independent transaction precedes payload validation and formal phase outputs.
                run_id = self.open_run(project, workspace, request)
                trace = safe_path(self.store.home, f'runs/{run_id}/{op_id}')
                self.write_trace(trace/'request.json', request)
                self.write_trace(trace/'bindings.json', {'project_id': project, 'workspace_id': workspace,
                                 'change_id': request.get('change_id'), 'run_id': run_id, 'runtime_version': VERSION,
                                 'runtime_digest': runtime_digest(), 'request_digest': request_hash})
                try:
                    with self.store.transaction() as con:
                        validate_payload(request)
                        data = self.write_command(con, project, workspace, run_id, request)
                        response = success(data, op_id, run_id)
                        self.record_operation(con, project, run_id, request, request_hash, response)
                except (Fault, sqlite3.DatabaseError, OSError, ValueError) as exc:
                    fault = as_fault(exc)
                    response = failure(fault, op_id, run_id)
                    with self.store.transaction() as con:
                        con.execute('UPDATE runs SET status=?,error_code=?,error_message=? WHERE run_id=?',
                                    ('blocked' if fault.status in {'blocked', 'conflict'} else 'failed', fault.code, response['errors'][0]['message'], run_id))
                        self.record_operation(con, project, run_id, request, request_hash, response)
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
        require(row['instance_id'] == config['instance_id'], 'WORKSPACE_INSTANCE', 'Rebind the copied workspace before writing', '/workspace_id', status='blocked')
        return project, workspace

    def open_run(self, project, workspace, request):
        supplied = request.get('run_id')
        with self.store.transaction() as con:
            if supplied:
                row = one(con, 'SELECT * FROM runs WHERE project_id=? AND workspace_id=? AND run_id=?', (project, workspace, supplied), code='RUN_SCOPE')
                require(row['change_id'] == request.get('change_id'), 'RUN_SCOPE', 'Run belongs to a different change', '/run_id')
                require(row['status'] not in {'completed', 'cancelled'}, 'RUN_CLOSED', 'Start a new run for further work', '/run_id', status='blocked')
                con.execute("UPDATE runs SET status='running',error_code=NULL,error_message=NULL WHERE run_id=?", (supplied,))
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
            insert(con, 'runs', {'run_id': value, 'project_id': project, 'change_id': change,
                   'workspace_id': workspace, 'input_revision_id': adopted, 'status': 'running',
                   'actor_id': actor, 'runtime_version': VERSION, 'contract_version': API,
                   'skill_version': VERSION, 'review_mode': review_mode, 'started_at': now()})
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
        if command in {'change.get', 'phase.prepare'}:
            return content.prepare(self.store, con, project, change, payload.get('phase'))
        raise Fault('UNKNOWN_COMMAND', 'Command is not implemented', '/command')

    def write_command(self, con, project, workspace, run, request):
        command, payload, change = request['command'], request.get('payload', {}), request.get('change_id')
        generation = request.get('expected_generation')
        if command == 'workspace.init':
            data = {'config': self.store.config(), 'next_actions': [{'action': 'context.commit', 'phase': 'CTX'}]}
            self.step(con, project, None, run, 'INIT', 'workspace.init')
            con.execute("UPDATE runs SET status='completed',finished_at=? WHERE run_id=?", (now(), run))
            return data
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
            data = content.create_change(con, project, payload, head_commit(self.root))
            con.execute('UPDATE runs SET change_id=?,input_revision_id=?,actor_id=?,review_mode=? WHERE run_id=?',
                        (data['change_id'], data['revision_id'], data['actor_id'], data['review_mode'], run))
            return data
        ch = content.change_row(con, project, change)
        if command == 'run.start':
            return {'change_id': change, 'revision_id': ch['active_revision_id']}
        if command == 'phase.submit':
            return content.phase_submit(con, project, change, payload, generation)
        if command == 'phase.complete':
            data = content.phase_complete(self.store, con, project, change, payload, generation)
            self.step(con, project, change, run, payload['phase'], 'phase.complete:'+payload['phase'],
                      payload['revision_id'], data['committed_revision_id'])
            return data
        if command == 'change.revise':
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
