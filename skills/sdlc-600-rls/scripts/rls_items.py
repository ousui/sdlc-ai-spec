"""Release Item and target-side Confirmation normalization."""
from __future__ import annotations

from rls_common import exact_reference, require, stable_unique

RLI_RESULTS = {"pending", "success", "partial", "fail", "cancelled", "waived"}
RCF_RESULTS = {"pending", "pass", "fail", "not_run", "n/a", "waived"}
FOLLOWUPS = {"none", "retry_rls", "return_req", "return_dsn", "return_pln", "return_imp"}


def normalize_requested_ids(values, kind: str) -> tuple[list[str], list[str]]:
    prefix = "RLI" if kind == "rli" else "RCF"
    output: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item_id = exact_reference(raw, prefix)
        if item_id in seen:
            warnings.append(f"duplicate {item_id} ignored")
            continue
        seen.add(item_id)
        output.append(item_id)
    return output, warnings


def normalize_items(rows, kind: str) -> list[dict]:
    prefix = "RLI" if kind == "rli" else "RCF"
    allowed = RLI_RESULTS if kind == "rli" else RCF_RESULTS
    require(isinstance(rows, list), "RLS_CONTRACT_INVALID", f"{prefix} rows must be an array")
    output: list[dict] = []
    seen: set[str] = set()
    for raw in rows:
        require(isinstance(raw, dict), "RLS_CONTRACT_INVALID", f"{prefix} row must be an object")
        row = dict(raw)
        item_id = exact_reference(row.get("id", ""), prefix)
        require(item_id not in seen, "RLS_CONTRACT_INVALID", "duplicate item id", item=item_id)
        seen.add(item_id)
        result = row.get("result", "pending")
        require(result in allowed, "RLS_CONTRACT_INVALID", "invalid item result", item=item_id)
        follow_up = row.get("follow_up", "none")
        require(follow_up in FOLLOWUPS, "RLS_FOLLOW_UP_INVALID", "invalid follow-up", item=item_id)
        source_refs = stable_unique(row.get("source_references", []))
        require(source_refs, "RLS_WORK_ITEM_COVERAGE_INCOMPLETE", "item source references required", item=item_id)
        row.update(
            id=item_id,
            result=result,
            follow_up=follow_up,
            source_references=source_refs,
            evidence_references=stable_unique(row.get("evidence_references", [])),
        )
        if prefix == "RLI":
            require(
                isinstance(row.get("action"), str) and row["action"].strip(),
                "RLS_CONTRACT_INVALID",
                "one independently judgeable RLI action is required",
                item=item_id,
            )
            require(
                int(row.get("independent_result_count", 1)) == 1,
                "RLS_CONTRACT_INVALID",
                "one RLI cannot cover multiple independently judgeable results",
                item=item_id,
            )
            row.setdefault("prerequisite", "None")
            row.setdefault("prerequisite_satisfied", True)
            row.setdefault("executor", "sandbox-executor")
        else:
            for field in ("confirmation", "expected", "evidence_requirement"):
                require(
                    isinstance(row.get(field), str) and row[field].strip(),
                    "RLS_CONFIRMATION_CONTRACT_INCOMPLETE",
                    f"{field} is required",
                    item=item_id,
                )
            row.setdefault("executor", "sandbox-observer")
            row.setdefault("observed", None)
            row.setdefault("subjective", False)
            row.setdefault("objective_na_reason", None)
        output.append(row)
    require(output, "RLS_CONTRACT_INVALID", f"{prefix} set cannot be empty")
    return output


def default_items(candidate) -> tuple[list[dict], list[dict]]:
    release_items = [
        {
            "id": "RLI-001",
            "action": "apply exact verified Result Set",
            "source_references": [*candidate.result_references, *candidate.rls_work_item_references],
            "prerequisite": "exact baseline and current Effect Authorization",
            "prerequisite_satisfied": True,
            "executor": "sandbox-executor",
            "result": "pending",
            "follow_up": "none",
            "evidence_references": [],
        }
    ]
    obligations = list(candidate.release_target_obligations) or [
        {
            "reference": candidate.vfy_reference,
            "confirmation": "Observe the authorized local Sandbox release",
            "expected": "The target version equals the bound release reference",
            "evidence_requirement": "Immutable target-side snapshot after the selected RLI",
        }
    ]
    confirmations: list[dict] = []
    for index, obligation in enumerate(obligations, start=1):
        confirmations.append(
            {
                "id": f"RCF-{index:03d}",
                "source_references": next((list(row["source_references"]) for row in candidate.obligation_sources if row["reference"] == obligation["reference"]), [obligation["reference"]]),
                "confirmation": obligation["confirmation"],
                "expected": obligation["expected"],
                "executor": "sandbox-observer",
                "evidence_requirement": obligation["evidence_requirement"],
                "observed": None,
                "result": "pending",
                "follow_up": "none",
                "evidence_references": [],
            }
        )
    return normalize_items(release_items, "rli"), normalize_items(confirmations, "rcf")
