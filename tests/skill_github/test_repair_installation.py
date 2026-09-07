"""R7/R8 regressions: exact compiler binding and optional no-scan evidence."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from tools.install_sdlc_github import install
from tests.skill_github.native_evidence import check_workspace_access
ROOT=Path(__file__).resolve().parents[2]


class RepairInstallation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
    def tearDown(self):self.tmp.cleanup()
    def command(self,args,**kwargs):
        return subprocess.run(args,capture_output=True,text=True,timeout=30,**kwargs)

    def test_r7_uninstalled_launcher_is_offline_guard_not_system_python(self):
        r=self.command([str(ROOT/'skills/sdlc-github/scripts/run'),'status'])
        self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['errors'][0]['code'],'INSTALLATION_REQUIRED')
        self.assertEqual(r.stderr,'')

    def test_r7_installed_compiler_uses_bound_interpreter_and_relative_resources(self):
        code=self.root/'version one';data=self.root/'stable data'
        receipt=install('codex',code,data,Path(sys.executable))
        launcher=Path(receipt['compiler_launcher'])
        stub=self.root/'untrusted-bin';stub.mkdir()
        (stub/'python3').write_text('#!/bin/sh\nprintf "wrong Python" >&2\nexit 89\n');(stub/'python3').chmod(0o755)
        env={**os.environ,'PATH':str(stub)+':/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
        env.pop('SDLC_GITHUB_TOKEN',None)
        workspace=self.root/'workspace';workspace.mkdir()
        (workspace/'private.txt').write_text('not input for compiler')
        before=(workspace/'private.txt').read_bytes()
        r=self.command([str(launcher),'read','--repo','example/project','--kind','issue.list','--state','all','--output','json'],cwd=workspace,env=env)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['tool'],'sdlc_github_read')
        self.assertEqual(json.loads(r.stdout)['arguments']['state'],'all')
        self.assertEqual(r.stderr,'');self.assertEqual((workspace/'private.txt').read_bytes(),before)
        skill=(code/'skills/sdlc-github/SKILL.md').read_text()
        self.assertIn('../_shared/contracts/github-runtime.md',skill)
        self.assertTrue((code/'skills/_shared/contracts/github-runtime.md').is_file())
        self.assertEqual(list(data.iterdir()),[])
        relocated=self.root/'version moved';code.rename(relocated)
        r=self.command([str(relocated/'skills/sdlc-github/scripts/run'),'status','--output','json'],cwd=workspace,env=env)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['tool'],'sdlc_github_status')
        self.assertNotIn('Traceback',r.stderr)
        self.assertEqual(receipt['native_gate'],'OUT_OF_SCOPE_MANUAL_FEEDBACK')

    def test_r7_missing_dependency_has_safe_explicit_failure_and_meta_stays_offline(self):
        path=ROOT/'skills/sdlc-github/scripts/runtime.py'
        r=self.command([sys.executable,'-B','-S',str(path),'read','--repo','example/project','--kind','issue.list','--output','json'])
        self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['errors'][0]['code'],'DEPENDENCY_UNAVAILABLE')
        self.assertNotIn('Traceback',r.stderr)
        r=self.command([sys.executable,'-B','-S',str(path),'help','--output','json'])
        self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['ok'])

    def test_r8_file_hash_only_cannot_prove_no_scan(self):
        trace={'file_count':10000,'before_sha256':'a'*64,'after_sha256':'a'*64}
        with self.assertRaises(ValueError):check_workspace_access(trace)
        trace['workspace_access']={'complete':True,'events':[
            {'actor':'host_discovery','action':'search','path':'/fixture/AGENTS.md'},
            {'actor':'skill','action':'read','scope':'declared_plugin','path':'/plugin/skills/_shared/contracts/github-runtime.md'}]}
        check_workspace_access(trace)
        for event in ({'actor':'skill','action':'search','scope':'workspace','path':'/fixture'},
                      {'actor':'skill','action':'read','scope':'workspace','path':'/fixture/private.txt'},
                      {'actor':'host_discovery','action':'write','path':'/fixture/AGENTS.md'},
                      {'actor':'unknown','action':'read','path':'/fixture/private.txt'}):
            with self.subTest(event=event):
                bad=deepcopy(trace);bad['workspace_access']['events'].append(event)
                with self.assertRaises(ValueError):check_workspace_access(bad)
        trace['workspace_access']['complete']=False
        with self.assertRaises(ValueError):check_workspace_access(trace)
