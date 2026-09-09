"""Optional Issue publishing. Shares projections; never advances lifecycle gates.

Uses an explicitly installed/authenticated gh transport, no implicit fallback.
Intent/receipt rows reuse the operations journal with run_id=NULL; all remote
writes have exact scope and are reconciled instead of blindly repeated.
"""
from __future__ import annotations

import re
import subprocess
from .common import Fault, canonical, digest, file_lock, loads, now, redact, require
from .rendering import markdown, snapshot
from .storage import Store, insert, one

COMMANDS = {'github.preview', 'github.publish', 'github.status', 'github.reconcile'}
MAX_BODY = 60000
MAX_PAGES = 20
URL = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)/?\Z')


class GhTransport:
    def api(self, method, endpoint, payload=None):
        require(endpoint == 'graphql' or endpoint.startswith('repos/'), 'GITHUB_ENDPOINT', 'Unapproved API endpoint')
        argv = ['gh', 'api', '--hostname', 'github.com', '--method', method,
                '-H', 'Accept: application/vnd.github+json', endpoint]
        if payload is not None: argv += ['--input', '-']
        try:
            proc = subprocess.run(argv, input=canonical(payload) if payload is not None else None,
                                  capture_output=True, timeout=45)
        except FileNotFoundError as exc:
            raise Fault('GITHUB_TRANSPORT_MISSING', 'Install GitHub CLI and authenticate with gh auth login before publishing', status='blocked') from exc
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Fault('GITHUB_TRANSPORT_ERROR', 'GitHub transport did not return a verified response', status='blocked') from exc
        # Do not persist arbitrary gh stderr, environment, tokens or HTTP headers.
        require(proc.returncode == 0, 'GITHUB_API_ERROR', 'GitHub API failed; check identity, Issue permissions and network', status='blocked')
        require(len(proc.stdout) <= 8*1024*1024, 'GITHUB_RESPONSE_LIMIT', 'Response exceeds the bounded reader', status='blocked')
        try: return loads(proc.stdout)
        except Fault as exc: raise Fault('GITHUB_RESPONSE_INVALID', 'GitHub did not return valid JSON', status='blocked') from exc


def target(url):
    match = URL.fullmatch(url or '')
    require(match and all(s not in {'.','..'} for s in match.groups()[:2]), 'GITHUB_TARGET_REQUIRED',
            'Select one exact https://github.com/owner/repo/issues/number URL', status='needs_input')
    owner, repo, number = match.groups()
    return f'https://github.com/{owner}/{repo}/issues/{number}', f'repos/{owner}/{repo}', int(number)


def records(con, project, change):
    result = []
    for row in con.execute("SELECT * FROM operations WHERE project_id=? AND command='github.publish' ORDER BY created_at,operation_id", (project,)):
        intent = loads(row['intent_json']) if row['intent_json'] else {}
        if intent.get('change_id') == change: result.append((dict(row), intent))
    return result


def preview(store, project, change, payload):
    revision = payload.get('revision_id')
    if not revision:
        with store.read() as con:
            revision = one(con, 'SELECT active_revision_id FROM changes WHERE project_id=? AND change_id=?', (project, change))[0]
        require(revision, 'GITHUB_DRAFT', 'Complete the current content phase before sharing', status='blocked')
    data = snapshot(store, project, change, revision)
    require(data['revision']['state'] == 'committed', 'GITHUB_DRAFT', 'Commit the selected phase content before sharing; drafts are not published implicitly', status='blocked')
    issue_url = payload.get('issue_url')
    if not issue_url:
        with store.read() as con:
            urls = {intent['issue_url'] for row, intent in records(con, project, change) if row['status']=='succeeded'}
        require(len(urls)==1, 'GITHUB_TARGET_REQUIRED', 'Provide the target Issue URL once; multiple targets require an explicit selection', status='needs_input')
        issue_url = urls.pop()
    issue_url, repo_path, number = target(issue_url)
    phase = payload.get('phase', 'ALL')
    body = redact(markdown(data, phase))
    # Local absolute locations are not portable or appropriate for Issue sharing.
    body = re.sub(r'(?<![A-Za-z0-9])(?:/Users/|/home/|/private/tmp/|/tmp/)[^\s`|<>]*', '[本地路径]', body)
    body = body.replace('@', '@\u200b')  # Do not turn user-provided prose into mass mentions.
    require(len(body.encode('utf-8')) <= MAX_BODY-512, 'GITHUB_BODY_LIMIT', 'Select a single phase; the generated Markdown exceeds the Issue comment budget', status='blocked')
    result = {'issue_url':issue_url,'repository_path':repo_path,'issue_number':number,'change_id':change,
              'revision_id':data['revision']['revision_id'],'phase':phase,'body':body,'body_digest':digest(body)}
    result['preview_digest'] = digest(result)
    return result


