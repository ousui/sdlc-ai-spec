"""Automatic collection sources must still belong to the registered Git worktree."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

try:
    from tests import test_storage as fixture
except ImportError:
    import test_storage as fixture


class SourceIdentityTests(unittest.TestCase):
    # Reuse the disposable fixture helpers without inheriting its test methods.
    setUp = fixture.StorageTests.setUp
    git = fixture.StorageTests.git
    runpy = fixture.StorageTests.runpy
    init = fixture.StorageTests.init
    binding = fixture.StorageTests.binding
    prepare = fixture.StorageTests.prepare
    apply = fixture.StorageTests.apply

    def make_foreign(self, workspace):
        (workspace / '.git').unlink()
        self.git('init', '-q', str(workspace), cwd=self.base)
        # The main repository still has this address, even without a prunable flag.
        listing = self.git('worktree', 'list', '--porcelain').stdout
        self.assertIn('worktree ' + str(workspace) + '\n', listing)

    def choose_source(self, plan, source):
        proposal = Path(plan['proposal'])
        choices = json.loads(proposal.read_text())
        for name in choices:
            choices[name] = {'action': 'copy', 'source': str(source)}
        proposal.write_text(json.dumps(choices))

    def test_foreign_repository_at_stale_worktree_address_is_not_automatic_source(self):
        self.make_foreign(self.a)
        self.init(self.a)
        source = self.a / '.sdlc'
        (source / 'memory/long-term.md').write_text('Foreign project knowledge\n')
        before = fixture.files(self.main / '.sdlc')
        self.assertFalse((self.main / '.sdlc/store.json').exists())
        self.assertNotIn(str(source), self.binding(self.main)['sources'])
        self.runpy('store_changes.py', 'prepare', '--kind', 'collect',
                   '--source', str(source), ok=False)
        self.assertEqual(fixture.files(self.main / '.sdlc'), before)

    def test_relative_git_worktree_registration_remains_valid(self):
        workspace = self.base / 'relative worktree'
        result = subprocess.run(['git', 'worktree', 'add', '--relative-paths', '-q',
                                 '-b', 'relative', str(workspace)], cwd=self.main,
                                env=self.env, capture_output=True, text=True)
        if result.returncode and "unknown option `relative-paths'" in result.stderr:
            self.skipTest('Installed Git does not support relative worktree registration')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.init(workspace, '--mode', 'local')
        source = workspace / '.sdlc'
        self.assertIn(str(source), self.binding(self.main)['sources'])
        text = 'Knowledge from relative Git registration\n'
        (source / 'memory/long-term.md').write_text(text)
        plan = self.prepare(sources=[source])
        self.choose_source(plan, source)
        self.assertEqual(self.apply(plan)['status'], 'applied')
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), text)

    def test_source_repository_identity_is_rechecked_at_apply_with_identical_bytes(self):
        self.init(self.a, '--mode', 'local')
        source = self.a / '.sdlc'
        (source / 'memory/long-term.md').write_text('Selected source knowledge\n')
        plan = self.prepare(sources=[source])
        self.choose_source(plan, source)
        before = fixture.files(self.main / '.sdlc')
        source_before = fixture.files(source)
        self.make_foreign(self.a)
        self.assertEqual(fixture.files(source), source_before)
        self.apply(plan, ok=False)
        self.assertEqual(fixture.files(self.main / '.sdlc'), before)
        self.assertEqual(fixture.files(source), source_before)

    def test_worktree_git_pointer_must_match_its_registered_backlink(self):
        self.init(self.a, '--mode', 'local')
        self.init(self.b, '--mode', 'local')
        source = self.a / '.sdlc'
        (source / 'memory/long-term.md').write_text('Selected source knowledge\n')
        plan = self.prepare(sources=[source])
        self.choose_source(plan, source)
        before = fixture.files(self.main / '.sdlc')
        # Both addresses still report the same common directory, and Git reports
        # a as the toplevel even when its pointer actually uses b's Git directory.
        (self.a / '.git').write_bytes((self.b / '.git').read_bytes())
        self.assertEqual(self.git('rev-parse', '--show-toplevel', cwd=self.a).stdout.strip(), str(self.a))
        self.assertEqual(self.git('rev-parse', '--git-common-dir', cwd=self.a).stdout,
                         self.git('rev-parse', '--git-common-dir', cwd=self.b).stdout)
        self.assertNotIn(str(source), self.binding(self.main)['sources'])
        self.assertIn(str(self.b / '.sdlc'), self.binding(self.main)['sources'])
        self.runpy('store_changes.py', 'prepare', '--kind', 'collect',
                   '--source', str(source), ok=False)
        self.apply(plan, ok=False)
        self.assertEqual(fixture.files(self.main / '.sdlc'), before)

    def test_explicit_registration_allows_foreign_source_at_stale_address(self):
        self.make_foreign(self.a)
        self.init(self.a)
        source = self.a / '.sdlc'
        text = 'Explicitly selected external project knowledge\n'
        (source / 'memory/long-term.md').write_text(text)
        self.runpy('sdlc_store.py', 'register', '--source', str(source))
        self.assertIn(str(source), self.binding(self.main)['sources'])
        source_before = fixture.files(source)
        plan = self.prepare(sources=[source])
        self.choose_source(plan, source)
        self.assertEqual(self.apply(plan)['status'], 'applied')
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), text)
        self.assertEqual(fixture.files(source), source_before)

    def test_nested_repository_is_not_the_same_project_at_corresponding_module_path(self):
        for workspace in (self.main, self.a, self.b):
            (workspace / 'module').mkdir()
        main = self.main / 'module'
        foreign = self.a / 'module'
        valid = self.b / 'module'
        self.init(main)
        self.init(foreign, '--mode', 'local')
        self.init(valid, '--mode', 'local')
        self.git('init', '-q', str(foreign), cwd=self.base)
        sources = self.binding(main)['sources']
        self.assertNotIn(str(foreign / '.sdlc'), sources)
        self.assertIn(str(valid / '.sdlc'), sources)
        self.runpy('store_changes.py', 'prepare', '--kind', 'collect',
                   '--source', str(foreign / '.sdlc'), project=main, ok=False)
        self.prepare(project=main, sources=[valid / '.sdlc'])

    def test_valid_worktree_source_is_still_discovered_and_collected(self):
        self.init(self.a, '--mode', 'local')
        source = self.a / '.sdlc'
        text = 'Same project worktree knowledge\n'
        (source / 'memory/long-term.md').write_text(text)
        before = fixture.files(source)
        self.assertIn(str(source), self.binding(self.main)['sources'])
        plan = self.prepare(sources=[source])
        self.choose_source(plan, source)
        self.assertEqual(self.apply(plan)['status'], 'applied')
        self.assertEqual((self.main / '.sdlc/memory/long-term.md').read_text(), text)
        self.assertEqual(fixture.files(source), before)


if __name__ == '__main__':
    unittest.main()
