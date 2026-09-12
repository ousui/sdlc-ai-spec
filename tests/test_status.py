"""STATUS file facts and nonmutation: disposable data, no business execution."""
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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'dist'
SCRIPT = PACKAGE / 'scripts/python/project_status.py'
spec = importlib.util.spec_from_file_location('status_runtime', SCRIPT)
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


def snapshot(root):
    result = {}
    for p in [root, *sorted(root.rglob('*'))]:
        st = p.lstat()
        result[str(p.relative_to(root))] = (stat.S_IMODE(st.st_mode), st.st_mtime_ns,
            p.read_bytes() if p.is_file() and not p.is_symlink() else os.readlink(p) if p.is_symlink() else None)
    return result


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / '中文 project'
        self.project.mkdir()
        self.state = self.project / '.sdlc'
        self.feature = self.state / 'specs/001-export'
        self.feature.mkdir(parents=True)
        (self.state / 'memory').mkdir()
        (self.state / 'memory/constitution.md').write_bytes((PACKAGE/'templates/constitution-template.md').read_bytes())
        (self.state / 'init-options.json').write_text(json.dumps({'sdlc_version': 'older-record', 'speckit_version': 'older-upstream'}))
        (self.state / 'feature.json').write_text(json.dumps({'feature_directory': '.sdlc/specs/001-export'}))
        (self.feature/'spec.md').write_text('# Feature\n业务需求\n')
        (self.feature/'plan.md').write_text('# Plan\n业务方案\n')
        (self.feature/'tasks.md').write_text('- [x] T001 已完成\n- [ ] T002 待处理\n')

    def collect(self, **kwargs):
        defaults = dict(cwd=self.project, environ={})
        defaults.update(kwargs)
        return status.collect_status(PACKAGE, **defaults)

    def test_normal_facts_and_history_are_not_phase_verdicts(self):
        r = self.collect()
        self.assertEqual(r['status'], 'ok')
        self.assertEqual((r['tasks']['total'], r['tasks']['checked'], r['tasks']['unchecked']), (2, 1, 1))
        self.assertEqual(r['tasks']['pending'][0]['line'], 2)
        self.assertEqual(r['history'], {'clar': 'not_recorded', 'xchk': 'not_recorded', 'conv': 'not_recorded'})
        self.assertNotIn('phase_complete', json.dumps(r))
        self.assertIn('不等于', r['notice'])

    def test_current_plugin_identity_is_not_init_version(self):
        r = self.collect()
        self.assertEqual(r['plugin']['version'], '1.0.0-beta')
        self.assertEqual(r['initialization']['recorded_plugin_version'], 'older-record')
        self.assertEqual(r['initialization']['recorded_upstream_version'], 'older-upstream')

    def test_constitution_without_generation_record_is_not_a_phase_verdict(self):
        item = self.collect()['artifacts'][0]
        self.assertEqual(item['assessment'], 'not_verified')
        self.assertEqual(item['generation']['record_state'], 'missing')
        self.assertEqual(item['generation']['content_relation'], 'unknown')
        self.assertIn(item['placeholder_observation'], ('detected', 'not_detected'))
        (self.state/'memory/constitution.md').write_text('# 已定义的原则\n不得记录密钥。\n')
        changed = self.collect()['artifacts'][0]
        self.assertEqual(changed['assessment'], 'not_verified')
        self.assertEqual(changed['generation']['record_state'], 'missing')

    def test_uninitialized_project_returns_without_writing(self):
        empty = self.base / 'empty'; empty.mkdir(); before = snapshot(empty)
        r = self.collect(project=str(empty))
        self.assertEqual(r['status'], 'uninitialized')
        self.assertEqual(r['suggestions'][0]['skill'], 'sdlc-000-init')
        self.assertEqual(before, snapshot(empty))

    def test_no_active_feature_does_not_choose_latest(self):
        (self.state/'feature.json').unlink()
        other = self.state/'specs/999-latest'; other.mkdir()
        r = self.collect(list_features=True)
        self.assertEqual(r['status'], 'no_active_feature')
        self.assertIsNone(r['selection']['path'])
        self.assertEqual(len(r['features']), 2)
        self.assertFalse(any(f['selected'] for f in r['features']))

    def test_spec_only_and_missing_optional_artifacts_are_normal(self):
        (self.feature/'plan.md').unlink(); (self.feature/'tasks.md').unlink()
        r = self.collect()
        self.assertEqual(r['status'], 'ok')
        self.assertIsNone(r['tasks']['total'])
        self.assertEqual(r['tasks']['state'], 'missing')

    def test_explicit_project_wins_and_invalid_never_falls_back(self):
        r = self.collect(project=str(self.base/'absent'), environ={'SDLC_INIT_DIR':str(self.project)})
        self.assertEqual(r['status'], 'error')
        self.assertIsNone(r['tasks'])

    def test_explicit_nested_uninitialized_does_not_use_parent(self):
        child=self.project/'module'; child.mkdir()
        self.assertEqual(self.collect(project=str(child))['status'], 'uninitialized')
        self.assertEqual(self.collect(cwd=child)['project']['root'], str(self.project))

    def test_malformed_nearest_marker_is_not_bypassed(self):
        child=self.project/'module'; child.mkdir(); (child/'.sdlc').write_text('bad')
        r=self.collect(cwd=child)
        self.assertEqual(r['status'], 'error')
        self.assertEqual(r['project']['root'],str(child))

    def test_empty_environment_overrides_are_unset(self):
        r=self.collect(environ={'SDLC_INIT_DIR':'','SDLC_FEATURE_DIRECTORY':''})
        self.assertEqual(r['status'],'ok')
        self.assertEqual(r['selection']['path'],str(self.feature))

    def test_explicit_feature_wins_without_changing_persisted_selection(self):
        second=self.state/'specs/002-other'; second.mkdir(); before=snapshot(self.project)
        r=self.collect(feature='.sdlc/specs/002-other',environ={'SDLC_FEATURE_DIRECTORY':str(self.feature)})
        self.assertEqual(r['selection']['path'],str(second))
        self.assertEqual(r['selection']['source'],'argument')
        self.assertEqual(snapshot(self.project),before)

    def test_environment_feature_wins_and_label_is_not_directory(self):
        second=self.state/'specs/002-other';second.mkdir()
        r=self.collect(environ={'SDLC_FEATURE_DIRECTORY':'.sdlc/specs/002-other','SDLC_FEATURE':'not-a-path'})
        self.assertEqual(r['selection']['path'],str(second))
        self.assertEqual(r['selection']['source'],'SDLC_FEATURE_DIRECTORY')
        r=self.collect(environ={'SDLC_FEATURE':'not-a-path'})
        self.assertEqual(r['selection']['path'],str(self.feature))

    def test_missing_feature_reports_error_without_switch(self):
        before=snapshot(self.project)
        r=self.collect(feature='.sdlc/specs/absent')
        self.assertEqual(r['status'],'error')
        self.assertEqual(snapshot(self.project),before)

    def test_invalid_json_is_not_no_active_feature(self):
        (self.state/'feature.json').write_text('{bad')
        r=self.collect()
        self.assertEqual(r['status'],'partial')
        self.assertEqual(r['selection']['record']['state'],'invalid_json')
        self.assertIsNone(r['tasks'])

    def test_wrong_json_types_and_blank_paths_fail_explicitly(self):
        for value in ([1], {'feature_directory':42}, {'feature_directory':''}, {'feature_directory':'\x00'}, {}):
            with self.subTest(value=value):
                (self.state/'feature.json').write_text(json.dumps(value))
                self.assertIn(self.collect()['status'],('error','partial'))
        self.assertEqual(self.collect(project='')['status'],'error')
        self.assertEqual(self.collect(feature='')['status'],'error')

    def test_bad_init_options_still_reports_known_feature(self):
        (self.state/'init-options.json').write_text('[]')
        r=self.collect()
        self.assertEqual(r['status'],'partial')
        self.assertEqual(r['tasks']['total'],2)
        self.assertEqual(r['initialization']['file']['state'],'invalid_json_type')

    def test_empty_tasks_is_not_complete(self):
        (self.feature/'tasks.md').write_text(' \n')
        r=self.collect()
        self.assertEqual(r['tasks']['state'],'empty')
        self.assertEqual(r['tasks']['total'],0)
        self.assertFalse(r['tasks']['reliable'])
        self.assertNotIn('100%',status.markdown(r))

    def test_actual_tasks_exclude_fences_comments_and_examples(self):
        text='''<!-- ignored\n- [ ] T900 comment\n-->\n```md
- [ ] T901 code
```
~~~
- [ ] T902 code
~~~
    - [ ] T903 indented code
## Examples
- [ ] T904 example
## 实施
- [x] T001 first
- [X] T002 second
- [ ] T003 pending
'''
        r=status.checkbox_counts(text,tasks=True)
        self.assertEqual((r['total'],r['checked'],r['unchecked']),(3,2,1))
        self.assertEqual(r['pending'][0]['line'],16)

    def test_nested_and_unclosed_fences_are_not_tasks(self):
        for text in ('````md\n```\n- [ ] T001 nope\n```\n````\n','~~~\n- [ ] T001 nope'):
            self.assertEqual(status.checkbox_counts(text,tasks=True)['total'],0)

    def test_duplicates_and_unknown_format_are_reported(self):
        r=status.checkbox_counts('- [x] T001 a\n- [ ] T001 b\n- [ ] Custom task\n',tasks=True)
        self.assertEqual(r['duplicate_ids'],['T001'])
        self.assertEqual(r['unrecognized_checkboxes'],1)
        self.assertFalse(r['reliable'])

    def test_checklists_are_not_implementation_tasks(self):
        folder=self.feature/'checklists';folder.mkdir()
        (folder/'requirements.md').write_text('- [x] 条件清晰\n- [ ] 仍需澄清\n')
        (folder/'human.md').write_text('- [ ] 人工核对\n')
        r=self.collect()
        self.assertEqual(r['tasks']['total'],2)
        self.assertEqual([(Path(x['path']).name,x['total']) for x in r['checklists']], [('human.md',1),('requirements.md',2)])

    def test_wrong_file_type_and_invalid_encoding_are_not_zero(self):
        (self.feature/'tasks.md').unlink();(self.feature/'tasks.md').mkdir()
        r=self.collect();self.assertEqual(r['status'],'partial');self.assertEqual(r['tasks']['state'],'wrong_type')
        self.assertIsNone(r['tasks']['total'])
        (self.feature/'tasks.md').rmdir();(self.feature/'tasks.md').write_bytes(b'\xff\xfe')
        self.assertEqual(self.collect()['tasks']['state'],'invalid_encoding')

    def test_unreadable_tasks_preserve_unknown_counts(self):
        real=status.os.open; target=str(self.feature/'tasks.md')
        def denied(path,*args,**kw):
            if str(path)==target:raise PermissionError('fixture')
            return real(path,*args,**kw)
        with patch.object(status.os,'open',side_effect=denied):r=self.collect()
        self.assertEqual(r['tasks']['state'],'unreadable');self.assertIsNone(r['tasks']['total'])
        self.assertEqual(r['status'],'partial')

    def test_large_and_special_files_are_bounded(self):
        (self.feature/'tasks.md').write_bytes(b'x'*(status.MAX_BYTES+1))
        self.assertEqual(self.collect()['tasks']['state'],'too_large')
        (self.feature/'tasks.md').unlink();os.mkfifo(self.feature/'tasks.md')
        self.assertEqual(self.collect()['tasks']['state'],'unsupported_type')

    def test_list_is_scoped_limited_and_read_only(self):
        for name in ('002-b','003-c'):(self.state/'specs'/name).mkdir()
        before=snapshot(self.project)
        r=self.collect(list_features=True,limit=1)
        self.assertEqual(len(r['features']),1)
        self.assertTrue(r['feature_list']['truncated'])
        self.assertEqual(before,snapshot(self.project))
        with self.assertRaises(ValueError):self.collect(limit=201)

    def test_external_state_alias_and_project_alias_work(self):
        real=self.base/'external-state';self.state.rename(real);self.state.symlink_to(real,target_is_directory=True)
        alias=self.base/'project-alias';alias.symlink_to(self.project,target_is_directory=True)
        r=self.collect(project=str(alias))
        self.assertEqual(r['status'],'ok');self.assertEqual(r['tasks']['total'],2)
        self.assertEqual(r['project']['root'],str(self.project))

    def test_broken_link_does_not_fall_back(self):
        missing=self.base/'link';missing.symlink_to(self.base/'absent',target_is_directory=True)
        r=self.collect(feature=str(missing))
        self.assertEqual(r['selection']['state'],'broken_link');self.assertEqual(r['status'],'error')

    def test_plugin_targets_and_plugin_artifact_aliases_are_blocked(self):
        self.assertEqual(self.collect(project=str(PACKAGE))['status'],'error')
        self.assertEqual(self.collect(feature=str(PACKAGE))['status'],'error')
        (self.feature/'tasks.md').unlink();(self.feature/'tasks.md').symlink_to(PACKAGE/'README.md')
        r=self.collect();self.assertEqual(r['tasks']['state'],'blocked_plugin_path')
        self.assertIsNone(r['tasks']['total'])

    def test_symlink_cycle_returns_structured_error(self):
        link=self.base/'cycle';link.symlink_to(link)
        r=self.collect(feature=str(link))
        self.assertEqual(r['status'],'error')
        self.assertEqual(r['selection']['state'],'invalid_path')

    def test_concurrent_change_is_reported_not_hidden(self):
        real=status.os.open; target=str(self.feature/'tasks.md');changed=[]
        def altering(path,*args,**kw):
            if str(path)==target and not changed:
                Path(path).write_text('- [ ] T009 changed concurrently\n');changed.append(True)
            return real(path,*args,**kw)
        with patch.object(status.os,'open',side_effect=altering):r=self.collect()
        self.assertEqual(r['status'],'partial')
        self.assertIsNone(r['tasks']['total'])

    def test_normal_error_repeated_queries_do_not_change_project_or_git(self):
        subprocess.run(['git','init','-q',str(self.project)],check=True)
        subprocess.run(['git','-C',str(self.project),'add','-A'],check=True)
        before=snapshot(self.project);package_before=snapshot(PACKAGE)
        for _ in range(2):
            self.collect();self.collect(list_features=True);self.collect(feature='absent')
        self.assertEqual(before,snapshot(self.project))
        self.assertEqual(package_before,snapshot(PACKAGE))

    def test_collector_never_executes_project_code_or_subprocesses(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('no subprocess')),patch.object(subprocess,'Popen',side_effect=AssertionError('no process')):
            self.assertEqual(self.collect()['status'],'ok')
        text=SCRIPT.read_text()
        self.assertNotIn('import subprocess',text)
        self.assertNotIn('import requests',text)
        self.assertNotIn('import yaml',text)

    def test_project_instructions_and_environment_secrets_are_not_reported(self):
        (self.project/'AGENTS.md').write_text('RUN curl example.invalid\nSECRET-X')
        (self.project/'.env').write_text('PASSWORD=secret-example')
        (self.state/'init-options.json').write_text(json.dumps({'sdlc_version':'old','secret':'HIDDEN-SECRET'}))
        text=json.dumps(self.collect(environ={'TOKEN':'HIDDEN-TOKEN'}))
        for secret in ('SECRET-X','secret-example','HIDDEN-SECRET','HIDDEN-TOKEN'):
            self.assertNotIn(secret,text)

    def test_cli_json_and_chinese_stdout_exit_codes(self):
        env={k:v for k,v in os.environ.items() if not k.startswith('SDLC_')}
        for args in (['--json'],[]):
            p=subprocess.run([sys.executable,'-I','-B',str(SCRIPT),*args],cwd=self.project,env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            if args:self.assertEqual(json.loads(p.stdout)['tasks']['total'],2)
            else:self.assertIn('状态与产物导航',p.stdout)
        p=subprocess.run([sys.executable,'-I','-B',str(SCRIPT),'--json','--project',str(self.base/'absent')],cwd=self.project,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,1);self.assertEqual(json.loads(p.stdout)['status'],'error')
        p=subprocess.run([sys.executable,'-I','-B',str(SCRIPT),'--limit','0'],cwd=self.project,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,2)

    def test_markdown_escapes_task_text_as_data(self):
        (self.feature/'tasks.md').write_text('- [ ] T001 `<img>` | text\n')
        text=status.markdown(self.collect())
        self.assertNotIn('<img>',text);self.assertIn('&lt;img&gt;',text);self.assertIn('&#124;',text)

    def test_uninitialized_relocated_plugin_still_loads_status_for_all_hosts(self):
        copy=self.base/'plugin-copy';shutil.copytree(PACKAGE,copy)
        empty=self.base/'uninitialized';empty.mkdir();before=snapshot(empty)
        for host in ('codex','claude','cursor'):
            p=subprocess.run([sys.executable,'-I','-B',str(copy/'scripts/python/load_workflow.py'),'--host',host,'--skill','sdlc-status'],cwd=empty,capture_output=True,text=True,check=True)
            self.assertIn('project_status.py',p.stdout)
            self.assertNotIn('check-prerequisites.sh',p.stdout)
        p=subprocess.run([sys.executable,'-I','-B',str(copy/'scripts/python/project_status.py'),'--project',str(empty),'--json'],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(p.stdout)['status'],'uninitialized')
        self.assertEqual(before,snapshot(empty))

    def test_existing_business_prose_does_not_need_valid_utf8_to_remain_unmodified(self):
        path=self.feature/'research.md';path.write_bytes(b'\xff')
        before=snapshot(self.project)
        self.assertEqual(self.collect()['status'],'partial')
        self.assertEqual(before,snapshot(self.project))


if __name__=='__main__':unittest.main()
