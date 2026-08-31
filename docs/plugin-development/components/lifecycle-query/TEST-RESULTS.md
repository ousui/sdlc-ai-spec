# Lifecycle Query Test Results

## Validated commit

```text
891b1fdfe17c9bc7ab614e6d960d3f6082c88e51
```

GitHub Actions:

```text
Run: 33420616638
Conclusion: success
```

## Commands and results

```bash
python3 -m compileall packages scripts skills
# PASS

python3 tools/validate_runtime_contracts.py
# PASS — 5 shared contracts, 2 formal Skills

python3 tools/validate_skill_interfaces.py
# PASS — authority source locks unchanged

python3 tools/validate_lifecycle_query.py
# PASS — writes: 0

python3 tools/validate_sdlc_100_req_source_lock.py
# PASS — 8 contracts

python3 tools/test_sdlc_100_req_runtime_independence.py
# PASS — docs copied: 0; external dependencies: 0

python3 -m unittest discover -s tests -p 'test_*.py' -v
# PASS — 131/131

python3 tools/test_springgear_lifecycle_query.py --source _integration/springgear
# PASS
```

## SpringGear evidence

```text
Repository: ousui/springgear
Branch: devl
Source commit: e855096ff19dcdb303dc4250ba19c30acd743ac7
Generated CTX: CTX-20260831190000-01@1
Generated REQ: REQ-20260831190000-01@1
Projection: ready_for_next_phase
Query-time project mutations: 0
Remote springgear writes: 0
```

The integration checkout is copied to a temporary directory. The actual `sdlc-000-ctx` and `sdlc-100-req` runtimes create the test Store there; the query then verifies the exact frozen artifacts. No `.sdlc` data is committed or pushed to SpringGear.

## Covered boundaries

- Store missing: no `.sdlc` creation;
- exact REQ Revision selection;
- multiple REQ lineages and materialized Revision listing;
- Context / Scope / Control / Return / Issue edge model;
- Open Item, failed and abandoned state handling;
- missing declared dependency;
- frontier and next-phase computation;
- installed Skill availability;
- CTX producer and frozen-authority consumer digest parity;
- full-project file digest equality before and after query.

## Unverified

- lifecycle relations produced by DSN, PLN, IMP, VFY and RLS real runtimes; those Skills do not yet exist;
- remote or multi-provider Stores;
- real Codex invocation of `sdlc-status`, which belongs to the following Skill branch.
