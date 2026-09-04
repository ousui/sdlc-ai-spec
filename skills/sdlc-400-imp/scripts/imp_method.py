"""Validate the fixed consideration catalog and continuous semantic Method."""
from __future__ import annotations

from copy import deepcopy
import re

from packages.sdlc_phasekit import refs, rows
from imp_common import CONSIDERATIONS, canonical, require, reject_secrets

BLOCKS = {
    "Calculation Rules": ("CAL", ("output", "expression", "inputs_and_units", "precision_and_rounding", "boundary_and_invalid_values")),
    "Decision Rules": ("DEC", ("rules",)),
    "State Transitions": ("STA", ("transitions",)),
    "Algorithm & Invariants": ("ALG", ("inputs", "outputs", "invariants", "scale_or_limits", "pseudocode")),
    "Data Contract & Transformation": ("MAP", ("mappings",)),
    "Boundary & Failure Handling": ("ERR", ("trigger", "classification", "handling", "observable_result", "recovery")),
    "Effects & Consistency": ("EFF", ("resource_or_effect", "order_and_condition", "consistency_or_atomicity", "idempotency", "failure_handling")),
}
BLOCK_TABLES = {
    "Decision Rules": ("id", "priority", "conditions", "outcome"),
    "State Transitions": ("id", "current", "event", "next", "effect", "illegal_handling"),
    "Data Contract & Transformation": ("source", "target", "transformation", "validation", "null_or_default"),
}
EXCEPTION_FIELDS = {
    "scope": "作用域或被跳过义务 Scope or Skipped Obligation", "reason": "原因 Reason",
    "known_risk": "已知风险 Known Risk", "compensating_control": "补偿措施 Compensating Control",
    "approval": "批准记录 Approver, Role and Time", "revisit_condition": "复查条件 Revisit Condition",
    "downstream_obligation": "下游限制 Downstream Obligation",
    "resolution_references": "解决或替代引用 Resolution or Superseding References",
}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_method(candidate, binding):
    require(isinstance(candidate, dict), "IMP_READINESS_FAILED",
            "Provide an Implementation Method before acquiring a Claim", status="action_required")
    value = deepcopy(candidate)
    reject_secrets(value)
    missing = value.get("missing_decision")
    actions = {"requirement": "RETURN_TO_REQUIREMENT", "design": "RETURN_TO_DESIGN", "plan": "RETURN_TO_PLAN"}
    require(missing is None, "IMP_UPSTREAM_DECISION_REQUIRED", "An upstream decision is missing",
            action=actions.get(missing, "RETURN_TO_DESIGN"), status="action_required")
    if any(value.get(key) for key in ("new_public_abstraction", "new_dependency", "cross_module_interface")):
        decisions = refs(value.get("design_decision_references"), "design_decision_references")
        require(decisions and set(decisions).issubset(binding.design_decisions),
                "IMP_UPSTREAM_DECISION_REQUIRED", "This implementation needs an exact approved DSN Decision",
                action="RETURN_TO_DESIGN", status="action_required")
    exceptions = rows(value.get("exceptions"), "exceptions")
    origins = set()
    for upstream in binding.exceptions:
        record = upstream["record"]
        origin = record.get("Origin Exception Reference")
        origin = upstream["reference"] if origin in {None, "", "N/A"} else origin
        if origin in origins:
            continue
        origins.add(origin)
        carried = {key: record[header] for key, header in EXCEPTION_FIELDS.items()}
        carried.update(state="carried", origin_reference=origin)
        existing = [item for item in exceptions if item.get("origin_reference") == origin]
        if existing:
            require(len(existing) == 1 and all(existing[0].get(key) == content for key, content in carried.items()),
                    "IMP_READINESS_FAILED", "Carried Exception cannot drop or alter its upstream obligation")
        else:
            used = {item.get("id") for item in exceptions}
            identity = next(f"EX-{index:03d}" for index in range(1, len(used) + 2)
                            if f"EX-{index:03d}" not in used)
            exceptions.append({"id": identity, **carried})
    exception_ids = set()
    for exception in exceptions:
        required = ("id", "scope", "reason", "known_risk", "compensating_control",
                    "approval", "revisit_condition", "downstream_obligation")
        require(all(_text(exception.get(key)) and exception[key] != "N/A" for key in required),
                "IMP_READINESS_FAILED", "Exception requires scope, risk, control and explicit approval")
        require(exception.get("state") in {"active", "carried"} and re.fullmatch(r"EX-[0-9]{3}", exception["id"]),
                "IMP_READINESS_FAILED", "Invalid active Exception")
        require(exception["id"] not in exception_ids, "IMP_READINESS_FAILED", "Duplicate Exception ID")
        exception_ids.add(exception["id"])
    matrix = rows(value.get("considerations"), "considerations")
    require(tuple(item.get("name") for item in matrix) == CONSIDERATIONS,
            "IMP_READINESS_FAILED", "Implementation Considerations must use the fixed seven names and order")
    steps = rows(value.get("steps"), "steps")
    require(steps, "IMP_READINESS_FAILED", "At least one semantic Implementation Step is required")
    step_ids, orders, block_ids = set(), set(), set()
    for step in steps:
        step_id, order = step.get("id"), step.get("order")
        require(isinstance(step_id, str) and re.fullmatch(r"STEP-[0-9]{3}", step_id)
                and step_id not in step_ids, "IMP_READINESS_FAILED", "Step ID must be unique and stable")
        require(isinstance(order, int) and not isinstance(order, bool) and order > 0 and order not in orders,
                "IMP_READINESS_FAILED", "Step Order must be a unique positive integer")
        step_ids.add(step_id)
        orders.add(order)
        for field in ("purpose", "expected_result", "transaction_boundary", "failure_boundary"):
            require(_text(step.get(field)), "IMP_READINESS_FAILED", f"Step requires one {field}")
        require(step.get("split_by", "semantics") == "semantics", "IMP_UPSTREAM_DECISION_REQUIRED",
                "Steps must describe semantic actions instead of file decomposition", action="RETURN_TO_PLAN")
        require(step.get("transaction_boundaries") is None and step.get("failure_boundaries") is None,
                "IMP_READINESS_FAILED", "Split Steps at different transaction or failure boundaries")
        targets = refs(step.get("target"), "Step Target", required=True)
        require(set(targets).issubset(binding.execution_scope), "IMP_SCOPE_VIOLATION",
                "Step Target is outside Claim Scope")
        basis = refs(step.get("basis_references"), "Step Basis", required=True)
        require(set(basis).issubset(binding.basis_references), "IMP_UPSTREAM_DECISION_REQUIRED",
                "Step Basis must resolve in the exact upstream chain", action="RETURN_TO_DESIGN")
        considerations = refs(step.get("considerations"), "Step Considerations")
        require(tuple(item for item in CONSIDERATIONS if item in considerations) == considerations,
                "IMP_READINESS_FAILED", "Step Considerations must follow Catalog order")
        logic = step.get("logic")
        require(isinstance(logic, list) and logic and all(_text(item) for item in logic),
                "IMP_READINESS_FAILED", "Step implementation logic is required")
        for block in rows(step.get("blocks"), "Method Blocks"):
            name, block_id = block.get("consideration"), block.get("id")
            require(name in considerations, "IMP_READINESS_FAILED", "Method Block must map to its Step")
            prefix, fields = BLOCKS[name]
            require(isinstance(block_id, str) and re.fullmatch(prefix + r"-[0-9]{3}", block_id)
                    and block_id not in block_ids, "IMP_READINESS_FAILED", "Method Block ID is invalid or duplicated")
            block_ids.add(block_id)
            require(all(block.get(field) for field in fields), "IMP_READINESS_FAILED", "Method Block fields are incomplete")
            if name in BLOCK_TABLES:
                table = rows(block[fields[0]], fields[0])
                require(table and all(all(str(row.get(key, "")).strip() for key in BLOCK_TABLES[name]) for row in table),
                        "IMP_READINESS_FAILED", "Fixed Method Block table is incomplete")
                if name == "Decision Rules":
                    require(sum(row["conditions"] == "DEFAULT" for row in table) == 1,
                            "IMP_READINESS_FAILED", "Decision Rules require an explicit DEFAULT")
            else:
                require(all(_text(block[field]) for field in fields), "IMP_READINESS_FAILED",
                        "Method Block fields must be text")
    by_id = {item["id"]: item for item in steps}
    for item in matrix:
        name, disposition = item["name"], item.get("disposition")
        require(disposition in {"pending", "required", "n/a", "waived"}, "IMP_READINESS_FAILED",
                "Invalid Consideration Disposition")
        require(_text(item.get("basis")), "IMP_READINESS_FAILED", "Each Consideration needs an objective basis")
        targets = refs(item.get("steps"), "Consideration Steps")
        require(set(targets).issubset(step_ids), "IMP_READINESS_FAILED", "Consideration names an unknown Step")
        if disposition == "required":
            require(targets, "IMP_READINESS_FAILED", "Required Consideration has no Step")
            require(all(name in by_id[target].get("considerations", []) for target in targets),
                    "IMP_READINESS_FAILED", "Consideration and Step coverage disagree")
            require(any(block.get("consideration") == name for target in targets
                        for block in by_id[target].get("blocks", [])),
                    "IMP_READINESS_FAILED", "Required Consideration has no corresponding Method Block")
        elif disposition == "waived":
            require(item.get("exception") in exception_ids, "IMP_READINESS_FAILED",
                    "Waived Consideration requires an approved Exception")
        elif disposition == "pending":
            require(False, "IMP_READINESS_FAILED", "Pending Consideration cannot acquire or pass Gate",
                    status="action_required", action="RETURN_TO_DESIGN")
        if disposition != "required":
            require(not targets and not any(name in step.get("considerations", []) for step in steps),
                    "IMP_READINESS_FAILED", "Non-required Consideration must not contain Method Steps")
    value["steps"] = sorted(steps, key=lambda item: item["order"])
    value["considerations"], value["exceptions"] = matrix, exceptions
    return value


