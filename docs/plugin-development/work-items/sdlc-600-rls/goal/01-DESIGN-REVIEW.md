# RLS Independent Design Review

## Verdict

`Blocker=0`, `Major=0` after the goal-design corrections below. The private
provisional implementation may proceed; formal RLS closure remains blocked by
final VFY integration, shared lifecycle/status integration and local exact-SHA
validation.

## Findings

| Severity | ID | Finding | Closure |
|---|---|---|---|
| Blocker | RLS-DR-B01 | The prior design had no single VFY schema adaptation boundary, so provisional field guesses could spread through Runtime. | Closed by `rls_vfy_adapter.py`, `VfyReleaseCandidate` and the Assumption Ledger. |
| Blocker | RLS-DR-B02 | Effect Authorization lacked an executable exact-binding digest and invalidation algorithm. | Closed by `05-EFFECT-AUTHORIZATION.md` and a dedicated module. |
| Major | RLS-DR-M01 | Product conclusion, Artifact status and Artifact Gate were described but not represented as independent state dimensions. | Closed by the state machine and verifier rules. |
| Major | RLS-DR-M02 | Target Baseline recapture on retry and target-change identity were insufficiently explicit. | Closed: retry reacquires Baseline/Authorization; target change creates a new Artifact and same-second IDs remain unique. |
| Major | RLS-DR-M03 | Cancellation after partial target effect could be mislabeled cancelled. | Closed: cancelled is effect-free only; otherwise partial/failed. |
| Major | RLS-DR-M04 | RCF could accidentally treat pipeline success as target-side pass or turn a carried VFY obligation into `n/a`. | Closed: actual target-side Evidence is required, and mapped VFY obligations cannot become `n/a`. |
| Major | RLS-DR-M05 | Lifecycle and status integration could collide with concurrently changing VFY shared paths. | Closed by deferring all shared integration until the post-VFY merge commit. |
| Major | RLS-DR-M06 | Runtime Independence and fixed eval had no provisional/final authority split. | Closed by provisional validators and a final exact-SHA delivery plan. |
| Major | RLS-DR-M07 | Real-project sandbox acceptance lacked a no-production-effect invariant. | Closed by isolated local targets, before/after repository checks and zero remote writes. |
| Minor | RLS-DR-m01 | Original metadata referred to an obsolete base branch and a temporary probe-bearing VFY head. | Corrected to the clean frozen VFY snapshot `ea49c1df...`; probe ancestry is excluded from both RLS refs. |
| Minor | RLS-DR-m02 | Release Result Set terminology was not consistently separated from VFY Subject Set. | Normalized in the interface contract. |
| Observation | RLS-DR-O01 | PR #7 body and actual VFY design Ref now both identify `ea49c1df...`. | `stale_pr_body_head=false`; actual Ref remains the authority and PR #7 is untouched. |
| Observation | RLS-DR-O02 | Pre-VFY tests validate design intent, not the final VFY wire format. | Every affected result and fixture is marked `PROVISIONAL`. |

## Ten required review dimensions

1. Original RLS design defects: B01/B02/M01–M04.
2. VFY→RLS gap: B01 and Assumption Ledger.
3. Effect Authorization gap: B02.
4. Product conclusion versus Artifact Gate: M01.
5. Target/Baseline gap: M02.
6. Retry/cancel/partial gap: M02/M03.
7. Lifecycle Query gap: M05.
8. Runtime Independence gap: M06.
9. Real-project sandbox gap: M07.
10. Shared integration delayed during parallel work: M05.

No stable Spec requirement was removed or weakened.
