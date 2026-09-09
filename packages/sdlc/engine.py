"""IMP/VFY application services with persistent leases and attempt identities."""
from pathlib import Path
from .common import Fault, atomic_write, canonical, digest, loads, now, redact, require, safe_path, sha, uid
from . import content, execution, verification
from .domain import fields, task_fingerprint
from .protocol import FILE_CHANGE, REVIEW_FINDING
from .storage import insert, one


def adopted(con, project, change, revision):
    ch = content.change_row(con, project, change)
    require(ch['active_revision_id'] == revision, 'REVISION_SCOPE', 'Execution must use the adopted committed snapshot', '/payload/revision_id', status='blocked')
    require(not con.execute("SELECT 1 FROM revisions WHERE change_id=? AND state='draft'", (change,)).fetchone(),
            'DRAFT_PENDING', 'Complete the current content draft before execution', status='blocked')
    return one(con, "SELECT * FROM revisions WHERE project_id=? AND change_id=? AND revision_id=? AND state='committed'", (project, change, revision))


def run_row(con, project, change, run):
    return one(con, 'SELECT * FROM runs WHERE project_id=? AND change_id=? AND run_id=?', (project, change, run), code='RUN_SCOPE')


def phase(con, project, change, run):
    return run_row(con, project, change, run)['current_phase'] or 'IMP'


def lease(con, project, change, run, value):
    row = run_row(con, project, change, run)
    require(value and row['lease_id'] == value, 'LEASE_STALE', 'Acquire the current execution lease', '/payload/lease_id', status='blocked')
    budget_available(row)
    return row


def budget_available(row):
    require(row['repair_round'] < row['max_repair_rounds'] and row['no_progress_rounds'] < row['no_progress_limit'],
            'REPAIR_BUDGET', 'Inspect the recorded gap and explicitly configure a higher budget before continuing', status='blocked')


def acquire(con, project, change, run):
    row = run_row(con, project, change, run)
    budget_available(row)
    other = con.execute("SELECT run_id FROM runs WHERE workspace_id=? AND origin_kind='local' AND lease_id IS NOT NULL AND run_id<>?", (row['workspace_id'], run)).fetchone()
    require(other is None, 'WORKSPACE_BUSY', 'Another Run owns product execution', status='blocked', details={'run_id': other[0]} if other else None)
    value = row['lease_id'] or uid()
    con.execute('UPDATE runs SET lease_id=? WHERE run_id=?', (value, run))
    return {'lease_id': value, 'phase': phase(con, project, change, run)}


def task_row(con, revision, task):
    return one(con, 'SELECT * FROM tasks WHERE revision_id=? AND task_id=?', (revision, task), code='TASK_SCOPE')


def live_task(con, run, task, step):
    return one(con, "SELECT * FROM steps WHERE run_id=? AND task_id=? AND step_id=? AND step_key=? AND status='running'", (run, task, step, 'task:'+task), code='TASK_NOT_RUNNING')


def new_step(con, project, change, run, revision, phase_name, key, *, task=None, definition=None, status='running'):
    value = uid()
    attempt = con.execute('SELECT coalesce(max(attempt),0)+1 FROM steps WHERE run_id=? AND step_key=?', (run, key)).fetchone()[0]
    insert(con, 'steps', {'step_id': value, 'project_id': project, 'change_id': change, 'run_id': run, 'phase': phase_name,
           'step_key': key, 'attempt': attempt, 'input_revision_id': revision, 'task_id': task,
           'definition_digest': definition, 'status': status, 'started_at': now()})
    return value


