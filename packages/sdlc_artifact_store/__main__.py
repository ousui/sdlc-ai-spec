"""JSON-in/JSON-out command line interface for the shared ArtifactStore."""

import argparse
import base64
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .errors import (
    ArtifactStoreError,
    ConflictError,
    ControlReservationError,
    DatabaseError,
    IntegrityError,
    InvalidInputError,
    InvalidStateError,
    NotFoundError,
    ReadOnlyError,
    ReferenceError,
    SchemaError,
    StaleVerificationError,
    StoreNotFoundError,
    TrackedRuntimeContentError,
    VerificationFailedError,
    VerifierRequiredError,
)
from .models import (
    CanonicalManifest,
    CanonicalMember,
    CanonicalRevisionPayload,
    ClaimReservation,
    ManifestMember,
    RevisionControlRecord,
    StoredRevision,
)
from .sqlite_store import ArtifactStore


READ_ONLY_OPERATIONS = frozenset(
    {"read_revision", "resolve_exact_reference", "verify_digest"}
)


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise InvalidInputError(message)


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = JsonArgumentParser(description="Shared Local SQLite ArtifactStore")
    parser.add_argument("--project-root", required=True, help="Explicit target Project Root")
    parser.add_argument(
        "--operation",
        required=True,
        choices=(
            "initialize",
            "allocate_artifact",
            "allocate_revision",
            "read_revision",
            "write_open_revision",
            "freeze_revision",
            "abandon_revision",
            "resolve_exact_reference",
            "verify_digest",
        ),
    )
    parser.add_argument(
        "--input",
        help="JSON input path, or '-' for stdin; omitted means an empty object",
    )
    return parser.parse_args(argv)


def _load_input(location: Optional[str]) -> Dict[str, Any]:
    if location is None:
        return {}
    try:
        raw = sys.stdin.read() if location == "-" else Path(location).read_text("utf-8")
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidInputError(f"Cannot read JSON input: {exc}") from exc
    if not isinstance(value, dict):
        raise InvalidInputError("JSON input must be one object")
    return value


