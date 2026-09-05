"""Read-only authority compiler for persistent VFY operations.

The compiler never treats caller-provided Scope, Subject, Target, Control or
Exception fields as authority.  It re-derives them from the exact frozen
Artifact graph and the current Claim/Result projection, then compares any hint
with the derived values.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_lifecycle import LifecycleQueryService
from packages.sdlc_runtime import (
    ControlInputError,
    ControlInputResolver,
    FrozenArtifactAuthorityVerifier,
    parse_canonical_artifact,
    parse_markdown_tables,
    parse_reference_set,
)
from packages.sdlc_runtime.canonical import (
    decode_primary_markdown,
    exact_artifact_reference as runtime_exact,
)

from vfy_common import (
    exact_artifact_reference,
    exact_item_reference,
    require,
    sha256_value,
    stable_unique,
)
from vfy_exceptions import normalize_exceptions


READY_GATES = frozenset({"pass", "pass_with_exception"})
READY_STATUSES = frozenset({"ready", "ready_with_exception"})
SCOPE_PHASES = ("PLN", "DSN", "REQ")


def _phase_disposition(store: ArtifactStore, projection: Any, phase: str) -> dict[str, str]:
    """Read the nearest frozen lifecycle table, never a Candidate decision."""
    for owner_phase in SCOPE_PHASES:
        nodes = [node for node in projection.nodes
                 if node.artifact_type == owner_phase and _ready_node(node)]
        rows = []
        for node in nodes:
            stored = store.read_revision(node.artifact_id, node.revision)
            parsed = parse_canonical_artifact(stored.payload.primary_blob)
            if owner_phase == "PLN":
                heading = "## 聚合适用性 Aggregated Applicability"
                require(parsed.text.count(heading) == 1,
                        "VFY_INPUT_AUTHORITY_MISMATCH", "PLN aggregated applicability is missing")
                section = re.split(r"(?m)^## ", parsed.text.split(heading, 1)[1], maxsplit=1)[0]
                tables = parse_markdown_tables(section)
            else:
                tables = parsed.tables
            for table in tables:
                for row in table.rows:
                    if row.get("Phase") == phase and "Disposition" in row:
                        rows.append(dict(row))
        if rows:
            require(len(rows) == 1 and rows[0].get("判断依据 Basis", "").strip(),
                    "VFY_INPUT_AUTHORITY_MISMATCH", "Lifecycle applicability Authority is ambiguous")
            require(rows[0]["Disposition"] in {"required", "n/a", "waived", "pending"},
                    "VFY_INPUT_AUTHORITY_MISMATCH", "Lifecycle applicability Authority is invalid")
            return rows[0]
    require(False, "VFY_INPUT_AUTHORITY_MISMATCH",
            "No frozen upstream lifecycle applicability Authority", details={"phase": phase})
    raise AssertionError("unreachable")


def _owner_refs(owner: str, cell: str) -> list[str]:
    return [exact_item_reference(item if "@" in item else f"{owner}#{item}")
            for item in parse_reference_set(cell)]


def _base(reference: str) -> str:
    text = str(reference).strip()
    if "@" not in text:
        return text
    return text.split("#", 1)[0].split("/", 1)[0]


def _plain(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {key: getattr(value, key) for key in dir(value) if not key.startswith("_")}


def _ready_node(node: Any) -> bool:
    return (
        node.revision_state == "frozen"
        and node.artifact_status in READY_STATUSES
        and node.gate_result in READY_GATES
        and node.authority_state == "valid"
        and not node.projection_errors
        and not node.open_items
    )


def _all_item_ids(stored: Any) -> dict[str, dict[str, str]]:
    """Collect exact Item IDs from primary and UTF-8 Markdown members."""

    output: dict[str, dict[str, str]] = {}

    def collect(raw: bytes, *, primary: bool) -> None:
        try:
            tables = (
                parse_canonical_artifact(raw).tables
                if primary
                else parse_markdown_tables(decode_primary_markdown(raw))
            )
        except Exception:
            return
        for table in tables:
            for row in table.rows:
                identity = row.get("ID") or row.get("Change ID")
                if not isinstance(identity, str) or not identity:
                    continue
                output.setdefault(identity, dict(row))

    collect(stored.payload.primary_blob, primary=True)
    for member in stored.payload.members:
        if member.media_type in {"text/markdown", "text/plain"}:
            collect(member.raw_bytes, primary=False)
    return output


def _select_requirement_projection(
    service: LifecycleQueryService,
    references: tuple[str, ...],
):
    artifact_bases = {_base(item) for item in references if "@" in item}
    matches = []
    for requirement in service.list_requirements():
        if not requirement.lineage_head or requirement.revision_state == "abandoned":
            continue
        projection = service.inspect_requirement(requirement.reference)
        graph = {node.reference for node in projection.nodes}
        if artifact_bases and artifact_bases <= graph | {
            _base(str(item.get("result_reference", "")))
            for item in projection.vfy_results
        }:
            matches.append(projection)
    require(
        len(matches) == 1,
        "VFY_INPUT_AUTHORITY_MISMATCH",
        "Exact VFY inputs must resolve to one current Requirement graph",
        status="action_required",
        details={"candidate_count": len(matches), "inputs": list(references)},
    )
    return matches[0]


def _authoritative_subjects(projection: Any) -> list[dict[str, Any]]:
    expected_results = {
        str(item["result_reference"]): dict(item) for item in projection.vfy_results
    }
    require(
        bool(expected_results),
        "VFY_SUBJECT_SET_INCOMPLETE",
        "Lifecycle Query exposes no complete current terminal IMP Result Set",
    )
    output: list[dict[str, Any]] = []
    for reference, result in sorted(expected_results.items()):
        owners = [
            claim
            for claim in projection.current_claims
            if claim.completed
            and claim.vfy_ready
            and any(row.get("result_reference") == reference for row in claim.results)
        ]
        require(
            len(owners) == 1,
            "VFY_SUBJECT_NOT_CURRENT",
            "Every terminal Result requires one current completed Claim owner",
            details={"reference": reference, "owner_count": len(owners)},
        )
        claim = owners[0]
        row = next(row for row in claim.results if row.get("result_reference") == reference)
        digest = row.get("result_digest") or result.get("result_digest")
        require(
            isinstance(digest, str) and digest.startswith("sha256:"),
            "VFY_SUBJECT_NOT_CURRENT",
            "Terminal Result Digest is unavailable",
            details={"reference": reference},
        )
        output.append(
            {
                "reference": reference,
                "resource_id": str(row["resource"]),
                "imp_revision_reference": str(claim.artifact_reference),
                "binding_lineage": str(claim.binding_lineage),
                "attempt": str(claim.attempt),
                "claim_state": str(claim.claim_state),
                "imp_revision_state": str(claim.revision_state),
                "baseline_reference": str(row["baseline_reference"]),
                "result_digest": str(digest),
                "cumulative_changed_scope": list(row.get("changed_scope", ())),
                "dependency_result_references": list(claim.dependency_results),
                "current_valid": True,
                "dependency_chain_valid": True,
            }
        )
    return output


def _select_scope_reference(
    references: tuple[str, ...], projection: Any, hint: Mapping[str, Any]
) -> str:
    graph = {node.reference: node for node in projection.nodes}
    explicit = []
    for phase in SCOPE_PHASES:
        explicit.extend(
            _base(item)
            for item in references
            if str(item).startswith(phase + "-") and "#" not in str(item) and "/" not in str(item)
        )
        if explicit:
            break
    hinted = _base(str((hint.get("scope") or {}).get("reference", "")))
    if not explicit and hinted:
        explicit = [hinted]
    explicit = list(dict.fromkeys(explicit))
    require(
        len(explicit) == 1 and explicit[0] in graph and _ready_node(graph[explicit[0]]),
        "VFY_SCOPE_AMBIGUOUS",
        "VFY requires one exact frozen ready Scope Source",
        details={"scope_candidates": explicit},
    )
    return explicit[0]


def _authoritative_scope(
    scope_reference: str,
    projection: Any,
    subjects: list[dict[str, Any]],
    hint: Mapping[str, Any],
    store: ArtifactStore,
) -> dict[str, Any]:
    phase = scope_reference.split("-", 1)[0]
    pln = _phase_disposition(store, projection, "PLN")
    require((phase == "PLN" and pln["Disposition"] == "required")
            or (phase != "PLN" and pln["Disposition"] in {"n/a", "waived"}),
            "VFY_SCOPE_REQUIRED", "Scope must follow the frozen PLN applicability")
    if phase == "REQ":
        dsn = _phase_disposition(store, projection, "DSN")
        require(dsn["Disposition"] in {"n/a", "waived"},
                "VFY_SCOPE_REQUIRED", "REQ fallback requires frozen DSN n/a or waived")
    subject_refs = {item["reference"] for item in subjects}
    claims = [
        claim
        for claim in projection.current_claims
        if any(row.get("result_reference") in subject_refs for row in claim.results)
    ]
    delivery_scope = sorted(
        {token for claim in claims for token in claim.execution_scope}
    )
    work_items = []
    for claim in sorted(claims, key=lambda item: item.binding_reference):
        resources = sorted(
            {
                str(row["resource"])
                for row in claim.results
                if row.get("result_reference") in subject_refs
            }
        )
        work_items.append(
            {
                "reference": str(claim.binding_reference),
                "target_phase": "IMP",
                "binding_reference": str(claim.binding_reference),
                "resource_ids": resources,
                "depends_on": list(claim.dependency_results),
            }
        )
    require(
        bool(delivery_scope) and bool(work_items),
        "VFY_SCOPE_REQUIRED",
        "Complete current IMP Scope and Work Item set are required",
    )
    disposition = pln["Disposition"]
    result = {
        "reference": scope_reference,
        "disposition": disposition,
        "delivery_scope": delivery_scope,
        "input_references": [
            str(node.reference)
            for node in projection.nodes
            if node.artifact_type == "CTX" and _ready_node(node)
        ],
        "imp_work_items": work_items,
    }
    if phase != "PLN":
        basis = pln["判断依据 Basis"].strip()
        require(
            disposition in {"n/a", "waived"} and bool(basis),
            "VFY_SCOPE_REQUIRED",
            "REQ/DSN fallback requires authoritative PLN disposition and basis",
        )
        result["disposition_basis"] = basis
    return result


def _authoritative_targets(
    store: ArtifactStore,
    projection: Any,
    hint: Mapping[str, Any],
) -> list[dict[str, Any]]:
    graph = {node.reference: node for node in projection.nodes}
    discovered: dict[str, dict[str, str]] = {}
    for node in projection.nodes:
        if node.artifact_type not in {"REQ", "DSN"} or not _ready_node(node):
            continue
        stored = store.read_revision(node.artifact_id, node.revision)
        for identity, row in _all_item_ids(stored).items():
            if identity.startswith("VFO-"):
                discovered[f"{node.reference}#{identity}"] = row
    hinted = list(hint.get("targets") or [])
    hinted_by_ref = {str(item.get("reference")): dict(item) for item in hinted if isinstance(item, Mapping)}
    if discovered:
        require(
            set(hinted_by_ref) == set(discovered),
            "VFY_TARGET_SET_INVALID",
            "Caller Target Set must exactly equal every authoritative VFO",
            details={"expected": sorted(discovered), "actual": sorted(hinted_by_ref)},
        )
        refs = sorted(discovered)
    else:
        disposition = _phase_disposition(store, projection, "DSN")
        require(disposition["Disposition"] in {"n/a", "waived"},
                "VFY_TARGET_SET_INVALID", "AC/Goal fallback requires frozen DSN n/a or waived")
        for node in projection.nodes:
            if node.artifact_type == "REQ" and _ready_node(node):
                stored = store.read_revision(node.artifact_id, node.revision)
                for identity, row in _all_item_ids(stored).items():
                    if identity.startswith(("AC-", "GOAL-", "GOL-")):
                        discovered[f"{node.reference}#{identity}"] = row
        refs = sorted(discovered)
        require(
            bool(refs) and set(refs) == set(hinted_by_ref),
            "VFY_TARGET_SET_INVALID",
            "Without VFO authority, only an explicit complete AC/Goal fallback is allowed",
        )
        for reference in refs:
            owner = _base(reference)
            require(
                owner in graph and _ready_node(graph[owner]),
                "VFY_TARGET_SET_INVALID",
                "Fallback Target owner is not current frozen Authority",
                details={"reference": reference},
            )
            stored = store.read_revision(graph[owner].artifact_id, graph[owner].revision)
            require(
                reference.split("#", 1)[1] in _all_item_ids(stored),
                "VFY_TARGET_SET_INVALID",
                "Fallback Target does not exist in its canonical owner",
                details={"reference": reference},
            )
    output = []
    for reference in refs:
        row = discovered[reference]
        is_vfo = "#VFO-" in reference
        purpose = str(row.get("Kind", "")).strip() if is_vfo else (
            "verification" if "#AC-" in reference else "validation"
        )
        require(
            purpose in {"verification", "validation", "both"},
            "VFY_TARGET_SET_INVALID",
            "Target Purpose must be explicitly frozen by the VFY strategy",
            details={"reference": reference},
        )
        output.append(
            {
                "reference": reference,
                "purpose": purpose,
                "summary": str(row.get("可观察结果 Observable Result", "")).strip()
                if is_vfo else " | ".join(str(value) for key, value in row.items() if key != "ID"),
                "source_kind": "vfo" if "#VFO-" in reference else (
                    "ac" if "#AC-" in reference else "goal"
                ),
                "obligation_references": _owner_refs(
                    _base(reference), row.get("Domain VFY Point References", "")
                ) if is_vfo else [reference],
            }
        )
    return output


def _required_obligations(store: ArtifactStore, projection: Any,
                          targets: list[dict[str, Any]], scope: Mapping[str, Any],
                          controls: list[str]) -> list[str]:
    required = set(controls)
    required.update(item["binding_reference"] for item in scope["imp_work_items"])
    nodes = {node.reference: node for node in projection.nodes}
    for target in targets:
        required.update(target["obligation_references"])
        owner = _base(target["reference"])
        node = nodes[owner]
        stored = store.read_revision(node.artifact_id, node.revision)
        row = _all_item_ids(stored)[target["reference"].split("#")[1]]
        for field in ("Method References", "Pass Criteria References", "Evidence Contract References"):
            required.update(_owner_refs(owner, row.get(field, "")))
    if scope["reference"].startswith("PLN-"):
        node = nodes[scope["reference"]]
        stored = store.read_revision(node.artifact_id, node.revision)
        for identity, row in _all_item_ids(stored).items():
            if row.get("目标 Phase Target Phase") == "VFY":
                required.add(f"{node.reference}#{identity}")
    return sorted(required)


def _resolve_control(
    resolver: ControlInputResolver, store: ArtifactStore, reference: str
) -> dict[str, Any]:
    errors = []
    if reference.startswith("VFY-"):
        for phase in ("REQ", "DSN", "PLN", "IMP"):
            try:
                value = resolver.resolve_vfy_return(store, reference, phase)
                result = _plain(value)
                result["authority_verified"] = True
                return result
            except Exception as exc:  # exact resolver is the authority; aggregate diagnostics only
                errors.append(str(exc))
    elif reference.startswith("RLS-"):
        for follow_up in ("return_req", "return_dsn", "return_pln", "return_imp"):
            try:
                value = resolver.resolve_rls_issue(store, reference, follow_up)
                result = _plain(value)
                result["authority_verified"] = True
                return result
            except Exception as exc:
                errors.append(str(exc))
    raise ControlInputError(
        f"Control Input is not one usable frozen VFY Return/RLS Issue: {reference}; "
        + " | ".join(errors[-4:])
    )


def _resolve_exception(
    store: ArtifactStore,
    authority: FrozenArtifactAuthorityVerifier,
    reference: str,
) -> dict[str, Any]:
    exact_item_reference(reference)
    require("#EX-" in reference, "VFY_EXCEPTION_INVALID", "Exception Reference must select EX-NNN")
    base, identity = reference.split("#", 1)
    artifact_id, revision = runtime_exact(base)
    resolved = store.resolve_exact_reference(base, verifier=authority).revision
    require(
        resolved.control.artifact_id == artifact_id and resolved.control.revision == revision,
        "VFY_EXCEPTION_INVALID",
        "Exception owner resolution changed",
    )
    rows = _all_item_ids(resolved)
    require(identity in rows, "VFY_EXCEPTION_INVALID", "Exception item is missing from frozen owner")
    row = rows[identity]
    scope = parse_reference_set(
        row.get("作用域或被跳过义务 Scope or Skipped Obligation", "")
    )
    if not scope:
        raw_scope = row.get("Scope") or row.get("scope") or ""
        scope = tuple(item.strip() for item in str(raw_scope).split(",") if item.strip())
    raw = {
        "id": identity,
        "state": row.get("State", "active"),
        "origin_reference": reference,
        "scope": list(scope),
        "reason": row.get("原因 Reason", ""),
        "known_risk": row.get("已知风险 Known Risk", ""),
        "compensating_control": row.get("补偿措施 Compensating Control", ""),
        "approval": row.get("批准记录 Approver, Role and Time", ""),
        "revisit_condition": row.get("复查条件 Revisit Condition", ""),
        "downstream_obligation": row.get("下游限制 Downstream Obligation", ""),
        "resolution_references": list(
            parse_reference_set(row.get("解决或替代引用 Resolution or Superseding References", ""))
        ),
        "accepts_product_failure": "product_result:fail" in scope,
        "authority_verified": True,
    }
    return normalize_exceptions([raw])[0]


def _assert_hint_equal(name: str, expected: Any, actual: Any) -> None:
    require(
        sha256_value(expected) == sha256_value(actual),
        "VFY_INPUT_AUTHORITY_MISMATCH",
        f"Caller {name} differs from canonical Authority",
        details={"expected_digest": sha256_value(expected), "actual_digest": sha256_value(actual)},
    )


def compile_candidate(
    project_root: Path,
    input_references: Iterable[str],
    hint: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Compile one persistent Candidate from exact references and caller method hints."""

    root = Path(project_root).expanduser().resolve()
    references = stable_unique(input_references, field="VFY input")
    require(
        bool(references),
        "VFY_INPUT_REQUIRED",
        "Persistent create/revise requires repeatable exact --input",
        status="action_required",
    )
    candidate_hint = deepcopy(dict(hint or {}))
    store = ArtifactStore.open_read_only(root)
    service = LifecycleQueryService(root)
    projection = _select_requirement_projection(service, references)
    subjects = _authoritative_subjects(projection)
    scope_reference = _select_scope_reference(references, projection, candidate_hint)
    scope = _authoritative_scope(scope_reference, projection, subjects, candidate_hint, store)
    targets = _authoritative_targets(store, projection, candidate_hint)

    control_refs = [
        item for item in references if item.startswith(("VFY-", "RLS-")) and "#" in item
    ]
    resolver = ControlInputResolver(root)
    controls = [_resolve_control(resolver, store, item) for item in control_refs]
    exception_refs = [item for item in references if "#EX-" in item]
    authority = FrozenArtifactAuthorityVerifier(root)
    exceptions = [_resolve_exception(store, authority, item) for item in exception_refs]

    applicability = _phase_disposition(store, projection, "RLS")["Disposition"]
    if "rls_applicability" in candidate_hint:
        _assert_hint_equal("rls_applicability", applicability, candidate_hint["rls_applicability"])
    require(
        applicability in {"required", "n/a", "waived", "pending"},
        "VFY_CONTRACT_INVALID",
        "RLS applicability is invalid",
    )
    context_nodes = [
        node.reference
        for node in projection.nodes
        if node.artifact_type == "CTX" and _ready_node(node)
    ]
    require(
        len(context_nodes) == 1,
        "VFY_INPUT_AUTHORITY_MISMATCH",
        "Requirement graph must contain one current ready Context",
    )
    authoritative = {
        "scope": scope,
        "subjects": subjects,
        "targets": targets,
        "control_inputs": control_refs,
        "exceptions": exceptions,
    }
    required_obligations = _required_obligations(store, projection, targets, scope, control_refs)
    if "required_obligation_references" in candidate_hint:
        _assert_hint_equal("required_obligation_references", required_obligations,
                           sorted(candidate_hint["required_obligation_references"]))
    for key in ("scope", "subjects", "targets", "control_inputs", "exceptions"):
        if key in candidate_hint and candidate_hint.get(key) is not None:
            _assert_hint_equal(key, authoritative[key], candidate_hint[key])

    owner_inputs = {
        context_nodes[0],
        scope_reference,
        *(str(item["imp_revision_reference"]) for item in subjects),
        *(_base(str(item["reference"])) for item in targets),
        *(_base(item) for item in control_refs),
        *(_base(item) for item in exception_refs),
    }
    return {
        "contract": "sdlc-ai-spec/vfy-candidate/v1",
        "context_reference": context_nodes[0],
        "profile": str(candidate_hint.get("profile", "full")),
        "title": str(candidate_hint.get("title", "Verification and Validation")),
        "scope": scope,
        "subjects": subjects,
        "targets": targets,
        "methods": deepcopy(list(candidate_hint.get("methods") or [])),
        "required_obligation_references": required_obligations,
        "control_inputs": control_refs,
        "control_authorities": controls,
        "control_resolutions": deepcopy(
            list(candidate_hint.get("control_resolutions") or [])
        ),
        "returns": deepcopy(list(candidate_hint.get("returns") or [])),
        "exceptions": exceptions,
        "rls_applicability": applicability,
        "release_target_obligations": deepcopy(
            list(candidate_hint.get("release_target_obligations") or [])
        ),
        "target_fallback_allowed": bool(candidate_hint.get("target_fallback_allowed")),
        "owner_artifact_inputs": sorted(owner_inputs),
        "authority_compiled": True,
    }


def assert_candidate_authority(project_root: Path, candidate: Mapping[str, Any]) -> None:
    """Recompile and require exact authoritative equality before persistence."""

    refs = list(candidate.get("owner_artifact_inputs") or [])
    refs.extend(candidate.get("control_inputs") or [])
    refs.extend(
        str(item.get("origin_reference"))
        for item in candidate.get("exceptions", [])
        if isinstance(item, Mapping) and item.get("origin_reference")
    )
    compiled = compile_candidate(project_root, refs, candidate)
    for key in (
        "context_reference",
        "scope",
        "subjects",
        "targets",
        "control_inputs",
        "exceptions",
        "rls_applicability",
    ):
        _assert_hint_equal(key, compiled[key], candidate.get(key))
