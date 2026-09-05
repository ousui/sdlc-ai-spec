"""Release Contract binding, coverage and effect-digest rules."""
from __future__ import annotations

from rls_common import require, sha256_value, stable_unique

# Outcome fields change only as a consequence of an authorized execution or
# confirmation. They are not part of the immutable pre-effect item contract.
_RLI_OUTCOME_FIELDS = {"result", "follow_up", "evidence_references", "exception_reference"}
_RCF_OUTCOME_FIELDS = {
    "result",
    "follow_up",
    "evidence_references",
    "observed",
    "exception_reference",
}


def release_item_contract(row: dict) -> dict:
    return {
        key: value
        for key, value in row.items()
        if key not in _RLI_OUTCOME_FIELDS
    }


def confirmation_contract(row: dict) -> dict:
    return {
        key: value
        for key, value in row.items()
        if key not in _RCF_OUTCOME_FIELDS
    }


def release_item_contracts(items: list[dict]) -> list[dict]:
    return [release_item_contract(row) for row in items]


def confirmation_contracts(confirmations: list[dict]) -> list[dict]:
    return [confirmation_contract(row) for row in confirmations]


def release_item_contract_digest(items: list[dict]) -> str:
    return sha256_value(release_item_contracts(items))


def confirmation_contract_digest(confirmations: list[dict]) -> str:
    return sha256_value(confirmation_contracts(confirmations))


def pre_execution_checklist(
    release_contract: dict,
    items: list[dict],
    confirmations: list[dict],
) -> dict:
    return {
        "release_reference": release_contract["release_reference"],
        "scope_reference": release_contract["scope_reference"],
        "result_references": list(release_contract["result_references"]),
        "vfy_reference": release_contract["vfy_reference"],
        "vfy_source_digest": release_contract.get("vfy_source_digest"),
        "vfy_candidate_digest": release_contract.get("vfy_candidate_digest"),
        "vfy_exception_references": list(
            release_contract.get("vfy_exception_references", [])
        ),
        "vfy_rls_ready": release_contract.get("vfy_rls_ready"),
        "release_target": release_contract["release_target"],
        "target_baseline": release_contract["target_baseline"],
        "release_contract_digest": sha256_value(release_contract),
        "rli_ids": [row["id"] for row in items],
        "rcf_ids": [row["id"] for row in confirmations],
        "release_item_contract_digest": release_item_contract_digest(items),
        "confirmation_contract_digest": confirmation_contract_digest(
            confirmations
        ),
        "checks": [
            "scope_result_exact",
            "vfy_ready",
            "vfy_source_digest_bound",
            "target_unique",
            "baseline_captured",
            "rls_work_items_covered",
            "release_target_obligations_covered",
            "authorization_required_before_effect",
        ],
    }


def effect_binding(
    artifact: dict,
    requested_rli_ids=None,
    *,
    require_pending: bool = False,
) -> dict:
    release_contract = artifact["release_contract"]
    ids = stable_unique(
        [row["id"] for row in artifact["release_items"]]
        if requested_rli_ids is None
        else requested_rli_ids
    )
    by_id = {row["id"]: row for row in artifact["release_items"]}
    require(
        ids and all(item_id in by_id for item_id in ids),
        "RLS_CONTRACT_INVALID",
        "authorization contains an unknown RLI",
    )
    if require_pending:
        require(
            all(by_id[item_id].get("result") == "pending" for item_id in ids),
            "RLS_EFFECT_AUTHORIZATION_STALE",
            "Effect Authorization can bind only pending RLI",
        )
    selected_rows = [release_item_contract(by_id[item_id]) for item_id in ids]
    return {
        "artifact_id": artifact["artifact"]["id"],
        "artifact_reference": artifact["artifact"]["reference"],
        "revision": artifact["artifact"]["revision"],
        "release_reference": release_contract["release_reference"],
        "scope_reference": release_contract["scope_reference"],
        "result_references": sorted(release_contract["result_references"]),
        "vfy_reference": release_contract["vfy_reference"],
        "vfy_source_digest": release_contract.get("vfy_source_digest"),
        "vfy_candidate_digest": release_contract.get("vfy_candidate_digest"),
        "release_target": release_contract["release_target"],
        "target_baseline": release_contract["target_baseline"],
        "target_baseline_digest": sha256_value(
            release_contract["target_baseline"]
        ),
        "release_contract_digest": sha256_value(release_contract),
        "rli_ids": ids,
        "action_summaries": [
            by_id[item_id]["action"] for item_id in ids
        ],
        "selected_rli_contract_digest": sha256_value(selected_rows),
        "release_item_set_digest": release_item_contract_digest(
            artifact["release_items"]
        ),
        "confirmation_set_digest": confirmation_contract_digest(
            artifact["confirmations"]
        ),
        "pre_execution_checklist_digest": artifact[
            "pre_execution_checklist_digest"
        ],
    }