def task_start(store, con, project, change, run, p):
    adopted(con, project, change, p['revision_id'])
    lease(con, project, change, run, p['lease_id'])
    task = task_row(con, p['revision_id'], p['task_id'])
    require(task['target_phase'] == phase(con, project, change, run), 'PHASE_ORDER', 'Task belongs to a different execution phase', '/payload/task_id', status='blocked')
    require(not con.execute("SELECT 1 FROM steps WHERE run_id=? AND task_id=? AND step_key=? AND status='running'", (run, p['task_id'], 'task:'+p['task_id'])).fetchone(), 'TASK_RUNNING', 'Task already has an active attempt', status='conflict')
    for scope in loads(task['scope_paths_json']):
        verification.authorize(con, project, change, run, 'edit_local' if scope['access'] == 'write' else 'run_check', scope['resource'])
    verification.ensure_conditions(store, con, project, change, run, p['revision_id'], task, 'start', p.get('environment'))
    step = new_step(con, project, change, run, p['revision_id'], task['target_phase'], 'task:'+p['task_id'],
                    task=p['task_id'], definition=task_fingerprint(con, p['revision_id'], p['task_id']))
    return {'step_id': step, 'task_id': p['task_id'], 'lease_id': p['lease_id'], 'status': 'running'}


def task_finish(store, con, project, change, run, p):
    adopted(con, project, change, p['revision_id'])
    lease(con, project, change, run, p['lease_id'])
    task = task_row(con, p['revision_id'], p['task_id'])
    live_task(con, run, p['task_id'], p['step_id'])
    verification.ensure_conditions(store, con, project, change, run, p['revision_id'], task, 'complete', p.get('environment'))
    observed = execution.observe(store.root, [s['path'] for s in loads(task['scope_paths_json']) if s['resource'] == 'main'])
    snap = execution.snapshot(store, con, project, run, observed)
    # No test conclusion is fabricated from task completion.
    con.execute("UPDATE steps SET status='completed',outcome='not_applicable',snapshot_id=?,finished_at=? WHERE step_id=?", (snap, now(), p['step_id']))
    return {'task_id': p['task_id'], 'step_id': p['step_id'], 'snapshot_id': snap, 'status': 'completed', 'summary': redact(p['summary'])}


def task_next(store, con, project, change, run, revision, overrides=None):
    adopted(con, project, change, revision)
    current = phase(con, project, change, run)
    result = []
    for task in con.execute('SELECT * FROM tasks WHERE revision_id=? AND target_phase=? ORDER BY ordinal,task_id', (revision, current)):
        if verification.task_completed(con, change, revision, task['task_id']):
            continue
        blocks = verification.task_conditions(store, con, project, change, run, revision, task, 'start', overrides)
        result.append({'task': dict(task), 'runnable': not blocks, 'blockers': blocks})
    return {'phase': current, 'tasks': result}


def prepare_write(store, con, project, change, run, p, work):
    adopted(con, project, change, p['revision_id'])
    lease(con, project, change, run, p['lease_id'])
    task = task_row(con, p['revision_id'], p['task_id'])
    live_task(con, run, p['task_id'], p['step_id'])
    verification.ensure_conditions(store, con, project, change, run, p['revision_id'], task, 'execute', p.get('environment'))
    scope = loads(task['scope_paths_json'])
    require(isinstance(p['files'], list) and p['files'], 'FILES_REQUIRED', 'Provide explicit file changes', '/payload/files')
    files, names = [], set()
    for i, file in enumerate(p['files']):
        at = f'/payload/files/{i}'
        fields(file, FILE_CHANGE, at)
        resource = file.get('resource', 'main')
        action = file.get('action', 'write')
        require(action in {'write', 'delete'}, 'INVALID_ENUM', 'Expected write/delete', at+'/action')
        require(action == 'delete' or 'content' in file, 'MISSING_FIELD', 'Write requires content', at+'/content')
        require((resource, file['path']) not in names, 'DUPLICATE_PATH', 'One change per file in a batch', at+'/path')
        names.add((resource, file['path']))
        verification.authorize(con, project, change, run, 'edit_local', resource)
        patterns = [s['path'] for s in scope if s['resource'] == resource and s['access'] == 'write']
        require(execution.in_scope(file['path'], patterns), 'WRITE_SCOPE', 'File is outside the planned write scope', at+'/path', status='blocked')
        require(not any(part in {'.git', '.sdlc'} for part in Path(file['path']).parts), 'WRITE_SCOPE', 'Product writes cannot change runtime/Git internals', at+'/path')
        target = safe_path(store.resource(resource), file['path'])
        require(not target.exists() or target.is_file(), 'WRITE_SCOPE', 'Target is not a regular file', at+'/path')
        raw = file.get('content', '').encode()
        asset = store.put_asset(con, project, raw) if action == 'write' else None
        old = sha(target.read_bytes()) if target.is_file() else None
        files.append({'path': file['path'], 'resource': resource, 'action': action, 'asset_id': asset,
                      'before_sha256': old, 'after_sha256': sha(raw) if action == 'write' else None})
    intent = {'kind': 'task.write', 'revision_id': p['revision_id'], 'step_id': p['step_id'], 'files': files}
    atomic_write(work/'intent.json', canonical(intent)+b'\n')
    return intent


