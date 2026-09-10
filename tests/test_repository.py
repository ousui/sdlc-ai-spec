"""Repository-only regressions for product layout and fixed beta metadata."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOSTS = ('codex', 'claude', 'cursor')
EXPECTED_VERSION = '1.0.0-beta'
EXPECTED_REPOSITORY = 'https://github.com/goedgecloud/sdlc-ai-spec'


class RepositoryTests(unittest.TestCase):
    def test_root_layout_and_no_legacy_entrypoints(self):
        allowed = {
            '.git', '.github', '.gitignore', '.venv', '.pytest_cache',
            'AGENTS.md', 'CLAUDE.md', 'README.md', 'CHANGELOG.md', 'LICENSE',
            'NOTICE', 'plugin-metadata.json', 'upstream.lock.json',
            'src', 'adapters', 'tools', 'tests', 'dist', 'docs',
        }
        self.assertLessEqual({p.name for p in ROOT.iterdir()}, allowed)
        self.assertEqual({p.name for p in (ROOT/'docs').iterdir()},
                         {'DEVELOPMENT.md', 'MIGRATION.md', 'VERIFICATION.md'})
        self.assertEqual({p.name for p in (ROOT/'dist').iterdir()},
                         set(HOSTS) | {'.sdlc-build'})
        self.assertEqual((ROOT/'CLAUDE.md').read_text(), '@AGENTS.md\n')

    def test_single_product_metadata(self):
        metadata = json.loads((ROOT/'plugin-metadata.json').read_text())
        self.assertEqual(metadata['name'], 'sdlc')
        self.assertEqual(metadata['version'], EXPECTED_VERSION)
        self.assertEqual(metadata['author'], {'name': 'Blade'})
        self.assertEqual(metadata['repository'], EXPECTED_REPOSITORY)
        self.assertEqual(metadata['license'], 'MIT')
        builder = (ROOT/'tools/build.py').read_text()
        self.assertIn("ROOT / 'plugin-metadata.json'", builder)
        self.assertNotIn('0.0.0-engineering', builder)

    def test_packages_use_product_metadata(self):
        metadata = json.loads((ROOT/'plugin-metadata.json').read_text())
        for host in HOSTS:
            with self.subTest(host=host):
                package = ROOT/'dist'/host
                name = '.claude-plugin/plugin.json' if host == 'claude' else 'plugin.json'
                manifest = json.loads((package/name).read_text())
                manifest.pop('$schema', None)
                self.assertEqual(manifest, metadata)
                readme = (package/'README.md').read_text()
                self.assertIn('v'+EXPECTED_VERSION, readme)
                self.assertIn('Author: Blade', readme)
                self.assertIn(EXPECTED_REPOSITORY, readme)

    def test_provenance_separates_upstream_and_port(self):
        lock = json.loads((ROOT/'upstream.lock.json').read_text())
        for host in HOSTS:
            with self.subTest(host=host):
                provenance = json.loads((ROOT/'dist'/host/'UPSTREAM.json').read_text())
                self.assertEqual(provenance['repository'], lock['repository'])
                self.assertEqual(provenance['commit'], lock['commit'])
                self.assertEqual(provenance['port_repository'], EXPECTED_REPOSITORY)
                self.assertEqual(provenance['port_version'], EXPECTED_VERSION)
                self.assertEqual(provenance['port_author'], 'Blade')
                self.assertIs(provenance['init_implemented'], False)
                self.assertIs(provenance['native_host_verified'], False)
                self.assertEqual(provenance['included_commands'], lock['commands'])

    def test_license_and_notice_are_bundled(self):
        original = (ROOT/'src/LICENSE').read_bytes()
        self.assertEqual((ROOT/'LICENSE').read_bytes(), original)
        self.assertIn(b'Copyright GitHub, Inc.', original)
        notice = (ROOT/'NOTICE').read_bytes()
        for host in HOSTS:
            self.assertEqual((ROOT/'dist'/host/'LICENSE').read_bytes(), original)
            self.assertEqual((ROOT/'dist'/host/'NOTICE').read_bytes(), notice)

    def test_documentation_links_and_new_tool_paths(self):
        documents = list((ROOT/'docs').glob('*.md')) + [
            ROOT/'README.md', ROOT/'AGENTS.md', ROOT/'CHANGELOG.md']
        for document in documents:
            text = document.read_text()
            self.assertNotIn('v0/', text)
            self.assertNotIn('0.0.0-engineering', text)
            for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', text):
                target = target.split(' "', 1)[0]
                if urlsplit(target).scheme or target.startswith('#'):
                    continue
                path = unquote(target.split('#', 1)[0])
                self.assertTrue((document.parent/path).exists(), (document, target))
        for name in ('build', 'port', 'verify'):
            self.assertIn('tools/'+name+'.py', (ROOT/'docs/DEVELOPMENT.md').read_text())

    def test_ci_uses_root_paths_and_read_only_permissions(self):
        workflows = list((ROOT/'.github/workflows').glob('*.yml'))
        self.assertEqual([p.name for p in workflows], ['engineering.yml'])
        text = workflows[0].read_text()
        workflow = yaml.safe_load(text)
        self.assertEqual(workflow['permissions'], {'contents': 'read'})
        self.assertIn('${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}.git', text)
        self.assertIn('python" -B tools/verify.py', text)
        self.assertIn('for agent in codex claude cursor-agent', text)
        self.assertIn('--events=false', text)
        self.assertNotIn('v0/', text)
        self.assertNotIn('git push', text)
        self.assertNotIn('contents: write', text)
        self.assertIn('sdlc-engineering-${{ github.sha }}', text)


if __name__ == '__main__':
    unittest.main()
