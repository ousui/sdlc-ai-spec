#!/usr/bin/env python3
"""Engineering verification only: source, installed-CLI parity and fixtures.

Does NOT invoke Agents, implement INIT, or run on any real business project.
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

from build import ROOT,COMMANDS,HOSTS,UPSTREAM_SHA,REPOSITORY,VERSION,AUTHOR,render_source,split,build,binding


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
        shell=(r'SDLC_HOST='+host+r' SPECIFY_INIT_DIR="\$\{SDLC_PROJECT_ROOT:\?\}" '
               r'bash "\$\{SDLC_PLUGIN_ROOT:\?\}/scripts/bash/([a-z-]+\.sh)"')
        text=re.sub(shell,r'.specify/scripts/bash/\1',text)
        text=text.replace('.specify/scripts/bash/resolve-template.sh spec-template','specify preset resolve spec-template')
        text=text.replace('${SDLC_PLUGIN_ROOT}/templates/','.specify/templates/')
        text=text.replace('/sdlc:sdlc-','/speckit-').replace('/sdlc-','/speckit-').replace('$sdlc-','$speckit-')
        text=text.replace('/skill:sdlc-','/skill:speckit-').replace('`sdlc.git.commit`','`speckit.git.commit`')
        text=text.replace('.sdlc/specs/','@SPECS@/').replace('.sdlc/','.specify/')
    else:
        text=re.sub(r'(?<![\w./])/?specs/','@SPECS@/',text)
    return text


def template_norm(text: str) -> str:
    text=text.replace('.sdlc/specs/','@SPECS@/')
    text=re.sub(r'(?<![\w./])/?specs/','@SPECS@/',text)
    return text.replace('/sdlc:sdlc-','/speckit-').replace('/sdlc-','/speckit-').replace('$sdlc-','$speckit-')


def require_equal(a,b,label):
    if a!=b:
        if isinstance(a,str) and isinstance(b,str):
            diff=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='expected',tofile='actual'))
        else:diff=repr((a,b))
        raise AssertionError(label+'\n'+diff[:6000])


def verify(upstream:Path,baselines:Path,evidence:Path)->dict:
    evidence.mkdir(parents=True,exist_ok=True)
    (evidence/"failure.txt").unlink(missing_ok=True)
    (evidence/"result.json").unlink(missing_ok=True)
    checks=[]
    def passed(group,item):
        checks.append({'group':group,'item':item,'result':'PASS'})
        print('PASS:',group,item,flush=True)
    lock=json.loads((ROOT/'upstream.lock.json').read_text())
    require_equal(lock['commit'],UPSTREAM_SHA,'Pinned SHA')
    for source,record in lock['files'].items():
        require_equal(digest(upstream/source),record['sha256'],'Upstream source '+source)
        passed('pinned_source',source)
    for command in COMMANDS:
        require_equal((ROOT/'src/commands'/f'{command}.md').read_bytes(),
                      (upstream/'templates/commands'/f'{command}.md').read_bytes(),'English command source '+command)
        passed('unchanged_source_command',command)
    for host,integ,folder in [('codex','codex','.agents'),('claude','claude','.claude'),('cursor','cursor-agent','.cursor')]:
        base=baselines/integ
        package=ROOT/'dist'/host
        actual_skills={p.parent.name for p in (package/'skills').glob('*/SKILL.md')}
        require_equal(actual_skills,{'sdlc-'+c for c in COMMANDS},'Skill inventory '+host)
        for name in COMMANDS:
            native=base/folder/'skills'/('speckit-'+name)/'SKILL.md'
            oracle_meta,oracle_body=split(native.read_text())
            rendered=render_source((ROOT/'src/commands'/f'{name}.md').read_text(),name,host)
            require_equal(rendered,(oracle_meta,oracle_body),'Source renderer vs installed CLI '+host+'/'+name)
            passed('source_renderer_vs_installed_cli',host+'/'+name)
            meta,body=split((package/'skills'/('sdlc-'+name)/'SKILL.md').read_text())
            expected_meta=dict(oracle_meta,name='sdlc-'+name,
                compatibility='Requires an initialized .sdlc project, Bash and Python 3.9+; INIT is not included in this engineering build')
            require_equal(meta,expected_meta,'Native metadata '+host+'/'+name)
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
        manifest=package/('.claude-plugin/plugin.json' if host=='claude' else 'plugin.json')
        m=json.loads(manifest.read_text())
        require_equal(m['name'],'sdlc','Plugin name')
        require_equal(m['repository'],REPOSITORY,'Fixed repository')
        require_equal(m['version'],VERSION,'Version')
        require_equal(m['author'],AUTHOR,'Plugin author')
        allowed={'name','version','description','repository','license','author'}
        if host!='claude':
            allowed.add('$schema')
            require_equal(m['$schema'],'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json','Schema identifier')
        require_equal(set(m),allowed,'Documented manifest subset')
        passed('manifest_documented_subset',host)
        if host!='claude':
            from jsonschema import Draft202012Validator
            schema=json.loads((ROOT/'tests/agent-plugins-1.0.0.schema.json').read_text())
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(m)
            passed('official_portable_manifest_schema',host)
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
        if (package/'skills/sdlc-init').exists() or (package/'hooks').exists():
            raise AssertionError('INIT or hooks unexpectedly shipped')
        for f in (package/'scripts').rglob('*'):
            if f.is_file():
                text=f.read_text()
                if re.search(r'(?m)^\s*(?:from\s+specify_cli\b|import\s+specify_cli\b|(?:exec\s+)?specify\s)',text):
                    raise AssertionError('CLI runtime dependency '+str(f))
        passed('runtime_dependency_and_inventory',host)
    # Unmodified leaf scripts remain exact except the project marker.
    for name in ('check-prerequisites.sh','resolve-template.sh','setup-plan.sh'):
        expected=(upstream/'scripts/bash'/name).read_text().replace('.specify','.sdlc')
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
    passed('reproducible_build','all three packages')
    spec=importlib.util.spec_from_file_location('sdlc_runtime_tests',ROOT/'tests/test_runtime.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    (evidence/'runtime-tests.txt').write_text(stream.getvalue())
    print(stream.getvalue())
    if not result.wasSuccessful():raise AssertionError('Synthetic runtime fixture tests failed')
    passed('synthetic_runtime_tests',str(result.testsRun)+' test methods (mostly parameterized over three packages)')
    repo_spec=importlib.util.spec_from_file_location('sdlc_repository_tests',ROOT/'tests/test_repository.py')
    repo_module=importlib.util.module_from_spec(repo_spec);repo_spec.loader.exec_module(repo_module)
    repo_stream=io.StringIO()
    repo_result=unittest.TextTestRunner(stream=repo_stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(repo_module))
    (evidence/'repository-tests.txt').write_text(repo_stream.getvalue())
    print(repo_stream.getvalue())
    if not repo_result.wasSuccessful():raise AssertionError('Repository layout/metadata tests failed')
    passed('repository_layout_metadata_tests',str(repo_result.testsRun)+' test methods')
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
    source_id=os.environ.get('GITHUB_SHA')
    report={'status':'PASS','scope':'engineering-only; synthetic fixtures; no INIT or Agent execution',
            'source_sha':source_id,'upstream_sha':UPSTREAM_SHA,
            'source_repository':os.environ.get('GITHUB_REPOSITORY'),
            'product_version':VERSION,'declared_repository':REPOSITORY,'author':AUTHOR['name'],
            'repository_test_methods':repo_result.testsRun,
            'environment':{'python':sys.version,'platform':platform.platform(),
                'bash':subprocess.run(['bash','--version'],capture_output=True,text=True).stdout.splitlines()[0]},
            'checks':checks,'runtime_test_methods':result.testsRun,'differential_cases':len(differential_cases),
            'distribution_inventory':inventory(ROOT/'dist'),
            'not_performed':['INIT skill construction','native plugin installation/discovery','LLM workflow execution',
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
