"""Fixed local delivery, immutable package bytes and independent readback."""
import io
import os
import sys
import tempfile
import zipfile
from pathlib import Path

from . import content, engine, execution, verification
from .common import atomic_write, canonical, digest, loads, now, redact, require, safe_path, sha, uid
from .storage import insert, one
from .domain import native_readback

def row(con, project, change, delivery_id):
    return one(con, 'SELECT * FROM deliveries WHERE project_id=? AND change_id=? AND delivery_id=?',
               (project, change, delivery_id), code='DELIVERY_SCOPE')


def destination(store, target, hashed):
    # Managed outputs stay outside the product input graph and never overwrite
    # arbitrary source files. This supported target is fixed at change creation.
    parts = Path(target).parts
    require(len(parts) >= 3 and parts[:2] == ('.sdlc', 'exports'), 'DELIVERY_TARGET',
            'Local delivery target must be a named directory under .sdlc/exports', '/payload/delivery_target', status='blocked')
    require(len(hashed) == 64 and all(c in '0123456789abcdef' for c in hashed), 'DELIVERY_INTEGRITY', 'Invalid package digest')
    return safe_path(store.root, target+'/'+hashed+'.zip')


def package(store, con, project, change, revision, snapshot_id, evaluation, usage):
    snap = one(con, 'SELECT * FROM code_snapshots WHERE snapshot_id=?', (snapshot_id,))
    files, modes = {}, {}
    for file in loads(snap['untracked_json']):
        resource = file.get('resource', 'main')
        name = 'code/'+resource+'/'+file['path']
        files[name] = store.asset_bytes(con, file['asset_id'], project)
        modes[name] = file['mode']
    files['content.json'] = canonical(store.content(con, revision))+b'\n'
    files['verification.json'] = canonical(evaluation)+b'\n'
    files['USAGE.md'] = (redact(usage)+'\n').encode()
    # Original inputs remain in the complete workspace archive. A deployable
    # package includes only evidence selected by this exact evaluation, not
    # every ancestor ZIP or historic check result.
    assets = {one(con, 'SELECT evidence_asset_id FROM check_results WHERE result_id=?',
                  (item['result_id'],))[0] for item in evaluation['checks'] if item['result_id']}
    attachments = [dict(row) for row in con.execute(
        'SELECT l.original_name,l.purpose,a.sha256,a.size_bytes FROM asset_links l JOIN assets a USING(asset_id) WHERE l.revision_id=? ORDER BY l.ordinal,l.link_id', (revision,))]
    files['attachments.json'] = canonical({'storage': 'complete workspace archive', 'attachments': attachments})+b'\n'
    for asset in assets:
        raw = store.asset_bytes(con, asset, project)
        hashed = sha(raw)
        files[f'assets/{hashed[:2]}/{hashed[2:4]}/{hashed}'] = raw
    from .runtime import runtime_digest
    manifest = {'format': 'sdlc-local-delivery-2', 'project_id': project, 'change_id': change,
                'revision_id': revision, 'snapshot_id': snapshot_id, 'runtime_digest': runtime_digest(),
                'head_commit': snap['head_commit'], 'subject_digest': snap['digest'],
                'files': {name: sha(raw) for name, raw in sorted(files.items())},
                'modes': {name: modes.get(name, 0o644) for name in sorted(files)}}
    require(sum(map(len, files.values())) <= 256*1024*1024, 'DELIVERY_SIZE_LIMIT',
            'Product delivery exceeds 256 MiB expanded; narrow the delivery input scope. Complete history is exported separately.', status='blocked')
    files['manifest.json'] = canonical(manifest)+b'\n'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100000 | modes.get(name, 0o644)) << 16
            archive.writestr(info, raw)
    raw = buffer.getvalue()
    require(len(raw) <= 64*1024*1024, 'DELIVERY_SIZE_LIMIT',
            'Product package exceeds 64 MiB; revise the same change delivery input scope, then verify and retry. History is exported separately.',
            status='blocked', details={'package_bytes': len(raw), 'files': len(files)})
    return store.put_asset(con, project, raw, 'application/zip'), sha(raw), manifest


