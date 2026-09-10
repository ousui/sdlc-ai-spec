#!/usr/bin/env python3
"""Controlled upstream candidates. No LLM, downloads, pushes or automatic merge.

prepare creates a detached worktree and an external change record. Run the
installed-CLI verifier independently; accept validates its exact-byte report and
an explicit human review, then commits ONLY that candidate worktree. The current
branch and current dist are never overwritten by prepare/accept.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.venv', '__pycache__', '.pytest_cache'}


def run(*args: str, cwd: Path) -> str:
    result = subprocess.run(list(args), cwd=cwd, text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or 'Command failed')
    return result.stdout.strip()


def source_digest(root: Path) -> str:
    """Content AND executable modes; ignore only tool caches and Git internals."""
    records = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts) or path.suffix in ('.pyc', '.pyo'):
            continue
        if path.is_symlink():
            raise ValueError('Source snapshot contains a symlink: '+str(relative))
        if path.is_file():
            records[relative.as_posix()] = [hashlib.sha256(path.read_bytes()).hexdigest(),
                                            path.stat().st_mode & 0o111]
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


def blob(data: bytes) -> dict:
    return {'git_blob': hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
            'sha256': hashlib.sha256(data).hexdigest()}


def git_clean(root: Path) -> str:
    if Path(run('git', 'rev-parse', '--show-toplevel', cwd=root)).resolve() != root.resolve():
        raise ValueError('Select the repository root')
    if run('git', 'status', '--porcelain', '--untracked-files=all', cwd=root):
        raise ValueError('Worktree must be clean')
    return run('git', 'rev-parse', 'HEAD', cwd=root)


def candidate_lock(upstream: Path, old: dict, commit: str, tag: str) -> tuple[dict, list[dict]]:
    names = {'LICENSE'}
    names.update('templates/commands/'+name+'.md' for name in old['commands'])
    names.update('templates/'+p.name for p in (upstream/'templates').glob('*.md'))
    names.update('scripts/bash/'+p.name for p in (upstream/'scripts/bash').glob('*.sh'))
    selected = {name: blob((upstream/name).read_bytes()) for name in sorted(names)}
    watched = {name: blob((upstream/name).read_bytes()) for name in old.get('watch_files', {})}
    changes = []
    for group, new in [('files', selected), ('watch_files', watched)]:
        previous = old.get(group, {})
        for path in sorted(set(previous) | set(new)):
            if previous.get(path) != new.get(path):
                changes.append({'group': group, 'path': path,
                    'before': previous.get(path), 'after': new.get(path),
                    'review_required': True})
    # Discover newly added core commands; do not silently add or silently ignore.
    upstream_commands = {p.stem for p in (upstream/'templates/commands').glob('*.md')}
    supported = set(old['commands']) | set(old.get('excluded_commands', []))
    if upstream_commands != supported:
        raise ValueError('Core command inventory changed; review scope before preparing: '
                         + repr(sorted(upstream_commands ^ supported)))
    version = tomllib.loads((upstream/'pyproject.toml').read_text())['project']['version']
    if not isinstance(version, str) or not version:
        raise ValueError('Upstream package version is missing')
    return dict(old, commit=commit, tag=tag, version=version, files=selected, watch_files=watched), changes


def prepare(root: Path, upstream: Path, out: Path, ref: str) -> dict:
    root, upstream, out = root.resolve(), upstream.resolve(), out.absolute()
    if not ref or ref.startswith('-'):
        raise ValueError('An explicit upstream commit or tag is required')
    base = git_clean(root)
    upstream_head = git_clean(upstream)
    commit = run('git', 'rev-parse', '--verify', ref+'^{commit}', cwd=upstream)
    if upstream_head != commit:
        raise ValueError('Upstream checkout HEAD is not the selected ref')
    if out.exists() or out.is_symlink() or root == out or root in out.parents:
        raise ValueError('Candidate must be a new directory outside the source repository')
    record_path = out.parent/(out.name+'.upgrade.json')
    if record_path.exists():
        raise ValueError('Candidate record already exists')
    old = json.loads((root/'upstream.lock.json').read_text())
    new, changes = candidate_lock(upstream, old, commit, ref)
    out.parent.mkdir(parents=True, exist_ok=True)
    record = {'base_sha': base, 'base_lock_sha256': hashlib.sha256((root/'upstream.lock.json').read_bytes()).hexdigest(),
              'source_root': str(root), 'candidate_root': str(out), 'upstream_root': str(upstream),
              'upstream_sha': commit, 'changes': changes, 'status': 'PREPARING'}
    run('git', 'worktree', 'add', '--detach', str(out), base, cwd=root)
    try:
        (out/'upstream.lock.json').write_text(json.dumps(new, indent=2)+'\n')
        run(sys.executable, '-B', str(out/'tools/port.py'), '--upstream', str(upstream), cwd=out)
        run(sys.executable, '-B', str(out/'tools/build.py'), '--marketplaces', cwd=out)
        record.update(status='CANDIDATE_READY', candidate_digest=source_digest(out))
    except Exception as error:
        record.update(status='BLOCKED', error=str(error))
        raise
    finally:
        record_path.write_text(json.dumps(record, indent=2)+'\n')
    return record


def check_accept(record_path: Path, evidence: Path, review: Path) -> tuple[Path, dict]:
    record = json.loads(record_path.read_text())
    if record.get('status') != 'CANDIDATE_READY':
        raise ValueError('Candidate is not ready')
    candidate, source = Path(record['candidate_root']), Path(record['source_root'])
    if git_clean(source) != record['base_sha']:
        raise ValueError('Accepted source advanced; prepare a fresh candidate')
    if run('git', 'rev-parse', 'HEAD', cwd=candidate) != record['base_sha']:
        raise ValueError('Candidate base changed')
    # A prepared candidate remains detached; do not commit someone else's branch.
    head = subprocess.run(['git','symbolic-ref','-q','HEAD'],cwd=candidate,capture_output=True)
    if head.returncode == 0:
        raise ValueError('Candidate must remain a detached worktree')
    actual = source_digest(candidate)
    if actual != record['candidate_digest']:
        raise ValueError('Candidate was edited; prepare again with reviewed adapter changes')
    report = json.loads(evidence.read_text())
    if (report.get('status') != 'PASS' or report.get('source_digest') != actual
            or report.get('upstream_sha') != record['upstream_sha']):
        raise ValueError('Verification does not attest the exact candidate')
    if not report.get('checks') or not all(c.get('result') == 'PASS' for c in report['checks']):
        raise ValueError('Missing/failed verification checks')
    approval = json.loads(review.read_text())
    required = sorted({c['path'] for c in record['changes']})
    if (approval.get('decision') != 'accept' or not approval.get('reviewer')
            or approval.get('candidate_digest') != actual
            or sorted(approval.get('reviewed_paths', [])) != required):
        raise ValueError('Explicit review must bind this candidate and every changed upstream path')
    return candidate, record


def accept(record_path: Path, evidence: Path, review: Path, check_only: bool) -> dict:
    candidate, record = check_accept(record_path, evidence, review)
    if check_only:
        return {'status': 'ACCEPT_CHECK_PASS', 'candidate_digest': record['candidate_digest']}
    # Ordinary local Git commit; use the maintainer's configured identity.
    run('git', 'add', '-A', '--', '.', cwd=candidate)
    if run('git', 'diff', '--cached', '--name-only', cwd=candidate):
        run('git', 'commit', '-m', 'build: accept Spec Kit '+record['upstream_sha'], cwd=candidate)
    accepted = run('git', 'rev-parse', 'HEAD', cwd=candidate)
    record.update(status='ACCEPTED', accepted_commit=accepted)
    record_path.write_text(json.dumps(record, indent=2)+'\n')
    return {'status': 'ACCEPTED', 'commit': accepted,
            'note': 'Only the detached candidate was committed; source branch, remote refs and tags are unchanged.'}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    q = sub.add_parser('prepare')
    q.add_argument('--upstream', type=Path, required=True)
    q.add_argument('--ref', required=True)
    q.add_argument('--out', type=Path, required=True)
    q = sub.add_parser('accept')
    q.add_argument('--record', type=Path, required=True)
    q.add_argument('--evidence', type=Path, required=True, help='External verifier result.json')
    q.add_argument('--review', type=Path, required=True, help='External explicit review JSON')
    q.add_argument('--check', action='store_true')
    args = p.parse_args()
    try:
        result = (prepare(ROOT,args.upstream,args.out,args.ref) if args.action == 'prepare'
                  else accept(args.record,args.evidence,args.review,args.check))
        print(json.dumps(result, indent=2)); return 0
    except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired) as error:
        print('ERROR: '+str(error),file=sys.stderr);return 1


if __name__ == '__main__':
    raise SystemExit(main())
