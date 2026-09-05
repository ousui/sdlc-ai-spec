# Local Codex `/goal` — Final RLS Close Loop

Use this entire document as one Goal. Do not stop at an intermediate status.

## Required starting state

- VFY local closed loop is complete and its independent Web Review is `ACCEPTED`;
- `impl/vfy-v2 → main` and the RLS Design PR were merged with **Create a merge commit**;
- `impl/rls-v2` contains the provisional implementation and Web pre-integration
  hardening from this work package;
- production effects remain forbidden; the only Release Target is a local sandbox.

If any required starting condition is false, end `RLS_CLOSED_LOOP = HARD_BLOCKED`.
Do not reinterpret a VFY repair-source snapshot, provisional fixture, PR body,
branch name, CI status or old Evidence as final VFY authority.

## Owned branch and safety

Work only on `impl/rls-v2`; do not rewrite `main`, VFY refs or Evidence history.
Fetch all refs, verify a clean worktree, record start SHA/tree, and stop as
`HARD_BLOCKED` on unexplained branch drift. Merge latest `origin/main` into the
branch with `--no-ff`; never rebase or squash.

Do not create an Evidence branch, payload branch, observer/finalizer/materializer,
GitHub Actions workflow, GitHub Release, Git tag, deployment, database write,
cloud effect or production API call. Repository permissions and
`write_policy=auto` never substitute for Effect Authorization.

## Existing Web pre-integration assets — preserve and verify

The provisional branch already contains the following work. Inspect it before
changing it; do not reimplement it blindly:

- dual-mode `rls_vfy_adapter.py` supporting the historical provisional fixture
  and the observed final-shaped VFY Candidate;
- bundled `vfy-release-candidate-v1.schema.json` and exact shadow fixture;
- separate upstream `source_digest` and transport `candidate_digest`;
- final-shaped `rls_ready`, `exception_references`, exact Artifact Status/Gate,
  exact Scope and two-or-more-digit allocation suffix support;
- complete Effect Authorization binding over Release Contract, selected RLI,
  full RLI set, RCF set and Pre-execution Checklist;
- authorization-history verification that separates immutable Contract fields
  from legal post-effect outcome fields;
- executable `tests/skill_rls/preweb_review.py` with provisional and final modes.

Before implementing final integration, run:

```bash
python3 tests/skill_rls/preweb_review.py \
  --profile provisional \
  --root "$PWD" \
  --json-out /tmp/rls-preweb-provisional.json
```

It must pass. A failure is a real regression to repair, not a test to weaken.
The provisional result is not final Evidence.

## VFY_RLS_INTERFACE_DELTA_REVIEW

Use the integrated, accepted VFY Runtime, its bundled schema, formal Evidence and
Handoff as authority. For every `PROVISIONAL_VFY_INTERFACE-A01..A12` ledger row:

1. identify the exact accepted VFY Implementation Subject and Evidence Head;
2. read the final `sdlc-ai-spec/vfy-release-candidate/v1` producer and schema;
3. compare every field, enum, conditional, digest and identity rule with the RLS
   bundled shadow schema and `VfyReleaseCandidate` mapping;
4. verify final Candidate production from real frozen VFY Artifacts;
5. preserve VFY `source_digest`; independently compute/bind Candidate bytes;
6. ensure product fail requires a current scoped authoritative Exception;
7. ensure `pass_with_exception` carries exact Exception References;
8. ensure `rls_applicability=required` requires `rls_ready=true`;
9. ensure n/a/waived produce legal zero-effect dispositions;
10. replace provisional fixtures in all final runs with real VFY Artifacts;
11. remove `VFY_FINAL_SHAPE_SHADOW` only after all ledger rows are closed;
12. record the delta review and exact source SHAs in formal Evidence.

VFY final authority wins over the shadow adapter. Adapt RLS unless final VFY
itself demonstrably violates the approved v1.1 Spec.

## Goal

1. Verify integrated VFY Design, Runtime, formal Evidence and Handoff.
2. Merge latest `origin/main` with a merge commit and execute the interface delta
   review above.
3. Update `rls_vfy_adapter.py` and the bundled schema to exact final VFY bytes;
   prohibit provisional input in final delivery mode.
4. Implement canonical RLS Artifact construction and exact RLS Revision
   persistence/readback through the shared ArtifactStore facade. Do not copy its
   schema or fall back to loose files.
5. Make `create/execute/confirm/revise/cancel` persist current open state with
   generation checks; make `check -r RLS-...@N` reject stdin Artifact state and
   read one exact persisted Revision.
6. Implement Primary ↔ `RLS-STATE` ↔ Manifest semantic verification and a domain
   verifier before freeze. Persist Evidence as immutable Supporting Members or
   exact immutable references; do not trust self-asserted digests.
7. Implement `packages/sdlc_lifecycle/query_rls.py` as an additive pure query.
8. Integrate RLS projection into `skills/sdlc-status` without changing VFY,
   Product Result or Artifact Gate semantics.
