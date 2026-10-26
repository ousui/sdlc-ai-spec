#!/usr/bin/env python3
"""Local/authority storage binding. Standard library; Git discovery is read-only."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import unicodedata
import uuid

PLUGIN = Path(__file__).resolve().parents[2]
KNOWLEDGE = ('memory/constitution.md', 'memory/long-term.md')


def path_anchor(path: Path) -> tuple[Path, tuple[int, int], tuple[str, ...]]:
    """Identify the nearest existing object without changing caller path spelling."""
    suffix = []
    while True:
        try:
            info = path.stat()
            return path, (info.st_dev, info.st_ino), tuple(reversed(suffix))
        except FileNotFoundError:
            if path == path.parent:
                raise
            suffix.append(path.name)
            path = path.parent


def lookup_sensitive(directory: Path, name: str, variant: str) -> bool:
    """Require stable original metadata before interpreting an alternate lookup."""
    original = directory / name
    first = original.lstat()
    try:
        second = (directory / variant).lstat()
    except FileNotFoundError:
        second = None
    try:
        after = original.lstat()
    except FileNotFoundError as error:
        raise ValueError('Directory entry changed during lookup: ' + str(original)) from error
    identity = first.st_dev, first.st_ino
    if identity != (after.st_dev, after.st_ino):
        raise ValueError('Directory entry changed during lookup: ' + str(original))
    return second is None or identity != (second.st_dev, second.st_ino)


def case_sensitive(directory: Path, *, strict: bool = False) -> bool:
    if sys.platform == 'darwin':
        # Darwin sys/unistd.h: _PC_CASE_SENSITIVE is 11 (not exposed by Python).
        try:
            value = os.pathconf(directory, 11)
        except OSError:
            if strict:
                raise
            value = None
        if value in (0, 1):
            return bool(value)
    if strict:
        raise ValueError('Cannot verify case-distinct source paths from native directory attributes: ' + str(directory))
    # Other filesystems can demonstrate their lookup rule using existing entries;
    # lstat also works for dangling aliases. Never create a probe in user data.
    with os.scandir(directory) as entries:
        for entry in entries:
            index = next((i for i, c in enumerate(entry.name) if c.isascii() and c.isalpha()), None)
            if index is None:
                continue
            variant = entry.name[:index] + entry.name[index].swapcase() + entry.name[index + 1:]
            try:
                return lookup_sensitive(directory, entry.name, variant)
            except FileNotFoundError:
                continue
    raise ValueError('Cannot verify case-distinct missing paths in this directory: ' + str(directory))


def normalization_sensitive(directory: Path, *, strict: bool = False) -> bool:
    """Observe canonical Unicode lookup using existing entries, without a probe write."""
    if strict:
        # No native normalization attribute is available here. A transient probe
        # cannot prove that a known source and its missing role are distinct.
        raise ValueError('Cannot verify Unicode normalization of source roles: ' + str(directory))
    with os.scandir(directory) as entries:
        for entry in entries:
            for form in ('NFC', 'NFD'):
                variant = unicodedata.normalize(form, entry.name)
                if variant == entry.name:
                    continue
                try:
                    return lookup_sensitive(directory, entry.name, variant)
                except FileNotFoundError:
                    continue
    raise ValueError('Cannot verify Unicode normalization of missing paths in this directory: ' + str(directory))


def name_key(value: str) -> str:
    """Bucket possible aliases; actual equivalence still requires filesystem checks."""
    return unicodedata.normalize('NFD', unicodedata.normalize('NFD', value).casefold())


def distinct_source_spelling(left: Path, right: Path) -> bool:
    """Exclude a nonmatching role only when it cannot alias the known source.

    Repeated absence cannot establish distinctness: a valid alternate spelling
    can disappear during every lookup. Use the lookup rules of each actual
    parent instead. Only native attributes may establish a sensitive rule for
    this decision; directory observations are not evidence of stable absence.
    """
    if len(left.parts) != len(right.parts):
        return True
    parent = Path()
    for actual, candidate in zip(left.parts, right.parts):
        if actual != candidate:
            if name_key(actual) != name_key(candidate):
                return True
            normalized = unicodedata.normalize('NFD', actual) == unicodedata.normalize('NFD', candidate)
            if not normalized and case_sensitive(parent, strict=True):
                return True
            if normalized or actual.casefold() != candidate.casefold():
                if normalization_sensitive(parent, strict=True):
                    return True
        parent = parent / actual
    return False


def same_path(left: Path, right: Path, *, strict: bool = False) -> bool:
    if left == right:
        return True
    if strict:
        # The left spelling is a known snapshot file; only the candidate may be absent.
        first = left.stat()
        try:
            second = right.stat()
        except FileNotFoundError:
            second = None
        identity = first.st_dev, first.st_ino
        matches = second is not None and identity == (second.st_dev, second.st_ino)
        distinct = not matches and distinct_source_spelling(left, right)
        after = left.stat()
        if identity != (after.st_dev, after.st_ino):
            raise ValueError('Source path changed during lookup: ' + str(left))
        if not matches:
            if distinct:
                return False
            raise ValueError('Source role changed during lookup: ' + str(right))
        return True
    try:
        anchor, identity, suffix = path_anchor(left)
        _, other_identity, other_suffix = path_anchor(right)
    except OSError:
        return False  # Unrelated inaccessible/invalid metadata adds no ownership.
    if identity != other_identity:
        return False
    if suffix == other_suffix:
        return True
    if tuple(map(name_key, suffix)) != tuple(map(name_key, other_suffix)):
        return False
    canonically_equal = (tuple(unicodedata.normalize('NFD', p) for p in suffix) ==
                         tuple(unicodedata.normalize('NFD', p) for p in other_suffix))
    if not canonically_equal:
        if case_sensitive(anchor):
            return False
    if canonically_equal or tuple(p.casefold() for p in suffix) != tuple(p.casefold() for p in other_suffix):
        if normalization_sensitive(anchor):
            return False
    return True


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents or any(same_path(p, root) for p in (path, *path.parents))


def same_target(left: Path, right: Path) -> bool:
    """Compare resolved ownership targets; an uncertain negative must stop a write.

    Either target may legitimately be absent. Positive anchor identity with the
    same suffix is conclusive; different observations need a namespace proof,
    not another entry's lookup result or a transient candidate inode.
    """
    if left == right:
        return True
    anchor, identity, suffix = path_anchor(left)
    _, other_identity, other_suffix = path_anchor(right)
    if identity == other_identity:
        if suffix == other_suffix:
            return True
        # Existing aliases of the same parent need no spelling assumptions.
        left, right = anchor.joinpath(*suffix), anchor.joinpath(*other_suffix)
    if tuple(map(name_key, left.parts)) != tuple(map(name_key, right.parts)):
        return False
    if distinct_source_spelling(left, right):
        return False
    raise ValueError('Cannot verify target path relationship: ' + str(left) + ' / ' + str(right))


def target_inside(path: Path, root: Path) -> bool:
    """Ownership containment, separate from ordinary feature address matching."""
    return path == root or root in path.parents or any(same_target(p, root) for p in (path, *path.parents))


def project_directory(path: Path) -> Path:
    """Use the filesystem's directory spelling for project identity, never feature values."""
    current = Path.cwd()
    if same_path(path, current):
        return current
    actual = None
    if sys.platform == 'darwin':
        import fcntl
        try:
            # Darwin O_SEARCH opens a directory using traversal rights only.
            descriptor = os.open(path, getattr(os, 'O_SEARCH', 0x40000000 | os.O_DIRECTORY))
        except PermissionError:
            # A searchable directory need not be readable. Its parent entries
            # can still establish the spelling without opening the directory.
            pass
        else:
            try:
                # Darwin sys/fcntl.h: F_GETPATH (50) returns a MAXPATHLEN buffer.
                raw = fcntl.fcntl(descriptor, getattr(fcntl, 'F_GETPATH', 50), b'\0' * 1024)
                actual = Path(os.fsdecode(raw.split(b'\0', 1)[0]))
            finally:
                os.close(descriptor)
    if actual is None:
        # Resolve existing directory entries only; no subprocess, cwd change or
        # assumption that a case-sensitive filesystem also preserves normalization.
        actual = Path(path.anchor)
        for part in path.parts[1:]:
            with os.scandir(actual) as entries:
                names = [entry.name for entry in entries]
            if part not in names:
                matches = [name for name in names if not (actual / name).is_symlink()
                           and same_path(actual / name, actual / part)]
                if len(matches) != 1:
                    raise ValueError('Cannot resolve project directory identity: ' + str(path))
                part = matches[0]
            actual = actual / part
    if not same_path(path, actual):
        raise ValueError('Project directory changed during identity lookup: ' + str(path))
    return actual


