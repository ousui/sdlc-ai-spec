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
from localize import restore_template


def normalize_project_paths(text: str, project: Path) -> str:
    """Collapse logical and physical spellings of one project to <PROJECT>.

    macOS commonly exposes temporary directories as /var/... while physical
    resolution returns /private/var/.... Upstream and ported scripts are both
    allowed to canonicalize filesystem paths, so the differential verifier must
    compare path identity rather than the platform-specific spelling. This only
    normalizes the selected synthetic project root; unrelated paths are untouched.
    """
    forms={str(project)}
    try:
        forms.add(str(project.resolve()))
    except OSError:
        pass
    # Replace only a complete path occurrence or a path prefix followed by a
    # separator/output delimiter. Do not rewrite unrelated same-prefix paths such
    # as /tmp/project-backup when the selected project is /tmp/project.
    boundary = r'(?=$|[\/\s"\',;:)}\]])'
    for value in sorted(forms,key=len,reverse=True):
        text=re.sub(re.escape(value)+boundary,'<PROJECT>',text)
    return text


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
        ('explicit-plan','setup-plan.sh',('--json',)),
        ('explicit-plan-no-persist','setup-plan.sh',('--json',)),
        ('dot-paths','check-prerequisites.sh',('--json','--paths-only')),
        ('dot-slash-paths','check-prerequisites.sh',('--json','--paths-only')),
        ('dot-plan','setup-plan.sh',('--json',)),
        ('dot-slash-plan','setup-plan.sh',('--json',)),
        ('invalid-selection','check-prerequisites.sh',('--json','--paths-only')),
        ('explicit-missing-feature','check-prerequisites.sh',('--json','--require-spec')),
        ('store-dot-paths','check-prerequisites.sh',('--json','--paths-only')),
        ('store-dot-plan','setup-plan.sh',('--json',)),
        ('store-dot-no-persist','setup-plan.sh',('--json',)),
        ('store-absolute-dot-plan','setup-plan.sh',('--json',)),
        ('store-leading-dot-plan','setup-plan.sh',('--json',)),
        ('store-trailing-slash-plan','setup-plan.sh',('--json',)),
        ('store-repeated-slash-plan','setup-plan.sh',('--json',)),
        ('alias-prerequisite-noop','check-prerequisites.sh',('--json',)),
        ('alias-plan-noop','setup-plan.sh',('--json',)),
        ('alias-explicit-root-plan','setup-plan.sh',('--json',)),
        ('alias-physical-plan','setup-plan.sh',('--json',)),
        ('alias-no-persist','setup-plan.sh',('--json',)),
        ('alias-paths-only','check-prerequisites.sh',('--json','--paths-only')),
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
                    if case.startswith('dot-'):
                        relative = './' if case.startswith('dot-slash-') else '.'
                    if case.startswith('store-'):
                        relative += ('/' if case == 'store-trailing-slash-plan' else
                                     '//' if case == 'store-repeated-slash-plan' else '/.')
                        if case == 'store-leading-dot-plan':
                            relative = './' + relative
                        if case == 'store-absolute-dot-plan':
                            # Auto-discovery uses the physical cwd. Keep this explicit
                            # absolute value in the same spelling for the upstream oracle.
                            relative = str(project.resolve()) + '/' + relative
                    alias = project.with_name(project.name + '-alias')
                    if case.startswith('alias-'):
                        alias.symlink_to(project, target_is_directory=True)
                        prefix_path = project.resolve() if case == 'alias-physical-plan' else alias
                        relative = str(prefix_path) + '/' + relative + '/.'
                    feature=project/relative;feature.mkdir(parents=True, exist_ok=True)
                    selection = state/'feature.json'
                    previous = case.startswith('store-') or case in ('alias-explicit-root-plan', 'alias-no-persist', 'alias-paths-only')
                    selection.write_text('{invalid\n' if case.startswith('explicit-plan') or case == 'invalid-selection'
                                         else json.dumps({'feature_directory':'previous' if previous else relative})+'\n')
                    selection_before = selection.read_bytes(), selection.stat().st_mtime_ns
                    (feature/'spec.md').write_text('Synthetic specification\n')
                    if (script != 'setup-plan.sh' and case != 'missing-plan') or case.startswith('alias-'):
                        (feature/'plan.md').write_text('Synthetic plan\n')
                    if case=='required':
                        (feature/'tasks.md').write_text('- [ ] T001 Synthetic task\n')
                    env={k:v for k,v in os.environ.items() if not k.startswith(('SPECIFY_','SDLC_','PYTHON'))}
                    env.update(SDLC_HOST=host,PYTHONDONTWRITEBYTECODE='1')
                    prefix = 'SDLC_' if ported else 'SPECIFY_'
                    if case.startswith(('explicit-', 'dot-', 'store-', 'alias-')):
                        env[prefix + 'FEATURE_DIRECTORY'] = relative + '-missing' if case == 'explicit-missing-feature' else relative
                    if case in ('alias-explicit-root-plan', 'alias-physical-plan'):
                        env[prefix + 'INIT_DIR'] = str(alias)
                    if case in ('explicit-plan-no-persist', 'store-dot-no-persist', 'alias-no-persist'):
                        env[prefix + 'FEATURE_NO_PERSIST'] = '1'
                    script_dir=(package/'scripts/bash') if ported else state/'scripts/bash'
                    result=subprocess.run(['bash',str(script_dir/script),*args],cwd=project,
                        env=env,capture_output=True,text=True,timeout=20)
                    def normalize(text):
                        if ported: text=reverse_names(text, bare=True)
                        text=text.replace(str(package)+'/templates/',str(project)+'/.specify/templates/')
                        text=normalize_project_paths(text,project)
                        if case.startswith('alias-'):
                            text=normalize_project_paths(text,alias)
                        text=text.replace('.sdlc/specs/','specs/').replace('.sdlc/','.specify/')
                        text=re.sub(r'(?<![\w./])/?specs/','@SPECS@/',text)
                        text=re.sub(r'(?<![\w:/\$-])sdlc-(constitution|specify|clarify|plan|tasks|analyze|checklist|implement|converge)\b',r'/speckit-\1',text)
                        return text.replace('/sdlc:sdlc-','/speckit-').replace('$sdlc-','$speckit-').replace('/sdlc-','/speckit-').replace('$speckit-','/speckit-')
                    files={}
                    for p in feature.iterdir():
                        if p.is_file():
                            text=p.read_text()
                            # Alias cases start with an existing synthetic plan;
                            # only newly copied templates need localization reversal.
                            if ported and script == 'setup-plan.sh' and p.name == 'plan.md' and not case.startswith('alias-'):
                                text=restore_template('plan-template',text)
                            files[p.name]=normalize(text)
                    stdout=result.stdout
                    if ported and result.returncode == 0 and case in ('tasks','template'):
                        payload=json.loads(stdout)
                        key='TASKS_TEMPLATE_CONTENT' if case == 'tasks' else 'TEMPLATE_CONTENT'
                        name='tasks-template' if case == 'tasks' else 'checklist-template'
                        payload[key]=restore_template(name,payload[key])
                        # Compare JSON values, not encoder spacing/key order.
                        stdout=json.dumps(payload,ensure_ascii=False,sort_keys=True)
                    elif not ported and result.returncode == 0 and case in ('tasks','template'):
                        stdout=json.dumps(json.loads(stdout),ensure_ascii=False,sort_keys=True)
                    # Upstream script diagnostics use / even for Codex.
                    stderr=normalize(result.stderr).replace('$speckit-','/speckit-')
                    selection_preserved = (selection.read_bytes(), selection.stat().st_mtime_ns) == selection_before
                    output.append((result.returncode,normalize(stdout),stderr,files,
                                   normalize(selection.read_text()),selection_preserved))
                if output[0]!=output[1]:
                    raise AssertionError(f'Differential mismatch {host}/{case}: {output!r}')
                records.append({'host':host,'case':case,'result':'PASS'})
    return records
