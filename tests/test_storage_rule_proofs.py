"""Transient observations cannot prove source filesystem lookup sensitivity."""
from __future__ import annotations

from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import stat
import unittest
from unittest import mock

try:
    from tests import test_storage_source_roles as roles
except ImportError:
    import test_storage_source_roles as roles

storage = roles.storage
CONSTITUTION, HISTORY, KNOWLEDGE = roles.CONSTITUTION, roles.HISTORY, roles.KNOWLEDGE


class RuleProofTests(unittest.TestCase):
    def setUp(self):
        self.helper = roles.SourceRoleTests('runTest')

    @contextmanager
    def rule_fault(self, source, name, fault, native, *, call=1, target=None):
        """Arm a transient candidate lookup and an independent unstable probe.

        Old code consumes the independent ENOENT/replacement as a sensitive rule.
        Source recognition must stop before consulting this observation at all.
        """
        expected = storage.changes.source_snapshot(source)
        original_roles = storage.changes.source_files
        original_probe, original_stat = storage.store.lookup_sensitive, Path.stat
        actual = source / 'MEMORY' / Path(name).name.upper()
        candidate = source / name
        self.assertTrue(os.path.samefile(actual, candidate))
        held_role, held_probe = source.parent / 'held-role', source.parent / 'held-independent'
        observed = {'roles': 0, 'candidate': 0, 'native': 0, 'probes': 0, 'faults': 0}

        def native_rule(*args, **kwargs):
            observed['native'] += 1
            if native == 'io-error':
                raise OSError(errno.EIO, 'Native directory lookup rule unavailable')
            return -1

        def missing_candidate(path, *args, **kwargs):
            if path == candidate:
                observed['candidate'] += 1
                actual.rename(held_role)
                try:
                    if fault == 'candidate-replacement':
                        actual.write_bytes(b'Temporary canonical candidate replacement')
                    info = original_stat(path, *args, **kwargs)
                    old = original_stat(held_role)
                    self.assertNotEqual((info.st_dev, info.st_ino), (old.st_dev, old.st_ino))
                    return info
                finally:
                    if fault == 'candidate-replacement':
                        actual.unlink()
                    held_role.rename(actual)
            return original_stat(path, *args, **kwargs)

        def independent_rule(parent, name, variant):
            observed['probes'] += 1
            original, alternate = parent / name, parent / variant
            self.assertNotEqual(storage.store.name_key(name), storage.store.name_key('memory'))
            self.assertTrue(os.path.samefile(original, alternate))
            before = original.lstat()

            def unstable(path, *args, **kwargs):
                if path == alternate:
                    observed['faults'] += 1
                    original.rename(held_probe)
                    try:
                        if fault == 'replacement':
                            if stat.S_ISDIR(before.st_mode):
                                original.mkdir()
                            else:
                                original.write_bytes(b'Temporary independent replacement')
                            info = original_stat(path, *args, **kwargs)
                            self.assertNotEqual((info.st_dev, info.st_ino), (before.st_dev, before.st_ino))
                            return info
                        with self.assertRaises(FileNotFoundError) as missing:
                            original_stat(path, *args, **kwargs)
                        raise missing.exception
                    finally:
                        if fault == 'replacement':
                            if stat.S_ISDIR(before.st_mode):
                                original.rmdir()
                            else:
                                original.unlink()
                        held_probe.rename(original)
                return missing_candidate(path, *args, **kwargs)

            with mock.patch.object(Path, 'stat', unstable):
                result = original_probe(parent, name, variant)
            after = original.lstat()
            self.assertEqual((before.st_dev, before.st_ino), (after.st_dev, after.st_ino))
            return result

        def source_files(root, files, features):
            if root != source:
                return original_roles(root, files, features)
            observed['roles'] += 1
            if observed['roles'] != call:
                return original_roles(root, files, features)
            self.assertEqual(files, expected)
            if target is not None:
                self.assertEqual((target / '.write-lock').is_dir(), call == 2)
            with mock.patch.object(storage.store.sys, 'platform', 'darwin'), \
                    mock.patch.object(Path, 'stat', missing_candidate), \
                    mock.patch.object(storage.store.os, 'pathconf', side_effect=native_rule), \
                    mock.patch.object(storage.store, 'lookup_sensitive', side_effect=independent_rule):
                return original_roles(root, files, features)

        with mock.patch.object(storage.changes, 'source_files', side_effect=source_files):
            yield observed
        self.assertEqual(observed['roles'], call)
        self.assertEqual(observed['candidate'], 1)
        self.assertEqual(observed['native'], 1)
        self.assertEqual(observed['probes'], 0)
        self.assertEqual(observed['faults'], 0)
        self.assertEqual(storage.changes.source_snapshot(source), expected)

    @contextmanager
    def assert_rule_error(self, native):
        if native == 'io-error':
            with self.assertRaises(OSError) as raised:
                yield
            self.assertEqual(raised.exception.errno, errno.EIO)
        else:
            with self.assertRaisesRegex(ValueError, 'Cannot verify case-distinct source paths'):
                yield

    @contextmanager
    def offline_recovery(self, source):
        offline = source.with_name('offline-source')
        source.rename(offline)
        original_case = storage.store.case_sensitive
        original_normalization = storage.store.normalization_sensitive

        def forbid_strict(original):
            def rule(parent, **kwargs):
                if kwargs.get('strict'):
                    raise AssertionError('Recovery cannot require live source lookup rules')
                return original(parent, **kwargs)
            return rule

        try:
            with mock.patch.object(storage.changes, 'source_files', side_effect=AssertionError('No live source roles')), \
                    mock.patch.object(storage.changes, 'source_snapshot', side_effect=AssertionError('No live source snapshot')), \
                    mock.patch.object(storage.changes, 'allowed_sources', side_effect=AssertionError('No live source validation')), \
                    mock.patch.object(storage.changes, 'planned_bytes', side_effect=AssertionError('No replanning')), \
                    mock.patch.object(storage.store, 'case_sensitive', side_effect=forbid_strict(original_case)), \
                    mock.patch.object(storage.store, 'normalization_sensitive', side_effect=forbid_strict(original_normalization)):
                yield
        finally:
            offline.rename(source)

    def test_first_init_stops_before_creation_without_inferring_independent_rules(self):
        for fault in ('missing', 'replacement', 'candidate-replacement'):
            for native in ('io-error', 'unsupported'):
                for dry_run in (False, True):
                    with self.subTest(fault=fault, native=native, dry_run=dry_run), self.helper.fixture() as f:
                        source = f.main / '.sdlc'
                        self.helper.aliases(source)
                        (f.a / 'existing.txt').write_bytes(b'Preserve user data')
                        before_source, before_project = self.helper.identities(source), self.helper.identities(f.a)
                        with self.rule_fault(source, CONSTITUTION, fault, native):
                            with self.assert_rule_error(native):
                                self.helper.init(f, dry_run=dry_run)
                        self.assertFalse((f.a / '.sdlc').exists())
                        self.assertEqual(self.helper.identities(f.a), before_project)
                        self.assertEqual(self.helper.identities(source), before_source)
                        answer = self.helper.init(f)
                        self.assertEqual(answer['constitution_source'], 'authority-import')
                        self.assertEqual(answer['constitution_provenance'], 'imported')
                        for name in KNOWLEDGE:
                            self.assertEqual((f.a / '.sdlc' / name).read_bytes(), (source / name).read_bytes())
                        after = self.helper.identities(f.a / '.sdlc')
                        self.assertEqual(self.helper.init(f)['status'], 'unchanged')
                        self.assertEqual(self.helper.identities(f.a / '.sdlc'), after)

    def test_prepare_keeps_existing_files_and_never_reports_a_false_noop(self):
        for kind in ('import', 'collect'):
            for fault in ('missing', 'replacement', 'candidate-replacement'):
                for native in ('io-error', 'unsupported'):
                    with self.subTest(kind=kind, fault=fault, native=native), self.helper.fixture() as f:
                        project, source, sources = self.helper.copy_case(f, kind)
                        (source / 'memory/long-term.md').write_bytes(b'Selected shared knowledge')
                        target = project / '.sdlc'
                        before_target, before_source = self.helper.identities(target), self.helper.identities(source)
                        with self.rule_fault(source, 'memory/long-term.md', fault, native):
                            with self.assert_rule_error(native):
                                storage.changes.prepare(project, kind, sources, [], [])
                        self.assertFalse((target / 'transactions').exists())
                        self.assertEqual(self.helper.identities(target), before_target)
                        self.assertEqual(self.helper.identities(source), before_source)
                        plan = storage.changes.prepare(project, kind, sources, [], [])
                        self.assertEqual(plan['files'], ['memory/long-term.md'])
                        self.assertEqual(plan['changed_sources'], [str(source)])
                        Path(plan['proposal']).write_text(json.dumps({plan['files'][0]: {'action': 'copy', 'source': str(source)}}))
                        storage.changes.apply(project, Path(plan['transaction']))
                        after = self.helper.identities(target)
                        noop = storage.changes.prepare(project, kind, sources, [], [])
                        self.assertEqual(noop['files'], [])
                        self.assertEqual(storage.changes.apply(project, Path(noop['transaction']))['written'], [])
                        self.assertEqual(self.helper.identities(target), after)

    def test_apply_keeps_prepared_record_then_retries_and_recovers_offline(self):
        for kind in ('import', 'collect'):
            for call in (1, 2):
                for fault in ('missing', 'replacement', 'candidate-replacement'):
                    for native in ('io-error', 'unsupported'):
                        with self.subTest(kind=kind, call=call, fault=fault, native=native), self.helper.fixture() as f:
                            project, source, sources = self.helper.copy_case(f, kind)
                            target = project / '.sdlc'
                            for name in (CONSTITUTION, HISTORY):
                                (target / name).unlink()
                            before_target, before_source = self.helper.identities(target), self.helper.identities(source)
                            plan = storage.changes.prepare(project, kind, sources, [], [])
                            folder = Path(plan['transaction'])
                            records = {name: self.helper.identity(folder / name) for name in ('manifest.json', 'proposal.json')}
                            with self.rule_fault(source, HISTORY, fault, native, call=call, target=target):
                                with self.assert_rule_error(native):
                                    storage.changes.apply(project, folder)
                            self.assertEqual({name: self.helper.identity(folder / name) for name in records}, records)
                            self.assertEqual(self.helper.identities(target), before_target)
                            self.assertEqual(self.helper.identities(source), before_source)
                            self.assertFalse((target / '.write-lock').exists())
                            self.assertEqual(set(storage.changes.apply(project, folder)['written']), {CONSTITUTION, HISTORY})
                            for name in (CONSTITUTION, HISTORY):
                                self.assertEqual((target / name).read_bytes(), (source / name).read_bytes())
                            manifest = folder / 'manifest.json'
                            saved = json.loads(manifest.read_text())
                            saved['status'] = 'applying'
                            manifest.write_text(json.dumps(saved))
                            with self.offline_recovery(source):
                                self.assertEqual(storage.changes.recover(project, folder)['status'], 'recovered')
                                self.assertEqual(self.helper.identities(target), before_target)
                            self.assertEqual(self.helper.identities(source), before_source)

    def test_native_rules_and_non_equivalent_missing_candidates_keep_their_meaning(self):
        with self.helper.fixture() as f:
            source = f.main / '.sdlc'
            self.helper.aliases(source)
            actual, candidate = source / 'MEMORY/CONSTITUTION.MD', source / CONSTITUTION
            original_stat = Path.stat

            def missing(path, *args, **kwargs):
                if path == candidate:
                    if candidate_state == 'missing':
                        raise FileNotFoundError(errno.ENOENT, 'Case-distinct candidate', str(path))
                    return original_stat(source / 'README.md', *args, **kwargs)
                return original_stat(path, *args, **kwargs)

            for candidate_state in ('missing', 'different-inode'):
                for value in (0, 1):
                    with self.subTest(candidate_state=candidate_state, native_value=value), \
                            mock.patch.object(storage.store.sys, 'platform', 'darwin'), \
                            mock.patch.object(Path, 'stat', missing), \
                            mock.patch.object(storage.store.os, 'pathconf', return_value=value), \
                            mock.patch.object(storage.store, 'lookup_sensitive', side_effect=AssertionError('Native rule needs no probe')):
                        if value:
                            self.assertFalse(storage.store.same_path(actual, candidate, strict=True))
                        else:
                            with self.assertRaisesRegex(ValueError, 'Source role changed during lookup'):
                                storage.store.same_path(actual, candidate, strict=True)
            with mock.patch.object(storage.store.os, 'pathconf', side_effect=AssertionError('Unrelated names need no rule')), \
                    mock.patch.object(storage.store, 'lookup_sensitive', side_effect=AssertionError('No unrelated probe')):
                self.assertFalse(storage.store.same_path(actual, source / 'constitution-notes.md', strict=True))
            raw = storage.changes.source_snapshot(source)
            (source / CONSTITUTION).rename(source / 'MEMORY/constitution-notes.md')
            with mock.patch.object(storage.store.os, 'pathconf', side_effect=AssertionError('No missing-role rule')):
                selected = storage.changes.source_files(source, storage.changes.source_snapshot(source), [])
            self.assertEqual(set(selected), {'memory/long-term.md'})
            self.assertIn('MEMORY/CONSTITUTION.MD', raw)

    def test_strict_unknown_rules_do_not_consult_directory_observations(self):
        with self.helper.fixture() as f:
            directory = f.main / '.sdlc'
            with mock.patch.object(storage.store.os, 'pathconf', return_value=-1), \
                    mock.patch.object(storage.store, 'lookup_sensitive', side_effect=AssertionError('No rule observations')):
                with self.assertRaisesRegex(ValueError, 'Cannot verify case-distinct source paths'):
                    storage.store.case_sensitive(directory, strict=True)
                with self.assertRaisesRegex(ValueError, 'Cannot verify Unicode normalization'):
                    storage.store.normalization_sensitive(directory, strict=True)
            with mock.patch.object(storage.store.sys, 'platform', 'metadata-only-test'), \
                    mock.patch.object(storage.store.os, 'pathconf', side_effect=AssertionError('No non-native attribute')), \
                    mock.patch.object(storage.store, 'lookup_sensitive', side_effect=AssertionError('No alternate probe')):
                with self.assertRaisesRegex(ValueError, 'Cannot verify case-distinct source paths'):
                    storage.store.case_sensitive(directory, strict=True)

    def test_pending_init_resumes_saved_bytes_without_live_lookup_rules(self):
        for phase in ('before-constitution', 'after-constitution'):
            with self.subTest(phase=phase), self.helper.fixture() as f:
                source = f.main / '.sdlc'
                self.helper.aliases(source)
                expected = {name: (source / name).read_bytes() for name in KNOWLEDGE}
                target = f.a / '.sdlc'
                publish = roles.initializer.publish

                def interrupt(path, data, old):
                    stop = CONSTITUTION if phase == 'before-constitution' else 'README.md'
                    if path == target / stop:
                        raise OSError('Interrupted after initialization intent')
                    return publish(path, data, old)

                with mock.patch.object(roles.initializer, 'publish', side_effect=interrupt):
                    with self.assertRaisesRegex(OSError, 'initialization intent'):
                        self.helper.init(f)
                existing = self.helper.identity(target / CONSTITUTION) if phase == 'after-constitution' else None
                with self.offline_recovery(source):
                    result = self.helper.init(f)
                self.assertFalse((target / '.init-pending.json').exists())
                for name in storage.store.KNOWLEDGE:
                    self.assertEqual((target / name).read_bytes(), expected[name])
                if existing is None:
                    self.assertEqual((target / HISTORY).read_bytes(), expected[HISTORY])
                    self.assertEqual(result['constitution_provenance'], 'imported')
                else:
                    self.assertEqual(self.helper.identity(target / CONSTITUTION), existing)
                    self.assertFalse((target / HISTORY).exists())


if __name__ == '__main__':
    unittest.main()
