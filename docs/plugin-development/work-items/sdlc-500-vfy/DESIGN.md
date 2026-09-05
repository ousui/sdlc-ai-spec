# Skill Design Contract — `sdlc-500-vfy`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-500-vfy` |
| Stage | `design` |
| Status | `approved` |
| Intended Plugin | `sdlc-ai-spec` |
| Git Physical Base | `main@3a2f13082fe2f661081ded74e45f860da2046bd1` |
| Semantic IMP Subject | `207a4a16bea8979faee0474cc43cb642cef1f655` |
| IMP Delivery Checkpoint | `impl/imp-v2@86aaa04a0238d3151606073e89219eea0d60b7d3` |
| Design Branch | `design/sdlc-500-vfy-goal` |
| Maintainer Decision | Explicitly approved for design and initial implementation by the 2026-09-04 work order |
| Integration Mode | `TREE_EQUIVALENT` (`main` and `impl/imp-v2` tree `a5b0898738d749db9238f13f8bedb471a251ee6b`) |

### Authority

```text
docs/v1.1/500-vfy-spec.md
> bundled stable runtime contracts
> integrated IMP runtime
> IMP Handoff/Evidence
> this DESIGN.md / EVAL-PLAN.md
> goal implementation plan
```

The historical IMP Handoff fields describing `main@0c38135...`, PR #5, an
`impl/vfy-v2 → impl/imp-v2` PR, or the formal IMP SHA as the only physical
parent are historical closure facts. They are not the current Git ancestry instruction.

### Current Integration Binding

```text
Git physical base          = 3a2f13082fe2f661081ded74e45f860da2046bd1
Semantic IMP subject       = 207a4a16bea8979faee0474cc43cb642cef1f655
IMP delivery checkpoint    = 86aaa04a0238d3151606073e89219eea0d60b7d3
VFY implementation parent  = design/sdlc-500-vfy-goal@<DESIGN_HEAD_SHA>
VFY PR base                = main
```

Production runtime must not read `docs/**`. The bundled VFY contract,
interface, schema and source lock are the installed authority.

## 2. Problem and intended outcome

VFY is not a test runner. It must bind one complete Delivery Scope, an exact
current terminal IMP Subject Set, authoritative Targets and Method obligations;
execute or review applicable Methods; preserve immutable Evidence; aggregate
Method Result → Target Conclusion → `CON-VER`/`CON-VAL`; return confirmed gaps
to the owning upstream Phase; and independently decide whether the VFY Artifact
itself is trustworthy.

The user outcome is one explicit phase command that:

- resolves exact Scope, Target, Subject and Control Input references;
- creates the smallest sufficient Method Contract without inventing upstream decisions;
- executes only safe authorized automated work;
- requests real human Evidence for manual/hybrid Methods instead of fabricating it;
- records product pass/fail separately from Artifact Gate pass/fail;
- produces exactly one next action: remain in VFY, return to REQ/DSN/PLN/IMP,
  enter RLS, or complete when RLS is validly not applicable.

## 3. Scope

### In scope

- `auto`, `create`, `run`, `revise`, `check` and meta commands;
- repeatable `--input/-i`, repeatable `--method/-m`, exact `--reference/-r`;
- complete Delivery Scope and Current terminal IMP Subject Set resolution;
- authoritative Target Set, VFY Strategy and Work Item obligation mapping;
- `inspection`, `analysis`, `demonstration`, `test`;
- `automated`, `manual`, `hybrid` Execution Modes;
- Method Contract and Method Result;
- Target Conclusion and fixed `CON-VER`/`CON-VAL`;
- Evidence, Supporting Member, Secret rejection/redaction;
- product fail / Artifact Gate pass;
- Return to REQ/DSN/PLN/IMP and later Return resolution;
- failure-checkpoint early stop;
- frozen-subject Revision, no-change and abandoned reservation;
- Lifecycle Query and `sdlc-status` VFY/RLS-readiness projection.

### Out of scope

- product implementation or test-asset authoring;
- Requirement, Design, Plan or Release decisions;
- automatic upstream Skill execution or RLS execution;
- branch/tag/`latest`/`current`/PR number as Subject authority;
- dependency installation or network-based production Runtime behavior;
- GitHub Actions as validation or delivery authority;
- release, traffic, deployment or target-state mechanisms;
- copying ArtifactStore, Claim Provider, Resource Result, IMP Lifecycle or RLS.

## 4. Object and authority model

| Object | Authority and identity |
|---|---|
| IMP Artifact Reference | Exact frozen `IMP-...@N`; identifies canonical Artifact bytes |
| IMP Result Member Reference | Exact `IMP-...@N/RES-*`; identifies one immutable Result Member |
| Product Resource Result | Resource ID + baseline/result locator + digest + cumulative changed scope |
| Claim Record | Binding Lineage + Attempt + Owner + terminal `completed` state |
| Lifecycle Projection | Read-only derived next-action view; never a Subject |
| VFY Subject | Exact immutable Product Resource Result or registered immutable locator, bound to the current completed Claim and frozen IMP Revision |
| VFY Control Input | Exact frozen VFY Return or product-correction RLS Issue Revision |
| Evidence | Immutable observation bound to Method, Target, actual Subject, environment/data and time |

