"""Pure RLS value helpers, exact references, canonical JSON and stable errors."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from dataclasses import asdict, is_dataclass
import hashlib
import json
import re
from typing import Any, Iterable


class RlsError(Exception):
    """Stable domain failure used by the provisional RLS Runtime."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": self.details}


def require(condition: bool, code: str, message: str, **details: Any) -> None:
    if not condition:
        raise RlsError(code, message, **details)


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_reference(value: Any) -> str:
    """Return the repository-wide prefixed digest representation."""
    return "sha256:" + sha256_value(value)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_unique(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        require(
            isinstance(raw, str) and raw.strip(),
            "RLS_CONTRACT_INVALID",
            "reference/item must be a non-empty string",
        )
        value = raw.strip()
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_time(value: str) -> datetime:
    require(
        isinstance(value, str) and value,
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "authorization time is missing",
    )
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RlsError(
            "RLS_EFFECT_AUTHORIZATION_STALE", "authorization time is invalid"
        ) from exc
    require(
        result.tzinfo is not None,
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "authorization time must include a timezone",
    )
    return result


_EXACT = {
    "CTX": re.compile(r"^CTX-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*$"),
    "VFY": re.compile(r"^VFY-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*$"),
    "RLS": re.compile(r"^RLS-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*$"),
    "RLI": re.compile(r"^RLI-[0-9]{3}$"),
    "RCF": re.compile(r"^RCF-[0-9]{3}$"),
}
_SCOPE_REFERENCE = re.compile(
    r"^(?:REQ|DSN|PLN)-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*$"
)
_EXCEPTION_REFERENCE = re.compile(
    r"^(?:CTX|REQ|DSN|PLN|IMP|VFY|RLS)-[0-9]{14}-[0-9]{2,}"
    r"@[1-9][0-9]*#EX-[0-9]{3}$"
)
_DIGEST_REFERENCE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_SELECTOR = re.compile(
    r"(^|[/#\s])(latest|current|head|refs/heads|branch|tag|pull|pr\s*#?)($|[/#\s])",
    re.IGNORECASE,
)


def exact_reference(value: str, kind: str) -> str:
    require(
        isinstance(value, str) and value.strip(),
        "RLS_REFERENCE_REQUIRED",
        f"{kind} reference is required",
    )
    normalized = value.strip()
    require(
        not _FORBIDDEN_SELECTOR.search(normalized),
        "RLS_REFERENCE_NOT_EXACT",
        "movable/routing selector is not authority",
        value=normalized,
    )
    require(
        kind in _EXACT and bool(_EXACT[kind].fullmatch(normalized)),
        "RLS_REFERENCE_NOT_EXACT",
        f"invalid exact {kind} reference",
        value=normalized,
    )
    return normalized


def exact_scope_reference(value: str) -> str:
    require(
        isinstance(value, str)
        and bool(_SCOPE_REFERENCE.fullmatch(value.strip()))
        and not _FORBIDDEN_SELECTOR.search(value.strip()),
        "RLS_SCOPE_MISMATCH",
        "VFY Scope must be one exact REQ/DSN/PLN Artifact Revision",
        value=value,
    )
    return value.strip()


def exact_exception_reference(value: str) -> str:
    require(
        isinstance(value, str)
        and bool(_EXCEPTION_REFERENCE.fullmatch(value.strip()))
        and not _FORBIDDEN_SELECTOR.search(value.strip()),
        "RLS_VFY_NOT_READY",
        "VFY Exception reference is not exact",
        value=value,
    )
    return value.strip()


def digest_reference(value: str) -> str:
    require(
        isinstance(value, str) and bool(_DIGEST_REFERENCE.fullmatch(value.strip())),
        "RLS_VFY_NOT_READY",
        "VFY source digest must use sha256:<64hex>",
        value=value,
    )
    return value.strip()


_SECRET_KEY = re.compile(
    r"(secret|token|password|passwd|cookie|credential|private.?key|authorization_header)",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._~+/=-]{16,})"
)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _SECRET_KEY.search(str(key)) else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    return deepcopy(value)


def assert_no_secret(value: Any) -> None:
    require(
        sanitize(value) == value,
        "RLS_SECRET_REJECTED",
        "secret-like content cannot enter an RLS Artifact",
    )


def deep_copy(value: Any) -> Any:
    return deepcopy(value)
