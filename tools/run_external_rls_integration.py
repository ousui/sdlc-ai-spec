#!/usr/bin/env python3
"""Two fixed public projects: real CTX-through-RLS lifecycle, local Sandbox only."""
from __future__ import annotations
import argparse
import base64
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"skills/sdlc-600-rls/scripts"))
from tools.rls_validation_support import digest,git,source_state,run_step,write_json
PROJECTS=(
    ("springgear","ousui/springgear","https://github.com/ousui/springgear.git","e855096ff19dcdb303dc4250ba19c30acd743ac7"),
    ("gin-vue-admin","flipped-aurora/gin-vue-admin","https://github.com/flipped-aurora/gin-vue-admin.git","a6882210a80bb27e3aa5dff0b4c21aa4afe8988a"),
)


def project_snapshot(root):
    return {"head":git(root,"rev-parse","HEAD"),"tree":git(root,"rev-parse","HEAD^{tree}"),
            "refs":git(root,"for-each-ref","--format=%(refname) %(objectname)"),
            "status":git(root,"status","--porcelain=v1","--untracked-files=all"),
            "tracked":git(root,"ls-files","--stage"),"untracked":git(root,"ls-files","--others","--exclude-standard"),
            "tracked_bytes_modes":worktree_files(root, "--cached"),
            "untracked_bytes_modes":worktree_files(root, "--others", "--exclude-standard"),
            "sdlc":file_snapshot(root/".sdlc")}


def file_record(path):
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        raw = os.fsencode(os.readlink(path)); kind = "symlink"
    elif stat.S_ISREG(metadata.st_mode):
        raw = path.read_bytes(); kind = "file"
    else:
        raise AssertionError("unsupported external resource file type: " + str(path))
    return {"kind":kind,"mode":stat.S_IMODE(metadata.st_mode),"bytes":len(raw),"sha256":digest(raw)}


def worktree_files(root, *selection):
    names = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z", *selection]).split(b"\0")
    return {os.fsdecode(name):file_record(root/os.fsdecode(name)) for name in names if name}


def file_snapshot(root):
    if not root.exists(): return {"exists":False,"files":{}}
    return {"exists":True,"files":{str(path.relative_to(root)):file_record(path) for path in sorted(root.rglob("*")) if path.is_file() or path.is_symlink()}}


def _serial(value):
    if isinstance(value,bytes): return {"base64":base64.b64encode(value).decode(),"sha256":digest(value)}
    raise TypeError(type(value).__name__)


def export_store(root):
    from packages.sdlc_artifact_store import ArtifactStore
    from packages.sdlc_artifact_store.catalog import ArtifactCatalog
    store=ArtifactStore.open_read_only(root);catalog=ArtifactCatalog(store);records=[]
    for artifact in catalog.list_artifacts():
        for control in catalog.list_revisions(artifact.artifact_id):
            records.append(asdict(store.read_revision(artifact.artifact_id,control.revision)) if control.materialized else {"control":asdict(control)})
    return json.loads(json.dumps(records,default=_serial))


