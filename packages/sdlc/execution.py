"""Observed code and bounded command evidence. No model text becomes command PASS."""
from __future__ import annotations
import fnmatch
import os
import platform
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from .common import Fault, atomic_write, canonical, digest, loads, now, redact, require, safe_path, sha, uid
from .storage import insert

IGNORED = {'.git', '.sdlc', '__pycache__', '.pytest_cache', '.venv', 'node_modules', 'target', '.DS_Store'}
BUILD_FILES = {'pom.xml', 'go.mod', 'go.sum', 'requirements.txt', 'requirements.lock', 'pyproject.toml',
               'uv.lock', 'package.json', 'package-lock.json', 'Makefile', 'mvnw'}
ENV_ALLOWED = {'PATH', 'JAVA_HOME', 'GOPROXY', 'GOTOOLCHAIN', 'GOCACHE', 'GOPATH', 'GOFLAGS',
               'PYTHONDONTWRITEBYTECODE', 'PYTHONPATH', 'LANG', 'LC_ALL', 'MAVEN_OPTS', 'JAVA_TOOL_OPTIONS'}


def in_scope(relative, patterns):
    return any(p in {'.', '**', '**/*'} or relative == p or relative.startswith(p.rstrip('/')+'/')
               or fnmatch.fnmatchcase(relative, p) or (p.startswith('**/') and fnmatch.fnmatchcase(relative, p[3:])) for p in patterns)


def environment(overrides=None):
    overrides = overrides or {}
    require(isinstance(overrides, dict), 'INVALID_ENVIRONMENT', 'Expected environment map', '/payload/environment')
    for name, value in overrides.items():
        require(name in ENV_ALLOWED and isinstance(value, str) and '\x00' not in value, 'INVALID_ENVIRONMENT',
                'Only explicit non-secret toolchain variables are accepted', '/payload/environment/'+name)
    env = {k: os.environ[k] for k in ENV_ALLOWED if k in os.environ}
    env.update(overrides)
    env.setdefault('PATH', os.defpath)
    env.update(PYTHONDONTWRITEBYTECODE='1', GOPROXY='off', GOTOOLCHAIN='local')
    # Java supports a documented fork backend, preserving ordinary Maven/JUnit
    # subprocesses while the sandbox rejects posix_spawn session/group escapes.
    fork_option = '-Djdk.lang.Process.launchMechanism=FORK'
    options = env.get('JAVA_TOOL_OPTIONS', '')
    if fork_option not in options.split():
        env['JAVA_TOOL_OPTIONS'] = (options+' '+fork_option).strip()
    return env


def environment_identity(env, argv=None):
    tools = {}
    names = ([argv[0]] if argv else [])
    if env.get('JAVA_HOME'):
        names.append(str(Path(env['JAVA_HOME'])/'bin/java'))
    for name in names:
        binary = shutil.which(name, path=env.get('PATH'))
        if binary and Path(binary).is_file():
            path = Path(binary).resolve()
            tools[path.name] = sha(path.read_bytes())
    dependencies = []
    roots = [Path(p) for p in env.get('PYTHONPATH', '').split(os.pathsep) if p]
    if argv and (binary := shutil.which(argv[0], path=env.get('PATH'))):
        # A venv may symlink the same interpreter while loading different packages.
        prefix = Path(binary).absolute().parent.parent
        if (prefix/'pyvenv.cfg').is_file():
            roots.extend(sorted((prefix/'lib').glob('python*/site-packages')))
    for root in roots:
        records = []
        require(root.is_absolute() and root.is_dir(), 'ENVIRONMENT_PATH', 'Dependency paths must identify existing absolute directories', status='blocked')
        for directory, dirs, files in os.walk(root, followlinks=False):
            require(not any((Path(directory)/name).is_symlink() for name in dirs+files),
                    'DEPENDENCY_SYMLINK', 'Resolve dependency symlinks into an isolated directory before verification', status='blocked')
            dirs[:] = sorted(d for d in dirs if d not in {'__pycache__', '.git', '.sdlc', '.pytest_cache'})
            for name in sorted(files):
                if name.endswith('.pyc'):
                    continue
                file = Path(directory)/name
                require(file.is_file() and file.stat().st_size <= 128*1024*1024, 'ENVIRONMENT_LIMIT', 'Dependency file exceeds the hashing limit', status='blocked')
                records.append({'path': file.relative_to(root).as_posix(), 'sha256': sha(file.read_bytes())})
                require(len(records) <= 50000, 'ENVIRONMENT_LIMIT', 'Dependency tree exceeds the hashing limit', status='blocked')
        dependencies.append(digest(records))
    stable_env = {k: v for k, v in env.items() if k not in {'PATH', 'JAVA_HOME', 'GOPATH', 'GOCACHE', 'PYTHONPATH', 'TMPDIR'}}
    return {'platform': platform.system(), 'machine': platform.machine(), 'python': platform.python_version(),
            'tools': tools, 'dependencies': dependencies, 'variables': stable_env}


