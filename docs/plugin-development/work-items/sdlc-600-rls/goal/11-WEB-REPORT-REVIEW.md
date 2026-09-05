# Web Sol Pro Prompt — Review Final Local RLS Delivery

Review only. Do not implement, repair VFY, comment on PRs, merge PRs, create
releases/tags or execute any real target effect.

Read the final `impl/rls-v2`, its Draft PR, current `main`, accepted VFY Design /
Implementation / Evidence / Handoff, RLS formal Evidence/Handoff and all
validation JSON/logs. Distinguish and name:

```text
WEB_PROVISIONAL_CHECKPOINT_SHA
FINAL_IMPLEMENTATION_SUBJECT_SHA
EVIDENCE_HEAD_SHA
ACCEPTED_VFY_IMPLEMENTATION_SUBJECT_SHA
ACCEPTED_VFY_EVIDENCE_HEAD_SHA
```

A PR Head, branch, tag, `latest`, old Evidence Head or Web repair source snapshot
is not an Implementation Subject.

## 1. Ancestry and scope

Verify from actual refs and commits, not PR prose:

- main Tree equals accepted VFY Evidence Tree under TREE_EQUIVALENT_LINEAR_REPLAY;
- B has tree(V), first parent accepted VFY Evidence V and second parent main M;
- B -> D -> S -> E is the final chain; D differs only by RLS design paths;
- main is an ancestor of D/S/E and net PR changes against main are RLS-only;
- old RLS source commits are not newly introduced ancestors;
- PR #7/#9 are historical records; do not require them to be merged or modify them;
- the Evidence/Handoff commit is a child of the exact Implementation Subject;
- RLS-authored commits do not modify VFY files or rewrite accepted VFY history;
- only explicitly authorized RLS/shared final-integration paths changed;
- no `.github/workflows/**`, Evidence branch, payload/observer/finalizer branch,
  Release, tag or production adapter was introduced.

## 2. VFY → RLS final interface

Re-read the accepted VFY producer and bundled
`sdlc-ai-spec/vfy-release-candidate/v1` schema. Independently compare them with
RLS `rls_vfy_adapter.py`, bundled schema, Source Lock and Evidence.

Verify all `PROVISIONAL_VFY_INTERFACE-A01..A12` ledger rows are closed and that:

- final delivery rejects `provisional=true` input;
- `vfy_reference`, Scope, Subject/Result Set, conclusions, Artifact Status/Gate,
  early-stop, pending state, unresolved Return/Control, applicability,
  `rls_ready`, Evidence and Exception references are exact;
- the upstream VFY `source_digest` is preserved;
- the Candidate transport bytes have an independently recomputed digest;
- product fail requires a current scoped authoritative Exception;
- `pass_with_exception` carries exact Exception references;
- final code and Evidence contain no `VFY_FINAL_SHAPE_SHADOW` authority claim;
- real accepted VFY Artifacts, not provisional fixtures, drive final tests.

Any unreviewed field or schema mismatch is `CHANGES_REQUIRED`.

## 3. Canonical ArtifactStore authority

Prove that RLS does not trust an Artifact object supplied on stdin:

- create/revise allocate and persist through the shared ArtifactStore facade;
- open writes use current generation and fail on stale generation;
- `check -r RLS-...@N` opens the Store read-only and resolves exactly that
  numeric Revision;
- Primary ↔ `RLS-STATE` ↔ Manifest semantic verification is executable;
- frozen readback runs the RLS DomainVerifier;
- Final Confirmation binds current canonical bytes;
- Store failure does not fall back to loose JSON/temp storage;
- runtime reads no `docs/**`.

Tampered Primary, State Member, Manifest, Supporting Member, Evidence digest,
reference, generation or Final Confirmation must fail closed.

## 4. Effect Authorization

Review authorization issuance, validation, execution order, history and tests.
Prove that workspace write policy, GitHub permission, Approval/Trigger, Final
Confirmation, previous consent or agent judgment cannot substitute for one
current exact authorization.

Every change below must invalidate the old authorization before the target is
observed or mutated:

