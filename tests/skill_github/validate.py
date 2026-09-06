#!/usr/bin/env python3
"""Single fixed entry: offline, real loopback protocol, prepare, live, native, client."""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from packages.sdlc_github.models import GithubError

CODE_PATHS=('packages','scripts','skills','config','tools','tests','.github','.codex-plugin','.cursor-plugin','.claude-plugin','AGENTS.md','.gitignore')


def git(*args):
    value=subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,text=True,timeout=30)
    if value.returncode:raise ValueError('Git source binding unavailable')
    return value.stdout.strip()


def metadata(expected_sha=None):
    head=git('rev-parse','HEAD')
    dirty=bool(git('status','--porcelain','--',*CODE_PATHS))
    if expected_sha:
        if git('rev-parse',expected_sha+'^{commit}')!=expected_sha:raise ValueError('Exact 40-character implementation SHA required')
        if git('diff','--name-only',expected_sha,'--',*CODE_PATHS) or dirty:
            raise ValueError('Runtime/test/build sources differ from pinned implementation SHA')
    files={}
    for relative in CODE_PATHS:
        base=ROOT/relative
        for path in ([base] if base.is_file() else sorted(base.rglob('*'))):
            if not path.is_file() or any(x in {'__pycache__','.local','.cache','.git'} for x in path.parts) or path.suffix in {'.pyc','.pyo'}:continue
            if path.is_symlink():raise ValueError('Linked validation source is not accepted')
            files[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return {'implementation_sha':expected_sha or (None if dirty else head),'code_head':head,'dirty_source':dirty,
            'source_scope':'working-tree digest' if dirty else 'pinned commit' if expected_sha else 'HEAD',
            'source_files_sha256':files,'dependency_lock_sha256':hashlib.sha256((ROOT/'packages/sdlc_github/requirements.lock').read_bytes()).hexdigest(),
            'python':platform.python_version(),'platform':platform.system(),'mcp':importlib.metadata.version('mcp')}


class RecordingResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.rows=[]
    def addSuccess(self,test):super().addSuccess(test);self.rows.append({'id':test.id(),'status':'PASS'})
    def addFailure(self,test,err):super().addFailure(test,err);self.rows.append({'id':test.id(),'status':'FAIL','kind':'assertion'})
    def addError(self,test,err):super().addError(test,err);self.rows.append({'id':test.id(),'status':'FAIL','kind':'error'})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.rows.append({'id':test.id(),'status':'BLOCKED','reason':reason})
    def addSubTest(self,test,subtest,err):
        super().addSubTest(test,subtest,err)
        if err is not None:self.rows.append({'id':subtest.id(),'status':'FAIL','kind':'subtest'})


def run_tests(layer,output):
    modules=['tests.skill_github.test_offline','tests.skill_github.test_installation','tests.skill_github.test_client'] if layer=='offline' else ['tests.skill_github.test_protocol']
    from unittest.mock import patch
    stream=io.StringIO();start=time.monotonic()
    env={'SDLC_GITHUB_TOKEN':'','SDLC_GITHUB_TOKEN_B':'','SDLC_GITHUB_TEST_EVIDENCE':str(output/'protocol-evidence')}
    with patch.dict(os.environ,env):
        suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordingResult).run(suite)
    (output/'unittest.log').write_text(stream.getvalue())
    return {'layer':layer,'status':'FAIL' if not result.wasSuccessful() else 'BLOCKED' if result.skipped else 'PASS',
            'tests_run':result.testsRun,'passed':sum(r['status']=='PASS' for r in result.rows),'rows':result.rows,
            'duration_seconds':round(time.monotonic()-start,3),'exit_code':1 if not result.wasSuccessful() else 2 if result.skipped else 0}


