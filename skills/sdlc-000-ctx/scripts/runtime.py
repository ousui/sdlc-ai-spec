#!/usr/bin/env python3
"""Deterministic CTX builder, validator, and shared Store orchestrator."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence, TypeVar


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
for import_root in (PLUGIN_ROOT, PLUGIN_ROOT / "packages"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

_FOUNDATION_IMPORT_ERROR: ImportError | None = None
try:
    from sdlc_artifact_store import (  # noqa: E402
        ArtifactStore,
        ArtifactStoreError,
        CanonicalManifest,
        CanonicalMember,
        CanonicalRevisionPayload,
        ControlReservationError,
        DomainVerification,
        ManifestMember,
        StoredRevision,
        compute_sha256,
    )
    from sdlc_artifact_store.context_lineage import ContextLineageRegistry  # noqa: E402
    from sdlc_runtime import (  # noqa: E402
        EnvelopeValidationError,
        RESULT_CONTRACT,
        SourceLockError,
        error_result,
        execute_phase,
        load_registry,
        validate_result,
        validate_source_lock_shape,
    )
except ImportError as exc:
    _FOUNDATION_IMPORT_ERROR = exc


CTX_CONTRACT = "sdlc-ai-spec/project-context/v1"
CTX_REFERENCE_RE = re.compile(r"^(CTX-\d{14}-\d{2,})@([1-9]\d*)$")
ID_RE = re.compile(r"^(RSC|TEC|ENG|CMP|RUL|ENV|CON|OPI|EVD|SUP|EX)-\d{3}$")
IDENTITY_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@%+#-]*$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
AUTHORITY_REFERENCE_RE = re.compile(
    r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))([^@]+)@sha256:([0-9a-f]{64})$"
)
ALLOWED_BASIS = frozenset({"observed", "confirmed", "referenced"})
SPEC_ROOT = "docs" + "/v1.1/"
SPEC_REFERENCES = tuple(
    sorted(
        (
            SPEC_ROOT
            + "core-spec.md@sha256:1eefa7a138f2d221140137a5fac0f5429b7f847273fe9d70e891ace6c3b7a89b",
            SPEC_ROOT
            + "artifact-store-spec.md@sha256:b340ca2a38dfe0f7409acaa8f9ac559e8872bed44725037889528e3d167d4764",
            SPEC_ROOT
            + "000-ctx-spec.md@sha256:1d98e7cce686664cbf9897cbac852c425644ba3ea81a0d9c1db5e27b0e530470",
        )
    )
)
EVALUATION_CONTRACT_SET = ", ".join(SPEC_REFERENCES)
BOOTSTRAP_RESULT_CONTRACT = "sdlc-ai-spec/runtime-result/v1"
INITIALIZE_RECOVERY_TIMEOUT_SECONDS = 1.0
INITIALIZE_RECOVERY_DELAY_SECONDS = 0.01
T = TypeVar("T")

CORE_CHECKS = (
    "CORE-G-001",
    "CORE-G-002",
    "CORE-G-003",
    "CORE-G-004",
    "CORE-G-005",
    "CORE-G-006",
    "CORE-G-007",
    "CORE-G-008",
    "CORE-G-009",
)
CTX_CHECKS = tuple(f"CTX-G-{number:03d}" for number in range(1, 7))

IDENTITY_FIELDS = (
    ("project_name", "Project Name"),
    ("purpose", "Purpose"),
    ("boundary", "Boundary"),
    ("primary_resource_reference", "Primary Resource Reference"),
    ("authoritative_references", "Authoritative References"),
)

COLLECTIONS: dict[str, tuple[str, tuple[tuple[str, str], ...], str]] = {
    "resources": (
        "RSC",
        (
            ("id", "ID"),
            ("type", "Type"),
            ("name", "Name"),
            ("role", "Role"),
            ("locator", "Locator"),
            ("baseline_reference", "Baseline Reference"),
            ("basis", "Basis"),
            ("basis_references", "Basis References"),
        ),
        "CTX-G-003",
    ),
    "technologies": (
        "TEC",
        (
            ("id", "ID"),
            ("category", "Category"),
            ("name", "Name"),
            ("version_or_constraint", "Version or Constraint"),
            ("purpose", "Purpose"),
            ("basis", "Basis"),
            ("basis_references", "Basis References"),
        ),
        "CTX-G-004",
    ),
    "engineering_entries": (
        "ENG",
        (
            ("id", "ID"),
            ("purpose", "Purpose"),
            ("command_or_entry_point", "Command or Entry Point"),
            ("working_scope", "Working Scope"),
            ("preconditions", "Preconditions"),
            ("basis", "Basis"),
            ("basis_references", "Basis References"),
        ),
        "CTX-G-004",
    ),
    "components": (
        "CMP",
        (
            ("id", "ID"),
            ("name", "Name"),
            ("type", "Type"),
            ("resource_reference", "Resource Reference"),
            ("responsibility", "Responsibility"),
            ("entry_point", "Entry Point"),
            ("depends_on", "Depends On"),
            ("authority_reference", "Authority Reference"),
            ("basis", "Basis"),
            ("basis_references", "Basis References"),
        ),
        "CTX-G-004",
    ),
    "rules": (
        "RUL",
        (
            ("id", "ID"),
            ("category", "Category"),
            ("rule_summary", "Rule Summary"),
            ("scope", "Scope"),
            ("authority_reference", "Authority Reference"),
            ("basis", "Basis"),
            ("basis_references", "Basis References"),
        ),
        "CTX-G-004",
    ),
    "environments": (
        "ENV",
        (
            ("id", "ID"),
            ("environment", "Environment"),
            ("purpose", "Purpose"),
            ("accessibility", "Accessibility"),
            ("data_and_network_boundary", "Data and Network Boundary"),
            ("basis", "Basis"),
            ("basis_references", "Basis References"),
        ),
        "CTX-G-004",
    ),
    "constraints": (
        "CON",
        (
            ("id", "ID"),
            ("constraint", "Constraint"),
            ("scope", "Scope"),
            ("impact", "Impact"),
            ("required_handling", "Required Handling"),
            ("authority_reference", "Authority Reference"),
            ("basis", "Basis"),
            ("basis_references", "Basis References"),
        ),
        "CTX-G-004",
    ),
}

EVIDENCE_FIELDS = (
    ("id", "ID"),
    ("type", "Type"),
    ("supports_references", "Supports References"),
    ("source_or_producer", "Source or Producer"),
    ("reference", "Reference"),
    ("integrity_or_digest", "Integrity or Digest"),
    ("produced_at", "Produced At"),
    ("sensitivity_or_access", "Sensitivity or Access"),
    ("empty_reason", "Empty Reason"),
)

COLLECTION_ENUMS: dict[str, dict[str, frozenset[str]]] = {
    "resources": {
        "type": frozenset(
            {
                "repository", "module", "service", "application", "library",
                "database", "infrastructure", "document-set", "other",
            }
        ),
        "role": frozenset({"primary", "supporting"}),
    },
    "technologies": {
        "category": frozenset(
            {"language", "runtime", "framework", "package", "build", "test", "quality", "other"}
        ),
    },
    "engineering_entries": {
        "purpose": frozenset({"build", "test", "run", "format", "lint", "package", "other"}),
    },
    "rules": {
        "category": frozenset(
            {"code", "branch", "commit", "test", "documentation", "compatibility", "security", "release", "other"}
        ),
    },
    "environments": {
        "environment": frozenset({"local", "development", "test", "staging", "production", "other"}),
        "accessibility": frozenset({"available", "restricted", "unavailable"}),
    },
}

DELEGATED_AUTHORITY_HEADER = (
    "Delegation Basis",
    "Reviewer Identity",
    "Reviewer Role",
    "Reviewed Executor Identity",
    "Independence",
    "Control Input Digest",
    "Evaluation Contract Set",
    "Check Set Result Digest",
    "Excluded Authority",
)
DELEGATED_INDEPENDENCE = "fresh_read, recomputed, separate_execution_identity"
DELEGATED_EXCLUDED_AUTHORITY = (
    "business_or_design_choice, exception_or_risk_acceptance, "
    "external_action_or_side_effect, external_permission_or_authorization, "
    "subjective_or_human_experience_judgment"
)


@dataclass
class BuildProduct:
    payload: CanonicalRevisionPayload
    gate_result: str
    failed_checks: list[str]
    open_items: list[dict[str, str]]
    warnings: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    expected_bindings: dict[str, str]


def boundary_key(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Project Boundary must be a string")
    normalized = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError("Project Boundary must not be empty")
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _cell(value: Any) -> str:
    if isinstance(value, list):
        value = ", ".join(sorted({str(item) for item in value})) or "None"
    if value is None:
        value = "None"
    return str(value).replace("|", "&#124;").replace("\r", " ").replace("\n", " ").strip()


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(_cell(cell) for cell in row) + " |" for row in rows),
    ]


def _confirmation(invocation: Mapping[str, Any], kind: str) -> Mapping[str, Any] | None:
    matches = [item for item in invocation.get("confirmations", []) if item.get("type") == kind]
    if len(matches) != 1:
        return None
    return matches[0]


def _artifact_result(
    operation: str,
    *,
    ok: bool,
    status: str,
    artifact: Mapping[str, Any] | None,
    gate_result: str = "pending",
    failed_checks: Sequence[str] = (),
    open_items: Sequence[Mapping[str, Any]] = (),
    warnings: Sequence[Mapping[str, Any]] = (),
    errors: Sequence[Mapping[str, Any]] = (),
    next_action: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return validate_result(
        {
            "contract": RESULT_CONTRACT,
            "ok": ok,
            "operation": operation,
            "status": status,
            "artifact": dict(artifact) if artifact is not None else None,
            "gate": {"result": gate_result, "failed_checks": list(failed_checks)},
            "open_items": [dict(item) for item in open_items],
            "warnings": [dict(item) for item in warnings],
            "errors": [dict(item) for item in errors],
            "next_action": dict(next_action) if next_action is not None else None,
        }
    )


def _action(code: str, message: str, *, user: bool = True) -> dict[str, Any]:
    return {"code": code, "message": message, "requires_user": user, "command": None}


def _bootstrap_error_result(
    operation: str,
    *,
    code: str,
    message: str,
    next_action_code: str,
    next_action_message: str,
    requires_user: bool,
) -> dict[str, Any]:
    """Serialize only the Result shell needed when Foundation cannot import."""

    return {
        "contract": BOOTSTRAP_RESULT_CONTRACT,
        "ok": False,
        "operation": operation,
        "status": "failed",
        "artifact": None,
        "gate": {"result": "pending", "failed_checks": []},
        "open_items": [],
        "warnings": [],
        "errors": [{"code": code, "message": message}],
        "next_action": {
            "code": next_action_code,
            "message": next_action_message,
            "requires_user": requires_user,
            "command": None,
        },
    }


def _artifact_view(stored: StoredRevision, *, authority: bool) -> dict[str, Any]:
    return {
        "id": stored.payload.artifact_id,
        "type": "CTX",
        "revision": stored.payload.revision,
        "revision_state": stored.control.state,
        "artifact_status": stored.payload.artifact_status,
        "reference": f"{stored.payload.artifact_id}@{stored.payload.revision}" if authority else None,
    }


def _reference(value: Any) -> str:
    if isinstance(value, list):
        values = sorted({str(item).strip() for item in value if str(item).strip()})
        return ", ".join(values) if values else "None"
    text = _cell(value)
    return text or "None"


def _valid_fact(value: Any, evidence_ids: set[str]) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(value, Mapping):
        return None, "fact must be an object"
    if set(value) != {"value", "basis", "basis_references"}:
        return None, "fact requires exactly value, basis and basis_references"
    fact_value = _cell(value["value"])
    basis = value["basis"]
    refs = value["basis_references"]
    if not fact_value:
        return None, "fact value must not be empty"
    if basis not in ALLOWED_BASIS:
        return None, "basis must be observed, confirmed or referenced"
    if not isinstance(refs, list) or not refs:
        return None, "basis_references must be a non-empty array"
    normalized_refs = sorted({_cell(item) for item in refs if _cell(item)})
    if not normalized_refs:
        return None, "basis_references must not be empty"
    internal = {item for item in normalized_refs if item.startswith("EVD-")}
    if basis in {"observed", "confirmed"} and not internal:
        return None, f"{basis} basis requires an Evidence ID"
    if not internal.issubset(evidence_ids):
        return None, "basis_references contains an unknown Evidence ID"
    return {
        "value": fact_value,
        "basis": basis,
        "basis_references": ", ".join(normalized_refs),
    }, None


def _is_rfc3339(value: Any) -> bool:
    text = _cell(value)
    if not RFC3339_RE.fullmatch(text):
        return False
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _is_typed_value(value: Any) -> bool:
    return _cell(value) not in {"", "None", "N/A", "TBD", "Unknown", "-", "待定"}


def _collection_row_problem(name: str, row: Mapping[str, str]) -> str | None:
    for field, allowed in COLLECTION_ENUMS.get(name, {}).items():
        if row[field] not in allowed:
            return f"{name}.{field} uses an invalid enum value"

    required_typed = {
        "resources": ("type", "name", "role", "locator"),
        "technologies": ("category", "name", "version_or_constraint", "purpose"),
        "engineering_entries": ("purpose", "command_or_entry_point", "working_scope"),
        "components": ("name", "type", "resource_reference", "responsibility", "entry_point"),
        "rules": ("category", "rule_summary", "scope", "authority_reference"),
        "environments": ("environment", "purpose", "accessibility", "data_and_network_boundary"),
        "constraints": ("constraint", "scope", "impact", "required_handling", "authority_reference"),
    }
    if any(not _is_typed_value(row[field]) for field in required_typed[name]):
        return f"{name} contains an empty or placeholder typed value"
    return None


def _new_open_item(number: int, needed: str, blocked: str) -> dict[str, str]:
    return {
        "id": f"OPI-{number:03d}",
        "needed": needed,
        "expected_source": "Project Authority or reproducible Evidence",
        "blocked_references": blocked,
        "state": "open",
        "resolution": "N/A",
    }


def _normalize_context(
    context: Any,
    *,
    inputs: Mapping[str, Any],
    operation: str,
    artifact_id: str,
    revision: int,
    base_revision: int | None,
    now: datetime,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, Any]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, Any]] = []
    open_items: list[dict[str, str]] = []
    context = context if isinstance(context, Mapping) else {}

    expected_context_fields = {
        "summary", "project_identity", *COLLECTIONS, "exceptions",
    }
    unknown_context_fields = set(context) - expected_context_fields
    if unknown_context_fields:
        errors.append(
            {
                "code": "CTX_CONTENT_INVALID",
                "message": "inputs.context contains unsupported fields: "
                + ", ".join(sorted(unknown_context_fields)),
            }
        )

    evidence_input = inputs.get("evidence", [])
    evidence: list[dict[str, str]] = []
    if not isinstance(evidence_input, list):
        errors.append({"code": "CTX_CONTENT_INVALID", "message": "evidence must be an array"})
        evidence_input = []
    for raw in evidence_input:
        evidence_fields = {name for name, _ in EVIDENCE_FIELDS if name != "empty_reason"}
        if not isinstance(raw, Mapping) or set(raw) != evidence_fields:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": "Evidence row fields do not match the Contract"})
            continue
        row_id = _cell(raw.get("id"))
        if not re.fullmatch(r"EVD-\d{3}", row_id):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Invalid Evidence row: {row_id or 'missing ID'}"})
            continue
        row = {name: _reference(raw.get(name)) for name, _ in EVIDENCE_FIELDS}
        row["empty_reason"] = "N/A"
        if (
            any(not _is_typed_value(row[field]) for field in evidence_fields - {"id", "produced_at"})
            or not _is_rfc3339(row["produced_at"])
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", row["integrity_or_digest"])
        ):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Evidence row is incomplete or invalid: {row_id}"})
            continue
        evidence.append(row)
    evidence.sort(key=lambda item: item["id"])
    evidence_ids = {item["id"] for item in evidence}
    if len(evidence_ids) != len(evidence):
        errors.append({"code": "CTX_CONTENT_INVALID", "message": "Evidence IDs must be unique"})

    summary = _cell(context.get("summary"))
    if not summary:
        open_items.append(_new_open_item(len(open_items) + 1, "Provide a concise project summary", "CTX-G-004"))

    identity_input = context.get("project_identity")
    identity: dict[str, dict[str, str]] = {}
    if not isinstance(identity_input, Mapping):
        identity_input = {}
    for key, label in IDENTITY_FIELDS:
        fact, problem = _valid_fact(identity_input.get(key), evidence_ids)
        if problem:
            open_items.append(_new_open_item(len(open_items) + 1, f"Confirm Project Identity field: {label}", "CTX-G-002"))
        else:
            identity[key] = fact
    for required_identity in ("project_name", "purpose", "boundary", "primary_resource_reference"):
        if required_identity in identity and not _is_typed_value(identity[required_identity]["value"]):
            errors.append(
                {
                    "code": "CTX_CONTENT_INVALID",
                    "message": f"Project Identity {required_identity} cannot be None, N/A, or a placeholder",
                }
            )

    collections: dict[str, dict[str, Any]] = {}
    all_ids: set[str] = set(evidence_ids)
    for name, (prefix, fields, blocked) in COLLECTIONS.items():
        supplied = context.get(name)
        normalized: dict[str, Any] = {"none": None, "rows": []}
        if isinstance(supplied, Mapping) and set(supplied) == {"none"}:
            none_value = supplied["none"]
            if not isinstance(none_value, Mapping):
                problem = "none declaration must be an object"
            else:
                fact, problem = _valid_fact(
                    {"value": "None", **dict(none_value)}, evidence_ids
                )
                if not problem:
                    normalized["none"] = fact
            if problem:
                errors.append({"code": "CTX_CONTENT_INVALID", "message": f"{name}: {problem}"})
        elif isinstance(supplied, list) and supplied:
            for raw in supplied:
                if not isinstance(raw, Mapping) or set(raw) != {key for key, _ in fields}:
                    errors.append({"code": "CTX_CONTENT_INVALID", "message": f"{name} row fields do not match the Contract"})
                    continue
                row = {key: _reference(raw[key]) for key, _ in fields}
                row_id = row["id"]
                if not re.fullmatch(prefix + r"-\d{3}", row_id) or row_id in all_ids:
                    errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Invalid or duplicate item ID: {row_id}"})
                    continue
                if row["basis"] not in ALLOWED_BASIS or row["basis_references"] == "None":
                    errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Invalid Basis for {row_id}"})
                    continue
                row_problem = _collection_row_problem(name, row)
                if row_problem:
                    errors.append({"code": "CTX_CONTENT_INVALID", "message": f"{row_id}: {row_problem}"})
                    continue
                internal_refs = {
                    item for item in row["basis_references"].split(", ") if item.startswith("EVD-")
                }
                if row["basis"] in {"observed", "confirmed"} and not internal_refs:
                    errors.append({"code": "CTX_CONTENT_INVALID", "message": f"{row['basis']} Basis requires Evidence for {row_id}"})
                    continue
                if not internal_refs.issubset(evidence_ids):
                    errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Unknown Evidence for {row_id}"})
                    continue
                all_ids.add(row_id)
                normalized["rows"].append(row)
            normalized["rows"].sort(key=lambda item: item["id"])
        else:
            open_items.append(_new_open_item(len(open_items) + 1, f"Confirm applicable {name} or an objective None declaration", blocked))
        if name == "resources" and normalized["none"] is not None:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": "Resource Registry cannot be None; at least one primary Resource is required"})
        collections[name] = normalized

    resources = collections["resources"]["rows"]
    primary_refs = {row["id"] for row in resources if row.get("role") == "primary"}
    identity_primary = identity.get("primary_resource_reference", {}).get("value")
    if resources and (not primary_refs or identity_primary not in primary_refs):
        errors.append({"code": "CTX_CONTENT_INVALID", "message": "Primary Resource Reference must resolve to one primary Resource"})
    resource_ids = {row["id"] for row in resources}
    resource_locators = [row["locator"] for row in resources]
    if len(resource_locators) != len(set(resource_locators)):
        errors.append({"code": "CTX_CONTENT_INVALID", "message": "Resource Locator must be unique within the Project Boundary"})
    components = collections["components"]["rows"]
    component_ids = {row["id"] for row in components}
    for component in components:
        dependencies = [] if component["depends_on"] == "None" else component["depends_on"].split(", ")
        if component["resource_reference"] not in resource_ids or any(
            dependency not in component_ids for dependency in dependencies
        ):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Component references do not close within the CTX: {component['id']}"})

    supporting_input = inputs.get("supporting_members", [])
    members: list[dict[str, Any]] = []
    if not isinstance(supporting_input, list):
        errors.append({"code": "CTX_CONTENT_INVALID", "message": "supporting_members must be an array"})
        supporting_input = []
    for raw in supporting_input:
        if not isinstance(raw, Mapping):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": "Supporting Member must be an object"})
            continue
        allowed_member_fields = {
            "member_id", "canonical_name", "media_type", "purpose", "sha256",
            "content", "content_base64",
        }
        required_member_fields = {"member_id", "canonical_name", "media_type", "purpose"}
        if set(raw) - allowed_member_fields or not required_member_fields.issubset(raw):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": "Supporting Member fields do not match the Contract"})
            continue
        member_id = _cell(raw.get("member_id"))
        name = _cell(raw.get("canonical_name"))
        media_type = _cell(raw.get("media_type"))
        if not re.fullmatch(r"SUP-\d{3}", member_id) or member_id in all_ids:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Invalid or duplicate Supporting Member ID: {member_id}"})
            continue
        path = Path(name)
        if (
            not name
            or path.is_absolute()
            or ".." in path.parts
            or not re.fullmatch(r"[^/\s]+/[^/\s]+", media_type)
            or not _is_typed_value(raw.get("purpose"))
        ):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Invalid Supporting Member metadata: {member_id}"})
            continue
        has_text = "content" in raw
        has_base64 = "content_base64" in raw
        if has_text == has_base64:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"{member_id} requires exactly one content representation"})
            continue
        try:
            raw_bytes = (
                str(raw["content"]).encode("utf-8")
                if has_text
                else base64.b64decode(raw["content_base64"], validate=True)
            )
        except (ValueError, TypeError) as exc:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Invalid content for {member_id}: {exc}"})
            continue
        digest = compute_sha256(raw_bytes)
        supplied_digest = raw.get("sha256")
        if supplied_digest is not None and supplied_digest not in {digest, "sha256:" + digest}:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Digest mismatch for {member_id}"})
            continue
        all_ids.add(member_id)
        members.append(
            {
                "member_id": member_id,
                "canonical_name": name,
                "media_type": media_type,
                "purpose": _cell(raw.get("purpose")) or "Supporting Evidence",
                "raw_bytes": raw_bytes,
                "sha256": digest,
            }
        )
    members.sort(key=lambda item: item["member_id"])

    exceptions_input = context.get("exceptions", [])
    exceptions: list[dict[str, str]] = []
    if not isinstance(exceptions_input, list):
        errors.append({"code": "CTX_CONTENT_INVALID", "message": "exceptions must be an array"})
        exceptions_input = []
    exception_fields = (
        "id", "state", "origin_exception_reference", "scope_or_skipped_obligation",
        "reason", "known_risk", "compensating_control", "approver_role_time",
        "revisit_condition", "downstream_obligation", "resolution_or_superseding_references",
    )
    for raw in exceptions_input:
        if not isinstance(raw, Mapping) or set(raw) != set(exception_fields):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": "Exception row fields do not match the Contract"})
            continue
        row = {key: _reference(raw[key]) for key in exception_fields}
        if not re.fullmatch(r"EX-\d{3}", row["id"]) or row["id"] in all_ids:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Invalid or duplicate Exception ID: {row['id']}"})
            continue
        if row["state"] not in {"active", "carried", "resolved", "superseded"}:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Invalid Exception state: {row['id']}"})
            continue
        if any(
            not _is_typed_value(row[field])
            for field in (
                "scope_or_skipped_obligation", "reason", "known_risk",
                "compensating_control", "approver_role_time", "revisit_condition",
                "downstream_obligation",
            )
        ):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Exception row is incomplete: {row['id']}"})
            continue
        if row["state"] == "active" and row["origin_exception_reference"] != "N/A":
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Active Exception origin must be N/A: {row['id']}"})
            continue
        if row["state"] == "carried" and not re.fullmatch(r"[A-Z]+-[A-Za-z0-9-]+@[1-9]\d*#EX-\d{3}", row["origin_exception_reference"]):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Carried Exception requires an exact origin: {row['id']}"})
            continue
        resolution = row["resolution_or_superseding_references"]
        if row["state"] in {"active", "carried"} and resolution != "N/A":
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Open Exception resolution must be N/A: {row['id']}"})
            continue
        if row["state"] in {"resolved", "superseded"} and not _is_typed_value(resolution):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": f"Closed Exception requires a resolution reference: {row['id']}"})
            continue
        all_ids.add(row["id"])
        exceptions.append(row)
    exceptions.sort(key=lambda item: item["id"])

    refresh_input = inputs.get("refresh")
    if operation == "create":
        baseline = "None"
        if resources:
            baseline = resources[0].get("baseline_reference") or resources[0].get("id")
        refresh = {
            "base_revision": "None",
            "observed_at": now.isoformat(timespec="seconds"),
            "observation_baseline": baseline,
            "refresh_reason": "initial",
            "effective_change_references": "None",
            "evidence_references": _reference(sorted(evidence_ids)),
        }
    elif isinstance(refresh_input, Mapping):
        required_refresh = {
            "base_revision", "observed_at", "observation_baseline", "refresh_reason",
            "effective_change_references", "evidence_references",
        }
        if set(refresh_input) != required_refresh or refresh_input.get("base_revision") != base_revision:
            errors.append({"code": "CTX_CONTENT_INVALID", "message": "refresh must bind the exact Base Revision and fixed fields"})
        refresh = {key: _reference(refresh_input.get(key)) for key in required_refresh}
        refresh_evidence = {
            item for item in refresh["evidence_references"].split(", ") if item.startswith("EVD-")
        }
        if (
            not _is_rfc3339(refresh["observed_at"])
            or any(not _is_typed_value(refresh[key]) for key in ("observation_baseline", "refresh_reason", "evidence_references"))
            or not refresh_evidence.issubset(evidence_ids)
        ):
            errors.append({"code": "CTX_CONTENT_INVALID", "message": "refresh values, Evidence, or effective changes are invalid"})
    else:
        refresh = {
            "base_revision": str(base_revision), "observed_at": "Pending — OPI-999",
            "observation_baseline": "Pending — OPI-999", "refresh_reason": "Pending — OPI-999",
            "effective_change_references": "Pending — OPI-999", "evidence_references": "Pending — OPI-999",
        }
        open_items.append(_new_open_item(len(open_items) + 1, "Provide the complete Refresh Summary for revise", "CTX-G-006"))

    model = {
        "artifact_id": artifact_id,
        "revision": revision,
        "summary": summary or "Pending project summary",
        "identity": identity,
        "collections": collections,
        "evidence": evidence,
        "members": members,
        "exceptions": exceptions,
        "refresh": refresh,
    }
    return model, open_items, errors


def _collection_rows(name: str, collection: Mapping[str, Any]) -> list[list[Any]]:
    _, fields, _ = COLLECTIONS[name]
    if collection["rows"]:
        return [[row[key] for key, _ in fields] for row in collection["rows"]]
    none = collection.get("none")
    if none:
        values = ["None"] + ["N/A"] * (len(fields) - 3) + [none["basis"], none["basis_references"]]
        return [values]
    return [["None"] + ["N/A"] * (len(fields) - 1)]


def _render_markdown(
    model: Mapping[str, Any],
    *,
    status: str,
    open_items: Sequence[Mapping[str, Any]],
    checks: Mapping[str, tuple[str, str]],
    final_confirmation: Mapping[str, Any] | None,
    gate_summary: Mapping[str, str],
) -> bytes:
    lines = [
        "---", CTX_CONTRACT.join(("contract: ", "")),
        f"id: {model['artifact_id']}", f"revision: {model['revision']}", f"status: {status}", "---", "",
        f"# {model['identity'].get('project_name', {}).get('value', 'Pending Project')} Project Context", "",
        "## 摘要 Summary", "", model["summary"], "",
        "## 项目标识 Project Identity", "",
    ]
    identity_rows = []
    for key, label in IDENTITY_FIELDS:
        fact = model["identity"].get(key)
        identity_rows.append([label, fact["value"], fact["basis"], fact["basis_references"]] if fact else [label, f"Pending — OPI-001", "confirmed", "OPI-001"])
    lines += _table(["Field", "Value", "Basis", "Basis References"], identity_rows) + [""]

    section_layout = (
        ("## 资源登记 Resource Registry", "resources"),
        ("## 技术与工程基线 Technical and Engineering Baseline", None),
        ("### 技术基线 Technology Baseline", "technologies"),
        ("### 工程入口 Engineering Entry Points", "engineering_entries"),
        ("## 项目结构 Project Topology", "components"),
        ("## 项目规则 Project Rules", "rules"),
        ("## 环境与约束 Environment and Constraints", None),
        ("### 环境 Environment", "environments"),
        ("### 约束 Constraints", "constraints"),
    )
    for heading, name in section_layout:
        lines += [heading, ""]
        if name:
            _, fields, _ = COLLECTIONS[name]
            lines += _table([label for _, label in fields], _collection_rows(name, model["collections"][name])) + [""]

    lines += ["## 待确认项 Open Items", ""]
    if open_items:
        rows = [[item["id"], item["needed"], item["expected_source"], item["blocked_references"], item["state"], item["resolution"]] for item in open_items]
    else:
        rows = [["None", "No open items", "N/A", "N/A", "none", "N/A"]]
    lines += _table(
        ["ID", "所需输入或待确认决策 Needed Input or Decision", "预期来源 Expected Source", "被阻塞项 Blocked References", "状态 State", "解决结果或证据 Resolution or Evidence"],
        rows,
    ) + [""]

    lines += ["## 证据 Evidence", ""]
    if model["evidence"]:
        evidence_rows = [[row[key] for key, _ in EVIDENCE_FIELDS] for row in model["evidence"]]
    else:
        evidence_rows = [["None", "none", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "No independent Evidence"]]
    lines += _table([label for _, label in EVIDENCE_FIELDS], evidence_rows) + [""]

    refresh = model["refresh"]
    lines += ["## 刷新摘要 Refresh Summary", ""]
    lines += _table(
        ["Base Revision", "Observed At", "Observation Baseline", "Refresh Reason", "Effective Change References", "Evidence References"],
        [[refresh[key] for key in ("base_revision", "observed_at", "observation_baseline", "refresh_reason", "effective_change_references", "evidence_references")]],
    ) + [""]

    lines += ["## 支撑产物清单 Supporting Artifact Manifest", ""]
    if model["members"]:
        member_rows = [[item["member_id"], "supporting", item["canonical_name"], item["media_type"], item["purpose"], "sha256:" + item["sha256"], "N/A"] for item in model["members"]]
    else:
        member_rows = [["None", "none", "N/A", "N/A", "N/A", "N/A", "No supporting artifacts"]]
    lines += _table(["Member ID", "Type", "Path or Reference", "Media Type", "Purpose", "SHA-256 Digest", "Empty Reason"], member_rows) + [""]

    lines += ["## 豁免 Exceptions", ""]
    if model["exceptions"]:
        exception_keys = (
            "id", "state", "origin_exception_reference", "scope_or_skipped_obligation", "reason",
            "known_risk", "compensating_control", "approver_role_time", "revisit_condition",
            "downstream_obligation", "resolution_or_superseding_references",
        )
        exception_rows = [[row[key] for key in exception_keys] for row in model["exceptions"]]
    else:
        exception_rows = [["None", "none", "N/A", "N/A", "No Exceptions", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]]
    lines += _table(
        ["ID", "State", "Origin Exception Reference", "作用域或被跳过义务 Scope or Skipped Obligation", "原因 Reason", "已知风险 Known Risk", "补偿措施 Compensating Control", "批准记录 Approver, Role and Time", "复查条件 Revisit Condition", "下游限制 Downstream Obligation", "解决或替代引用 Resolution or Superseding References"],
        exception_rows,
    ) + [""]

    lines += ["## 门禁 Gate", "", "### Core Checks", ""]
    core_rows = [[check_id, "Core Contract Integrity", checks[check_id][0], checks[check_id][1]] for check_id in CORE_CHECKS]
    lines += _table(["Check ID", "检查项 Check", "结果 Result", "证据或说明 Evidence or Notes"], core_rows) + [""]
    lines += ["### CTX Checks", ""]
    ctx_rows = [[check_id, "Project Context Contract", checks[check_id][0], checks[check_id][1]] for check_id in CTX_CHECKS]
    lines += _table(["Check ID", "Check", "Result", "Basis References"], ctx_rows) + [""]

    lines += ["### Final Confirmation", ""]
    if final_confirmation:
        fc = final_confirmation
        fc_row = [[str(model["revision"]), fc["control_input_digest"], fc["evaluation_contract_set"], fc["check_set_result_digest"], fc["result"], fc["mode"], fc["confirmer"], fc["role"], fc["authority_reference"], _reference(fc["accepted_exception_references"]), fc["confirmed_at"]]]
    else:
        fc_row = [[str(model["revision"]), "", EVALUATION_CONTRACT_SET, "", "pending", "", "", "", "None", "None", ""]]
    lines += _table(["Revision", "Control Input Digest", "Evaluation Contract Set", "Check Set Result Digest", "Result", "Mode", "Confirmer", "Role", "Authority Reference", "Accepted Exception References", "Confirmed At"], fc_row) + [""]

    lines += ["### Artifact Gate Summary", ""]
    lines += _table(
        ["Evaluated Revision", "Control Input Digest", "Evaluation Contract Set", "Check Set Result Digest", "Gate Result", "Exception References", "Evaluator", "Evaluated At"],
        [[gate_summary[key] for key in ("revision", "control_input_digest", "evaluation_contract_set", "check_set_result_digest", "gate_result", "exception_references", "evaluator", "evaluated_at")]],
    ) + [""]
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _control_input_digest(primary: bytes) -> str:
    text = primary.decode("utf-8")
    projected = re.sub(r"(?m)^status: .+\n", "", text, count=1)
    marker = projected.find("## 门禁 Gate\n")
    if marker < 0:
        raise ValueError("Gate section is missing")
    projected = projected[:marker]
    return "sha256:" + hashlib.sha256(projected.encode("utf-8")).hexdigest()


def _effective_content_digest(primary: bytes) -> str:
    """Compare business content while excluding Revision refresh and derived control state."""

    text = primary.decode("utf-8")
    projected = re.sub(r"(?m)^status: .+\n", "", text, count=1)
    projected = re.sub(r"(?m)^revision: .+\n", "", projected, count=1)
    open_start = projected.find("## 待确认项 Open Items\n")
    evidence_start = projected.find("## 证据 Evidence\n")
    refresh_start = projected.find("## 刷新摘要 Refresh Summary\n")
    manifest_start = projected.find("## 支撑产物清单 Supporting Artifact Manifest\n")
    gate_start = projected.find("## 门禁 Gate\n")
    if (
        min(open_start, evidence_start, refresh_start, manifest_start, gate_start) < 0
        or not open_start < evidence_start < refresh_start < manifest_start < gate_start
    ):
        raise ValueError("Required CTX sections are missing or out of order")
    projected = (
        projected[:open_start]
        + projected[evidence_start:refresh_start]
        + projected[manifest_start:gate_start]
    )
    return "sha256:" + hashlib.sha256(projected.encode("utf-8")).hexdigest()


def _check_digest(checks: Mapping[str, tuple[str, str]]) -> str:
    rows = []
    for check_id in (*CORE_CHECKS[:-1], *CTX_CHECKS):
        result, notes = checks[check_id]
        if result == "pending":
            raise ValueError("Cannot digest pending checks")
        label = "Core Contract Integrity" if check_id.startswith("CORE") else "Project Context Contract"
        rows.append(f"| {check_id} | {label} | {result} | {_cell(notes)} |\n")
    return "sha256:" + hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def _authority_bytes(project_root: Path, reference: str) -> bytes | None:
    match = AUTHORITY_REFERENCE_RE.fullmatch(reference) if isinstance(reference, str) else None
    if not match:
        return None
    path = (project_root / match.group(1)).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError:
        return None
    if not path.is_file():
        return None
    raw = path.read_bytes()
    return raw if hashlib.sha256(raw).hexdigest() == match.group(2) else None


def _validate_delegated_authority(
    raw: bytes,
    *,
    project_root: Path,
    authority_reference: str,
    artifact_reference: str,
    expected: Mapping[str, str],
    reviewer: str,
    reviewed_executor: str,
) -> str | None:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "Delegated Authority record must be UTF-8"
    lines = text.splitlines()
    if len(lines) != 10 or lines[0] != "---" or lines[5] != "---" or lines[6] != "":
        return "Delegated Authority record does not use the fixed document structure"
    expected_front = [
        "---",
        "contract: sdlc-ai-spec/final-confirmation-authority/v1",
        f"artifact: {artifact_reference}",
        "decision: approved",
    ]
    if lines[:4] != expected_front or not lines[4].startswith("decided_at: "):
        return "Delegated Authority Front Matter does not match the fixed Contract"
    if not _is_rfc3339(lines[4].removeprefix("decided_at: ")):
        return "Delegated Authority decided_at must be RFC 3339"
    expected_header = "| " + " | ".join(DELEGATED_AUTHORITY_HEADER) + " |"
    expected_separator = "| " + " | ".join("---" for _ in DELEGATED_AUTHORITY_HEADER) + " |"
    if lines[7] != expected_header or lines[8] != expected_separator:
        return "Delegated Authority table header does not match the fixed Contract"
    if not lines[9].startswith("|") or not lines[9].endswith("|"):
        return "Delegated Authority must contain exactly one data row"
    row = [cell.strip() for cell in lines[9].strip("|").split("|")]
    if len(row) != len(DELEGATED_AUTHORITY_HEADER):
        return "Delegated Authority row does not match the fixed Contract"
    values = dict(zip(DELEGATED_AUTHORITY_HEADER, row))
    delegation_basis = values["Delegation Basis"]
    if (
        delegation_basis == authority_reference
        or _authority_bytes(project_root, delegation_basis) is None
    ):
        return "Delegation Basis must reference a separate immutable project authorization record"
    expected_values = {
        "Reviewer Identity": reviewer,
        "Reviewer Role": "Delegated Independent Reviewer",
        "Reviewed Executor Identity": reviewed_executor,
        "Independence": DELEGATED_INDEPENDENCE,
        "Control Input Digest": expected["control_input_digest"],
        "Evaluation Contract Set": expected["evaluation_contract_set"],
        "Check Set Result Digest": expected["check_set_result_digest"],
        "Excluded Authority": DELEGATED_EXCLUDED_AUTHORITY,
    }
    if any(values[key] != value for key, value in expected_values.items()):
        return "Delegated Authority bindings or fixed sets do not match the Contract"
    return None


def _validate_final_confirmation(
    confirmation: Mapping[str, Any] | None,
    *,
    project_root: Path,
    artifact_reference: str,
    expected: Mapping[str, str],
    active_exceptions: Sequence[str],
) -> tuple[Mapping[str, Any] | None, str | None]:
    if confirmation is None:
        return None, "Final Confirmation is required"
    required = {
        "type", "result", "mode", "confirmer", "role", "authority_reference",
        "accepted_exception_references", "confirmed_at", "control_input_digest",
        "evaluation_contract_set", "check_set_result_digest",
    }
    allowed = required | {"reviewed_executor"}
    if set(confirmation) - allowed or not required.issubset(confirmation):
        return None, "Final Confirmation fields do not match the Contract"
    if confirmation["result"] not in {"approved", "rejected"}:
        return None, "Final Confirmation result must be approved or rejected"
    if confirmation["mode"] not in {"human", "delegated"}:
        return None, "Final Confirmation mode must be human or delegated"
    if confirmation["mode"] == "human" and "reviewed_executor" in confirmation:
        return None, "Human Final Confirmation must not declare a delegated reviewed executor"
    if not _is_typed_value(confirmation["role"]):
        return None, "Final Confirmation role must be a non-empty authorized role"
    if not _is_rfc3339(confirmation["confirmed_at"]):
        return None, "Final Confirmation confirmed_at must be RFC 3339"
    for key in ("control_input_digest", "evaluation_contract_set", "check_set_result_digest"):
        if confirmation[key] != expected[key]:
            return None, f"Final Confirmation {key} does not bind the current payload"
    accepted = sorted({_cell(item) for item in confirmation["accepted_exception_references"]}) if isinstance(confirmation["accepted_exception_references"], list) else []
    if accepted != sorted(active_exceptions):
        return None, "Accepted Exception references do not match active/carried Exceptions"
    if not IDENTITY_TOKEN_RE.fullmatch(_cell(confirmation["confirmer"])):
        return None, "Confirmer must be one stable identity token"
    raw = _authority_bytes(project_root, _cell(confirmation["authority_reference"]))
    if raw is None:
        return None, "Authority Reference is missing, outside the project, or has the wrong digest"
    if confirmation["mode"] == "delegated":
        reviewed = _cell(confirmation.get("reviewed_executor"))
        if active_exceptions or confirmation["role"] != "Delegated Independent Reviewer":
            return None, "Delegated confirmation cannot accept Exceptions and requires the fixed role"
        if not IDENTITY_TOKEN_RE.fullmatch(reviewed) or reviewed == confirmation["confirmer"]:
            return None, "Delegated Reviewer must be independent from the reviewed executor"
        authority_problem = _validate_delegated_authority(
            raw,
            project_root=project_root,
            authority_reference=_cell(confirmation["authority_reference"]),
            artifact_reference=artifact_reference,
            expected=expected,
            reviewer=_cell(confirmation["confirmer"]),
            reviewed_executor=reviewed,
        )
        if authority_problem:
            return None, authority_problem
    else:
        authority_text = raw.decode("utf-8", errors="replace")
        for bound in (artifact_reference, expected["control_input_digest"], expected["check_set_result_digest"]):
            if bound not in authority_text:
                return None, "Authority record does not bind the current Artifact and digests"
    return dict(confirmation), None


def _pending_checks(open_items: Sequence[Mapping[str, Any]], errors: Sequence[Mapping[str, Any]]) -> dict[str, tuple[str, str]]:
    if errors:
        return {check_id: ("fail", errors[0]["message"]) for check_id in (*CORE_CHECKS, *CTX_CHECKS)}
    blocked = {value for item in open_items for value in str(item["blocked_references"]).split(", ")}
    checks: dict[str, tuple[str, str]] = {}
    for check_id in (*CORE_CHECKS, *CTX_CHECKS):
        if check_id == "CORE-G-009" or check_id in blocked:
            checks[check_id] = ("pending", "Blocked by an Open Item")
        elif open_items and check_id in {"CORE-G-006", "CTX-G-006"}:
            checks[check_id] = ("pending", "Open Items remain")
        else:
            checks[check_id] = ("pass", "Deterministic runtime validation")
    return checks


def _canonical_payload(
    model: Mapping[str, Any],
    primary: bytes,
    status: str,
) -> CanonicalRevisionPayload:
    members = tuple(
        CanonicalMember(
            member_id=item["member_id"], canonical_name=item["canonical_name"],
            media_type=item["media_type"], raw_bytes=item["raw_bytes"], sha256=item["sha256"],
        )
        for item in model["members"]
    )
    manifest_members = tuple(
        ManifestMember(
            member_id=item.member_id, canonical_name=item.canonical_name,
            media_type=item.media_type, sha256=item.sha256,
        )
        for item in members
    )
    manifest_raw = json.dumps(
        {
            "contract": "sdlc-ai-spec/canonical-manifest/v1",
            "artifact": f"{model['artifact_id']}@{model['revision']}",
            "local_members": [
                {"member_id": item.member_id, "canonical_name": item.canonical_name, "media_type": item.media_type, "sha256": item.sha256}
                for item in manifest_members
            ],
            "external_references": [],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return CanonicalRevisionPayload(
        artifact_id=model["artifact_id"], artifact_type="CTX", revision=model["revision"],
        artifact_status=status, primary_blob=primary, primary_media_type="text/markdown",
        primary_sha256=compute_sha256(primary), members=members,
        manifest=CanonicalManifest(raw_bytes=manifest_raw, media_type="application/json", local_members=manifest_members),
    )


def build_payload(
    invocation: Mapping[str, Any],
    *,
    artifact_id: str,
    revision: int,
    base_revision: int | None,
    now: datetime,
) -> BuildProduct:
    model, open_items, errors = _normalize_context(
        invocation.get("inputs", {}).get("context"), inputs=invocation.get("inputs", {}),
        operation=invocation["operation"],
        artifact_id=artifact_id, revision=revision, base_revision=base_revision, now=now,
    )
    warnings: list[dict[str, Any]] = []
    checks = _pending_checks(open_items, errors)
    empty_gate = {
        "revision": str(revision), "control_input_digest": "", "evaluation_contract_set": EVALUATION_CONTRACT_SET,
        "check_set_result_digest": "", "gate_result": "fail" if errors else "pending",
        "exception_references": "None", "evaluator": "sdlc-000-ctx-runtime", "evaluated_at": now.isoformat(timespec="seconds"),
    }
    provisional = _render_markdown(model, status="failed" if errors else "draft", open_items=open_items, checks=checks, final_confirmation=None, gate_summary=empty_gate)
    expected: dict[str, str] = {"evaluation_contract_set": EVALUATION_CONTRACT_SET}

    final_confirmation = None
    if not errors and not open_items:
        complete_checks = {check_id: ("pass", "Deterministic runtime validation") for check_id in (*CORE_CHECKS, *CTX_CHECKS)}
        complete_checks["CORE-G-009"] = ("pending", "Final Confirmation is not bound")
        candidate = _render_markdown(model, status="draft", open_items=[], checks=complete_checks, final_confirmation=None, gate_summary=empty_gate)
        expected["control_input_digest"] = _control_input_digest(candidate)
        expected["check_set_result_digest"] = _check_digest(complete_checks)
        confirmation = _confirmation(invocation, "final_confirmation")
        active_exceptions = [row["id"] for row in model["exceptions"] if row["state"] in {"active", "carried"}]
        final_confirmation, confirmation_problem = _validate_final_confirmation(
            confirmation, project_root=Path(invocation["project_root"]),
            artifact_reference=f"{artifact_id}@{revision}", expected=expected,
            active_exceptions=active_exceptions,
        )
        if confirmation_problem:
            open_items.append(_new_open_item(len(open_items) + 1, confirmation_problem, "CORE-G-009"))
            warnings.append({"code": "FINAL_CONFIRMATION_BINDINGS", "message": "Use these exact bindings in the authoritative confirmation record", "details": expected})
            checks = _pending_checks(open_items, [])
        elif final_confirmation["result"] == "rejected":
            errors.append({"code": "FINAL_CONFIRMATION_REJECTED", "message": "Final Confirmation rejected this Revision"})
            checks = _pending_checks([], errors)
        else:
            checks = complete_checks
            checks["CORE-G-009"] = ("pass", "Final Confirmation binds current digests")

    if errors:
        gate_result = "fail"
        status = "failed"
    elif open_items:
        gate_result = "pending"
        status = "waiting_input"
    else:
        active = [row["id"] for row in model["exceptions"] if row["state"] in {"active", "carried"}]
        gate_result = "pass_with_exception" if active else "pass"
        status = "ready_with_exception" if active else "ready"

    if "control_input_digest" not in expected:
        expected["control_input_digest"] = _control_input_digest(provisional)
    if "check_set_result_digest" not in expected:
        expected["check_set_result_digest"] = ""
    gate_summary = {
        "revision": str(revision),
        "control_input_digest": expected["control_input_digest"] if gate_result != "pending" else "",
        "evaluation_contract_set": EVALUATION_CONTRACT_SET,
        "check_set_result_digest": expected["check_set_result_digest"] if gate_result != "pending" else "",
        "gate_result": gate_result,
        "exception_references": _reference([row["id"] for row in model["exceptions"] if row["state"] in {"active", "carried"}]),
        "evaluator": "sdlc-000-ctx-runtime",
        "evaluated_at": now.isoformat(timespec="seconds"),
    }
    primary = _render_markdown(
        model, status=status, open_items=open_items, checks=checks,
        final_confirmation=final_confirmation, gate_summary=gate_summary,
    )
    payload = _canonical_payload(model, primary, status)
    failed_checks = [check_id for check_id, (result, _) in checks.items() if result == "fail"]
    return BuildProduct(payload, gate_result, failed_checks, open_items, warnings, errors, expected)


def _parse_tables(text: str) -> dict[tuple[str, ...], list[list[str]]]:
    lines = text.splitlines()
    tables: dict[tuple[str, ...], list[list[str]]] = {}
    index = 0
    while index + 1 < len(lines):
        if lines[index].startswith("|") and lines[index + 1].startswith("|") and "---" in lines[index + 1]:
            headers = tuple(cell.strip() for cell in lines[index].strip("|").split("|"))
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([cell.strip() for cell in lines[index].strip("|").split("|")])
                index += 1
            if headers in tables:
                raise ValueError(f"Duplicate table header: {headers}")
            tables[headers] = rows
            continue
        index += 1
    return tables


def _validate_ctx_tables(
    tables: Mapping[tuple[str, ...], list[list[str]]], stored: StoredRevision
) -> list[str]:
    failures: list[str] = []
    basis_reference_sets: list[str] = []
    identity_header = ("Field", "Value", "Basis", "Basis References")
    identity_rows = tables.get(identity_header, [])
    if (
        len(identity_rows) != len(IDENTITY_FIELDS)
        or [row[0] for row in identity_rows if len(row) == 4]
        != [label for _, label in IDENTITY_FIELDS]
        or any(
            len(row) != 4
            or not row[1]
            or row[2] not in ALLOWED_BASIS
            or row[3] in {"", "None", "N/A"}
            for row in identity_rows
        )
    ):
        failures.append("CTX-G-002")
    elif (
        any(not _is_typed_value(identity_rows[index][1]) for index in range(4))
        or not re.fullmatch(r"RSC-\d{3}", identity_rows[3][1])
    ):
        failures.append("CTX-G-002")
    else:
        basis_reference_sets.extend(row[3] for row in identity_rows)

    seen_ids: set[str] = set()
    resource_rows: list[list[str]] = []
    for name, (prefix, fields, check_id) in COLLECTIONS.items():
        header = tuple(label for _, label in fields)
        rows = tables.get(header, [])
        if name == "resources":
            resource_rows = rows
        if not rows:
            failures.append(check_id)
            continue
        if rows[0][0] == "None":
            expected_none = ["None"] + ["N/A"] * (len(fields) - 3) + [rows[0][-2], rows[0][-1]]
            if (
                len(rows) != 1
                or len(rows[0]) != len(fields)
                or rows[0] != expected_none
                or rows[0][-2] not in ALLOWED_BASIS
                or rows[0][-1] in {"", "None", "N/A"}
            ):
                failures.append(check_id)
            continue
        ids = [row[0] for row in rows if len(row) == len(fields)]
        normalized_rows = [dict(zip((field for field, _ in fields), row)) for row in rows if len(row) == len(fields)]
        if (
            len(ids) != len(rows)
            or ids != sorted(ids)
            or any(not re.fullmatch(prefix + r"-\d{3}", item) for item in ids)
            or any(item in seen_ids for item in ids)
            or any(row[-2] not in ALLOWED_BASIS or row[-1] in {"", "None", "N/A"} for row in rows)
            or any(_collection_row_problem(name, row) for row in normalized_rows)
        ):
            failures.append(check_id)
        basis_reference_sets.extend(row[-1] for row in rows if len(row) == len(fields))
        seen_ids.update(ids)

    if not resource_rows or resource_rows[0][0] == "None":
        failures.append("CTX-G-003")
    else:
        primary_ids = {row[0] for row in resource_rows if len(row) == 8 and row[3] == "primary"}
        resource_ids = {row[0] for row in resource_rows if len(row) == 8}
        resource_locators = [row[4] for row in resource_rows if len(row) == 8]
        identity_primary = identity_rows[3][1] if len(identity_rows) == 5 and len(identity_rows[3]) == 4 else None
        component_header = tuple(label for _, label in COLLECTIONS["components"][1])
        component_rows = [row for row in tables.get(component_header, []) if row and row[0] != "None"]
        component_ids = {row[0] for row in component_rows if len(row) == len(component_header)}
        if (
            not primary_ids
            or identity_primary not in primary_ids
            or len(resource_locators) != len(set(resource_locators))
            or any(row[3] not in resource_ids for row in component_rows if len(row) == len(component_header))
            or any(
                dependency not in component_ids
                for row in component_rows
                if len(row) == len(component_header) and row[6] != "None"
                for dependency in row[6].split(", ")
            )
        ):
            failures.append("CTX-G-003")

    evidence_header = tuple(label for _, label in EVIDENCE_FIELDS)
    evidence_rows = tables.get(evidence_header, [])
    evidence_ids: list[str] = []
    if not evidence_rows:
        failures.append("CORE-G-005")
    elif evidence_rows[0][0] == "None":
        if evidence_rows != [["None", "none", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "No independent Evidence"]]:
            failures.append("CORE-G-005")
    else:
        evidence_ids = [row[0] for row in evidence_rows if len(row) == len(EVIDENCE_FIELDS)]
        if (
            len(evidence_ids) != len(evidence_rows)
            or evidence_ids != sorted(evidence_ids)
            or len(set(evidence_ids)) != len(evidence_ids)
            or any(not re.fullmatch(r"EVD-\d{3}", item) for item in evidence_ids)
            or any(
                any(not _is_typed_value(row[index]) for index in (1, 2, 3, 4, 5, 7))
                or not _is_rfc3339(row[6])
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", row[5])
                or row[8] != "N/A"
                for row in evidence_rows
            )
        ):
            failures.append("CORE-G-005")
        seen_ids.update(evidence_ids)
    referenced_evidence = {
        reference
        for value in basis_reference_sets
        for reference in value.split(", ")
        if reference.startswith("EVD-")
    }
    if not referenced_evidence.issubset(set(evidence_ids)):
        failures.append("CTX-G-005")

    refresh_header = (
        "Base Revision", "Observed At", "Observation Baseline", "Refresh Reason",
        "Effective Change References", "Evidence References",
    )
    refresh_rows = tables.get(refresh_header, [])
    if (
        len(refresh_rows) != 1
        or len(refresh_rows[0]) != len(refresh_header)
        or not _is_rfc3339(refresh_rows[0][1])
        or any(not _is_typed_value(refresh_rows[0][index]) for index in (2, 3, 5))
        or refresh_rows[0][0] != (
            "None" if stored.control.base_revision is None else str(stored.control.base_revision)
        )
    ):
        failures.append("CTX-G-006")
    elif (
        stored.control.base_revision is not None
        and refresh_rows[0][4] == "None"
    ):
        failures.append("CTX-G-006")

    manifest_header = (
        "Member ID", "Type", "Path or Reference", "Media Type", "Purpose",
        "SHA-256 Digest", "Empty Reason",
    )
    manifest_rows = tables.get(manifest_header, [])
    expected_members = [
        [
            item.member_id, "supporting", item.canonical_name, item.media_type,
            next(
                (
                    row[4]
                    for row in manifest_rows
                    if len(row) == len(manifest_header) and row[0] == item.member_id
                ),
                "Supporting Evidence",
            ),
            "sha256:" + item.sha256, "N/A",
        ]
        for item in stored.payload.members
    ]
    if stored.payload.members:
        if (
            manifest_rows != expected_members
            or any(not _is_typed_value(row[4]) for row in manifest_rows)
        ):
            failures.append("CORE-G-003")
    elif manifest_rows != [["None", "none", "N/A", "N/A", "N/A", "N/A", "No supporting artifacts"]]:
        failures.append("CORE-G-003")

    exception_header = (
        "ID", "State", "Origin Exception Reference",
        "作用域或被跳过义务 Scope or Skipped Obligation", "原因 Reason", "已知风险 Known Risk",
        "补偿措施 Compensating Control", "批准记录 Approver, Role and Time",
        "复查条件 Revisit Condition", "下游限制 Downstream Obligation",
        "解决或替代引用 Resolution or Superseding References",
    )
    exception_rows = tables.get(exception_header, [])
    if not exception_rows:
        failures.append("CORE-G-007")
    elif exception_rows[0][0] == "None":
        if exception_rows != [["None", "none", "N/A", "N/A", "No Exceptions", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]]:
            failures.append("CORE-G-007")
    else:
        ids = [row[0] for row in exception_rows if len(row) == len(exception_header)]
        states = [row[1] for row in exception_rows if len(row) == len(exception_header)]
        if (
            len(ids) != len(exception_rows)
            or ids != sorted(ids)
            or len(set(ids)) != len(ids)
            or any(not re.fullmatch(r"EX-\d{3}", item) for item in ids)
            or any(state not in {"active", "carried", "resolved", "superseded"} for state in states)
            or any(
                any(not _is_typed_value(row[index]) for index in range(3, 10))
                or (row[1] == "active" and row[2] != "N/A")
                or (row[1] == "carried" and not re.fullmatch(r"[A-Z]+-[A-Za-z0-9-]+@[1-9]\d*#EX-\d{3}", row[2]))
                or (row[1] in {"active", "carried"} and row[10] != "N/A")
                or (row[1] in {"resolved", "superseded"} and not _is_typed_value(row[10]))
                for row in exception_rows
                if len(row) == len(exception_header)
            )
        ):
            failures.append("CORE-G-007")
    return sorted(set(failures))


def _validate_payload_closure(stored: StoredRevision) -> list[str]:
    payload = stored.payload
    failures: list[str] = []
    if (
        payload.artifact_type != "CTX"
        or payload.primary_media_type != "text/markdown"
        or payload.manifest.media_type != "application/json"
        or payload.primary_sha256 != compute_sha256(payload.primary_blob)
    ):
        failures.append("CORE-G-003")

    member_ids: set[str] = set()
    member_projection: list[dict[str, str]] = []
    for member in payload.members:
        path = Path(member.canonical_name)
        if (
            not re.fullmatch(r"SUP-\d{3}", member.member_id)
            or member.member_id in member_ids
            or not member.canonical_name
            or path.is_absolute()
            or ".." in path.parts
            or not re.fullmatch(r"[^/\s]+/[^/\s]+", member.media_type)
            or member.sha256 != compute_sha256(member.raw_bytes)
        ):
            failures.append("CORE-G-003")
        member_ids.add(member.member_id)
        member_projection.append(
            {
                "member_id": member.member_id,
                "canonical_name": member.canonical_name,
                "media_type": member.media_type,
                "sha256": member.sha256,
            }
        )
    if [member.member_id for member in payload.members] != sorted(member_ids):
        failures.append("CORE-G-003")

    manifest_projection = [
        {
            "member_id": member.member_id,
            "canonical_name": member.canonical_name,
            "media_type": member.media_type,
            "sha256": member.sha256,
        }
        for member in payload.manifest.local_members
    ]
    if manifest_projection != member_projection:
        failures.append("CORE-G-003")
    expected_manifest = {
        "contract": "sdlc-ai-spec/canonical-manifest/v1",
        "artifact": f"{payload.artifact_id}@{payload.revision}",
        "local_members": member_projection,
        "external_references": [],
    }
    try:
        parsed_manifest = json.loads(payload.manifest.raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed_manifest = None
    if parsed_manifest != expected_manifest:
        failures.append("CORE-G-003")
    return sorted(set(failures))


def validate_stored_revision(stored: StoredRevision) -> tuple[list[str], str, list[dict[str, str]]]:
    failures: list[str] = _validate_payload_closure(stored)
    try:
        text = stored.payload.primary_blob.decode("utf-8")
    except UnicodeDecodeError:
        return ["CORE-G-003"], "fail", []
    expected_front = [
        "---", f"contract: {CTX_CONTRACT}", f"id: {stored.payload.artifact_id}",
        f"revision: {stored.payload.revision}", f"status: {stored.payload.artifact_status}", "---",
    ]
    if text.splitlines()[:6] != expected_front:
        failures.append("CORE-G-001")
    required_headings = [
        "## 摘要 Summary", "## 项目标识 Project Identity", "## 资源登记 Resource Registry",
        "## 技术与工程基线 Technical and Engineering Baseline", "### 技术基线 Technology Baseline",
        "### 工程入口 Engineering Entry Points", "## 项目结构 Project Topology", "## 项目规则 Project Rules",
        "## 环境与约束 Environment and Constraints", "### 环境 Environment", "### 约束 Constraints",
        "## 待确认项 Open Items", "## 证据 Evidence", "## 刷新摘要 Refresh Summary",
        "## 支撑产物清单 Supporting Artifact Manifest", "## 豁免 Exceptions", "## 门禁 Gate",
    ]
    positions = [text.find(heading + "\n") for heading in required_headings]
    all_headings = [
        line for line in text.splitlines() if line.startswith("## ") or line.startswith("### ")
    ]
    expected_headings = [
        *required_headings,
        "### Core Checks", "### CTX Checks", "### Final Confirmation",
        "### Artifact Gate Summary",
    ]
    summary_start = text.find("## 摘要 Summary\n")
    summary_end = text.find("## 项目标识 Project Identity\n")
    summary = text[summary_start + len("## 摘要 Summary\n"):summary_end].strip()
    if (
        any(position < 0 for position in positions)
        or positions != sorted(positions)
        or all_headings != expected_headings
        or not _is_typed_value(summary)
    ):
        failures.append("CTX-G-001")
    try:
        tables = _parse_tables(text)
        check_rows = tables[("Check ID", "检查项 Check", "结果 Result", "证据或说明 Evidence or Notes")]
        ctx_rows = tables[("Check ID", "Check", "Result", "Basis References")]
        fc_rows = tables[("Revision", "Control Input Digest", "Evaluation Contract Set", "Check Set Result Digest", "Result", "Mode", "Confirmer", "Role", "Authority Reference", "Accepted Exception References", "Confirmed At")]
        gate_rows = tables[("Evaluated Revision", "Control Input Digest", "Evaluation Contract Set", "Check Set Result Digest", "Gate Result", "Exception References", "Evaluator", "Evaluated At")]
        open_rows = tables[("ID", "所需输入或待确认决策 Needed Input or Decision", "预期来源 Expected Source", "被阻塞项 Blocked References", "状态 State", "解决结果或证据 Resolution or Evidence")]
    except (KeyError, ValueError):
        return sorted(set(failures + ["CORE-G-003"])), "fail", []
    expected_table_headers = {
        ("Field", "Value", "Basis", "Basis References"),
        *(tuple(label for _, label in fields) for _, fields, _ in COLLECTIONS.values()),
        tuple(label for _, label in EVIDENCE_FIELDS),
        ("Base Revision", "Observed At", "Observation Baseline", "Refresh Reason", "Effective Change References", "Evidence References"),
        ("Member ID", "Type", "Path or Reference", "Media Type", "Purpose", "SHA-256 Digest", "Empty Reason"),
        (
            "ID", "State", "Origin Exception Reference",
            "作用域或被跳过义务 Scope or Skipped Obligation", "原因 Reason", "已知风险 Known Risk",
            "补偿措施 Compensating Control", "批准记录 Approver, Role and Time",
            "复查条件 Revisit Condition", "下游限制 Downstream Obligation",
            "解决或替代引用 Resolution or Superseding References",
        ),
        ("ID", "所需输入或待确认决策 Needed Input or Decision", "预期来源 Expected Source", "被阻塞项 Blocked References", "状态 State", "解决结果或证据 Resolution or Evidence"),
        ("Check ID", "检查项 Check", "结果 Result", "证据或说明 Evidence or Notes"),
        ("Check ID", "Check", "Result", "Basis References"),
        ("Revision", "Control Input Digest", "Evaluation Contract Set", "Check Set Result Digest", "Result", "Mode", "Confirmer", "Role", "Authority Reference", "Accepted Exception References", "Confirmed At"),
        ("Evaluated Revision", "Control Input Digest", "Evaluation Contract Set", "Check Set Result Digest", "Gate Result", "Exception References", "Evaluator", "Evaluated At"),
    }
    if set(tables) != expected_table_headers:
        failures.append("CORE-G-003")
    failures.extend(_validate_ctx_tables(tables, stored))
    check_map = {row[0]: (row[2], row[3]) for row in (*check_rows, *ctx_rows) if len(row) == 4}
    if (
        [row[0] for row in check_rows if len(row) == 4] != list(CORE_CHECKS)
        or [row[0] for row in ctx_rows if len(row) == 4] != list(CTX_CHECKS)
        or set(check_map) != set((*CORE_CHECKS, *CTX_CHECKS))
        or any(result not in {"pending", "pass", "fail"} for result, _ in check_map.values())
        or any(not _is_typed_value(notes) for _, notes in check_map.values())
    ):
        failures.append("CORE-G-008")
    gate = gate_rows[0] if len(gate_rows) == 1 and len(gate_rows[0]) == 8 else []
    fc = fc_rows[0] if len(fc_rows) == 1 and len(fc_rows[0]) == 11 else []
    if (
        not gate
        or gate[0] != str(stored.payload.revision)
        or gate[2] != EVALUATION_CONTRACT_SET
        or gate[4] not in {"pending", "pass", "pass_with_exception", "fail"}
        or not _is_typed_value(gate[6])
        or not _is_rfc3339(gate[7])
    ):
        failures.append("CORE-G-008")
    exception_rows = tables.get(
        (
            "ID", "State", "Origin Exception Reference",
            "作用域或被跳过义务 Scope or Skipped Obligation", "原因 Reason", "已知风险 Known Risk",
            "补偿措施 Compensating Control", "批准记录 Approver, Role and Time",
            "复查条件 Revisit Condition", "下游限制 Downstream Obligation",
            "解决或替代引用 Resolution or Superseding References",
        ),
        [],
    )
    active_exceptions = sorted(
        row[0]
        for row in exception_rows
        if len(row) == 11 and row[0] != "None" and row[1] in {"active", "carried"}
    )
    if gate:
        try:
            control_digest = _control_input_digest(stored.payload.primary_blob)
            if gate[1] and gate[1] != control_digest:
                failures.append("CORE-G-009")
            if gate[4] in {"pass", "pass_with_exception"}:
                check_digest = _check_digest(check_map)
                accepted = sorted([] if not fc or fc[9] == "None" else fc[9].split(", "))
                if (
                    gate[1] != control_digest
                    or gate[3] != check_digest
                    or gate[5] != _reference(active_exceptions)
                    or not fc
                    or fc[0] != str(stored.payload.revision)
                    or fc[1:4] != gate[1:4]
                    or fc[4] != "approved"
                    or fc[5] not in {"human", "delegated"}
                    or not IDENTITY_TOKEN_RE.fullmatch(fc[6])
                    or not _is_typed_value(fc[7])
                    or not AUTHORITY_REFERENCE_RE.fullmatch(fc[8])
                    or accepted != active_exceptions
                    or not _is_rfc3339(fc[10])
                    or any(result != "pass" for result, _ in check_map.values())
                    or (gate[4] == "pass" and active_exceptions)
                    or (gate[4] == "pass_with_exception" and not active_exceptions)
                    or (fc[5] == "delegated" and (active_exceptions or fc[7] != "Delegated Independent Reviewer"))
                ):
                    failures.append("CORE-G-009")
        except ValueError:
            failures.append("CORE-G-008")
    open_items = []
    if open_rows == [["None", "No open items", "N/A", "N/A", "none", "N/A"]]:
        pass
    else:
        ids = [row[0] for row in open_rows if len(row) == 6]
        if (
            len(ids) != len(open_rows)
            or ids != sorted(ids)
            or len(set(ids)) != len(ids)
            or any(not re.fullmatch(r"OPI-\d{3}", item) for item in ids)
            or any(
                row[4] not in {"open", "resolved"}
                or not _is_typed_value(row[1])
                or not _is_typed_value(row[2])
                or not row[3]
                or any(check not in {*CORE_CHECKS, *CTX_CHECKS} for check in row[3].split(", "))
                or (row[4] == "open" and row[5] != "N/A")
                or (row[4] == "resolved" and not _is_typed_value(row[5]))
                for row in open_rows
                if len(row) == 6
            )
        ):
            failures.append("CORE-G-006")
        for row in open_rows:
            if len(row) == 6 and row[0] != "None" and row[4] == "open":
                open_items.append({"id": row[0], "needed": row[1], "expected_source": row[2], "blocked_references": row[3], "state": row[4], "resolution": row[5]})
    gate_result = gate[4] if gate else "fail"
    expected_status = {
        "pass": "ready", "pass_with_exception": "ready_with_exception", "fail": "failed",
    }.get(gate_result, "waiting_input" if open_items else "draft")
    if stored.payload.artifact_status != expected_status:
        failures.append("CTX-G-006")
    if gate_result == "pending" and not open_items and stored.payload.artifact_status != "draft":
        failures.append("CTX-G-006")
    if gate_result in {"pass", "pass_with_exception"} and open_items:
        failures.append("CTX-G-006")
    return sorted(set(failures)), gate_result if not failures else "fail", open_items


class CtxDomainVerifier:
    def verify(self, reference: str, revision: StoredRevision) -> DomainVerification:
        failures, gate_result, _ = validate_stored_revision(revision)
        approved = not failures and gate_result in {"pass", "pass_with_exception"}
        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=approved,
            message="" if approved else "CTX Domain Validator failed: " + ", ".join(failures or [gate_result]),
        )


def _parse_ctx_reference(value: Any, operation: str) -> tuple[str, int] | dict[str, Any]:
    if value is None or value == "":
        return error_result(
            operation=operation, status="action_required", code="ARTIFACT_REFERENCE_REQUIRED",
            message="An exact CTX Reference is required", next_action_code="PROVIDE_EXACT_CTX_REFERENCE",
            next_action_message="提供准确的 CTX-ID@数字Revision", requires_user=True,
        )
    match = CTX_REFERENCE_RE.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        return error_result(
            operation=operation, status="action_required", code="ARTIFACT_REFERENCE_INVALID",
            message="Reference must be an exact numeric CTX Revision; latest/current are forbidden",
            next_action_code="PROVIDE_EXACT_CTX_REFERENCE", next_action_message="提供准确的 CTX-ID@数字Revision", requires_user=True,
        )
    return match.group(1), int(match.group(2))


def _project_root(invocation: Mapping[str, Any], operation: str) -> Path | dict[str, Any]:
    root = Path(invocation["project_root"])
    if not root.is_absolute() or not root.exists() or not root.is_dir():
        return error_result(
            operation=operation, status="action_required", code="TARGET_AMBIGUOUS",
            message="project_root must identify one existing absolute directory",
            next_action_code="PROVIDE_UNIQUE_PROJECT_ROOT", next_action_message="提供唯一、现存的绝对 Project Root", requires_user=True,
        )
    return root.resolve()


def _write_authorized(invocation: Mapping[str, Any]) -> bool:
    item = _confirmation(invocation, "write")
    return bool(item and item.get("approved") is True and set(item) == {"type", "approved"})


def _recoverable_initialize_failure(exc: ArtifactStoreError) -> bool:
    if exc.code == "SCHEMA_ERROR":
        return True
    if exc.code == "CONFLICT":
        return exc.message.startswith(
            (
                "Artifact Store appeared during initialize",
                "Existing runtime ignore file does not contain the fixed content",
            )
        )
    return exc.code == "DATABASE_ERROR" and "database is locked" in exc.message.lower()


def _recoverable_validation_failure(exc: ArtifactStoreError) -> bool:
    if exc.code in {"STORE_NOT_FOUND", "SCHEMA_ERROR"}:
        return True
    return exc.code == "DATABASE_ERROR" and "database is locked" in exc.message.lower()


def _open_initialized_store(root: Path, *, clock: Any) -> ArtifactStore:
    store = ArtifactStore.open_read_write(root, clock=clock)
    deadline = time.monotonic() + INITIALIZE_RECOVERY_TIMEOUT_SECONDS
    last_error: ArtifactStoreError | None = None
    while True:
        try:
            store.initialize()
        except ArtifactStoreError as initialize_error:
            last_error = initialize_error
            if not _recoverable_initialize_failure(initialize_error):
                raise
        else:
            try:
                ArtifactStore.open_read_only(root)
                return store
            except ArtifactStoreError as validation_error:
                last_error = validation_error
                if not _recoverable_validation_failure(validation_error):
                    raise
        if time.monotonic() >= deadline:
            assert last_error is not None
            raise last_error
        time.sleep(INITIALIZE_RECOVERY_DELAY_SECONDS)


def _run_with_lock_recovery(root: Path, operation: Callable[[], T]) -> T:
    try:
        return operation()
    except ArtifactStoreError as operation_error:
        if not _recoverable_validation_failure(operation_error):
            raise
        last_error = operation_error

    deadline = time.monotonic() + INITIALIZE_RECOVERY_TIMEOUT_SECONDS
    while True:
        try:
            ArtifactStore.open_read_only(root)
        except ArtifactStoreError as validation_error:
            last_error = validation_error
            if not (
                validation_error.code == "DATABASE_ERROR"
                and "database is locked" in validation_error.message.lower()
            ):
                raise
        else:
            try:
                return operation()
            except ArtifactStoreError as retry_error:
                last_error = retry_error
                if not (
                    retry_error.code == "DATABASE_ERROR"
                    and "database is locked" in retry_error.message.lower()
                ):
                    raise
        if time.monotonic() >= deadline:
            raise last_error
        time.sleep(INITIALIZE_RECOVERY_DELAY_SECONDS)


class CtxHandler:
    def __init__(self, *, clock: Any = None):
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def create(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        root = _project_root(invocation, "create")
        if isinstance(root, dict):
            return root
        context = invocation["inputs"].get("context")
        identity = context.get("project_identity") if isinstance(context, Mapping) else None
        boundary_fact = identity.get("boundary") if isinstance(identity, Mapping) else None
        boundary_confirmation = _confirmation(invocation, "project_boundary")
        evidence_input = invocation["inputs"].get("evidence", [])
        evidence_ids = {
            item.get("id") for item in evidence_input if isinstance(item, Mapping)
        } if isinstance(evidence_input, list) else set()
        fact, problem = _valid_fact(boundary_fact, evidence_ids) if isinstance(context, Mapping) else (None, "missing")
        if (
            problem or fact is None or fact["basis"] != "confirmed" or boundary_confirmation is None
            or boundary_confirmation.get("value") != fact["value"]
            or boundary_confirmation.get("authority_reference") not in fact["basis_references"].split(", ")
        ):
            return error_result(
                operation="create", status="action_required", code="PROJECT_BOUNDARY_CONFIRMATION_REQUIRED",
                message="Project Boundary requires a separate matching confirmed Basis before any Store allocation",
                next_action_code="CONFIRM_PROJECT_BOUNDARY", next_action_message="提供匹配 Boundary 的明确确认与 Evidence", requires_user=True,
            )
        dry_run = invocation["options"].get("dry_run", False)
        if not dry_run and not _write_authorized(invocation):
            return error_result(
                operation="create", status="action_required", code="WRITE_AUTHORIZATION_REQUIRED",
                message="create requires a separate explicit write authorization", next_action_code="AUTHORIZE_CTX_WRITE",
                next_action_message="明确授权写入准确 Project Root 的 .sdlc Store", requires_user=True,
            )
        now = self.clock()
        if dry_run:
            product = build_payload(invocation, artifact_id="CTX-00000000000000-00", revision=1, base_revision=None, now=now)
            return _artifact_result(
                "create", ok=True, status="completed", artifact=None, gate_result=product.gate_result,
                failed_checks=product.failed_checks, open_items=product.open_items,
                warnings=[*product.warnings, {"code": "DRY_RUN", "message": "No Store, Artifact ID, Revision, write, freeze, or Authority was created"}],
                errors=[], next_action=_action("REVIEW_DRY_RUN", "检查候选结果；需要持久化时另行明确写入授权", user=True),
            )
        preliminary = build_payload(invocation, artifact_id="CTX-00000000000000-00", revision=1, base_revision=None, now=now)
        if preliminary.errors:
            return _artifact_result(
                "create", ok=False, status="failed", artifact=None, gate_result="fail",
                failed_checks=preliminary.failed_checks, open_items=preliminary.open_items,
                warnings=preliminary.warnings, errors=preliminary.errors,
                next_action=_action("CORRECT_CTX_INPUT", "修正结构化 CTX 输入后重试", user=True),
            )
        try:
            store = _open_initialized_store(root, clock=self.clock)
            registry = ContextLineageRegistry(store)
            key = boundary_key(fact["value"])
            binding = _run_with_lock_recovery(
                root, lambda: registry.reserve(key, now=now)
            )
            if not binding.created:
                return _artifact_result(
                    "create", ok=False, status="blocked",
                    artifact={"id": binding.artifact_id, "type": "CTX", "revision": None, "revision_state": None, "artifact_status": None, "reference": None},
                    errors=[{"code": "CTX_LINEAGE_EXISTS", "message": "This confirmed Project Boundary already has a CTX Lineage"}],
                    next_action=_action("USE_EXISTING_CTX_LINEAGE", f"使用已有 CTX ID {binding.artifact_id} 的准确 Revision", user=True),
                )
            control = _run_with_lock_recovery(
                root, lambda: store.allocate_revision(binding.artifact_id, now=now)
            )
            product = build_payload(invocation, artifact_id=binding.artifact_id, revision=control.revision, base_revision=None, now=now)
            stored = store.write_open_revision(product.payload, expected_generation=control.generation)
            if product.gate_result in {"pass", "pass_with_exception"}:
                store.freeze_revision(binding.artifact_id, control.revision, verifier=CtxDomainVerifier(), now=now)
                stored = store.read_revision(binding.artifact_id, control.revision)
            return self._product_result("create", stored, product)
        except ArtifactStoreError as exc:
            return self._store_error("create", exc)

    def revise(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._revise_or_check(invocation, check=False)

    def check(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._revise_or_check(invocation, check=True)

    def _revise_or_check(self, invocation: Mapping[str, Any], *, check: bool) -> Mapping[str, Any]:
        operation = "check" if check else "revise"
        allocated_writer: ArtifactStore | None = None
        allocated_control: Any = None
        root = _project_root(invocation, operation)
        if isinstance(root, dict):
            return root
        parsed = _parse_ctx_reference(invocation.get("artifact_reference"), operation)
        if isinstance(parsed, dict):
            return parsed
        artifact_id, revision = parsed
        dry_run = invocation["options"].get("dry_run", False)
        if not check and not dry_run and not _write_authorized(invocation):
            return error_result(
                operation="revise", status="action_required", code="WRITE_AUTHORIZATION_REQUIRED",
                message="revise requires a separate explicit write authorization", next_action_code="AUTHORIZE_CTX_WRITE",
                next_action_message="明确授权修订准确 CTX Revision", requires_user=True,
            )
        try:
            reader = ArtifactStore.open_read_only(root)
            current = reader.read_revision(artifact_id, revision)
            if check:
                failures, gate_result, open_items = validate_stored_revision(current)
                if failures:
                    return _artifact_result(
                        "check", ok=False, status="failed", artifact=_artifact_view(current, authority=False),
                        gate_result="fail", failed_checks=failures,
                        errors=[{"code": "CTX_DOMAIN_INVALID", "message": "Stored CTX failed deterministic domain validation", "details": failures}],
                        next_action=_action("REVISE_EXACT_CTX", "在独立、明确授权的 revise 操作中修正准确 CTX", user=True),
                    )
                authority = current.control.state == "frozen" and gate_result in {"pass", "pass_with_exception"}
                warning = [] if authority else [{"code": "NON_AUTHORITY_STATE", "message": f"Revision state {current.control.state} does not provide Context Authority"}]
                return _artifact_result(
                    "check", ok=True, status="completed", artifact=_artifact_view(current, authority=authority),
                    gate_result=gate_result, open_items=open_items, warnings=warning,
                    next_action=None if authority else _action("REVISE_EXACT_CTX", "如需形成 Authority，请显式修订此准确 Revision", user=True),
                )
            if current.control.state == "abandoned":
                return _artifact_result(
                    "revise", ok=False, status="failed", artifact=_artifact_view(current, authority=False),
                    errors=[{"code": "INVALID_STATE", "message": "An abandoned Revision cannot be revived"}],
                    next_action=_action("SELECT_VALID_BASE", "提供同一 CTX Lineage 的准确 frozen 或 materialized open Revision", user=True),
                )
            now = self.clock()
            preview_revision = revision if current.control.state == "open" else revision + 1
            preview_product = build_payload(
                invocation,
                artifact_id=artifact_id,
                revision=preview_revision,
                base_revision=revision if current.control.state == "frozen" else current.control.base_revision,
                now=now,
            )
            if preview_product.errors:
                return _artifact_result(
                    "revise", ok=False, status="failed", artifact=_artifact_view(current, authority=current.control.state == "frozen"),
                    gate_result="fail", failed_checks=preview_product.failed_checks, open_items=preview_product.open_items,
                    warnings=preview_product.warnings, errors=preview_product.errors,
                    next_action=_action("CORRECT_CTX_INPUT", "修正结构化 CTX 输入后重试", user=True),
                )
            if current.control.state == "frozen":
                refresh = invocation["inputs"].get("refresh")
                no_effective_change = (
                    isinstance(refresh, Mapping)
                    and _reference(refresh.get("effective_change_references")) == "None"
                    and _effective_content_digest(preview_product.payload.primary_blob)
                    == _effective_content_digest(current.payload.primary_blob)
                )
                if no_effective_change:
                    current_tables = _parse_tables(current.payload.primary_blob.decode("utf-8"))
                    gate_rows = current_tables[("Evaluated Revision", "Control Input Digest", "Evaluation Contract Set", "Check Set Result Digest", "Gate Result", "Exception References", "Evaluator", "Evaluated At")]
                    return _artifact_result(
                        "revise", ok=True, status="completed", artifact=_artifact_view(current, authority=True),
                        gate_result=gate_rows[0][4], warnings=[{"code": "NO_EFFECTIVE_CHANGE", "message": "No new Revision was allocated"}], next_action=None,
                    )
            if dry_run:
                return _artifact_result(
                    "revise", ok=True, status="completed", artifact=None, gate_result=preview_product.gate_result,
                    failed_checks=preview_product.failed_checks, open_items=preview_product.open_items,
                    warnings=[*preview_product.warnings, {"code": "DRY_RUN", "message": "No Revision, write, freeze, or Authority was created"}],
                    next_action=_action("REVIEW_DRY_RUN", "检查候选修订；需要持久化时另行明确写入授权", user=True),
                )
            writer = ArtifactStore.open_read_write(root, clock=self.clock)
            writer.initialize()
            if current.control.state == "frozen":
                control = writer.allocate_revision(artifact_id, base_revision=revision, now=now)
                allocated_writer = writer
                allocated_control = control
                product = build_payload(
                    invocation,
                    artifact_id=artifact_id,
                    revision=control.revision,
                    base_revision=revision,
                    now=now,
                )
            else:
                control = current.control
                product = preview_product
            stored = writer.write_open_revision(product.payload, expected_generation=control.generation)
            if product.gate_result in {"pass", "pass_with_exception"}:
                writer.freeze_revision(artifact_id, control.revision, verifier=CtxDomainVerifier(), now=now)
                stored = writer.read_revision(artifact_id, control.revision)
            return self._product_result("revise", stored, product)
        except ControlReservationError as exc:
            cleanup_error = self._abandon_unmaterialized_reservation(
                allocated_writer, allocated_control
            )
            if cleanup_error is not None:
                return self._store_error(operation, cleanup_error)
            return self._store_error(operation, exc)
        except (ArtifactStoreError, KeyError, ValueError) as exc:
            cleanup_error = self._abandon_unmaterialized_reservation(
                allocated_writer, allocated_control
            )
            if cleanup_error is not None:
                return self._store_error(operation, cleanup_error)
            if isinstance(exc, ArtifactStoreError):
                return self._store_error(operation, exc)
            return _artifact_result(
                operation, ok=False, status="failed", artifact=None,
                errors=[{"code": "CTX_DOMAIN_INVALID", "message": str(exc)}],
                next_action=_action("INSPECT_EXACT_CTX", "检查准确 CTX Revision 的结构和状态", user=True),
            )
        except Exception as exc:
            cleanup_error = self._abandon_unmaterialized_reservation(
                allocated_writer, allocated_control
            )
            if cleanup_error is not None:
                return self._store_error(operation, cleanup_error)
            return _artifact_result(
                operation, ok=False, status="failed", artifact=None,
                errors=[{"code": "CTX_DOMAIN_INVALID", "message": str(exc)}],
                next_action=_action("INSPECT_EXACT_CTX", "检查准确 CTX Revision 的结构和状态", user=True),
            )

    @staticmethod
    def _abandon_unmaterialized_reservation(
        writer: ArtifactStore | None, control: Any
    ) -> ArtifactStoreError | None:
        if writer is None or control is None:
            return None
        try:
            writer.read_revision(control.artifact_id, control.revision)
            return None
        except ControlReservationError:
            try:
                writer.abandon_revision(
                    control.artifact_id,
                    control.revision,
                    reason="CTX revise failed before Payload materialization",
                )
            except ArtifactStoreError as cleanup_error:
                return cleanup_error
            return None
        except ArtifactStoreError as read_error:
            return read_error

    def _product_result(self, operation: str, stored: StoredRevision, product: BuildProduct) -> Mapping[str, Any]:
        authority = stored.control.state == "frozen" and product.gate_result in {"pass", "pass_with_exception"}
        if product.errors:
            result_status, ok = "failed", False
        elif product.open_items:
            result_status, ok = "action_required", False
        else:
            result_status, ok = "completed", True
        return _artifact_result(
            operation, ok=ok, status=result_status, artifact=_artifact_view(stored, authority=authority),
            gate_result=product.gate_result, failed_checks=product.failed_checks,
            open_items=product.open_items, warnings=product.warnings, errors=product.errors,
            next_action=(
                None if authority else _action("PROVIDE_REQUIRED_CTX_INPUT", "补充 Open Items 或准确 Final Confirmation 后显式 revise 当前 Revision", user=True)
            ),
        )

    @staticmethod
    def _store_error(operation: str, exc: ArtifactStoreError) -> Mapping[str, Any]:
        return _artifact_result(
            operation, ok=False, status="failed", artifact=None,
            errors=[{"code": exc.code, "message": exc.message}],
            next_action=_action("RESOLVE_STORE_FAILURE", "根据准确错误修复目标 Store 或选择有效 Project Root", user=True),
        )


def _verify_bundled_source_lock() -> None:
    lock_path = Path(__file__).resolve().parents[1] / "references" / "source-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    entries = validate_source_lock_shape(lock)
    by_id = {item["contract_id"]: item for item in entries}
    registry = load_registry(PLUGIN_ROOT / "skills/_shared/contracts/registry.json")
    for source in registry:
        item = by_id.get(source.contract_id)
        actual = hashlib.sha256((PLUGIN_ROOT / source.resource).read_bytes()).hexdigest()
        if item is None or item["contract_version"] != source.contract_version or item["sha256"] != actual:
            raise SourceLockError(f"bundled runtime contract drift: {source.contract_id}")
    expected_build = {
        "sdlc-ai-spec/build-source/core/v1.1": "1eefa7a138f2d221140137a5fac0f5429b7f847273fe9d70e891ace6c3b7a89b",
        "sdlc-ai-spec/build-source/artifact-store/v1.1": "b340ca2a38dfe0f7409acaa8f9ac559e8872bed44725037889528e3d167d4764",
        "sdlc-ai-spec/build-source/ctx/v1.1": "1d98e7cce686664cbf9897cbac852c425644ba3ea81a0d9c1db5e27b0e530470",
    }
    for contract_id, digest in expected_build.items():
        item = by_id.get(contract_id)
        if item is None or item["contract_version"] != "1.1" or item["sha256"] != digest:
            raise SourceLockError(f"build source lock drift: {contract_id}")
    if set(by_id) != {source.contract_id for source in registry} | set(expected_build):
        raise SourceLockError("source lock contract set is not exact")


def invoke(value: Mapping[str, Any], *, clock: Any = None) -> dict[str, Any]:
    operation = value.get("operation") if isinstance(value, Mapping) else None
    safe_operation = operation if operation in {"create", "revise", "check"} else "check"
    if _FOUNDATION_IMPORT_ERROR is not None:
        return _bootstrap_error_result(
            safe_operation,
            code="FOUNDATION_RUNTIME_UNAVAILABLE",
            message=f"Bundled Foundation Runtime is unavailable: {_FOUNDATION_IMPORT_ERROR}",
            next_action_code="RESTORE_VERIFIED_PLUGIN_RUNTIME",
            next_action_message="恢复包含共享 Runtime 与 ArtifactStore Package 的完整 Plugin Runtime",
            requires_user=False,
        )
    try:
        _verify_bundled_source_lock()
        return execute_phase(CtxHandler(clock=clock), value)
    except EnvelopeValidationError as exc:
        return error_result(
            operation=safe_operation, status="failed", code="INVALID_ENVELOPE", message=str(exc),
            next_action_code="CORRECT_INVOCATION_ENVELOPE", next_action_message="按共享 Invocation Contract 修正输入", requires_user=True,
        )
    except (SourceLockError, OSError, json.JSONDecodeError) as exc:
        return error_result(
            operation=safe_operation, status="failed", code="SOURCE_LOCK_INVALID", message=str(exc),
            next_action_code="RESTORE_VERIFIED_PLUGIN_RUNTIME", next_action_message="恢复与 Source Lock 一致的完整 Plugin Runtime", requires_user=False,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute one sdlc-000-ctx Runtime operation")
    parser.add_argument("invocation", nargs="?", help="Invocation JSON file; stdin when omitted")
    args = parser.parse_args(argv)
    try:
        raw = Path(args.invocation).read_text(encoding="utf-8") if args.invocation else sys.stdin.read()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        if _FOUNDATION_IMPORT_ERROR is None:
            result = error_result(operation="check", status="failed", code="INVALID_ENVELOPE", message=str(exc), next_action_code="CORRECT_INVOCATION_ENVELOPE", next_action_message="提供合法 JSON Invocation", requires_user=True)
        else:
            result = _bootstrap_error_result(
                "check", code="INVALID_ENVELOPE", message=str(exc),
                next_action_code="CORRECT_INVOCATION_ENVELOPE",
                next_action_message="提供合法 JSON Invocation", requires_user=True,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    result = invoke(value)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
