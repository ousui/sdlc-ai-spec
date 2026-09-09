"""Single producer/consumer contract for all six phases."""
from __future__ import annotations

from pathlib import PurePosixPath
from .common import PHASES, Fault, canonical, digest, ident, require, uid
from .storage import CONTENT_TABLES, ENTITY_IDS, insert, one

# A descriptor is both the input validator and the source for machine schemas.
# SQL owns nullability, primitive enum checks and exact same-revision foreign keys.
FIELDS = {
    'source': ('sources', {'kind': 'str', 'original_text': 'str', 'origin_uri': 'str?', 'observed_at': 'str?', 'ordinal': 'int?'}),
    'requirement': ('requirements', {'kind': 'str', 'statement': 'str', 'ordinal': 'int?', 'sources': 'refs?'}),
    'criterion': ('criteria', {'condition_text': 'str', 'expected_result': 'str', 'ordinal': 'int?', 'requirements': 'refs?'}),
    'design': ('designs', {'domain': 'str', 'title': 'str', 'decision': 'str', 'rationale': 'str', 'alternatives': 'str', 'detail': 'str', 'ordinal': 'int?', 'requirements': 'refs?'}),
    'task': ('tasks', {'target_phase': 'str', 'kind': 'str', 'title': 'str', 'description': 'str', 'completion_text': 'str', 'scope_paths': 'paths', 'ordinal': 'int?', 'designs': 'refs?', 'criteria': 'refs?'}),
    'check': ('checks', {'task': 'ref?', 'purpose': 'str', 'method': 'str', 'executor': 'str', 'description': 'str', 'expected_result': 'str', 'argv': 'argv?', 'input_paths': 'paths?', 'required': 'bool', 'timeout_seconds': 'positive?', 'max_age_seconds': 'nonnegative?', 'criteria': 'refs?'}),
    'precondition': ('preconditions', {'consumer_task': 'ref', 'check': 'ref', 'producer_task': 'ref?', 'enforce_at': 'str', 'reason': 'str'}),
}
RELATIONS = {
    'link_requirement_source': ('requirement_sources', {'requirement': 'requirement_id', 'source': 'source_id'}),
    'link_criterion_requirement': ('criterion_requirements', {'criterion': 'criterion_id', 'requirement': 'requirement_id'}),
    'link_design_requirement': ('design_requirements', {'design': 'design_id', 'requirement': 'requirement_id'}),
    'link_task_design': ('task_designs', {'task': 'task_id', 'design': 'design_id'}),
    'link_task_criterion': ('task_criteria', {'task': 'task_id', 'criterion': 'criterion_id'}),
    'link_check_criterion': ('check_criteria', {'check': 'check_id', 'criterion': 'criterion_id'}),
    'add_task_dependency': ('task_dependencies', {'task': 'task_id', 'predecessor': 'predecessor_id', 'reason': 'text'}),
}
REL_INLINE = {
    ('requirement', 'sources'): ('requirement_sources', 'requirement_id', 'source_id'),
    ('criterion', 'requirements'): ('criterion_requirements', 'criterion_id', 'requirement_id'),
    ('design', 'requirements'): ('design_requirements', 'design_id', 'requirement_id'),
    ('task', 'designs'): ('task_designs', 'task_id', 'design_id'),
    ('task', 'criteria'): ('task_criteria', 'task_id', 'criterion_id'),
    ('check', 'criteria'): ('check_criteria', 'check_id', 'criterion_id'),
}
STAGE_TABLES = {
    'REQ': {'sources', 'requirements', 'criteria', 'requirement_sources', 'criterion_requirements'},
    'DSN': {'designs', 'design_requirements', 'checks', 'check_criteria'},
    'PLN': {'tasks', 'task_designs', 'task_criteria', 'task_dependencies', 'checks', 'check_criteria', 'preconditions'},
}