def _parse_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidInputError("now must be an RFC 3339 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidInputError(f"Invalid RFC 3339 time: {value}") from exc
    if parsed.tzinfo is None:
        raise InvalidInputError("now must include a timezone offset")
    return parsed


def _parse_claim(data: Dict[str, Any]) -> Optional[ClaimReservation]:
    value = data.get("claim")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise InvalidInputError("claim must be an object")
    try:
        return ClaimReservation(
            binding_lineage=value["binding_lineage"],
            attempt=value["attempt"],
            owner=value["owner"],
        )
    except KeyError as exc:
        raise InvalidInputError(f"claim is missing field: {exc.args[0]}") from exc


def _decode_bytes(value: Any, label: str) -> bytes:
    if not isinstance(value, str):
        raise InvalidInputError(f"{label} must be base64 text")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise InvalidInputError(f"{label} is not valid base64") from exc


def _parse_payload(data: Dict[str, Any]) -> CanonicalRevisionPayload:
    value = data.get("payload")
    if not isinstance(value, dict):
        raise InvalidInputError("payload must be an object")
    manifest_value = value.get("manifest")
    if not isinstance(manifest_value, dict):
        raise InvalidInputError("payload.manifest must be an object")
    members_value = value.get("members", [])
    local_members_value = manifest_value.get("local_members", [])
    if not isinstance(members_value, list) or not isinstance(local_members_value, list):
        raise InvalidInputError("members and manifest.local_members must be arrays")
    try:
        members = tuple(
            CanonicalMember(
                member_id=item["member_id"],
                canonical_name=item["canonical_name"],
                media_type=item["media_type"],
                raw_bytes=_decode_bytes(item["raw_bytes_base64"], "member raw bytes"),
                sha256=item["sha256"],
            )
            for item in members_value
        )
        manifest_members = tuple(
            ManifestMember(
                member_id=item["member_id"],
                canonical_name=item["canonical_name"],
                media_type=item["media_type"],
                sha256=item["sha256"],
            )
            for item in local_members_value
        )
        return CanonicalRevisionPayload(
            artifact_id=value["artifact_id"],
            artifact_type=value["artifact_type"],
            revision=value["revision"],
            artifact_status=value["artifact_status"],
            primary_blob=_decode_bytes(value["primary_blob_base64"], "primary_blob_base64"),
            primary_media_type=value["primary_media_type"],
            primary_sha256=value["primary_sha256"],
            members=members,
            manifest=CanonicalManifest(
                raw_bytes=_decode_bytes(
                    manifest_value["raw_bytes_base64"], "manifest.raw_bytes_base64"
                ),
                media_type=manifest_value["media_type"],
                local_members=manifest_members,
            ),
        )
    except (KeyError, TypeError) as exc:
        missing = exc.args[0] if isinstance(exc, KeyError) else str(exc)
        raise InvalidInputError(f"Malformed Payload input: {missing}") from exc


def _control_json(control: RevisionControlRecord) -> Dict[str, Any]:
    result = {
        "artifact_id": control.artifact_id,
        "revision": control.revision,
        "state": control.state,
        "base_revision": control.base_revision,
        "allocated_at": control.allocated_at,
        "frozen_at": control.frozen_at,
        "abandon_reason": control.abandon_reason,
        "generation": control.generation,
        "materialized": control.materialized,
    }
    if control.claim is not None:
        result["claim"] = {
            "binding_lineage": control.claim.binding_lineage,
            "attempt": control.claim.attempt,
            "owner": control.claim.owner,
        }
    return result


def _stored_json(stored: StoredRevision) -> Dict[str, Any]:
    return {
        "control": _control_json(stored.control),
        "payload": {
            "artifact_id": stored.payload.artifact_id,
            "artifact_type": stored.payload.artifact_type,
            "revision": stored.payload.revision,
            "artifact_status": stored.payload.artifact_status,
            "primary_media_type": stored.payload.primary_media_type,
            "primary_sha256": stored.payload.primary_sha256,
            "members": [
                {
                    "member_id": member.member_id,
                    "canonical_name": member.canonical_name,
                    "media_type": member.media_type,
                    "sha256": member.sha256,
                }
                for member in stored.payload.members
            ],
            "manifest": {
                "media_type": stored.payload.manifest.media_type,
                "local_member_count": len(stored.payload.manifest.local_members),
            },
        },
    }


def _execute(operation: str, root: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    store = (
        ArtifactStore.open_read_only(root)
        if operation in READ_ONLY_OPERATIONS
        else ArtifactStore.open_read_write(root)
    )
    if operation == "initialize":
        return {"schema_version": store.initialize(), "store": str(store.store_path)}
    if operation == "allocate_artifact":
        allocation = store.allocate_artifact(
            data.get("artifact_type"),
            now=_parse_time(data.get("now")),
            external_artifact_id=data.get("external_artifact_id"),
            claim=_parse_claim(data),
        )
        return {
            "artifact_id": allocation.artifact_id,
            "artifact_type": allocation.artifact_type,
            "created_at": allocation.created_at,
        }
    if operation == "allocate_revision":
        control = store.allocate_revision(
            data.get("artifact_id"),
            base_revision=data.get("base_revision"),
            now=_parse_time(data.get("now")),
            external_revision=data.get("external_revision"),
            claim=_parse_claim(data),
        )
        return _control_json(control)
    if operation == "read_revision":
        return _stored_json(store.read_revision(data.get("artifact_id"), data.get("revision")))
    if operation == "write_open_revision":
        stored = store.write_open_revision(
            _parse_payload(data), expected_generation=data.get("expected_generation")
        )
        return _stored_json(stored)
    if operation == "freeze_revision":
        control = store.freeze_revision(
            data.get("artifact_id"),
            data.get("revision"),
            verifier=None,
            now=_parse_time(data.get("now")),
        )
        return _control_json(control)
    if operation == "abandon_revision":
        return _control_json(
            store.abandon_revision(
                data.get("artifact_id"), data.get("revision"), reason=data.get("reason")
            )
        )
    if operation == "resolve_exact_reference":
        resolved = store.resolve_exact_reference(data.get("reference"), verifier=None)
        return {"reference": resolved.reference, "revision": _stored_json(resolved.revision)}
    if operation == "verify_digest":
        result = store.verify_digest(data.get("artifact_id"), data.get("revision"))
        return {
            "artifact_id": result.artifact_id,
            "revision": result.revision,
            "primary_verified": result.primary_verified,
            "member_count": result.member_count,
            "manifest_member_count": result.manifest_member_count,
            "closure_verified": result.closure_verified,
        }
    raise InvalidInputError(f"Unsupported operation: {operation}")


def _exit_code(error: ArtifactStoreError) -> int:
    if isinstance(error, (InvalidInputError, ReferenceError)):
        return 2
    if isinstance(error, (StoreNotFoundError, NotFoundError, SchemaError)):
        return 3
    if isinstance(
        error,
        (
            ConflictError,
            InvalidStateError,
            ControlReservationError,
            ReadOnlyError,
            TrackedRuntimeContentError,
        ),
    ):
        return 4
    if isinstance(
        error,
        (
            IntegrityError,
            VerifierRequiredError,
            VerificationFailedError,
            StaleVerificationError,
        ),
    ):
        return 5
    if isinstance(error, DatabaseError):
        return 10
    return 1


def main(argv: Optional[list] = None) -> int:
    operation = "unknown"
    try:
        args = _parse_args(argv)
        operation = args.operation
        data = _load_input(args.input)
        result = _execute(args.operation, Path(args.project_root), data)
        output = {"ok": True, "operation": args.operation, "result": result}
        code = 0
    except ArtifactStoreError as exc:
        output = {
            "ok": False,
            "operation": operation,
            "error": {"code": exc.code, "message": exc.message},
        }
        code = _exit_code(exc)
    except Exception:  # Protocol boundary: no traceback or sensitive detail on stdout.
        output = {
            "ok": False,
            "operation": operation,
            "error": {
                "code": "UNEXPECTED_ERROR",
                "message": "Unexpected internal failure; inspect local diagnostics",
            },
        }
        code = 11
    sys.stdout.write(json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
