# Skill Eval Plan — `sdlc-status`

## Status

`ready` — fixed before implementation.

## Critical checks

| ID | Requirement | Pass condition |
|---|---|---|
| STS-E01 | Bare invocation | zero-argument auto works |
| STS-E02 | No Store | returns not_started and creates nothing |
| STS-E03 | CTX only | recommends REQ without writing |
| STS-E04 | One REQ | auto-inspects exact Revision |
| STS-E05 | Multiple REQs | lists candidates and requires selection |
| STS-E06 | Exact inspect | returns graph/frontier/blockers/next action |
| STS-E07 | Symbolic reference | latest/current rejected |
| STS-E08 | Meta commands | help/version/commands/examples have zero project access |
| STS-E09 | Alias matrix | canonical and compatible forms normalize correctly |
| STS-E10 | Write policy | effective policy always deny; zero mutations |
| STS-E11 | Output modes | summary/json/debug consistent |
| STS-E12 | Runtime independence | executes without docs |
| STS-E13 | Sibling isolation | does not call CTX/REQ/DSN Skills |
| STS-E14 | SpringGear closure | real CTX→REQ→status path succeeds |
| STS-E15 | Foundation failure | corrupt/missing dependencies fail closed |

## Cases

| Case | Fixture | Expected |
|---|---|---|
| empty-auto | existing directory, no `.sdlc` | not_started; CTX action |
| ctx-only | one frozen ready CTX | context_only; REQ action |
| req-single | one active REQ | automatic inspect |
| req-multiple | two active REQs | selection_required |
| req-open | waiting_input REQ | action_required; revise command |
| req-ready | frozen ready REQ | ready_for_next_phase; DSN availability |
| req-abandoned | abandoned REQ | blocked |
| missing-dependency | declared exact missing input | blocked |
| bad-ref | latest/item ref for inspect | structured error |
| help | any project state | static help, no project access |
| output-json | exact REQ | one JSON document |
| output-debug | exact REQ | resolved command plus raw projection, no secrets |
| springgear | actual repository snapshot | same project hashes before/after |

## Oracle protection

- foundation behavior is consumed, not copied;
- no test may bypass exact references;
- no fixture may use direct SQL;
- no expected result may be weakened to hide a write;
- project hash equality is mandatory for real integration;
- unexecuted host behavior remains Unknown/Partial.

## Pass gate

- all critical cases pass;
- full repository regression passes;
- static Skill Interface validator passes;
- SpringGear integration passes;
- Review has zero Blocker/Major;
- remote branch contains all required evidence files;
- CI is green on the exact final branch HEAD.
