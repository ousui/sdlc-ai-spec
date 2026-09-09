#!/usr/bin/env python3
"""Opt-in REAL Issue publish/readback test via installed public CLI.

Requires an explicitly supplied disposable Issue and existing gh credentials.
Does not create/close Issues or assert a six-stage product/Agent closure.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--issue-url',required=True);p.add_argument('--plugin-root',required=True,type=Path)
    p.add_argument('--work',required=True,type=Path);p.add_argument('--evidence-dir',required=True,type=Path)
    a=p.parse_args();root=a.work.resolve();root.mkdir(parents=True,exist_ok=False)
    evidence=a.evidence_dir.resolve();evidence.mkdir(parents=True,exist_ok=True)
    cli=a.plugin_root.resolve()/'scripts/sdlc.py';bindings={};count=0
    def call(command,payload,bind=True):
        nonlocal count
        request={'api_version':'2','command':command,'payload':payload,**(bindings if bind else {})}
        count+=1
        result=subprocess.run([sys.executable,'-B',str(cli),'--root',str(root),'--request','-'],
                              input=json.dumps(request),text=True,capture_output=True,timeout=120)
        out=json.loads(result.stdout)
        (evidence/f'{count:02d}-{command}.json').write_text(json.dumps({'request':request,'response':out,'exit_code':result.returncode},ensure_ascii=False,indent=2)+'\n')
        if result.returncode or not out['ok']:raise RuntimeError(json.dumps(out,ensure_ascii=False))
        return out
    call('workspace.init',{'name':'GitHub sharing public integration fixture'})
    ctx=call('context.commit',{'summary':'Explicit isolated Issue sharing test, not a business release','entries':[]})['data']['context_id']
    initial=call('change.create',{'slug':'github-sharing-smoke','context_id':ctx,'title':'阶段产物共享验证',
        'summary':'Verify that an actual structured requirement is shared as readable Markdown.',
        'goal':'One Issue comment, exact readback and idempotent repeat','in_scope':'Public CLI Issue sharing',
        'out_of_scope':'Product deployment and private data','delivery_mode':'local','delivery_target':'.sdlc/exports/smoke',
        'original_text':'Create a synthetic requirement, publish its REQ view to the explicitly authorized test Issue, read back and repeat without duplication.',
        'authorizations':[]})
    bindings.update(change_id=initial['data']['change_id'],run_id=initial['run_id'])
    state=call('phase.prepare',{'phase':'REQ'})['data']
    submitted={'phase':'REQ','revision_id':state['content']['revision']['revision_id'],'operations':[
        {'op':'create_requirement','client_key':'req','kind':'behavior','statement':'Publish readable requirement snapshot once','sources':[{'id':initial['data']['source_id']}]},
        {'op':'create_criterion','client_key':'ac','condition_text':'Publish twice to the same explicitly selected Issue',
         'expected_result':'One remotely verified comment and a reused receipt','requirements':[{'client_key':'req'}]}]}
    req={'api_version':'2','command':'phase.submit','payload':submitted,'expected_generation':state['generation'],**bindings}
    result=subprocess.run([sys.executable,'-B',str(cli),'--root',str(root)],input=json.dumps(req),text=True,capture_output=True,timeout=30)
    value=json.loads(result.stdout);assert value['ok'],value
    (evidence/'req-submit.json').write_text(json.dumps({'request':req,'response':value},ensure_ascii=False,indent=2))
    req['command']='phase.complete';req['payload']={'phase':'REQ','revision_id':submitted['revision_id']};req['expected_generation']=value['data']['generation']
    result=subprocess.run([sys.executable,'-B',str(cli),'--root',str(root)],input=json.dumps(req),text=True,capture_output=True,timeout=30)
    value=json.loads(result.stdout);assert value['ok'],value
    (evidence/'req-complete.json').write_text(json.dumps({'request':req,'response':value},ensure_ascii=False,indent=2))
    preview=call('github.preview',{'issue_url':a.issue_url,'phase':'REQ'})['data']
    payload={'issue_url':a.issue_url,'phase':'REQ','preview_digest':preview['preview_digest'],'confirmed':True}
    first=call('github.publish',payload);second=call('github.publish',payload)
    assert first['data']['state']=='confirmed' and second['data']['idempotent']
    assert first['data']['comment_id']==second['data']['comment_id']
    reconciled=call('github.reconcile',{'publication_id':first['operation_id']})
    assert reconciled['data']['comment_id']==first['data']['comment_id']
    call('github.status',{})
    archive=call('workspace.export',{'change_id':bindings['change_id']},bind=False)['data']
    receipt={'success':True,'scope':'real public CLI/gh Issue sharing only; not a product Agent lifecycle',
             'comment_url':first['data']['comment_url'],'operation_id':first['operation_id'],
             'archive':archive,'cli':str(cli),'requests':count+2}
    (evidence/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
