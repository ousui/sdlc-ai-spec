#!/usr/bin/env python3
"""Exact-source post-integration checks; historical phase topology gates stay intact."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from tools.rls_validation_support import git, run_step, source_state, write_json

BASELINE = "0289a5ee8d702450fb3f3bc73c89f30a11664bdb"


def validate(profile: str, source: str, output: Path):
    result = {"contract":"sdlc-ai-spec/post-integration-validation/v1", "profile":profile,
              "source_sha":source, "success":False, "steps":[], "native_clients":"NOT_RUN",
              "strict_vfy_execution":"NOT_RUN", "real_target_effects":0}
    output = output.resolve()
    if output.is_relative_to(ROOT): raise ValueError("validation output must be outside the source tree")
    logs=output.parent/(output.stem+"-logs")
    try:
        if profile not in {"portable", "strict"} or not re.fullmatch(r"[0-9a-f]{40}", source): raise ValueError("invalid profile/source")
        before=source_state(ROOT);result["source_before"]=before
        if before["sha"]!=source or before["status"]: raise ValueError("clean exact source checkout required")
        git(ROOT,"merge-base","--is-ancestor",BASELINE,source)
        commands=[
            ("runtime-contracts", ["tools/validate_runtime_contracts.py"]),
            ("interfaces", ["tools/validate_skill_interfaces.py"]),
            ("inventory", ["tools/validate_skill_conformance.py","--json-out",str(logs/"inventory.json")]),
            ("all-source-locks", ["tools/validate_all_skill_source_locks.py","--json-out",str(logs/"locks.json")]),
            ("status-static", ["tools/validate_sdlc_status.py"]),
            ("status-coverage", ["-m","unittest","tests.evals.test_sdlc_status_case_coverage","-v"]),
            ("status-fixed", ["tests/evals/run_sdlc_status_eval.py","--json-out",str(logs/"status-fixed.json")]),
            ("status-installed", ["tools/test_sdlc_status_runtime_independence.py","--json-out",str(logs/"status-installed.json")]),
            ("rls-fixed", ["tests/evals/run_sdlc_600_rls_eval.py","--json-out",str(logs/"rls-fixed.json")]),
            ("repo-suite", ["tools/run_rls_test_suite.py","--suite","repo","--json-out",str(logs/"repo-suite.json")]),
        ]
        if profile=="strict":
            commands += [("vfy-strict",["tests/evals/run_sdlc_500_vfy_eval.py","--json-out",str(logs/"vfy-strict.json")]),
                         ("vfy-installed",["tools/test_sdlc_500_vfy_runtime_independence.py"]),
                         ("rls-installed",["tools/test_sdlc_600_rls_runtime_independence.py","--json-out",str(logs/"rls-installed.json")])]
        for name, args in commands:
            receipt=run_step(ROOT,name,[sys.executable,"-B",*args],logs,timeout=900)
            result["steps"].append({key:receipt[key] for key in ("name","exit_code","success","source_unchanged","stdout_sha256","stderr_sha256","stdout_log","stderr_log","duration_ms")})
            if not receipt["success"]: raise ValueError("first failing step: "+name)
        after=source_state(ROOT);result["source_after"]=after
        if before!=after: raise ValueError("source changed during validation")
        result["success"]=True
        if profile=="strict":result["strict_vfy_execution"]="PASS"
    except Exception as exc: result["error"]=str(exc)
    write_json(output,result)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--profile",choices=("portable","strict"),required=True)
    parser.add_argument("--source-sha",required=True);parser.add_argument("--json-out",type=Path,required=True);args=parser.parse_args()
    try: result=validate(args.profile,args.source_sha,args.json_out)
    except Exception as exc:
        print("POST_INTEGRATION = HARD_BLOCKED: "+str(exc));raise SystemExit(1)
    print("POST_INTEGRATION =", "PASS" if result["success"] else "HARD_BLOCKED")
    print("NATIVE_CLIENTS = NOT_RUN")
    raise SystemExit(0 if result["success"] else 1)
