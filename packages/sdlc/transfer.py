"""Bounded logical archives and explicit workspace identity operations.

Archives are untrusted data. Import validates a fresh Store before touching target
rows; SQLite is never replaced by collect. Clone alone uses the Backup API.
"""
import html
import io
import os
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
import zipfile
import zlib
from pathlib import Path

from . import content
from .common import Fault, atomic_write, canonical, digest, file_lock, ident, loads, now, require, safe_path, sha, uid
from .storage import CONTENT_TABLES, Store, insert, one

TABLES = ('projects', 'contexts', 'context_entries', 'workspaces', 'changes', 'revisions',
          *CONTENT_TABLES, 'assets', 'runs', 'code_snapshots', 'steps', 'check_results',
          'findings', 'deliveries', 'asset_links', 'authorizations', 'operations')
# Dependency evidence such as Maven JARs is already compressed. Keep both
# admission limits bounded without assuming a two-to-one compression ratio.
MAX_ARCHIVE = 512*1024*1024
MAX_EXPANDED = 512*1024*1024
MAX_ROWS = 50000
OWNED = {
    'changes': [(t, 'change_id') for t in ('revisions', 'runs', 'findings', 'deliveries', 'authorizations')],
    'revisions': [(t, 'revision_id') for t in (*CONTENT_TABLES, 'asset_links')],
    'contexts': [('context_entries', 'context_id')],
    'runs': [('steps', 'run_id'), ('code_snapshots', 'run_id'), ('operations', 'run_id')],
    'steps': [('check_results', 'step_id')],
    'check_results': [('asset_links', 'result_id')],
    'deliveries': [('asset_links', 'delivery_id')],
}


def metadata(con):
    result = {}
    for table in TABLES:
        cols = list(con.execute(f'PRAGMA table_info({table})'))
        keys = [r['name'] for r in sorted(cols, key=lambda r: r['pk']) if r['pk']]
        groups = {}
        for fk in con.execute(f'PRAGMA foreign_key_list({table})'):
            groups.setdefault(fk['id'], []).append(dict(fk))
        result[table] = {'columns': [r['name'] for r in cols], 'keys': keys, 'fks': list(groups.values())}
    return result


def intent_assets(row):
    if row['intent_json'] is None:
        return []
    intent = loads(row['intent_json'])
    require(isinstance(intent, dict) and intent.get('kind') == row['command'], 'ARCHIVE_SCHEMA', 'Invalid operation intent object')
    if intent['kind'] == 'task.write':
        files = intent.get('files')
        require(isinstance(files, list) and all(isinstance(f, dict) and 'asset_id' in f for f in files),
                'ARCHIVE_SCHEMA', 'Write intent requires a file array with asset references')
        assets = [f['asset_id'] for f in files if f['asset_id'] is not None]
    elif intent['kind'] == 'delivery.execute':
        assets = [intent.get('asset_id')]
    else:
        assets = []
    for value in assets:
        ident(value, '/database/operations/intent_json/asset_id')
    return assets


def closure(con, project, change):
    content.change_row(con, project, change)
    meta = metadata(con)
    selected = {table: {} for table in TABLES}
    queue = [('changes', dict(one(con, 'SELECT * FROM changes WHERE change_id=?', (change,))))]
    count = 0
    while queue:
        table, row = queue.pop()
        key = tuple(row[k] for k in meta[table]['keys'])
        if key in selected[table]:
            continue
        selected[table][key] = row
        count += 1
        require(count <= MAX_ROWS, 'ARCHIVE_LIMIT', 'Selected change exceeds the archive row budget', status='blocked')
        for fk in meta[table]['fks']:
            target = fk[0]['table']
            values = [row[f['from']] for f in fk]
            if any(v is None for v in values):
                continue
            sql = ' AND '.join(f['to']+'=?' for f in fk)
            queue.append((target, dict(one(con, f'SELECT * FROM {target} WHERE {sql}', values, code='ARCHIVE_CLOSURE'))))
        for child, column in OWNED.get(table, []):
            queue.extend((child, dict(r)) for r in con.execute(f'SELECT * FROM {child} WHERE {column}=?', (row[column],)))
        if table == 'code_snapshots':
            for file in loads(row['untracked_json']):
                queue.append(('assets', dict(one(con, 'SELECT * FROM assets WHERE project_id=? AND asset_id=?', (row['project_id'], file['asset_id']), code='ARCHIVE_ASSET_SCOPE'))))
        if table == 'operations':
            for asset in intent_assets(row):
                queue.append(('assets', dict(one(con, 'SELECT * FROM assets WHERE project_id=? AND asset_id=?', (row['project_id'], asset), code='ARCHIVE_ASSET_SCOPE'))))
        if table == 'changes':
            for operation in con.execute("SELECT * FROM operations WHERE project_id=? AND command='github.publish'", (project,)):
                if operation['intent_json'] and loads(operation['intent_json']).get('change_id') == row['change_id']:
                    queue.append(('operations', dict(operation)))
        if table == 'operations' and row['command'] == 'github.publish':
            intent = loads(row['intent_json'])
            require(intent.get('project_id') == project and intent.get('change_id') == change,
                    'ARCHIVE_SCOPE', 'Publication receipt belongs to another scope')
            queue.append(('revisions', dict(one(con, 'SELECT * FROM revisions WHERE project_id=? AND change_id=? AND revision_id=?',
                         (project, change, intent.get('revision_id')), code='ARCHIVE_CLOSURE'))))
        if table == 'contexts':
            for operation in con.execute("SELECT * FROM operations WHERE project_id=? AND command='context.commit'", (project,)):
                response = loads(operation['response_json'])
                if response.get('data', {}).get('context_id') == row['context_id']:
                    queue.append(('operations', dict(operation)))
    return {table: sorted(rows.values(), key=canonical) for table, rows in selected.items()}


