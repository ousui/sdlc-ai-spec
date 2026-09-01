# Skill Design Contract — `sdlc-status`

## 1. Metadata

| Field | Value |
|---|---|
| Skill Name | `sdlc-status` |
| Stage | `design` |
| Status | `approved` |
| Intended Plugin | `sdlc-ai-spec` |
| Foundation | `foundation/lifecycle-query@55411a55d69eec2a1d7349ae4b4ad4588b6b50ed` |
| Shared Interface | `sdlc-ai-spec/runtime/skill-interface/v1` |
| Shared Query | `packages/sdlc_lifecycle/` |
| Decision | User-delegated approval for this exact unattended target |

## 2. Problem and outcome

A project can contain multiple CTX/REQ artifacts and later a non-linear lifecycle graph. Users need one short, read-only command that answers where a requirement is, what blocks it, and what to do next without reading SQLite, Canonical Markdown, digests, or internal JSON.

Observable outcome:

```text
/sdlc-status
```

returns a concise project or exact-REQ status, and never modifies the project.

## 3. Single responsibility

In scope:

- read-only project overview;
- list exact REQ revisions;
- inspect one exact REQ revision;
- show graph, frontier, blockers and next actions;
- show whether the next Phase Skill is installed;
- common help/version/commands/examples and output modes.

Out of scope:

- creating, revising or checking Canonical Artifacts;
- selecting a symbolic latest/current authority;
- calling another business Skill;
- changing Gate, Open Item, Store or project files;
- automatically entering DSN or another phase.

## 4. Command contract

| Command | Purpose | Writes |
|---|---|---:|
| `auto` | Resolve the only deterministic status action | no |
| `list` | List exact REQ candidates and states | no |
| `inspect` | Inspect one exact `REQ-...@Revision` | no |
| `help` | Show usage and options | no |
| `version` | Show Skill and Interface versions | no |
| `commands` | List command surface | no |
| `examples` | Show copyable examples | no |

Bare invocation defaults to `auto`.

## 5. Auto resolution

| Observed state | Result |
|---|---|
| no Store | `not_started`; recommend `sdlc-000-ctx` if installed |
| CTX exists, no active REQ | `context_only` or `context_action_required` |
| exactly one active REQ | inspect it automatically |
| multiple active REQs | list candidates; user selects an exact reference |
| exact `--reference` supplied | inspect it |

`lineage_head` is list metadata only and never becomes Authority.

## 6. Interface and defaults

- supports all aliases defined by Shared Skill Interface;
- `project_root=auto` resolves to the unique current working directory supplied by the host;
- `decision_policy=user` by default;
- effective `write_policy=deny` for all commands, even when the common parser default is `auto`;
- `summary` is default; `json` and `debug` are available;
- unknown or conflicting arguments fail before project access.

## 7. Input contract

| Input | Required | Rule |
|---|---:|---|
| project root | auto | one existing absolute directory |
| command | auto | `auto/list/inspect` or meta command |
| reference | inspect only | exact base `REQ-...@<number>` |
| free text | optional | may help the Agent choose an exact candidate, never the Runtime by similarity |

## 8. Output contract

Machine result: `sdlc-ai-spec/status-result/v1`.

Required fields:

- command, status, project root;
- effective write policy;
- overview or projection;
- warnings/errors;
- one primary next action where possible;
- human summary unless `output=json`.

Projection state is not Canonical Artifact status or Authority.

## 9. Execution

1. parse common Skill arguments;
2. return meta command before any project access;
3. resolve project root;
4. force read-only policy;
5. use `LifecycleQueryService`;
6. auto/list/inspect;
7. render summary/json/debug;
8. stop without invoking any Phase Skill.

## 10. Side effects

Expected project writes: zero.

Forbidden:

- Store initialization;
- direct SQL;
- cache/log/temp files inside project;
- Git operations;
- sibling Skill calls;
- external API writes.

## 11. Failure behavior

- missing Store in `auto/list`: valid not-started/empty projection;
- missing Store in `inspect`: structured failure;
- invalid or symbolic reference: structured failure;
- corrupt Store or Artifact: blocked/failed with exact code;
- multiple requirements: action required, not arbitrary selection.

## 12. Runtime independence

Production Runtime uses only:

```text
skills/sdlc-status/**
skills/_shared/**
packages/sdlc_lifecycle/**
packages/sdlc_artifact_store/**
packages/sdlc_runtime/**
```

It does not read `docs/**`.

## 13. Compatibility

| Surface | Required state |
|---|---|
| Portable Python Runtime | Verified by tests |
| Codex static discovery/config | Partial until static adapter checks pass |
| Real Codex invocation | report actual evidence only |
| Cursor / Claude Code | Unknown unless executed |

## 14. Design DoD

- [x] single read-only responsibility;
- [x] unified interface and bare invocation;
- [x] exact-reference boundary;
- [x] deterministic auto matrix;
- [x] user selection for multiple REQs;
- [x] zero project writes;
- [x] shared foundation dependency fixed;
- [x] Runtime Independence defined;
- [x] Eval Oracle fixed;
- [x] blocking Open Items = 0.

## 15. Maintainer decision

The current user explicitly authorized unattended implementation and closure for this exact `sdlc-status` target. Approval is valid only while this Design and Eval Oracle are unchanged. Scope expansion or Oracle weakening invalidates the delegation.