ENUMS = {
    ('source', 'kind'): ('text', 'document', 'image', 'observation', 'assumption'),
    ('requirement', 'kind'): ('behavior', 'rule', 'quality', 'constraint'),
    ('task', 'target_phase'): ('IMP', 'VFY', 'RLS'),
    ('task', 'kind'): ('prepare', 'implement', 'verify', 'review', 'deliver'),
    ('check', 'purpose'): ('acceptance', 'precondition', 'convergence', 'release_readback'),
    ('check', 'method'): ('test', 'inspection', 'analysis', 'demonstration'),
    ('check', 'executor'): ('command', 'agent', 'human'),
    ('precondition', 'enforce_at'): ('start', 'execute', 'complete'),
}
NULLABLE = {
    'source': {'origin_uri', 'observed_at'},
    'check': {'task', 'argv', 'timeout_seconds', 'max_age_seconds'},
    'precondition': {'producer_task'},
}
REF_TABLES = {**{k: v[0] for k, v in FIELDS.items()},
              'consumer_task': 'tasks', 'producer_task': 'tasks', 'predecessor': 'tasks'}


def pointer(path, key):
    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')


def value_type(value, kind, path):
    if kind == 'text':
        require(isinstance(value, str), 'INVALID_TYPE', 'Expected text', path)
    elif kind == 'str':
        require(isinstance(value, str) and bool(value.strip()), 'INVALID_TYPE', 'Expected non-empty text', path)
    elif kind == 'int':
        require(type(value) is int, 'INVALID_TYPE', 'Expected integer', path)
    elif kind in {'positive', 'nonnegative'}:
        require(type(value) is int and value >= (1 if kind == 'positive' else 0), 'INVALID_TYPE', 'Expected bounded integer', path)
    elif kind == 'bool':
        require(type(value) is bool, 'INVALID_TYPE', 'Expected boolean', path)
    elif kind == 'id':
        ident(value, path)
    elif kind == 'ref':
        require(isinstance(value, dict) and len(value) == 1 and next(iter(value)) in {'id', 'client_key'},
                'INVALID_REFERENCE', 'Use {id: UUID} or {client_key: batch key}', path)
        key = next(iter(value))
        value_type(value[key], 'id' if key == 'id' else 'str', pointer(path, key))
    elif kind == 'refs':
        require(isinstance(value, list), 'INVALID_TYPE', 'Expected reference array', path)
        for i, ref in enumerate(value):
            value_type(ref, 'ref', pointer(path, i))
        require(len({canonical(ref) for ref in value}) == len(value), 'DUPLICATE_REFERENCE', 'Duplicate reference', path)
    elif kind == 'argv':
        require(isinstance(value, list) and value and isinstance(value[0], str) and value[0].strip(),
                'INVALID_ARGV', 'Command is a nonempty string array', path)
        for i, arg in enumerate(value):
            require(isinstance(arg, str) and '\x00' not in arg, 'INVALID_ARGV', 'Expected argument string without NUL', pointer(path, i))
    elif kind == 'paths':
        require(isinstance(value, list) and value, 'INVALID_SCOPE', 'Expected nonempty scope array', path)
        for i, item in enumerate(value):
            p = pointer(path, i)
            fields(item, {'resource': 'str', 'path': 'str', 'access': 'str'}, p)
            name = item['path']
            require(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and '\\' not in name and '\x00' not in name,
                    'UNSAFE_PATH', 'Scope must be relative to its resource', p+'/path')
            require(item['access'] in {'read', 'write'}, 'INVALID_SCOPE', 'Use read or write', p+'/access')
    elif kind in {'object', 'array'}:
        require(isinstance(value, dict if kind == 'object' else list), 'INVALID_TYPE', 'Expected '+kind, path)
    else:
        raise RuntimeError('Unknown schema descriptor: '+kind)


def fields(obj, definitions, path='', *, partial=False, nullable=()):
    require(isinstance(obj, dict), 'INVALID_TYPE', 'Expected object', path)
    extras = sorted(set(obj) - set(definitions))
    require(not extras, 'UNKNOWN_FIELD', 'Unknown field(s): '+', '.join(extras), pointer(path, extras[0]) if extras else path)
    for key, spec in definitions.items():
        p = pointer(path, key)
        if key not in obj:
            require(partial or spec.endswith('?'), 'MISSING_FIELD', key+' is required', p)
        elif obj[key] is not None or key not in nullable:
            value_type(obj[key], spec.rstrip('?'), p)


