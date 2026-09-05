"""Authorized Release Item executor."""
from __future__ import annotations

from rls_authorization import validate_authorization
from rls_common import deep_copy, require, RlsError
import uuid
from rls_items import normalize_requested_ids


def execute_items(
    artifact: dict,
    target,
    item_ids,
    authorization,
    *,
    behaviors: dict[str, str] | None = None,
    now: str | None = None,
    trusted_records=None,
    journal=None,
    persist=None,
) -> dict:
    ids, warnings = normalize_requested_ids(item_ids, "rli")
    require(ids, "RLS_CONTRACT_INVALID", "at least one RLI must be selected")
    require(
        getattr(target, "target_id", None)
        == artifact["release_contract"]["release_target"],
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "execution target does not match the Release Contract",
    )
    # Authorization is validated before the target is observed or mutated.
    if not artifact.get("provisional", True):
        require(trusted_records is not None and journal is not None and persist is not None,
                "RLS_EFFECT_AUTHORIZATION_REQUIRED", "final execution requires trusted host grant, journal and CAS persistence")
        require(now is None, "RLS_EFFECT_AUTHORIZATION_STALE", "business input cannot override execution time")
        journal.require_resolved()
        trusted_records.verify(artifact, authorization)
    validate_authorization(artifact, authorization, ids, now=now)
    by_id = {row["id"]: row for row in artifact["release_items"]}
    require(
        all(item_id in by_id for item_id in ids),
        "RLS_CONTRACT_INVALID",
        "unknown RLI",
    )
    require(
        all(by_id[item_id]["result"] == "pending" for item_id in ids),
        "RLS_EXECUTION_FAILED",
        "every selected RLI must be pending",
    )

    require(all(by_id[item_id].get("prerequisite_satisfied") is True for item_id in ids),
            "RLS_EXECUTION_FAILED", "selected Release Item prerequisite is not satisfied")
    require(all(value in {"no-op", "success", "partial", "failure"} for value in (behaviors or {}).values()),
            "RLS_EXECUTION_FAILED", "unsupported Sandbox behavior")
    # Bind the authorization to the target state that actually exists immediately
    # before effect. After an earlier RLS item, the prior RLS snapshot—not the
    # original release baseline—is the expected current state.
    before_all = target.assert_expected_state(
        artifact["release_contract"]["target_baseline"],
        artifact.get("target_snapshot_after"),
    )

    if trusted_records is not None:
        trusted_records.consume(artifact, authorization, ids)
    authorization_record = deep_copy(authorization)
    artifact["effect_authorization"] = authorization_record
    artifact.setdefault("effect_authorization_history", []).append(
        deep_copy(authorization_record)
    )

    artifact["target_snapshot_before"] = artifact.get("target_snapshot_before") or before_all
    for item_id in ids:
        item = by_id[item_id]
        attempt = uuid.uuid4().hex
        try:
            if journal is not None:
                journal.append("intent", deep_copy(artifact), item=item_id, attempt=attempt)
            artifact["effect_uncertain"] = True
            if persist is not None:
                persist(artifact)
            if trusted_records is not None:
                from rls_common import parse_time, utc_now
                require(parse_time(authorization["authorized_at"]) <= parse_time(utc_now()) <= parse_time(authorization["valid_until"]),
                        "RLS_EFFECT_AUTHORIZATION_STALE", "grant expired before selected item execution")
            result, effect, evidence_item, _before, after = target.execute(
                dict(item, artifact_reference=artifact["artifact"]["reference"]),
                artifact["release_contract"]["release_reference"],
                (behaviors or {}).get(item_id, "success"))
            item["result"] = result
            item["evidence_references"] = [evidence_item["reference"]]
            if result in {"partial", "fail"} and item.get("follow_up") == "none":
                item["follow_up"] = "retry_rls"
            artifact["evidence"].append(evidence_item)
            artifact["target_effect"] = bool(artifact.get("target_effect") or effect)
            artifact["target_snapshot_after"] = after
            artifact["effect_uncertain"] = False
            if journal is not None:
                journal.append("observed", deep_copy(artifact), item=item_id, attempt=attempt)
            if persist is not None:
                persist(artifact)
            if journal is not None:
                journal.append("persisted", deep_copy(artifact), item=item_id, attempt=attempt)
        except Exception:
            artifact["effect_uncertain"] = True
            try:
                snapshot = target.snapshot()
                artifact["target_effect"] = bool(artifact.get("target_effect") or snapshot != before_all)
                artifact["target_snapshot_after"] = snapshot
            except Exception:
                pass
            if journal is not None:
                try:
                    journal.append("uncertain", deep_copy(artifact), item=item_id, attempt=attempt)
                except Exception:
                    pass  # The durable pre-effect intent already prevents replay.
            raise RlsError("RLS_EXECUTION_UNCERTAIN", "execution or persistence failed; retained effects require explicit recovery") from None
    artifact["status"] = "waiting_confirmation"
    artifact["warnings"].extend(warnings)
    return artifact