def pack(files, manifest):
    manifest = {**manifest, 'files': {name: sha(raw) for name, raw in sorted(files.items())}}
    logical = digest(manifest)
    files = {**files, 'manifest.json': canonical(manifest)+b'\n'}
    require(sum(len(raw) for raw in files.values()) <= MAX_EXPANDED, 'ARCHIVE_LIMIT', 'Archive exceeds expanded byte budget')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, raw)
    raw = buffer.getvalue()
    require(len(raw) <= MAX_ARCHIVE, 'ARCHIVE_LIMIT', 'Archive exceeds compressed byte budget')
    return raw, logical


def export(store, con, project, change):
    rows = closure(con, project, change)
    config = store.config()
    files = {'database.json': canonical(rows)+b'\n'}
    for row in rows['assets']:
        h = row['sha256']
        files[f'assets/{h[:2]}/{h[2:4]}/{h}'] = store.asset_bytes(con, row['asset_id'], row['project_id'])
    # Raw request/response, stdout/stderr and effect intents are evidence, not views.
    # Disposable collector tmp trees and managed exports are not recursively archived.
    for run in rows['runs']:
        base = safe_path(store.home, 'runs/'+run['run_id'])
        if base.is_dir():
            for path in sorted(base.rglob('*')):
                rel = path.relative_to(base)
                require(not path.is_symlink(), 'ARCHIVE_SYMLINK', 'Managed run archive contains a symlink', status='blocked')
                if path.is_file() and 'tmp' not in rel.parts:
                    require(path.stat().st_size <= 8*1024*1024, 'ARCHIVE_LIMIT', 'Raw diagnostic exceeds per-file budget; preserve it and configure a larger archive adapter', status='blocked')
                    files['runs/'+run['run_id']+'/'+rel.as_posix()] = path.read_bytes()
    # Version projection needs portable original evidence, not an absolute path
    # to a previous workspace. These are opaque provenance, never import rows.
    for receipt in con.execute('SELECT * FROM imports ORDER BY bundle_digest'):
        summary = loads(receipt['summary'])
        if (summary.get('change_id') != change or not summary.get('rows_imported')
                or not (summary.get('revision_id_aliases') or summary.get('inherited_revision_provenance') or summary.get('preserved_observations'))):
            continue
        name = 'imports/'+receipt['bundle_digest']
        original = safe_path(store.home, name+'.zip').read_bytes()
        require(sha(original) == summary['archive_sha256'], 'ARCHIVE_INTEGRITY', 'Retained import archive differs')
        files[name+'.zip'] = original
        files[name+'.json'] = canonical({**dict(receipt), 'summary': summary})+b'\n'
    from .rendering import document, pretty
    links = '<ul>'+''.join('<li><a href="'+html.escape(name, quote=True)+'">'+html.escape(name)+'</a></li>' for name in sorted(files) if name != 'database.json')+'</ul>'
    files['index.html'] = document('SDLC offline change archive', '<p>完整事实、历史结果和原始诊断；历史 PASS 不代表当前环境已验证。</p><h2>原始证据与附件</h2>'+links+pretty(rows))
    from .runtime import runtime_digest
    raw, hashed = pack(files, {'format': 'sdlc-workspace-2', 'schema_digest': sha(Path(__file__).with_name('schema.sql').read_bytes()),
        'source_store_id': config['store_id'], 'source_workspace_id': config['workspace_id'],
        'project_id': project, 'change_id': change, 'runtime_digest': runtime_digest(),
        'resources': config['resources'], 'source_root': str(store.root)})
    path = safe_path(store.home, 'exports/workspace/'+hashed+'.zip')
    if path.exists():
        require(path.read_bytes() == raw, 'ARCHIVE_CONFLICT', 'Existing archive differs', status='conflict')
    else:
        atomic_write(path, raw)
    return {'path': str(path), 'bundle_digest': hashed, 'archive_sha256': sha(raw), 'row_count': sum(map(len, rows.values())),
            'change_id': change, 'status': 'exported'}


