# Effect Authorization Contract

## Non-substitutability

Effect Authorization cannot be replaced by `write_policy`, workspace access,
GitHub permission, Final Confirmation, Approval/Trigger Reference, earlier
similar consent or agent judgement. It is a separate expiring execution object.

## Exact binding

The canonical authorization payload binds:

```text
contract, authorization_id,
rls_artifact_id, revision, release_reference,
scope_reference, sorted result_references,
vfy_reference, release_target, target_baseline_digest,
ordered rli_ids, ordered action_summaries,
pre_execution_checklist_digest,
authorizer_identity, authorized_at, valid_until,
effect_digest
```

`effect_digest` is SHA-256 over the canonical contract tuple excluding the
identity/time envelope. Any tuple change makes an old authorization stale.
Authorization permits exactly the ordered RLI set, not a subset/superset or an
attached action. Secrets and credentials are never fields and are rejected or
redacted before Artifact persistence.

## Operation rules

- `create`: no target authorization; local Artifact write only.
- `execute`: verify exact current contract, unexpired identity envelope and item set
  immediately before effect; rejection means target bytes remain identical.
- `confirm`: read-only target observation is allowed by project read access; any
  confirmation mutation requires another exact effect authorization.
- `cancel`: legal only when before/after target snapshot proves no effect.
- `retry`: new Revision, Baseline, checklist and Authorization.

The provisional executor recognizes only a local Fake/Sandbox target. Production
adapters, credentials and external effects are intentionally absent.
