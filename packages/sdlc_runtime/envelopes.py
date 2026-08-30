"""Stable invocation/result envelope helpers for SDLC Phase runtimes."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

INVOCATION_CONTRACT = "sdlc-ai-spec/runtime-invocation/v1"
RESULT_CONTRACT = "sdlc-ai-spec/runtime-result/v1"
OPERATIONS = frozenset({"create", "revise", "check"})
RESULT_STATUSES = frozenset({"completed", "action_required", "blocked", "failed"})
GATE_RESULTS = frozenset({"pending", "pass", "pass_with_exception", "fail"})


class EnvelopeValidationError(ValueError):
    """Raised when a runtime envelope violates the shared contract."""

    code = "INVALID_ENVELOPE"


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EnvelopeValidationError(f"{name} must be an object")
    return value


def _check_allowed_keys(value: Mapping[str, Any], allowed: set[str], name: str) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise EnvelopeValidationError(
            f"{name} contains unsupported fields: {', '.join(extra)}"
        )


def validate_invocation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a defensive copy of an invocation envelope."""

    payload = _require_mapping(value, "invocation")
    required = {"contract", "operation", "project_root", "inputs"}
    allowed = required | {"artifact_reference", "confirmations", "options"}
    _check_allowed_keys(payload, allowed, "invocation")
    missing = sorted(required - set(payload))
    if missing:
        raise EnvelopeValidationError(
            f"invocation is missing required fields: {', '.join(missing)}"
        )
    if payload["contract"] != INVOCATION_CONTRACT:
        raise EnvelopeValidationError(f"contract must be {INVOCATION_CONTRACT}")
    operation = payload["operation"]
    if operation not in OPERATIONS:
        raise EnvelopeValidationError(
            f"operation must be one of: {', '.join(sorted(OPERATIONS))}"
        )
    project_root = payload["project_root"]
    if not isinstance(project_root, str) or not project_root.strip():
        raise EnvelopeValidationError("project_root must be a non-empty string")
    if not Path(project_root).expanduser().is_absolute():
        raise EnvelopeValidationError("project_root must be an absolute path")
    artifact_reference = payload.get("artifact_reference")
    if artifact_reference is not None and not isinstance(artifact_reference, str):
        raise EnvelopeValidationError("artifact_reference must be a string or null")
    _require_mapping(payload["inputs"], "inputs")
    confirmations = payload.get("confirmations", [])
    if not isinstance(confirmations, list) or any(
        not isinstance(item, Mapping) for item in confirmations
    ):
        raise EnvelopeValidationError("confirmations must be an array of objects")
    options = payload.get("options", {})
    _require_mapping(options, "options")
    if "dry_run" in options and not isinstance(options["dry_run"], bool):
        raise EnvelopeValidationError("options.dry_run must be a boolean")
    result = deepcopy(dict(payload))
    result.setdefault("artifact_reference", None)
    result.setdefault("confirmations", [])
    result.setdefault("options", {"dry_run": False})
    if "dry_run" not in result["options"]:
        result["options"]["dry_run"] = False
    return result


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a defensive copy of a result envelope."""

    payload = _require_mapping(value, "result")
    required = {
        "contract",
        "ok",
        "operation",
        "status",
        "artifact",
        "gate",
        "open_items",
        "warnings",
        "errors",
        "next_action",
    }
    _check_allowed_keys(payload, required, "result")
    missing = sorted(required - set(payload))
    if missing:
        raise EnvelopeValidationError(
            f"result is missing required fields: {', '.join(missing)}"
        )
    if payload["contract"] != RESULT_CONTRACT:
        raise EnvelopeValidationError(f"contract must be {RESULT_CONTRACT}")
    if not isinstance(payload["ok"], bool):
        raise EnvelopeValidationError("ok must be a boolean")
    if payload["operation"] not in OPERATIONS:
        raise EnvelopeValidationError("result operation is invalid")
    if payload["status"] not in RESULT_STATUSES:
        raise EnvelopeValidationError("result status is invalid")

    artifact = payload["artifact"]
    if artifact is not None:
        artifact = _require_mapping(artifact, "artifact")
        artifact_allowed = {
            "id",
            "type",
            "revision",
            "revision_state",
            "artifact_status",
            "reference",
        }
        _check_allowed_keys(artifact, artifact_allowed, "artifact")
        revision = artifact.get("revision")
        if revision is not None and (
            not isinstance(revision, int) or isinstance(revision, bool) or revision < 1
        ):
            raise EnvelopeValidationError(
                "artifact.revision must be a positive integer or null"
            )

    gate = _require_mapping(payload["gate"], "gate")
    _check_allowed_keys(gate, {"result", "failed_checks"}, "gate")
    if set(gate) != {"result", "failed_checks"}:
        raise EnvelopeValidationError("gate requires result and failed_checks")
    if gate["result"] not in GATE_RESULTS:
        raise EnvelopeValidationError("gate.result is invalid")
    if not isinstance(gate["failed_checks"], list) or any(
        not isinstance(item, str) or not item for item in gate["failed_checks"]
    ):
        raise EnvelopeValidationError("gate.failed_checks must be an array of strings")

    for name in ("open_items", "warnings"):
        if not isinstance(payload[name], list) or any(
            not isinstance(item, Mapping) for item in payload[name]
        ):
            raise EnvelopeValidationError(f"{name} must be an array of objects")

    errors = payload["errors"]
    if not isinstance(errors, list):
        raise EnvelopeValidationError("errors must be an array")
    for item in errors:
        item = _require_mapping(item, "error")
        _check_allowed_keys(item, {"code", "message", "details"}, "error")
        if not isinstance(item.get("code"), str) or not item["code"]:
            raise EnvelopeValidationError("error.code must be a non-empty string")
        if not isinstance(item.get("message"), str) or not item["message"]:
            raise EnvelopeValidationError("error.message must be a non-empty string")

    next_action = payload["next_action"]
    if next_action is not None:
        next_action = _require_mapping(next_action, "next_action")
        _check_allowed_keys(
            next_action,
            {"code", "message", "requires_user", "command"},
            "next_action",
        )
        for field in ("code", "message", "requires_user"):
            if field not in next_action:
                raise EnvelopeValidationError(f"next_action requires {field}")
        if not isinstance(next_action["code"], str) or not next_action["code"]:
            raise EnvelopeValidationError("next_action.code must be non-empty")
        if not isinstance(next_action["message"], str) or not next_action["message"]:
            raise EnvelopeValidationError("next_action.message must be non-empty")
        if not isinstance(next_action["requires_user"], bool):
            raise EnvelopeValidationError("next_action.requires_user must be boolean")
        if next_action.get("command") is not None and not isinstance(
            next_action["command"], str
        ):
            raise EnvelopeValidationError("next_action.command must be a string or null")

    if payload["ok"] and errors:
        raise EnvelopeValidationError("successful result must not contain errors")
    if payload["status"] == "completed" and not payload["ok"]:
        raise EnvelopeValidationError("completed result must set ok=true")
    return deepcopy(dict(payload))


def error_result(
    *,
    operation: str,
    status: str,
    code: str,
    message: str,
    next_action_code: str,
    next_action_message: str,
    requires_user: bool,
    details: Any = None,
) -> dict[str, Any]:
    """Build a deterministic failure/action-required result."""

    if operation not in OPERATIONS:
        raise EnvelopeValidationError("operation is invalid")
    if status not in RESULT_STATUSES - {"completed"}:
        raise EnvelopeValidationError("error result status is invalid")
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return validate_result(
        {
            "contract": RESULT_CONTRACT,
            "ok": False,
            "operation": operation,
            "status": status,
            "artifact": None,
            "gate": {"result": "pending", "failed_checks": []},
            "open_items": [],
            "warnings": [],
            "errors": [error],
            "next_action": {
                "code": next_action_code,
                "message": next_action_message,
                "requires_user": requires_user,
                "command": None,
            },
        }
    )
