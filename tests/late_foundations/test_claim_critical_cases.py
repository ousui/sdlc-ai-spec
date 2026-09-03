from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import tempfile
from threading import Barrier
import unittest

from packages.sdlc_claim_provider import (
    AcquireRequest, ClaimConflictError, ClaimMismatchError, ClaimNotFoundError, ClaimProvider,
)
from tests.late_foundations.claim_support import prepare_frozen_claim


class ClaimCriticalCases(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.provider = ClaimProvider.open_read_write(self.root)
        self.request = AcquireRequest('PLN-20260903120000-01@1#WI-001', 'executor', ('resource:repo',))

    def transition(self, claim, **overrides):
        return dict(attempt=claim.attempt, owner=claim.owner, artifact_id=claim.artifact_id,
                    revision=claim.revision, generation=claim.generation, **overrides)

    def concurrent_acquire(self, requests):
        barrier = Barrier(len(requests))

        def acquire(request):
            provider = ClaimProvider.open_read_write(self.root)
            barrier.wait(timeout=10)
            try:
                return provider.acquire(request)
            except ClaimConflictError as exc:
                return exc

        with ThreadPoolExecutor(max_workers=len(requests)) as executor:
            return list(executor.map(acquire, requests))

    def test_concurrent_same_lineage_allocates_one_identity_and_attempt(self):
        records = self.concurrent_acquire([self.request] * 4)
        self.assertTrue(all(not isinstance(record, Exception) for record in records), records)
        self.assertEqual(len(set(records)), 1)
        self.assertEqual((records[0].attempt, records[0].revision, records[0].state), (1, 1, 'active'))

    def test_concurrent_same_lineage_leaves_one_current_active_row(self):
        records = self.concurrent_acquire([self.request] * 4)
        current = self.provider.resolve(self.request.binding_reference)
        self.assertIsNotNone(current)
        self.assertEqual(current.state, 'active')
        self.assertTrue(all(record == current for record in records), records)

    def test_concurrent_different_lineages_cannot_share_active_resource(self):
        requests = [replace(self.request, binding_reference=f'PLN-20260903120000-01@1#WI-{index:03d}')
                    for index in range(1, 5)]
        results = self.concurrent_acquire(requests)
        self.assertEqual(sum(isinstance(item, ClaimConflictError) for item in results), 3)
        current = [self.provider.resolve(request.binding_reference) for request in requests]
        self.assertEqual(sum(item is not None and item.state == 'active' for item in current), 1)

    def test_active_binding_input_and_rework_mismatch_preserves_claim(self):
        first = self.provider.acquire(self.request)
        before = self.provider.path.read_bytes()
        for changes in (
            {'binding_reference': 'PLN-20260903120000-01@2#WI-001'},
            {'dependency_results': ('IMP-20260903120000-02@1',)},
            {'rework_references': ('VFY-20260903120000-01@1#RET-001',)},
        ):
            with self.subTest(changes=changes), self.assertRaises(ClaimMismatchError):
                self.provider.acquire(replace(self.request, **changes))
        self.assertEqual(self.provider.resolve(first.binding_reference), first)
        self.assertEqual(self.provider.path.read_bytes(), before)

    def test_completed_acquire_and_complete_retry_return_same_record(self):
        first = self.provider.acquire(self.request)
        prepare_frozen_claim(self.root, first)
        complete = self.provider.complete(first.binding_lineage, **self.transition(first))
        before = self.provider.path.read_bytes()
        self.assertEqual(self.provider.complete(first.binding_lineage, **self.transition(first)), complete)
        self.assertEqual(
            self.provider.complete(
                first.binding_lineage,
                **{**self.transition(first), "generation": complete.generation},
            ),
            complete,
        )
        self.assertEqual(self.provider.acquire(self.request), complete)
        self.assertEqual(self.provider.path.read_bytes(), before)
        for changes in ({'owner': 'other'}, {'attempt': 99}, {'revision': 99},
                        {'generation': 99},
                        {'artifact_id': 'IMP-20260903120000-99'}):
            with self.subTest(changes=changes), self.assertRaises(
                (ClaimMismatchError, ClaimNotFoundError)
            ):
                self.provider.complete(
                    first.binding_lineage,
                    **{**self.transition(first), **changes},
                )
        self.assertEqual(self.provider.resolve(first.binding_reference), complete)

    def test_abandon_cas_rejects_owner_attempt_artifact_and_revision_mismatch(self):
        first = self.provider.acquire(self.request)
        before = self.provider.path.read_bytes()
        for changes in ({'owner': 'other'}, {'attempt': 99}, {'revision': 99},
                        {'generation': 99},
                        {'artifact_id': 'IMP-20260903120000-99'}):
            with self.subTest(changes=changes), self.assertRaises((ClaimMismatchError, ClaimNotFoundError)):
                self.provider.abandon(first.binding_lineage, reason='Explicit cancellation',
                                      **{**self.transition(first), **changes})
        self.assertEqual(self.provider.resolve(first.binding_reference), first)
        self.assertEqual(self.provider.path.read_bytes(), before)

    def test_frozen_abandon_rejects_a_forged_completion_failure_reason(self):
        first = self.provider.acquire(self.request)
        prepare_frozen_claim(self.root, first)
        before = self.provider.path.read_bytes()
        with self.assertRaisesRegex(ClaimMismatchError, "still satisfies"):
            self.provider.abandon(
                first.binding_lineage,
                reason='complete:CLAIM_PROVIDER_ERROR:forged failure',
                abandoned_by='authorized-recovery-agent',
                **self.transition(first),
            )
        self.assertEqual(self.provider.resolve(first.binding_reference), first)
        self.assertEqual(self.provider.path.read_bytes(), before)

    def test_abandon_records_actor_and_terminal_retry_preserves_actor_and_reason(self):
        predecessor_request = replace(
            self.request,
            binding_reference='PLN-20260903120000-01@1#WI-000',
            execution_scope=('resource:predecessor',),
        )
        predecessor = self.provider.acquire(predecessor_request)
        prepare_frozen_claim(self.root, predecessor)
        self.provider.complete(
            predecessor.binding_lineage, **self.transition(predecessor)
        )
        dependent_request = replace(
            self.request,
            execution_scope=('resource:dependent',),
            dependency_results=(
                f'{predecessor.artifact_id}@{predecessor.revision}',
            ),
        )
        first = self.provider.acquire(dependent_request)
        prepare_frozen_claim(self.root, first)
        self.provider.acquire(replace(
            predecessor_request,
            rework_references=('VFY-20260903130000-01@1#RET-001',),
        ))
        with self.assertRaisesRegex(ClaimMismatchError, "does not match"):
            self.provider.abandon(
                first.binding_lineage,
                reason='complete:CLAIM_MISMATCH:caller supplied different detail',
                abandoned_by='authorized-recovery-agent',
                **self.transition(first),
            )
        self.assertEqual(self.provider.resolve(first.binding_reference), first)
        abandoned = self.provider.abandon(
            first.binding_lineage,
            abandoned_by='authorized-recovery-agent',
            **self.transition(first),
        )
        self.assertEqual(abandoned.state, 'abandoned')
        self.assertEqual(abandoned.owner, first.owner)
        self.assertEqual(abandoned.abandoned_by, 'authorized-recovery-agent')
        self.assertTrue(abandoned.abandon_reason.startswith(
            'complete:CLAIM_MISMATCH:dependency is not the Current completed Result:'
        ))
        before = self.provider.path.read_bytes()
        repeated = self.provider.abandon(
            first.binding_lineage,
            reason=abandoned.abandon_reason,
            abandoned_by=abandoned.abandoned_by,
            **self.transition(first),
        )
        self.assertEqual(repeated, abandoned)
        self.assertEqual(self.provider.path.read_bytes(), before)
        for changes in (
            {'abandoned_by': 'different-actor'},
            {'reason': 'different reason'},
            {'owner': 'different-expected-owner'},
            {'revision': 99},
            {'generation': 99},
            {'artifact_id': 'IMP-20260903120000-99'},
        ):
            values = {
                'reason': abandoned.abandon_reason,
                'abandoned_by': abandoned.abandoned_by,
                **self.transition(first),
                **changes,
            }
            with self.subTest(changes=changes), self.assertRaises(ClaimMismatchError):
                self.provider.abandon(first.binding_lineage, **values)
        self.assertEqual(self.provider.resolve(first.binding_reference), abandoned)
        self.assertEqual(self.provider.path.read_bytes(), before)

    def test_historical_completed_attempt_does_not_replace_current_active_attempt(self):
        first = self.provider.acquire(self.request)
        prepare_frozen_claim(self.root, first)
        self.provider.complete(first.binding_lineage, **self.transition(first))
        current = self.provider.acquire(replace(self.request, rework_references=('VFY-20260903120000-01@1#RET-001',)))
        self.assertEqual((current.artifact_id, current.attempt, current.revision, current.state),
                         (first.artifact_id, 2, 2, 'active'))
        self.assertEqual(self.provider.resolve(first.binding_reference), current)
        self.assertEqual(self.provider.resolve_artifact(first.artifact_id), current)
