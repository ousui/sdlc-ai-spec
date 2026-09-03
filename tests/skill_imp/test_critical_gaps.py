from copy import deepcopy
from dataclasses import replace
import json
from unittest.mock import patch

from tests.skill_imp.support import ImpFixture, tree_bytes
from packages.sdlc_artifact_store import ArtifactStore, compute_sha256
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_claim_provider import ClaimProvider
from packages.sdlc_phasekit import CheckOutcome, PhaseInputs, manifest, render_phase_artifact, table
from packages.sdlc_runtime.control_inputs import RLS_ITEM_HEADERS
from imp_common import ImpError
from imp_executor import PROJECT_CHECK_CONTRACT
from imp_readiness import current_result
from imp_result import read_state, snapshot_from_member, snapshot_reference
from imp_verifier import ImpVerifier


class CriticalGapTests(ImpFixture):
    def test_clean_git_baseline_is_a_complete_immutable_snapshot(self):
        original = (self.root / 'integration/app.txt').read_bytes()
        opened = self.create_open()
        stored = self.stored(opened)
        row = read_state(stored)['resources'][0]
        baseline = snapshot_reference(ArtifactStore.open_read_only(self.root), row['baseline_reference'], 'repo', local=stored)
        self.assertEqual({item['path'] for item in baseline['entries']}, {'integration/app.txt', 'user-note.txt'})
        self.assertEqual(bytes.fromhex(baseline['entries'][0]['content_hex']), original)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.original_head)

    def test_new_resource_retains_absence_evidence_and_complete_result(self):
        candidate = self.plan()
        candidate['work_items'][0]['execution_scope'] = ['resource:repo', 'resource:new']
        candidate['delivery_scope'].append({'scope_token': 'resource:new',
            'source_references': [self.dsn_reference + '#CHG-001'], 'outcome': 'Create the declared companion resource'})
        upstream = self.execute_pln(plan=candidate)
        self.assertTrue(upstream['ok'], upstream)
        method = self.implementation()
        method['resources'] = [{'id': 'repo', 'root': 'integration'}, {'id': 'new', 'root': 'generated'}]
        method['steps'][0]['target'] = ['resource:repo', 'resource:new']
        method['operations'][0]['path'] = method['checks'][0]['path'] = 'app.txt'
        method['operations'].append({'resource': 'new', 'path': 'product.txt', 'step': 'STEP-001',
                                     'op': 'write_text', 'content': 'new product', 'expected_sha256': 'absent'})
        self.assertFalse((self.root / 'generated').exists())
        opened = self.create_open(binding=upstream['artifact']['reference'] + '#WI-001', implementation=method)
        stored = self.stored(opened)
        row = next(item for item in read_state(stored)['resources'] if item['resource'] == 'new')
        self.assertEqual(row['baseline_reference'], 'N/A')
        baseline = snapshot_from_member(stored, row['baseline_member'], 'new')
        self.assertFalse(baseline['existed'])
        self.assertEqual(baseline['entries'], [])
        self.assertEqual((self.root / 'generated/product.txt').read_text(), 'new product')
        self.assertTrue(self.finish(opened)['ok'])

    def test_mutable_and_path_only_result_references_are_rejected(self):
        opened = self.create_open()
        stored = self.stored(opened)
        store = ArtifactStore.open_read_only(self.root)
        before = tree_bytes(self.root)
        for reference in ('vcs:repo@main', 'vcs:repo@v1', 'snapshot:repo@latest', 'current',
                          'integration/app.txt', opened['artifact']['id'] + '@latest/RESULT-RES-001'):
            with self.subTest(reference=reference), self.assertRaises(ImpError):
                snapshot_reference(store, reference, 'repo', local=stored)
        self.assertEqual(tree_bytes(self.root), before)

    def test_required_or_pending_pln_cannot_use_direct_binding(self):
        for disposition in ('required', 'pending'):
            direct = self.create_requirement(self.context_reference, dsn_disposition='n/a', pln_disposition=disposition)
            before = tree_bytes(self.root)
            result = self.invoke(binding=direct, implementation=self.implementation(binding=direct))
            self.assertEqual(result['next_action']['code'], 'RETURN_TO_PLAN', result)
            self.assertEqual(tree_bytes(self.root), before)

    def test_missing_business_design_and_plan_decisions_return_to_the_owner(self):
        for missing, expected in (('requirement', 'RETURN_TO_REQUIREMENT'),
                                  ('design', 'RETURN_TO_DESIGN'), ('plan', 'RETURN_TO_PLAN')):
            method = self.implementation()
            method['missing_decision'] = missing
            before = tree_bytes(self.root)
            result = self.invoke(implementation=method)
            self.assertEqual(result['next_action']['code'], expected, result)
            self.assertEqual(tree_bytes(self.root), before)

    def test_missing_design_decision_returns_to_design(self):
        method = self.implementation()
        method['missing_decision'] = 'design'
        before = tree_bytes(self.root)
        result = self.invoke(implementation=method)
        self.assertEqual(result['next_action']['code'], 'RETURN_TO_DESIGN', result)
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_successor_inputs_must_include_the_current_predecessor_result(self):
        upstream = self.execute_pln(plan=self.plan(second_imp=True))
        self.assertTrue(upstream['ok'], upstream)
        plan = upstream['artifact']['reference']
        first = self.finish(self.create_open(binding=plan + '#WI-001'))
        second = self.finish(self.create_open(binding=plan + '#WI-002',
            implementation=self.implementation(before='after', after='second')))
        stored = self.stored(second)
        raw = stored.payload.primary_blob.replace(('  - ' + first['artifact']['reference'] + '\n').encode(), b'', 1)
        self.assertNotEqual(raw, stored.payload.primary_blob)
        broken = replace(stored, payload=replace(stored.payload, primary_blob=raw, primary_sha256=compute_sha256(raw)))
        store = ArtifactStore.open_read_only(self.root)
        original_read, original_verify = store.read_revision, ImpVerifier.verify_payload
        state = read_state(stored)

        def read(artifact, revision):
            return broken if artifact == stored.control.artifact_id else original_read(artifact, revision)

        def verify(verifier, candidate):
            # Isolate the mandatory dependency-input gate from the independent
            # canonical-tamper gate. Claim/Store/dependency resolution stay real.
            return state if candidate is broken else original_verify(verifier, candidate)

        before = tree_bytes(self.root)
        with patch.object(store, 'read_revision', side_effect=read), patch.object(ImpVerifier, 'verify_payload', verify):
            with self.assertRaisesRegex(ImpError, 'Successor inputs do not include') as caught:
                current_result(store, ClaimProvider.open_read_only(self.root), second['artifact']['reference'])
        self.assertEqual(caught.exception.code, 'IMP_DEPENDENCY_INCOMPLETE')
        self.assertEqual(tree_bytes(self.root), before)

    def test_return_imp_issue_without_unique_imp_lineage_returns_to_plan(self):
        completed = self.finish(self.create_open())
        source = completed['artifact']['reference']
        authority = self._authority('issue-input')

        def produce(identity, revision):
            # A frozen control-input fixture, not a Release runtime or execution.
            return render_phase_artifact(
                artifact_id=identity, phase='RLS', revision=revision, status='ready', profile='full',
                phase_inputs=PhaseInputs(self.context_reference, (source,)), title='Unroutable Issue fixture',
                sections=(('## Release Items', table(RLS_ITEM_HEADERS, [
                    ('RLI-001', 'Recorded failed action', self.pln_reference, 'Declared scope', 'fixture-owner',
                     'fail', 'return_imp', source + '/EVD-PRE')
                ])), ('## Conclusion', table(('Release Conclusion',), [('failed',)]))),
                checks={f'CORE-G-{index:03d}': CheckOutcome('pass', 'Fixture authority') for index in range(1, 10)},
                open_items=(), evidence=(), exceptions=(), lifecycle_applicability=(),
                final_confirmation={'mode': 'human', 'confirmer': 'fixture-owner', 'role': 'Input Authority',
                                    'authority_reference': authority, 'confirmed_at': '2026-09-03T10:00:00Z'},
                gate_result='pass', evaluation_contract_set='fixture-issue@sha256:' + 'a' * 64,
                evaluator='Fixture producer')

        issue = self._source('RLS', produce) + '#RLI-001'
        before = tree_bytes(self.root)
        result = self.invoke('revise', binding=False, reference=source, inputs={'input_references': [issue]})
        self.assertEqual(result['next_action']['code'], 'RETURN_TO_PLAN', result)
        self.assertEqual(tree_bytes(self.root), before)

    def test_resource_mapping_and_method_scope_expansion_fail_before_claim(self):
        cases = []
        duplicate = self.implementation()
        duplicate['resources'].append(dict(duplicate['resources'][0]))
        cases.append((duplicate, 'RETURN_TO_PLAN'))
        expanded = self.implementation()
        expanded['steps'][0]['target'].append('path:repo/unplanned')
        cases.append((expanded, 'IMP_SCOPE_VIOLATION'))
        before = tree_bytes(self.root)
        for method, expected in cases:
            result = self.invoke(implementation=method)
            self.assertEqual(result['next_action']['code'], expected, result)
            self.assertEqual(tree_bytes(self.root), before)

    def test_method_block_identity_survives_active_revision_and_rework(self):
        opened = self.create_open()
        same = self.invoke('revise', binding=False, reference=opened['artifact']['reference'])
        self.assertEqual(same['artifact']['reference'], opened['artifact']['reference'])
        first = self.finish(same)
        binding = self.revise_plan() + '#WI-001'
        second = self.create_open(command='revise', reference=first['artifact']['reference'], binding=binding,
                                  implementation=self.implementation(binding=binding, before='after', after='reworked'),
                                  inputs={'input_references': [binding]})
        old_method = read_state(self.stored(first))['method']
        new_method = read_state(self.stored(second))['method']
        self.assertEqual(new_method['steps'][0]['blocks'][0]['id'], old_method['steps'][0]['blocks'][0]['id'])
        self.assertEqual(second['artifact']['revision'], first['artifact']['revision'] + 1)

    def test_step_block_and_check_ids_cannot_be_renamed_during_rework(self):
        first = self.finish(self.create_open())
        binding = self.revise_plan() + '#WI-001'
        method = self.implementation(binding=binding, before='after', after='reworked')
        method['steps'][0]['id'] = 'STEP-999'
        method['steps'][0]['blocks'][0]['id'] = 'EFF-999'
        method['considerations'][-1]['steps'] = ['STEP-999']
        method['operations'][0]['step'] = 'STEP-999'
        method['checks'][0]['id'] = 'CHK-999'
        before = tree_bytes(self.root)
        result = self.invoke(
            'revise', reference=first['artifact']['reference'], binding=binding,
            implementation=method, inputs={'input_references': [binding]},
        )
        self.assertEqual(result['errors'][0]['code'], 'IMP_BINDING_MISMATCH', result)
        self.assertEqual(ClaimProvider.open_read_only(self.root).resolve(binding).attempt, 1)
        self.assertEqual(tree_bytes(self.root), before)

    def test_absent_unmodified_claim_resource_fails_before_any_product_write(self):
        plan = self.plan()
        plan['work_items'][0]['execution_scope'] = ['resource:repo', 'resource:missing']
        plan['delivery_scope'].append({
            'scope_token': 'resource:missing',
            'source_references': [self.dsn_reference + '#CHG-001'],
            'outcome': 'Create the declared companion resource',
        })
        upstream = self.execute_pln(plan=plan)
        self.assertTrue(upstream['ok'], upstream)
        binding = upstream['artifact']['reference'] + '#WI-001'
        method = self.implementation(binding=binding)
        method['resources'] = [
            {'id': 'repo', 'root': 'integration'},
            {'id': 'missing', 'root': 'missing'},
        ]
        method['steps'][0]['target'] = ['resource:repo']
        method['operations'][0]['path'] = method['checks'][0]['path'] = 'app.txt'
        before = tree_bytes(self.root)
        result = self.invoke(binding=binding, implementation=method)
        self.assertEqual(result['errors'][0]['code'], 'IMP_RESULT_INCOMPLETE', result)
        self.assertFalse((self.root / 'missing').exists())
        self.assertEqual(self.claim_count(), 0)
        self.assertEqual(tree_bytes(self.root), before)

    def test_patch_without_full_result_and_tampered_result_content_fail_check(self):
        opened = self.create_open()
        original = self.stored(opened)
        state = read_state(original)
        row = state['resources'][0]
        result_member = next(item for item in original.payload.members if item.member_id == row['result_member'])
        self.assertTrue(any(item.member_id == row['change_member'] for item in original.payload.members))
        for kind in ('missing', 'content'):
            members = [item for item in original.payload.members if item.member_id != result_member.member_id]
            if kind == 'content':
                snapshot = json.loads(result_member.raw_bytes)
                snapshot['entries'][0]['content_hex'] = b'tampered'.hex()
                raw = json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()
                members.append(replace(result_member, raw_bytes=raw, sha256=compute_sha256(raw)))
            writer = ArtifactStore.open_read_write(self.root)
            current = self.stored(opened)
            payload = replace(original.payload, members=tuple(members), manifest=manifest(members))
            writer.write_open_revision(payload, expected_generation=current.control.generation)
            before = tree_bytes(self.root)
            checked = self.invoke('check', binding=False, reference=opened['artifact']['reference'])
            self.assertFalse(checked['ok'], checked)
            self.assertEqual(tree_bytes(self.root), before)

    def test_candidate_patch_without_execution_cannot_be_claimed_as_result(self):
        method = self.implementation()
        method['operations'] = []
        method['checks'][0]['expected'] = 'version=before\n'
        before = tree_bytes(self.root)
        result = self.invoke(implementation=method)
        self.assertEqual(result['errors'][0]['code'], 'IMP_READINESS_FAILED', result)
        self.assertEqual(tree_bytes(self.root), before)

    def test_secret_in_method_or_baseline_never_enters_artifact_or_evidence(self):
        synthetic = 'token=synthetic_fixture_value'
        for location in ('method', 'baseline'):
            method = self.implementation()
            if location == 'method':
                method['summary'] = synthetic
            else:
                (self.root / 'sensitive.txt').write_text(synthetic)
            before = tree_bytes(self.root)
            result = self.invoke(implementation=method)
            self.assertFalse(result['ok'], result)
            self.assertNotIn(synthetic, json.dumps(result))
            self.assertEqual(tree_bytes(self.root), before)

    def test_applicable_local_checks_save_real_execution_evidence(self):
        plan = self.plan()
        plan['work_items'][0]['execution_scope'] = ['resource:repo']
        upstream = self.execute_pln(plan=plan)
        self.assertTrue(upstream['ok'], upstream)
        binding = upstream['artifact']['reference'] + '#WI-001'
        (self.root / 'integration/test_marker.py').write_text(
            'from pathlib import Path\n'
            'import unittest\n\n'
            'class MarkerTest(unittest.TestCase):\n'
            '    def test_result(self):\n'
            '        self.assertEqual(Path("integration/app.txt").read_text(), '
            '"{\\\"result\\\":\\\"ready\\\"}\\n")\n'
        )
        method = self.implementation()
        method['steps'][0]['target'] = ['resource:repo']
        target = '{"result":"ready"}\n'
        method['operations'][0].update(op='write_text', content=target)
        method['checks'] = [
            dict(id=f'CHK-{index:03d}', name=kind, kind=kind, resource='repo',
                 path='integration/app.txt', expected=target if kind == 'equals' else 'ready')
            for index, kind in enumerate(('equals', 'contains', 'python_syntax', 'json'), 1)
        ]
        method['checks'].append({
            'id': 'CHK-005', 'name': 'Existing unit test', 'kind': 'project_command',
            'resource': 'repo', 'cwd': '.',
            'command': ['python', '-m', 'unittest', 'discover', '-s', 'integration',
                        '-p', 'test_marker.py'],
            'timeout_seconds': 30,
        })
        completed = self.finish(self.create_open(binding=binding, implementation=method))
        stored = self.stored(completed)
        checks = read_state(stored)['checks']
        self.assertEqual(len(checks), 5)
        for check in checks:
            evidence = json.loads(next(item.raw_bytes for item in stored.payload.members
                                       if item.member_id == check['evidence_member']))
            self.assertEqual((check['result'], evidence['result'], evidence['exit_code']), ('pass', 'pass', 0))
        project = json.loads(next(
            item.raw_bytes for item in stored.payload.members
            if item.member_id == 'EVD-CHK-005'
        ))
        self.assertEqual(project['contract'], PROJECT_CHECK_CONTRACT)
        self.assertEqual(project['isolation'], 'complete-resource-snapshot')
        self.assertEqual(project['sandbox'], 'python-audit-hook')
        self.assertEqual(project['network'], 'denied-offline-no-credentials')
        self.assertTrue(project['subject_sha256'].startswith('sha256:'))
        self.assertEqual(completed['next_action']['code'], 'VFY_READY')

    def test_project_check_rejects_shell_install_and_wrapper_commands(self):
        plan = self.plan()
        plan['work_items'][0]['execution_scope'] = ['resource:repo']
        upstream = self.execute_pln(plan=plan)
        binding = upstream['artifact']['reference'] + '#WI-001'
        for command in (
            ['git', 'push'],
            ['npm', 'install'],
            ['go', 'build', '-toolexec=./arbitrary-wrapper', './...'],
            ['go', 'test', '-exec=/bin/sh', './...'],
            ['cargo', 'test', '--config',
             'build.rustc-wrapper=./arbitrary-wrapper'],
            ['cargo', 'test', '--', '--arbitrary-forwarded-argument'],
        ):
            method = self.implementation(binding=binding)
            method['steps'][0]['target'] = ['resource:repo']
            method['checks'] = [{
                'id': 'CHK-001', 'name': 'Unsafe command', 'kind': 'project_command',
                'resource': 'repo', 'cwd': '.', 'command': command,
            }]
            before = tree_bytes(self.root)
            with self.subTest(command=command):
                result = self.invoke(binding=binding, implementation=method)
                self.assertEqual(result['errors'][0]['code'], 'IMP_READINESS_FAILED', result)
                self.assertEqual(tree_bytes(self.root), before)

    def test_python_project_check_denies_network_processes_and_snapshot_external_writes(self):
        plan = self.plan()
        plan['work_items'][0]['execution_scope'] = ['resource:repo']
        upstream = self.execute_pln(plan=plan)
        binding = upstream['artifact']['reference'] + '#WI-001'
        escaped = self.root / 'escaped-by-check.txt'
        (self.root / 'integration/test_isolation.py').write_text(
            'from pathlib import Path\n'
            'import socket\n'
            'import subprocess\n'
            'import unittest\n\n'
            'class IsolationTest(unittest.TestCase):\n'
            '    def test_external_write(self):\n'
            f'        Path({str(escaped)!r}).write_text("forbidden")\n\n'
            '    def test_network(self):\n'
            '        socket.socket()\n\n'
            '    def test_process(self):\n'
            '        subprocess.run(["true"], check=True)\n'
        )
        method = self.implementation(binding=binding)
        method['steps'][0]['target'] = ['resource:repo']
        method['checks'] = [{
            'id': 'CHK-001', 'name': 'Sandbox negative fixture',
            'kind': 'project_command', 'resource': 'repo', 'cwd': '.',
            'command': ['python', '-m', 'unittest', 'discover', '-s', 'integration',
                        '-p', 'test_isolation.py'],
        }]
        result = self.invoke(binding=binding, implementation=method)
        self.assertEqual(result['gate']['result'], 'fail', result)
        self.assertFalse(escaped.exists())
        stored = self.stored(result)
        evidence = json.loads(next(
            item.raw_bytes for item in stored.payload.members
            if item.member_id == 'EVD-CHK-001'
        ))
        self.assertIn('isolated project check denied', evidence['stderr'])

    def test_applicable_checks_cannot_be_omitted_or_marked_na(self):
        for value in ([], [{'id': 'CHK-001', 'name': 'Not run', 'kind': 'n/a', 'resource': 'repo', 'path': 'integration/app.txt'}]):
            method = self.implementation()
            method['checks'] = value
            before = tree_bytes(self.root)
            result = self.invoke(implementation=method)
            self.assertFalse(result['ok'], result)
            self.assertEqual(tree_bytes(self.root), before)

    def test_imp_build_failure_after_allocation_abandons_exact_reservation(self):
        before_product = (self.root / 'integration/app.txt').read_bytes()
        with patch('imp_builder.ImpBuilder.build', side_effect=ValueError('injected IMP build failure')):
            result = self.invoke(implementation=self.implementation())
        self.assertFalse(result['ok'], result)
        claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        self.assertEqual(claim.state, 'abandoned')
        revisions = ArtifactCatalog(ArtifactStore.open_read_only(self.root)).list_revisions(claim.artifact_id)
        self.assertEqual([(row.revision, row.state, row.materialized) for row in revisions], [(claim.revision, 'abandoned', False)])
        self.assertEqual((self.root / 'integration/app.txt').read_bytes(), before_product)
