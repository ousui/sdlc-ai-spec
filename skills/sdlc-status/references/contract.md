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

## Error codes

- `PROJECT_ROOT_INVALID`
- `LIFECYCLE_STORE_UNAVAILABLE`
- `LIFECYCLE_REFERENCE_INVALID`
- `LIFECYCLE_ARTIFACT_INVALID`
- shared Skill argument errors

Missing Store is a normal `not_started` state for auto/list, but a failure for inspect.