def unpack(path):
    require(path.is_file() and not path.is_symlink(), 'ARCHIVE_PATH', 'Select a local regular archive file')
    with path.open('rb') as stream:
        raw = stream.read(MAX_ARCHIVE+1)
    require(len(raw) <= MAX_ARCHIVE, 'ARCHIVE_LIMIT', 'Archive exceeds byte budget')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            require(len(infos) <= 50000 and sum(i.file_size for i in infos) <= MAX_EXPANDED,
                    'ARCHIVE_LIMIT', 'Archive exceeds file or expanded byte budget')
            names = [i.filename for i in infos]
            require(len(names) == len(set(names)), 'ARCHIVE_PATH', 'Duplicate archive path')
            for info in infos:
                p = Path(info.filename)
                require(not p.is_absolute() and '..' not in p.parts and '\\' not in info.filename
                        and p.as_posix() == info.filename and not info.is_dir()
                        and ((info.external_attr >> 16) & 0o170000) != 0o120000,
                        'ARCHIVE_PATH', 'Unsafe archive entry')
            files = {i.filename: archive.read(i) for i in infos}
    except (zipfile.BadZipFile, RuntimeError, zlib.error, EOFError) as exc:
        raise Fault('ARCHIVE_CORRUPT', 'Archive cannot be verified') from exc
    manifest = loads(files.pop('manifest.json', b'{}'))
    require(isinstance(manifest, dict) and set(manifest) == {'format', 'schema_digest', 'source_store_id', 'source_workspace_id',
            'project_id', 'change_id', 'runtime_digest', 'resources', 'source_root', 'files'}, 'ARCHIVE_SCHEMA', 'Invalid archive manifest fields')
    for key in ('source_store_id', 'source_workspace_id', 'project_id', 'change_id'):
        ident(manifest[key], '/manifest/'+key)
    require(isinstance(manifest['resources'], dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in manifest['resources'].items()),
            'ARCHIVE_SCHEMA', 'Invalid source resource map')
    require(isinstance(manifest['source_root'], str) and isinstance(manifest['runtime_digest'], str), 'ARCHIVE_SCHEMA', 'Invalid source provenance')
    require(manifest.get('format') == 'sdlc-workspace-2', 'ARCHIVE_VERSION', 'Expected a v2 logical workspace archive')
    require(manifest.get('schema_digest') == sha(Path(__file__).with_name('schema.sql').read_bytes()),
            'ARCHIVE_VERSION', 'Archive schema differs; original bytes preserved', status='blocked')
    require(manifest.get('files') == {name: sha(data) for name, data in sorted(files.items())},
            'ARCHIVE_INTEGRITY', 'Archive manifest does not match its complete file set')
    return raw, manifest, files, digest(manifest)


# These fields evolve under their originating Run/workspace. Import never
# overwrites an existing observation or grants execution/authorization rights.
MUTABLE_OBSERVATIONS = {
    'runs': {'input_revision_id','status','current_phase','lease_id','error_code','error_message','finished_at',
             'repair_round','no_progress_rounds','last_progress_digest','max_repair_rounds','no_progress_limit',
             'format_attempts','max_format_attempts'},
    'operations': {'status','response_json','result_digest','config_applied_at'},
    'steps': {'status','outcome','output_revision_id','snapshot_id','finished_at'},
    'deliveries': {'status','readback_result_id','summary'},
}


def shared_observation(old, incoming, table):
    if table not in MUTABLE_OBSERVATIONS:
        return False
    stable = set(incoming) - MUTABLE_OBSERVATIONS[table] - {'origin_kind'}
    return all(old[key] == incoming[key] for key in stable)