def prepare(output,meta):
    from tests.skill_github.native_evidence import HOSTS,template
    from tools.validate_sdlc_github_source_lock import validate
    validate()
    native=output/'native-templates';native.mkdir(exist_ok=True)
    for host in HOSTS:
        path=native/(host+'.json')
        if not path.exists():path.write_text(json.dumps(template(host,meta['implementation_sha'],meta['dependency_lock_sha256']),ensure_ascii=False,indent=2)+'\n')
    workspace=output/'workspace'
    manifest=output/'WORKSPACE-SHA256.json'
    if workspace.exists():
        if not manifest.is_file():raise ValueError('Existing unowned workspace cannot be reused')
        expected=json.loads(manifest.read_text())
        actual={p.relative_to(workspace).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(workspace.rglob('*')) if p.is_file()}
        if actual!=expected:raise ValueError('Synthetic workspace changed; preserve evidence rather than overwrite')
    else:
        workspace.mkdir()
        for number in range(10000):
            file=workspace/str(number//100)/('fixture-'+str(number)+'.txt')
            file.parent.mkdir(exist_ok=True)
            file.write_text('Rebuildable SDLC GitHub native fixture '+str(number)+'\n')
        hashes={p.relative_to(workspace).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(workspace.rglob('*')) if p.is_file()}
        manifest.write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n')
    return {'layer':'prepare' ,'status':'PASS','live_status':'NOT_RUN','native_status':'NOT_RUN',
            'required_local_inputs':['Exact runtime SHA','Host-installed Python with the hashed dependency lock','SDLC_GITHUB_TOKEN in host environment',
              'Explicit fixture repository/existing head/base and Actions run','Existing Tag/Release fixture, or record BLOCKED','Native host execution and original sanitized transcripts'],
            'note':'Preparation does not validate PAT permissions or native behavior.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layer',choices=['offline','integration','prepare','live','identity','native','client'],required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--implementation-sha')
    p.add_argument('--fixture',type=Path)
    p.add_argument('--data-root',type=Path)
    p.add_argument('--allow-test-writes',action='store_true')
    p.add_argument('--native-evidence',type=Path)
    args=p.parse_args(argv)
    from tools.install_sdlc_github import safe_path
    output=safe_path(args.output.absolute());output.mkdir(parents=True,exist_ok=True,mode=0o700)
    try:
        meta=metadata(args.implementation_sha)
        if args.layer in {'live','identity','native','client'} and not args.implementation_sha:
            raise ValueError('Live/native/client batch requires an exact implementation SHA')
        layers=['offline','integration','live','identity','native'] if args.layer=='client' else [args.layer]
        results=[]
        for layer in layers:
            folder=output/layer;folder.mkdir(exist_ok=True)
            if layer in {'offline','integration'}:
                value=run_tests(layer,folder)
            elif layer=='prepare':value=prepare(folder,meta)
            elif layer=='live':
                if any(x['status']!='PASS' for x in results):value={'layer':layer,'status':'BLOCKED','reason':'Offline/protocol prerequisite failed'}
                elif not args.fixture or not args.data_root:value={'layer':layer,'status':'BLOCKED','reason':'--fixture and explicit existing --data-root required'}
                else:
                    from tests.skill_github.client import run_live
                    value=asyncio.run(run_live(args.fixture,folder,data_root=args.data_root,allow_writes=args.allow_test_writes))
            elif layer=='identity':
                if not args.fixture or not args.data_root:value={'layer':layer,'status':'BLOCKED','reason':'Explicit fixture and stable data root required'}
                else:
                    from tests.skill_github.client import run_identity,fixture_config
                    value=asyncio.run(run_identity(folder,data_root=args.data_root,repository=fixture_config(args.fixture)['repository']))
            else:
                if not args.native_evidence:value={'layer':layer,'status':'BLOCKED','reason':'Three original native host evidence bundles are required; SDK tests are not substitutes'}
                else:
                    from tests.skill_github.native_evidence import validate_native
                    value=validate_native(args.native_evidence,args.implementation_sha,meta['dependency_lock_sha256'])
            results.append(value)
        status='FAIL' if any(x['status']=='FAIL' for x in results) else 'BLOCKED' if any(x['status']=='BLOCKED' for x in results) else 'PASS'
        report={'contract':'sdlc-ai-spec/github-validation/v1','status':status,'metadata':meta,'layers':results}
    except (ValueError,OSError,importlib.metadata.PackageNotFoundError,GithubError):
        report={'contract':'sdlc-ai-spec/github-validation/v1','status':'BLOCKED','reason':'Verify exact source binding, dependency lock, fixture schema, and explicit paths; no fallback was attempted.'}
    from packages.sdlc_github.models import redact
    report=redact(report,os.environ.get('SDLC_GITHUB_TOKEN',''))
    (output/'VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    sums={f.relative_to(output).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(output.rglob('*')) if f.is_file() and f.name!='SHA256SUMS.json'}
    (output/'SHA256SUMS.json').write_text(json.dumps(sums,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'report':str(output/'VALIDATION.json'),'layers':[{k:x[k] for k in ('layer','status','tests_run','passed') if k in x} for x in report.get('layers',[])]},ensure_ascii=False))
    return 0 if report['status']=='PASS' else 2 if report['status']=='BLOCKED' else 1


if __name__=='__main__':raise SystemExit(main())