9. Freeze final RLS Source Lock from exact installed bundled bytes. It must be
   non-provisional and must not name `docs/**`, test fixtures or a VFY repair
   snapshot.
10. Complete installed-copy Runtime Independence with docs/tests/Handoff absent.
11. Execute Fixed Eval `RLS-E001..RLS-E087`; missing, skipped,
    `expectedFailure`, duplicate, out-of-order, weak or unexecuted cases fail.
12. Run the full Fake/Sandbox Target matrix: baseline, no-op, success, partial,
    failure, cancel-before-effect, retry, confirmation, immutable Evidence,
    target drift, authorization expiry/reuse and cleanup.
13. Perform an independent Effect Authorization review proving that any Release
    Contract, VFY digest, RLI/RCF contract, target/baseline, selected set,
    checklist or Revision change invalidates the old authorization.
14. Run all focused RLS tests, VFY Fixed Eval/Runtime Independence gates and the
    complete repository regression.
15. At exact SHAs `ousui/springgear@e855096ff19dcdb303dc4250ba19c30acd743ac7`
    and `flipped-aurora/gin-vue-admin@a6882210a80bb27e3aa5dff0b4c21aa4afe8988a`,
    run CTX→REQ→DSN→PLN→IMP→VFY→RLS. The RLS Target is local sandbox only.
    Capture before/after HEAD, refs, tracked/untracked digest and prove zero
    remote writes and zero real target effects.
16. Run fresh exact-SHA `attest` against the final Implementation Subject SHA.
17. Generate formal RLS Evidence, SHA-256 manifest, final result and Handoff;
    append them on the same `impl/rls-v2` branch as an Evidence/Handoff commit.
18. Update the existing Draft PR body with actual counts and immutable SHAs;
    keep it Draft and do not merge `main`.

## Five mandatory final-readiness gates

Immediately before the Implementation Subject is frozen, run:

```bash
python3 tests/skill_rls/preweb_review.py \
  --profile final \
  --root "$PWD" \
  --json-out /tmp/rls-preweb-final.json
```

It must report all five as PASS:

```text
RLS-FINAL-001 canonical ArtifactStore persistence and exact Revision readback
RLS-FINAL-002 shared additive query_rls lifecycle projection
RLS-FINAL-003 sdlc-status RLS projection
RLS-FINAL-004 final non-shadow Source Lock
RLS-FINAL-005 accepted final VFY interface replaces shadow authority
```

A deferred item is a blocker. Do not edit this guard merely to obtain PASS;
change the implementation and authoritative inputs that it checks.

## Validation authority

Run in order and repair the first actual failure repeatedly:

```bash
python3 tools/run_rls_delivery_validation.py --profile quick    --source-sha "$SHA" --json-out /tmp/rls-quick.json
python3 tools/run_rls_delivery_validation.py --profile phase    --source-sha "$SHA" --json-out /tmp/rls-phase.json
python3 tools/run_rls_delivery_validation.py --profile full     --source-sha "$SHA" --json-out /tmp/rls-full.json
python3 tools/run_rls_delivery_validation.py --profile external --source-sha "$SHA" --json-out /tmp/rls-external.json
python3 tools/run_rls_delivery_validation.py --profile attest   --source-sha "$SHA" --json-out /tmp/rls-attest.json
```

Every result must bind the exact requested/observed SHA and tree; preserve argv,
cwd, exit code, duration, logs and redaction. GitHub Actions and PR checks are
observations, never authority. Do not weaken a Spec, test, oracle, fixture or
assertion to obtain PASS.

## Commit and Evidence model

The final branch must expose unambiguous identities:

```text
<merged latest main including accepted VFY and RLS design>
    ↓
<one final RLS Implementation Subject commit>
    ↓
<one RLS Evidence/Handoff commit>
```

Consolidate only RLS implementation history when required to establish that
model, using exact `--force-with-lease`; never rewrite accepted upstream history.
Re-run all exact-SHA validation after any consolidation. Formal Evidence must
bind the final Implementation Subject, not a Web checkpoint or Evidence Head.

## Final result

Success output must end with exactly:

```text
RLS_CLOSED_LOOP = PASS
IMPLEMENTATION_SUBJECT_SHA = <exact sha>
EVIDENCE_HEAD_SHA = <exact sha>
FIXED_EVAL = 87/87 PASS
REAL_TARGET_EFFECTS = 0
PR_MERGED = NO
```

Any first non-recoverable blocker must end with:

```text
RLS_CLOSED_LOOP = HARD_BLOCKED
FIRST_BLOCKER = <fact>
EXPECTED_SHA = <sha or n/a>
ACTUAL_SHA = <sha or n/a>
RLS_BRANCH_PRESERVED = YES/NO
VFY_MODIFIED = NO
MAIN_MODIFIED = NO
```

`RUNNING`, `PENDING`, waiting for GitHub or promises to continue later are not
valid final results.
