"""Machine-contract and read-only localization precheck regressions.

These tests protect maintenance-time localization validation. They do not change
or claim to validate arbitrary model semantics in the 11 distributed Skills.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import localize


class MachineContractTests(unittest.TestCase):
    def assert_contract_rejects(self, source: str, translated: str) -> None:
        with self.assertRaises(localize.LocalizationError):
            localize.validate_translation_contract('fixture', source, translated)

    def test_current_reviewed_commands_and_presentations_still_pass(self):
        for name in localize.COMMANDS:
            with self.subTest(command=name):
                localize.validate_translation_contract(
                    name,
                    localize.canonical_source(name),
                    (localize.LOCALES / 'workflows' / f'{name}.md').read_text(),
                )
        for name in (*localize.TEMPLATES, 'requirements'):
            with self.subTest(presentation=name):
                localize.validate_presentation_contract(
                    name, localize.presentation_source(name),
                    localize.presentation_file(name).read_text())

    def test_inline_machine_status_change_is_rejected_without_freezing_prose(self):
        source = 'Use `PASS` when complete and run `--json` against `spec.md`.\n'
        translated = '完成时使用 `PASS`，并对 `spec.md` 运行 `--json`。\n'
        localize.validate_translation_contract('fixture', source, translated)
        self.assert_contract_rejects(source, translated.replace('`PASS`', '`FAIL`'))

    def test_shell_exit_code_change_is_rejected(self):
        source = '```sh\nexit 1\n```\n'
        translated = '```sh\nexit 0\n```\n'
        self.assert_contract_rejects(source, translated)

    def test_json_boolean_and_key_association_changes_are_rejected(self):
        source = '```json\n{"enabled": true, "required": false}\n```\n'
        swapped = '```json\n{"enabled": false, "required": true}\n```\n'
        self.assert_contract_rejects(source, swapped)
        source_plain = 'State: {"enabled": true, "required": false}\n'
        swapped_plain = '状态：{"enabled": false, "required": true}\n'
        self.assert_contract_rejects(source_plain, swapped_plain)

    def test_table_value_swap_is_rejected_even_with_same_global_counts(self):
        source = ('| file | status |\n| --- | --- |\n'
                  '| a.md | PASS |\n| b.md | FAIL |\n')
        translated = ('| 文件 | 状态 |\n| --- | --- |\n'
                      '| a.md | FAIL |\n| b.md | PASS |\n')
        self.assert_contract_rejects(source, translated)

    def test_translated_pseudo_bash_task_prose_remains_allowed(self):
        source = ('```bash\n# Launch model\n'
                  'Task: "Create [Entity] in src/models/entity.py"\n```\n')
        translated = ('```bash\n# 启动模型\n'
                      'Task: "在 src/models/entity.py 中创建 [Entity]"\n```\n')
        localize.validate_translation_contract('fixture', source, translated)

    def test_actual_shell_command_in_bash_fence_remains_exact(self):
        source = '```bash\ngit rev-parse --git-dir 2>/dev/null\n```\n'
        translated = '```bash\ngit status --short 2>/dev/null\n```\n'
        self.assert_contract_rejects(source, translated)

    def test_unclosed_fence_fails_closed(self):
        with self.assertRaisesRegex(localize.LocalizationError, 'Unclosed Markdown fence'):
            localize.machine_contract('```sh\nexit 1\n')


class LocalizationPrecheckTests(unittest.TestCase):
    def test_precheck_all_current_items_is_read_only(self):
        catalog = localize.LOCALES / 'catalog.json'
        before = catalog.read_bytes()
        for name in localize.COMMANDS:
            self.assertEqual(localize.precheck_review(name)['status'], 'PASS')
        for name in (*localize.TEMPLATES, 'requirements'):
            self.assertEqual(localize.precheck_review(name, is_presentation=True)['status'], 'PASS')
        for name in localize.RESOURCES:
            self.assertEqual(localize.precheck_review(name, is_resource=True)['status'], 'PASS')
        self.assertEqual(before, catalog.read_bytes())

    def test_source_equivalent_resource_machine_drift_is_rejected(self):
        name = 'binding'
        text = (localize.LOCALES / f'{name}.md').read_text()
        bad = text.replace('--feature', '--force', 1)
        self.assertNotEqual(text, bad)
        with tempfile.TemporaryDirectory() as temp:
            copy_root = Path(temp) / 'zh'; shutil.copytree(localize.LOCALES, copy_root)
            (copy_root / f'{name}.md').write_text(bad)
            with patch.object(localize, 'LOCALES', copy_root):
                with self.assertRaisesRegex(localize.LocalizationError, 'Resource machine/structure'):
                    localize.precheck_review(name, is_resource=True)

    def test_local_policy_resource_critical_clause_drift_is_rejected(self):
        for name, old, new in (
            ('status', '参考入口只提供建议和事实依据，不执行。', '参考入口可以自动执行。'),
            ('output-language', '不得为了翻译新增写入或重写其他已有内容。', '可以为了翻译新增写入。'),
        ):
            with self.subTest(resource=name), tempfile.TemporaryDirectory() as temp:
                copy_root = Path(temp) / 'zh'; shutil.copytree(localize.LOCALES, copy_root)
                file = copy_root / f'{name}.md'; text = file.read_text()
                self.assertEqual(text.count(old), 1); file.write_text(text.replace(old, new, 1))
                with patch.object(localize, 'LOCALES', copy_root):
                    with self.assertRaisesRegex(localize.LocalizationError, 'Critical localized resource clause'):
                        localize.precheck_review(name, is_resource=True)

    def test_resource_record_refuses_contract_drift_without_updating_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            copy_root = Path(temp) / 'zh'; shutil.copytree(localize.LOCALES, copy_root)
            file = copy_root / 'output-language.md'
            file.write_text(file.read_text().replace(
                '机器契约保持原样', '机器契约可以按翻译需要修改', 1))
            before = (copy_root / 'catalog.json').read_bytes()
            with patch.object(localize, 'LOCALES', copy_root):
                with self.assertRaises(localize.LocalizationError):
                    localize.record_review('output-language', 'fixture review', is_resource=True)
            self.assertEqual(before, (copy_root / 'catalog.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