A branch, tag, symbolic `latest/current`, Draft PR, delivery branch SHA, or
Lifecycle projection is never Subject authority. The IMP implementation Subject
SHA is repository-delivery Evidence, not a replacement for product-level VFY
Subjects inside a user's Artifact Store.

## 5. Command contract

| Command | Writes | Deterministic behavior |
|---|---:|---|
| `auto` | conditional | no VFY → create; one open pending VFY → run; frozen stale/control change → revise; frozen unchanged → check |
| `create` | yes | resolve one complete Scope, persist pre-execution Contract, execute safe ready Methods, finalize only when legal |
| `run` | yes | execute only selected or all ready pending Methods in the materialized open Revision |
| `revise` | yes | create a new Revision only for a new current Subject or valid Control Input; otherwise `NO_CHANGE` |
| `check` | no | open Store read-only, verify exact Reference, digests, current validity, aggregation, Return and Gate |
| `help/version/commands/examples` | no | no project scan, Store open, network, or write |

```text
--input / -i <exact reference>      repeatable; stable first-occurrence order
--method / -m <VFM-NNN>             repeatable; run only
--reference / -r <VFY-...@N>        exact numeric Revision only
```

Unknown options, missing values, conflicting command/arguments and non-exact
references fail closed.

## 6. Scope, Subject and Target resolution

1. Resolve exactly one full PLN Delivery Scope when PLN is `required`; otherwise
   use the nearest complete REQ/DSN Scope plus its valid disposition/Exception.
2. Expand every `Target Phase=IMP` Work Item; resolve exactly one matching
   Current `completed` Claim, frozen IMP Revision and dependency-complete Result.
3. Build every planned Resource's terminal Product Resource Result. Cumulative
   change is measured from initial baseline through the terminal Result, not only
   the final Attempt delta.
4. Revalidate the entire Subject Set at VFY start, before each execution, and
   immediately before freeze.
5. Reject unresolved, active, abandoned, non-frozen, stale, discontinuous or
   movable Subjects.
6. Use all VFOs when a VFY Objective Set exists. Otherwise, only when DSN is
   validly `n/a`/`waived`, use ACs as verification Targets and Goal intended
   outcomes/success conditions as validation Targets.
7. Never create Targets or Pass Criteria inside VFY to repair upstream gaps.

## 7. Method Contract and execution

A Method has stable `VFM-NNN`, Purpose, exact Target References, exact Subject
References, Obligation References, Method Type, Disposition, Executor Identity,
Execution Mode, environment/data Contract, procedure/basis, Pass Criteria and
Evidence Requirement.

Method Type is exactly one of:

```text
inspection | analysis | demonstration | test
```

Execution Mode is exactly one of:

```text
automated | manual | hybrid
```

Before an execution with external effects or formal Evidence, the complete
pre-execution checklist is persisted and read back. The executor:

- verifies the actual Subject immediately before and after the operation;
- never installs a dependency and never gains undeclared permission;
- captures command, cwd, bounded duration/timeout, exit code and immutable output;
- redacts known Secret values and rejects content that cannot be safely redacted;
- marks missing environment/data/person input as `required` + `pending`, never `n/a`;
- accepts manual/hybrid completion only with a structured real observation,
  evaluator identity, scenario, scope, time and attachment/reference digest.

## 8. Result and conclusion rules

Aggregation is deterministic:

```text
fail > pending > waived > pass > n/a
```

- every Method has one current Result row;
- every Target has one Conclusion per applicable dimension;
- `both` requires both verification and validation Evidence;
- `CON-VER` and `CON-VAL` aggregate only their compatible dimension;
- waived proof never becomes pass;
- an accurate product `fail` may coexist with Artifact Gate `pass`;
- Artifact `ready` means the record is trustworthy, not that the product passed.

## 9. Return and recovery

`RET-NNN` names exactly one Return Phase: REQ, DSN, PLN or IMP. It records exact
Targets, Methods, Subjects, observed gap, required outcome and Evidence.
`return_imp` additionally records the exact current IMP Binding Lineage and
Attempt/Revision/Result relationship. Multiple Phases or Lineages require
separate Returns.

Receiving a Return or producing a new completed IMP Result does not resolve it.
A later frozen VFY Revision resolves it only when it:

- includes the frozen Return/RLS Issue Revision as Control Input;
- cites the Item in Method Obligation References;
- uses the new current terminal Subject;
- provides Method Result, Target Conclusion and Evidence proving the required outcome.

## 10. State, Revision and early stop

- no complete Scope: no VFY allocation;
- complete Scope but missing Contract/human/environment input: open `waiting_input`;
- executor or Artifact Contract failure: open `failed`;
- normal terminal product pass/fail with complete Gate and confirmation: frozen;
- failure-checkpoint early stop: frozen credible failure record, pending remainder,
  precise Returns, permanently not RLS-ready;
