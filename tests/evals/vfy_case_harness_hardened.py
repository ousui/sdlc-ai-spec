"""Hardened VFY-E001..080 Oracle extensions for Web Review repairs."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/sdlc-500-vfy/scripts"
for entry in (ROOT, SCRIPTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from tests.evals import vfy_case_harness as legacy  # noqa: E402
from tests.skill_vfy.support import (  # noqa: E402
    SUBJECT,
    VFO_VER,
    delegated_confirmation,
    human_confirmation,
    persistent_authority_candidate,
    persistent_passing_fixture,
    valid_candidate,
)
from packages.sdlc_artifact_store import (  # noqa: E402
    ArtifactStore,
    CanonicalManifest,
    CanonicalRevisionPayload,
    DomainVerification,
    compute_sha256,
)
from packages.sdlc_runtime import ControlInputError, ControlInputResolver  # noqa: E402
from packages.sdlc_runtime.canonical import (  # noqa: E402
    compute_check_set_result_digest,
    compute_control_input_digest,
    parse_canonical_artifact,
    sha256_bytes,
)
from vfy_builder import build_state  # noqa: E402
from vfy_common import VfyError  # noqa: E402
from vfy_executor import execute_method  # noqa: E402
from vfy_handler import VfyHandler  # noqa: E402
from vfy_release import build_release_candidate  # noqa: E402


_CONTROL_TIME = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
_EVALUATION_SET = (
    "docs/v1.1/core-spec.md@sha256:" + "a" * 64
    + ", docs/v1.1/artifact-store-spec.md@sha256:" + "b" * 64
)


class _PassingControlVerifier:
    def verify(self, reference, revision):
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="frozen control fixture",
        )


def _control_primary(
    root: Path,
    artifact_id: str,
    phase: str,
    body: str,
    phase_check: str,
) -> bytes:
    authority_dir = root / ".sdlc/authority"
    authority_dir.mkdir(parents=True, exist_ok=True)
    authority_file = authority_dir / f"{phase.lower()}-control-owner.md"
    authority_file.write_text(
        "Approved by control-fixture-owner at 2026-09-04T12:00:00Z\n",
        encoding="utf-8",
    )
    authority_reference = (
        authority_file.relative_to(root).as_posix()
        + "@"
        + sha256_bytes(authority_file.read_bytes())
    )
    prefix = (
        "---\n"
        "contract: sdlc-ai-spec/artifact/v1\n"
        f"phase: {phase}\n"
        f"id: {artifact_id}\n"
        "revision: 1\n"
        "status: ready\n"
        f"context: {legacy.CTX}\n"
        "profile: full\n"
        "inputs: []\n"
        "---\n"
        f"# {phase} Control Fixture\n\n"
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
    check_digest = compute_check_set_result_digest(parse_canonical_artifact(raw_prefix))
    return (
        prefix
        + "| Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Result | Mode | Confirmer | Role | Authority Reference | Accepted Exception References | Confirmed At |\n"
        + "|---|---|---|---|---|---|---|---|---|---|---|\n"
        + f"| 1 | {control_digest} | {_EVALUATION_SET} | {check_digest} | approved | human | control-fixture-owner | Product Owner | {authority_reference} | None | 2026-09-04T12:00:00Z |\n\n"
        + "| Evaluated Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Gate Result | Exception References | Evaluator | Evaluated At |\n"
        + "|---|---|---|---|---|---|---|---|\n"
        + f"| 1 | {control_digest} | {_EVALUATION_SET} | {check_digest} | pass | None | evaluator-1 | 2026-09-04T12:00:01Z |\n"
    ).encode("utf-8")


def _persist_control_authority(
    root: Path,
    kind: str,
    *,
    return_phase: str = "IMP",
    imp_binding: str | None = None,
    required_outcome: str = "current Subject restores exact result",
):
    store = ArtifactStore.open_read_write(root)
    store.initialize()
    if kind == "vfy":
        phase = "VFY"
        binding = imp_binding or (legacy.WI if return_phase == "IMP" else "N/A")
        body = (
            "## 失败与返回 Failures and Returns\n\n"
            "| ID | Return Phase | IMP Binding Reference | Target References | Method References | Subject References | 已观察缺口 Observed Gap | 必须达到的结果 Required Outcome | Evidence References |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            f"| RET-001 | {return_phase} | {binding} | {VFO_VER} | VFM-001 | {SUBJECT} | old Subject lacks required result | {required_outcome} | EVD-001 |\n"
        )
        item_id = "RET-001"
        phase_check = "VFY-G-001"
    else:
        phase = "RLS"
        body = (
            "## 发版项 Release Items\n\n"
            "| ID | 变更或操作 Change or Action | 来源引用 Source References | 前置条件或注意事项 Prerequisite or Note | 执行方 Executor | 结果 Result | Follow-up Disposition | 证据引用 Evidence References |\n"
            "|---|---|---|---|---|---|---|---|\n"
            f"| RLI-001 | current Subject must restore exact result | {SUBJECT} | none | pipeline-1 | fail | return_imp | EVD-001 |\n"
        )
        item_id = "RLI-001"
        phase_check = "RLS-G-001"
    allocation = store.allocate_artifact(phase, now=_CONTROL_TIME)
    control = store.allocate_revision(allocation.artifact_id, now=_CONTROL_TIME)
    primary = _control_primary(root, allocation.artifact_id, phase, body, phase_check)
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
    store.write_open_revision(payload, expected_generation=control.generation)
    store.freeze_revision(
        allocation.artifact_id,
        1,
        verifier=_PassingControlVerifier(),
        now=_CONTROL_TIME,
    )
    reference = f"{allocation.artifact_id}@1#{item_id}"
    resolver = ControlInputResolver(root)
    resolved = (
        resolver.resolve_vfy_return(store, reference, return_phase)
        if kind == "vfy"
        else resolver.resolve_rls_issue(store, reference, "return_imp")
    )
    authority = asdict(resolved)
    authority["authority_verified"] = True
    return reference, authority


def expect_error(code, operation):
    try:
        operation()
    except VfyError as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}: {exc}") from exc
        return {"error": exc.code}
    raise AssertionError(f"expected {code}, operation succeeded")


def expect_control_error(operation):
    try:
        operation()
    except ControlInputError as exc:
        return {"error": exc.code}
    raise AssertionError("expected CONTROL_INPUT_INVALID, operation succeeded")


def _real_cli_create(root: Path, *, command: str | None):
    candidate = persistent_authority_candidate(root)
    arguments = [] if command is None else [command]
    arguments.extend(["-p", str(root)])
    for reference in (
        candidate["scope"]["reference"],
        *(item["reference"] for item in candidate["subjects"]),
    ):
        arguments.extend(["-i", reference])
    result, _ = legacy._RUNTIME.run_cli(
        arguments,
        {
            "candidate": candidate,
            "persist": True,
            "run_automated": True,
        },
    )
    state = result["result"]["state"]
    if not state["authority_compiled"]:
        raise AssertionError("real CLI did not retain compiled Authority")
    return state, candidate


def _command_method(root: Path, *, should_pass: bool):
    fixture = root / "test_vfy_command_fixture.py"
    assertion = "self.assertTrue(True)" if should_pass else "self.fail('expected failure')"
    fixture.write_text(
        "import unittest\n\n"
        "class CommandFixture(unittest.TestCase):\n"
        "    def test_result(self):\n"
        f"        {assertion}\n",
        encoding="utf-8",
    )
    candidate = valid_candidate()
    candidate["methods"][0]["procedure"] = {
        "kind": "command",
        "argv": ["python3", "-m", "unittest", "test_vfy_command_fixture"],
        "policy": "deterministic-test-v1",
        "workspace": "isolated-copy",
        "network": "disabled",
        "timeout_seconds": 30,
        "max_output_bytes": 65536,
    }
    return build_state(candidate)["methods"][0]


def _command_result(root: Path, *, should_pass: bool):
    method = _command_method(root, should_pass=should_pass)
    return execute_method(
        method,
        project_root=root,
        evidence_sequence=1,
        allow_commands=True,
    )


def _exception(
    *,
    scope: list[str],
    downstream: str = "RLS records the accepted risk",
) -> dict[str, object]:
    return {
        "id": "EX-001",
        "state": "active",
        "origin_reference": "DSN-20260904100500-01@1#EX-001",
        "scope": scope,
        "reason": "explicit bounded exception",
        "known_risk": "known residual risk",
        "compensating_control": "monitor exact release target",
        "approval": "Product Owner at 2026-09-04T12:00:00Z",
        "revisit_condition": "next release",
        "downstream_obligation": downstream,
        "resolution_references": [],
        "authority_verified": True,
        "accepts_product_failure": "product_result:fail" in scope,
    }


def _finalized_exception_state(
    root: Path,
    *,
    rls_applicability: str,
    waive_method: bool,
) -> dict[str, object]:
    candidate = valid_candidate()
    candidate["rls_applicability"] = rls_applicability
    if waive_method:
        exception = _exception(scope=["VFM-001"])
        candidate["methods"][0].update(
            disposition="waived",
            exception_reference=exception["origin_reference"],
        )
    else:
        exception = _exception(scope=["phase:RLS"])
    candidate["exceptions"] = [exception]
    handler = VfyHandler(root)
    opened = handler.create(
        candidate,
        persist=False,
        run_automated=True,
        allow_commands=False,
        finalize=False,
    )["state"]
    return handler.run_state(
        opened,
        method_ids=[],
        allow_commands=False,
        finalize=True,
        confirmation=human_confirmation(root, opened),
    )["state"]


def _control_candidate(root: Path, kind: str, **authority_options):
    candidate = valid_candidate()
    candidate["subjects"][0]["reference"] = (
        candidate["subjects"][0]["imp_revision_reference"] + "/RESULT-RES-001"
    )
    current_subject = candidate["subjects"][0]["reference"]
    for method in candidate["methods"]:
        method["subject_references"] = [current_subject]
    control, authority = _persist_control_authority(
        root, kind, **authority_options
    )
    candidate["control_inputs"] = [control]
    candidate["control_authorities"] = [authority]
    candidate["methods"][0]["obligation_references"].append(control)
    candidate["required_obligation_references"].append(control)
    return candidate, control


def _resolved_control(root: Path, kind: str):
    candidate, control = _control_candidate(root, kind)
    handler = VfyHandler(root)
    opened = handler.create(
        candidate,
        persist=False,
        run_automated=True,
        finalize=False,
    )["state"]
    result = next(item for item in opened["method_results"] if item["method_id"] == "VFM-001")
    target = next(item for item in opened["target_conclusions"] if item["target_reference"] == VFO_VER)
    if result["result"] != "pass" or target["conclusion"] != "pass":
        raise AssertionError("control recovery Method/Target did not pass")
    opened["control_resolutions"] = [
        {
            "control_reference": control,
            "method_references": ["VFM-001"],
            "target_references": [VFO_VER],
            "evidence_references": list(result["evidence_references"]),
        }
    ]
    opened = handler.run_state(
        opened,
        method_ids=[],
        allow_commands=False,
        finalize=False,
    )["state"]
    final = handler.run_state(
        opened,
        method_ids=[],
        allow_commands=False,
        finalize=True,
        confirmation=delegated_confirmation(root, opened),
    )["state"]
    if final["control_resolutions"][0]["status"] != "resolved":
        raise AssertionError("control recovery did not derive resolved status")
    return {"control": control, "status": "resolved"}


def _override(number: int, root: Path):
    if number == 1:
        state, _ = _real_cli_create(root, command=None)
        if any(item["result"] != "pass" for item in state["method_results"]):
            raise AssertionError("bare auto CLI did not run safe Methods")
        return {"authority_compiled": True, "operation": "auto"}
    if number == 3:
        state, candidate = _real_cli_create(root, command="create")
        if (
            state["scope"]["reference"] != candidate["scope"]["reference"]
            or state["subjects"] != candidate["subjects"]
            or set(state["input_references"])
            != set(state["owner_artifact_inputs"])
        ):
            raise AssertionError("repeatable CLI inputs were not classified exactly")
        return {"authority_compiled": True, "inputs": state["input_references"]}
    if number in {6, 76}:
        state, _ = persistent_passing_fixture(root)
        before = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
            and ".git" not in path.relative_to(root).parts
            and "__pycache__" not in path.relative_to(root).parts
        }
        checked = VfyHandler(root).check(reference=state["artifact"]["reference"])
        after = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
            and ".git" not in path.relative_to(root).parts
            and "__pycache__" not in path.relative_to(root).parts
        }
        if before != after or checked["state"] != state:
            raise AssertionError("exact persisted Reference check mutated bytes")
        return {"digest_unchanged": True}
    if number == 10:
        state, candidate = _real_cli_create(root, command="create")
        scope = state["scope"]
        if (
            scope["reference"] != candidate["scope"]["reference"]
            or scope["delivery_scope"] != sorted(candidate["scope"]["delivery_scope"])
            or scope["imp_work_items"] != candidate["scope"]["imp_work_items"]
        ):
            raise AssertionError("compiler selected a partial PLN Scope")
        return {"scope": scope["reference"], "work_items": scope["imp_work_items"]}
    if number == 15:
        state, candidate = _real_cli_create(root, command="create")
        if state["subjects"] != candidate["subjects"] or not all(
            item["current_valid"]
            and item["dependency_chain_valid"]
            and item["claim_state"] == "completed"
            and item["imp_revision_state"] == "frozen"
            for item in state["subjects"]
        ):
            raise AssertionError("current completed IMP chain was not discovered")
        return {"subjects": [item["reference"] for item in state["subjects"]]}
    if number == 18:
        candidate = persistent_authority_candidate(root)
        exact_subject = candidate["subjects"][0]["reference"]
        candidate["subjects"] = []
        return expect_error(
            "VFY_INPUT_AUTHORITY_MISMATCH",
            lambda: legacy._RUNTIME.run_cli(
                [
                    "create",
                    "-p",
                    str(root),
                    "-i",
                    candidate["scope"]["reference"],
                    "-i",
                    exact_subject,
                ],
                {"candidate": candidate, "persist": True},
            ),
        )
    if number == 41:
        row, evidence = _command_result(root, should_pass=True)
        if row["result"] != "pass" or evidence["result"] != "pass":
            raise AssertionError("safe isolated command did not produce Evidence")
        return row
    if number == 42:
        candidate = valid_candidate()
        candidate["methods"][0]["procedure"] = {
            "kind": "command",
            "argv": ["pip", "install", "x"],
            "policy": "deterministic-test-v1",
            "workspace": "isolated-copy",
            "network": "disabled",
        }
        method = build_state(candidate)["methods"][0]
        return expect_error(
            "VFY_METHOD_NOT_READY",
            lambda: execute_method(
                method,
                project_root=root,
                evidence_sequence=1,
                allow_commands=True,
            ),
        )
    if number == 46:
        row, evidence = _command_result(root, should_pass=False)
        if row["result"] != "fail" or evidence["result"] != "fail":
            raise AssertionError("command exit failure was hidden")
        return row
    if number in {56, 57, 58, 59}:
        phase = {56: "IMP", 57: "REQ", 58: "DSN", 59: "PLN"}[number]
        control, authority = _persist_control_authority(
            root, "vfy", return_phase=phase
        )
        expected_binding = legacy.WI if phase == "IMP" else "N/A"
        if (
            authority["return_phase"] != phase
            or authority["imp_binding_reference"] != expected_binding
        ):
            raise AssertionError("frozen Return routed to the wrong authority")
        return {"control": control, "return_phase": phase}
    if number == 60:
        return expect_control_error(
            lambda: _persist_control_authority(
                root, "vfy", required_outcome=""
            )
        )
    if number == 61:
        candidate, control = _control_candidate(root, "vfy")
        state = VfyHandler(root).create(
            candidate,
            persist=False,
            run_automated=False,
        )["state"]
        checked = legacy.verify_state(state, finalizing=False)
        if control not in checked["unresolved_controls"]:
            raise AssertionError("received Return was treated as resolved")
        return {"control": control, "status": "open"}
    if number == 62:
        return _resolved_control(root, "vfy")
    if number == 63:
        candidate, control = _control_candidate(
            root,
            "vfy",
            imp_binding=legacy.PLN + "#WI-999",
        )
        handler = VfyHandler(root)
        opened = handler.create(
            candidate,
            persist=False,
            run_automated=True,
            finalize=False,
        )["state"]
        result = next(
            item
            for item in opened["method_results"]
            if item["method_id"] == "VFM-001"
        )
        opened["control_resolutions"] = [
            {
                "control_reference": control,
                "method_references": ["VFM-001"],
                "target_references": [VFO_VER],
                "evidence_references": list(result["evidence_references"]),
            }
        ]
        return expect_error(
            "VFY_CONTROL_INVALID",
            lambda: handler.run_state(
                opened, method_ids=[], allow_commands=False, finalize=False
            ),
        )
    if number == 64:
        return _resolved_control(root, "rls")
    if number == 77:
        state = _finalized_exception_state(
            root,
            rls_applicability="required",
            waive_method=True,
        )
        projection = legacy.project_vfy_state(state)
        candidate = build_release_candidate(state)
        if not (
            state["artifact_gate"] == "pass_with_exception"
            and state["artifact"]["artifact_status"] == "ready_with_exception"
            and projection.next_phase == "RLS"
            and projection.rls_ready
            and candidate["exception_references"]
        ):
            raise AssertionError("accepted Method waiver did not project to RLS")
        return {
            "projection": projection.to_dict(),
            "release_candidate": candidate,
        }
    if number == 79:
        n_a_candidate = valid_candidate()
        n_a_candidate["rls_applicability"] = "n/a"
        n_a_handler = VfyHandler(root)
        n_a_opened = n_a_handler.create(
            n_a_candidate,
            persist=False,
            run_automated=True,
            allow_commands=False,
            finalize=False,
        )["state"]
        n_a_state = n_a_handler.run_state(
            n_a_opened,
            method_ids=[],
            allow_commands=False,
            finalize=True,
            confirmation=delegated_confirmation(root, n_a_opened),
        )["state"]
        waived_state = _finalized_exception_state(
            root,
            rls_applicability="waived",
            waive_method=False,
        )
        projections = [
            legacy.project_vfy_state(n_a_state),
            legacy.project_vfy_state(waived_state),
        ]
        if not all(
            item.next_phase is None
            and item.next_action == "LIFECYCLE_COMPLETE"
            for item in projections
        ):
            raise AssertionError("RLS n/a/waived created empty downstream work")
        if waived_state["artifact_gate"] != "pass_with_exception":
            raise AssertionError("RLS waiver lost exact Exception closure")
        return {"projections": [item.to_dict() for item in projections]}
    raise KeyError(number)


def run_case(case_id: str):
    if not isinstance(case_id, str) or not case_id.startswith("VFY-E"):
        raise ValueError("invalid Case ID")
    number = int(case_id[-3:])
    with legacy.workspace() as root:
        if number in {
            1, 3, 6, 10, 15, 18, 41, 42, 46,
            56, 57, 58, 59, 60, 61, 62, 63, 64, 76, 77, 79,
        }:
            result = _override(number, root)
        else:
            result = legacy._case(case_id, root)
            return result
    return {"case_id": case_id, "status": "PASS", "result": result}
