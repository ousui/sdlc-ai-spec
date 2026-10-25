"""Target ownership cannot be excluded by transient lookup observations."""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
import errno
import json
import os
from pathlib import Path
import stat
import unicodedata
import unittest
from unittest import mock

try:
    from tests import test_storage_source_roles as roles
except ImportError:
    import test_storage_source_roles as roles

storage = roles.storage


class TargetLookupTests(unittest.TestCase):
    def setUp(self):
        self.helper = roles.SourceRoleTests('runTest')

    def require_equivalent_lookup(self, fixture, *, unicode=False):
        probe = fixture.base / 'lookup-probe\u00e9'
        alternate = probe.with_name(unicodedata.normalize('NFD', probe.name) if unicode else probe.name.upper())
        probe.write_bytes(b'filesystem capability')
        try:
            equivalent = alternate.exists() and os.path.samefile(probe, alternate)
        finally:
            probe.unlink()
        if not equivalent:
            self.skipTest('Requires equivalent case or Unicode filename lookup')

    @contextmanager
    def rule_fault(self, fixture, mode, native):
        """Keep the real independent probe unstable, but never forge its result."""
        original_rule = storage.store.os.pathconf
        original_probe, original_stat = storage.store.lookup_sensitive, Path.stat
        seen = {'native': 0, 'probes': 0}

        def no_rule(path, *args):
            directory = Path(path) if not isinstance(path, int) else None
            if directory is not None and (directory == fixture.base or fixture.base in directory.parents):
                seen['native'] += 1
                if native == 'error':
                    raise OSError(errno.EIO, 'Native target lookup rule unavailable')
                return -1
            return original_rule(path, *args)

        def unstable_probe(parent, name, variant):
            self.assertTrue(parent == fixture.base or fixture.base in parent.parents)
            actual, alternate = parent / name, parent / variant
            before = actual.lstat()
            self.assertTrue(os.path.samefile(actual, alternate))
            seen['probes'] += 1
            held = fixture.base / ('held-probe-' + str(seen['probes']))

            def transient(path, *args, **kwargs):
                if path != alternate:
                    return original_stat(path, *args, **kwargs)
                actual.rename(held)
                try:
                    if mode == 'replacement':
                        if stat.S_ISDIR(before.st_mode):
                            actual.mkdir()
                        else:
                            actual.write_bytes(b'Unrelated temporary inode')
                        info = original_stat(path, *args, **kwargs)
                        self.assertNotEqual((info.st_dev, info.st_ino), (before.st_dev, before.st_ino))
                        return info
                    with self.assertRaises(FileNotFoundError) as missing:
                        original_stat(path, *args, **kwargs)
                    raise missing.exception
                finally:
                    if mode == 'replacement':
                        actual.rmdir() if stat.S_ISDIR(before.st_mode) else actual.unlink()
                    held.rename(actual)

            with mock.patch.object(Path, 'stat', transient):
                answer = original_probe(parent, name, variant)
            after = actual.lstat()
            self.assertEqual((after.st_dev, after.st_ino), (before.st_dev, before.st_ino))
            return answer

        with mock.patch.object(storage.store.os, 'pathconf', side_effect=no_rule), \
                mock.patch.object(storage.store, 'lookup_sensitive', side_effect=unstable_probe):
            yield seen

    @contextmanager
    def candidate_replacement(self, fixture, target):
        self.require_equivalent_lookup(fixture)
        alternate = target.with_name(target.name.upper())
        self.assertTrue(os.path.samefile(target, alternate))
        held = fixture.base / 'held-target'
        original_stat, original_rule = Path.stat, storage.store.os.pathconf
        seen = {'candidate': 0, 'native': 0}

        def transient(path, *args, **kwargs):
            if path != alternate:
                return original_stat(path, *args, **kwargs)
            before = original_stat(target)
            target.rename(held)
            try:
                target.write_bytes(b'Only visible during candidate lookup')
                info = original_stat(path, *args, **kwargs)
                self.assertNotEqual((info.st_dev, info.st_ino), (before.st_dev, before.st_ino))
                seen['candidate'] += 1
                return info
            finally:
                target.unlink()
                held.rename(target)

        def native(*args, **kwargs):
            seen['native'] += 1
            return original_rule(*args, **kwargs)

        with mock.patch.object(Path, 'stat', transient), \
                mock.patch.object(storage.store.os, 'pathconf', side_effect=native):
            yield seen

    def control(self, fixture, target, *, unicode=False, exact=False):
        if not exact:
            self.require_equivalent_lookup(fixture, unicode=unicode)
        path = fixture.b / '.sdlc/transactions/witness/proposal.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        name = target.name if exact else unicodedata.normalize('NFD', target.name) if unicode else target.name.upper()
        path.symlink_to(target.with_name(name))
        return path

    @contextmanager
    def offline(self, source):
        with ExitStack() as stack:
            if source is not None:
                moved = source.with_name('offline-source')
                source.rename(moved)
                stack.callback(moved.rename, source)
            for name in ('source_files', 'source_snapshot', 'allowed_sources'):
                stack.enter_context(mock.patch.object(storage.changes, name, side_effect=AssertionError('No live recovery sources')))
            yield

    def test_first_init_import_stops_before_any_local_publication(self):
        for mode in ('missing', 'replacement'):
            for native in ('error', 'unsupported'):
                for dry_run in (False, True):
                    with self.subTest(mode=mode, native=native, dry_run=dry_run), self.helper.fixture() as f:
                        f.init(f.b, '--mode', 'local')
                        target = f.a / '.sdlc/README.md'
                        self.control(f, target)
                        before = self.helper.identities(f.a)
                        source = self.helper.identities(f.main / '.sdlc')
                        with self.rule_fault(f, mode, native) as seen:
                            with self.assertRaises((OSError, ValueError)):
                                self.helper.init(f, dry_run=dry_run)
                        self.assertEqual(seen['native'] > 0, storage.store.sys.platform == 'darwin')
                        self.assertEqual(seen['probes'], 0)
                        self.assertFalse((f.a / '.sdlc').exists())
                        self.assertEqual(self.helper.identities(f.a), before)
                        self.assertEqual(self.helper.identities(f.main / '.sdlc'), source)

    def test_completion_and_offline_pending_resume_preserve_existing_records(self):
        for phase in ('completion', 'pending'):
            for mode in ('missing', 'replacement'):
                for native in ('error', 'unsupported'):
                    with self.subTest(phase=phase, mode=mode, native=native), self.helper.fixture() as f:
                        f.init(f.b, '--mode', 'local')
                        target = f.a / '.sdlc/README.md'
                        if phase == 'completion':
                            self.helper.init(f)
                            target.unlink()
                        else:
                            publish = roles.initializer.publish

                            def interrupt(path, data, old):
                                if path == target:
                                    raise OSError('Stop before README publication')
                                return publish(path, data, old)

                            with mock.patch.object(roles.initializer, 'publish', side_effect=interrupt):
                                with self.assertRaisesRegex(OSError, 'Stop before README'):
                                    self.helper.init(f)
                        self.control(f, target)
                        before = self.helper.identities(f.a / '.sdlc')
                        with ExitStack() as stack:
                            if phase == 'pending':
                                stack.enter_context(self.offline(f.main / '.sdlc'))
                            seen = stack.enter_context(self.rule_fault(f, mode, native))
                            with self.assertRaises((OSError, ValueError)):
                                self.helper.init(f)
                        self.assertEqual(seen['native'] > 0, storage.store.sys.platform == 'darwin')
                        self.assertEqual(seen['probes'], 0)
                        self.assertEqual(self.helper.identities(f.a / '.sdlc'), before)
                        self.assertFalse(target.exists())
                        self.assertFalse((f.a / '.sdlc/.write-lock').exists())

    def setup_case(self, f, kind, *, existing=False, unicode=False):
        f.init(f.a, '--mode', 'local')
        f.init(f.b, '--mode', 'local')
        project = f.main if kind == 'collect' else f.a
        source = None if kind == 'edit' else (f.a if kind == 'collect' else f.main) / '.sdlc'
        feature = f.feature(project)
        basename = 'caf\u00e9.md' if unicode else 'notes.md'
        name = 'specs/001-one/' + basename
        if unicode:
            (feature / 'probe\u00e9').write_bytes(b'Independent normalization entry')
        target = feature / basename
        if existing:
            target.write_bytes(b'Existing protected data')
        if source is not None:
            (f.feature(f.a if kind == 'collect' else f.main) / basename).write_bytes(b'Candidate data')
        sources = [source] if kind == 'collect' else []
        return project, source, sources, name, target

    def prepare(self, project, kind, sources, name):
        plan = storage.changes.prepare(project, kind, sources,
                                       [] if kind == 'edit' else ['001-one'], [name] if kind == 'edit' else [])
        Path(plan['proposal']).write_text(json.dumps({name: {'action': 'replace', 'text': 'Candidate data'}}))
        return plan

    def check_phase(self, kind, phase, mode, native, *, unicode=False, inode=False):
        with self.helper.fixture() as f:
            project, source, sources, name, target = self.setup_case(f, kind, existing=inode, unicode=unicode)
            plan = None if phase == 'prepare' else self.prepare(project, kind, sources, name)
            folder = Path(plan['transaction']) if plan is not None else None
            if phase == 'recover':
                storage.changes.apply(project, folder)
                path = folder / 'manifest.json'
                data = json.loads(path.read_text())
                data['status'] = 'applying'
                path.write_text(json.dumps(data))
            alias = self.control(f, target, unicode=unicode)
            before = self.helper.identities(project / '.sdlc')
            records = {n: self.helper.identity(folder / n) for n in ('manifest.json', 'proposal.json')} if folder else None
            source_before = self.helper.identities(source) if source is not None else None
            with ExitStack() as stack:
                if phase == 'recover':
                    stack.enter_context(self.offline(source))
                seen = stack.enter_context(self.candidate_replacement(f, target) if inode else self.rule_fault(f, mode, native))
                with self.assertRaises((OSError, ValueError)):
                    if phase == 'prepare':
                        self.prepare(project, kind, sources, name)
                    else:
                        getattr(storage.changes, phase)(project, folder)
            if inode:
                self.assertGreater(seen['candidate'], 0)
            else:
                self.assertEqual(seen['probes'], 0)
                if not unicode and phase != 'recover':
                    self.assertEqual(seen['native'] > 0, storage.store.sys.platform == 'darwin')
            self.assertEqual(self.helper.identities(project / '.sdlc'), before)
            if source is not None:
                self.assertEqual(self.helper.identities(source), source_before)
            self.assertFalse((project / '.sdlc/.write-lock').exists())
            if folder:
                self.assertEqual({n: self.helper.identity(folder / n) for n in records}, records)
            else:
                self.assertFalse((project / '.sdlc/transactions').exists())
            alias.unlink()
            if phase == 'recover':
                with self.offline(source):
                    self.assertEqual(storage.changes.recover(project, folder)['status'], 'recovered')
                self.assertEqual(target.read_bytes() if target.exists() else None,
                                 b'Existing protected data' if inode else None)
            else:
                plan = plan or self.prepare(project, kind, sources, name)
                storage.changes.apply(project, Path(plan['transaction']))
                self.assertEqual(target.read_bytes(), b'Candidate data')

    def test_native_rule_failures_block_prepare_apply_and_recover(self):
        for kind in ('edit', 'import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                for native in ('error', 'unsupported'):
                    for mode in ('missing', 'replacement'):
                        with self.subTest(kind=kind, phase=phase, native=native, mode=mode):
                            self.check_phase(kind, phase, mode, native)

    def test_unicode_observations_cannot_exclude_owned_targets(self):
        for kind in ('edit', 'import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                for mode in ('missing', 'replacement'):
                    with self.subTest(kind=kind, phase=phase, mode=mode):
                        self.check_phase(kind, phase, mode, 'unsupported', unicode=True)

    def test_candidate_inode_replacement_cannot_exclude_existing_owned_files(self):
        for kind in ('edit', 'import', 'collect'):
            for phase in ('prepare', 'apply', 'recover'):
                with self.subTest(kind=kind, phase=phase):
                    self.check_phase(kind, phase, 'replacement', 'available', inode=True)

    def test_confirmed_distinct_missing_names_and_positive_aliases_need_no_probes(self):
        with self.helper.fixture() as f:
            root = f.a
            left, right = root / 'new-file', root / 'NEW-FILE'
            with mock.patch.object(storage.store.sys, 'platform', 'darwin'), \
                    mock.patch.object(storage.store.os, 'pathconf', return_value=1), \
                    mock.patch.object(storage.store, 'lookup_sensitive', side_effect=AssertionError('No ownership probes')):
                self.assertFalse(storage.store.same_target(left, right))
            with mock.patch.object(storage.store.os, 'pathconf', side_effect=AssertionError('No rule needed')):
                self.assertFalse(storage.store.same_target(left, root / 'different-file'))
                self.assertTrue(storage.store.same_target(left, left))
                alias = f.base / 'positive-root-alias'
                alias.symlink_to(root, target_is_directory=True)
                self.assertTrue(storage.store.same_target(root, alias))

    def test_non_darwin_unknown_native_rules_preserve_ownership_and_missing_paths(self):
        with self.helper.fixture() as f:
            left, right = f.a / 'missing-name', f.a / 'MISSING-NAME'
            for platform in ('linux', 'metadata-only-test'):
                with self.subTest(platform=platform), mock.patch.object(storage.store.sys, 'platform', platform), \
                        mock.patch.object(storage.store.os, 'pathconf', side_effect=AssertionError('No Darwin attribute')), \
                        mock.patch.object(storage.store, 'lookup_sensitive', side_effect=AssertionError('No ownership probe')):
                    with self.assertRaisesRegex(ValueError, 'Cannot verify case-distinct'):
                        storage.store.same_target(left, right)
                    self.assertFalse(storage.store.same_target(left, f.a / 'unrelated-name'))
                    self.assertTrue(storage.store.same_target(left, left))

    def test_unrelated_control_alias_does_not_block_legal_missing_document(self):
        with self.helper.fixture() as f:
            project, source, sources, name, target = self.setup_case(f, 'edit')
            self.control(f, target.with_name('unrelated.md'))
            with self.rule_fault(f, 'missing', 'error') as seen:
                plan = self.prepare(project, 'edit', [], name)
                storage.changes.apply(project, Path(plan['transaction']))
            self.assertEqual(seen, {'native': 0, 'probes': 0})
            self.assertEqual(target.read_bytes(), b'Candidate data')


if __name__ == '__main__':
    unittest.main()
