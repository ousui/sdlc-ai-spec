"""Small, secret-safe result and error vocabulary for the GitHub boundary."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

CONTRACT = "sdlc-ai-spec/github-result/v1"
MAX_RESULT = 256 * 1024
MAX_TEXT = 1024 * 1024
TIMEOUT = 60.0

MESSAGES = {
    "AUTH_REQUIRED": "Set SDLC_GITHUB_TOKEN in the host environment, then restart this instance.",
    "AUTH_FAILED": "GitHub rejected authentication; verify the credential outside the conversation.",
    "PERMISSION_DENIED": "The authenticated account cannot perform this operation.",
    "NOT_FOUND_OR_INACCESSIBLE": "The exact target was not found or is not accessible.",
    "RATE_LIMITED": "GitHub rate limit reached; wait and explicitly retry the read or inspect the receipt.",
    "TIMEOUT": "The bounded upstream request timed out.",
    "DISCONNECTED": "The upstream MCP session disconnected.",
    "UPSTREAM_FAILED": "The upstream operation failed; no automatic write retry was attempted.",
    "UPSTREAM_INVALID": "The upstream response does not satisfy this operation's contract.",
    "CAPABILITY_UNAVAILABLE": "A required upstream tool or parameter schema is incompatible.",
    "ARGUMENT_INVALID": "Parameters do not match the fixed operation schema; consult help.",
    "TARGET_MISMATCH": "Repository, URL, object type or exact target disagrees.",
    "TARGET_REQUIRED": "Provide one exact repository and target; no default was guessed.",
    "REF_AMBIGUOUS": "File URL requires an exact ref and path, or an exact commit SHA.",
    "ACTOR_MISMATCH": "The verified actor differs from expected_actor_id; obtain status again.",
    "IDENTITY_REQUIRED": "Run status in this instance before reading a local receipt.",
    "WRITE_DENIED": "write_policy=deny prohibits this remote effect.",
    "REQUEST_CONFLICT": "This request_id is already bound to different parameters.",
    "EFFECT_UNKNOWN": "An intent exists without a verified terminal effect. Do not replay; reconcile read-only.",
    "RECORD_CORRUPT": "Local operation state is invalid; preserve it and investigate without replay.",
    "STORAGE_UNSAFE": "Data root or state entry is not a safe private filesystem object.",
    "STORAGE_FAILED": "Durable local state could not be read or written.",
    "RECEIPT_NOT_FOUND": "No operation record exists for this actor, repository and request_id.",
    "READBACK_FAILED": "GitHub confirmed a write but exact readback verification is incomplete.",
    "RESULT_LIMIT": "The result exceeded a bounded response limit; the result is not complete.",
    "SECRET_IN_INPUT": "The request contains credential-shaped content; remove it before sending.",
    "DEPENDENCY_UNAVAILABLE": "Install the bundled exact dependency lock in a build environment.",
}


class GithubError(Exception):
    def __init__(self, code: str, *, effect: str = "none") -> None:
        self.code = code
        self.effect = effect
        super().__init__(MESSAGES.get(code, code))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


_PAT = re.compile(r"(?:github_pat_[A-Za-z0-9_]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|$))")
_HEADER = re.compile(r"(?i)(authorization\s*[:=]\s*(?:bearer|token)\s+)[^\s\"',}]+")


def redact(value: Any, token: str = "") -> Any:
    if isinstance(value, str):
        if token:
            value = value.replace(token, "[REDACTED]")
        return _HEADER.sub(r"\1[REDACTED]", _PAT.sub("[REDACTED]", value))
    if isinstance(value, list):
        return [redact(x, token) for x in value]
    if isinstance(value, dict):
        return {redact(str(k), token): ("[REDACTED]" if str(k).lower() in {"authorization", "token", "cookie", "password", "private_key"} else redact(v, token)) for k, v in value.items()}
    return value


def ensure_no_secret(value: Any, token: str = "") -> None:
    if redact(value, token) != value:
        raise GithubError("SECRET_IN_INPUT")


def result(operation: str, *, actor=None, repository=None, target=None, data=None,
           status="completed", effect="none", receipt=None, pagination=None,
           completeness="complete", errors=None, warnings=None, next_action=None) -> dict:
    return {"contract": CONTRACT, "ok": status == "completed", "status": status,
            "operation": operation, "actor": actor, "repository": repository, "target": target,
            "data": data, "pagination": pagination or {"mode": "none", "has_more": False, "next_page": None, "next_cursor": None},
            "completeness": completeness, "effect": effect, "receipt": receipt,
            "errors": errors or [], "warnings": warnings or [], "next_action": next_action}


def failure(operation: str, error: GithubError, **context) -> dict:
    status = "unknown" if error.effect == "unknown" else "blocked"
    if error.code in {"UPSTREAM_FAILED", "UPSTREAM_INVALID", "DISCONNECTED", "TIMEOUT"} and error.effect == "none":
        status = "failed"
    if error.code == "RESULT_LIMIT" and error.effect == "none":
        status = "partial"
    return result(operation, status=status, effect=error.effect, completeness="unknown",
                  errors=[{"code": error.code, "message": str(error)}],
                  next_action="Inspect operation_status without replay." if error.effect == "unknown" else str(error), **context)
