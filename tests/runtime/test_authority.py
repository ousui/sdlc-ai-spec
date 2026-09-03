import tempfile
import unittest
from pathlib import Path

from packages.sdlc_artifact_store import (
    CanonicalManifest,
    CanonicalRevisionPayload,
    ClaimReservation,
    RevisionControlRecord,
    StoredRevision,
    compute_sha256,
)
from packages.sdlc_runtime import (
    FrozenArtifactAuthorityVerifier,
    FrozenAuthorityVerificationError,
)
from packages.sdlc_runtime.canonical import (
    compute_check_set_result_digest,
    compute_control_input_digest,
    parse_canonical_artifact,
    sha256_bytes,
)
from packages.sdlc_runtime.authority import (
    DELEGATED_EXCLUDED_AUTHORITY, DELEGATED_INDEPENDENCE,
)


ARTIFACT_ID = "REQ-20260830120000-01"
REFERENCE = ARTIFACT_ID + "@1"
EVALUATION_SET = (
    "docs/v1.1/core-spec.md@sha256:" + "a" * 64
    + ", docs/v1.1/100-req-spec.md@sha256:" + "b" * 64
)


class FrozenAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.authority_dir = self.root / ".sdlc" / "authority"
        self.authority_dir.mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def _authority(
        self,
        mode: str,
        *,
        control_digest="",
        check_digest="",
        artifact_reference=REFERENCE,
        reviewed_executor="builder-1",
    ) -> str:
        if mode == "delegated":
            basis_raw = b"reviewer-1 may confirm contract compliance\n"
            basis = self.authority_dir / "policy.md"
            basis.write_bytes(basis_raw)
            basis_ref = ".sdlc/authority/policy.md@" + sha256_bytes(basis_raw)
            raw = (
                "---\n"
                "contract: sdlc-ai-spec/final-confirmation-authority/v1\n"
                f"artifact: {artifact_reference}\n"
                "decision: approved\n"
                "decided_at: 2026-08-30T12:00:00Z\n"
                "---\n\n"
                "| Delegation Basis | Reviewer Identity | Reviewer Role | Reviewed Executor Identity | Independence | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Excluded Authority |\n"
                "|---|---|---|---|---|---|---|---|---|\n"
                f"| {basis_ref} | reviewer-1 | Delegated Independent Reviewer | {reviewed_executor} | "
                f"{DELEGATED_INDEPENDENCE} | {control_digest} | {EVALUATION_SET} | "
                f"{check_digest} | {DELEGATED_EXCLUDED_AUTHORITY} |\n"
            ).encode("utf-8")
        else:
            raw = (
                "Human approval for "
                + REFERENCE
                + "\nApproved by product-owner-1 at 2026-08-30T12:00:00Z\n"
            ).encode("utf-8")
        target = self.authority_dir / (
            "delegated.md" if mode == "delegated" else "human.md"
        )
        target.write_bytes(raw)
        relative = target.relative_to(self.root).as_posix()
        return f"{relative}@{sha256_bytes(raw)}"

    def _blob(
        self,
        mode: str = "human",
        status: str = "ready",
        *,
        artifact_id=ARTIFACT_ID,
        phase="REQ",
        reviewed_executor="builder-1",
    ) -> bytes:
        reference = artifact_id + "@1"
        prefix = (
            "---\n"
            "contract: sdlc-ai-spec/artifact/v1\n"
            f"phase: {phase}\n"
            f"id: {artifact_id}\n"
            "revision: 1\n"
            f"status: {status}\n"
            "context: CTX-20260830110000-01@1\n"
            "profile: full\n"
            "inputs: []\n"
            "---\n"
            "# Requirement\n\n"
            "## 摘要 Summary\n\n"
            "A stable requirement.\n\n"
            "## 门禁 Gate\n\n"
            "| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |\n"
            "|---|---|---|---|\n"
            "| CORE-G-001 | identity | pass | stable |\n"
            "| CORE-G-009 | final | pass | authority |\n"
            "| REQ-G-001 | source | pass | stable |\n\n"
        )
        preliminary = prefix.encode("utf-8")
        control_digest = compute_control_input_digest(preliminary)
        check_digest = compute_check_set_result_digest(
            parse_canonical_artifact(preliminary)
        )
        authority_ref = self._authority(
            mode,
            control_digest=control_digest,
            check_digest=check_digest,
            artifact_reference=reference,
            reviewed_executor=reviewed_executor,
        )
        role = (
            "Delegated Independent Reviewer"
            if mode == "delegated"
            else "Product Owner"
        )
        confirmer = "reviewer-1" if mode == "delegated" else "product-owner-1"
        gate_result = "pass" if status == "ready" else "pass_with_exception"
        exceptions = "None" if status == "ready" else f"{reference}#EX-001"
        return (
            prefix
            + "| Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Result | Mode | Confirmer | Role | Authority Reference | Accepted Exception References | Confirmed At |\n"
            + "|---|---|---|---|---|---|---|---|---|---|---|\n"
            + f"| 1 | {control_digest} | {EVALUATION_SET} | {check_digest} | approved | {mode} | {confirmer} | {role} | {authority_ref} | {exceptions} | 2026-08-30T12:00:00Z |\n\n"
            + "| Evaluated Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Gate Result | Exception References | Evaluator | Evaluated At |\n"
            + "|---|---|---|---|---|---|---|---|\n"
            + f"| 1 | {control_digest} | {EVALUATION_SET} | {check_digest} | {gate_result} | {exceptions} | evaluator-1 | 2026-08-30T12:00:01Z |\n"
        ).encode("utf-8")

    def _stored(
        self,
        blob: bytes,
        status: str = "ready",
        *,
        artifact_id=ARTIFACT_ID,
        artifact_type="REQ",
        claim=None,
    ) -> StoredRevision:
        control = RevisionControlRecord(
            artifact_id=artifact_id,
            revision=1,
            state="frozen",
            base_revision=None,
            allocated_at="2026-08-30T11:59:00+00:00",
            frozen_at="2026-08-30T12:00:02+00:00",
            abandon_reason=None,
            generation=2,
            materialized=True,
            claim=claim,
        )
        payload = CanonicalRevisionPayload(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            revision=1,
            artifact_status=status,
            primary_blob=blob,
            primary_media_type="text/markdown",
            primary_sha256=compute_sha256(blob),
            members=(),
            manifest=CanonicalManifest(
                raw_bytes=b'{"local_members":[]}',
                media_type="application/json",
                local_members=(),
            ),
        )
        return StoredRevision(
            control=control,
            payload=payload,
            verification_binding="sha256:" + "d" * 64,
        )

    def test_valid_human_authority(self):
        stored = self._stored(self._blob())
        result = FrozenArtifactAuthorityVerifier(self.root).verify(REFERENCE, stored)
        self.assertTrue(result.approved)
        self.assertEqual(result.payload_binding, stored.verification_binding)

    def test_valid_delegated_authority(self):
        stored = self._stored(self._blob(mode="delegated"))
        result = FrozenArtifactAuthorityVerifier(self.root).verify(REFERENCE, stored)
        self.assertTrue(result.approved)

    def test_delegated_imp_authority_must_bind_persisted_claim_owner(self):
        artifact_id = "IMP-20260830120000-01"
        reference = artifact_id + "@1"
        blob = self._blob(
            mode="delegated",
            artifact_id=artifact_id,
            phase="IMP",
            reviewed_executor="different-builder",
        )
        stored = self._stored(
            blob,
            artifact_id=artifact_id,
            artifact_type="IMP",
            claim=ClaimReservation("lineage-1", "attempt-1", "builder-1"),
        )
        with self.assertRaises(FrozenAuthorityVerificationError):
            FrozenArtifactAuthorityVerifier(self.root).verify(reference, stored)

    def test_ready_with_exception_requires_matching_sets(self):
        stored = self._stored(
            self._blob(status="ready_with_exception"),
            status="ready_with_exception",
        )
        result = FrozenArtifactAuthorityVerifier(self.root).verify(REFERENCE, stored)
        self.assertTrue(result.approved)

    def test_tampered_content_invalidates_control_digest(self):
        blob = self._blob().replace(
            b"A stable requirement.", b"A changed requirement."
        )
        with self.assertRaises(FrozenAuthorityVerificationError):
            FrozenArtifactAuthorityVerifier(self.root).verify(
                REFERENCE, self._stored(blob)
            )

    def test_status_gate_mismatch_is_rejected(self):
        blob = self._blob(status="ready_with_exception")
        with self.assertRaises(FrozenAuthorityVerificationError):
            FrozenArtifactAuthorityVerifier(self.root).verify(
                REFERENCE, self._stored(blob, status="ready")
            )

    def test_missing_authority_file_is_rejected(self):
        blob = self._blob()
        for path in self.authority_dir.iterdir():
            path.unlink()
        with self.assertRaises(FrozenAuthorityVerificationError):
            FrozenArtifactAuthorityVerifier(self.root).verify(
                REFERENCE, self._stored(blob)
            )


if __name__ == "__main__":
    unittest.main()
