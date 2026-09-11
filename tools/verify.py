#!/usr/bin/env python3
"""Engineering verification only: source, installed-CLI parity and fixtures.

Exercises project INIT only on disposable synthetic fixtures; never invokes Agents or real business projects.
"""
from __future__ import annotations
import argparse
import ast
import difflib
import hashlib
import importlib.util
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from build import ROOT,COMMANDS,HOSTS,UPSTREAM_SHA,REPOSITORY,VERSION,AUTHOR,render_source,split,build,binding,ALL_COMMANDS,CORE_COMPATIBILITY,skill_entry,manifest_skills
from localize import english_body,localized_workflow,translated_metadata,check_all
from naming import product_prose


from naming_check import EXPECTED, reverse_names, leaf_projection


def digest(path: Path) -> str:return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path) -> dict:
    return {str(p.relative_to(root)):{'sha256':digest(p),'mode':oct(p.stat().st_mode&0o777)}
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def normalize(text: str,host: str, *, ported: bool) -> str:
    """Independent comparison projection; only allowlisted address changes.

    No paragraphs, business words, sections, punctuation or whitespace are
    stripped. Unexpected prose is a failing difference, not a normalization.
    """
    if ported:
        prefix='\n'+binding(host)
        if not text.startswith(prefix):raise AssertionError('Package binding is missing or modified')
        text=text[len(prefix):]
        shell=(r'SDLC_HOST='+host+r' SDLC_INIT_DIR="\$\{SDLC_PROJECT_ROOT:\?\}" '
               r'bash "\$\{SDLC_PLUGIN_ROOT:\?\}/scripts/bash/([a-z-]+\.sh)"')
        text=re.sub(shell,r'.specify/scripts/bash/\1',text)
        text=text.replace('.specify/scripts/bash/resolve-template.sh spec-template','specify preset resolve spec-template')
        text=text.replace('${SDLC_PLUGIN_ROOT}/templates/','.specify/templates/')
        text=reverse_names(text)
        text=text.replace('/sdlc-ai-spec:sdlc-git-commit','/speckit-git-commit')
        text=text.replace('/sdlc:sdlc-','/speckit-').replace('/sdlc-','/speckit-').replace('$sdlc-','$speckit-')
        text=text.replace('/skill:sdlc-','/skill:speckit-').replace('`sdlc.git.commit`','`speckit.git.commit`')
        text=text.replace('.sdlc/specs/','@SPECS@/').replace('.sdlc/','.specify/')
    else:
        text=re.sub(r'(?<![\w./])/?specs/','@SPECS@/',text)
    return text


def template_norm(text: str) -> str:
    text=reverse_names(text, bare=True)
    text=text.replace('.sdlc/specs/','@SPECS@/')
    text=re.sub(r'(?<![\w./])/?specs/','@SPECS@/',text)
    text=re.sub(r'(?<![\w:/\$-])sdlc-(constitution|specify|clarify|plan|tasks|analyze|checklist|implement|converge)\b',r'/speckit-\1',text)
    return text.replace('/sdlc:sdlc-','/speckit-').replace('/sdlc-','/speckit-').replace('$sdlc-','$speckit-').replace('$speckit-','/speckit-')


def require_equal(a,b,label):
    if a!=b:
        if isinstance(a,str) and isinstance(b,str):
            diff=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='expected',tofile='actual'))
        else:diff=repr((a,b))
        raise AssertionError(label+'\n'+diff[:6000])


