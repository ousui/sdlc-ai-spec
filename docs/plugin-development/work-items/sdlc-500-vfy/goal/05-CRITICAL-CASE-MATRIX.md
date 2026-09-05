# Critical Case Matrix — 80/80

Every row is a distinct executable oracle. `P/N` is positive/negative;
`R/M` is read-only/mutation. A skipped, expected-failure, missing or shared empty
placeholder test never counts as PASS.

Module/test shorthand: `I`=`runtime.py`/`vfy_handler.py`, `S`=`vfy_scope.py`/`vfy_subject.py`, `T`=`vfy_targets.py`, `M`=`vfy_methods.py`, `E`=`vfy_executor.py`/`vfy_results.py`, `C`=`vfy_conclusions.py`/`vfy_returns.py`, `X`=`vfy_verifier.py`, `L`=`vfy_builder.py`/`vfy_handler.py`/`query_vfy.py`. Fixtures are deterministic IMP completed/currentness/result/revision fixtures.

| Case ID | Spec Clause | Design Clause | P/N | R/M | Layer | Module | Test File | Test Method | IMP Fixture | Real Project | Mode | Blocks Artifact Gate | Blocks RLS | Expected |
|---|---|---|---|---|---|---|---|---|---|---:|---|---:|---:|---|
| VFY-E001 | Interface | D§5 | P | M | unit | I | `test_interface.py` | `test_vfy_e001` | `imp-completed` | no | automated | yes | yes | auto create/run |
| VFY-E002 | Interface | D§5 | N | M | unit | I | `test_interface.py` | `test_vfy_e002` | `multi-scope` | no | automated | yes | yes | list candidates; require selection |
| VFY-E003 | Interface | D§5 | P | M | unit | I | `test_interface.py` | `test_vfy_e003` | `imp-completed` | no | automated | yes | yes | classify repeatable inputs exactly |
| VFY-E004 | Interface | D§5 | P | M | unit | I | `test_interface.py` | `test_vfy_e004` | `open-vfy` | no | automated | yes | yes | run only selected pending Method |
| VFY-E005 | Interface | D§5/10 | P | M | integration | I | `test_interface.py` | `test_vfy_e005` | `frozen-vfy-new-subject` | no | automated | yes | yes | revise for changed upstream/control |
| VFY-E006 | Interface | D§5/10 | P | R | integration | I | `test_interface.py` | `test_vfy_e006` | `frozen-vfy` | no | automated | yes | yes | absolute read-only check |
| VFY-E007 | Interface | D§5 | P | R | unit | I | `test_interface.py` | `test_vfy_e007` | `none` | no | automated | no | no | meta: zero scan/write |
| VFY-E008 | Interface | D§5 | N | M | unit | I | `test_interface.py` | `test_vfy_e008` | `open-vfy` | no | automated | yes | yes | stable missing-Method error |
| VFY-E009 | Interface | D§5 | P | M | unit | I | `test_interface.py` | `test_vfy_e009` | `open-vfy` | no | automated | yes | yes | dedupe; first-occurrence order |
| VFY-E010 | Scope | D§6 | P | M | integration | S | `test_scope_subject.py` | `test_vfy_e010` | `pln-required` | no | automated | yes | yes | whole PLN scope, never partial WI |
| VFY-E011 | Scope | D§6 | P | M | integration | S | `test_scope_subject.py` | `test_vfy_e011` | `pln-na-waived` | no | automated | yes | yes | nearest complete REQ/DSN plus basis |
| VFY-E012 | Scope | D§6 | N | M | integration | S | `test_scope_subject.py` | `test_vfy_e012` | `unaggregated-scopes` | no | automated | yes | yes | return upstream; no VFY merge |
| VFY-E013 | Subject | D§6 | N | M | integration | S | `test_scope_subject.py` | `test_vfy_e013` | `imp-nonterminal` | no | automated | yes | yes | block unclaimed/active/abandoned/open |
| VFY-E014 | Subject | D§6 | N | M | integration | S | `test_scope_subject.py` | `test_vfy_e014` | `claim-active` | no | automated | yes | yes | frozen IMP with active Claim blocked |
| VFY-E015 | Subject | D§6 | P | M | integration | S | `test_scope_subject.py` | `test_vfy_e015` | `current-completed-chain` | no | automated | yes | yes | Subject accepted |
| VFY-E016 | Subject | D§6 | N | M | integration | S | `test_scope_subject.py` | `test_vfy_e016` | `dependency-new-attempt` | no | automated | yes | yes | stale Subject |
| VFY-E017 | Subject | D§4/6 | N | M | unit | S | `test_scope_subject.py` | `test_vfy_e017` | `movable-locator` | no | automated | yes | yes | reject branch/tag/current |
| VFY-E018 | Subject | D§6 | N | M | integration | S | `test_scope_subject.py` | `test_vfy_e018` | `incomplete-result-set` | no | automated | yes | yes | VFY-G-001 fail |
| VFY-E019 | Subject | D§6/10 | N | M | integration | S | `test_scope_subject.py` | `test_vfy_e019` | `subject-drift` | no | automated | yes | yes | stop/new revision; no reuse |
| VFY-E020 | Target | D§6 | P | M | unit | T | `test_targets.py` | `test_vfy_e020` | `dsn-vfo` | no | automated | yes | yes | all VFO; no duplicate AC/Goal |
| VFY-E021 | Target | D§6 | P | M | unit | T | `test_targets.py` | `test_vfy_e021` | `dsn-na` | no | automated | yes | yes | AC verification; Goal validation |
| VFY-E022 | Target | D§6 | P | M | unit | T | `test_targets.py` | `test_vfy_e022` | `multi-target-set` | no | automated | yes | yes | union by exact reference |
| VFY-E023 | Target | D§6 | N | M | unit | T | `test_targets.py` | `test_vfy_e023` | `target-gap` | no | automated | yes | yes | RETURN_TO_REQ/DSN |
| VFY-E024 | Target | D§6 | N | M | unit | T | `test_targets.py` | `test_vfy_e024` | `duplicate-requirement` | no | automated | yes | yes | reject duplicate Requirement target |
| VFY-E025 | Target | D§8 | N | M | unit | T | `test_targets.py` | `test_vfy_e025` | `both-undercovered` | no | automated | yes | yes | cannot pass |
| VFY-E026 | Methods | D§7 | P | M | unit | M | `test_methods.py` | `test_vfy_e026` | `inspection` | no | automated | yes | yes | static review; no target execution |
| VFY-E027 | Methods | D§7 | P | M | unit | M | `test_methods.py` | `test_vfy_e027` | `analysis` | no | automated | yes | yes | computed/scanned Evidence |
| VFY-E028 | Methods | D§7 | P | M | unit | M | `test_methods.py` | `test_vfy_e028` | `demonstration` | no | manual | yes | yes | observable operation result |
| VFY-E029 | Methods | D§7 | P | M | unit | M | `test_methods.py` | `test_vfy_e029` | `test-method` | no | automated | yes | yes | input/conditions/expected/criteria |
| VFY-E030 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e030` | `bad-method-type` | no | automated | yes | yes | unit/security/e2e are scope/level |
| VFY-E031 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e031` | `target-no-method` | no | automated | yes | yes | VFY-G-003 fail |
| VFY-E032 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e032` | `method-no-binding` | no | automated | yes | yes | fail |
| VFY-E033 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e033` | `purpose-mismatch` | no | automated | yes | yes | fail |
| VFY-E034 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e034` | `unmapped-vfp` | no | automated | yes | yes | fail |
| VFY-E035 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e035` | `unmapped-vfy-wi` | no | automated | yes | yes | fail |
| VFY-E036 | Methods | D§7/9 | N | M | unit | M | `test_methods.py` | `test_vfy_e036` | `unmapped-control` | no | automated | yes | yes | fail |
| VFY-E037 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e037` | `incomplete-method` | no | hybrid | yes | yes | waiting_input/fail |
| VFY-E038 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e038` | `tool-unavailable` | no | automated | yes | yes | pending/waived, never n/a |
| VFY-E039 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e039` | `waiver-no-exception` | no | automated | yes | yes | fail |
| VFY-E040 | Methods | D§7 | N | M | unit | M | `test_methods.py` | `test_vfy_e040` | `mode-as-type` | no | automated | yes | yes | fail |
| VFY-E041 | Execution/Evidence | D§7 | P | M | external | E | `test_executor_evidence.py` | `test_vfy_e041` | `safe-command` | yes | automated | yes | yes | run plus Evidence |
| VFY-E042 | Execution/Evidence | D§7 | N | M | external | E | `test_executor_evidence.py` | `test_vfy_e042` | `missing-dependency` | no | automated | yes | yes | no install; action_required |
| VFY-E043 | Execution/Evidence | D§7 | P | M | integration | E | `test_executor_evidence.py` | `test_vfy_e043` | `manual-ux` | no | manual | yes | yes | scenario/expected/evidence; wait |
| VFY-E044 | Execution/Evidence | D§7 | N | M | integration | E | `test_executor_evidence.py` | `test_vfy_e044` | `vague-human-note` | no | manual | yes | yes | Evidence insufficient |
| VFY-E045 | Execution/Evidence | D§7 | N | M | integration | E | `test_executor_evidence.py` | `test_vfy_e045` | `subject-mismatch` | no | automated | yes | yes | Result invalid |
| VFY-E046 | Execution/Evidence | D§7/8 | P | M | external | E | `test_executor_evidence.py` | `test_vfy_e046` | `command-fail` | yes | automated | no | yes | Method fail; Gate may pass |
| VFY-E047 | Execution/Evidence | D§7 | N | M | integration | E | `test_executor_evidence.py` | `test_vfy_e047` | `secret-log` | no | automated | yes | yes | redact or reject persistence |
| VFY-E048 | Execution/Evidence | D§7/14 | N | M | integration | E | `test_executor_evidence.py` | `test_vfy_e048` | `digest-tamper` | no | automated | yes | yes | check fail |
| VFY-E049 | Execution/Evidence | D§7 | N | M | integration | E | `test_executor_evidence.py` | `test_vfy_e049` | `evidence-metadata-gap` | no | hybrid | yes | yes | G-004/G-007 fail |
| VFY-E050 | Execution/Evidence | D§7 | P | M | integration | E | `test_executor_evidence.py` | `test_vfy_e050` | `matching-upstream-evidence` | yes | automated | yes | yes | independent reuse allowed |
| VFY-E051 | Execution/Evidence | D§6/7 | N | M | integration | E | `test_executor_evidence.py` | `test_vfy_e051` | `stale-evidence` | no | automated | yes | yes | reject reuse |
| VFY-E052 | Conclusions | D§8 | P | M | integration | C | `test_conclusions_returns.py` | `test_vfy_e052` | `all-pass` | yes | automated | yes | yes | fixed CON-VER/VAL aggregate |
| VFY-E053 | Conclusions | D§8 | P | M | integration | C | `test_conclusions_returns.py` | `test_vfy_e053` | `product-fail-complete` | yes | automated | no | yes | product fail; Artifact Gate may pass |
| VFY-E054 | Conclusions | D§8/12 | N | M | unit | C | `test_conclusions_returns.py` | `test_vfy_e054` | `artifact-invalid` | no | automated | yes | yes | Gate fail, separate from product |
| VFY-E055 | Conclusions | D§8 | N | M | unit | C | `test_conclusions_returns.py` | `test_vfy_e055` | `both-one-dimension` | no | automated | yes | yes | non-pass |
| VFY-E056 | Returns | D§9 | P | M | integration | C | `test_conclusions_returns.py` | `test_vfy_e056` | `imp-attributable` | yes | automated | no | yes | return_imp with lineage |
| VFY-E057 | Returns | D§9 | P | M | unit | C | `test_conclusions_returns.py` | `test_vfy_e057` | `req-gap` | no | automated | no | yes | return_req |
| VFY-E058 | Returns | D§9 | P | M | unit | C | `test_conclusions_returns.py` | `test_vfy_e058` | `dsn-gap` | no | automated | no | yes | return_dsn |
| VFY-E059 | Returns | D§9 | P | M | unit | C | `test_conclusions_returns.py` | `test_vfy_e059` | `pln-gap` | no | automated | no | yes | return_pln |
| VFY-E060 | Returns | D§9 | N | M | unit | C | `test_conclusions_returns.py` | `test_vfy_e060` | `return-incomplete` | no | automated | yes | yes | fail |
| VFY-E061 | Returns | D§9 | N | M | unit | C | `test_conclusions_returns.py` | `test_vfy_e061` | `return-received-only` | no | automated | yes | yes | not resolved |
| VFY-E062 | Returns | D§9 | P | M | integration | C | `test_conclusions_returns.py` | `test_vfy_e062` | `return-proof` | no | automated | yes | yes | later VFY proves resolution |
| VFY-E063 | Returns | D§9 | N | M | integration | C | `test_conclusions_returns.py` | `test_vfy_e063` | `return-lineage-mismatch` | no | automated | yes | yes | fail |
| VFY-E064 | Returns | D§9 | P | M | integration | C | `test_conclusions_returns.py` | `test_vfy_e064` | `rls-product-issue` | no | automated | yes | yes | complete control recovery PASS |
| VFY-E065 | Early stop | D§10 | P | M | integration | X | `test_early_stop.py` | `test_vfy_e065` | `confirmed-fail` | no | automated | no | yes | legal early-stop candidate |
| VFY-E066 | Early stop | D§10 | N | M | integration | X | `test_early_stop.py` | `test_vfy_e066` | `attribution-uncertain` | no | hybrid | yes | yes | cannot freeze early |
| VFY-E067 | Early stop | D§10 | P | M | integration | X | `test_early_stop.py` | `test_vfy_e067` | `pending-remainder` | no | hybrid | no | yes | pending only under early-stop rules |
| VFY-E068 | Early stop | D§10/12 | N | M | integration | X | `test_early_stop.py` | `test_vfy_e068` | `early-stop-frozen` | no | automated | yes | yes | RLS prohibited |
| VFY-E069 | Early stop | D§10 | N | M | integration | X | `test_early_stop.py` | `test_vfy_e069` | `open-item-false-resolution` | no | hybrid | yes | yes | fail |
| VFY-E070 | Early stop | D§8/10 | N | M | integration | X | `test_early_stop.py` | `test_vfy_e070` | `confirmation-override` | no | hybrid | yes | yes | fail |
| VFY-E071 | Revision/Gate | D§10 | P | M | integration | L | `test_revision_lifecycle.py` | `test_vfy_e071` | `open-revision` | no | automated | yes | yes | update same revision |
| VFY-E072 | Revision/Gate | D§10 | P | M | integration | L | `test_revision_lifecycle.py` | `test_vfy_e072` | `frozen-new-subject` | no | automated | yes | yes | allocate new revision |
| VFY-E073 | Revision/Gate | D§10 | P | R | integration | L | `test_revision_lifecycle.py` | `test_vfy_e073` | `frozen-no-change` | no | automated | yes | yes | NO_CHANGE; no allocation |
| VFY-E074 | Revision/Gate | D§10/12 | N | M | integration | L | `test_revision_lifecycle.py` | `test_vfy_e074` | `stale-confirmation` | no | hybrid | yes | yes | open/failed; no freeze |
| VFY-E075 | Revision/Gate | D§10 | N | M | integration | L | `test_revision_lifecycle.py` | `test_vfy_e075` | `first-write-failure` | no | automated | yes | yes | reservation abandoned |
| VFY-E076 | Revision/Gate | D§10 | P | R | external | L | `test_revision_lifecycle.py` | `test_vfy_e076` | `read-only-digest` | yes | automated | yes | yes | byte-identical before/after |
| VFY-E077 | Lifecycle | D§12 | P | R | external | L | `test_revision_lifecycle.py` | `test_vfy_e077` | `product-pass-rls-required` | yes | automated | yes | no | next phase RLS |
| VFY-E078 | Lifecycle | D§9/12 | P | R | external | L | `test_revision_lifecycle.py` | `test_vfy_e078` | `product-fail-return` | yes | automated | yes | yes | exact upstream next action |
| VFY-E079 | Lifecycle | D§12 | P | R | external | L | `test_revision_lifecycle.py` | `test_vfy_e079` | `rls-na-waived` | yes | automated | yes | no | lifecycle complete; no empty RLS |
| VFY-E080 | Lifecycle | D§8/12 | P | R | external | L | `test_revision_lifecycle.py` | `test_vfy_e080` | `ready-product-fail` | yes | automated | no | yes | status explicitly separates dimensions |

## Coverage contract

- the fixed ID set is exactly `VFY-E001..VFY-E080`;
- each Eval JSON entry names one concrete discovered unittest method;
- no named method may be skipped or expected-failure;
- external/hybrid evidence is separately required when the row says so;
- all rows are included in the final verification-result case ledger.
