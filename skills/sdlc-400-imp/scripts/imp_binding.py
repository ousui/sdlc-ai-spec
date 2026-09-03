"""Read-only resolution of exact IMP Bindings and their real CTX relationship."""
from __future__ import annotations

import json
import re

from packages.sdlc_artifact_store.catalog import ArtifactCatalog
from packages.sdlc_claim_provider import binding_lineage
from packages.sdlc_phasekit import refs
from packages.sdlc_runtime import FrozenArtifactAuthorityVerifier, parse_canonical_artifact
from packages.sdlc_runtime.canonical import find_tables, parse_markdown_tables, require_single_table

from imp_common import (
    APPLICABILITY_HEADERS, Binding, CHANGE_HEADERS, EXACT_BINDING, ImpError,
    WORK_HEADERS, base_ref, exact_base, require, validate_scope,
)

DECISION_HEADERS = (
    "ID", "Requirement or Constraint References", "决策问题 Decision Question",
    "候选方案 Options", "选择结果 Decision", "选择依据 Rationale", "影响 Domain Affected Domains",
)
GOAL_HEADERS = (
    "ID", "当前问题 Current Problem", "目标结果与预期用途 Goal, Intended Outcome and Use",
    "成功条件 Success Condition",
)
AC_HEADERS = ("ID", "关联需求 Requirement References", "条件 Condition", "预期结果 Expected Result")
DEPENDENCY_HEADERS = (
    "ID", "依赖项 Dependency", "要求状态 Required State", "当前状态 Current State",
    "状态检查引用 State Check Reference",
)


def read_authority(store, reference):
    exact_base(reference)
    stored = store.resolve_exact_reference(
        reference, verifier=FrozenArtifactAuthorityVerifier(store.project_root),
    ).revision
    return stored, parse_canonical_artifact(stored.payload.primary_blob)


def _context(store, stored, parsed):
    context = parsed.front_matter.get("context")
    require(isinstance(context, str), "IMP_BINDING_MISMATCH",
            "Upstream Artifact has no unique Context relationship")
    exact_base(context, "CTX")
    manifest = json.loads(stored.payload.manifest.raw_bytes)
    related = []
    for name in ("context", "context_reference"):
        if name in manifest:
            related.append(manifest[name])
    for item in manifest.get("relationships", []):
        require(isinstance(item, dict), "IMP_BINDING_MISMATCH", "Invalid Manifest relationship")
        if str(item.get("role", item.get("type", ""))).lower() == "context":
            related.append(item.get("reference", item.get("target")))
    require(not related or (len(related) == 1 and related[0] == context),
            "IMP_BINDING_MISMATCH", "Upstream Context and Manifest relationships disagree or are ambiguous")
    read_authority(store, context)
    return context


def _applicability(parsed, phase):
    tables = find_tables(parsed, APPLICABILITY_HEADERS)
    matches = [row for table in tables for row in table.rows if row["Phase"] == phase]
    # PLN renders the same aggregate twice. They must describe identical authority.
    unique = {(row["Phase"], row["Disposition"], row["Host"]) for row in matches}
    require(len(unique) == 1, "IMP_READINESS_FAILED",
            f"Upstream {phase} applicability is absent or inconsistent", action="RETURN_TO_PLAN")
    return matches[0]


