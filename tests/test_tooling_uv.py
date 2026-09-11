"""Development tooling uses uv while the installed dist runtime stays uv-independent."""
from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class UvToolingTests(unittest.TestCase):
    def test_pyproject_is_virtual_dev_tooling_not_product_metadata(self):
        data = tomllib.loads((ROOT / 'pyproject.toml').read_text())
        self.assertEqual(data['project']['name'], 'sdlc-ai-spec-tooling')
        self.assertEqual(data['project']['version'], '0.0.0')
        self.assertEqual(data['project']['dependencies'], [])
        self.assertEqual(data['project']['requires-python'], '>=3.11,<3.16')
        self.assertEqual(set(data['dependency-groups']['dev']), {
            'jsonschema==4.26.0', 'pyyaml==6.0.3',
        })
        self.assertFalse(data['tool']['uv']['package'])
        self.assertEqual(data['tool']['uv']['required-version'], '>=0.12.13,<0.13')
        self.assertEqual((ROOT / '.python-version').read_text(), '3.12\n')
        self.assertEqual(json.loads((ROOT / 'plugin-metadata.json').read_text())['version'], '1.0.0-beta')

    def test_lockfile_contains_exact_accepted_tool_versions(self):
        lock = (ROOT / 'uv.lock').read_text()
        self.assertIn('name = "sdlc-ai-spec-tooling"', lock)
        for name, version in {
            'jsonschema': '4.26.0', 'pyyaml': '6.0.3', 'attrs': '26.1.0',
            'jsonschema-specifications': '2025.9.1', 'referencing': '0.37.0',
            'rpds-py': '2026.6.3', 'typing-extensions': '4.16.0',
        }.items():
            self.assertRegex(lock, rf'name = "{name}"\nversion = "{version}"')

    def test_requirements_txt_is_not_a_second_dependency_source(self):
        self.assertFalse((ROOT / 'tools/requirements.txt').exists())
        for doc in (ROOT / 'README.md', ROOT / 'AGENTS.md', ROOT / 'docs/DEVELOPMENT.md', ROOT / 'docs/UPGRADING.md'):
            text = doc.read_text()
            self.assertNotIn('pip install -r tools/requirements.txt', text)
            self.assertNotIn('python -m venv .venv', text)

    def test_ci_uses_pinned_uv_and_locked_project(self):
        ci = yaml.safe_load((ROOT / '.github/workflows/engineering.yml').read_text())
        self.assertEqual(ci['permissions'], {'contents': 'read'})
        steps = ci['jobs']['engineering']['steps']
        action = next(step for step in steps if step.get('name') == 'Install pinned uv and Python')
        self.assertEqual(action['uses'], 'astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d')
        self.assertEqual(action['with']['version'], '0.12.13')
        self.assertEqual(action['with']['python-version'], '3.12')
        text = (ROOT / '.github/workflows/engineering.yml').read_text()
        for required in ('uv sync --locked', 'uv run --locked python', 'uv venv', 'uv pip install'):
            self.assertIn(required, text)
        for forbidden in ('python3 -m venv', ' -m pip install', 'tools/requirements.txt'):
            self.assertNotIn(forbidden, text)

    def test_dist_does_not_ship_uv_project_or_virtual_environment(self):
        package = ROOT / 'dist'
        for path in ('pyproject.toml', 'uv.lock', '.python-version', '.venv', 'tools/requirements.txt'):
            self.assertFalse((package / path).exists(), path)
        readme = (package / 'README.md').read_text()
        self.assertIn('No install-time build, uv, upstream CLI or network is required.', readme)
        self.assertIn('Runtime requires Bash, Python 3.9+ and standard POSIX tools.', readme)

    def test_build_identity_tracks_uv_reproducibility_inputs(self):
        data = json.loads((ROOT / 'dist/BUILD.json').read_text())
        inputs = data['inputs']
        for path in ('pyproject.toml', 'uv.lock', '.python-version'):
            self.assertIn(path, inputs)
        self.assertNotIn('tools/requirements.txt', inputs)


if __name__ == '__main__':
    unittest.main()
