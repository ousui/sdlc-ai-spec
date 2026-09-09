"""Installed-copy public execution and reproducible runtime-only packaging."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_delivery as delivery_fixture
import test_execution as execution_fixture
import test_runtime as runtime_fixture
from tools.build_plugin import build, verify, SKILLS
from tools.validate_skill_style import validate


class InstalledSession(runtime_fixture.Session):
    def __init__(self, root, cli=True):
        super().__init__(root, cli=True)


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-v2-install-')
        self.root = Path(self.temp.name)
        self.package = self.root/'installed'
        self.built = build(self.package)
        self.cli = self.package/'scripts/sdlc.py'

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, *args, input=None):
        return subprocess.run([sys.executable, '-I', '-B', str(self.cli), *args], input=input,
                              capture_output=True, text=True, cwd=self.root)

    def test_package_uses_only_registered_skills_and_no_development_runtime_dependencies(self):
        manifest = verify(self.package)
        self.assertEqual(list(SKILLS), manifest['skills'])
        self.assertFalse(any((self.package/name).exists() for name in ('docs','tests','tools','AGENTS.md','config')))
        self.assertEqual(['sdlc'], sorted(p.name for p in (self.package/'packages').iterdir()))
        self.assertTrue(validate(self.package)['success'])
        for name in ('.codex-plugin','.claude-plugin','.cursor-plugin'):
            self.assertNotIn('mcpServers', json.loads((self.package/name/'plugin.json').read_text()))

    def test_metadata_flags_do_not_open_or_initialize_a_product_store(self):
        missing = self.root/'missing-product'
        version = self.invoke('-r', str(missing), '-V')
        self.assertEqual(0, version.returncode)
        self.assertEqual({'runtime_version': '2.0.0-dev', 'api_version': '2', 'schema_version': 1}, json.loads(version.stdout))
        schema = self.invoke('--contract')
        self.assertEqual('2', json.loads(schema.stdout)['api_version'])
        self.assertEqual(0, self.invoke('-h').returncode)
        self.assertFalse(missing.exists())
        self.assertFalse((self.package/'.sdlc').exists())

    def test_short_request_and_root_parameters_use_installed_cli(self):
        product = self.root/'product'
        product.mkdir()
        request = self.root/'request.json'
        request.write_text(json.dumps({'api_version':'2','command':'workspace.init','payload':{'name':'isolated product'}}))
        result = self.invoke('-r', str(product), '-i', str(request))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])
        self.assertTrue((product/'.sdlc/store.sqlite3').exists())

    def test_repeated_build_preserves_exact_package_and_rejects_tampered_output(self):
        again = build(self.package)
        self.assertEqual(self.built['archive_sha256'], again['archive_sha256'])
        (self.package/'scripts/sdlc.py').write_text('different source')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            build(self.package)

    def test_actual_installed_cli_chain_and_delivery_without_source_docs(self):
        with patch.object(runtime_fixture, 'CLI', self.cli), patch.object(execution_fixture, 'Session', InstalledSession):
            fixture = delivery_fixture.DeliveryTests()
            try:
                fixture.setUp()
                fixture.test_actual_package_readback_and_local_closure()
                archive = InstalledSession(fixture.root).ok('workspace.export', {'change_id': fixture.s.bindings['change_id']})
                self.assertTrue(Path(archive['path']).is_file())
            finally:
                fixture.tearDown()
        self.assertEqual(self.built['package_digest'], verify(self.package)['package_digest'])


if __name__ == '__main__':
    unittest.main()