def load_rows(con, rows, *, importing=False, observations=None):
    """Insert complete closure in a deferred-FK transaction without disabling locks."""
    meta = metadata(con)
    require(isinstance(rows, dict) and set(rows) == set(TABLES), 'ARCHIVE_SCHEMA', 'Unexpected logical table set')
    require(all(isinstance(v, list) for v in rows.values()) and sum(map(len, rows.values())) <= MAX_ROWS,
            'ARCHIVE_LIMIT', 'Invalid row collection or excessive row count')
    for table, values in rows.items():
        for row in values:
            require(isinstance(row, dict) and set(row) == set(meta[table]['columns']), 'ARCHIVE_SCHEMA', 'Invalid '+table+' row columns')
            if table == 'operations':
                intent_assets(row)
                require(isinstance(loads(row['response_json']), dict), 'ARCHIVE_SCHEMA', 'Operation receipt must be an object')
            if table == 'code_snapshots':
                files = loads(row['untracked_json'])
                require(isinstance(files, list) and all(isinstance(f, dict) and 'asset_id' in f and 'path' in f for f in files),
                        'ARCHIVE_SCHEMA', 'Snapshot file list must contain asset_id and path objects')
                for i, file in enumerate(files):
                    ident(file['asset_id'], '/database/code_snapshots/untracked_json/'+str(i)+'/asset_id')
                    require(isinstance(file['path'], str), 'ARCHIVE_SCHEMA', 'Snapshot path must be text')
                require(isinstance(loads(row['files_json']), list), 'ARCHIVE_SCHEMA', 'Snapshot input manifest must be an array')
            for column, value in row.items():
                if value is not None and column.endswith('_id') and column not in {'actor_id', 'operation_id', 'tree_id'}:
                    ident(value, '/database/'+table+'/'+column)
    con.execute('PRAGMA defer_foreign_keys=ON')
    suspended = {}
    new_committed_changes = {r['change_id'] for r in rows['revisions'] if r.get('state') != 'draft' and not con.execute('SELECT 1 FROM revisions WHERE revision_id=?', (r.get('revision_id'),)).fetchone()}
    for change in new_committed_changes:
        draft = con.execute("SELECT * FROM revisions WHERE change_id=? AND state='draft'", (change,)).fetchone()
        if draft:
            suspended[draft['revision_id']] = dict(draft)
            # FK checks are deferred and readers cannot see this staging interval.
            # Retain every draft relation, then restore the exact mutable row below.
            con.execute('DELETE FROM revisions WHERE revision_id=?', (draft['revision_id'],))
    staged_revisions, staged_contexts, pending = [], [], []
    for table in TABLES:
        for row in rows[table]:
            require(isinstance(row, dict) and set(row) == set(meta[table]['columns']), 'ARCHIVE_SCHEMA', 'Invalid '+table+' row columns')
            keys = meta[table]['keys']
            old = con.execute(f'SELECT * FROM {table} WHERE '+ ' AND '.join(k+'=?' for k in keys), [row[k] for k in keys]).fetchone()
            if old is None and table == 'revisions':
                old = suspended.get(row['revision_id'])
            if old:
                if table == 'changes':
                    stable = [k for k in row if k not in {'state', 'active_revision_id'}]
                    require(all(old[k] == row[k] for k in stable), 'IMPORT_ROW_CONFLICT', 'Change identity has different stable attributes', status='conflict')
                elif importing and shared_observation(old, row, table):
                    if observations is not None and dict(old) != row:
                        observations.append({'table': table, 'identity': {k: row[k] for k in keys},
                                             'target_digest': digest(dict(old)), 'source_digest': digest(row)})
                else:
                    comparable = dict(row)
                    if importing and table in {'runs', 'authorizations', 'operations'}:
                        comparable['origin_kind'] = old['origin_kind']
                    require(dict(old) == comparable, 'IMPORT_ROW_CONFLICT', 'Existing '+table+' identity contains different data', status='conflict', details={k: row[k] for k in keys})
                continue
            value = dict(row)
            if importing and table in {'runs', 'authorizations', 'operations'}:
                value['origin_kind'] = 'imported'
            if table == 'contexts' and row['state'] == 'committed':
                value.update(state='draft', digest=None)
                staged_contexts.append(row)
            if table == 'revisions':
                # Only one mutable draft at a time. Insert and fill each snapshot separately.
                pending.append(row)
                continue
            if table in CONTENT_TABLES or (table == 'asset_links' and row['revision_id']):
                continue
            insert(con, table, value)
    for revision in sorted(pending, key=lambda row: row['state'] == 'draft'):
        value = {**revision, 'state': 'draft', 'digest': None}
        insert(con, 'revisions', value)
        for table in (*CONTENT_TABLES, 'asset_links'):
            for row in rows[table]:
                if row['revision_id'] == revision['revision_id']:
                    insert(con, table, row)
        con.execute('UPDATE revisions SET state=?,digest=? WHERE revision_id=?',
                    (revision['state'], revision['digest'], revision['revision_id']))
        staged_revisions.append(revision)
    for row in suspended.values():
        insert(con, 'revisions', row)
    for row in staged_contexts:
        con.execute('UPDATE contexts SET state=?,digest=? WHERE context_id=?', (row['state'], row['digest'], row['context_id']))
    require(not con.execute('PRAGMA foreign_key_check').fetchall(), 'ARCHIVE_CLOSURE', 'Archive has missing or inconsistent references')
    return staged_revisions