def apply_write(store, project, intent):
    prepared = []
    with store.read() as con:
        for file in intent['files']:
            target = safe_path(store.resource(file['resource']), file['path'])
            actual = sha(target.read_bytes()) if target.is_file() else None
            require(actual in {file['before_sha256'], file['after_sha256']}, 'WRITE_CONFLICT',
                    'Target changed outside this recorded operation; inspect before resuming', file['path'], status='conflict')
            raw = store.asset_bytes(con, file['asset_id'], project) if file['asset_id'] else None
            prepared.append((target, raw))
    for target, raw in prepared:
        if raw is None:
            target.unlink(missing_ok=True)
        else:
            atomic_write(target, raw)
    return {'written_files': [{'path': f['path'], 'sha256': f['after_sha256']} for f in intent['files']]}


def prepare_check(store, con, project, change, run, p, work):
    adopted(con, project, change, p['revision_id'])
    lease(con, project, change, run, p['lease_id'])
    verification.authorize(con, project, change, run, 'run_check', 'main')
    check = dict(one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (p['revision_id'], p['check_id']), code='CHECK_SCOPE'))
    require(check['executor'] == 'command', 'CHECK_EXECUTOR', 'Command execution requires a command Check', '/payload/check_id')
    require(loads(check['argv_json']) != ['@runtime', 'delivery.readback'], 'CHECK_ADAPTER', 'Use delivery.execute for native package readback', status='blocked')
    current = phase(con, project, change, run)
    require(current in {'IMP', 'VFY', 'RLS'}, 'PHASE_ORDER', 'Checks require an execution phase', status='blocked')
    writable = []
    if check['task_id']:
        task = task_row(con, p['revision_id'], check['task_id'])
        active = con.execute("SELECT 1 FROM steps WHERE run_id=? AND task_id=? AND step_key=? AND status='running'", (run, check['task_id'], 'task:'+check['task_id'])).fetchone()
        rerun = current == 'VFY' and check['purpose'] in {'acceptance', 'convergence'} and verification.task_completed(con, change, p['revision_id'], check['task_id'])
        require(active or rerun, 'TASK_NOT_RUNNING', 'Start the responsible task before its check', status='blocked')
        verification.ensure_conditions(store, con, project, change, run, p['revision_id'], task, 'execute', p.get('environment'))
        for scope in loads(task['scope_paths_json']):
            if scope['access'] == 'write':
                verification.authorize(con, project, change, run, 'edit_local', scope['resource'])
                writable.append((str(store.resource(scope['resource'])), scope['path']))
    else:
        require(check['purpose'] in {'convergence', 'acceptance', 'release_readback'}, 'CHECK_OWNER_REQUIRED', 'Precondition needs a responsible task', status='blocked')
    observed = verification.current_subject(store, con, p['revision_id'], check, p.get('environment'))
    snap = execution.snapshot(store, con, project, run, observed)
    step = new_step(con, project, change, run, p['revision_id'], current, 'check:'+check['check_id'], task=check['task_id'])
    intent = {'kind': 'check.run', 'revision_id': p['revision_id'], 'check_id': check['check_id'], 'step_id': step,
              'snapshot_id': snap, 'subject_digest': observed['digest'], 'environment_digest': observed['environment_digest'],
              'argv': loads(check['argv_json']), 'timeout_seconds': check['timeout_seconds'] or 60,
              'environment': p.get('environment', {}), 'writable': writable}
    atomic_write(work/'intent.json', canonical(intent)+b'\n')
    return intent


