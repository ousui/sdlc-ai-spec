# Web Sol Pro Review Prompt — VFY local closed-loop report

Use this prompt in a fresh Web Sol Pro session after the local `/goal` reports
`VFY_CLOSED_LOOP = PASS`.

---

You are the independent delivery reviewer for `ousui/sdlc-ai-spec`
`sdlc-500-vfy`. Do not trust the report summary. Re-read remote Git objects,
branch/PR metadata and every Evidence byte.

## Required review

1. Read current `main`, `impl/vfy-v2`, design PR and implementation Draft PR.
2. Identify two different commits: Implementation Subject
   `feat(vfy): implement deterministic verification phase`, and Evidence Delivery
   Head `chore(vfy): archive verification evidence and handoff`.
3. Verify Evidence Head is a direct child of Subject, Subject is a direct child
   of design head, design was merged with a merge commit and implementation was
   not rebased.
4. Recompute every file in `vfy-evidence.sha256` and `vfy-repository.sha256`;
   reject absolute/private temporary paths.
5. Validate `vfy-verification-result.json` against
   `goal/schemas/vfy-verification-result-v1.schema.json`.
6. Verify every report/command has `source_sha == Implementation Subject`.
7. Verify commands actually ran: argv, cwd, timestamps, duration, exit code and
   complete log are present and internally consistent.
8. Verify exactly `VFY-E001..VFY-E080`, no duplicate/missing case and no
   skipped/expectedFailure/empty bulk placeholder test.
9. Inspect source/test diff for deleted tests, weaker assertions/oracles, reduced
   source lock or Design changes used to manufacture PASS.
10. Confirm an accurate product fail may have Artifact Gate pass, while
    early-stop/product fail/unresolved Return is never RLS-ready.
11. Verify manual/hybrid Evidence is not synthesized. Fixture boundary tests
    must not be reported as real human acceptance.
12. Verify SpringGear and gin-vue-admin each executed the complete
    CTX→REQ→DSN→PLN→IMP→VFY chain at the exact fixed SHA and at least two
    independently auditable Method Types.
13. Verify external cleanup: HEAD, refs, status, tracked/untracked digest and
    `.sdlc`; no remote write or dependency installation.
14. Verify production runtime does not read `docs/**`, no Workflow was added,
    and no RLS implementation exists.
15. Verify current `main` was not modified by the local Goal and both PR
    base/head pairs are correct.
16. Verify the implementation PR remains Draft unless this review accepts it.

## Decision

When any defect exists:

```text
WEB_VFY_REVIEW = CHANGES_REQUIRED
```

Keep the PR Draft. List the exact file, line/object, Critical Case, violated
contract and necessary repair. Require the local Goal to rewrite the
Implementation Subject when source changes and regenerate all affected Evidence.
Do not treat the old PASS report as valid.

Only when every check passes:

```text
WEB_VFY_REVIEW = ACCEPTED
```

Update the PR body with accepted Subject/Evidence SHAs and review result. The PR
may be marked Ready for Review, but do not merge it and do not start RLS.

Provide a compact verification ledger with SHA, tree, ancestry, 80/80 result,
all profiles, Evidence digest, external projects, main/PR state and prohibitions.