def validate_archive(store, manifest, files):
    rows = loads(files.get('database.json', b'{}'))
    # A disposable database exercises the same strict tables, triggers and FKs.
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(Path(__file__).with_name('schema.sql').read_text())
    try:
        con.execute('BEGIN')
        inserted = load_rows(con, rows)
        require([r['project_id'] for r in rows['projects']] == [manifest['project_id']] and
                [r['change_id'] for r in rows['changes']] == [manifest['change_id']],
                'ARCHIVE_SCOPE', 'Archive must contain exactly the selected project and change')
        selected = closure(con, manifest['project_id'], manifest['change_id'])
        require(selected == rows, 'ARCHIVE_CLOSURE', 'Archive includes unrelated or unreachable facts')
        for context in rows['contexts']:
            if context['state'] == 'committed':
                require(content.context_digest(con, context['context_id']) == context['digest'], 'ARCHIVE_CONTEXT_DIGEST', 'Context snapshot digest differs')
        for row in inserted:
            if row['state'] != 'draft':
                require(store.content_digest(con, row['revision_id']) == row['digest'],
                        'ARCHIVE_CONTENT_DIGEST', 'Content snapshot digest does not match its relations')
        run_ids = {r['run_id'] for r in rows['runs']}
        asset_paths = {f"assets/{r['sha256'][:2]}/{r['sha256'][2:4]}/{r['sha256']}" for r in rows['assets']}
        provenance = set()
        for name, raw in files.items():
            if not name.startswith('imports/') or not name.endswith('.json'):
                continue
            receipt = loads(raw)
            require(isinstance(receipt, dict) and isinstance(receipt.get('summary'), dict),
                    'ARCHIVE_PROVENANCE', 'Invalid import provenance receipt')
            summary = receipt['summary']
            original_name = name[:-5]+'.zip'
            require(name == 'imports/'+str(receipt.get('bundle_digest'))+'.json'
                    and summary.get('change_id') == manifest['change_id']
                    and original_name in files and sha(files[original_name]) == summary.get('archive_sha256'),
                    'ARCHIVE_PROVENANCE', 'Import provenance must retain its exact archive and selected scope')
            provenance.update((name, original_name))
        for name in files:
            parts = Path(name).parts
            require(name in {'database.json', 'index.html'} or name in asset_paths or name in provenance or
                    (len(parts) >= 3 and parts[0] == 'runs' and parts[1] in run_ids),
                    'ARCHIVE_CLOSURE', 'Archive contains a file outside selected evidence closure')
        for asset in rows['assets']:
            h = asset['sha256']
            raw = files.get(f'assets/{h[:2]}/{h[2:4]}/{h}')
            require(raw is not None and len(raw) == asset['size_bytes'] and sha(raw) == h,
                    'ARCHIVE_ASSET', 'Required asset is missing or differs')
        con.commit()
    finally:
        con.close()
    return rows


def ancestors(con, revision):
    seen, queue = set(), [revision] if revision else []
    while queue:
        value = queue.pop()
        if value in seen:
            continue
        seen.add(value)
        row = one(con, 'SELECT parent_id,merged_from_id FROM revisions WHERE revision_id=?', (value,))
        queue.extend(v for v in row if v)
    return seen


def asset_aliases(con, rows):
    aliases = {}
    retained = []
    for asset in rows['assets']:
        existing = con.execute('SELECT * FROM assets WHERE project_id=? AND sha256=?', (asset['project_id'], asset['sha256'])).fetchone()
        if existing and existing['asset_id'] != asset['asset_id']:
            require(existing['size_bytes'] == asset['size_bytes'], 'ASSET_CORRUPT', 'Equal asset digest has a different size', status='blocked')
            aliases[asset['asset_id']] = existing['asset_id']
        else:
            retained.append(asset)
    rows['assets'] = retained
    for table, values in rows.items():
        for row in values:
            for field in ('asset_id', 'patch_asset_id', 'evidence_asset_id', 'bundle_asset_id'):
                if row.get(field) in aliases:
                    row[field] = aliases[row[field]]
            if table == 'operations' and row['intent_json']:
                intent = loads(row['intent_json'])
                if intent.get('kind') == 'task.write':
                    for file in intent['files']:
                        file['asset_id'] = aliases.get(file['asset_id'], file['asset_id'])
                elif intent.get('kind') == 'delivery.execute':
                    intent['asset_id'] = aliases.get(intent['asset_id'], intent['asset_id'])
                row['intent_json'] = canonical(intent).decode()
            if table == 'code_snapshots':
                files = loads(row['untracked_json'])
                for file in files:
                    file['asset_id'] = aliases.get(file['asset_id'], file['asset_id'])
                row['untracked_json'] = canonical(files).decode()
    return aliases