def effect_digest(
    artifact: dict,
    requested_rli_ids=None,
    *,
    require_pending: bool = False,
) -> str:
    return sha256_value(
        effect_binding(
            artifact,
            requested_rli_ids,
            require_pending=require_pending,
        )
    )


def final_confirmation_binding(artifact: dict) -> dict:
    # Final Confirmation binds the terminal frozen identity.  Computing this
    # projection before the Store freeze and checking it after the freeze must
    # produce the same digest; otherwise a valid final record self-invalidates.
    terminal_artifact = dict(artifact["artifact"])
    terminal_artifact["revision_state"] = "frozen"
    return {
        "artifact": terminal_artifact,
        "release_contract": artifact["release_contract"],
        "release_items": artifact["release_items"],
        "confirmations": artifact["confirmations"],
        "effect_authorization": artifact.get("effect_authorization"),
        "effect_authorization_history": artifact.get(
            "effect_authorization_history", []
        ),
        "evidence": artifact["evidence"],
        "target_effect": artifact["target_effect"],
        "target_snapshot_before": artifact["target_snapshot_before"],
        "target_snapshot_after": artifact["target_snapshot_after"],
        "release_conclusion": artifact["release_conclusion"],
        "follow_up": artifact["follow_up"],
    }


def final_confirmation_digest(artifact: dict) -> str:
    return sha256_value(final_confirmation_binding(artifact))


def assert_contract_unchanged(old: dict, new: dict) -> None:
    require(
        effect_digest(old) == effect_digest(new),
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "Release Contract changed; prior result/authorization is stale",
    )


def assert_revision_change_allowed(old: dict, candidate, target: str) -> None:
    release_contract = old["release_contract"]
    require(
        candidate.scope_reference == release_contract["scope_reference"],
        "RLS_SCOPE_MISMATCH",
        "Scope change must return upstream",
    )
    require(
        len(candidate.result_references)
        == len(release_contract["result_references"])
        and set(candidate.result_references)
        == set(release_contract["result_references"]),
        "RLS_RESULT_MISMATCH",
        "Result Set change must return upstream",
    )
    require(
        target == release_contract["release_target"],
        "RLS_TARGET_AMBIGUOUS",
        "Target change requires a new RLS Artifact",
    )


def assert_no_effect_disposition(artifact: dict, applicability: str) -> None:
    if applicability in {"n/a", "waived"}:
        require(
            not artifact.get("target_effect")
            and artifact.get("target_snapshot_before")
            == artifact.get("target_snapshot_after"),
            "RLS_NOT_REQUIRED",
            "RLS cannot become n/a/waived after a target effect may have occurred",
        )


def validate_contract_coverage(artifact: dict) -> None:
    contract = artifact["release_contract"]
    item_sources = {
        ref
        for row in artifact["release_items"] + artifact["confirmations"]
        for ref in row["source_references"]
    }
    missing_work_items = sorted(
        set(contract.get("rls_work_item_references", [])) - item_sources
    )
    require(
        not missing_work_items,
        "RLS_WORK_ITEM_COVERAGE_INCOMPLETE",
        "RLS Work Item coverage is incomplete",
        missing=missing_work_items,
    )
    confirmations = artifact["confirmations"]
    for closure in contract.get("obligation_source_references", []):
        matching = [row for row in confirmations if closure["reference"] in row["source_references"]]
        require(matching and all(set(closure["source_references"]) <= set(row["source_references"]) for row in matching),
                "RLS_CONFIRMATION_CONTRACT_INCOMPLETE", "RCF must bind the exact carried Method, Target and Exception together")
    for obligation in contract.get("release_target_obligations", []):
        matching = [
            row
            for row in confirmations
            if obligation["reference"] in row["source_references"]
        ]
        require(
            matching,
            "RLS_CONFIRMATION_CONTRACT_INCOMPLETE",
            "VFY Release Target obligation has no RCF",
            obligation=obligation["reference"],
        )
        for row in matching:
            require(
                row["confirmation"] == obligation["confirmation"]
                and row["expected"] == obligation["expected"]
                and row["evidence_requirement"]
                == obligation["evidence_requirement"],
                "RLS_CONFIRMATION_CONTRACT_INCOMPLETE",
                "RCF narrowed or replaced the VFY obligation",
                obligation=obligation["reference"],
            )
            require(
                row.get("result") != "n/a",
                "RLS_CONFIRMATION_CONTRACT_INCOMPLETE",
                "a carried VFY Release Target obligation cannot become n/a in RLS",
                obligation=obligation["reference"],
            )
            if row.get("result") == "waived":
                require(
                    row.get("exception_reference"),
                    "RLS_CONFIRMATION_CONTRACT_INCOMPLETE",
                    "re-waived VFY obligation requires a current active RLS Exception",
                    obligation=obligation["reference"],
                )