def _lineage(store, reference, context):
    visited, active, lineage, basis, decisions, exceptions = set(), set(), [], [], [], []

    def walk(current):
        require(current not in active, "IMP_BINDING_MISMATCH", "Upstream Input cycle")
        if current in visited:
            return
        active.add(current)
        stored, parsed = read_authority(store, current)
        require(_context(store, stored, parsed) == context, "IMP_BINDING_MISMATCH",
                "Upstream Artifacts do not share the exact Context")
        lineage.append(current)
        basis.append(current)
        for table in parsed.tables:
            for row in table.rows:
                item = row.get("ID") or row.get("Change ID")
                require(row.get("状态 State") != "open", "IMP_READINESS_FAILED",
                        "Upstream has an unresolved Open Item", action="RETURN_TO_PLAN")
                if table.headers == DEPENDENCY_HEADERS and item != "None":
                    check_reference = row["状态检查引用 State Check Reference"]
                    require(not check_reference.startswith("IMP-"), "IMP_DEPENDENCY_INCOMPLETE",
                            "IMP Result dependencies require an explicit PLN Work Item chain", action="RETURN_TO_PLAN")
                    try:
                        dependency, _ = read_authority(store, check_reference)
                    except Exception as exc:
                        raise ImpError("IMP_DEPENDENCY_INCOMPLETE",
                                       "Dependency State Check is not an exact readable immutable source",
                                       action="RETURN_TO_PLAN") from exc
                    require(row["要求状态 Required State"] in
                            {dependency.control.state, dependency.payload.artifact_status},
                            "IMP_DEPENDENCY_INCOMPLETE",
                            "Dependency Required State is not established by the current exact source",
                            action="RETURN_TO_PLAN")
                    basis.append(check_reference)
                if item and re.fullmatch(r"[A-Z]+-[0-9]{3}", item):
                    basis.append(f"{current}#{item}")
                if table.headers == DECISION_HEADERS:
                    if row["ID"] == "None":
                        require(len(table.rows) == 1 and row["决策问题 Decision Question"] not in {"", "N/A", "pending"}
                                and all(row[key] == "N/A" for key in DECISION_HEADERS
                                        if key not in {"ID", "决策问题 Decision Question"}),
                                "IMP_UPSTREAM_DECISION_REQUIRED", "DSN has no justified no-decision record",
                                action="RETURN_TO_DESIGN")
                        continue
                    require(row["选择结果 Decision"] not in {"", "N/A", "pending"},
                            "IMP_UPSTREAM_DECISION_REQUIRED", "DSN Decision is incomplete",
                            action="RETURN_TO_DESIGN")
                    decisions.append(f"{current}#{row['ID']}")
                if row.get("State") in {"active", "carried"} and item and item.startswith("EX-"):
                    exceptions.append({"reference": f"{current}#{item}", "record": dict(row)})
        for member in stored.payload.members:
            basis.append(f"{current}/{member.member_id}")
            if member.media_type == "text/markdown":
                for table in parse_markdown_tables(member.raw_bytes.decode("utf-8")):
                    for row in table.rows:
                        item = row.get("ID")
                        if item and re.fullmatch(r"[A-Z]+-[0-9]{3}", item):
                            basis.extend((f"{current}#{item}", f"{current}/{member.member_id}#{item}"))
        for item in refs(parsed.front_matter.get("inputs"), "upstream inputs"):
            upstream = base_ref(item)
            exact_base(upstream)
            if upstream.startswith(("REQ-", "DSN-", "PLN-")):
                walk(upstream)
        active.remove(current)
        visited.add(current)

    walk(reference)
    lineage.append(context)
    basis.append(context)
    return tuple(lineage), tuple(dict.fromkeys(basis)), tuple(decisions), tuple(exceptions)


def _lifecycle(parsed, exceptions):
    vfy, release = _applicability(parsed, "VFY"), _applicability(parsed, "RLS")
    require(vfy["Disposition"] == "required", "IMP_READINESS_FAILED",
            "VFY is a required downstream control point", action="RETURN_TO_PLAN")
    require(release["Disposition"] in {"required", "n/a", "waived"}, "IMP_READINESS_FAILED",
            "Resolve pending RLS applicability in the authoritative input before implementation",
            status="action_required", action="RETURN_TO_PLAN")
    if release["Disposition"] == "waived":
        require(any("RLS" in item["record"].get("作用域或被跳过义务 Scope or Skipped Obligation", "")
                    and item["record"].get("批准记录 Approver, Role and Time") not in {None, "", "N/A"}
                    for item in exceptions),
                "IMP_READINESS_FAILED", "RLS waiver lacks an approved upstream Exception",
                action="RETURN_TO_PLAN")
    return tuple({"phase": row["Phase"], "disposition": row["Disposition"],
                  "host": row["Host"], "basis": row["判断依据 Basis"]} for row in (vfy, release))


