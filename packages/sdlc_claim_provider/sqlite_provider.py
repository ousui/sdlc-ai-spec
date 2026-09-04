"""Local SQLite Current Claim Provider for IMP Binding execution."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
from contextlib import closing, contextmanager
from typing import Callable, Iterable

from packages.sdlc_artifact_store import (
    ArtifactStore,
    ArtifactStoreError,
    ClaimReservation,
    compute_sha256,
)
from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_runtime import (
    FrozenArtifactAuthorityVerifier,
    exact_artifact_reference,
    parse_canonical_artifact,
)
from packages.sdlc_runtime.authority import is_rfc3339
from packages.sdlc_runtime.canonical import (
    CHECK_HEADERS,
    GATE_SUMMARY_HEADERS,
    require_single_row,
    require_single_table,
)

from .models import AcquireRequest, ClaimRecord

CLAIM_RELATIVE_PATH = Path(".sdlc") / "store.sqlite3"
STATES = frozenset({"active", "completed", "abandoned"})
RESOURCE_RE = re.compile(r"^resource:[A-Za-z0-9._:/+-]+$")
IMP_BINDING_HEADERS = (
    "IMP Binding Reference",
    "Binding Lineage Key",
    "Attempt",
    "Owner",
    "Rework References",
)
IMP_RESULT_HEADERS = (
    "ID",
    "Resource",
    "Baseline Reference",
    "Change Reference",
    "Result Reference",
    "Changed Scope",
    "Approach Step References",
)
IMP_GATE_CHECKS = tuple(f"IMP-G-{index:03d}" for index in range(1, 7))
RESULT_ID_RE = re.compile(r"^RES-([0-9]{3,})$")
PRE_EXECUTION_CONTRACT = "sdlc-ai-spec/imp-pre-execution-readback/v1"
SNAPSHOT_CONTRACT = "sdlc-ai-spec/imp-resource-snapshot/v1"
COMPLETE_FAILURE_RE = re.compile(r"^complete:[A-Z][A-Z0-9_]*:.+$")


class ClaimProviderError(ValueError):
    code = "CLAIM_PROVIDER_ERROR"


class ClaimConflictError(ClaimProviderError):
    code = "CLAIM_CONFLICT"


class ClaimMismatchError(ClaimProviderError):
    code = "CLAIM_MISMATCH"


class ClaimNotFoundError(ClaimProviderError):
    code = "CLAIM_NOT_FOUND"


def _canonical_json(raw: bytes, description: str):
    def object_pairs(pairs):
        keys = [key for key, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ClaimMismatchError(f"{description} contains duplicate JSON keys")
        return dict(pairs)

    try:
        value = json.loads(raw, object_pairs_hook=object_pairs)
    except ClaimProviderError:
        raise
    except (TypeError, json.JSONDecodeError, UnicodeError) as exc:
        raise ClaimMismatchError(f"{description} is not valid JSON") from exc
    canonical = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    if raw != canonical:
        raise ClaimMismatchError(f"{description} is not canonical JSON")
    return value


def _safe_product_path(value: object, description: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ClaimMismatchError(f"{description} is not a canonical product path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) == "."
        or ".." in path.parts
        or any(part in {".git", ".sdlc"} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ClaimMismatchError(f"{description} escapes the product Resource")
    return value


def binding_lineage(reference: str) -> str:
    artifact_id, _ = exact_artifact_reference(reference)
    suffix = reference.split("@", 1)[1]
    item = None
    if "#" in suffix:
        item = suffix.split("#", 1)[1]
    if item:
        return f"{artifact_id}#{item}"
    return artifact_id


def _tuple_json(values: Iterable[str]) -> str:
    return json.dumps(tuple(values), ensure_ascii=False, separators=(",", ":"))


def _parse_tuple(value: str) -> tuple[str, ...]:
    try:
        loaded = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ClaimProviderError("Claim tuple storage is invalid") from exc
    if not isinstance(loaded, list) or any(not isinstance(item, str) for item in loaded):
        raise ClaimProviderError("Claim tuple storage is invalid")
    return tuple(loaded)


def _normalized_set(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({item.strip() for item in values if item.strip()}))


def _normalized_ordered(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip() for item in values if item.strip()))


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not is_rfc3339(value):
        raise ClaimProviderError(f"Stored Claim {field} is not valid RFC 3339")
    return datetime.fromisoformat(
        value[:-1] + "+00:00" if value.endswith("Z") else value
    )


class ClaimProvider:
    def __init__(
        self,
        project_root: Path | str,
        *,
        read_only: bool = False,
        clock: Callable[[], datetime] | None = None,
    ):
        self.project_root = Path(project_root).expanduser().resolve()
        if not self.project_root.is_dir():
            raise ClaimProviderError("project_root must be an existing directory")
        self.path = self.project_root / CLAIM_RELATIVE_PATH
        self.read_only = read_only
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @classmethod
    def open_read_only(cls, project_root: Path | str) -> "ClaimProvider":
        provider = cls(project_root, read_only=True)
        if not provider.path.is_file():
            raise ClaimNotFoundError(f"Claim Store does not exist: {provider.path}")
        provider._validate_schema()
        return provider

    @classmethod
    def open_read_write(
        cls, project_root: Path | str, *, clock: Callable[[], datetime] | None = None
    ) -> "ClaimProvider":
        return cls(project_root, read_only=False, clock=clock)

    def initialize(self) -> None:
        if self.read_only:
            raise ClaimProviderError("read-only Claim Provider cannot initialize")
        try:
            if self.path.is_file():
                ArtifactStore.open_read_only(self.project_root)
            else:
                ArtifactStore.open_read_write(
                    self.project_root, clock=self.clock
                ).initialize()
        except ArtifactStoreError as exc:
            raise ClaimProviderError(
                f"Shared Artifact Store is invalid: {exc}"
            ) from exc
        with closing(self._connect(allow_create=True)) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS imp_claims (
                    binding_lineage TEXT NOT NULL,
                    attempt INTEGER NOT NULL CHECK (attempt > 0),
                    binding_reference TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision > 0),
                    owner TEXT NOT NULL,
                    execution_scope TEXT NOT NULL,
                    dependency_results TEXT NOT NULL,
                    rework_references TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('active', 'completed', 'abandoned')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK (generation >= 0),
                    completed_at TEXT,
                    abandoned_by TEXT,
                    abandoned_at TEXT,
                    abandon_reason TEXT,
                    PRIMARY KEY(binding_lineage, attempt),
                    UNIQUE(artifact_id, revision)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_imp_claim
                ON imp_claims(binding_lineage)
                WHERE state = 'active';
                """
            )
            connection.commit()
        self._validate_schema()

    def resolve(self, binding_or_lineage: str) -> ClaimRecord | None:
        lineage = (
            binding_lineage(binding_or_lineage)
            if "@" in binding_or_lineage
            else binding_or_lineage
        )
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT * FROM imp_claims WHERE binding_lineage=? ORDER BY attempt DESC LIMIT 1",
                (lineage,),
            ).fetchone()
        return self._record(row) if row else None

    def resolve_artifact(self, artifact_id: str) -> ClaimRecord | None:
        """Return the latest Claim Attempt for one stable IMP Artifact ID."""
        with self._read_connection() as connection:
            row = connection.execute(
                "SELECT * FROM imp_claims WHERE artifact_id=? ORDER BY attempt DESC LIMIT 1",
                (artifact_id,),
            ).fetchone()
        return self._record(row) if row else None

    def acquire(self, request: AcquireRequest) -> ClaimRecord:
        if self.read_only:
            raise ClaimProviderError("read-only Claim Provider cannot acquire")
        lineage = binding_lineage(request.binding_reference)
        owner = request.owner.strip()
        if not owner:
            raise ClaimProviderError("owner must be non-empty")
        scope = _normalized_ordered(request.execution_scope)
        resources = tuple(item for item in scope if item.startswith("resource:"))
        if not resources or any(not RESOURCE_RE.fullmatch(item) for item in resources):
            raise ClaimProviderError("execution_scope must contain valid resource:<id> tokens")
        dependencies = _normalized_ordered(request.dependency_results)
        rework = _normalized_set(request.rework_references)
        self.initialize()
        with self._transaction() as connection:
            records = self._records_tx(connection)
            rows = [record for record in records if record.binding_lineage == lineage]
            current = rows[-1] if rows else None
            if current and current.state == "active":
                if (
                    current.binding_reference == request.binding_reference
                    and current.owner == owner
                    and current.execution_scope == scope
                    and current.dependency_results == dependencies
                    and current.rework_references == rework
                ):
                    return current
                raise ClaimMismatchError("Binding Lineage already has a different active Claim")
            if current and current.state == "completed":
                same_sequence = (
                    current.binding_reference == request.binding_reference
                    and current.execution_scope == scope
                    and current.dependency_results == dependencies
                    and current.rework_references == rework
                )
                if same_sequence:
                    if current.owner != owner:
                        raise ClaimMismatchError(
                            "completed Claim sequence belongs to a different Owner"
                        )
                    return current
                if not rework:
                    raise ClaimMismatchError("completed Claim requires explicit rework references")
            if current and current.state == "abandoned":
                same_sequence = (
                    current.binding_reference == request.binding_reference
                    and current.execution_scope == scope
                    and current.dependency_results == dependencies
                    and current.rework_references == rework
                )
                if request.retry_abandoned:
                    if not same_sequence:
                        raise ClaimMismatchError(
                            "abandoned Claim retry must preserve the exact sequence conditions"
                        )
                elif same_sequence or not rework:
                    raise ClaimMismatchError(
                        "abandoned Claim sequence requires explicit retry"
                    )

            for other in (record for record in records if record.state == "active"):
                if other.binding_lineage == lineage:
                    continue
                if set(resources) & set(item for item in other.execution_scope if item.startswith("resource:")):
                    raise ClaimConflictError(
                        f"Resource scope conflicts with active Claim {other.binding_lineage}"
                    )

            attempt = (current.attempt + 1) if current else 1
            if current:
                artifact_id = current.artifact_id
                revision = current.revision + 1
            else:
                moment = self.clock().astimezone(timezone.utc)
                prefix = f"IMP-{moment.strftime('%Y%m%d%H%M%S')}"
                count = connection.execute(
                    "SELECT COUNT(DISTINCT artifact_id) AS n FROM imp_claims WHERE artifact_id LIKE ?",
                    (prefix + "-%",),
                ).fetchone()["n"]
                artifact_id = f"{prefix}-{count + 1:02d}"
                revision = 1
            created_at = self.clock().astimezone(timezone.utc).isoformat()
            connection.execute(
                """
                INSERT INTO imp_claims(
                    binding_lineage, attempt, binding_reference, artifact_id,
                    revision, owner, execution_scope, dependency_results,
                    rework_references, state, created_at, updated_at, generation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, 0)
                """,
                (
                    lineage, attempt, request.binding_reference, artifact_id,
                    revision, owner, _tuple_json(scope), _tuple_json(dependencies),
                    _tuple_json(rework), created_at, created_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM imp_claims WHERE binding_lineage=? AND attempt=?",
                (lineage, attempt),
            ).fetchone()
            return self._record(row)

    def complete(
        self,
        lineage: str,
        *,
        attempt: int,
        owner: str,
        artifact_id: str,
        revision: int,
        generation: int,
    ) -> ClaimRecord:
        return self._transition(
            lineage, attempt=attempt, owner=owner, artifact_id=artifact_id,
            revision=revision, generation=generation,
            target="completed", reason=None,
        )

    def _verify_dependencies_current_tx(
        self,
        connection,
        record: ClaimRecord,
        *,
        visited: set[tuple[str, int]] | None = None,
    ) -> None:
        """Recursively verify the dependency chain inside the transition transaction."""

        visited = visited or set()
        key = (record.binding_lineage, record.attempt)
        if key in visited:
            raise ClaimMismatchError("dependency Claim graph contains a cycle")
        visited.add(key)
        for reference in record.dependency_results:
            artifact_id, revision = exact_artifact_reference(reference)
            dependency = connection.execute(
                "SELECT * FROM imp_claims WHERE artifact_id=? ORDER BY attempt DESC LIMIT 1",
                (artifact_id,),
            ).fetchone()
            if dependency is None:
                raise ClaimMismatchError(
                    f"dependency Claim is missing: {reference}"
                )
            current = self._record(dependency)
            if current.state != "completed" or current.revision != revision:
                raise ClaimMismatchError(
                    f"dependency is not the Current completed Result: {reference}"
                )
            self._verify_dependencies_current_tx(
                connection, current, visited=visited
            )
        visited.remove(key)

    def abandon(
        self,
        lineage: str,
        *,
        attempt: int,
        owner: str,
        artifact_id: str,
        revision: int,
        generation: int,
        reason: str | None = None,
        abandoned_by: str | None = None,
    ) -> ClaimRecord:
        if reason is not None and (
            not isinstance(reason, str) or not reason.strip()
        ):
            raise ClaimProviderError("abandon reason is required")
        normalized_reason = reason.strip() if reason is not None else None
        actor_value = owner if abandoned_by is None else abandoned_by
        if (
            not isinstance(actor_value, str)
            or not actor_value.strip()
            or actor_value != actor_value.strip()
        ):
            raise ClaimProviderError("abandoned_by must identify the actual actor")
        return self._transition(
            lineage, attempt=attempt, owner=owner, artifact_id=artifact_id,
            revision=revision, generation=generation, target="abandoned",
            reason=normalized_reason, actor=actor_value,
        )

    def _completion_failure_reason_tx(self, connection, record: ClaimRecord) -> str | None:
        """Run the exact completion checks and return their authoritative failure.

        A frozen Claim may only be released when the same transaction proves
        that completing the same Attempt cannot currently succeed.  The caller
        cannot manufacture this record by supplying a suitably shaped string.
        """

        try:
            self._verify_dependencies_current_tx(connection, record)
            self._verify_artifact_terminal_state(
                record, target="completed", reason=None
            )
        except ClaimProviderError as exc:
            detail = " ".join(str(exc).split()) or type(exc).__name__
            return f"complete:{exc.code}:{detail}"
        return None

    def _verify_artifact_terminal_state(
        self,
        record: ClaimRecord,
        *,
        target: str,
        reason: str | None,
        completion_failure: str | None = None,
    ) -> str | None:
        """Verify ArtifactStore reached the matching terminal state first.

        Claim state is execution Authority, but it cannot manufacture Artifact
        Authority.  The public provider therefore re-reads the exact external
        Reservation and, for completion, independently verifies the frozen
        Gate and Final Confirmation before changing Claim state.
        """

        expected_claim = ClaimReservation(
            record.binding_lineage, record.attempt_token, record.owner
        )
        try:
            store = ArtifactStore.open_read_only(self.project_root)
            controls = ArtifactCatalog(store).list_revisions(record.artifact_id)
            control = next(
                (
                    item for item in controls
                    if item.revision == record.revision
                ),
                None,
            )
            if control is None:
                raise ClaimMismatchError(
                    "Artifact Revision Reservation does not exist"
                )
            if control.claim != expected_claim:
                raise ClaimMismatchError(
                    "Artifact Revision Reservation does not match the Claim"
                )
            reference = f"{record.artifact_id}@{record.revision}"
            if target == "completed":
                resolved = store.resolve_exact_reference(
                    reference,
                    verifier=FrozenArtifactAuthorityVerifier(self.project_root),
                )
                self._verify_imp_terminal_payload(
                    store, resolved.revision, record
                )
                return None
            if control.state == "abandoned":
                if control.abandon_reason != reason:
                    raise ClaimMismatchError(
                        "Artifact and Claim abandon reasons do not match"
                    )
                return reason
            if control.state == "frozen":
                if completion_failure is None:
                    raise ClaimMismatchError(
                        "Frozen Artifact still satisfies Claim completion conditions"
                    )
                if COMPLETE_FAILURE_RE.fullmatch(completion_failure) is None:
                    raise ClaimProviderError(
                        "Provider completion failure is not canonical"
                    )
                if reason is not None and reason != completion_failure:
                    raise ClaimMismatchError(
                        "Frozen Artifact abandon reason does not match the Provider-observed completion failure"
                    )
                store.resolve_exact_reference(
                    reference,
                    verifier=FrozenArtifactAuthorityVerifier(self.project_root),
                )
                return completion_failure
            raise ClaimMismatchError(
                "Artifact Revision must reach its terminal state before the Claim"
            )
        except ClaimProviderError:
            raise
        except ArtifactStoreError as exc:
            raise ClaimMismatchError(
                f"Artifact Revision cannot authorize Claim {target}: {exc}"
            ) from exc
        except (KeyError, TypeError, ValueError, UnicodeError) as exc:
            raise ClaimMismatchError(
                f"Artifact Revision cannot authorize Claim {target}: {exc}"
            ) from exc

    def _verify_imp_terminal_payload(self, store, stored, record) -> None:
        """Verify the frozen IMP carries this Claim's complete Result chain."""

        if stored.payload.artifact_type != "IMP":
            raise ClaimMismatchError("Claim completion requires an IMP Artifact")
        parsed = parse_canonical_artifact(stored.payload.primary_blob)
        binding = require_single_row(
            require_single_table(
                parsed, IMP_BINDING_HEADERS, "IMP Binding"
            ),
            "IMP Binding",
        )
        expected_binding = (
            record.binding_reference,
            record.binding_lineage,
            str(record.attempt),
            record.owner,
            ", ".join(record.rework_references) or "None",
        )
        if tuple(binding[field] for field in IMP_BINDING_HEADERS) != expected_binding:
            raise ClaimMismatchError(
                "Frozen IMP Binding does not match the Current Claim"
            )

        state_members = tuple(
            member
            for member in stored.payload.members
            if member.member_id == "IMP-STATE"
        )
        if len(state_members) != 1:
            raise ClaimMismatchError("Frozen IMP State Member is missing or duplicated")
        state = _canonical_json(state_members[0].raw_bytes, "Frozen IMP State")
        expected_claim = {
            "binding_lineage": record.binding_lineage,
            "binding_reference": record.binding_reference,
            "artifact_id": record.artifact_id,
            "revision": record.revision,
            "attempt": record.attempt,
            "owner": record.owner,
            "execution_scope": list(record.execution_scope),
            "dependency_results": list(record.dependency_results),
            "rework_references": list(record.rework_references),
        }
        if (
            not isinstance(state, dict)
            or state.get("contract") != "sdlc-ai-spec/imp-state/v1"
            or state.get("stage") != "executed"
            or state.get("claim") != expected_claim
            or state.get("failure") is not None
        ):
            raise ClaimMismatchError(
                "Frozen IMP State is not an executed passing Claim Result"
            )
        request = state.get("request")
        if (
            not isinstance(request, dict)
            or request.get("dependencies") != list(record.dependency_results)
            or request.get("rework") != list(record.rework_references)
        ):
            raise ClaimMismatchError(
                "Frozen IMP request does not match Claim dependencies and rework"
            )
        inputs = parsed.front_matter.get("inputs")
        if (
            not isinstance(inputs, list)
            or any(not isinstance(item, str) for item in inputs)
            or len(inputs) != len(set(inputs))
            or not set(record.dependency_results).issubset(inputs)
        ):
            raise ClaimMismatchError(
                "Frozen IMP inputs omit a Claim Dependency Result"
            )

        check_results = {}
        for table in parsed.tables:
            if table.headers != CHECK_HEADERS:
                continue
            for row in table.rows:
                check_id = row["Check ID"]
                if check_id in check_results:
                    raise ClaimMismatchError(
                        "Frozen IMP contains duplicate Gate Check IDs"
                    )
                check_results[check_id] = row["结果 Result"]
        if any(check_results.get(check_id) != "pass" for check_id in IMP_GATE_CHECKS):
            raise ClaimMismatchError("Frozen IMP Phase Gate is incomplete")

        summary = require_single_row(
            require_single_table(parsed, GATE_SUMMARY_HEADERS, "IMP Gate Summary"),
            "IMP Gate Summary",
        )
        self._verify_pre_execution(stored, state, record, summary)
        method_step_ids = self._verify_local_checks(stored, state, record)

        resources = sorted(
            item.removeprefix("resource:")
            for item in record.execution_scope
            if item.startswith("resource:")
        )
        state_rows = state.get("resources")
        result_rows = require_single_table(
            parsed, IMP_RESULT_HEADERS, "IMP Result Set"
        ).rows
        if (
            not isinstance(state_rows, list)
            or any(not isinstance(row, dict) for row in state_rows)
            or [row["resource"] for row in state_rows] != resources
            or len(result_rows) != len(resources)
            or len({row["id"] for row in state_rows}) != len(resources)
        ):
            raise ClaimMismatchError(
                "Frozen IMP Result Set does not cover every Claim Resource"
            )
        self._verify_result_id_history(store, stored, state_rows)
        for row, canonical_row in zip(state_rows, result_rows):
            self._verify_result_row_shape(row)
            expected_row = (
                row["id"],
                row["resource"],
                row["baseline_reference"],
                row["change_reference"],
                row["result_reference"],
                ", ".join(row["changed_scope"]) or "None",
                ", ".join(row["steps"]) or "None",
            )
            if tuple(
                canonical_row[field] for field in IMP_RESULT_HEADERS
            ) != expected_row:
                raise ClaimMismatchError(
                    "Frozen canonical Result differs from retained IMP State"
                )
            self._verify_resource_result(
                store, stored, record, row, method_step_ids
            )

    @staticmethod
    def _member(stored, member_id: str, description: str):
        matches = tuple(
            member
            for member in stored.payload.members
            if member.member_id == member_id
        )
        if len(matches) != 1:
            raise ClaimMismatchError(f"{description} is missing or duplicated")
        return matches[0]

    def _verify_pre_execution(self, stored, state, record, summary) -> None:
        current = state.get("pre_execution")
        required = {
            "contract",
            "evidence_member",
            "evidence_sha256",
            "observed_at",
            "evaluation_contract_set",
            "checklist_digest",
        }
        if (
            not isinstance(current, dict)
            or set(current) != required
            or current.get("contract") != PRE_EXECUTION_CONTRACT
            or current.get("evidence_member") != "EVD-PRE"
            or not is_rfc3339(current.get("observed_at"))
            or not isinstance(current.get("evaluation_contract_set"), str)
            or not current["evaluation_contract_set"].strip()
            or current["evaluation_contract_set"] == "N/A"
            or current["evaluation_contract_set"]
            != summary["Evaluation Contract Set"]
        ):
            raise ClaimMismatchError("Frozen IMP pre-execution record is invalid")
        member = self._member(stored, "EVD-PRE", "Pre-execution Evidence")
        if current.get("evidence_sha256") != member.sha256:
            raise ClaimMismatchError("Pre-execution Evidence digest changed")
        evidence = _canonical_json(
            member.raw_bytes, "Frozen IMP pre-execution Evidence"
        )
        evidence_fields = {
            "contract",
            "artifact_reference",
            "observed_at",
            "evaluation_contract_set",
            "checklist",
            "checklist_digest",
            "executor",
            "result",
        }
        checklist = evidence.get("checklist") if isinstance(evidence, dict) else None
        checklist_digest = (
            compute_sha256(json.dumps(
                checklist,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8"))
            if isinstance(checklist, dict)
            else None
        )
        reference = f"{record.artifact_id}@{record.revision}"
        if (
            not isinstance(evidence, dict)
            or set(evidence) != evidence_fields
            or evidence.get("contract") != PRE_EXECUTION_CONTRACT
            or evidence.get("artifact_reference") != reference
            or evidence.get("observed_at") != current["observed_at"]
            or evidence.get("evaluation_contract_set")
            != current["evaluation_contract_set"]
            or evidence.get("checklist_digest")
            != current.get("checklist_digest")
            or evidence.get("checklist_digest") != checklist_digest
            or evidence.get("executor") != record.owner
            or evidence.get("result") != "pass"
        ):
            raise ClaimMismatchError(
                "Frozen IMP pre-execution Evidence is not bound to the Claim"
            )

    def _verify_local_checks(self, stored, state, record) -> frozenset[str]:
        method = state.get("method")
        state_checks = state.get("checks")
        if (
            not isinstance(method, dict)
            or not isinstance(method.get("steps"), list)
            or not isinstance(method.get("checks"), list)
            or not method["checks"]
            or not isinstance(state_checks, list)
            or len(state_checks) != len(method["checks"])
        ):
            raise ClaimMismatchError("Frozen IMP local Check Set is incomplete")
        step_ids = []
        for step in method["steps"]:
            if not isinstance(step, dict) or not isinstance(step.get("id"), str):
                raise ClaimMismatchError("Frozen IMP Method Step is invalid")
            step_ids.append(step["id"])
        if len(step_ids) != len(set(step_ids)):
            raise ClaimMismatchError("Frozen IMP Method Step IDs are duplicated")
        resources = {
            item.removeprefix("resource:")
            for item in record.execution_scope
            if item.startswith("resource:")
        }
        seen = set()
        for spec, result in zip(method["checks"], state_checks):
            if not isinstance(spec, dict) or not isinstance(result, dict):
                raise ClaimMismatchError("Frozen IMP local Check record is invalid")
            check_id = spec.get("id")
            kind = spec.get("kind")
            resource = spec.get("resource")
            expected_path = spec.get("cwd", ".") if kind == "project_command" else spec.get("path")
            if (
                not isinstance(check_id, str)
                or not check_id
                or check_id in seen
                or not isinstance(spec.get("name"), str)
                or not spec["name"].strip()
                or resource not in resources
                or set(result) != {
                    "id", "name", "resource", "path", "result", "evidence_member"
                }
                or result != {
                    "id": check_id,
                    "name": spec["name"],
                    "resource": resource,
                    "path": expected_path,
                    "result": "pass",
                    "evidence_member": "EVD-" + check_id,
                }
            ):
                raise ClaimMismatchError(
                    "Frozen IMP local Check identity or Result is invalid"
                )
            seen.add(check_id)
            evidence_member = self._member(
                stored, "EVD-" + check_id, "Local Check Evidence"
            )
            evidence = _canonical_json(
                evidence_member.raw_bytes, "Frozen IMP local Check Evidence"
            )
            if (
                not isinstance(evidence, dict)
                or evidence.get("result") != "pass"
                or evidence.get("exit_code") != 0
            ):
                raise ClaimMismatchError(
                    "Frozen IMP local Check Evidence does not prove a pass"
                )
            if kind != "project_command":
                path = _safe_product_path(expected_path, "IMP Check target")
                prefix = f"path:{resource}/"
                scopes = [
                    item[len(prefix):].rstrip("/")
                    for item in record.execution_scope
                    if item.startswith(prefix)
                ]
                if scopes and not any(
                    path == scope or path.startswith(scope + "/")
                    for scope in scopes
                ):
                    raise ClaimMismatchError("IMP Check target exceeds Claim Scope")
        return frozenset(step_ids)

    @staticmethod
    def _verify_result_row_shape(row) -> None:
        required = {
            "id", "resource", "root", "baseline_member", "baseline_reference",
            "change_member", "change_reference", "result_member",
            "result_reference", "changed_paths", "changed_scope", "steps",
        }
        match = RESULT_ID_RE.fullmatch(row.get("id", ""))
        root = row.get("root")
        if (
            set(row) != required
            or match is None
            or int(match.group(1)) <= 0
            or not isinstance(row.get("resource"), str)
            or not row["resource"]
            or not isinstance(root, str)
            or not root
            or any(
                not isinstance(row.get(field), str) or not row[field]
                for field in (
                    "baseline_member", "baseline_reference", "change_member",
                    "change_reference", "result_member", "result_reference",
                )
            )
            or any(
                not isinstance(row.get(field), list)
                or any(not isinstance(item, str) or not item for item in row[field])
                or row[field] != list(dict.fromkeys(row[field]))
                for field in ("changed_paths", "changed_scope", "steps")
            )
        ):
            raise ClaimMismatchError("Frozen IMP Resource Result record is invalid")
        identity = row["id"]
        if (
            row["baseline_member"] != "BASE-" + identity
            or row["change_member"] != "CHANGE-" + identity
            or row["result_member"] != "RESULT-" + identity
        ):
            raise ClaimMismatchError("IMP Result Member identity is not stable")
        if root != ".":
            _safe_product_path(root, "IMP Resource root")

    def _verify_result_id_history(self, store, stored, rows) -> None:
        by_resource = {}
        by_identity = {}
        high_water = 0
        for control in ArtifactCatalog(store).list_revisions(
            stored.control.artifact_id
        ):
            if control.revision >= stored.control.revision or not control.materialized:
                continue
            prior = store.read_revision(control.artifact_id, control.revision)
            state_member = self._member(
                prior, "IMP-STATE", "Historical IMP State"
            )
            state = _canonical_json(
                state_member.raw_bytes, "Historical IMP State"
            )
            historical_rows = state.get("resources") if isinstance(state, dict) else None
            if (
                not isinstance(historical_rows, list)
                or any(not isinstance(row, dict) for row in historical_rows)
            ):
                raise ClaimMismatchError("Historical IMP Result identity is invalid")
            for row in historical_rows:
                resource, identity = row.get("resource"), row.get("id")
                match = RESULT_ID_RE.fullmatch(identity or "")
                if (
                    not isinstance(resource, str)
                    or not resource
                    or match is None
                    or int(match.group(1)) <= 0
                    or by_resource.setdefault(resource, identity) != identity
                    or by_identity.setdefault(identity, resource) != resource
                ):
                    raise ClaimMismatchError(
                        "Historical IMP Result identity was repurposed"
                    )
                high_water = max(high_water, int(match.group(1)))
        new_id_numbers = []
        for row in rows:
            resource, identity = row["resource"], row["id"]
            if (
                resource in by_resource and by_resource[resource] != identity
            ) or (
                identity in by_identity and by_identity[identity] != resource
            ):
                raise ClaimMismatchError("IMP Result identity differs from history")
            if resource not in by_resource:
                new_id_numbers.append(int(RESULT_ID_RE.fullmatch(identity).group(1)))
        if new_id_numbers != list(
            range(high_water + 1, high_water + len(new_id_numbers) + 1)
        ):
            raise ClaimMismatchError(
                "New IMP Result identities do not continue the historical sequence"
            )

    def _verify_resource_result(
        self, store, stored, record, row, method_step_ids
    ) -> None:
        resource = row["resource"]

        def snapshot(reference):
            base, separator, member_id = reference.partition("/")
            if (
                not separator
                or not member_id
                or "/" in member_id
                or "#" in member_id
            ):
                raise ClaimMismatchError(
                    "IMP Result requires an exact Snapshot Member Reference"
                )
            artifact_id, revision = exact_artifact_reference(base)
            if base != f"{artifact_id}@{revision}":
                raise ClaimMismatchError(
                    "IMP Result Snapshot uses a non-exact Artifact Reference"
                )
            if (artifact_id, revision) == (
                stored.control.artifact_id,
                stored.control.revision,
            ):
                source = stored
            else:
                if (
                    artifact_id != record.artifact_id
                    and base not in record.dependency_results
                ):
                    raise ClaimMismatchError(
                        "IMP Result follows an undeclared external Resource chain"
                    )
                if artifact_id == record.artifact_id and revision >= record.revision:
                    raise ClaimMismatchError(
                        "IMP Result follows a non-historical same-Lineage Revision"
                    )
                source = store.resolve_exact_reference(
                    base,
                    verifier=FrozenArtifactAuthorityVerifier(self.project_root),
                ).revision
            if source.payload.artifact_type != "IMP":
                raise ClaimMismatchError("IMP Result Snapshot source is not IMP")
            member = self._member(
                source, member_id, "IMP Result Snapshot Member"
            )
            if (
                member.media_type != "application/json"
                or member.canonical_name != f"snapshots/{member_id.lower()}.json"
            ):
                raise ClaimMismatchError("IMP Result Snapshot Member metadata is invalid")
            value = _canonical_json(
                member.raw_bytes, "Frozen IMP Result Snapshot"
            )
            if (
                not isinstance(value, dict)
                or set(value) != {
                    "contract", "resource", "existed", "root_mode",
                    "entries", "directories",
                }
                or value.get("contract") != SNAPSHOT_CONTRACT
                or value.get("resource") != resource
                or not isinstance(value.get("entries"), list)
                or not isinstance(value.get("directories"), list)
                or not isinstance(value.get("existed"), bool)
            ):
                raise ClaimMismatchError("IMP Result Snapshot is invalid")
            entries = value["entries"]
            entry_paths = []
            for item in entries:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"path", "sha256", "content_hex", "mode"}
                    or not isinstance(item.get("content_hex"), str)
                    or not isinstance(item.get("sha256"), str)
                    or not isinstance(item.get("mode"), int)
                    or isinstance(item.get("mode"), bool)
                    or not 0 <= item["mode"] <= 0o7777
                ):
                    raise ClaimMismatchError("IMP Result Snapshot entry is invalid")
                path = _safe_product_path(item.get("path"), "Snapshot entry path")
                try:
                    raw = bytes.fromhex(item["content_hex"])
                except ValueError as exc:
                    raise ClaimMismatchError(
                        "Snapshot entry content is not hexadecimal"
                    ) from exc
                if compute_sha256(raw).split(":", 1)[1] != item["sha256"]:
                    raise ClaimMismatchError("Snapshot entry digest changed")
                entry_paths.append(path)
            if entry_paths != sorted(set(entry_paths)):
                raise ClaimMismatchError(
                    "Snapshot entry paths are duplicated or unsorted"
                )
            directory_paths = []
            for item in value["directories"]:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"path", "mode"}
                    or not isinstance(item.get("mode"), int)
                    or isinstance(item.get("mode"), bool)
                    or not 0 <= item["mode"] <= 0o7777
                ):
                    raise ClaimMismatchError("IMP Result Snapshot directory is invalid")
                directory_paths.append(
                    _safe_product_path(item.get("path"), "Snapshot directory path")
                )
            if (
                directory_paths != sorted(set(directory_paths))
                or set(entry_paths) & set(directory_paths)
            ):
                raise ClaimMismatchError(
                    "Snapshot directory paths are duplicated, unsorted or conflicting"
                )
            root_mode = value.get("root_mode")
            if value["existed"]:
                if (
                    not isinstance(root_mode, int)
                    or isinstance(root_mode, bool)
                    or not 0 <= root_mode <= 0o7777
                ):
                    raise ClaimMismatchError("Existing Snapshot root mode is invalid")
            elif root_mode is not None or entries or value["directories"]:
                raise ClaimMismatchError(
                    "Nonexistent Snapshot contains product state"
                )
            return value

        baseline_member = f"{stored.control.artifact_id}@{stored.control.revision}/{row['baseline_member']}"
        retained_baseline = snapshot(baseline_member)
        if row["baseline_reference"] == "N/A":
            if retained_baseline["existed"]:
                raise ClaimMismatchError("Existing Resource cannot use N/A Baseline")
            baseline = retained_baseline
        else:
            baseline = snapshot(row["baseline_reference"])
            if baseline != retained_baseline:
                raise ClaimMismatchError(
                    "IMP retained Baseline differs from its Resource chain"
                )
        if row["result_reference"] == "N/A":
            raise ClaimMismatchError("Frozen IMP Resource has no Result Reference")
        result = snapshot(row["result_reference"])
        before = {item["path"]: item for item in baseline["entries"]}
        after = {item["path"]: item for item in result["entries"]}
        changed = sorted(
            path
            for path in before.keys() | after.keys()
            if before.get(path) != after.get(path)
        )
        if row.get("changed_paths") != changed:
            raise ClaimMismatchError(
                "IMP Result changed paths differ from immutable Snapshots"
            )
        prefix = f"path:{resource}/"
        path_scopes = [
            item[len(prefix):].rstrip("/")
            for item in record.execution_scope
            if item.startswith(prefix)
        ]
        if any(
            path_scopes
            and not any(
                path == scope or path.startswith(scope + "/")
                for scope in path_scopes
            )
            for path in changed
        ):
            raise ClaimMismatchError("IMP Result exceeds Claim path Scope")
        expected_scope = (
            [
                f"resource:{resource}",
                *(
                    item
                    for item in record.execution_scope
                    if item.startswith(prefix)
                    and any(
                        path == item[len(prefix):].rstrip("/")
                        or path.startswith(item[len(prefix):].rstrip("/") + "/")
                        for path in changed
                    )
                ),
            ]
            if changed
            else []
        )
        if row["changed_scope"] != expected_scope:
            raise ClaimMismatchError(
                "IMP Result Changed Scope differs from immutable Snapshots"
            )
        if not set(row["steps"]).issubset(method_step_ids):
            raise ClaimMismatchError("IMP Result names an unknown Method Step")
        if not changed:
            if not (
                row["baseline_reference"] == row["result_reference"]
                and row["change_reference"] == "N/A"
                and row["changed_scope"] == []
                and row["steps"] == []
            ):
                raise ClaimMismatchError(
                    "Unchanged IMP Resource does not preserve Baseline=Result"
                )
            return
        if (
            not row["steps"]
            or row["result_reference"]
            != f"{record.artifact_id}@{record.revision}/{row['result_member']}"
            or row["change_reference"]
            != f"{record.artifact_id}@{record.revision}/{row['change_member']}"
        ):
            raise ClaimMismatchError("Changed IMP Resource has incomplete Result Evidence")
        change_member = self._member(
            stored, row["change_member"], "IMP Change Evidence"
        )
        if (
            change_member.media_type != "application/json"
            or change_member.canonical_name
            != f"evidence/{row['change_member'].lower()}.json"
            or _canonical_json(
                change_member.raw_bytes, "Frozen IMP Change Evidence"
            )
            != {"resource": resource, "changed_paths": changed}
        ):
            raise ClaimMismatchError(
                "IMP Change Evidence differs from immutable Snapshots"
            )

    def _transition(
        self, lineage, *, attempt, owner, artifact_id, revision, generation,
        target, reason, actor=None,
    ):
        if self.read_only:
            raise ClaimProviderError("read-only Claim Provider cannot transition")
        if target not in {"completed", "abandoned"}:
            raise ClaimProviderError("invalid Claim transition")
        with self._transaction() as connection:
            self._records_tx(connection)
            row = connection.execute(
                "SELECT * FROM imp_claims WHERE binding_lineage=? AND attempt=?",
                (lineage, attempt),
            ).fetchone()
            if row is None:
                raise ClaimNotFoundError("Claim does not exist")
            record = self._record(row)
            if (
                record.owner != owner
                or record.artifact_id != artifact_id
                or record.revision != revision
            ):
                raise ClaimMismatchError("Claim transition conditions do not match")
            if record.state == target:
                if generation not in {record.generation, record.generation - 1}:
                    raise ClaimMismatchError("Claim transition generation does not match")
                if target == "abandoned" and (
                    record.abandon_reason != reason or record.abandoned_by != actor
                ):
                    raise ClaimMismatchError(
                        "abandoned Claim retry must preserve Actor and Reason"
                    )
                self._verify_artifact_terminal_state(
                    record,
                    target=target,
                    reason=reason,
                    completion_failure=(
                        record.abandon_reason if target == "abandoned" else None
                    ),
                )
                return record
            if record.state != "active":
                raise ClaimMismatchError(f"Claim is {record.state}, not active")
            if record.generation != generation:
                raise ClaimMismatchError("Claim transition generation does not match")
            if target == "completed":
                self._verify_dependencies_current_tx(connection, record)
            completion_failure = (
                self._completion_failure_reason_tx(connection, record)
                if target == "abandoned"
                else None
            )
            reason = self._verify_artifact_terminal_state(
                record,
                target=target,
                reason=reason,
                completion_failure=completion_failure,
            )
            moment = self.clock().astimezone(timezone.utc).isoformat()
            updated = connection.execute(
                """
                UPDATE imp_claims
                SET state=?, completed_at=?, abandoned_by=?, abandoned_at=?, abandon_reason=?,
                    updated_at=?, generation=generation + 1
                WHERE binding_lineage=? AND attempt=? AND state='active' AND generation=?
                """,
                (
                    target,
                    moment if target == "completed" else None,
                    actor if target == "abandoned" else None,
                    moment if target == "abandoned" else None,
                    reason,
                    moment,
                    lineage,
                    attempt,
                    generation,
                ),
            )
            if updated.rowcount != 1:
                raise ClaimMismatchError("Claim transition lost its generation CAS")
            row = connection.execute(
                "SELECT * FROM imp_claims WHERE binding_lineage=? AND attempt=?",
                (lineage, attempt),
            ).fetchone()
            return self._record(row)

    def _record(self, row) -> ClaimRecord:
        state = row["state"]
        if state not in STATES:
            raise ClaimProviderError(f"Stored Claim State is invalid: {state!r}")
        attempt, revision = row["attempt"], row["revision"]
        if (not isinstance(attempt, int) or isinstance(attempt, bool) or attempt <= 0
                or not isinstance(revision, int) or isinstance(revision, bool) or revision <= 0):
            raise ClaimProviderError("Stored Claim Attempt or Revision is invalid")
        execution_scope = _parse_tuple(row["execution_scope"])
        if (
            not execution_scope
            or execution_scope != _normalized_ordered(execution_scope)
        ):
            raise ClaimProviderError("Stored Claim Scope is invalid")
        resources = tuple(item for item in execution_scope if item.startswith("resource:"))
        if not resources or any(not RESOURCE_RE.fullmatch(item) for item in resources):
            raise ClaimProviderError("Stored Claim Scope has no valid Resource")
        dependency_results = _parse_tuple(row["dependency_results"])
        rework_references = _parse_tuple(row["rework_references"])
        if dependency_results != _normalized_ordered(dependency_results):
            raise ClaimProviderError(
                "Stored Claim Dependency Results are not canonical"
            )
        if rework_references != _normalized_set(rework_references):
            raise ClaimProviderError(
                "Stored Claim Rework References are not a canonical set"
            )
        try:
            for reference in (*dependency_results, *rework_references):
                exact_artifact_reference(reference)
        except ValueError as exc:
            raise ClaimProviderError("Stored Claim Reference is invalid") from exc
        record = ClaimRecord(
            binding_lineage=row["binding_lineage"],
            binding_reference=row["binding_reference"],
            artifact_id=row["artifact_id"],
            revision=revision,
            attempt=attempt,
            owner=row["owner"],
            execution_scope=execution_scope,
            dependency_results=dependency_results,
            rework_references=rework_references,
            state=state,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            generation=row["generation"],
            completed_at=row["completed_at"],
            abandoned_by=row["abandoned_by"],
            abandoned_at=row["abandoned_at"],
            abandon_reason=row["abandon_reason"],
        )
        try:
            if binding_lineage(record.binding_reference) != record.binding_lineage:
                raise ClaimProviderError("Stored Claim Binding Lineage is invalid")
            exact_artifact_reference(f"{record.artifact_id}@{record.revision}")
        except ValueError as exc:
            raise ClaimProviderError("Stored Claim identity is invalid") from exc
        if (not isinstance(record.owner, str) or not record.owner
                or record.owner != record.owner.strip()
                or not isinstance(record.generation, int)
                or isinstance(record.generation, bool) or record.generation < 0):
            raise ClaimProviderError("Stored Claim metadata is invalid")
        created_at = _timestamp(record.created_at, "created_at")
        updated_at = _timestamp(record.updated_at, "updated_at")
        if updated_at < created_at:
            raise ClaimProviderError("Stored Claim timestamps are out of order")
        if record.state == "active" and (
            record.generation != 0 or record.completed_at is not None
            or record.abandoned_by is not None or record.abandoned_at is not None
            or record.abandon_reason is not None
        ):
            raise ClaimProviderError("Stored active Claim terminal fields are invalid")
        if record.state == "completed" and (
            record.generation != 1 or not record.completed_at
            or record.abandoned_by is not None or record.abandoned_at is not None
            or record.abandon_reason is not None
        ):
            raise ClaimProviderError("Stored completed Claim terminal fields are invalid")
        if record.state == "completed" and (
            _timestamp(record.completed_at, "completed_at") != updated_at
        ):
            raise ClaimProviderError("Stored completed Claim timestamps do not match")
        if record.state == "abandoned" and (
            record.generation != 1 or record.completed_at is not None
            or not isinstance(record.abandoned_by, str)
            or not record.abandoned_by
            or record.abandoned_by != record.abandoned_by.strip()
            or not record.abandoned_at
            or not isinstance(record.abandon_reason, str)
            or not record.abandon_reason
            or record.abandon_reason != record.abandon_reason.strip()
        ):
            raise ClaimProviderError("Stored abandoned Claim terminal fields are invalid")
        if record.state == "abandoned" and (
            _timestamp(record.abandoned_at, "abandoned_at") != updated_at
        ):
            raise ClaimProviderError("Stored abandoned Claim timestamps do not match")
        return record

    def _records_tx(self, connection) -> tuple[ClaimRecord, ...]:
        records = tuple(
            self._record(row)
            for row in connection.execute(
                "SELECT * FROM imp_claims ORDER BY binding_lineage, attempt"
            ).fetchall()
        )
        by_lineage: dict[str, list[ClaimRecord]] = {}
        artifact_lineages: dict[str, str] = {}
        for record in records:
            by_lineage.setdefault(record.binding_lineage, []).append(record)
            prior = artifact_lineages.setdefault(
                record.artifact_id, record.binding_lineage
            )
            if prior != record.binding_lineage:
                raise ClaimProviderError(
                    "Stored IMP Artifact ID belongs to multiple Claim Lineages"
                )
        active_resources: dict[str, str] = {}
        for lineage, attempts in by_lineage.items():
            expected_attempts = list(range(1, len(attempts) + 1))
            if [record.attempt for record in attempts] != expected_attempts:
                raise ClaimProviderError("Stored Claim Attempts are not contiguous")
            artifact_ids = {record.artifact_id for record in attempts}
            if len(artifact_ids) != 1:
                raise ClaimProviderError("Stored Claim Lineage changed IMP Artifact ID")
            if [record.revision for record in attempts] != expected_attempts:
                raise ClaimProviderError("Stored Claim Revisions are not contiguous")
            if any(record.state == "active" for record in attempts[:-1]):
                raise ClaimProviderError("A historical Claim Attempt remains active")
            current = attempts[-1]
            if current.state == "active":
                for resource in (
                    item for item in current.execution_scope
                    if item.startswith("resource:")
                ):
                    other = active_resources.setdefault(resource, lineage)
                    if other != lineage:
                        raise ClaimProviderError(
                            "Stored active Claims have conflicting Resource Scope"
                        )
        return records

    def _connect(self, allow_create: bool = False):
        if not self.path.exists() and not allow_create:
            raise ClaimNotFoundError(f"Claim Store does not exist: {self.path}")
        if self.read_only:
            self._read_only_image()
            # immutable prevents SQLite from creating WAL/SHM even if another
            # process changes journal mode after the preflight. Public reads
            # also compare the database image before/after and fail on races.
            connection = sqlite3.connect(self.path.as_uri() + "?mode=ro&immutable=1", uri=True)
            connection.execute("PRAGMA query_only=ON")
        else:
            connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _read_only_image(self):
        raw = self.path.read_bytes()
        if raw[18:20] != b"\x01\x01" or any(
            Path(str(self.path) + suffix).exists()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            raise ClaimProviderError("read-only Claim Store requires a quiescent rollback-journal database")
        return raw

    @contextmanager
    def _read_connection(self):
        before = self._read_only_image() if self.read_only else None
        with closing(self._connect()) as connection:
            yield connection
        if self.read_only and self._read_only_image() != before:
            raise ClaimProviderError("Claim Store changed during read-only query")

    def _transaction(self):
        provider = self
        class Transaction:
            def __enter__(self):
                self.connection = provider._connect(allow_create=True)
                self.connection.execute("BEGIN IMMEDIATE")
                return self.connection
            def __exit__(self, exc_type, exc, tb):
                if exc_type is None:
                    self.connection.commit()
                else:
                    self.connection.rollback()
                self.connection.close()
        return Transaction()

    def _validate_schema(self):
        if self.read_only:
            self._read_only_image()
        try:
            ArtifactStore.open_read_only(self.project_root)
        except ArtifactStoreError as exc:
            raise ClaimProviderError(
                f"Shared Artifact Store is invalid: {exc}"
            ) from exc
        with self._read_connection() as connection:
            table = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='imp_claims'"
            ).fetchone()
            if table is None:
                raise ClaimNotFoundError("Shared Store has no IMP Claim tables")
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(imp_claims)")
            }
            required = {
                "binding_lineage", "attempt", "binding_reference", "artifact_id",
                "revision", "owner", "execution_scope", "dependency_results",
                "rework_references", "state", "created_at", "updated_at",
                "generation", "completed_at", "abandoned_by", "abandoned_at",
                "abandon_reason",
            }
            indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(imp_claims)")
            }
            normalized_sql = " ".join(str(table["sql"] or "").lower().split())
            valid = (
                required.issubset(columns)
                and "one_active_imp_claim" in indexes
                and "check (state in ('active', 'completed', 'abandoned'))"
                in normalized_sql
            )
            if valid:
                self._records_tx(connection)
        if not valid:
            raise ClaimProviderError("Claim Store Schema is invalid")


__all__ = tuple(name for name in globals() if not name.startswith("_"))
