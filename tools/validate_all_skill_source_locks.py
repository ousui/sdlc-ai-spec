#!/usr/bin/env python3
"""Validate all Phase/Utility locks in their existing formats; regenerate nothing."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def validate():
    from packages.sdlc_runtime import ContractSource, registry_sources, verify_source_lock
    rows = []
    try:
        extra = tuple(ContractSource("sdlc-ai-spec/build-source/"+name+"/v1.1", "1.1", "docs/v1.1/"+path)
                      for name, path in (("artifact-store","artifact-store-spec.md"),("core","core-spec.md"),("ctx","000-ctx-spec.md")))
        verify_source_lock(ROOT, json.loads((ROOT/"skills/sdlc-000-ctx/references/source-lock.json").read_bytes()),
                           (*registry_sources(ROOT, ROOT/"skills/_shared/contracts/registry.json"), *extra))
        rows.append({"skill":"sdlc-000-ctx", "success":True})
    except Exception as exc: rows.append({"skill":"sdlc-000-ctx", "success":False, "error":str(exc)})
    for name in ("100-req", "200-dsn", "300-pln", "400-imp", "500-vfy", "600-rls", "status"):
        tool="tools/validate_sdlc_"+name.replace("-","_")+"_source_lock.py"
        p=subprocess.run([sys.executable,"-B",str(ROOT/tool)], cwd=ROOT, input=b"", capture_output=True, timeout=60)
        rows.append({"skill":"sdlc-"+name,"success":p.returncode==0,"exit_code":p.returncode,
                     "stdout":p.stdout.decode(errors="replace"),"stderr":p.stderr.decode(errors="replace")})
    return {"contract":"sdlc-ai-spec/all-skill-lock-result/v1", "success":len(rows)==8 and all(row["success"] for row in rows), "skills":rows}


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--json-out",type=Path);args=parser.parse_args()
    try: result=validate()
    except Exception as exc: result={"success":False,"error":str(exc)}
    from tools.rls_validation_support import redact_receipt,write_json
    result=redact_receipt(result)
    if args.json_out: write_json(args.json_out,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result["success"] else 1)
