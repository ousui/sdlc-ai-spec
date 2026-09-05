# Validation Closed Loop

## Single authority entry point

```bash
python3 tools/run_vfy_delivery_validation.py \
  --profile <quick|phase|full|external|attest> \
  --source-sha <exact-40-hex-sha> \
  --json-out <absolute-or-worktree-relative-path>
```

The runner verifies `git rev-parse HEAD == --source-sha` before every profile,
records the tree SHA, and fails when the worktree is dirty unless the profile
explicitly creates and later removes only `.sdlc`.

## Profiles

| Profile | Required work |
|---|---|
| `quick` | JSON/schema parse, Python compile/import, interface/source-lock/coverage guards, focused deterministic smoke |
| `phase` | all `tests/skill_vfy`, VFY Fixed Eval, lifecycle/status regressions, Runtime Independence |
| `full` | quick + phase + complete repository unittest discovery + diff/forbidden-path review |
| `external` | both fixed projects, full phase chain, at least two Method Types, cleanup/digest invariants |
| `attest` | fresh worktree at exact final Subject; rerun quick/phase/full/external plus evidence-integrity preflight |

A profile succeeds only when all required commands exit zero and every nested
structured result is PASS.

## Machine result

The result conforms to
`goal/schemas/vfy-verification-result-v1.schema.json` and contains:

- exact `source_sha` and source tree;
- profile and start/end timestamps;
- commands with argv, cwd, exit code, duration and log path/digest;
- exact 80-case ledger for applicable profiles;
- external project exact SHAs and cleanup result;
- evidence digest;
- final status `PASS` or `FAIL`.

Missing tools, files, cases, logs or nested results are failures, not skips.

## Retry policy

Only external fetch/read operations that fail with DNS resolution, HTTP
502/503/504 or an equivalent transient transport error receive bounded retry:

```text
attempts = 3
backoff  = 2s, 5s
```

Every attempt and error is logged. Test assertions, syntax errors, contract
failures, 4xx authentication/authorization and deterministic project failures
are never retried as infrastructure noise.

## Failure loop

1. stop at the first actual failed gate while preserving its complete log;
2. identify the smallest violated Design/Spec contract;
3. fix implementation or legitimate fixture, never authority or assertion;
4. run the smallest impacted profile;
5. rerun every downstream profile invalidated by the change;
6. amend/rebuild the Implementation Subject before formal Evidence exists;
7. once fresh attestation passes, freeze the Subject SHA;
8. generate Evidence in a distinct later commit;
9. any post-Evidence source change invalidates affected Evidence and requires
   Subject rewrite plus complete regeneration.

## Evidence directory

```text
docs/plugin-development/work-items/sdlc-500-vfy/evidence/
<VFY_IMPLEMENTATION_SUBJECT_SHA>/
├── vfy-full-regression.log
├── vfy-fixed-eval.log
├── vfy-real-projects.json
├── vfy-final-attestation.log
├── vfy-design-review.md
├── vfy-verification-result.json
├── vfy-handoff.md
├── vfy-evidence.sha256
└── vfy-repository.sha256
```

The Evidence commit must not modify implementation/test/tool files and must have
the Implementation Subject as its direct parent.

## Terminal outcomes

`VFY_CLOSED_LOOP = PASS` is allowed only after all exact-SHA gates and evidence
verification pass. Any non-recoverable or exhausted real failure terminates as
`VFY_CLOSED_LOOP = HARD_BLOCKED`. `RUNNING`, `PENDING`, a GitHub check or an
unexecuted plan is not a terminal result.
