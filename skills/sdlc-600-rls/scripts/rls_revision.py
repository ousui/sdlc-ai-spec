"""VFY candidate delta detection for RLS Revision decisions."""
from __future__ import annotations

from typing import Any


def candidate_release_binding(candidate) -> dict[str, Any]:
    """Project one normalized VFY candidate onto immutable RLS Contract fields."""
    return {
        **({"obligation_source_references": list(candidate.obligation_sources)} if candidate.authority_verified else {}),
        "vfy_reference": candidate.vfy_reference,
        "vfy_conclusions": {
            "con_ver": candidate.con_ver,
            "con_val": candidate.con_val,
            "product_result": candidate.product_result,
            "artifact_status": candidate.artifact_status,
            "artifact_gate": candidate.artifact_gate,
        },
        "vfy_candidate_provisional": candidate.provisional,
        "vfy_rls_ready": candidate.rls_ready,
        "vfy_source_digest": candidate.source_digest,
        "vfy_candidate_digest": candidate.candidate_digest,
        "vfy_exception_references": list(candidate.exception_references),
        "release_target_obligations": [
            dict(row) for row in candidate.release_target_obligations
        ],
    }


def candidate_contract_delta(
    release_contract: dict,
    candidate,
) -> list[str]:
    """Return every immutable VFY-derived Contract field that changed."""
    expected = candidate_release_binding(candidate)
    return [
        field
        for field, value in expected.items()
        if release_contract.get(field) != value
    ]