def prepare(store, con, project, change, run, p):
    engine.adopted(con, project, change, p['revision_id'])
    engine.lease(con, project, change, run, p['lease_id'])
    require(engine.phase(con, project, change, run) == 'RLS', 'PHASE_ORDER', 'Delivery follows converged VFY', status='blocked')
    ch = content.change_row(con, project, change)
    require(ch['delivery_mode'] == 'local', 'DELIVERY_ADAPTER_UNAVAILABLE', 'Only the local delivery adapter is installed', status='blocked')
    verification.authorize(con, project, change, run, 'package_local', ch['delivery_target'])
    evaluation = verification.evaluate(store, con, project, change, p['revision_id'], p.get('environment'), workspace=engine.run_row(con, project, change, run)['workspace_id'])
    require(evaluation['converged'], 'NOT_CONVERGED', 'Current VFY inputs or results no longer converge', status='blocked', details=evaluation)
    readbacks = list(con.execute("SELECT * FROM checks WHERE revision_id=? AND required=1 AND purpose='release_readback'", (p['revision_id'],)))
    require(len(readbacks) == 1 and native_readback(readbacks[0]),
            'READBACK_CHECK_REQUIRED', 'Plan one required command Check with purpose release_readback and argv [@runtime, delivery.readback]', status='blocked')
    check = readbacks[0]
    if check['task_id']:
        task = engine.task_row(con, p['revision_id'], check['task_id'])
        require(con.execute("SELECT 1 FROM steps WHERE run_id=? AND task_id=? AND step_key=? AND status='running'",
                            (run, check['task_id'], 'task:'+check['task_id'])).fetchone(), 'TASK_NOT_RUNNING', 'Start the delivery task', status='blocked')
        verification.ensure_conditions(store, con, project, change, run, p['revision_id'], task, 'execute', p.get('environment'))
    # The immutable native Check defines the delivered source set. Its default
    # is main, while an explicit project scope must not collect sibling code.
    observed = verification.current_subject(store, con, p['revision_id'], check, p.get('environment'))
    snapshot_id = execution.snapshot(store, con, project, run, observed)
    asset, hashed, manifest = package(store, con, project, change, p['revision_id'], snapshot_id, evaluation, p['usage'])
    target = destination(store, ch['delivery_target'], hashed)
    require(not target.exists() or (target.is_file() and sha(target.read_bytes()) == hashed),
            'DELIVERY_TARGET_CONFLICT', 'Existing content-addressed target contains different bytes; preserve it for reconciliation', status='conflict')
    effect = p.get('effect_key', uid())
    require(not con.execute('SELECT 1 FROM deliveries WHERE project_id=? AND effect_key=?', (project, effect)).fetchone(),
            'EFFECT_KEY_CONFLICT', 'Reuse the original delivery identity for this effect', status='conflict')
    step = engine.new_step(con, project, change, run, p['revision_id'], 'RLS', 'delivery:'+effect)
    value = uid()
    vfy = next(r['result_id'] for r in evaluation['checks'] if r['purpose'] == 'convergence')
    insert(con, 'deliveries', {'delivery_id': value, 'project_id': project, 'change_id': change, 'revision_id': p['revision_id'],
           'step_id': step, 'snapshot_id': snapshot_id, 'vfy_result_id': vfy, 'mode': 'local', 'target': ch['delivery_target'],
           'effect_key': effect, 'status': 'prepared', 'summary': 'Prepared exact local package; delivery/readback pending',
           'bundle_asset_id': asset, 'readback_check_id': check['check_id'], 'environment_json': canonical(p.get('environment', {})).decode()})
    return {'delivery_id': value, 'effect_key': effect, 'target': ch['delivery_target'], 'package_sha256': hashed, 'package_path': target.relative_to(store.root).as_posix(),
            'file_count': len(manifest['files']), 'status': 'prepared', 'next_actions': [{'action': 'delivery.execute'}]}


