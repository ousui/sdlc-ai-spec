#!/usr/bin/env python3
"""Execute real IMP scenarios using only a separately installed production runtime."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from test_late_phase_runtime_independence import ROOT, copy_plugin, parsed, scan_runtime

# The development harness stays outside the plugin. -I excludes development
# sys.path/PYTHONPATH; the audit hook observes the installed CLI and permits Git
# status plus the two fixed isolated Check adapters, never arbitrary commands.
AUDIT_RUNNER = r'''
import fcntl, json, os, runpy, sys, tempfile
from pathlib import Path
runtime, project, policy = map(str, sys.argv[1:4])
arguments = sys.argv[4:]
runtime, project = Path(runtime).resolve(), Path(project).resolve()
plugin = runtime.parents[3]
system_temporary = Path(tempfile.gettempdir()).resolve()
counts = dict(network_operations=0, dependencies_installed=0, git_ref_mutations=0,
              read_only_project_writes=0, product_writes=0, project_scans=0,
              pre_write_readbacks=0, forbidden_operations=0, violations=[])

def reject(key, message):
    counts[key] += 1
    counts['violations'].append(message)
    raise RuntimeError(message)

def location(value, dir_fd=None):
    if not isinstance(value, (str, bytes, os.PathLike)):
        return None
    path = Path(os.fsdecode(value))
    try:
        if not path.is_absolute() and isinstance(dir_fd, int) and dir_fd >= 0:
            try:
                parent = Path(os.readlink('/proc/self/fd/' + str(dir_fd)))
            except OSError:
                raw = fcntl.fcntl(dir_fd, 50, b'\0' * 1024)
                parent = Path(raw.split(b'\0', 1)[0].decode())
            path = parent / path
        return path.resolve()
    except OSError as exc:
        raise RuntimeError('audit location failed: value=' + repr(value) +
                           ' dir_fd=' + repr(dir_fd)) from exc

def touch(value, write=False, scan=False, dir_fd=None):
    path = location(value, dir_fd)
    if path is None:
        return
    if path.is_relative_to(project):
        if policy == 'meta':
            reject('project_scans', 'meta command accessed the project')
        if write:
            if policy != 'write':
                reject('read_only_project_writes', 'read-only command attempted a project write')
            if path.is_relative_to(project / '.git'):
                reject('git_ref_mutations', 'runtime attempted a Git control write')
            if not path.is_relative_to(project / '.sdlc'):
                # apply_operations calls mkdir(exist_ok=True) on this already
                # existing claimed parent before opening the one product file.
                if path == project / 'integration' and path.is_dir():
                    return
                if path != project / 'integration/app.txt':
                    reject('forbidden_operations', 'product write outside the fixture Claim Scope: ' + str(path))
                from packages.sdlc_artifact_store import ArtifactStore
                from packages.sdlc_claim_provider import ClaimProvider
                store = ArtifactStore.open_read_only(project)
                provider = ClaimProvider.open_read_only(project)
                from packages.sdlc_artifact_store.catalog import ArtifactCatalog
                artifacts = ArtifactCatalog(store).list_artifacts('IMP')
                if len(artifacts) != 1:
                    reject('forbidden_operations', 'product write without a unique IMP Reservation')
                claim = provider.resolve_artifact(artifacts[0].artifact_id)
                stored = store.read_revision(claim.artifact_id, claim.revision)
                state = json.loads(next(m.raw_bytes for m in stored.payload.members if m.member_id == 'IMP-STATE'))
                if claim.state != 'active' or stored.control.state != 'open' or state['stage'] != 'prepared' or not state['pre_execution']:
                    reject('forbidden_operations', 'product write preceded Claim/Baseline readback')
                if not any(m.member_id == 'EVD-PRE' for m in stored.payload.members):
                    reject('forbidden_operations', 'missing pre-execution Evidence')
                counts['pre_write_readbacks'] += 1
                counts['product_writes'] += 1
    elif any(parent.parent == system_temporary and parent.name.startswith('sdlc-imp-check-')
             for parent in (path, *path.parents)):
        # project_command owns one automatically cleaned isolated snapshot;
        # neither the installed Plugin nor the real project is writable there.
        return
    elif write:
        reject('forbidden_operations', 'runtime wrote outside the project: ' + str(path) +
               '; temp=' + str(system_temporary))
    elif any(part in {'docs', 'tests', 'AGENTS.md', 'CLAUDE.md', 'HANDOFF.md'} for part in path.parts):
        reject('forbidden_operations', 'runtime read a development resource')
    elif policy == 'meta' and scan and not path.is_relative_to(plugin) and path == Path.cwd():
        reject('project_scans', 'meta command scanned its external CWD')

def audit(event, args):
    if event.startswith('socket.'):
        reject('network_operations', 'runtime attempted network access')
    if event == 'import' and (args[0] == 'tests' or args[0].startswith('tests.')):
        reject('forbidden_operations', 'runtime imported a test module')
    if event == 'subprocess.Popen':
        executable, command, cwd, environment = args
        if not isinstance(command, (tuple, list)):
            reject('forbidden_operations', 'runtime attempted a shell command')
        words = {str(word) for word in command}
        if words & {'pip', 'pip3', 'npm', 'npx', 'mvn', 'maven', 'gradle'}:
            reject('dependencies_installed', 'runtime attempted dependency management')
        if 'git' in words and words & {'commit', 'push', 'merge', 'tag', 'update-ref'}:
            reject('git_ref_mutations', 'runtime attempted Git mutation')
        git_status = command == ['git', '-C', str(project), 'status', '--porcelain=v1', '-z', '--untracked-files=all']
        local_check = (len(command) == 8 and command[:4] == [sys.executable, '-I', '-B', '-S']
                       and command[4] == str(runtime.with_name('imp_check.py'))
                       and location(command[6]).is_relative_to(project))
        project_check = (len(command) >= 9 and command[:4] == [sys.executable, '-I', '-B', '-S']
                         and command[4] == str(runtime.with_name('imp_project_check.py'))
                         and location(command[5]).parent == system_temporary
                         and location(command[5]).name.startswith('sdlc-imp-check-')
                         and command[6:8] == ['-m', 'unittest'])
        if policy == 'meta' or not (git_status or local_check or project_check):
            reject('forbidden_operations', 'runtime attempted an undeclared subprocess')
    if event in {'os.system', 'os.posix_spawn', 'os.exec', 'os.fork'}:
        reject('forbidden_operations', 'runtime attempted an unaudited process')
    if event == 'sqlite3.connect':
        database = str(args[0])
        if policy == 'meta':
            reject('project_scans', 'meta command accessed SQLite')
        if policy == 'read' and (not database.startswith('file:') or 'mode=ro' not in database):
            reject('read_only_project_writes', 'check opened a writable SQLite connection')
    if event == 'open':
        flags = args[2] or 0
        touch(args[0], bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
    if event in {'os.scandir', 'os.listdir'}:
        touch(args[0], scan=True)
    if event in {'os.mkdir', 'os.chmod'}:
        touch(args[0], write=True, dir_fd=args[2] if len(args) > 2 else None)
    if event in {'os.remove', 'os.rmdir'}:
        touch(args[0], write=True, dir_fd=args[1] if len(args) > 1 else None)
    if event in {'os.truncate', 'os.utime', 'os.symlink', 'os.link'}:
        touch(args[0], write=True)
    if event in {'os.rename'}:
        touch(args[0], write=True, dir_fd=args[2] if len(args) > 2 else None)
        touch(args[1], write=True, dir_fd=args[3] if len(args) > 3 else None)

sys.addaudithook(audit)
sys.argv = [str(runtime), *arguments]
try:
    runpy.run_path(str(runtime), run_name='__main__')
finally:
    print('IMP_AUDIT=' + json.dumps(counts, sort_keys=True), file=sys.stderr)
'''


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def tree_state(root, *, product_only=False):
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if product_only and relative.parts[0] == '.sdlc':
            continue
        info = path.stat()
        result[relative.as_posix()] = (info.st_mode, info.st_mtime_ns if path.is_file() else None,
                                      hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None)
    return result


class InstalledRuntime:
    def __init__(self, plugin, outside):
        self.plugin, self.outside = plugin, outside
        self.entry = plugin / 'skills/sdlc-400-imp/scripts/runtime.py'
        self.audits = []

    def invoke(self, project, arguments, *, inputs=None, policy='read'):
        before = tree_state(project)
        plugin_before, cwd_before = tree_state(self.plugin), tree_state(self.outside)
        completed = subprocess.run(
            [sys.executable, '-I', '-B', '-c', AUDIT_RUNNER, str(self.entry), str(project), policy,
             *arguments, *([] if policy == 'meta' else ['-p', str(project)]), '-f', 'json'],
            cwd=self.outside, input=json.dumps({'inputs': inputs or {}}), text=True,
            capture_output=True, timeout=60, check=False,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'GIT_OPTIONAL_LOCKS': '0',
                 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_TERMINAL_PROMPT': '0'},
        )
        result = parsed(completed)
        lines = completed.stderr.splitlines()
        require(len(lines) == 1 and lines[0].startswith('IMP_AUDIT='),
                f'installed runtime audit failed: {completed.stderr}')
        audit = json.loads(lines[0].split('=', 1)[1])
        for field in ('network_operations', 'dependencies_installed', 'git_ref_mutations',
                      'read_only_project_writes', 'project_scans', 'forbidden_operations'):
            require(audit[field] == 0, f'{field}: {audit}; result={result}')
        require(tree_state(self.plugin) == plugin_before, 'runtime modified its installed plugin')
        require(tree_state(self.outside) == cwd_before, 'runtime modified the external CWD')
        if policy in {'meta', 'read'}:
            require(tree_state(project) == before, 'read-only command modified project bytes, modes or mtimes')
        self.audits.append(audit)
        return completed.returncode, result, audit


@contextmanager
def fixture():
    # Only the driver imports development fixture builders. Their real Stores,
    # frozen upstream Artifacts and initial Git commit exist before measurement.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tests.skill_imp.support import ImpFixture
    value = ImpFixture()
    try:
        value.setUp()
        yield value
    finally:
        value.tearDown()


def main():
    with tempfile.TemporaryDirectory(prefix='sdlc-imp-installed-') as temporary:
        workspace = Path(temporary)
        plugin, outside, empty = workspace / 'plugin', workspace / 'cwd', workspace / 'empty'
        outside.mkdir()
        empty.mkdir()
        copy_plugin(plugin, 'sdlc-400-imp')
        scan_runtime(plugin)
        require({p.name for p in plugin.iterdir()} == {'packages', 'scripts', 'skills'}, 'invalid plugin layout')
        require({p.name for p in (plugin / 'skills').iterdir()} == {'_shared', 'sdlc-400-imp'}, 'sibling Skill copied')
        runtime = InstalledRuntime(plugin, outside)
        for command in ('--help', '--version', '--commands', '--examples'):
            code, result, _ = runtime.invoke(empty, [command], policy='meta')
            require(code == 0 and result.get('ok') is True and result.get('effects') == [], f'meta failed: {result}')
        code, result, _ = runtime.invoke(empty, ['check', '-r', 'IMP-20990101000000-01@1'])
        require(code != 0 and result.get('ok') is False, 'missing Store did not fail closed')
        require(not (empty / '.sdlc').exists(), 'missing-store check created runtime state')
        with fixture() as value:
            from packages.sdlc_artifact_store import ArtifactStore, compute_sha256
            from packages.sdlc_claim_provider import ClaimProvider
            from packages.sdlc_runtime import parse_canonical_artifact
            from imp_result import read_state, snapshot_from_member
            (value.root / 'user-note.txt').write_text('staged user content\n')
            value.git('add', 'user-note.txt')
            (value.root / 'user-note.txt').write_text('staged user content\nunstaged user content\n')
            (value.root / 'untracked.txt').write_text('untracked user content\n')
            git_before = tree_state(value.root / '.git')
            method = value.implementation()
            args = ['create', '-b', value.binding, '--owner', 'installed-executor']
            for policy_args in (['--write-policy', 'deny'], ['--dry-run']):
                code, result, audit = runtime.invoke(value.root, args + policy_args, inputs={'implementation': method})
                require(result['next_action']['code'] == 'IMP_WRITE_DENIED' and audit['product_writes'] == 0,
                        f'Readiness/preview failed: {result}')
                require(value.claim_count() == 0, 'preview acquired a Claim')
            escaped = deepcopy(method)
            escaped['operations'].append({'op': 'write_text', 'resource': 'repo', 'path': 'outside.txt',
                                          'step': 'STEP-001', 'content': 'out of scope', 'expected_sha256': 'absent'})
            code, result, _ = runtime.invoke(value.root, args, inputs={'implementation': escaped})
            require(code != 0 and result['errors'][0]['code'] == 'IMP_SCOPE_VIOLATION', f'Scope escape accepted: {result}')
            code, opened, audit = runtime.invoke(value.root, args, inputs={'implementation': method}, policy='write')
            require(code == 2 and opened['artifact']['revision_state'] == 'open' and
                    audit['pre_write_readbacks'] == 1, f'create/readback failed: {opened}')
            require((value.root / 'integration/app.txt').read_text() == 'version=after\n', 'product operation did not execute')
            stored = value.stored(opened)
            state = read_state(stored)
            plan_id, revision = value.pln_reference.split('@')
            plan = ArtifactStore.open_read_only(value.root).read_revision(plan_id, int(revision))
            context = parse_canonical_artifact(plan.payload.primary_blob).front_matter['context']
            require(state['binding']['context_reference'] == context == value.context_reference, 'IMP Context differs from PLN')
            require(state['binding']['reference'] == value.binding and state['claim']['owner'] == 'installed-executor', 'Binding/Owner mismatch')
            baseline = snapshot_from_member(stored, state['resources'][0]['baseline_member'], 'repo')
            baseline_bytes = {item['path']: bytes.fromhex(item['content_hex']) for item in baseline['entries']}
            require(baseline_bytes['integration/app.txt'] == b'version=before\n', 'Baseline was captured after execution')
            for name in ('user-note.txt', 'untracked.txt'):
                require(baseline_bytes[name] == (value.root / name).read_bytes(), 'user changes were not retained in Baseline')
            code, completed, audit = runtime.invoke(value.root,
                ['revise', '-r', opened['artifact']['reference'], '--owner', 'installed-executor'],
                inputs={'final_confirmation': value.confirmation(opened)}, policy='write')
            require(code == 0 and completed['ok'] and completed['artifact']['revision_state'] == 'frozen', f'freeze failed: {completed}')
            claim = ClaimProvider.open_read_only(value.root).resolve(value.binding)
            require(claim.state == 'completed' and claim.owner == 'installed-executor', 'Claim not completed')
            frozen = value.stored(completed)
            row = read_state(frozen)['resources'][0]
            require(row['changed_paths'] == ['integration/app.txt'], 'Changed Scope includes another product')
            result_member = next(item for item in frozen.payload.members if item.member_id == row['result_member'])
            require(compute_sha256(result_member.raw_bytes) == result_member.sha256, 'Result Digest is not reproducible')
            snapshot = json.loads(result_member.raw_bytes)
            for entry in snapshot['entries']:
                require(hashlib.sha256(bytes.fromhex(entry['content_hex'])).hexdigest() == entry['sha256'], 'Result Entry digest mismatch')
            require(result_member.raw_bytes == json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode(),
                    'Result Snapshot is not canonical')
            stores_before = {
                'store.sqlite3': compute_sha256(
                    (value.root / '.sdlc/store.sqlite3').read_bytes()
                )
            }
            code, checked, _ = runtime.invoke(value.root, ['check', '-r', completed['artifact']['reference']])
            require(code == 0 and checked['ok'] and value.info(checked)['results'] == value.info(completed)['results'],
                    f'immutable Result check failed: {checked}')
            require(stores_before == {name: compute_sha256((value.root / '.sdlc' / name).read_bytes()) for name in stores_before},
                    'check changed ArtifactStore or Claim Store')
            require(value.stored(checked).payload == frozen.payload, 'check changed frozen Result')
            require(tree_state(value.root / '.git') == git_before, 'runtime mutated Git controls or refs')
        with fixture() as value:
            plan = value.plan()
            plan['work_items'][0]['execution_scope'] = ['resource:repo']
            upstream = value.execute_pln(plan=plan)
            binding = upstream['artifact']['reference'] + '#WI-001'
            (value.root / 'integration/test_installed.py').write_text(
                'from pathlib import Path\nimport unittest\n\n'
                'class InstalledTest(unittest.TestCase):\n'
                '    def test_marker(self):\n'
                '        self.assertEqual(Path("integration/app.txt").read_text(), "version=after\\n")\n'
            )
            method = value.implementation(binding=binding)
            method['steps'][0]['target'] = ['resource:repo']
            method['checks'] = [{
                'id': 'CHK-001', 'name': 'Installed isolated unit test',
                'kind': 'project_command', 'resource': 'repo', 'cwd': '.',
                'command': ['python', '-m', 'unittest', 'discover', '-s', 'integration',
                            '-p', 'test_installed.py'],
            }]
            code, opened, audit = runtime.invoke(
                value.root, ['create', '-b', binding, '--owner', 'installed-executor'],
                inputs={'implementation': method}, policy='write',
            )
            require(code == 2 and opened.get('artifact') is not None
                    and opened['gate']['result'] == 'pending',
                    f'installed project Check failed: {opened}')
            stored = value.stored(opened)
            evidence = json.loads(next(
                item.raw_bytes for item in stored.payload.members
                if item.member_id == 'EVD-CHK-001'
            ))
            require(evidence['contract'] == 'sdlc-ai-spec/imp-isolated-project-check/v1'
                    and evidence['sandbox'] == 'python-audit-hook'
                    and evidence['result'] == 'pass'
                    and audit['network_operations'] == 0,
                    f'installed project Check Evidence failed: {evidence}')
        with fixture() as value:
            git_before = tree_state(value.root / '.git')
            _, opened, _ = runtime.invoke(value.root, ['create', '-b', value.binding, '--owner', 'installed-executor'],
                                          inputs={'implementation': value.implementation()}, policy='write')
            require(opened['artifact']['revision_state'] == 'open', 'abandon fixture is not open')
            require(ClaimProvider.open_read_only(value.root).resolve(value.binding).state == 'active', 'abandon fixture Claim is not active')
            before = tree_state(value.root, product_only=True)
            code, abandoned, audit = runtime.invoke(value.root,
                ['abandon', '-r', opened['artifact']['reference'], '--owner', 'installed-executor'],
                inputs={'abandon_reason': 'Explicit installed fixture cancellation'}, policy='write')
            require(code == 0 and abandoned['ok'] and audit['product_writes'] == 0, f'abandon failed: {abandoned}')
            claim = ClaimProvider.open_read_only(value.root).resolve(value.binding)
            stored = value.stored(abandoned)
            require(claim.state == stored.control.state == 'abandoned', 'abandon did not close both authorities')
            require(claim.abandon_reason == stored.control.abandon_reason, 'abandon reasons differ')
            require(tree_state(value.root, product_only=True) == before, 'abandon modified products or Git')
            require(tree_state(value.root / '.git') == git_before, 'abandon scenario mutated Git')
    print('sdlc-imp runtime independence: PASS')
    print('development docs copied: 0')
    print('network operations: 0')
    print('dependencies installed: 0')
    print('git ref mutations: 0')
    print('read-only project writes: 0')
    print('create/check/abandon: PASS')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'sdlc-imp runtime independence: FAIL: {exc}', file=sys.stderr)
        raise SystemExit(1)
