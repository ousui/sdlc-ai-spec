import ast
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PACKAGES_ROOT = REPOSITORY_ROOT / "packages"
if str(PACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGES_ROOT))

from sdlc_artifact_store import (  # noqa: E402
    ArtifactStore,
    CanonicalManifest,
    CanonicalMember,
    CanonicalRevisionPayload,
    ClaimReservation,
    ConflictError,
    ControlReservationError,
    DatabaseError,
    DomainVerification,
    IntegrityError,
    InvalidInputError,
    InvalidStateError,
    ManifestMember,
    NotFoundError,
    ReadOnlyError,
    ReferenceError,
    SchemaError,
    SchemaVersionMismatchError,
    StaleVerificationError,
    StoreNotFoundError,
    TrackedRuntimeContentError,
    VerificationFailedError,
    VerifierRequiredError,
    compute_sha256,
)


FIXED_TIME = datetime(2026, 8, 30, 9, 10, 11, tzinfo=timezone.utc)


class PassingVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
        )


class RejectingVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=False,
            message="deterministic rejection",
        )


class StaleVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding="internal-verifier-binding:" + "0" * 64,
            approved=True,
        )


class ArtifactStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temporary.name) / "project"
        self.project_root.mkdir()
        self.store = ArtifactStore.open_read_write(
            self.project_root, clock=lambda: FIXED_TIME
        )
        self.store.initialize()

    def tearDown(self):
        self.temporary.cleanup()

    def allocate_open(self, artifact_type="CTX"):
        artifact = self.store.allocate_artifact(artifact_type, now=FIXED_TIME)
        control = self.store.allocate_revision(
            artifact.artifact_id, now=FIXED_TIME
        )
        return artifact, control

    def member(self, member_id="SUP-001", name="evidence.json", raw=b"member"):
        return CanonicalMember(
            member_id=member_id,
            canonical_name=name,
            media_type="application/json",
            raw_bytes=raw,
            sha256=compute_sha256(raw),
        )

    def payload(
        self,
        artifact_id,
        revision,
        *,
        status="draft",
        primary=b"---\nstatus: draft\n---\n",
        members=None,
        manifest_members=None,
    ):
        members = tuple(members or ())
        if manifest_members is None:
            manifest_members = tuple(
                ManifestMember(
                    member_id=member.member_id,
                    canonical_name=member.canonical_name,
                    media_type=member.media_type,
                    sha256=member.sha256,
                )
                for member in members
            )
        else:
            manifest_members = tuple(manifest_members)
        artifact_type = artifact_id.split("-", 1)[0]
        manifest_raw = json.dumps(
            {
                "local_members": [item.member_id for item in manifest_members],
                "external_references": [
                    {
                        "reference": "vcs:RSC-001@0123456789abcdef",
                        "digest": "sha256:" + "a" * 64,
                        "access": "project-authorized",
                    }
                ],
            },
            sort_keys=True,
        ).encode("utf-8")
        return CanonicalRevisionPayload(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            revision=revision,
            artifact_status=status,
            primary_blob=primary,
            primary_media_type="text/markdown",
            primary_sha256=compute_sha256(primary),
            members=members,
            manifest=CanonicalManifest(
                raw_bytes=manifest_raw,
                media_type="application/json",
                local_members=manifest_members,
            ),
        )

    def materialize(self, status="draft", members=None):
        artifact, control = self.allocate_open()
        stored = self.store.write_open_revision(
            self.payload(
                artifact.artifact_id,
                control.revision,
                status=status,
                members=members,
            ),
            expected_generation=0,
        )
        return artifact, stored

    def freeze_ready(self):
        artifact, stored = self.materialize(status="ready")
        control = self.store.freeze_revision(
            artifact.artifact_id,
            stored.control.revision,
            verifier=PassingVerifier(),
            now=FIXED_TIME,
        )
        return artifact, control

    def snapshot_files(self, root):
        result = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                result[str(path.relative_to(root))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        return result

    def test_01_initialize_first_create_uses_fixed_runtime_layout(self):
        self.assertEqual((self.project_root / ".sdlc/.gitignore").read_text(), "*\n")
        self.assertTrue((self.project_root / ".sdlc/store.sqlite3").is_file())
        self.assertFalse((self.project_root / ".gitignore").exists())

    def test_02_initialize_is_idempotent(self):
        before = self.snapshot_files(self.project_root / ".sdlc")
        self.assertEqual(self.store.initialize(), 1)
        self.assertEqual(before, self.snapshot_files(self.project_root / ".sdlc"))

    def test_03_read_only_missing_runtime_creates_nothing(self):
        root = Path(self.temporary.name) / "missing-runtime"
        root.mkdir()
        before = self.snapshot_files(root)
        with self.assertRaises(StoreNotFoundError):
            ArtifactStore.open_read_only(root)
        self.assertEqual(before, self.snapshot_files(root))
        self.assertFalse((root / ".sdlc").exists())

    def test_04_read_only_missing_database_creates_nothing(self):
        root = Path(self.temporary.name) / "missing-database"
        (root / ".sdlc").mkdir(parents=True)
        before = self.snapshot_files(root)
        with self.assertRaises(StoreNotFoundError):
            ArtifactStore.open_read_only(root)
        self.assertEqual(before, self.snapshot_files(root))
        self.assertFalse((root / ".sdlc/store.sqlite3").exists())

    def test_05_schema_version_mismatch_fails(self):
        connection = sqlite3.connect(self.store.store_path)
        try:
            connection.execute(
                "UPDATE schema_metadata SET value = '2' WHERE key = 'schema_version'"
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(SchemaVersionMismatchError):
            ArtifactStore.open_read_only(self.project_root)

    def test_06_missing_or_damaged_schema_fails_without_repair(self):
        root = Path(self.temporary.name) / "missing-schema"
        (root / ".sdlc").mkdir(parents=True)
        connection = sqlite3.connect(root / ".sdlc/store.sqlite3")
        connection.close()
        before = self.snapshot_files(root)
        with self.assertRaises(SchemaError):
            ArtifactStore.open_read_only(root)
        self.assertEqual(before, self.snapshot_files(root))
        damaged = Path(self.temporary.name) / "damaged-database"
        (damaged / ".sdlc").mkdir(parents=True)
        (damaged / ".sdlc/store.sqlite3").write_bytes(b"not-a-sqlite-database")
        damaged_before = self.snapshot_files(damaged)
        with self.assertRaises(DatabaseError):
            ArtifactStore.open_read_only(damaged)
        self.assertEqual(damaged_before, self.snapshot_files(damaged))

    def test_07_artifact_id_is_unique_and_same_second_sequence_increments(self):
        first = self.store.allocate_artifact("REQ", now=FIXED_TIME)
        second = self.store.allocate_artifact("REQ", now=FIXED_TIME)
        self.assertEqual(first.artifact_id, "REQ-20260830091011-01")
        self.assertEqual(second.artifact_id, "REQ-20260830091011-02")
        self.assertNotEqual(first.artifact_id, second.artifact_id)

    def test_08_all_supported_prefixes_allocate(self):
        ids = {
            kind: self.store.allocate_artifact(kind, now=FIXED_TIME).artifact_id
            for kind in ("CTX", "REQ", "DSN", "PLN", "VFY", "RLS")
        }
        self.assertEqual(set(ids), {"CTX", "REQ", "DSN", "PLN", "VFY", "RLS"})
        self.assertTrue(all(value.startswith(kind + "-") for kind, value in ids.items()))

    def test_09_revision_is_monotonic_and_never_reused(self):
        artifact, first = self.freeze_ready()
        second = self.store.allocate_revision(
            artifact.artifact_id, base_revision=1, now=FIXED_TIME
        )
        self.assertEqual(second.revision, 2)
        self.store.abandon_revision(artifact.artifact_id, 2, reason="superseded candidate")
        third = self.store.allocate_revision(
            artifact.artifact_id, base_revision=1, now=FIXED_TIME
        )
        self.assertEqual(third.revision, 3)

    def test_10_only_one_open_revision_per_artifact(self):
        artifact, _ = self.allocate_open()
        with self.assertRaises(ConflictError):
            self.store.allocate_revision(artifact.artifact_id, now=FIXED_TIME)

    def test_11_control_reservation_cannot_read_resolve_or_freeze(self):
        artifact, control = self.allocate_open()
        reference = f"{artifact.artifact_id}@{control.revision}"
        with self.assertRaises(ControlReservationError):
            self.store.read_revision(artifact.artifact_id, control.revision)
        with self.assertRaises(ControlReservationError):
            self.store.resolve_exact_reference(reference, verifier=PassingVerifier())
        with self.assertRaises(ControlReservationError):
            self.store.freeze_revision(
                artifact.artifact_id, control.revision, verifier=PassingVerifier()
            )

    def test_12_first_complete_payload_materializes_atomically(self):
        member = self.member()
        artifact, stored = self.materialize(members=(member,))
        self.assertTrue(stored.control.materialized)
        self.assertEqual(stored.control.generation, 1)
        self.assertEqual(stored.payload.members, (member,))
        report = self.store.verify_digest(artifact.artifact_id, 1)
        self.assertTrue(report.closure_verified)
        self.assertEqual(report.member_count, 1)

    def test_13_materialized_open_revision_rewrites_in_place(self):
        artifact, stored = self.materialize()
        rewritten = self.store.write_open_revision(
            self.payload(
                artifact.artifact_id,
                1,
                primary=b"---\nstatus: waiting_input\n---\nchanged\n",
                status="waiting_input",
            ),
            expected_generation=stored.control.generation,
        )
        self.assertEqual(rewritten.control.revision, 1)
        self.assertEqual(rewritten.control.generation, 2)
        connection = sqlite3.connect(self.store.store_path)
        try:
            count = connection.execute(
                "SELECT COUNT(*) FROM revisions WHERE artifact_id = ?",
                (artifact.artifact_id,),
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(count, 1)

    def test_14_missing_member_fails(self):
        artifact, control = self.allocate_open()
        member = self.member()
        declaration = ManifestMember(
            member.member_id, member.canonical_name, member.media_type, member.sha256
        )
        payload = self.payload(
            artifact.artifact_id, control.revision, members=(), manifest_members=(declaration,)
        )
        with self.assertRaises(IntegrityError):
            self.store.write_open_revision(payload, expected_generation=0)

    def test_15_unregistered_extra_member_fails(self):
        artifact, control = self.allocate_open()
        payload = self.payload(
            artifact.artifact_id,
            control.revision,
            members=(self.member(),),
            manifest_members=(),
        )
        with self.assertRaises(IntegrityError):
            self.store.write_open_revision(payload, expected_generation=0)

    def test_16_duplicate_member_id_and_name_fail(self):
        artifact, control = self.allocate_open()
        first = self.member("SUP-001", "one.json", b"one")
        duplicate_id = self.member("SUP-001", "two.json", b"two")
        with self.assertRaises(IntegrityError):
            self.store.write_open_revision(
                self.payload(
                    artifact.artifact_id,
                    control.revision,
                    members=(first, duplicate_id),
                ),
                expected_generation=0,
            )
        duplicate_name = self.member("SUP-002", "one.json", b"two")
        with self.assertRaises(IntegrityError):
            self.store.write_open_revision(
                self.payload(
                    artifact.artifact_id,
                    control.revision,
                    members=(first, duplicate_name),
                ),
                expected_generation=0,
            )

    def test_17_primary_and_member_digest_mismatch_fail(self):
        artifact, control = self.allocate_open()
        payload = self.payload(artifact.artifact_id, control.revision)
        bad_primary = CanonicalRevisionPayload(
            **{**payload.__dict__, "primary_sha256": "sha256:" + "0" * 64}
        )
        with self.assertRaises(IntegrityError):
            self.store.write_open_revision(bad_primary, expected_generation=0)
        bad_member = CanonicalMember(
            "SUP-001", "bad.json", "application/json", b"member", "sha256:" + "0" * 64
        )
        declaration = ManifestMember(
            bad_member.member_id,
            bad_member.canonical_name,
            bad_member.media_type,
            bad_member.sha256,
        )
        with self.assertRaises(IntegrityError):
            self.store.write_open_revision(
                self.payload(
                    artifact.artifact_id,
                    control.revision,
                    members=(bad_member,),
                    manifest_members=(declaration,),
                ),
                expected_generation=0,
            )

    def test_18_manifest_member_metadata_must_match(self):
        artifact, control = self.allocate_open()
        member = self.member()
        declaration = ManifestMember(
            member.member_id, "different.json", member.media_type, member.sha256
        )
        with self.assertRaises(IntegrityError):
            self.store.write_open_revision(
                self.payload(
                    artifact.artifact_id,
                    control.revision,
                    members=(member,),
                    manifest_members=(declaration,),
                ),
                expected_generation=0,
            )

    def test_19_frozen_revision_is_immutable(self):
        artifact, control = self.freeze_ready()
        with self.assertRaises(InvalidStateError):
            self.store.write_open_revision(
                self.payload(artifact.artifact_id, control.revision, status="ready"),
                expected_generation=control.generation,
            )

    def test_20_control_reservation_can_be_abandoned(self):
        artifact, control = self.allocate_open()
        abandoned = self.store.abandon_revision(
            artifact.artifact_id, control.revision, reason="materialization cancelled"
        )
        self.assertEqual(abandoned.state, "abandoned")
        self.assertEqual(abandoned.abandon_reason, "materialization cancelled")
        replacement = self.store.allocate_revision(artifact.artifact_id, now=FIXED_TIME)
        self.assertEqual(replacement.revision, 2)

    def test_21_materialized_open_can_be_abandoned_but_not_authority(self):
        artifact, stored = self.materialize()
        abandoned = self.store.abandon_revision(
            artifact.artifact_id, 1, reason="failed verification"
        )
        self.assertEqual(abandoned.state, "abandoned")
        historical = self.store.read_revision(artifact.artifact_id, 1)
        self.assertEqual(historical.payload.primary_blob, stored.payload.primary_blob)
        with self.assertRaises(InvalidStateError):
            self.store.resolve_exact_reference(
                f"{artifact.artifact_id}@1", verifier=PassingVerifier()
            )

    def test_22_exact_reference_has_no_latest_or_other_revision_fallback(self):
        artifact, _ = self.freeze_ready()
        resolved = self.store.resolve_exact_reference(
            f"{artifact.artifact_id}@1", verifier=PassingVerifier()
        )
        self.assertEqual(resolved.revision.control.revision, 1)
        with self.assertRaises(NotFoundError):
            self.store.resolve_exact_reference(
                f"{artifact.artifact_id}@2", verifier=PassingVerifier()
            )
        with self.assertRaises(ReferenceError):
            self.store.resolve_exact_reference(
                f"{artifact.artifact_id}@latest", verifier=PassingVerifier()
            )

    def test_23_freeze_and_resolve_fail_closed_without_verifier(self):
        artifact, stored = self.materialize(status="ready")
        with self.assertRaises(VerifierRequiredError):
            self.store.freeze_revision(artifact.artifact_id, 1)
        self.store.freeze_revision(
            artifact.artifact_id, 1, verifier=PassingVerifier(), now=FIXED_TIME
        )
        with self.assertRaises(VerifierRequiredError):
            self.store.resolve_exact_reference(f"{artifact.artifact_id}@1")

    def test_24_stale_and_rejected_verifiers_fail(self):
        artifact, _ = self.materialize(status="ready")
        with self.assertRaises(StaleVerificationError):
            self.store.freeze_revision(
                artifact.artifact_id, 1, verifier=StaleVerifier(), now=FIXED_TIME
            )
        with self.assertRaises(VerificationFailedError):
            self.store.freeze_revision(
                artifact.artifact_id, 1, verifier=RejectingVerifier(), now=FIXED_TIME
            )

    def test_25_passing_verifier_completes_freeze_and_resolve(self):
        artifact, control = self.freeze_ready()
        self.assertEqual(control.state, "frozen")
        result = self.store.resolve_exact_reference(
            f"{artifact.artifact_id}@1", verifier=PassingVerifier()
        )
        self.assertEqual(result.reference, f"{artifact.artifact_id}@1")

    def test_26_transaction_exception_leaves_no_partial_payload(self):
        artifact, control = self.allocate_open()
        payload = self.payload(
            artifact.artifact_id, control.revision, members=(self.member(),)
        )
        with mock.patch.object(
            self.store,
            "_insert_manifest_members",
            side_effect=sqlite3.IntegrityError("forced transaction failure"),
        ):
            with self.assertRaises(DatabaseError):
                self.store.write_open_revision(payload, expected_generation=0)
        with self.assertRaises(ControlReservationError):
            self.store.read_revision(artifact.artifact_id, control.revision)
        connection = sqlite3.connect(self.store.store_path)
        try:
            count = connection.execute(
                "SELECT COUNT(*) FROM payloads WHERE artifact_id = ?",
                (artifact.artifact_id,),
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(count, 0)

    def test_27_cli_uses_explicit_project_root_from_different_cwd(self):
        root = Path(self.temporary.name) / "cli-project"
        cwd = Path(self.temporary.name) / "other-cwd"
        root.mkdir()
        cwd.mkdir()
        script = REPOSITORY_ROOT / "scripts/sdlc_artifact_store.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--project-root",
                str(root),
                "--operation",
                "initialize",
            ],
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((root / ".sdlc/store.sqlite3").is_file())
        self.assertFalse((cwd / ".sdlc").exists())
        protocol = json.loads(result.stdout)
        self.assertTrue(protocol["ok"])
        self.assertEqual(result.stdout.count("\n"), 1)
        allocate = subprocess.run(
            [
                sys.executable,
                str(script),
                "--project-root",
                str(root),
                "--operation",
                "allocate_artifact",
                "--input",
                "-",
            ],
            cwd=cwd,
            input=json.dumps(
                {"artifact_type": "CTX", "now": "2026-08-30T09:10:11+00:00"}
            ),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(allocate.returncode, 0, allocate.stderr)
        allocated = json.loads(allocate.stdout)
        self.assertEqual(
            allocated["result"]["artifact_id"], "CTX-20260830091011-01"
        )
        self.assertFalse((cwd / ".sdlc").exists())

    def test_28_initialize_does_not_modify_root_gitignore(self):
        root = Path(self.temporary.name) / "gitignore-project"
        root.mkdir()
        root_ignore = root / ".gitignore"
        root_ignore.write_text("custom-rule\n", encoding="utf-8")
        ArtifactStore.open_read_write(root).initialize()
        self.assertEqual(root_ignore.read_text(encoding="utf-8"), "custom-rule\n")

    def test_29_runtime_has_no_third_party_or_network_install_code(self):
        allowed_roots = {
            "argparse",
            "base64",
            "contextlib",
            "dataclasses",
            "datetime",
            "hashlib",
            "json",
            "pathlib",
            "re",
            "sqlite3",
            "subprocess",
            "sys",
            "typing",
            "urllib",
            "errors",
            "models",
            "sqlite_store",
        }
        forbidden_text = ("urlopen(", "socket.", "requests.", "pip install", "subprocess.Popen")
        for path in (REPOSITORY_ROOT / "packages/sdlc_artifact_store").glob("*.py"):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            roots = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    roots.add(node.module.split(".", 1)[0])
            self.assertEqual(roots - allowed_roots, set(), path)
            for marker in forbidden_text:
                self.assertNotIn(marker, source, path)

    def test_30_external_imp_exact_id_and_revision_are_idempotent_or_conflict(self):
        with self.assertRaises(InvalidInputError):
            self.store.allocate_artifact("IMP", now=FIXED_TIME)
        claim = ClaimReservation("binding:IMP-001", "attempt-1", "owner-1")
        exact_id = "IMP-20260830091011-01"
        first = self.store.allocate_artifact(
            "IMP", external_artifact_id=exact_id, claim=claim, now=FIXED_TIME
        )
        repeated = self.store.allocate_artifact(
            "IMP", external_artifact_id=exact_id, claim=claim, now=FIXED_TIME
        )
        self.assertEqual(first, repeated)
        first_revision = self.store.allocate_revision(
            exact_id, external_revision=1, claim=claim, now=FIXED_TIME
        )
        repeated_revision = self.store.allocate_revision(
            exact_id, external_revision=1, claim=claim, now=FIXED_TIME
        )
        self.assertEqual(first_revision, repeated_revision)
        self.store.abandon_revision(exact_id, 1, reason="claim attempt ended")
        next_claim = ClaimReservation("binding:IMP-001", "attempt-2", "owner-2")
        same_lineage = self.store.allocate_artifact(
            "IMP", external_artifact_id=exact_id, claim=next_claim, now=FIXED_TIME
        )
        self.assertEqual(same_lineage.artifact_id, exact_id)
        next_revision = self.store.allocate_revision(
            exact_id, external_revision=2, claim=next_claim, now=FIXED_TIME
        )
        self.assertEqual(next_revision.revision, 2)
        with self.assertRaises(ConflictError):
            self.store.allocate_artifact(
                "IMP",
                external_artifact_id="IMP-20260830091011-02",
                claim=claim,
                now=FIXED_TIME,
            )
        other_claim = ClaimReservation("binding:IMP-002", "attempt-2", "owner-2")
        with self.assertRaises(ConflictError):
            self.store.allocate_revision(
                exact_id, external_revision=1, claim=other_claim, now=FIXED_TIME
            )
        with self.assertRaises(ConflictError):
            self.store.allocate_artifact(
                "IMP", external_artifact_id=exact_id, claim=other_claim, now=FIXED_TIME
            )

    def test_31_generation_conflict_prevents_last_write_wins(self):
        artifact, stored = self.materialize()
        updated = self.payload(
            artifact.artifact_id, 1, primary=b"updated", status="waiting_input"
        )
        self.store.write_open_revision(
            updated, expected_generation=stored.control.generation
        )
        with self.assertRaises(ConflictError):
            self.store.write_open_revision(
                self.payload(artifact.artifact_id, 1, primary=b"stale"),
                expected_generation=stored.control.generation,
            )
        self.assertEqual(self.store.read_revision(artifact.artifact_id, 1).payload.primary_blob, b"updated")

    def test_32_read_only_open_creates_no_sidecars_and_rejects_writes(self):
        artifact, _ = self.materialize()
        before = self.snapshot_files(self.project_root / ".sdlc")
        reader = ArtifactStore.open_read_only(self.project_root)
        reader.read_revision(artifact.artifact_id, 1)
        reader.verify_digest(artifact.artifact_id, 1)
        after = self.snapshot_files(self.project_root / ".sdlc")
        self.assertEqual(before, after)
        self.assertFalse(any(path.name.endswith(("-journal", "-wal", "-shm")) for path in (self.project_root / ".sdlc").iterdir()))
        with self.assertRaises(ReadOnlyError):
            reader.initialize()

    def test_33_tracked_runtime_content_fails_closed(self):
        root = Path(self.temporary.name) / "tracked-project"
        root.mkdir()
        subprocess.run(
            ["git", "init", str(root)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (root / ".sdlc").mkdir()
        (root / ".sdlc/tracked.txt").write_text("tracked\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(root), "add", ".sdlc/tracked.txt"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        store = ArtifactStore.open_read_write(root)
        with self.assertRaises(TrackedRuntimeContentError):
            store.initialize()
        self.assertFalse((root / ".sdlc/store.sqlite3").exists())
        self.assertFalse((root / ".sdlc/.gitignore").exists())

    def test_34_cli_freeze_without_verifier_returns_stable_json_error(self):
        artifact, _ = self.materialize(status="ready")
        input_path = Path(self.temporary.name) / "freeze.json"
        input_path.write_text(
            json.dumps({"artifact_id": artifact.artifact_id, "revision": 1}),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(REPOSITORY_ROOT / "scripts/sdlc_artifact_store.py"),
                "--project-root",
                str(self.project_root),
                "--operation",
                "freeze_revision",
                "--input",
                str(input_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        protocol = json.loads(result.stdout)
        self.assertEqual(result.returncode, 5)
        self.assertEqual(protocol["error"]["code"], "VERIFIER_REQUIRED")
        self.assertNotIn("Traceback", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
