"""Finite review regressions, not proof of arbitrary translation semantics.

Use isolated fixtures only. Clauses pin responsibilities in reviewed zh-CN
source AND the full reconstructed host prompts; factored fragments are not
standalone workflows. Alias expectations are deliberately independent of the
mutable localization catalog and require explicit review when changed.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from upgrade import source_digest, frozen_localization_inputs, localization_digest
from naming import invocation, skill_id

STRUCTURAL_ALIASES = {
    'User Scenarios & Testing': '用户场景与测试',
    'User Story': '用户故事',
    'Edge Cases': '边界情况',
    'Requirements': '需求',
    'Functional Requirements': '功能需求',
    'Key Entities': '关键实体',
    'Success Criteria': '成功标准',
    'Measurable Outcomes': '可衡量的结果',
    'Assumptions': '假设',
    'Clarifications': '澄清记录',
    'Session': '会话',
    'Technical Context': '技术上下文',
    'Constitution Check': '宪法检查',
    'Project Structure': '项目结构',
    'Phase': '阶段',
}
INPUT_ALIASES = {
    'accept_recommendation': ['yes', 'recommended', '采用推荐'],
    'accept_suggestion': ['yes', 'suggested', '采用建议'],
    'continue': ['yes', 'proceed', 'continue', '继续'],
    'stop': ['no', 'wait', 'stop', '停止', '等待'],
}
# These clauses belong to the currently reviewed source, not an independent
# lifecycle engine. New upstream wording requires source-aware re-review.
CLAUSES = {
    'implement': (
        '`checklists/requirements.md` 是由 `{{SDLC:SPECIFY}}` 和 `{{SDLC:CLARIFY}}` 维护的内置规格质量清单；`{{SDLC:CHECKLIST}}` 生成的自定义清单，是由评审者负责的需求质量评审产物。',
        '不得修改清单文件或标记。',
        '等待用户回答后再继续。',
        '用户回答 no、wait、stop 或“停止／等待”时，停止执行。',
        '用户回答 yes、proceed、continue 或“继续”时，继续第 3 步。',
    ),
    'checklist': (
        '不检查代码／实现是否匹配规格。',
        '本命令生成或追加清单条目；**不得**把新生成条目标为 `[x]`。',
        '只有评审者明确要求时，Agent 才能协助评估条目。',
        '`checklists/requirements.md` 是独立的内置规格质量清单，由 `{{SDLC:SPECIFY}}` 和 `{{SDLC:CLARIFY}}` 维护；不能将这一例外套用于此处生成的自定义清单。',
    ),
    'converge': (
        '本命令**唯一**的写入，是向 `tasks.md` 追加新的 `## 阶段 N：收敛` 章节。**不得**：',
        '以任何方式修改 `spec.md` 或 `plan.md`。',
        '重写、重新编号、重排或删除任何既有任务，包括之前 Convergence 阶段的任务。',
        '修改、创建或删除任何应用代码；完成追加任务是 `{{SDLC:IMPLEMENT}}` 的职责。',
        '代码已经满足全部要求时，必须保持 `tasks.md` **逐字节不变**',
    ),
}


def assert_clauses(case: unittest.TestCase, name: str, text: str, host: str | None = None) -> None:
    for clause in CLAUSES[name]:
        if host is not None:
            for command in ('specify', 'clarify', 'checklist', 'implement'):
                clause = clause.replace('{{SDLC:' + command.upper() + '}}', invocation(command, host))
        case.assertIn(clause, text, name + ': reviewed responsibility clause changed')


def assert_aliases(case: unittest.TestCase, contract: dict) -> None:
    expected = {en: {'canonical': zh, 'legacy': [en, en + '（' + zh + '）']}
                for en, zh in STRUCTURAL_ALIASES.items()}
    case.assertEqual(contract['structural_aliases'], expected)
    case.assertEqual(contract['input_aliases'], INPUT_ALIASES)
    case.assertEqual(contract['read_compatibility'], [
        'upstream-en', 'legacy-bilingual-zh-CN', 'canonical-zh-CN'])


class DigestNoiseReviewTests(unittest.TestCase):
    def test_finder_files_do_not_change_source_or_frozen_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'code.py').write_text('original\n')
            (root / 'src/locales/zh-CN').mkdir(parents=True)
            (root / 'src/locales/zh-CN/text.md').write_text('正文\n')
            before = (source_digest(root), frozen_localization_inputs(root), localization_digest(root))
            for relative in ('.DS_Store', 'src/.DS_Store', 'src/locales/zh-CN/.DS_Store'):
                path = root / relative
                for contents in (b'Finder metadata', b'changed metadata'):
                    path.write_bytes(contents)
                    path.chmod(0o755)
                    self.assertEqual(before, (source_digest(root), frozen_localization_inputs(root), localization_digest(root)))
                path.unlink()
                self.assertEqual(before, (source_digest(root), frozen_localization_inputs(root), localization_digest(root)))

    def test_real_content_and_executable_modes_remain_protected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / 'code.py'; file.write_text('original\n'); file.chmod(0o644)
            for fn in (source_digest, frozen_localization_inputs):
                before = fn(root)
                file.chmod(0o755); self.assertNotEqual(before, fn(root))
                file.chmod(0o644); self.assertEqual(before, fn(root))
                file.write_text('changed\n'); self.assertNotEqual(before, fn(root))
                file.write_text('original\n')
                near = root / '.DS_Store.backup'; near.write_text('not allowlisted')
                self.assertNotEqual(before, fn(root)); near.unlink()

    def test_finder_named_symlinks_are_not_an_ignore_bypass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'source'; root.mkdir()
            target = Path(temp) / 'outside'; target.write_text('not metadata')
            (root / '.DS_Store').symlink_to(target)
            for fn in (source_digest, frozen_localization_inputs):
                with self.subTest(fn=fn.__name__), self.assertRaisesRegex(ValueError, 'symlink'):
                    fn(root)

    def test_finder_named_directory_does_not_hide_source_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / '.DS_Store').mkdir()
            file = root / '.DS_Store/code.py'; file.write_text('original')
            for fn in (source_digest, frozen_localization_inputs):
                before = fn(root); file.write_text('changed')
                self.assertNotEqual(before, fn(root)); file.write_text('original')

    def test_nested_finder_files_never_enter_distribution_or_build_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base / 'source'
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__', '.pytest_cache'))
            def build(out: Path) -> dict:
                subprocess.run([sys.executable, '-B', str(source / 'tools/build.py'), '--out', str(out)],
                               cwd=source, check=True, capture_output=True, text=True, timeout=60)
                return {p.relative_to(out).as_posix(): (p.read_bytes(), p.stat().st_mode & 0o111)
                        for p in out.rglob('*') if p.is_file()}
            before = build(base / 'clean')
            for relative in ('src/.DS_Store', 'src/scripts/bash/.DS_Store',
                             'src/templates/.DS_Store', 'src/assets/.DS_Store',
                             'src/locales/zh-CN/.DS_Store', 'tools/.DS_Store'):
                (source / relative).write_bytes(b'Finder metadata')
            after = build(base / 'with-noise')
            self.assertFalse(any(Path(name).name == '.DS_Store' for name in after))
            self.assertEqual(before, after)


class LocalizedResponsibilityReviewTests(unittest.TestCase):
    def test_reviewed_source_preserves_critical_responsibilities(self):
        for name in CLAUSES:
            with self.subTest(command=name):
                text = (ROOT / 'src/locales/zh-CN/workflows' / (name + '.md')).read_text()
                assert_clauses(self, name, text)

    def test_all_three_full_loaded_prompts_preserve_critical_responsibilities(self):
        script = ROOT / 'dist/scripts/python/load_workflow.py'
        spec = importlib.util.spec_from_file_location('review_loader', script)
        loader = importlib.util.module_from_spec(spec); spec.loader.exec_module(loader)
        for host in ('codex', 'claude', 'cursor'):
            for name in CLAUSES:
                with self.subTest(host=host, command=name):
                    assert_clauses(self, name, loader.load(ROOT / 'dist', host, skill_id(name)), host)

    def test_responsibility_inversion_is_detected_even_when_tokens_are_unchanged(self):
        from localize import machine_contract
        mutations = {
            'implement': ('维护的内置规格质量清单', '维护的自定义实现验收清单'),
            'checklist': ('**不得**把新生成条目标为', '**必须**把新生成条目标为'),
            'converge': ('**逐字节不变**', '**重新写入**'),
        }
        for name, (old, new) in mutations.items():
            with self.subTest(command=name):
                text = (ROOT / 'src/locales/zh-CN/workflows' / (name + '.md')).read_text()
                self.assertEqual(text.count(old), 1)
                bad = text.replace(old, new, 1)
                self.assertEqual(machine_contract(text), machine_contract(bad))
                with self.assertRaises(AssertionError):
                    assert_clauses(self, name, bad)

    def test_reviewed_aliases_preserve_all_english_and_chinese_inputs(self):
        contract = json.loads((ROOT / 'src/locales/zh-CN/catalog.json').read_text())['contract']
        assert_aliases(self, contract)

    def test_alias_addition_removal_and_meaning_change_require_explicit_review(self):
        original = json.loads((ROOT / 'src/locales/zh-CN/catalog.json').read_text())['contract']
        variants = []
        new = copy.deepcopy(original); new['input_aliases']['continue'].append('自动批准'); variants.append(new)
        new = copy.deepcopy(original); new['input_aliases']['stop'].remove('no'); variants.append(new)
        new = copy.deepcopy(original); new['structural_aliases']['Clarifications']['canonical'] = '验收通过'; variants.append(new)
        new = copy.deepcopy(original); new['structural_aliases']['Unknown'] = {'canonical': '未知', 'legacy': ['Unknown']}; variants.append(new)
        for index, new in enumerate(variants):
            with self.subTest(mutation=index), self.assertRaises(AssertionError):
                assert_aliases(self, new)


if __name__ == '__main__':
    unittest.main()