def batch(con, revision, phase, operations):
    """Validate/resolve a complete batch before applying its atomic savepoint."""
    require(phase in STAGE_TABLES, 'PHASE_OWNERSHIP', 'Revise the owning content phase', '/payload/phase')
    require(isinstance(operations, list), 'INVALID_TYPE', 'Expected operation array', '/payload/operations')
    require(len(operations) <= 1000, 'BATCH_LIMIT', 'Batch exceeds 1000 operations', '/payload/operations')
    rev = one(con, 'SELECT * FROM revisions WHERE revision_id=?', (revision,))
    require(rev['state'] == 'draft', 'IMMUTABLE_REVISION', 'Create a child revision before editing', '/payload/revision_id')
    keys, allocated, origins = {}, {}, {}
    for i, op in enumerate(operations):
        p = f'/payload/operations/{i}'
        require(isinstance(op, dict) and isinstance(op.get('op'), str), 'INVALID_OPERATION', 'Expected named operation', p)
        verb, _, kind = op['op'].partition('_')
        if verb in {'create', 'update'} and kind in FIELDS:
            table, definitions = FIELDS[kind]
            fields(op, {'op': 'str', **({'client_key': 'str?'} if verb == 'create' else {'id': 'id'}), **definitions},
                   p, partial=verb == 'update', nullable=NULLABLE.get(kind, ()))
            if verb == 'update':
                require('id' in op, 'MISSING_FIELD', 'id is required', p+'/id')
            for (entity, field), values in ENUMS.items():
                if entity == kind and field in op:
                    require(op[field] in values, 'INVALID_ENUM', 'Expected one of '+', '.join(values), p+'/'+field)
            if 'ordinal' in op:
                require(op['ordinal'] >= 0, 'INVALID_TYPE', 'Ordinal must be nonnegative', p+'/ordinal')
            if verb == 'create':
                allocated[i] = uid()
                if 'client_key' in op:
                    require(op['client_key'] not in keys, 'DUPLICATE_CLIENT_KEY', 'Batch keys must be unique', p+'/client_key')
                    keys[op['client_key']] = (allocated[i], table)
            origins[(table, allocated[i] if verb == 'create' else op['id'])] = p
        elif op['op'] in RELATIONS:
            table, columns = RELATIONS[op['op']]
            fields(op, {'op': 'str', **{k: 'str' if v == 'text' else 'ref' for k, v in columns.items()}}, p)
        else:
            raise Fault('UNKNOWN_OPERATION', 'Unsupported domain operation: '+op['op'], p+'/op')
        require(table in STAGE_TABLES[phase], 'PHASE_OWNERSHIP', table+' belongs to another phase', p)

    def ref(obj, table, path):
        if obj is None:
            return None
        if 'client_key' in obj:
            require(obj['client_key'] in keys, 'UNKNOWN_CLIENT_KEY', 'No such key in this batch', path+'/client_key')
            value, actual = keys[obj['client_key']]
            require(actual == table, 'REFERENCE_TYPE', 'Reference must identify '+table, path)
            return value
        value = obj['id']
        require(con.execute(f'SELECT 1 FROM {table} WHERE revision_id=? AND {ENTITY_IDS[table]}=?', (revision, value)).fetchone(),
                'REFERENCE_SCOPE', 'Reference is absent from the exact revision or has a different entity type', path+'/id')
        return value

    rows, relations, updates, clears = [], [], [], []
    for i, op in enumerate(operations):
        p = f'/payload/operations/{i}'
        verb, _, kind = op['op'].partition('_')
        if op['op'] in RELATIONS:
            table, columns = RELATIONS[op['op']]
            row = {'revision_id': revision}
            for key, column in columns.items():
                row['reason' if column == 'text' else column] = op[key] if column == 'text' else ref(op[key], REF_TABLES[key], p+'/'+key)
            relations.append((table, row, p))
            if table == 'task_dependencies':
                require(row['task_id'] != row['predecessor_id'], 'TASK_SELF_DEPENDENCY', 'A task cannot depend on itself', p+'/predecessor')
                origins[(table, row['task_id'], row['predecessor_id'])] = p
            continue
        table, definitions = FIELDS[kind]
        idcol = ENTITY_IDS[table]
        value = allocated[i] if verb == 'create' else op['id']
        row = {'revision_id': revision, idcol: value}
        if verb == 'update':
            require(con.execute(f'SELECT 1 FROM {table} WHERE revision_id=? AND {idcol}=?', (revision, value)).fetchone(),
                    'REFERENCE_SCOPE', 'Updated object is absent from this exact revision', p+'/id')
        for key in definitions:
            if key not in op:
                continue
            v = op[key]
            if (kind, key) in REL_INLINE:
                rel, left, right = REL_INLINE[kind, key]
                if verb == 'update':
                    clears.append((rel, left, value))
                target_table = next(t for t, col in ENTITY_IDS.items() if col == right)
                for j, obj in enumerate(v):
                    relations.append((rel, {'revision_id': revision, left: value, right: ref(obj, target_table, f'{p}/{key}/{j}')}, p+'/'+key))
            elif key in {'task', 'consumer_task', 'producer_task', 'check'}:
                row[key+'_id'] = ref(v, REF_TABLES[key], p+'/'+key)
            elif key in {'argv', 'scope_paths', 'input_paths'}:
                if key == 'input_paths':
                    require(all(item['access'] == 'read' for item in v), 'CHECK_INPUT_SCOPE', 'Check input paths describe read dependencies', p+'/'+key)
                row[key+'_json'] = canonical(v).decode() if v is not None else None
            elif key == 'required':
                row[key] = int(v)
            else:
                row[key] = v
        if verb == 'create':
            if 'ordinal' in definitions:
                row.setdefault('ordinal', con.execute(f'SELECT count(*) FROM {table} WHERE revision_id=?', (revision,)).fetchone()[0] + i)
            if kind == 'check':
                row.setdefault('task_id', None)
                row.setdefault('argv_json', None)
                row.setdefault('timeout_seconds', 60)
                row.setdefault('max_age_seconds', None)
            if kind == 'precondition':
                row.setdefault('producer_task_id', None)
            rows.append((table, row, p))
        else:
            updates.append((table, row, p))

    order = {table: i for i, table in enumerate(CONTENT_TABLES)}
    con.execute('SAVEPOINT domain_batch')
    try:
        for table, row, p in sorted(rows, key=lambda item: order[item[0]]):
            if table == 'preconditions':
                continue
            if table == 'checks':
                validate_check(row, p)
            insert(con, table, row)
        for table, row, p in updates:
            idcol = ENTITY_IDS[table]
            if table == 'checks':
                old = dict(one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (revision, row[idcol])))
                validate_check({**old, **row}, p)
            if table == 'preconditions':
                old = dict(one(con, 'SELECT * FROM preconditions WHERE revision_id=? AND condition_id=?', (revision, row[idcol])))
                validate_precondition(con, {**old, **row}, p)
            changes = {k: v for k, v in row.items() if k not in {'revision_id', idcol}}
            if changes:
                con.execute(f'UPDATE {table} SET '+','.join(k+'=?' for k in changes)+f' WHERE revision_id=? AND {idcol}=?',
                            (*changes.values(), revision, row[idcol]))
        for table, row, p in rows:
            if table == 'preconditions':
                validate_precondition(con, row, p)
                insert(con, table, row)
        for table, left, value in clears:
            con.execute(f'DELETE FROM {table} WHERE revision_id=? AND {left}=?', (revision, value))
        for table, row, p in relations:
            columns = tuple(row)
            duplicate = con.execute(f'SELECT 1 FROM {table} WHERE '+' AND '.join(k+'=?' for k in columns), tuple(row.values())).fetchone()
            if not duplicate:
                insert(con, table, row)
        validate_graph(con, revision, origins)
    except BaseException:
        con.execute('ROLLBACK TO domain_batch')
        con.execute('RELEASE domain_batch')
        raise
    con.execute('RELEASE domain_batch')
    return {key: value for key, (value, table) in keys.items()}


