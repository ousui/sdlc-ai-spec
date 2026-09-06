"""Explicit local real-GitHub validation using the unmodified production stdio server.

No real credential is loaded during import. Mutations are confined to this batch's
new objects. Unknown requests retain their UUID and stop all subsequent writes.
"""
from __future__ import annotations
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from packages.sdlc_github.models import canonical, digest, redact, ensure_no_secret
from packages.sdlc_github.operations import READS, WRITES, validate_request
from packages.sdlc_github.service import items

ROOT=Path(__file__).resolve().parents[2]
FIXTURE_KEYS={'repository','head','base','file_path','sha','tag','tag_repository','workflow_id','run_id','job_id'}


def fixture_config(path):
    value=json.loads(Path(path).read_text())
    if not isinstance(value,dict) or set(value)-FIXTURE_KEYS:
        raise ValueError('Unsupported fixture fields')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',str(value.get('repository',''))):
        raise ValueError('Explicit fixture repository required')
    for key in ('head','base','file_path'):
        if key in value and (not isinstance(value[key],str) or not value[key]):raise ValueError('Invalid fixture selector')
    if value.get('tag_repository') and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',value['tag_repository']):
        raise ValueError('Invalid read-only tag/release repository')
    for key in ('run_id','job_id'):
        if value.get(key) is not None and (type(value[key]) is not int or value[key]<1):raise ValueError('Invalid numeric fixture')
    if value.get('sha') and not re.fullmatch('[0-9a-f]{40}',value['sha']):raise ValueError('Exact fixture SHA required')
    ensure_no_secret(value)
    return value


def atomic_json(path:Path,value):
    ensure_no_secret(value)
    content=canonical(value)
    temp=path.with_name('.'+path.name+'-'+str(uuid4()))
    fd=os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        view=memoryview(content)
        while view:
            written=os.write(fd,view)
            if written<=0:raise OSError('Short state write')
            view=view[written:]
        os.fsync(fd)
    finally:os.close(fd)
    os.replace(temp,path)


def evidence_summary(value):
    """Do not archive private repository bodies, files, diffs or job logs."""
    summary={k:value.get(k) for k in ('contract','ok','status','operation','actor','repository','target','pagination','completeness','effect','receipt','errors','warnings','next_action')}
    summary['response_sha256']=digest(value)
    data=value.get('data')
    if isinstance(data,dict):
        summary['identifiers']={k:data[k] for k in ('number','id','url','html_url','sha','state','draft','tag_name','job_id') if k in data and isinstance(data[k],(str,int,bool))}
    try:summary['item_count']=len(items(data))
    except Exception:pass
    return summary


