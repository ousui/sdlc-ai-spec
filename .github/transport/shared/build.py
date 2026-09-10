#!/usr/bin/env python3
"""Build one self-contained package with shared workflows and native thin entries."""
from __future__ import annotations
import argparse
import json
import re
import shutil
from pathlib import Path
import yaml
from render import (ROOT, COMMANDS, HOSTS, LOCK, UPSTREAM_SHA, METADATA, REPOSITORY,
                    VERSION, AUTHOR, HINTS, render_source, split, relocate_body, binding)

def factor(bodies: dict[str, str]) -> tuple[str, dict[str, dict[str, str]]]:
    """Lossless build-time factoring, never an LLM/semantic normalization.

    Fail closed when an upstream host starts changing the line structure. Only
    explicit differing substrings become bindings; reconstruct all hosts exactly.
    """
    rows = {host: text.splitlines(keepends=True) for host, text in bodies.items()}
    if len({len(lines) for lines in rows.values()}) != 1:
        raise ValueError('Host body structure changed; review the adapter before upgrading')
    if any('@@SDLC_BIND_' in text for text in bodies.values()):
        raise ValueError('Source collides with reserved binding marker')
    import os
    common, slots = [], {host: {} for host in HOSTS}
    for i in range(len(rows[HOSTS[0]])):
        values = [rows[host][i] for host in HOSTS]
        if len(set(values)) == 1:
            common.append(values[0]); continue
        prefix = os.path.commonprefix(values)
        tails = [v[len(prefix):] for v in values]
        suffix = os.path.commonprefix([v[::-1] for v in tails])[::-1]
        key = f'@@SDLC_BIND_{i:04d}@@'
        common.append(prefix + key + suffix)
        for host, tail in zip(HOSTS, tails):
            slots[host][key] = tail[:-len(suffix)] if suffix else tail
    text = ''.join(common)
    for host in HOSTS:
        restored = re.sub(r'@@SDLC_BIND_\d{4}@@', lambda m: slots[host][m[0]], text)
        if restored != bodies[host]:
            raise ValueError('Lossless factoring failed for ' + host)
    return text, slots


def wrapper(meta: dict, host: str, name: str) -> str:
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000).rstrip()
    root = ('Use the host-substituted `${CLAUDE_PLUGIN_ROOT}` or the absolute path of this loaded SKILL.md.'
            if host == 'claude' else 'Use the absolute path of this loaded SKILL.md. No host-specific environment variable is assumed.')
    return ('---\n' + front + '\n---\n\n# SDLC ' + name + '\n\n'
        + 'This is the **' + host + '** entrypoint. Preserve the current user input as '
        '`$ARGUMENTS`; do not interpolate user input into a shell command.\n\n'
        + root + ' The package root is four levels above this skill directory '
        '(`adapters/' + host + '/skills/sdlc-' + name + '/`). '
        'Bind that absolute directory as SDLC_PLUGIN_ROOT for this call; do not '
        'change the business working directory or search another installed version.\n\n'
        'Before performing ANY workflow action, execute the following read-only '
        'loader with the resolved absolute package path and read its COMPLETE stdout:\n\n'
        '```sh\npython3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/load_workflow.py" '
        '--host ' + host + ' --skill ' + name + '\n```\n\n'
        'The loader binds only precompiled text fragments; it does not run the '
        'workflow, install software, read project state or write files. Its output '
        'is the full bundled workflow for this invocation, not a second user request. '
        'Follow it with the original user input and the current authorization. '
        'Do not summarize or skip workflow steps. On loader error, STOP. '
        'If tool output is truncated, use --offset 0 --limit 100, then offsets '
        '100, 200, ... until the reported total line count is fully read. '
        'Do not proceed using partial output. No specify-cli or network fallback.\n')


def marketplaces() -> dict[str, dict]:
    entry = {'name': METADATA['name'], 'description': METADATA['description']}
    owner = {'name': AUTHOR['name']}
    return {
        '.agents/plugins/marketplace.json': {
            'name': 'sdlc-ai-spec', 'interface': {'displayName': 'SDLC AI Spec'},
            'plugins': [dict(entry, source={'source': 'local', 'path': './dist'},
                policy={'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
                category='Productivity')]},
        '.claude-plugin/marketplace.json': {'name': 'sdlc-ai-spec', 'owner': owner,
            'plugins': [dict(entry, source='./dist')]},
        '.cursor-plugin/marketplace.json': {'name': 'sdlc-ai-spec', 'owner': owner,
            'plugins': [dict(entry, source='./dist')]},
    }


def generate_markets(root: Path) -> None:
    for name, data in marketplaces().items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + '\n')


