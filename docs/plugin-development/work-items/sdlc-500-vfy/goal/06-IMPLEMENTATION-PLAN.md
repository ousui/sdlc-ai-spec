# VFY Implementation Plan

Each checkpoint is resumable and fail-closed. A PASS condition means the named
gate was actually executed; during Web preparation all execution-heavy gates
remain `LOCAL_VALIDATION_REQUIRED`.

## 1. Scope / Subject / Target

- **Input:** frozen scope sources and current completed IMP public projections.
- **Allowed paths:** `vfy_scope.py`, `vfy_subject.py`, `vfy_targets.py`, focused tests.
- **Forbidden:** direct SQL, branch/tag Subject, partial scope, invented Target.
- **Implementation:** normalize one full scope, immutable current Subject Set and authoritative Target Set.
- **Tests:** E010-E025.
- **PASS:** all references exact/current/complete; ambiguity and stale chain fail closed.
- **Preserved state:** no Artifact allocation before complete scope.
- **Rollback:** discard in-memory candidate.
- **Resume:** rerun resolver after correcting authoritative input.
- **Dependency:** integrated IMP public projection.

## 2. Method Contract

- **Input:** Targets, Subjects, VFY obligations and Control Inputs.
- **Allowed paths:** `vfy_methods.py`, method tests.
- **Forbidden:** invented pass criteria, extra Method Type, mode/type conflation.
- **Implementation:** stable Method index/details and Purpose compatibility.
- **Tests:** E026-E040.
- **PASS:** every applicable Target and obligation covered exactly.
- **Preserved state:** open `waiting_input` when required facts are absent.
- **Rollback:** edit only the open pre-execution contract.
- **Resume:** after the precise fact/decision is supplied.
- **Dependency:** checkpoint 1.

## 3. Executor / Evidence

- **Input:** persisted and read-back Method Contract.
- **Allowed paths:** `vfy_executor.py`, `vfy_results.py`, Supporting Members and tests.
- **Forbidden:** shell, install, unrestricted cwd/network, fabricated human Evidence.
- **Implementation:** bounded automated runner and structured manual/hybrid intake.
- **Tests:** E041-E051.
- **PASS:** actual Subject and immutable Evidence bind every pass/fail.
- **Preserved state:** pending/fail plus diagnostic Evidence.
- **Rollback:** terminate process and retain only trustworthy output.
- **Resume:** explicit readiness followed by current-Subject recheck.
- **Dependency:** checkpoint 2.

## 4. Conclusion / Return / Early Stop

- **Input:** Method Results and Evidence.
- **Allowed paths:** `vfy_conclusions.py`, `vfy_returns.py`, `vfy_verifier.py`.
- **Forbidden:** pass override, ambiguous Return, pending Disposition.
- **Implementation:** dimension aggregation, exact Return attribution and early-stop proof.
- **Tests:** E052-E070.
- **PASS:** fixed aggregation; every failure actionable; illegal early stop rejected.
- **Preserved state:** open or trusted frozen fail; never RLS-ready.
- **Rollback:** recompute from immutable Method rows.
- **Resume:** new revision after upstream rework.
- **Dependency:** checkpoint 3.

## 5. Revision / Artifact Gate

- **Input:** complete normalized VFY state.
- **Allowed paths:** `vfy_builder.py`, `vfy_verifier.py`, ArtifactStore public API.
- **Forbidden:** SQL, product/Gate collapse, empty revision.
- **Implementation:** generation-CAS write, closure verification, freeze/abandon/no-change.
- **Tests:** E071-E076.
- **PASS:** digests, current confirmation and VFY-G-001..008 recompute.
- **Preserved state:** exact open/frozen/abandoned revision.
- **Rollback:** abandon failed first-write reservation.
- **Resume:** create/revise from last frozen authority.
- **Dependency:** checkpoints 1-4.

## 6. Lifecycle Query / sdlc-status

- **Input:** verified VFY projection.
- **Allowed paths:** `packages/sdlc_lifecycle/query_vfy.py` and additive `skills/sdlc-status` changes.
- **Forbidden:** RLS execution; Artifact-ready=product-pass.
- **Implementation:** exact Return phase, RLS readiness or lifecycle complete projection.
- **Tests:** E077-E080 and status regression.
- **PASS:** early-stop/fail/unresolved Return never RLS-ready.
- **Preserved state:** pure read-only projection.
- **Rollback:** revert only additive projection.
- **Resume:** rerun query fixture.
- **Dependency:** checkpoint 5.