def validate_stable_identities(previous, current):
    """Prevent a later Revision from removing or repurposing an identity.

    The compact runtime has no separate tombstone or supersession table.  It
    therefore keeps every identity that has already appeared in this IMP
    Artifact while still allowing a later Revision to append new Steps,
    Method Blocks, or Checks. Mutable implementation detail and expected
    values may evolve, but an existing ID cannot move to another semantic
    target or logical role.
    """

    def block_role(step_id, block):
        name = block.get("consideration")
        role = {"step": step_id, "consideration": name}
        if name == "Calculation Rules":
            role["output"] = block.get("output")
        elif name == "Decision Rules":
            role["rule_ids"] = [row.get("id") for row in block.get("rules", [])]
        elif name == "State Transitions":
            role["transition_ids"] = [row.get("id") for row in block.get("transitions", [])]
        elif name == "Algorithm & Invariants":
            role.update(inputs=block.get("inputs"), outputs=block.get("outputs"))
        elif name == "Data Contract & Transformation":
            role["mapping_targets"] = [
                (row.get("source"), row.get("target"))
                for row in block.get("mappings", [])
            ]
        elif name == "Boundary & Failure Handling":
            role.update(trigger=block.get("trigger"), classification=block.get("classification"))
        elif name == "Effects & Consistency":
            role["resource_or_effect"] = block.get("resource_or_effect")
        return role

    def check_role(item):
        command = item.get("command")
        # A project-command's complete bounded argv is its logical role.  In
        # particular, ``npm run test`` and ``npm run lint`` are different
        # Checks even though their first two tokens are identical.
        entrypoint = list(command) if isinstance(command, list) else None
        return {
            "name": item.get("name"),
            "kind": item.get("kind"),
            "resource": item.get("resource"),
            "path": item.get("path"),
            "cwd": item.get("cwd"),
            "entrypoint": entrypoint,
        }

    def identities(method):
        steps = method.get("steps", [])
        return {
            "Step": {
                item.get("id"): {
                    "purpose": item.get("purpose"),
                    "target": item.get("target"),
                    "considerations": item.get("considerations"),
                }
                for item in steps if isinstance(item, dict)
            },
            "Method Block": {
                block.get("id"): block_role(step.get("id"), block)
                for step in steps if isinstance(step, dict)
                for block in step.get("blocks", []) if isinstance(block, dict)
            },
            "Check": {
                item.get("id"): check_role(item)
                for item in method.get("checks", [])
                if isinstance(item, dict)
            },
        }

    before, after = identities(previous), identities(current)
    for kind in before:
        missing = sorted(identity for identity in before[kind] if identity not in after[kind])
        require(not missing, "IMP_BINDING_MISMATCH",
                f"{kind} IDs must remain stable across IMP Revisions",
                details={"missing_ids": missing})
        repurposed = sorted(
            identity for identity, definition in before[kind].items()
            if identity in after[kind]
            and canonical(definition) != canonical(after[kind][identity])
        )
        require(not repurposed, "IMP_BINDING_MISMATCH",
                f"{kind} IDs cannot be assigned to new semantics",
                details={"repurposed_ids": repurposed})
