# Requirement → Implementation → Evidence Traceability

| Requirement | VFY Design | Module | Test | Critical Cases | Evidence | Gate | Delivery |
|---|---|---|---|---|---|---|---|
| exact full Delivery Scope | Design §6; Interface §2 | `vfy_scope.py` | `test_scope_subject.py` | E010-E013,E018 | fixed-eval + state member | G-001 | Subject commit |
| current terminal IMP Subject Set | Design §4/6; Interface §3-6 | `vfy_subject.py` | `test_scope_subject.py` | E014-E019 | subject/currentness log | G-001 | Subject + Handoff |
| authoritative Target Set | Design §6 | `vfy_targets.py` | `test_targets.py` | E020-E025 | target coverage ledger | G-002 | Subject commit |
| four Method Types and compatible Purpose | Design §7 | `vfy_methods.py` | `test_methods.py` | E026-E040 | fixed Eval | G-003 | Subject commit |
| safe automated/manual/hybrid execution | Design §7; Architecture | `vfy_executor.py` | `test_executor_evidence.py` | E041-E047 | command/manual negative logs | G-004,G-007 | Subject + Evidence |
| immutable Evidence and digest | Design §7/14 | `vfy_results.py`,`vfy_builder.py` | `test_executor_evidence.py` | E048-E051 | Supporting Members/manifests | G-004,G-007 | Evidence commit |
| deterministic conclusions | Design §8 | `vfy_conclusions.py` | `test_conclusions_returns.py` | E052-E055 | result/conclusion JSON | G-005 | Subject + Evidence |
| exact Return and resolution | Design §9 | `vfy_returns.py` | `test_conclusions_returns.py` | E056-E064 | Return fixtures/external result | G-006 | Subject + Handoff |
| legal failure early stop | Design §10; State Machine | `vfy_verifier.py` | `test_early_stop.py` | E065-E070 | early-stop Eval log | G-004..G-008 | Subject + Evidence |
| revision/freeze/no-change/abandon | Design §10 | `vfy_builder.py`,`vfy_handler.py` | `test_revision_lifecycle.py` | E071-E076 | Store/digest/read-only log | G-001..G-008 | Subject + Evidence |
| RLS readiness and status projection | Design §12 | `query_vfy.py`,`sdlc-status` | lifecycle/status tests | E077-E080 | lifecycle projection log | G-008 | Subject commit |
| Runtime Independence | Design §14 | independence tool | tool + phase tests | all runtime paths | `vfy-fixed-eval.log` | delivery gate | Evidence commit |
| 80/80 no-skip critical coverage | Eval Plan §3 | Eval runner/guard | coverage test | E001-E080 | verification case ledger | delivery gate | Evidence commit |
| full repository compatibility | Validation `full` | all additive code | unittest discovery | regression | `vfy-full-regression.log` | delivery gate | Evidence commit |
| two real full chains | Eval Plan §5 | external runner | system integration | mapped external cases | `vfy-real-projects.json` | delivery gate | Evidence commit |
| fresh exact-SHA attestation | Validation `attest` | top validator | all | E001-E080 | final attestation/result/digests | delivery gate | Evidence commit |
| no RLS/Workflow/main mutation | Design §3; Goal prohibitions | path guard | full/attest | delivery invariant | repository manifest/readback | delivery gate | Draft PR only |

## Closure rule

Every row must resolve through all columns. A missing Test, skipped Case,
unverifiable Evidence, failed Gate or delivery mismatch prevents
`VFY_CLOSED_LOOP = PASS`.