def validate_check(row, path):
    command = row['executor'] == 'command'
    require(command == (row.get('argv_json') is not None), 'CHECK_EXECUTOR',
            'Only command checks require argv', path+'/argv')
    require(row['method'] != 'test' or command, 'CHECK_EXECUTOR',
            'Test requires actual command execution; use inspection/analysis for an Agent review', path+'/executor')


def validate_precondition(con, row, path):
    check = one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?',
                (row['revision_id'], row['check_id']))
    producer = row.get('producer_task_id') or check['task_id']
    require(not row.get('producer_task_id') or row['producer_task_id'] == check['task_id'],
            'CHECK_PRODUCER', 'Producer must own the check execution', path+'/producer_task')
    require(producer != row['consumer_task_id'] or row['enforce_at'] == 'complete',
            'TASK_SELF_DEPENDENCY', 'A task cannot wait on its own future output', path+'/enforce_at')


def dependency_graph(con, revision, origins=None):
    """Event DAG: start -> execute -> complete. Checks are produced during execute."""
    origins = origins or {}
    tasks = {r['task_id']: dict(r) for r in con.execute('SELECT * FROM tasks WHERE revision_id=?', (revision,))}
    graph = {(t, event): [] for t in tasks for event in ('start', 'execute', 'complete')}
    for t in tasks:
        graph[t, 'execute'].append((t, 'start'))
        graph[t, 'complete'].append((t, 'execute'))

    def edge(consumer, moment, producer, produced_at, path):
        require(PHASES.index(tasks[producer]['target_phase']) <= PHASES.index(tasks[consumer]['target_phase']),
                'DEPENDENCY_PHASE_ORDER', 'A task cannot depend on a later lifecycle phase', path)
        if consumer == producer:
            require(moment == 'complete' and produced_at == 'execute', 'TASK_SELF_DEPENDENCY',
                    'A task cannot wait on its own future output', path)
        graph[consumer, moment].append((producer, produced_at))

    for row in con.execute('SELECT * FROM task_dependencies WHERE revision_id=?', (revision,)):
        p = origins.get(('task_dependencies', row['task_id'], row['predecessor_id']), '/task_dependencies')
        edge(row['task_id'], 'start', row['predecessor_id'], 'complete', p)
    for row in con.execute('SELECT p.*,c.task_id AS check_task FROM preconditions p JOIN checks c USING(revision_id,check_id) WHERE p.revision_id=?', (revision,)):
        p = origins.get(('preconditions', row['condition_id']), '/preconditions/'+row['condition_id'])
        producer = row['producer_task_id'] or row['check_task']
        require(not row['producer_task_id'] or row['producer_task_id'] == row['check_task'],
                'CHECK_PRODUCER', 'Producer must own the check execution', p+'/producer_task')
        if producer:
            edge(row['consumer_task_id'], row['enforce_at'], producer, 'execute', p+'/enforce_at')
    return graph


