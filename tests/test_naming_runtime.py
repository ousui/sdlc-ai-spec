"""End-to-end naming contracts on generated files and disposable projects only."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from naming import audit_package, identifiers, invocation, skill_id, template_references
from naming_check import EXPECTED
from render import command_refs, HOSTS
from verify import normalize
from build import binding
from localize import english_body


class NamingRuntimeTests(unittest.TestCase):
    def test_exact_public_inventory_and_no_stale_paths(self):
        wanted = set(EXPECTED.values())
        package = ROOT / 'dist'
        for host in HOSTS:
            path = package / 'adapters' / host / 'skills'
            self.assertEqual({p.name for p in path.iterdir()}, {'sdlc-000-init'})
            self.assertEqual({p.name for p in (package/'skills').iterdir()}, wanted-{'sdlc-000-init'})
            self.assertEqual(set(json.loads((package / 'bindings' / (host + '.json')).read_text())), wanted)
        self.assertEqual({p.stem for p in (package / 'references/workflows').glob('*.md')}, wanted)
        self.assertNotIn('sdlc-status', wanted)
        spec = importlib.util.spec_from_file_location('naming_loader', package / 'scripts/python/load_workflow.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.assertEqual(set(mod.SKILLS), wanted)
        with self.assertRaises(ValueError): mod.load(package, 'codex', 'specify')
        with self.assertRaises(ValueError): mod.load(package, 'codex', 'sdlc-status')

    def test_source_map_matches_independent_approved_inventory(self):
        for source, target in EXPECTED.items():
            self.assertEqual(skill_id(source), target)
            self.assertEqual(invocation(source, 'codex'), '$' + target)
            self.assertEqual(invocation(source, 'claude'), '/sdlc-ai-spec:' + target)
            self.assertEqual(invocation(source, 'cursor'), '/' + target)
        with self.assertRaises(ValueError): skill_id('new-upstream-stage')
        with self.assertRaises(ValueError): invocation('plan', 'guess')

    def test_new_upstream_placeholders_fail_closed(self):
        for source in ('UNREVIEWED', 'SPECIFY_EXTRA', 'TASKSTOISSUES'):
            text = '__SPECKIT_COMMAND_' + source + '__'
            with self.assertRaises(ValueError): template_references(text)
            with self.assertRaises(ValueError): command_refs(text, 'codex')
        with self.assertRaises(ValueError): identifiers('SPECIFY_UNKNOWN=value')
        self.assertEqual(identifiers('OTHER_SPECIFY_INIT_DIR=value'), 'OTHER_SPECIFY_INIT_DIR=value')

    def test_product_scan_has_only_documented_provenance_exceptions(self):
        audit_package(ROOT / 'dist')
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / 'dist'; shutil.copytree(ROOT / 'dist', package)
            path = package / 'references/workflows/sdlc-100-spec.md'
            original = path.read_text()
            for addition in ('\nRun sdlc-specify now\n', '\nSPECIFY_UNREVIEWED=1\n'):
                path.write_text(original + addition)
                with self.assertRaises(ValueError): audit_package(package)

    def test_compatibility_exception_is_not_a_whole_script_exclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / 'dist'; shutil.copytree(ROOT / 'dist', package)
            path = package / 'scripts/python/init_project.py'
            path.write_text(path.read_text() + '\n# run specify to bypass the initializer\n')
            with self.assertRaises(ValueError): audit_package(package)

    def test_inverse_comparison_does_not_hide_business_or_unknown_name_changes(self):
        for host in HOSTS:
            proc = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'dist/scripts/python/load_workflow.py'),
                '--host', host, '--skill', 'sdlc-310-xchk'], capture_output=True, text=True, check=True, timeout=10)
            full = '\n' + binding(host) + english_body('analyze', host)
            normal = normalize(full, host, ported=True)
            self.assertNotEqual(normal, normalize(full.replace('STRICTLY READ-ONLY', 'WRITES ALLOWED'), host, ported=True))
            self.assertNotEqual(normal, normalize(full + '\nUNAPPROVED BUSINESS RULE\n', host, ported=True))
            self.assertNotEqual(normal, normalize(full + '\n/sdlc-900-fake\n', host, ported=True))

    def test_all_diagnostic_commands_resolve_to_an_installed_skill(self):
        common = ROOT / 'dist/scripts/bash/common.sh'
        for host in HOSTS:
            for source, target in EXPECTED.items():
                result = subprocess.run(['bash', '-c', 'source "$1"; format_sdlc_command "$2"',
                    'naming-test', str(common), target], env=dict(os.environ, SDLC_HOST=host),
                    capture_output=True, text=True, check=True, timeout=5)
                self.assertEqual(result.stdout.strip(), invocation(source, host))
        result = subprocess.run(['bash', '-c', 'source "$1"; format_sdlc_command "$2"',
            'naming-test', str(common), 'sdlc-900-fake'], capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)

    def test_unrelated_legacy_prefix_preserves_explicit_project_selection(self):
        # Upstream ignores unrelated SPECIFY_* names. The documented SDLC
        # override still determines the selected project after the rename.
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / 'project'
            (project / '.sdlc').mkdir(parents=True)
            env = dict(os.environ, SDLC_INIT_DIR=str(project), SPECIFY_UNRELATED='1')
            result = subprocess.run(
                ['bash', '-c', 'source "$1"; get_repo_root', 'fixture',
                 str(root / 'dist/scripts/bash/common.sh')],
                cwd=project, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()).resolve(), project.resolve())


    def test_new_project_readme_names_and_repeat_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            args = [sys.executable, '-I', '-B', str(ROOT / 'dist/scripts/python/init_project.py'),
                    '--project', temp, '--json']
            subprocess.run(args, capture_output=True, check=True, timeout=10)
            path = project / '.sdlc/README.md'; text = path.read_text()
            self.assertIn('SDLC AI SPEC', text)
            self.assertIn('sdlc-010-rule', text); self.assertIn('sdlc-100-spec', text)
            path.write_text('Historical user text: sdlc-specify\n')
            before = path.read_bytes(), path.stat().st_mtime_ns
            subprocess.run(args, capture_output=True, check=True, timeout=10)
            self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))

    def test_build_identity_includes_the_naming_contract(self):
        import hashlib
        data = json.loads((ROOT / 'dist/BUILD.json').read_text())
        expected = hashlib.sha256((ROOT / 'docs/naming-map.json').read_bytes()).hexdigest()
        self.assertEqual(data['inputs']['docs/naming-map.json'], expected)