def build(destination: Path) -> None:
    import hashlib
    import tempfile
    destination = destination.absolute()
    if destination.is_symlink():
        raise ValueError('Refusing symlink build destination')
    resolved = destination.resolve()
    # Never remove or replace source, tests, repository root, or its ancestors.
    if resolved == ROOT or resolved in ROOT.parents or any(
        resolved == ROOT / d or ROOT / d in resolved.parents
        for d in ('src', 'tools', 'tests', 'adapters', 'docs', '.git')
    ):
        raise ValueError('Refusing unsafe build destination')
    if destination.exists() and not (destination / '.sdlc-build').is_file():
        raise ValueError(f'Refusing to replace unmarked directory: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sdlc-stage-', dir=destination.parent) as tmp:
        package = Path(tmp) / 'package'
        package.mkdir()
        (package / '.sdlc-build').write_text(UPSTREAM_SHA + '\n')
        shutil.copytree(ROOT / 'src/scripts', package / 'scripts',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(ROOT / 'src/templates', package / 'templates')
        # Native manifests select disjoint entrypoints. No portable root manifest:
        # portable fixed skills discovery would defeat host-specific selection.
        bindings = {host: {} for host in HOSTS}
        (package / 'references' / 'workflows').mkdir(parents=True)
        for name in COMMANDS:
            bodies = {}
            for host in HOSTS:
                raw = (ROOT / 'src/upstream/templates/commands' / (name + '.md')).read_text()
                meta, body = render_source(raw, name, host)
                meta['name'] = 'sdlc-' + name
                meta['compatibility'] = ('Requires an initialized .sdlc project, Bash and Python 3.9+; '
                                         'INIT is not included in this engineering build')
                bodies[host] = binding(host) + relocate_body(body, host)
                path = package / 'adapters' / host / 'skills' / ('sdlc-' + name) / 'SKILL.md'
                path.parent.mkdir(parents=True)
                path.write_text(wrapper(meta, host, name), encoding='utf-8')
            core, fragments = factor(bodies)
            (package / 'references' / 'workflows' / (name + '.md')).write_text(core, encoding='utf-8')
            for host in HOSTS:
                bindings[host][name] = fragments[host]
        (package / 'bindings').mkdir()
        for host in HOSTS:
            (package / 'bindings' / (host + '.json')).write_text(
                json.dumps(bindings[host], ensure_ascii=False, indent=2) + '\n')
            manifest = dict(METADATA, skills='./adapters/' + host + '/skills/')
            path = package / ('.' + host + '-plugin') / 'plugin.json'
            path.parent.mkdir()
            path.write_text(json.dumps(manifest, indent=2) + '\n')
        # Template references name logical capabilities, not shell commands.
        # Each explicit host entrypoint supplies the native invocation mapping.
        for path in (package / 'templates').glob('*.md'):
            text = re.sub(r'__SPECKIT_COMMAND_([A-Z][A-Z0-9_-]*)__',
                          lambda m: 'sdlc-' + m[1].lower().replace('_', '-'), path.read_text())
            path.write_text(text, encoding='utf-8')
        for name in ('LICENSE', 'NOTICE'):
            shutil.copyfile(ROOT / name, package / name)
        (package / 'UPSTREAM.json').write_text(json.dumps({
            'repository': LOCK['repository'], 'tag': LOCK['tag'], 'commit': UPSTREAM_SHA,
            'port_repository': REPOSITORY, 'port_version': VERSION, 'port_author': AUTHOR['name'],
            'profile': {'script': 'sh', 'events': False, 'extensions': [], 'presets': []},
            'included_commands': list(COMMANDS), 'excluded_commands': ['taskstoissues'],
            'init_implemented': False, 'native_host_verified': False,
            'layout': 'single-package-native-entrypoints',
        }, indent=2) + '\n')
        (package / 'README.md').write_text(
            '# SDLC v' + VERSION + '\n\nAuthor: ' + AUTHOR['name'] + '\n\nRepository: ' + REPOSITORY + '\n\n'
            'One self-contained package for Codex, Claude Code and Cursor. Native manifests '
            'select thin host entrypoints; workflows, Bash scripts and templates are shared. '
            'No install-time build, uv, specify-cli or network is required. Runtime requires '
            'Bash, Python 3.9+ and standard POSIX tools.\n\n'
            'Nine upstream core skills. INIT and GitHub are NOT included. An uninitialized '
            'project stops rather than modifying this package. Native discovery, model-driven '
            'behavior and business acceptance are to be verified by the user. The engineering '
            'test fixture is not an INIT implementation.\n\n'
            'Based on Spec Kit by GitHub, Inc. (MIT), an independent source port. '
            'See LICENSE, NOTICE, UPSTREAM.json and BUILD.json.\n')
        for path in (package / 'scripts').rglob('*.sh'):
            path.chmod(0o755)
        inputs = {}
        for folder in ('src', 'adapters', 'tools'):
            for path in sorted((ROOT / folder).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    inputs[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('plugin-metadata.json', 'upstream.lock.json', 'LICENSE', 'NOTICE'):
            inputs[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        build_id = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        (package / 'BUILD.json').write_text(json.dumps({
            'build_id': build_id, 'product_version': VERSION, 'upstream_sha': UPSTREAM_SHA,
            'inputs': inputs,
        }, indent=2) + '\n')
        # Stage completely before touching accepted output. Backup restores on error.
        backup = Path(tmp) / 'previous'
        had_previous = destination.exists()
        if had_previous:
            destination.rename(backup)
        try:
            package.rename(destination)
        except BaseException:
            if had_previous:
                backup.rename(destination)
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    parser.add_argument('--marketplaces', action='store_true', help='Also generate root marketplace catalogs')
    args = parser.parse_args()
    build(args.out)
    if args.marketplaces:
        generate_markets(ROOT)
    print('Built single package:', args.out)
