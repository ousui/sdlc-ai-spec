"""SQLite and managed-file persistence, with short explicit transactions."""
from __future__ import annotations

import os
import sqlite3
import subprocess
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

from .common import Fault, SCHEMA, atomic_write, canonical, digest, file_lock, loads, now, require, safe_path, sha, uid

CONTENT_TABLES = ('sources', 'requirements', 'criteria', 'requirement_sources', 'criterion_requirements',
                  'designs', 'design_requirements', 'tasks', 'task_designs', 'task_criteria',
                  'task_dependencies', 'checks', 'check_criteria', 'preconditions')
ENTITY_IDS = {'sources': 'source_id', 'requirements': 'requirement_id', 'criteria': 'criterion_id',
              'designs': 'design_id', 'tasks': 'task_id', 'checks': 'check_id', 'preconditions': 'condition_id'}


class Store:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        require(self.root.is_dir(), 'WORKSPACE_NOT_FOUND', 'Project root must exist')
        self.home = safe_path(self.root, '.sdlc')
        self.db_path = safe_path(self.home, 'store.sqlite3')
        self.config_path = safe_path(self.home, 'config.json')

    def config(self):
        require(self.config_path.is_file() and self.db_path.is_file(), 'STORE_NOT_FOUND', 'Run sdlc-init first', status='blocked')
        config = loads(self.config_path.read_bytes())
        require(isinstance(config, dict), 'STORE_CONFIG', 'Store config must be an object', status='blocked')
        require(config.get('format_version') == 2 and config.get('database') == 'store.sqlite3',
                'STORE_VERSION', 'Expected a v2 local store; existing data is not changed', status='blocked')
        require(all(isinstance(config.get(k), str) and config[k] for k in ('store_id', 'instance_id', 'project_id', 'workspace_id')),
                'STORE_CONFIG', 'Store identity fields are missing or invalid', status='blocked')
        require(isinstance(config.get('resources'), dict) and all(isinstance(k, str) and isinstance(v, str) and v for k, v in config['resources'].items()),
                'STORE_CONFIG', 'Resource bindings must be a string map', status='blocked')
        return config

    def connect(self, *, readonly=False):
        require(sqlite3.sqlite_version_info >= (3, 37, 0), 'SQLITE_VERSION', 'SQLite 3.37+ is required', status='blocked')
        require(self.db_path.is_file(), 'STORE_NOT_FOUND', 'Store does not exist', status='blocked')
        con = sqlite3.connect(f'file:{quote(str(self.db_path))}?mode={"ro" if readonly else "rw"}', uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA busy_timeout=5000')
        if readonly: con.execute('PRAGMA query_only=ON')
        try:
            version = con.execute('SELECT max(version) FROM schema_migrations').fetchone()[0]
            require(version == SCHEMA, 'STORE_VERSION', 'Unsupported store schema', status='blocked')
            actual = con.execute('SELECT migration_digest FROM schema_migrations WHERE version=?', (version,)).fetchone()[0]
            expected = sha(Path(__file__).with_name('schema.sql').read_bytes())
            require(actual == expected, 'STORE_VERSION', 'Development schema differs; preserve the existing store and use a fresh v2 workspace', status='blocked')
        except sqlite3.DatabaseError as exc:
            con.close()
            raise Fault('STORE_CORRUPT', 'Store schema cannot be read; original file preserved', status='runtime_error') from exc
        except BaseException:
            con.close()
            raise
        return con

    @contextmanager
    def transaction(self):
        con = self.connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            yield con
            con.commit()
        except BaseException:
            con.rollback(); raise
        finally:
            con.close()

    @contextmanager
    def read(self):
        con = self.connect(readonly=True)
        try:
            # All queries in one input package observe the same SQLite snapshot.
            con.execute('BEGIN')
            yield con
        finally:
            con.rollback()
            con.close()

    def initialize(self, name):
        with file_lock(self.home / '.init.lock'):
            if self.db_path.exists() or self.config_path.exists():
                config = self.config()
                with self.read() as con:
                    require(con.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'STORE_CORRUPT', 'Integrity check failed', status='runtime_error')
                return {**config, 'initialized': False}
            try:
                tracked = subprocess.run(['git', '-C', str(self.root), 'ls-files', '--', '.sdlc'], capture_output=True, timeout=5)
                require(not tracked.stdout.strip(), 'TRACKED_RUNTIME', '.sdlc is tracked; choose a fresh local workspace', status='blocked')
            except FileNotFoundError:
                pass
            project, workspace, instance = uid(), uid(), uid()
            config = {'format_version': 2, 'store_id': uid(), 'instance_id': instance,
                      'database': 'store.sqlite3', 'project_id': project, 'workspace_id': workspace,
                      'active_change_id': None, 'resources': {'main': '.'}, 'root_path': str(self.root)}
            self.home.mkdir(exist_ok=True)
            temporary = self.home / ('.init-' + uid() + '.sqlite3')
            schema = Path(__file__).with_name('schema.sql').read_text()
            con = sqlite3.connect(temporary)
            con.execute('PRAGMA foreign_keys=ON')
            try:
                con.executescript('BEGIN IMMEDIATE;\n' + schema)
                con.execute('INSERT INTO schema_migrations VALUES (?,?,?)', (SCHEMA, sha(schema.encode()), now()))
                con.execute('INSERT INTO projects VALUES (?,?,?)', (project, name, now()))
                con.execute('INSERT INTO workspaces VALUES (?,?,?,?,?)', (workspace, project, self.root.name, instance, now()))
                con.commit()
            except BaseException:
                con.rollback(); raise
            finally:
                con.close()
            os.replace(temporary, self.db_path)
            atomic_write(self.config_path, canonical(config) + b'\n')
            atomic_write(self.home / '.gitignore', b'*\n')
            for folder in ('runs', 'assets', 'changes', 'exports'):
                (self.home / folder).mkdir(exist_ok=True)
            return {**config, 'initialized': True}

    def resource(self, key='main'):
        config = self.config()
        require(key in config['resources'], 'RESOURCE_NOT_FOUND', f'Unknown resource: {key}', status='blocked')
        location = Path(config['resources'][key]).expanduser()
        return (location if location.is_absolute() else self.root / location).resolve()

    def put_asset(self, con, project, raw, media='application/octet-stream', *, limit=64*1024*1024):
        require(isinstance(raw, bytes) and len(raw) <= limit, 'ASSET_LIMIT', 'Asset exceeds the configured byte budget')
        hashed = sha(raw)
        path = safe_path(self.home, f'assets/{hashed[:2]}/{hashed[2:4]}/{hashed}')
        if path.exists():
            require(sha(path.read_bytes()) == hashed, 'ASSET_CORRUPT', 'Existing managed asset has a different digest', status='runtime_error')
        else:
            atomic_write(path, raw)
        row = con.execute('SELECT asset_id FROM assets WHERE project_id=? AND sha256=?', (project, hashed)).fetchone()
        if row: return row['asset_id']
        asset = uid()
        con.execute('INSERT INTO assets VALUES (?,?,?,?,?,?)', (asset, project, hashed, len(raw), media, now()))
        return asset

    def asset_bytes(self, con, asset_id, project):
        row = one(con, 'SELECT * FROM assets WHERE asset_id=? AND project_id=?', (asset_id, project))
        h = row['sha256']
        require(len(h) == 64 and all(c in '0123456789abcdef' for c in h), 'ASSET_CORRUPT', 'Invalid asset digest', status='runtime_error')
        p = safe_path(self.home, f'assets/{h[:2]}/{h[2:4]}/{h}')
        require(p.is_file(), 'ASSET_MISSING', 'Required asset is missing', status='blocked')
        raw = p.read_bytes()
        require(len(raw) == row['size_bytes'] and sha(raw) == h, 'ASSET_CORRUPT', 'Asset integrity mismatch', status='runtime_error')
        return raw

    def inspect_assets(self, con, project):
        """Read-only bounded inventory; never deletes bytes or follows symlinks."""
        registered = {r[0] for r in con.execute('SELECT sha256 FROM assets')}
        selected = {r['sha256']: r['asset_id'] for r in con.execute('SELECT asset_id,sha256 FROM assets WHERE project_id=?', (project,))}
        base = safe_path(self.home, 'assets')
        seen, orphaned, invalid, count = set(), [], [], 0
        for folder, directories, files in os.walk(base, followlinks=False):
            parent = Path(folder)
            count += len(directories)+len(files)
            require(count <= 50000, 'ASSET_INVENTORY_LIMIT', 'Asset inventory exceeds 50000 entries; no files changed', status='blocked')
            for name in list(directories):
                path = parent/name
                if path.is_symlink() or len(path.relative_to(base).parts) > 2:
                    invalid.append(path.relative_to(base).as_posix())
                    directories.remove(name)
            for name in files:
                path = parent/name
                relative = path.relative_to(base).as_posix()
                if path.is_symlink() or not path.is_file() or len(name) != 64 or any(c not in '0123456789abcdef' for c in name) or relative != f'{name[:2]}/{name[2:4]}/{name}':
                    invalid.append(relative)
                    continue
                seen.add(name)
                if name not in registered:
                    orphaned.append({'path': 'assets/'+relative, 'sha256_name': name, 'size_bytes': path.stat().st_size})
        return {'project_asset_count': len(selected), 'unregistered_files': sorted(orphaned, key=lambda r: r['path']),
                'missing_assets': [{'asset_id': selected[h], 'sha256': h} for h in sorted(set(selected)-seen)],
                'invalid_paths': sorted(invalid), 'integrity_verified': False,
                'scope': 'Workspace inventory; unregistered means absent from every project asset registry. No cleanup or byte-integrity claim.'}

    def content(self, con, revision):
        result = {'revision': dict(one(con, 'SELECT * FROM revisions WHERE revision_id=?', (revision,)))}
        for table in CONTENT_TABLES:
            result[table] = sorted([dict(row) for row in con.execute(f'SELECT * FROM {table} WHERE revision_id=?', (revision,))], key=lambda r: canonical(r))
        return result

    def content_digest(self, con, revision):
        content = self.content(con, revision)
        for key in ('revision_id', 'generation', 'state', 'digest', 'created_at'):
            content['revision'].pop(key, None)
        for table in CONTENT_TABLES:
            for row in content[table]: row.pop('revision_id')
        links = []
        for row in con.execute('SELECT a.sha256,l.source_id,l.design_id,l.original_name,l.purpose,l.ordinal FROM asset_links l JOIN assets a USING(asset_id) WHERE l.revision_id=?', (revision,)):
            links.append(dict(row))
        content['attachments'] = sorted(links, key=canonical)
        return digest(content)


def one(con, sql, args=(), *, code='NOT_FOUND'):
    row = con.execute(sql, args).fetchone()
    require(row is not None, code, 'Requested object does not exist', status='blocked')
    return row


def insert(con, table, row):
    # table/column identifiers originate from fixed implementation declarations.
    keys = tuple(row)
    con.execute(f'INSERT INTO {table} ({",".join(keys)}) VALUES ({",".join("?" for _ in keys)})', tuple(row.values()))
