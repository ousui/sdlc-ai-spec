# VFY Design Review

## Review baseline

- Base main: `3a2f13082fe2f661081ded74e45f860da2046bd1` / tree `a5b0898738d749db9238f13f8bedb471a251ee6b`
- IMP implementation subject: `207a4a16bea8979faee0474cc43cb642cef1f655`
- IMP delivery: `86aaa04a0238d3151606073e89219eea0d60b7d3` / tree `a5b0898738d749db9238f13f8bedb471a251ee6b`
- Integration mode: `TREE_EQUIVALENT`
- Original VFY Design blob: `f50194e1371a724715d7cc7f8de7d177c971cc7a`
- Original Eval Plan blob: `761f33b3d00a95a190f16c89ad9d7b6cad6844dd`
- Stable VFY Spec blob: `270e1291e450a129d842833b996a75c57d45b58e`

## Findings

### Blocker — closed in this design

**B-01 Historical physical ancestry was no longer valid.** The original Design
named `main@0c38135...`; the IMP Handoff also instructed the next phase to use
the IMP implementation SHA as the sole parent. Current `main` already contains
the integrated IMP Runtime and Evidence and has the same tree as the IMP
delivery branch. Continuing the historical parent rule would fork from the
current integrated repository and replay obsolete history.

**Closure:** `00-BASELINE.json`, `02-IMP-VFY-INTERFACE.md` and `11-DESIGN-HANDOFF.md`
define the Current Integration Binding: physical base=current main, semantic
IMP subject=`207a4a16bea8979faee0474cc43cb642cef1f655`, implementation parent=design head, PR base=main.

### Major — closed in this design

**M-01 Repository SHA and product Subject were conflated.** The prior design did
not explicitly separate the IMP implementation commit, delivery head, integrated
main, IMP Artifact, Result Member and Product Resource Result.

**Closure:** the interface contract defines all six identities and forbids
branch/tag/current/latest/PR numbers as Subject authority.

**M-02 Current validity and stale-result recovery were underspecified.**

**Closure:** Subject validity is rechecked at create/run/freeze/check; a new
upstream Attempt or dependency not absorbed by a successor invalidates the
Subject and forces a revision or upstream return.

**M-03 Method execution lacked a persisted pre-execution/readback boundary.**

**Closure:** Architecture and State Machine require the complete Method Contract
to be materialized and read back before formal execution/evidence capture.

**M-04 Product result and Artifact Gate could still be collapsed by status and
delivery tooling.**

**Closure:** schemas, lifecycle projection, matrix and Web Review explicitly
model `product_result` separately from `artifact_gate`; a trusted fail record may
freeze but is not RLS-ready.

**M-05 No machine-verifiable 80/80 coverage guard or exact-SHA evidence format.**

**Closure:** `05-CRITICAL-CASE-MATRIX.md`, two JSON schemas and validation entry
point define exact identifiers, commands, logs, evidence digest and source SHA.

**M-06 Local closed-loop and Web review responsibilities were not executable.**

**Closure:** `09-LOCAL-CODEX-GOAL.md` is the implementation/fix/attestation
controller; `10-WEB-REPORT-REVIEW.md` independently validates its report.

### Minor — implementation must preserve

- Prefer small responsibility modules; `runtime.py` is only CLI assembly.
- Keep Evidence primary summaries bounded and raw material in Supporting Members.
- External project runner must accept prepared caches when network is unavailable.
- Record every bounded DNS/502/503/504 retry; never convert exhaustion into skip.

### Observation

- Current ArtifactStore already supports VFY allocation and canonical revision
  persistence through its public API; no schema fork is required.
- Current IMP Resource/Claim contracts provide the needed semantic inputs, but
  VFY must consume their public result projection rather than direct SQL.
- GitHub Actions may remain repository infrastructure, but are explicitly not
  VFY development or closure authority.

## Result

```text
Blocker: 0 open
Major:   0 open
Minor:   implementation constraints only
Observation: 3
DESIGN_REVIEW: READY_FOR_INITIAL_IMPLEMENTATION
```
