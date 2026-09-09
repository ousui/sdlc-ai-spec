#!/usr/bin/env python3
"""Explicit non-collector suite for Linux/Podman; not full native execution PASS."""
import argparse
import json
import os
import platform
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests/v2')]
MODULES=('test_store','test_domain','test_runtime','test_golden','test_redaction',
         'test_asset_recovery','test_github_sharing','test_review_fixes','test_transfer','test_transfer_provenance',
         'test_revision_text')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence-dir',type=Path,required=True);a=p.parse_args()
    evidence=a.evidence_dir.expanduser().resolve()
    if evidence.is_relative_to(ROOT):p.error('Evidence must be outside the source tree')
    evidence.mkdir(parents=True,exist_ok=True)
    os.environ.pop('PYTHONPATH',None)  # Child checks use explicit absolute dependency paths, not the test import path.
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in MODULES)
    started=time.monotonic()
    with (evidence/'unittest.log').open('w') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    sha=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
    status=subprocess.run(['git','status','--short'],cwd=ROOT,capture_output=True,text=True)
    report={'suite':'portable-mechanisms','source_head':sha.stdout.strip(),'source_status':status.stdout,
            'platform':platform.platform(),'python':sys.version,'tests':result.testsRun,'failures':len(result.failures),
            'errors':len(result.errors),'skipped':len(result.skipped),'seconds':round(time.monotonic()-started,3),
            'success':result.wasSuccessful() and not result.skipped,
            'not_tested':['native Linux/Windows command collector','native macOS execution in this portable suite','real remote GitHub writes','real Agent business demand chains']}
    (evidence/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False));return 0 if report['success'] else 1


if __name__=='__main__':raise SystemExit(main())