- new current Subject or valid Control Input after freeze: new Revision;
- unchanged revise request: `NO_CHANGE`;
- first write/build failure: abandon the reservation;
- `check` is byte-for-byte read-only.

Early stop is legal only when at least one immutable supported fail cannot be
invalidated or reattributed by the unexecuted facts. Pending required Methods
remain pending and every one cites the stopping fail and Return.

## 11. Artifact and module architecture

```text
skills/sdlc-500-vfy/
├── SKILL.md
├── agents/openai.yaml
├── assets/vfy-template.md
├── references/
│   ├── 500-vfy-spec.md
│   ├── contract.md
│   ├── interface.json
│   └── source-lock.json
└── scripts/
    ├── vfy_common.py
    ├── vfy_scope.py
    ├── vfy_subject.py
    ├── vfy_targets.py
    ├── vfy_methods.py
    ├── vfy_executor.py
    ├── vfy_results.py
    ├── vfy_conclusions.py
    ├── vfy_returns.py
    ├── vfy_builder.py
    ├── vfy_verifier.py
    ├── vfy_handler.py
    └── runtime.py
```

Shared additive integration:

```text
packages/sdlc_lifecycle/query_vfy.py
skills/sdlc-status VFY projection
tests/skill_vfy/**
tests/evals/run_sdlc_500_vfy_eval.py
tests/evals/sdlc_500_vfy_cases.json
tools/validate_sdlc_500_vfy_source_lock.py
tools/test_sdlc_500_vfy_runtime_independence.py
tools/run_external_vfy_integration.py
tools/run_vfy_delivery_validation.py
```

ArtifactStore remains the only canonical Artifact persistence authority. VFY
stores a canonical Markdown primary plus a canonical `VFY-STATE` JSON Supporting
Member and Evidence Supporting Members. It never issues SQL.

## 12. Gate and lifecycle

`VFY-G-001` through `VFY-G-008` implement the stable Spec unchanged. The Domain
Verifier recomputes them; persisted claimed Gate values are not trusted.

| VFY condition | Next action |
|---|---|
| absent / open / pending | VFY |
| frozen product fail or unresolved Return | exact REQ/DSN/PLN/IMP Return Phase |
| frozen early-stop | exact Return Phase; never RLS |
| frozen product pass or accepted scoped Exception, RLS required | RLS |
| same, RLS validly n/a/waived | lifecycle complete |
| Artifact Gate fail | repair VFY record, not product pass/fail |

## 13. Stable failures

```text
VFY_SCOPE_REQUIRED
VFY_SCOPE_AMBIGUOUS
VFY_SUBJECT_NOT_CURRENT
VFY_DEPENDENCY_CHAIN_INVALID
VFY_TARGET_SET_INVALID
VFY_METHOD_COVERAGE_INCOMPLETE
VFY_METHOD_NOT_READY
VFY_METHOD_EXECUTION_FAILED
VFY_EVIDENCE_INSUFFICIENT
VFY_PURPOSE_MISMATCH
VFY_CONCLUSION_INCONSISTENT
VFY_RETURN_INVALID
VFY_EARLY_STOP_INVALID
VFY_FINAL_CONFIRMATION_STALE
VFY_RLS_NOT_ALLOWED
VFY_REFERENCE_REQUIRED
VFY_NO_CHANGE
VFY_STORE_CONFLICT
```

## 14. Source lock and Runtime Independence

The source lock pins exact bundled Runtime Contract bytes and records design
source Git blob identities. A validator rejects missing, extra, duplicate,
unsorted or digest-drifted entries. Installed Runtime performs no read under
`docs/**`; deleting docs/tests/Handoff must leave meta/create/run/revise/check,
verification, Return and Lifecycle Query operational.

## 15. Design corrections in this Revision

1. Replaced historical `main@0c38135...` with the dynamic Current Integration Binding.
2. Separated repository IMP implementation Subject, delivery checkpoint and integrated main.
3. Added explicit Product Resource Result / Claim / Artifact / Subject distinctions.
4. Added Subject-currentness checks at start, execution and freeze.
5. Added deterministic state machine, early-stop and unresolved-Return RLS prohibition.
6. Added machine-readable Evidence/delivery schemas and one local validation authority.
7. Removed GitHub Actions from PASS authority.
8. Added exact 80/80 Case-to-module/test/Evidence/Gate traceability.
9. Added a two-commit implementation/Evidence convergence Contract for local `/goal`.
10. Kept all stable Spec requirements; none were weakened.

## 16. Definition of Done

- this Design and Eval Plan are internally complete and 80/80 Cases are mapped;
- initial implementation is a child of the Design Head;
- local validation remains explicitly required until exact-SHA execution;
- no RLS, Workflow or Evidence branch is created;
- only a local `/goal` may declare `VFY_CLOSED_LOOP = PASS` after fresh exact-SHA
  attestation and formal Evidence generation.