def validate_graph(con, revision, origins=None):
    graph = dependency_graph(con, revision, origins)
    # Kahn traversal avoids recursion limits for large, legal plans.
    remaining = {node: set(parents) for node, parents in graph.items()}
    ready = [node for node, parents in remaining.items() if not parents]
    dependants = {node: [] for node in graph}
    for node, parents in remaining.items():
        for parent in parents:
            dependants[parent].append(node)
    done = set()
    while ready:
        node = ready.pop()
        done.add(node)
        for child in dependants[node]:
            remaining[child].discard(node)
            if not remaining[child]:
                ready.append(child)
    require(len(done) == len(graph), 'DEPENDENCY_CYCLE', 'Execution dependency cycle', '/payload/operations',
            details={'events': [list(node) for node in graph if node not in done]})


def validate_complete(con, revision, phase):
    problems=[]
    def missing(table,idcol,relation,condition=''):
        rows=con.execute(f'SELECT a.{idcol} FROM {table} a WHERE a.revision_id=? AND NOT EXISTS (SELECT 1 FROM {relation} r WHERE r.revision_id=a.revision_id AND r.{idcol}=a.{idcol} {condition})',(revision,))
        problems.extend({'code':'COVERAGE_MISSING','table':table,'id':r[0],'relationship':relation} for r in rows)
    for table in ('sources','requirements','criteria'):
        if not con.execute(f'SELECT 1 FROM {table} WHERE revision_id=?',(revision,)).fetchone():problems.append({'code':'CONTENT_REQUIRED','table':table})
    missing('requirements','requirement_id','requirement_sources')
    missing('requirements','requirement_id','criterion_requirements')
    missing('criteria','criterion_id','criterion_requirements')
    if PHASES.index(phase)>=1:
        missing('requirements','requirement_id','design_requirements')
        missing('criteria','criterion_id','check_criteria',"AND EXISTS (SELECT 1 FROM checks k WHERE k.revision_id=r.revision_id AND k.check_id=r.check_id AND k.required=1 AND k.purpose='acceptance')")
        if not con.execute("SELECT 1 FROM checks WHERE revision_id=? AND purpose='convergence' AND required=1",(revision,)).fetchone():problems.append({'code':'CONVERGENCE_CHECK_REQUIRED','table':'checks'})
    if PHASES.index(phase)>=2:
        missing('designs','design_id','task_designs')
        missing('criteria','criterion_id','task_criteria')
        if not con.execute('SELECT 1 FROM tasks WHERE revision_id=?',(revision,)).fetchone():problems.append({'code':'TASKS_REQUIRED','table':'tasks'})
    validate_graph(con,revision)
    require(not problems,'PHASE_INCOMPLETE','Complete the listed coverage/content before advancing',status='blocked',details=problems)


