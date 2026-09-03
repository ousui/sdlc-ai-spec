"""Normalize PLN candidate data and evaluate deterministic contract checks."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from packages.sdlc_phasekit import CheckOutcome, PhaseInputs, refs, rows, text

from pln_common import (
    CORE_CHECKS,
    DISPOSITIONS,
    GENERIC_COMPLETION,
    GENERIC_EVIDENCE,
    PHASE_RANK,
    PLN_CHECKS,
    WORK_ALLOWED,
    PlnError,
)

def _outcome(result: str, message: str) -> CheckOutcome:
    return CheckOutcome(result=result, message=message)


def _check_graph(work_items: Sequence[Mapping[str, Any]]) -> tuple[bool, str]:
    by_id = {str(item.get("id")): item for item in work_items}
    if len(by_id) != len(work_items):
        return False, "duplicate Work Item ID"
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identity: str):
        if identity in visiting:
            raise PlnError("Work Item dependency cycle")
        if identity in visited:
            return
        visiting.add(identity)
        current = by_id[identity]
        current_rank = PHASE_RANK.get(str(current.get("target_phase")), 99)
        for dependency in refs(current.get("depends_on"), f"{identity}.depends_on"):
            target = by_id.get(dependency)
            if target is None:
                raise PlnError(f"unknown Work Item dependency: {dependency}")
            if dependency == identity:
                raise PlnError("Work Item cannot depend on itself")
            if PHASE_RANK.get(str(target.get("target_phase")), 99) > current_rank:
                raise PlnError("Work Item dependency points to a later Phase")
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)

    try:
        for identity in by_id:
            visit(identity)
    except PlnError as exc:
        return False, str(exc)
    return True, "dependency graph is acyclic and respects Phase order"


def _resource_tokens(item: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(token for token in refs(item.get("execution_scope"), "execution_scope", required=True) if token.startswith("resource:"))


def _analyze(candidate: Mapping[str, Any], phase_inputs: PhaseInputs):
    value = deepcopy(dict(candidate))
    disposition = str(value.get("pln_disposition") or "")
    if disposition not in DISPOSITIONS:
        raise PlnError("pln_disposition is invalid")
    authoritative_disposition = str(phase_inputs.metadata.get("pln_disposition"))
    if disposition != authoritative_disposition:
        raise PlnError(
            f"candidate PLN disposition {disposition!r} does not match authoritative Scope disposition {authoritative_disposition!r}"
        )

    checks = {item: _outcome("pass", "validated") for item in (*CORE_CHECKS, *PLN_CHECKS)}
    open_items = rows(value.get("open_items"), "open_items")
    exceptions = rows(value.get("exceptions"), "exceptions")
    active_exceptions = tuple(
        str(item.get("id")) for item in exceptions
        if item.get("state") in {"active", "carried"} and item.get("id")
    )
    work_items = rows(value.get("work_items"), "work_items")
    delivery_scope = rows(value.get("delivery_scope"), "delivery_scope")
    lifecycle = rows(value.get("lifecycle_applicability"), "lifecycle_applicability")
    aggregated = rows(value.get("aggregated_applicability"), "aggregated_applicability")
    obligations = refs(value.get("obligations"), "obligations")
    authoritative_obligations = tuple(phase_inputs.metadata.get("authoritative_obligations") or ())

    if disposition != "required":
        if work_items:
            checks["PLN-G-005"] = _outcome("fail", "non-required PLN cannot contain Work Items")
        value.update({
            "work_items": work_items,
            "delivery_scope": delivery_scope,
            "lifecycle_applicability": lifecycle,
            "aggregated_applicability": aggregated,
            "obligations": list(obligations),
            "open_items": open_items,
            "exceptions": exceptions,
        })
        return value, checks, open_items, active_exceptions

    if not delivery_scope:
        checks["PLN-G-001"] = _outcome("fail", "Delivery Scope is missing")
    if set(obligations) != set(authoritative_obligations):
        checks["PLN-G-002"] = _outcome("fail", "Plan obligations do not exactly cover authoritative upstream obligations")

    # Fixed Work Item fields, stable IDs and atomic completion/evidence semantics.
    seen_ids: set[str] = set()
    semantic_keys: set[tuple[Any, ...]] = set()
    role_pending = False
    for index, item in enumerate(work_items, start=1):
        extra = set(item) - WORK_ALLOWED
        if extra:
            checks["PLN-G-003"] = _outcome("fail", f"Work Item contains unsupported authority fields: {', '.join(sorted(extra))}")
        identity = str(item.get("id") or "")
        if identity != f"WI-{index:03d}" or identity in seen_ids:
            checks["PLN-G-003"] = _outcome("fail", "Work Item IDs must be unique sequential WI-NNN values")
        seen_ids.add(identity)
        phase = str(item.get("target_phase") or "")
        if phase not in PHASE_RANK:
            checks["PLN-G-003"] = _outcome("fail", f"invalid Work Item Target Phase: {identity}")
        try:
            outcome = text(item.get("outcome"), f"{identity}.outcome")
            scope = refs(item.get("execution_scope"), f"{identity}.execution_scope", required=True)
            sources = refs(item.get("source_references"), f"{identity}.source_references", required=True)
            constraints = refs(item.get("constraint_references"), f"{identity}.constraint_references")
            depends = refs(item.get("depends_on"), f"{identity}.depends_on")
            completion = text(item.get("completion_criteria"), f"{identity}.completion_criteria")
            expected = text(item.get("expected_evidence"), f"{identity}.expected_evidence")
        except Exception as exc:
            checks["PLN-G-003"] = _outcome("fail", str(exc))
            outcome, scope, sources, constraints, depends, completion, expected = "", (), (), (), (), "", ""
        role = str(item.get("responsible_role") or "").strip()
        if not role:
            role_pending = True
        if completion.casefold() in GENERIC_COMPLETION or len(completion.split()) < 3:
            checks["PLN-G-003"] = _outcome("fail", "Completion Criteria is not independently decidable")
        if expected.casefold() in GENERIC_EVIDENCE or len(expected.split()) < 2:
            checks["PLN-G-003"] = _outcome("fail", "Expected Evidence is not reproducible")
        if any(reference not in authoritative_obligations for reference in (*sources, *constraints)):
            checks["PLN-G-006"] = _outcome("fail", "Work Item introduces a source/constraint outside authoritative scope")
        resources = tuple(token for token in scope if token.startswith("resource:"))
        paths = tuple(token for token in scope if token.startswith("path:"))
        environments = tuple(token for token in scope if token.startswith("environment:"))
        if phase == "IMP" and not resources:
            checks["PLN-G-004"] = _outcome("fail", "IMP Work Item requires at least one versioned resource token")
        if phase == "RLS" and len(environments) != 1:
            checks["PLN-G-003"] = _outcome("fail", "RLS Work Item requires exactly one environment token")
        if phase != "RLS" and environments:
            checks["PLN-G-003"] = _outcome("fail", "only RLS Work Items may own environment tokens")
        resource_ids = {token.split(":", 1)[1] for token in resources}
        for token in paths:
            parts = token.split("/", 1)
            prefix = parts[0]
            rid = prefix.split(":", 1)[1] if ":" in prefix else ""
            if rid not in resource_ids:
                checks["PLN-G-004"] = _outcome("fail", f"path token is outside its declared resource: {token}")
        semantic = (
            phase, outcome.casefold(), tuple(sorted(scope)), tuple(sorted(sources)),
            completion.casefold(), expected.casefold(),
        )
        if semantic in semantic_keys:
            checks["PLN-G-003"] = _outcome("fail", "duplicate semantic Work Item")
        semantic_keys.add(semantic)
        item.update({
            "id": identity, "target_phase": phase, "outcome": outcome,
            "execution_scope": list(scope), "source_references": list(sources),
            "constraint_references": list(constraints), "depends_on": list(depends),
            "completion_criteria": completion, "expected_evidence": expected,
            "responsible_role": role,
        })

    graph_ok, graph_message = _check_graph(work_items)
    if not graph_ok:
        checks["PLN-G-004"] = _outcome("fail", graph_message)

    # Shared resources form a deterministic direct dependency chain in Plan order.
    by_resource: dict[str, list[Mapping[str, Any]]] = {}
    for item in work_items:
        if item.get("target_phase") != "IMP":
            continue
        for resource in _resource_tokens(item):
            by_resource.setdefault(resource, []).append(item)
    for resource, grouped in by_resource.items():
        for previous, current in zip(grouped, grouped[1:]):
            if previous.get("id") not in refs(current.get("depends_on"), "depends_on"):
                checks["PLN-G-004"] = _outcome("fail", f"shared {resource} IMP Work Items require a direct dependency chain")

    lifecycle_by_phase = {str(item.get("phase")): item for item in lifecycle}
    work_by_phase = {phase: [item for item in work_items if item.get("target_phase") == phase] for phase in PHASE_RANK}
    for phase in PHASE_RANK:
        row = lifecycle_by_phase.get(phase)
        if row is None or row.get("disposition") not in DISPOSITIONS:
            checks["PLN-G-005"] = _outcome("fail", f"Lifecycle Applicability is missing or invalid for {phase}")
            continue
        disposition_value = row.get("disposition")
        if phase == "VFY" and disposition_value != "required":
            checks["PLN-G-005"] = _outcome("fail", "VFY must always be required")
        if disposition_value == "required" and not work_by_phase[phase]:
            checks["PLN-G-005"] = _outcome("fail", f"required {phase} has no Work Item")
        if disposition_value in {"n/a", "embedded", "waived"} and work_by_phase[phase]:
            checks["PLN-G-005"] = _outcome("fail", f"non-required {phase} contains a pseudo Work Item")

    covered = {reference for item in work_items for reference in refs(item.get("source_references"), "sources")}
    if set(authoritative_obligations) - covered:
        checks["PLN-G-002"] = _outcome("fail", "one or more authoritative obligations are not covered by Work Items")

    if role_pending and checks["PLN-G-003"].result != "fail":
        checks["PLN-G-003"] = _outcome("pending", "Responsible Role requires an explicit authority decision")
        open_items.append({
            "id": f"OPI-{len(open_items)+1:03d}",
            "needed": "Assign a responsible role to every Work Item",
            "expected_source": "Plan Authority",
            "blocked_references": "PLN-G-003",
            "state": "open",
            "resolution": "N/A",
        })

    value.update({
        "work_items": work_items,
        "delivery_scope": delivery_scope,
        "lifecycle_applicability": lifecycle,
        "aggregated_applicability": aggregated,
        "obligations": list(obligations),
        "open_items": open_items,
        "exceptions": exceptions,
    })
    return value, checks, open_items, active_exceptions