def observe(root, patterns=None, env=None, argv=None):
    """Digest selected bytes and shared build inputs; HEAD is provenance, not identity."""
    root = Path(root).resolve()
    patterns = patterns or ['.']
    files = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            relative = (Path(directory)/name).relative_to(root).as_posix()
            if name not in IGNORED and in_scope(relative, patterns):
                require(not (Path(directory)/name).is_symlink(), 'SUBJECT_SYMLINK',
                        'Resolve source directory symlinks before capturing a closed input snapshot', relative, status='blocked')
        dirs[:] = sorted(d for d in dirs if d not in IGNORED)
        for name in sorted(names):
            if name in IGNORED or name.endswith(('.pyc', '.class')) or name.startswith('.env'):
                continue
            path = Path(directory)/name
            relative = path.relative_to(root).as_posix()
            if not (in_scope(relative, patterns) or name in BUILD_FILES):
                continue
            safe_path(root, relative)
            require(path.is_file() and path.stat().st_size <= 64*1024*1024, 'SUBJECT_LIMIT', 'Subject file exceeds 64 MiB', relative, status='blocked')
            files.append({'path': relative, 'sha256': sha(path.read_bytes()), 'size': path.stat().st_size, 'mode': path.stat().st_mode & 0o777})
            require(len(files) <= 20000, 'SUBJECT_LIMIT', 'Subject exceeds 20000 files', status='blocked')
    env_identity = environment_identity(env or environment(), argv)
    files.sort(key=lambda row: row['path'])
    def git(*args):
        try:
            r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=5)
            return r.stdout if r.returncode == 0 else b''
        except (OSError, subprocess.TimeoutExpired):
            return b''
    return {'files': files, 'digest': digest(files), 'environment': env_identity,
            'environment_digest': digest(env_identity), 'head_commit': git('rev-parse', 'HEAD').decode().strip() or None,
            'tree_id': git('rev-parse', 'HEAD^{tree}').decode().strip() or None,
            'patch': git('diff', '--binary', 'HEAD', '--', *[f['path'] for f in files])}


def snapshot(store, con, project, run, observed, *, resource='main'):
    # Preserve actual input files, including untracked bytes, alongside the patch.
    archived = []
    root = store.resource(resource)
    for record in observed['files']:
        raw = safe_path(store.resource(record.get('resource', resource)), record['path']).read_bytes()
        path = safe_path(store.resource(record.get('resource', resource)), record['path'])
        require(sha(raw) == record['sha256'] and (path.stat().st_mode & 0o777) == record['mode'], 'SUBJECT_CHANGED', 'File changed while capturing snapshot', record['path'], status='conflict')
        asset = store.put_asset(con, project, raw)
        archived.append({**record, 'asset_id': asset})
    patch_asset = store.put_asset(con, project, observed['patch'], 'text/x-diff') if observed['patch'] else None
    value = uid()
    insert(con, 'code_snapshots', {'snapshot_id': value, 'project_id': project, 'run_id': run,
           'resource_key': resource, 'head_commit': observed['head_commit'], 'tree_id': observed['tree_id'],
           'patch_asset_id': patch_asset, 'untracked_json': canonical(archived).decode(),
           'files_json': canonical(observed['files']).decode(), 'environment_digest': observed['environment_digest'],
           'digest': observed['digest'], 'captured_at': now()})
    return value


def sandbox_profile(writable, work):
    require(sys.platform == 'darwin', 'SANDBOX_UNAVAILABLE',
            'This command collector requires the supported macOS sandbox; no silent fallback', status='blocked')
    # SBPL literals are escaped JSON strings, never shell arguments.
    rules = ['(version 1)', '(deny default)', '(allow process* sysctl-read mach-lookup signal)', '(allow file-read*)',
             '(deny syscall-unix (syscall-number 82) (syscall-number 147) (syscall-number 244))',
             '(allow file-write* (literal "/dev/null"))', '(allow file-write* (subpath '+canonical(str(work/'tmp')).decode()+'))']
    for root, pattern in writable:
        root = Path(root).resolve()
        require(pattern and '..' not in Path(pattern).parts, 'UNSAFE_PATH', 'Unsafe write scope')
        if pattern in {'.', '**', '**/*'}:
            rule = '(subpath '+canonical(str(root)).decode()+')'
        elif not any(char in pattern for char in '*?['):
            rule = '(subpath '+canonical(str(safe_path(root, pattern))).decode()+')'
        else:
            import re
            expression = re.escape(str(root)+'/'+pattern).replace(r'\*\*', '.*').replace(r'\*', '[^/]*').replace(r'\?', '[^/]')
            rule = '(regex '+canonical('^'+expression+'$').decode()+')'
        protected = [root/'.git', root/'.sdlc', work]
        guards = ''.join(' (require-not (subpath '+canonical(str(p)).decode()+'))' for p in protected)
        rules.append('(allow file-write* (require-all '+rule+guards+'))')
    return '\n'.join(rules)+'\n'


