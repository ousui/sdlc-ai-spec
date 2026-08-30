"""Read-only resolution of cross-phase VFY Return and RLS Issue inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping

from packages.sdlc_artifact_store import ArtifactStore

from .authority import FrozenArtifactAuthorityVerifier
from .canonical import (
    CanonicalFormatError,
    exact_artifact_reference,
    parse_canonical_artifact,
    parse_reference_set,
)

ITEM_REFERENCE_RE = re.compile(
    r"^(?P<base>(?P<artifact>(?:VFY|RLS)-[0-9]{14}-[0-9]{2,})"
    r"@(?P<revision>[1-9][0-9]*))#(?P<item>[A-Z]+-[0-9]{3})$"
)

VFY_RETURN_HEADERS = (
    "ID",
    "Return Phase",
    "IMP Binding Reference",
    "Target References",
    "Method References",
    "Subject References",
    "已观察缺口 Observed Gap",
    "必须达到的结果 Required Outcome",
    "Evidence References",
)
RLS_ITEM_HEADERS = (
    "ID",
    "变更或操作 Change or Action",
    "来源引用 Source References",
    "前置条件或注意事项 Prerequisite or Note",
    "执行方 Executor",
    "结果 Result",
    "Follow-up Disposition",
    "证据引用 Evidence References",
)
RLS_CONFIRMATION_HEADERS = (
    "ID",
    "来源引用 Source References",
    "确认项 Confirmation",
    "预期 Expected",
    "执行方 Executor",
    "Evidence 要求及获取方式 Evidence Requirement and Acquisition",
    "实际 Observed",
    "结果 Result",
    "Follow-up Disposition",
    "证据引用 Evidence References",
)
RETURN_PHASES = frozenset({"REQ", "DSN", "PLN", "IMP"})
FOLLOW_UPS = frozenset(
    {"return_req", "return_dsn", "return_pln", "return_imp"}
)
RLI_RETURN_RESULTS = frozenset({"partial", "fail", "cancelled"})
RCF_RETURN_RESULTS = frozenset({"fail"})


class ControlInputError(ValueError):
    """Raised when a cross-phase Control Input is not an exact usable record."""

    code = "CONTROL_INPUT_INVALID"


@dataclass(frozen=True)
class VFYReturnControlInput:
    reference: str
    artifact_reference: str
    item_id: str
    return_phase: str
    imp_binding_reference: str
    target_references: tuple[str, ...]
    method_references: tuple[str, ...]
    subject_references: tuple[str, ...]
    observed_gap: str
    required_outcome: str
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class RLSIssueControlInput:
    reference: str
    artifact_reference: str
    item_id: str
    item_kind: str
    source_references: tuple[str, ...]
    result: str
    follow_up_disposition: str
    evidence_references: tuple[str, ...]
    statement: str
    expected: str | None
    observed: str | None


class ControlInputResolver:
    """Resolve exact frozen Control Inputs without invoking sibling Skills."""

    def __init__(self, project_root: Path):
        root = Path(project_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ControlInputError(
                f"Project root is not an existing directory: {root}"
            )
        self.project_root = root
        self._authority = FrozenArtifactAuthorityVerifier(root)

    def resolve_for_phase(
        self, store: ArtifactStore, reference: str, phase: str
    ) -> VFYReturnControlInput | RLSIssueControlInput:
        phase = phase.upper() if isinstance(phase, str) else ""
        if phase not in RETURN_PHASES:
            raise ControlInputError(
                "Control Input target phase must be REQ, DSN, PLN, or IMP"
            )
        match = self._match(reference)
        artifact_type = match.group("artifact").split("-", 1)[0]
        if artifact_type == "VFY":
            return self.resolve_vfy_return(store, reference, phase)
        if artifact_type == "RLS":
            return self.resolve_rls_issue(
                store, reference, "return_" + phase.lower()
            )
        raise ControlInputError(
            "Only VFY Return and RLS Issue References are Control Inputs"
        )

    def resolve_vfy_return(
        self, store: ArtifactStore, reference: str, expected_return_phase: str
    ) -> VFYReturnControlInput:
        phase = expected_return_phase.upper()
        if phase not in RETURN_PHASES:
            raise ControlInputError("Expected Return Phase is invalid")
        match = self._match(reference)
        if not match.group("artifact").startswith("VFY-"):
            raise ControlInputError("VFY Return Reference must target a VFY Artifact")
        item_id = match.group("item")
        if not item_id.startswith("RET-"):
            raise ControlInputError("VFY Return item ID must use RET-NNN")
        base = match.group("base")
        stored = store.resolve_exact_reference(base, verifier=self._authority).revision
        parsed = parse_canonical_artifact(stored.payload.primary_blob)
        row = self._find_unique_row(parsed.tables, VFY_RETURN_HEADERS, item_id)
        return_phase = row["Return Phase"]
        if return_phase != phase:
            raise ControlInputError(
                f"VFY Return Phase is {return_phase}; expected {phase}"
            )
        imp_binding = row["IMP Binding Reference"]
        if phase == "IMP":
            if imp_binding in {"", "N/A", "None"}:
                raise ControlInputError(
                    "Return Phase=IMP requires an IMP Binding Reference"
                )
        elif imp_binding != "N/A":
            raise ControlInputError(
                "Non-IMP VFY Return must use IMP Binding Reference=N/A"
            )
        observed = self._required_text(
            row["已观察缺口 Observed Gap"], "Observed Gap"
        )
        outcome = self._required_text(
            row["必须达到的结果 Required Outcome"], "Required Outcome"
        )
        targets = self._required_reference_set(
            row["Target References"], "Target References"
        )
        methods = self._required_reference_set(
            row["Method References"], "Method References"
        )
        subjects = self._required_reference_set(
            row["Subject References"], "Subject References"
        )
        evidence = self._required_reference_set(
            row["Evidence References"], "Evidence References"
        )
        return VFYReturnControlInput(
            reference=reference,
            artifact_reference=base,
            item_id=item_id,
            return_phase=return_phase,
            imp_binding_reference=imp_binding,
            target_references=targets,
            method_references=methods,
            subject_references=subjects,
            observed_gap=observed,
            required_outcome=outcome,
            evidence_references=evidence,
        )

    def resolve_rls_issue(
        self, store: ArtifactStore, reference: str, expected_follow_up: str
    ) -> RLSIssueControlInput:
        follow_up = expected_follow_up.lower()
        if follow_up not in FOLLOW_UPS:
            raise ControlInputError("Expected Follow-up Disposition is invalid")
        match = self._match(reference)
        if not match.group("artifact").startswith("RLS-"):
            raise ControlInputError("RLS Issue Reference must target an RLS Artifact")
        item_id = match.group("item")
        if not (item_id.startswith("RLI-") or item_id.startswith("RCF-")):
            raise ControlInputError("RLS Issue item ID must use RLI-NNN or RCF-NNN")
        base = match.group("base")
        stored = store.resolve_exact_reference(base, verifier=self._authority).revision
        parsed = parse_canonical_artifact(stored.payload.primary_blob)
        if item_id.startswith("RLI-"):
            row = self._find_unique_row(parsed.tables, RLS_ITEM_HEADERS, item_id)
            result = row["结果 Result"]
            allowed_results = RLI_RETURN_RESULTS
            statement = self._required_text(
                row["变更或操作 Change or Action"], "Change or Action"
            )
            expected = None
            observed = None
            sources = self._required_reference_set(
                row["来源引用 Source References"], "Source References"
            )
        else:
            row = self._find_unique_row(
                parsed.tables, RLS_CONFIRMATION_HEADERS, item_id
            )
            result = row["结果 Result"]
            allowed_results = RCF_RETURN_RESULTS
            statement = self._required_text(
                row["确认项 Confirmation"], "Confirmation"
            )
            expected = self._required_text(row["预期 Expected"], "Expected")
            observed = self._required_text(row["实际 Observed"], "Observed")
            sources = self._required_reference_set(
                row["来源引用 Source References"], "Source References"
            )
        actual_follow_up = row["Follow-up Disposition"]
        if actual_follow_up != follow_up:
            raise ControlInputError(
                "RLS Issue Follow-up Disposition is "
                f"{actual_follow_up}; expected {follow_up}"
            )
        if result not in allowed_results:
            raise ControlInputError(
                f"RLS {item_id} result {result} cannot route a return_* issue"
            )
        evidence = self._required_reference_set(
            row["证据引用 Evidence References"], "Evidence References"
        )
        return RLSIssueControlInput(
            reference=reference,
            artifact_reference=base,
            item_id=item_id,
            item_kind="release_item" if item_id.startswith("RLI-") else "confirmation",
            source_references=sources,
            result=result,
            follow_up_disposition=actual_follow_up,
            evidence_references=evidence,
            statement=statement,
            expected=expected,
            observed=observed,
        )

    def _match(self, reference: str) -> re.Match[str]:
        if not isinstance(reference, str):
            raise ControlInputError("Control Input Reference must be a string")
        match = ITEM_REFERENCE_RE.fullmatch(reference)
        if match is None:
            raise ControlInputError(
                "Control Input Reference must use exact VFY/RLS Artifact@Revision#Item"
            )
        exact_artifact_reference(match.group("base"))
        return match

    def _find_unique_row(
        self, tables, headers: tuple[str, ...], item_id: str
    ) -> Mapping[str, str]:
        matches: list[Mapping[str, str]] = []
        for table in tables:
            if table.headers != headers:
                continue
            matches.extend(row for row in table.rows if row["ID"] == item_id)
        if len(matches) != 1:
            raise ControlInputError(
                f"Control Input item {item_id} must appear exactly once; found {len(matches)}"
            )
        return matches[0]

    def _required_text(self, value: str, name: str) -> str:
        value = value.strip()
        if not value or value in {"None", "N/A", "pending"}:
            raise ControlInputError(f"Control Input {name} is missing")
        return value

    def _required_reference_set(self, value: str, name: str) -> tuple[str, ...]:
        values = parse_reference_set(value)
        if not values:
            raise ControlInputError(f"Control Input {name} is empty")
        return values
