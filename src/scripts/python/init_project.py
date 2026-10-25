#!/usr/bin/env python3
"""Prepare project data for the installed SDLC AI SPEC plugin; never install tool resources.

Stdlib only. --project is explicit so a nested module is not silently replaced by
its enclosing Git root. Existing user files are preserved; compatible partial
initializations are completed. This is not an upstream/legacy data migrator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

LAYOUT = 1
ALLOWED = {'memory', 'specs', 'templates', 'feature.json', 'init-options.json',
           '.gitignore', 'README.md', 'store.json', 'workspaces', 'transactions', '.write-lock', '.init-pending.json'}
PROVENANCE_NAME = '.constitution-template.json'
PENDING_NAME = '.init-pending.json'
SHA256_RE = re.compile(r'^[0-9a-f]{64}$')


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


def provenance_bytes(content: bytes, source: str) -> bytes:
    return (json.dumps({'sha256': hashlib.sha256(content).hexdigest(), 'source': source},
                       ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def inspect_existing_provenance(path: Path) -> tuple[str, str | None]:
    """Classify an optional existing record without turning it into an INIT gate."""
    if not os.path.lexists(path):
        return 'missing', None
    if path.is_symlink() or not path.is_file():
        return 'unavailable', 'Existing constitution generation provenance is not a regular file; preserved without repair.'
    try:
        data = read_json(path)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        return 'unavailable', f'Existing constitution generation provenance is unreadable or invalid; preserved without repair: {exc}'
    digest, source = data.get('sha256'), data.get('source')
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest.lower()):
        return 'unavailable', 'Existing constitution generation provenance has an invalid sha256; preserved without repair.'
    if not isinstance(source, str) or not source.strip():
        return 'unavailable', 'Existing constitution generation provenance has an invalid source; preserved without repair.'
    return 'preserved', None


def check_path(path: Path, directory: bool = False) -> None:
    if path.is_symlink():
        raise ValueError(f'Refusing symlink project data: {path}')
    if path.exists() and (not path.is_dir() if directory else not path.is_file()):
        raise ValueError(f'Expected {"directory" if directory else "regular file"}: {path}')


def published_identity(info: os.stat_result) -> dict:
    return {'device': info.st_dev, 'inode': info.st_ino,
            'size': info.st_size, 'mtime_ns': info.st_mtime_ns}


def publish(path: Path, data: bytes, expected: bytes | None) -> dict:
    """Stage complete bytes, then publish without overwriting an unexpected file."""
    fd, temporary = tempfile.mkstemp(prefix='.sdlc-init-', dir=path.parent)
    try:
        mode = stat.S_IMODE(path.stat().st_mode) if expected is not None else 0o644
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
            identity = published_identity(os.fstat(stream.fileno()))
        check_path(path)
        if expected is None:
            # Atomic create-if-absent. A concurrent creator is an error, not permission
            # to overwrite their content. Same-directory hardlink requires no Git.
            os.link(temporary, path)
        else:
            if path.stat().st_nlink != 1 or path.read_bytes() != expected:
                raise ValueError(f'Project data changed during initialization: {path}')
            os.replace(temporary, path)
        return identity
    finally:
        Path(temporary).unlink(missing_ok=True)


def publish_new_directory(source: Path, target: Path) -> None:
    """Publish a complete intent without replacing even an existing empty store."""
    import ctypes
    import errno
    if os.name == 'nt':
        os.rename(source, target)  # Windows rename already refuses an existing target.
        return
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        rename = getattr(library, 'renamex_np', None)
        signature = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        arguments = (os.fsencode(source), os.fsencode(target), 0x4)  # RENAME_EXCL
    elif sys.platform.startswith('linux'):
        rename = getattr(library, 'renameat2', None)
        signature = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        arguments = (-100, os.fsencode(source), -100, os.fsencode(target), 1)  # AT_FDCWD, RENAME_NOREPLACE
    else:
        rename = None
    if rename is None:
        raise OSError(errno.ENOTSUP, 'Atomic no-replace directory publication is unavailable', str(target))
    rename.argtypes, rename.restype = signature, ctypes.c_int
    if rename(*arguments) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(target))


def create_store_with_intent(state: Path, content: bytes, validate) -> os.stat_result:
    # The store is either absent or already contains its complete recovery record.
    staged = state.with_name('.sdlc-init-' + uuid.uuid4().hex)
    staged.mkdir()  # Keep the same umask behavior as ordinary state.mkdir().
    identity = staged.stat()
    pending = staged / PENDING_NAME
    receipt = None
    try:
        receipt = publish(pending, content, None)
        validate()
        publish_new_directory(staged, state)
        return identity
    finally:
        # Never recursively remove concurrent files or a replacement directory.
        try:
            current = staged.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                if (receipt is not None and not pending.is_symlink() and
                        published_identity(pending.stat()) == receipt and pending.read_bytes() == content):
                    pending.unlink()
                staged.rmdir()
        except OSError:
            pass


def tracking(root: Path, state: Path | None = None) -> tuple[str, list[str]]:
    """Optional read-only warning. Never add, remove, initialize or configure Git."""
    root = state.parent if state is not None else root
    marker = state.name if state is not None else '.sdlc'
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
        result = subprocess.run([git, '-c', 'core.fsmonitor=false', '-C', str(root), 'ls-files', '-z', '--', marker],
                                env=env, capture_output=True, timeout=10)
        if result.returncode:
            return 'not-checked', ['Git tracking query failed; no Git state was changed.']
        if result.stdout:
            return 'tracked', ['Some .sdlc files are already tracked; ignore rules do not untrack them.']
        return 'untracked', []
    except (OSError, subprocess.TimeoutExpired):
        return 'not-checked', ['Git tracking status unavailable; no Git state was changed.']


def initialize(plugin: Path, project: Path, numbering: str | None = None,
               dry_run: bool = False, *, state_dir: Path | None = None,
               seed_files: dict | None = None, binding: dict | None = None) -> dict:
    plugin = plugin.resolve(strict=True)
    root = project.expanduser().resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or inside(root, plugin):
        raise ValueError('Select an existing business project directory outside the plugin')
    state = state_dir if state_dir is not None else root / '.sdlc'
    feature_json = Path(binding['FEATURE_JSON']) if binding is not None else state / 'feature.json'
    seed_files = dict(seed_files or {})
    def display(path):
        return path.relative_to(root).as_posix() if inside(path, root) else str(path)
    def check_target(path):
        if binding is not None:
            from sdlc_store import document_path
            document_path(binding, path, allowed_control=path)
    if inside(state.resolve(), plugin) or not state.parent.is_dir():
        raise ValueError('Data directory must have an existing parent outside the plugin')
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
                                      'memory/constitution.md')] + [feature_json]
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
    if feature_json.exists():
        feature = read_json(feature_json).get('feature_directory')
        if not isinstance(feature, str) or not feature.strip():
            raise ValueError('Existing feature.json needs a nonempty feature_directory; it was preserved')
        if binding is not None:
            from sdlc_store import feature_path
            resolved = feature_path(binding, feature)
        else:
            resolved = (root / feature).resolve()
        if inside(resolved, plugin):
            raise ValueError('Existing feature directory points into the plugin')
    override = templates / 'overrides/constitution-template.md'
    check_path(override)
    seed = override if override.is_file() else source
    constitution = seed.read_bytes()
    constitution_path = state / 'memory/constitution.md'
    provenance_path = state / 'memory' / PROVENANCE_NAME
    source_label = ('project-override:.sdlc/templates/overrides/constitution-template.md'
                    if seed == override else 'plugin-template:templates/constitution-template.md')
    provenance_state, provenance_warning = inspect_existing_provenance(provenance_path)
    skipped_import_provenance = (constitution_path.exists() and not os.path.lexists(provenance_path)
                                 and 'memory/' + PROVENANCE_NAME in seed_files)
    if skipped_import_provenance:
        # A pending import records intent, not proof that an existing constitution
        # was published by this INIT. Never backfill its historical generation.
        seed_files.pop('memory/' + PROVENANCE_NAME)
    readme = plugin / 'references/PROJECT-README.md'
    if not readme.is_file() or not inside(readme.resolve(), plugin):
        raise ValueError('Installed plugin lacks its project README; reinstall the plugin')
    readme_content = readme.read_bytes()
    proposed = {
        options_file: (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode(),
        constitution_path: constitution,
        state / 'README.md': readme_content,
        state / '.gitignore': b'*\n',
    }
    proposed.update({state / name: data for name, data in seed_files.items()})
    for name in seed_files:
        for parent in (state / name).parents:
            if parent == state:
                break
            if parent not in directories:
                directories.append(parent)
    directories.sort(key=lambda p: len(p.parts))
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
            preserved.append(display(path))
    # All shape/profile/template validation above happens before the first write.
    new_dirs = [p for p in directories if not p.exists()]
    for path in [*new_dirs, *(path for path, _, _ in writes)]:
        check_target(path)
    git_status, warnings = tracking(root, state)
    if options.get('ai') or options.get('integration'):
        warnings.append('Existing host metadata retained for compatibility, not used to select this plugin host.')
    if (state / '.gitignore').exists():
        warnings.append('Existing .sdlc/.gitignore preserved; its ignore policy was not replaced.')
    if provenance_warning:
        warnings.append(provenance_warning)
    if skipped_import_provenance:
        warnings.append('Existing constitution was preserved; authority provenance was not imported because its origin cannot be asserted.')

    constitution_will_create = 'memory/constitution.md' not in seed_files and any(path == constitution_path and old is None for path, _, old in writes)
    provenance_result = provenance_state if provenance_state != 'missing' else 'not_recorded'
    provenance_created = False
    if constitution_will_create and provenance_state == 'missing':
        provenance_result = 'would_record' if dry_run else 'not_recorded'
    elif constitution_will_create and provenance_state == 'preserved':
        warnings.append('Pre-existing provenance was preserved; it is not claimed as the record for the constitution created by this run.')

    if not constitution_will_create and provenance_state == 'missing' and constitution_path.exists():
        warnings.append('Existing constitution has no generation provenance; preserved without backfilling historical origin.')

    if not dry_run:
        for path in directories:
            check_path(path, True)
            if not path.exists():
                check_target(path)
            path.mkdir(exist_ok=True)
        for path, data, expected in writes:
            check_target(path)
            publish(path, data, expected)
            if constitution_will_create and path == constitution_path and expected is None and provenance_state == 'missing':
                try:
                    check_target(provenance_path)
                    publish(provenance_path, provenance_bytes(data, source_label), None)
                    provenance_result = 'recorded'
                    provenance_created = True
                except (OSError, ValueError) as exc:
                    provenance_result = 'unavailable'
                    warnings.append('Constitution generation provenance was not recorded; the constitution was preserved: ' + str(exc))
    changes = bool(new_dirs or writes or provenance_created)
    status = ('initialized' if not was_initialized else 'completed') if changes else 'unchanged'
    return {'status': status, 'dry_run': dry_run, 'PROJECT_ROOT': str(root),
            'SDLC_DIR': str(state),
            'created': [display(p) + '/' for p in new_dirs]
                       + [display(p) for p, _, old in writes if old is None]
                       + ([display(provenance_path)]
                          if provenance_created or (dry_run and constitution_will_create and provenance_state == 'missing') else []),
            'updated': [display(p) for p, _, old in writes if old is not None],
            'preserved': preserved, 'feature_created': False,
            'constitution_source': 'project-override' if seed == override else 'plugin-template',
            'constitution_provenance': provenance_result,
            'git_tracking': git_status, 'warnings': warnings}



def initialize_selected(args) -> dict:
    # Explicit package sibling import also works with Python isolated mode (-I).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sdlc_store import resolve, validate_state, write_lock, KNOWLEDGE, parse_object, json_bytes, safe, document_path
    from store_changes import source_snapshot, source_files, MAX_FILE, MAX_TOTAL
    import base64
    plugin = Path(__file__).resolve().parents[2]
    context = resolve(args.project, plugin=plugin, missing=True)
    project = Path(context['PROJECT_ROOT'])
    if args.discover:
        return dict(context, status='discovered')
    if args.mode == 'auto' and ((not context['can_collect'] and not context['local_exists']) or
            (context['can_collect'] and not context['authority_exists'] and context['sources'])):
        return dict(context, status='needs_choice', choices=['shared', 'local'] if not context['can_collect'] else ['shared', 'collect'],
                    warning='Choose storage explicitly; discovery did not initialize or merge data')
    if args.mode == 'shared' and context['local_exists']:
        raise ValueError('Local data takes precedence; shared mode cannot bypass a local store')
    state = Path(context['SDLC_DIR'])
    binding = context
    if args.mode == 'local' and not context['can_collect']:
        state = project / '.sdlc'
        if state != Path(context['SDLC_DIR']):
            binding = dict(context, SDLC_DIR=str(state), FEATURE_JSON=str(state / 'feature.json'), mode='local')
    if args.seed == 'none' and args.feature:
        raise ValueError('Feature import cannot be combined with blank initialization')
    seeds = {}
    source = None
    authority = Path(context['AUTHORITY_DIR']) if context['AUTHORITY_DIR'] is not None else None
    planned_new_state = not state.exists()
    if any('/' in name or name in ('', '.', '..') for name in args.feature):
        raise ValueError('Select exact feature directory names')
    pending_path = state / PENDING_NAME
    pending_bytes = None
    intent = {'schema': 1, 'project': str(project), 'target': str(state.resolve()),
              'authority': str(authority) if authority is not None else None,
              'seed': args.seed, 'features': sorted(set(args.feature)), 'numbering': args.feature_numbering}
    if os.path.lexists(pending_path):
        safe(pending_path)
        pending_bytes = pending_path.read_bytes()
        pending = parse_object(pending_bytes)
        if type(pending.get('schema')) is not int or any(pending.get(k) != v for k, v in intent.items()):
            raise ValueError('Interrupted initialization has different choices or authority; inspect .init-pending.json and retry the original choices')
        encoded = pending.get('seeds')
        if not isinstance(encoded, dict) or not encoded or len(encoded) > 10000:
            raise ValueError('Invalid interrupted initialization seed snapshot')
        for name, data in encoded.items():
            if (not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts
                    or not isinstance(data, str) or not (name in (*KNOWLEDGE, 'memory/' + PROVENANCE_NAME)
                    or any(name.startswith('specs/' + f + '/') for f in args.feature))):
                raise ValueError('Invalid interrupted initialization seed path')
            seeds[name] = base64.b64decode(data, validate=True)
            if len(seeds[name]) > MAX_FILE:
                raise ValueError('Interrupted initialization seed is too large')
        if sum(map(len, seeds.values())) > MAX_TOTAL:
            raise ValueError('Interrupted initialization snapshot is too large')
        if (args.seed != 'knowledge' or authority is None or state == authority
                or ('memory/' + PROVENANCE_NAME in seeds and 'memory/constitution.md' not in seeds)
                or any(not any(n.startswith('specs/' + f + '/') for n in seeds) for f in args.feature)):
            raise ValueError('Incomplete interrupted initialization seed snapshot')
    elif (state != authority and planned_new_state and args.seed == 'knowledge'
          and (args.feature or context['authority_exists'])):
        if authority is None or not authority.is_dir():
            raise ValueError('Selected import requires an available authority')
        validate_state({'SDLC_DIR': str(authority)}, selection=False)
        source = source_snapshot(authority)
        if any(not any(n.startswith('specs/' + f + '/') for n in source) for f in args.feature):
            raise ValueError('Selected requirement is absent from authority')
        seeds = {name: base64.b64decode(data)
                 for name, data in source_files(authority, source, args.feature).items()}
    preview = initialize(plugin, project, args.feature_numbering, True, state_dir=state, seed_files=seeds, binding=binding)
    if args.dry_run:
        return dict(preview, binding=context)
    if preview['status'] == 'unchanged' and pending_bytes is None:
        return dict(preview, dry_run=False, binding=context, imported=[])
    if source is not None and source_snapshot(authority) != source:
        raise ValueError('Authority changed during initialization; retry discovery')
    new_state = planned_new_state
    if new_state:
        if seeds:
            pending_bytes = json_bytes(dict(intent, seeds={n: base64.b64encode(d).decode('ascii') for n, d in seeds.items()}))
            def validate_new_store():
                latest = resolve(project, plugin=plugin, missing=True)
                if latest['AUTHORITY_DIR'] != context['AUTHORITY_DIR']:
                    raise ValueError('Storage binding changed during initialization; retry discovery')
                local_binding = dict(latest, SDLC_DIR=str(state), FEATURE_JSON=str(state / 'feature.json'), mode='local')
                document_path(local_binding, state)
                document_path(local_binding, pending_path, allowed_control=pending_path)
                if source_snapshot(authority) != source:
                    raise ValueError('Authority changed during initialization; retry discovery')
            created_state = create_store_with_intent(state, pending_bytes, validate_new_store)
        else:
            state.mkdir()
            created_state = state.stat()
    try:
        with write_lock(state):
            current = resolve(project, plugin=plugin, missing=True)
            if current['AUTHORITY_DIR'] != context['AUTHORITY_DIR'] or Path(current['SDLC_DIR']).resolve() != state.resolve():
                raise ValueError('Storage binding changed during initialization; retry discovery')
            if source is not None and not seeds and source_snapshot(authority) != source:
                raise ValueError('Authority changed during initialization; retry discovery')
            initialize(plugin, project, args.feature_numbering, True, state_dir=state,
                       seed_files=seeds, binding=current)
            if pending_bytes is not None:
                safe(pending_path)
                if pending_path.read_bytes() != pending_bytes:
                    raise ValueError('Interrupted initialization record changed; retry discovery')
            result = initialize(plugin, project, args.feature_numbering, False, state_dir=state, seed_files=seeds, binding=current)
            if pending_bytes is not None:
                safe(pending_path)
                if pending_path.read_bytes() != pending_bytes:
                    raise ValueError('Interrupted initialization record changed; preserve it for inspection')
                document_path(current, pending_path, allowed_control=pending_path)
                pending_path.unlink()
    except BaseException:
        # Only remove the directory made by this invocation when it is still empty.
        # A persisted intent or any concurrent/user data must remain available.
        if new_state:
            try:
                current_state = state.lstat()
                if (current_state.st_dev, current_state.st_ino) == (created_state.st_dev, created_state.st_ino):
                    state.rmdir()
            except OSError:
                pass
        raise
    if preview['status'] == 'initialized':
        result['status'] = 'initialized'
        root = project
        created_directory = state.relative_to(root).as_posix() if inside(state, root) else str(state)
        result['created'] = sorted(set(result['created']) | {created_directory + '/'})
    root = project
    imported = [name for name in seeds if (state / name).relative_to(root).as_posix() in result['created']]
    if 'memory/constitution.md' in seeds:
        result['constitution_source'] = 'authority-import' if 'memory/constitution.md' in imported else 'preserved'
        if 'memory/' + PROVENANCE_NAME in imported:
            result['constitution_provenance'] = 'imported'
    preserved_imports = [name for name in seeds if name not in imported and (state / name).exists()]
    if preserved_imports:
        result['warnings'].append('Existing selected import files were preserved; only files created by this invocation are reported as imported.')
    return dict(result, binding=resolve(project), imported=imported, preserved_imports=preserved_imports)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True,
                        help='Explicit project directory; never inferred from the plugin or Git root')
    parser.add_argument('--discover', action='store_true')
    parser.add_argument('--mode', choices=('auto', 'shared', 'local'), default='auto')
    parser.add_argument('--seed', choices=('knowledge', 'none'), default='knowledge')
    parser.add_argument('--feature', action='append', default=[])
    parser.add_argument('--feature-numbering', choices=('sequential', 'timestamp'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        if sys.version_info < (3, 9):
            raise ValueError('Python 3.9+ is required')
        if shutil.which('bash') is None:
            raise ValueError('Bash is required by the SDLC core; no software was installed')
        result = initialize_selected(args)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        print('No existing documents were intentionally overwritten. Inspect any partial new layout and rerun; do not delete .sdlc.', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(('DRY RUN: ' if args.dry_run else '') + result['status'] + ': ' + result.get('SDLC_DIR', ''))
        for field in ('created', 'updated', 'preserved', 'warnings', 'choices', 'sources'):
            for item in result.get(field, []):
                print(f'{field}: {item}')
        if result.get('warning'):
            print('warning: ' + result['warning'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
