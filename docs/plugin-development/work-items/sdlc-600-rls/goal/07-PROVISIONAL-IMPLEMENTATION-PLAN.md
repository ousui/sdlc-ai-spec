# Provisional Implementation Plan

| CP | Input | Allowed paths | Output / test | PASS or provisional condition | Resume |
|---|---|---|---|---|---|
| P1 Skill skeleton / Interface | approved goal design | private Skill paths | SKILL, YAML, interface; JSON parse | meta contract complete | start at interface validator |
| P2 VFY Adapter | frozen design assumptions | adapter + fixture/tests | stable candidate; reject stale/early-stop | all assumptions labeled provisional | rerun delta ledger |
| P3 Release Contract | candidate + target/baseline | contract/scope/items | exact binding/effect digest | no scope/result mutation | rebuild from candidate |
| P4 Effect Authorization | exact contract | authorization module/tests | issue/validate/invalidate | zero effect on reject | reacquire auth |
| P5 Release Items | RLI/RCF plan | items/executor | ordered independent results | evidence required | resume pending item |
| P6 Fake/Sandbox Target | temp target root | target module/tests | snapshots/evidence/cleanup | no path/network escape | recreate sandbox |
| P7 Confirmation | target snapshot | confirmation module | actual target-side pass/fail | pipeline alone never pass | rerun RCF |
| P8 Conclusion / Follow-up | terminal item states | conclusion/verifier | deterministic outcome/gate | dimensions distinct | recompute pure functions |
| P9 Revision / Retry / Cancel | frozen/open state | handler/tests | same-revision flow, retry, cancel | target/scope rules hold | exact reference |
| P10 Private Tests | P1–P9 | tests/skill_rls | focused unittest suite | actual pass only | failed method |
| P11 Provisional Eval / Independence | matrix + runtime | allowed eval/tools | 87 unique cases + JSON report | report says provisional only | rerun profile |
| P12 Draft PR | persisted commits | owned refs only | Draft PR to main | PROVISIONAL—DO NOT MERGE | same branch |

At every checkpoint: syntax/JSON validation, forbidden-path and secret scan,
normal commit, branch readback and allowed-path diff check. Never touch VFY or
shared deferred paths. No checkpoint may claim final Evidence or fixed eval.