def run_projects(output, *, cache_root=None):
    from tools.rls_fixture_chain import build_chain,rls_final_confirmation
    from rls_service import RlsService
    from rls_target import SandboxReleaseTarget
    from rls_trusted_effect import TrustedEffectRecords
    from rls_vfy_adapter import read_vfy_candidate
    from packages.sdlc_artifact_store import ArtifactStore
    from packages.sdlc_runtime.authority import FrozenArtifactAuthorityVerifier
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    results=[]
    for name,repository,url,sha in PROJECTS:
        row={"name":name,"repository":repository,"expected_sha":sha,"success":False,"fetch_attempts":[],"real_target_effects":0,"remote_writes":0,"installations":0}
        with tempfile.TemporaryDirectory(prefix="rls-external-"+name+"-") as directory:
            base=Path(directory).resolve();project=base/"project";logs=output/name;project.mkdir()
            before=None;readme=None;metadata=None;readme_path=None
            try:
                cache=(Path(cache_root)/name).resolve() if cache_root else None
                if cache is not None and cache.exists():
                    row["cache_before"]=source_state(cache)
                    assert git(cache,"rev-parse",sha+"^{commit}")==sha
                    receipt=run_step(base,"clone-exact-cache",["git","clone","--no-hardlinks","--no-checkout",str(cache),str(project)],logs,track_source=False)
                    row["fetch_attempts"].append(receipt);assert receipt["success"]
                    row["cache_after"]=source_state(cache);assert row["cache_before"]==row["cache_after"]
                else:
                    receipt=run_step(base,"initialize",["git","-C",str(project),"init","-q"],logs,track_source=False);assert receipt["success"]
                    for attempt in range(1,4):
                        receipt=run_step(base,"fetch-exact",["git","-C",str(project),"fetch","--depth=1",url,sha],logs,track_source=False,attempt=attempt,timeout=120)
                        row["fetch_attempts"].append(receipt)
                        if receipt["success"]: break
                    assert receipt["success"],"exact external object unavailable after bounded reads"
                checkout=run_step(base,"checkout-exact",["git","-C",str(project),"checkout","--detach",sha],logs,track_source=False)
                row["checkout"]=checkout;assert checkout["success"]
                before=project_snapshot(project);row["before"]=before
                assert before["head"]==sha and before["status"]=="" and not before["sdlc"]["exists"]
                from tools.rls_fixture_chain import upstream
                resource_root=upstream._select_resource_root(project)
                row["resource_selection"]={"root":resource_root,"source":"accepted VFY/IMP external integration _select_resource_root", "scope":"resource:repo path:repo/README.md"}
                readme_path=project/resource_root/"README.md"
                readme=readme_path.read_bytes();metadata=readme_path.stat()
                chain=build_chain(project,repository=repository,resource_root=resource_root)
                candidate=read_vfy_candidate(project,chain["vfy"],expected_candidate=chain["candidate"])
                target=SandboxReleaseTarget(base/"sandbox-target","sandbox-a");service=RlsService(project)
                state,generation=service.create(chain["vfy"],target,release_reference="lifecycle-validation-"+sha[:12])
                reference=state["artifact"]["reference"]
                ids=[item["id"] for item in state["release_items"]]
                grant=TrustedEffectRecords(project).grant(state,ids,authorizer_identity="external-fixture-host",approved=True)
                state,generation=service.execute(reference,target,ids,grant)
                state,generation=service.confirm(reference,target,[item["id"] for item in state["confirmations"]])
                confirmation=rls_final_confirmation(project,service,reference,target)
                state,generation=service.finalize(reference,target,confirmation)
                store_before=file_snapshot(project/".sdlc");target_before=file_snapshot(target.root)
                check=service.check(reference,target)
                authority=ArtifactStore.open_read_only(project).resolve_exact_reference(reference,verifier=FrozenArtifactAuthorityVerifier(project))
                assert authority.revision.control.state=="frozen" and state["release_conclusion"]=="success" and state["artifact_gate"]=="pass"
                assert store_before==file_snapshot(project/".sdlc") and target_before==file_snapshot(target.root)
                row.update(chain={key:chain[key] for key in ("context","requirement","design","plan","vfy")},
                           imp_subjects=chain["state"]["subjects"],vfy_candidate=chain["candidate"],adapter=candidate.to_dict(),
                           rls_reference=reference,rls_state=state,generation=generation,grant=grant,confirmation=confirmation,
                           check=check,store_snapshot=store_before,target_snapshot=target_before,
                           effect_journal=file_snapshot(project/".sdlc/rls-execution"),during=project_snapshot(project),success=True)
                export=logs/"store-export.json";write_json(export,export_store(project))
                row["store_export"]={"path":str(export),"sha256":digest(export.read_bytes())}
                target.cleanup();row["target_cleanup"]=not target.root.exists()
            except Exception as exc:
                import traceback
                row.update(success=False,error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
            finally:
                if readme is not None:
                    path=readme_path;path.write_bytes(readme);os.chmod(path,metadata.st_mode)
                    os.utime(path,ns=(metadata.st_atime_ns,metadata.st_mtime_ns))
                if (project/".sdlc").exists(): shutil.rmtree(project/".sdlc")
                if before is not None:
                    after=project_snapshot(project);row["after_cleanup"]=after
                    row["project_cleanup"]=after==before
                    row["success"]=row["success"] and row["project_cleanup"] and row.get("target_cleanup",False)
                write_json(logs/"project-result.json",row)
        row["temporary_root_removed"]=not base.exists();row["success"]=row["success"] and row["temporary_root_removed"]
        results.append(row)
    return {"contract":"sdlc-ai-spec/rls-external-integration/v1","success":len(results)==2 and all(x["success"] for x in results),
            "projects":results,"passed":sum(x["success"] for x in results),"real_target_effects":0,"remote_writes":0,"installations":0,
            "scope":"Lifecycle integration on exact public source projects, not complete product acceptance"}


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--source-sha",required=True);parser.add_argument("--json-out",type=Path,required=True)
    parser.add_argument("--cache-root",type=Path,default=os.environ.get("RLS_EXTERNAL_CACHE"));args=parser.parse_args(argv)
    before=source_state(ROOT)
    try:
        assert before["sha"]==args.source_sha and len(args.source_sha)==40 and not before["status"],"external validation requires clean exact S"
        result=run_projects(args.json_out.parent/(args.json_out.stem+"-projects"),cache_root=args.cache_root)
    except Exception as exc: result={"success":False,"error":str(exc)}
    result.update(source_before=before,source_after=source_state(ROOT),source_sha=args.source_sha)
    result["success"]=result["success"] and result["source_before"]==result["source_after"]
    write_json(args.json_out,result);print("RLS_EXTERNAL_PROJECTS = "+("2/2 PASS" if result["success"] else "FAIL"))
    return 0 if result["success"] else 1


if __name__=="__main__":raise SystemExit(main())
