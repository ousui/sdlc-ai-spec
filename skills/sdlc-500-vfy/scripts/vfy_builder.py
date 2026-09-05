"""Pure VFY state builder and exact canonical Markdown projection."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from packages.sdlc_artifact_store import CanonicalMember, compute_sha256
from packages.sdlc_phasekit import (
    CheckOutcome,
    PhaseInputs,
    evaluation_contract_set,
    render_phase_artifact,
)
from packages.sdlc_runtime import (
    compute_check_set_result_digest,
    compute_control_input_digest,
    parse_canonical_artifact,
    parse_reference_set,
)
from packages.sdlc_runtime.canonical import (
    FINAL_CONFIRMATION_HEADERS,
    require_single_row,
    require_single_table,
)

from vfy_canonical import owner_artifact_inputs, sections
from vfy_common import (
    canonical_bytes,
    exact_artifact_reference,
    exact_item_reference,
    reject_secrets,
    require,
    sha256_value,
    stable_unique,
)
from vfy_conclusions import (
    aggregate_fixed_conclusions,
    aggregate_target_conclusions,
    product_result,
)
from vfy_exceptions import normalize_exceptions, validate_exception_bindings
from vfy_methods import normalize_methods
from vfy_results import pending_result
from vfy_returns import normalize_returns
from vfy_scope import require_single_scope, validate_scope_subject_coverage
from vfy_subject import normalize_subjects, subject_references, subject_set_digest
from vfy_targets import normalize_targets

STATE_CONTRACT = "sdlc-ai-spec/vfy-state/v1"
CANDIDATE_CONTRACT = "sdlc-ai-spec/vfy-candidate/v1"


def new_artifact_id(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return "VFY-" + moment.strftime("%Y%m%d%H%M%S") + "-01"


def _control_reference(value: str) -> str:
    reference = exact_item_reference(value)
    require(
        reference.startswith(("VFY-", "RLS-")) and "#" in reference,
        "VFY_CONTROL_INVALID",
        "Control Input must be one exact VFY Return or RLS product-correction Issue",
        details={"reference": reference},
    )
    return reference


def normalize_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(
        candidate.get("contract") == CANDIDATE_CONTRACT,
        "VFY_CONTRACT_INVALID",
        "Unsupported VFY candidate contract",
    )
    scope = require_single_scope(candidate)
    subjects = normalize_subjects(candidate)
    validate_scope_subject_coverage(scope, subjects)
    targets = normalize_targets(candidate)
    subject_refs = subject_references(subjects)
    methods = normalize_methods(candidate, targets, subject_refs)
    controls = tuple(
        _control_reference(item)
        for item in stable_unique(candidate.get("control_inputs", []), field="control input")
    )
    control_authorities = deepcopy(list(candidate.get("control_authorities") or []))
    if controls:
        require(
            len(control_authorities) == len(controls)
            and {str(item.get("reference")) for item in control_authorities} == set(controls)
            and all(item.get("authority_verified") is True for item in control_authorities),
            "VFY_CONTROL_INVALID",
            "Every Control Input requires one verified frozen authority record",
        )
    subject_lineages = {
        str(item["reference"]): str(item["binding_lineage"]) for item in subjects
    }
    returns = normalize_returns(
        candidate.get("returns", []),
        subject_lineages=subject_lineages,
    )
    exceptions = normalize_exceptions(list(candidate.get("exceptions") or []))
    applicability = str(candidate.get("rls_applicability", "pending")).strip()
    require(
        applicability in {"required", "n/a", "waived", "pending"},
        "VFY_CONTRACT_INVALID",
        "RLS applicability is invalid",
    )
    validate_exception_bindings(
        methods,
        exceptions,
        rls_applicability=applicability,
        scope_tokens=scope["delivery_scope"],
    )
    context_reference = exact_artifact_reference(
        str(candidate.get("context_reference", "")), "CTX"
    )
    owners = tuple(
        exact_artifact_reference(str(item))
        for item in stable_unique(
            candidate.get("owner_artifact_inputs", []), field="owner Artifact input"
        )
    )
    if candidate.get("authority_compiled") is True:
        require(
            context_reference in owners
            and scope["reference"] in owners
            and all(item["imp_revision_reference"] in owners for item in subjects),
            "VFY_INPUT_AUTHORITY_MISMATCH",
            "Authority compiler omitted a direct owner Artifact Revision",
        )
    return {
        "contract": CANDIDATE_CONTRACT,
        "context_reference": context_reference,
        "scope": scope,
        "subjects": [dict(item) for item in subjects],
        "targets": [dict(item) for item in targets],
        "methods": [dict(item) for item in methods],
        "control_inputs": list(controls),
        "control_authorities": control_authorities,
        "control_resolutions": deepcopy(list(candidate.get("control_resolutions") or [])),
        "returns": returns,
        "exceptions": exceptions,
        "rls_applicability": applicability,
        "release_target_obligations": deepcopy(
            list(candidate.get("release_target_obligations", []))
        ),
        "profile": str(candidate.get("profile", "full")),
        "title": str(candidate.get("title", "Verification and Validation")),
        "owner_artifact_inputs": list(owners),
        "authority_compiled": bool(candidate.get("authority_compiled")),
    }


def build_state(
    candidate: Mapping[str, Any],
    *,
    artifact_id: str | None = None,
    revision: int = 1,
    base_revision: int | None = None,
) -> dict[str, Any]:
    normalized = normalize_candidate(candidate)
    require(
        isinstance(revision, int) and revision > 0,
        "VFY_CONTRACT_INVALID",
        "Revision must be a positive integer",
    )
    identifier = artifact_id or new_artifact_id()
    exact_artifact_reference(f"{identifier}@{revision}", "VFY")
    if base_revision is not None:
        require(
            isinstance(base_revision, int) and 0 < base_revision < revision,
            "VFY_CONTRACT_INVALID",
            "Base Revision must precede the new Revision",
        )

    methods = tuple(normalized["methods"])
    targets = tuple(normalized["targets"])
    method_results = [pending_result(method) for method in methods]
    target_conclusions = aggregate_target_conclusions(targets, methods, method_results)
    fixed_conclusions = aggregate_fixed_conclusions(targets, target_conclusions)
    product = product_result(fixed_conclusions)
    state = {
        "contract": STATE_CONTRACT,
        "artifact": {
            "id": identifier,
            "revision": revision,
            "reference": f"{identifier}@{revision}",
            "base_revision": base_revision,
            "revision_state": "open",
            "artifact_status": (
                "waiting_input"
                if any(item["result"] == "pending" for item in method_results)
                else "draft"
            ),
        },
        "context_reference": normalized["context_reference"],
        "profile": normalized["profile"],
        "title": normalized["title"],
        "scope": normalized["scope"],
        "subjects": normalized["subjects"],
        "subject_set_digest": subject_set_digest(tuple(normalized["subjects"])),
        "targets": normalized["targets"],
        "methods": normalized["methods"],
        "method_results": method_results,
        "target_conclusions": target_conclusions,
        "fixed_conclusions": fixed_conclusions,
        "product_result": product,
        "returns": normalized["returns"],
        "control_inputs": normalized["control_inputs"],
        "control_authorities": normalized["control_authorities"],
        "control_resolutions": normalized["control_resolutions"],
        "evidence": [],
        "supporting_members": [],
        "exceptions": normalized["exceptions"],
        "open_items": [],
        "early_stop": False,
        "early_stop_basis": None,
        "rls_applicability": normalized["rls_applicability"],
        "release_target_obligations": normalized["release_target_obligations"],
        "owner_artifact_inputs": normalized["owner_artifact_inputs"],
        "authority_compiled": normalized["authority_compiled"],
        "final_confirmation": None,
        "gate_checks": [],
        "artifact_gate": "pending",
        "rls_ready": False,
        "next_action": "RUN_PENDING_METHOD",
    }
    state["input_references"] = list(owner_artifact_inputs(state))
    state["pre_execution_contract_digest"] = state_contract_digest(state)
    reject_secrets(state)
    return state


def candidate_from_state(state: Mapping[str, Any]) -> dict[str, Any]:
    require(
        state.get("contract") == STATE_CONTRACT,
        "VFY_CONTRACT_INVALID",
        "Unsupported stored VFY state contract",
    )
    return {
        "contract": CANDIDATE_CONTRACT,
        "context_reference": state["context_reference"],
        "scope": deepcopy(state["scope"]),
        "subjects": deepcopy(state["subjects"]),
        "targets": deepcopy(state["targets"]),
        "methods": deepcopy(state["methods"]),
        "control_inputs": deepcopy(state["control_inputs"]),
        "control_authorities": deepcopy(state.get("control_authorities", [])),
        "control_resolutions": deepcopy(state.get("control_resolutions", [])),
        "returns": deepcopy(state["returns"]),
        "exceptions": deepcopy(state["exceptions"]),
        "rls_applicability": state["rls_applicability"],
        "release_target_obligations": deepcopy(state["release_target_obligations"]),
        "profile": state["profile"],
        "title": state["title"],
        "target_fallback_allowed": not any(
            item.get("source_kind") == "vfo" for item in state["targets"]
        ),
        "required_obligation_references": list(
            dict.fromkeys(
                reference
                for method in state["methods"]
                for reference in method["obligation_references"]
            )
        ),
        "owner_artifact_inputs": deepcopy(state.get("owner_artifact_inputs", [])),
        "authority_compiled": bool(state.get("authority_compiled")),
    }


def state_contract_digest(state: Mapping[str, Any]) -> str:
    return sha256_value(
        {
            "scope": state["scope"],
            "subjects": state["subjects"],
            "targets": state["targets"],
            "methods": state["methods"],
            "control_inputs": state["control_inputs"],
            "control_authorities": state.get("control_authorities", []),
            "exceptions": state.get("exceptions", []),
            "rls_applicability": state["rls_applicability"],
            "release_target_obligations": state["release_target_obligations"],
            "owner_artifact_inputs": state.get("owner_artifact_inputs", []),
        }
    )


def confirmation_subject_digest(state: Mapping[str, Any]) -> str:
    return sha256_value(
        {
            "artifact_reference": state["artifact"]["reference"],
            "pre_execution_contract_digest": state["pre_execution_contract_digest"],
            "subject_set_digest": state["subject_set_digest"],
            "method_results": state["method_results"],
            "target_conclusions": state["target_conclusions"],
            "fixed_conclusions": state["fixed_conclusions"],
            "product_result": state["product_result"],
            "returns": state["returns"],
            "control_resolutions": state.get("control_resolutions", []),
            "exceptions": state.get("exceptions", []),
            "early_stop": state["early_stop"],
            "early_stop_basis": state["early_stop_basis"],
            "rls_applicability": state["rls_applicability"],
            "release_target_obligations": state["release_target_obligations"],
        }
    )


def canonical_members(state: Mapping[str, Any]) -> tuple[CanonicalMember, ...]:
    member_state = deepcopy(dict(state))
    member_state["final_confirmation"] = None

    def member(member_id: str, name: str, value: Any) -> CanonicalMember:
        raw = canonical_bytes(value)
        return CanonicalMember(
            member_id=member_id,
            canonical_name=name,
            media_type="application/json",
            raw_bytes=raw,
            sha256=compute_sha256(raw),
        )

    members = [member("VFY-STATE", "vfy-state.json", member_state)]
    members.extend(
        member(
            f"VFY-EVIDENCE-{index:03d}",
            f"vfy-evidence-{index:03d}.json",
            evidence,
        )
        for index, evidence in enumerate(state.get("evidence", []), 1)
    )
    return tuple(sorted(members, key=lambda item: item.member_id))


def final_confirmation_from_payload(
    raw: bytes,
    state: Mapping[str, Any],
) -> dict[str, Any] | None:
    row = require_single_row(
        require_single_table(
            parse_canonical_artifact(raw),
            FINAL_CONFIRMATION_HEADERS,
            "Final Confirmation",
        ),
        "Final Confirmation",
    )
    if row["Result"] != "approved":
        return None
    return {
        "mode": row["Mode"],
        "confirmer": row["Confirmer"],
        "role": row["Role"],
        "authority_reference": row["Authority Reference"],
        "confirmed_at": row["Confirmed At"],
        "accepted_exception_references": list(
            parse_reference_set(row["Accepted Exception References"])
        ),
        "subject_digest": confirmation_subject_digest(state),
        "control_input_digest": row["Control Input Digest"],
        "evaluation_contract_set": row["Evaluation Contract Set"],
        "check_set_result_digest": row["Check Set Result Digest"],
        "contract_digest": state["pre_execution_contract_digest"],
        "subject_set_digest": state["subject_set_digest"],
        "product_result": state["product_result"],
        "method_result_digest": sha256_value(state["method_results"]),
        "return_digest": sha256_value(state["returns"]),
    }


def _evaluation_contract_set() -> str:
    return evaluation_contract_set(
        Path(__file__).resolve().parents[1] / "references/source-lock.json",
        (
            "sdlc-ai-spec/spec/core/v1.1",
            "sdlc-ai-spec/spec/artifact-store/v1.1",
            "sdlc-ai-spec/spec/vfy/v1.1",
            "sdlc-ai-spec/runtime/vfy/v1",
        ),
    )


def _projected_for_confirmation(state: Mapping[str, Any]) -> dict[str, Any]:
    projected = deepcopy(dict(state))
    has_exception = bool(projected.get("exceptions"))
    projected["artifact"] = deepcopy(dict(projected["artifact"]))
    projected["artifact"]["artifact_status"] = (
        "ready_with_exception" if has_exception else "ready"
    )
    projected["artifact"]["revision_state"] = "frozen"
    projected["artifact_gate"] = "pass_with_exception" if has_exception else "pass"
    projected["final_confirmation"] = {
        "mode": "human",
        "confirmer": "prospective-binding",
        "role": "Prospective Binding",
        "authority_reference": "prospective@sha256:" + "0" * 64,
        "accepted_exception_references": [
            f"{projected['artifact']['reference']}#{item['id']}"
            for item in projected.get("exceptions", [])
            if item.get("state") in {"active", "carried"}
        ],
        "confirmed_at": "1970-01-01T00:00:00Z",
    }
    return projected


def final_confirmation_bindings(
    state: Mapping[str, Any],
    *,
    members: Sequence[CanonicalMember] = (),
) -> dict[str, str]:
    prospective = _projected_for_confirmation(state)
    raw = render_markdown(prospective, members=members).encode("utf-8")
    return {
        "subject_digest": confirmation_subject_digest(state),
        "control_input_digest": compute_control_input_digest(raw),
        "evaluation_contract_set": _evaluation_contract_set(),
        "check_set_result_digest": compute_check_set_result_digest(
            parse_canonical_artifact(raw)
        ),
    }


def _evidence_projection(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in state.get("evidence", []):
        rows.append(
            {
                "id": item["id"],
                "type": "observation",
                "supports_references": [
                    item["method_id"],
                    *item["target_references"],
                    *item["subject_references"],
                ],
                "source": item["executor_identity"],
                "reference": item["reference"],
                "digest": item["sha256"],
                "produced_at": item["observed_at"],
                "sensitivity": "normal",
            }
        )
    return rows


def render_markdown(
    state: Mapping[str, Any],
    *,
    members: Sequence[CanonicalMember] = (),
) -> str:
    checks = {
        f"CORE-G-{index:03d}": CheckOutcome(
            "pass", "Canonical VFY records and immutable closure are verified"
        )
        for index in range(1, 9)
    }
    checks["CORE-G-009"] = CheckOutcome(
        "pass" if state.get("final_confirmation") else "pending",
        "Current Final Confirmation"
        if state.get("final_confirmation")
        else "Final Confirmation is required",
    )
    checks.update(
        {
            item["id"]: CheckOutcome(item["result"], item["note"])
            for item in state["gate_checks"]
        }
    )
    lifecycle = (
        {
            "phase": "RLS",
            "disposition": state["rls_applicability"],
            "host": "sdlc-600-rls",
            "basis": state["next_action"],
        },
    )
    raw = render_phase_artifact(
        artifact_id=state["artifact"]["id"],
        phase="VFY",
        revision=int(state["artifact"]["revision"]),
        status=state["artifact"]["artifact_status"],
        profile=state["profile"],
        phase_inputs=PhaseInputs(
            state["context_reference"],
            owner_artifact_inputs(state),
            (),
            tuple(item["reference"] for item in state["subjects"]),
        ),
        title=state["title"],
        sections=sections(state),
        checks=checks,
        open_items=state["open_items"],
        evidence=_evidence_projection(state),
        exceptions=state["exceptions"],
        lifecycle_applicability=lifecycle,
        final_confirmation=state.get("final_confirmation"),
        gate_result=state["artifact_gate"],
        evaluation_contract_set=_evaluation_contract_set(),
        evaluator="sdlc-500-vfy",
        members=members,
    )
    return raw.decode("utf-8")
