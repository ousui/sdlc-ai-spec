"""Bounded C-layer probe using only the unchanged production stdio entry.
No direct HTTP transport and no native-host claims. Never repeat a started write.
"""
import asyncio,json,os,signal,sys,hashlib,time
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
W=Path(__file__).resolve().parent
S=W.parent/'sdlc-github-local'
sys.path.insert(0,str(S))
from packages.sdlc_github.models import digest
from tests.skill_github.client import evidence_summary,atomic_json
PYTHON=W/'venv/bin/python';DATA=W/'data/live';OUT=W/'persistence'
SHA='b035880a6135c1f126ae1a35e1c173221f28807a'
def stamp():return datetime.now(timezone.utc).isoformat()
def inventory(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
class Process:
 def __init__(self,label,root=S):self.label=label;self.root=root;self.seq=0;self.waiters={};self.calls=[]
 async def start(self):
  self.err=(OUT/(self.label+'.stderr.log')).open('w')
  self.p=await asyncio.create_subprocess_exec(str(PYTHON),'-B',str(self.root/'scripts/sdlc_github_mcp.py'),'--data-root',str(DATA),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=self.err,cwd=W)
  self.reader=asyncio.create_task(self.read())
  r=await self.rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'sdlc-github-real-persistence-probe','version':'1'}})
  self.protocol=r.get('protocolVersion');await self.send({'jsonrpc':'2.0','method':'notifications/initialized'})
  return self
 async def read(self):
  try:
   while line:=await self.p.stdout.readline():
    d=json.loads(line)
    f=self.waiters.pop(d.get('id'),None)
    if f is not None and not f.done():
     if 'error' in d:f.set_exception(RuntimeError('MCP protocol error'))
     else:f.set_result(d.get('result'))
  finally:
   for f in self.waiters.values():
    if not f.done():f.set_exception(EOFError('Production stdio process closed'))
 async def send(self,d):self.p.stdin.write((json.dumps(d)+'\n').encode());await self.p.stdin.drain()
 async def begin(self,method,params):
  self.seq+=1;f=asyncio.get_running_loop().create_future();self.waiters[self.seq]=f
  await self.send({'jsonrpc':'2.0','id':self.seq,'method':method,'params':params});return f
 async def rpc(self,m,p):return await asyncio.wait_for(await self.begin(m,p),60)
 async def begin_tool(self,tool,args):
  row={'process':self.label,'pid':self.p.pid,'time_sent':stamp(),'tool':tool,'arguments':args}
  self.calls.append(row);atomic_json(OUT/(self.label+'.calls.json'),self.calls)
  future=await self.begin('tools/call',{'name':tool,'arguments':args})
  return future,row
 async def finish_tool(self,f,row):
  try:
   value=await asyncio.wait_for(asyncio.shield(f),60);value=value['structuredContent']
   row.update(time_received=stamp(),result=evidence_summary(value))
  except Exception as e:
   row.update(time_received=stamp(),process_error=type(e).__name__);value=None
  atomic_json(OUT/(self.label+'.calls.json'),self.calls);return value
 async def tool(self,tool,args):return await self.finish_tool(*(await self.begin_tool(tool,args)))
 async def close(self,kill=False):
  if self.p.returncode is None:
   if kill:self.p.kill()
   else:self.p.stdin.close()
  try:await asyncio.wait_for(self.p.wait(),10)
  except asyncio.TimeoutError:self.p.terminate();await self.p.wait()
  await self.reader;self.err.close()
  atomic_json(OUT/(self.label+'.process.json'),{'pid':self.p.pid,'runtime_sha':SHA,'entry':str(self.root.relative_to(W)) if self.root.is_relative_to(W) else '$SOURCE','protocol':self.protocol,'exit_code':self.p.returncode,'terminated_at':stamp()})