class LiveBatch:
    def __init__(self,session,fixture,output,*,allow_writes=False):
        self.session=session;self.fixture=fixture;self.output=Path(output)
        self.output.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.state_path=self.output/'run-state.json'
        self.state=json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            'run_id':str(uuid4()),'fixture_digest':digest(fixture),'requests':{},'objects':{},'actor_id':None}
        if self.state.get('fixture_digest')!=digest(fixture):raise ValueError('Existing batch belongs to a different fixture')
        self.allow_writes=allow_writes;self.write_blocked=False;self.rows=[];self.actor=None
        self.repo=fixture['repository'].lower();self.counter=0
        atomic_json(self.state_path,self.state)

    def blocked(self,operation,reason):
        self.rows.append({'operation':operation,'status':'BLOCKED','reason':reason,'mcp_calls':0})

    async def call(self,operation,tool,arguments):
        self.counter+=1
        try:
            response=await self.session.call_tool(tool,arguments)
            value=response.structuredContent
            if not isinstance(value,dict):raise ValueError('Structured result required')
        except Exception:
            # A sent request can have an effect even if the pipe closes.
            value={'operation':operation,'ok':False,'status':'unknown','effect':'unknown' if operation in WRITES else 'none',
                   'errors':[{'code':'CLIENT_CALL_FAILED','message':'Inspect the original request receipt; do not replay with a new ID.'}]}
        code=(value.get('errors') or [{}])[0].get('code')
        status='PASS' if value.get('ok') else 'BLOCKED' if code in {'AUTH_REQUIRED','AUTH_FAILED','PERMISSION_DENIED','CAPABILITY_UNAVAILABLE','NOT_FOUND_OR_INACCESSIBLE','RATE_LIMITED'} else 'FAIL'
        row={'operation':operation,'status':status,'tool':tool,'arguments':arguments,'mcp_calls':1,'upstream_calls':'not externally observed',
             'response':evidence_summary(value)}
        self.rows.append(row)
        # Immutable per-call records allow a resumed batch without erasing history.
        atomic_json(self.output/('event-'+str(uuid4())+'.json'),row)
        if operation in WRITES and value.get('effect')=='unknown':self.write_blocked=True
        return value

    async def read(self,operation,repository=None,**parameters):
        args={'operation':operation,'repository':repository or self.repo,**parameters}
        validate_request('sdlc_github_read',args)
        return await self.call(operation,'sdlc_github_read',args)

    async def write(self,operation,**parameters):
        if not self.allow_writes or self.write_blocked:
            self.blocked(operation,'Explicit --allow-test-writes required, or a previous effect is unknown')
            return None
        args={'repository':self.repo,'expected_actor_id':self.actor['id'],'write_policy':'auto','dry_run':False,**parameters}
        old=self.state['requests'].get(operation)
        if old:
            if {k:v for k,v in old.items() if k!='request_id'}!=args:
                self.blocked(operation,'Persisted request parameters differ; preserve this batch and inspect its receipt')
                self.write_blocked=True;return None
            args=old
        else:
            args['request_id']=str(uuid4());self.state['requests'][operation]=args
            atomic_json(self.state_path,self.state)  # before any network side effect
        tool='sdlc_github_'+operation.replace('.','_')
        validate_request(tool,args)
        value=await self.call(operation,tool,args)
        if value.get('effect')=='confirmed' and isinstance(value.get('data'),dict):
            number=value['data'].get('number')
            if operation in {'issue.create','pr.create'} and type(number) is int:
                self.state['objects'][operation.split('.')[0]]=number
                atomic_json(self.state_path,self.state)
        return value

    async def run(self):
        status=await self.call('status','sdlc_github_status',{})
        self.actor=status.get('actor')
        if not self.actor:
            for operation in (*READS,*WRITES):self.blocked(operation,'Verified identity unavailable')
            return self.report()
        if self.state['actor_id'] not in (None,self.actor['id']):
            for operation in (*READS,*WRITES):self.blocked(operation,'Batch is bound to another actor; use its original credential')
            return self.report()
        self.state['actor_id']=self.actor['id'];atomic_json(self.state_path,self.state)
        title='[sdlc-github-eval:'+self.state['run_id']+']'
        body='Authorized synthetic GitHub foundation evaluation. Preserve this object and its operation markers for review.'
        await self.write('issue.create',title=title+' issue',body=body)
        if self.fixture.get('head') and self.fixture.get('base'):
            await self.write('pr.create',head=self.fixture['head'],base=self.fixture['base'],title=title+' draft',body=body)
        else:self.blocked('pr.create','Existing distinct head/base fixture required; no branches are created')
        issue=self.state['objects'].get('issue');pr=self.state['objects'].get('pr')
        if issue:await self.write('comment.create',subject_type='issue',number=issue,body=body+' Ordinary comment.')
        else:self.blocked('comment.create','This batch has no confirmed created Issue')
        # Read all 27 operations, using only exact fixture IDs or IDs obtained here.
        await self.read('repo.branches')
        commits=await self.read('repo.commits',**({'sha':self.fixture['head']} if self.fixture.get('head') else {}))
        sha=self.fixture.get('sha')
        if not sha and commits.get('ok'):
            try:sha=items(commits['data'])[0]['sha']
            except (IndexError,KeyError,TypeError):pass
        if sha:
            await self.read('repo.files',path=self.fixture.get('file_path','README.md'),sha=sha)
            await self.read('repo.commit',sha=sha)
        else:
            self.blocked('repo.files','Readable commit fixture unavailable');self.blocked('repo.commit','Readable commit fixture unavailable')
        tag_repo=self.fixture.get('tag_repository') or self.repo
        tags=await self.read('repo.tags',repository=tag_repo)
        tag=self.fixture.get('tag')
        if not tag and tags.get('ok'):
            try:tag=items(tags['data'])[0]['name']
            except (IndexError,KeyError,TypeError):pass
        if tag:await self.read('repo.tag',repository=tag_repo,tag=tag)
        else:self.blocked('repo.tag','Existing Tag fixture required; this batch never creates Tags')
        await self.read('issue.list',state='all')
        for operation in ('issue.get','issue.comments'):
            if issue:await self.read(operation,number=issue)
            else:self.blocked(operation,'This batch has no confirmed created Issue')
        await self.read('pr.list',state='all')
        for operation in ('pr.get','pr.diff','pr.files','pr.reviews','pr.review-comments','pr.comments','pr.checks','pr.status'):
            if pr:await self.read(operation,number=pr)
            else:self.blocked(operation,'This batch has no confirmed created Draft PR')
        await self.read('actions.workflows')
        await self.read('actions.runs',**({'workflow_id':str(self.fixture['workflow_id'])} if self.fixture.get('workflow_id') else {}))
        run_id=self.fixture.get('run_id');job_id=self.fixture.get('job_id')
        if run_id:
            jobs=await self.read('actions.jobs',run_id=run_id)
            await self.read('actions.artifacts',run_id=run_id)
            await self.read('actions.run',run_id=run_id)
            if not job_id and jobs.get('ok'):
                try:job_id=min(x['id'] for x in items(jobs['data']))
                except (ValueError,KeyError,TypeError):pass
        else:
            for operation in ('actions.jobs','actions.artifacts','actions.run'):self.blocked(operation,'Exact existing run_id fixture required')
        if job_id:await self.read('actions.logs',job_id=job_id)
        else:self.blocked('actions.logs','Exact Job fixture unavailable; no implicit aggregation or workflow execution')
        await self.read('release.list',repository=tag_repo)
        if tag:await self.read('release.get',repository=tag_repo,tag=tag)
        else:self.blocked('release.get','Existing release/tag fixture required')
        await self.read('release.latest',repository=tag_repo)
        # Close only objects created by this batch. Comments and all audit traces remain.
        if issue:await self.write('issue.update',number=issue,title=title+' issue verified',state='closed')
        else:self.blocked('issue.update','This batch has no confirmed created Issue')
        if pr:await self.write('pr.update',number=pr,title=title+' draft verified',state='closed')
        else:self.blocked('pr.update','This batch has no confirmed created Draft PR')
        return self.report()

    def report(self):
        for operation in (*READS,*WRITES):
            if not any(r['operation']==operation for r in self.rows):self.blocked(operation,'Batch stopped before this operation')
        states={r['status'] for r in self.rows}
        status='FAIL' if 'FAIL' in states else 'BLOCKED' if 'BLOCKED' in states else 'PASS'
        value={'layer':'live','status':status,'run_id':self.state['run_id'],'actor':self.actor,'repository':self.repo,'rows':self.rows,
               'native_behavior':'NOT_RUN','note':'Production stdio/MCP program evidence, not native-host behavior. Empty lists do not replace missing object fixtures.'}
        atomic_json(self.output/'LIVE-VALIDATION.json',value)
        return value