def finish_check(store, con, project, change, run, intent, evidence):
    check = one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (intent['revision_id'], intent['check_id']))
    current = verification.current_subject(store, con, intent['revision_id'], check, intent['environment'])
    if current['digest'] != intent['subject_digest'] or current['environment_digest'] != intent['environment_digest']:
        evidence = {**evidence, 'status': 'unknown', 'error_code': 'SUBJECT_CHANGED', 'summary': 'Subject changed during verification'}
    result = verification.record_result(store, con, project, change, run, intent['revision_id'], check, intent['step_id'], intent['snapshot_id'], evidence, source_kind='command')
    con.execute('UPDATE steps SET status=?,outcome=?,snapshot_id=?,finished_at=? WHERE step_id=?',
                ('blocked' if evidence['status'] == 'blocked' else 'completed', 'unknown' if evidence['status'] in {'unknown','blocked'} else evidence['status'], intent['snapshot_id'], now(), intent['step_id']))
    finding = None
    if evidence['status'] == 'fail' and check['purpose'] in {'acceptance', 'convergence'}:
        finding = verification.finding_from_result(con, project, change, intent['revision_id'], check, result,
                    check['description']+': actual check failed')
    return {'result_id': result, 'check_id': check['check_id'], 'snapshot_id': intent['snapshot_id'],
            'outcome': evidence['status'], 'exit_code': evidence.get('exit_code'), 'finding_id': finding,
            'error_code': evidence.get('error_code')}


def record_review(store, con, project, change, run, p):
    adopted(con, project, change, p['revision_id'])
    lease(con, project, change, run, p['lease_id'])
    check = one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (p['revision_id'], p['check_id']))
    require(check['executor'] == 'agent' and check['method'] != 'test', 'CHECK_EXECUTOR', 'Only actual Agent review is accepted here', '/payload/check_id')
    verification.authorize(con, project, change, run, 'run_check', 'main')
    current = phase(con, project, change, run)
    require(current in {'IMP', 'VFY', 'RLS'}, 'PHASE_ORDER', 'Reviews require an execution phase', status='blocked')
    if check['task_id']:
        task = task_row(con, p['revision_id'], check['task_id'])
        active = con.execute("SELECT 1 FROM steps WHERE run_id=? AND task_id=? AND step_key=? AND status='running'", (run, check['task_id'], 'task:'+check['task_id'])).fetchone()
        rerun = current == 'VFY' and check['purpose'] in {'acceptance', 'convergence'} and verification.task_completed(con, change, p['revision_id'], check['task_id'])
        require(active or rerun, 'TASK_NOT_RUNNING', 'Start the responsible task before its review', status='blocked')
        verification.ensure_conditions(store, con, project, change, run, p['revision_id'], task, 'execute', p.get('environment'))
    require(p['status'] in {'pass', 'fail'}, 'INVALID_ENUM', 'Review status is pass/fail', '/payload/status')
    observed = verification.current_subject(store, con, p['revision_id'], check, p.get('environment'))
    snap = execution.snapshot(store, con, project, run, observed)
    step = new_step(con, project, change, run, p['revision_id'], phase(con, project, change, run), 'review:'+check['check_id'])
    evidence = {'status': p['status'], 'summary': p['observations'], 'source_kind': 'agent',
                'actor_id': run_row(con, project, change, run)['actor_id'], 'review_kind': 'self_review'}
    result = verification.record_result(store, con, project, change, run, p['revision_id'], check, step, snap, evidence, source_kind='agent')
    con.execute("UPDATE steps SET status='completed',outcome=?,snapshot_id=?,finished_at=? WHERE step_id=?", (p['status'], snap, now(), step))
    findings = []
    for i, f in enumerate(p.get('findings', [])):
        fields(f, REVIEW_FINDING, f'/payload/findings/{i}')
        require(p['status'] == 'fail' or f['severity'] == 'advisory', 'REVIEW_CONTRADICTION', 'Blocking gap cannot accompany pass')
        findings.append(verification.finding_from_result(con, project, change, p['revision_id'], check, result,
                        f['description'], kind=f['kind'], severity=f['severity'], return_phase=f['return_phase'], criterion=f.get('criterion_id'), issue_key=f.get('issue_key')))
    return {'result_id': result, 'snapshot_id': snap, 'source_kind': 'agent', 'outcome': p['status'], 'finding_ids': findings}


