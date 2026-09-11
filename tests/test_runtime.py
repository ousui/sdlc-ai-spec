"""Deterministic synthetic filesystem tests; no real project or Agent calls.

Preservation and --paths-only scenarios follow upstream script tests. No test
helper here is shipped as an initializer or used against a business directory.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HOSTS=('codex','claude','cursor')


def tree(root: Path) -> dict:
    return {str(p.relative_to(root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode&0o777)
            for p in sorted(root.rglob('*')) if p.is_file()}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='sdlc fixture 中文 ')
        self.base=Path(self.tmp.name)
        self.trap=self.base/'bin';self.trap.mkdir()
        trap=self.trap/'specify'
        trap.write_text('#!/bin/sh\nprintf called >> "$SDLC_TRAP_FILE"\nexit 97\n')
        trap.chmod(0o755)
        self.trap_file=self.base/'unexpected-cli-call'
        self.package=ROOT/'dist'
        self.host='codex'
        self.before={host:tree(ROOT/'dist') for host in HOSTS}
        self.env={k:v for k,v in os.environ.items() if not k.startswith(('SPECIFY_','SDLC_','PYTHON'))}
        self.env.update(PATH=str(self.trap)+os.pathsep+os.environ.get('PATH','/usr/bin:/bin'),
                        HOME=str(self.base/'home'),SDLC_TRAP_FILE=str(self.trap_file),
                        PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
        (self.base/'home').mkdir()
        self.sequence=0

    def tearDown(self):
        try:
            self.assertFalse(self.trap_file.exists(),'Runtime invoked specify')
            for host in HOSTS:self.assertEqual(self.before[host],tree(ROOT/'dist'))
        finally:
            for p in self.base.rglob('*'):
                if not p.is_symlink():
                    try:p.chmod(0o755 if p.is_dir() else 0o644)
                    except OSError:pass
            self.tmp.cleanup()

    def hosts(self):
        for host in HOSTS:
            self.host=host;self.package=ROOT/'dist'
            yield host

    def seed(self, *, plan=True, tasks=False, feature=True, name=None):
        self.sequence+=1
        project=self.base/(name or f'project {self.sequence} 中文')
        state=project/'.sdlc'
        (state/'memory').mkdir(parents=True)
        (state/'init-options.json').write_text('{"script":"sh","feature_numbering":"sequential"}\n')
        (state/'memory/constitution.md').write_text('Synthetic test principles\n')
        f=state/'specs/001-fixture'
        if feature:
            f.mkdir(parents=True)
            (f/'spec.md').write_text('Synthetic spec\n')
            (state/'feature.json').write_text('{"feature_directory":".sdlc/specs/001-fixture"}\n')
            if plan:(f/'plan.md').write_text('Synthetic plan\n')
            if tasks:(f/'tasks.md').write_text('- [ ] T001 Synthetic task\n')
        return project,f

    def run_script(self,project,script,*args,overrides=None,success=True,cwd=None):
        env=dict(self.env,SDLC_HOST=self.host)
        if overrides:env.update(overrides)
        result=subprocess.run(['bash',str(self.package/'scripts/bash'/script),*args],
             cwd=cwd or project,env=env,text=True,capture_output=True,timeout=20)
        if success:self.assertEqual(result.returncode,0,(script,args,result.stdout,result.stderr))
        else:self.assertNotEqual(result.returncode,0,(script,args,result.stdout,result.stderr))
        return result

    def test_core_templates_exact_and_no_feature_required(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,_=self.seed(feature=False)
                for template in sorted((self.package/'templates').glob('*.md')):
                    r=self.run_script(p,'resolve-template.sh',template.stem,'--json')
                    self.assertEqual(json.loads(r.stdout)['TEMPLATE_CONTENT'],template.read_text())
                self.assertFalse((p/'.sdlc/feature.json').exists())

    def test_setup_plan_creation_and_no_overwrite(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,f=self.seed(plan=False)
                result=json.loads(self.run_script(p,'setup-plan.sh','--json').stdout)
                self.assertEqual(result['FEATURE_DIR'],str(f))
                self.assertEqual(result['FEATURE_SPEC'],str(f/'spec.md'))
                self.assertEqual((f/'plan.md').read_text(),(self.package/'templates/plan-template.md').read_text())
                (f/'plan.md').write_text('Human edits survive\n\n')
                self.run_script(p,'setup-plan.sh','--json')
                self.assertEqual((f/'plan.md').read_text(),'Human edits survive\n\n')

    def test_tasks_template_and_existing_tasks_are_preserved(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,f=self.seed(tasks=True)
                before=(f/'tasks.md').read_bytes()
                result=json.loads(self.run_script(p,'setup-tasks.sh','--json').stdout)
                self.assertEqual(result['TASKS_TEMPLATE'],str(self.package/'templates/tasks-template.md'))
                self.assertEqual(result['TASKS_TEMPLATE_CONTENT'],(self.package/'templates/tasks-template.md').read_text())
                self.assertEqual(before,(f/'tasks.md').read_bytes())
                (f/'spec.md').unlink()
                self.run_script(p,'setup-tasks.sh','--json',success=False)

    def test_prerequisite_flags_and_native_failure_hints(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,f=self.seed(plan=False)
                r=self.run_script(p,'check-prerequisites.sh','--json',success=False)
                prefix={'codex':'$sdlc-','claude':'/sdlc-ai-spec:sdlc-','cursor':'/sdlc-'}[host]
                self.assertIn(prefix+'200-plan',r.stderr)
                (f/'plan.md').write_text('plan\n')
                self.run_script(p,'check-prerequisites.sh','--require-tasks',success=False)
                (f/'tasks.md').write_text('tasks\n')
                (f/'research.md').write_text('research\n')
                r=self.run_script(p,'check-prerequisites.sh','--json','--require-spec','--require-tasks','--include-tasks')
                self.assertEqual(json.loads(r.stdout)['AVAILABLE_DOCS'],['research.md','tasks.md'])
                (f/'spec.md').unlink()
                self.run_script(p,'check-prerequisites.sh','--json','--require-spec',success=False)

    def test_paths_only_does_not_persist_or_create(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,_=self.seed()
                state=p/'.sdlc/feature.json';before=state.read_bytes()
                target='.sdlc/specs/099-uncreated'
                r=self.run_script(p,'check-prerequisites.sh','--json','--paths-only',
                                  overrides={'SDLC_FEATURE_DIRECTORY':target})
                self.assertEqual(json.loads(r.stdout)['FEATURE_DIR'],str(p/target))
                self.assertEqual(before,state.read_bytes())
                self.assertFalse((p/target).exists())

    def test_project_override_does_not_mutate_shared_template(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,_=self.seed()
                overrides=p/'.sdlc/templates/overrides';overrides.mkdir(parents=True)
                (overrides/'tasks-template.md').write_text('User override\n\n')
                r=self.run_script(p,'setup-tasks.sh','--json')
                self.assertEqual(json.loads(r.stdout)['TASKS_TEMPLATE_CONTENT'],'User override\n\n')
                self.assertEqual(json.loads(r.stdout)['TASKS_TEMPLATE'],str(overrides/'tasks-template.md'))

    def test_two_projects_and_cross_host_sequential_reuse(self):
        a,af=self.seed();b,bf=self.seed()
        for host in self.hosts():
            with self.subTest(host=host):
                ar=json.loads(self.run_script(a,'check-prerequisites.sh','--json','--paths-only').stdout)
                br=json.loads(self.run_script(b,'check-prerequisites.sh','--json','--paths-only').stdout)
                self.assertEqual(ar['FEATURE_DIR'],str(af));self.assertEqual(br['FEATURE_DIR'],str(bf))
                self.assertNotEqual(ar['REPO_ROOT'],br['REPO_ROOT'])
        for p in (a,b):
            for d in ('.agents','.claude','.cursor','.sdlc/scripts'):
                self.assertFalse((p/d).exists())
            for f in (p/'.sdlc').rglob('*'):
                if f.is_file():self.assertNotIn(str(ROOT/'dist'),f.read_text())

    def test_nearest_root_and_explicit_selection(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,f=self.seed();nested=f/'nested';nested.mkdir()
                r=json.loads(self.run_script(p,'project-paths.sh',cwd=nested).stdout)
                self.assertEqual(r['PROJECT_ROOT'],str(p))
                other,_=self.seed()
                r=json.loads(self.run_script(p,'project-paths.sh',cwd=nested,overrides={'SDLC_INIT_DIR':str(other)}).stdout)
                self.assertEqual(r['PROJECT_ROOT'],str(other))
                self.run_script(p,'project-paths.sh',overrides={'SDLC_INIT_DIR':str(self.base/'missing')},success=False)

    def test_no_initialized_project_never_falls_back_to_plugin(self):
        for host in self.hosts():
            with self.subTest(host=host):
                empty=self.base/('empty-'+host);empty.mkdir()
                for script in ('project-paths.sh','setup-plan.sh','setup-tasks.sh'):
                    self.run_script(empty,script,success=False)
                self.run_script(empty,'resolve-template.sh','spec-template',success=False)
                self.assertEqual(list(empty.iterdir()),[])

    def test_plugin_and_symlink_targets_are_rejected(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,f=self.seed();before=tree(p)
                self.run_script(p,'check-prerequisites.sh','--paths-only',
                                overrides={'SDLC_FEATURE_DIRECTORY':str(self.package)},success=False)
                self.assertEqual(before,tree(p))
                (f/'plan.md').unlink();(f/'plan.md').symlink_to(self.package/'templates/plan-template.md')
                self.run_script(p,'setup-plan.sh','--json',success=False)
                other=self.base/('linked-'+host);other.mkdir()
                (other/'.sdlc').symlink_to(p/'.sdlc',target_is_directory=True)
                self.run_script(other,'project-paths.sh',success=False)

    def test_quoted_unicode_paths_and_shell_injection_are_data(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,_=self.seed(name=f"{host} quote' Unicode中文 $(touch INJECTED)")
                target='.sdlc/specs/007-quote"-$HOME-$(touch INJECTED)'
                r=self.run_script(p,'check-prerequisites.sh','--json','--paths-only',overrides={'SDLC_FEATURE_DIRECTORY':target})
                self.assertEqual(json.loads(r.stdout)['FEATURE_DIR'],str(p/target))
                self.assertFalse((p/'INJECTED').exists())
                self.assertFalse((p/target).exists())

    def test_readonly_and_relocated_package_stays_unchanged(self):
        for host in self.hosts():
            with self.subTest(host=host):
                original=self.package
                relocated=self.base/('readonly package '+host)
                shutil.copytree(original,relocated)
                for file in relocated.rglob('*'):
                    file.chmod(0o555 if file.is_dir() else 0o444)
                relocated.chmod(0o555);before=tree(relocated)
                self.package=relocated
                p,_=self.seed(plan=False)
                self.run_script(p,'setup-plan.sh','--json')
                r=json.loads(self.run_script(p,'setup-tasks.sh','--json').stdout)
                self.assertEqual(r['TASKS_TEMPLATE'],str(relocated/'templates/tasks-template.md'))
                self.assertEqual(before,tree(relocated))
                self.package=original

    def test_create_feature_dry_run_numbering_and_preservation(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,_=self.seed(feature=False);before=tree(p)
                r=self.run_script(p,'create-new-feature.sh','--json','--dry-run','--short-name','sample','Example feature')
                self.assertTrue(json.loads(r.stdout)['DRY_RUN']);self.assertEqual(before,tree(p))
                r=self.run_script(p,'create-new-feature.sh','--json','--short-name','sample','Example feature')
                created=Path(json.loads(r.stdout)['SPEC_FILE'])
                self.assertEqual(created,p/'.sdlc/specs/001-sample/spec.md')
                self.assertEqual(created.read_text(),(self.package/'templates/spec-template.md').read_text())
                created.write_text('Human spec\n')
                self.run_script(p,'create-new-feature.sh','--json','--allow-existing-branch','--number','1','--short-name','sample','Example feature')
                self.assertEqual(created.read_text(),'Human spec\n')
                self.assertFalse((p/'.git').exists())

    def test_invalid_flags_and_template_name_fail(self):
        for host in self.hosts():
            with self.subTest(host=host):
                p,_=self.seed()
                for script in ('setup-plan.sh','setup-tasks.sh','check-prerequisites.sh','project-paths.sh'):
                    self.run_script(p,script,'--invalid',success=False)
                self.run_script(p,'resolve-template.sh','../spec-template','--json',success=False)
                self.run_script(p,'resolve-template.sh','missing-template','--json',success=False)

    def test_python_dependency_failure_is_explicit(self):
        p,_=self.seed()
        minimal=self.base/'minimal-bin';minimal.mkdir()
        for command in ('bash','dirname'):
            (minimal/command).symlink_to(shutil.which(command))
        r=self.run_script(p,'project-paths.sh',overrides={'PATH':str(minimal)},success=False)
        self.assertIn('Python 3.9+',r.stderr)


if __name__=='__main__':unittest.main()
