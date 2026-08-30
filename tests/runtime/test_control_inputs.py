import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from packages.sdlc_artifact_store import (
    ArtifactStore,
    CanonicalManifest,
    CanonicalRevisionPayload,
    DomainVerification,
    compute_sha256,
)
from packages.sdlc_runtime import ControlInputError, ControlInputResolver
from packages.sdlc_runtime.canonical import (
    compute_check_set_result_digest,
    compute_control_input_digest,
    parse_canonical_artifact,
    sha256_bytes,
)

FIXED_TIME = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
EVALUATION_SET = (
    "docs/v1.1/core-spec.md@sha256:" + "a" * 64
    + ", docs/v1.1/artifact-store-spec.md@sha256:" + "b" * 64
)


class PassingVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="fixture authority",
        )


class ControlInputResolverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ArtifactStore.open_read_write(self.root)
        self.store.initialize()
        authority_dir = self.root / ".sdlc" / "authority"
        authority_dir.mkdir()
        self.authority_file = authority_dir / "human.md"
        self.authority_file.write_text(
            "Approved by fixture-owner at 2026-08-30T12:00:00Z\n",
            encoding="utf-8",
        )
        self.authority_reference = (
            self.authority_file.relative_to(self.root).as_posix()
            + "@"
            + sha256_bytes(self.authority_file.read_bytes())
        )
        self.resolver = ControlInputResolver(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def _primary(self, artifact_id, phase, body, phase_check):
        prefix = (
            "---\n"
            "contract: sdlc-ai-spec/artifact/v1\n"
            f"phase: {phase}\n"
            f"id: {artifact_id}\n"
            "revision: 1\n"
            "status: ready\n"
            "context: CTX-20260830110000-01@1\n"
            "profile: full\n"
            "inputs: []\n"
            "---\n"
            f"# {phase} Fixture\n\n"
            + body
            + "\n## 门禁 Gate\n\n"
            "| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |\n"
            "|---|---|---|---|\n"
            "| CORE-G-001 | identity | pass | stable |\n"
            "| CORE-G-009 | final | pass | authority |\n"
            f"| {phase_check} | phase | pass | stable |\n\n"
        )
        raw_prefix = prefix.encode("utf-8")
        control_digest = compute_control_input_digest(raw_prefix)
        check_digest = compute_check_set_result_digest(
            parse_canonical_artifact(raw_prefix)
        )
        return (
            prefix
            + "| Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Result | Mode | Confirmer | Role | Authority Reference | Accepted Exception References | Confirmed At |\n"
            + "|---|---|---|---|---|---|---|---|---|---|---|\n"
            + f"| 1 | {control_digest} | {EVALUATION_SET} | {check_digest} | approved | human | fixture-owner | Product Owner | {self.authority_reference} | None | 2026-08-30T12:00:00Z |\n\n"
            + "| Evaluated Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Gate Result | Exception References | Evaluator | Evaluated At |\n"
            + "|---|---|---|---|---|---|---|---|\n"
            + f"| 1 | {control_digest} | {EVALUATION_SET} | {check_digest} | pass | None | evaluator-1 | 2026-08-30T12:00:01Z |\n"
        ).encode("utf-8")

    def _persist(self, phase, body, phase_check):
        allocation = self.store.allocate_artifact(phase, now=FIXED_TIME)
        control = self.store.allocate_revision(
            allocation.artifact_id, now=FIXED_TIME
        )
        primary = self._primary(
            allocation.artifact_id, phase, body, phase_check
        )
        payload = CanonicalRevisionPayload(
            artifact_id=allocation.artifact_id,
            artifact_type=phase,
            revision=1,
            artifact_status="ready",
            primary_blob=primary,
            primary_media_type="text/markdown",
            primary_sha256=compute_sha256(primary),
            members=(),
            manifest=CanonicalManifest(
                raw_bytes=b'{"local_members":[]}',
                media_type="application/json",
                local_members=(),
            ),
        )
        self.store.write_open_revision(payload, expected_generation=control.generation)
        self.store.freeze_revision(
            allocation.artifact_id,
            1,
            verifier=PassingVerifier(),
            now=FIXED_TIME,
        )
        return allocation.artifact_id + "@1"

    def _vfy(self, return_phase="REQ"):
        body = (
            "## 失败与返回 Failures and Returns\n\n"
            "| ID | Return Phase | IMP Binding Reference | Target References | Method References | Subject References | 已观察缺口 Observed Gap | 必须达到的结果 Required Outcome | Evidence References |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            f"| RET-001 | {return_phase} | {'IMP-20260830113000-01@1' if return_phase == 'IMP' else 'N/A'} | REQ-20260830100000-01@1#AC-001 | VFM-001 | IMP-20260830113000-01@1 | expected behavior not met | restore accepted behavior | EVD-001 |\n"
        )
        return self._persist("VFY", body, "VFY-G-001")

    def _rls(self, rli_follow_up="return_req", rcf_follow_up="return_req"):
        body = (
            "## 发版项 Release Items\n\n"
            "| ID | 变更或操作 Change or Action | 来源引用 Source References | 前置条件或注意事项 Prerequisite or Note | 执行方 Executor | 结果 Result | Follow-up Disposition | 证据引用 Evidence References |\n"
            "|---|---|---|---|---|---|---|---|\n"
            f"| RLI-001 | deploy release | IMP-20260830113000-01@1 | none | pipeline-1 | fail | {rli_follow_up} | EVD-001 |\n\n"
            "## 上线后确认 Post-release Confirmation\n\n"
            "| ID | 来源引用 Source References | 确认项 Confirmation | 预期 Expected | 执行方 Executor | Evidence 要求及获取方式 Evidence Requirement and Acquisition | 实际 Observed | 结果 Result | Follow-up Disposition | 证据引用 Evidence References |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            f"| RCF-001 | REQ-20260830100000-01@1#AC-001 | confirm behavior | accepted behavior | operator-1 | target observation | behavior failed | fail | {rcf_follow_up} | EVD-002 |\n"
        )
        return self._persist("RLS", body, "RLS-G-001")

    def test_resolve_vfy_return_for_req(self):
        base = self._vfy()
        result = self.resolver.resolve_for_phase(
            self.store, base + "#RET-001", "REQ"
        )
        self.assertEqual(result.return_phase, "REQ")
        self.assertEqual(result.observed_gap, "expected behavior not met")
        self.assertEqual(result.evidence_references, ("EVD-001",))

    def test_vfy_return_phase_mismatch_fails(self):
        base = self._vfy()
        with self.assertRaises(ControlInputError):
            self.resolver.resolve_for_phase(
                self.store, base + "#RET-001", "DSN"
            )

    def test_resolve_rls_release_item_issue(self):
        base = self._rls()
        result = self.resolver.resolve_for_phase(
            self.store, base + "#RLI-001", "REQ"
        )
        self.assertEqual(result.item_kind, "release_item")
        self.assertEqual(result.result, "fail")
        self.assertEqual(result.follow_up_disposition, "return_req")

    def test_resolve_rls_confirmation_issue(self):
        base = self._rls()
        result = self.resolver.resolve_for_phase(
            self.store, base + "#RCF-001", "REQ"
        )
        self.assertEqual(result.item_kind, "confirmation")
        self.assertEqual(result.expected, "accepted behavior")
        self.assertEqual(result.observed, "behavior failed")

    def test_rls_follow_up_mismatch_fails(self):
        base = self._rls(rli_follow_up="return_dsn")
        with self.assertRaises(ControlInputError):
            self.resolver.resolve_for_phase(
                self.store, base + "#RLI-001", "REQ"
            )

    def test_reference_must_name_an_exact_item(self):
        base = self._vfy()
        with self.assertRaises(ControlInputError):
            self.resolver.resolve_for_phase(self.store, base, "REQ")
        with self.assertRaises(ControlInputError):
            self.resolver.resolve_for_phase(
                self.store, base + "#RLI-001", "REQ"
            )


if __name__ == "__main__":
    unittest.main()
