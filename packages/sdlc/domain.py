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
    'check': ('checks', {'task': 'ref?', 'purpose': 'str', 'method': 'str', 'executor': 'str', 'description': 'str', 'expected_result': 'str', 'argv': 'argv?', 'required': 'bool', 'timeout_seconds': 'positive?', 'max_age_seconds': 'nonnegative?', 'criteria': 'refs?'}),
    'precondition': ('preconditions', {'consumer_task': 'ref', 'check': 'ref', 'producer_task': 'ref?', 'enforce_at': 'str', 'reason': 'str'}),
}
RELATIONS = {
    'link_requirement_source': ('requirement_sources', {'requirement': 'requirement_id', 'source': 'source_id'}),
    'link_criterion_requirement': ('criterion_requirements', {'criterion': 'criterion_id', 'requirement': 'requirement_id'}),
    'link_design_requirement': ('design_requirements', {'design': 'design_id', 'requirement': 'requirement_id'}),
    'link_task_design': ('task_designs', {'task': 'task_id', 'design': 'design_id'}),
    'link_task_criterion': ('task_criteria', {'task': 'task_id', 'criterion': 'criterion_id'}),
    'link_check_criterion': ('check_criteria', {'check': 'check_id', 'criterion': 'criterion_id'}),
    'add_dependency': ('task_dependencies', {'task': 'task_id', 'predecessor': 'predecessor_id', 'reason': 'text'}),
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


def fields(obj, definitions, path=''):
    require(isinstance(obj, dict), 'INVALID_TYPE', 'Expected object', path)
    extras = set(obj) - set(definitions)
    require(not extras, 'UNKNOWN_FIELD', 'Unknown field(s): ' + ', '.join(sorted(extras)), path)
    for key, spec in definitions.items():
        optional = spec.endswith('?'); kind = spec.rstrip('?'); value = obj.get(key)
        if key not in obj:
            require(optional, 'MISSING_FIELD', f'{key} is required', path+'/'+key); continue
        if value is None and optional: continue
        p = path+'/'+key
        if kind == 'str': require(isinstance(value, str) and bool(value.strip()), 'INVALID_TYPE', 'Expected non-empty text', p)
        elif kind == 'int': require(type(value) is int, 'INVALID_TYPE', 'Expected integer', p)
        elif kind in {'positive', 'nonnegative'}:
            require(type(value) is int and value >= (1 if kind == 'positive' else 0), 'INVALID_TYPE', 'Expected bounded integer', p)
        elif kind == 'bool': require(type(value) is bool, 'INVALID_TYPE', 'Expected boolean', p)
        elif kind == 'id': ident(value, p)
        elif kind == 'ref':
            require(isinstance(value, dict) and len(value) == 1 and next(iter(value)) in {'id', 'client_key'}, 'INVALID_REFERENCE', 'Use {id: UUID} or {client_key: batch key}', p)
            v = next(iter(value.values()))
            require(isinstance(v, str) and bool(v), 'INVALID_REFERENCE', 'Reference value must be text', p)
            if 'id' in value: ident(v, p)
        elif kind == 'refs':
            require(isinstance(value, list), 'INVALID_TYPE', 'Expected reference array', p)
            for i, ref in enumerate(value): fields({'ref': ref}, {'ref': 'ref'}, f'{p}/{i}')
        elif kind == 'argv':
            require(isinstance(value, list) and value and all(isinstance(x, str) and '\x00' not in x for x in value), 'INVALID_ARGV', 'Command is a nonempty string array', p)
        elif kind == 'paths':
            require(isinstance(value, list), 'INVALID_SCOPE', 'Expected scope array', p)
            for i, item in enumerate(value):
                fields(item, {'resource': 'str', 'path': 'str', 'access': 'str'}, f'{p}/{i}')
                name = item['path']
                require(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and '\\' not in name and '\x00' not in name,
                        'UNSAFE_PATH', 'Scope must be relative to its resource', f'{p}/{i}/path')
                require(item['access'] in {'read','write'}, 'INVALID_SCOPE', 'Use read or write', f'{p}/{i}/access')
        elif kind == 'object': require(isinstance(value, dict), 'INVALID_TYPE', 'Expected object', p)
        elif kind == 'array': require(isinstance(value, list), 'INVALID_TYPE', 'Expected array', p)
        else: raise RuntimeError('Unknown schema descriptor: '+kind)


def batch(con, revision, phase, operations):
    require(phase in STAGE_TABLES, 'PHASE_OWNERSHIP', 'Execution phases record results; revise the owning content phase')
    require(isinstance(operations, list), 'INVALID_TYPE', 'operations must be an array', '/payload/operations')
    require(len(operations) <= 1000, 'BATCH_LIMIT', 'Batch exceeds 1000 operations')
    keys, allocated = {}, {}
    for i, op in enumerate(operations):
        p = f'/payload/operations/{i}'
        require(isinstance(op, dict) and isinstance(op.get('op'), str), 'INVALID_OPERATION', 'Expected named operation', p)
        verb, _, kind = op['op'].partition('_')
        if verb in {'create','update'} and kind in FIELDS:
            table, definitions = FIELDS[kind]
            required_defs = definitions if verb == 'create' else {k: v.rstrip('?')+'?' for k,v in definitions.items()}
            fields(op, {'op':'str', 'client_key':'str?' if verb=='create' else 'str?', **({'id':'id'} if verb=='update' else {}), **required_defs}, p)
            require(table in STAGE_TABLES[phase], 'PHASE_OWNERSHIP', f'{table} belongs to a different content phase', p)
            if verb == 'create':
                value = uid(); allocated[i] = value
                if 'client_key' in op:
                    require(op['client_key'] not in keys, 'DUPLICATE_CLIENT_KEY', 'Batch keys must be unique', p+'/client_key')
                    keys[op['client_key']] = value
        elif op['op'] in RELATIONS:
            table, columns = RELATIONS[op['op']]
            fields(op, {'op':'str', **{k:'str' if v=='text' else 'ref' for k,v in columns.items()}}, p)
            require(table in STAGE_TABLES[phase], 'PHASE_OWNERSHIP', f'{table} belongs to a different phase', p)
        else:
            raise Fault('UNKNOWN_OPERATION', 'Unsupported domain operation: '+op['op'], p+'/op')

    def ref(obj):
        if obj is None: return None
        if 'id' in obj: return obj['id']
        require(obj['client_key'] in keys, 'UNKNOWN_CLIENT_KEY', 'Reference names an absent batch key')
        return keys[obj['client_key']]

    pending = []
    for i, op in enumerate(operations):
        verb, _, kind = op['op'].partition('_')
        if op['op'] in RELATIONS:
            table, columns = RELATIONS[op['op']]
            row = {'revision_id': revision}
            for key, column in columns.items(): row['reason' if column=='text' else column] = op[key] if column=='text' else ref(op[key])
            pending.append((table,row)); continue
        table, definitions = FIELDS[kind]; idcol = ENTITY_IDS[table]
        value = allocated[i] if verb == 'create' else op['id']
        row = {'revision_id':revision, idcol:value}
        for key in definitions:
            if key not in op: continue
            v=op[key]
            if (kind,key) in REL_INLINE:
                rel,left,right=REL_INLINE[kind,key]
                if verb == 'update': con.execute(f'DELETE FROM {rel} WHERE revision_id=? AND {left}=?',(revision,value))
                for obj in v or []: pending.append((rel,{'revision_id':revision,left:value,right:ref(obj)}))
            elif key in {'task','consumer_task','producer_task','check'}: row[key+'_id']=ref(v)
            elif key in {'argv','scope_paths'}: row[key+'_json']=canonical(v).decode() if v is not None else None
            elif key=='required': row[key]=int(v)
            else: row[key]=v
        if verb == 'create':
            if 'ordinal' in definitions: row.setdefault('ordinal',con.execute(f'SELECT count(*) FROM {table} WHERE revision_id=?',(revision,)).fetchone()[0])
            if kind=='check':
                row.setdefault('task_id',None); row.setdefault('argv_json',None)
                row.setdefault('timeout_seconds',60);row.setdefault('max_age_seconds',None)
            if kind in {'check','precondition'}: pending.insert(0,(table,row))
            else: insert(con,table,row)
        else:
            one(con,f'SELECT * FROM {table} WHERE revision_id=? AND {idcol}=?',(revision,value))
            changes={k:v for k,v in row.items() if k not in {'revision_id',idcol}}
            if changes: con.execute(f'UPDATE {table} SET '+','.join(f'{k}=?' for k in changes)+f' WHERE revision_id=? AND {idcol}=?',(*changes.values(),revision,value))
    order={t:i for i,t in enumerate(CONTENT_TABLES)}
    for table,row in sorted(pending,key=lambda item:order[item[0]]): insert(con,table,row)
    validate_graph(con,revision)
    return keys


def validate_graph(con, revision):
    tasks={r['task_id']:dict(r) for r in con.execute('SELECT * FROM tasks WHERE revision_id=?',(revision,))}
    graph={k:[] for k in tasks}
    def edge(consumer, producer, source):
        require(consumer!=producer,'TASK_SELF_DEPENDENCY','A task cannot wait on its own future output',source)
        require(PHASES.index(tasks[producer]['target_phase']) <= PHASES.index(tasks[consumer]['target_phase']),
                'DEPENDENCY_PHASE_ORDER','A task cannot depend on a later lifecycle phase',source)
        graph[consumer].append(producer)
    for r in con.execute('SELECT * FROM task_dependencies WHERE revision_id=?',(revision,)):
        edge(r['task_id'],r['predecessor_id'],'/task_dependencies')
    for r in con.execute('SELECT * FROM preconditions WHERE revision_id=?',(revision,)):
        if r['producer_task_id'] and r['enforce_at']!='complete': edge(r['consumer_task_id'],r['producer_task_id'],'/preconditions')
    done=set()
    def visit(node,stack):
        require(node not in stack,'DEPENDENCY_CYCLE','Execution dependency cycle',details={'cycle':[*stack,node]})
        if node in done:return
        for parent in graph[node]:visit(parent,(*stack,node))
        done.add(node)
    for task in tasks:visit(task,())


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
    seen=set() if seen is None else seen
    require(task_id not in seen,'DEPENDENCY_CYCLE','Task closure contains a cycle')
    seen={*seen,task_id}
    task=dict(one(con,'SELECT * FROM tasks WHERE revision_id=? AND task_id=?',(revision,task_id)))
    task.pop('revision_id'); task.pop('ordinal')
    content={'task':task,'designs':[],'criteria':[],'requirements':[],'predecessors':[],'preconditions':[]}
    reqs=set()
    for r in con.execute('SELECT d.* FROM designs d JOIN task_designs x USING(revision_id,design_id) WHERE x.revision_id=? AND x.task_id=?',(revision,task_id)):
        row=dict(r);row.pop('revision_id');row.pop('ordinal');content['designs'].append(row)
        reqs.update(x[0] for x in con.execute('SELECT requirement_id FROM design_requirements WHERE revision_id=? AND design_id=?',(revision,row['design_id'])))
    for r in con.execute('SELECT c.* FROM criteria c JOIN task_criteria x USING(revision_id,criterion_id) WHERE x.revision_id=? AND x.task_id=?',(revision,task_id)):
        row=dict(r);row.pop('revision_id');row.pop('ordinal');content['criteria'].append(row)
        reqs.update(x[0] for x in con.execute('SELECT requirement_id FROM criterion_requirements WHERE revision_id=? AND criterion_id=?',(revision,row['criterion_id'])))
    for rid in sorted(reqs):
        row=dict(one(con,'SELECT * FROM requirements WHERE revision_id=? AND requirement_id=?',(revision,rid)))
        row.pop('revision_id');row.pop('ordinal');content['requirements'].append(row)
    for r in con.execute('SELECT predecessor_id FROM task_dependencies WHERE revision_id=? AND task_id=?',(revision,task_id)):
        content['predecessors'].append((r[0],task_fingerprint(con,revision,r[0],seen)))
    for r in con.execute('SELECT p.*, c.description,c.expected_result,c.argv_json,c.executor,c.max_age_seconds FROM preconditions p JOIN checks c USING(revision_id,check_id) WHERE p.revision_id=? AND p.consumer_task_id=?',(revision,task_id)):
        row=dict(r);row.pop('revision_id');content['preconditions'].append(row)
    for k,v in content.items():
        if isinstance(v,list):v.sort(key=canonical)
    return digest(content)
