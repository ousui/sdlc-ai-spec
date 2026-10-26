"""Transient source-role metadata failures never become missing knowledge or no-op copies."""
from __future__ import annotations

from contextlib import contextmanager
import errno
import importlib.util
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage

spec = importlib.util.spec_from_file_location('sdlc_source_roles_initializer', storage.SCRIPTS / 'init_project.py')
initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)

CONSTITUTION = 'memory/constitution.md'
HISTORY = 'memory/.constitution-template.json'
KNOWLEDGE = (CONSTITUTION, 'memory/long-term.md', HISTORY)
ROLE_ERRORS = ((errno.EACCES, 'actual'), (errno.EIO, 'actual'),
               (errno.ENOENT, 'actual'), (errno.ENOENT, 'canonical'))


class SourceRoleTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        fixture = storage.StorageTests('runTest')
        fixture.setUp()
        try:
            with mock.patch.dict(os.environ, fixture.env, clear=True):
                yield fixture
        finally:
            fixture.doCleanups()
            self.assertFalse(fixture.base.exists())

    def identity(self, path):
        info = path.stat()
        return path.read_bytes(), info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_mtime_ns

    def identities(self, root):
        return {name: self.identity(root / name) for name in storage.files(root)}

    def aliases(self, source):
        probe = source / 'memory/constitution.md'
        if not (source / 'MEMORY/CONSTITUTION.MD').exists():
            self.skipTest('Requires case-insensitive source lookup')
        self.assertTrue(os.path.samefile(probe, source / 'MEMORY/CONSTITUTION.MD'))
        memory = source / 'MEMORY'
        probe.parent.rename(memory)
        for name in KNOWLEDGE:
            path = memory / Path(name).name
            path.rename(path.with_name(path.name.upper()))
            self.assertTrue(os.path.samefile(source / name, memory / path.name.upper()))
        return memory

    def init(self, fixture, **overrides):
        args = dict(project=fixture.a, discover=False, mode='local', seed='knowledge',
                    feature=[], feature_numbering=None, dry_run=False)
        return initializer.initialize_selected(SimpleNamespace(**(args | overrides)))

    def copy_case(self, fixture, kind):
        fixture.init(fixture.a, '--mode', 'local')
        project, source = ((fixture.a, fixture.main / '.sdlc') if kind == 'import'
                           else (fixture.main, fixture.a / '.sdlc'))
        self.aliases(source)
        return project, source, [source] if kind == 'collect' else []

    @contextmanager
    def role_fault(self, source, error, *, name=CONSTITUTION, call=1, target=None,
                   side='actual', lookup=1, repeat=False):
        """Read a genuine snapshot, then deny metadata only during role recognition."""
        expected = storage.changes.source_snapshot(source)
        self.assertTrue(all('MEMORY/' + Path(n).name.upper() in expected for n in KNOWLEDGE))
        original_roles = storage.changes.source_files
        original_snapshot = storage.changes.source_snapshot
        original_stat = Path.stat
        observed = {'calls': 0, 'faults': 0, 'snapshots': 0, 'lookups': 0}
        memory = source / 'MEMORY'

        def snapshot(root):
            result = original_snapshot(root)
            if root == source:
                self.assertEqual(result, expected)
                observed['snapshots'] += 1
            return result

        def source_files(root, files, features):
            if root != source:
                return original_roles(root, files, features)
            observed['calls'] += 1
            if observed['calls'] != call:
                return original_roles(root, files, features)
            self.assertEqual(files, expected)
            if target is not None:
                self.assertEqual((target / '.write-lock').is_dir(), call == 2)
            if error == errno.EACCES:
                mode = stat.S_IMODE(memory.stat().st_mode)
                memory.chmod(0)
                try:
                    try:
                        (source / name).stat()
                    except PermissionError as denied:
                        self.assertEqual(denied.errno, errno.EACCES)
                        observed['faults'] += 1
                    else:
                        self.skipTest('chmod(0) does not deny source metadata for this user')
                    return original_roles(root, files, features)
                finally:
                    memory.chmod(mode)
            actual = memory / Path(name).name.upper()
            failed_path = actual if side == 'actual' else source / name
            held = source.parent / '.held-source-role'
            self.assertFalse(held.exists())

            def transient_stat(path, *args, **kwargs):
                if path == failed_path and (repeat or not observed['faults']):
                    observed['lookups'] += 1
                    if observed['lookups'] < lookup:
                        return original_stat(path, *args, **kwargs)
                    observed['faults'] += 1
                    if error == errno.ENOENT:
                        actual.rename(held)
                        try:
                            with self.assertRaises(FileNotFoundError) as missing:
                                original_stat(path, *args, **kwargs)
                            self.assertEqual(missing.exception.errno, errno.ENOENT)
                            raise missing.exception
                        finally:
                            held.rename(actual)
                    raise OSError(error, 'transient source-role metadata failure', str(path))
                return original_stat(path, *args, **kwargs)

            with mock.patch.object(Path, 'stat', transient_stat):
                return original_roles(root, files, features)

        with mock.patch.object(storage.changes, 'source_snapshot', side_effect=snapshot), \
                mock.patch.object(storage.changes, 'source_files', side_effect=source_files):
            yield observed
        self.assertEqual(observed['calls'], call)
        if repeat:
            self.assertGreaterEqual(observed['faults'], 1)
        else:
            self.assertEqual(observed['faults'], 1)
        self.assertEqual(original_snapshot(source), expected)

    @contextmanager
    def assert_role_error(self, error, side):
        if error == errno.ENOENT and side == 'canonical':
            with self.assertRaisesRegex(ValueError, 'Source role changed during lookup'):
                yield
        else:
            with self.assertRaises(OSError) as raised:
                yield
            self.assertEqual(raised.exception.errno, error)

    def test_first_init_rejects_transient_role_errors_before_creating_local_store(self):
        for error, side in ROLE_ERRORS:
            for dry_run in (False, True):
                with self.subTest(error=error, side=side, dry_run=dry_run), self.fixture() as fixture:
                    source = fixture.main / '.sdlc'
                    self.aliases(source)
                    (fixture.a / 'existing.txt').write_text('Preserve this user file\n')
                    before_source = self.identities(source)
                    before_project = self.identities(fixture.a)
                    with self.role_fault(source, error, side=side) as observed:
                        with self.assert_role_error(error, side):
                            self.init(fixture, dry_run=dry_run)
                    self.assertEqual(observed['snapshots'], 1)
                    self.assertFalse((fixture.a / '.sdlc').exists())
                    self.assertEqual(self.identities(fixture.a), before_project)
                    self.assertEqual(self.identities(source), before_source)
                    result = self.init(fixture)
                    self.assertEqual(result['constitution_source'], 'authority-import')
                    self.assertEqual(result['constitution_provenance'], 'imported')
                    for name in KNOWLEDGE:
                        self.assertEqual((fixture.a / '.sdlc' / name).read_bytes(), (source / name).read_bytes())
                    self.assertEqual(self.identities(source), before_source)

    def test_source_roles_propagate_either_anchor_error_without_changing_default_comparison(self):
        with self.fixture() as fixture:
            source = fixture.main / '.sdlc'
            self.aliases(source)
            raw = storage.changes.source_snapshot(source)
            actual = source / 'MEMORY/CONSTITUTION.MD'
            canonical = source / CONSTITUTION
            original_stat = Path.stat
            before = self.identities(source)
            for failed_path in (actual, canonical):
                with self.subTest(anchor=failed_path.relative_to(source).as_posix()):
                    failures = 0

                    def transient_stat(path, *args, **kwargs):
                        nonlocal failures
                        if path == failed_path and not failures:
                            failures += 1
                            raise OSError(errno.EIO, 'transient role anchor failure', str(path))
                        return original_stat(path, *args, **kwargs)

                    with mock.patch.object(Path, 'stat', transient_stat):
                        self.assertFalse(storage.store.same_path(actual, canonical))
                        self.assertEqual(failures, 1)
                        failures = 0
                        with self.assertRaises(OSError) as raised:
                            storage.changes.source_files(source, raw, [])
                        self.assertEqual(raised.exception.errno, errno.EIO)
                        self.assertEqual(failures, 1)
                    self.assertEqual(self.identities(source), before)

    def test_missing_candidates_keep_default_address_and_non_equivalent_role_semantics(self):
        with self.fixture() as fixture:
            source = fixture.main / '.sdlc'
            self.aliases(source)
            actual, canonical = source / 'MEMORY/CONSTITUTION.MD', source / CONSTITUTION
            before = self.identities(source)
            raw = storage.changes.source_snapshot(source)
            original_stat = Path.stat

            def case_distinct_candidate(path, *args, **kwargs):
                # Model a case-sensitive lookup while retaining real source metadata.
                if path == canonical:
                    raise FileNotFoundError(errno.ENOENT, 'Distinct canonical candidate', str(path))
                return original_stat(path, *args, **kwargs)

            with mock.patch.object(Path, 'stat', case_distinct_candidate), \
                    mock.patch.object(storage.store, 'case_sensitive', return_value=True):
                self.assertFalse(storage.store.same_path(actual, canonical, strict=True))
                self.assertEqual(set(storage.changes.source_files(source, raw, [])), {'memory/long-term.md'})
            missing = source / 'not-created'
            self.assertFalse(storage.store.same_path(actual, missing, strict=True))
            self.assertEqual(storage.store.same_path(missing, source / 'NOT-CREATED'),
                             not storage.store.case_sensitive(source))
            with mock.patch.object(Path, 'stat', side_effect=AssertionError('Equal addresses need no lookup')):
                self.assertTrue(storage.store.same_path(missing, missing))
                self.assertTrue(storage.store.same_path(missing, missing, strict=True))
            self.assertEqual(self.identities(source), before)

    def test_repeated_candidate_absence_cannot_silently_fall_back_during_first_init(self):
        for name in KNOWLEDGE:
            for dry_run in (False, True):
                with self.subTest(name=name, dry_run=dry_run), self.fixture() as fixture:
                    source = fixture.main / '.sdlc'
                    self.aliases(source)
                    (fixture.a / 'existing.txt').write_text('Preserve user data\n')
                    before_source = self.identities(source)
                    before_project = self.identities(fixture.a)
                    with self.role_fault(source, errno.ENOENT, name=name, side='canonical', repeat=True) as observed:
                        with self.assertRaisesRegex(ValueError, 'Source role changed during lookup'):
                            self.init(fixture, dry_run=dry_run)
                    self.assertEqual(observed['snapshots'], 1)
                    self.assertFalse((fixture.a / '.sdlc').exists())
                    self.assertEqual(self.identities(fixture.a), before_project)
                    self.assertEqual(self.identities(source), before_source)
                    result = self.init(fixture)
                    self.assertEqual(result['constitution_source'], 'authority-import')
                    self.assertEqual(result['constitution_provenance'], 'imported')
                    for selected in KNOWLEDGE:
                        self.assertEqual((fixture.a / '.sdlc' / selected).read_bytes(), (source / selected).read_bytes())
                    after = self.identities(fixture.a / '.sdlc')
                    self.assertEqual(self.init(fixture)['status'], 'unchanged')
                    self.assertEqual(self.identities(fixture.a / '.sdlc'), after)
                    self.assertEqual(self.identities(source), before_source)

    def test_missing_role_requires_lookup_rule_proof_at_each_actual_parent(self):
        with self.fixture() as fixture:
            source = fixture.main / '.sdlc'
            self.aliases(source)
            actual, canonical = source / 'MEMORY/CONSTITUTION.MD', source / CONSTITUTION
            before = self.identities(source)
            original_stat = Path.stat
            for sensitive_parent in (source, source / 'MEMORY', None):
                with self.subTest(sensitive_parent=sensitive_parent):
                    lookups, parents = [], []

                    def missing(path, *args, **kwargs):
                        if path == canonical:
                            lookups.append(path)
                            raise FileNotFoundError(errno.ENOENT, 'Repeated role absence', str(path))
                        return original_stat(path, *args, **kwargs)

                    def sensitive(parent, *, strict=False):
                        parents.append(parent)
                        self.assertTrue(strict)
                        return parent == sensitive_parent

                    with mock.patch.object(Path, 'stat', missing), \
                            mock.patch.object(storage.store, 'case_sensitive', side_effect=sensitive):
                        if sensitive_parent is None:
                            with self.assertRaisesRegex(ValueError, 'Source role changed during lookup'):
                                storage.store.same_path(actual, canonical, strict=True)
                        else:
                            self.assertFalse(storage.store.same_path(actual, canonical, strict=True))
                    self.assertEqual(lookups, [canonical])
                    self.assertEqual(parents, [source] if sensitive_parent == source else [source, source / 'MEMORY'])
                    self.assertEqual(self.identities(source), before)

            for error in (ValueError('Unverifiable lookup rule'), OSError(errno.EIO, 'Lookup rule unavailable')):
                with self.subTest(error=type(error).__name__), \
                        mock.patch.object(Path, 'stat', missing), \
                        mock.patch.object(storage.store, 'case_sensitive', side_effect=error):
                    with self.assertRaises(type(error)):
                        storage.store.same_path(actual, canonical, strict=True)
            self.assertEqual(self.identities(source), before)

    def test_missing_unicode_role_uses_normalization_rule_without_case_assumptions(self):
        with self.fixture() as fixture:
            source = fixture.main / '.sdlc'
            actual, canonical = source / 'memory/caf\u00e9.md', source / 'memory/cafe\u0301.md'
            actual.write_bytes(b'Preserve Unicode knowledge\n')
            before = self.identities(source)
            original_stat = Path.stat
            for sensitive in (False, True):
                with self.subTest(sensitive=sensitive):
                    lookups = []

                    def missing(path, *args, **kwargs):
                        if path == canonical:
                            lookups.append(path)
                            raise FileNotFoundError(errno.ENOENT, 'Repeated Unicode role absence', str(path))
                        return original_stat(path, *args, **kwargs)

                    with mock.patch.object(Path, 'stat', missing), \
                            mock.patch.object(storage.store, 'case_sensitive', side_effect=AssertionError('No case assumption')), \
                            mock.patch.object(storage.store, 'normalization_sensitive', return_value=sensitive) as rule:
                        if sensitive:
                            self.assertFalse(storage.store.same_path(actual, canonical, strict=True))
                        else:
                            with self.assertRaisesRegex(ValueError, 'Source role changed during lookup'):
                                storage.store.same_path(actual, canonical, strict=True)
                        rule.assert_called_once_with(source / 'memory', strict=True)
                    self.assertEqual(lookups, [canonical])
                    self.assertEqual(self.identities(source), before)

    def test_known_source_is_rechecked_after_missing_role_lookup_rule(self):
        with self.fixture() as fixture:
            source = fixture.main / '.sdlc'
            self.aliases(source)
            actual, canonical = source / 'MEMORY/CONSTITUTION.MD', source / CONSTITUTION
            before = self.identities(source)
            original_stat = Path.stat
            held = fixture.base / 'held-original'

            def missing(path, *args, **kwargs):
                if path == canonical:
                    raise FileNotFoundError(errno.ENOENT, 'Missing role', str(path))
                return original_stat(path, *args, **kwargs)

            def replace_during_rule(parent, *, strict=False):
                self.assertTrue(strict)
                actual.rename(held)
                actual.write_bytes(b'Later edit during lookup rule\n')
                return True

            try:
                with mock.patch.object(Path, 'stat', missing), \
                        mock.patch.object(storage.store, 'case_sensitive', side_effect=replace_during_rule):
                    with self.assertRaisesRegex(ValueError, 'Source path changed during lookup'):
                        storage.store.same_path(actual, canonical, strict=True)
            finally:
                if held.exists():
                    actual.unlink()
                    held.rename(actual)
            self.assertEqual(self.identities(source), before)

    def test_role_policy_does_not_requery_a_failed_case_candidate(self):
        for independent_entry in (False, True):
            with self.subTest(independent_entry=independent_entry), self.fixture() as fixture:
                directory = fixture.base / 'case-policy'
                directory.mkdir()
                actual, canonical = directory / 'Constitution.md', directory / 'constitution.md'
                actual.write_bytes(b'Known source with a single case difference\n')
                if not canonical.exists():
                    self.skipTest('Requires case-insensitive lookup')
                self.assertTrue(os.path.samefile(actual, canonical))
                if independent_entry:
                    (directory / 'independent.txt').write_bytes(b'Independent directory entry\n')
                before = self.identities(directory)
                original_stat = Path.stat
                held = fixture.base / 'held-case-source'
                lookups = []

                def missing(path, *args, **kwargs):
                    # Every other spelling of this source fails, not just the
                    # first candidate or a fixed number of metadata calls.
                    if (path.parent == directory and path != actual and
                            storage.store.name_key(path.name) == storage.store.name_key(actual.name)):
                        lookups.append((path.name, kwargs.get('follow_symlinks', True)))
                        actual.rename(held)
                        try:
                            return original_stat(path, *args, **kwargs)
                        finally:
                            held.rename(actual)
                    return original_stat(path, *args, **kwargs)

                # Unknown native rules cannot be replaced by directory observations.
                with mock.patch.object(storage.store.sys, 'platform', 'linux'), \
                        mock.patch.object(Path, 'stat', missing):
                    with self.assertRaisesRegex(ValueError, 'Cannot verify case-distinct source paths'):
                        storage.store.same_path(actual, canonical, strict=True)
                self.assertEqual(lookups, [(canonical.name, True)])
                self.assertEqual(self.identities(directory), before)

    def test_role_policy_stops_when_unicode_rule_would_require_the_failed_candidate(self):
        with self.fixture() as fixture:
            directory = fixture.base / 'unicode-policy'
            directory.mkdir()
            actual, candidate = directory / 'caf\u00e9.md', directory / 'cafe\u0301.md'
            actual.write_bytes(b'Known Unicode source\n')
            # Use the filesystem's actual spelling as the known snapshot name.
            actual = next(directory.iterdir())
            canonical = candidate if actual.name != candidate.name else directory / 'caf\u00e9.md'
            if not canonical.exists():
                self.skipTest('Requires normalization-insensitive lookup')
            self.assertTrue(os.path.samefile(actual, canonical))
            before = self.identity(actual)
            original_stat = Path.stat
            held = fixture.base / 'held-unicode-source'
            lookups = []

            def missing(path, *args, **kwargs):
                if path == canonical:
                    lookups.append(kwargs.get('follow_symlinks', True))
                    actual.rename(held)
                    try:
                        return original_stat(path, *args, **kwargs)
                    finally:
                        held.rename(actual)
                return original_stat(path, *args, **kwargs)

            with mock.patch.object(Path, 'stat', missing):
                with self.assertRaisesRegex(ValueError, 'Cannot verify Unicode normalization'):
                    storage.store.same_path(actual, canonical, strict=True)
            self.assertEqual(lookups, [True])
            self.assertEqual(self.identity(actual), before)

    def test_repeated_candidate_absence_stops_copy_prepare_without_an_empty_plan(self):
        for kind in ('import', 'collect'):
            for name in KNOWLEDGE:
                with self.subTest(kind=kind, name=name), self.fixture() as fixture:
                    project, source, sources = self.copy_case(fixture, kind)
                    (source / 'memory/long-term.md').write_text('Selected shared knowledge\n')
                    target = project / '.sdlc'
                    before_target, before_source = self.identities(target), self.identities(source)
                    with self.role_fault(source, errno.ENOENT, name=name, side='canonical', repeat=True):
                        with self.assertRaisesRegex(ValueError, 'Source role changed during lookup'):
                            storage.changes.prepare(project, kind, sources, [], [])
                    self.assertFalse((target / 'transactions').exists())
                    self.assertEqual(self.identities(target), before_target)
                    self.assertEqual(self.identities(source), before_source)
                    plan = storage.changes.prepare(project, kind, sources, [], [])
                    self.assertEqual(plan['files'], ['memory/long-term.md'])
                    self.assertEqual(plan['changed_sources'], [str(source)])
                    self.assertEqual(plan['unresolved'], plan['files'])
                    Path(plan['proposal']).write_text(json.dumps({plan['files'][0]: {'action': 'copy', 'source': str(source)}}))
                    storage.changes.apply(project, Path(plan['transaction']))
                    after = self.identities(target)
                    noop = storage.changes.prepare(project, kind, sources, [], [])
                    self.assertEqual(noop['files'], [])
                    self.assertEqual(noop['changed_sources'], [])
                    self.assertEqual(storage.changes.apply(project, Path(noop['transaction']))['written'], [])
                    self.assertEqual(self.identities(target), after)
                    self.assertEqual(self.identities(source), before_source)

    def test_repeated_candidate_absence_preserves_apply_and_saved_offline_recovery(self):
        for kind in ('import', 'collect'):
            for call in (1, 2):
                with self.subTest(kind=kind, call=call), self.fixture() as fixture:
                    project, source, sources = self.copy_case(fixture, kind)
                    target = project / '.sdlc'
                    for name in (CONSTITUTION, HISTORY):
                        (target / name).unlink()
                    before_target, before_source = self.identities(target), self.identities(source)
                    plan = storage.changes.prepare(project, kind, sources, [], [])
                    self.assertEqual(plan['files'], [CONSTITUTION])
                    folder = Path(plan['transaction'])
                    before_record = {name: self.identity(folder / name) for name in ('manifest.json', 'proposal.json')}
                    with self.role_fault(source, errno.ENOENT, name=HISTORY, side='canonical',
                                         call=call, target=target, repeat=True):
                        with self.assertRaisesRegex(ValueError, 'Source role changed during lookup'):
                            storage.changes.apply(project, folder)
                    self.assertEqual({name: self.identity(folder / name) for name in before_record}, before_record)
                    self.assertEqual(self.identities(target), before_target)
                    self.assertEqual(self.identities(source), before_source)
                    self.assertFalse((target / '.write-lock').exists())
                    self.assertEqual(set(storage.changes.apply(project, folder)['written']), {CONSTITUTION, HISTORY})
                    for name in (CONSTITUTION, HISTORY):
                        self.assertEqual((target / name).read_bytes(), (source / name).read_bytes())
                    manifest = folder / 'manifest.json'
                    record = json.loads(manifest.read_text())
                    record['status'] = 'applying'
                    manifest.write_text(json.dumps(record))
                    offline = source.with_name('offline-source')
                    source.rename(offline)
                    try:
                        with mock.patch.object(storage.changes, 'source_files', side_effect=AssertionError('No roles during recovery')), \
                                mock.patch.object(storage.changes, 'source_snapshot', side_effect=AssertionError('No source snapshot during recovery')), \
                                mock.patch.object(storage.changes, 'allowed_sources', side_effect=AssertionError('No source discovery during recovery')), \
                                mock.patch.object(storage.changes, 'planned_bytes', side_effect=AssertionError('No source replanning during recovery')):
                            self.assertEqual(storage.changes.recover(project, folder)['status'], 'recovered')
                        self.assertEqual(self.identities(target), before_target)
                    finally:
                        offline.rename(source)
                    self.assertEqual(self.identities(source), before_source)

    def test_known_source_disappearance_during_recheck_stops_prepare(self):
        for kind in ('import', 'collect'):
            with self.subTest(kind=kind), self.fixture() as fixture:
                project, source, sources = self.copy_case(fixture, kind)
                (source / 'memory/long-term.md').write_text('Selected knowledge')
                target = project / '.sdlc'
                before_target, before_source = self.identities(target), self.identities(source)
                with self.role_fault(source, errno.ENOENT, name='memory/long-term.md', lookup=2):
                    with self.assertRaises(FileNotFoundError):
                        storage.changes.prepare(project, kind, sources, [], [])
                self.assertFalse((target / 'transactions').exists())
                self.assertEqual(self.identities(target), before_target)
                self.assertEqual(self.identities(source), before_source)

    def test_replaced_known_source_is_rejected_during_role_lookup(self):
        with self.fixture() as fixture:
            source = fixture.main / '.sdlc'
            self.aliases(source)
            before = self.identities(source)
            raw = storage.changes.source_snapshot(source)
            actual, canonical = source / 'MEMORY/CONSTITUTION.MD', source / CONSTITUTION
            held = fixture.base / 'held-constitution'
            original_stat = Path.stat
            replaced = False

            def replace_during_lookup(path, *args, **kwargs):
                nonlocal replaced
                if path == canonical and not replaced:
                    replaced = True
                    actual.rename(held)
                    actual.write_bytes(b'Later source edit')
                return original_stat(path, *args, **kwargs)

            try:
                with mock.patch.object(Path, 'stat', replace_during_lookup):
                    with self.assertRaisesRegex(ValueError, 'Source path changed during lookup'):
                        storage.changes.source_files(source, raw, [])
                self.assertTrue(replaced)
            finally:
                if replaced:
                    actual.unlink()
                    held.rename(actual)
            self.assertEqual(self.identities(source), before)

    def test_copy_prepare_rejects_transient_role_errors_instead_of_empty_candidates(self):
        for kind in ('import', 'collect'):
            for error, side in ROLE_ERRORS:
                with self.subTest(kind=kind, error=error, side=side), self.fixture() as fixture:
                    project, source, sources = self.copy_case(fixture, kind)
                    (source / 'memory/long-term.md').write_text('New knowledge from ' + kind)
                    target = project / '.sdlc'
                    before_target, before_source = self.identities(target), self.identities(source)
                    with self.role_fault(source, error, name='memory/long-term.md', side=side) as observed:
                        with self.assert_role_error(error, side):
                            storage.changes.prepare(project, kind, sources, [], [])
                    self.assertEqual(observed['snapshots'], 1)
                    self.assertFalse((target / 'transactions').exists())
                    self.assertEqual(self.identities(target), before_target)
                    self.assertEqual(self.identities(source), before_source)
                    plan = storage.changes.prepare(project, kind, sources, [], [])
                    self.assertEqual(plan['files'], ['memory/long-term.md'])
                    self.assertEqual(plan['changed_sources'], [str(source)])
                    self.assertEqual(plan['unresolved'], plan['files'])
                    Path(plan['proposal']).write_text(json.dumps({plan['files'][0]: {'action': 'copy', 'source': str(source)}}))
                    storage.changes.apply(project, Path(plan['transaction']))
                    self.assertEqual((target / 'memory/long-term.md').read_bytes(), (source / 'memory/long-term.md').read_bytes())
                    self.assertEqual(self.identities(source), before_source)
                    after = self.identities(target)
                    noop = storage.changes.prepare(project, kind, sources, [], [])
                    self.assertEqual(noop['files'], [])
                    self.assertEqual(noop['changed_sources'], [])
                    self.assertEqual(storage.changes.apply(project, Path(noop['transaction']))['written'], [])
                    self.assertEqual(self.identities(target), after)

    def test_copy_apply_role_errors_preserve_prepared_transaction_before_and_inside_lock(self):
        for kind in ('import', 'collect'):
            for call in (1, 2):
                for error, side in ROLE_ERRORS:
                    with self.subTest(kind=kind, call=call, error=error, side=side), self.fixture() as fixture:
                        project, source, sources = self.copy_case(fixture, kind)
                        target = project / '.sdlc'
                        for name in (CONSTITUTION, HISTORY):
                            (target / name).unlink()
                        plan = storage.changes.prepare(project, kind, sources, [], [])
                        self.assertEqual(plan['files'], [CONSTITUTION])
                        self.assertEqual(plan['unresolved'], [])
                        folder = Path(plan['transaction'])
                        before_record = {name: self.identity(folder / name) for name in ('manifest.json', 'proposal.json')}
                        before_target, before_source = self.identities(target), self.identities(source)
                        with self.role_fault(source, error, name=HISTORY, call=call, target=target, side=side) as observed:
                            with self.assert_role_error(error, side):
                                storage.changes.apply(project, folder)
                        self.assertEqual(observed['snapshots'], call - 1)
                        self.assertEqual({name: self.identity(folder / name) for name in before_record}, before_record)
                        self.assertEqual(self.identities(target), before_target)
                        self.assertEqual(self.identities(source), before_source)
                        self.assertFalse((target / '.write-lock').exists())
                        result = storage.changes.apply(project, folder)
                        self.assertEqual(set(result['written']), {CONSTITUTION, HISTORY})
                        for name in (CONSTITUTION, HISTORY):
                            self.assertEqual((target / name).read_bytes(), (source / name).read_bytes())
                        self.assertEqual(self.identities(source), before_source)

    def test_pending_init_resumes_saved_role_bytes_without_live_source_queries(self):
        for phase in ('before-constitution', 'after-constitution'):
            with self.subTest(phase=phase), self.fixture() as fixture:
                source = fixture.main / '.sdlc'
                self.aliases(source)
                expected = {name: (source / name).read_bytes() for name in KNOWLEDGE}
                target = fixture.a / '.sdlc'
                original_publish = initializer.publish

                def interrupt(path, data, previous):
                    stop = CONSTITUTION if phase == 'before-constitution' else 'README.md'
                    if path == target / stop:
                        raise OSError('interrupt after saved initialization intent')
                    return original_publish(path, data, previous)

                with mock.patch.object(initializer, 'publish', side_effect=interrupt):
                    with self.assertRaisesRegex(OSError, 'saved initialization intent'):
                        self.init(fixture)
                self.assertEqual(set(json.loads((target / '.init-pending.json').read_text())['seeds']), set(KNOWLEDGE))
                if phase == 'after-constitution':
                    existing = self.identity(target / CONSTITUTION)
                    self.assertEqual(existing[0], expected[CONSTITUTION])
                else:
                    self.assertFalse((target / CONSTITUTION).exists())
                self.assertFalse((target / HISTORY).exists())
                saved = source.with_name('offline-authority')
                source.rename(saved)
                try:
                    with mock.patch.object(storage.changes, 'source_files', side_effect=AssertionError('No live role query during resume')), \
                            mock.patch.object(storage.changes, 'source_snapshot', side_effect=AssertionError('No live snapshot during resume')):
                        result = self.init(fixture)
                    self.assertFalse((target / '.init-pending.json').exists())
                    for name in storage.store.KNOWLEDGE:
                        self.assertEqual((target / name).read_bytes(), expected[name])
                        self.assertIn(name, result['imported'] + result['preserved_imports'])
                    if phase == 'before-constitution':
                        self.assertEqual((target / HISTORY).read_bytes(), expected[HISTORY])
                        self.assertIn(HISTORY, result['imported'])
                    else:
                        # Saved intent does not prove who published an existing constitution.
                        self.assertEqual(self.identity(target / CONSTITUTION), existing)
                        self.assertFalse((target / HISTORY).exists())
                        self.assertNotIn(HISTORY, result['imported'] + result['preserved_imports'])
                        self.assertTrue(any('origin cannot be asserted' in warning for warning in result['warnings']))
                finally:
                    saved.rename(source)

    def test_copy_recovery_uses_saved_publication_without_source_role_queries(self):
        for kind in ('import', 'collect'):
            with self.subTest(kind=kind), self.fixture() as fixture:
                project, source, sources = self.copy_case(fixture, kind)
                target = project / '.sdlc'
                for name in (CONSTITUTION, HISTORY):
                    (target / name).unlink()
                before = self.identities(target)
                plan = storage.changes.prepare(project, kind, sources, [], [])
                folder = Path(plan['transaction'])
                storage.changes.apply(project, folder)
                manifest = folder / 'manifest.json'
                record = json.loads(manifest.read_text())
                self.assertEqual(set(record['after']), {CONSTITUTION, HISTORY})
                record['status'] = 'applying'
                manifest.write_text(json.dumps(record))
                saved = source.with_name('offline-source')
                source.rename(saved)
                try:
                    with mock.patch.object(storage.changes, 'source_files', side_effect=AssertionError('No source roles during recovery')), \
                            mock.patch.object(storage.changes, 'source_snapshot', side_effect=AssertionError('No source snapshot during recovery')), \
                            mock.patch.object(storage.changes, 'allowed_sources', side_effect=AssertionError('No source revalidation during recovery')), \
                            mock.patch.object(storage.changes, 'planned_bytes', side_effect=AssertionError('No source replanning during recovery')):
                        self.assertEqual(storage.changes.recover(project, folder)['status'], 'recovered')
                    self.assertEqual(self.identities(target), before)
                    self.assertFalse((target / CONSTITUTION).exists())
                    self.assertFalse((target / HISTORY).exists())
                finally:
                    saved.rename(source)

    def test_real_non_equivalent_name_remains_out_of_scope_and_copy_is_noop(self):
        for kind in ('import', 'collect'):
            with self.subTest(kind=kind), self.fixture() as fixture:
                fixture.init(fixture.a, '--mode', 'local')
                project, source = ((fixture.a, fixture.main / '.sdlc') if kind == 'import'
                                   else (fixture.main, fixture.a / '.sdlc'))
                distinct = source / 'memory/constitution-notes.md'
                (source / CONSTITUTION).rename(distinct)
                self.assertFalse((source / CONSTITUTION).exists())
                self.assertFalse(storage.store.same_path(distinct, source / CONSTITUTION))
                raw = storage.changes.source_snapshot(source)
                self.assertEqual(set(storage.changes.source_files(source, raw, [])), {'memory/long-term.md'})
                target = project / '.sdlc'
                before_target, before_source = self.identities(target), self.identities(source)
                plan = storage.changes.prepare(project, kind, [source] if kind == 'collect' else [], [], [])
                self.assertEqual(plan['files'], [])
                self.assertEqual(plan['changed_sources'], [])
                self.assertEqual(storage.changes.apply(project, Path(plan['transaction']))['written'], [])
                self.assertEqual(self.identities(target), before_target)
                self.assertEqual(self.identities(source), before_source)


if __name__ == '__main__':
    unittest.main()
