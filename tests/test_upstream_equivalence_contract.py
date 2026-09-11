"""Negative/positive controls for local-only behavioral deviations.

These tests do not repair or redefine upstream business behavior.
"""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from naming import product_prose


class UpstreamEquivalenceContractTests(unittest.TestCase):
    def test_event_keys_are_protocol_not_branding(self):
        source = 'hooks.before_specify hooks.after_specify'
        self.assertEqual(product_prose(source), source)

    def test_unrelated_legacy_environment_does_not_reject(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / 'project'
            (project / '.sdlc').mkdir(parents=True)
            result = subprocess.run(
                ['bash', '-c', 'source "$1"; get_repo_root', 'fixture',
                 str(ROOT / 'dist/scripts/bash/common.sh')], cwd=project,
                env=dict(os.environ, SDLC_INIT_DIR=str(project), SPECIFY_UNRELATED='1'),
                text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()).resolve(), project.resolve())

    def test_external_state_alias_remains_a_valid_input(self):
        spec = importlib.util.spec_from_file_location('guard_equivalence', ROOT / 'src/scripts/python/path_guard.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            plugin, project, state = base/'plugin', base/'project', base/'state'
            for path in (plugin, project, state): path.mkdir()
            (project/'.sdlc').symlink_to(state, target_is_directory=True)
            result = module.validate(plugin, project)
            self.assertEqual(Path(result['PROJECT_ROOT']), project.resolve())

    def test_alias_into_shared_plugin_is_still_rejected(self):
        spec = importlib.util.spec_from_file_location('guard_equivalence', ROOT / 'src/scripts/python/path_guard.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            plugin, project = base/'plugin', base/'project'
            plugin.mkdir(); project.mkdir()
            (project/'.sdlc').symlink_to(plugin, target_is_directory=True)
            with self.assertRaises(ValueError): module.validate(plugin, project)
