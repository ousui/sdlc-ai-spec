"""Equivalent logical store addresses keep their effective store and selection."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

try:
    from tests import test_storage as fixture
except ImportError:
    import test_storage as fixture


class RelativeStorePathTests(unittest.TestCase):
    setUp = fixture.StorageTests.setUp
    git = fixture.StorageTests.git
    runpy = fixture.StorageTests.runpy
    init = fixture.StorageTests.init
    binding = fixture.StorageTests.binding
    feature = fixture.StorageTests.feature

    def shell(self, script, value=None, *args, project=None, no_persist=False):
        env = dict(self.env)
        if value is not None:
            env['SDLC_FEATURE_DIRECTORY'] = value
        if no_persist:
            env['SDLC_FEATURE_NO_PERSIST'] = '1'
        options = ['--feature', value] if script == 'project-paths.sh' else ['--json']
        result = subprocess.run(['bash', str(fixture.PACKAGE / 'scripts/bash' / script),
                                 *options, *args], cwd=project or self.a, env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def check_shared_spellings(self):
        feature = self.feature(self.main)
        (self.a / 'nested').mkdir()
        (self.a / 'self').symlink_to(self.a, target_is_directory=True)
        own = Path(self.binding(self.a)['FEATURE_JSON'])
        for prefix in ('.sdlc', './.sdlc', 'nested/../.sdlc', 'self/.sdlc',
                       './self//.sdlc', 'self/nested/../.sdlc'):
            for suffix in ('/.', '//'):
                with self.subTest(prefix=prefix, suffix=suffix):
                    value = prefix + '/specs/001-one' + suffix
                    paths = self.shell('project-paths.sh', value)
                    self.assertEqual(Path(paths['FEATURE_DIR']).resolve(), feature)
                    result = self.shell('setup-plan.sh', value)
                    self.assertEqual(Path(result['FEATURE_DIR']).resolve(), feature)
                    self.assertEqual(result['BRANCH'], '.' if suffix == '/.' else '')
                    self.assertTrue((feature / 'plan.md').is_file())
                    self.assertFalse((self.a / '.sdlc').exists())
                    before = own.read_bytes(), own.stat().st_mtime_ns
                    self.shell('check-prerequisites.sh', value)
                    followup = self.shell('check-prerequisites.sh', None, '--paths-only')
                    self.assertEqual(Path(followup['FEATURE_DIR']).resolve(), feature)
                    self.assertEqual((own.read_bytes(), own.stat().st_mtime_ns), before)
                    status = self.runpy('project_status.py', project=self.a)
                    self.assertEqual(Path(status['selection']['resolved_path']), feature)

    def test_shared_equivalent_relative_paths_preserve_store_and_noop_selection(self):
        self.check_shared_spellings()

    def test_designated_authority_uses_same_relative_mapping(self):
        authority = self.base / 'authority'
        (self.main / '.sdlc').rename(authority)
        self.runpy('sdlc_store.py', 'register', '--authority', str(authority))
        marker = fixture.files(self.main / '.sdlc')
        self.check_shared_spellings()
        self.assertEqual(fixture.files(self.main / '.sdlc'), marker)

    def test_explicit_relative_alias_ignores_unused_selection_and_respects_no_persist(self):
        feature = self.feature(self.main)
        (feature / 'plan.md').write_text('Existing plan\n')
        (self.a / 'self').symlink_to(self.a, target_is_directory=True)
        own = Path(self.binding(self.a)['FEATURE_JSON'])
        own.parent.mkdir(parents=True)
        own.write_text('{invalid\n')
        before = own.read_bytes(), own.stat().st_mtime_ns
        value = 'self/.sdlc/specs/001-one/.'
        self.shell('check-prerequisites.sh', value, no_persist=True)
        self.assertEqual((own.read_bytes(), own.stat().st_mtime_ns), before)
        self.shell('check-prerequisites.sh', value)
        self.assertEqual(json.loads(own.read_text())['feature_directory'], value)
        self.assertEqual(Path(self.shell('check-prerequisites.sh')['FEATURE_DIR']).resolve(), feature)
        self.assertFalse((self.a / '.sdlc').exists())

    def test_local_relative_alias_and_external_feature_keep_original_scope(self):
        self.init(self.a, '--mode', 'local')
        local = self.feature(self.a)
        (self.a / 'self').symlink_to(self.a, target_is_directory=True)
        (self.a / 'main-alias').symlink_to(self.main, target_is_directory=True)
        before = fixture.files(self.main / '.sdlc')
        result = self.shell('setup-plan.sh', 'self/.sdlc/specs/001-one/.')
        self.assertEqual(Path(result['FEATURE_DIR']).resolve(), local)
        self.runpy('sdlc_store.py', 'feature', '--value', 'main-alias/.sdlc/specs/001-one/.',
                   '--persist', project=self.a, ok=False)
        external = self.base / 'external'
        external.mkdir()
        (self.a / 'external').symlink_to(external, target_is_directory=True)
        result = self.shell('setup-plan.sh', 'external/.')
        self.assertEqual(Path(result['FEATURE_DIR']).resolve(), external)
        self.assertEqual(fixture.files(self.main / '.sdlc'), before)

    def test_missing_or_file_prefix_does_not_create_independent_store(self):
        self.feature(self.main)
        (self.a / 'file').write_text('not a directory')
        before = fixture.files(self.main / '.sdlc')
        for prefix in ('missing/../', 'file/../'):
            for absolute in (False, True):
                value = (str(self.a) + '/' if absolute else '') + prefix + '.sdlc/specs/001-one/.'
                with self.subTest(value=value):
                    result = subprocess.run(['bash', str(fixture.PACKAGE / 'scripts/bash/setup-plan.sh'), '--json'],
                        cwd=self.a, env=dict(self.env, SDLC_FEATURE_DIRECTORY=value),
                        capture_output=True, text=True, timeout=30)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse((self.a / '.sdlc').exists())
                    self.assertFalse((self.a / 'missing').exists())
                    self.assertEqual(fixture.files(self.main / '.sdlc'), before)


if __name__ == '__main__':
    unittest.main()