def _plan_binding(store, reference, parsed):
    plan, wi_id = reference.split("#")
    rows = require_single_table(parsed, WORK_HEADERS, "PLN Work Items").rows
    identifiers = [row["ID"] for row in rows]
    require(len(set(identifiers)) == len(identifiers), "IMP_BINDING_AMBIGUOUS",
            "PLN contains duplicate Work Item identities", status="action_required")
    selected = [row for row in rows if row["ID"] == wi_id]
    require(len(selected) == 1, "IMP_BINDING_MISMATCH", "Exact Work Item does not exist",
            action="RETURN_TO_PLAN")
    row = selected[0]
    require(row["目标 Phase Target Phase"] == "IMP", "IMP_BINDING_MISMATCH",
            "Work Item Target Phase must be IMP", action="RETURN_TO_PLAN")
    dispositions = [
        item["Value"] for table in parsed.tables for item in table.rows
        if item.get("Field") == "PLN Disposition"
    ]
    require(dispositions == ["required"], "IMP_READINESS_FAILED",
            "PLN Binding requires PLN Disposition=required", action="RETURN_TO_PLAN")
    require(_applicability(parsed, "IMP")["Disposition"] == "required",
            "IMP_READINESS_FAILED", "Upstream IMP must be required", action="RETURN_TO_PLAN")
    by_id = {item["ID"]: item for item in rows}
    seen = set()

    def visit(item_id, stack):
        require(item_id in by_id and item_id not in stack, "IMP_DEPENDENCY_INCOMPLETE",
                "PLN Dependency is missing or cyclic", action="RETURN_TO_PLAN")
        if item_id in seen:
            return
        require(by_id[item_id]["目标 Phase Target Phase"] == "IMP", "IMP_DEPENDENCY_INCOMPLETE",
                "IMP cannot depend on a later Phase Work Item", action="RETURN_TO_PLAN")
        for parent in refs(by_id[item_id]["依赖 Depends On"], "Depends On"):
            require(re.fullmatch(r"WI-[0-9]{3}", parent), "IMP_DEPENDENCY_INCOMPLETE",
                    "Depends On must name an exact Work Item in the bound Plan")
            visit(parent, {*stack, item_id})
        seen.add(item_id)

    visit(wi_id, set())
    dependencies = tuple(f"{plan}#{item}" for item in refs(row["依赖 Depends On"], "Depends On"))
    return (
        validate_scope(row["执行范围 Execution Scope"]), dependencies,
        row["结果 Outcome"], row["完成条件 Completion Criteria"],
        row["预期证据 Expected Evidence"],
        refs(row["来源引用 Source References"], "WI Sources", required=True)
        + refs(row["约束引用 Constraint References"], "WI Constraints"),
    )


def _direct_binding(reference, parsed, exceptions):
    disposition = _applicability(parsed, "PLN")["Disposition"]
    require(disposition in {"n/a", "waived"}, "IMP_READINESS_FAILED",
            "Direct Binding requires authoritative PLN n/a or waived", action="RETURN_TO_PLAN")
    require(_applicability(parsed, "IMP")["Disposition"] == "required",
            "IMP_READINESS_FAILED", "Direct Binding requires IMP=required", action="RETURN_TO_PLAN")
    if disposition == "waived":
        require(any("PLN" in str(item["record"]) and item["record"].get("批准记录 Approver, Role and Time") not in
                    {None, "", "N/A"} for item in exceptions),
                "IMP_READINESS_FAILED", "PLN waiver requires an approved upstream Exception",
                action="RETURN_TO_PLAN")
    if reference.startswith("REQ-"):
        dsn = _applicability(parsed, "DSN")["Disposition"]
        require(dsn in {"n/a", "waived"},
                "IMP_UPSTREAM_DECISION_REQUIRED", "REQ Direct Binding requires DSN n/a or waived",
                action="RETURN_TO_DESIGN")
        if dsn == "waived":
            require(any("DSN" in item["record"].get("作用域或被跳过义务 Scope or Skipped Obligation", "")
                        and item["record"].get("批准记录 Approver, Role and Time") not in {None, "", "N/A"}
                        for item in exceptions),
                    "IMP_UPSTREAM_DECISION_REQUIRED", "REQ DSN waiver requires an approved upstream Exception",
                    action="RETURN_TO_DESIGN")
        scopes = re.findall(r"(?m)^- Direct IMP Scope: (.+)$", parsed.text)
        require(len(scopes) == 1, "IMP_READINESS_FAILED",
                "REQ requires exactly one authoritative Direct IMP Scope", action="RETURN_TO_PLAN")
        scope = validate_scope(scopes[0])
        require(sum(item.startswith("resource:") for item in scope) == 1, "IMP_READINESS_FAILED",
                "REQ Direct Scope must contain exactly one Resource", action="RETURN_TO_PLAN")
        goals = require_single_table(parsed, GOAL_HEADERS, "REQ Goals").rows
        criteria = require_single_table(parsed, AC_HEADERS, "REQ Acceptance Criteria").rows
        require(len(goals) == 1 and criteria, "IMP_READINESS_FAILED",
                "Direct REQ must have one complete atomic Goal and Acceptance Criteria", action="RETURN_TO_PLAN")
        return scope, (), goals[0][GOAL_HEADERS[2]], goals[0][GOAL_HEADERS[3]], "; ".join(
            row["预期结果 Expected Result"] for row in criteria), ()
    changes = require_single_table(parsed, CHANGE_HEADERS, "DSN Change Items").rows
    require(len(changes) == 1, "IMP_READINESS_FAILED",
            "Multiple DSN outcomes require PLN coordination", action="RETURN_TO_PLAN")
    change = changes[0]
    vfy = [row for table in parsed.tables for row in table.rows
           if str(row.get("ID", "")).startswith(("VFP-", "OBJ-"))]
    if not vfy:
        vfy = [row for table in parsed.tables for row in table.rows
               if row.get("VFY Point or Objective References") not in {None, "", "None", "N/A"}]
    require(vfy, "IMP_READINESS_FAILED", "Direct DSN requires an equivalent VFY completion basis",
            action="RETURN_TO_DESIGN")
    return (validate_scope(change["Object or Boundary"]), (), change["Change"],
            change["Target State"], "DSN VFY Points: " + "; ".join(str(row) for row in vfy),
            (f"{reference}#{change['Change ID']}",))


