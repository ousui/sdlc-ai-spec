"""Lossless factoring and read-only loader; no native host is simulated as PASS."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build import factor,render_source,relocate_body,binding,COMMANDS,HOSTS,split,build
spec=importlib.util.spec_from_file_location('sdlc_workflow',ROOT/'dist/scripts/python/load_workflow.py')
loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)

from naming_check import EXPECTED

class DistributionTests(unittest.TestCase):
    def test_exact_reconstruction_of_all_host_prompts(self):
        for host in HOSTS:
            for name in COMMANDS:
                raw=(ROOT/'src/upstream/templates/commands'/f'{name}.md').read_text()
                _,body=render_source(raw,name,host)
                self.assertEqual(loader.load(ROOT/'dist',host,EXPECTED[name]),binding(host)+relocate_body(body,host))
                meta,entry=split((ROOT/'dist/adapters'/host/'skills'/EXPECTED[name]/'SKILL.md').read_text())
                self.assertIn('--host '+host+' --skill '+EXPECTED[name],entry)
                self.assertIn('read its COMPLETE stdout',entry)
                self.assertNotIn('## Outline',entry)

    def test_factor_structure_or_reserved_token_change_fails(self):
        with self.assertRaises(ValueError):factor({'codex':'x\n','claude':'x\ny\n','cursor':'x\n'})
        with self.assertRaises(ValueError):factor({h:'@@SDLC_BIND_0000@@' for h in HOSTS})

    def test_literal_fragments_not_recursive_templates(self):
        text,slots=factor({'codex':'foo $x bar\n','claude':'foo ${Y} bar\n','cursor':'foo \\1 bar\n'})
        self.assertEqual(len(slots['codex']),1)
        self.assertIn('@@SDLC_BIND_',text)

    def test_loader_rejects_host_skill_and_corrupted_bindings(self):
        for host,skill in [('guess','plan'),('codex','../plan')]:
            with self.assertRaises(ValueError):loader.load(ROOT/'dist',host,skill)
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'package';shutil.copytree(ROOT/'dist',copy)
            path=copy/'bindings/codex.json';data=json.loads(path.read_text())
            data['sdlc-200-plan']['@@SDLC_BIND_9999@@']='injected';path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):loader.load(copy,'codex','sdlc-200-plan')

    def test_loader_pages_reconstruct_without_project_or_cli(self):
        before={p: p.read_bytes() for p in (ROOT/'dist').rglob('*') if p.is_file()}
        script=ROOT/'dist/scripts/python/load_workflow.py'
        complete=loader.load(ROOT/'dist','codex','sdlc-100-spec')
        output=[]
        with tempfile.TemporaryDirectory() as temp:
            for offset in range(0,len(complete.splitlines()),73):
                r=subprocess.run([sys.executable,'-I','-B',str(script),'--host','codex','--skill','sdlc-100-spec','--offset',str(offset),'--limit','73'],cwd=temp,text=True,capture_output=True,check=True)
                output.append(r.stdout)
            bad=subprocess.run([sys.executable,'-I','-B',str(script),'--host','codex','--skill','sdlc-200-plan','--limit','0'],cwd=temp,capture_output=True)
            self.assertNotEqual(bad.returncode,0)
        self.assertEqual(''.join(output),complete)
        self.assertEqual(before,{p: p.read_bytes() for p in (ROOT/'dist').rglob('*') if p.is_file()})

    def test_loader_rejects_package_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'package';shutil.copytree(ROOT/'dist',copy)
            target=copy/'references/workflows/sdlc-200-plan.md';target.unlink()
            outside=Path(temp)/'outside.md';outside.write_text('untrusted')
            target.symlink_to(outside)
            with self.assertRaises(ValueError):loader.load(copy,'codex','sdlc-200-plan')

    def test_builder_refuses_source_and_unmarked_output(self):
        for path in (ROOT,ROOT/'src',ROOT/'tools',ROOT.parent):
            with self.assertRaises(ValueError):build(path)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'unknown';out.mkdir();(out/'user.txt').write_text('keep')
            with self.assertRaises(ValueError):build(out)
            self.assertEqual((out/'user.txt').read_text(),'keep')
