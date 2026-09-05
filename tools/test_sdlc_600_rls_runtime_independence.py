#!/usr/bin/env python3
"""Cold-process installed RLS commands over real persisted upstream authority."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rls_validation_support import REDACTION_POLICY, redact_receipt, write_json


def validate(root):
    from tools.rls_fixture_chain import build_chain
    from packages.sdlc_artifact_store import compute_sha256
    root = Path(root).resolve()
    receipts = []
    with tempfile.TemporaryDirectory(prefix="rls-installed-final-") as directory:
        base = Path(directory).resolve(); project = base / "project"; project.mkdir()
        chain = build_chain(project)
        installed = base / "plugin"
        for relative in ("packages", "skills/_shared", "skills/sdlc-600-rls", "scripts"):
            shutil.copytree(root / relative, installed / relative, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        assert all(not (installed / name).exists() for name in ("docs", "tests", "AGENTS.md", "CLAUDE.md", "tools", "skills/sdlc-500-vfy"))
        script = installed / "skills/sdlc-600-rls/scripts/runtime.py"
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE":"1", "PYTHONPATH":str(installed)}
        def invoke(command, payload=None):
            before = time.monotonic()
            result = subprocess.run(command, cwd=base, env=environment, input=json.dumps(payload) if payload is not None else "",
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
            receipt=redact_receipt({"argv":command, "cwd":str(base), "exit_code":result.returncode,
                     "duration_ms":round((time.monotonic()-before)*1000), "stdout":result.stdout, "stderr":result.stderr}, environment)
            receipt.update(stdout_sha256=compute_sha256(receipt["stdout"].encode()),
                           stderr_sha256=compute_sha256(receipt["stderr"].encode()), redaction_policy=REDACTION_POLICY)
            receipts.append(receipt)
            if result.returncode:
                raise AssertionError("installed command failed: " + result.stdout + result.stderr)
            return json.loads(result.stdout)
        def cli(arguments, payload=None):
            return invoke([sys.executable,str(script),*arguments,"--output","json"],payload)
        def host(code, *arguments):
            # A separate explicit host API invocation, not a business JSON permission.
            prelude = "import sys,json;from pathlib import Path;sys.path[:0]=[sys.argv[1],str(Path(sys.argv[1])/'skills/sdlc-600-rls/scripts')];"
            return invoke([sys.executable,"-c",prelude+code,str(installed),str(project),*arguments])
        for name in ("help","version","commands","examples"):
            result = cli([name]); assert result["state"] == "meta" and result["effects"] == []
        target = base / "target"
        arguments = ["-p",str(project)]
        created = cli(["auto",*arguments,"--target","sandbox-a","--release-reference","1.0.0"],{"sandbox_root":str(target)})
        reference = created["artifact"]["artifact"]["reference"]
        assert not created["artifact"]["target_effect"] and not created["artifact"]["provisional"]
        grant = host("from rls_service import RlsService;from rls_trusted_effect import TrustedEffectRecords;s,_=RlsService(sys.argv[2]).read(sys.argv[3]);print(json.dumps(TrustedEffectRecords(sys.argv[2]).grant(s,['RLI-001'],authorizer_identity='installed-fixture-host',approved=True)))",reference)
        executed = cli(["execute",*arguments,"-r",reference,"--item","RLI-001"],{"sandbox_root":str(target),"effect_authorization":grant})
        assert executed["artifact"]["target_effect"] and executed["real_target_effects"] == 0
        confirmed = cli(["confirm",*arguments,"-r",reference,"--item","RCF-001"],{"sandbox_root":str(target)})
        assert confirmed["artifact"]["confirmations"][0]["result"] == "pass"
        bindings = host("from rls_service import RlsService;from rls_target import SandboxReleaseTarget;print(json.dumps(RlsService(sys.argv[2]).confirmation_requirements(sys.argv[3],SandboxReleaseTarget(sys.argv[4],'sandbox-a'))))",reference,str(target))
        approval = project / ".sdlc/authority/installed-rls-approval.txt"
        approval.write_text(json.dumps({"artifact":reference,"decision":"approved","authority":"explicit installed fixture host",**bindings})+"\n")
        confirmation = {"mode":"human","confirmer":"installed-fixture-host","role":"Fixture Owner",
                        "authority_reference":approval.relative_to(project).as_posix()+"@"+compute_sha256(approval.read_bytes()),
                        "confirmed_at":"2026-09-05T00:00:00Z",**bindings}
        frozen = cli(["finalize",*arguments,"-r",reference],{"sandbox_root":str(target),"final_confirmation":confirmation})
        assert frozen["artifact"]["artifact"]["revision_state"] == "frozen"
        def file_snapshot(path):
            return {str(item.relative_to(path)):(compute_sha256(item.read_bytes()),item.stat().st_mtime_ns)
                    for item in path.rglob("*") if item.is_file()}
        before = file_snapshot(project); before_target = file_snapshot(target)
        checked = cli(["check",*arguments,"-r",reference],{"sandbox_root":str(target)})
        assert checked["check"]["ok"] and file_snapshot(project) == before and file_snapshot(target) == before_target
        same = cli(["revise",*arguments,"-r",reference],{"sandbox_root":str(target)})
        assert "RLS_NO_CHANGE" in same["artifact"]["warnings"]
        retry = cli(["revise",*arguments,"-r",reference],{"sandbox_root":str(target),"retry":True})
        retry_ref = retry["artifact"]["artifact"]["reference"]
        assert retry["artifact"]["artifact"]["revision"] == 2 and retry["artifact"]["effect_authorization"] is None
        cancelled = cli(["cancel",*arguments,"-r",retry_ref],{"sandbox_root":str(target)})
        assert cancelled["artifact"]["release_conclusion"] == "cancelled" and not cancelled["artifact"]["target_effect"]
        explicit = cli(["create",*arguments,"-i",chain["vfy"],"--target","sandbox-b","--release-reference","2.0.0"],{"sandbox_root":str(base/"target-b")})
        assert explicit["artifact"]["artifact"]["id"] != created["artifact"]["artifact"]["id"]
        return {"contract":"sdlc-ai-spec/rls-final-runtime-independence/v1","provisional":False,
                "result":"PASS","commands":["help","version","commands","examples","auto","create","execute","confirm","check","revise","cancel","finalize"],
                "removed":["docs","tests","AGENTS.md","CLAUDE.md","tools","sibling phase Skills"],
                "receipts":receipts,"real_target_effects":0,"network_reads":0,"installations":0,"cleanup":"PASS"}


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--root",type=Path,default=ROOT); parser.add_argument("--json-out",type=Path)
    args=parser.parse_args(argv)
    try:
        result=validate(args.root)
    except Exception as exc:
        result={"result":"FAIL","error":str(exc)}
    result=redact_receipt(result)
    if args.json_out:
        write_json(args.json_out,result)
    print("RLS_RUNTIME_INDEPENDENCE = "+result["result"])
    if result["result"] != "PASS": print(result.get("error"),file=sys.stderr)
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
