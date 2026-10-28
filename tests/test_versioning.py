"""Product version is machine-owned, generated consistently, and absent from evergreen docs."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
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

    def version_fixture(self, root: Path):
        for directory in ('tools', 'dist/nested', '.agents/plugins', '.claude-plugin', '.cursor-plugin', 'tmp'):
            (root/directory).mkdir(parents=True, exist_ok=True)
        script = root/'tools/version-tool.sh'
        shutil.copy2(ROOT/'tools/version-tool.sh', script)
        (root/'upstream.lock.json').write_text(json.dumps({'version': self.lock['version']}))
        (root/'plugin-metadata.json').write_text(json.dumps({'version': self.version}) + '\n')
        (root/'CHANGELOG.md').write_text(
            '## Unreleased\n\n- 测试版本记录。\n\n'
            f'## {self.version} — 2026-01-01\n\n- 旧版本。\n')
        for name in ('dist/BUILD.json', 'dist/nested/content', '.agents/plugins/marketplace.json',
                     '.claude-plugin/marketplace.json', '.cursor-plugin/marketplace.json'):
            (root/name).write_text('original ' + name + '\n')
        return script

    def test_version_tool_restores_backup_and_stops_after_build_failure(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-version-failure-') as temp:
            root = Path(temp)
            script = self.version_fixture(root)
            mock_bin = root/'bin'
            mock_bin.mkdir()
            uv = mock_bin/'uv'
            uv.write_text('#!/bin/sh\nexit 42\n')
            uv.chmod(0o755)
            tracked = [root/'plugin-metadata.json', root/'CHANGELOG.md',
                       *[p for directory in ('dist', '.agents', '.claude-plugin', '.cursor-plugin')
                         for p in (root/directory).rglob('*') if p.is_file()]]
            before = {p: p.read_bytes() for p in tracked}
            env = dict(os.environ, PATH=str(mock_bin) + os.pathsep + os.environ['PATH'], TMPDIR=str(root/'tmp'))
            revision = int(self.version.rsplit('.', 1)[1]) + 1
            result = subprocess.run([str(script), f'sdlc.{revision}'], cwd=root,
                                    env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 42, result.stderr)
            self.assertIn('touched version/build files were restored', result.stderr)
            self.assertNotIn('Version ready:', result.stdout)
            self.assertEqual(before, {p: p.read_bytes() for p in tracked})
            self.assertEqual(list((root/'tmp').iterdir()), [])

    def test_version_tool_backup_failure_does_not_remove_original_distribution(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-version-backup-') as temp:
            root = Path(temp)
            script = self.version_fixture(root)
            (root/'.cursor-plugin/marketplace.json').unlink()
            tracked = [root/'plugin-metadata.json', root/'CHANGELOG.md',
                       *[p for p in (root/'dist').rglob('*') if p.is_file()]]
            before = {p: p.read_bytes() for p in tracked}
            revision = int(self.version.rsplit('.', 1)[1]) + 1
            result = subprocess.run([str(script), f'sdlc.{revision}'], cwd=root,
                                    env=dict(os.environ, TMPDIR=str(root/'tmp')),
                                    text=True, capture_output=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, {p: p.read_bytes() for p in tracked})
            self.assertEqual(list((root/'tmp').iterdir()), [])

    def test_version_tool_keeps_backup_when_restore_fails(self):
        with tempfile.TemporaryDirectory(prefix='sdlc-version-restore-') as temp:
            root = Path(temp)
            script = self.version_fixture(root)
            original_metadata = (root/'plugin-metadata.json').read_bytes()
            mock_bin = root/'bin'
            mock_bin.mkdir()
            uv = mock_bin/'uv'
            uv.write_text('#!/bin/sh\nexit 42\n')
            uv.chmod(0o755)
            cp = mock_bin/'cp'
            cp.write_text('#!/bin/sh\ncase "$2:$3" in '
                          '*/sdlc-version.*/plugin-metadata.json:plugin-metadata.json) exit 11;; '
                          'esac\nexec /bin/cp "$@"\n')
            cp.chmod(0o755)
            env = dict(os.environ, PATH=str(mock_bin) + os.pathsep + os.environ['PATH'], TMPDIR=str(root/'tmp'))
            revision = int(self.version.rsplit('.', 1)[1]) + 1
            result = subprocess.run([str(script), f'sdlc.{revision}'], cwd=root,
                                    env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 42, result.stderr)
            self.assertIn('restore incomplete, backup retained at', result.stderr)
            self.assertNotIn('Version ready:', result.stdout)
            backups = list((root/'tmp').iterdir())
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0]/'plugin-metadata.json').read_bytes(), original_metadata)
            self.assertEqual((root/'dist/nested/content').read_text(), 'original dist/nested/content\n')


if __name__ == '__main__':
    unittest.main()
