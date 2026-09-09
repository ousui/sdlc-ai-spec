"""Content services: relational drafts, coverage and immutable adopted snapshots."""
from .common import PHASES, canonical, digest, now, require, uid
from .domain import batch, fields, validate_complete
from .storage import CONTENT_TABLES, insert, one
from .protocol import AUTHORIZATION, CONTEXT_ENTRY, operation_schema

REVISION_TEXT = ('title', 'summary', 'goal', 'in_scope', 'out_of_scope')


def change_row(con, project, change):
    require(change is not None, 'CHANGE_REQUIRED', 'Select an explicit change_id', '/change_id', status='blocked')
    return one(con, 'SELECT * FROM changes WHERE project_id=? AND change_id=?', (project, change), code='CHANGE_SCOPE')


def revision_row(con, project, change, revision=None):
    ch = change_row(con, project, change)
    draft = con.execute("SELECT revision_id FROM revisions WHERE change_id=? AND state='draft'", (change,)).fetchone()
    current = draft[0] if draft else ch['active_revision_id']
    value = revision or current
    row = one(con, 'SELECT * FROM revisions WHERE project_id=? AND change_id=? AND revision_id=?', (project, change, value), code='REVISION_SCOPE')
    require(value == current, 'STALE_REVISION', 'Input is no longer the current draft or adopted revision', '/payload/revision_id', status='conflict')
    return row


def cas(con, revision, generation):
    require(type(generation) is int, 'GENERATION_REQUIRED', 'Use expected_generation from phase.prepare', '/expected_generation')
    n = con.execute("UPDATE revisions SET generation=generation+1 WHERE revision_id=? AND state='draft' AND generation=?",
                    (revision, generation)).rowcount
    require(n == 1, 'GENERATION_CONFLICT', 'Draft changed or was committed; prepare again', '/expected_generation', status='conflict')


def child_revision(con, parent, phase, *, context_id=None):
    require(parent['state'] in {'committed', 'abandoned'}, 'DRAFT_EXISTS', 'Checkpoint the current draft before revising', status='conflict')
    value = uid()
    row = dict(parent)
    row.update(revision_id=value, parent_id=parent['revision_id'], merged_from_id=None,
               created_phase=phase, state='draft', generation=0, digest=None, created_at=now())
    if context_id:
        row['context_id'] = context_id
    insert(con, 'revisions', row)
    for table in CONTENT_TABLES:
        for old in con.execute(f'SELECT * FROM {table} WHERE revision_id=?', (parent['revision_id'],)).fetchall():
            insert(con, table, {**dict(old), 'revision_id': value})
    for old in con.execute('SELECT * FROM asset_links WHERE revision_id=?', (parent['revision_id'],)).fetchall():
        insert(con, 'asset_links', {**dict(old), 'link_id': uid(), 'revision_id': value})
    con.execute("UPDATE changes SET state='active' WHERE change_id=?", (parent['change_id'],))
    return value


def context_commit(con, project, payload):
    parent = payload.get('parent_id')
    if parent:
        one(con, "SELECT * FROM contexts WHERE project_id=? AND context_id=? AND state='committed'", (project, parent), code='CONTEXT_SCOPE')
    entries, keys = [], set()
    for i, entry in enumerate(payload['entries']):
        p = f'/payload/entries/{i}'
        fields(entry, CONTEXT_ENTRY, p)
        kind = entry['kind']
        require(kind in {'fact', 'rule', 'resource', 'command'}, 'INVALID_ENUM', 'Expected fact/rule/resource/command', p+'/kind')
        key = kind, entry['name']
        require(key not in keys, 'DUPLICATE_ENTRY', 'Context names are unique within a kind', p+'/name')
        keys.add(key)
        settings = entry.get('settings', {})
        schema = {'argv': 'argv', 'resource': 'str', 'environment_names': 'array?'} if kind == 'command' else ({'resource': 'str'} if kind == 'resource' else {})
        fields(settings, schema, p+'/settings')
        for j, name in enumerate(settings.get('environment_names', [])):
            require(isinstance(name, str) and name.isidentifier(), 'INVALID_ENV_NAME', 'Store environment names only', f'{p}/settings/environment_names/{j}')
        entries.append({**entry, 'settings': settings})
    value = uid()
    insert(con, 'contexts', {'context_id': value, 'project_id': project, 'parent_id': parent,
           'summary': payload['summary'], 'state': 'draft', 'created_at': now()})
    inherited = {(r['kind'], r['name']): r['entry_id'] for r in con.execute(
        'SELECT * FROM context_entries WHERE context_id=?', (parent,))} if parent else {}
    for entry in entries:
        insert(con, 'context_entries', {'context_id': value, 'entry_id': inherited.get((entry['kind'], entry['name']), uid()), 'kind': entry['kind'],
               'name': entry['name'], 'content': entry['content'], 'origin': entry.get('origin'),
               'settings_json': canonical(entry['settings']).decode()})
    hashed = digest({'summary': payload['summary'], 'entries': sorted(entries, key=canonical)})
    con.execute("UPDATE contexts SET state='committed',digest=? WHERE context_id=?", (hashed, value))
    return {'context_id': value, 'digest': hashed, 'next_actions': [{'action': 'change.create', 'phase': 'REQ'}]}