- Artifact ID/reference or Revision;
- Release Reference, Scope, Result Set or VFY Reference;
- VFY source/Candidate digest, conclusions, Exception set or RLS readiness;
- Release Target or current Target Baseline;
- any Release Contract field;
- selected RLI IDs, action/source/prerequisite/executor contract;
- complete RLI contract set or RCF contract set;
- Pre-execution Checklist digest;
- validity interval or authorizer identity.

Check authorization history retains the full immutable grant and that legal
post-effect results/Evidence do not rewrite the historical contract. Confirm an
expired, reused, mismatched, narrowed or broadened grant produces zero effect.

## 5. Release semantics and sandbox

Verify baseline, target-state drift, no-op, success, partial, failure,
cancel-before-effect, retry, target change, confirmation, immutable Evidence and
cleanup. Cancellation after any possible effect is forbidden. Partial/failed/
cancelled records may have Artifact Gate pass; Gate pass must never be displayed
as Release success.

Only a dedicated OS temporary/sandbox root is permitted. Confirm:

```text
REAL_TARGET_EFFECTS = 0
```

No GitHub Release, tag/push, deployment, database, cloud, network API or
production target effect may have occurred.

## 6. Lifecycle and status

Review `packages/sdlc_lifecycle/query_rls.py` and `skills/sdlc-status` as additive
shared integrations. They must preserve independent dimensions:

- VFY Product Result;
- VFY Artifact Gate and RLS readiness;
- RLS Revision state;
- Release Conclusion;
- RLS Artifact Gate;
- target effect;
- Follow-up and next action.

Check success/partial/failed/cancelled/retry/return/no-change/n-a/waived are
projected correctly and no lifecycle query mutates the Store.

## 7. Executable validation and Evidence

Re-run, against the exact Implementation Subject:

```bash
python3 tests/skill_rls/preweb_review.py --profile final --root "$PWD" --json-out /tmp/web-rls-preweb-final.json
python3 tools/run_rls_delivery_validation.py --profile quick    --source-sha "$SHA" --json-out /tmp/web-rls-quick.json
python3 tools/run_rls_delivery_validation.py --profile phase    --source-sha "$SHA" --json-out /tmp/web-rls-phase.json
python3 tools/run_rls_delivery_validation.py --profile full     --source-sha "$SHA" --json-out /tmp/web-rls-full.json
python3 tools/run_rls_delivery_validation.py --profile external --source-sha "$SHA" --json-out /tmp/web-rls-external.json
python3 tools/run_rls_delivery_validation.py --profile attest   --source-sha "$SHA" --json-out /tmp/web-rls-attest.json
```

Verify:

- final Pre-Web gate is PASS with all five `RLS-FINAL-*` checks PASS;
- Fixed Eval is exactly 87/87 with no skip, `expectedFailure`, duplicate,
  weakened assertion, missing command or unexecuted case;
- Source Lock is final, non-shadow and matches exact installed bytes;
- installed-copy Runtime Independence passes with docs/tests absent;
- VFY Fixed Eval/Runtime Independence and full repository regression actually ran;
- SpringGear and Gin-Vue-Admin exact-SHA full chains completed using only local
  sandbox targets and recorded before/after repository state;
- every Evidence file matches the SHA-256 manifest and binds the exact source SHA;
- argv, cwd, exit code, duration, logs and secret redaction are complete;
- attestation is fresh and was produced after the final Subject was stable.

Do not accept copied logs, mismatched SHA, PR checks, GitHub Actions, stale
Evidence or an Evidence Head tested as though it were the Implementation Subject.

## 8. PR and repository final state

Confirm `main` and VFY refs were not modified by RLS work; PR base is `main`, PR
remains Draft, merge method is Create a merge commit, and no PR was merged by the
local Goal or this review.

## Verdict

Output exactly one verdict:

```text
WEB_RLS_REVIEW = ACCEPTED
```

or:

```text
WEB_RLS_REVIEW = CHANGES_REQUIRED
```

For changes required, list severity, exact file/line or Evidence object,
violated authority, reproducible check and minimal RLS repair. Never repair VFY
unless the accepted final VFY itself demonstrably violates approved Spec.