def reuse_check(store, con, project, change, run, p):
    adopted(con, project, change, p['revision_id'])
    lease(con, project, change, run, p['lease_id'])
    verification.authorize(con, project, change, run, 'run_check', 'main')
    check = one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (p['revision_id'], p['check_id']), code='CHECK_SCOPE')
    subject = verification.current_subject(store, con, p['revision_id'], check, p.get('environment'))
    original = verification.applicable(con, change, p['revision_id'], check, subject)
    require(original and original['status'] == 'pass', 'REUSE_INAPPLICABLE', 'Execute an applicable check before reusing its evidence', status='blocked')
    if original['revision_id'] == p['revision_id'] and one(con, 'SELECT run_id FROM steps WHERE step_id=?', (original['step_id'],))['run_id'] == run:
        return {'result_id': original['result_id'], 'reused': False, 'outcome': 'pass'}
    step = new_step(con, project, change, run, p['revision_id'], phase(con, project, change, run), 'reuse:'+check['check_id'])
    value = verification.record_result(store, con, project, change, run, p['revision_id'], check, step, original['snapshot_id'],
        {'status': 'pass', 'summary': 'Applicable prior evidence reused; no new tool execution', 'original_result_id': original['result_id']},
        source_kind='reused', reused=original)
    con.execute("UPDATE steps SET status='completed',outcome='pass',snapshot_id=?,finished_at=? WHERE step_id=?", (original['snapshot_id'], now(), step))
    return {'result_id': value, 'reused_from_id': original['result_id'], 'reused': True, 'outcome': 'pass', 'observed_at': original['observed_at']}


