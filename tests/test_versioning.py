"""Product version is machine-owned, generated consistently, and absent from evergreen docs."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_VERSION = re.compile(r'(?<![0-9A-Za-z])\d+\.\d+\.\d+-(?:sdlc\.[1-9][0-9]*|alpha|beta)\b')


class VersioningTests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads((ROOT / 'upstream.lock.json').read_text())
        self.meta = json.loads((ROOT / 'plugin-metadata.json').read_text())
        self.version = self.meta['version']

    def test_product_version_aligns_with_locked_upstream(self):
        match = re.fullmatch(re.escape(str(self.lock['version'])) + r'-sdlc\.([1-9][0-9]*)', self.version)
        self.assertIsNotNone(match)
        self.revision = int(match[1])
        self.assertGreaterEqual(self.revision, 1)

    def test_changelog_first_released_version_matches_machine_version(self):
        text = (ROOT / 'CHANGELOG.md').read_text()
        self.assertIn('## Unreleased', text)
        releases = re.findall(r'^## (\d+\.\d+\.\d+-sdlc\.[1-9][0-9]*) — ', text, re.M)
        self.assertTrue(releases)
        self.assertEqual(releases[0], self.version)

    def test_generated_versions_match_machine_version(self):
        build = json.loads((ROOT / 'dist/BUILD.json').read_text())
        upstream = json.loads((ROOT / 'dist/UPSTREAM.json').read_text())
        self.assertEqual(build['product_version'], self.version)
        self.assertEqual(upstream['port_version'], self.version)
        self.assertEqual(build['upstream_version'], self.lock['version'])
        self.assertEqual(upstream['version'], self.lock['version'])
        for name in ('.claude-plugin/marketplace.json', '.cursor-plugin/marketplace.json'):
            data = json.loads((ROOT / name).read_text())
            self.assertEqual(data['metadata']['version'], self.version)
            self.assertEqual(data['plugins'][0]['version'], self.version)

    def test_evergreen_documents_do_not_embed_product_release_numbers(self):
        paths = [ROOT/'README.md', ROOT/'AGENTS.md']
        paths += list((ROOT/'docs').rglob('*.md')) + list((ROOT/'docs').rglob('*.html'))
        paths += list((ROOT/'maintenance').rglob('*.md')) + list((ROOT/'maintenance').rglob('*.html'))
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIsNone(PRODUCT_VERSION.search(path.read_text(encoding='utf-8')))

    def test_current_product_version_occurs_only_in_version_sources_and_generated_outputs(self):
        allowed = {
            'plugin-metadata.json', 'CHANGELOG.md',
            '.claude-plugin/marketplace.json', '.cursor-plugin/marketplace.json',
        }
        unexpected = []
        for path in ROOT.rglob('*'):
            if not path.is_file() or '.git' in path.parts or '.venv' in path.parts or '__pycache__' in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith('dist/') or relative in allowed:
                continue
            try:
                text = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            if self.version in text:
                unexpected.append(relative)
        self.assertEqual(unexpected, [])

    def test_changelog_is_part_of_reproducible_build_identity(self):
        inputs = json.loads((ROOT / 'dist/BUILD.json').read_text())['inputs']
        self.assertIn('CHANGELOG.md', inputs)

    def test_version_tool_check_is_read_only_and_passes(self):
        before = {p: p.read_bytes() for p in (
            ROOT/'plugin-metadata.json', ROOT/'CHANGELOG.md', ROOT/'dist/BUILD.json',
            ROOT/'.claude-plugin/marketplace.json', ROOT/'.cursor-plugin/marketplace.json')}
        result = subprocess.run([str(ROOT/'tools/version-tool.sh'), '--check'], cwd=ROOT,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), self.version)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_version_tool_shell_syntax(self):
        subprocess.run(['bash', '-n', str(ROOT/'tools/version-tool.sh')], check=True)


if __name__ == '__main__':
    unittest.main()