def create_change(con, project, payload, base_commit):
    context = one(con, "SELECT * FROM contexts WHERE project_id=? AND context_id=? AND state='committed'", (project, payload['context_id']), code='CONTEXT_SCOPE')
    require(payload['delivery_mode'] in {'local', 'git', 'deployment'}, 'INVALID_ENUM', 'Expected local/git/deployment', '/payload/delivery_mode')
    require(not con.execute('SELECT 1 FROM changes WHERE project_id=? AND slug=?', (project, payload['slug'])).fetchone(),
            'CHANGE_EXISTS', 'This project already has the requested slug', '/payload/slug', status='conflict')
    review_mode = payload.get('review_mode', 'auto')
    require(review_mode in {'auto', 'assisted'}, 'INVALID_ENUM', 'Expected auto/assisted', '/payload/review_mode')
    value, rev = uid(), uid()
    insert(con, 'changes', {'change_id': value, 'project_id': project, 'slug': payload['slug'], 'state': 'active',
           'initial_base_commit': base_commit, 'delivery_mode': payload['delivery_mode'],
           'delivery_target': payload['delivery_target'], 'created_at': now()})
    insert(con, 'revisions', {'revision_id': rev, 'project_id': project, 'change_id': value, 'context_id': context['context_id'],
           'created_phase': 'REQ', 'state': 'draft', 'created_at': now(), **{k: payload[k] for k in REVISION_TEXT}})
    source = uid()
    insert(con, 'sources', {'revision_id': rev, 'source_id': source, 'kind': 'text', 'original_text': payload['original_text'], 'ordinal': 0})
    actor = payload.get('actor_id', 'current-agent')
    for i, auth in enumerate(payload['authorizations']):
        p = f'/payload/authorizations/{i}'
        fields(auth, AUTHORIZATION, p)
        require(auth['action'] in {'edit_local', 'run_check', 'package_local'}, 'AUTHORIZATION_SCOPE',
                'First version accepts explicit local authorizations only', p+'/action', status='blocked')
        insert(con, 'authorizations', {'authorization_id': uid(), 'project_id': project, 'change_id': value, 'actor_id': actor,
               **auth, 'issued_at': now()})
    return {'change_id': value, 'revision_id': rev, 'generation': 0, 'source_id': source,
            'actor_id': actor, 'review_mode': review_mode, 'next_actions': [{'action': 'phase.prepare', 'phase': 'REQ'}]}


def phase_submit(con, project, change, payload, generation):
    row = revision_row(con, project, change, payload['revision_id'])
    require(payload['phase'] == row['created_phase'], 'PHASE_ORDER', 'Submit to the adopted draft phase', '/payload/phase')
    cas(con, row['revision_id'], generation)
    keys = batch(con, row['revision_id'], payload['phase'], payload['operations'])
    return {'change_id': change, 'revision_id': row['revision_id'], 'generation': generation+1, 'ids': keys}


def phase_complete(store, con, project, change, payload, generation):
    row = revision_row(con, project, change, payload['revision_id'])
    phase = payload['phase']
    require(phase in {'REQ', 'DSN', 'PLN'} and row['created_phase'] == phase, 'PHASE_ORDER', 'Complete the adopted content phase', '/payload/phase')
    cas(con, row['revision_id'], generation)
    validate_complete(con, row['revision_id'], phase)
    hashed = store.content_digest(con, row['revision_id'])
    con.execute("UPDATE revisions SET state='committed',digest=? WHERE revision_id=?", (hashed, row['revision_id']))
    con.execute('UPDATE changes SET active_revision_id=? WHERE change_id=?', (row['revision_id'], change))
    next_phase = PHASES[PHASES.index(phase)+1]
    adopted = row['revision_id']
    if next_phase in {'DSN', 'PLN'}:
        adopted = child_revision(con, one(con, 'SELECT * FROM revisions WHERE revision_id=?', (adopted,)), next_phase)
    return {'change_id': change, 'committed_revision_id': row['revision_id'], 'digest': hashed,
            'revision_id': adopted, 'generation': 0 if adopted != row['revision_id'] else generation+1,
            'next_actions': [{'action': 'phase.prepare', 'phase': next_phase}]}


def prepare(store, con, project, change, phase=None):
    ch = change_row(con, project, change)
    row = revision_row(con, project, change)
    inferred = row['created_phase'] if row['state'] == 'draft' else 'IMP'
    selected = phase or inferred
    require(selected in PHASES, 'INVALID_ENUM', 'Expected lifecycle phase', '/payload/phase')
    require(selected == inferred, 'PHASE_ORDER', 'Prepare the current phase: '+inferred, '/payload/phase', status='blocked')
    context = dict(one(con, 'SELECT * FROM contexts WHERE context_id=?', (row['context_id'],)))
    context['entries'] = [dict(r) for r in con.execute('SELECT * FROM context_entries WHERE context_id=? ORDER BY kind,name', (row['context_id'],))]
    return {'change': dict(ch), 'content': store.content(con, row['revision_id']), 'context': context,
            'phase': selected, 'generation': row['generation'], 'input_schema': operation_schema(selected),
            'attachments': [dict(r) for r in con.execute('SELECT l.*,a.sha256,a.media_type FROM asset_links l JOIN assets a USING(asset_id) WHERE l.revision_id=? ORDER BY l.ordinal,l.link_id', (row['revision_id'],))],
            'authorizations': [dict(r) for r in con.execute('SELECT * FROM authorizations WHERE project_id=? AND change_id=?', (project, change))]}
