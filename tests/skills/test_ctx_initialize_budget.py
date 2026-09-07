"""Bounded initialization recovery starts when recovery is first needed.

Use controlled monotonic time, not sleeps or a nested invocation of another test
suite. Real concurrent-first-create and corrupt-store tests remain in full.
"""
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from tests.skills import test_sdlc_000_ctx as ctx
from sdlc_artifact_store.errors import ConflictError, SchemaError, TrackedRuntimeContentError


class ControlledTime:
    def __init__(self):
        self.elapsed = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.elapsed += seconds


class InitializationBudgetTests(unittest.TestCase):
    def test_slow_first_conflict_still_gets_a_validated_retry(self):
        clock, store = ControlledTime(), MagicMock()
        attempts = []

        def initialize():
            attempts.append(None)
            if len(attempts) == 1:
                clock.elapsed += 2.0
                raise ConflictError('Artifact Store appeared during initialize; retry only after validating its Schema')
            return 1

        store.initialize.side_effect = initialize
        with patch.object(ctx.runtime, 'time', clock), \
                patch.object(ctx.runtime.ArtifactStore, 'open_read_write', return_value=store), \
                patch.object(ctx.runtime.ArtifactStore, 'open_read_only') as validate:
            actual = ctx.runtime._open_initialized_store(Path('/synthetic-fixture'), clock=lambda: None)
        self.assertIs(actual, store)
        self.assertEqual(store.initialize.call_count, 2)
        self.assertEqual(validate.call_count, 1)
        self.assertEqual(clock.sleeps, [ctx.runtime.INITIALIZE_RECOVERY_DELAY_SECONDS])

    def test_slow_initial_validation_failure_still_requires_successful_validation(self):
        clock, store = ControlledTime(), MagicMock()
        validations = []

        def validate(_root):
            validations.append(None)
            if len(validations) == 1:
                clock.elapsed += 2.0
                raise SchemaError('first creator has not completed the schema')
            return object()

        with patch.object(ctx.runtime, 'time', clock), \
                patch.object(ctx.runtime.ArtifactStore, 'open_read_write', return_value=store), \
                patch.object(ctx.runtime.ArtifactStore, 'open_read_only', side_effect=validate):
            actual = ctx.runtime._open_initialized_store(Path('/synthetic-fixture'), clock=lambda: None)
        self.assertIs(actual, store)
        self.assertEqual(store.initialize.call_count, 2)
        self.assertEqual(len(validations), 2)

    def test_persistent_schema_failure_exhausts_budget_without_succeeding(self):
        clock, store = ControlledTime(), MagicMock()
        failure = SchemaError('persistent invalid schema')
        store.initialize.side_effect = failure
        with patch.object(ctx.runtime, 'time', clock), \
                patch.object(ctx.runtime.ArtifactStore, 'open_read_write', return_value=store), \
                patch.object(ctx.runtime.ArtifactStore, 'open_read_only') as validate:
            with self.assertRaises(SchemaError) as caught:
                ctx.runtime._open_initialized_store(Path('/synthetic-fixture'), clock=lambda: None)
        self.assertIs(caught.exception, failure)
        self.assertGreater(store.initialize.call_count, 1)
        self.assertFalse(validate.called)
        self.assertGreaterEqual(clock.elapsed, ctx.runtime.INITIALIZE_RECOVERY_TIMEOUT_SECONDS)
        self.assertLessEqual(clock.elapsed, ctx.runtime.INITIALIZE_RECOVERY_TIMEOUT_SECONDS +
                             ctx.runtime.INITIALIZE_RECOVERY_DELAY_SECONDS + 1e-9)

    def test_nonrecoverable_failure_is_never_retried(self):
        clock, store = ControlledTime(), MagicMock()
        failure = TrackedRuntimeContentError('tracked runtime requires explicit user action')
        store.initialize.side_effect = failure
        with patch.object(ctx.runtime, 'time', clock), \
                patch.object(ctx.runtime.ArtifactStore, 'open_read_write', return_value=store), \
                patch.object(ctx.runtime.ArtifactStore, 'open_read_only') as validate:
            with self.assertRaises(TrackedRuntimeContentError) as caught:
                ctx.runtime._open_initialized_store(Path('/synthetic-fixture'), clock=lambda: None)
        self.assertIs(caught.exception, failure)
        self.assertEqual(store.initialize.call_count, 1)
        self.assertFalse(validate.called)
        self.assertEqual(clock.sleeps, [])
