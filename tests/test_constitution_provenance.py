"""Constitution generation provenance: creation facts, not phase completion."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'dist'
INIT = PACKAGE / 'scripts/python/init_project.py'
STATUS = PACKAGE / 'scripts/python/project_status.py'

init_spec = importlib.util.spec_from_file_location('provenance_init', INIT)
initializer = importlib.util.module_from_spec(init_spec)
init_spec.loader.exec_module(initializer)
status_spec = importlib.util.spec_from_file_location('provenance_status', STATUS)
status = importlib.util.module_from_spec(status_spec)
status_spec.loader.exec_module(status)

PROVENANCE = '.sdlc/memory/.constitution-template.json'
CONSTITUTION = '.sdlc/memory/constitution.md'


def snapshot(root: Path):
    result = {}
    for path in [root, *sorted(root.rglob('*'))]:
        value = path.lstat()
        result[str(path.relative_to(root))] = (
            stat.S_IMODE(value.st_mode), value.st_mtime_ns,
            path.read_bytes() if path.is_file() and not path.is_symlink()
            else os.readlink(path) if path.is_symlink() else None,
        )
    return result


class ConstitutionProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-provenance-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / 'project'
        self.project.mkdir()

    def run_init(self, *args, package=PACKAGE, project=None, success=True):
        proc = subprocess.run([
            sys.executable, '-I', '-B', str(package / 'scripts/python/init_project.py'),
            '--project', str(project or self.project), '--json', *args,
        ], cwd=self.base, text=True, capture_output=True, timeout=30)
        if success:
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)
        self.assertNotEqual(proc.returncode, 0)
        return proc

    def collect(self, package=PACKAGE, project=None):
        return status.collect_status(package, project=str(project or self.project), environ={})

    def provenance(self, project=None):
        return json.loads(((project or self.project) / PROVENANCE).read_text())

    def test_new_default_constitution_records_exact_generated_bytes(self):
        result = self.run_init()
        content = (self.project / CONSTITUTION).read_bytes()
        record = self.provenance()
        self.assertEqual(record['sha256'], hashlib.sha256(content).hexdigest())
        self.assertEqual(record['source'], 'plugin-template:templates/constitution-template.md')
        self.assertEqual(result['constitution_provenance'], 'recorded')
        self.assertIn(PROVENANCE, result['created'])
        report = self.collect()
        item = report['artifacts'][0]
        self.assertEqual(item['assessment'], 'not_verified')
        self.assertEqual(item['generation']['record_state'], 'valid')
        self.assertEqual(item['generation']['content_relation'], 'matches_baseline')
        self.assertEqual(item['generation']['source'], record['source'])
        self.assertIn(item['placeholder_observation'], ('detected', 'not_detected'))

    def test_project_override_records_override_source_and_exact_bytes(self):
        override = self.project / '.sdlc/templates/overrides/constitution-template.md'
        override.parent.mkdir(parents=True)
        override.write_bytes(b'\xef\xbb\xbf# Team\r\n[PROJECT_NAME]\r\n')
        result = self.run_init()
        content = (self.project / CONSTITUTION).read_bytes()
        self.assertEqual(content, override.read_bytes())
        record = self.provenance()
        self.assertEqual(record['sha256'], hashlib.sha256(content).hexdigest())
        self.assertEqual(record['source'], 'project-override:.sdlc/templates/overrides/constitution-template.md')
        self.assertEqual(result['constitution_provenance'], 'recorded')
        self.assertEqual(self.collect()['artifacts'][0]['generation']['content_relation'], 'matches_baseline')

    def test_repeat_init_preserves_provenance_bytes_and_mtime(self):
        self.run_init()
        before = snapshot(self.project)
        result = self.run_init()
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(result['constitution_provenance'], 'preserved')
        self.assertEqual(before, snapshot(self.project))

    def test_existing_constitution_without_record_is_not_backfilled(self):
        memory = self.project / '.sdlc/memory'
        memory.mkdir(parents=True)
        (memory / 'constitution.md').write_text('# Human governance\n')
        before = (memory / 'constitution.md').read_bytes()
        result = self.run_init()
        self.assertEqual((memory / 'constitution.md').read_bytes(), before)
        self.assertFalse((memory / '.constitution-template.json').exists())
        self.assertEqual(result['constitution_provenance'], 'not_recorded')
        self.assertTrue(any('generation provenance' in item.lower() for item in result['warnings']))
        item = self.collect()['artifacts'][0]
        self.assertEqual(item['generation']['record_state'], 'missing')
        self.assertEqual(item['generation']['content_relation'], 'unknown')

    def test_edit_and_restore_only_change_content_relation_not_assessment(self):
        self.run_init()
        path = self.project / CONSTITUTION
        original = path.read_bytes()
        path.write_bytes(original + b'\nManual edit\n')
        changed = self.collect()['artifacts'][0]
        self.assertEqual(changed['generation']['content_relation'], 'differs_from_baseline')
        self.assertEqual(changed['assessment'], 'not_verified')
        path.write_bytes(original)
        restored = self.collect()['artifacts'][0]
        self.assertEqual(restored['generation']['content_relation'], 'matches_baseline')
        self.assertEqual(restored['assessment'], 'not_verified')

    def test_current_plugin_template_change_does_not_replace_historical_baseline(self):
        copy = self.base / 'plugin-copy'
        shutil.copytree(PACKAGE, copy)
        project = self.base / 'other'; project.mkdir()
        self.run_init(package=copy, project=project)
        (copy / 'templates/constitution-template.md').write_text('# New plugin template\n')
        item = status.collect_status(copy, project=str(project), environ={})['artifacts'][0]
        self.assertEqual(item['generation']['content_relation'], 'matches_baseline')

    def test_invalid_or_duplicate_record_is_observed_not_repaired(self):
        self.run_init()
        record = self.project / PROVENANCE
        for body in ('{', '{"sha256":"' + '0'*64 + '","sha256":"' + '1'*64 + '","source":"x"}',
                     '{"sha256":"bad","source":"x"}', '{"sha256":"'+'0'*64+'","source":""}'):
            with self.subTest(body=body):
                record.write_text(body)
                before = record.read_bytes()
                report = self.collect()
                item = report['artifacts'][0]
                self.assertEqual(item['generation']['record_state'], 'invalid')
                self.assertEqual(item['generation']['content_relation'], 'unknown')
                self.assertEqual(record.read_bytes(), before)
                result = self.run_init()
                self.assertEqual(result['constitution_provenance'], 'unavailable')
                self.assertEqual(record.read_bytes(), before)

    def test_missing_record_is_normal_for_legacy_project_status(self):
        self.run_init()
        (self.project / PROVENANCE).unlink()
        report = self.collect()
        self.assertEqual(report['status'], 'no_active_feature')
        item = report['artifacts'][0]
        self.assertEqual(item['generation']['record_state'], 'missing')
        self.assertEqual(item['generation']['content_relation'], 'unknown')

    def test_orphan_record_is_reported_without_repair(self):
        self.run_init()
        (self.project / CONSTITUTION).unlink()
        before = snapshot(self.project)
        report = self.collect()
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['artifacts'][0]['generation']['content_relation'], 'unknown')
        self.assertTrue(any(item.get('code') == 'constitution_provenance_orphaned' for item in report['warnings']))
        self.assertEqual(before, snapshot(self.project))

    def test_existing_orphan_record_is_not_claimed_as_new_when_constitution_is_completed(self):
        memory = self.project / '.sdlc/memory'; memory.mkdir(parents=True)
        record = memory / '.constitution-template.json'
        record.write_text(json.dumps({'sha256':'0'*64,'source':'legacy-source'}) + '\n')
        before = record.read_bytes()
        result = self.run_init()
        self.assertTrue((memory / 'constitution.md').is_file())
        self.assertEqual(record.read_bytes(), before)
        self.assertEqual(result['constitution_provenance'], 'preserved')
        self.assertTrue(any('pre-existing provenance' in item.lower() for item in result['warnings']))

    def test_provenance_publish_failure_is_nonfatal_and_not_reported_created(self):
        real = initializer.publish
        def fail_record(path, data, expected):
            if path.name == '.constitution-template.json':
                raise OSError('synthetic provenance failure')
            return real(path, data, expected)
        with mock.patch.object(initializer, 'publish', side_effect=fail_record):
            result = initializer.initialize(PACKAGE, self.project)
        self.assertTrue((self.project / CONSTITUTION).is_file())
        self.assertFalse((self.project / PROVENANCE).exists())
        self.assertEqual(result['constitution_provenance'], 'unavailable')
        self.assertNotIn(PROVENANCE, result['created'])
        self.assertTrue(any('provenance' in item.lower() for item in result['warnings']))

    def test_dry_run_plans_record_without_writing(self):
        before = snapshot(self.project)
        result = self.run_init('--dry-run')
        self.assertEqual(result['constitution_provenance'], 'would_record')
        self.assertIn(PROVENANCE, result['created'])
        self.assertFalse((self.project / '.sdlc').exists())
        self.assertEqual(before, snapshot(self.project))

    def test_status_markdown_uses_neutral_generation_language(self):
        self.run_init()
        text = status.markdown(self.collect())
        self.assertIn('与记录的生成内容一致', text)
        self.assertIn('不代表 RULE 已完成或宪法已批准', text)
        self.assertNotIn('未批准的模板', text)
        self.assertNotIn('template_copy_not_ratified', text)

    def test_status_query_is_read_only_with_provenance(self):
        self.run_init()
        before = snapshot(self.project)
        for _ in range(2):
            self.collect()
        self.assertEqual(before, snapshot(self.project))


if __name__ == '__main__':
    unittest.main()
