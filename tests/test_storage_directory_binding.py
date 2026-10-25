"""Parent/child handoff and full source snapshots retain directory identity."""
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
import unittest
from unittest import mock

try:
    from tests import test_storage_target_lookup as lookup
except ImportError:
    import test_storage_target_lookup as lookup

storage = lookup.storage


class DirectoryBindingTests(unittest.TestCase):
    def setUp(self):
        self.case = lookup.TargetLookupTests('runTest')
        self.case.setUp()

    def control(self, fixture, target):
        alias = fixture.b / '.sdlc/transactions/witness/proposal.json'
        alias.parent.mkdir(parents=True, exist_ok=True)
        alias.symlink_to(target)
        return alias

    @contextmanager
    def handoff(self, fixture, directory, when):
        store = storage.store
        original_resolve, original_directory = store.resolve_alias, store.alias_directory
        held = fixture.base / 'held-handoff-directory'
        identity = directory.stat().st_ino
        seen = {'replacements': 0, 'active': False}

        def replace():
            self.assertFalse(seen['active'])
            directory.rename(held)
            directory.mkdir()
            self.assertNotEqual(directory.stat().st_ino, identity)
            seen['replacements'] += 1
            seen['active'] = True

        def restore():
            if seen['active']:
                directory.rmdir()
                held.rename(directory)
                seen['active'] = False

        def resolved(path):
            if path == directory and when == 'resolve':
                replace()
            try:
                return original_resolve(path)
            except BaseException:
                restore()
                raise

        @contextmanager
        def opened(path, **kwargs):
            if path == directory and when == 'open':
                replace()
            try:
                with original_directory(path, **kwargs) as descriptor:
                    yield descriptor
            finally:
                if path == directory:
                    restore()

        try:
            with mock.patch.object(store, 'resolve_alias', side_effect=resolved), \
                    mock.patch.object(store, 'alias_directory', side_effect=opened):
                yield seen
        finally:
            restore()
        self.assertEqual(directory.stat().st_ino, identity)

    @contextmanager
    def empty_source(self, fixture, source):
        directory, held = source / 'memory', fixture.base / 'held-source-memory'
        original, original_open = os.scandir, os.open
        info = directory.stat()
        seen = {'replacements': 0}
        case = self

        class Entries:
            def __init__(self, path):
                self.changed = not isinstance(path, int) and Path(path) == directory
                if self.changed:
                    directory.rename(held)
                    directory.mkdir()
                    case.assertNotEqual(directory.stat().st_ino, info.st_ino)
                    seen['replacements'] += 1
                try:
                    self.entries = original(path)
                except BaseException:
                    self.close()
                    raise

            def __iter__(self):
                return self

            def __next__(self):
                return next(self.entries)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

            def close(self):
                if hasattr(self, 'entries'):
                    self.entries.close()
                if self.changed:
                    directory.rmdir()
                    held.rename(directory)
                    self.changed = False

        def opened(path, flags, *args, **kwargs):
            metadata_flag = getattr(os, 'O_PATH', getattr(os, 'O_SEARCH',
                0x40000000 if storage.store.sys.platform == 'darwin' else 0))
            metadata_flag &= ~os.O_DIRECTORY
            if (Path(path) != directory or not flags & os.O_DIRECTORY
                    or (metadata_flag and flags & metadata_flag)):
                return original_open(path, flags, *args, **kwargs)
            directory.rename(held)
            directory.mkdir()
            seen['replacements'] += 1
            try:
                return original_open(path, flags, *args, **kwargs)
            finally:
                directory.rmdir()
                held.rename(directory)

        with mock.patch.object(os, 'scandir', side_effect=Entries), \
                mock.patch.object(os, 'open', side_effect=opened):
            yield seen
        self.assertEqual(directory.stat().st_ino, info.st_ino)

    def records(self, folder):
        return {name: (folder / name).read_bytes() for name in ('manifest.json', 'proposal.json')}

    @contextmanager
    def root_link_handoff(self, fixture, link, alternate):
        store = storage.store
        real_resolve, real_directory, real_targets = store.resolve_alias, store.alias_directory, store.alias_targets
        held = fixture.base / 'held-root-link'
        seen = {'faults': 0, 'active': False, 'scanning': False}
        def restore():
            if seen['active']:
                link.unlink()
                held.rename(link)
                seen['active'] = False
        def resolved(path):
            if path == link and seen['scanning']:
                self.assertFalse(seen['active'])
                link.rename(held)
                link.symlink_to(alternate, target_is_directory=alternate.is_dir())
                seen['active'] = True
                seen['faults'] += 1
            return real_resolve(path)
        @contextmanager
        def opened(path, **kwargs):
            try:
                with real_directory(path, **kwargs) as descriptor:
                    yield descriptor
            finally:
                if path == alternate:
                    restore()
        def targets(roots):
            seen['scanning'] = True
            try:
                yield from real_targets(roots)
            finally:
                restore()
                seen['scanning'] = False
        try:
            with mock.patch.object(store, 'resolve_alias', side_effect=resolved), \
                    mock.patch.object(store, 'alias_directory', side_effect=opened), \
                    mock.patch.object(store, 'alias_targets', side_effect=targets):
                yield seen
        finally:
            restore()

    def test_declared_root_links_cannot_be_temporarily_rebound_and_restored(self):
        for role in ('knowledge', 'control'):
            for kind in ('edit',) if role == 'knowledge' else ('edit', 'import', 'collect'):
                for phase in ('prepare', 'apply', 'recover'):
                    with self.subTest(role=role, kind=kind, phase=phase), self.case.helper.fixture() as f:
                        project, source, sources, name, target = self.case.setup_case(f, kind, existing=True)
                        plan = None if phase == 'prepare' else self.case.prepare(project, kind, sources, name)
                        folder = Path(plan['transaction']) if plan else None
                        if phase == 'recover':
                            storage.changes.apply(project, folder)
                            manifest = json.loads((folder / 'manifest.json').read_text())
                            manifest['status'] = 'applying'
                            (folder / 'manifest.json').write_text(json.dumps(manifest))
                        alternate = f.base / 'unrelated-root-target'
                        if role == 'knowledge':
                            link = f.main / '.sdlc/memory/constitution.md'
                            link.unlink()
                            link.symlink_to(target)
                            alternate.write_bytes(b'Unrelated knowledge file')
                        else:
                            owner = f.base / 'external-root-control'
                            owner.mkdir()
                            (owner / 'protected').symlink_to(target)
                            link = f.b / '.sdlc/transactions'
                            link.symlink_to(owner, target_is_directory=True)
                            alternate.mkdir()
                        before = self.case.helper.identities(project / '.sdlc')
                        records = self.records(folder) if folder else None
                        with ExitStack() as stack:
                            if phase == 'recover':
                                stack.enter_context(self.case.offline(source))
                            seen = stack.enter_context(self.root_link_handoff(f, link, alternate))
                            with self.assertRaises((OSError, ValueError)):
                                if phase == 'prepare':
                                    self.case.prepare(project, kind, sources, name)
                                else:
                                    getattr(storage.changes, phase)(project, folder)
                        self.assertGreater(seen['faults'], 0)
                        self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                        if folder:
                            self.assertEqual(self.records(folder), records)

    @contextmanager
    def linked_handoff(self, fixture, directory, links):
        store = storage.store
        original_resolve, original_directory = store.resolve_alias, store.alias_directory
        held = fixture.base / 'held-link-target'
        seen = {'replacements': 0, 'active': False}

        def restore():
            if seen['active']:
                directory.rmdir()
                held.rename(directory)
                seen['active'] = False

        def resolved(path):
            if path in links and not seen['replacements']:
                directory.rename(held)
                directory.mkdir()
                seen['replacements'] += 1
                seen['active'] = True
            return original_resolve(path)

        @contextmanager
        def opened(path, **kwargs):
            try:
                with original_directory(path, **kwargs) as descriptor:
                    yield descriptor
            finally:
                if path == directory:
                    restore()

        try:
            with mock.patch.object(store, 'resolve_alias', side_effect=resolved), \
                    mock.patch.object(store, 'alias_directory', side_effect=opened):
                yield seen
        finally:
            restore()

    def test_link_target_identity_is_rechecked_on_revisit_and_at_traversal_end(self):
        for duplicate in (False, True):
            for kind in ('edit', 'import', 'collect'):
                for phase in ('prepare', 'apply', 'recover'):
                    with self.subTest(duplicate=duplicate, kind=kind, phase=phase), self.case.helper.fixture() as f:
                        project, source, sources, name, target = self.case.setup_case(f, kind, existing=True)
                        plan = None if phase == 'prepare' else self.case.prepare(project, kind, sources, name)
                        folder = Path(plan['transaction']) if plan else None
                        if phase == 'recover':
                            storage.changes.apply(project, folder)
                            manifest = json.loads((folder / 'manifest.json').read_text())
                            manifest['status'] = 'applying'
                            (folder / 'manifest.json').write_text(json.dumps(manifest))
                        owner = f.b / '.sdlc/transactions/witness'
                        owner.mkdir(parents=True)
                        external = f.base / 'external-control-directory'
                        external.mkdir()
                        (external / 'protected').symlink_to(target)
                        links = [owner / name for name in ('first', 'second')[:2 if duplicate else 1]]
                        for link in links:
                            link.symlink_to(external, target_is_directory=True)
                        before = self.case.helper.identities(project / '.sdlc')
                        records = self.records(folder) if folder else None
                        with ExitStack() as stack:
                            if phase == 'recover':
                                stack.enter_context(self.case.offline(source))
                            seen = stack.enter_context(self.linked_handoff(f, external, links))
                            with self.assertRaises((OSError, ValueError)):
                                if phase == 'prepare':
                                    self.case.prepare(project, kind, sources, name)
                                else:
                                    getattr(storage.changes, phase)(project, folder)
                        self.assertEqual(seen['replacements'], 1)
                        self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                        if folder:
                            self.assertEqual(self.records(folder), records)

    def test_alias_handoff_blocks_all_transaction_phases(self):
        for when in ('resolve', 'open'):
            for kind in ('edit', 'import', 'collect'):
                for phase in ('prepare', 'apply', 'recover'):
                    with self.subTest(when=when, kind=kind, phase=phase), self.case.helper.fixture() as f:
                        project, source, sources, name, target = self.case.setup_case(f, kind, existing=True)
                        plan = None if phase == 'prepare' else self.case.prepare(project, kind, sources, name)
                        folder = Path(plan['transaction']) if plan else None
                        if phase == 'recover':
                            storage.changes.apply(project, folder)
                            manifest = json.loads((folder / 'manifest.json').read_text())
                            manifest['status'] = 'applying'
                            (folder / 'manifest.json').write_text(json.dumps(manifest))
                        alias = self.control(f, target)
                        before = self.case.helper.identities(project / '.sdlc')
                        records = self.records(folder) if folder else None
                        with ExitStack() as stack:
                            if phase == 'recover':
                                stack.enter_context(self.case.offline(source))
                            seen = stack.enter_context(self.handoff(f, alias.parent, when))
                            with self.assertRaises((OSError, ValueError)):
                                if phase == 'prepare':
                                    self.case.prepare(project, kind, sources, name)
                                else:
                                    getattr(storage.changes, phase)(project, folder)
                        self.assertGreater(seen['replacements'], 0)
                        self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                        if folder:
                            self.assertEqual(self.records(folder), records)
                        else:
                            self.assertFalse((project / '.sdlc/transactions').exists())
                        alias.unlink()
                        if phase == 'recover':
                            with self.case.offline(source):
                                storage.changes.recover(project, folder)
                            self.assertEqual(target.read_bytes(), b'Existing protected data')

    def test_init_handoff_blocks_first_completion_and_offline_resume(self):
        for when in ('resolve', 'open'):
            for phase in ('first', 'dry-run', 'completion', 'pending'):
                with self.subTest(when=when, phase=phase), self.case.helper.fixture() as f:
                    f.init(f.b, '--mode', 'local')
                    target = f.a / '.sdlc/README.md'
                    if phase == 'completion':
                        self.case.helper.init(f)
                        target.unlink()
                    elif phase == 'pending':
                        original = lookup.roles.initializer.publish
                        def interrupted(path, data, old):
                            if path == target:
                                raise OSError('Stop before README')
                            return original(path, data, old)
                        with mock.patch.object(lookup.roles.initializer, 'publish', side_effect=interrupted):
                            with self.assertRaisesRegex(OSError, 'Stop before README'):
                                self.case.helper.init(f)
                    alias = self.control(f, target)
                    before = self.case.helper.identities(f.a)
                    with ExitStack() as stack:
                        if phase == 'pending':
                            stack.enter_context(self.case.offline(f.main / '.sdlc'))
                        seen = stack.enter_context(self.handoff(f, alias.parent, when))
                        with self.assertRaises((OSError, ValueError)):
                            self.case.helper.init(f, dry_run=phase == 'dry-run')
                    self.assertGreater(seen['replacements'], 0)
                    self.assertEqual(self.case.helper.identities(f.a), before)
                    self.assertFalse(target.exists())
                    alias.unlink()
                    if phase == 'pending':
                        with self.case.offline(f.main / '.sdlc'):
                            self.case.helper.init(f)
                    else:
                        self.case.helper.init(f)
                    self.assertTrue(target.is_file())

    def test_partial_recovery_retains_files_until_handoff_is_repaired(self):
        for kind in ('edit', 'import', 'collect'):
            with self.subTest(kind=kind), self.case.helper.fixture() as f:
                project, source, sources, name, target = self.case.setup_case(f, kind, existing=True)
                second = target.with_name('second.md')
                second.write_bytes(b'Existing second file')
                names = [name, str(Path(name).with_name(second.name))]
                if source:
                    (source / names[1]).write_bytes(b'Second candidate')
                plan = storage.changes.prepare(project, kind, sources, ['001-one'] if kind != 'edit' else [], names if kind == 'edit' else [])
                folder = Path(plan['transaction'])
                Path(plan['proposal']).write_text(json.dumps({n: {'action': 'replace', 'text': 'Candidate-' + str(i)} for i,n in enumerate(names)}))
                original = storage.changes.publish_data
                def interrupted(path, data, old):
                    if path == second:
                        raise OSError('Stop second publication')
                    return original(path, data, old)
                with mock.patch.object(storage.changes, 'publish_data', side_effect=interrupted), \
                        mock.patch.object(storage.changes, 'rollback', side_effect=OSError('Stop rollback')):
                    with self.assertRaisesRegex(OSError, 'Stop second publication'):
                        storage.changes.apply(project, folder)
                alias = self.control(f, target)
                before, records = self.case.helper.identities(project / '.sdlc'), self.records(folder)
                with self.case.offline(source), self.handoff(f, alias.parent, 'resolve'):
                    with self.assertRaises((OSError, ValueError)):
                        storage.changes.recover(project, folder)
                self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                self.assertEqual(self.records(folder), records)
                alias.unlink()
                with self.case.offline(source):
                    storage.changes.recover(project, folder)
                self.assertEqual(target.read_bytes(), b'Existing protected data')
                self.assertEqual(second.read_bytes(), b'Existing second file')

    def test_first_init_rejects_an_empty_replacement_source_subtree(self):
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run), self.case.helper.fixture() as f:
                source = f.main / '.sdlc'
                before = self.case.helper.identities(source)
                with self.empty_source(f, source) as seen:
                    with self.assertRaises((OSError, ValueError)):
                        self.case.helper.init(f, dry_run=dry_run)
                self.assertGreater(seen['replacements'], 0)
                self.assertFalse((f.a / '.sdlc').exists())
                self.assertEqual(self.case.helper.identities(source), before)

    def test_copy_prepare_and_apply_reject_empty_source_subtree(self):
        for kind in ('import', 'collect'):
            for phase in ('prepare', 'apply'):
                with self.subTest(kind=kind, phase=phase), self.case.helper.fixture() as f:
                    f.init(f.a, '--mode', 'local')
                    project, source = (f.a, f.main / '.sdlc') if kind == 'import' else (f.main, f.a / '.sdlc')
                    sources = [] if kind == 'import' else [source]
                    name = 'memory/long-term.md'
                    (source / name).write_bytes(b'Changed source fact')
                    plan = None if phase == 'prepare' else storage.changes.prepare(project, kind, sources, [], [])
                    folder = Path(plan['transaction']) if plan else None
                    if plan:
                        Path(plan['proposal']).write_text(json.dumps({name: {'action': 'copy', 'source': str(source)}}))
                    before, original = self.case.helper.identities(project / '.sdlc'), self.case.helper.identities(source)
                    records = self.records(folder) if folder else None
                    with self.empty_source(f, source) as seen:
                        with self.assertRaises((OSError, ValueError)):
                            if phase == 'prepare':
                                storage.changes.prepare(project, kind, sources, [], [])
                            else:
                                storage.changes.apply(project, folder)
                    self.assertGreater(seen['replacements'], 0)
                    self.assertEqual(self.case.helper.identities(project / '.sdlc'), before)
                    self.assertEqual(self.case.helper.identities(source), original)
                    if folder:
                        self.assertEqual(self.records(folder), records)

    def test_genuine_empty_source_subtree_and_scoped_edits_remain_valid(self):
        with self.case.helper.fixture() as f:
            f.init(f.a, '--mode', 'local')
            source = f.main / '.sdlc'
            for path in (source / 'memory').iterdir():
                path.unlink()
            self.assertFalse(any(n.startswith('memory/') for n in storage.changes.source_snapshot(source)))
            plan = storage.changes.prepare(f.a, 'import', [], [], [])
            self.assertEqual(plan['files'], [])
            self.assertEqual(storage.changes.apply(f.a, Path(plan['transaction']))['written'], [])
            with self.empty_source(f, source) as seen:
                plan = self.case.prepare(f.a, 'edit', [], 'memory/long-term.md')
                storage.changes.apply(f.a, Path(plan['transaction']))
            self.assertEqual(seen['replacements'], 0)


if __name__ == '__main__':
    unittest.main()
