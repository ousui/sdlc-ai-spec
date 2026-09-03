"""Producer-compatible frozen Authority verification.

Lifecycle Artifacts continue using the original shared digest algorithm. CTX is a
separate Contract whose producer uses a distinct fixed Core/CTX Check layout and
byte projection, so it is verified without changing existing REQ authority bytes.
"""

from __future__ import annotations

import hashlib
import re

from packages.sdlc_artifact_store import DomainVerification, StoredRevision

from .authority import (
    FrozenArtifactAuthorityVerifier as BaseFrozenArtifactAuthorityVerifier,
    FrozenAuthorityVerificationError,
)
from .canonical import (
    CHECK_HEADERS,
    FINAL_CONFIRMATION_HEADERS,
    GATE_HEADING,
    GATE_SUMMARY_HEADERS,
    CanonicalFormatError,
    exact_artifact_reference,
    find_tables,
    parse_canonical_artifact,
    require_single_row,
    require_single_table,
    sha256_bytes,
)

CTX_CONTRACT = "sdlc-ai-spec/project-context/v1"
CTX_CHECK_HEADERS = ("Check ID", "Check", "Result", "Basis References")
ALLOWED_RESULTS = frozenset({"pass", "n/a", "waived"})


def compute_ctx_control_input_digest(raw_bytes: bytes) -> str:
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalFormatError("CTX primary Markdown must be valid UTF-8") from exc
    status_matches = list(re.finditer(r"(?m)^status: .+\n", text))
    if len(status_matches) != 1:
        raise CanonicalFormatError(
            f"CTX Front Matter must contain exactly one status line; found {len(status_matches)}"
        )
    projected = re.sub(r"(?m)^status: .+\n", "", text, count=1)
    marker = projected.find(GATE_HEADING + "\n")
    if marker < 0:
        raise CanonicalFormatError("CTX Gate heading is missing")
    return sha256_bytes(projected[:marker].encode("utf-8"))


def _checked_rows(parsed) -> tuple[str, ...]:
    core_tables = find_tables(parsed, CHECK_HEADERS)
    ctx_tables = find_tables(parsed, CTX_CHECK_HEADERS)
    if len(core_tables) != 1 or len(ctx_tables) != 1:
        raise CanonicalFormatError(
            "CTX must contain exactly one Core Check table and one CTX Check table"
        )
    rows: list[str] = []
    seen: set[str] = set()
    for table, result_key, prefix in (
        (core_tables[0], "结果 Result", "CORE-G-"),
        (ctx_tables[0], "Result", "CTX-G-"),
    ):
        ids = tuple(row["Check ID"] for row in table.rows)
        if ids != tuple(sorted(ids)):
            raise CanonicalFormatError(f"{prefix} Check rows must be sorted")
        for row, raw_line in zip(table.rows, table.raw_rows):
            check_id = row["Check ID"]
            if not check_id.startswith(prefix):
                raise CanonicalFormatError(f"Unexpected CTX Check ID: {check_id}")
            if check_id in seen:
                raise CanonicalFormatError(f"Duplicate CTX Check ID: {check_id}")
            seen.add(check_id)
            result = row[result_key]
            if check_id == "CORE-G-009":
                if result != "pass":
                    raise CanonicalFormatError("CORE-G-009 must be pass")
                continue
            if result == "pending":
                raise CanonicalFormatError(
                    f"CTX Check Set Digest cannot include pending Check: {check_id}"
                )
            if result not in ALLOWED_RESULTS:
                raise CanonicalFormatError(
                    f"Frozen CTX contains non-passing Check {check_id}: {result}"
                )
            rows.append(raw_line)
    return tuple(rows)


def compute_ctx_check_set_result_digest(parsed) -> str:
    raw = "".join(row + "\n" for row in _checked_rows(parsed)).encode("utf-8")
    return sha256_bytes(raw)


class FrozenArtifactAuthorityVerifier(BaseFrozenArtifactAuthorityVerifier):
    """Verify frozen Authority using the exact producing Contract algorithm."""

    def verify(self, reference: str, revision: StoredRevision) -> DomainVerification:
        if revision.payload.artifact_type != "CTX":
            return super().verify(reference, revision)
        try:
            artifact_id, revision_number = exact_artifact_reference(reference)
            suffix = reference.split("@", 1)[1]
            if "#" in suffix or "/" in suffix:
                raise CanonicalFormatError(
                    "Frozen Artifact Authority requires a base Artifact Reference"
                )
            if artifact_id != revision.control.artifact_id:
                raise CanonicalFormatError("Reference Artifact ID does not match Revision")
            if revision_number != revision.control.revision:
                raise CanonicalFormatError("Reference Revision does not match Revision")
            if revision.control.state != "frozen":
                raise CanonicalFormatError("Revision is not frozen")

            parsed = parse_canonical_artifact(revision.payload.primary_blob)
            if parsed.front_matter.get("contract") != CTX_CONTRACT:
                raise CanonicalFormatError("CTX must use the Project Context Contract")
            self._verify_front_matter(parsed.front_matter, revision)
            control_digest = compute_ctx_control_input_digest(
                revision.payload.primary_blob
            )
            check_digest = compute_ctx_check_set_result_digest(parsed)
            confirmation = require_single_row(
                require_single_table(
                    parsed, FINAL_CONFIRMATION_HEADERS, "Final Confirmation"
                ),
                "Final Confirmation",
            )
            summary = require_single_row(
                require_single_table(parsed, GATE_SUMMARY_HEADERS, "Gate Summary"),
                "Gate Summary",
            )
            self._verify_confirmation_and_summary(
                reference=reference,
                revision=revision,
                confirmation=confirmation,
                summary=summary,
                control_digest=control_digest,
                check_digest=check_digest,
            )
            self._verify_authority_file(reference, revision, confirmation)
        except (CanonicalFormatError, OSError, UnicodeError) as exc:
            raise FrozenAuthorityVerificationError(str(exc)) from exc

        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="Frozen CTX Authority is bound to the current immutable Payload",
        )
