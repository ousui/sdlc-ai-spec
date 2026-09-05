# VFY Private Runtime Contract — v1

## Authority compiler

Persistent `auto/create/revise` compiles one Candidate from repeatable exact input References. Caller JSON is a hint only. The compiler opens ArtifactStore read-only, uses Frozen Artifact Authority, Lifecycle Query and Current Claim readback, and requires exact equality with:

- one complete REQ/DSN/PLN Scope Source;
- the complete current terminal IMP Product Result Set;
- all authoritative VFOs, or the legal AC/Goal fallback;
- every current VFY Return/RLS Issue through ControlInputResolver;
- every active/carried scoped Exception through its frozen owner Artifact.

Branches, tags, PRs, symbolic latest/current values and lifecycle routing names are never product Subject authority.

Scope fallback and RLS applicability are read from frozen upstream lifecycle tables. VFO Purpose, observable outcome and VFP mapping are compiled from the frozen owner. The required obligation set also includes upstream Method, Pass Criteria, Evidence Contract and applicable PLN VFY Work Items; caller hints cannot omit or replace them.

## Canonical Artifact

The primary Markdown is the human-readable canonical authority and implements the fixed v1.1 VIN, Target, Method, Method Detail, Method Result, fixed Conclusion and Return contracts. Every Item Reference owner Revision appears in Front Matter `inputs`. `VFY-STATE` is a machine Supporting Member, not an alternate authority. The Domain Verifier parses the primary and proves exact primary/state/manifest agreement before freeze.

## Execution and Evidence

Automated commands require the persisted `deterministic-test-v1` positive policy, run in an isolated workspace copy, use no shell or inline arbitrary code, have no network or dependency acquisition, and enforce timeout/output budgets. The source workspace and exact Subject are re-read before and after execution.

Command containment requires an available OS sandbox: macOS `sandbox-exec`, or Linux `bwrap` with working namespaces. It denies network access and writes outside the isolated copy, including effects of subprocesses. Proxy variables are not isolation evidence. Missing or unavailable containment is `VFY_METHOD_NOT_READY`, never an unsandboxed fallback; no sandbox dependency is installed by the Runtime. Escaping source symlinks are rejected before copying.

Manual/hybrid Evidence requires the exact contracted evaluator identity, scenario, expected result, scope, RFC 3339 observation time and immutable source `reference@sha256` object. Evidence is bound to Method, Target, Subject, result, environment, executor, time and Evidence Requirement. Secrets are rejected before persistence.

## Return, Control and Exception

A Return is always created open. Caller input cannot mark it resolved. Resolution is derived only when a later current VFY Revision carries the exact frozen Return/RLS Issue as Control Input, maps it to a Method obligation, uses the changed current Subject Set and records passing Method/Target/Evidence for the required outcome. Every failed Method not accepted by a scoped active Exception has an exact Return.

Waiver and `rls_applicability=waived` require a verified active/carried Exception whose scope covers the affected Method/Target/phase. Valid Exception closure produces `ready_with_exception/pass_with_exception`; downstream projection consumes those states without treating them as unqualified product pass.

## Persistence and read-only behavior

All persistence uses the shared ArtifactStore public API. The VFY Runtime creates no private Store and executes no SQL. Production `check` requires one exact persisted VFY Revision, opens the Store read-only, recomputes canonical/domain/currentness checks and preserves Store plus tracked/untracked product bytes.

## Delivery validation

The authoritative controller runs Skill Interface validation, Source Lock, 80 Case coverage, focused VFY tests, full repository regression, installed-copy Runtime Independence, both fixed external projects and Fresh exact-SHA Attestation. A prewritten review file is not itself an independent review result.
