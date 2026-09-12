#!/usr/bin/env python3
"""Prepare project data for the installed SDLC AI SPEC plugin; never install tool resources.

Stdlib only. --project is explicit so a nested module is not silently replaced by
its enclosing Git root. Existing user files are preserved; compatible partial
initializations are completed. This is not an upstream/legacy data migrator.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

LAYOUT = 1
ALLOWED = {'memory', 'specs', 'templates', 'feature.json', 'init-options.json',
           '.gitignore', 'README.md'}


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def read_json(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key in {path.name}: {key}')
            result[key] = value
        return result
    value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError(f'{path} must contain a JSON object')
    return value


def check_path(path: Path, directory: bool = False) -> None:
    if path.is_symlink():
        raise ValueError(f'Refusing symlink project data: {path}')
    if path.exists() and (not path.is_dir() if directory else not path.is_file()):
        raise ValueError(f'Expected {"directory" if directory else "regular file"}: {path}')


def publish(path: Path, data: bytes, expected: bytes | None) -> None:
    """Stage complete bytes, then publish without overwriting an unexpected file."""
    fd, temporary = tempfile.mkstemp(prefix='.sdlc-init-', dir=path.parent)
    try:
        mode = stat.S_IMODE(path.stat().st_mode) if expected is not None else 0o644
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        check_path(path)
        if expected is None:
            # Atomic create-if-absent. A concurrent creator is an error, not permission
            # to overwrite their content. Same-directory hardlink requires no Git.
            os.link(temporary, path)
        else:
            if path.stat().st_nlink != 1 or path.read_bytes() != expected:
                raise ValueError(f'Project data changed during initialization: {path}')
            os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def tracking(root: Path) -> tuple[str, list[str]]:
    """Optional read-only warning. Never add, remove, initialize or configure Git."""
    git = shutil.which('git')
    if not git:
        return 'not-checked', ['Git unavailable: tracking status was not checked.']
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    # Ambient Git routing must not redirect this read to another repository.
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
        env.pop(key, None)
    try:
        probe = subprocess.run([git, '-c', 'core.fsmonitor=false', '-C', str(root), 'rev-parse', '--is-inside-work-tree'],
                               env=env, capture_output=True, timeout=10)
        if probe.returncode:
            return 'not-checked', ['Not a readable Git worktree; tracking status was not checked.']
        result = subprocess.run([git, '-c', 'core.fsmonitor=false', '-C', str(root), 'ls-files', '-z', '--', '.sdlc'],
                                env=env, capture_output=True, timeout=10)
        if result.returncode:
            return 'not-checked', ['Git tracking query failed; no Git state was changed.']
        if result.stdout:
            return 'tracked', ['Some .sdlc files are already tracked; ignore rules do not untrack them.']
        return 'untracked', []
    except (OSError, subprocess.TimeoutExpired):
        return 'not-checked', ['Git tracking status unavailable; no Git state was changed.']


def initialize(plugin: Path, project: Path, numbering: str | None = None,
               dry_run: bool = False) -> dict:
    plugin = plugin.resolve(strict=True)
    root = project.expanduser().resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or inside(root, plugin):
        raise ValueError('Select an existing business project directory outside the plugin')
    state = root / '.sdlc'
    # Do not silently clone or convert another implementation's data.
    if (root / '.specify').exists() or (root / '.specify').is_symlink():
        raise ValueError('Existing .specify requires explicit migration; no files were changed')
    check_path(state, True)
    was_initialized = state.is_dir()
    if was_initialized:
        unknown = sorted(p.name for p in state.iterdir() if p.name not in ALLOWED)
        if unknown:
            raise ValueError('Unrecognized .sdlc layout; preserve and review before initialization: '
                             + ', '.join(unknown))
        for path in state.rglob('*'):
            if path.is_symlink():
                raise ValueError(f'Refusing symlink project data: {path}')
    directories = [state, state / 'memory', state / 'specs']
    for path in directories:
        check_path(path, True)
    files = [state / name for name in ('init-options.json', 'README.md', '.gitignore',
                                      'memory/constitution.md', 'feature.json')]
    for path in files:
        check_path(path)
    templates = state / 'templates'
    check_path(templates, True)
    if templates.is_dir() and any(p.name != 'overrides' for p in templates.iterdir()):
        raise ValueError('Only project template overrides belong in .sdlc; do not copy core resources')
    check_path(templates / 'overrides', True)
    source = plugin / 'templates/constitution-template.md'
    if not source.is_file() or not inside(source.resolve(), plugin):
        raise ValueError('Installed plugin lacks a contained constitution template; reinstall the plugin')
    provenance = read_json(plugin / 'UPSTREAM.json')
    options_file = state / 'init-options.json'
    original = options_file.read_bytes() if options_file.exists() else None
    options = read_json(options_file) if original is not None else {}
    if options.get('script', 'sh') != 'sh':
        raise ValueError('This plugin supports only the sh project profile')
    layout = options.get('sdlc_layout', LAYOUT)
    if type(layout) is not int or layout != LAYOUT:
        raise ValueError('Unsupported SDLC project layout; initialization is not a data migration')
    selected = options.get('feature_numbering', options.get('branch_numbering', numbering or 'sequential'))
    if selected not in ('sequential', 'timestamp'):
        raise ValueError('Invalid project feature_numbering')
    if numbering is not None and selected != numbering:
        raise ValueError('Initialization preserves existing numbering; edit project configuration explicitly')
    # Never store a host choice or a plugin installation path in the project.
    defaults = {'script': 'sh', 'feature_numbering': selected,
                'speckit_version': provenance['version'],
                'sdlc_layout': LAYOUT, 'sdlc_version': provenance['port_version']}
    merged = dict(options)
    for key, value in defaults.items():
        merged.setdefault(key, value)
    if (state / 'feature.json').exists():
        feature = read_json(state / 'feature.json').get('feature_directory')
        if not isinstance(feature, str) or not feature.strip():
            raise ValueError('Existing feature.json needs a nonempty feature_directory; it was preserved')
        resolved = (root / feature).resolve()
        if inside(resolved, plugin):
            raise ValueError('Existing feature directory points into the plugin')
    override = templates / 'overrides/constitution-template.md'
    check_path(override)
    seed = override if override.is_file() else source
    constitution = seed.read_bytes()
    readme = plugin / 'references/PROJECT-README.md'
    if not readme.is_file() or not inside(readme.resolve(), plugin):
        raise ValueError('Installed plugin lacks its project README; reinstall the plugin')
    readme_content = readme.read_bytes()
    proposed = {
        options_file: (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode(),
        state / 'memory/constitution.md': constitution,
        state / 'README.md': readme_content,
        state / '.gitignore': b'*\n',
    }
    writes = []
    preserved = []
    for path, data in proposed.items():
        if not path.exists():
            writes.append((path, data, None))
        elif path == options_file and merged != options:
            if path.stat().st_nlink != 1:
                raise ValueError('Refusing to rewrite hardlinked init-options.json')
            writes.append((path, data, original))
        else:
            preserved.append(path.relative_to(root).as_posix())
    # All shape/profile/template validation above happens before the first write.
    new_dirs = [p for p in directories if not p.exists()]
    git_status, warnings = tracking(root)
    if options.get('ai') or options.get('integration'):
        warnings.append('Existing host metadata retained for compatibility, not used to select this plugin host.')
    if (state / '.gitignore').exists():
        warnings.append('Existing .sdlc/.gitignore preserved; its ignore policy was not replaced.')
    if not dry_run:
        for path in directories:
            check_path(path, True)
            path.mkdir(exist_ok=True)
        for path, data, expected in writes:
            publish(path, data, expected)
    changes = bool(new_dirs or writes)
    status = ('initialized' if not was_initialized else 'completed') if changes else 'unchanged'
    return {'status': status, 'dry_run': dry_run, 'PROJECT_ROOT': str(root),
            'SDLC_DIR': str(state),
            'created': [p.relative_to(root).as_posix() + '/' for p in new_dirs]
                       + [p.relative_to(root).as_posix() for p, _, old in writes if old is None],
            'updated': [p.relative_to(root).as_posix() for p, _, old in writes if old is not None],
            'preserved': preserved, 'feature_created': False,
            'constitution_source': 'project-override' if seed == override else 'plugin-template',
            'git_tracking': git_status, 'warnings': warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True,
                        help='Explicit project directory; never inferred from the plugin or Git root')
    parser.add_argument('--feature-numbering', choices=('sequential', 'timestamp'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        if sys.version_info < (3, 9):
            raise ValueError('Python 3.9+ is required')
        if shutil.which('bash') is None:
            raise ValueError('Bash is required by the SDLC core; no software was installed')
        result = initialize(Path(__file__).resolve().parents[2], args.project,
                            args.feature_numbering, args.dry_run)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        print('No existing documents were intentionally overwritten. Inspect any partial new layout and rerun; do not delete .sdlc.', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(('DRY RUN: ' if args.dry_run else '') + result['status'] + ': ' + result['SDLC_DIR'])
        for field in ('created', 'updated', 'preserved', 'warnings'):
            for item in result[field]:
                print(f'{field}: {item}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
