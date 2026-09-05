"""VFY status projection adapter; preserves product/Gate/RLS distinctions."""
from __future__ import annotations

from typing import Any, Mapping

from packages.sdlc_lifecycle.query_vfy import project_vfy_state


def project_vfy_status(state: Mapping[str, Any] | None) -> dict[str, Any]:
    projection = project_vfy_state(state)
    return {
        "phase": "VFY",
        "artifact_reference": projection.artifact_reference,
        "revision_state": projection.revision_state,
        "artifact_status": projection.artifact_status,
        "product_result": projection.product_result,
        "artifact_gate": projection.artifact_gate,
        "early_stop": projection.early_stop,
        "unresolved_returns": list(projection.unresolved_returns),
        "rls_applicability": projection.rls_applicability,
        "rls_ready": projection.rls_ready,
        "next_phase": projection.next_phase,
        "next_action": projection.next_action,
        "return_phase": projection.return_phase,
        "display": {
            "product": f"Product Result: {projection.product_result}",
            "artifact": f"Artifact Gate: {projection.artifact_gate}",
            "downstream": (
                "RLS ready: yes" if projection.rls_ready else "RLS ready: no"
            ),
        },
    }
