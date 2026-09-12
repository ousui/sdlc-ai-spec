"""Path normalization tests for cross-platform engineering differentials."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from differential import normalize_project_paths


class DifferentialPathTests(unittest.TestCase):
    def test_logical_and_physical_project_paths_normalize_identically(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            physical=root/'physical-project'
            physical.mkdir()
            logical=root/'logical-project'
            logical.symlink_to(physical,target_is_directory=True)

            logical_text=str(logical/'specs/001-fixture')
            physical_text=str(logical.resolve()/'specs/001-fixture')
            self.assertEqual(normalize_project_paths(logical_text,logical),'<PROJECT>/specs/001-fixture')
            self.assertEqual(normalize_project_paths(physical_text,logical),'<PROJECT>/specs/001-fixture')

    def test_same_prefix_unrelated_path_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp)/'project'
            project.mkdir()
            text=str(project)+'-backup/file'
            self.assertEqual(normalize_project_paths(text,project),text)
            quoted='path="'+str(project)+'" next='+str(project/'spec.md')
            self.assertEqual(normalize_project_paths(quoted,project),'path="<PROJECT>" next=<PROJECT>/spec.md')

    def test_unrelated_paths_are_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp)/'project'
            project.mkdir()
            self.assertEqual(normalize_project_paths('/tmp/another-project/file',project),'/tmp/another-project/file')


if __name__=='__main__':
    unittest.main()
