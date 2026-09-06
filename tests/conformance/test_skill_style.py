"""Style regression checks reject missing sections and invented CLI semantics."""
import unittest
from tools.validate_skill_style import ROOT, validate, validate_text


class SkillStyleTests(unittest.TestCase):
    def setUp(self):
        self.skill = 'sdlc-600-rls'
        self.text = (ROOT/'skills'/self.skill/'SKILL.md').read_text()

    def test_all_eight_documents_follow_the_same_format(self):
        self.assertEqual(8, len(validate()['skills']))

    def test_missing_section_rejected(self):
        with self.assertRaises(ValueError): validate_text(ROOT, self.skill, self.text.replace('## 参数', '## 参数说明'))

    def test_invented_command_rejected(self):
        with self.assertRaises(ValueError): validate_text(ROOT, self.skill, self.text.replace('| `execute` |', '| `deploy` |'))

    def test_write_permission_must_match_machine_contract(self):
        with self.assertRaises(ValueError): validate_text(ROOT, self.skill, self.text.replace('是，须满足本阶段授权', '否', 1))

    def test_parameter_alias_drift_rejected(self):
        with self.assertRaises(ValueError): validate_text(ROOT, self.skill, self.text.replace('| `--input` | `-i` |', '| `--input` | `-x` |'))

    def test_broken_bundled_link_rejected(self):
        with self.assertRaises(ValueError): validate_text(ROOT, self.skill, self.text.replace('(references/contract.md)', '(references/missing.md)'))

    def test_implicit_invocation_change_rejected(self):
        with self.assertRaises(ValueError): validate_text(ROOT, self.skill, self.text.replace('disable-model-invocation: true', 'disable-model-invocation: false'))

    def test_duplicate_or_reordered_section_rejected(self):
        with self.assertRaises(ValueError): validate_text(ROOT, self.skill, self.text+'\n## 参数\n')

    def test_oversized_ui_description_rejected(self):
        from pathlib import Path
        from unittest.mock import patch
        original = Path.read_text
        target = ROOT / 'skills' / self.skill / 'agents/openai.yaml'
        def read(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path == target:
                import re
                value = re.sub(r'short_description:.*', 'short_description: "' + 'x' * 65 + '"', value)
            return value
        with patch.object(Path, 'read_text', new=read), self.assertRaisesRegex(ValueError, '25–64'):
            validate_text(ROOT, self.skill, self.text)
