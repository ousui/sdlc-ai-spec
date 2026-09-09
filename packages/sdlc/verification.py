"""One applicability/convergence service for planning status and actual execution."""
from datetime import datetime, timedelta, timezone
from .common import PHASES, canonical, digest, loads, now, redact, require, uid
from .domain import task_fingerprint, validate_complete
from .execution import environment, observe
from .storage import CONTENT_TABLES, insert, one


def check_fingerprint(con, revision, check_id):
    check = dict(one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (revision, check_id)))
    check.pop('revision_id')
    criteria, requirements, sources = [], {}, {}
    for row in con.execute('SELECT c.* FROM criteria c JOIN check_criteria x USING(revision_id,criterion_id) WHERE x.revision_id=? AND x.check_id=?', (revision, check_id)):
        row = dict(row)
        row.pop('revision_id')
        row.pop('ordinal')
        criteria.append(row)
        for req in con.execute('SELECT q.* FROM requirements q JOIN criterion_requirements x USING(revision_id,requirement_id) WHERE x.revision_id=? AND x.criterion_id=?', (revision, row['criterion_id'])):
            req = dict(req)
            req.pop('revision_id')
            req.pop('ordinal')
            requirements[req['requirement_id']] = req
            for source in con.execute('SELECT s.* FROM sources s JOIN requirement_sources x USING(revision_id,source_id) WHERE x.revision_id=? AND x.requirement_id=?', (revision, req['requirement_id'])):
                source = dict(source)
                source.pop('revision_id')
                source.pop('ordinal')
                sources[source['source_id']] = source
    # Convergence inspects the entire scope, including changes with no criterion edge.
    if check['purpose'] == 'convergence':
        scope = {table: [{k: v for k, v in dict(r).items() if k not in {'revision_id', 'ordinal'}}
                         for r in con.execute(f'SELECT * FROM {table} WHERE revision_id=? ORDER BY rowid', (revision,))]
                 for table in CONTENT_TABLES}
        for table in scope:
            scope[table].sort(key=canonical)
    else:
        scope = {'criteria': sorted(criteria, key=canonical), 'requirements': sorted(requirements.values(), key=canonical),
                 'sources': sorted(sources.values(), key=canonical)}
        scope['criterion_requirements'] = sorted([dict(r) | {'revision_id': None} for r in con.execute(
            'SELECT x.* FROM criterion_requirements x JOIN check_criteria c USING(revision_id,criterion_id) WHERE c.revision_id=? AND c.check_id=?',
            (revision, check_id))], key=canonical)
    owner = task_fingerprint(con, revision, check['task_id']) if check['task_id'] else None
    context = one(con, 'SELECT c.digest FROM contexts c JOIN revisions r USING(context_id) WHERE r.revision_id=?', (revision,))['digest']
    return digest({'check': check, 'scope': scope, 'owner': owner, 'context': context})


def task_completed(con, change, revision, task):
    definition = task_fingerprint(con, revision, task)
    row = con.execute("SELECT * FROM steps WHERE change_id=? AND task_id=? AND step_key=? ORDER BY started_at DESC,attempt DESC LIMIT 1",
                      (change, task, 'task:'+task)).fetchone()
    # Completion is a historical work fact. Only checks claim PASS on the current code.
    return bool(row and row['status'] == 'completed' and row['definition_digest'] == definition)


def check_scope(con, revision, check):
    # Write permissions are not the input/dependency closure of a check.
    return loads(check['input_paths_json']) or [{'resource': 'main', 'path': '.', 'access': 'read'}]


def current_subject(store, con, revision, check, overrides=None):
    argv = loads(check['argv_json']) if check['argv_json'] else None
    groups = {}
    for scope in check_scope(con, revision, check):
        groups.setdefault(scope['resource'], []).append(scope['path'])
    observations = {resource: observe(store.resource(resource), paths, environment(overrides), argv) for resource, paths in groups.items()}
    main = observations.get('main') or next(iter(observations.values()))
    files = sorted([{**f, 'resource': resource} for resource, item in observations.items() for f in item['files']], key=canonical)
    return {**main, 'files': files, 'digest': digest(files)}


def applicable(con, change, revision, check, subject):
    definition = check_fingerprint(con, revision, check['check_id'])
    for row in con.execute('SELECT r.*,s.digest AS code_digest,s.environment_digest FROM check_results r JOIN code_snapshots s USING(snapshot_id) WHERE r.change_id=? AND r.check_id=? ORDER BY r.observed_at DESC,r.rowid DESC', (change, check['check_id'])):
        if row['definition_digest'] != definition or row['code_digest'] != subject['digest'] or row['environment_digest'] != subject['environment_digest']:
            continue
        if row['expires_at'] and row['expires_at'] <= now():
            return None
        if check['executor'] == 'command' and row['source_kind'] not in {'command', 'reused'}:
            continue
        return dict(row)
    return None


def authorize(con, project, change, run, action, target):
    actor = one(con, 'SELECT actor_id,workspace_id FROM runs WHERE project_id=? AND change_id=? AND run_id=?', (project, change, run))
    row = con.execute("SELECT 1 FROM authorizations WHERE origin_kind='local' AND project_id=? AND change_id=? AND workspace_id=? AND actor_id=? AND action=? AND target=? AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at>?)",
                      (project, change, actor['workspace_id'], actor['actor_id'], action, target, now())).fetchone()
    require(row, 'AUTHORIZATION_REQUIRED', 'Action requires the recorded actor/action/target authorization',
            '/payload', status='blocked', details={'action': action, 'target': target})