def verify(upstream:Path,baselines:Path,evidence:Path)->dict:
    if evidence.resolve() == ROOT or ROOT in evidence.resolve().parents:
        raise ValueError('Evidence must be outside the source checkout')
    evidence.mkdir(parents=True,exist_ok=True)
    (evidence/"failure.txt").unlink(missing_ok=True)
    (evidence/"result.json").unlink(missing_ok=True)
    checks=[]
    def passed(group,item):
        checks.append({'group':group,'item':item,'result':'PASS'})
        print('PASS:',group,item,flush=True)
    lock=json.loads((ROOT/'upstream.lock.json').read_text())
    require_equal(lock['commit'],UPSTREAM_SHA,'Pinned SHA')
    for source,record in {**lock['files'], **lock.get('watch_files', {})}.items():
        require_equal(digest(upstream/source),record['sha256'],'Upstream source '+source)
        passed('pinned_source',source)
    for command in COMMANDS:
        require_equal((ROOT/'src/upstream/templates/commands'/f'{command}.md').read_bytes(),
                      (upstream/'templates/commands'/f'{command}.md').read_bytes(),'English command source '+command)
        passed('unchanged_source_command',command)
    for host,integ,folder in [('codex','codex','.agents'),('claude','claude','.claude'),('cursor','cursor-agent','.cursor')]:
        base=baselines/integ
        package=ROOT/'dist'
        actual_skills={p.parent.name for directory in (package/'skills',package/'adapters'/host/'skills') for p in directory.glob('*/SKILL.md')}
        require_equal(actual_skills,set(EXPECTED.values()),'Skill inventory '+host)
        for name in COMMANDS:
            native=base/folder/'skills'/('speckit-'+name)/'SKILL.md'
            oracle_meta,oracle_body=split(native.read_text())
            rendered=render_source((ROOT/'src/upstream/templates/commands'/f'{name}.md').read_text(),name,host)
            require_equal(rendered,(oracle_meta,oracle_body),'Source renderer vs installed CLI '+host+'/'+name)
            passed('source_renderer_vs_installed_cli',host+'/'+name)
            meta,entry=split(skill_entry(package,host,name).read_text())
            loader=subprocess.run([sys.executable,'-I','-B',str(package/'scripts/python/load_workflow.py'),'--host',host,'--skill',EXPECTED[name]],capture_output=True,text=True,check=True)
            body='\n'+binding(host)+english_body(name,host)
            require_equal(loader.stdout,localized_workflow(name,host),'Localized complete workflow '+host+'/'+name)
            passed('localized_workflow_source_binding',host+'/'+name)
            if '--host "${SDLC_HOST:?}" --skill '+EXPECTED[name] not in entry or 'COMPLETE stdout' not in entry:
                raise AssertionError('Thin entrypoint does not bind the full workflow')
            # Compare native behavior first: common core defaults must preserve
            # each host's original policy. UI hints do not control invocation.
            require_equal(meta.get('user-invocable',True),oracle_meta.get('user-invocable',True),'User invocation '+host+'/'+name)
            require_equal(meta.get('disable-model-invocation',False),oracle_meta.get('disable-model-invocation',False),'Implicit invocation '+host+'/'+name)
            common,_=render_source((ROOT/'src/upstream/templates/commands'/f'{name}.md').read_text(),name,'claude')
            common.update(name=EXPECTED[name],compatibility=CORE_COMPATIBILITY)
            for field in ('description','argument-hint'):
                if field in common:common[field]=product_prose(common[field])
            expected_meta=translated_metadata(name,common)
            require_equal(meta,expected_meta,'Shared localized metadata '+host+'/'+name)
            require_equal(normalize(oracle_body,host,ported=False),normalize(body,host,ported=True),'Migrated body '+host+'/'+name)
            # Negative control proves normalization cannot hide a prose mutation.
            mutated=body+'\nUNAPPROVED BUSINESS RULE\n'
            if normalize(mutated,host,ported=True)==normalize(oracle_body,host,ported=False):
                raise AssertionError('Normalization hides business changes')
            for token in ('{SCRIPT}','{ARGS}','__SPECKIT_COMMAND_','__AGENT__'):
                if token in body:raise AssertionError('Unrendered token '+token)
            passed('migrated_skill_vs_installed_cli',host+'/'+name)
        for template in sorted((package/'templates').glob('*.md')):
            native=base/'.specify/templates'/template.name
            require_equal(template_norm(native.read_text()),template_norm(template.read_text()),'Template parity '+host+'/'+template.name)
            passed('template_vs_installed_cli',host+'/'+template.name)
        manifest=package/('.'+host+'-plugin/plugin.json')
        m=json.loads(manifest.read_text())
        require_equal(m['name'],'sdlc-ai-spec','Plugin name')
        require_equal(m['repository'],REPOSITORY,'Fixed repository')
        require_equal(m['version'],VERSION,'Version')
        require_equal(m['author'],AUTHOR,'Plugin author')
        require_equal(m['skills'],manifest_skills(host),'Shared core and host INIT selection')
        require_equal(set(m),{'name','version','description','repository','license','author','skills'},'Native minimal manifest fields')
        if (package/'plugin.json').exists() or not (package/'skills').is_dir():
            raise AssertionError('Missing shared core or ambiguous portable root manifest')
        passed('native_manifest_documented_subset',host)
        for f in package.rglob('*'):
            if f.is_symlink():raise AssertionError('Package symlink '+str(f))
            if f.is_file():
                if '__pycache__' in f.parts or f.suffix in ('.pyc','.pyo'):raise AssertionError('Cache shipped')
                if f.suffix=='.sh':
                    subprocess.run(['bash','-n',str(f)],check=True,capture_output=True,text=True)
                    passed('bash_syntax',host+'/'+f.name)
                if f.suffix=='.py':
                    ast.parse(f.read_text(),filename=str(f))
                    passed('python_syntax',host+'/'+f.name)
        if (package/'hooks').exists():
            raise AssertionError('Hooks unexpectedly shipped')
        for f in (package/'scripts').rglob('*'):
            if f.is_file():
                text=f.read_text()
                if re.search(r'(?m)^\s*(?:from\s+specify_cli\b|import\s+specify_cli\b|(?:exec\s+)?specify\s)',text):
                    raise AssertionError('CLI runtime dependency '+str(f))
        passed('runtime_dependency_and_inventory',host)
    check_all()
    passed('localization_freshness_and_protected_spans','nine complete Chinese workflows')
    # Compare only the declared project-data projection of real CLI init outputs.
    # Integration registries, scripts and templates are intentionally not copied.
    with tempfile.TemporaryDirectory(prefix='sdlc-init-parity-') as temp:
        for integ in ('codex','claude','cursor-agent'):
            project = Path(temp) / integ
            project.mkdir()
            process = subprocess.run([sys.executable,'-I','-B',str(ROOT/'dist/scripts/python/init_project.py'),
                '--project',str(project),'--json'],capture_output=True,text=True,check=True)
            require_equal(json.loads(process.stdout)['status'],'initialized','Init status '+integ)
            original = baselines/integ/'.specify'
            actual = project/'.sdlc'
            require_equal((actual/'memory/constitution.md').read_bytes(),
                (original/'memory/constitution.md').read_bytes(),'CLI init constitution '+integ)
            old_opts=json.loads((original/'init-options.json').read_text())
            new_opts=json.loads((actual/'init-options.json').read_text())
            for key in ('script','feature_numbering','speckit_version'):
                require_equal(new_opts[key],old_opts[key],'CLI init project setting '+integ+'/'+key)
            for name in ('scripts','skills','integrations','feature.json'):
                if (actual/name).exists():raise AssertionError('Init copied non-project resource '+name)
            passed('installed_init_project_data',integ)
    # Unmodified leaf scripts remain exact except the project marker.
    for name in ('check-prerequisites.sh','resolve-template.sh','setup-plan.sh'):
        expected=leaf_projection((upstream/'scripts/bash'/name).read_text())
        require_equal((ROOT/'src/scripts/bash'/name).read_text(),expected,'Leaf script preservation '+name)
        passed('leaf_script_source_parity',name)
    from port import port_script
    for script in (upstream/'scripts/bash').glob('*.sh'):
        require_equal((ROOT/'src/scripts/bash'/script.name).read_text(),port_script(script.name,script.read_text()),'Script derivation '+script.name)
        passed('reviewed_script_transform',script.name)
    for f in (ROOT/'tools').glob('*.py'):
        ast.parse(f.read_text(),filename=str(f));passed('tool_python_syntax',f.name)
    # Rebuild from source into a marked fresh directory, not from CLI output.
    with tempfile.TemporaryDirectory(prefix='sdlc-build-check-') as temp:
        out=Path(temp)/'dist'
        build(out)
        require_equal(inventory(ROOT/'dist'),inventory(out),'Reproducible distribution')
    passed('reproducible_build','one self-contained package')
    sys.path.insert(0,str(ROOT/'tools'))
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_*.py')
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (evidence/'unit-tests.txt').write_text(stream.getvalue())
    print(stream.getvalue())
    if not result.wasSuccessful():raise AssertionError('Engineering unit tests failed')
    passed('engineering_unit_tests',str(result.testsRun)+' test methods')
    from differential import compare
    differential_cases=compare(baselines)
    (evidence/'differential-tests.json').write_text(json.dumps(differential_cases,indent=2)+'\n')
    for case in differential_cases:
        passed('installed_script_differential',case['host']+'/'+case['case'])
    # Save exact migration source deltas for human review, not an all-green substitute.
    diffs=[]
    for f in sorted((ROOT/'src/scripts/bash').glob('*.sh')):
        original=upstream/'scripts/bash'/f.name
        old=original.read_text() if original.exists() else ''
        diffs.extend(difflib.unified_diff(old.splitlines(True),f.read_text().splitlines(True),
                      fromfile='upstream/scripts/bash/'+f.name,tofile='ported/scripts/bash/'+f.name))
    (evidence/'script-deltas.patch').write_text(''.join(diffs))
    from upgrade import source_digest
    source_id=os.environ.get('GITHUB_SHA')
    report={'status':'PASS','scope':'engineering-only; one package, installed-tool parity and synthetic fixtures including project INIT; no Agent execution',
            'source_sha':source_id,'source_digest':source_digest(ROOT),'upstream_sha':UPSTREAM_SHA,
            'source_repository':os.environ.get('GITHUB_REPOSITORY'),
            'product_version':VERSION,'declared_repository':REPOSITORY,'author':AUTHOR['name'],
            'unit_test_methods':result.testsRun,
            'environment':{'python':sys.version,'platform':platform.platform(),
                'bash':subprocess.run(['bash','--version'],capture_output=True,text=True).stdout.splitlines()[0]},
            'checks':checks,'runtime_test_methods':result.testsRun,'differential_cases':len(differential_cases),
            'distribution_inventory':inventory(ROOT/'dist'),
            'not_performed':['native plugin installation/discovery','LLM workflow execution',
                             'real project verification','macOS runtime verification','Windows/PowerShell verification']}
    (evidence/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',required=True,type=Path)
    p.add_argument('--baselines',required=True,type=Path)
    p.add_argument('--evidence',required=True,type=Path)
    args=p.parse_args()
    try:
        report=verify(args.upstream.resolve(),args.baselines.resolve(),args.evidence.resolve())
    except Exception as error:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/'failure.txt').write_text(str(error)+'\n')
        raise
    print('ENGINEERING PASS:',len(report['checks']),'checks;',report['runtime_test_methods'],'fixture test methods')
