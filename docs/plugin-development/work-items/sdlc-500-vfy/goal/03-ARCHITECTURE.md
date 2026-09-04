# VFY Runtime Architecture

## Principles

- stable v1.1 semantics are bundled and executable without `docs/**`;
- ArtifactStore is the only canonical Artifact authority;
- IMP Claim/Resource/Lifecycle state is consumed through public projections;
- pure domain modules are deterministic and side-effect-free;
- executor effects are isolated, bounded and explicitly authorized;
- CLI, persistence, verification and lifecycle projection remain separable.

## Module map

| Module | Responsibility | Must not own |
|---|---|---|
| `vfy_common.py` | value objects, exact references, canonical JSON, stable errors, secret policy | Store, subprocess orchestration |
| `vfy_scope.py` | one full Delivery Scope and obligation-set normalization | target invention |
| `vfy_subject.py` | immutable subject parsing, current-chain validation and stale diff | Claim mutation |
| `vfy_targets.py` | VFO or valid AC/Goal target derivation, stable dedupe/order | pass criteria invention |
| `vfy_methods.py` | Method Contract normalization and coverage checks | actual execution |
| `vfy_executor.py` | bounded authorized automated execution and structured manual/hybrid intake | installation, network authority |
| `vfy_results.py` | Method Result/evidence validation and state replacement | target aggregation |
| `vfy_conclusions.py` | purpose-aware Target and `CON-VER`/`CON-VAL` aggregation | Artifact Gate |
| `vfy_returns.py` | Return attribution, IMP lineage binding and resolution proof | upstream execution |
| `vfy_builder.py` | canonical Markdown/state/member payload and ArtifactStore calls | SQL |
| `vfy_verifier.py` | recomputed VFY-G-001..008, early-stop/freeze eligibility | stored claims of PASS |
| `vfy_handler.py` | auto/create/run/revise/check transaction choreography | CLI formatting |
| `runtime.py` | shared argument parser, invocation/result rendering | domain implementation |

## Canonical payload

The primary Markdown follows `assets/vfy-template.md`. The `VFY-STATE` canonical
JSON Supporting Member is the executable state. Evidence is stored as
`VFY-EVD-*` members with media type, raw bytes and SHA-256. The manifest is the
closure authority.

The state member includes:

```text
context, scope_source, inputs, subjects, targets, methods,
method_results, target_conclusions, conclusions,
returns, open_items, evidence, exceptions,
lifecycle_applicability, final_confirmation,
artifact_gate, early_stop, revision_reason
```

## Persistence sequence

### create

1. resolve and validate complete scope/subjects/targets/methods in memory;
2. allocate VFY Artifact and Revision;
3. write canonical pre-execution payload;
4. read back and compare binding digest;
5. run only ready authorized methods;
6. write results/evidence using generation CAS;
7. re-read, revalidate current Subjects and recompute Gate;
8. freeze only when Domain Verifier approves;
9. abandon an unmaterialized/failed-first-write reservation.

### run

Read exact open revision, assert expected generation, select stable pending
methods, execute each independently, merge current results without loss, write
once per deterministic checkpoint, then attempt legal finalization.

### revise

Read a frozen exact revision, resolve current inputs. Create a new revision only
when normalized Subject/Control/Scope binding differs; otherwise return
`VFY_NO_CHANGE` without allocation.

### check

Open `ArtifactStore.open_read_only`, read exact revision and Supporting Members,
recompute digest/domain/currentness/lifecycle projection, and emit no writes.

## Executor boundary

Automated command methods use an argv array, validated cwd under project root,
sanitized deterministic environment, timeout, maximum output budget and no
shell. An allowlist is provided by the persisted Method Contract; runtime never
discovers and executes arbitrary repository text.

Manual/hybrid methods return `action_required` until a structured observation
is explicitly provided. Final confirmation cannot substitute for human product
Evidence.

## Lifecycle integration

`packages/sdlc_lifecycle/query_vfy.py` is additive and pure. It receives a
normalized VFY projection and returns:

```text
phase, state, product_result, artifact_gate,
early_stop, unresolved_returns, rls_ready,
next_phase, next_action, basis
```

`sdlc-status` formats this projection and never changes product conclusions.

## Runtime independence and source lock

`references/500-vfy-spec.md`, `contract.md`, `interface.json` and schemas are
bundled. Runtime modules contain no `docs/` path. Source-lock validation checks
exact sorted entries and bundled SHA-256. The independence tool copies only
installed runtime/package paths to a temporary directory, removes docs/tests,
and executes meta plus deterministic fixture create/run/revise/check.

## Security

- secret-like input is rejected before persistence;
- executor output is redacted against explicit values and common credential
  patterns; unverifiable residue fails the Method;
- cwd/path traversal, `.git`, `.sdlc`, absolute uncontrolled paths and shell
  metacharacter interpretation are rejected;
- no dependency installation, remote write, release or RLS execution;
- external integration restores repository and runtime-control state.