def task_fingerprint(con, revision, task_id, seen=None):
    """Fingerprint the relation closure as a set, including legal completion checks."""
    selected, pending = set(), [task_id]
    while pending:
        task = pending.pop()
        if task in selected:
            continue
        selected.add(task)
        pending.extend(r[0] for r in con.execute('SELECT predecessor_id FROM task_dependencies WHERE revision_id=? AND task_id=?', (revision, task)))
        pending.extend(r[0] for r in con.execute('SELECT coalesce(p.producer_task_id,c.task_id) FROM preconditions p JOIN checks c USING(revision_id,check_id) WHERE p.revision_id=? AND p.consumer_task_id=?', (revision, task)) if r[0])
    content = {table: [] for table in CONTENT_TABLES}
    ids = {'tasks': selected, 'designs': set(), 'criteria': set(), 'requirements': set(), 'sources': set(), 'checks': set()}
    for task in selected:
        ids['designs'].update(r[0] for r in con.execute('SELECT design_id FROM task_designs WHERE revision_id=? AND task_id=?', (revision, task)))
        ids['criteria'].update(r[0] for r in con.execute('SELECT criterion_id FROM task_criteria WHERE revision_id=? AND task_id=?', (revision, task)))
        ids['checks'].update(r[0] for r in con.execute('SELECT check_id FROM checks WHERE revision_id=? AND task_id=? UNION SELECT check_id FROM preconditions WHERE revision_id=? AND consumer_task_id=?', (revision, task, revision, task)))
    for table, relation, idcol in (('designs', 'design_requirements', 'design_id'), ('criteria', 'criterion_requirements', 'criterion_id')):
        for value in ids[table]:
            ids['requirements'].update(r[0] for r in con.execute(f'SELECT requirement_id FROM {relation} WHERE revision_id=? AND {idcol}=?', (revision, value)))
    for value in ids['requirements']:
        ids['sources'].update(r[0] for r in con.execute('SELECT source_id FROM requirement_sources WHERE revision_id=? AND requirement_id=?', (revision, value)))
    for table in CONTENT_TABLES:
        for record in con.execute(f'SELECT * FROM {table} WHERE revision_id=?', (revision,)):
            row = dict(record)
            # Include only relations whose endpoints belong to this closure.
            refs = [(key, value) for key, value in row.items() if key.endswith('_id') and key not in {'revision_id', 'condition_id'} and value]
            def selected_ref(key, value):
                if key in {'consumer_task_id', 'producer_task_id', 'predecessor_id'}:
                    return value in selected
                target = next((t for t, col in ENTITY_IDS.items() if col == key), None)
                return target in ids and value in ids[target]
            if refs and all(selected_ref(key, value) for key, value in refs):
                row.pop('revision_id')
                row.pop('ordinal', None)
                content[table].append(row)
        content[table].sort(key=canonical)
    return digest(content)