def prepare_effect(store, con, project, change, run, p, work):
    item = row(con, project, change, p['delivery_id'])
    engine.adopted(con, project, change, item['revision_id'])
    engine.lease(con, project, change, run, p['lease_id'])
    require(engine.phase(con, project, change, run) == 'RLS', 'PHASE_ORDER', 'Execute delivery in RLS', status='blocked')
    verification.authorize(con, project, change, run, 'package_local', item['target'])
    require(item['status'] != 'cancelled', 'DELIVERY_STATE', 'Delivery was cancelled', status='blocked')
    require(one(con, 'SELECT run_id FROM steps WHERE step_id=?', (item['step_id'],))['run_id'] == run,
            'RUN_SCOPE', 'Resume the original delivery Run', status='blocked')
    original = one(con, 'SELECT * FROM code_snapshots WHERE snapshot_id=?', (item['snapshot_id'],))
    check = one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (item['revision_id'], item['readback_check_id']))
    observed = verification.current_subject(store, con, item['revision_id'], check, loads(item['environment_json']))
    require((observed['digest'], observed['environment_digest']) == (original['digest'], original['environment_digest']),
            'DELIVERY_SUBJECT_CHANGED', 'Prepared package no longer matches current product inputs', status='blocked')
    require(verification.evaluate(store, con, project, change, item['revision_id'], loads(item['environment_json']), workspace=engine.run_row(con, project, change, run)['workspace_id'])['converged'],
            'NOT_CONVERGED', 'Verification must remain applicable before delivery', status='blocked')
    raw = store.asset_bytes(con, item['bundle_asset_id'], project)
    step = engine.new_step(con, project, change, run, item['revision_id'], 'RLS', 'delivery.readback:'+item['delivery_id'])
    intent = {'kind': 'delivery.execute', 'delivery_id': item['delivery_id'], 'revision_id': item['revision_id'],
              'asset_id': item['bundle_asset_id'], 'sha256': sha(raw), 'target': item['target'],
              'environment': loads(item['environment_json']), 'step_id': step, 'readback_only': item['status'] == 'succeeded'}
    atomic_write(work/'intent.json', canonical(intent)+b'\n')
    con.execute("UPDATE deliveries SET status='unknown' WHERE delivery_id=?", (item['delivery_id'],))
    return intent


def execute(store, project, intent, work, *, write=True):
    path = destination(store, intent['target'], intent['sha256'])
    with store.read() as con:
        raw = store.asset_bytes(con, intent['asset_id'], project)
    require(sha(raw) == intent['sha256'], 'DELIVERY_INTEGRITY', 'Prepared package asset differs', status='blocked')
    if write and not intent['readback_only']:
        install_package(path, raw, intent['sha256'])
    argv = [sys.executable, '-I', '-B', str(Path(__file__).with_name('readback_worker.py')), str(path), intent['sha256']]
    return execution.run_command(argv, store.root, work, [], env=intent['environment'], timeout=60)


def install_package(path, raw, hashed):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.delivery-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # An intervening external writer cannot be overwritten by rename.
            os.link(temporary, path)
        except FileExistsError:
            require(not path.is_symlink() and path.is_file() and sha(path.read_bytes()) == hashed,
                    'DELIVERY_TARGET_CONFLICT', 'Target changed outside this delivery', status='conflict')
    finally:
        Path(temporary).unlink(missing_ok=True)


