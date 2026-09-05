#!/usr/bin/env python3
"""Strict RLS/repository test receipts; missing, skipped or expected failures fail."""
import argparse
import io
import json
from pathlib import Path
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.rls_validation_support import REDACTION_POLICY, redact_receipt, write_json


def run(suite_name, json_out):
    started=time.monotonic(); stream=io.StringIO()
    payload={"contract":"sdlc-ai-spec/rls-test-suite/v1","suite":suite_name,"success":False}
    try:
        if suite_name == "effect":
            suite=unittest.defaultTestLoader.loadTestsFromNames(["tests.skill_rls.test_effect_safety"])
        else:
            directory=ROOT/"tests" if suite_name=="repo" else ROOT/"tests/skill_rls"
            suite=unittest.defaultTestLoader.discover(str(directory),pattern="test_*.py",top_level_dir=str(ROOT))
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        payload.update(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                       skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses),
                       success=result.wasSuccessful() and result.testsRun>0 and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses,
                       log=stream.getvalue())
    except Exception as exc:
        payload.update(error=str(exc),log=stream.getvalue())
    payload["duration_ms"]=round((time.monotonic()-started)*1000)
    payload["redaction_policy"]=REDACTION_POLICY
    payload=redact_receipt(payload)
    write_json(json_out,payload)
    print(payload.get("log",""),end="")
    print(f"RLS_TEST_SUITE {suite_name}: {'PASS' if payload['success'] else 'FAIL'} ({payload.get('tests_run',0)} executed)")
    return payload


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--suite",choices=("rls","repo","effect"),required=True); parser.add_argument("--json-out",type=Path,required=True)
    args=parser.parse_args(); raise SystemExit(0 if run(args.suite,args.json_out)["success"] else 1)
