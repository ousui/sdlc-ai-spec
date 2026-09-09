"""Review-only regressions against the checked-out Runtime plugin, never a product closure certificate.
Invokes the public CLI in separate processes; no SQL writes or result mocks.
"""
from pathlib import Path
import sys,tempfile,json,stat,subprocess,hashlib
PLUGIN=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PLUGIN))
from packages.sdlc.runtime import Runtime
from packages.sdlc.execution import observe

TRACE=[]
class Case:
 def __init__(self,root):
  self.root=Path(root);self.change=None;self.run=None;self.rev=None;self.gen=0;self.ids={};self.lease=None
 def call(self,cmd,p=None,*,bind=True,expect=True,generation=False):
  req={'api_version':'2','command':cmd,'payload':p or {}}
  if bind and self.change:req['change_id']=self.change
  if bind and self.run:req['run_id']=self.run
  if generation:req['expected_generation']=self.gen
  process=subprocess.run([sys.executable,'-B',str(PLUGIN/'scripts/sdlc.py'),'--root',str(self.root),'--request','-'],input=json.dumps(req),text=True,capture_output=True,timeout=20);r=json.loads(process.stdout);TRACE.append({'root':str(self.root),'request':req,'response':r})
  if expect and not r['ok']:raise AssertionError((cmd,r))
  return r
 def submit(self,phase,ops):
  d=self.call('phase.submit',{'phase':phase,'revision_id':self.rev,'operations':ops},generation=True)['data'];self.gen=d['generation'];self.ids.update(d['ids']);return d
 def complete(self,phase,expect=True):
  p={'phase':phase,'revision_id':self.rev}
  if self.lease:p['lease_id']=self.lease
  r=self.call('phase.complete',p,generation=phase in {'REQ','DSN','PLN'},expect=expect)
  if r['ok'] and phase in {'REQ','DSN','PLN'}:self.rev=r['data']['revision_id'];self.gen=r['data']['generation']
  return r
 def ref(self,name):return {'id':self.ids[name]}
 def setup(self,rls_check=False):
  self.call('workspace.init',{'name':'isolated-review'},bind=False)
  ctx=self.call('context.commit',{'summary':'Synthetic review fixture','entries':[{'kind':'fact','name':'scope','content':'Test protocol invariants in a disposable directory'}]},bind=False)['data']['context_id']
  r=self.call('change.create',{'slug':'review','context_id':ctx,'title':'Protocol review','summary':'Review only','goal':'Verify protocol invariants','in_scope':'Synthetic local fixture','out_of_scope':'Production, network and deployments','delivery_mode':'local','delivery_target':'.sdlc/exports/review','original_text':'Review a minimal local workflow','authorizations':[{'action':a,'target':t,'issued_by':'review-fixture','basis_text':'User authorized code review; isolated local reproducer only'} for a,t in [('edit_local','main'),('run_check','main'),('package_local','.sdlc/exports/review')]]},bind=False)
  d=r['data'];self.run=r['run_id'];self.change=d['change_id'];self.rev=d['revision_id'];self.ids['source']=d['source_id']
  self.submit('REQ',[{'op':'create_requirement','client_key':'req','kind':'behavior','statement':'Local script retains execution capability','sources':[self.ref('source')]},{'op':'create_criterion','client_key':'ac','condition_text':'A script is edited','expected_result':'It remains executable','requirements':[{'client_key':'req'}]}]);self.complete('REQ')
  self.submit('DSN',[{'op':'create_design','client_key':'dsn','domain':'implementation','title':'Minimal fixture','decision':'Edit local script','rationale':'Exercise public writes','alternatives':'Leave unchanged','detail':'Isolated protocol review, not product acceptance','requirements':[self.ref('req')]},{'op':'create_check','client_key':'accept','purpose':'acceptance','method':'inspection','executor':'agent','description':'Synthetic check for state-machine review','expected_result':'Review fixture ready','required':True,'criteria':[self.ref('ac')]},{'op':'create_check','client_key':'conv','purpose':'convergence','method':'inspection','executor':'agent','description':'Synthetic convergence fixture','expected_result':'No fixture setup gaps','required':True}]);self.complete('DSN')
  ops=[{'op':'create_task','client_key':'imp','target_phase':'IMP','kind':'implement','title':'Edit script','description':'Change isolated script text','completion_text':'Write recorded','scope_paths':[{'resource':'main','path':'.','access':'write'}],'designs':[self.ref('dsn')],'criteria':[self.ref('ac')]},{'op':'create_task','client_key':'rls','target_phase':'RLS','kind':'deliver','title':'Deliver','description':'Local package','completion_text':'Local condition and readback pass','scope_paths':[{'resource':'main','path':'.','access':'read'}]},{'op':'create_check','client_key':'rb','task':{'client_key':'rls'},'purpose':'release_readback','method':'test','executor':'command','description':'Package readback','expected_result':'Package content matches','argv':['@runtime','delivery.readback'],'required':True}]
  if rls_check:
   ops.extend([{'op':'create_check','client_key':'rls-condition','task':{'client_key':'rls'},'purpose':'precondition','method':'inspection','executor':'agent','description':'Local delivery target readiness inspection','expected_result':'Target is usable','required':True},{'op':'create_precondition','client_key':'rls-pre','consumer_task':{'client_key':'rls'},'producer_task':{'client_key':'rls'},'check':{'client_key':'rls-condition'},'enforce_at':'complete','reason':'Check delivery readiness during delivery, before task completion'}])
  self.submit('PLN',ops);self.complete('PLN');self.lease=self.call('run.acquire')['data']['lease_id']
 def task_start(self,key,expect=True):return self.call('task.start',{'revision_id':self.rev,'task_id':self.ids[key],'lease_id':self.lease},expect=expect)
 def review(self,key,expect=True):return self.call('check.record_review',{'revision_id':self.rev,'check_id':self.ids[key],'lease_id':self.lease,'status':'pass','observations':'Synthetic protocol fixture observation only; not real application acceptance.'},expect=expect)