def task_conditions(store, con, project, change, run, revision, task, moment, overrides=None):
    blockers = []
    if moment == 'start':
        for row in con.execute('SELECT * FROM task_dependencies WHERE revision_id=? AND task_id=?', (revision, task['task_id'])):
            if not task_completed(con, change, revision, row['predecessor_id']):
                blockers.append({'code': 'PREDECESSOR_PENDING', 'task_id': row['predecessor_id']})
    for row in con.execute('SELECT p.condition_id,c.* FROM preconditions p JOIN checks c USING(revision_id,check_id) WHERE p.revision_id=? AND p.consumer_task_id=? AND p.enforce_at=?', (revision, task['task_id'], moment)):
        subject = current_subject(store, con, revision, row, overrides)
        result = applicable(con, change, revision, row, subject)
        if not result or result['status'] != 'pass':
            blockers.append({'code': 'CONDITION_UNSATISFIED', 'condition_id': row['condition_id'], 'check_id': row['check_id'],
                             'result_id': result['result_id'] if result else None, 'observed_status': result['status'] if result else 'missing'})
    return blockers


def ensure_conditions(*args, **kwargs):
    blockers = task_conditions(*args, **kwargs)
    require(not blockers, 'TASK_BLOCKED', 'Required execution conditions are not satisfied', status='blocked', details=blockers)


def record_result(store, con, project, change, run, revision, check, step, snapshot_id, evidence, *, source_kind, reused=None):
    value = uid()
    asset = store.put_asset(con, project, canonical(redact(evidence)), 'application/json')
    observed = now()
    expires = None
    if check['max_age_seconds'] is not None:
        expires = (datetime.now(timezone.utc)+timedelta(seconds=check['max_age_seconds'])).isoformat(timespec='microseconds').replace('+00:00', 'Z')
    if reused:
        observed, expires = reused['observed_at'], reused['expires_at']
    insert(con, 'check_results', {'result_id': value, 'project_id': project, 'change_id': change, 'revision_id': revision,
           'check_id': check['check_id'], 'step_id': step, 'snapshot_id': snapshot_id, 'status': evidence['status'],
           'evidence_asset_id': asset, 'source_kind': source_kind, 'observed_at': observed, 'expires_at': expires,
           'reused_from_id': reused['result_id'] if reused else None,
           'definition_digest': check_fingerprint(con, revision, check['check_id']),
           'summary': redact(evidence.get('summary') or ('Actual exit '+str(evidence.get('exit_code'))))})
    return value


def finding_from_result(con, project, change, revision, check, result, description, *, kind='partial', severity='blocking', return_phase='IMP', criterion=None, issue_key=None):
    require(kind in {'missing', 'partial', 'contradicts', 'unrequested', 'environment'}, 'INVALID_ENUM', 'Invalid finding kind')
    require(severity in {'blocking', 'advisory'} and return_phase in PHASES, 'INVALID_ENUM', 'Invalid finding disposition')
    if criterion:
        one(con, 'SELECT 1 FROM check_criteria WHERE revision_id=? AND check_id=? AND criterion_id=?', (revision, check['check_id'], criterion), code='FINDING_SCOPE')
    fingerprint = digest({'check_id': check['check_id'], 'criterion_id': criterion, 'kind': kind,
                          'return_phase': return_phase, 'issue': issue_key or description.strip()})
    existing = con.execute('SELECT finding_id FROM findings WHERE change_id=? AND fingerprint=?', (change, fingerprint)).fetchone()
    if existing:
        con.execute("UPDATE findings SET status='open',result_id=?,resolution_result_id=NULL,description=?,severity=CASE WHEN severity='blocking' OR ?='blocking' THEN 'blocking' ELSE 'advisory' END WHERE finding_id=?", (result, redact(description), severity, existing[0]))
        return existing[0]
    value = uid()
    insert(con, 'findings', {'finding_id': value, 'project_id': project, 'change_id': change, 'revision_id': revision,
           'result_id': result, 'criterion_id': criterion, 'task_id': check['task_id'], 'return_phase': return_phase,
           'kind': kind, 'severity': severity, 'status': 'open', 'fingerprint': fingerprint, 'description': redact(description)})
    return value


def evaluate(store, con, project, change, revision, overrides=None):
    validate_complete(con, revision, 'VFY')
    checks, missing, failed = [], [], []
    for check in con.execute("SELECT * FROM checks WHERE revision_id=? AND required=1 AND purpose<>'release_readback' ORDER BY check_id", (revision,)):
        subject = current_subject(store, con, revision, check, overrides)
        result = applicable(con, change, revision, check, subject)
        row = {'check_id': check['check_id'], 'purpose': check['purpose'], 'executor': check['executor'],
               'result_id': result['result_id'] if result else None, 'status': result['status'] if result else 'missing'}
        checks.append(row)
        if result is None:
            missing.append(row)
        elif result['status'] != 'pass':
            failed.append(row)
    pending = [r['task_id'] for r in con.execute("SELECT * FROM tasks WHERE revision_id=? AND target_phase<>'RLS'", (revision,))
               if not task_completed(con, change, revision, r['task_id'])]
    findings = [dict(r) for r in con.execute("SELECT * FROM findings WHERE project_id=? AND change_id=? AND severity='blocking' AND status IN ('open','addressed')", (project, change))]
    unknown = [r[0] for r in con.execute("SELECT o.operation_id FROM operations o JOIN runs r USING(run_id) WHERE r.change_id=? AND r.workspace_id=? AND r.origin_kind='local' AND o.origin_kind='local' AND o.status='unknown'", (change, store.config()['workspace_id']))]
    return {'converged': not (missing or failed or pending or findings or unknown), 'checks': checks,
            'missing_checks': missing, 'failed_checks': failed, 'pending_tasks': pending, 'blocking_findings': findings,
            'unknown_operations': unknown}