def response(data, operation_id=None):
    ok = data.get('state') not in {'unknown','conflict'}
    return {'api_version':'2','ok':ok,'status':'completed' if ok else data['state'], 'operation_id':operation_id,
            'run_id':None,'data':data,'errors':[] if ok else [{'code':'GITHUB_UNCONFIRMED','message':'Remote effect is not confirmed; reconcile this publication before any further send'}],
            'next_actions':[] if ok else [{'action':'github.reconcile','operation_id':operation_id}]}


def confirm_comment(comment, intent):
    require(isinstance(comment,dict) and type(comment.get('id')) is int and comment['id'] > 0,
            'GITHUB_READBACK', 'Comment identity missing', status='blocked')
    require(comment.get('issue_url') == 'https://api.github.com/'+intent['repository_path']+'/issues/'+str(intent['issue_number']),
            'GITHUB_READBACK', 'Comment belongs to another Issue', status='blocked')
    require(comment.get('body') == intent['body'] and comment.get('user',{}).get('id') == intent['actor_id'],
            'GITHUB_READBACK', 'Published comment differs or has another author', status='conflict')
    expected = intent['issue_url']+'#issuecomment-'+str(comment['id'])
    require(comment.get('html_url') == expected, 'GITHUB_READBACK', 'Unexpected comment URL', status='blocked')
    return {'state':'confirmed','issue_url':intent['issue_url'],'comment_url':expected,'comment_id':comment['id'],
            'revision_id':intent['revision_id'],'phase':intent['phase'],'body_digest':intent['body_digest']}


def read_identity(transport):
    result = transport.api('POST','graphql',{'query':'query { viewer { databaseId login } }'})
    require(isinstance(result,dict) and not result.get('errors'), 'GITHUB_IDENTITY', 'Authenticated viewer lookup failed', status='blocked')
    viewer = result.get('data',{}).get('viewer') or {}
    actor = {'id':viewer.get('databaseId'), 'login':viewer.get('login')}
    require(isinstance(actor,dict) and type(actor.get('id')) is int and actor['id'] > 0,
            'GITHUB_IDENTITY', 'Authenticated GitHub identity is unavailable', status='blocked')
    return actor['id']


def save(store, op, data):
    value = response(data, op)
    with store.transaction() as con:
        con.execute('UPDATE operations SET status=?,response_json=? WHERE operation_id=?',
                    ('succeeded' if value['ok'] else 'unknown',canonical(value).decode(),op))
    return value


def reconcile(store, project, change, workspace, op, transport):
    with store.read() as con:
        row = dict(one(con, "SELECT * FROM operations WHERE project_id=? AND operation_id=? AND command='github.publish'", (project,op),code='GITHUB_RECEIPT'))
    intent = loads(row['intent_json'])
    require(intent['change_id']==change, 'GITHUB_RECEIPT_SCOPE', 'Receipt belongs to another change')
    require(row['origin_kind']=='local' and intent['workspace_id']==workspace, 'GITHUB_IMPORTED',
            'Imported publication receipts are history; reconcile in their originating workspace', status='blocked')
    require(read_identity(transport)==intent['actor_id'], 'GITHUB_IDENTITY_CHANGED', 'Reconcile with the original publishing account', status='blocked')
    matched = []
    for page in range(1,MAX_PAGES+1):
        comments = transport.api('GET', f'{intent["repository_path"]}/issues/{intent["issue_number"]}/comments?per_page=100&page={page}')
        require(isinstance(comments,list), 'GITHUB_RESPONSE_INVALID', 'Expected Issue comment page', status='blocked')
        for comment in comments:
            if intent['marker'] in (comment.get('body') or ''):
                matched.append(comment)
        if len(comments)<100: break
    else:
        return save(store,op,{'state':'unknown','reason':'Comment pagination incomplete; no repeat write','issue_url':intent['issue_url']})
    if len(matched)==1:
        try: data=confirm_comment(matched[0],intent)
        except Fault: data={'state':'conflict','reason':'Marker found but author/content/target differs; inspect remote content'}
        return save(store,op,data)
    return save(store,op,{'state':'unknown','reason':'No unique verified comment found; absence is not authorization to replay','issue_url':intent['issue_url']})


