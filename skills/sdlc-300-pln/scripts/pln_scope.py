"""Resolve exact frozen PLN scope and control inputs."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_phasekit import PhaseInputs, refs
from packages.sdlc_runtime import (
    ControlInputResolver,
    FrozenArtifactAuthorityVerifier,
    parse_canonical_artifact,
)
from packages.sdlc_runtime.canonical import find_tables

from pln_common import (
    APPLICABILITY_HEADERS,
    CHANGE_HEADERS,
    DISPOSITIONS,
    PHASE_RANK,
    PlnError,
    _artifact_items,
    _base,
    _merge_disposition,
)

def resolve_inputs(
    store: ArtifactStore,
    inputs: Mapping[str, Any],
    verifier_factory=FrozenArtifactAuthorityVerifier,
) -> PhaseInputs:
    scope = refs(inputs.get("scope_inputs"), "scope_inputs", required=True)
    controls = refs(inputs.get("control_inputs"), "control_inputs")
    verifier = verifier_factory(Path(store.project_root))
    context: str | None = None
    applicability: list[str] = []
    downstream: dict[str, list[Mapping[str, str]]] = {phase: [] for phase in PHASE_RANK}
    obligations: list[str] = []
    resources: list[str] = []

    for reference in scope:
        exact = _base(reference)
        if reference != exact:
            raise PlnError("PLN Scope Input must be a complete Artifact Revision, not an item/member")
        if not exact.startswith(("REQ-", "DSN-")):
            raise PlnError(f"unsupported PLN Scope Input type: {reference}")
        resolved = store.resolve_exact_reference(exact, verifier=verifier)
        parsed = parse_canonical_artifact(resolved.revision.payload.primary_blob)
        candidate_context = parsed.front_matter.get("context")
        if not isinstance(candidate_context, str):
            raise PlnError(f"Scope Input has no CTX binding: {reference}")
        if context is None:
            context = candidate_context
        elif context != candidate_context:
            raise PlnError("PLN Scope Inputs belong to different CTX revisions")

        app_tables = find_tables(parsed, APPLICABILITY_HEADERS)
        if len(app_tables) != 1:
            raise PlnError(f"Scope Input has no unique Lifecycle Applicability: {reference}")
        by_phase = {row["Phase"]: row for row in app_tables[0].rows}
        pln_row = by_phase.get("PLN")
        if pln_row is None or pln_row["Disposition"] not in DISPOSITIONS:
            raise PlnError(f"PLN Applicability is invalid: {reference}")
        applicability.append(pln_row["Disposition"])
        for phase in PHASE_RANK:
            row = by_phase.get(phase)
            if row is not None:
                downstream[phase].append(row)

        obligations.extend(_artifact_items(exact, parsed, resolved.revision.payload.members))
        for change_table in find_tables(parsed, CHANGE_HEADERS):
            for row in change_table.rows:
                token = row["Object or Boundary"].strip()
                if token.startswith("resource:"):
                    resources.append(token)

    if context is None:
        raise PlnError("PLN requires at least one complete REQ or DSN Scope Input")

    resolver = ControlInputResolver(Path(store.project_root))
    for reference in controls:
        resolver.resolve_for_phase(store, reference, "PLN")
        obligations.append(reference)

    aggregate_rows: list[dict[str, str]] = []
    for phase in PHASE_RANK:
        phase_rows = downstream[phase]
        dispositions = [row["Disposition"] for row in phase_rows]
        disposition = _merge_disposition(dispositions)
        bases = tuple(dict.fromkeys(row["判断依据 Basis"] for row in phase_rows))
        hosts = tuple(dict.fromkeys(row["Host"] for row in phase_rows if row["Host"] not in {"", "N/A"}))
        aggregate_rows.append({
            "phase": phase,
            "disposition": disposition,
            "host": ", ".join(hosts) or "N/A",
            "basis": "; ".join(bases) or "Aggregated from authoritative Scope Inputs",
        })
    # VFY is a mandatory control point even when a weak upstream producer omitted it.
    vfy = next(item for item in aggregate_rows if item["phase"] == "VFY")
    if vfy["disposition"] not in {"required", "pending"}:
        vfy["disposition"] = "required"
        vfy["basis"] = "VFY is the mandatory lifecycle control point"

    return PhaseInputs(
        context_reference=context,
        scope_references=scope,
        control_references=controls,
        metadata={
            "pln_disposition": _merge_disposition(applicability),
            "authoritative_obligations": tuple(dict.fromkeys(obligations)),
            "declared_resources": tuple(dict.fromkeys(resources)),
            "aggregated_applicability": tuple(aggregate_rows),
        },
    )
