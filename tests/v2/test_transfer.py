"""Independent workspaces and logical imports through public requests."""
import json
import html
import re
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import test_execution as fixture
from test_runtime import Session
from packages.sdlc import transfer
from packages.sdlc.common import canonical, uid
from packages.sdlc.storage import Store


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.ExecutionFlowTests()
        self.fixture.setUp()
        self.root = self.fixture.root
        self.s = self.fixture.s
        self.change = self.s.bindings['change_id']
        self.rev = self.fixture.rev
        self.s.ok('run.cancel', {'reason': 'Checkpoint isolated fixture before creating independent copies'})
        self.temp = tempfile.TemporaryDirectory(prefix='sdlc-v2-transfer-')
        self.copy = Path(self.temp.name)/'copy'
        self.copy.mkdir()
        self.public = Session(self.root)

    def tearDown(self):
        self.fixture.tearDown()
        self.temp.cleanup()

    def clone(self):
        result = self.public.ok('workspace.clone', {'target': str(self.copy)})
        s = Session(self.copy)
        s.context = self.s.context
        response = s.send('run.start', {'actor_id': 'current-agent'}, change_id=self.change)
        self.assertTrue(response['ok'], response)
        s.bindings = {'change_id': self.change, 'run_id': response['run_id']}
        return s, result

    def start_original(self):
        response = self.public.send('run.start', {'actor_id': 'current-agent'}, change_id=self.change)
        self.assertTrue(response['ok'], response)
        self.s.bindings['run_id'] = response['run_id']

    def revise(self, session, title):
        session.ok('change.revise', {'phase': 'PLN', 'reason': title})
        session.submit('PLN', [{'op': 'update_task', 'id': self.fixture.task, 'title': title}])
        return session.complete('PLN')['revision_id']

    def archive(self, root, change=None):
        return Session(root).ok('workspace.export', {'change_id': change or self.change})

    def collect(self, archive):
        return self.public.ok('workspace.collect', {'path': archive['path']})

    def test_backup_clone_preserves_history_and_isolates_authorizations(self):
        copied, result = self.clone()
        source, target = Store(self.root), Store(self.copy)
        for key in ('store_id', 'workspace_id', 'instance_id'):
            self.assertNotEqual(source.config()[key], target.config()[key])
        self.assertEqual(source.config()['project_id'], target.config()['project_id'])
        self.assertFalse(result['source_authorizations_active'])
        lease = copied.ok('run.acquire')['lease_id']
        failed = copied.send('task.start', {'revision_id': self.rev, 'task_id': self.fixture.task, 'lease_id': lease})
        self.assertEqual('AUTHORIZATION_REQUIRED', failed['errors'][0]['code'])
        copied.ok('authorization.grant', {'authorizations': [{'action': 'edit_local', 'target': 'main',
                   'issued_by': 'user', 'basis_text': 'Explicit fixture permission for independent local product copy'}]})
        self.assertEqual('running', copied.ok('task.start', {'revision_id': self.rev, 'task_id': self.fixture.task, 'lease_id': lease})['status'])
        with source.read() as con:
            self.assertFalse(con.execute('SELECT 1 FROM workspaces WHERE workspace_id=?', (target.config()['workspace_id'],)).fetchone())

    def test_clone_never_overwrites_existing_store(self):
        self.clone()
        before = Store(self.copy).config()
        result = self.public.send('workspace.clone', {'target': str(self.copy)})
        self.assertEqual('CLONE_TARGET_EXISTS', result['errors'][0]['code'])
        self.assertEqual(before, Store(self.copy).config())

    def test_export_validates_selected_closure_without_unrelated_change(self):
        separate = Session(self.root)
        separate.context = self.s.context
        other = separate.new_change('private-other')
        archive = self.archive(self.root)
        raw, manifest, files, hashed = transfer.unpack(Path(archive['path']))
        rows = transfer.validate_archive(Store(self.root), manifest, files)
        self.assertEqual([self.change], [r['change_id'] for r in rows['changes']])
        self.assertNotIn(other['change_id'], files['database.json'].decode())
        self.assertIn('index.html', files)
        self.assertTrue(any(name.endswith('/request.json') for name in files))
        self.assertEqual(archive['bundle_digest'], hashed)

    def test_same_bundle_is_idempotent_and_fast_forward_preserves_other_changes(self):
        copied, _ = self.clone()
        revision = self.revise(copied, 'Copy task revision')
        other = Session(self.root)
        other.context = self.s.context
        untouched = other.new_change('untouched')
        archive = self.archive(self.copy)
        first = self.collect(archive)
        self.assertEqual(('imported', 'fast_forward'), (first['status'], first['relation']), first)
        second = self.collect(archive)
        self.assertTrue(second['idempotent'])
        self.assertEqual(first['import_id'], second['import_id'])
        with Store(self.root).read() as con:
            self.assertEqual(revision, con.execute('SELECT active_revision_id FROM changes WHERE change_id=?', (self.change,)).fetchone()[0])
            self.assertTrue(con.execute('SELECT 1 FROM revisions WHERE revision_id=?', (untouched['revision_id'],)).fetchone())
            self.assertFalse(con.execute('PRAGMA foreign_key_check').fetchall())

    def test_offline_archive_is_readable_without_original_workspace(self):
        archive = self.archive(self.root)
        portable = Path(self.temp.name)/'portable.zip'
        shutil.copyfile(archive['path'], portable)
        self.root.rename(Path(self.temp.name)/'unavailable-original')
        self.assertFalse(self.root.exists())
        _, manifest, files, hashed = transfer.unpack(portable)
        self.assertEqual(archive['bundle_digest'], hashed)
        rows = json.loads(files['database.json'])
        self.assertEqual([self.change], [r['change_id'] for r in rows['changes']])
        self.assertTrue(rows['runs'])
        self.assertTrue(any(name.endswith('/request.json') for name in files))
        links = re.findall(r'href="([^"]+)"', files['index.html'].decode())
        self.assertTrue(links)
        self.assertTrue(all(html.unescape(link) in files for link in links))

    def test_archive_budget_rejection_preserves_evidence_and_later_exports_complete_bytes(self):
        self.public.context = self.s.context
        created = self.public.new_change('archive-budget')
        self.change = created['change_id']
        evidence = self.root/'binary-evidence.bin'
        # Deterministic compressed input, representative of dependency archives.
        import random
        evidence.write_bytes(random.Random(17).randbytes(16384))
        self.public.ok('asset.add', {'path': evidence.name, 'owner_type': 'source',
                       'owner_id': created['source_id'], 'purpose': 'original dependency evidence'},
                       expected_generation=0)
        config_before = Store(self.root).config()
        with patch.object(transfer, 'MAX_ARCHIVE', 8192):
            refused = self.public.send('workspace.export', {'change_id': self.change})
        self.assertEqual('ARCHIVE_LIMIT', refused['errors'][0]['code'])
        self.assertFalse(list((self.root/'.sdlc/exports/workspace').glob('*.zip')))
        self.assertEqual(config_before, Store(self.root).config())
        archive = self.archive(self.root)
        _, _, files, _ = transfer.unpack(Path(archive['path']))
        self.assertIn(evidence.read_bytes(), files.values())

    def test_divergence_retains_both_heads_and_explicit_merge_parentage(self):
        copied, _ = self.clone()
        source_head = self.revise(copied, 'Independent source decision')
        self.start_original()
        target_head = self.revise(self.s, 'Independent target decision')
        result = self.collect(self.archive(self.copy))
        self.assertEqual(('conflict', 'diverged'), (result['status'], result['relation']), result)
        with Store(self.root).read() as con:
            self.assertEqual(target_head, con.execute('SELECT active_revision_id FROM changes WHERE change_id=?', (self.change,)).fetchone()[0])
            self.assertTrue(con.execute('SELECT 1 FROM revisions WHERE revision_id=?', (source_head,)).fetchone())
        resolved = self.s.ok('change.resolve', {'source_revision_id': source_head, 'phase': 'PLN', 'reason': 'Explicitly integrate source decision'})
        self.assertEqual((target_head, source_head), (resolved['parent_id'], resolved['merged_from_id']))
        self.s.submit('PLN', [{'op': 'update_task', 'id': self.fixture.task, 'title': 'Integrated decision'}])
        self.s.complete('PLN')

    def test_new_change_collect_preserves_target_identity(self):
        copied, _ = self.clone()
        new = Session(self.copy)
        new.context = copied.context
        change = new.new_change('new-source-change')
        result = self.collect(self.archive(self.copy, change['change_id']))
        self.assertEqual(('imported', 'new_change'), (result['status'], result['relation']), result)
        self.assertEqual(self.public.ok('workspace.inspect')['config']['root_path'], str(self.root.resolve()))
        with Store(self.root).read() as con:
            self.assertEqual(2, con.execute('SELECT count(*) FROM changes').fetchone()[0])

    def test_manual_copy_requires_rebind_and_does_not_activate_old_run(self):
        shutil.copytree(self.root/'.sdlc', self.copy/'.sdlc')
        copied = Session(self.copy)
        inspected = copied.ok('workspace.inspect')
        failed = copied.send('run.start', {'actor_id': 'current-agent'}, change_id=self.change)
        self.assertEqual('WORKSPACE_MOVED', failed['errors'][0]['code'])
        rebound = copied.ok('workspace.rebind', {'reason': 'User explicitly chose this manual copy'})
        self.assertNotEqual(inspected['config']['workspace_id'], rebound['config']['workspace_id'])
        self.assertEqual(str(self.copy.resolve()), Store(self.copy).config()['root_path'])
        old_run = self.s.bindings['run_id']
        failed = copied.send('run.resume', {'reason': 'Attempt source Run replay'}, change_id=self.change, run_id=old_run)
        self.assertEqual('RUN_SCOPE', failed['errors'][0]['code'])

    def test_tampered_manifest_is_rejected_before_target_mutation(self):
        self.clone()
        archive = self.archive(self.copy)
        path = Path(self.temp.name)/'tampered.zip'
        with zipfile.ZipFile(archive['path']) as original, zipfile.ZipFile(path, 'w') as changed:
            for name in original.namelist():
                changed.writestr(name, b'{}' if name == 'database.json' else original.read(name))
        result = self.public.send('workspace.collect', {'path': str(path)})
        self.assertEqual('ARCHIVE_INTEGRITY', result['errors'][0]['code'])
        with Store(self.root).read() as con:
            self.assertEqual(0, con.execute('SELECT count(*) FROM imports').fetchone()[0])

    def test_same_primary_key_changed_content_records_conflict_without_overwrite(self):
        copied, _ = self.clone()
        archive = self.archive(self.copy)
        _, manifest, files, _ = transfer.unpack(Path(archive['path']))
        rows = json.loads(files['database.json'])
        rows['projects'][0]['name'] = 'Different project name under same UUID'
        files['database.json'] = canonical(rows)+b'\n'
        raw, _ = transfer.pack(files, {k: v for k, v in manifest.items() if k != 'files'})
        path = Path(self.temp.name)/'conflict.zip'
        path.write_bytes(raw)
        result = self.collect({'path': str(path)})
        self.assertEqual(('conflict', 'row_conflict'), (result['status'], result['relation']))
        self.assertEqual('example', self.public.ok('workspace.inspect')['projects'][0]['name'])
        self.assertTrue(Path(result['archive']).exists())

    def test_replaying_old_binding_receipt_cannot_revert_new_binding(self):
        a, b = Path(self.temp.name)/'a', Path(self.temp.name)/'b'
        a.mkdir(); b.mkdir()
        first = {'resources': {'main': '.', 'extra': str(a)}, 'reason': 'Bind fixture A'}
        second = {'resources': {'main': '.', 'extra': str(b)}, 'reason': 'Bind fixture B'}
        original = self.public.send('workspace.bind', first, operation_id='bind-A')
        self.assertTrue(original['ok'], original)
        self.public.ok('workspace.bind', second, operation_id='bind-B')
        replay = self.public.send('workspace.bind', first, operation_id='bind-A')
        self.assertEqual(original, replay)
        self.assertEqual(str(b), Store(self.root).config()['resources']['extra'])

    def test_binding_is_blocked_by_local_execution_lease(self):
        self.start_original()
        self.s.ok('run.acquire')
        result = self.public.send('workspace.bind', {'resources': {'main': '.'}, 'reason': 'Attempt to replace active inputs'})
        self.assertEqual('WORKSPACE_BUSY', result['errors'][0]['code'])

    def test_target_draft_survives_while_source_committed_head_is_retained(self):
        copied, _ = self.clone()
        source_head = self.revise(copied, 'Source checkpoint')
        self.start_original()
        draft = self.s.ok('change.revise', {'phase': 'PLN', 'reason': 'Target draft must survive'})
        self.s.submit('PLN', [{'op': 'update_task', 'id': self.fixture.task, 'title': 'Uncommitted target work'}])
        before = self.s.ok('phase.prepare')['content']
        result = self.collect(self.archive(self.copy))
        self.assertEqual(('conflict', 'target_draft_pending'), (result['status'], result['relation']), result)
        self.assertEqual(before, self.s.ok('phase.prepare')['content'])
        with Store(self.root).read() as con:
            self.assertTrue(con.execute('SELECT 1 FROM revisions WHERE revision_id=?', (source_head,)).fetchone())
            self.assertEqual(self.rev, con.execute('SELECT active_revision_id FROM changes WHERE change_id=?', (self.change,)).fetchone()[0])
        self.s.complete('PLN')
        self.s.ok('change.resolve', {'source_revision_id': source_head, 'phase': 'PLN', 'reason': 'Resolve after preserving target draft'})

    def fork_mutable_revision(self):
        self.start_original()
        shared = self.s.ok('change.revise', {'phase': 'PLN', 'reason': 'Fork a mutable content version'})['revision_id']
        self.s.ok('run.cancel', {'reason': 'Keep shared historical Run unchanged across copies'})
        copied, _ = self.clone()
        self.start_original()
        return copied, shared

    def test_explicit_revision_preservation_recovers_original_failed_bundle_and_resolves(self):
        copied, shared = self.fork_mutable_revision()
        copied.submit('PLN', [{'op': 'update_task', 'id': self.fixture.task, 'title': 'Source frozen fork'}])
        copied.complete('PLN')
        source_head = self.revise(copied, 'Source descendant retains its original evidence')
        self.s.ok('change.revise', {'phase': 'PLN', 'reason': 'Keep independent target draft'},
                  expected_generation=self.s.ok('phase.prepare')['generation'])
        self.s.submit('PLN', [{'op': 'update_task', 'id': self.fixture.task, 'title': 'Target work'}])
        before = self.s.ok('phase.prepare')['content']
        other = Session(self.root)
        other.context = self.s.context
        other.new_change('unrelated-control')
        control = other.ok('change.get')['content']
        archive = self.archive(self.copy)
        raw, manifest, source_files, _ = transfer.unpack(Path(archive['path']))
        source_rows = json.loads(source_files['database.json'])
        request = {'path': archive['path']}
        original = self.public.send('workspace.collect', request, operation_id='default-conflict')
        self.assertEqual('row_conflict', original['data']['relation'])
        self.assertFalse(original['data']['rows_imported'])
        self.assertEqual([], original['data']['next_actions'])
        result = self.public.ok('workspace.collect', {**request, 'conflict_policy': 'preserve_revision_versions'},
                                operation_id='preserve-frozen-versions')
        self.assertTrue(result['rows_imported'], result)
        self.assertEqual('target_draft_pending', result['relation'])
        aliases = result['revision_id_aliases']
        self.assertEqual({shared, source_head}, set(aliases))
        self.assertEqual(source_head, result['source_head'])
        self.assertEqual(aliases[source_head], result['imported_source_head'])
        self.assertEqual(original['data']['error'], result['prior_conflict']['error'])
        self.assertEqual(raw, Path(result['archive']).read_bytes())
        self.assertEqual(before, self.s.ok('phase.prepare')['content'])
        self.assertEqual(control, other.ok('change.get')['content'])
        with Store(self.root).read() as con:
            for key, version in result['revision_versions'].items():
                self.assertEqual(version['imported_digest'], Store(self.root).content_digest(con, aliases[key]))
            root_version = result['revision_versions'][shared]
            self.assertEqual(root_version['source_digest'], root_version['imported_digest'])
            child_version = result['revision_versions'][source_head]
            self.assertNotEqual(child_version['source_digest'], child_version['imported_digest'])
            self.assertEqual(aliases[shared], con.execute('SELECT parent_id FROM revisions WHERE revision_id=?', (aliases[source_head],)).fetchone()[0])
            for row in source_rows['operations']:
                imported = con.execute('SELECT response_json,request_digest FROM operations WHERE operation_id=?', (row['operation_id'],)).fetchone()
                self.assertEqual((row['response_json'], row['request_digest']), tuple(imported))
            self.assertEqual('imported', con.execute('SELECT origin_kind FROM runs WHERE run_id=?', (copied.bindings['run_id'],)).fetchone()[0])
            count = con.execute('SELECT count(*) FROM revisions').fetchone()[0]
            self.assertFalse(con.execute('PRAGMA foreign_key_check').fetchall())
        repeat = self.public.ok('workspace.collect', {**request, 'conflict_policy': 'preserve_revision_versions'})
        self.assertTrue(repeat['idempotent'])
        self.assertEqual(aliases, repeat['revision_id_aliases'])
        self.assertEqual(original, self.public.send('workspace.collect', request, operation_id='default-conflict'))
        with Store(self.root).read() as con:
            self.assertEqual(count, con.execute('SELECT count(*) FROM revisions').fetchone()[0])
        target_head = self.s.complete('PLN')['revision_id']
        resolved = self.s.ok('change.resolve', {'source_revision_id': aliases[source_head], 'phase': 'PLN', 'reason': 'Explicitly integrate preserved source fork'})
        self.assertEqual((target_head, aliases[source_head]), (resolved['parent_id'], resolved['merged_from_id']))
        self.s.complete('PLN')
        exported = self.archive(self.root)
        _, exported_manifest, exported_files, _ = transfer.unpack(Path(exported['path']))
        transfer.validate_archive(Store(self.root), exported_manifest, exported_files)
        base = 'imports/'+archive['bundle_digest']
        self.assertEqual(raw, exported_files[base+'.zip'])
        self.assertEqual(aliases, json.loads(exported_files[base+'.json'])['summary']['revision_id_aliases'])
        for name, data in source_files.items():
            if name.startswith('runs/') and name in exported_files:
                self.assertEqual(data, exported_files[name])

    def test_revision_policy_preserves_both_committed_heads_without_overwrite(self):
        copied, shared = self.fork_mutable_revision()
        for session, title in ((copied, 'Source choice'), (self.s, 'Target choice')):
            session.submit('PLN', [{'op': 'update_task', 'id': self.fixture.task, 'title': title}])
            session.complete('PLN')
        before = self.s.ok('phase.prepare')['content']
        result = self.public.ok('workspace.collect', {'path': self.archive(self.copy)['path'], 'conflict_policy': 'preserve_revision_versions'})
        self.assertTrue(result['rows_imported'], result)
        self.assertEqual(('conflict', 'diverged'), (result['status'], result['relation']))
        self.assertEqual(before, self.s.ok('phase.prepare')['content'])
        self.assertNotEqual(shared, result['imported_source_head'])

    def test_revision_policy_cannot_rename_conflicting_project_or_execution_rows(self):
        copied, shared = self.fork_mutable_revision()
        copied.complete('PLN')
        self.s.ok('change.revise', {'phase': 'PLN', 'reason': 'Abandon target variant'},
                  expected_generation=self.s.ok('phase.prepare')['generation'])
        archive = self.archive(self.copy)
        _, manifest, original_files, _ = transfer.unpack(Path(archive['path']))
        before = self.s.ok('phase.prepare')['content']
        for table, column in [('projects', 'name'), ('runs', 'error_message')]:
            with self.subTest(table=table):
                files = dict(original_files)
                rows = json.loads(files['database.json'])
                with Store(self.root).read() as con:
                    keys = {r[0] for r in con.execute('SELECT '+('project_id' if table == 'projects' else 'run_id')+' FROM '+table)}
                key = 'project_id' if table == 'projects' else 'run_id'
                row = next(r for r in rows[table] if r[key] in keys)
                row[column] = 'Unrelated identity conflict must not be renamed'
                files['database.json'] = canonical(rows)+b'\n'
                raw, _ = transfer.pack(files, {k: v for k, v in manifest.items() if k != 'files'})
                path = Path(self.temp.name)/(table+'-conflict.zip')
                path.write_bytes(raw)
                result = self.public.ok('workspace.collect', {'path': str(path), 'conflict_policy': 'preserve_revision_versions'})
                self.assertEqual('row_conflict', result['relation'], result)
                self.assertFalse(result['rows_imported'])
                self.assertIsNone(result['imported_source_head'])
                self.assertEqual(before, self.s.ok('phase.prepare')['content'])
                with Store(self.root).read() as con:
                    for alias in result.get('revision_id_aliases', {}).values():
                        self.assertIsNone(con.execute('SELECT 1 FROM revisions WHERE revision_id=?', (alias,)).fetchone())

    def test_revision_policy_rejects_mutable_source_and_unknown_policy(self):
        copied, shared = self.fork_mutable_revision()
        copied.submit('PLN', [{'op': 'update_task', 'id': self.fixture.task, 'title': 'Unfinished source'}])
        path = self.archive(self.copy)['path']
        invalid = self.public.send('workspace.collect', {'path': path, 'conflict_policy': 'overwrite'})
        self.assertEqual(('INVALID_ENUM', '/payload/conflict_policy'), (invalid['errors'][0]['code'], invalid['errors'][0]['path']))
        result = self.public.ok('workspace.collect', {'path': path, 'conflict_policy': 'preserve_revision_versions'})
        self.assertEqual('IMPORT_DRAFT_CONFLICT', result['error']['code'])
        self.assertFalse(result['rows_imported'])

    def test_older_source_only_adds_history(self):
        self.clone()
        archive = self.archive(self.copy)
        self.start_original()
        target = self.revise(self.s, 'Target has moved forward')
        result = self.collect(archive)
        self.assertEqual(('imported', 'history_only'), (result['status'], result['relation']), result)
        with Store(self.root).read() as con:
            self.assertEqual(target, con.execute('SELECT active_revision_id FROM changes WHERE change_id=?', (self.change,)).fetchone()[0])

    def test_configuration_write_interruption_recovers_committed_transition(self):
        from packages.sdlc import runtime
        request = {'resources': {'main': '.'}, 'reason': 'Explicit bind recovery fixture'}
        original = transfer.apply_config
        with patch.object(transfer, 'apply_config', side_effect=OSError('Synthetic interruption before config update')):
            failed = self.public.send('workspace.bind', request, operation_id='binding-interrupted')
        self.assertFalse(failed['ok'])
        blocked = self.public.send('context.commit', {'summary': 'Must wait', 'entries': []})
        self.assertEqual('CONFIG_TRANSITION_PENDING', blocked['errors'][0]['code'])
        recovered = self.public.send('workspace.bind', request, operation_id='binding-interrupted')
        self.assertTrue(recovered['ok'], recovered)
        with Store(self.root).read() as con:
            self.assertIsNotNone(con.execute('SELECT config_applied_at FROM operations WHERE operation_id=?', ('binding-interrupted',)).fetchone()[0])

    def test_missing_manifest_field_and_malformed_rows_are_structured_errors(self):
        self.clone()
        archive = self.archive(self.copy)
        _, manifest, files, _ = transfer.unpack(Path(archive['path']))
        for label, data in [('missing-project', {}), ('malformed-rows', {'revisions': [1]})]:
            if label == 'missing-project':
                changed = {k: v for k, v in manifest.items() if k not in {'files', 'project_id'}}
            else:
                changed = {k: v for k, v in manifest.items() if k != 'files'}
                rows = json.loads(files['database.json'])
                rows.update(data)
                files['database.json'] = canonical(rows)+b'\n'
            raw, _ = transfer.pack(files, changed)
            path = Path(self.temp.name)/(label+'.zip')
            path.write_bytes(raw)
            result = self.public.send('workspace.collect', {'path': str(path)})
            self.assertEqual('ARCHIVE_SCHEMA', result['errors'][0]['code'], result)

    def repack(self, archive, transform, name='changed'):
        _, manifest, files, _ = transfer.unpack(Path(archive['path']))
        rows = json.loads(files['database.json'])
        transform(rows, files)
        rows = {table: sorted(values, key=canonical) for table, values in rows.items()}
        files['database.json'] = canonical(rows)+b'\n'
        raw, _ = transfer.pack(files, {k: v for k, v in manifest.items() if k != 'files'})
        path = Path(self.temp.name)/(name+'.zip')
        path.write_bytes(raw)
        return {'path': str(path)}

    def test_imported_authorization_and_run_never_become_local_capabilities(self):
        self.clone()
        archive = self.archive(self.copy)
        fake_actor, fake_run = 'imported-untrusted-actor', uid()
        workspace = Store(self.root).config()['workspace_id']
        def forge(rows, files):
            auth = dict(rows['authorizations'][0])
            auth.update(authorization_id=uid(), workspace_id=workspace, actor_id=fake_actor,
                        action='edit_local', target='main', origin_kind='local')
            rows['authorizations'].append(auth)
            run = dict(next(r for r in rows['runs'] if r['change_id'] == self.change))
            run.update(run_id=fake_run, workspace_id=workspace, origin_kind='local', actor_id=fake_actor,
                       status='running', current_phase='RLS', lease_id=uid(), started_at='2999-01-01T00:00:00Z',
                       max_repair_rounds=99)
            rows['runs'].append(run)
        result = self.collect(self.repack(archive, forge, 'forged-capabilities'))
        self.assertEqual('imported', result['status'], result)
        imported = self.public.send('run.resume', {'reason': 'Attempt imported executor'}, change_id=self.change, run_id=fake_run)
        self.assertEqual('RUN_IMPORTED', imported['errors'][0]['code'])
        response = self.public.send('run.start', {'actor_id': fake_actor}, change_id=self.change)
        self.assertTrue(response['ok'], response)
        local = Session(self.root)
        local.bindings = {'change_id': self.change, 'run_id': response['run_id']}
        lease = local.ok('run.acquire')['lease_id']
        failed = local.send('task.start', {'revision_id': self.rev, 'task_id': self.fixture.task, 'lease_id': lease})
        self.assertEqual('AUTHORIZATION_REQUIRED', failed['errors'][0]['code'])
        state = local.ok('run.get')['run']
        self.assertNotEqual('RLS', state['current_phase'])
        self.assertEqual(5, state['max_repair_rounds'])

    def test_malformed_snapshot_json_is_a_structured_rejection(self):
        self.start_original()
        self.fixture.lease = self.s.ok('run.acquire')['lease_id']
        step = self.fixture.start()
        self.fixture.write(step, True)
        self.fixture.finish(step)
        self.s.ok('run.cancel', {'reason': 'Checkpoint actual file write evidence'})
        self.clone()
        archive = self.archive(self.copy)
        def corrupt(rows, files):
            rows['code_snapshots'][0]['untracked_json'] = '"bad"'
        result = self.public.send('workspace.collect', {'path': self.repack(archive, corrupt)['path']})
        self.assertEqual('ARCHIVE_SCHEMA', result['errors'][0]['code'])

    def test_corrupted_deflate_stream_is_a_structured_rejection(self):
        import struct
        self.clone()
        path = Path(self.archive(self.copy)['path'])
        raw = bytearray(path.read_bytes())
        name_length, extra_length = struct.unpack_from('<HH', raw, 26)
        raw[30+name_length+extra_length] = 255
        damaged = Path(self.temp.name)/'bad-deflate.zip'
        damaged.write_bytes(raw)
        result = self.public.send('workspace.collect', {'path': str(damaged)})
        self.assertEqual('ARCHIVE_CORRUPT', result['errors'][0]['code'])

    def test_unknown_effect_blocks_binding_before_it_can_redirect_recovery(self):
        from packages.sdlc import engine
        self.start_original()
        self.fixture.lease = self.s.ok('run.acquire')['lease_id']
        step = self.fixture.start()
        with patch.object(engine, 'apply_write', side_effect=OSError('Synthetic interruption after durable intent')):
            result = self.s.send('task.write', {'revision_id': self.rev, 'task_id': self.fixture.task,
                'step_id': step, 'lease_id': self.fixture.lease, 'files': [{'path': 'original.txt', 'content': 'saved intent'}]},
                operation_id='unknown-write')
        self.assertEqual('unknown', result['status'])
        blocked = self.public.send('workspace.bind', {'resources': {'main': '.'}, 'reason': 'Binding change while effect is unknown'})
        self.assertEqual('UNRESOLVED_EFFECT', blocked['errors'][0]['code'])
        recovered = self.s.ok('operation.reconcile', {'operation_id': 'unknown-write'})
        self.assertEqual('saved intent', (self.root/'original.txt').read_text())

    def test_source_assets_and_raw_execution_logs_survive_collection(self):
        copied, _ = self.clone()
        copied.ok('authorization.grant', {'authorizations': [{'action': 'edit_local', 'target': 'main',
                   'issued_by': 'user', 'basis_text': 'Explicit independent fixture code operation'}]})
        lease = copied.ok('run.acquire')['lease_id']
        step = copied.ok('task.start', {'revision_id': self.rev, 'task_id': self.fixture.task, 'lease_id': lease})['step_id']
        copied.ok('task.write', {'revision_id': self.rev, 'task_id': self.fixture.task, 'step_id': step, 'lease_id': lease,
                  'files': [{'path': 'product.py', 'content': 'print("actual archived product")'}]})
        copied.ok('task.finish', {'revision_id': self.rev, 'task_id': self.fixture.task, 'step_id': step, 'lease_id': lease, 'summary': 'Actual file produced'})
        copied.ok('run.cancel', {'reason': 'Freeze source execution evidence'})
        result = self.collect(self.archive(self.copy))
        self.assertEqual('imported', result['status'], result)
        self.assertFalse((self.root/'product.py').exists())
        source_run = copied.bindings['run_id']
        self.assertTrue((self.root/'.sdlc/runs'/source_run/'index.html').is_file())
        with Store(self.root).read() as con:
            asset_rows = con.execute('SELECT * FROM assets').fetchall()
            self.assertTrue(asset_rows)
            for row in asset_rows:
                self.assertTrue(Store(self.root).asset_bytes(con, row['asset_id'], row['project_id']) is not None)
            self.assertEqual('imported', con.execute('SELECT origin_kind FROM runs WHERE run_id=?', (source_run,)).fetchone()[0])

    def test_unknown_write_archive_contains_bytes_not_yet_written_to_product(self):
        from packages.sdlc import engine
        self.start_original()
        self.fixture.lease = self.s.ok('run.acquire')['lease_id']
        step = self.fixture.start()
        with patch.object(engine, 'apply_write', side_effect=OSError('Stop before writing archived bytes')):
            result = self.s.send('task.write', {'revision_id': self.rev, 'task_id': self.fixture.task,
                'step_id': step, 'lease_id': self.fixture.lease, 'files': [{'path': 'pending.py', 'content': 'retained pending bytes'}]},
                operation_id='pending-file-archive')
        self.assertEqual('unknown', result['status'])
        self.assertFalse((self.root/'pending.py').exists())
        archive = self.archive(self.root)
        _, manifest, files, _ = transfer.unpack(Path(archive['path']))
        rows = transfer.validate_archive(Store(self.root), manifest, files)
        self.assertTrue(rows['assets'])
        self.assertIn(b'retained pending bytes', files.values())
        context_runs = [r for r in rows['runs'] if r['change_id'] is None]
        self.assertTrue(context_runs)

    def test_shared_asset_bytes_are_deduplicated_with_explicit_aliases(self):
        copied, _ = self.clone()
        # Separate changes may independently attach identical bytes under distinct IDs.
        created = []
        for root, label in ((self.root, 'target-asset'), (self.copy, 'source-asset')):
            session = Session(root)
            session.context = self.s.context
            change = session.new_change(label)
            attachment = root/'attachment.txt'
            attachment.write_text('identical independent attachment')
            asset = session.ok('asset.add', {'path': 'attachment.txt', 'owner_type': 'source',
                'owner_id': change['source_id'], 'purpose': 'Original fixture attachment'}, expected_generation=0)
            created.append((change, asset))
        archive = self.archive(self.copy, created[1][0]['change_id'])
        result = self.collect(archive)
        self.assertEqual('imported', result['status'], result)
        self.assertEqual(1, len(result['asset_id_aliases']))
        with Store(self.root).read() as con:
            self.assertEqual(1, con.execute('SELECT count(*) FROM assets').fetchone()[0])
            self.assertFalse(con.execute('PRAGMA foreign_key_check').fetchall())

    def test_archive_cannot_expand_to_another_project_through_json_asset_reference(self):
        self.start_original()
        self.fixture.lease = self.s.ok('run.acquire')['lease_id']
        step = self.fixture.start()
        self.fixture.write(step, True)
        self.fixture.finish(step)
        self.s.ok('run.cancel', {'reason': 'Freeze actual snapshot'})
        archive = self.archive(self.root)
        def forge(rows, files):
            project = {**rows['projects'][0], 'project_id': uid(), 'name': 'Unrelated project'}
            rows['projects'].append(project)
            asset = {**rows['assets'][0], 'asset_id': uid(), 'project_id': project['project_id']}
            rows['assets'].append(asset)
            snapshot = next(r for r in rows['code_snapshots'] if json.loads(r['untracked_json']))
            manifest = json.loads(snapshot['untracked_json'])
            manifest[0]['asset_id'] = asset['asset_id']
            snapshot['untracked_json'] = canonical(manifest).decode()
        result = self.public.send('workspace.collect', {'path': self.repack(archive, forge, 'cross-project')['path']})
        self.assertEqual('ARCHIVE_SCOPE', result['errors'][0]['code'])


if __name__ == '__main__':
    unittest.main()