def invoke(root, request, transport=None):
    store = Store(root); config = store.config(); transport = transport or GhTransport()
    project=request.get('project_id',config['project_id']); workspace=request.get('workspace_id',config['workspace_id'])
    change=request.get('change_id'); payload=request.get('payload',{}); command=request['command']
    with store.read() as con:
        one(con,'SELECT * FROM changes WHERE project_id=? AND change_id=?',(project,change),code='CHANGE_SCOPE')
        ws=one(con,'SELECT * FROM workspaces WHERE project_id=? AND workspace_id=?',(project,workspace),code='WORKSPACE_SCOPE')
        if command not in {'github.preview','github.status'}:
            require(config.get('root_path')==str(store.root) and ws['instance_id']==config['instance_id'], 'WORKSPACE_MOVED','Rebind the workspace before publishing',status='blocked')
    if command=='github.preview': return response(preview(store,project,change,payload))
    if command=='github.status':
        with store.read() as con:
            return response({'publications':[{'operation_id':r['operation_id'],'status':r['status'],'origin_kind':r['origin_kind'],
                'issue_url':i['issue_url'],'phase':i['phase'],'revision_id':i['revision_id'],
                'receipt':loads(r['response_json']).get('data')} for r,i in records(con,project,change)]})
    with file_lock(store.home/'.command.lock'):
        if command=='github.reconcile': return reconcile(store,project,change,workspace,payload['publication_id'],transport)
        require(payload.get('confirmed') is True, 'GITHUB_CONFIRMATION_REQUIRED', 'Publishing requires the current user intent for this exact Issue and preview',status='blocked')
        prepared=preview(store,project,change,payload)
        require(payload['preview_digest']==prepared['preview_digest'], 'GITHUB_PREVIEW_CHANGED','Artifact or target changed; show a fresh preview before sending',status='conflict')
        actor=read_identity(transport)
        issue=transport.api('GET',f'{prepared["repository_path"]}/issues/{prepared["issue_number"]}')
        require(isinstance(issue,dict) and issue.get('html_url')==prepared['issue_url'] and 'pull_request' not in issue,
                'GITHUB_TARGET', 'Select an existing Issue, not a PR or another repository',status='blocked')
        require(issue.get('locked') is not True,'GITHUB_LOCKED','Target Issue is locked',status='blocked')
        key=digest({'project':project,'change':change,'preview':prepared['preview_digest'],'actor':actor})
        op=request.get('operation_id') or 'github-'+key
        with store.read() as con:
            occupied=con.execute('SELECT * FROM operations WHERE operation_id=?',(op,)).fetchone()
            if occupied:
                require(occupied['command']=='github.publish' and occupied['project_id']==project and occupied['request_digest']==key,
                        'OPERATION_CONFLICT','This operation_id already names a different request',status='conflict')
            entries=records(con,project,change)
        existing=occupied or next((r for r,i in entries if r['request_digest']==key),None)
        if existing:
            require(existing['origin_kind']=='local','GITHUB_IMPORTED','Imported receipt is history; inspect/reconcile in its source workspace',status='blocked')
            if existing['status']=='succeeded':
                result=loads(existing['response_json']); result['data']['idempotent']=True; return result
            return response({'state':'unknown','issue_url':prepared['issue_url'],'reason':'Existing uncertain send; reconcile, do not POST again'},existing['operation_id'])
        unresolved=next((r for r,i in entries if r['status']=='unknown' and i['issue_url']==prepared['issue_url'] and i['phase']==prepared['phase']),None)
        if unresolved:
            return response({'state':'unknown','reason':'A previous publication to this target is unconfirmed; reconcile it first'},unresolved['operation_id'])
        marker='<!-- sdlc-v2-publication:'+key+' -->'
        intent={'kind':'github.publish','project_id':project,'change_id':change,'workspace_id':workspace,'actor_id':actor,
                **prepared,'marker':marker,'body':prepared['body']+'\n'+marker+'\n'}
        pending=response({'state':'unknown','issue_url':prepared['issue_url'],'reason':'Durable intent before remote write'},op)
        with store.transaction() as con:
            insert(con,'operations',{'operation_id':op,'project_id':project,'run_id':None,'command':'github.publish',
                'request_digest':key,'status':'unknown','response_json':canonical(pending).decode(),'intent_json':canonical(intent).decode(),'created_at':now()})
        try:
            posted=transport.api('POST',f'{prepared["repository_path"]}/issues/{prepared["issue_number"]}/comments',{'body':intent['body']})
            require(type(posted.get('id')) is int and posted['id']>0,'GITHUB_READBACK','POST did not return a comment id',status='blocked')
            comment=transport.api('GET',f'{prepared["repository_path"]}/issues/comments/{posted["id"]}')
            return save(store,op,confirm_comment(comment,intent))
        except (Fault,OSError,ValueError,TypeError,AttributeError):
            return save(store,op,{'state':'unknown','issue_url':prepared['issue_url'],'reason':'Send/readback not confirmed; use github.reconcile'})
