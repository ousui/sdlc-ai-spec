#!/usr/bin/env python3
"""Build an explicit, credential-free installed copy; never edit host settings."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'codex': '.codex-plugin', 'cursor': '.cursor-plugin', 'claude-code': '.claude-plugin'}
EXCLUDED = {'.git', '.local', '.cache', '__pycache__', 'docs', 'tests', 'evals', 'AGENTS.md', 'CLAUDE.md', 'HANDOFF.md'}
SOURCES = ('packages', 'scripts', 'skills', 'config/github', '.codex-plugin', '.claude-plugin', '.cursor-plugin')


def safe_path(path: Path) -> Path:
    if not path.is_absolute() or '..' in path.parts or path == Path('/'):
        raise ValueError('Explicit non-root absolute path required')
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError('Symbolic links in destination/data paths are not allowed')
        if ancestor.exists() and not ancestor.is_dir():
            raise ValueError('Destination/data path must be a directory')
    return path


def runtime_files(root: Path):
    for relative in SOURCES:
        base = root / relative
        if not base.is_dir() or base.is_symlink():
            raise ValueError('Missing or linked bundled resource')
        for current, directories, files in os.walk(base, followlinks=False):
            for name in list(directories):
                if (Path(current) / name).is_symlink():
                    raise ValueError('Linked source directory is not distributable')
            directories[:] = sorted(d for d in directories if d not in EXCLUDED)
            for name in sorted(files):
                if name in EXCLUDED or name.endswith(('.pyc', '.pyo')):
                    continue
                path = Path(current) / name
                if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
                    raise ValueError('Source must be a regular file')
                yield path.relative_to(root)


def render_config(host, python, plugin, data_root):
    server = {'command': str(python), 'args': [str(plugin/'scripts/sdlc_github_mcp.py'), '--data-root', str(data_root)]}
    if host == 'codex':
        server['env_vars'] = ['SDLC_GITHUB_TOKEN']
    else:
        server['env'] = {'SDLC_GITHUB_TOKEN': '${env:SDLC_GITHUB_TOKEN}' if host == 'cursor' else '${SDLC_GITHUB_TOKEN}'}
    return {'mcpServers': {'sdlc_github': server}}


def install(host, destination: Path, data_root: Path, python: Path, *, source=ROOT):
    destination, data_root = safe_path(destination), safe_path(data_root)
    if host not in HOSTS or not python.is_absolute() or not python.is_file():
        raise ValueError('Known host and absolute Python interpreter required')
    if destination.exists():
        raise ValueError('Destination already exists; never overwrite an installation')
    source = source.resolve()
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError('Installation must be independent of the source tree')
    if destination == data_root or data_root.is_relative_to(destination) or destination.is_relative_to(data_root):
        raise ValueError('Stable data and versioned code need non-overlapping roots')
    paths = list(runtime_files(source))  # Validate before creating any destination.
    # Exact dependency combination is prepared by the installer, not by Runtime.
    env = {k:v for k,v in os.environ.items() if k != 'SDLC_GITHUB_TOKEN'}
    check = subprocess.run([str(python), '-B', str(source/'scripts/sdlc_github_mcp.py'), '--check-install'],
                           capture_output=True, env=env, text=True, timeout=30)
    if check.returncode:
        raise ValueError('DEPENDENCY_UNAVAILABLE: explicitly install the hashed lock first')
    dependency_result = json.loads(check.stdout)
    destination.mkdir(parents=True, mode=0o700)
    data_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    for relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/relative, target)
        target.chmod(0o644)
    # The Skill invokes this exact relative launcher; never PATH's system Python.
    launcher = destination / 'skills/sdlc-github/scripts/run'
    launcher.write_text('#!/bin/sh\nset -eu\nHERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd)\n'
                       + 'exec ' + shlex.quote(str(python)) + ' -B "$HERE/runtime.py" "$@"\n')
    launcher.chmod(0o755)
    config = render_config(host, python, destination, data_root)
    config_path = destination / f'config/github/{host}.mcp.json'
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    if host == 'codex':
        entry = config['mcpServers']['sdlc_github']
        # JSON basic strings/arrays used here are valid TOML values.
        (destination/'config/github/codex.standalone.toml').write_text(
            '[mcp_servers.sdlc_github]\n' + '\n'.join(k+' = '+json.dumps(v,ensure_ascii=False) for k,v in entry.items())+'\n')
    inventory = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(destination.rglob('*')) if p.is_file()}
    receipt = {'contract': 'sdlc-ai-spec/github-install/v1', 'host': host, 'python': str(python),
               'plugin': str(destination), 'data_root': str(data_root), 'configuration': str(config_path),
               'registration': 'plugin manifest; standalone fragment is an alternative, never add both',
               'native_status': 'NOT_RUN', 'native_gate': 'OUT_OF_SCOPE_MANUAL_FEEDBACK',
               'compiler_launcher': str(launcher), 'generated_files': [str(launcher.relative_to(destination))],
               'dependencies': dependency_result, 'files': inventory}
    (destination/'INSTALL.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=HOSTS, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    args=parser.parse_args(argv)
    try:
        receipt=install(args.host,args.destination,args.data_root,args.python)
        print(json.dumps({k:v for k,v in receipt.items() if k!='files'},ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,subprocess.SubprocessError):
        print('INSTALL_BLOCKED: verify explicit paths, dependency lock, and empty destination; no host settings changed.',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