async def run_live(fixture_path,output,*,data_root,allow_writes=False,plugin=ROOT):
    fixture=fixture_config(fixture_path)
    output=Path(output);output.mkdir(parents=True,exist_ok=True,mode=0o700)
    if not os.environ.get('SDLC_GITHUB_TOKEN'):
        return {'layer':'live','status':'BLOCKED','reason':'Set SDLC_GITHUB_TOKEN in the local host environment; never put it in chat or fixtures.'}
    if not Path(data_root).is_absolute() or not Path(data_root).is_dir():
        return {'layer':'live','status':'BLOCKED','reason':'Explicit existing absolute data root required'}
    parameters=StdioServerParameters(command=sys.executable,args=['-B',str(plugin/'scripts/sdlc_github_mcp.py'),'--data-root',str(data_root)],
                                    env={'SDLC_GITHUB_TOKEN':os.environ['SDLC_GITHUB_TOKEN'],'PYTHONDONTWRITEBYTECODE':'1'})
    # Suppress upstream diagnostics; the production result already carries safe errors.
    with open(os.devnull,'w') as null:
        try:
            async with stdio_client(parameters,errlog=null) as (read,write):
                async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=1800)) as session:
                    await session.initialize()
                    return await LiveBatch(session,fixture,output,allow_writes=allow_writes).run()
        except Exception:
            return {'layer':'live','status':'BLOCKED','reason':'Production stdio session failed; inspect persisted request IDs without replay. No native result is implied.'}


