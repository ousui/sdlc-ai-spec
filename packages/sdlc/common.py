"""Portable protocol primitives. No host-specific objects enter persisted data."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PHASES = ('REQ', 'DSN', 'PLN', 'IMP', 'VFY', 'RLS')
VERSION = '2.0.0-dev'
API = '2'
SCHEMA = 1
MAX_REQUEST_BYTES = 4 * 1024 * 1024


class Fault(Exception):
    def __init__(self, code: str, message: str, path: str = '', *, status: str = 'invalid_input', details=None):
        super().__init__(message)
        self.code, self.path, self.status, self.details = code, path, status, details

    def record(self):
        value = {'code': self.code, 'path': self.path, 'message': str(self)}
        if self.details is not None:
            value['details'] = self.details
        return value


def require(ok, code, message, path='', *, status='invalid_input', details=None):
    if not ok:
        raise Fault(code, message, path, status=status, details=details)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def uid() -> str:
    return str(uuid.uuid4())


def ident(value, path='') -> str:
    require(isinstance(value, str), 'INVALID_ID', 'Expected a UUID', path)
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise Fault('INVALID_ID', 'Expected a UUID', path) from exc
    require(str(parsed) == value, 'INVALID_ID', 'Use a lowercase canonical UUID', path)
    return value


def canonical(value) -> bytes:
    def check(v, depth=0):
        require(depth <= 64, 'JSON_DEPTH', 'JSON nesting exceeds 64 levels')
        if isinstance(v, dict):
            require(all(isinstance(k, str) for k in v), 'INVALID_JSON', 'Object keys must be strings')
            for x in v.values(): check(x, depth+1)
        elif isinstance(v, list) or isinstance(v, tuple):
            for x in v: check(x, depth+1)
        elif type(v) is int:
            require(-(2**63) <= v < 2**63, 'INVALID_JSON', 'Integer exceeds signed 64-bit range')
        elif type(v) is float:
            require(math.isfinite(v), 'INVALID_JSON', 'NaN and Infinity are not allowed')
            raise Fault('INVALID_JSON', 'Exact decimal values use strings in protocol v2')
        else:
            require(v is None or isinstance(v, (str, bool)), 'INVALID_JSON', 'Unsupported JSON value')
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def loads(raw):
    def pairs(items):
        obj = {}
        for k, v in items:
            require(k not in obj, 'INVALID_JSON', f'Duplicate JSON key: {k}')
            obj[k] = v
        return obj
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        canonical(value)
        return value
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise Fault('INVALID_JSON', str(exc)) from exc


def safe_path(root: Path, relative: str, *, allow_dot=False) -> Path:
    require(isinstance(relative, str) and relative and '\x00' not in relative and '\\' not in relative,
            'UNSAFE_PATH', 'Expected a portable relative path')
    p = Path(relative)
    require(not p.is_absolute() and '..' not in p.parts and (allow_dot or p.parts),
            'UNSAFE_PATH', 'Path escapes its resource')
    root = root.resolve()
    target = root / p
    cur = root
    for part in p.parts:
        cur = cur / part
        require(not cur.is_symlink(), 'UNSAFE_PATH', 'Symbolic links are not accepted for managed paths')
    require(target.resolve().is_relative_to(root), 'UNSAFE_PATH', 'Path escapes its resource')
    return target


def atomic_write(path: Path, raw: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.sdlc-write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, path)
        if os.name != 'nt':
            fd = os.open(path.parent, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


@contextmanager
def file_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.is_symlink(), 'UNSAFE_PATH', 'Lock may not be a symlink')
    with path.open('a+b') as f:
        try:
            if os.name == 'nt':
                import msvcrt
                if path.stat().st_size == 0: f.write(b'0'); f.flush()
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise Fault('WORKSPACE_BUSY', 'Another runtime operation owns this workspace', status='blocked') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_UN)


_SECRET_NAME = re.compile(r'(?:token|secret|password|passwd|api[_-]?key|authorization|cookie|private[_-]?key)', re.I)
_SECRET_TEXT = re.compile(r'(?i)(\b(?:password|passwd|api[_-]?key|token|secret|authorization)\b\s*[:=]\s*)([^\s,;]+)')


def redact(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if _SECRET_NAME.search(k) else redact(v) for k, v in value.items()}
    if isinstance(value, list): return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----.*?(?:-----END (?:[A-Z ]*PRIVATE KEY)-----|$)',
                       '[REDACTED PRIVATE KEY]', value, flags=re.S)
        value = re.sub(r'\b(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_-]+', '[REDACTED]', value)
        value = _SECRET_TEXT.sub(r'\1[REDACTED]', value)
        for key, secret in os.environ.items():
            if _SECRET_NAME.search(key) and len(secret) >= 8:
                value = value.replace(secret, '[REDACTED]')
        return value
    return value