def parse_object(content: str | bytes) -> dict:
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    data = json.loads(content, object_pairs_hook=unique)
    if not isinstance(data, dict):
        raise ValueError('Expected JSON object')
    return data


def read_object(path: Path) -> dict:
    safe(path)
    return parse_object(path.read_text(encoding='utf-8'))


def json_bytes(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()


def safe(path: Path, plugin: Path = PLUGIN) -> None:
    if target_inside(path.resolve(), plugin.resolve()):
        raise ValueError('Project data cannot target the plugin')
    if path.is_symlink():
        raise ValueError('Symlink data is unsupported: ' + str(path))
    if path.exists() and not (path.is_dir() or path.is_file()):
        raise ValueError('Unsupported data type: ' + str(path))
    if path.is_file() and path.stat().st_nlink != 1:
        raise ValueError('Hardlinked data is unsupported: ' + str(path))


def validate_selection_path(state: Path, selection: Path) -> None:
    """Keep a workspace's selection at its own address without parsing its content."""
    current = state
    for part in selection.relative_to(state).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Workspace selection cannot use a symlink: ' + str(current))


def git_output(project: Path, *args: str) -> bytes | None:
    if not shutil.which('git'):
        return None
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env['GIT_OPTIONAL_LOCKS'] = '0'
    try:
        process = subprocess.run(['git', '-C', str(project), *args], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    except subprocess.TimeoutExpired as error:
        raise ValueError(f'Git workspace discovery timed out after {error.timeout} seconds') from error
    return process.stdout if process.returncode == 0 else None


def worktrees(project: Path) -> tuple[Path, list[Path]]:
    if not any(os.path.lexists(p / '.git') for p in (project, *project.parents)):
        return project, [project]
    raw = git_output(project, 'rev-parse', '--show-toplevel')
    if raw is None:
        raise ValueError('Cannot discover Git workspace identity for a project with a Git marker')
    # Git appends one LF; whitespace belonging to the pathname must survive.
    repo = project_directory(Path(os.fsdecode(raw).removesuffix('\n')).resolve())
    listing = git_output(project, 'worktree', 'list', '--porcelain', '-z')
    if listing is None:
        raise ValueError('Cannot discover Git worktrees')
    roots = [Path(os.fsdecode(item[9:])).resolve() for item in listing.split(b'\0')
             if item.startswith(b'worktree ')]
    # Git versions may leave an equivalent .GIT suffix in their listing. Only
    # recognize the actual gitfile; repository/backlink checks still follow.
    roots = [root.parent if root.is_file() and not root.is_symlink()
             and name_key(root.name) == name_key('.git') and same_path(root, root.parent / '.git')
             else root for root in roots]
    roots = [project_directory(root) if root.is_dir() else root for root in roots]
    if not roots or not roots[0].is_dir():
        raise ValueError('Main workspace is unavailable; select an accessible authority explicitly')
    return repo, roots


def git_identity(project: Path) -> tuple[Path, Path] | None:
    """Verify the repository currently occupying a registered workspace address."""
    top = git_output(project, 'rev-parse', '--show-toplevel')
    common = git_output(project, 'rev-parse', '--git-common-dir')
    if top is None or common is None:
        return None
    directory = Path(os.fsdecode(common).removesuffix('\n'))
    if not directory.is_absolute():
        directory = project / directory
    return (project_directory(Path(os.fsdecode(top).removesuffix('\n')).resolve()),
            project_directory(directory.resolve()))


def registered_workspace(root: Path, common: Path) -> bool:
    if git_identity(root) != (root, common) or (root / '.git').is_symlink():
        return False
    raw = git_output(root, 'rev-parse', '--absolute-git-dir')
    if raw is None:
        return False
    directory = project_directory(Path(os.fsdecode(raw).removesuffix('\n')).resolve())
    try:
        backlink = Path((directory / 'gitdir').read_text().removesuffix('\n'))
        if not backlink.is_absolute():
            backlink = directory / backlink
        return (directory != common and
                same_path(backlink.parent.resolve(), root) and same_path(backlink, root / '.git'))
    except (OSError, ValueError):
        return False


def workspace_sources(repo: Path, roots: list[Path], relative: Path) -> list[Path]:
    candidates = [(root, root / relative) for root in roots[1:]
                  if (root / relative / '.sdlc').is_dir()]
    if not candidates:
        return []
    identity = git_identity(repo)
    if identity is None:
        return []
    result = []
    for root, project in candidates:
        state = project / '.sdlc'
        if not state.is_dir() or project.resolve() != project:
            continue
        project = project_directory(project)
        state = project / '.sdlc'
        expected = (root, identity[1])
        # The workspace and the corresponding subproject must both still belong
        # to this repository. A stale listing or a nested repo is not a source.
        if registered_workspace(root, identity[1]) and (project == root or git_identity(project) == expected):
            result.append(state)
    return result


def resolve(project: Path | None = None, *, plugin: Path = PLUGIN,
            missing: bool = False, cwd: Path | None = None, env=None, observe=False) -> dict:
    env = os.environ if env is None else env
    cwd = Path.cwd() if cwd is None else cwd
    explicit = project is not None or bool(env.get('SDLC_INIT_DIR'))
    value = project if project is not None else env.get('SDLC_INIT_DIR') or cwd
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError('Project path must be nonempty')
    root = Path(value).expanduser()
    if not root.is_absolute():
        root = cwd / root
    root = root.resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or target_inside(root, plugin.resolve()):
        raise ValueError('Select an existing business project outside the plugin')
    root = project_directory(root)
    repo, roots = worktrees(root)
    if not explicit:
        # Do not cross a Git project boundary. A malformed nearest marker still wins.
        candidates = [p for p in (root, *root.parents) if inside(p, repo)]
        if repo == root and len(roots) == 1 and not any(os.path.lexists(p / '.git') for p in (root, *root.parents)):
            candidates = list((root, *root.parents))[:-1]
        selected = next((p for p in candidates if os.path.lexists(p / '.sdlc')), None)
        if selected is None and len(roots) > 1:
            selected = next((p for p in candidates
                             if os.path.lexists(roots[0] / p.relative_to(repo) / '.sdlc')), None)
        root = selected or repo
        repo, roots = worktrees(root)
    relative = root.relative_to(repo)
    caller_repo, caller_roots = worktrees(cwd.resolve())
    same_repository = roots[0] == caller_roots[0]
    linked_origin = same_repository and caller_repo != caller_roots[0]
    if explicit and same_repository and caller_repo != repo:
        caller_project = caller_repo / relative
        if os.path.lexists(caller_project / '.sdlc'):
            raise ValueError('Local workspace data cannot be bypassed by selecting another worktree')
    main = roots[0] / relative
    if main.is_dir():
        main = project_directory(main)
    local = root / '.sdlc'
    has_local = root != main and os.path.lexists(local)
    registry = main / '.sdlc/store.json'
    authority_error = None
    registered_sources = []
    try:
        if root != main:
            identity = git_identity(repo)
            probe = main
            while True:
                try:
                    probe.lstat()
                    break
                except FileNotFoundError:
                    if probe == roots[0] or not inside(probe, roots[0]):
                        raise
                    probe = probe.parent
            if not stat.S_ISDIR(probe.stat().st_mode):
                raise ValueError('Corresponding main project ancestor is not a directory: ' + str(probe))
            if identity is None or git_identity(probe) != (roots[0], identity[1]):
                raise ValueError('Corresponding main project Git identity is unavailable or belongs to another repository: ' + str(main))
        if not observe:
            safe((main / '.sdlc').resolve(), plugin)
        registered = os.path.lexists(registry)
        config = read_object(registry) if registered else {}
        if registered and (type(config.get('schema')) is not int or config.get('schema') != 1 or not isinstance(config.get('sources', []), list)):
            raise ValueError('Unsupported store registry')
        raw_authority = config.get('authority', str(main / '.sdlc'))
        if not isinstance(raw_authority, str) or not Path(raw_authority).is_absolute():
            raise ValueError('Authority must be an absolute directory')
        authority = Path(raw_authority).resolve()
        if not observe:
            safe(authority, plugin)
        for value in config.get('sources', []):
            if not isinstance(value, str) or not Path(value).is_absolute():
                raise ValueError('Registered source must be an absolute directory')
            registered_sources.append(Path(value))
    except (OSError, ValueError, RuntimeError) as error:
        if not has_local:
            raise
        # Local work does not depend on authority being readable. Never guess an
        # authority after a failed registry read, including for external paths.
        authority, registered_sources = None, []
        authority_error = str(error)
        if local.resolve() != local:
            raise ValueError('Cannot validate a local alias while authority is unavailable') from error
    state = local if has_local else authority
    if not observe:
        safe(state.resolve(), plugin)
    if has_local and authority is not None and (target_inside(state.resolve(), authority) or target_inside(authority, state.resolve())):
        raise ValueError('Independent local storage cannot overlap authority; use disjoint data directories')
    if not observe and state.exists() and not state.is_dir():
        raise ValueError('Invalid local/authority data directory: ' + str(state))
    if not state.is_dir() and not missing:
        raise ValueError('No initialized .sdlc project found; run sdlc-000-init explicitly')
    if not observe:
        state = state.resolve()
    workspace = hashlib.sha256(str(root).encode()).hexdigest()[:24]
    selection = state / ('workspaces/' + workspace + '/feature.json' if root != main and not has_local else 'feature.json')
    validate_selection_path(state, selection)
    sources = workspace_sources(repo, roots, relative) + registered_sources
    sources = sorted({str(project_directory(p.resolve())) for p in sources if p.is_dir()
                      and (authority is None or not same_path(p.resolve(), authority))
                      and not same_path(p.resolve(), main / '.sdlc')})
    return {'PROJECT_ROOT': str(root), 'MAIN_PROJECT_ROOT': str(main),
            'SDLC_DIR': str(state), 'AUTHORITY_DIR': str(authority) if authority is not None else None,
            'FEATURE_JSON': str(selection), 'STORE_REGISTRY': str(registry),
            'STORE_DIRS': [str(r / relative / '.sdlc') for r in roots] + [str(p) for p in registered_sources],
            'mode': 'local' if has_local else 'authority' if root == main else 'shared',
            'can_collect': root == main and not linked_origin, 'local_exists': has_local,
            'authority_exists': authority.is_dir() if authority is not None else None,
            'authority_error': authority_error, 'sources': sources}


def require_authority(context: dict) -> Path:
    if context['AUTHORITY_DIR'] is None:
        raise ValueError('Authority is unavailable: ' + str(context.get('authority_error')))
    return Path(context['AUTHORITY_DIR'])


def validate_options(data: dict) -> None:
    """Keep accepted edit candidates consistent with ordinary configuration reads."""
    if data.get('script', 'sh') != 'sh' or type(data.get('sdlc_layout', 1)) is not int or data.get('sdlc_layout', 1) != 1:
        raise ValueError('Unsupported project profile/layout')
    if data.get('feature_numbering', data.get('branch_numbering', 'sequential')) not in ('sequential', 'timestamp'):
        raise ValueError('Invalid feature_numbering')


def validate_state(context: dict, *, selection=True, knowledge_aliases=False) -> None:
    state = Path(context['SDLC_DIR'])
    if os.path.lexists(state / '.init-pending.json'):
        raise ValueError('Initialization is incomplete; rerun INIT with the original selections before using this store')
    for name in ('memory', 'specs', 'templates', 'workspaces', 'transactions'):
        path = state / name
        safe(path)
        if path.exists() and not path.is_dir():
            raise ValueError('Expected data directory: ' + str(path))
    options = state / 'init-options.json'
    if options.exists():
        validate_options(read_object(options))
    for name in ('extensions.yml', 'extensions', 'presets'):
        if os.path.lexists(state / name):
            raise ValueError('Unsupported optional project profile: ' + name)
    knowledge = [state / name for name in KNOWLEDGE] if knowledge_aliases else [state / 'memory/constitution.md']
    for path in knowledge:
        actual = document_path(context, path) if knowledge_aliases else path
        safe(actual)
        if actual.exists() and not actual.is_file():
            raise ValueError('Expected data file: ' + str(path))
    paths = []
    if selection:
        paths.append(Path(context['FEATURE_JSON']))
    for path in paths:
        safe(path)
        if path.exists() and not path.is_file():
            raise ValueError('Expected data file: ' + str(path))
    if selection and Path(context['FEATURE_JSON']).exists():
        selected = read_object(Path(context['FEATURE_JSON'])).get('feature_directory')
        if not isinstance(selected, str) or not selected.strip():
            raise ValueError('Invalid feature_directory in current workspace selection')


def feature_location(context: dict, value: str) -> str:
    """Map store addresses while preserving explicit path spelling for shell callers."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Empty or invalid feature directory')
    path = Path(value)
    if path.is_absolute():
        root, state = Path(context['PROJECT_ROOT']), Path(context['SDLC_DIR'])
        if not same_path((root / '.sdlc').resolve(), state.resolve()):
            # An absolute code-project .sdlc address denotes the same effective
            # store as a relative one. Preserve the suffix used by shell labels.
            for marker in re.finditer(r'(?<=/)\.sdlc(?=/|$)', value):
                prefix = Path(value[:marker.start()])
                if same_path(prefix.resolve(), root):
                    if not prefix.is_dir():
                        raise ValueError('Logical store address has an unavailable project prefix')
                    return str(state) + value[marker.end():]
        return value
    marker = re.match(r'((?:\./+)*)\.sdlc(?=/|$)', value)
    if marker:
        state = Path(context['SDLC_DIR'])
        return str(state.parent) + '/' + marker[1] + state.name + value[marker.end():]
    root, state = Path(context['PROJECT_ROOT']), Path(context['SDLC_DIR'])
    if not same_path((root / '.sdlc').resolve(), state.resolve()):
        for marker in re.finditer(r'(?<=/)\.sdlc(?=/|$)', value):
            prefix = root / value[:marker.start()]
            if same_path(prefix.resolve(), root):
                if not prefix.is_dir():
                    raise ValueError('Logical store address has an unavailable project prefix')
                return str(state) + value[marker.end():]
    return context['PROJECT_ROOT'] + '/' + value


def project_spelling(context: dict) -> str:
    """Retain the shell's project spelling for upstream's literal prefix strip.

    Identity checks select the prefix; they must not normalize the feature value
    itself, since a different alias can be an already saved no-op selection.
    """
    root, cwd = Path(context['PROJECT_ROOT']), Path.cwd()
    def matches(path: Path, target: Path) -> bool:
        try:
            return same_path(path.resolve(), target)
        except (OSError, RuntimeError):
            return False
    logical = Path(os.environ.get('PWD', str(cwd)))
    if not logical.is_absolute() or not matches(logical, cwd):
        logical = cwd
    override = os.environ.get('SDLC_INIT_DIR')
    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_absolute():
            candidate = logical / candidate
        candidate = Path(os.path.normpath(candidate))
        if matches(candidate, root):
            return str(candidate)
    for candidate in (logical, *logical.parents):
        if matches(candidate, root):
            return str(candidate)
    return str(root)


def resolve_alias(path: Path) -> Path | None:
    def inspect(address, seen):
        try:
            # Check before non-strict resolution can fold an inaccessible link
            # and following '..' out of the spelling, hiding its ownership error.
            _, before_identity, before_suffix = path_anchor(address)
            actual = address.resolve()
            # Non-strict realpath may leave an unresolved suffix after I/O or
            # permission errors. Verify its nearest existing ancestor as well.
            _, actual_identity, actual_suffix = path_anchor(actual)
            if not before_suffix and (before_identity != actual_identity or actual_suffix):
                raise ValueError('Store alias resolution changed: ' + str(address))
            return actual
        except RuntimeError as error:
            failure = error
        except OSError as error:
            if error.errno != errno.ELOOP:
                # Genuine missing suffixes already have an existing anchor.
                raise ValueError('Cannot inspect store alias ownership: ' + str(address)) from error
            failure = error
        # A loop error alone cannot discard an enumerated directory. Prove a
        # stable cycle using literal link entries and held parent namespaces.
        if address == address.parent:
            raise ValueError('Cannot inspect store alias cycle: ' + str(address)) from failure
        parent = inspect(address.parent, seen)
        if parent is None:
            return None
        with alias_directory(parent, metadata_only=True) as descriptor:
            if descriptor is None:
                raise ValueError('Store alias parent changed: ' + str(address)) from failure
            before = os.stat(address.name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISLNK(before.st_mode):
                raise ValueError('Store alias type changed: ' + str(address)) from failure
            value = os.readlink(address.name, dir_fd=descriptor)
            after = os.stat(address.name, dir_fd=descriptor, follow_symlinks=False)
            identity = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_mtime_ns, info.st_ctime_ns)
            if identity(before) != identity(after) or value != os.readlink(address.name, dir_fd=descriptor):
                raise ValueError('Store alias binding changed: ' + str(address)) from failure
            namespace = os.fstat(descriptor)
            key = namespace.st_dev, namespace.st_ino, address.name, before.st_dev, before.st_ino, value
            if key in seen:
                return None
            if len(seen) >= 40:
                raise ValueError('Cannot inspect store alias cycle: ' + str(address)) from failure
            target = Path(value)
            if not target.is_absolute():
                target = parent / target
            if inspect(target, seen | {key}) is not None:
                raise ValueError('Store alias cycle changed: ' + str(address)) from failure
        return None
    return inspect(path, set())


def entry_identity(info: os.stat_result) -> tuple:
    return info.st_dev, info.st_ino, info.st_mode, info.st_mtime_ns, info.st_ctime_ns


@contextmanager
def alias_directory(path: Path, *, metadata_only=False, expected=None):
    """Hold a directory while inspecting aliases; absence needs namespace evidence."""
    def unchanged(descriptor, before, address):
        try:
            current = address.stat()
            if (not stat.S_ISDIR(current.st_mode) or entry_identity(current) != entry_identity(before)
                    or entry_identity(os.fstat(descriptor)) != entry_identity(before)):
                raise ValueError('Store alias directory changed during inspection: ' + str(address))
        except OSError as error:
            raise ValueError('Cannot inspect store alias ownership: ' + str(address)) from error

    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    if metadata_only:
        metadata_flag = getattr(os, 'O_PATH', None)
        if metadata_flag is None and sys.platform == 'darwin':
            metadata_flag = getattr(os, 'O_SEARCH', 0x40000000)
        if metadata_flag is not None:
            flags = metadata_flag | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if expected is not None:
            raise ValueError('Cannot inspect store alias ownership: ' + str(path) + ': ' + str(error)) from error
        if error.errno not in (errno.ENOENT, errno.ENOTDIR, errno.EACCES) or path == path.parent:
            raise ValueError('Cannot inspect store alias ownership: ' + str(path)) from error
        # A positive leaf classification needs neither file read permission nor
        # parent enumeration. Hold a searchable parent and verify its namespace.
        metadata_flag = getattr(os, 'O_PATH', None)
        if metadata_flag is None and sys.platform == 'darwin':
            metadata_flag = getattr(os, 'O_SEARCH', 0x40000000)
        if metadata_flag is not None:
            try:
                metadata = os.open(path.parent, metadata_flag | getattr(os, 'O_DIRECTORY', 0)
                                   | getattr(os, 'O_NOFOLLOW', 0))
            except OSError as unavailable:
                if unavailable.errno not in (errno.ENOENT, errno.ENOTDIR, errno.EACCES):
                    raise ValueError('Cannot inspect store alias ownership: ' + str(path)) from unavailable
            else:
                leaf = False
                try:
                    parent_before = os.fstat(metadata)
                    try:
                        info = os.stat(path.name, dir_fd=metadata, follow_symlinks=False)
                    except OSError as unavailable:
                        unchanged(metadata, parent_before, path.parent)
                        if unavailable.errno not in (errno.ENOENT, errno.ENOTDIR):
                            raise ValueError('Cannot inspect store alias ownership: ' + str(path)) from unavailable
                        # A held, unchanged parent namespace also proves a
                        # missing leaf without requiring its read permission.
                        leaf = unavailable.errno == errno.ENOENT
                    else:
                        current = path.stat()
                        unchanged(metadata, parent_before, path.parent)
                        if (info.st_dev, info.st_ino, info.st_mode) != (current.st_dev, current.st_ino, current.st_mode):
                            raise ValueError('Store alias entry changed during inspection: ' + str(path))
                        if stat.S_ISDIR(info.st_mode):
                            raise ValueError('Cannot enumerate store aliases: ' + str(path)) from error
                        if stat.S_ISLNK(info.st_mode):
                            raise ValueError('Store alias binding changed during inspection: ' + str(path))
                        leaf = True
                finally:
                    os.close(metadata)
                if leaf:
                    yield None
                    return
        # A failed open is not proof of an absent subtree. Inspect its parent's
        # complete namespace, recursively allowing genuinely absent ancestors.
        with alias_directory(path.parent) as parent:
            if parent is not None:
                try:
                    with os.scandir(parent) as entries:
                        for entry in entries:
                            if name_key(entry.name) != name_key(path.name):
                                continue
                            if entry.name != path.name and not same_target(path.parent / entry.name, path):
                                continue
                            info = entry.stat(follow_symlinks=False)
                            if error.errno == errno.EACCES and stat.S_ISDIR(info.st_mode):
                                raise ValueError('Cannot enumerate store aliases: ' + str(path)) from error
                            if (error.errno == errno.ENOENT or stat.S_ISDIR(info.st_mode)
                                    or stat.S_ISLNK(info.st_mode) or entry.is_dir(follow_symlinks=False)
                                    or entry.is_symlink()):
                                raise ValueError('Store alias directory changed or is unavailable: ' + str(path))
                except OSError as unavailable:
                    raise ValueError('Cannot inspect store alias ownership: ' + str(path)) from unavailable
        yield None
        return
    try:
        before = os.fstat(descriptor)
        if expected is not None and entry_identity(before) != expected:
            raise ValueError('Previously discovered directory changed: ' + str(path))
        unchanged(descriptor, before, path)
        yield descriptor
        unchanged(descriptor, before, path)
    finally:
        os.close(descriptor)


def alias_targets(roots: list[Path]):
    """Find reachable alias targets without reading document/control contents."""
    def identity(path):
        try:
            return entry_identity(path.lstat())
        except FileNotFoundError:
            return None
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise  # Only resolve_alias can prove that this is a stable cycle.
            raise ValueError('Cannot inspect store alias ownership: ' + str(path) + ': ' + str(error)) from error

    pending = [(path, None) for path in roots]
    bindings = {}
    visited = {}
    while pending:
        path, expected = pending.pop()
        if expected is None:
            try:
                expected = identity(path)
            except OSError as error:
                if error.errno == errno.ELOOP and resolve_alias(path) is None:
                    continue  # An inaccessible descendant of a verified stable cycle.
                raise
        bindings[path] = expected
        def check_entry():
            if identity(path) != expected:
                raise ValueError('Previously discovered alias entry changed: ' + str(path))
        check_entry()
        actual = resolve_alias(path)
        check_entry()
        if actual is None:
            continue
        if actual != path:
            yield actual
        current = identity(actual)
        if actual in visited:
            if visited[actual] != current:
                raise ValueError('Previously inspected alias target changed: ' + str(actual))
            continue
        visited[actual] = current
        directory_identity = expected if expected is not None and stat.S_ISDIR(expected[2]) else (
            current if current is not None and stat.S_ISDIR(current[2]) else None)
        with alias_directory(actual, expected=directory_identity) as descriptor:
            if descriptor is None:
                continue
            try:
                with os.scandir(descriptor) as entries:
                    for entry in entries:
                        info = entry.stat(follow_symlinks=False)
                        directory, link = stat.S_ISDIR(info.st_mode), stat.S_ISLNK(info.st_mode)
                        if directory != entry.is_dir(follow_symlinks=False) or link != entry.is_symlink():
                            raise ValueError('Store alias entry changed during inspection: ' + str(actual / entry.name))
                        if directory or link:
                            # scandir(fd) returns entry names, not absolute paths.
                            pending.append((actual / entry.name, entry_identity(info)))
            except OSError as error:
                raise ValueError('Cannot enumerate store aliases: ' + str(actual)) from error
        check_entry()
    for observed in (bindings, visited):
        for path, expected in observed.items():
            if identity(path) != expected:
                raise ValueError('Alias target changed during traversal: ' + str(path))


def check_authority_aliases(authority: Path, resolved: Path) -> None:
    roots = [authority / name for name in (*KNOWLEDGE, 'specs', 'templates/overrides')]
    for actual in alias_targets(roots):
        if not target_inside(actual, authority) and target_inside(resolved, actual):
            raise ValueError('Local workspace cannot target authority data through an alias')


def feature_path(context: dict, value: str, *, observe=False) -> Path:
    path = Path(feature_location(context, value))
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError, ValueError):
        if observe:
            return path
        raise
    if not observe and target_inside(resolved, PLUGIN):
        raise ValueError('Feature cannot target the plugin')
    if context['mode'] == 'local':
        authority = context['AUTHORITY_DIR']
        if authority is None and not target_inside(resolved, Path(context['SDLC_DIR']).resolve()):
            raise ValueError('Authority is unavailable; external feature targets cannot be verified')
        if authority is not None and target_inside(resolved, Path(authority)):
            raise ValueError('Local workspace cannot write or select authority data')
        if authority is not None:
            check_authority_aliases(Path(authority), resolved)
    return path if observe else resolved


def document_path(context: dict, path: Path, *, allowed_control: Path | None = None) -> Path:
    """Check a business document's actual target, including other stores' controls."""
    actual = path.resolve()
    if feature_path(context, str(actual)) != actual:
        raise ValueError('Document target is a logical registry address: ' + str(path))
    roots = [context['SDLC_DIR'], *context.get('STORE_DIRS', []), *context.get('sources', [])]
    if context.get('STORE_REGISTRY'):
        roots.append(str(Path(context['STORE_REGISTRY']).parent))
    if context.get('AUTHORITY_DIR'):
        roots.append(context['AUTHORITY_DIR'])
    controls = ['feature.json', 'init-options.json', 'store.json', '.init-pending.json',
                'README.md', '.gitignore', 'memory/.constitution-template.json']
    for value in set(roots):
        root = resolve_alias(Path(value))
        if root is None:
            continue
        if same_target(root, Path(context['SDLC_DIR'])):
            root = Path(context['SDLC_DIR'])
        for name in [*controls, 'workspaces', 'transactions', '.write-lock']:
            control = resolve_alias(root / name)
            if control is None:
                continue
            subtree = name in ('workspaces', 'transactions', '.write-lock')
            if same_target(actual, control) or (subtree and target_inside(actual, control)):
                # An explicit write may address its own control file directly,
                # but another control alias must not share that actual target.
                address = root / name
                own_control = (root == Path(context['SDLC_DIR']) and actual == allowed_control and
                               (address == allowed_control or
                                (subtree and control == address and target_inside(allowed_control, control))))
                if not own_control:
                    raise ValueError('Document targets a reserved store path: ' + str(path))
            if subtree:
                for linked in alias_targets([root / name]):
                    if target_inside(actual, linked):
                        raise ValueError('Document targets a reserved store path: ' + str(path))
    return actual


def _native_lease_module():
    try:
        import fcntl
    except ImportError as error:
        raise ValueError('Native inherited file leases are required for store writes') from error
    return fcntl


def _open_lock_lease(lock: Path, *, create=False) -> int:
    path = lock / 'lease'
    safe(path)
    flags = os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        # Shell redirections may replace stdin/stdout/stderr; keep the lease separate.
        if descriptor < 3:
            native = _native_lease_module()
            replacement = native.fcntl(descriptor, native.F_DUPFD, 3)
            os.close(descriptor)
            descriptor = replacement
        os.set_inheritable(descriptor, False)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _check_lock_lease(lock: Path, descriptor: int) -> None:
    safe(lock / 'lease')
    current, opened = (lock / 'lease').stat(), os.fstat(descriptor)
    if not stat.S_ISREG(opened.st_mode) or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
        raise ValueError('Store writer lease binding changed')


def _acquire_lock_lease(descriptor: int) -> None:
    native = _native_lease_module()
    try:
        native.flock(descriptor, native.LOCK_EX | native.LOCK_NB)
    except BlockingIOError as error:
        raise ValueError('Store has an active writer lease; lock retained') from error


@contextmanager
def _exclusive_lock_lease(lock: Path):
    descriptor = _open_lock_lease(lock)
    try:
        _check_lock_lease(lock, descriptor)
        _acquire_lock_lease(descriptor)
        yield descriptor
    finally:
        os.close(descriptor)


def inherited_lock(state: Path) -> tuple[str, int]:
    lock = state / '.write-lock'
    token = os.environ.get('SDLC_STORE_LOCK_TOKEN')
    try:
        descriptor = int(os.environ['SDLC_STORE_LOCK_FD'])
    except (KeyError, ValueError) as error:
        raise ValueError('Missing or invalid store writer lease') from error
    safe(lock / 'owner')
    if not token or (lock / 'owner').read_text() != token:
        raise ValueError('Missing or invalid store write token')
    _check_lock_lease(lock, descriptor)
    _acquire_lock_lease(descriptor)
    return token, descriptor


def _clear_lock(lock: Path, descriptor: int, identity: tuple, owner: bytes, pid: bytes) -> None:
    current = lock.stat()
    _check_lock_lease(lock, descriptor)
    for name in ('owner', 'pid'):
        safe(lock / name)
    if ((current.st_dev, current.st_ino) != identity or (lock / 'owner').read_bytes() != owner
            or (lock / 'pid').read_bytes() != pid):
        raise ValueError('Lock ownership changed')
    for name in ('pid', 'owner', 'lease'):
        (lock / name).unlink()
    lock.rmdir()


@contextmanager
def write_lock(state: Path):
    safe(state)
    lock = state / '.write-lock'
    safe(lock)
    if os.environ.get('SDLC_STORE_LOCK_TOKEN'):
        yield inherited_lock(state)
        return
    _native_lease_module()
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Store has an active write lock; inspect the interrupted operation before recovery') from None
    info = lock.stat()
    identity = info.st_dev, info.st_ino
    token, pid = uuid.uuid4().hex, str(os.getpid()).encode()
    descriptor, issued = None, False
    try:
        descriptor = _open_lock_lease(lock, create=True)
        _acquire_lock_lease(descriptor)
        (lock / 'owner').write_text(token)
        (lock / 'pid').write_bytes(pid)
        issued = True
        yield token, descriptor
    finally:
        if descriptor is not None:
            # Do not LOCK_UN: Bash and its descendants share this open-file lease.
            os.close(descriptor)
        if issued:
            with _exclusive_lock_lease(lock) as cleanup:
                _clear_lock(lock, cleanup, identity, token.encode(), pid)
        else:
            # No writer received the lease. Only discard this newly created lock.
            current = lock.stat()
            if (current.st_dev, current.st_ino) == identity:
                for name in ('owner', 'pid', 'lease'):
                    safe(lock / name)
                    (lock / name).unlink(missing_ok=True)
                lock.rmdir()


def release_stale_lock(state: Path) -> dict:
    lock = state / '.write-lock'
    safe(lock)
    if not lock.exists():
        return {'status': 'not_locked'}
    if not lock.is_dir() or {p.name for p in lock.iterdir()} != {'owner', 'pid', 'lease'}:
        raise ValueError('Incomplete lock ownership; inspect manually without changing project data')
    safe(lock / 'pid')
    safe(lock / 'owner')
    pid_bytes, owner = (lock / 'pid').read_bytes(), (lock / 'owner').read_bytes()
    pid = int(pid_bytes)
    if pid <= 0:
        raise ValueError('Invalid lock owner')
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        info = lock.stat()
        with _exclusive_lock_lease(lock) as descriptor:
            _clear_lock(lock, descriptor, (info.st_dev, info.st_ino), owner, pid_bytes)
        return {'status': 'stale_lock_released'}
    raise ValueError('Lock owner is still running; recovery refused')


def register(context: dict, authority: Path | None, sources: list[Path], dry_run=False) -> dict:
    if not context['can_collect']:
        raise ValueError('Only main may register authority or additional sources')
    path = Path(context['STORE_REGISTRY'])
    def proposal(current):
        if (not current['can_collect'] or current['PROJECT_ROOT'] != context['PROJECT_ROOT']
                or current['STORE_REGISTRY'] != str(path)):
            raise ValueError('Registration workspace binding changed')
        old = read_object(path) if path.exists() else {}
        target = authority.expanduser().absolute() if authority else Path(current['AUTHORITY_DIR'])
        safe(target)
        if target.exists() and not target.is_dir():
            raise ValueError('Authority must be a directory: ' + str(target))
        if not target.parent.is_dir():
            raise ValueError('Authority parent directory must exist')
        target = target.resolve()
        if target == Path(target.anchor) or target_inside(Path(current['PROJECT_ROOT']), target) or target_inside(PLUGIN, target):
            raise ValueError('Authority must be a separate data directory')
        if target != Path(current['AUTHORITY_DIR']):
            previous = Path(current['AUTHORITY_DIR'])
            if old or (previous.is_dir() and any(p.name != '.write-lock' for p in previous.iterdir())):
                raise ValueError('Existing authority cannot be redirected; explicit migration is required')
        for source in sources:
            safe(source)
            if not source.is_dir():
                raise ValueError('Registered source must exist')
        return old, {'schema': 1, 'authority': str(target),
                     'sources': sorted(set(old.get('sources', []) + [str(p.resolve()) for p in sources]))}
    # Reject invalid input without creating a state directory, including previews.
    _, data = proposal(context)
    if dry_run:
        return data
    path.parent.mkdir(exist_ok=True)
    with write_lock(path.parent):
        current = resolve(Path(context['PROJECT_ROOT']), missing=True)
        old, data = proposal(current)
        if data != old:
            atomic(path, json_bytes(data))
    return data


def atomic(path: Path, data: bytes) -> None:
    import tempfile
    safe(path)
    fd, name = tempfile.mkstemp(prefix='.store-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('resolve', 'discover', 'register', 'feature', 'run', 'check-lock', 'recover-lock'))
    parser.add_argument('--project', type=Path)
    parser.add_argument('--field')
    parser.add_argument('--authority', type=Path)
    parser.add_argument('--source', action='append', type=Path, default=[])
    parser.add_argument('--value')
    parser.add_argument('--persist', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--script')
    raw = sys.argv[1:]
    split = raw.index('--') if '--' in raw else len(raw)
    args = parser.parse_args(raw[:split])
    args.arguments = raw[split + 1:]
    try:
        context = resolve(args.project, missing=args.action in ('discover', 'register'))
        if args.action == 'register':
            result = register(context, args.authority, args.source, args.dry_run)
        elif args.action == 'feature':
            value = args.value
            validate_state(context, selection=value is None, knowledge_aliases=True)
            if value is None:
                path = Path(context['FEATURE_JSON'])
                value = read_object(path).get('feature_directory') if path.exists() else None
            if value:
                feature_path(context, value)
                prefix = project_spelling(context) + '/'
                stored = value[len(prefix):] if value.startswith(prefix) else value
            result = {'FEATURE_DIR': feature_location(context, value) if value else None,
                      'FEATURE_VALUE': stored if value else None}
            if args.persist:
                if not value:
                    raise ValueError('A feature value is required')
                path = Path(context['FEATURE_JSON'])
                data = {'feature_directory': stored}
                def unchanged():
                    validate_selection_path(Path(context['SDLC_DIR']), path)
                    safe(path)
                    if not path.exists():
                        return False
                    try:
                        previous = parse_object(path.read_text(encoding='utf-8'))
                    except ValueError:
                        # An explicit selection replaces unreadable selection content,
                        # just as the upstream persistence helper does.
                        return False
                    return previous.get('feature_directory') == stored
                if not unchanged():
                    with write_lock(Path(context['SDLC_DIR'])):
                        validate_selection_path(Path(context['SDLC_DIR']), path)
                        if not unchanged():
                            document_path(context, path, allowed_control=path)
                            path.parent.mkdir(parents=True, exist_ok=True)
                            if not unchanged():
                                document_path(context, path, allowed_control=path)
                                atomic(path, (json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
        elif args.action == 'recover-lock':
            result = release_stale_lock(Path(context['SDLC_DIR']))
        elif args.action == 'check-lock':
            inherited_lock(Path(context['SDLC_DIR']))
            return 0
        elif args.action == 'run':
            if args.script not in ('create-new-feature.sh', 'setup-plan.sh', 'setup-tasks.sh'):
                raise ValueError('Only packaged data-writing helpers may run under the store lock')
            validate_state(context, selection=False, knowledge_aliases=True)
            with write_lock(Path(context['SDLC_DIR'])) as (token, descriptor):
                arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
                return subprocess.run(['bash', str(PLUGIN / 'scripts/bash' / args.script), *arguments],
                    env=dict(os.environ, SDLC_INIT_DIR=project_spelling(context), SDLC_STORE_LOCK_TOKEN=token,
                             SDLC_STORE_LOCK_FD=str(descriptor)), pass_fds=(descriptor,)).returncode
        else:
            if args.action == 'resolve':
                validate_state(context, selection=False, knowledge_aliases=True)
            result = context
        print(result[args.field] if args.field else json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