def revision_aliases(store, con, rows, source_store, bundle):
    """Explicitly preserve frozen revision forks; never rename execution identities."""
    revisions = {r['revision_id']: r for r in rows['revisions']}
    changed = set()
    for key, row in revisions.items():
        old = con.execute('SELECT * FROM revisions WHERE revision_id=?', (key,)).fetchone()
        if old and dict(old) != row:
            require((old['project_id'], old['change_id']) == (row['project_id'], row['change_id']),
                    'IMPORT_ROW_CONFLICT', 'Revision identity belongs to another scope', status='conflict')
            changed.add(key)
    while True:
        descendants = {key for key, row in revisions.items()
                       if row['parent_id'] in changed or row['merged_from_id'] in changed}
        if descendants <= changed:
            break
        changed.update(descendants)
    require(all(revisions[key]['state'] != 'draft' for key in changed),
            'IMPORT_DRAFT_CONFLICT', 'Checkpoint source drafts before preserving divergent versions', status='conflict')
    def alias(kind, key):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, 'sdlc-v2:'+source_store+':'+bundle+':'+kind+':'+key))
    aliases = {key: alias('revision', key) for key in sorted(changed)}
    versions = {key: {'revision_id': aliases[key], 'source_digest': revisions[key]['digest']}
                for key in aliases}
    # Only schema-declared revision FKs are projected. Embedded historical JSON,
    # request/result digests and raw logs remain the exact source evidence.
    meta = metadata(con)
    for table, values in rows.items():
        refs = {f['from'] for group in meta[table]['fks'] for f in group
                if f['table'] == 'revisions' and f['to'] == 'revision_id'}
        if table == 'revisions':
            refs.add('revision_id')
        for row in values:
            if table == 'asset_links' and row['revision_id'] in aliases:
                row['link_id'] = alias('asset_link', row['link_id'])
            for field in refs:
                row[field] = aliases.get(row[field], row[field])
    if aliases:
        # Calculate local digests against the complete projected content before
        # inserting frozen target rows. Parent identities participate in digest.
        scratch = sqlite3.connect(':memory:')
        scratch.row_factory = sqlite3.Row
        try:
            scratch.executescript(Path(__file__).with_name('schema.sql').read_text())
            scratch.execute('BEGIN')
            load_rows(scratch, rows)
            for key, version in versions.items():
                local = version['revision_id']
                version['imported_digest'] = store.content_digest(scratch, local)
                revisions[key]['digest'] = version['imported_digest']
        finally:
            scratch.close()
    return aliases, versions


def collect_result(value):
    if value.get('status') == 'conflict':
        value = {**value, 'control_status': 'conflict', 'error_code': 'IMPORT_CONFLICT',
                 'error_message': 'Import preserved source evidence; resolve the reported conflict before adopting it.'}
        value.setdefault('next_actions', [])
        if not value['next_actions']:
            value['next_actions'] = [{'action': 'inspect_import', 'import_id': value['import_id'],
                                      'relation': value.get('relation'), 'error': value.get('error')}]
    return value