async def run_identity(output,*,data_root,repository,plugin=ROOT):
    """Two real processes and credentials; a dry-run mismatch cannot mutate GitHub."""
    from contextlib import AsyncExitStack
    token_a=os.environ.get('SDLC_GITHUB_TOKEN');token_b=os.environ.get('SDLC_GITHUB_TOKEN_B')
    if not token_a or not token_b:
        return {'layer':'identity','status':'BLOCKED','reason':'Two local PATs for different actors are required in SDLC_GITHUB_TOKEN and SDLC_GITHUB_TOKEN_B; never archive their values.'}
    root=Path(data_root)
    if not root.is_absolute() or not root.is_dir():return {'layer':'identity','status':'BLOCKED','reason':'Existing absolute stable data root required'}
    try:
        with open(os.devnull,'w') as null:
            async with AsyncExitStack() as stack:
                sessions=[]
                for token in (token_a,token_b):
                    params=StdioServerParameters(command=sys.executable,args=['-B',str(plugin/'scripts/sdlc_github_mcp.py'),'--data-root',str(root)],env={'SDLC_GITHUB_TOKEN':token,'PYTHONDONTWRITEBYTECODE':'1'})
                    read,write=await stack.enter_async_context(stdio_client(params,errlog=null))
                    client=await stack.enter_async_context(ClientSession(read,write,read_timeout_seconds=timedelta(seconds=120)))
                    await client.initialize();sessions.append(client)
                statuses=[(await c.call_tool('sdlc_github_status',{})).structuredContent for c in sessions]
                actors=[x.get('actor') for x in statuses]
                if not all(actors):return {'layer':'identity','status':'BLOCKED','reason':'Both identities must be verified online'}
                if actors[0]['id']==actors[1]['id']:return {'layer':'identity','status':'BLOCKED','reason':'Different PAT values for the same actor do not prove cross-account isolation','actors':actors}
                probe={'repository':repository,'title':'Identity mismatch dry-run fixture','body':'Must not be written','expected_actor_id':actors[0]['id'],
                       'request_id':str(uuid4()),'dry_run':True,'write_policy':'auto'}
                result=(await sessions[1].call_tool('sdlc_github_issue_create',probe)).structuredContent
                passed=result.get('effect')=='none' and (result.get('errors') or [{}])[0].get('code')=='ACTOR_MISMATCH'
                report={'layer':'identity','status':'PASS' if passed else 'FAIL','actors':actors,'probe':evidence_summary(result),
                        'meaning':'Two real stdio processes; native-host behavior is a separate layer. No remote mutation requested.'}
                atomic_json(Path(output)/'IDENTITY-VALIDATION.json',report)
                return report
    except Exception:
        return {'layer':'identity','status':'BLOCKED','reason':'Identity session failed; no credential or raw exception archived'}
