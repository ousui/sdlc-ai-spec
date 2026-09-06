"""Test-owned temporary roots may contain OS aliases; runtime links stay denied.

No nested suite is run: these cases exercise fixture construction and explicit
compiler/filesystem behavior. All original test IDs and negative cases remain.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from packages.sdlc_github.models import GithubError
from packages.sdlc_runtime.local_paths import directory
from tests.skill_github import test_offline


class FixturePathTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve(strict=True)
        self.physical = self.root / 'physical'
        self.physical.mkdir()
        self.alias = self.root / 'temporary-parent-alias'
        self.alias.symlink_to(self.physical, target_is_directory=True)

    def test_service_fixture_normalizes_its_owned_temporary_parent(self):
        original = tempfile.TemporaryDirectory
        allocated = []

        def allocate():
            value = original(dir=self.alias)
            allocated.append(Path(value.name))
            return value

        case = test_offline.RuntimeTests()
        with patch.object(test_offline.tempfile, 'TemporaryDirectory', side_effect=allocate):
            case.setUp()
        self.addCleanup(case.tearDown)
        self.assertEqual(len(allocated), 1)
        self.assertTrue(allocated[0].is_relative_to(self.alias))
        self.assertEqual(case.root, allocated[0].resolve(strict=True))
        self.assertTrue(case.root.is_relative_to(self.physical))
        with directory(case.root, ()) as fd:
            self.assertEqual(os.fstat(fd).st_ino, allocated[0].stat().st_ino)
        with self.assertRaises(OSError):
            with directory(allocated[0], ()):
                pass

    def test_body_file_canonical_parent_works_but_raw_alias_and_leaf_link_do_not(self):
        with tempfile.TemporaryDirectory(dir=self.alias) as value:
            logical = Path(value)
            physical = logical.resolve(strict=True)
            file = physical / 'body'
            file.write_text('test-owned explicit body')
            args = ['issue-create', '--repo', 'example/project', '--title', 'test',
                    '--expected-actor-id', '101', '--body-file']
            output = test_offline.COMPILER.compile_invocation([*args, str(file)])
            self.assertEqual(output['arguments']['body'], 'test-owned explicit body')
            with self.assertRaises(GithubError):
                test_offline.COMPILER.compile_invocation([*args, str(logical / 'body')])
            linked = physical / 'linked-body'
            linked.symlink_to(file)
            with self.assertRaises(GithubError):
                test_offline.COMPILER.compile_invocation([*args, str(linked)])

    def test_canonical_fixture_root_does_not_allow_a_linked_state_namespace(self):
        with tempfile.TemporaryDirectory(dir=self.alias) as value:
            physical = Path(value).resolve(strict=True)
            outside = self.root / 'outside'
            outside.mkdir(mode=0o700)
            (physical / '.local').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError):
                with directory(physical, ('.local', 'github'), create=True):
                    pass
            self.assertEqual(list(outside.iterdir()), [])