def collect(store, con, project, p):
    path = Path(p['path']).expanduser().resolve()
    raw, manifest, files, hashed = unpack(path)
    require(manifest['project_id'] == project, 'IMPORT_PROJECT', 'Source and target project identities differ', status='conflict')
    prior = con.execute('SELECT * FROM imports WHERE bundle_digest=?', (hashed,)).fetchone()
    preserve = p.get('conflict_policy', 'reject') == 'preserve_revision_versions'
    previous = loads(prior['summary']) if prior else None
    if prior and not (preserve and previous.get('relation') == 'row_conflict'):
        return collect_result({**dict(prior), **previous, 'idempotent': True})
    rows = validate_archive(store, manifest, files)
    change = rows['changes'][0]
    target = con.execute('SELECT * FROM changes WHERE change_id=?', (change['change_id'],)).fetchone()
    # Always retain the exact source archive, including divergent mutable rows.
    retained = safe_path(store.home, 'imports/'+hashed+'.zip')
    if retained.exists():
        require(retained.read_bytes() == raw, 'ARCHIVE_CONFLICT',
                'This logical bundle already has different original ZIP bytes; select the retained archive',
                status='conflict', details={'archive': str(retained)})
    else:
        atomic_write(retained, raw)
    outcome = 'imported'
    summary = {'change_id': change['change_id'], 'source_head': change['active_revision_id'],
               'target_head': target['active_revision_id'] if target else None, 'archive': str(retained),
               'archive_sha256': sha(raw), 'rows_imported': False,
               'inherited_revision_provenance': any(name.startswith('imports/') for name in files)}
    if previous:
        summary['prior_conflict'] = previous
    con.execute('SAVEPOINT logical_collect')
    try:
        if preserve:
            revision_ids, versions = revision_aliases(store, con, rows, manifest['source_store_id'], hashed)
            summary.update(revision_id_aliases=revision_ids, revision_versions=versions)
        summary['imported_source_head'] = change['active_revision_id']
        aliases = asset_aliases(con, rows)
        summary['asset_id_aliases'] = aliases
        inserted = load_rows(con, rows, importing=True, observations=summary.setdefault('preserved_observations', []))
        for revision in inserted:
            if revision['state'] != 'draft':
                require(store.content_digest(con, revision['revision_id']) == revision['digest'], 'ARCHIVE_CONTENT_DIGEST', 'Imported snapshot changed its content identity')
        for asset in rows['assets']:
            h = asset['sha256']
            asset_path = safe_path(store.home, f'assets/{h[:2]}/{h[2:4]}/{h}')
            raw_asset = files[f'assets/{h[:2]}/{h[2:4]}/{h}']
            if asset_path.exists():
                require(asset_path.read_bytes() == raw_asset, 'ASSET_CORRUPT', 'Target asset differs from its digest', status='runtime_error')
            else:
                atomic_write(asset_path, raw_asset)
        for name, raw_file in files.items():
            if not name.startswith('runs/'):
                continue
            log_path = safe_path(store.home, name)
            if log_path.exists() and log_path.read_bytes() != raw_file:
                # Existing execution history stays unchanged; both raw versions survive.
                log_path = safe_path(store.home, 'imports/'+hashed+'/'+name)
            if not log_path.exists():
                atomic_write(log_path, raw_file)
        if target:
            source_head, target_head = change['active_revision_id'], target['active_revision_id']
            target_draft = con.execute("SELECT revision_id FROM revisions WHERE change_id=? AND state='draft'", (change['change_id'],)).fetchone()
            if source_head == target_head:
                summary['relation'] = 'same'
            elif target_head is None or target_head in ancestors(con, source_head):
                if target_draft:
                    outcome, summary['relation'] = 'conflict', 'target_draft_pending'
                else:
                    con.execute('UPDATE changes SET active_revision_id=?,state=? WHERE change_id=?',
                                (source_head, change['state'], change['change_id']))
                    summary['relation'] = 'fast_forward'
            elif source_head is None or source_head in ancestors(con, target_head):
                summary['relation'] = 'history_only'
            else:
                outcome, summary['relation'] = 'conflict', 'diverged'
        else:
            summary['relation'] = 'new_change'
        summary['rows_imported'] = True
        con.execute('RELEASE logical_collect')
    except (Fault, sqlite3.IntegrityError) as exc:
        con.execute('ROLLBACK TO logical_collect')
        con.execute('RELEASE logical_collect')
        outcome, summary['relation'] = 'conflict', 'row_conflict'
        summary['error'] = exc.record() if isinstance(exc, Fault) else {'code': 'IMPORT_CONSTRAINT', 'message': str(exc)}
        summary['imported_source_head'] = None
    value = prior['import_id'] if prior else uid()
    if prior:
        con.execute('UPDATE imports SET status=?,summary=? WHERE import_id=?', (outcome, canonical(summary).decode(), value))
    else:
        insert(con, 'imports', {'import_id': value, 'source_store_id': manifest['source_store_id'], 'bundle_digest': hashed,
               'status': outcome, 'summary': canonical(summary).decode(), 'created_at': now()})
    return collect_result({'import_id': value, 'status': outcome, 'bundle_digest': hashed, **summary,
            'next_actions': ([{'action': 'change.resolve', 'source_revision_id': summary['imported_source_head'],
                              'precondition': 'Complete the target content checkpoint first'}]
                             if outcome == 'conflict' and summary['rows_imported'] else [])})


