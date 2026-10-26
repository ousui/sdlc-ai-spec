"""Equivalent Git registrations and source addresses retain one verified identity."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import unicodedata
import unittest

try:
    from tests import test_storage as storage
except ImportError:
    import test_storage as storage


class SourcePathTests(unittest.TestCase):
    def setUp(self):
        self.f = storage.StorageTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        probe = self.f.base / 'caf\u00e9'
        probe.write_text('probe')
        insensitive = (self.f.base / 'CAFE\u0301').exists()
        probe.unlink()
        if not insensitive:
            self.skipTest('Requires case-insensitive and normalization-insensitive lookup')

    def alias(self, path):
        return path.with_name(unicodedata.normalize('NFD', path.name.upper()))

    def choose(self, plan, source):
        path = Path(plan['proposal'])
        proposal = json.loads(path.read_text())
        for name in proposal:
            proposal[name] = {'action': 'copy', 'source': str(source)}
        path.write_text(json.dumps(proposal))

    def registered_alias(self):
        parent = self.f.base / 'caf\u00e9-holder'
        parent.mkdir()
        raw = self.alias(parent) / 'linked'
        actual = parent / 'linked'
        self.f.git('worktree', 'add', '-q', '-b', 'alias-source', str(raw))
        self.f.init(actual, '--mode', 'local')
        return actual, raw

    def test_equivalent_git_registration_is_discovered_and_collected(self):
        actual, raw = self.registered_alias()
        source = actual / '.sdlc'
        self.assertEqual(self.f.binding(actual), self.f.binding(raw))
        self.assertIn(str(source), self.f.binding(self.f.main)['sources'])
        (source / 'memory/long-term.md').write_text('alias registration knowledge')
        plan = self.f.prepare(sources=[raw / '.sdlc'])
        self.choose(plan, source)
        self.f.apply(plan)
        self.assertEqual((self.f.main / '.sdlc/memory/long-term.md').read_text(), 'alias registration knowledge')

    def test_equivalent_git_directory_common_directory_and_backlink_remain_verified(self):
        self.f.init(self.f.a, '--mode', 'local')
        gitdir = Path(self.f.git('rev-parse', '--absolute-git-dir', cwd=self.f.a).stdout.strip())
        (self.f.a / '.git').write_text('gitdir: ' + str(self.alias(gitdir)) + '\n')
        (gitdir / 'commondir').write_text(str(self.f.main / '.GIT') + '\n')
        (gitdir / 'gitdir').write_text(str(self.alias(self.f.a) / '.git') + '\n')
        source = self.f.a / '.sdlc'
        self.assertIn(str(source), self.f.binding(self.f.main)['sources'])
        self.f.prepare(sources=[self.alias(self.f.a) / '.sdlc'])

    def test_equivalent_gitfile_backlink_is_discovered_collected_and_rechecked(self):
        self.f.init(self.f.a, '--mode', 'local')
        gitdir = Path(self.f.git('rev-parse', '--absolute-git-dir', cwd=self.f.a).stdout.strip())
        for relative in (False, True):
            with self.subTest(relative=relative):
                backlink = self.alias(self.f.a) / '.GIT'
                value = os.path.relpath(backlink, gitdir) if relative else str(backlink)
                (gitdir / 'gitdir').write_text(value + '\n')
                source = self.f.a / '.sdlc'
                self.assertIn(str(source), self.f.binding(self.f.main)['sources'])
                self.assertEqual(self.f.binding(self.f.a)['mode'], 'local')
                (source / 'memory/long-term.md').write_text('backlink ' + str(relative))
                plan = self.f.prepare(sources=[self.alias(self.f.a) / '.SDLC'])
                self.choose(plan, source)
                self.f.apply(plan)
                self.assertEqual((self.f.main / '.sdlc/memory/long-term.md').read_text(), 'backlink ' + str(relative))
                again = self.f.prepare(sources=[source])
                self.assertEqual(again['files'], [])
                self.assertEqual(self.f.apply(again)['written'], [])
        (source / 'memory/long-term.md').write_text('new update')
        plan = self.f.prepare(sources=[source])
        self.choose(plan, source)
        (gitdir / 'gitdir').write_text(str(self.f.b / '.GIT') + '\n')
        before = storage.files(self.f.main / '.sdlc')
        self.f.apply(plan, ok=False)
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)

    def test_equivalent_backlink_does_not_grant_worktree_collection(self):
        self.f.init(self.f.a, '--mode', 'local')
        gitdir = Path(self.f.git('rev-parse', '--absolute-git-dir', cwd=self.f.a).stdout.strip())
        (gitdir / 'gitdir').write_text(str(self.f.a / '.GIT') + '\n')
        before = storage.files(self.f.main / '.sdlc')
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source', str(self.f.a / '.sdlc'),
                     project=self.f.main, cwd=self.f.a, ok=False)
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)

    def test_equivalent_backlink_preserves_shared_selection_and_prepared_edit_noop(self):
        self.f.feature(self.f.main)
        value = '.sdlc/specs/001-one/.'
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.f.b)
        binding = self.f.binding(self.f.b)
        pointer = Path(binding['FEATURE_JSON'])
        before = pointer.read_bytes(), pointer.stat().st_mtime_ns
        main_selection = self.f.main / '.sdlc/feature.json'
        main_selection.write_text('{invalid main selection')
        plan = self.f.prepare(self.f.b, kind='edit', paths=['memory/long-term.md'])
        self.f.replace(plan, 'memory/long-term.md', 'shared edit')
        gitdir = Path(self.f.git('rev-parse', '--absolute-git-dir', cwd=self.f.b).stdout.strip())
        (gitdir / 'gitdir').write_text(str(self.alias(self.f.b) / '.GIT') + '\n')
        self.assertEqual(self.f.binding(self.f.b), binding)
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.alias(self.f.b))
        self.assertEqual((pointer.read_bytes(), pointer.stat().st_mtime_ns), before)
        self.f.apply(plan, self.f.b)
        self.assertEqual((self.f.main / '.sdlc/memory/long-term.md').read_text(), 'shared edit')
        self.assertEqual(main_selection.read_text(), '{invalid main selection')
        self.assertFalse((self.f.b / '.sdlc').exists())

    def test_corresponding_subprojects_and_shared_selection_use_physical_directories(self):
        main, local, shared = self.f.main / 'module', self.f.a / 'MODULE', self.f.b / 'Module'
        for project in (main, local, shared):
            project.mkdir()
        self.f.init(main)
        self.f.init(local, '--mode', 'local')
        (local / '.sdlc/memory/long-term.md').write_text('module knowledge')
        self.assertIn(str(local / '.sdlc'), self.f.binding(main)['sources'])
        plan = self.f.prepare(main, sources=[local / '.sdlc'])
        self.choose(plan, local / '.sdlc')
        self.f.apply(plan, main)
        normal = self.f.binding(shared)
        self.assertEqual(normal['MAIN_PROJECT_ROOT'], str(main))
        self.assertEqual(normal, self.f.binding(self.alias(shared)))
        value = '.sdlc/specs/001-one/.'
        self.f.feature(main)
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=shared)
        pointer = Path(normal['FEATURE_JSON'])
        before = pointer.read_bytes(), pointer.stat().st_mtime_ns
        self.f.runpy('sdlc_store.py', 'feature', '--value', value, '--persist', project=self.alias(shared))
        self.assertEqual((pointer.read_bytes(), pointer.stat().st_mtime_ns), before)
        self.assertFalse((shared / '.sdlc').exists())

    def test_multiple_equivalent_source_arguments_deduplicate_and_keep_noop(self):
        self.f.init(self.f.a, '--mode', 'local')
        source = self.f.a / '.sdlc'
        target = self.f.main / '.sdlc/memory/long-term.md'
        before = target.read_bytes(), target.stat().st_mtime_ns
        plan = self.f.prepare(sources=[source, self.alias(self.f.a) / '.SDLC'])
        manifest = json.loads((Path(plan['transaction']) / 'manifest.json').read_text())
        self.assertEqual(list(manifest['sources']), [str(source)])
        self.assertEqual(plan['files'], [])
        self.assertEqual(self.f.apply(plan)['written'], [])
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)

    def test_registered_external_source_accepts_equivalent_address_but_not_authority(self):
        source = self.f.base / 'caf\u00e9-source'
        (source / 'memory').mkdir(parents=True)
        (source / 'memory/long-term.md').write_text('registered knowledge')
        self.f.runpy('sdlc_store.py', 'register', '--source', str(source))
        plan = self.f.prepare(sources=[self.alias(source)])
        self.choose(plan, source)
        self.f.apply(plan)
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect',
                     '--source', str(self.alias(self.f.main) / '.SDLC'), ok=False)

    def test_equivalent_stale_registration_and_mismatched_backlink_are_still_rejected(self):
        actual, raw = self.registered_alias()
        source = actual / '.sdlc'
        gitdir = Path(self.f.git('rev-parse', '--absolute-git-dir', cwd=actual).stdout.strip())
        backlink = gitdir / 'gitdir'
        original = backlink.read_bytes()
        backlink.write_text(str(self.f.b / '.git') + '\n')
        self.assertNotIn(str(source), self.f.binding(self.f.main)['sources'])
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source', str(raw / '.sdlc'), ok=False)
        backlink.write_bytes(original)
        plan = self.f.prepare(sources=[source])
        (actual / '.git').unlink()
        self.f.git('init', '-q', str(actual), cwd=self.f.base)
        self.assertNotIn(str(source), self.f.binding(self.f.main)['sources'])
        self.f.apply(plan, ok=False)

    def test_equivalent_registered_worktree_cannot_bypass_local_store_or_collect(self):
        actual, raw = self.registered_alias()
        before = storage.files(self.f.main / '.sdlc')
        self.f.runpy('sdlc_store.py', 'resolve', project=self.alias(self.f.main), cwd=raw, ok=False)
        self.f.runpy('store_changes.py', 'prepare', '--kind', 'collect', '--source', str(actual / '.sdlc'),
                     project=self.alias(self.f.main), cwd=raw, ok=False)
        self.assertEqual(storage.files(self.f.main / '.sdlc'), before)

    def test_searchable_worktrees_do_not_require_read_access_for_local_operations(self):
        self.f.init(self.f.a, '--mode', 'local')
        actual, _ = self.registered_alias()
        expected = self.f.binding(self.f.a)
        authority = storage.files(self.f.main / '.sdlc')
        for directories in ((self.f.b,), (self.f.main,), (actual.parent, actual)):
            with self.subTest(directories=[path.name for path in directories]):
                modes = {path: stat.S_IMODE(path.stat().st_mode) for path in directories}
                try:
                    for directory in directories:
                        directory.chmod(0o111)
                        if os.access(directory, os.R_OK):
                            self.skipTest('Directory read permissions are not enforced')
                    binding = self.f.binding(self.alias(self.f.a))
                    # Git may omit a source whose parents it cannot inspect;
                    # that must not change this workspace's effective binding.
                    self.assertEqual({k: v for k, v in binding.items() if k != 'sources'},
                                     {k: v for k, v in expected.items() if k != 'sources'})
                    self.assertTrue(set(binding['sources']) <= set(expected['sources']))
                    plan = self.f.prepare(self.f.a, kind='edit', paths=['memory/long-term.md'])
                    self.f.replace(plan, 'memory/long-term.md', 'Local work with ' + directory.name)
                    self.f.apply(plan, self.f.a)
                    self.assertEqual((self.f.a / '.sdlc/memory/long-term.md').read_text(),
                                     'Local work with ' + directory.name)
                finally:
                    for path, mode in modes.items():
                        path.chmod(mode)
        self.assertEqual(storage.files(self.f.main / '.sdlc'), authority)


if __name__ == '__main__':
    unittest.main()