async def main():
 OUT.mkdir(exist_ok=True)
 statefile=OUT/'probe-state.json'
 live=json.loads((W/'results/live/run-state.json').read_text())
 report=json.loads((W/'results/live/LIVE-VALIDATION.json').read_text())
 assert not any(r.get('response',{}).get('effect')=='unknown' for r in report['rows']),'Prior unknown effect; no more write probes'
 assert live['actor_id']==2839512 and live['objects'].get('issue')
 if statefile.exists():raise SystemExit('Probe already registered; only inspect original operation_status, never repeat this script')
 state={'runtime_sha':SHA,'run_id':live['run_id'],'request_id':str(uuid4()),'mismatch_request_id':str(uuid4()),'started_at':stamp(),'write_started':False}
 atomic_json(statefile,state)
 old=live['requests']['issue.create']['request_id'];repo='ousui/sdlc-ai-monitor'
 oldargs={'repository':repo,'expected_actor_id':2839512,'request_id':old,'reconcile':False}
 before=inventory(DATA/'.local')
 p=await Process('original-path').start()
 status=await p.tool('sdlc_github_status',{});assert status['actor']=={'id':2839512,'login':'ousui'}
 receipt=await p.tool('sdlc_github_operation_status',oldargs);assert receipt['effect']=='confirmed' and receipt['receipt']['readback_verified']
 mismatch=await p.tool('sdlc_github_issue_create',{'repository':repo,'expected_actor_id':1,'request_id':state['mismatch_request_id'],'title':'[sdlc-github-client:'+live['run_id']+'] actor guard','dry_run':True,'write_policy':'auto'})
 assert mismatch['effect']=='none' and mismatch['errors'][0]['code']=='ACTOR_MISMATCH'
 await p.close()
 cache=DATA/'.cache';cache_exists=cache.exists();cache.mkdir(mode=0o700,exist_ok=True)
 sentinel=cache/('client-validation-'+live['run_id']);assert not sentinel.exists();sentinel.write_text('Disposable cache fixture; no durable state.\n');sentinel.unlink()
 if not cache_exists:cache.rmdir()
 p=await Process('installed-path',W/'installed/codex').start()
 await p.tool('sdlc_github_status',{});receipt=await p.tool('sdlc_github_operation_status',oldargs);await p.close()
 after=inventory(DATA/'.local')
 assert before==after and receipt['effect']=='confirmed' and receipt['receipt']['readback_verified']
 atomic_json(OUT/'restart-path-cache.json',{'status':'PASS','runtime_sha':SHA,'same_data_root':True,'actual_runtime_paths':['$SOURCE/scripts/sdlc_github_mcp.py','$GH_WORK/installed/codex/scripts/sdlc_github_mcp.py'],'original_request_id':old,'local_records_unchanged':before==after,'durable_file_count':len(before),'cache_fixture':'Only an owned synthetic disposable cache sentinel was removed; production runtime had created no cache.','actor_mismatch':{'status':'PASS','effect':'none','request_id':state['mismatch_request_id']},'upstream_calls':'not externally observed','native_behavior':'NOT_RUN'})
 a=await Process('race-a').start();b=await Process('race-b').start()
 for p in (a,b):
  r=await p.tool('sdlc_github_status',{});assert r['actor']['id']==2839512
 rid=state['request_id'];directory=DATA/'.local/github/2839512'/digest(repo)/'operations'/rid
 assert not directory.exists()
 args={'repository':repo,'expected_actor_id':2839512,'request_id':rid,'title':'[sdlc-github-client:'+live['run_id']+'] crash and concurrent claim','body':'Authorized synthetic persistence verification. Preserve this object; do not replay an uncertain request.','dry_run':False,'write_policy':'auto'}
 state.update(write_started=True,request=args,dispatch_at=stamp());atomic_json(statefile,state)
 fa,ra=await a.begin_tool('sdlc_github_issue_create',args)
 deadline=time.monotonic()+45
 while not (directory/'intent.json').exists() and not fa.done() and time.monotonic()<deadline:await asyncio.sleep(.002)
 if not (directory/'intent.json').exists():
  first=await a.finish_tool(fa,ra);await a.close();await b.close()
  atomic_json(OUT/'crash-race.json',{'status':'BLOCKED','reason':'No durable intent observed in the one permitted attempt; no new request ID was sent.','result':evidence_summary(first) if first else None});return
 observed=stamp()
 fb,rb=await b.begin_tool('sdlc_github_issue_create',args)
 receipt_before=(directory/'receipt.json').exists()
 await a.close(kill=True);first=await a.finish_tool(fa,ra)
 second=await b.finish_tool(fb,rb);await b.close()
 recovery=await Process('recovery').start()
 await recovery.tool('sdlc_github_status',{})
 query={'repository':repo,'expected_actor_id':2839512,'request_id':rid,'reconcile':False}
 local=await recovery.tool('sdlc_github_operation_status',query)
 reconciled=await recovery.tool('sdlc_github_operation_status',{**query,'reconcile':True})
 await recovery.close()
 result={'runtime_sha':SHA,'status':'PASS' if not receipt_before and local and local['effect']=='unknown' else 'NOT_RUN','request_id':rid,'intent_observed_at':observed,'receipt_present_before_kill':receipt_before,'process_a_exit_code':a.p.returncode,'process_b_result':evidence_summary(second) if second else None,'restart_local_result':evidence_summary(local) if local else None,'readonly_reconcile_result':evidence_summary(reconciled) if reconciled else None,'client_write_calls':2,'distinct_write_request_ids':1,'dispatch_order':'Both equal-ID calls dispatched before killing A and before observing any unknown result; B contended with the existing durable claim. No write dispatched after unknown.','remote_effect':'unknown' if not reconciled or reconciled['effect']=='unknown' else reconciled['effect'],'upstream_calls':'not externally observed','automatic_replay_observed':False,'limitations':['This exercises one actual after-intent process-crash window, not every deterministic fault-injection window.','HTTP mutation counts are not externally instrumented; two stdio calls are not two HTTP calls.','Killing A closes its real SDK connection, but does not isolate an SDK-only disconnect from a process crash.'],'followup':'Read original operation_status or perform remote read-only verification; preserve intent and all receipts. No cleanup write after unknown.'}
 atomic_json(OUT/'crash-race.json',result)
 state.update(finished_at=stamp(),result_status=result['status'],remote_effect=result['remote_effect']);atomic_json(statefile,state)
 print(json.dumps({k:result[k] for k in ('status','request_id','remote_effect','client_write_calls','process_a_exit_code')}))
if __name__=='__main__':asyncio.run(main())
