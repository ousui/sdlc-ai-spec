#!/usr/bin/env python3
"""Same-version engineering rehearsal of candidate/verify/accept-check.

Does not accept a release, commit the candidate, push or run a business project.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from upgrade import ROOT,prepare,accept,source_digest,run


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',type=Path,required=True)
    p.add_argument('--baselines',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    out=args.out.resolve()
    if out.exists() or ROOT == out or ROOT in out.parents:
        raise ValueError('Rehearsal output must be a new directory outside the repository')
    out.mkdir(parents=True)
    before=source_digest(ROOT)
    locked=json.loads((ROOT/'upstream.lock.json').read_text())
    candidate=out/'candidate'
    prepared=prepare(ROOT,args.upstream,candidate,locked['commit'])
    if prepared['changes']:
        raise ValueError('Rehearsal must use the same locked source')
    try:
        subprocess.run([sys.executable,'-B',str(candidate/'tools/verify.py'),
            '--upstream',str(args.upstream.resolve()),'--baselines',str(args.baselines.resolve()),
            '--evidence',str(out/'verification')],cwd=candidate,check=True,timeout=900)
        review=out/'review.json'
        review.write_text(json.dumps({'decision':'accept','reviewer':'synthetic CI check, not release approval',
            'candidate_digest':prepared['candidate_digest'],'reviewed_paths':[]},indent=2)+'\n')
        result=accept(out/'candidate.upgrade.json',out/'verification/result.json',review,True)
        if source_digest(ROOT)!=before:raise AssertionError('Rehearsal changed accepted source')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print('UPGRADE REHEARSAL PASS: accepted source untouched; no candidate commit')
    finally:
        run('git','worktree','remove','--force',str(candidate),cwd=ROOT)


if __name__=='__main__':main()
