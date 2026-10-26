"""Absent main code modules retain default bindings without bypassing Git identity."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import unittest
from unittest import mock

try:
    from tests import test_storage as storage
    from tests import test_storage_authority_init_review as authority_review
except ImportError:
    import test_storage as storage
    import test_storage_authority_init_review as authority_review

snapshot = authority_review.snapshot


def business_snapshot(root):
    return {name: data for name, data in snapshot(root).items() if '.git' not in Path(name).parts}


@contextmanager
def project_cwd(project, env):
    previous = Path.cwd()
    try:
        os.chdir(project)
        with mock.patch.dict(os.environ, env, clear=True):
            yield
    finally:
        os.chdir(previous)


class MissingMainModuleTests(unittest.TestCase):
    setUp = authority_review.AuthorityInitReviewTests.setUp
    command = authority_review.AuthorityInitReviewTests.command
    foreign = authority_review.AuthorityInitReviewTests.foreign
    selected_init = authority_review.AuthorityInitReviewTests.selected_init
    interrupted_import = authority_review.AuthorityInitReviewTests.interrupted_import

    def modules(self, name):
        main, work = self.f.main / name, self.f.a / name
        main.mkdir(parents=True)
        work.mkdir(parents=True)
        self.f.init(main)
        (main / '.sdlc/memory/long-term.md').write_text('Original module knowledge\n')
        self.f.feature(main)
        return main, work

    def test_a_new_worktree_only_module_can_initialize_local_without_creating_main_code(self):
        (self.f.main / 'business.txt').write_text('Main business file\n')
        before = business_snapshot(self.f.main)
        for seed in ('none', 'knowledge'):
            with self.subTest(seed=seed):
                relative = Path('new-' + seed) / 'nested module'
                main, work = self.f.main / relative, self.f.a / relative
                work.mkdir(parents=True)
                flags = ['--mode', 'local', *(['--seed', 'none'] if seed == 'none' else [])]
                preview = self.f.init(work, *flags, '--dry-run')
                self.assertTrue(preview['dry_run'])
                self.assertFalse((work / '.sdlc').exists())
                self.assertEqual(business_snapshot(self.f.main), before)
                result = self.f.init(work, *flags)
                self.assertEqual(result['status'], 'initialized')
                context = self.f.binding(work)
                self.assertEqual(context['mode'], 'local')
                self.assertEqual(context['SDLC_DIR'], str(work / '.sdlc'))
                self.assertEqual(context['AUTHORITY_DIR'], str(main / '.sdlc'))
                self.assertIsNone(context['authority_error'])
                created = self.command(work, 'create-new-feature.sh', '--json', '--short-name', 'local',
                                       'Local module request', explicit=True)
                self.assertEqual(created.returncode, 0, created.stderr)
                self.assertTrue(Path(json.loads(created.stdout)['SPEC_FILE']).is_relative_to(work / '.sdlc'))
                local_before = snapshot(work / '.sdlc')
                self.assertEqual(self.f.init(work, *flags)['status'], 'unchanged')
                self.assertEqual(self.f.init(work)['status'], 'unchanged')
                self.assertEqual(snapshot(work / '.sdlc'), local_before)
                self.assertFalse(main.exists())
                self.assertEqual(business_snapshot(self.f.main), before)

    def test_a_selected_feature_still_requires_source_before_creating_local_store(self):
        work = self.f.a / 'no-source-module'
        work.mkdir()
        before = business_snapshot(self.f.main)
        for preview in (True, False):
            process = self.f.runpy('init_project.py', '--mode', 'local', '--feature', '001-one',
                                  *(['--dry-run'] if preview else []), project=work, ok=False)
            self.assertIn('Selected import requires an available authority', process.stderr)
            self.assertFalse((work / '.sdlc').exists())
            self.assertFalse((self.f.main / work.name).exists())
            self.assertEqual(business_snapshot(self.f.main), before)

    def test_b_pending_resume_offline_uses_saved_bytes_and_preserves_user_files(self):
        for mode in ('auto', 'local'):
            with self.subTest(mode=mode):
                main, work = self.modules('pending-' + mode)
                self.interrupted_import(work)
                state = work / '.sdlc'
                pending = state / '.init-pending.json'
                saved = json.loads(pending.read_text())
                self.assertEqual(saved['authority'], str(main / '.sdlc'))
                user = state / 'memory/constitution.md'
                user.write_bytes(b'User principles after interruption\n')
                user.chmod(0o640)
                user_before = user.read_bytes(), user.stat().st_mode, user.stat().st_mtime_ns
                (main / '.sdlc/memory/long-term.md').write_text('Changed source knowledge\n')
                offline = self.f.base / ('offline-' + main.name)
                main.rename(offline)
                source_before, local_before = snapshot(offline), snapshot(state)
                flags = ['--mode', mode, '--feature', '001-one']
                preview = self.f.init(work, *flags, '--dry-run')
                self.assertTrue(preview['dry_run'])
                self.assertEqual(snapshot(state), local_before)
                with mock.patch.object(storage.changes, 'source_snapshot', side_effect=AssertionError('Source must stay offline')):
                    result = self.selected_init(work, mode=mode)
                self.assertEqual(result['status'], 'completed')
                for name in ('memory/long-term.md', 'specs/001-one/spec.md'):
                    self.assertEqual((state / name).read_bytes(), base64.b64decode(saved['seeds'][name]))
                self.assertEqual((user.read_bytes(), user.stat().st_mode, user.stat().st_mtime_ns), user_before)
                self.assertFalse(pending.exists())
                completed = snapshot(state)
                self.assertEqual(self.f.init(work, *flags)['status'], 'unchanged')
                self.assertEqual(snapshot(state), completed)
                self.assertEqual(snapshot(offline), source_before)
                self.assertFalse(main.exists())

    def test_c_real_partial_import_recovers_local_backups_while_source_module_is_offline(self):
        main, work = self.modules('import-module')
        self.f.init(work, '--mode', 'local', '--seed', 'none')
        state, source = work / '.sdlc', main / '.sdlc'
        names = ('memory/constitution.md', 'memory/long-term.md')
        for name in names:
            (state / name).write_text('Local original ' + name + '\n')
            (source / name).write_text('Source replacement ' + name + '\n')
        originals = {name: (state / name).read_bytes() for name in names}
        plan = self.f.prepare(work, kind='import', sources=[source])
        proposal = Path(plan['proposal'])
        decisions = json.loads(proposal.read_text())
        self.assertTrue(set(names).issubset(decisions))
        proposal.write_text(json.dumps({name: {'action': 'copy', 'source': str(source)} if name in names
                                       else {'action': 'skip'} for name in decisions}))
        real_publish = storage.changes.publish_data
        calls = []
        def publish(path, data, expected):
            calls.append(path)
            if len(calls) == 2:
                raise OSError('Second import publication interrupted')
            return real_publish(path, data, expected)
        with project_cwd(work, self.f.env), \
                mock.patch.object(storage.changes, 'publish_data', publish), \
                mock.patch.object(storage.changes, 'rollback', side_effect=OSError('Immediate rollback interrupted')):
            with self.assertRaisesRegex(OSError, 'Second import publication interrupted'):
                storage.changes.apply(work, Path(plan['transaction']))
        manifest_path = Path(plan['transaction']) / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(len(calls), 2)
        self.assertEqual(manifest['status'], 'applying')
        self.assertEqual(len(manifest['published']), 1)
        self.assertEqual(set(manifest['after']), set(names))
        for name in names:
            self.assertEqual(base64.b64decode(manifest['before'][name]), originals[name])
        first = next(iter(manifest['published']))
        self.assertNotEqual((state / first).read_bytes(), originals[first])
        offline = self.f.base / 'offline-import-module'
        main.rename(offline)
        source_before = snapshot(offline)
        result = self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=work)
        self.assertEqual(result['status'], 'recovered')
        for name in names:
            self.assertEqual((state / name).read_bytes(), originals[name])
        recovered = snapshot(state)
        self.assertEqual(self.f.runpy('store_changes.py', 'recover', '--transaction', plan['transaction'], project=work)['status'], 'already_recovered')
        self.assertEqual(snapshot(state), recovered)
        self.assertEqual(snapshot(offline), source_before)
        self.assertFalse(main.exists())

    def test_missing_descendant_of_foreign_bad_gitfile_file_or_dangling_alias_is_rejected(self):
        for kind in ('foreign', 'bad-gitfile', 'file', 'dangling-alias'):
            with self.subTest(kind=kind):
                parent = self.f.main / kind
                if kind == 'file':
                    parent.write_text('User file\n')
                elif kind == 'dangling-alias':
                    parent.symlink_to(self.f.base / 'unavailable-directory', target_is_directory=True)
                else:
                    parent.mkdir()
                    if kind == 'foreign':
                        self.foreign(parent)
                    else:
                        (parent / '.git').write_text('gitdir: missing-git-directory\n')
                work = self.f.a / kind / 'missing-module'
                work.mkdir(parents=True)
                before = business_snapshot(self.f.main)
                self.f.runpy('init_project.py', '--mode', 'local', '--seed', 'none', project=work, ok=False)
                self.assertFalse((work / '.sdlc').exists())
                self.assertEqual(business_snapshot(self.f.main), before)

    def test_metadata_errors_and_existing_directory_git_failure_never_use_parent_identity(self):
        main, work = self.modules('unverifiable-module')
        for error in (PermissionError(errno.EACCES, 'Denied'), OSError(errno.EIO, 'Metadata unavailable')):
            original = Path.lstat
            def lstat(path, *args, **kwargs):
                if path == main:
                    raise error
                return original(path, *args, **kwargs)
            with self.subTest(error=error.errno), mock.patch.object(Path, 'lstat', lstat):
                with self.assertRaises((OSError, ValueError)):
                    storage.store.resolve(work, missing=True, cwd=work, env={})
        identity = storage.store.git_identity
        def failed(project):
            return None if project == main else identity(project)
        with mock.patch.object(storage.store, 'git_identity', failed):
            with self.assertRaisesRegex(ValueError, 'main project Git identity'):
                storage.store.resolve(work, missing=True, cwd=work, env={})
        self.assertFalse((work / '.sdlc').exists())

    def test_missing_external_authority_registration_does_not_rebind_pending_to_default(self):
        main, work = self.modules('external-module')
        authority = self.f.base / 'external-authority'
        (main / '.sdlc').rename(authority)
        self.f.runpy('sdlc_store.py', 'register', '--authority', str(authority), project=main)
        self.interrupted_import(work)
        before = snapshot(work / '.sdlc')
        main.rename(self.f.base / 'offline-external-module')
        process = self.f.runpy('init_project.py', '--mode', 'local', '--feature', '001-one', project=work, ok=False)
        self.assertIn('different choices or authority', process.stderr)
        self.assertEqual(snapshot(work / '.sdlc'), before)

    def test_missing_main_module_replaced_before_lock_still_stops_initialization(self):
        main, work = self.f.main / 'new-module', self.f.a / 'new-module'
        work.mkdir()
        original = storage.store.write_lock
        hits = []
        @contextmanager
        def changed(target):
            with original(target) as token:
                hits.append(target)
                main.mkdir()
                self.foreign(main)
                yield token
        with mock.patch.object(storage.store, 'write_lock', changed):
            with self.assertRaisesRegex(ValueError, 'Storage binding changed'):
                self.selected_init(work, seed='none', feature=[])
        self.assertEqual(len(hits), 1)
        self.assertFalse((work / '.sdlc').exists())
        self.assertFalse((main / '.sdlc').exists())


if __name__ == '__main__':
    unittest.main()