def finish(store, con, project, change, run, intent, evidence):
    item = row(con, project, change, intent['delivery_id'])
    check = one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (item['revision_id'], item['readback_check_id']))
    result = verification.record_result(store, con, project, change, run, item['revision_id'], check, intent['step_id'],
                                        item['snapshot_id'], evidence, source_kind='command')
    status = 'succeeded' if evidence['status'] == 'pass' else 'unknown' if evidence['status'] == 'unknown' else 'failed'
    con.execute('UPDATE deliveries SET status=?,readback_result_id=?,summary=? WHERE delivery_id=?',
                (status, result, 'Local package independently read back: '+evidence['status'], item['delivery_id']))
    con.execute("UPDATE steps SET status='completed',outcome=?,snapshot_id=?,finished_at=? WHERE step_id IN (?,?)",
                ('unknown' if evidence['status'] == 'blocked' else evidence['status'], item['snapshot_id'], now(), item['step_id'], intent['step_id']))
    return {'delivery_id': item['delivery_id'], 'status': status, 'outcome': evidence['status'], 'result_id': result,
            'target': item['target'], 'package_sha256': intent['sha256'], 'error_code': evidence.get('error_code')}


def close(store, con, project, change, run, p):
    item = con.execute("SELECT d.* FROM deliveries d JOIN steps s USING(step_id) WHERE d.project_id=? AND d.change_id=? AND d.revision_id=? AND s.run_id=? AND d.status='succeeded' ORDER BY d.rowid DESC LIMIT 1",
                       (project, change, p['revision_id'], run)).fetchone()
    require(item, 'DELIVERY_PENDING', 'Execute and independently read back the local delivery', status='blocked')
    check = one(con, 'SELECT * FROM checks WHERE revision_id=? AND check_id=?', (item['revision_id'], item['readback_check_id']))
    subject = verification.current_subject(store, con, item['revision_id'], check, loads(item['environment_json']))
    original = one(con, 'SELECT * FROM code_snapshots WHERE snapshot_id=?', (item['snapshot_id'],))
    require((subject['digest'], subject['environment_digest']) == (original['digest'], original['environment_digest']),
            'DELIVERY_SUBJECT_CHANGED', 'Current inputs differ from the independently verified delivered package', status='blocked')
    readback = verification.applicable(con, change, item['revision_id'], check, subject)
    require(readback and readback['result_id'] == item['readback_result_id'] and readback['status'] == 'pass',
            'DELIVERY_READBACK_EXPIRED', 'The recorded readback no longer applies; perform a new authorized readback', status='blocked')
    pending = [r[0] for r in con.execute("SELECT task_id FROM tasks WHERE revision_id=? AND target_phase='RLS'", (p['revision_id'],))
               if not verification.task_completed(con, change, p['revision_id'], r[0])]
    require(not pending, 'TASKS_PENDING', 'Complete the delivery tasks', status='blocked', details=pending)
    require(verification.evaluate(store, con, project, change, p['revision_id'], loads(item['environment_json']), workspace=engine.run_row(con, project, change, run)['workspace_id'], through_phase='RLS')['converged'],
            'NOT_CONVERGED', 'Current product evidence changed before closure', status='blocked')
    expected = one(con, 'SELECT sha256 FROM assets WHERE asset_id=?', (item['bundle_asset_id'],))[0]
    path = destination(store, item['target'], expected)
    require(path.is_file() and sha(path.read_bytes()) == expected, 'DELIVERY_READBACK_CHANGED', 'Delivered bytes changed after readback', status='blocked')
    con.execute("UPDATE changes SET state='completed' WHERE change_id=?", (change,))
    con.execute("UPDATE runs SET status='completed',lease_id=NULL,finished_at=? WHERE run_id=?", (now(), run))
    step = engine.new_step(con, project, change, run, p['revision_id'], 'RLS', 'phase.complete:RLS')
    con.execute("UPDATE steps SET status='completed',outcome='pass',finished_at=? WHERE step_id=?", (now(), step))
    return {'change_id': change, 'delivery_id': item['delivery_id'], 'status': 'completed', 'target': item['target'],
            'readback_result_id': item['readback_result_id'], 'next_actions': [{'action': 'workspace.export'}]}
