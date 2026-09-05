"""Common deterministic helpers for the VFY Runtime."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable, Mapping, Sequence


METHOD_TYPES = frozenset({"inspection", "analysis", "demonstration", "test"})
EXECUTION_MODES = frozenset({"automated", "manual", "hybrid"})
PURPOSES = frozenset({"verification", "validation", "both"})
DISPOSITIONS = frozenset({"required", "embedded", "n/a", "waived"})
RESULTS = frozenset({"pending", "pass", "fail", "n/a", "waived"})
RETURN_PHASES = frozenset({"REQ", "DSN", "PLN", "IMP"})

ARTIFACT_BASE_RE = re.compile(
    r"^(?P<phase>CTX|REQ|DSN|PLN|IMP|VFY|RLS)-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*$"
)
ITEM_REFERENCE_RE = re.compile(
    r"^(?:CTX|REQ|DSN|PLN|IMP|VFY|RLS)-[0-9]{14}-[0-9]{2,}@[1-9][0-9]*"
    r"(?:[#/][A-Za-z0-9._:+%-]+)?$"
)
VFY_METHOD_RE = re.compile(r"^VFM-[0-9]{3}$")
RETURN_ID_RE = re.compile(r"^RET-[0-9]{3}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
IMMUTABLE_LOCATOR_RE = re.compile(
    r"^(?:vcs:git:[0-9a-f]{40}|sha256:[0-9a-f]{64}|product:[A-Za-z0-9._:+%-]+@[A-Za-z0-9._:+%-]+)$"
)
MOVABLE_SELECTOR_RE = re.compile(
    r"(^|[/#\s])(latest|current|head|refs/heads|branch|tag|pull|pr\s*#?)($|[/#\s])",
    re.IGNORECASE,
)
SECRET_KEY_RE = re.compile(
    r"secret|token|password|passwd|cookie|credential|private.?key|access.?key",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16})"
)


class VfyError(ValueError):
    """Stable fail-closed domain error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: str = "blocked",
        action: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.action = action or code
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "status": self.status,
            "action": self.action,
            "details": deepcopy(self.details),
        }


def require(
    condition: bool,
    code: str,
    message: str,
    *,
    status: str = "blocked",
    action: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> None:
    if not condition:
        raise VfyError(
            code,
            message,
            status=status,
            action=action,
            details=details,
        )


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_text(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def stable_unique(values: Iterable[str], *, field: str = "reference") -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        require(
            isinstance(raw, str) and bool(raw.strip()),
            "VFY_CONTRACT_INVALID",
            f"{field} must be a non-empty string",
        )
        value = raw.strip()
        if value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)


def exact_artifact_reference(value: str, phase: str | None = None) -> str:
    require(
        isinstance(value, str) and bool(value.strip()),
        "VFY_REFERENCE_REQUIRED",
        "An exact Artifact Revision reference is required",
    )
    reference = value.strip()
    match = ARTIFACT_BASE_RE.fullmatch(reference)
    require(
        match is not None and not MOVABLE_SELECTOR_RE.search(reference),
        "VFY_REFERENCE_NOT_EXACT",
        "Reference must name an exact numeric Artifact Revision",
        details={"reference": reference},
    )
    if phase is not None:
        require(
            match.group("phase") == phase,
            "VFY_REFERENCE_NOT_EXACT",
            f"Expected an exact {phase} Artifact Revision",
            details={"reference": reference},
        )
    return reference


def exact_item_reference(value: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()),
        "VFY_REFERENCE_REQUIRED",
        "An exact Artifact or Item reference is required",
    )
    reference = value.strip()
    require(
        ITEM_REFERENCE_RE.fullmatch(reference) is not None
        and MOVABLE_SELECTOR_RE.search(reference) is None,
        "VFY_REFERENCE_NOT_EXACT",
        "Item reference is not exact",
        details={"reference": reference},
    )
    return reference


def reference_base(value: str) -> str:
    reference = exact_item_reference(value)
    return reference.split("#", 1)[0].split("/", 1)[0]


def immutable_locator(value: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()),
        "VFY_SUBJECT_NOT_CURRENT",
        "Subject locator is required",
    )
    locator = value.strip()
    if ITEM_REFERENCE_RE.fullmatch(locator):
        require(
            locator.startswith("IMP-")
            and ("/RES-" in locator or "/RESULT-RES-" in locator),
            "VFY_SUBJECT_NOT_CURRENT",
            "Artifact Subject must be an exact IMP Result Member",
            details={"reference": locator},
        )
        return locator
    require(
        IMMUTABLE_LOCATOR_RE.fullmatch(locator) is not None
        and MOVABLE_SELECTOR_RE.search(locator) is None,
        "VFY_SUBJECT_NOT_CURRENT",
        "Subject must use an immutable Product Result locator",
        details={"reference": locator},
    )
    return locator


def safe_project_path(value: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()),
        "VFY_METHOD_NOT_READY",
        "Project-relative path is required",
    )
    path = PurePosixPath(value.strip())
    require(
        not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in value
        and not any(part in {".git", ".sdlc"} for part in path.parts),
        "VFY_METHOD_NOT_READY",
        "Method path must remain inside the product workspace",
        details={"path": value},
    )
    return path.as_posix()


def contains_secret(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)) or contains_secret(item):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(contains_secret(item) for item in value)
    return isinstance(value, str) and SECRET_VALUE_RE.search(value) is not None


def reject_secrets(value: Any) -> None:
    require(
        not contains_secret(value),
        "VFY_SECRET_REJECTED",
        "Secret-like content cannot enter a VFY Artifact or Evidence",
    )


def redact_text(value: str, *, limit: int = 32768) -> str:
    text = SECRET_VALUE_RE.sub("[REDACTED]", str(value))
    if len(text) > limit:
        return text[:limit] + "\n[TRUNCATED]"
    return text


def load_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        result = deepcopy(dict(value))
    elif isinstance(value, (str, Path)):
        result = json.loads(Path(value).expanduser().read_text(encoding="utf-8"))
    else:
        raise VfyError("VFY_CONTRACT_INVALID", "JSON object or path is required")
    require(
        isinstance(result, dict),
        "VFY_CONTRACT_INVALID",
        "Input JSON must be an object",
    )
    reject_secrets(result)
    return result


def ensure_sequence(value: Any, *, field: str) -> Sequence[Any]:
    require(
        isinstance(value, list),
        "VFY_CONTRACT_INVALID",
        f"{field} must be an array",
    )
    return value
