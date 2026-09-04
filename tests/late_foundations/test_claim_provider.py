from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from packages.sdlc_claim_provider import (
    AcquireRequest,
    ClaimConflictError,
    ClaimMismatchError,
    ClaimProvider,
    ClaimProviderError,
)
from tests.late_foundations.claim_support import (
    prepare_abandoned_claim,
    prepare_frozen_claim,
)

FIXED = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


class ClaimProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.provider = ClaimProvider.open_read_write(self.root, clock=lambda: FIXED)

    def tearDown(self):
        self.temp.cleanup()

    def request(self, binding="PLN-20260901120000-01@1#WI-001", owner="agent-a", scope=("resource:repo",), deps=(), rework=(), retry=False):
        return AcquireRequest(binding, owner, tuple(scope), tuple(deps), tuple(rework), retry)

    def transition(self, claim):
        return {
            "attempt": claim.attempt,
            "owner": claim.owner,
            "artifact_id": claim.artifact_id,
            "revision": claim.revision,
            "generation": claim.generation,
        }

    def complete_claim(self, claim, **overrides):
        prepare_frozen_claim(self.root, claim)
        values = self.transition(claim)
        values.update(overrides)
        return self.provider.complete(claim.binding_lineage, **values)

    def abandon_claim(self, claim, *, reason, **overrides):
        prepare_abandoned_claim(self.root, claim, reason)
        values = self.transition(claim)
        values.update(overrides)
        return self.provider.abandon(
            claim.binding_lineage, reason=reason, **values
        )

    def test_acquire_is_idempotent_for_same_active_request(self):
        first = self.provider.acquire(self.request())
        second = self.provider.acquire(self.request())
        self.assertEqual(first, second)
        self.assertEqual(first.attempt, 1)
        self.assertEqual(first.state, "active")
        self.assertEqual(first.generation, 0)
        self.assertEqual(first.created_at, first.updated_at)

    def test_read_only_connection_cannot_write_even_with_query_only_disabled(self):
        first = self.provider.acquire(self.request())
        reader = ClaimProvider.open_read_only(self.root)
        before = reader.path.read_bytes()
        with closing(reader._connect()) as connection:
            connection.execute("PRAGMA query_only=OFF")
            with self.assertRaisesRegex(sqlite3.OperationalError, "readonly"):
                connection.execute("DELETE FROM imp_claims WHERE 0")
        self.assertEqual(reader.resolve(first.binding_reference), first)
        self.assertEqual(reader.path.read_bytes(), before)

    def test_active_mismatch_and_resource_conflict_fail_closed(self):
        self.provider.acquire(self.request())
        with self.assertRaises(ClaimMismatchError):
            self.provider.acquire(self.request(owner="agent-b"))
        with self.assertRaises(ClaimConflictError):
            self.provider.acquire(self.request(binding="PLN-20260901120000-01@1#WI-002", scope=("resource:repo",)))

    def test_completed_claim_can_start_new_rework_attempt(self):
        first = self.provider.acquire(self.request())
        self.complete_claim(first)
        second = self.provider.acquire(self.request(rework=("VFY-20260901130000-01@1#RET-001",)))
        self.assertEqual(second.attempt, 2)
        self.assertEqual(second.artifact_id, first.artifact_id)
        self.assertEqual(second.revision, 2)
        self.assertEqual(second.state, "active")

    def test_completed_rework_sequence_is_idempotent(self):
        first = self.provider.acquire(self.request())
        self.complete_claim(first)
        rework = ("VFY-20260901130000-01@1#RET-001",)
        second = self.provider.acquire(self.request(rework=rework))
        completed = self.complete_claim(second)
        repeated = self.provider.acquire(self.request(rework=rework))
        self.assertEqual(repeated, completed)
        self.assertEqual((repeated.attempt, repeated.revision), (2, 2))
        with self.assertRaisesRegex(ClaimMismatchError, "different Owner"):
            self.provider.acquire(self.request(owner="agent-b", rework=rework))

    def test_rework_reference_order_is_one_canonical_set(self):
        first = self.provider.acquire(self.request())
        self.complete_claim(first)
        references = (
            "VFY-20260901130000-01@1#RET-001",
            "VFY-20260901130000-01@1#RET-002",
        )
        second = self.provider.acquire(self.request(rework=references))
        completed = self.complete_claim(second)
        repeated = self.provider.acquire(self.request(rework=tuple(reversed(references))))
        self.assertEqual(repeated, completed)
        self.assertEqual(repeated.rework_references, tuple(sorted(references)))

    def test_terminal_transition_requires_matching_artifact_control(self):
        claim = self.provider.acquire(self.request())
        with self.assertRaisesRegex(ClaimMismatchError, "Artifact Revision"):
            self.provider.complete(
                claim.binding_lineage, **self.transition(claim)
            )
        with self.assertRaisesRegex(ClaimMismatchError, "Artifact Revision"):
            self.provider.abandon(
                claim.binding_lineage,
                **self.transition(claim),
                reason="cancelled",
            )
        self.assertEqual(self.provider.resolve(claim.binding_lineage).state, "active")

    def test_complete_rejects_a_generically_frozen_mismatched_imp_payload(self):
        claim = self.provider.acquire(self.request())

        def replace_claim_owner(state):
            state["claim"]["owner"] = "unreserved-owner"

        prepare_frozen_claim(
            self.root, claim, state_mutator=replace_claim_owner
        )
        with self.assertRaisesRegex(ClaimMismatchError, "Claim Result"):
            self.provider.complete(
                claim.binding_lineage, **self.transition(claim)
            )
        self.assertEqual(
            self.provider.resolve(claim.binding_lineage).state, "active"
        )

    def test_complete_rechecks_frozen_final_confirmation_authority(self):
        claim = self.provider.acquire(self.request())
        prepare_frozen_claim(self.root, claim)
        authority = (
            self.root
            / ".sdlc"
            / "authority"
            / f"claim-{claim.artifact_id}-{claim.revision}.txt"
        )
        authority.unlink()
        with self.assertRaisesRegex(ClaimMismatchError, "authorize Claim"):
            self.provider.complete(
                claim.binding_lineage, **self.transition(claim)
            )
        self.assertEqual(
            self.provider.resolve(claim.binding_lineage).state, "active"
        )

    def test_complete_recomputes_the_immutable_resource_chain(self):
        claim = self.provider.acquire(self.request())

        def corrupt_snapshot_digest(snapshot):
            snapshot["entries"][0]["sha256"] = "0" * 64

        prepare_frozen_claim(
            self.root,
            claim,
            snapshot_mutator=corrupt_snapshot_digest,
        )
        with self.assertRaisesRegex(ClaimMismatchError, "digest changed"):
            self.provider.complete(
                claim.binding_lineage, **self.transition(claim)
            )
        self.assertEqual(
            self.provider.resolve(claim.binding_lineage).state, "active"
        )

    def test_noncanonical_stored_rework_fails_closed(self):
        claim = self.provider.acquire(self.request())
        corrupt = json.dumps([
            "VFY-20260901130000-01@1#RET-002",
            "VFY-20260901130000-01@1#RET-001",
            "VFY-20260901130000-01@1#RET-001",
        ])
        with closing(sqlite3.connect(self.provider.path)) as connection:
            connection.execute(
                "UPDATE imp_claims SET rework_references=?",
                (corrupt,),
            )
            connection.commit()
        with self.assertRaisesRegex(ClaimProviderError, "canonical set"):
            self.provider.resolve(claim.binding_lineage)

    def test_invalid_or_reversed_stored_timestamps_fail_closed(self):
        claim = self.provider.acquire(self.request())
        cases = (
            ("not-rfc3339", claim.updated_at),
            (claim.created_at, "2026-08-31T23:59:59+00:00"),
        )
        for created_at, updated_at in cases:
            with self.subTest(created_at=created_at, updated_at=updated_at):
                with closing(sqlite3.connect(self.provider.path)) as connection:
                    connection.execute(
                        "UPDATE imp_claims SET created_at=?, updated_at=?",
                        (created_at, updated_at),
                    )
                    connection.commit()
                with self.assertRaises(ClaimProviderError):
                    self.provider.resolve(claim.binding_lineage)
        with closing(sqlite3.connect(self.provider.path)) as connection:
            connection.execute(
                "UPDATE imp_claims SET created_at=?, updated_at=?",
                (claim.created_at, claim.updated_at),
            )
            connection.commit()

    def test_blank_or_noncanonical_stored_identity_fields_fail_closed(self):
        claim = self.provider.acquire(self.request())
        for field, value in (("owner", ""), ("owner", " agent-a")):
            with self.subTest(field=field, value=value):
                with closing(sqlite3.connect(self.provider.path)) as connection:
                    connection.execute(
                        f"UPDATE imp_claims SET {field}=?",
                        (value,),
                    )
                    connection.commit()
                with self.assertRaisesRegex(ClaimProviderError, "metadata"):
                    self.provider.resolve(claim.binding_lineage)
                with closing(sqlite3.connect(self.provider.path)) as connection:
                    connection.execute(
                        "UPDATE imp_claims SET owner=?",
                        (claim.owner,),
                    )
                    connection.commit()

        abandoned = self.abandon_claim(claim, reason="cancelled")
        for field, value in (("abandoned_by", " "), ("abandon_reason", " ")):
            with self.subTest(field=field):
                with closing(sqlite3.connect(self.provider.path)) as connection:
                    connection.execute(
                        f"UPDATE imp_claims SET {field}=?",
                        (value,),
                    )
                    connection.commit()
                with self.assertRaisesRegex(ClaimProviderError, "terminal fields"):
                    self.provider.resolve(claim.binding_lineage)
                with closing(sqlite3.connect(self.provider.path)) as connection:
                    connection.execute(
                        f"UPDATE imp_claims SET {field}=?",
                        (getattr(abandoned, field),),
                    )
                    connection.commit()

    def test_invalid_stored_state_fails_closed_before_resource_reallocation(self):
        self.provider.acquire(self.request())
        with closing(sqlite3.connect(self.provider.path)) as connection:
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute("UPDATE imp_claims SET state='bogus'")
            connection.commit()
        with self.assertRaises(ClaimProviderError):
            self.provider.acquire(self.request(
                binding="PLN-20260901120000-01@1#WI-002",
                scope=("resource:repo",),
            ))
        with closing(sqlite3.connect(self.provider.path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM imp_claims").fetchone()[0],
                1,
            )

    def test_claim_tables_are_namespaced_in_the_shared_artifact_store(self):
        self.provider.acquire(self.request())
        self.assertEqual(self.provider.path.name, "store.sqlite3")
        with closing(sqlite3.connect(self.provider.path)) as connection:
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='imp_claims'"
            ).fetchone()[0]
        self.assertIn("artifacts", tables)
        self.assertIn("imp_claims", tables)
        self.assertIn("CHECK (state IN ('active', 'completed', 'abandoned'))", schema)
        self.assertIn("created_at TEXT NOT NULL", schema)
        self.assertIn("updated_at TEXT NOT NULL", schema)
        self.assertIn("generation INTEGER NOT NULL CHECK (generation >= 0)", schema)

    def test_abandoned_claim_requires_explicit_retry(self):
        first = self.provider.acquire(self.request())
        self.abandon_claim(first, reason="cancelled")
        with self.assertRaises(ClaimMismatchError):
            self.provider.acquire(self.request())
        second = self.provider.acquire(self.request(retry=True))
        self.assertEqual(second.attempt, 2)

    def test_abandoned_retry_may_assign_a_new_stable_owner(self):
        first = self.provider.acquire(self.request())
        self.abandon_claim(first, reason="cancelled")
        second = self.provider.acquire(self.request(owner="agent-b", retry=True))
        self.assertEqual(
            (second.artifact_id, second.attempt, second.revision, second.owner, second.state),
            (first.artifact_id, 2, 2, "agent-b", "active"),
        )

    def test_abandoned_nonempty_rework_sequence_still_requires_explicit_retry(self):
        first = self.provider.acquire(self.request())
        self.complete_claim(first)
        rework = ("VFY-20260901130000-01@1#RET-001",)
        second = self.provider.acquire(self.request(rework=rework))
        self.abandon_claim(second, reason="execution stopped")
        with self.assertRaisesRegex(ClaimMismatchError, "explicit retry"):
            self.provider.acquire(self.request(rework=rework))
        retried = self.provider.acquire(self.request(rework=rework, retry=True))
        self.assertEqual((retried.attempt, retried.revision, retried.state), (3, 3, "active"))

    def test_complete_requires_current_completed_dependencies(self):
        predecessor = self.provider.acquire(self.request(binding="PLN-20260901120000-01@1#WI-001", scope=("resource:a",)))
        self.complete_claim(predecessor)
        dependency_ref = predecessor.artifact_id + "@1"
        successor = self.provider.acquire(self.request(binding="PLN-20260901120000-01@1#WI-002", scope=("resource:b",), deps=(dependency_ref,)))
        completed = self.complete_claim(successor)
        self.assertEqual(completed.state, "completed")
        self.assertEqual(completed.generation, 1)
        rework = self.provider.acquire(self.request(binding="PLN-20260901120000-01@1#WI-001", scope=("resource:a",), rework=("VFY-20260901130000-01@1#RET-001",)))
        third = self.provider.acquire(self.request(binding="PLN-20260901120000-01@1#WI-003", scope=("resource:c",), deps=(dependency_ref,)))
        with self.assertRaises(ClaimMismatchError):
            self.provider.complete(third.binding_lineage, **self.transition(third))
        self.assertEqual(rework.state, "active")

    def test_complete_recursively_rechecks_dependency_chain(self):
        first = self.provider.acquire(
            self.request(
                binding="PLN-20260901120000-01@1#WI-001",
                scope=("resource:a",),
            )
        )
        self.complete_claim(first)
        second = self.provider.acquire(
            self.request(
                binding="PLN-20260901120000-01@1#WI-002",
                scope=("resource:b",),
                deps=(first.artifact_id + "@1",),
            )
        )
        self.complete_claim(second)
        third = self.provider.acquire(
            self.request(
                binding="PLN-20260901120000-01@1#WI-003",
                scope=("resource:c",),
                deps=(second.artifact_id + "@1",),
            )
        )
        self.provider.acquire(
            self.request(
                binding="PLN-20260901120000-01@1#WI-001",
                scope=("resource:a",),
                rework=("VFY-20260901130000-01@1#RET-001",),
            )
        )
        with self.assertRaises(ClaimMismatchError):
            self.provider.complete(
                third.binding_lineage,
                **self.transition(third),
            )


if __name__ == "__main__":
    unittest.main()
