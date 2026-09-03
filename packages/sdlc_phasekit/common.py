"""Deterministic, dependency-free primitives for late Phase Skills."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from packages.sdlc_artifact_store import CanonicalMember, compute_sha256
from packages.sdlc_runtime import authority_reference, sha256_bytes
from packages.sdlc_runtime.authority import (
    IDENTITY_TOKEN_RE, is_rfc3339, validate_delegated_authority_record,
)

SECRET_RE = re.compile(
    r"(?i)(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:password|passwd|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*[^\s|]{6,})"
)


class PhaseKitError(ValueError):
    code = "PHASE_RUNTIME_ERROR"


def text(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise PhaseKitError(f"{name} must be text")
    result = value.strip()
    if not result and not allow_empty:
        raise PhaseKitError(f"{name} must not be empty")
    return result


def rows(value: Any, name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise PhaseKitError(f"{name} must be an array of objects")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            raise PhaseKitError(f"{name}[{index}] must be an object")
        result.append(dict(item))
    return result


def refs(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if value is None:
        items: list[str] = []
    elif isinstance(value, str):
        raw = value.strip()
        if raw in {"", "None", "N/A"}:
            items = []
        else:
            items = [part.strip() for part in raw.split(",")]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        items = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise PhaseKitError(f"{name} must contain non-empty references")
            items.append(item.strip())
    else:
        raise PhaseKitError(f"{name} must be a reference or reference array")
    if any(not item for item in items):
        raise PhaseKitError(f"{name} contains an empty reference")
    deduped = tuple(dict.fromkeys(items))
    if required and not deduped:
        raise PhaseKitError(f"{name} requires at least one reference")
    return deduped


def _json_default(value: Any):
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"unsupported deterministic JSON value: {type(value).__name__}")


def subject_digest(candidate: Mapping[str, Any], bindings: Mapping[str, Any]) -> str:
    if not isinstance(candidate, Mapping) or not isinstance(bindings, Mapping):
        raise PhaseKitError("subject digest requires candidate and binding objects")
    raw = json.dumps(
        {"candidate": candidate, "bindings": bindings},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return sha256_bytes(raw)


def _cell(value: Any) -> str:
    if value is None:
        value = "N/A"
    if isinstance(value, bool):
        value = "true" if value else "false"
    if isinstance(value, (list, tuple, set)):
        value = ", ".join(str(item) for item in value) or "None"
    result = str(value).replace("\\", "\\\\").replace("|", "\\|")
    result = " ".join(result.splitlines()).strip()
    return result or "N/A"


def table(headers: Sequence[str], data_rows: Sequence[Sequence[Any]]) -> str:
    if not headers:
        raise PhaseKitError("table requires headers")
    lines = [
        "| " + " | ".join(_cell(item) for item in headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in data_rows:
        if len(row) != len(headers):
            raise PhaseKitError("table row width does not match headers")
        lines.append("| " + " | ".join(_cell(item) for item in row) + " |")
    return "\n".join(lines)


def decode_supporting_member(item: Mapping[str, Any], index: int) -> CanonicalMember:
    if not isinstance(item, Mapping):
        raise PhaseKitError("supporting member must be an object")
    member_id = str(item.get("id") or item.get("member_id") or f"SUP-{index:03d}")
    canonical_name = str(
        item.get("canonical_name")
        or item.get("path")
        or f"supporting/{member_id.lower()}.txt"
    )
    media_type = str(item.get("media_type") or "text/plain")
    if "raw_base64" in item:
        try:
            raw = base64.b64decode(str(item["raw_base64"]), validate=True)
        except Exception as exc:
            raise PhaseKitError(f"invalid supporting member base64: {member_id}") from exc
    else:
        value = item.get("raw", item.get("content", ""))
        if isinstance(value, bytes):
            raw = value
        elif isinstance(value, str):
            raw = value.encode("utf-8")
        else:
            raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if SECRET_RE.search(raw.decode("utf-8", errors="ignore")):
        raise PhaseKitError(f"supporting member appears to contain a Secret: {member_id}")
    return CanonicalMember(
        member_id=member_id,
        canonical_name=canonical_name,
        media_type=media_type,
        raw_bytes=raw,
        sha256=compute_sha256(raw),
    )


def validate_final_confirmation(
    project_root: Path | str,
    confirmation: Mapping[str, Any] | None,
    expected_subject_digest: str,
) -> bool:
    if confirmation is None:
        return False
    if not isinstance(confirmation, Mapping):
        raise PhaseKitError("final_confirmation must be an object")
    if confirmation.get("mode") not in {"human", "delegated"}:
        raise PhaseKitError("Final Confirmation mode must be human or delegated")
    if confirmation.get("subject_digest") != expected_subject_digest:
        return False
    for field in ("confirmer", "role", "authority_reference", "confirmed_at"):
        text(confirmation.get(field), f"final_confirmation.{field}")
    if not is_rfc3339(str(confirmation["confirmed_at"])):
        raise PhaseKitError("Final Confirmation confirmed_at must use RFC 3339")
    relative, digest = authority_reference(str(confirmation["authority_reference"]))
    root = Path(project_root).expanduser().resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PhaseKitError("Authority Reference escapes the Project Root") from exc
    if not target.is_file():
        raise PhaseKitError(f"Authority Reference does not exist: {relative}")
    if sha256_bytes(target.read_bytes()) != digest:
        raise PhaseKitError("Authority Reference digest does not match")
    return True


def validate_delegated_final_confirmation(
    project_root: Path | str,
    confirmation: Mapping[str, Any],
    *,
    artifact_reference: str,
    reviewed_executor: str,
    control_input_digest: str,
    evaluation_contract_set: str,
    check_set_result_digest: str,
) -> bool:
    """Validate IMP's delegated bindings after its unsigned bytes are known."""
    if confirmation.get("mode") != "delegated":
        return True
    if confirmation.get("role") != "Delegated Independent Reviewer":
        return False
    reviewer = str(confirmation.get("confirmer") or "")
    reviewed = str(confirmation.get("reviewed_executor") or "")
    if (
        reviewed != reviewed_executor
        or not IDENTITY_TOKEN_RE.fullmatch(reviewer)
        or not IDENTITY_TOKEN_RE.fullmatch(reviewed)
        or reviewer == reviewed
    ):
        return False
    expected = {
        "control_input_digest": control_input_digest,
        "evaluation_contract_set": evaluation_contract_set,
        "check_set_result_digest": check_set_result_digest,
    }
    if any(confirmation.get(key) != value for key, value in expected.items()):
        return False
    accepted = confirmation.get("accepted_exception_references", [])
    if accepted not in (None, []):
        return False
    try:
        validate_delegated_authority_record(
            Path(project_root),
            str(confirmation["authority_reference"]),
            artifact_reference,
            reviewer=reviewer,
            reviewed_executor=reviewed,
            control_input_digest=control_input_digest,
            evaluation_contract_set=evaluation_contract_set,
            check_set_result_digest=check_set_result_digest,
        )
    except (KeyError, OSError, UnicodeError, ValueError):
        return False
    return True


def contains_secret(value: Any) -> bool:
    if isinstance(value, bytes):
        candidate = value.decode("utf-8", errors="ignore")
    elif isinstance(value, str):
        candidate = value
    else:
        candidate = json.dumps(value, ensure_ascii=False, default=_json_default)
    return SECRET_RE.search(candidate) is not None
