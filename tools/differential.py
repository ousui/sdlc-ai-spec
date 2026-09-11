"""Compare installed upstream scripts with the port on synthetic fixtures.

Only explicit address/name differences are projected. Return codes, stdout,
stderr and generated spec/plan/task bytes otherwise have to agree.
"""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from build import ROOT, HOSTS
from naming_check import reverse_names


def compare(baselines: Path) -> list[dict]:
    records=[]
    cases=[
        ('plan','setup-plan.sh',('--json',)),
        ('tasks','setup-tasks.sh',('--json',)),
        ('paths','check-prerequisites.sh',('--json','--paths-only')),
        ('required','check-prerequisites.sh',('--json','--require-spec','--require-tasks','--include-tasks')),
        ('missing-plan','check-prerequisites.sh',('--json',)),
        ('template','resolve-template.sh',('checklist-template','--json')),
        ('dry-run','create-new-feature.sh',('--json','--dry-run','--short-name','next','Next feature')),
    ]
    with tempfile.TemporaryDirectory(prefix='sdlc differential ') as temp:
        root=Path(temp)
        for host in HOSTS:
            baseline=baselines/('cursor-agent' if host=='cursor' else host)
            package=ROOT/'dist'
            for case,script,args in cases:
                output=[]
                for ported in (False,True):
                    project=root/(host+'-'+case+('-port' if ported else '-oracle'))
                    project.mkdir()
                    state=project/('.sdlc' if ported else '.specify')
                    if ported:
                        (state/'memory').mkdir(parents=True)
                        (state/'init-options.json').write_text('{"script":"sh","feature_numbering":"sequential"}\n')
                    else:
                        shutil.copytree(baseline/'.specify',state)
                    relative=('.sdlc/' if ported else '')+'specs/001-fixture'
                    feature=project/relative;feature.mkdir(parents=True)
                    (state/'feature.json').write_text(json.dumps({'feature_directory':relative})+'\n')
                    (feature/'spec.md').write_text('Synthetic specification\n')
                    if case not in ('plan','missing-plan'):
                        (feature/'plan.md').write_text('Synthetic plan\n')
                    if case=='required':
                        (feature/'tasks.md').write_text('- [ ] T001 Synthetic task\n')
                    env={k:v for k,v in os.environ.items() if not k.startswith(('SPECIFY_','SDLC_','PYTHON'))}
                    env.update(SDLC_HOST=host,PYTHONDONTWRITEBYTECODE='1')
                    script_dir=(package/'scripts/bash') if ported else state/'scripts/bash'
                    result=subprocess.run(['bash',str(script_dir/script),*args],cwd=project,
                        env=env,capture_output=True,text=True,timeout=20)
                    def normalize(text):
                        if ported: text=reverse_names(text, bare=True)
                        text=text.replace(str(package)+'/templates/',str(project)+'/.specify/templates/')
                        text=text.replace(str(project),'<PROJECT>')
                        text=text.replace('.sdlc/specs/','specs/').replace('.sdlc/','.specify/')
                        text=re.sub(r'(?<![\w./])/?specs/','@SPECS@/',text)
                        text=re.sub(r'(?<![\w:/\$-])sdlc-(constitution|specify|clarify|plan|tasks|analyze|checklist|implement|converge)\b',r'/speckit-\1',text)
                        return text.replace('/sdlc:sdlc-','/speckit-').replace('$sdlc-','$speckit-').replace('/sdlc-','/speckit-').replace('$speckit-','/speckit-')
                    files={p.name:normalize(p.read_text()) for p in feature.iterdir() if p.is_file()}
                    # Upstream script diagnostics use / even for Codex.
                    stderr=normalize(result.stderr).replace('$speckit-','/speckit-')
                    output.append((result.returncode,normalize(result.stdout),stderr,files))
                if output[0]!=output[1]:
                    raise AssertionError(f'Differential mismatch {host}/{case}: {output!r}')
                records.append({'host':host,'case':case,'result':'PASS'})
    return records
