# sdlc-status Runtime Contract

## Result

Machine contract:

```text
sdlc-ai-spec/status-result/v1
```

Required fields:

```text
contract
ok
command
status
project_root
effective_write_policy
state
overview
projection
warnings
errors
next_action
```

`overview` and `projection` use `sdlc-ai-spec/lifecycle-status/v1` objects from `packages/sdlc_lifecycle`.

## Command semantics

### auto

- no `.sdlc/store.sqlite3`: `not_started`;
- CTX but no active REQ: project overview;
- exactly one active REQ: inspect it;
- multiple active REQs: `selection_required` list;
- explicit accurate REQ reference: inspect it.

### list

Lists all materialized REQ revisions. `lineage_head` is informational only and never an Authority alias.

### inspect

Requires exact base `REQ-...@<number>`. Item/member references and symbolic revisions fail.

## Read-only guarantee

All query commands force `effective_write_policy=deny`. Meta commands return before project-root resolution. No command initializes Store, writes files, invokes sibling Skills, performs Git actions or sends external writes.

## Output

- summary hides digests, SQLite and Manifest details;
- json emits one JSON document;
- debug includes normalized arguments and raw Projection but not Secret material.
- IMP summary displays exact Binding, Owner, Attempt, Claim State, materialization,
  Outcome, Resource Baseline/Result, Changed Scope, current completion and VFY readiness.
- `projection.current_claims` contains only Current Claim projections; historical
  Artifact nodes are not current completion evidence.
- `projection.vfy_inputs` contains only exact current completed terminal IMP inputs.
  VFY readiness does not imply VFY execution, acceptance, or Skill availability.
- `projection.vfy_results` selects one exact terminal Result per Resource, including
  when different Resources have terminal Results in different IMP revisions.
- `projection.vfy_projection` separates the frozen VFY Product Result, Artifact Gate,
  unresolved Return, RLS applicability and RLS readiness. Product failure never
  becomes an Artifact authority failure and never authorizes RLS by itself.
- Multiple next actions remain visible in the summary. The top-level `next_action`
  asks for selection instead of silently selecting the first candidate.
- An unavailable next Skill has `skill_available=false` and no executable command.

## Error codes

- `PROJECT_ROOT_INVALID`
- `LIFECYCLE_STORE_UNAVAILABLE`
- `LIFECYCLE_REFERENCE_INVALID`
- `LIFECYCLE_ARTIFACT_INVALID`
- shared Skill argument errors

Missing Store is a normal `not_started` state for auto/list, but a failure for inspect.
