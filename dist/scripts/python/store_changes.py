#!/usr/bin/env python3
"""Prepare, review, apply and recover bounded SDLC file changes; no LLM calls."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sdlc_store import (PLUGIN, KNOWLEDGE, alias_directory, atomic, document_path, entry_identity, feature_path, json_bytes, name_key, project_directory,
                        read_object, parse_object, release_stale_lock, require_authority, resolve, safe, same_path, same_target, target_inside, validate_state, worktrees, write_lock)

from init_project import publish as publish_data, published_identity

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024


def relative(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or '..' in path.parts or path.as_posix() != value:
        raise ValueError('Invalid relative data path: ' + value)
    return value


def file_bytes(path: Path) -> bytes:
    safe(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
            raise ValueError('Unsupported or oversized data file: ' + str(path))
        data = stream.read(MAX_FILE + 1)
        after = os.fstat(stream.fileno())
    if len(data) > MAX_FILE or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Data changed while reading: ' + str(path))
    return data


def snapshot(root: Path, paths: list[str] | None = None) -> dict:
    safe(root)
    result = {}
    total = 0
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError('Snapshot root is not a directory: ' + str(root))
    def include(path):
        nonlocal total
        data = file_bytes(path)
        total += len(data)
        if total > MAX_TOTAL or len(result) >= 10000:
            raise ValueError('Store snapshot exceeds supported size')
        result[path.relative_to(root).as_posix()] = base64.b64encode(data).decode()
    if paths is not None:
        for name in sorted(set(paths)):
            path = destination(root, name)
            if path.exists():
                include(path)
    else:
        pending = [(root, entry_identity(root.lstat()))]
        observed = []
        while pending:
            current, expected = pending.pop()
            safe(current)
            children, files = [], []
            with alias_directory(current, expected=expected) as descriptor:
                if descriptor is None:
                    raise ValueError('Snapshot directory is unavailable: ' + str(current))
                with os.scandir(descriptor) as entries:
                    for entry in entries:
                        path = current / entry.name
                        info = entry.stat(follow_symlinks=False)
                        if current == root and entry.name in ('transactions', '.write-lock') and entry.is_dir():
                            continue
                        safe(path)
                        if stat.S_ISDIR(info.st_mode):
                            children.append((path, entry_identity(info)))
                        else:
                            files.append(path)
                for path in sorted(files):
                    include(path)
            observed.append((current, expected))
            pending.extend(reversed(children))
        for path, expected in observed:
            if entry_identity(path.lstat()) != expected:
                raise ValueError('Snapshot directory changed during traversal: ' + str(path))
    return result


def optional_snapshot(root: Path, paths: list[str] | None = None) -> dict:
    """An uninitialized destination may be absent; a selected source may not."""
    safe(root)
    try:
        root.lstat()
    except FileNotFoundError:
        return {}
    return snapshot(root, paths)


def source_snapshot(root: Path) -> dict:
    """A selected source must remain a directory, even when its snapshot is empty."""
    before = root.lstat()
    if not stat.S_ISDIR(before.st_mode):
        raise ValueError('Source is not a directory: ' + str(root))
    result = snapshot(root)
    after = root.lstat()
    if not stat.S_ISDIR(after.st_mode) or entry_identity(before) != entry_identity(after):
        raise ValueError('Source directory changed during snapshot: ' + str(root))
    return result


def digest(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def authority_action(context: dict, kind: str) -> Path:
    if kind == 'collect':
        if not context['can_collect']:
            raise ValueError('Only main may collect copies into authority')
        # A target override must not disguise a call originating in a linked worktree.
        cwd_repo, cwd_roots = worktrees(Path.cwd().resolve())
        if len(cwd_roots) > 1 and cwd_repo != cwd_roots[0] and cwd_roots[0] == worktrees(Path(context['PROJECT_ROOT']))[1][0]:
            raise ValueError('Collection must be initiated from main, not a linked worktree')
        return require_authority(context)
    if kind == 'import':
        if context['PROJECT_ROOT'] == context['MAIN_PROJECT_ROOT']:
            raise ValueError('Import is authority-to-local; main uses collect')
        if not context['local_exists']:
            raise ValueError('Import refresh requires an existing local store; run INIT with --mode local first')
        return Path(context['PROJECT_ROOT']) / '.sdlc'
    return Path(context['SDLC_DIR'])


def allowed_sources(context: dict, kind: str, sources: list[Path]) -> list[Path]:
    allowed = {context['AUTHORITY_DIR']} if kind == 'import' else set(context['sources'])
    if kind == 'edit':
        if sources:
            raise ValueError('Ordinary edit does not accept copy sources')
        return []
    if kind == 'import' and not sources:
        sources = [require_authority(context)]
    resolved = sorted({project_directory(p.resolve(strict=True)) for p in sources})
    if not resolved or any(not any(value is not None and same_path(p, Path(value)) for value in allowed)
                           for p in resolved):
        raise ValueError('Select existing same-project worktree or explicitly registered sources')
    for path in resolved:
        safe(path)
        validate_state({'SDLC_DIR': str(path)}, selection=False)
        if not path.is_dir():
            raise ValueError('Source is unavailable: ' + str(path))
    return resolved


def in_scope(name: str, kind: str, features: list[str], paths: list[str]) -> bool:
    if kind == 'edit':
        return name in paths
    return name in KNOWLEDGE or any(name.startswith('specs/' + feature + '/') for feature in features)


def source_files(root: Path, files: dict, features: list[str]) -> dict:
    """Recognize knowledge roles on the source filesystem; retain raw snapshots."""
    record = 'memory/.constitution-template.json'
    roles = {tuple(map(name_key, Path(name).parts)): name for name in (*KNOWLEDGE, record)}
    result = {}
    for name, data in files.items():
        role = roles.get(tuple(map(name_key, Path(name).parts)))
        # A failed role lookup cannot turn selected knowledge into an empty import.
        if role is not None and same_path(root / name, root / role, strict=True):
            if role in result:
                raise ValueError('Ambiguous source knowledge file: ' + role)
            result[role] = data
        elif any(name.startswith('specs/' + feature + '/') for feature in features):
            result[name] = data
    if 'memory/constitution.md' not in result:
        result.pop(record, None)
    return result


def editable(name: str, context: dict) -> bool:
    relative(name)
    pointer = Path(context['FEATURE_JSON']).relative_to(context['SDLC_DIR']).as_posix()
    return (name in ('init-options.json', 'README.md', '.gitignore', pointer) or
            name.startswith(('specs/', 'templates/overrides/')) or name in KNOWLEDGE)


def copy_targets(target: Path, names: list[str]) -> dict:
    """Bind copy names to one destination spelling, including planned directories.

    Existing names win. Missing aliases are compared using the destination
    filesystem's lookup rules, never by unconditional Unicode/case folding.
    """
    children, roles, result = {}, {}, {}
    for name in sorted(set(names)):
        parts = Path(relative(name)).parts
        parent = target
        for index, part in enumerate(parts):
            if parent not in children:
                buckets = {}
                if parent.exists():
                    with os.scandir(parent) as entries:
                        for entry in entries:
                            buckets.setdefault(name_key(entry.name), []).append(entry.name)
                children[parent] = buckets
            candidates = children[parent].setdefault(name_key(part), [])
            matches = [entry for entry in candidates if same_path(parent / entry, parent / part)]
            if len(matches) > 1:
                raise ValueError('Ambiguous copy destination: ' + name)
            chosen = matches[0] if matches else part
            if not matches:
                candidates.append(chosen)
            parent = parent / chosen
            role = 'file' if index == len(parts) - 1 else 'directory'
            if roles.setdefault(parent, role) != role:
                raise ValueError('Copy file and directory destinations overlap: ' + name)
            safe(parent)
            if parent.exists() and (not parent.is_file() if role == 'file' else not parent.is_dir()):
                raise ValueError('Copy destination has a different file type: ' + name)
        result[name] = parent.relative_to(target).as_posix()
    return result


def validate_copy_targets(target: Path, manifest: dict) -> None:
    bindings = manifest.get('copy_targets')
    if bindings is None:
        if manifest['kind'] == 'edit':
            return
        # Old transactions have no destination mapping. Never infer an absent
        # original from an alias key and delete an existing file during recovery.
        names = set(manifest['before']) | set(manifest['variants']) | set(manifest.get('after', {}))
        if any(name != actual for name, actual in copy_targets(target, list(names)).items()):
            raise ValueError('Legacy copy transaction has equivalent names; preserve it for review and prepare again')
        return
    current = copy_targets(target, list(bindings))
    if any(not same_path(target / current[name], target / actual) for name, actual in bindings.items()):
        raise ValueError('Copy destination binding changed; prepare and review again')


def original_bytes(manifest: dict, name: str) -> str | None:
    return manifest['before'].get((manifest.get('copy_targets') or {}).get(name, name))


def copy_snapshot(target: Path, manifest: dict) -> dict:
    validate_copy_targets(target, manifest)
    files = snapshot(target, manifest.get('watch_paths'))
    # Some filesystems return a normalized spelling after creating a new name.
    # Project only those new destinations; existing snapshot names stay exact.
    buckets = {}
    for name in files:
        buckets.setdefault(tuple(map(name_key, Path(name).parts)), []).append(name)
    for name in set((manifest.get('copy_targets') or {}).values()) - set(manifest['before']):
        if name in files:
            continue
        matches = [item for item in buckets.get(tuple(map(name_key, Path(name).parts)), [])
                   if item in files and same_path(target / item, target / name)]
        if len(matches) > 1:
            raise ValueError('Ambiguous copy snapshot: ' + name)
        if matches:
            files[name] = files.pop(matches[0])
    return files


def edit_binding(context: dict, target: Path, name: str) -> dict:
    """Bind an ordinary document address to its file without replacing its links."""
    relative(name)
    try:
        (target / name).stat()
    except FileNotFoundError:
        pass  # A supported document may be created through a dangling alias.
    pending = list((target / name).parts[1:])
    current = Path(target.anchor)
    links = []
    while pending:
        part = pending.pop(0)
        if part == '..':
            if not current.is_dir():
                raise ValueError('Document alias crosses a missing or non-directory path: ' + name)
            current = current.parent
            continue
        if part in ('.', ''):
            if not pending or (current.exists() and not current.is_dir()):
                raise ValueError('Document alias requires a directory: ' + name)
            continue
        candidate = current / part
        if candidate.is_symlink():
            if len(links) >= 40:
                raise ValueError('Too many document symlinks: ' + name)
            info = candidate.lstat()
            value = os.readlink(candidate)
            links.append({'path': str(candidate), 'value': value,
                          'device': info.st_dev, 'inode': info.st_ino,
                          'ctime_ns': info.st_ctime_ns})
            if value.startswith('/'):
                current = Path('/')
                pending = value.split('/')[1:] + pending
            else:
                pending = value.split('/') + pending
        else:
            if pending and candidate.exists() and not candidate.is_dir():
                raise ValueError('Document alias crosses a non-directory path: ' + name)
            current = candidate
    # Resolve through the same authority/plugin boundary as public path checks.
    actual = feature_path(context, str(current))
    if actual != current:
        raise ValueError('Document binding changed during inspection: ' + name)
    for parent in (actual, *actual.parents):
        safe(parent)
        if parent == target or parent == Path(parent.anchor):
            break
    artifact = name.startswith(('specs/', 'templates/overrides/')) or name in KNOWLEDGE
    if links:
        # Control files are address-bound; artifact aliases cannot impersonate a
        # selector/configuration/transaction or make an otherwise forbidden write.
        if not artifact:
            raise ValueError('Only document artifacts may use edit symlinks: ' + name)
        if target_inside(actual, target):
            if not (target_inside(actual, target / 'specs') or target_inside(actual, target / 'templates/overrides')
                    or any(same_target(actual, target / name) for name in KNOWLEDGE)):
                raise ValueError('Document alias targets a reserved store path: ' + name)
    if artifact:
        # A plain file may itself be referenced by another store's control alias.
        # Recheck that role on every binding, including apply and recovery.
        document_path(context, actual)
    return {'path': str(actual), 'links': links}


def edit_bindings(context: dict, target: Path, paths: list[str]) -> dict:
    result = {name: edit_binding(context, target, name) for name in sorted(set(paths))}
    destinations = []
    for item in result.values():
        path = Path(item['path'])
        if any(same_target(path, other) for other in destinations):
            raise ValueError('Ordinary edit paths must have distinct destinations')
        destinations.append(path)
    return result


def bound_paths(context: dict, target: Path, bindings: dict) -> dict:
    if edit_bindings(context, target, list(bindings)) != bindings:
        raise ValueError('Document alias binding changed; prepare and review again')
    return {name: Path(item['path']) for name, item in bindings.items()}


def edit_snapshot(context: dict, target: Path, bindings: dict) -> dict:
    paths = bound_paths(context, target, bindings)
    result = {}
    total = 0
    for name, path in paths.items():
        if path.exists():
            data = file_bytes(path)
            total += len(data)
            if total > MAX_TOTAL or len(result) >= 10000:
                raise ValueError('Store snapshot exceeds supported size')
            result[name] = base64.b64encode(data).decode()
    bound_paths(context, target, bindings)
    return result


def transaction_snapshot(context: dict, target: Path, manifest: dict) -> dict:
    if manifest.get('edit_bindings') is not None:
        return edit_snapshot(context, target, manifest['edit_bindings'])
    return copy_snapshot(target, manifest)


def transaction_path(context: dict, target: Path, manifest: dict, name: str) -> Path:
    if manifest.get('edit_bindings') is not None:
        path = bound_paths(context, target, manifest['edit_bindings'])[name]
        return document_path(context, path, allowed_control=target / name)
    path = destination(target, (manifest.get('copy_targets') or {}).get(name, name))
    logical = target / name
    if not same_path(path, logical):
        raise ValueError('Copy destination no longer matches its logical address: ' + name)
    # Control permissions belong to the explicit logical address; retaining an
    # existing directory's spelling must neither grant nor remove those rights.
    document_path(context, logical, allowed_control=logical)
    return path


def prepare(project: Path, kind: str, sources: list[Path], features: list[str], paths: list[str]) -> dict:
    context = resolve(project, missing=True)
    target = authority_action(context, kind)
    sources = allowed_sources(context, kind, sources)
    if kind == 'edit':
        # These paths are explicit; an unused saved selection is only a watched
        # binding, not a prerequisite for authoring or selecting a new feature.
        validate_state(context, selection=False, knowledge_aliases=True)
        if not target.is_dir() or not paths or any(not editable(n, context) for n in paths):
            raise ValueError('Select supported files within the effective store')
    if any('/' in f or f in ('.', '..', '') for f in features):
        raise ValueError('Select exact feature directory names, not arbitrary paths')
    if target.exists() and kind != 'edit':
        validate_state({'SDLC_DIR': str(target)}, selection=False)
    # Watch only this edit and its workspace binding. Other requirements and
    # other worktrees' selections must not invalidate an ordinary edit.
    watch_paths = (sorted(set(paths + ['init-options.json',
                    Path(context['FEATURE_JSON']).relative_to(target).as_posix()]))
                   if kind == 'edit' else None)
    bindings = edit_bindings(context, target, watch_paths) if kind == 'edit' else None
    if bindings is not None:
        for name in paths:
            document_path(context, Path(bindings[name]['path']), allowed_control=target / name)
    before = edit_snapshot(context, target, bindings) if bindings is not None else optional_snapshot(target, watch_paths)
    originals = {str(p): source_snapshot(p) for p in sources}
    if any(not any(n.startswith('specs/' + f + '/') for files in originals.values() for n in files) for f in features):
        raise ValueError('Selected requirement is absent from sources')
    variants, target_names = {}, None
    scoped = {source: source_files(Path(source), files, features) for source, files in originals.items()}
    if kind != 'edit':
        names = {name for files in scoped.values() for name in files if in_scope(name, kind, features, paths)}
        if 'memory/constitution.md' in names:
            names.add('memory/.constitution-template.json')
        target_names = copy_targets(target, list(names))
    representatives, source_destinations = {}, set()
    changed_sources = []
    for source, files in scoped.items():
        changed = False
        for name, data in files.items():
            if in_scope(name, kind, features, paths):
                actual = target_names[name]
                if (source, actual) in source_destinations:
                    raise ValueError('One source has multiple files at the same copy destination: ' + name)
                source_destinations.add((source, actual))
                representative = representatives.setdefault(actual, name)
                if before.get(actual) != data:
                    variants.setdefault(representative, {})[source] = data
                    changed = True
        if changed:
            changed_sources.append(source)
    if kind != 'edit':
        target_context = dict(context, SDLC_DIR=str(target),
                              mode='local' if kind == 'import' else context['mode'])
        for name in variants:
            document_path(target_context, destination(target, name), allowed_control=target / name)
    proposal = {}
    for name, values in variants.items():
        source = next(iter(values))
        proposal[name] = ({'action': 'copy', 'source': source}
                          if target_names[name] not in before and len(set(values.values())) == 1
                          else {'action': 'unresolved'})
    for name in paths:
        proposal[name] = {'action': 'unresolved'}
    identifier = uuid.uuid4().hex
    target.mkdir(exist_ok=True)
    with write_lock(target):
        if (edit_snapshot(context, target, bindings) if bindings is not None else snapshot(target, watch_paths)) != before:
            raise ValueError('Target changed during preparation')
        folder = target / 'transactions' / identifier
        safe(folder.parent)
        folder.mkdir(parents=True)
        manifest = {'schema': 1, 'kind': kind, 'project': context['PROJECT_ROOT'],
                    'authority': context['AUTHORITY_DIR'], 'target': str(target),
                    'features': features, 'paths': paths, 'watch_paths': watch_paths, 'before': before,
                    'edit_bindings': bindings, 'copy_targets': target_names,
                    'sources': originals, 'variants': variants, 'status': 'prepared'}
        atomic(folder / 'manifest.json', json_bytes(manifest))
        atomic(folder / 'proposal.json', json_bytes(proposal))
    return {'transaction': str(folder), 'proposal': str(folder / 'proposal.json'),
            'changed_sources': changed_sources, 'multiple_sources': len(changed_sources) > 1,
            'files': list(proposal), 'unresolved': [n for n, v in proposal.items() if v['action'] == 'unresolved']}


def load_transaction(project: Path, folder: Path, *, check_sources=True) -> tuple[dict, dict, Path]:
    context = resolve(project, missing=True)
    safe(folder)
    manifest = read_object(folder / 'manifest.json')
    if manifest.get('schema') != 1 or manifest.get('kind') not in ('collect', 'import', 'edit'):
        raise ValueError('Unsupported transaction')
    target = authority_action(context, manifest['kind'])
    local_edit = manifest['kind'] == 'edit' and context['mode'] == 'local'
    if (manifest['project'] != context['PROJECT_ROOT'] or (not local_edit and manifest['authority'] != context['AUTHORITY_DIR']) or
            manifest['target'] != str(target) or folder.resolve().parent != target / 'transactions'):
        raise ValueError('Transaction binding changed or does not belong to this project')
    if check_sources:
        allowed_sources(context, manifest['kind'], [Path(p) for p in manifest['sources']])
    if manifest['status'] in ('prepared', 'applying'):
        validate_copy_targets(target, manifest)
    return context, manifest, target


def planned_bytes(context: dict, manifest: dict, proposal: dict) -> dict:
    expected = set(manifest['variants']) | set(manifest['paths'])
    if set(proposal) != expected:
        raise ValueError('Proposal must resolve exactly the prepared paths')
    output = {}
    for name, decision in proposal.items():
        relative(name)
        if not in_scope(name, manifest['kind'], manifest['features'], manifest['paths']):
            raise ValueError('Proposal path is outside the selected scope')
        if manifest['kind'] == 'edit' and not editable(name, context):
            raise ValueError('Unsupported ordinary edit path')
        action = decision.get('action')
        if action == 'skip':
            continue
        if action == 'copy' and decision.get('source') in manifest['variants'].get(name, {}):
            output[name] = manifest['variants'][name][decision['source']]
        elif action == 'replace' and isinstance(decision.get('text'), str):
            output[name] = base64.b64encode(decision['text'].encode()).decode()
        else:
            raise ValueError('Unresolved or invalid proposal: ' + name)
        if manifest['kind'] == 'edit' and name in ('init-options.json', Path(context['FEATURE_JSON']).relative_to(context['SDLC_DIR']).as_posix()):
            data = parse_object(base64.b64decode(output[name]))
            if not isinstance(data, dict):
                raise ValueError('Candidate JSON must be an object')
            if name == 'init-options.json':
                if data.get('script', 'sh') != 'sh' or type(data.get('sdlc_layout', 1)) is not int or data.get('sdlc_layout', 1) != 1 or data.get('feature_numbering', 'sequential') not in ('sequential', 'timestamp'):
                    raise ValueError('Candidate has unsupported initialization settings')
            else:
                if not isinstance(data.get('feature_directory'), str):
                    raise ValueError('Candidate selection needs feature_directory')
                feature_path(context, data['feature_directory'])
        if len(base64.b64decode(output[name])) > MAX_FILE:
            raise ValueError('Candidate file is too large')
    # Preserve genuine source generation history only when copying a new constitution.
    constitution = 'memory/constitution.md'
    record = 'memory/.constitution-template.json'
    if original_bytes(manifest, constitution) is None and original_bytes(manifest, record) is None:
        decision = proposal.get(constitution, {})
        if decision.get('action') == 'copy':
            source = decision['source']
            original = source_files(Path(source), manifest['sources'][source], manifest['features'])
            if record in original:
                output[record] = original[record]
    output = {n: data for n, data in output.items() if original_bytes(manifest, n) != data}
    for name in output:
        transaction_path(context, Path(manifest['target']), manifest, name)
    return output


def destination(target: Path, name: str) -> Path:
    relative(name)
    path = target / name
    for parent in (path, *path.parents):
        safe(parent)
        if parent == target:
            break
    if not target_inside(path.resolve(), target):
        raise ValueError('Destination escapes store')
    return path


def rollback(context: dict, target: Path, manifest: dict) -> None:
    # Validate every affected file first; never overwrite an unrelated later edit.
    validate_copy_targets(target, manifest)
    def owned_change(name):
        path = transaction_path(context, target, manifest, name)
        now = base64.b64encode(file_bytes(path)).decode() if path.exists() else None
        if now == original_bytes(manifest, name):
            return False
        if (now != manifest['after'][name] or now is None or
                published_identity(path.stat()) != manifest.get('published', {}).get(name)):
            raise ValueError('Recovery cannot verify publication ownership or would overwrite a later edit: ' + name)
        return True
    for name in manifest['after']:
        owned_change(name)
    for name in reversed(list(manifest['after'])):
        if not owned_change(name):
            continue
        path = transaction_path(context, target, manifest, name)
        old = original_bytes(manifest, name)
        if old is None:
            path.unlink(missing_ok=True)
        else:
            atomic(path, base64.b64decode(old))


def apply(project: Path, folder: Path) -> dict:
    context, manifest, target = load_transaction(project, folder)
    if manifest['status'] == 'applied':
        return {'status': 'already_applied', 'transaction': str(folder)}
    if manifest['status'] != 'prepared':
        raise ValueError('Interrupted transaction requires recovery')
    proposal = read_object(folder / 'proposal.json')
    output = planned_bytes(context, manifest, proposal)
    with write_lock(target):
        if transaction_snapshot(context, target, manifest) != manifest['before']:
            raise ValueError('Target changed; prepare and review again')
        for source, original in manifest['sources'].items():
            if source_snapshot(Path(source)) != original:
                raise ValueError('Source changed; prepare and review again')
        # Re-resolve while locked so changed authority registration cannot redirect a write.
        context, _, _ = load_transaction(project, folder)
        if transaction_snapshot(context, target, manifest) != manifest['before']:
            raise ValueError('Target changed; prepare and review again')
        output = planned_bytes(context, manifest, proposal)
        manifest.update(status='applying', after=output, published={})
        atomic(folder / 'manifest.json', json_bytes(manifest))
        try:
            for name, data in output.items():
                path = transaction_path(context, target, manifest, name)
                old = original_bytes(manifest, name)
                now = base64.b64encode(file_bytes(path)).decode() if path.exists() else None
                if now != old:
                    raise ValueError('Destination changed before publication: ' + name)
                path.parent.mkdir(parents=True, exist_ok=True)
                transaction_path(context, target, manifest, name)
                manifest['published'][name] = publish_data(path, base64.b64decode(data),
                                                         base64.b64decode(old) if old is not None else None)
                atomic(folder / 'manifest.json', json_bytes(manifest))
            for name, data in output.items():
                if file_bytes(transaction_path(context, target, manifest, name)) != base64.b64decode(data):
                    raise ValueError('Written data failed verification: ' + name)
            published = {(manifest.get('copy_targets') or {}).get(n, n): data for n, data in output.items()}
            if transaction_snapshot(context, target, manifest) != dict(manifest['before'], **published):
                raise ValueError('Target changed during publication')
        except BaseException:
            try:
                rollback(context, target, manifest)
                manifest['status'] = 'recovered'
                atomic(folder / 'manifest.json', json_bytes(manifest))
            except (OSError, ValueError):
                pass
            raise
        manifest['status'] = 'applied'
        atomic(folder / 'manifest.json', json_bytes(manifest))
    return {'status': 'applied', 'written': list(output),
            'skipped': [n for n, v in proposal.items() if v['action'] == 'skip'], 'transaction': str(folder)}


def recover(project: Path, folder: Path) -> dict:
    # Recovery restores the recorded target; it does not import source data again.
    context, manifest, target = load_transaction(project, folder, check_sources=False)
    if manifest['status'] == 'recovered':
        return {'status': 'already_recovered'}
    if manifest['status'] != 'applying':
        raise ValueError('Only interrupted applying transactions may be recovered')
    release_stale_lock(target)
    with write_lock(target):
        context, _, _ = load_transaction(project, folder, check_sources=False)
        rollback(context, target, manifest)
        manifest['status'] = 'recovered'
        atomic(folder / 'manifest.json', json_bytes(manifest))
    return {'status': 'recovered', 'transaction': str(folder)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'apply', 'recover'))
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--kind', choices=('collect', 'import', 'edit'), default='collect')
    parser.add_argument('--source', type=Path, action='append', default=[])
    parser.add_argument('--feature', action='append', default=[])
    parser.add_argument('--path', action='append', default=[])
    parser.add_argument('--transaction', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            result = prepare(args.project, args.kind, args.source, args.feature, args.path)
        elif args.transaction:
            result = (apply if args.action == 'apply' else recover)(args.project, args.transaction)
        else:
            raise ValueError('--transaction is required')
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
