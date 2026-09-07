"""Deterministic VFY control projection, separate from signed business material.

Canonical state members omit fields which change solely on Final Confirmation.
Consumers reconstruct those fields from actual Store and canonical Gate metadata.
This grants no authority: frozen readback and the existing validators still apply.
"""
from copy import deepcopy
from .canonical import (parse_canonical_artifact, require_single_row,
                        require_single_table, GATE_SUMMARY_HEADERS,
                        FINAL_CONFIRMATION_HEADERS)

PROJECTION = "sdlc-ai-spec/vfy-state-control-projection/v2"
CONTROL_FIELDS = ("final_confirmation", "artifact_gate", "rls_ready", "next_action")


def business_state(state):
    value = deepcopy(dict(state))
    value["control_projection"] = PROJECTION
    for key in CONTROL_FIELDS:
        value.pop(key, None)
    for key in ("revision_state", "artifact_status"):
        value["artifact"].pop(key, None)
    return value


def restore_control(state, primary, *, revision_state, artifact_status):
    value = deepcopy(dict(state))
    marker = value.pop("control_projection", None)
    value["artifact"].update(revision_state=revision_state, artifact_status=artifact_status)
    if marker is None:
        return value  # Historical full-state encoding, still checked by its readers.
    if marker != PROJECTION:
        raise ValueError("Unknown VFY control projection")
    parsed = parse_canonical_artifact(primary)
    gate = require_single_row(require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate"), "Gate")
    final = require_single_row(require_single_table(parsed, FINAL_CONFIRMATION_HEADERS, "Final Confirmation"), "Final Confirmation")
    value["artifact_gate"] = gate["Gate Result"]
    value["final_confirmation"] = None
    unresolved = [item for item in value.get("returns", []) if item.get("status") != "resolved"]
    controls = set(value.get("control_inputs", [])) - {str(item.get("control_reference")) for item in value.get("control_resolutions", []) if item.get("status") == "resolved"}
    pending = any(item.get("result") == "pending" for item in value["method_results"])
    eligible = value.get("product_result") in {"pass", "waived", "n/a"}
    if value.get("product_result") == "fail":
        eligible = any(item.get("state") in {"active", "carried"} and item.get("accepts_product_failure") is True and "product_result:fail" in item.get("scope", []) for item in value.get("exceptions", []))
    closed = final["Result"] == "approved" and value["artifact_gate"] in {"pass", "pass_with_exception"}
    value["rls_ready"] = bool(closed and not value.get("early_stop") and not unresolved and not controls and not pending and eligible and value["rls_applicability"] == "required")
    if value.get("early_stop"):
        action = "RETURN_UPSTREAM"
    elif unresolved or value.get("product_result") == "fail" and not eligible:
        action = "RETURN_TO_" + (str(unresolved[0]["return_phase"]) if unresolved else "UPSTREAM")
    elif controls:
        action = "RESOLVE_CONTROL_INPUT"
    elif pending:
        action = "RUN_PENDING_METHOD"
    elif not closed:
        action = "FINAL_CONFIRMATION_REQUIRED"
    elif value["rls_ready"]:
        action = "ENTER_RLS"
    elif value["rls_applicability"] in {"n/a", "waived"} and eligible:
        action = "LIFECYCLE_COMPLETE"
    else:
        action = "RESOLVE_RLS_APPLICABILITY"
    value["next_action"] = action
    return value
