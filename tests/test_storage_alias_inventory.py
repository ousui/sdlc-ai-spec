"""Incomplete alias inventories and unstable edit identities cannot authorize writes."""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
import errno
import json
import os
from pathlib import Path
import stat
import unittest
from unittest import mock

try:
    from tests import test_storage_target_lookup as lookup
except ImportError:
    import test_storage_target_lookup as lookup

storage = lookup.storage


class AliasInventoryTests(unittest.TestCase):
    def setUp(self):
        self.case = lookup.TargetLookupTests('runTest')
        self.case.setUp()

    @contextmanager
    def directory_fault(self, f, directory, mode, *, opening=False):
        """Return a real absence or different inode, restoring the directory first."""
        original_stat, original_open, original_resolve = Path.stat, os.open, Path.resolve
        before = original_stat(directory)
        ancestor = mode.startswith('ancestor-') or mode == 'resolution'
        changed_path = directory.parent if ancestor else directory
        replacement = mode != 'missing'
        held = f.base / 'held-alias-directory'
        seen = {'faults': 0}
        if mode == 'resolution':
            alternate = f.base / 'alternate-alias-directory'
            (alternate / directory.name).mkdir(parents=True)

        @contextmanager
        def changed():
            changed_path.rename(held)
            try:
                if replacement:
                    if mode == 'resolution':
                        changed_path.symlink_to(alternate)
                    elif mode in ('cycle', 'ancestor-cycle'):
                        changed_path.symlink_to(changed_path)
                    else:
                        changed_path.write_bytes(b'Temporary regular-file inode')
                seen['faults'] += 1
                yield
            finally:
                if replacement:
                    changed_path.unlink()
                held.rename(changed_path)

        def metadata(path, *args, **kwargs):
            if path != directory:
                return original_stat(path, *args, **kwargs)
            with changed():
                if ancestor or mode == 'cycle':
                    return original_stat(path, *args, **kwargs)
                if mode == 'missing':
                    with self.assertRaises(FileNotFoundError) as error:
                        original_stat(path, *args, **kwargs)
                    raise error.exception
                info = original_stat(path, *args, **kwargs)
                self.assertFalse(stat.S_ISDIR(info.st_mode))
                self.assertNotEqual((info.st_dev, info.st_ino), (before.st_dev, before.st_ino))
                return info

        def opened(path, flags, *args, **kwargs):
            if Path(path) != directory or not flags & os.O_DIRECTORY:
                return original_open(path, flags, *args, **kwargs)
            with changed():
                return original_open(path, flags, *args, **kwargs)

        def resolved(path, *args, **kwargs):
            if path != directory:
                return original_resolve(path, *args, **kwargs)
            with changed():
                return original_resolve(path, *args, **kwargs)

        patch = (mock.patch.object(storage.store.os, 'open', side_effect=opened) if opening else
                 mock.patch.object(Path, 'resolve', resolved) if mode == 'resolution' else
                 mock.patch.object(Path, 'stat', metadata))
        with patch:
            yield seen
        after = original_stat(directory)
        self.assertEqual((after.st_dev, after.st_ino), (before.st_dev, before.st_ino))

    def transaction_case(self, kind, phase, mode, *, authority=False):
        with self.case.helper.fixture() as f:
            project, source, sources, name, target = self.case.setup_case(f, kind, existing=True)
            plan = None if phase == 'prepare' else self.case.prepare(project, kind, sources, name)
            folder = Path(plan['transaction']) if plan else None
            if phase == 'recover':
                storage.changes.apply(project, folder)
                path = folder / 'manifest.json'
                data = json.loads(path.read_text())
                data['status'] = 'applying'
                path.write_text(json.dumps(data))
            if authority:
                owner = f.main / '.sdlc/specs'
                alias = owner / 'authority-witness/link.md'
                alias.parent.mkdir(parents=True)
                alias.symlink_to(target)
            else:
                owner = f.b / '.sdlc/transactions'
                alias = self.case.control(f, target, exact=True)
            before = self.case.helper.identities(project / '.sdlc')
            source_before = self.case.helper.identities(source) if source else None
            records = {n: self.case.helper.identity(folder / n) for n in ('manifest.json', 'proposal.json')} if folder else None
            with ExitStack() as stack:
                if phase == 'recover' and not authority:
                    stack.enter_context(self.case.offline(source))
                watched = alias.parent if mode.startswith('ancestor-') or mode == 'resolution' else owner
                seen = stack.enter_context(self.directory_fault(f, watched, mode))
                with self.assertRaises((OSError, ValueError)):
                    if phase == 'prepare':
                        self.case.prepare(project, kind, sources, name)
                    else:
                        getattr(storage.changes, phase)(project, folder)
            self.assertGreater(seen['faults'], 0)
            self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
            self.assertFalse((project / '.sdlc/.write-lock').exists())
            if source:
                self.assertEqual(self.case.helper.identities(source), source_before)
            if folder:
                self.assertEqual({n: self.case.helper.identity(folder / n) for n in records}, records)
            else:
                self.assertFalse((project / '.sdlc/transactions').exists())
            alias.unlink()
            if phase == 'recover':
                with self.case.offline(source):
                    self.assertEqual(storage.changes.recover(project, folder)['status'], 'recovered')
                self.assertEqual(target.read_bytes(), b'Existing protected data')
            else:
                plan = plan or self.case.prepare(project, kind, sources, name)
                storage.changes.apply(project, Path(plan['transaction']))
                self.assertEqual(target.read_bytes(), b'Candidate data')

    def test_control_directory_metadata_cannot_hide_aliases_in_any_transaction_phase(self):
        for mode in ('missing', 'replacement', 'ancestor-replacement', 'cycle', 'ancestor-cycle', 'resolution'):
            for kind in ('edit', 'import', 'collect'):
                for phase in ('prepare', 'apply', 'recover'):
                    with self.subTest(mode=mode, kind=kind, phase=phase):
                        self.transaction_case(kind, phase, mode)

    def test_authority_external_artifact_inventory_cannot_be_skipped(self):
        for mode in ('missing', 'replacement', 'ancestor-replacement', 'cycle', 'ancestor-cycle', 'resolution'):
            for phase in ('prepare', 'apply', 'recover'):
                with self.subTest(mode=mode, phase=phase):
                    self.transaction_case('edit', phase, mode, authority=True)

    def test_first_completion_and_offline_pending_init_preserve_records_on_alias_fault(self):
        for mode in ('missing', 'replacement', 'ancestor-replacement', 'cycle', 'ancestor-cycle', 'resolution'):
            for phase in ('first', 'completion', 'pending'):
                for dry_run in ((False, True) if phase == 'first' else (False,)):
                    with self.subTest(mode=mode, phase=phase, dry_run=dry_run), self.case.helper.fixture() as f:
                        f.init(f.b, '--mode', 'local')
                        target = f.a / '.sdlc/README.md'
                        if phase == 'completion':
                            self.case.helper.init(f)
                            target.unlink()
                        if phase == 'pending':
                            publish = lookup.roles.initializer.publish

                            def interrupt(path, data, old):
                                if path == target:
                                    raise OSError('Interrupt before README publication')
                                return publish(path, data, old)

                            with mock.patch.object(lookup.roles.initializer, 'publish', side_effect=interrupt):
                                with self.assertRaisesRegex(OSError, 'Interrupt before README'):
                                    self.case.helper.init(f)
                        alias = self.case.control(f, target, exact=True)
                        before = self.case.helper.identities(f.a)
                        source = self.case.helper.identities(f.main / '.sdlc')
                        with ExitStack() as stack:
                            if phase == 'pending':
                                stack.enter_context(self.case.offline(f.main / '.sdlc'))
                            watched = alias.parent if mode.startswith('ancestor-') or mode == 'resolution' else f.b / '.sdlc/transactions'
                            seen = stack.enter_context(self.directory_fault(f, watched, mode))
                            with self.assertRaises((OSError, ValueError)):
                                self.case.helper.init(f, dry_run=dry_run)
                        self.assertGreater(seen['faults'], 0)
                        self.assertEqual(self.case.helper.identities(f.a), before)
                        self.assertEqual(self.case.helper.identities(f.main / '.sdlc'), source)
                        self.assertFalse(target.exists())
                        alias.unlink()
                        with self.case.offline(f.main / '.sdlc') if phase == 'pending' else ExitStack():
                            result = self.case.helper.init(f, dry_run=dry_run)
                        self.assertEqual(result['dry_run'], dry_run)
                        self.assertEqual(target.exists(), not dry_run)

    def test_failed_directory_open_cannot_discard_an_existing_namespace_entry(self):
        for mode in ('missing', 'replacement'):
            with self.subTest(mode=mode), self.case.helper.fixture() as f:
                directory = f.b / '.sdlc/transactions'
                directory.mkdir(parents=True)
                with self.directory_fault(f, directory, mode, opening=True) as seen:
                    with self.assertRaises((OSError, ValueError)):
                        list(storage.store.alias_targets([directory]))
                self.assertGreater(seen['faults'], 0)

    def test_directory_replacement_during_enumeration_invalidates_the_inventory(self):
        with self.case.helper.fixture() as f:
            directory = f.b / '.sdlc/transactions'
            directory.mkdir(parents=True)
            held = f.base / 'held-enumeration'
            identity = directory.stat()
            original = os.scandir
            seen = []

            @contextmanager
            def changed(value):
                same = ((os.fstat(value).st_dev, os.fstat(value).st_ino) == (identity.st_dev, identity.st_ino)
                        if isinstance(value, int) else Path(value) == directory)
                if not same:
                    with original(value) as entries:
                        yield entries
                    return
                directory.rename(held)
                directory.mkdir()
                seen.append(True)
                with original(value) as entries:
                    yield entries

            try:
                with mock.patch.object(storage.store.os, 'scandir', side_effect=changed):
                    with self.assertRaises((OSError, ValueError)):
                        list(storage.store.alias_targets([directory]))
            finally:
                if held.exists():
                    directory.rmdir()
                    held.rename(directory)
            self.assertTrue(seen)

    def test_discovered_child_metadata_cannot_hide_a_directory(self):
        for mode in ('missing', 'replacement'):
            with self.subTest(mode=mode), self.case.helper.fixture() as f:
                directory = f.b / '.sdlc/transactions'
                child = directory / 'witness'
                child.mkdir(parents=True)
                (child / 'control-link').symlink_to(f.base / 'missing-target')
                held = f.base / 'held-known-entry'
                root_info = directory.stat()
                original = os.scandir
                seen = []

                class Entry:
                    def __init__(self, entry):
                        self.entry = entry
                        self.name = entry.name
                        self.path = entry.path

                    def is_dir(self, **kwargs):
                        return self.entry.is_dir(**kwargs)

                    def is_symlink(self):
                        return self.entry.is_symlink()

                    def stat(self, **kwargs):
                        child.rename(held)
                        try:
                            if mode == 'replacement':
                                child.write_bytes(b'Temporary entry inode')
                            seen.append(True)
                            return self.entry.stat(**kwargs)
                        finally:
                            if mode == 'replacement':
                                child.unlink()
                            held.rename(child)

                @contextmanager
                def scanned(value):
                    same = ((os.fstat(value).st_dev, os.fstat(value).st_ino) == (root_info.st_dev, root_info.st_ino)
                            if isinstance(value, int) else Path(value) == directory)
                    with original(value) as entries:
                        yield (Entry(entry) if same and entry.name == child.name else entry for entry in entries)

                with mock.patch.object(storage.store.os, 'scandir', side_effect=scanned):
                    with self.assertRaises((OSError, ValueError)):
                        list(storage.store.alias_targets([directory]))
                self.assertTrue(seen)

    def test_missing_paths_unreadable_regular_files_and_broken_aliases_remain_legal(self):
        with self.case.helper.fixture() as f:
            leaf = f.base / 'unreadable-leaf'
            leaf.write_bytes(b'No content read is needed')
            leaf.chmod(0)
            dangling, cycle = f.base / 'dangling', f.base / 'cycle'
            missing = f.base / 'missing-parent/missing-leaf'
            dangling.symlink_to(missing)
            cycle.symlink_to(cycle)
            cycle_a, cycle_b = f.base / 'cycle-a', f.base / 'cycle-b'
            cycle_a.symlink_to(cycle_b.name)
            cycle_b.symlink_to(cycle_a.name)
            try:
                targets = list(storage.store.alias_targets([missing, leaf, dangling, cycle, cycle_a, cycle_b / 'child']))
                self.assertEqual(targets, [missing])
            finally:
                leaf.chmod(0o644)
            parent = f.base / 'search-only-parent'
            parent.mkdir()
            protected = parent / 'unreadable-leaf'
            protected.write_bytes(b'No content or enumeration permission is needed')
            protected.chmod(0)
            protected_cycle = parent / 'cycle'
            protected_cycle.symlink_to(protected_cycle.name)
            parent.chmod(0o111)
            try:
                self.assertEqual(list(storage.store.alias_targets([protected])), [])
                self.assertEqual(list(storage.store.alias_targets([protected_cycle])), [])
                self.assertEqual(list(storage.store.alias_targets([parent / 'missing/child'])), [])
            finally:
                parent.chmod(0o755)
                protected.chmod(0o644)
            known = parent / 'known-directory'
            known.mkdir()
            (known / 'control-link').symlink_to(f.base / 'missing-target')
            parent_info = parent.stat()
            held_lookup = f.base / 'held-metadata-child'
            real_open, real_stat = os.open, os.stat
            metadata_faults = []
            open_faults = []

            def missing_open(path, flags, *args, **kwargs):
                if Path(path) != known:
                    return real_open(path, flags, *args, **kwargs)
                known.rename(held_lookup)
                try:
                    open_faults.append(True)
                    return real_open(path, flags, *args, **kwargs)
                finally:
                    held_lookup.rename(known)

            def missing_metadata(path, *args, **kwargs):
                descriptor = kwargs.get('dir_fd')
                same = descriptor is not None and (os.fstat(descriptor).st_dev, os.fstat(descriptor).st_ino) == (parent_info.st_dev, parent_info.st_ino)
                if not same or path != known.name:
                    return real_stat(path, *args, **kwargs)
                known.rename(held_lookup)
                try:
                    metadata_faults.append(True)
                    return real_stat(path, *args, **kwargs)
                finally:
                    held_lookup.rename(known)

            with mock.patch.object(os, 'open', side_effect=missing_open), \
                    mock.patch.object(os, 'stat', side_effect=missing_metadata):
                with self.assertRaises((OSError, ValueError)):
                    list(storage.store.alias_targets([known]))
            self.assertTrue(open_faults)  # A known directory now stops at its failed open.
            # A hardlinked relative symlink has different meaning in two
            # parents. A repeated inode alone must not prove a stable cycle.
            left, right = f.base / 'left', f.base / 'right'
            left.mkdir()
            right.mkdir()
            first, middle, last = left / 'entry', left / 'next', right / 'entry'
            first.symlink_to('next')
            os.link(first, last, follow_symlinks=False)
            self.assertEqual(first.lstat().st_ino, last.lstat().st_ino)
            middle.symlink_to(last)
            terminal, held = right / 'next', f.base / 'held-cycle-target'
            terminal.mkdir()
            original_stat = Path.stat
            seen = []

            def cycle_fault(path, *args, **kwargs):
                if path not in (first, middle, last):
                    return original_stat(path, *args, **kwargs)
                terminal.rename(held)
                terminal.symlink_to(terminal)
                try:
                    seen.append(True)
                    return original_stat(path, *args, **kwargs)
                finally:
                    terminal.unlink()
                    held.rename(terminal)

            with mock.patch.object(Path, 'stat', cycle_fault):
                with self.assertRaises((OSError, ValueError)):
                    list(storage.store.alias_targets([first]))
            self.assertTrue(seen)
            self.assertIn(terminal, list(storage.store.alias_targets([first])))
            f.init(f.a, '--mode', 'local')
            name = 'specs/001-one/new.md'
            f.feature(f.a)
            plan = self.case.prepare(f.a, 'edit', [], name)
            storage.changes.apply(f.a, Path(plan['transaction']))
            self.assertEqual((f.a / '.sdlc' / name).read_bytes(), b'Candidate data')

    @contextmanager
    def candidate_fault(self, f, target, *, narrow=False):
        if not narrow:
            with self.case.candidate_replacement(f, target) as seen:
                yield seen
            return
        original = storage.changes.edit_bindings
        seen = {'candidate': 0}

        def bindings(*args, **kwargs):
            with self.case.candidate_replacement(f, target) as fault:
                try:
                    return original(*args, **kwargs)
                finally:
                    seen['candidate'] += fault['candidate']

        with mock.patch.object(storage.changes, 'edit_bindings', side_effect=bindings):
            yield seen

    def test_duplicate_edit_candidates_stop_before_records_or_first_publication(self):
        for narrow in (False, True):
            with self.subTest(narrow=narrow), self.case.helper.fixture() as f:
                project, _, _, name, target = self.case.setup_case(f, 'edit', existing=True)
                names = [name, str(Path(name).with_name(target.name.upper()))]
                before = self.case.helper.identities(project / '.sdlc')
                with self.candidate_fault(f, target, narrow=narrow) as seen:
                    with self.assertRaises((OSError, ValueError)):
                        storage.changes.prepare(project, 'edit', [], [], names)
                self.assertGreater(seen['candidate'], 0)
                self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                self.assertFalse((project / '.sdlc/transactions').exists())

    def legacy_duplicate(self, project, names):
        def old_bindings(context, target, paths):
            return {name: storage.changes.edit_binding(context, target, name) for name in sorted(set(paths))}
        with mock.patch.object(storage.changes, 'edit_bindings', side_effect=old_bindings):
            plan = storage.changes.prepare(project, 'edit', [], [], names)
        Path(plan['proposal']).write_text(json.dumps({n: {'action': 'replace', 'text': 'candidate-' + str(i)}
                                                   for i, n in enumerate(names)}))
        return Path(plan['transaction'])

    def test_prepared_legacy_duplicate_is_rejected_without_partial_writes(self):
        for narrow in (False, True):
            with self.subTest(narrow=narrow), self.case.helper.fixture() as f:
                project, _, _, name, target = self.case.setup_case(f, 'edit', existing=True)
                names = [name, str(Path(name).with_name(target.name.upper()))]
                folder = self.legacy_duplicate(project, names)
                before = self.case.helper.identities(project / '.sdlc')
                records = {n: self.case.helper.identity(folder / n) for n in ('manifest.json', 'proposal.json')}
                with self.candidate_fault(f, target, narrow=narrow):
                    with self.assertRaises((OSError, ValueError)):
                        storage.changes.apply(project, folder)
                self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                self.assertEqual({n: self.case.helper.identity(folder / n) for n in records}, records)

    def test_ambiguous_legacy_partial_duplicate_is_preserved_for_manual_inspection(self):
        with self.case.helper.fixture() as f:
            project, _, _, name, target = self.case.setup_case(f, 'edit', existing=True)
            names = [name, str(Path(name).with_name(target.name.upper()))]
            folder = self.legacy_duplicate(project, names)
            target.write_bytes(b'First candidate from the old interrupted transaction')
            path = folder / 'manifest.json'
            manifest = json.loads(path.read_text())
            manifest.update(status='applying', after={n: storage.changes.base64.b64encode(b'candidate').decode() for n in names}, published={})
            path.write_text(json.dumps(manifest))
            before = self.case.helper.identities(project / '.sdlc')
            records = {n: self.case.helper.identity(folder / n) for n in ('manifest.json', 'proposal.json')}
            with self.candidate_fault(f, target):
                with self.assertRaises((OSError, ValueError)):
                    storage.changes.recover(project, folder)
            self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
            self.assertEqual({n: self.case.helper.identity(folder / n) for n in records}, records)

    def test_partial_publication_recovers_offline_after_alias_inventory_is_repaired(self):
        for kind in ('edit', 'import', 'collect'):
            for mode in ('missing', 'replacement', 'ancestor-replacement', 'cycle', 'ancestor-cycle', 'resolution'):
                with self.subTest(kind=kind, mode=mode), self.case.helper.fixture() as f:
                    project, source, sources, name, target = self.case.setup_case(f, kind, existing=True)
                    second = target.with_name('second.md')
                    second.write_bytes(b'Original second file')
                    names = [name, str(Path(name).with_name(second.name))]
                    if source:
                        (source / names[1]).write_bytes(b'Second candidate')
                    plan = storage.changes.prepare(project, kind, sources,
                        ['001-one'] if kind != 'edit' else [], names if kind == 'edit' else [])
                    folder = Path(plan['transaction'])
                    Path(plan['proposal']).write_text(json.dumps({n: {'action': 'replace', 'text': 'Candidate-' + str(i)}
                                                               for i, n in enumerate(names)}))
                    publish = storage.changes.publish_data

                    def interrupted(path, data, old):
                        if path == second:
                            raise OSError('Stop before second publication')
                        return publish(path, data, old)

                    with mock.patch.object(storage.changes, 'publish_data', side_effect=interrupted), \
                            mock.patch.object(storage.changes, 'rollback', side_effect=OSError('Interrupted rollback')):
                        with self.assertRaisesRegex(OSError, 'Stop before second'):
                            storage.changes.apply(project, folder)
                    self.assertEqual(target.read_bytes(), b'Candidate-0')
                    self.assertEqual(second.read_bytes(), b'Original second file')
                    alias = self.case.control(f, target, exact=True)
                    before = self.case.helper.identities(project / '.sdlc')
                    records = {n: self.case.helper.identity(folder / n) for n in ('manifest.json', 'proposal.json')}
                    watched = alias.parent if mode.startswith('ancestor-') or mode == 'resolution' else f.b / '.sdlc/transactions'
                    with self.case.offline(source), self.directory_fault(f, watched, mode):
                        with self.assertRaises((OSError, ValueError)):
                            storage.changes.recover(project, folder)
                    self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                    self.assertEqual({n: self.case.helper.identity(folder / n) for n in records}, records)
                    alias.unlink()
                    with self.case.offline(source):
                        self.assertEqual(storage.changes.recover(project, folder)['status'], 'recovered')
                    self.assertEqual(target.read_bytes(), b'Existing protected data')
                    self.assertEqual(second.read_bytes(), b'Original second file')


if __name__ == '__main__':
    unittest.main()
