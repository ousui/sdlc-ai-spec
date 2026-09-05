# Parallel Interference Guard

## Owned refs

- `design/sdlc-600-rls-goal`
- `impl/rls-v2`

## Read-only refs

- `main`
- `impl/imp-v2`
- `design/sdlc-500-vfy-goal`
- `impl/vfy-v2`

## Design-owned paths

`docs/plugin-development/work-items/sdlc-600-rls/**`

## Provisional implementation-owned paths

```text
skills/sdlc-600-rls/**
tests/skill_rls/**
tests/evals/sdlc_600_rls_cases.json
tests/evals/test_sdlc_600_rls_case_coverage.py
tests/evals/run_sdlc_600_rls_eval.py
tools/validate_sdlc_600_rls_source_lock.py
tools/test_sdlc_600_rls_runtime_independence.py
tools/run_rls_provisional_validation.py
```

## Deferred shared paths — forbidden in this Web implementation

```text
packages/sdlc_lifecycle/**
skills/sdlc-status/**
tests/lifecycle/**
tests/skill_status/**
tests/evals/late_phase_eval.py
tools/validate_lifecycle_query.py
tools/validate_sdlc_status.py
tools/run_external_rls_integration.py
tests/system_integration/test_external_rls_integration.py
skills/_shared/**
packages/sdlc_runtime/**
packages/sdlc_artifact_store/**
packages/sdlc_claim_provider/**
packages/sdlc_resource/**
packages/sdlc_execution/**
packages/sdlc_effects/**
```

VFY drift and main drift are recorded at task end but never chased, rebased or
merged during parallel preparation. Any unexplained movement of an owned RLS Ref
is a hard blocker; do not force-overwrite it.
