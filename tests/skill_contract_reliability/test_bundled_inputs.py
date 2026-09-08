"""Contract projections plus an installed-copy request, not model benchmarking."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from tools import generate_input_reference as docs

ROOT = Path(__file__).resolve().parents[2]

class BundledInputTests(unittest.TestCase):
    def test_input_12_generated_tables_match_actual_runtime_constants(self):
        generated = docs.render(ROOT)
        self.assertEqual(5, len(generated))
        for relative, expected in generated.items():
            with self.subTest(path=relative):
                self.assertEqual(expected, (ROOT/relative).read_text(encoding='utf-8'))
                self.assertIn('input-reference.md', (ROOT/relative).with_name('contract.md').read_text())

    def test_input_12_enum_change_is_detected_as_bundled_document_drift(self):
        with tempfile.TemporaryDirectory(prefix='scr-doc-drift-') as directory:
            root = Path(directory)
            for skill, (filename, _) in docs.SOURCES.items():
                target = root/'skills'/skill/'scripts'/filename
                target.parent.mkdir(parents=True)
                shutil.copyfile(ROOT/'skills'/skill/'scripts'/filename, target)
            original = docs.render(root)
            path = root/'skills/sdlc-000-ctx/scripts/runtime.py'
            text = path.read_text().replace('"bulid": "build"', '"builld": "build"')
            path.write_text(text)
            self.assertNotEqual(original, docs.render(root))

    def test_input_12_generator_does_not_execute_arbitrary_runtime_expressions(self):
        import ast
        with self.assertRaises((ValueError, TypeError)):
            docs.literal(ast.parse("__import__('os').getcwd()", mode='eval').body)

    def test_input_12_installed_complete_example_uses_real_digest_and_never_writes(self):
        with tempfile.TemporaryDirectory(prefix='scr-installed-') as directory:
            root = Path(directory)
            installed, project = root/'plugin', root/'project'
            project.mkdir()
            for name in ('skills', 'packages', 'scripts'):
                shutil.copytree(ROOT/name, installed/name,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'AGENTS.md'))
            self.assertFalse((installed/'docs').exists())
            self.assertFalse((installed/'tests').exists())
            request = json.loads((installed/'skills/sdlc-000-ctx/references/input-example.json').read_text())
            request['project_root'] = str(project)
            member = request['inputs']['supporting_members'][0]
            self.assertEqual(request['inputs']['evidence'][0]['integrity_or_digest'],
                             'sha256:' + hashlib.sha256(member['content'].encode('utf-8')).hexdigest())
            result = subprocess.run([sys.executable, '-B', str(installed/'skills/sdlc-000-ctx/scripts/runtime.py')],
                                    input=json.dumps(request), capture_output=True, text=True, cwd=project, timeout=15)
            self.assertEqual(0, result.returncode, result.stdout+result.stderr)
            body = json.loads(result.stdout)
            self.assertTrue(body['ok'], body)
            self.assertIsNone(body['artifact'])
            self.assertEqual({'result': 'pending', 'failed_checks': []}, body['gate'])
            self.assertEqual([], body['errors'])
            self.assertEqual([], list(project.iterdir()))
            # A paired bad input is rejected by the same installed formal entry.
            request['inputs']['context']['resources'][0]['type'] = 'source_worktree'
            result = subprocess.run([sys.executable, '-B', str(installed/'skills/sdlc-000-ctx/scripts/runtime.py')],
                                    input=json.dumps(request), capture_output=True, text=True, cwd=project, timeout=15)
            self.assertEqual(1, result.returncode)
            self.assertFalse(json.loads(result.stdout)['ok'])
            self.assertEqual([], list(project.iterdir()))

    def test_input_11_vfy_malformed_collections_fail_before_authority_resolution(self):
        for field, invalid in [('method_ids', 'VFM-001'), ('manual_observations', []), ('failure_returns', True),
                               ('confirmation', 'approved')]:
            with tempfile.TemporaryDirectory(prefix='scr-vfy-shape-') as directory:
                output = subprocess.run([sys.executable, '-B', str(ROOT/'skills/sdlc-500-vfy/scripts/runtime.py'),
                                         'create', '--output', 'json'], input=json.dumps({field: invalid}),
                                        text=True, capture_output=True, cwd=directory, timeout=10)
                self.assertEqual(2, output.returncode, output.stdout)
                body = json.loads(output.stdout)
                self.assertEqual('VFY_CONTRACT_INVALID', body['errors'][0]['code'])
                self.assertIn(field, body['errors'][0]['message'])
                self.assertEqual([], list(Path(directory).iterdir()))
