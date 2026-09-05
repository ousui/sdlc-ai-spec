"""Independent exact-binding Effect Authorization."""
from __future__ import annotations

from datetime import timedelta
import uuid

from rls_common import assert_no_secret, parse_time, require, utc_now
from rls_contract import effect_binding, effect_digest


_BINDING_TO_AUTHORIZATION = {
    "artifact_id": "rls_artifact_id",
    "artifact_reference": "rls_artifact_reference",
    "revision": "revision",
    "release_reference": "release_reference",
    "scope_reference": "scope_reference",
    "result_references": "result_references",
    "vfy_reference": "vfy_reference",
    "vfy_source_digest": "vfy_source_digest",
    "vfy_candidate_digest": "vfy_candidate_digest",
    "release_target": "release_target",
    "target_baseline_digest": "target_baseline_digest",
    "release_contract_digest": "release_contract_digest",
    "rli_ids": "rli_ids",
    "action_summaries": "action_summaries",
    "selected_rli_contract_digest": "selected_rli_contract_digest",
    "release_item_set_digest": "release_item_set_digest",
    "confirmation_set_digest": "confirmation_set_digest",
    "pre_execution_checklist_digest": "pre_execution_checklist_digest",
}


def issue_authorization(
    artifact: dict,
    rli_ids,
    authorizer_identity: str,
    *,
    authorized_at: str | None = None,
    valid_until: str | None = None,
) -> dict:
    require(
        isinstance(authorizer_identity, str) and authorizer_identity.strip(),
        "RLS_EFFECT_AUTHORIZATION_REQUIRED",
        "authorizer identity is required",
    )
    require(
        artifact["artifact"]["revision_state"] == "open",
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "authorization can only bind an open RLS Revision",
    )
    authorized_at = authorized_at or utc_now()
    authorized_time = parse_time(authorized_at)
    if valid_until is None:
        valid_until = (
            authorized_time + timedelta(minutes=15)
        ).isoformat().replace("+00:00", "Z")
    require(
        parse_time(valid_until) > authorized_time,
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "authorization validity must end after authorized_at",
    )

    binding = effect_binding(artifact, rli_ids, require_pending=True)
    authorization = {
        "contract": "sdlc-ai-spec/effect-authorization/v1",
        "authorization_id": "EA-" + uuid.uuid4().hex[:16],
        **{
            authorization_key: binding[binding_key]
            for binding_key, authorization_key in _BINDING_TO_AUTHORIZATION.items()
        },
        "authorizer_identity": authorizer_identity.strip(),
        "authorized_at": authorized_at,
        "valid_until": valid_until,
        "effect_digest": effect_digest(artifact, rli_ids),
    }
    assert_no_secret(authorization)
    return authorization


def authorization_binding_diff(
    artifact: dict,
    authorization: dict,
    requested_rli_ids,
) -> list[str]:
    expected = effect_binding(
        artifact,
        requested_rli_ids,
        require_pending=False,
    )
    differences = [
        authorization_key
        for binding_key, authorization_key in _BINDING_TO_AUTHORIZATION.items()
        if authorization.get(authorization_key) != expected[binding_key]
    ]
    if authorization.get("effect_digest") != effect_digest(
        artifact,
        requested_rli_ids,
        require_pending=False,
    ):
        differences.append("effect_digest")
    return differences


def validate_authorization(
    artifact: dict,
    authorization: dict | None,
    requested_rli_ids,
    *,
    now: str | None = None,
) -> bool:
    require(
        isinstance(authorization, dict),
        "RLS_EFFECT_AUTHORIZATION_REQUIRED",
        "Effect Authorization is required before any target effect",
    )
    require(
        authorization.get("contract") == "sdlc-ai-spec/effect-authorization/v1",
        "RLS_EFFECT_AUTHORIZATION_REQUIRED",
        "invalid Effect Authorization contract",
    )
    # Reuse for a terminal item is forbidden, but historical audit verification
    # may compare the immutable contract projection after execution.
    effect_binding(artifact, requested_rli_ids, require_pending=True)
    differences = authorization_binding_diff(
        artifact, authorization, requested_rli_ids
    )
    require(
        not differences,
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "Effect Authorization no longer matches the current contract",
        changed_fields=differences,
    )
    current = parse_time(now or utc_now())
    require(
        parse_time(authorization.get("authorized_at", ""))
        <= current
        <= parse_time(authorization.get("valid_until", "")),
        "RLS_EFFECT_AUTHORIZATION_STALE",
        "Effect Authorization is expired or not yet valid",
    )
    assert_no_secret(authorization)
    return True
