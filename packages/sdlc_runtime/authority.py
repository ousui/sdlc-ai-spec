"""Generic verification of already-frozen SDLC Artifact Authority.

The verifier validates the persisted authority binding of an exact frozen Revision.
It does not re-run Phase-specific business checks and therefore must never be used
to authorize `freeze_revision`; Phase runtimes still provide their own DomainVerifier
when finalizing a new Revision.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from packages.sdlc_artifact_store import (
    DomainVerification,
    IntegrityError,
    StoredRevision,
)

from .canonical import (
    CHECK_HEADERS,
    FINAL_CONFIRMATION_HEADERS,
    GATE_SUMMARY_HEADERS,
    CanonicalFormatError,
    authority_reference,
    compute_check_set_result_digest,
    compute_control_input_digest,
    exact_artifact_reference,
    find_tables,
    parse_canonical_artifact,
    parse_front_matter,
    parse_reference_set,
    require_single_row,
    require_single_table,
    sha256_bytes,
    validate_digest,
)

ARTIFACT_CONTRACTS = frozenset(
    {"sdlc-ai-spec/artifact/v1", "sdlc-ai-spec/project-context/v1"}
)
READY_STATUS_TO_GATE = {
    "ready": "pass",
    "ready_with_exception": "pass_with_exception",
}
ALLOWED_CHECK_RESULTS = frozenset({"pass", "n/a", "waived"})


class FrozenAuthorityVerificationError(IntegrityError):
    """A frozen Revision cannot prove its persisted downstream Authority."""

    code = "FROZEN_AUTHORITY_INVALID"


class FrozenArtifactAuthorityVerifier:
    """Verify the immutable authority records of an exact frozen Revision."""

    def __init__(self, project_root: Path):
        root = Path(project_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise FrozenAuthorityVerificationError(
                f"Project root is not an existing directory: {root}"
            )
        self.project_root = root

    def verify(
        self, reference: str, revision: StoredRevision
    ) -> DomainVerification:
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
            front = parsed.front_matter
            self._verify_front_matter(front, revision)
            control_digest = compute_control_input_digest(
                revision.payload.primary_blob
            )
            check_digest = compute_check_set_result_digest(parsed)
            self._verify_checks(parsed)
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
            self._verify_authority_file(reference, confirmation)
        except (CanonicalFormatError, OSError, UnicodeError) as exc:
            raise FrozenAuthorityVerificationError(str(exc)) from exc

        return DomainVerification(
            reference=reference,
            payload_binding=revision.verification_binding,
            approved=True,
            message="Frozen Artifact Authority is bound to the current immutable Payload",
        )

    def _verify_front_matter(
        self, front: Mapping[str, object], revision: StoredRevision
    ) -> None:
        contract = front.get("contract")
        if contract not in ARTIFACT_CONTRACTS:
            raise CanonicalFormatError(f"Unsupported Artifact Contract: {contract}")
        if front.get("id") != revision.control.artifact_id:
            raise CanonicalFormatError("Front Matter id does not match Artifact ID")
        if front.get("revision") != revision.control.revision:
            raise CanonicalFormatError("Front Matter revision does not match Revision")
        if front.get("status") != revision.payload.artifact_status:
            raise CanonicalFormatError(
                "Front Matter status does not match stored Artifact Status"
            )
        expected_prefix = revision.payload.artifact_type + "-"
        if not revision.control.artifact_id.startswith(expected_prefix):
            raise CanonicalFormatError(
                "Artifact Type does not match Artifact ID prefix"
            )
        if revision.payload.artifact_type == "CTX":
            if contract != "sdlc-ai-spec/project-context/v1":
                raise CanonicalFormatError("CTX must use the Project Context Contract")
            for forbidden in ("phase", "context", "profile", "inputs"):
                if forbidden in front:
                    raise CanonicalFormatError(
                        f"CTX Front Matter must not contain {forbidden}"
                    )
        else:
            if contract != "sdlc-ai-spec/artifact/v1":
                raise CanonicalFormatError(
                    "Lifecycle Artifact must use sdlc-ai-spec/artifact/v1"
                )
            if front.get("phase") != revision.payload.artifact_type:
                raise CanonicalFormatError(
                    "Front Matter phase does not match Artifact Type"
                )

    def _verify_checks(self, parsed) -> None:
        tables = find_tables(parsed, CHECK_HEADERS)
        if not tables:
            raise CanonicalFormatError("Artifact contains no Gate Check table")
        current: dict[str, str] = {}
        for table in tables:
            for row in table.rows:
                check_id = row["Check ID"]
                if check_id in current:
                    raise CanonicalFormatError(
                        f"Duplicate current Check ID: {check_id}"
                    )
                current[check_id] = row["结果 Result"]
        if current.get("CORE-G-009") != "pass":
            raise CanonicalFormatError("CORE-G-009 must be pass")
        for check_id, result in current.items():
            if check_id == "CORE-G-009":
                continue
            if result not in ALLOWED_CHECK_RESULTS:
                raise CanonicalFormatError(
                    f"Frozen Authority contains non-passing Check {check_id}: {result}"
                )

    def _verify_confirmation_and_summary(
        self,
        *,
        reference: str,
        revision: StoredRevision,
        confirmation: Mapping[str, str],
        summary: Mapping[str, str],
        control_digest: str,
        check_digest: str,
    ) -> None:
        expected_revision = str(revision.control.revision)
        if confirmation["Revision"] != expected_revision:
            raise CanonicalFormatError("Final Confirmation Revision is stale")
        if summary["Evaluated Revision"] != expected_revision:
            raise CanonicalFormatError("Gate Summary Revision is stale")

        for name, value in (
            ("Control Input Digest", control_digest),
            ("Check Set Result Digest", check_digest),
        ):
            validate_digest(value, name)
        if confirmation["Control Input Digest"] != control_digest:
            raise CanonicalFormatError("Final Confirmation Control Input Digest is stale")
        if summary["Control Input Digest"] != control_digest:
            raise CanonicalFormatError("Gate Summary Control Input Digest is stale")
        if confirmation["Check Set Result Digest"] != check_digest:
            raise CanonicalFormatError(
                "Final Confirmation Check Set Result Digest is stale"
            )
        if summary["Check Set Result Digest"] != check_digest:
            raise CanonicalFormatError("Gate Summary Check Set Result Digest is stale")

        evaluation_set = confirmation["Evaluation Contract Set"].strip()
        if not evaluation_set or evaluation_set in {"None", "N/A"}:
            raise CanonicalFormatError("Evaluation Contract Set is missing")
        if summary["Evaluation Contract Set"].strip() != evaluation_set:
            raise CanonicalFormatError(
                "Final Confirmation and Gate Summary use different Contract Sets"
            )
        for item in parse_reference_set(evaluation_set):
            if "@sha256:" not in item:
                raise CanonicalFormatError(
                    f"Evaluation Contract Reference is not immutable: {item}"
                )
            digest = "sha256:" + item.rsplit("@sha256:", 1)[1]
            validate_digest(digest, "Evaluation Contract digest")

        if confirmation["Result"] != "approved":
            raise CanonicalFormatError("Final Confirmation is not approved")
        if confirmation["Mode"] not in {"human", "delegated"}:
            raise CanonicalFormatError("Final Confirmation Mode is invalid")
        if not confirmation["Confirmer"].strip():
            raise CanonicalFormatError("Final Confirmation Confirmer is missing")
        if not confirmation["Role"].strip():
            raise CanonicalFormatError("Final Confirmation Role is missing")

        gate_result = summary["Gate Result"]
        expected_gate = READY_STATUS_TO_GATE.get(revision.payload.artifact_status)
        if expected_gate is None or gate_result != expected_gate:
            raise CanonicalFormatError(
                "Artifact Status and Gate Result do not form an authority state"
            )
        accepted = parse_reference_set(
            confirmation["Accepted Exception References"]
        )
        exceptions = parse_reference_set(summary["Exception References"])
        if accepted != exceptions:
            raise CanonicalFormatError(
                "Final Confirmation and Gate Summary Exception Sets differ"
            )
        if gate_result == "pass" and exceptions:
            raise CanonicalFormatError("pass Gate must not contain Exception References")
        if gate_result == "pass_with_exception" and not exceptions:
            raise CanonicalFormatError(
                "pass_with_exception Gate requires Exception References"
            )
        if confirmation["Mode"] == "delegated":
            if confirmation["Role"] != "Delegated Independent Reviewer":
                raise CanonicalFormatError("Delegated Reviewer Role is invalid")
            if exceptions:
                raise CanonicalFormatError(
                    "Delegated Final Confirmation cannot accept Exceptions"
                )
        if not summary["Evaluator"].strip() or not summary["Evaluated At"].strip():
            raise CanonicalFormatError("Gate Summary evaluator or time is missing")
        if not confirmation["Confirmed At"].strip():
            raise CanonicalFormatError("Final Confirmation time is missing")

    def _verify_authority_file(
        self, reference: str, confirmation: Mapping[str, str]
    ) -> None:
        relative, digest = authority_reference(confirmation["Authority Reference"])
        target = (self.project_root / relative).resolve()
        try:
            target.relative_to(self.project_root)
        except ValueError as exc:
            raise CanonicalFormatError(
                "Authority Reference escapes the Project Root"
            ) from exc
        if not target.is_file():
            raise CanonicalFormatError(
                f"Authority Reference does not exist: {relative}"
            )
        raw = target.read_bytes()
        if sha256_bytes(raw) != digest:
            raise CanonicalFormatError("Authority Reference digest does not match")
        if confirmation["Mode"] != "delegated":
            return
        text = raw.decode("utf-8")
        front, body = parse_front_matter(text)
        if front.get("contract") != (
            "sdlc-ai-spec/final-confirmation-authority/v1"
        ):
            raise CanonicalFormatError("Delegated Authority Contract is invalid")
        if front.get("artifact") != reference:
            raise CanonicalFormatError(
                "Delegated Authority is bound to a different Artifact"
            )
        if front.get("decision") != "approved":
            raise CanonicalFormatError("Delegated Authority decision is not approved")
        if "| Delegation Basis | Reviewer Identity |" not in body:
            raise CanonicalFormatError(
                "Delegated Authority record is missing its fixed review table"
            )
