#!/usr/bin/env python3
"""Independent source constraints plus adversarial execution behavior, not a document-presence check."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests.skill_rls.preweb_review import scan_runtime_source
from tools.run_rls_test_suite import run
from tools.rls_validation_support import digest, write_json


def review(output):
    sources=[]; violations=[]
    for path in sorted((ROOT/"skills/sdlc-600-rls/scripts").glob("*.py")):
        relative=path.relative_to(ROOT).as_posix(); raw=path.read_bytes()
        findings=scan_runtime_source(relative,raw.decode())
        if "skills/sdlc-500-vfy" in raw.decode() or "from vfy_" in raw.decode(): findings.append("private sibling runtime dependency")
        violations.extend({"path":relative,"finding":finding} for finding in findings)
        sources.append({"path":relative,"sha256":digest(raw)})
    behavior=run("effect",Path(output).with_name(Path(output).stem+"-behavior.json"))
    value={"contract":"sdlc-ai-spec/rls-effect-boundary-review/v1","review_method":"independent source constraint scan and adversarial behavior suite",
           "human_or_web_acceptance":False,"sources":sources,"violations":violations,"behavior":behavior,
           "success":not violations and behavior["success"],"real_target_effects":0}
    write_json(output,value)
    return value


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--json-out",type=Path,required=True);args=parser.parse_args()
    raise SystemExit(0 if review(args.json_out)["success"] else 1)
