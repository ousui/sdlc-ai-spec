#!/usr/bin/env python3
"""Run a temporary CTX -> REQ -> DSN -> PLN integration on any Git project.

The target project is test input only. The harness writes only the temporary
``.sdlc`` runtime directory, removes it before exit, and never commits, pushes,
or modifies source-controlled project files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
DSN_SCRIPTS = ROOT / "skills/sdlc-200-dsn/scripts"
PLN_SCRIPTS = ROOT / "skills/sdlc-300-pln/scripts"
for candidate in (ROOT, ROOT / "packages", TOOLS, DSN_SCRIPTS, PLN_SCRIPTS):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

import run_external_dsn_integration as dsn_fixture  # noqa: E402
from packages.sdlc_artifact_store import ArtifactStore  # noqa: E402
from packages.sdlc_lifecycle import LifecycleQueryService  # noqa: E402
from packages.sdlc_phasekit import subject_digest  # noqa: E402
from packages.sdlc_runtime import execute_phase, parse_canonical_artifact, sha256_bytes  # noqa: E402
from packages.sdlc_runtime.canonical import find_tables  # noqa: E402
from dsn_common import UpstreamScope  # noqa: E402
from pln_common import WORK_HEADERS  # noqa: E402
from pln_runtime import PlnHandler, resolve_inputs  # noqa: E402

FIXED = dsn_fixture.FIXED
BUILD_MARKERS = (
    "pom.xml",
    "go.mod",
    "package.json",
    "Cargo.toml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
)
SKIPPED_DIRECTORIES = {".git", ".sdlc", "node_modules", "vendor", "target", "dist"}


def _project_build_descriptors(root: Path) -> tuple[str, ...]:
    """Return stable, shallow build descriptors without scanning generated trees."""
    result: list[str] = []
    for marker in BUILD_MARKERS:
        candidate = root / marker
        if candidate.is_file():
            result.append(marker)
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if not child.is_dir() or child.name in SKIPPED_DIRECTORIES:
            continue
        for marker in BUILD_MARKERS:
            candidate = child / marker
            if candidate.is_file():
                result.append(candidate.relative_to(root).as_posix())
    return tuple(dict.fromkeys(result))


def _create_design(
    root: Path,
    project_label: str,
    store: ArtifactStore,
) -> tuple[str, str, Mapping[str, Any]]:
    context, requirement = dsn_fixture._create_upstream(store)
    authority_dir = root / ".sdlc/authority"
    authority_dir.mkdir(exist_ok=True)
    authority = authority_dir / "dsn-approval.md"
    authority.write_text(
        f"Approved external integration design for {project_label}\n",
        encoding="utf-8",
    )
    authority_reference = (
        authority.relative_to(root).as_posix()
        + "@"
        + sha256_bytes(authority.read_bytes())
    )
    design = dsn_fixture._design(root, requirement)
    normalized = dsn_fixture.DsnAnalyzer().analyze(
        design,
        UpstreamScope(
            context_reference=context,
            scope_references=(requirement,),
            control_references=(),
            requirement_items=(requirement + "#R-001",),
            acceptance_items=(requirement + "#AC-001",),
        ),
    ).normalized
    confirmation = {
        "mode": "human",
        "confirmer": "external-integration-authority",
        "role": "Design Authority",
        "authority_reference": authority_reference,
        "confirmed_at": "2026-09-01T10:00:00Z",
        "subject_digest": dsn_fixture._subject_digest(
            normalized,
            context,
            (requirement,),
            (),
        ),
    }
    invocation = {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create",
        "project_root": str(root),
        "artifact_reference": None,
        "inputs": {
            "scope_inputs": [requirement],
            "control_inputs": [],
            "design": design,
            "final_confirmation": confirmation,
        },
        "confirmations": [],
        "options": {"dry_run": False, "write_policy": "auto"},
    }
    result = execute_phase(
        dsn_fixture.DsnHandler(
            root,
            clock=lambda: FIXED,
            upstream_verifier_factory=lambda _: dsn_fixture.PassingVerifier(),
        ),
        invocation,
    )
    if not result.get("ok") or result["artifact"]["revision_state"] != "frozen":
        raise RuntimeError(
            "external DSN create did not freeze: "
            + json.dumps(result, ensure_ascii=False, sort_keys=True)
        )
    return context, requirement, result


def _phase_rows(phase_inputs) -> list[dict[str, str]]:
    return [dict(row) for row in phase_inputs.metadata["aggregated_applicability"]]


def _plan_candidate(root: Path, phase_inputs) -> dict[str, Any]:
    disposition = str(phase_inputs.metadata.get("pln_disposition"))
    if disposition != "required":
        raise RuntimeError(
            f"external PLN integration requires PLN=required, got {disposition!r}"
        )
    obligations = tuple(phase_inputs.metadata.get("authoritative_obligations") or ())
    if not obligations:
        raise RuntimeError("external DSN produced no PLN obligations")

    imp_sources = tuple(
        reference
        for reference in obligations
        if any(token in reference for token in ("#CHG-", "#OBL-", "#EX-"))
    )
    if not imp_sources:
        imp_sources = obligations
    vfy_sources = tuple(
        reference
        for reference in obligations
        if any(token in reference for token in ("#VFP-", "#OBJ-", "#AC-"))
    )
    if not vfy_sources:
        vfy_sources = obligations

    resources = tuple(phase_inputs.metadata.get("declared_resources") or ())
    if not resources:
        resources = (f"resource:{root.name}",)
    descriptors = _project_build_descriptors(root)

    work_items: list[dict[str, Any]] = []
    delivery_scope: list[dict[str, Any]] = []
    imp_ids: list[str] = []
    for resource in resources:
        resource_id = resource.split(":", 1)[1]
        execution_scope = [resource]
        for descriptor in descriptors[:4]:
            execution_scope.append(f"path:{resource_id}/{descriptor}")
        identity = f"WI-{len(work_items) + 1:03d}"
        imp_ids.append(identity)
        work_items.append(
            {
                "id": identity,
                "target_phase": "IMP",
                "outcome": (
                    f"Materialize the confirmed {root.name} change for resource "
                    f"{resource_id}"
                ),
                "execution_scope": execution_scope,
                "source_references": list(imp_sources),
                "constraint_references": [],
                "depends_on": [],
                "completion_criteria": (
                    "A versioned implementation result binds the declared resource "
                    "and the exact upstream obligations"
                ),
                "expected_evidence": (
                    "Immutable source snapshot, changed-path manifest, and result digest"
                ),
                "responsible_role": "Implementer",
            }
        )
        delivery_scope.append(
            {
                "scope_token": resource,
                "source_references": list(imp_sources),
                "outcome": (
                    f"Deliver the confirmed design change for {resource_id} without "
                    "expanding the authoritative scope"
                ),
            }
        )

    work_items.append(
        {
            "id": f"WI-{len(work_items) + 1:03d}",
            "target_phase": "VFY",
            "outcome": f"Verify the {root.name} implementation against all design objectives",
            "execution_scope": list(resources),
            "source_references": list(vfy_sources),
            "constraint_references": [],
            "depends_on": imp_ids,
            "completion_criteria": (
                "Every required verification objective has an explicit final conclusion "
                "bound to the implementation result"
            ),
            "expected_evidence": (
                "Verification method outputs, repository facts, and conclusion digest"
            ),
            "responsible_role": "Verifier",
        }
    )

    phase_rows = _phase_rows(phase_inputs)
    rls = next(row for row in phase_rows if row["phase"] == "RLS")
    if rls["disposition"] == "required":
        raise RuntimeError(
            "external PLN integration cannot guess a release environment for required RLS"
        )

    return {
        "title": f"{root.name} External Delivery Plan",
        "summary": (
            "Convert the frozen external-project design into stable implementation and "
            "verification Work Items."
        ),
        "profile": "full",
        "pln_disposition": disposition,
        "delivery_scope": delivery_scope,
        "aggregated_applicability": phase_rows,
        "obligations": list(obligations),
        "work_items": work_items,
        "lifecycle_applicability": phase_rows,
        "open_items": [],
        "evidence": [],
        "supporting_members": [],
        "exceptions": [],
    }


def _create_plan(
    root: Path,
    store: ArtifactStore,
    design_reference: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    phase_inputs = resolve_inputs(
        store,
        {"scope_inputs": [design_reference], "control_inputs": []},
        verifier_factory=lambda _: dsn_fixture.PassingVerifier(),
    )
    plan = _plan_candidate(root, phase_inputs)
    authority_dir = root / ".sdlc/authority"
    authority_dir.mkdir(exist_ok=True)
    authority = authority_dir / "pln-approval.md"
    authority.write_text(
        f"Approved external integration plan for {root.name}\n",
        encoding="utf-8",
    )
    authority_reference = (
        authority.relative_to(root).as_posix()
        + "@"
        + sha256_bytes(authority.read_bytes())
    )
    confirmation = {
        "mode": "human",
        "confirmer": "external-integration-plan-authority",
        "role": "Plan Authority",
        "authority_reference": authority_reference,
        "confirmed_at": "2026-09-01T10:00:00Z",
        "subject_digest": subject_digest(
            plan,
            {
                "context": phase_inputs.context_reference,
                "scope": phase_inputs.scope_references,
                "control": phase_inputs.control_references,
            },
        ),
    }
    invocation = {
        "contract": "sdlc-ai-spec/runtime-invocation/v1",
        "operation": "create",
        "project_root": str(root),
        "artifact_reference": None,
        "inputs": {
            "scope_inputs": [design_reference],
            "control_inputs": [],
            "plan": plan,
            "final_confirmation": confirmation,
        },
        "confirmations": [],
        "options": {"dry_run": False, "write_policy": "auto"},
    }
    result = execute_phase(
        PlnHandler(
            root,
            clock=lambda: FIXED,
            upstream_verifier_factory=lambda _: dsn_fixture.PassingVerifier(),
        ),
        invocation,
    )
    if not result.get("ok") or result["artifact"]["revision_state"] != "frozen":
        raise RuntimeError(
            "external PLN create did not freeze: "
            + json.dumps(result, ensure_ascii=False, sort_keys=True)
        )
    return plan, result


def run_integration(root: Path, project_label: str) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not (root / ".git").is_dir():
        raise RuntimeError("external project must be a Git checkout")

    before_status = dsn_fixture._git(root, "status", "--porcelain")
    before_snapshot = dsn_fixture._snapshot(root)
    runtime_dir = root / ".sdlc"
    if runtime_dir.exists():
        raise RuntimeError("external project already contains .sdlc")

    try:
        store = ArtifactStore.open_read_write(root, clock=lambda: FIXED)
        store.initialize()
        context, requirement, design_result = _create_design(root, project_label, store)
        plan, plan_result = _create_plan(
            root,
            store,
            design_result["artifact"]["reference"],
        )
        stored_plan = store.read_revision(plan_result["artifact"]["id"], 1)
        parsed_plan = parse_canonical_artifact(stored_plan.payload.primary_blob)
        work_tables = find_tables(parsed_plan, WORK_HEADERS)
        if len(work_tables) != 1:
            raise RuntimeError("external PLN has no unique Work Item table")
        work_rows = work_tables[0].rows
        expected_ids = tuple(f"WI-{index:03d}" for index in range(1, len(work_rows) + 1))
        if tuple(row["ID"] for row in work_rows) != expected_ids:
            raise RuntimeError("external PLN Work Item IDs are not stable sequential values")

        projection = LifecycleQueryService(
            root,
            plugin_root=ROOT,
            verifier_factory=lambda _: dsn_fixture.PassingVerifier(),
        ).inspect_requirement(requirement)
        if projection.frontier != (plan_result["artifact"]["reference"],):
            raise RuntimeError("external lifecycle frontier is not the frozen PLN")
        if not projection.next_actions:
            raise RuntimeError("external lifecycle did not project a PLN Work Item")
        first = projection.next_actions[0]
        first_binding = plan_result["artifact"]["reference"] + "#WI-001"
        if first.phase != "IMP" or first_binding not in str(first.command):
            raise RuntimeError("external lifecycle did not route PLN to exact IMP binding")

        output = {
            "contract": "sdlc-ai-spec/external-pln-integration/v1",
            "ok": True,
            "project": project_label,
            "project_commit": dsn_fixture._git(root, "rev-parse", "HEAD"),
            "build_descriptors": list(_project_build_descriptors(root)),
            "context_reference": context,
            "requirement_reference": requirement,
            "design_reference": design_result["artifact"]["reference"],
            "plan_reference": plan_result["artifact"]["reference"],
            "plan_gate": plan_result["gate"]["result"],
            "work_items": [
                {
                    "id": row["ID"],
                    "target_phase": row["目标 Phase Target Phase"],
                    "execution_scope": row["执行范围 Execution Scope"],
                    "depends_on": row["依赖 Depends On"],
                }
                for row in work_rows
            ],
            "lifecycle_state": projection.overall_state,
            "lifecycle_frontier": list(projection.frontier),
            "next_actions": [item.to_dict() for item in projection.next_actions],
            "source_snapshot_unchanged": before_snapshot == dsn_fixture._snapshot(root),
            "source_status_unchanged": before_status == dsn_fixture._git(root, "status", "--porcelain"),
        }
        if not output["source_snapshot_unchanged"]:
            raise RuntimeError("external project source files changed during PLN integration")
        return output
    finally:
        shutil.rmtree(runtime_dir, ignore_errors=True)
        after_status = dsn_fixture._git(root, "status", "--porcelain")
        after_snapshot = dsn_fixture._snapshot(root)
        if before_status != after_status or before_snapshot != after_snapshot:
            raise RuntimeError("external project was not restored to its original Git state")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-label", required=True)
    args = parser.parse_args()
    result = run_integration(Path(args.project_root), args.project_label)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
