#!/usr/bin/env python3
"""Stable exact-Subject RLS delivery gate, with fresh detached attestation."""
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.rls_validation_support import source_state, run_step, write_json, now, REDACTION_POLICY, redact_receipt


def validate(profile, source, output):
    output=Path(output).resolve()
    result=dict(contract="sdlc-ai-spec/rls-delivery-validation/v1",profile=profile,source_sha=source,
                success=False,started_at=now(),redaction_policy=REDACTION_POLICY,steps=[],real_target_effects=0,remote_writes=0,installations=0)
    try:
        assert not output.is_relative_to(ROOT), "OUT must be outside the source worktree"
        before=source_state(ROOT);result["source_before"]=before
        assert re.fullmatch(r"[0-9a-f]{40}",source) and before["sha"]==source and not before["status"], "clean exact S required"
        logs=output.parent/(output.stem+"-steps");logs.mkdir(parents=True,exist_ok=True)
        def step(name,argv,*,cwd=ROOT,timeout=1800):
            print("RLS_STEP_START "+name,flush=True)
            receipt=run_step(cwd,name,argv,logs,timeout=timeout)
            result["steps"].append(receipt);write_json(output,result)
            print("RLS_STEP_END "+name+" "+("PASS" if receipt["success"] else "FAIL"),flush=True)
            assert receipt["success"], name + " failed; inspect its exact process receipt"
            return receipt
        python=sys.executable
        step("source",[python,"tools/validate_rls_delivery_source.py","--source-sha",source,"--json-out",logs/"source.json"])
        if profile=="quick":
            step("runtime-contracts",[python,"tools/validate_runtime_contracts.py"])
            step("skill-interfaces",[python,"tools/validate_skill_interfaces.py"])
            step("rls-source-lock",[python,"tools/validate_sdlc_600_rls_source_lock.py","--json-out",logs/"source-lock.json"])
            step("vfy-source-lock",[python,"-m","unittest","tests.skill_vfy.test_source_lock"])
            step("critical-oracles",[python,"-m","unittest","tests.evals.test_sdlc_600_rls_case_coverage"])
        elif profile=="phase":
            step("critical-oracles",[python,"-m","unittest","tests.evals.test_sdlc_600_rls_case_coverage"])
            step("rls-e001-e087",[python,"tests/evals/run_sdlc_600_rls_eval.py","--json-out",logs/"fixed-eval.json"])
            result["fixed_eval"]=json.loads((logs/"fixed-eval.json").read_bytes())
        elif profile=="full":
            step("rls-private",[python,"tools/run_rls_test_suite.py","--suite","rls","--json-out",logs/"rls-private.json"])
            step("effect-boundary-review",[python,"tools/review_rls_effect_boundary.py","--json-out",logs/"effect-review.json"])
            # Keep accepted VFY untouched. Capture its JSON stdout, redact before persistence.
            receipt=step("vfy-strict-80",[python,"tests/evals/run_sdlc_500_vfy_eval.py"])
            result["vfy_regression"]=json.loads(receipt["stdout"])
            write_json(logs/"vfy-80.json",result["vfy_regression"])
            assert result["vfy_regression"]["passed"]==80 and result["vfy_regression"]["skipped"]==0
            step("vfy-installed-independence",[python,"tools/test_sdlc_500_vfy_runtime_independence.py"])
            step("rls-installed-independence",[python,"tools/test_sdlc_600_rls_runtime_independence.py","--json-out",logs/"rls-independence.json"])
            step("repository-regression",[python,"tools/run_rls_test_suite.py","--suite","repo","--json-out",logs/"repository.json"])
            result["full_regression"]=json.loads((logs/"repository.json").read_bytes())
        elif profile=="external":
            step("external-projects",[python,"tools/run_external_rls_integration.py","--source-sha",source,"--json-out",logs/"external-projects.json"])
            result["external"]=json.loads((logs/"external-projects.json").read_bytes())
            assert result["external"]["passed"]==2 and result["external"]["real_target_effects"]==0
        elif profile=="attest":
            with tempfile.TemporaryDirectory(prefix="rls-fresh-attest-") as directory:
                fresh=Path(directory).resolve()/"subject"
                added=False
                try:
                    step("fresh-worktree-add",["git","worktree","add","--detach",str(fresh),source]);added=True
                    fresh_state=source_state(fresh);result["fresh_source"]=fresh_state
                    assert not fresh_state["branch"] and not fresh_state["status"] and fresh_state["sha"]==source and fresh_state["root"]!=str(ROOT)
                    result["profiles"]={}
                    for subprofile in ("quick","phase","full","external"):
                        report=logs/("fresh-"+subprofile+".json")
                        step("fresh-"+subprofile,[python,"tools/run_rls_delivery_validation.py","--profile",subprofile,"--source-sha",source,"--json-out",report],cwd=fresh,timeout=2400)
                        result["profiles"][subprofile]=json.loads(report.read_bytes())
                    assert source_state(fresh)==fresh_state, "fresh Subject changed during attestation"
                finally:
                    if added: step("fresh-worktree-remove",["git","worktree","remove",str(fresh)])
                result["fresh_cleanup"]=not fresh.exists()
        else: raise AssertionError("unknown profile")
        result["source_after"]=source_state(ROOT)
        assert result["source_after"]==before, "source worktree changed during validation"
        result["success"]=True
    except Exception as exc:
        result.update(error_type=type(exc).__name__,error=str(exc))
        try: result["source_after"]=source_state(ROOT)
        except Exception as nested: result["source_state_error"]=str(nested)
    result["finished_at"]=now();result=redact_receipt(result);write_json(output,result)
    print("RLS_DELIVERY_"+profile.upper()+" = "+("PASS" if result["success"] else "FAIL"),flush=True)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--profile",choices=("quick","phase","full","external","attest"),required=True)
    parser.add_argument("--source-sha",required=True);parser.add_argument("--json-out",type=Path,required=True)
    args=parser.parse_args();raise SystemExit(0 if validate(args.profile,args.source_sha,args.json_out)["success"] else 1)
