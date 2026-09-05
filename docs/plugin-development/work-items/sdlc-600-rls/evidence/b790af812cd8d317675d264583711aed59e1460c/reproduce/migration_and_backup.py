import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = Path('/Users/shuaiw/.local/state/sdlc-ai-spec/rls-propagation-20260905-01a07149')
SOURCE = BASE / 'source'
sys.path.insert(0, str(SOURCE))
from tools.rls_validation_support import source_state, run_step, write_json, git, digest
from tools.validate_rls_delivery_source import allowed

R = 'ac0c3a8abbb975b8f1d7b4b630a5a902e4603759'
D = 'c9615cec2da3b39949a3fdd8be32396eae6db3aa'
B = 'f171118380535d8c27a1929d0ef061510f82305f'
V = '46509eb6688df30e71ed094132b2d10e81ceb2ac'
M = '644218e02876c5649fd87cfca12e1876d3b3b8bf'
S2 = '797bde43a31b6e5afdb028de7f8944cea996b460'
E2 = '93e98c577b5c3136df55ee5a7cb7a1c2adfcda30'
OLD = ['076994c1d28438fd3b038f5c928d3ceeda5a7453','13e37b100060d714a6b61c26e1ba990edb2dcae3','7a00aa04780b7d6b08676042b34f30d558b2a969','70e6f92fd1644831c836de1e2b8a0aa567c5a979','8fc15b71e0a90623e6805277fd131dd1f68de0fd']
state = source_state(SOURCE)
assert state['sha'] == R and not state['status']
assert git(SOURCE, 'rev-parse', 'origin/impl/rls-v2') == R
assert git(SOURCE, 'show', '-s', '--format=%P', B).split() == [V, M]
assert git(SOURCE, 'show', '-s', '--format=%P', D) == B
assert len({git(SOURCE, 'rev-parse', s+'^{tree}') for s in (B,V,M)}) == 1
assert git(SOURCE,'rev-parse',R+':tools/rls_validation_support.py') == 'a7fb955175a2a48b739965f6c5deec280c037de1'
assert git(SOURCE,'rev-parse',R+':tests/skill_rls/test_web_repair_redaction_propagation.py') == 'fa0ecad0c33cdd702237e75e4cc44d6123f6db0f'
before = dict(source=state, main=source_state(Path('/Users/shuaiw/Workspace/goedge.cloud/sdlc-ai-spec')),
              refs=git(SOURCE,'ls-remote','origin','refs/heads/main','refs/heads/impl/vfy-v2','refs/heads/design/sdlc-600-rls-goal','refs/heads/impl/rls-v2'),
              worktrees=git(SOURCE,'worktree','list','--porcelain'))
write_json(BASE/'preflight.json',before)
backup = BASE/'backup'; bundle = backup/'rls-history.bundle'
backup.mkdir(exist_ok=True)
def step(name, argv, root=SOURCE, tracked=True):
    assert not source_state(SOURCE)['status']
    receipt=run_step(root,name,argv,backup,track_source=tracked,timeout=600)
    print(name,receipt['exit_code'],flush=True)
    assert receipt['success'], name
    return receipt
step('bundle-create',['git','bundle','create',str(bundle),'origin/impl/rls-v2',*OLD])
step('bundle-verify',['git','bundle','verify',str(bundle)])
restored=backup/'restore.git'
step('restore-init',['git','init','--bare',str(restored)])
step('bundle-unbundle',['git','-C',str(restored),'bundle','unbundle',str(bundle)])
objects=[]
for ref in [S2,E2,R,D,B,V,M,'206c379b77bb47ba0cf7913ea6dc1f8a39ed9bcd',*OLD]:
    tree=git(SOURCE,'rev-parse',ref+'^{tree}')
    assert git(restored,'rev-parse',ref+'^{tree}')==tree
    assert git(restored,'cat-file','-t',ref)=='commit'
    objects.append(dict(sha=ref,tree=tree,restored=True))
step('restore-fsck',['git','-C',str(restored),'fsck','--full'],tracked=True)
write_json(backup/'bundle.json',dict(success=True,path=str(bundle),sha256=digest(bundle.read_bytes()),bytes=bundle.stat().st_size,prerequisites=False,objects=objects,remote_backup_refs_created=0))
candidate=BASE/'candidate'
step('candidate-add',['git','worktree','add','--detach',str(candidate),D])
assert source_state(candidate)['sha']==D and not source_state(candidate)['status']
oldpaths=git(SOURCE,'diff','--name-only',D,S2).splitlines()
assert len(oldpaths)==84 and all(allowed(p) for p in oldpaths)
new='tests/skill_rls/test_web_repair_redaction_propagation.py'
paths=sorted(set(oldpaths)|{new})
assert len(paths)==85 and all(allowed(p) for p in paths)
assert not any('/evidence/' in p or '/goal/' in p for p in paths)
subprocess.run(['git','-C',str(candidate),'restore','--source='+R,'--staged','--worktree','--',*paths],check=True)
entries=[]
for p in paths:
    raw=git(SOURCE,'ls-tree',R,'--',p).split()
    mode,kind,blob=raw[:3]
    assert kind=='blob'
    result=git(candidate,'hash-object',p)
    assert result==blob
    old=git(SOURCE,'ls-tree',S2,'--',p).split()
    oldblob=old[2] if old else None
    reason='Preserve S2 implementation unchanged' if oldblob==blob else ('New 56 propagation regressions' if p==new else 'Committed Web propagation repair' if p=='tools/rls_validation_support.py' else 'Register new test and exclude previous repair ancestry')
    entries.append(dict(path=p,source_sha=R,source_blob=blob,result_blob=result,mode=mode,previous_s2_blob=oldblob,reason=reason))
assert git(candidate,'diff','--cached','--name-only').splitlines()==paths
subprocess.run(['git','-C',str(candidate),'diff','--cached','--check'],check=True)
write_json(BASE/'migration.json',dict(source_sha=R,design_sha=D,entries=entries,count=len(entries),old_evidence_migrated=False,old_history_merged=False))
print(json.dumps(dict(backup='PASS',restored_objects=len(objects),migration_paths=len(entries),candidate=str(candidate))),flush=True)