def clone(store, con, p, operation):
    target = Path(p['target']).expanduser().resolve()
    require(target.is_dir() and target != store.root and not target.is_relative_to(store.home),
            'CLONE_TARGET', 'Select an existing independent product directory', '/payload/target')
    destination = safe_path(target, '.sdlc')
    with file_lock(target/'.sdlc-clone.lock'):
        if destination.exists():
            other = Store(target).config()
            require(other.get('clone_operation_id') == operation and other.get('source_store_id') == store.config()['store_id'],
                    'CLONE_TARGET_EXISTS', 'Target already has runtime data; preserve it', status='conflict')
            return {'target': str(target), 'config': other, 'idempotent': True}
        stage = Path(tempfile.mkdtemp(prefix='.sdlc-clone-', dir=target))
        try:
            db = sqlite3.connect(stage/'store.sqlite3')
            db.row_factory = sqlite3.Row
            source = store.connect(readonly=True)
            try:
                source.backup(db)
            finally:
                source.close()
            config = store.config()
            workspace, instance = uid(), uid()
            insert(db, 'workspaces', {'workspace_id': workspace, 'project_id': config['project_id'], 'label': target.name,
                   'instance_id': instance, 'created_at': now()})
            db.commit()
            for asset in db.execute('SELECT * FROM assets'):
                raw = store.asset_bytes(con, asset['asset_id'], asset['project_id'])
                h = asset['sha256']
                atomic_write(stage/f'assets/{h[:2]}/{h[2:4]}/{h}', raw)
            db.close()
            for folder in ('runs', 'changes'):
                source_dir = store.home/folder
                if source_dir.exists():
                    require(not any(p.is_symlink() for p in source_dir.rglob('*')), 'CLONE_SYMLINK', 'Managed history contains a symlink', status='blocked')
                    shutil.copytree(source_dir, stage/folder, ignore=shutil.ignore_patterns('tmp'))
            new_config = {**config, 'store_id': uid(), 'source_store_id': config['store_id'], 'clone_operation_id': operation,
                'workspace_id': workspace, 'instance_id': instance, 'root_path': str(target), 'resources': {'main': '.'},
                'unbound_resources': {k: v for k, v in config['resources'].items() if k != 'main'}}
            atomic_write(stage/'config.json', canonical(new_config)+b'\n')
            atomic_write(stage/'.gitignore', b'*\n')
            os.rename(stage, destination)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return {'target': str(target), 'config': new_config, 'source_authorizations_active': False,
            'next_actions': [{'action': 'authorization.grant'}, {'action': 'workspace.bind'}]}


def bindings(store, con, project, p, *, rebind=False):
    config = store.config()
    before_digest, source_store = digest(config), config['store_id']
    resources = p.get('resources', {'main': '.'} if rebind else config['resources'])
    require(isinstance(resources, dict) and resources.get('main') == '.' and all(isinstance(k, str) and k.isidentifier()
            and isinstance(v, str) and v for k, v in resources.items()), 'RESOURCE_BINDING', 'Use a resource map with main bound to .')
    for key, value in resources.items():
        path = Path(value).expanduser()
        resolved = (path if path.is_absolute() else store.root/path).resolve()
        require(resolved.is_dir(), 'RESOURCE_NOT_FOUND', 'Bound resource must be an existing directory: '+key, status='blocked')
        require(not resolved.is_relative_to(store.home) and not store.home.is_relative_to(resolved) or key == 'main',
                'RESOURCE_PROTECTED', 'An additional resource cannot include managed runtime state', status='blocked')
    if rebind:
        workspace, instance = uid(), uid()
        insert(con, 'workspaces', {'workspace_id': workspace, 'project_id': project, 'label': store.root.name,
               'instance_id': instance, 'created_at': now()})
        config.update(store_id=uid(), workspace_id=workspace, instance_id=instance, root_path=str(store.root))
    config.update(resources=resources, unbound_resources={})
    return {'config': config, 'before_config_digest': before_digest, 'configuration_store_id': source_store, 'reason': p['reason'], 'source_authorizations_active': False if rebind else None}


def apply_config(store, command, response):
    if command not in {'workspace.bind', 'workspace.rebind'} or not response['ok']:
        return
    with store.transaction() as con:
        operation = one(con, 'SELECT * FROM operations WHERE operation_id=?', (response['operation_id'],))
        require(operation['origin_kind'] == 'local', 'OPERATION_IMPORTED', 'Imported receipts cannot configure this workspace', status='blocked')
        if operation['config_applied_at'] is not None:
            return
        data = response['data']
        current = store.config()
        current_digest, after_digest = digest(current), digest(data['config'])
        require(current['store_id'] == data['configuration_store_id'] or current_digest == after_digest,
                'OPERATION_WORKSPACE', 'A historical configuration receipt cannot configure this copied workspace', status='blocked')
        require(current_digest in {data['before_config_digest'], after_digest},
                'CONFIG_TRANSITION_CONFLICT', 'Configuration changed after the committed intent; preserve it and inspect the pending transition', status='conflict')
        if current_digest != after_digest:
            atomic_write(store.config_path, canonical(data['config'])+b'\n')
        con.execute('UPDATE operations SET config_applied_at=? WHERE operation_id=?', (now(), response['operation_id']))


def discover(root):
    try:
        result = subprocess.run(['git', '-C', str(root), 'worktree', 'list', '--porcelain', '-z'],
                                capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    candidates = []
    for part in result.stdout.decode(errors='replace').split('\0'):
        if part.startswith('worktree '):
            path = Path(part[9:]).resolve()
            if path != root and (path/'.sdlc/config.json').is_file():
                try:
                    config = Store(path).config()
                    candidates.append({'path': str(path), 'project_id': config['project_id'], 'store_id': config['store_id']})
                except (Fault, OSError):
                    pass
    return candidates
