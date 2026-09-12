"""Template resolution, status parsing and localization; disposable fixtures only."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_status as fixtures

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'dist'
sys.path.insert(0, str(ROOT/'tools'))
import localize


class StatusReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name).resolve()/'project'
        self.feature = self.project/'.sdlc/specs/001-review'
        self.feature.mkdir(parents=True)
        (self.project/'.sdlc/init-options.json').write_text('{}')
        (self.project/'.sdlc/feature.json').write_text(json.dumps({'feature_directory':'.sdlc/specs/001-review'}))
        (self.feature/'spec.md').write_text('# Review\n')

    def check_counts(self, text, *, checklist=False, pending_line=None):
        target = self.feature/('checklists/requirements.md' if checklist else 'tasks.md')
        target.parent.mkdir(exist_ok=True)
        target.write_text(text, encoding='utf-8')
        before = fixtures.snapshot(self.project)
        result = fixtures.status.collect_status(PACKAGE, project=str(self.project), environ={})
        counts = result['checklists'][0] if checklist else result['tasks']
        self.assertEqual((counts['total'],counts['checked'],counts['unchecked']),(2,1,1))
        self.assertTrue(counts['reliable'])
        if pending_line is not None:
            self.assertEqual(counts['pending'][0]['line'], pending_line)
        self.assertEqual(before, fixtures.snapshot(self.project))

    def test_rev008_business_story_title_is_not_example_section(self):
        self.check_counts('## Setup\n- [x] T001 first\n\n## Phase 3: User Story 1 - 示例页面管理 (Priority: P1)\n- [ ] T002 待处理\n',pending_line=5)

    def test_business_examples_substring_english_and_chinese(self):
        for title in ('Examples management','用户示例数据','User Story 2 - API Examples', '示例页面管理'):
            with self.subTest(title=title):
                self.check_counts('- [x] T001 first\n## '+title+'\n- [ ] T002 pending\n')

    def test_rev009_nested_checklist_four_spaces(self):
        self.check_counts('- [x] CHK001 主需求\n    - [ ] CHK002 异常要求\n',checklist=True,pending_line=2)

    def test_nested_tab_and_multilevel_checklists(self):
        for text in ('- [x] parent\n\t- [ ] child\n', '1. Parent\n   - [x] child\n       - [ ] grandchild\n'):
            with self.subTest(text=text):self.check_counts(text,checklist=True)

    def test_rev010_fenced_html_comment_is_literal(self):
        for fence in ('```','~~~','````'):
            self.check_counts('- [x] T001 first\n'+fence+'html\n<!--\n'+fence+'\n- [ ] T002 last\n',pending_line=5)

    def test_inline_literal_html_comment_does_not_hide_tasks(self):
        self.check_counts('- [x] T001 显示 `<!--` 文本\n- [ ] T002 last\n',pending_line=2)

    def test_indented_code_comment_does_not_hide_later_tasks(self):
        self.check_counts('    <!--\n\n- [x] T001 first\n- [ ] T002 last\n')

    def test_nested_code_is_not_a_nested_task(self):
        self.check_counts('- [x] T001 first\n\n      - [ ] T900 code\n\n    - [ ] T002 nested\n')

    def test_only_explicit_example_sections_are_excluded(self):
        self.check_counts('## Examples\n- [ ] T900 example\n## 実施\n- [x] T001 first\n- [ ] T002 pending\n')

    def test_html_comments_outside_code_still_hide_checkboxes(self):
        self.check_counts('<!--\n- [ ] T900 hidden\n-->\n- [x] T001 first\n- [ ] T002 pending\n',pending_line=5)


class TemplatePathReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='SPEC 路径 ')
        self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name).resolve()/'project'
        (self.project/'.sdlc/templates/overrides').mkdir(parents=True)
        self.env={k:v for k,v in os.environ.items() if not k.startswith(('SDLC_','SPECIFY_','PYTHON'))}
        self.env.update(SDLC_INIT_DIR=str(self.project))

    def resolve(self, name='spec-template', script='resolve-template-path.sh', *args):
        return subprocess.run(['bash',str(PACKAGE/'scripts/bash'/script),name,*args],
                              cwd=self.project,env=self.env,text=True,capture_output=True,timeout=15)

    def test_rev007_override_returns_file_path_not_body(self):
        template=self.project/'.sdlc/templates/overrides/spec-template.md'
        template.write_text('# 自定义覆盖\n正文不是路径。\n')
        before=fixtures.snapshot(self.project)
        for host in ('codex','claude','cursor'):
            self.env['SDLC_HOST']=host
            r=self.resolve();self.assertEqual(r.returncode,0,r.stderr)
            selected=Path(r.stdout.rstrip('\n'))
            self.assertEqual(selected,template)
            self.assertEqual(selected.read_bytes(),template.read_bytes())
            workflow=localize.localized_workflow('specify',host)
            self.assertIn('resolve-template-path.sh" spec-template',workflow)
        self.assertEqual(before,fixtures.snapshot(self.project))

    def test_rev007_default_path_is_actual_localized_template(self):
        r=self.resolve();self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(Path(r.stdout.strip()),PACKAGE/'templates/spec-template.md')
        self.assertIn('用户场景',Path(r.stdout.strip()).read_text())

    def test_existing_content_resolver_contract_unchanged(self):
        r=self.resolve('spec-template','resolve-template.sh','--json')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['TEMPLATE_CONTENT'],(PACKAGE/'templates/spec-template.md').read_text())

    def test_unknown_or_missing_template_does_not_fall_back(self):
        for name in ('absent-template','../spec-template','--force'):
            with self.subTest(name=name):
                r=self.resolve(name);self.assertNotEqual(r.returncode,0)
                self.assertEqual(r.stdout,'')


class PresentationReviewTests(unittest.TestCase):
    def test_all_five_distributed_templates_match_reviewed_chinese_assets(self):
        for name in localize.TEMPLATES:
            actual=(PACKAGE/'templates'/(name+'.md')).read_text()
            self.assertEqual(actual,localize.presentation(name))
            self.assertRegex(actual,r'[\u4e00-\u9fff]')
            self.assertEqual(localize.restore_template(name,actual),localize.presentation_source(name))

    def test_requirements_fence_is_localized_for_each_host(self):
        for host in ('codex','claude','cursor'):
            text=localize.localized_workflow('specify',host)
            self.assertIn('- [ ] 需求可测试且无歧义',text)
            self.assertNotIn('- [ ] Requirements are testable and unambiguous',text)
            self.assertIn('[NEEDS CLARIFICATION]',text)
            original=localize.presentation_source('requirements')
            translated=localize.presentation('requirements')
            self.assertEqual(original.count('- [ ]'),16)
            self.assertEqual(translated.count('- [ ]'),16)

    def test_new_init_readme_and_constitution_are_localized_and_repeats_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            command=[sys.executable,'-I','-B',str(PACKAGE/'scripts/python/init_project.py'),'--project',str(root),'--json']
            r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            self.assertIn('项目数据',(root/'.sdlc/README.md').read_text())
            self.assertIn('核心原则',(root/'.sdlc/memory/constitution.md').read_text())
            (root/'.sdlc/README.md').write_text('Existing English customized README\n')
            before=fixtures.snapshot(root)
            r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(before,fixtures.snapshot(root))

    def test_language_directive_forbids_language_tags_without_new_write_permission(self):
        text=localize.resource('output-language')
        self.assertIn('不添加“中文注释”“中文说明”',text)
        self.assertIn('不得为了翻译新增写入',text)
        self.assertIn('只有原流程本来要求的注释',text)
        for path in (localize.LOCALES/'templates').glob('*.md'):
            self.assertNotRegex(path.read_text(),r'中文(?:说明|注释|版本)|\ufffc')

    def test_even_rehashed_template_machine_marker_drift_is_rejected(self):
        name='tasks-template';source=localize.presentation_source(name);text=localize.presentation(name)
        bad=text.replace('T001','T999',1)
        record=copy.deepcopy(localize.catalog()['presentations'][name]);record['translation_sha256']=localize.sha(bad)
        with self.assertRaisesRegex(localize.LocalizationError,'machine/structure'):
            localize.validate_presentation(name,source,bad,record)

    def test_template_and_fixed_requirements_stale_source_are_rejected(self):
        for name in (*localize.TEMPLATES,'requirements'):
            record=localize.catalog()['presentations'][name]
            with self.assertRaisesRegex(localize.LocalizationError,'Stale presentation'):
                localize.validate_presentation(name,localize.presentation_source(name)+'\nUpstream change\n',localize.presentation(name),record)

    def test_inverse_projection_rejects_extra_or_modified_business_text(self):
        name='plan-template'
        with self.assertRaises(localize.LocalizationError):
            localize.restore_template(name,localize.presentation(name)+'\n未审查的新规则\n')

    def test_record_and_refresh_preserve_new_presentation_assets(self):
        # Upgrade refresh already freezes every non-locale file. Verify new
        # template assets participate in that existing locale subtree contract.
        import upgrade
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);assets=root/'src/locales/zh-CN';shutil.copytree(localize.LOCALES,assets)
            original=upgrade.localization_digest(root)
            (assets/'templates/plan-template.md').write_text('待审查译文')
            self.assertNotEqual(original,upgrade.localization_digest(root))
            with patch.object(localize,'LOCALES',assets):
                with self.assertRaises(localize.LocalizationError):localize.check_all()

if __name__=='__main__':unittest.main()