def resolve_binding(store, reference):
    require(isinstance(reference, str) and EXACT_BINDING.fullmatch(reference),
            "IMP_BINDING_MISMATCH", "Binding requires exact PLN@Revision#WI or complete REQ/DSN@Revision",
            status="action_required")
    upstream = base_ref(reference)
    stored, parsed = read_authority(store, upstream)
    context = _context(store, stored, parsed)
    lineage, basis, decisions, exceptions = _lineage(store, upstream, context)
    if reference.startswith("PLN-"):
        scope, dependencies, outcome, criteria, evidence, wi_basis = _plan_binding(store, reference, parsed)
        require(set(wi_basis).issubset(basis), "IMP_READINESS_FAILED",
                "WI Sources or Constraints do not resolve through the exact upstream Input chain",
                action="RETURN_TO_PLAN")
    else:
        scope, dependencies, outcome, criteria, evidence, wi_basis = _direct_binding(reference, parsed, exceptions)
    require(all(isinstance(value, str) and value.strip() not in {"", "N/A", "None", "pending"}
                for value in (outcome, criteria, evidence)),
            "IMP_READINESS_FAILED", "Outcome, Completion Criteria and Expected Evidence must be complete",
            action="RETURN_TO_PLAN")
    return Binding(
        reference, binding_lineage(reference), upstream, context,
        upstream if reference.startswith("PLN-") else None,
        reference.split("#", 1)[1] if reference.startswith("PLN-") else None,
        lineage, scope, dependencies, outcome, criteria, evidence,
        tuple(dict.fromkeys((reference, *basis, *wi_basis))), decisions,
        _lifecycle(parsed, exceptions), exceptions,
    )


def discover_binding(store):
    """Enumerate exact candidates; recency and branch names never select a Binding."""
    catalog = ArtifactCatalog(store)
    candidates = []
    for phase in ("PLN", "DSN", "REQ"):
        for artifact in catalog.list_artifacts(phase):
            for control in catalog.list_revisions(artifact.artifact_id):
                if control.state != "frozen":
                    continue
                reference = f"{control.artifact_id}@{control.revision}"
                _, parsed = read_authority(store, reference)
                if phase == "PLN":
                    table = require_single_table(parsed, WORK_HEADERS, "PLN Work Items")
                    candidates.extend(f"{reference}#{row['ID']}" for row in table.rows
                                      if row["目标 Phase Target Phase"] == "IMP")
                elif _applicability(parsed, "PLN")["Disposition"] in {"n/a", "waived"}:
                    candidates.append(reference)
    candidates = sorted(set(candidates))
    require(len(candidates) == 1,
            "IMP_BINDING_AMBIGUOUS" if candidates else "IMP_BINDING_REQUIRED",
            "Select one exact IMP Binding" if candidates else "No executable exact IMP Binding",
            status="action_required", details={"candidates": candidates})
    return resolve_binding(store, candidates[0])
