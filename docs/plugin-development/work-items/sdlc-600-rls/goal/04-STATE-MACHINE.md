# RLS State Machine

## Independent dimensions

Release Item Result, Confirmation Result, Release Conclusion, Product/Target
Outcome, Artifact Status, Artifact Gate, Follow-up and Lifecycle state are stored
and computed independently.

| State | Entry | Legal next action |
|---|---|---|
| no RLS | no matching artifact | create when applicability required |
| applicability n/a | legal no target effect | complete without artifact |
| applicability waived | valid Exception before effect | complete without artifact |
| applicability pending | target/intent unresolved | action_required |
| open / contract_ready | complete contract, no effect | authorize/execute/cancel/check |
| open / waiting_authorization | execute requested without current auth | authorize/check/cancel |
| open / executing | authorized selected RLI running | record result/checkpoint |
| open / waiting_confirmation | effect/result exists, RCF pending | confirm/check |
| open / failed | trustworthy finalization blocked | repair open record or abandon |
| frozen / success | all required success/pass | terminal |
| frozen / partial | some effect, not complete | retry_rls or return_* |
| frozen / failed | explicit failure | retry_rls or return_* |
| frozen / cancelled | no target effect, active stop | terminal or new retry revision |
| frozen / retry_rls | follow-up RLS | new revision |
| frozen / return_req | requirement gap | REQ control input |
| frozen / return_dsn | design gap | DSN control input |
| frozen / return_pln | plan/scope gap | PLN control input |
| frozen / return_imp | unique product-result lineage gap | IMP control input |
| new revision retry | same ID/scope/results/target | reacquire baseline/auth/checklist |
| new target new artifact | target identity changed | independent artifact |
| no-change | normalized binding unchanged | exact existing ref, no write |
| abandoned reservation | first materialization failed | new safe attempt |

Rules:

- Gate pass is not release success; failed/partial/cancelled may freeze with Gate pass.
- Gate fail plus claimed success cannot freeze.
- Cancel is legal only while target snapshot proves zero effect.
- Any partial target effect is partial/failed, never cancelled.
- Retry always reacquires Target Baseline and Effect Authorization.
- Scope/Result change returns upstream; Target change creates another Artifact.
- `check` changes neither Artifact bytes nor target bytes.
