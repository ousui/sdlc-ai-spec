# RLS Traceability

| Requirement | Design authority | Runtime module | Tests / evidence |
|---|---|---|---|
| exact VFY readiness | 02 interface | adapter | E010–E024 |
| Scope/Result/Target contract | DESIGN §6 | scope/contract/items | E020–E031 |
| independent authorization | 05 authorization | authorization/executor | E032–E040 |
| truthful release items | 600 spec RLI | items/executor | E041–E050 |
| target-side confirmation | 600 spec RCF | confirmation | E051–E060 |
| conclusion/follow-up/gate split | DESIGN §8 | conclusion/verifier | E061–E071 |
| revision/retry/cancel/check | 04 state machine | handler/target | E072–E080 |
| lifecycle/status | 08 post-VFY plan | shared deferred query/status | E081–E087 final |
| runtime independence/source lock | 09 validation | tools + bundled references | quick/phase/attest |
| external complete chain | EVAL §5 | local sandbox only | external profile |

Every Critical Case has a unique row in `06-CRITICAL-CASE-MATRIX.md` and a unique
primary test in `tests/skill_rls/test_critical_cases.py`.
