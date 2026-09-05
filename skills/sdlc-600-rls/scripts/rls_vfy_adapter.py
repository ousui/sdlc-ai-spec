"""Single dual-mode VFY wire adapter used by every RLS module.

The final-shaped mode is a shadow compatibility boundary derived from the
observed VFY repair snapshot. It is not promoted to final authority until the
VFY implementation/evidence Web review is accepted and the interface delta
review is closed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from rls_common import (
    digest_reference,
    exact_exception_reference,
    exact_reference,
    exact_scope_reference,
    require,
    sha256_reference,
    stable_unique,
)


FINAL_FIELDS = frozenset(
    {
        "contract",
        "provisional",
        "vfy_reference",
        "revision_state",
        "artifact_status",
        "artifact_gate",
        "early_stop",
        "pending_fields",
        "scope_reference",
        "subject_references",
        "result_references",
        "subject_current_valid",
        "imp_chain_current_valid",
        "con_ver",
        "con_val",
        "product_result",
        "unresolved_returns",
        "rls_applicability",
        "release_target_obligations",
        "evidence_references",
        "exception",
        "exception_references",
        "source_digest",
        "rls_ready",
    }
)


@dataclass(frozen=True)
class VfyReleaseCandidate:
    vfy_reference: str
    scope_reference: str
    subject_references: tuple[str, ...]
    result_references: tuple[str, ...]
    con_ver: str
    con_val: str
    product_result: str
    artifact_status: str
    artifact_gate: str
    early_stop: bool
    unresolved_returns: tuple[str, ...]
    rls_applicability: str
    release_target_obligations: tuple[dict[str, Any], ...]
    evidence_references: tuple[str, ...]
    exception_references: tuple[str, ...]
    source_digest: str
    candidate_digest: str
    rls_ready: bool
    provisional: bool
    interface_mode: str
    context_reference: str | None = None
    profile: str | None = None
    input_references: tuple[str, ...] = ()
    authority_verified: bool = False
    rls_work_item_references: tuple[str, ...] = ()
    authority_exceptions: tuple[dict, ...] = ()
    obligation_sources: tuple[dict, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_vfy_source(source: Any) -> dict[str, Any]:
    if isinstance(source, dict):
        return dict(source)
    if isinstance(source, (str, Path)):
        path = Path(source)
        require(path.is_file(), "RLS_VFY_NOT_READY", "VFY JSON source does not exist")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        require(
            isinstance(loaded, dict),
            "RLS_VFY_NOT_READY",
            "VFY source must be an object",
        )
        return loaded
    raise TypeError("VFY source must be an object or JSON path")


def _unique_sequence(payload: dict[str, Any], field: str, *, strict: bool) -> tuple[str, ...]:
    raw = payload.get(field, [])
    require(isinstance(raw, list), "RLS_VFY_NOT_READY", f"{field} must be an array")
    normalized = tuple(stable_unique(raw))
    if strict:
        require(
            len(normalized) == len(raw),
            "RLS_VFY_NOT_READY",
            f"{field} must not contain duplicates",
        )
    return normalized


def _normalize_obligations(rows: Any) -> tuple[dict[str, Any], ...]:
    require(
        isinstance(rows, list),
        "RLS_VFY_NOT_READY",
        "VFY obligations must be an array",
    )
    output: list[dict[str, Any]] = []
    for index, raw in enumerate(rows, start=1):
        require(
            isinstance(raw, dict),
            "RLS_VFY_NOT_READY",
            "VFY obligation must be an object",
        )
        row = dict(raw)
        for key in ("reference", "confirmation", "expected", "evidence_requirement"):
            require(
                isinstance(row.get(key), str) and row[key].strip(),
                "RLS_VFY_NOT_READY",
                f"VFY obligation {index} missing {key}",
            )
            row[key] = row[key].strip()
        output.append(row)
    return tuple(output)


def _validate_final_shape(payload: dict[str, Any]) -> None:
    missing = sorted(FINAL_FIELDS - set(payload))
    extra = sorted(set(payload) - FINAL_FIELDS)
    require(
        not missing and not extra,
        "RLS_VFY_NOT_READY",
        "final VFY candidate fields differ from the shadow interface",
        missing=missing,
        extra=extra,
    )


def _validate_final_exception(
    product: str,
    applicability: str,
    gate: str,
    exception: Any,
    exception_references: tuple[str, ...],
) -> None:
    if gate == "pass_with_exception":
        require(
            bool(exception_references),
            "RLS_VFY_NOT_READY",
            "pass_with_exception requires exact VFY Exception references",
        )
    if applicability == "waived":
        require(
            bool(exception_references),
            "RLS_VFY_NOT_READY",
            "RLS applicability=waived requires an exact VFY Exception reference",
        )
    if product != "fail":
        return
    require(
        isinstance(exception, dict),
        "RLS_VFY_NOT_READY",
        "VFY product fail requires an active scoped Exception",
    )
    origin = exception.get("origin_reference")
    require(
        exception.get("state") in {"active", "carried"}
        and exception.get("authority_verified") is True
        and exception.get("accepts_product_failure") is True
        and "product_result:fail" in exception.get("scope", [])
        and origin in exception_references,
        "RLS_VFY_NOT_READY",
        "VFY product-failure Exception is not current, scoped and authoritative",
    )


def _validate_provisional_exception(product: str, exception: Any) -> tuple[str, ...]:
    if product != "fail":
        return ()
    require(
        isinstance(exception, dict)
        and (exception.get("status") == "active" or exception.get("state") in {"active", "carried"})
        and exception.get("scope"),
        "RLS_VFY_NOT_READY",
        "VFY product fail requires a current scoped Exception",
    )
    reference = exception.get("reference") or exception.get("origin_reference")
    return tuple(stable_unique([reference])) if reference else ()


def adapt_vfy_payload(
    source: Any,
    *,
    allow_provisional: bool = True,
) -> VfyReleaseCandidate:
    payload = load_vfy_source(source)
    require(
        payload.get("contract") == "sdlc-ai-spec/vfy-release-candidate/v1",
        "RLS_VFY_NOT_READY",
        "unsupported VFY projection contract",
    )
    require(
        isinstance(payload.get("provisional"), bool),
        "RLS_VFY_NOT_READY",
        "VFY candidate provisional flag must be boolean",
    )
    provisional = payload["provisional"]
    require(
        allow_provisional or not provisional,
        "RLS_VFY_NOT_READY",
        "provisional VFY input is not allowed",
    )
    if not provisional:
        _validate_final_shape(payload)

    reference = exact_reference(payload.get("vfy_reference", ""), "VFY")
    require(
        payload.get("revision_state") == "frozen",
        "RLS_VFY_NOT_READY",
        "VFY revision must be frozen",
    )
    gate = payload.get("artifact_gate")
    require(
        gate in {"pass", "pass_with_exception"},
        "RLS_VFY_NOT_READY",
        "VFY Artifact Gate is not downstream-usable",
    )
    require(
        payload.get("early_stop") is False,
        "RLS_VFY_NOT_READY",
        "early-stop VFY never enters RLS",
    )
    require(
        isinstance(payload.get("pending_fields", []), list)
        and not payload.get("pending_fields", []),
        "RLS_VFY_NOT_READY",
        "VFY has pending Method/Target/Conclusion fields",
    )

    terminal = {"pass", "waived", "n/a", "fail"}
    con_ver = payload.get("con_ver")
    con_val = payload.get("con_val")
    require(
        con_ver in terminal and con_val in terminal,
        "RLS_VFY_NOT_READY",
        "VFY conclusions are incomplete",
    )
    product = payload.get("product_result")
    require(
        product in terminal,
        "RLS_VFY_NOT_READY",
        "VFY product result is not terminal",
    )

    unresolved = _unique_sequence(payload, "unresolved_returns", strict=not provisional)
    require(
        not unresolved,
        "RLS_VFY_NOT_READY",
        "unresolved VFY Return blocks RLS",
        returns=list(unresolved),
    )

    scope_raw = payload.get("scope_reference")
    if provisional:
        require(
            isinstance(scope_raw, str) and scope_raw.strip(),
            "RLS_SCOPE_MISMATCH",
            "VFY Scope is missing",
        )
        scope = scope_raw.strip()
    else:
        scope = exact_scope_reference(scope_raw)

    subjects = _unique_sequence(payload, "subject_references", strict=not provisional)
    results = _unique_sequence(payload, "result_references", strict=not provisional)
    require(
        subjects
        and results
        and len(subjects) == len(results)
        and set(subjects) == set(results),
        "RLS_RESULT_MISMATCH",
        "Release Result Set must exactly equal the VFY Subject Set",
    )
    require(
        payload.get("subject_current_valid") is True
        and payload.get("imp_chain_current_valid") is True,
        "RLS_VFY_NOT_READY",
        "VFY Subject Set or IMP Result chain is stale",
    )

    applicability = payload.get("rls_applicability")
    allowed_applicability = {"required", "n/a", "waived"}
    if provisional:
        allowed_applicability.add("pending")
    require(
        applicability in allowed_applicability,
        "RLS_APPLICABILITY_PENDING",
        "invalid or unresolved RLS applicability",
    )

    evidence = _unique_sequence(payload, "evidence_references", strict=not provisional)
    require(
        bool(evidence),
        "RLS_VFY_NOT_READY",
        "VFY Evidence closure is incomplete",
    )
    if provisional:
        require(
            payload.get("supporting_member_closure_valid") is True,
            "RLS_VFY_NOT_READY",
            "provisional VFY Supporting Member closure is incomplete",
        )

    exception = payload.get("exception")
    if provisional:
        exception_references = _validate_provisional_exception(product, exception)
        supplied = payload.get("exception_references")
        if supplied is not None:
            exception_references = _unique_sequence(
                payload, "exception_references", strict=False
            )
        source_digest = payload.get("source_digest")
        source_digest = (
            digest_reference(source_digest)
            if source_digest is not None
            else sha256_reference(payload)
        )
        rls_ready = bool(payload.get("rls_ready", applicability == "required"))
        interface_mode = "PROVISIONAL_VFY_INTERFACE"
    else:
        exception_references = _unique_sequence(
            payload, "exception_references", strict=True
        )
        exception_references = tuple(
            exact_exception_reference(value) for value in exception_references
        )
        _validate_final_exception(
            product, applicability, gate, exception, exception_references
        )
        source_digest = digest_reference(payload.get("source_digest", ""))
        require(
            isinstance(payload.get("rls_ready"), bool),
            "RLS_VFY_NOT_READY",
            "final VFY candidate must declare rls_ready",
        )
        rls_ready = payload["rls_ready"]
        require(
            (applicability == "required" and rls_ready is True)
            or (applicability in {"n/a", "waived"} and rls_ready is False),
            "RLS_VFY_NOT_READY",
            "RLS readiness contradicts final applicability",
        )
        artifact_status = payload.get("artifact_status")
        require(
            (gate == "pass" and artifact_status == "ready")
            or (
                gate == "pass_with_exception"
                and artifact_status == "ready_with_exception"
            ),
            "RLS_VFY_NOT_READY",
            "VFY Artifact Status and Gate are inconsistent",
        )
        interface_mode = "VFY_FINAL_SHAPE_SHADOW"

    obligations = _normalize_obligations(
        payload.get("release_target_obligations", [])
    )
    return VfyReleaseCandidate(
        vfy_reference=reference,
        scope_reference=scope,
        subject_references=subjects,
        result_references=results,
        con_ver=con_ver,
        con_val=con_val,
        product_result=product,
        artifact_status=str(payload.get("artifact_status", "")),
        artifact_gate=gate,
        early_stop=False,
        unresolved_returns=unresolved,
        rls_applicability=applicability,
        release_target_obligations=obligations,
        evidence_references=evidence,
        exception_references=exception_references,
        source_digest=source_digest,
        candidate_digest=sha256_reference(payload),
        rls_ready=rls_ready,
        provisional=provisional,
        interface_mode=interface_mode,
    )


# Final persisted-input boundary. All VFY wire parsing lives in this adapter.
# These projections are locked to accepted VFY 46509eb... and differentially
# tested against its real producer; they do not execute a sibling Skill.
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_lifecycle.query_vfy import LifecycleQueryService
from packages.sdlc_phasekit import manifest
from packages.sdlc_runtime import (
    FrozenArtifactAuthorityVerifier, ControlInputResolver,
    parse_canonical_artifact, parse_reference_set,
)
from packages.sdlc_runtime.canonical import FINAL_CONFIRMATION_HEADERS, require_single_row, require_single_table, parse_markdown_tables

_CONFIRMATION_STATE_KEYS = (
    "pre_execution_contract_digest", "subject_set_digest", "method_results",
    "target_conclusions", "fixed_conclusions", "product_result", "returns",
    "control_resolutions", "exceptions", "early_stop", "early_stop_basis",
    "rls_applicability", "release_target_obligations",
)


def _final_confirmation(primary, state):
    row = require_single_row(require_single_table(parse_canonical_artifact(primary),
                              FINAL_CONFIRMATION_HEADERS, "Final Confirmation"), "Final Confirmation")
    require(row["Result"] == "approved", "RLS_VFY_NOT_READY", "VFY has no approved Final Confirmation")
    subject = {key: state[key] for key in _CONFIRMATION_STATE_KEYS}
    subject["artifact_reference"] = state["artifact"]["reference"]
    return {
        "mode": row["Mode"], "confirmer": row["Confirmer"], "role": row["Role"],
        "authority_reference": row["Authority Reference"], "confirmed_at": row["Confirmed At"],
        "accepted_exception_references": list(parse_reference_set(row["Accepted Exception References"])),
        "subject_digest": sha256_reference(subject), "control_input_digest": row["Control Input Digest"],
        "evaluation_contract_set": row["Evaluation Contract Set"],
        "check_set_result_digest": row["Check Set Result Digest"],
        "contract_digest": state["pre_execution_contract_digest"],
        "subject_set_digest": state["subject_set_digest"], "product_result": state["product_result"],
        "method_result_digest": sha256_reference(state["method_results"]),
        "return_digest": sha256_reference(state["returns"]),
    }


def _exact_authority(store, root, reference):
    resolved = store.resolve_exact_reference(reference, verifier=FrozenArtifactAuthorityVerifier(root))
    return resolved.revision


def _base_reference(reference):
    return reference.split("#", 1)[0].split("/", 1)[0]


def _requirement_owner(store, root, scope):
    todo, seen, owners = [scope], set(), set()
    while todo:
        reference = todo.pop()
        if reference in seen: continue
        seen.add(reference)
        stored = _exact_authority(store, root, reference)
        if stored.payload.artifact_type == "REQ":
            owners.add(reference)
            continue
        parsed = parse_canonical_artifact(stored.payload.primary_blob)
        todo.extend(_base_reference(value) for value in parsed.front_matter.get("inputs", [])
                    if value.startswith(("REQ-", "DSN-", "PLN-")))
    require(len(owners) == 1, "RLS_SCOPE_MISMATCH", "Scope requires one exact frozen Requirement lineage")
    return owners.pop()


def _aggregate(values):
    require(bool(values) and all(v in {"fail", "pending", "waived", "pass", "n/a"} for v in values),
            "RLS_VFY_NOT_READY", "VFY conclusion input is invalid")
    return next(value for value in ("fail", "pending", "waived", "pass", "n/a") if value in values)


def _verify_conclusions(state):
    methods = {row["id"]: row for row in state["methods"]}
    results = {row["method_id"]: row for row in state["method_results"]}
    require(len(methods) == len(state["methods"]) and len(results) == len(state["method_results"])
            and set(methods) == set(results), "RLS_VFY_NOT_READY", "VFY Method/Result coverage is incomplete")
    targets = {row["target_reference"]: row for row in state["target_conclusions"]}
    require(len(targets) == len(state["targets"]) == len(state["target_conclusions"])
            and set(targets) == {row["reference"] for row in state["targets"]},
            "RLS_VFY_NOT_READY", "VFY Target coverage is incomplete")
    by_dimension = {"verification": [], "validation": []}
    for target in state["targets"]:
        dimensions = tuple(by_dimension) if target["purpose"] == "both" else (target["purpose"],)
        expected = {}
        for dimension in dimensions:
            expected[dimension] = _aggregate([results[identity]["result"] for identity, method in methods.items()
                if target["reference"] in method["target_references"] and method["purpose"] in {dimension, "both"}])
            by_dimension[dimension].append(expected[dimension])
        row = targets[target["reference"]]
        require(row["dimension_projections"] == expected and row["conclusion"] == _aggregate(list(expected.values())),
                "RLS_VFY_NOT_READY", "VFY Target conclusion disagrees with Method results")
    fixed = {row["id"]: row["conclusion"] for row in state["fixed_conclusions"]}
    require(len(state["fixed_conclusions"]) == 2 and set(fixed) == {"CON-VER", "CON-VAL"},
            "RLS_VFY_NOT_READY", "VFY fixed Conclusion set is incomplete")
    for identity, dimension in (("CON-VER", "verification"), ("CON-VAL", "validation")):
        expected = _aggregate(by_dimension[dimension]) if by_dimension[dimension] else "n/a"
        require(fixed[identity] == expected, "RLS_VFY_NOT_READY", "VFY fixed Conclusion disagrees with Target results")
    require(state["product_result"] == _aggregate(list(fixed.values())),
            "RLS_VFY_NOT_READY", "VFY product result disagrees with fixed Conclusions")
    return fixed


def _verify_current_subjects(state, projection):
    require(not projection.blockers, "RLS_VFY_NOT_READY", "Current lifecycle has blockers", blockers=projection.blockers)
    current = {}
    for claim in projection.current_claims:
        for result in claim.results:
            if result["result_reference"] == "N/A": continue
            current[result["result_reference"]] = {
                "resource_id": result["resource"], "imp_revision_reference": claim.artifact_reference,
                "binding_lineage": claim.binding_lineage, "attempt": str(claim.attempt),
                "claim_state": claim.claim_state, "imp_revision_state": claim.revision_state,
                "baseline_reference": result["baseline_reference"], "result_digest": result["result_digest"],
                "cumulative_changed_scope": list(result["changed_scope"]),
                "dependency_result_references": list(claim.dependency_results),
            }
    selected = {row["result_reference"] for row in projection.vfy_results}
    subjects = state["subjects"]
    require(selected and len(subjects) == len(selected) and {row["reference"] for row in subjects} == selected,
            "RLS_RESULT_MISMATCH", "VFY must cover the complete current terminal IMP Result Set")
    for subject in subjects:
        expected = current.get(subject["reference"])
        require(expected is not None and all(subject.get(key) == value for key, value in expected.items())
                and subject.get("current_valid") is True and subject.get("dependency_chain_valid") is True,
                "RLS_VFY_NOT_READY", "VFY Subject differs from current IMP Claim/Result")
    scope = sorted({token for claim in projection.current_claims
                    if any(row["result_reference"] in selected for row in claim.results)
                    for token in claim.execution_scope})
    require(state["scope"]["delivery_scope"] == scope, "RLS_SCOPE_MISMATCH", "VFY narrowed the current IMP Scope")


def _verify_supporting(stored, state):
    require(manifest(stored.payload.members) == stored.payload.manifest,
            "RLS_VFY_NOT_READY", "VFY Manifest closure is inconsistent")
    indexed = {row.member_id: row for row in stored.payload.members}
    expected = {"VFY-STATE"} | {f"VFY-EVIDENCE-{n:03d}" for n in range(1, len(state["evidence"]) + 1)}
    require(set(indexed) == expected and len(indexed) == len(stored.payload.members),
            "RLS_VFY_NOT_READY", "VFY Supporting Member set is missing, extra or duplicated")
    references = set()
    for n, evidence in enumerate(state["evidence"], 1):
        require(json.loads(indexed[f"VFY-EVIDENCE-{n:03d}"].raw_bytes) == evidence,
                "RLS_VFY_NOT_READY", "VFY Evidence Member differs from State")
        source = deepcopy(evidence); digest = source.pop("sha256"); reference = source.pop("reference")
        require(digest == sha256_reference(source) and reference == evidence["id"] + "@" + digest
                and reference not in references, "RLS_VFY_NOT_READY", "VFY immutable Evidence digest mismatch")
        references.add(reference)
    methods = {row["id"]: row for row in state["methods"]}
    exception_refs = {row["origin_reference"] for row in state["exceptions"]}
    for row in state["method_results"]:
        method = methods[row["method_id"]]
        if row["result"] == "waived":
            require(method["disposition"] == "waived" and method["exception_reference"] in exception_refs
                    and row["evidence_references"] == [method["exception_reference"]],
                    "RLS_VFY_NOT_READY", "waived VFY Method must bind its exact current Exception")
        else:
            require(set(row["evidence_references"]) <= references,
                    "RLS_VFY_NOT_READY", "VFY Method references missing Evidence")
        if row["result"] in {"pass", "fail"}:
            require(bool(row["evidence_references"]), "RLS_VFY_NOT_READY", "VFY terminal Method has no Evidence")
    parsed = parse_canonical_artifact(stored.payload.primary_blob)
    tables = [table for table in parsed.tables if "Member ID" in table.headers and "SHA-256 Digest" in table.headers]
    require(len(tables) == 1, "RLS_VFY_NOT_READY", "VFY Primary Manifest table is ambiguous")
    require({row["Member ID"]: row["SHA-256 Digest"] for row in tables[0].rows} ==
            {identity: member.sha256 for identity, member in indexed.items()},
            "RLS_VFY_NOT_READY", "VFY Primary does not bind actual Supporting Member digests")


def _verify_exceptions(store, root, state):
    for exception in state["exceptions"]:
        reference = exact_exception_reference(exception["origin_reference"])
        owner, identity = reference.split("#")
        stored = _exact_authority(store, root, owner)
        tables = list(parse_canonical_artifact(stored.payload.primary_blob).tables)
        for member in stored.payload.members:
            if member.media_type in {"text/markdown", "text/plain"}:
                tables.extend(parse_markdown_tables(member.raw_bytes.decode("utf-8")))
        rows = [row for table in tables for row in table.rows if row.get("ID") == identity]
        require(len(rows) == 1, "RLS_VFY_NOT_READY", "VFY Exception owner is missing or ambiguous")
        row = rows[0]
        fields = {"state": "State", "reason": "原因 Reason", "known_risk": "已知风险 Known Risk",
                  "compensating_control": "补偿措施 Compensating Control", "approval": "批准记录 Approver, Role and Time",
                  "revisit_condition": "复查条件 Revisit Condition", "downstream_obligation": "下游限制 Downstream Obligation"}
        require(exception.get("state") in {"active", "carried"}
                and all(exception.get(key) == row.get(column) for key, column in fields.items())
                and list(parse_reference_set(row.get("作用域或被跳过义务 Scope or Skipped Obligation", ""))) == exception["scope"],
                "RLS_VFY_NOT_READY", "VFY Exception differs from current exact frozen owner")
        require(exception.get("authority_verified") is True
                and exception.get("accepts_product_failure") == ("product_result:fail" in exception["scope"])
                and exception.get("resolution_references", []) == list(parse_reference_set(row.get("解决或替代引用 Resolution or Superseding References", ""))),
                "RLS_VFY_NOT_READY", "VFY Exception authorization or resolution differs")
        boundary = {state["scope"]["reference"], *state["scope"]["delivery_scope"], "product_result:fail"}
        for method in state["methods"]:
            boundary.update([method["id"], *method["target_references"], *method["obligation_references"], *method["subject_references"]])
        if state["rls_applicability"] == "waived": boundary.update({"RLS", "phase:RLS"})
        require(bool(set(exception["scope"]) & boundary), "RLS_VFY_NOT_READY", "Exception has no current VFY scope")
    if state["rls_applicability"] == "waived":
        require(any(set(row["scope"]) & {"RLS", "phase:RLS"} or "RLS" in row["downstream_obligation"] for row in state["exceptions"]),
                "RLS_VFY_NOT_READY", "RLS waiver lacks a current scoped Exception")


def _verify_applicability(store, root, state, projection):
    import re
    for phase in ("PLN", "DSN", "REQ"):
        rows = []
        for node in projection.nodes:
            if node.artifact_type != phase or node.revision_state != "frozen" or node.authority_state != "valid": continue
            parsed = parse_canonical_artifact(_exact_authority(store, root, node.reference).payload.primary_blob)
            tables = parsed.tables
            if phase == "PLN":
                heading = "## 聚合适用性 Aggregated Applicability"
                require(parsed.text.count(heading) == 1, "RLS_VFY_NOT_READY", "PLN applicability is ambiguous")
                tables = parse_markdown_tables(re.split(r"(?m)^## ", parsed.text.split(heading, 1)[1], maxsplit=1)[0])
            rows.extend(row for table in tables for row in table.rows if row.get("Phase") == "RLS" and "Disposition" in row)
        if rows:
            require(len(rows) == 1 and rows[0].get("判断依据 Basis", "").strip()
                    and rows[0]["Disposition"] == state["rls_applicability"],
                    "RLS_VFY_NOT_READY", "RLS applicability differs from frozen upstream authority")
            return
    require(False, "RLS_VFY_NOT_READY", "RLS applicability authority is missing")


def _verify_controls(state):
    inputs = state["control_inputs"]
    authorities = {row["reference"]: row for row in state["control_authorities"]}
    resolutions = {row["control_reference"]: row for row in state["control_resolutions"]}
    require(len(inputs) == len(set(inputs)) == len(authorities) == len(state["control_authorities"])
            and set(inputs) == set(authorities) and len(resolutions) == len(state["control_resolutions"])
            and set(resolutions) <= set(inputs), "RLS_VFY_NOT_READY", "Control authority or resolution coverage differs")
    methods = {row["id"]: row for row in state["methods"]}
    results = {row["method_id"]: row for row in state["method_results"]}
    targets = {row["target_reference"]: row for row in state["target_conclusions"]}
    evidence = {row["reference"]: row for row in state["evidence"]}
    subjects = {row["reference"] for row in state["subjects"]}
    for reference, row in resolutions.items():
        authority = authorities[reference]
        method_ids, target_refs, evidence_refs = row["method_references"], row["target_references"], row["evidence_references"]
        require(row["status"] == "resolved" and row["subject_changed"] is True and method_ids and target_refs and evidence_refs,
                "RLS_VFY_NOT_READY", "Control has no complete current proof")
        require(row["required_outcome"] == (authority.get("required_outcome") or authority.get("expected") or authority.get("statement")),
                "RLS_VFY_NOT_READY", "Control required outcome changed")
        if reference.startswith("VFY-"):
            require(set(method_ids) == set(authority["method_references"]) and set(target_refs) == set(authority["target_references"]),
                    "RLS_VFY_NOT_READY", "Return proof scope changed")
        for identity in method_ids:
            require(identity in methods and reference in methods[identity]["obligation_references"]
                    and results[identity]["result"] == "pass" and set(results[identity]["actual_subject_references"]) == subjects,
                    "RLS_VFY_NOT_READY", "Control Method does not prove current Subjects")
        require(all(ref in targets and targets[ref]["conclusion"] == "pass" for ref in target_refs),
                "RLS_VFY_NOT_READY", "Control Target has no passing proof")
        for ref in evidence_refs:
            item = evidence.get(ref, {})
            require(item.get("result") == "pass" and item.get("method_id") in method_ids
                    and set(item.get("target_references", [])) <= set(target_refs)
                    and set(item.get("subject_references", [])) == subjects
                    and ref in results[item["method_id"]]["evidence_references"],
                    "RLS_VFY_NOT_READY", "Control Evidence does not bind current Method/Target/Subjects")
        previous = set(authority.get("subject_references", [])) or {ref for ref in authority.get("source_references", []) if ref.startswith("IMP-") and "/RES-" in ref}
        require(not previous or previous != subjects, "RLS_VFY_NOT_READY", "Control recovery reused old Subjects")


def _obligation_sources(state, exact, work_items):
    """Keep wire bytes unchanged; derive the complete RCF source closure separately."""
    known = set(work_items) | {row["origin_reference"] for row in state["exceptions"]}
    for method in state["methods"]:
        known.update([exact + "#" + method["id"], *method["target_references"], *method["obligation_references"]])
    output = []
    for obligation in state["release_target_obligations"]:
        extra = obligation.get("source_references", [])
        require(isinstance(extra, list) and all(isinstance(ref, str) for ref in extra),
                "RLS_CONFIRMATION_CONTRACT_INCOMPLETE", "obligation Source References must be exact references")
        sources = {obligation["reference"], *extra}
        require(sources <= known, "RLS_CONFIRMATION_CONTRACT_INCOMPLETE", "obligation has an unverified source")
        for method in state["methods"]:
            if method["disposition"] != "waived": continue
            linked = {exact + "#" + method["id"], method.get("exception_reference"), *method["target_references"], *method["obligation_references"]}
            if sources & linked:
                sources.update(ref for ref in linked if ref and (ref == exact + "#" + method["id"] or ref == method.get("exception_reference") or ref in method["target_references"]))
        output.append({"reference": obligation["reference"], "source_references": sorted(sources)})
    return tuple(output)


def read_vfy_candidate(project_root, reference, *, expected_candidate=None):
    root = Path(project_root).resolve(); exact = exact_reference(reference, "VFY")
    store = ArtifactStore.open_read_only(root)
    stored = _exact_authority(store, root, exact)
    matches = [item for item in stored.payload.members if item.member_id == "VFY-STATE"]
    require(len(matches) == 1, "RLS_VFY_NOT_READY", "VFY requires one actual State Member")
    state = json.loads(matches[0].raw_bytes)
    require(state.get("contract") == "sdlc-ai-spec/vfy-state/v1" and state["artifact"]["reference"] == exact,
            "RLS_VFY_NOT_READY", "VFY State contract or identity mismatch")
    require(state.get("final_confirmation") is None, "RLS_VFY_NOT_READY", "VFY State Member has unexpected Final Confirmation")
    state["artifact"]["revision_state"] = stored.control.state
    state["artifact"]["artifact_status"] = stored.payload.artifact_status
    state["final_confirmation"] = _final_confirmation(stored.payload.primary_blob, state)
    parsed = parse_canonical_artifact(stored.payload.primary_blob)
    require(parsed.front_matter.get("context") == state["context_reference"]
            and parsed.front_matter.get("profile") == state["profile"],
            "RLS_VFY_NOT_READY", "VFY Primary context/profile differs from State")
    _verify_supporting(stored, state)
    fixed = _verify_conclusions(state)
    requirement = _requirement_owner(store, root, state["scope"]["reference"])
    projection = LifecycleQueryService(root).inspect_requirement(requirement)
    _verify_current_subjects(state, projection)
    _verify_exceptions(store, root, state)
    _verify_applicability(store, root, state, projection)
    _verify_controls(state)
    resolutions = {row["control_reference"]: row for row in state["control_resolutions"] if row["status"] == "resolved"}
    unresolved_controls = sorted(set(state["control_inputs"]) - set(resolutions))
    resolver = ControlInputResolver(root)
    for authority in state["control_authorities"]:
        reference = authority["reference"]
        phase = authority.get("return_phase") or str(authority.get("follow_up_disposition", "")).removeprefix("return_").upper()
        observed = asdict(resolver.resolve_for_phase(store, reference, phase)); observed["authority_verified"] = True
        require(observed == authority, "RLS_VFY_NOT_READY", "VFY Control owner changed")
    exception = next((row for row in state["exceptions"] if row.get("accepts_product_failure") is True
                      and "product_result:fail" in row["scope"]), None)
    pending = [row["method_id"] for row in state["method_results"] if row["result"] == "pending"]
    pending += [row["target_reference"] for row in state["target_conclusions"] if row["conclusion"] == "pending"]
    pending += [row["id"] for row in state["fixed_conclusions"] if row["conclusion"] == "pending"]
    candidate = {
        "contract": "sdlc-ai-spec/vfy-release-candidate/v1", "provisional": False,
        "vfy_reference": exact, "revision_state": stored.control.state,
        "artifact_status": stored.payload.artifact_status, "artifact_gate": state["artifact_gate"],
        "early_stop": bool(state["early_stop"]), "pending_fields": pending,
        "scope_reference": state["scope"]["reference"],
        "subject_references": [row["reference"] for row in state["subjects"]],
        "result_references": [row["reference"] for row in state["subjects"]],
        "subject_current_valid": True, "imp_chain_current_valid": True,
        "con_ver": fixed["CON-VER"], "con_val": fixed["CON-VAL"], "product_result": state["product_result"],
        "unresolved_returns": [f"{exact}#{row['id']}" for row in state["returns"] if row["status"] != "resolved"] + unresolved_controls,
        "rls_applicability": state["rls_applicability"], "release_target_obligations": deepcopy(state["release_target_obligations"]),
        "evidence_references": [row["reference"] for row in state["evidence"]], "exception": deepcopy(exception),
        "exception_references": [row["origin_reference"] for row in state["exceptions"]],
        "source_digest": sha256_reference(state), "rls_ready": bool(state["rls_ready"]),
    }
    if expected_candidate is not None:
        require(candidate == expected_candidate, "RLS_VFY_NOT_READY", "Candidate transport differs from exact persisted producer state")
    scope_owner = _exact_authority(store, root, state["scope"]["reference"])
    work_items = tuple(sorted(state["scope"]["reference"] + "#" + row["ID"]
        for table in parse_canonical_artifact(scope_owner.payload.primary_blob).tables for row in table.rows
        if row.get("目标 Phase Target Phase") == "RLS"))
    result = adapt_vfy_payload(candidate, allow_provisional=False)
    return replace(result, interface_mode="FINAL_PERSISTED_VFY", authority_verified=True,
                   context_reference=state["context_reference"], profile=state["profile"], rls_work_item_references=work_items,
                   authority_exceptions=tuple(deepcopy(state["exceptions"])),
                   obligation_sources=_obligation_sources(state, exact, work_items),
                   input_references=tuple(sorted({exact, state["scope"]["reference"],
                       *(row["imp_revision_reference"] for row in state["subjects"])})))