def complete_phase(store, con, project, change, run, p):
    revision = p['revision_id']
    adopted(con, project, change, revision)
    lease(con, project, change, run, p.get('lease_id'))
    current = phase(con, project, change, run)
    require(current == p['phase'], 'PHASE_ORDER', 'Complete the current execution phase', '/payload/phase', status='blocked')
    if current == 'RLS':
        from .delivery import close
        return close(store, con, project, change, run, p)
    if current == 'IMP':
        pending = [r[0] for r in con.execute("SELECT task_id FROM tasks WHERE revision_id=? AND target_phase='IMP'", (revision,))
                   if not verification.task_completed(con, change, revision, r[0])]
        require(not pending, 'TASKS_PENDING', 'Complete the planned IMP tasks', status='blocked', details=pending)
        con.execute("UPDATE runs SET current_phase='VFY' WHERE run_id=?", (run,))
        step = new_step(con, project, change, run, revision, 'IMP', 'phase.complete:IMP')
        con.execute("UPDATE steps SET status='completed',outcome='not_applicable',finished_at=? WHERE step_id=?", (now(), step))
        return {'phase': 'IMP', 'next_actions': [{'action': 'phase.prepare', 'phase': 'VFY'}]}
    require(current == 'VFY', 'PHASE_ORDER', 'Expected verification phase', status='blocked')
    evaluation = verification.evaluate(store, con, project, change, revision, p.get('environment'))
    # Missing executions or still-running tasks do not consume a repair round.
    require(not evaluation['missing_checks'] and not evaluation['pending_tasks'], 'VERIFICATION_PENDING',
            'Execute the remaining tasks and checks before convergence', status='blocked', details=evaluation)
    require(not evaluation['unknown_operations'] and not any(r['status'] in {'unknown', 'blocked'} for r in evaluation['failed_checks']),
            'CHECK_INDETERMINATE', 'Reconcile unknown effects or restore the check environment before retrying verification', status='blocked', details=evaluation)
    step = new_step(con, project, change, run, revision, 'VFY', 'phase.complete:VFY')
    con.execute("UPDATE steps SET status='completed',outcome=?,finished_at=? WHERE step_id=?", ('pass' if evaluation['converged'] else 'fail', now(), step))
    if evaluation['converged']:
        con.execute("UPDATE runs SET current_phase='RLS',no_progress_rounds=0 WHERE run_id=?", (run,))
        return {**evaluation, 'next_actions': [{'action': 'phase.prepare', 'phase': 'RLS'}]}
    state = run_row(con, project, change, run)
    observed = execution.observe(store.root)
    fingerprint = digest({'code': observed['digest'], 'gaps': sorted(f['fingerprint'] for f in evaluation['blocking_findings']),
                          'failed_checks': [r['check_id'] for r in evaluation['failed_checks']]})
    stagnant = state['no_progress_rounds']+1 if fingerprint == state['last_progress_digest'] else 0
    rounds = state['repair_round']+1
    exhausted = rounds >= state['max_repair_rounds'] or stagnant >= state['no_progress_limit']
    earliest = min((f['return_phase'] for f in evaluation['blocking_findings']), key=lambda x: ['REQ','DSN','PLN','IMP','VFY','RLS'].index(x), default='IMP')
    con.execute('UPDATE runs SET current_phase=?,repair_round=?,no_progress_rounds=?,last_progress_digest=?,status=? WHERE run_id=?',
                (earliest, rounds, stagnant, fingerprint, 'blocked' if exhausted else 'running', run))
    return {**evaluation, 'control_status': 'blocked' if exhausted else 'needs_work',
            'error_code': 'REPAIR_BUDGET' if exhausted else 'GAPS_REMAIN', 'repair_round': rounds,
            'next_actions': [{'action': 'inspect' if exhausted else 'repair', 'phase': earliest,
                              'task_ids': sorted({f['task_id'] for f in evaluation['blocking_findings'] if f['task_id']})}]}


def finding_action(store, con, project, change, run, command, p):
    lease(con, project, change, run, p['lease_id'])
    finding = one(con, 'SELECT * FROM findings WHERE project_id=? AND change_id=? AND finding_id=?', (project, change, p['finding_id']), code='FINDING_SCOPE')
    if command == 'finding.address':
        require(finding['status'] == 'open', 'FINDING_STATE', 'Only an open finding can be addressed', status='blocked')
        con.execute("UPDATE findings SET status='addressed' WHERE finding_id=?", (p['finding_id'],))
        return {'finding_id': p['finding_id'], 'status': 'addressed', 'next_actions': [{'action': 'check.run', 'phase': 'VFY'}]}
    require(finding['status'] == 'addressed', 'FINDING_STATE', 'Record the repair before resolving', status='blocked')
    ch = content.change_row(con, project, change)
    original = one(con, 'SELECT * FROM check_results WHERE result_id=?', (finding['result_id'],))
    check = one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (ch['active_revision_id'], original['check_id']), code='CHECK_SCOPE')
    current = verification.current_subject(store, con, ch['active_revision_id'], check, p.get('environment'))
    result = verification.applicable(con, change, ch['active_revision_id'], check, current)
    require(result and result['result_id'] == p['result_id'] and result['status'] == 'pass' and result['observed_at'] > original['observed_at'],
            'RETEST_REQUIRED', 'Resolve only with a newer applicable passing recheck of the finding target', '/payload/result_id', status='blocked')
    con.execute("UPDATE findings SET status='resolved',resolution_result_id=? WHERE finding_id=?", (p['result_id'], p['finding_id']))
    return {'finding_id': p['finding_id'], 'status': 'resolved', 'resolution_result_id': p['result_id']}
