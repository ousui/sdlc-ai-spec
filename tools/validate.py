#!/usr/bin/env python3
"""Local-first checks: quick, one-pass full, strict OS containment, and full-chain e2e."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rls_validation_support import source_state, run_step, write_json, now, redact_receipt, git
BASELINE = '9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9'
PROFILES = ('quick', 'full', 'strict', 'e2e')


def validate(profile: str, source: str, output: Path, *, cache_root: Path | None = None) -> dict:
    output = Path(output).resolve()
    if output.is_relative_to(ROOT): raise ValueError('validation output must be outside source tree')
    result = {'contract':'sdlc-ai-spec/repository-validation/v2','profile':profile,'source_sha':source,
              'success':False,'started_at':now(),'steps':[], 'native_client_gate':'OUT_OF_SCOPE',
              'strict_vfy_execution':'NOT_RUN','real_target_effects':0,'remote_writes':0,'installations':0}
    logs = output.parent/(output.stem+'-logs')
    try:
        if profile not in PROFILES or re.fullmatch(r'[0-9a-f]{40}',source) is None: raise ValueError('invalid profile or exact source SHA')
        before=source_state(ROOT); result['source_before']=before
        if before['sha']!=source or before['status']: raise ValueError('clean exact source checkout required')
        git(ROOT,'merge-base','--is-ancestor',BASELINE,source)
        if profile in ('strict','e2e'):
            from tests.skill_vfy.sandbox_support import probe_sandbox_capability
            result['sandbox_capability']=probe_sandbox_capability()
            if not result['sandbox_capability']['available']: raise ValueError('OS_SANDBOX_UNAVAILABLE: no installation or unsandboxed fallback')
        if profile=='e2e':
            from tools.run_external_rls_integration import PROJECTS
            if cache_root is None: raise ValueError('e2e requires explicit local --project-cache; no automatic network fetch')
            for name, _, _, sha in PROJECTS:
                candidate=Path(cache_root).resolve()/name
                if not candidate.is_dir() or git(candidate,'rev-parse',sha+'^{commit}')!=sha: raise ValueError('fixed local project cache missing: '+name)
        commands = [
            ('runtime-contracts',['tools/validate_runtime_contracts.py']),
            ('skill-interfaces',['tools/validate_skill_interfaces.py']),
            ('skill-style',['tools/validate_skill_style.py']),
            ('inventory',['tools/validate_skill_conformance.py','--json-out',str(logs/'inventory.json')]),
            ('source-locks',['tools/validate_all_skill_source_locks.py','--json-out',str(logs/'source-locks.json')]),
            ('status-static',['tools/validate_sdlc_status.py']),
            ('lifecycle-static',['tools/validate_lifecycle_query.py']),
        ]
        def step(name: str, args: list) -> None:
            receipt=run_step(ROOT,name,[sys.executable,'-B',*map(str,args)],logs,timeout=1800)
            result['steps'].append({k:receipt[k] for k in ('name','exit_code','success','source_unchanged','stdout_log','stderr_log','stdout_sha256','stderr_sha256','duration_ms')})
            write_json(output,result)
            if not receipt['success']: raise ValueError('first failing step: '+name)
        for name,args in commands: step(name,args)
        from tools.test_plan import collect,bindings,execute
        tests=collect(); maps=bindings(tests)
        result['collection']={'unique_tests':len(tests),'registry_cases':{phase:len(rows) for phase,rows in maps.items()},'execution':'NOT_RUN'}
        # The immutable 87-case oracle and all declared IMP helper targets are checked here.
        if profile!='quick':
            started=time.monotonic(); suite=execute(tests,strict=profile in ('strict','e2e'))
            suite['source_sha']=source; suite['duration_ms']=round((time.monotonic()-started)*1000)
            suite=redact_receipt(suite); write_json(logs/'suite.json',suite)
            result['suite']={k:v for k,v in suite.items() if k not in ('log','timings','executed_ids','successful_ids','vfy_strict_observations')}
            result['suite_receipt']=str(logs/'suite.json'); result['collection']['execution']='EXECUTED_ONCE'
            if not suite['success']: raise ValueError('test suite failed; inspect suite.json')
            if profile in ('strict','e2e'): result['strict_vfy_execution']='PASS'
        if profile=='e2e':
            for phase in ('100_req','200_dsn','300_pln','400_imp','500_vfy'):
                step('installed-'+phase,['tools/test_sdlc_'+phase+'_runtime_independence.py'])
            step('rls-installed',['tools/test_sdlc_600_rls_runtime_independence.py','--json-out',logs/'rls-installed.json'])
            # Status installed-copy behavior is already part of the full suite; do not repeat it.
            step('vfy-implementation-review',['tools/review_sdlc_500_vfy_implementation.py'])
            step('external-chain',['tools/run_external_rls_integration.py','--source-sha',source,'--cache-root',cache_root,'--json-out',logs/'external.json'])
            external=json.loads((logs/'external.json').read_text()); result['external']=external
            if external.get('passed')!=2 or external.get('real_target_effects')!=0: raise ValueError('two local sandbox chains did not pass')
        result['source_after']=source_state(ROOT)
        if result['source_after']!=before: raise ValueError('source changed during validation')
        result['success']=True
    except Exception as exc:
        result['error']=str(exc)
    result['finished_at']=now();result=redact_receipt(result);write_json(output,result)
    print('REPOSITORY_'+profile.upper()+' = '+('PASS' if result['success'] else 'FAIL'))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=PROFILES,default='quick')
    parser.add_argument('--source-sha',required=True)
    parser.add_argument('--json-out',type=Path,required=True)
    parser.add_argument('--project-cache',type=Path)
    args=parser.parse_args()
    try: result=validate(args.profile,args.source_sha,args.json_out,cache_root=args.project_cache)
    except ValueError as exc: print(str(exc),file=sys.stderr);raise SystemExit(2)
    raise SystemExit(0 if result['success'] else 1)
