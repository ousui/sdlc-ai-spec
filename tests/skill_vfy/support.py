"""Deterministic fixtures for focused VFY tests and Fixed Eval."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

from packages.sdlc_artifact_store import compute_sha256
from packages.sdlc_lifecycle import LifecycleQueryService
from packages.sdlc_runtime.authority import (
    DELEGATED_AUTHORITY_HEADERS,
    DELEGATED_EXCLUDED_AUTHORITY,
    DELEGATED_INDEPENDENCE,
)


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "sdlc-500-vfy" / "scripts"
TOOLS = ROOT / "tools"
for entry in (ROOT, SCRIPTS, TOOLS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from vfy_builder import build_state  # noqa: E402
from vfy_handler import VfyHandler  # noqa: E402
import run_external_imp_integration as external_imp  # noqa: E402
import run_external_vfy_integration as external_vfy  # noqa: E402


CTX = "CTX-20260904100000-01@1"
PLN = "PLN-20260904101000-01@1"
WI = PLN + "#WI-001"
IMP = "IMP-20260904102000-01@1"
SUBJECT = IMP + "/RES-001"
VFO_VER = "DSN-20260904100500-01@1#VFO-001"
VFO_VAL = "DSN-20260904100500-01@1#VFO-002"
VFP_VER = "DSN-20260904100500-01@1#VFP-001"
VFP_VAL = "DSN-20260904100500-01@1#VFP-002"
RESULT_DIGEST = "sha256:" + "1" * 64


def valid_candidate() -> dict[str, Any]:
    return {
        "contract": "sdlc-ai-spec/vfy-candidate/v1",
        "context_reference": CTX,
        "profile": "full",
        "title": "Fixture verification",
        "scope": {
            "reference": PLN,
            "disposition": "required",
            "delivery_scope": ["resource:app"],
            "input_references": [CTX],
            "imp_work_items": [
                {
                    "reference": WI,
                    "target_phase": "IMP",
                    "binding_reference": WI,
                    "resource_ids": ["app"],
                    "depends_on": [],
                }
            ],
        },
        "subjects": [
            {
                "reference": SUBJECT,
                "resource_id": "app",
                "imp_revision_reference": IMP,
                "binding_lineage": WI,
                "attempt": "attempt-001",
                "claim_state": "completed",
                "imp_revision_state": "frozen",
                "baseline_reference": "vcs:git:" + "0" * 40,
                "result_digest": RESULT_DIGEST,
                "cumulative_changed_scope": ["path:app/README.md"],
                "dependency_result_references": [],
                "current_valid": True,
                "dependency_chain_valid": True,
            }
        ],
        "targets": [
            {
                "reference": VFO_VER,
                "purpose": "verification",
                "summary": "The exact result contains the required file",
                "source_kind": "vfo",
                "obligation_references": [VFP_VER],
            },
            {
                "reference": VFO_VAL,
                "purpose": "validation",
                "summary": "The delivered result supports its intended basic use",
                "source_kind": "vfo",
                "obligation_references": [VFP_VAL],
            },
        ],
        "methods": [
            {
                "id": "VFM-001",
                "title": "Inspect required file",
                "purpose": "verification",
                "target_references": [VFO_VER],
                "subject_references": [SUBJECT],
                "obligation_references": [VFP_VER, WI],
                "method_type": "inspection",
                "disposition": "required",
                "execution_mode": "automated",
                "executor_identity": "fixture-automated",
                "procedure": {"kind": "file_exists", "path": "README.md"},
                "pass_criteria": "README.md exists in the exact Subject workspace",
                "evidence_requirement": "Immutable path observation",
            },
            {
                "id": "VFM-002",
                "title": "Validate intended basic use",
                "purpose": "validation",
                "target_references": [VFO_VAL],
                "subject_references": [SUBJECT],
                "obligation_references": [VFP_VAL, WI],
                "method_type": "demonstration",
                "disposition": "required",
                "execution_mode": "automated",
                "executor_identity": "fixture-automated",
                "procedure": {"kind": "file_exists", "path": "README.md"},
                "pass_criteria": "The delivered entry point is observable",
                "evidence_requirement": "Immutable basic-use observation",
            },
        ],
        "required_obligation_references": [VFP_VER, VFP_VAL, WI],
        "control_inputs": [],
        "returns": [],
        "rls_applicability": "required",
        "release_target_obligations": [],
    }


def candidate_copy(**changes: Any) -> dict[str, Any]:
    value = valid_candidate()
    value.update(deepcopy(changes))
    return value


def prepare_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("fixture\n", encoding="utf-8")


def delegated_confirmation(
    root: Path,
    state: dict[str, Any],
    *,
    reviewer: str = "fixture-independent-reviewer",
    reviewed_executor: str = "fixture-automated",
) -> dict[str, Any]:
    """Create deterministic delegated technical authority, never human UX Evidence."""

    bindings = VfyHandler(root).confirmation_requirements(state)
    authority_dir = root / ".sdlc/authority"
    authority_dir.mkdir(parents=True, exist_ok=True)
    basis = authority_dir / "vfy-test-delegation.txt"
    basis.write_text(
        "The independent fixture reviewer may confirm deterministic VFY contract compliance.\n",
        encoding="utf-8",
    )
    basis_reference = (
        basis.relative_to(root).as_posix() + "@" + compute_sha256(basis.read_bytes())
    )
    values = (
        basis_reference,
        reviewer,
        "Delegated Independent Reviewer",
        reviewed_executor,
        DELEGATED_INDEPENDENCE,
        bindings["control_input_digest"],
        bindings["evaluation_contract_set"],
        bindings["check_set_result_digest"],
        DELEGATED_EXCLUDED_AUTHORITY,
    )
    raw = (
        "\n".join(
            (
                "---",
                "contract: sdlc-ai-spec/final-confirmation-authority/v1",
                f"artifact: {state['artifact']['reference']}",
                "decision: approved",
                "decided_at: 2026-09-04T10:30:00Z",
                "---",
                "",
                "| " + " | ".join(DELEGATED_AUTHORITY_HEADERS) + " |",
                "|" + "|".join("---" for _ in DELEGATED_AUTHORITY_HEADERS) + "|",
                "| " + " | ".join(values) + " |",
            )
        )
        + "\n"
    ).encode("utf-8")
    authority = authority_dir / "vfy-test-delegated-confirmation.md"
    authority.write_bytes(raw)
    return {
        "mode": "delegated",
        "confirmer": reviewer,
        "role": "Delegated Independent Reviewer",
        "reviewed_executor": reviewed_executor,
        "authority_reference": authority.relative_to(root).as_posix()
        + "@"
        + compute_sha256(raw),
        "accepted_exception_references": [],
        "confirmed_at": "2026-09-04T10:30:00Z",
        **bindings,
    }


def human_confirmation(
    root: Path,
    state: dict[str, Any],
    *,
    confirmer: str = "fixture-product-owner",
) -> dict[str, Any]:
    """Create a real project-local human authority for current Exceptions."""

    bindings = VfyHandler(root).confirmation_requirements(state)
    authority_dir = root / ".sdlc/authority"
    authority_dir.mkdir(parents=True, exist_ok=True)
    authority = authority_dir / "vfy-test-human-confirmation.txt"
    authority.write_text(
        "decision: approved\nauthority: product owner\n",
        encoding="utf-8",
    )
    accepted = [
        f"{state['artifact']['reference']}#{item['id']}"
        for item in state.get("exceptions", [])
        if item.get("state") in {"active", "carried"}
    ]
    return {
        "mode": "human",
        "confirmer": confirmer,
        "role": "Product Owner",
        "authority_reference": authority.relative_to(root).as_posix()
        + "@"
        + compute_sha256(authority.read_bytes()),
        "accepted_exception_references": accepted,
        "confirmed_at": "2026-09-04T10:30:00Z",
        **bindings,
    }


def passing_state(root: Path, *, finalize: bool = True) -> dict[str, Any]:
    prepare_workspace(root)
    handler = VfyHandler(root)
    created = handler.create(
        valid_candidate(),
        persist=False,
        run_automated=True,
        allow_commands=False,
        finalize=False,
    )
    if not finalize:
        return created["state"]
    return handler.run_state(
        created["state"],
        method_ids=[],
        allow_commands=False,
        finalize=True,
        confirmation=delegated_confirmation(root, created["state"]),
    )["state"]


def persistent_authority_candidate(root: Path) -> dict[str, Any]:
    """Build a Candidate from real CTX→REQ→DSN→PLN→IMP authorities."""

    prepare_workspace(root)
    if (root / ".sdlc").exists():
        raise AssertionError("persistent VFY fixture requires a fresh ArtifactStore")
    if not (root / ".git").exists():
        external_imp._git(root, "init", "-q")
        external_imp._git(root, "add", "README.md")
        external_imp._git(
            root,
            "-c",
            "user.name=VFY Fixture",
            "-c",
            "user.email=vfy-fixture@example.invalid",
            "commit",
            "-qm",
            "seed VFY authority fixture",
        )
    repository = "fixture/vfy-persistence"
    initial = external_imp._git_state(root)
    context_reference, _ = external_imp._create_context(
        root,
        repository,
        initial["head"],
        initial["workspace"]["sha256"],
    )
    requirement_reference, _ = external_imp._create_requirement(
        root,
        context_reference,
        repository,
        initial["head"],
        ".",
    )
    with external_vfy._external_design_with_vfy_strategy():
        design_reference, _ = external_imp._create_design(
            root,
            context_reference,
            requirement_reference,
            repository,
            initial["head"],
            (root / "README.md").read_bytes(),
            ".",
        )
    plan_reference, plan = external_imp._create_plan(
        root, design_reference, repository
    )
    external_imp._complete_imp(
        root,
        plan_reference + "#WI-001",
        design_reference,
        repository,
        ".",
    )
    projection = LifecycleQueryService(root, plugin_root=ROOT).inspect_requirement(
        requirement_reference
    )
    return external_vfy._candidate_from_lifecycle(
        root=root,
        project_label=repository,
        context_reference=context_reference,
        design_reference=design_reference,
        plan_reference=plan_reference,
        plan_candidate=plan,
        projection=projection,
        target_path="README.md",
    )


def persistent_passing_fixture(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = persistent_authority_candidate(root)
    handler = VfyHandler(root)
    opened = handler.create(
        candidate,
        persist=True,
        run_automated=True,
        allow_commands=False,
        finalize=False,
    )
    state = handler.run(
        reference=None,
        state=opened["state"],
        store_generation=opened["store_generation"],
        persist=True,
        method_ids=[],
        allow_commands=False,
        automated_only=False,
        manual_observations=None,
        failure_returns=None,
        early_stop_basis=None,
        finalize=True,
        confirmation=delegated_confirmation(
            root,
            opened["state"],
            reviewer="vfy-persistence-reviewer",
            reviewed_executor=external_vfy.VFY_EXECUTOR,
        ),
    )["state"]
    return state, candidate


def persistent_passing_state(root: Path) -> dict[str, Any]:
    return persistent_passing_fixture(root)[0]


def fixture_subject_snapshot(candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    subject = (candidate or valid_candidate())["subjects"][0]
    return {
        "subjects": [
            {
                "reference": subject["reference"],
                "result_digest": subject["result_digest"],
                "binding_lineage": subject["binding_lineage"],
                "attempt": subject["attempt"],
            }
        ]
    }


def open_state(root: Path) -> dict[str, Any]:
    prepare_workspace(root)
    return build_state(valid_candidate())