def run_command(argv, cwd, work, writable, *, env=None, timeout=60, output_limit=1024*1024):
    require(isinstance(argv, list) and argv and all(isinstance(s, str) and '\x00' not in s for s in argv), 'INVALID_ARGV', 'Expected argv string array')
    require(type(timeout) is int and 0 < timeout <= 3600, 'TIMEOUT_LIMIT', 'Timeout must be between 1 and 3600 seconds')
    work = Path(work).resolve()
    cwd = Path(cwd).resolve()
    work.mkdir(parents=True, exist_ok=True)
    (work/'tmp').mkdir(exist_ok=True)
    env = environment(env)
    env['TMPDIR'] = str(work/'tmp')
    profile = sandbox_profile(writable, work)
    atomic_write(work/'sandbox.sb', profile.encode())
    wrapped = [sys.executable, '-I', '-B', str(Path(__file__).with_name('sandbox_worker.py')), str(work/'sandbox.sb'), *argv]
    started = now()
    clock = time.monotonic()
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    totals = {'stdout': 0, 'stderr': 0}
    persisted = {'stdout': 0, 'stderr': 0}
    for name in buffers:
        atomic_write(work/(name+'.log'), b'')
    problem = None
    killed = False
    try:
        process = subprocess.Popen(wrapped, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    except OSError as exc:
        raise Fault('TOOL_START_FAILED', str(exc), status='blocked') from exc
    atomic_write(work/'process.json', canonical({'pid': process.pid, 'started_at': started, 'argv': redact(argv)})+b'\n')
    selector = selectors.DefaultSelector()
    for name, pipe in (('stdout', process.stdout), ('stderr', process.stderr)):
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ, name)
    try:
        while selector.get_map() or process.poll() is None:
            if time.monotonic()-clock > timeout:
                problem = 'TOOL_TIMEOUT'
            if problem and not killed:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                killed = True
            for key, _ in selector.select(0.1):
                raw = os.read(key.fileobj.fileno(), 65536)
                if not raw:
                    selector.unregister(key.fileobj)
                    continue
                name = key.data
                totals[name] += len(raw)
                room = max(0, output_limit-len(buffers[name]))
                buffers[name].extend(raw[:room])
                # Persist received complete lines during execution. A hard-killed
                # collector must not lose already flushed tool diagnostics. The
                # unfinished line stays buffered until EOF to avoid exposing a
                # partially received secret; these logs never establish PASS.
                complete = buffers[name].rfind(b'\n')+1
                if complete > persisted[name]:
                    atomic_write(work/(name+'.log'), redact(buffers[name][:complete].decode('utf-8', errors='replace')).encode())
                    persisted[name] = complete
                if len(raw) > room:
                    problem = 'OUTPUT_LIMIT'
        exit_code = process.wait()
        # A successful parent cannot leave an unobserved background tool alive.
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            pass
        else:
            problem = problem or 'TOOL_DESCENDANTS'
            os.killpg(process.pid, signal.SIGKILL)
    finally:
        selector.close()
        for pipe in (process.stdout, process.stderr):
            pipe.close()
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    outputs = {name: redact(raw.decode('utf-8', errors='replace')) for name, raw in buffers.items()}
    if exit_code == 71 and 'sdlc sandbox unavailable:' in outputs['stderr']:
        problem = 'SANDBOX_UNAVAILABLE'
    for name, text in outputs.items():
        atomic_write(work/(name+'.log'), (text+('\n[OUTPUT TRUNCATED]\n' if totals[name] > output_limit else '')).encode())
    return {'source_kind': 'command', 'argv': redact(argv), 'started_at': started, 'finished_at': now(),
            'duration_ms': int((time.monotonic()-clock)*1000), 'exit_code': exit_code,
            'status': 'pass' if exit_code == 0 and problem is None else 'blocked' if problem == 'SANDBOX_UNAVAILABLE' else 'fail',
            'error_code': problem, 'output_bytes': totals, 'truncated': any(n > output_limit for n in totals.values()),
            'stdout': outputs['stdout'], 'stderr': outputs['stderr'], 'sandbox': 'macos-seatbelt',
            'environment': environment_identity(env, argv)}
