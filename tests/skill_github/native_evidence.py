"""Check native-host evidence integrity; never substitute an SDK client for a host.

The local Goal drives each real host with its native approval policy. This module
validates the resulting trace bundle; provenance/behavior is independently reviewed.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from packages.sdlc_github.models import ensure_no_secret, GithubError
from packages.sdlc_github.operations import TOOLS, WRITE_TOOLS

HOSTS=('codex','cursor','claude-code')
CHECKS=('discovery','explicit_invocation','approval_denial','write_readback','restart_receipt',
        'no_implicit_invocation','exclusive_execution','workspace_isolation','secret_scan')


def check_workspace_access(trace):
    if (type(trace.get('file_count')) is not int or trace['file_count'] < 10000
            or not trace.get('before_sha256') or trace['before_sha256'] != trace.get('after_sha256')):
        raise ValueError('Workspace file integrity is not evidenced')
    access = trace.get('workspace_access')
    if not isinstance(access, dict) or access.get('complete') is not True or not isinstance(access.get('events'), list):
        raise ValueError('Hashes cannot prove absence of enumeration, search or content reads')
    for event in access['events']:
        if not isinstance(event, dict) or not isinstance(event.get('path'), str) or not event['path']:
            raise ValueError('Invalid access observation')
        if event.get('actor') == 'host_discovery':
            if event.get('action') not in {'enumerate', 'search', 'read'}:
                raise ValueError('Discovery cannot authorize workspace mutation')
        elif event.get('actor') == 'skill':
            if event.get('scope') != 'declared_plugin' or event.get('action') != 'read':
                raise ValueError('Skill delegated an unrelated scan/read/write')
        else:
            raise ValueError('Unknown attribution cannot support a no-scan conclusion')


def template(host,sha,lock_sha):
    return {'contract':'sdlc-ai-spec/github-native-evidence/v1','host':host,'host_version':None,
            'runtime_sha':sha,'dependency_lock_sha256':lock_sha,
            'checks':{name:{'status':'NOT_RUN','trace':None,'trace_sha256':None} for name in CHECKS}}


def validate_native(directory,sha,lock_sha):
    root=Path(directory).resolve();rows=[]
    for host in HOSTS:
        path=root/(host+'.json')
        if not path.is_file() or path.is_symlink():
            rows.append({'host':host,'status':'BLOCKED','reason':'Native evidence record missing'});continue
        try:
            document=json.loads(path.read_text());ensure_no_secret(document)
            if document.get('host')!=host or document.get('runtime_sha')!=sha or document.get('dependency_lock_sha256')!=lock_sha:
                raise ValueError('Source/lock/host binding mismatch')
            if not isinstance(document.get('host_version'),str) or not document['host_version'].strip():
                raise ValueError('Actual native host version missing')
            if set(document.get('checks',{}))!=set(CHECKS):raise ValueError('Incomplete native case set')
            missing=[]
            for name in CHECKS:
                check=document['checks'][name]
                if check.get('status')!='PASS':missing.append(name);continue
                relative=Path(check.get('trace') or '')
                file=root/relative
                if relative.is_absolute() or '..' in relative.parts or file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(root):
                    raise ValueError('Unsafe or absent trace path')
                content=file.read_bytes()
                if not content or hashlib.sha256(content).hexdigest()!=check.get('trace_sha256'):
                    raise ValueError('Trace digest mismatch')
                trace=json.loads(content);ensure_no_secret(trace)
                if trace.get('host')!=host or trace.get('runtime_sha')!=sha:raise ValueError('Trace provenance binding mismatch')
                calls=trace.get('calls',[])
                if not isinstance(calls,list):raise ValueError('Tool call transcript required')
                if name=='discovery' and set(trace.get('tools',[]))!=set(TOOLS):raise ValueError('Wrong discovery set')
                if name=='explicit_invocation' and not any(c.get('tool')=='sdlc_github_status' and c.get('result',{}).get('actor') for c in calls):raise ValueError('No native status result')
                if name=='approval_denial' and (trace.get('host_permission_decision')!='denied' or trace.get('remote_effect')!='none' or trace.get('write_tool_executed') is not False):raise ValueError('Native denial evidence missing')
                if name=='write_readback' and not any(c.get('tool') in WRITE_TOOLS and c.get('result',{}).get('effect')=='confirmed' and c.get('result',{}).get('receipt',{}).get('readback_verified') is True for c in calls):raise ValueError('No confirmed native write/readback')
                if name=='restart_receipt' and (trace.get('process_restarted') is not True or not any(c.get('tool')=='sdlc_github_operation_status' and c.get('result',{}).get('effect')=='confirmed' for c in calls)):raise ValueError('No restarted receipt result')
                if name=='no_implicit_invocation' and any(c.get('tool') in TOOLS for c in calls):raise ValueError('Implicit invocation occurred')
                if name=='exclusive_execution' and trace.get('sibling_skill_invocations')!=[]:raise ValueError('Sibling isolation not evidenced')
                if name=='workspace_isolation':check_workspace_access(trace)
                if name=='secret_scan' and (trace.get('secret_findings')!=[] or trace.get('files_scanned',0)<1):raise ValueError('Secret scan incomplete')
            rows.append({'host':host,'status':'BLOCKED' if missing else 'PASS','pending_checks':missing,'record_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        except (ValueError,TypeError,KeyError,OSError,AttributeError,GithubError):
            rows.append({'host':host,'status':'FAIL','reason':'Native evidence is malformed, unsafe, unbound, or does not satisfy its oracle'})
    return {'layer':'native','status':'FAIL' if any(x['status']=='FAIL' for x in rows) else 'BLOCKED' if any(x['status']=='BLOCKED' for x in rows) else 'PASS',
            'gate':'OUT_OF_SCOPE_MANUAL_FEEDBACK','meaning':'Optional feedback integrity checks, not a mandatory certificate. Original traces remain necessary; hashes alone do not prove no scans.', 'hosts':rows}
