"""IMP-E054: frozen bytes are candidates, never inherited execution authority."""
from copy import deepcopy
from dataclasses import replace
import json
from unittest.mock import patch

from packages.sdlc_artifact_store import ArtifactStore, NotFoundError
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_claim_provider import ClaimProvider
from packages.sdlc_lifecycle import LifecycleQueryService
from packages.sdlc_runtime import parse_canonical_artifact
from tests.skill_imp.support import ImpFixture, OWNER, tree_bytes
from imp_result import capture, read_member, read_state


class ControlRecoveryTests(ImpFixture):
    def lost_authority(self):
        completed = self.finish(self.create_open())
        old = self.stored(completed)
        # Only a disposable fixture's confirmation is lost; frozen Store bytes
        # and Claim history remain intact, as in Core control recovery.
        (self.root / self.imp_authority.split('@')[0]).unlink()
        self.imp_authority = self._authority('new-implementation-confirmation')
        return completed, old

    def recover(self, previous, **kwargs):
        return self.invoke('revise', binding=False, reference=previous['artifact']['reference'],
                           inputs={'input_references': [previous['artifact']['reference']]}, **kwargs)

    def test_frozen_no_change_control_recovery_uses_new_authority(self):
        completed, old = self.lost_authority()
        product = capture(self.root, 'repo')
        old_state = read_state(old)
        opened = self.recover(completed)
        self.assertEqual(opened['status'], 'action_required', opened)
        self.assertEqual(opened['artifact']['id'], old.control.artifact_id)
        self.assertEqual(opened['artifact']['revision'], old.control.revision + 1)
        self.assertEqual(opened['artifact']['revision_state'], 'open')
        self.assertEqual(self.info(opened)['attempt'], old_state['claim']['attempt'] + 1)
        self.assertFalse(self.info(opened)['vfy_ready'])
        new = self.stored(opened)
        state = read_state(new)
        self.assertEqual(new.control.base_revision, old.control.revision)
        self.assertEqual(state['binding'], old_state['binding'])
        self.assertEqual(state['claim']['rework_references'], [completed['artifact']['reference']])
        self.assertNotIn(completed['artifact']['reference'],
                         parse_canonical_artifact(new.payload.primary_blob).front_matter['inputs'])
        self.assertNotIn('final_confirmation', state)
        self.assertEqual(state['resources'][0]['id'], old_state['resources'][0]['id'])
        row = state['resources'][0]
        self.assertEqual(row['baseline_reference'], row['result_reference'])
        self.assertTrue(row['result_reference'].startswith(opened['artifact']['reference'] + '/'))
        self.assertEqual((row['change_reference'], row['changed_scope'], row['steps']), ('N/A', [], []))
        self.assertEqual(state['completed_operations'], [])
        self.assertEqual(state['actions'], [])
        proof = json.loads(read_member(new, 'EVD-RECOVERY').raw_bytes)
        self.assertEqual(proof['candidate'], completed['artifact']['reference'])
        self.assertEqual(proof['claim'], state['claim'])
        self.assertEqual(proof['result'], 'pass')
        self.assertNotEqual(read_member(new, 'EVD-PRE').sha256, read_member(old, 'EVD-PRE').sha256)
        self.assertEqual(capture(self.root, 'repo'), product)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.original_head)

        stale = self.invoke('revise', binding=False, reference=opened['artifact']['reference'],
                            final=self.confirmation(completed))
        self.assertFalse(stale['ok'], stale)
        self.assertEqual(stale['errors'][0]['code'], 'IMP_FINAL_CONFIRMATION_STALE')
        closed = self.finish(stale)
        self.assertTrue(self.info(closed)['vfy_ready'])
        self.assertEqual(self.info(closed)['claim_state'], 'completed')
        self.assertEqual(self.stored(completed), old)
        self.assertEqual(capture(self.root, 'repo'), product)

    def test_recovery_check_is_strictly_read_only(self):
        completed, _ = self.lost_authority()
        closed = self.finish(self.recover(completed))
        before = tree_bytes(self.root)
        with patch('imp_executor.execute', side_effect=AssertionError('check must not execute')):
            checked = self.invoke('check', binding=False, reference=closed['artifact']['reference'])
        self.assertTrue(checked['ok'], checked)
        self.assertEqual(tree_bytes(self.root), before)

    def test_valid_frozen_result_cannot_start_spurious_recovery(self):
        completed = self.finish(self.create_open())
        before = tree_bytes(self.root)
        denied = self.recover(completed)
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(denied['errors'][0]['code'], 'IMP_CONTROL_RECOVERY_INVALID')
        self.assertEqual(tree_bytes(self.root), before)

    def test_empty_or_ambiguous_recovery_reference_does_not_open_frozen(self):
        completed, old = self.lost_authority()
        before = tree_bytes(self.root)
        for references in ([], [''], ['None'], [old.control.artifact_id],
                           [old.control.artifact_id + '@latest'], [completed['artifact']['reference'] + '#RES-001']):
            with self.subTest(references=references):
                denied = self.invoke('revise', binding=False, reference=completed['artifact']['reference'],
                                     inputs={'input_references': references})
                self.assertFalse(denied['ok'], denied)
                self.assertEqual(tree_bytes(self.root), before)

    def test_ordinary_revise_cannot_bypass_frozen(self):
        completed = self.finish(self.create_open())
        before = tree_bytes(self.root)
        denied = self.invoke('revise', binding=False, reference=completed['artifact']['reference'],
                             implementation=self.implementation(before='after', after='unauthorized'))
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(tree_bytes(self.root), before)

    def test_recovery_rejects_product_drift_before_claim(self):
        completed, _ = self.lost_authority()
        (self.root / 'integration/app.txt').write_text('unrelated current change\n')
        before = tree_bytes(self.root)
        denied = self.recover(completed)
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(tree_bytes(self.root), before)

    def test_recovery_cannot_change_method_or_product(self):
        completed, old = self.lost_authority()
        method = deepcopy(read_state(old)['method'])
        method['operations'] = []
        method['checks'][0]['expected'] = 'another outcome\n'
        before = tree_bytes(self.root)
        denied = self.recover(completed, implementation=method)
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(tree_bytes(self.root), before)

    def test_unresolved_product_return_disqualifies_no_change_recovery(self):
        completed = self.finish(self.create_open())
        self.vfy_return(completed)
        (self.root / self.imp_authority.split('@')[0]).unlink()
        before = tree_bytes(self.root)
        denied = self.recover(completed)
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(tree_bytes(self.root), before)

    def test_same_recovery_sequence_is_idempotent_and_keeps_current_attempt(self):
        completed, _ = self.lost_authority()
        opened = self.recover(completed)
        self.assertIsNotNone(opened['artifact'], opened)
        reference = opened['artifact']['reference']
        repeated = self.invoke('revise', binding=False, reference=reference,
                               inputs={'input_references': [completed['artifact']['reference']]})
        self.assertEqual(repeated['artifact']['reference'], reference, repeated)
        closed = self.finish(repeated)
        before = tree_bytes(self.root)
        repeated = self.invoke('revise', binding=False, reference=reference,
                               inputs={'input_references': [completed['artifact']['reference']]})
        self.assertTrue(repeated['ok'], repeated)
        self.assertEqual(repeated['artifact'], closed['artifact'])
        self.assertEqual(tree_bytes(self.root), before)
        revisions = ArtifactCatalog(ArtifactStore.open_read_only(self.root)).list_revisions(closed['artifact']['id'])
        self.assertEqual([item.revision for item in revisions], [1, 2])

    def test_stale_reference_from_another_recovery_sequence_is_rejected(self):
        completed, _ = self.lost_authority()
        second = self.finish(self.recover(completed))
        (self.root / self.imp_authority.split('@')[0]).unlink()
        self.imp_authority = self._authority('third-implementation-confirmation')
        third = self.recover(second)
        self.assertIsNotNone(third['artifact'], third)
        before = tree_bytes(self.root)
        denied = self.invoke('revise', binding=False, reference=third['artifact']['reference'],
                             inputs={'input_references': [completed['artifact']['reference']]})
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(tree_bytes(self.root), before)

    def test_wrong_artifact_reference_is_rejected(self):
        completed, _ = self.lost_authority()
        before = tree_bytes(self.root)
        denied = self.invoke('revise', binding=False, reference=completed['artifact']['reference'],
                             inputs={'input_references': ['IMP-20260101000000-99@1']})
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(tree_bytes(self.root), before)

    def test_new_owner_receives_new_current_claim_not_old_authority(self):
        completed, old = self.lost_authority()
        opened = self.recover(completed, owner='new-stable-executor')
        self.assertIsNotNone(opened['artifact'], opened)
        claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        self.assertEqual((claim.owner, claim.attempt, claim.revision, claim.state),
                         ('new-stable-executor', 2, 2, 'active'))
        self.assertEqual(read_state(old)['claim']['owner'], OWNER)
        before = tree_bytes(self.root)
        denied = self.invoke('revise', binding=False, reference=opened['artifact']['reference'], owner=OWNER)
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(tree_bytes(self.root), before)

    def separate_resource_chain(self):
        plan = self.plan(second_imp=True)
        plan['work_items'][0]['execution_scope'] = ['resource:repo']
        plan['work_items'][1]['execution_scope'] = ['resource:aux']
        plan['delivery_scope'].append({'scope_token': 'resource:aux',
            'source_references': [self.dsn_reference + '#CHG-001'], 'outcome': 'Dependent auxiliary result'})
        upstream = self.execute_pln(operation='revise', reference=self.pln_reference, plan=plan)
        self.assertTrue(upstream['ok'], upstream)
        self.pln_reference = upstream['artifact']['reference']
        self.binding = self.pln_reference + '#WI-001'
        method = self.implementation()
        method['resources'] = [{'id': 'repo', 'root': 'integration'}]
        method['steps'][0]['target'] = ['resource:repo']
        method['operations'][0]['path'] = method['checks'][0]['path'] = 'app.txt'
        first = self.finish(self.create_open(implementation=method))
        first_authority = self.imp_authority
        self.imp_authority = self._authority('auxiliary-confirmation')
        method = self.implementation()
        method['resources'] = [{'id': 'aux', 'root': 'aux'}]
        method['steps'][0]['target'] = ['resource:aux']
        method['operations'] = [{'resource': 'aux', 'path': 'second.txt', 'step': 'STEP-001',
                                 'op': 'write_text', 'content': 'dependent', 'expected_sha256': 'absent'}]
        method['checks'][0].update(resource='aux', path='second.txt', expected='dependent')
        second = self.finish(self.create_open(binding=self.pln_reference + '#WI-002', implementation=method))
        return first, second, first_authority

    def test_cross_lineage_recovery_reference_is_rejected(self):
        first, second, _ = self.separate_resource_chain()
        before = tree_bytes(self.root)
        denied = self.invoke('revise', binding=False, reference=first['artifact']['reference'],
                             inputs={'input_references': [second['artifact']['reference']]})
        self.assertFalse(denied['ok'], denied)
        self.assertEqual(denied['errors'][0]['code'], 'IMP_BINDING_MISMATCH')
        self.assertEqual(tree_bytes(self.root), before)

    def test_new_current_attempt_invalidates_successor_and_rechecks_dependency_chain(self):
        first, second, authority = self.separate_resource_chain()
        (self.root / authority.split('@')[0]).unlink()
        self.imp_authority = self._authority('recovered-first-confirmation')
        recovery = self.recover(first)
        self.assertIsNotNone(recovery['artifact'], recovery)
        query = LifecycleQueryService(self.root)
        projection = query.inspect_requirement(self.requirement_reference)
        claims = {item.binding_reference: item for item in projection.current_claims}
        self.assertEqual(claims[self.binding].attempt, 2)
        self.assertEqual(claims[self.binding].artifact_reference, recovery['artifact']['reference'])
        self.assertFalse(claims[self.binding].completed)
        self.assertFalse(claims[self.pln_reference + '#WI-002'].completed)
        self.assertEqual(projection.vfy_inputs, ())
        restored_first = self.finish(recovery)
        projection = query.inspect_requirement(self.requirement_reference)
        self.assertEqual(projection.vfy_inputs, ())
        before = tree_bytes(self.root)
        incomplete = self.recover(second)
        self.assertFalse(incomplete['ok'], incomplete)
        self.assertEqual(tree_bytes(self.root), before)
        self.imp_authority = self._authority('recovered-second-confirmation')
        opened = self.invoke('revise', binding=False, reference=second['artifact']['reference'],
                             inputs={'input_references': [second['artifact']['reference'],
                                                          restored_first['artifact']['reference']]})
        self.assertIsNotNone(opened['artifact'], opened)
        restored_second = self.finish(opened)
        state = read_state(self.stored(restored_second))
        self.assertEqual(state['request']['dependencies'], [restored_first['artifact']['reference']])
        self.assertNotIn(first['artifact']['reference'], state['request']['artifact_inputs'])
        self.assertNotIn(second['artifact']['reference'], state['request']['artifact_inputs'])
        before = tree_bytes(self.root)
        projection = query.inspect_requirement(self.requirement_reference)
        self.assertEqual({item.attempt for item in projection.current_claims}, {2})
        self.assertTrue(all(item.completed and item.vfy_ready for item in projection.current_claims))
        self.assertEqual(set(projection.vfy_inputs),
                         {restored_first['artifact']['reference'], restored_second['artifact']['reference']})
        self.assertEqual(tree_bytes(self.root), before)

    def test_successor_recovery_uses_local_candidate_when_old_baseline_is_unreadable(self):
        first, second, authority = self.separate_resource_chain()
        (self.root / authority.split('@')[0]).unlink()
        self.imp_authority = self._authority('local-candidate-first-confirmation')
        restored_first = self.finish(self.recover(first))
        self.imp_authority = self._authority('local-candidate-second-confirmation')
        from imp_verifier import ImpVerifier
        first_stored = self.stored(restored_first)
        first_state = ImpVerifier(self.root).verify_payload(first_stored)
        old_artifact = first['artifact']['id']
        old_revision = first['artifact']['revision']
        original = ArtifactStore.read_revision
        from imp_readiness import current_result as original_current_result

        def without_old_baseline(store, artifact_id, revision):
            if (artifact_id, revision) == (old_artifact, old_revision):
                raise NotFoundError('former predecessor is no longer resolvable')
            return original(store, artifact_id, revision)

        def current_with_validated_predecessor(store, provider, reference, **kwargs):
            if reference == restored_first['artifact']['reference']:
                return first_stored, first_state
            return original_current_result(store, provider, reference, **kwargs)

        with patch.object(ArtifactStore, 'read_revision', without_old_baseline), \
             patch('imp_readiness.current_result', current_with_validated_predecessor):
            opened = self.invoke(
                'revise', binding=False, reference=second['artifact']['reference'],
                inputs={'input_references': [
                    second['artifact']['reference'],
                    restored_first['artifact']['reference'],
                ]},
            )
            self.assertIsNotNone(opened['artifact'], opened)
            completed = self.finish(opened)
        self.assertTrue(self.info(completed)['vfy_ready'])

    def test_candidate_local_closure_still_rejects_a_missing_retained_snapshot(self):
        completed, _ = self.lost_authority()
        stored = self.stored(completed)
        state = read_state(stored)
        missing = state['resources'][0]['result_member']
        broken = replace(
            stored,
            payload=replace(
                stored.payload,
                members=tuple(item for item in stored.payload.members if item.member_id != missing),
            ),
        )
        from imp_verifier import ImpVerifier
        with self.assertRaisesRegex(Exception, 'Immutable member is missing'):
            ImpVerifier(self.root).verify_recovery_candidate(broken)

    def test_post_checklist_readback_must_match_candidate_before_no_change_result(self):
        completed, _ = self.lost_authority()
        from imp_handler import ImpHandler
        original = ImpHandler._guard

        def drift(handler, claim, generation):
            original(handler, claim, generation)
            (self.root / 'integration/app.txt').write_text('concurrent product change\n')

        with patch.object(ImpHandler, '_guard', drift):
            denied = self.recover(completed)
        self.assertFalse(denied['ok'], denied)
        claim = ClaimProvider.open_read_only(self.root).resolve(self.binding)
        self.assertEqual((claim.attempt, claim.state), (2, 'active'))
        stored = ArtifactStore.open_read_only(self.root).read_revision(claim.artifact_id, claim.revision)
        self.assertEqual(stored.control.state, 'open')
        self.assertEqual(read_state(stored)['stage'], 'prepared')
        self.assertEqual((self.root / 'integration/app.txt').read_text(), 'concurrent product change\n')
