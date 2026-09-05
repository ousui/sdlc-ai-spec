"""Development-only real CTX -> REQ -> DSN -> PLN -> IMP -> VFY fixture.

Derived from accepted VFY scaffold 46509eb6688df30e71ed094132b2d10e81ceb2ac.
Adds an explicit Sandbox RLS Work Item before upstream Artifacts freeze. No
runtime validator is patched and no source or real project ref is written.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
from typing import Any, Mapping
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "tools", ROOT / "skills/sdlc-500-vfy/scripts"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))
import run_external_imp_integration as upstream
import run_external_vfy_integration as producer
from run_external_imp_integration import (
    ArtifactStore, resolve_inputs, subject_digest, execute_phase, PlnHandler,
    FIXED, FIXED_TEXT, _authority_reference, _assert, pln_fixture,
)
from run_external_pln_integration import _project_build_descriptors, _phase_rows
from packages.sdlc_lifecycle import LifecycleQueryService
from vfy_handler import VfyHandler
VFY_EXECUTOR = producer.VFY_EXECUTOR

def _rls_plan_candidate(root: Path, phase_inputs) -> dict[str, Any]:
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
        work_items.append({
            "id": f"WI-{len(work_items) + 1:03d}", "target_phase": "RLS",
            "outcome": "Record an authorized release only in a dedicated local Sandbox",
            "execution_scope": [*resources, "environment:sandbox-a"], "source_references": list(obligations),
            "constraint_references": [], "depends_on": [work_items[-1]["id"]],
            "completion_criteria": "Local target observation and frozen RLS conclusion agree",
            "expected_evidence": "Immutable Sandbox target snapshots and RLS record",
            "responsible_role": "Sandbox Release Executor",
        })

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
    design_reference: str,
    project_label: str,
    exception_scope=None,
) -> tuple[str, dict[str, Any]]:
    store = ArtifactStore.open_read_only(root)
    phase_inputs = resolve_inputs(
        store, {"scope_inputs": [design_reference], "control_inputs": []}
    )
    plan = _rls_plan_candidate(root, phase_inputs)
    if exception_scope:
        plan["exceptions"] = [{"id": "EX-001", "state": "active", "scope": ", ".join(exception_scope),
            "reason": "Explicit bounded fixture exception", "known_risk": "Known fixture residual risk",
            "compensating_control": "Observe only the local Sandbox", "approval": "Fixture Owner at 2026-09-05T00:00:00Z",
            "revisit_condition": "next release", "downstream_obligation": "RLS retains the exact scoped fixture obligation"}]
    _assert(len(plan["work_items"]) in {2, 3}, "PLN must contain IMP/VFY and optional Sandbox RLS")
    imp_item = plan["work_items"][0]
    imp_item.update(
        outcome=f"Materialize the reversible README marker for {project_label}",
        execution_scope=["resource:repo", "path:repo/README.md"],
        completion_criteria=(
            f"README.md contains the {project_label} marker and an immutable Result"
        ),
        expected_evidence=(
            f"Exact {project_label} Baseline, changed-path evidence and Result digest"
        ),
    )
    vfy_item = plan["work_items"][1]
    vfy_item.update(
        outcome=f"Verify the completed {project_label} README Result",
        execution_scope=["resource:repo", "path:repo/README.md"],
        completion_criteria="The current completed IMP is the exact VFY input",
        expected_evidence="Frozen IMP Result and completed Current Claim",
    )
    plan["title"] = f"{project_label} external IMP delivery plan"
    plan["summary"] = (
        f"Plan one deterministic README implementation and VFY handoff for {project_label}."
    )
    authority_reference = _authority_reference(
        root,
        "pln-approval.md",
        f"project: {project_label}\nwork_item: WI-001\ndecision: approved\n",
    )
    confirmation = {
        "mode": "human",
        "confirmer": "external-plan-authority",
        "role": "Plan Authority",
        "authority_reference": authority_reference,
        "confirmed_at": FIXED_TEXT,
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
    result = execute_phase(PlnHandler(root, clock=lambda: FIXED), invocation)
    _assert(
        result.get("ok")
        and result["artifact"]["revision_state"] == "frozen"
        and result["artifact"]["artifact_status"] == ("ready_with_exception" if exception_scope else "ready"),
        "real PLN did not freeze ready: "
        + json.dumps(result, ensure_ascii=False, sort_keys=True),
    )
    return result["artifact"]["reference"], plan


def _candidate_from_lifecycle(
    *,
    root: Path,
    project_label: str,
    context_reference: str,
    design_reference: str,
    plan_reference: str,
    plan_candidate: Mapping[str, Any],
    projection,
    target_path: str,
) -> dict[str, Any]:
    claims = [item for item in projection.current_claims if item.completed and item.vfy_ready]
    if len(claims) != 1 or not claims[0].results:
        raise upstream.IntegrationError(
            "VFY requires one exact Current completed IMP Claim with Results"
        )
    claim = claims[0]
    subjects = [
        {
            "reference": result["result_reference"],
            "resource_id": result["resource"],
            "imp_revision_reference": claim.artifact_reference,
            "binding_lineage": claim.binding_lineage,
            "attempt": str(claim.attempt),
            "claim_state": claim.claim_state,
            "imp_revision_state": claim.revision_state,
            "baseline_reference": result["baseline_reference"],
            "result_digest": result["result_digest"],
            "cumulative_changed_scope": list(result["changed_scope"]),
            "dependency_result_references": list(claim.dependency_results),
            "current_valid": True,
            "dependency_chain_valid": True,
        }
        for result in claim.results
    ]
    subject_refs = [item["reference"] for item in subjects]
    result_resources = [item["resource_id"] for item in subjects]
    vfy_item = next(
        item for item in plan_candidate["work_items"] if item["target_phase"] == "VFY"
    )
    rls = next(
        item
        for item in plan_candidate["aggregated_applicability"]
        if item["phase"] == "RLS"
    )
    if rls["disposition"] not in {"required", "n/a", "waived", "pending"}:
        raise upstream.IntegrationError("fixture requires explicit RLS disposition")
    target = design_reference + "#VFO-001"
    vfp_210 = design_reference + "#VFP-210-001"
    vfp_220 = design_reference + "#VFP-220-001"
    binding = claim.binding_reference
    expected = "sha256:" + hashlib.sha256((root / target_path).read_bytes()).hexdigest()
    return {
        "contract": "sdlc-ai-spec/vfy-candidate/v1",
        "context_reference": context_reference,
        "profile": "full",
        "title": f"{project_label} exact IMP Result verification",
        "scope": {
            "reference": plan_reference,
            "disposition": "required",
            "delivery_scope": sorted(claim.execution_scope),
            "input_references": [context_reference],
            "imp_work_items": [
                {
                    "reference": binding,
                    "target_phase": "IMP",
                    "binding_reference": binding,
                    "resource_ids": result_resources,
                    "depends_on": [],
                }
            ],
        },
        "subjects": subjects,
        "targets": [
            {
                "reference": target,
                "purpose": "both",
                "summary": f"{target_path} contains the exact completed IMP marker",
                "source_kind": "vfo",
                "obligation_references": [vfp_210, vfp_220],
            }
        ],
        "methods": [
            {
                "id": "VFM-001",
                "title": "Inspect exact completed Result path",
                "purpose": "verification",
                "target_references": [target],
                "subject_references": subject_refs,
                "obligation_references": [vfp_210, binding,
                    design_reference + "#VFM-001", design_reference + "#VPC-001",
                    design_reference + "#VEC-001", plan_reference + "#" + vfy_item["id"]],
                "method_type": "inspection",
                "disposition": "required",
                "execution_mode": "automated",
                "executor_identity": VFY_EXECUTOR,
                "procedure": {"kind": "file_exists", "path": target_path},
                "pass_criteria": f"{target_path} exists in the exact IMP product state",
                "evidence_requirement": "Immutable path observation",
            },
            {
                "id": "VFM-002",
                "title": "Analyze exact completed Result digest",
                "purpose": "validation",
                "target_references": [target],
                "subject_references": subject_refs,
                "obligation_references": [vfp_220, binding,
                    design_reference + "#VFM-002", design_reference + "#VPC-001",
                    design_reference + "#VEC-001", plan_reference + "#" + vfy_item["id"]],
                "method_type": "analysis",
                "disposition": "required",
                "execution_mode": "automated",
                "executor_identity": VFY_EXECUTOR,
                "procedure": {
                    "kind": "sha256_equals",
                    "path": target_path,
                    "expected": expected,
                },
                "pass_criteria": "The exact current product digest matches",
                "evidence_requirement": "Immutable SHA-256 observation",
            },
        ],
        "required_obligation_references": sorted([
            vfp_210, vfp_220, binding, design_reference + "#VFM-001",
            design_reference + "#VFM-002", design_reference + "#VPC-001",
            design_reference + "#VEC-001", plan_reference + "#" + vfy_item["id"],
        ]),
        "control_inputs": [],
        "returns": [],
        "rls_applicability": rls["disposition"],
        "release_target_obligations": ([{
            "reference": plan_reference + "#WI-003",
            "confirmation": "Observe the authorized local Sandbox release",
            "expected": "The target version equals the bound release reference",
            "evidence_requirement": "Immutable target-side snapshot after the selected RLI",
        }] if rls["disposition"] == "required" else []),
    }



def build_chain(root: Path, *, applicability="required", repository="fixture/rls-final", product_failure=False, finalize_vfy=True, early_stop=False, unresolved_return=False, resource_root=".", waived_method=False):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        (root / "README.md").write_text("RLS final integration fixture\n")
        upstream._git(root, "init", "-q")
        upstream._git(root, "add", "README.md")
        upstream._git(root, "-c", "user.name=RLS Fixture", "-c", "user.email=rls-fixture@example.invalid", "commit", "-qm", "seed disposable RLS fixture")
    initial = upstream._git_state(root)
    context, _ = upstream._create_context(root, repository, initial["head"], initial["workspace"]["sha256"])
    original = upstream._requirement_candidate
    def requirement_candidate(*args, **kwargs):
        value = original(*args, **kwargs)
        row = next(row for row in value["lifecycle_applicability"] if row["phase"] == "RLS")
        row.update(disposition=applicability, basis="Explicit local Sandbox lifecycle integration; no production release")
        return value
    with patch.object(upstream, "_requirement_candidate", requirement_candidate):
        requirement, _ = upstream._create_requirement(root, context, repository, initial["head"], resource_root)
    with producer._external_design_with_vfy_strategy():
        design_builder = upstream._design_candidate
        def design_candidate(*args, **kwargs):
            value = design_builder(*args, **kwargs)
            row = next(row for row in value["lifecycle_applicability"] if row["phase"] == "RLS")
            row.update(disposition=applicability, basis="Explicit local Sandbox release with target-side confirmation")
            return value
        with patch.object(upstream, "_design_candidate", design_candidate):
            design, _ = upstream._create_design(root, context, requirement, repository, initial["head"], (root / resource_root / "README.md").read_bytes(), resource_root)
    exception_scope = ["phase:RLS"] if applicability == "waived" else ["product_result:fail"] if product_failure else ["VFM-002"] if waived_method else None
    plan, plan_candidate = _create_plan(root, design, repository, exception_scope)
    _complete_rls_imp(root, plan + "#WI-001", design, repository, resource_root, bool(exception_scope))
    projection = LifecycleQueryService(root, plugin_root=ROOT).inspect_requirement(requirement)
    hint = _candidate_from_lifecycle(root=root, project_label=repository, context_reference=context,
            design_reference=design, plan_reference=plan, plan_candidate=plan_candidate,
            projection=projection, target_path="README.md" if resource_root == "." else resource_root + "/README.md")
    if exception_scope:
        from vfy_authority import _resolve_exception
        from packages.sdlc_runtime.authority import FrozenArtifactAuthorityVerifier
        hint["exceptions"] = [_resolve_exception(ArtifactStore.open_read_only(root), FrozenArtifactAuthorityVerifier(root), plan + "#EX-001")]
    if waived_method:
        hint["methods"][1].update(disposition="waived", exception_reference=plan+"#EX-001")
        hint["release_target_obligations"][0]["reference"]=plan+"#EX-001"
    if product_failure or early_stop or unresolved_return:
        hint["methods"][1]["procedure"]["expected"] = "sha256:" + "0" * 64
    handler = VfyHandler(root)
    opened = handler.create(hint, persist=True, run_automated=not (early_stop or unresolved_return), allow_commands=False, finalize=False)
    if early_stop or unresolved_return:
        method = hint["methods"][1]
        failures = {"VFM-002": {"id": "RET-001", "return_phase": "IMP",
                    "imp_binding_reference": projection.current_claims[0].binding_reference, "imp_binding_lineage": projection.current_claims[0].binding_lineage,
                    "target_references": method["target_references"], "subject_references": method["subject_references"],
                    "observed_gap": "The expected exact digest is absent", "required_outcome": "Restore exact declared product digest"}}
        basis = {"failure_method_references": ["VFM-002"],
                 "return_references": [opened["state"]["artifact"]["reference"] + "#RET-001"],
                 "pending_facts_cannot_change_failure_or_attribution": True} if early_stop else None
        opened = handler.run(reference=None, state=opened["state"], store_generation=opened["store_generation"],
                    persist=True, method_ids=["VFM-002"] if early_stop else ["VFM-001", "VFM-002"],
                    allow_commands=False, automated_only=False, manual_observations=None,
                    failure_returns=failures, early_stop_basis=basis, finalize=False, confirmation=None)
    # Test authority uses the same genuine producer confirmation protocol.
    from tests.skill_vfy.support import delegated_confirmation, human_confirmation
    result = handler.run(reference=None, state=opened["state"], store_generation=opened["store_generation"],
            persist=True, method_ids=[], allow_commands=False, automated_only=False,
            manual_observations=None, failure_returns=None, early_stop_basis=None, finalize=finalize_vfy,
            confirmation=(human_confirmation(root, opened["state"]) if exception_scope else delegated_confirmation(root, opened["state"], reviewer="rls-vfy-independent-reviewer", reviewed_executor=VFY_EXECUTOR)) if finalize_vfy else None)
    from vfy_release import build_release_candidate
    state = result["state"]
    assert state["rls_applicability"] == applicability
    assert state["rls_ready"] is (applicability == "required" and finalize_vfy and not (early_stop or unresolved_return))
    return {"context": context, "requirement": requirement, "design": design, "plan": plan,
            "vfy": state["artifact"]["reference"], "state": state, "candidate": build_release_candidate(state) if finalize_vfy and not (early_stop or unresolved_return) else None,
            "initial": initial, "plan_candidate": plan_candidate}


def rls_final_confirmation(root, service, reference, target):
    """Fixture delegated review: deterministic contract compliance only."""
    from packages.sdlc_runtime.authority import (DELEGATED_AUTHORITY_HEADERS, DELEGATED_INDEPENDENCE,
                                                DELEGATED_EXCLUDED_AUTHORITY)
    from packages.sdlc_artifact_store import compute_sha256
    from rls_common import utc_now
    bindings = service.confirmation_requirements(reference, target)
    directory = Path(root) / ".sdlc/authority"
    directory.mkdir(parents=True, exist_ok=True)
    if bindings["accepted_exception_references"]:
        from rls_common import canonical_json
        now = utc_now()
        raw = (canonical_json(dict(artifact_reference=reference, decision="approved", authority="explicit fixture risk owner", **bindings)) + "\n").encode()
        authority = directory / ("rls-exception-confirmation-" + compute_sha256(raw).split(":")[1] + ".json")
        authority.write_bytes(raw)
        return dict(mode="human", confirmer="fixture-risk-owner", role="Fixture Owner",
                    authority_reference=authority.relative_to(root).as_posix() + "@" + compute_sha256(raw),
                    confirmed_at=now, **bindings)
    basis_raw = b"Fixture host delegates deterministic RLS contract review; no business, risk or external effect authority.\n"
    basis = directory / ("rls-delegation-" + compute_sha256(basis_raw).split(":")[1] + ".txt")
    if not basis.exists():
        basis.write_bytes(basis_raw)
    basis_reference = basis.relative_to(root).as_posix() + "@" + compute_sha256(basis_raw)
    now = utc_now()
    values = (basis_reference, "rls-fixture-reviewer", "Delegated Independent Reviewer", "sandbox-executor",
              DELEGATED_INDEPENDENCE, bindings["control_input_digest"], bindings["evaluation_contract_set"],
              bindings["check_set_result_digest"], DELEGATED_EXCLUDED_AUTHORITY)
    raw = ("\n".join(("---", "contract: sdlc-ai-spec/final-confirmation-authority/v1", f"artifact: {reference}",
                      "decision: approved", f"decided_at: {now}", "---", "",
                      "| " + " | ".join(DELEGATED_AUTHORITY_HEADERS) + " |",
                      "|" + "|".join("---" for _ in DELEGATED_AUTHORITY_HEADERS) + "|",
                      "| " + " | ".join(values) + " |")) + "\n").encode()
    authority = directory / ("rls-confirmation-" + compute_sha256(raw).split(":")[1] + ".md")
    authority.write_bytes(raw)
    return {"mode": "delegated", "confirmer": "rls-fixture-reviewer", "role": "Delegated Independent Reviewer",
            "authority_reference": authority.relative_to(root).as_posix() + "@" + compute_sha256(raw),
            "confirmed_at": now, **bindings}


def _complete_rls_imp(
    root: Path,
    binding: str,
    design_reference: str,
    project_label: str,
    resource_root: str,
    with_exception=False,
) -> tuple[dict[str, Any], str]:
    method, marker = upstream._implementation_candidate(
        root, design_reference, project_label, resource_root
    )
    handler = upstream.ImpHandler(root, clock=lambda: FIXED)
    created = execute_phase(
        handler,
        upstream._imp_invocation(
            root,
            "create",
            binding=binding,
            implementation=method,
        ),
    )
    _assert(
        created.get("artifact") is not None
        and created["artifact"]["revision_state"] == "open"
        and created["status"] == "action_required",
        "IMP create did not execute and retain an open Revision: "
        + json.dumps(created, ensure_ascii=False, sort_keys=True),
    )
    info = upstream._execution_warning(created)
    reference = created["artifact"]["reference"]
    authority_text = "\n".join(
        (
            f"artifact: {reference}",
            f"subject: {info['subject_digest']}",
            f"control: {info['final_confirmation_bindings']['control_input_digest']}",
            f"contracts: {info['final_confirmation_bindings']['evaluation_contract_set']}",
            f"checks: {info['final_confirmation_bindings']['check_set_result_digest']}",
            "decision: approved",
        )
    ) + "\n"
    authority_reference = _authority_reference(
        root, "imp-approval.md", authority_text
    )
    final_confirmation = {
        "mode": "human",
        "confirmer": "external-implementation-authority",
        "role": "Implementation Authority",
        "authority_reference": authority_reference,
        "confirmed_at": FIXED_TEXT,
        "subject_digest": info["subject_digest"],
        **info["final_confirmation_bindings"],
    }
    completed = execute_phase(
        handler,
        upstream._imp_invocation(
            root,
            "revise",
            reference=reference,
            final_confirmation=final_confirmation,
        ),
    )
    _assert(
        completed.get("ok")
        and completed["status"] == "completed"
        and completed["artifact"]["revision_state"] == "frozen"
        and completed["artifact"]["artifact_status"] == ("ready_with_exception" if with_exception else "ready"),
        "IMP did not freeze and complete its Current Claim: "
        + json.dumps(completed, ensure_ascii=False, sort_keys=True),
    )
    return completed, marker