## 7. Source Lock / Runtime Independence / Fixed Eval

- **Input:** bundled Runtime Contract and implementation files.
- **Allowed paths:** VFY references and required validators/evals.
- **Forbidden:** production `docs/**` read, network install, missing-as-skip.
- **Implementation:** pin bytes, copy installed boundary, execute exact fixed cases.
- **Tests:** 80/80 coverage guard and independence fixtures.
- **PASS:** all mandatory commands execute; missing file/command is failure.
- **Preserved state:** `LOCAL_VALIDATION_REQUIRED` until actually run.
- **Rollback:** restore candidate commit; never weaken the lock.
- **Resume:** rerun quick then phase.
- **Dependency:** checkpoints 1-6.

## 8. Full Regression / Independent Review

- **Input:** stable initial Implementation Subject.
- **Allowed paths:** top validator outputs outside formal Evidence until PASS.
- **Forbidden:** test deletion/weakening and Design edits on implementation branch.
- **Implementation:** full repository tests plus fresh design/correctness review.
- **Tests:** `full` profile.
- **PASS:** zero regression; Blocker=0; Major=0.
- **Preserved state:** subject may still be amended before Evidence.
- **Rollback:** amend/rebuild Subject only before Evidence commit.
- **Resume:** rerun all impacted profiles.
- **Dependency:** checkpoint 7.

## 9. SpringGear / gin-vue-admin

- **Input:** exact fixed SHAs and prepared isolated checkouts.
- **Allowed paths:** external runner and system integration test.
- **Forbidden:** commit/push/install/project residue and commit-only probe.
- **Implementation:** CTX→REQ→DSN→PLN→IMP→VFY and at least two Method Types.
- **Tests:** `external` profile.
- **PASS:** both exact projects and cleanup invariants verified.
- **Preserved state:** subject amend allowed; old Evidence invalid after a fix.
- **Rollback:** restore checkout, refs and `.sdlc`.
- **Resume:** bounded retry only for DNS/502/503/504 fetch.
- **Dependency:** checkpoint 8.

## 10. Implementation Subject Commit

- **Input:** all implementation fixes.
- **Allowed paths:** implementation/test/tool paths authorized by the design.
- **Forbidden:** Evidence files and merge/rebase of design ancestry.
- **Implementation:** amend/rebuild one `feat(vfy): implement deterministic verification phase` commit.
- **Tests:** fresh attestation preflight.
- **PASS:** direct parent is design head and exact tree is clean.
- **Preserved state:** frozen candidate SHA.
- **Rollback:** force-with-lease to the last safe candidate only.
- **Resume:** fresh full/external/attest.
- **Dependency:** checkpoint 9.

## 11. Evidence/Handoff Commit

- **Input:** fresh exact-SHA PASS results.
- **Allowed paths:** `docs/plugin-development/work-items/sdlc-500-vfy/evidence/<subject>/**` only.
- **Forbidden:** Subject rewrite after Evidence and fabricated/manual PASS.
- **Implementation:** archive logs, result, review, Handoff and SHA-256 manifests.
- **Tests:** schema and digest validation.
- **PASS:** every report source SHA equals Subject and all evidence verifies.
- **Preserved state:** Evidence delivery head distinct from Subject.
- **Rollback:** delete invalid local Evidence and rerun; never edit a failure into PASS.
- **Resume:** append only after final attestation.
- **Dependency:** checkpoint 10.

## 12. Draft PR Delivery

- **Input:** design merged by merge commit and Evidence delivery head.
- **Allowed paths:** existing `impl/vfy-v2` Draft PR body/status.
- **Forbidden:** merge, rebase, RLS and new Evidence branch.
- **Implementation:** update exact SHAs/results while preserving ancestry and Draft state.
- **Tests:** remote readback of refs, parents, tree and PR base/head.
- **PASS:** base=`main`, head=`impl/vfy-v2`, two-commit delivery, no main mutation.
- **Preserved state:** Draft and blocked until independent Web acceptance.
- **Rollback:** force-with-lease only for a pre-Evidence Subject rewrite.
- **Resume:** local Goal restarts from first failed gate.
- **Dependency:** checkpoint 11.
