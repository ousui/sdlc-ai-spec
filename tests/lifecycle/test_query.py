from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from packages.sdlc_artifact_store import (
    ArtifactStore,
    CanonicalManifest,
    CanonicalRevisionPayload,
    DomainVerification,
    compute_sha256,
)
from packages.sdlc_lifecycle import (
    LifecycleQueryService,
    LifecycleReferenceError,
    LifecycleStoreUnavailable,
)

FIXED = datetime(2026, 8, 31, 18, 0, tzinfo=timezone.utc)


class PassingVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="fixture authority",
        )


def gate_block(revision: int, result: str) -> str:
    check_result = "fail" if result == "fail" else ("pending" if result == "pending" else "pass")
    return (
        "## 门禁 Gate\n\n"
        "| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |\n"
        "|---|---|---|---|\n"
        f"| CORE-G-001 | identity | {check_result} | fixture |\n"
        f"| CORE-G-009 | final | {check_result} | fixture |\n\n"
        "| Evaluated Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Gate Result | Exception References | Evaluator | Evaluated At |\n"
        "|---|---|---|---|---|---|---|---|\n"
        f"| {revision} | sha256:{'a'*64} | fixture@sha256:{'b'*64} | sha256:{'c'*64} | {result} | None | fixture | 2026-08-31T18:00:00Z |\n"
    )


def artifact_blob(
    artifact_id: str,
    revision: int,
    artifact_type: str,
    status: str,
    *,
    context: str | None = None,
    inputs: tuple[str, ...] = (),
    gate: str = "pass",
    open_item: bool = False,
) -> bytes:
    if artifact_type == "CTX":
        front = (
            "---\n"
            "contract: sdlc-ai-spec/project-context/v1\n"
            f"id: {artifact_id}\n"
            f"revision: {revision}\n"
            f"status: {status}\n"
            "---\n"
        )
    else:
        input_lines = (
            "inputs: []\n"
            if not inputs
            else "inputs:\n" + "".join(f"  - {item}\n" for item in inputs)
        )
        front = (
            "---\n"
            "contract: sdlc-ai-spec/artifact/v1\n"
            f"phase: {artifact_type}\n"
            f"id: {artifact_id}\n"
            f"revision: {revision}\n"
            f"status: {status}\n"
            f"context: {context}\n"
            "profile: full\n"
            f"{input_lines}"
            "---\n"
        )
    open_table = (
        "## 待确认项 Open Items\n\n"
        "| ID | 所需输入或待确认决策 Needed Input or Decision | 预期来源 Expected Source | 被阻塞项 Blocked References | 状态 State | 解决结果或证据 Resolution or Evidence |\n"
        "|---|---|---|---|---|---|\n"
        "| OPI-001 | confirm scope | project owner | REQ-G-001 | open | N/A |\n\n"
        if open_item
        else
        "## 待确认项 Open Items\n\n"
        "| ID | 所需输入或待确认决策 Needed Input or Decision | 预期来源 Expected Source | 被阻塞项 Blocked References | 状态 State | 解决结果或证据 Resolution or Evidence |\n"
        "|---|---|---|---|---|---|\n"
        "| None | None | None | None | resolved | N/A |\n\n"
    )
    return (
        front
        + f"# {artifact_type} fixture\n\n"
        + open_table
        + gate_block(revision, gate)
    ).encode("utf-8")


class LifecycleQueryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()
        self.plugin = Path(self.temporary.name) / "plugin"
        (self.plugin / "skills/sdlc-000-ctx").mkdir(parents=True)
        (self.plugin / "skills/sdlc-000-ctx/SKILL.md").write_text("ctx")
        (self.plugin / "skills/sdlc-100-req").mkdir(parents=True)
        (self.plugin / "skills/sdlc-100-req/SKILL.md").write_text("req")
        self.store = ArtifactStore.open_read_write(self.root, clock=lambda: FIXED)
        self.store.initialize()

    def tearDown(self):
        self.temporary.cleanup()

    def persist(
        self,
        artifact_type: str,
        status: str,
        *,
        context: str | None = None,
        inputs: tuple[str, ...] = (),
        gate: str = "pass",
        state: str = "frozen",
        open_item: bool = False,
        base_revision: int | None = None,
        artifact_id: str | None = None,
    ) -> str:
        if artifact_id is None:
            artifact_id = self.store.allocate_artifact(
                artifact_type, now=FIXED
            ).artifact_id
        control = self.store.allocate_revision(
            artifact_id, base_revision=base_revision, now=FIXED
        )
        raw = artifact_blob(
            artifact_id,
            control.revision,
            artifact_type,
            status,
            context=context,
            inputs=inputs,
            gate=gate,
            open_item=open_item,
        )
        payload = CanonicalRevisionPayload(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            revision=control.revision,
            artifact_status=status,
            primary_blob=raw,
            primary_media_type="text/markdown",
            primary_sha256=compute_sha256(raw),
            members=(),
            manifest=CanonicalManifest(
                raw_bytes=b'{"local_members":[]}',
                media_type="application/json",
                local_members=(),
            ),
        )
        self.store.write_open_revision(
            payload, expected_generation=control.generation
        )
        if state == "frozen":
            self.store.freeze_revision(
                artifact_id,
                control.revision,
                verifier=PassingVerifier(),
                now=FIXED,
            )
        elif state == "abandoned":
            self.store.abandon_revision(
                artifact_id, control.revision, reason="fixture abandoned"
            )
        return f"{artifact_id}@{control.revision}"

    def service(self):
        return LifecycleQueryService(
            self.root,
            plugin_root=self.plugin,
            verifier_factory=lambda _: PassingVerifier(),
        )

    def test_missing_store_is_strictly_read_only(self):
        other = Path(self.temporary.name) / "missing"
        other.mkdir()
        with self.assertRaises(LifecycleStoreUnavailable):
            LifecycleQueryService(other)
        self.assertFalse((other / ".sdlc").exists())

    def test_lists_all_materialized_requirement_revisions_and_head(self):
        ctx = self.persist("CTX", "ready")
        first = self.persist("REQ", "ready", context=ctx)
        artifact_id = first.split("@", 1)[0]
        second = self.persist(
            "REQ",
            "ready",
            context=ctx,
            artifact_id=artifact_id,
            base_revision=1,
        )
        candidates = self.service().list_requirements()
        self.assertEqual([item.reference for item in candidates], [first, second])
        self.assertFalse(candidates[0].lineage_head)
        self.assertTrue(candidates[1].lineage_head)

    def test_ready_req_graph_has_context_edge_and_next_dsn(self):
        ctx = self.persist("CTX", "ready")
        req = self.persist("REQ", "ready", context=ctx)
        projection = self.service().inspect_requirement(req)
        self.assertEqual(projection.overall_state, "ready_for_next_phase")
        self.assertEqual({item.reference for item in projection.nodes}, {ctx, req})
        self.assertEqual(
            [(item.source_reference, item.target_reference, item.relation) for item in projection.edges],
            [(ctx, req, "context")],
        )
        self.assertEqual(projection.frontier, (req,))
        self.assertEqual(projection.next_actions[0].phase, "DSN")
        self.assertFalse(projection.next_actions[0].skill_available)
        self.assertIsNone(projection.next_actions[0].command)

    def test_open_item_is_action_required_not_authority(self):
        ctx = self.persist("CTX", "ready")
        req = self.persist(
            "REQ",
            "waiting_input",
            context=ctx,
            gate="pending",
            state="open",
            open_item=True,
        )
        projection = self.service().inspect_requirement(req)
        self.assertEqual(projection.overall_state, "action_required")
        self.assertEqual(projection.nodes[-1].authority_state, "not_applicable")
        self.assertTrue(any(item["code"] == "OPEN_ITEM" for item in projection.blockers))
        self.assertEqual(projection.next_actions[0].phase, "REQ")
        self.assertTrue(projection.next_actions[0].skill_available)

    def test_missing_declared_dependency_is_blocked(self):
        ctx = self.persist("CTX", "ready")
        req = self.persist(
            "REQ",
            "ready",
            context=ctx,
            inputs=("DSN-20260831180000-99@1",),
        )
        projection = self.service().inspect_requirement(req)
        self.assertEqual(projection.overall_state, "blocked")
        self.assertTrue(
            any(item["code"] == "DEPENDENCY_MISSING" for item in projection.blockers)
        )

    def test_abandoned_revision_is_not_authority(self):
        ctx = self.persist("CTX", "ready")
        req = self.persist(
            "REQ",
            "waiting_input",
            context=ctx,
            gate="pending",
            state="abandoned",
            open_item=True,
        )
        projection = self.service().inspect_requirement(req)
        self.assertEqual(projection.overall_state, "blocked")
        self.assertTrue(
            any(item["code"] == "REVISION_ABANDONED" for item in projection.blockers)
        )

    def test_inspect_rejects_member_or_symbolic_reference(self):
        with self.assertRaises(LifecycleReferenceError):
            self.service().inspect_requirement("REQ-20260831180000-01@1#AC-001")
        with self.assertRaises(LifecycleReferenceError):
            self.service().inspect_requirement("REQ-20260831180000-01@latest")

    def test_overview_selects_only_one_active_requirement(self):
        ctx = self.persist("CTX", "ready")
        req = self.persist("REQ", "ready", context=ctx)
        overview = self.service().project_overview()
        self.assertEqual(overview.state, "single_requirement")
        self.assertEqual(overview.selected_requirement, req)

    def test_overview_requires_selection_for_multiple_requirements(self):
        ctx = self.persist("CTX", "ready")
        self.persist("REQ", "ready", context=ctx)
        self.persist("REQ", "ready", context=ctx)
        overview = self.service().project_overview()
        self.assertEqual(overview.state, "selection_required")
        self.assertIsNone(overview.selected_requirement)
        self.assertEqual(overview.next_actions[0].code, "SELECT_REQUIREMENT")


if __name__ == "__main__":
    unittest.main()
