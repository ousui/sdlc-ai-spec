# Local Codex `/goal` — close `sdlc-500-vfy`

Copy the complete prompt below into a local Codex `/goal` session after the VFY
design PR has been merged into `main` with **Create a merge commit**.

---

You are the execution and closed-loop owner for `ousui/sdlc-ai-spec`
`sdlc-500-vfy`.

## Goal

Take the existing initial implementation on `impl/vfy-v2`, repeatedly run real
validation, fix the first actual failure without weakening authority, produce a
fresh exact-SHA attestation, append formal Evidence/Handoff on the same branch,
and update the existing Draft PR. Finish only as `VFY_CLOSED_LOOP = PASS` or
`VFY_CLOSED_LOOP = HARD_BLOCKED`.

## Non-negotiable authority

```text
docs/v1.1/500-vfy-spec.md
> bundled stable runtime contracts
> integrated IMP runtime
> formal IMP Handoff/Evidence
> merged VFY DESIGN.md and EVAL-PLAN.md
> docs/plugin-development/work-items/sdlc-500-vfy/goal/**
```

Historical IMP handoff ancestry is not current Git instruction.

```text
Git physical base initially observed = 3a2f13082fe2f661081ded74e45f860da2046bd1
Semantic IMP implementation subject = 207a4a16bea8979faee0474cc43cb642cef1f655
IMP delivery checkpoint              = 86aaa04a0238d3151606073e89219eea0d60b7d3
Implementation branch                = impl/vfy-v2
PR base                              = main
```

Re-read all remote values at start. Never assume the observed values remain current.

## Start gate

1. Locate the repository and verify its Git root.
2. `git fetch --prune` without changing `main`.
3. Verify the design PR is merged by a merge commit and current `main` contains
   `docs/plugin-development/work-items/sdlc-500-vfy/goal/11-DESIGN-HANDOFF.md`.
4. Verify `impl/vfy-v2` contains exactly the initial implementation ancestry
   rooted at the design head and has no Evidence commit.
5. Record current main/head/tree, Draft PR number/body, and a force-with-lease
   expected old SHA.
6. Create or reuse one persistent dedicated Worktree for `impl/vfy-v2`; do not
   work in the user's active checkout.
7. Preserve unknown local changes; if the dedicated Worktree is dirty for an
   unknown reason, stop `HARD_BLOCKED` rather than deleting them.
8. Confirm no RLS implementation, VFY evidence branch or new Workflow exists.

## Validation controller

Use only:

```bash
python3 tools/run_vfy_delivery_validation.py \
  --profile <quick|phase|full|external|attest> \
  --source-sha "$(git rev-parse HEAD)" \
  --json-out "<path>"
```

Run in order:

```text
quick → phase → full → external → attest
```

`external` uses exact projects:

```text
ousui/springgear@e855096ff19dcdb303dc4250ba19c30acd743ac7
flipped-aurora/gin-vue-admin@a6882210a80bb27e3aa5dff0b4c21aa4afe8988a
```

Each must execute CTX→REQ→DSN→PLN→IMP→VFY and at least two independently
auditable Method Types. A commit-read probe is not acceptance.

## Fix loop

On every failure:

1. read the first actual failed command, log and nested oracle;
2. identify the violated Spec/Design clause and affected Critical Case;
3. make the smallest implementation or legitimate fixture correction;
4. do not delete, skip or expected-failure a test;
5. do not weaken an assertion, expected result, case mapping, source lock,
   Runtime Independence check or Design Authority;
6. do not fabricate manual/hybrid Evidence;
7. do not add dependency installation, GitHub Actions authority, upstream Skill
   execution, RLS or product release;
8. run the smallest impacted profile, then all invalidated downstream profiles;
9. keep exact logs of every attempt.

DNS and HTTP 502/503/504 may be retried at most three times with recorded bounded
backoff. Deterministic failures and other HTTP errors are not retried as noise.

## Subject commit management

Before formal Evidence exists, consolidate all source/test/tool fixes into one
commit:

```text
feat(vfy): implement deterministic verification phase
```

Its direct parent must be the final design commit. Use `commit --amend` or
rebuild the single Subject commit as needed. Before each remote rewrite:

```bash
git fetch origin impl/vfy-v2
git push --force-with-lease=refs/heads/impl/vfy-v2:<expected-old-sha> \
  origin HEAD:refs/heads/impl/vfy-v2
```

On lease failure, stop with `HARD_BLOCKED`; never overwrite remote drift. After
every rewrite, discard all validation/evidence produced for the prior SHA and
restart every affected profile.

## Fresh exact-SHA attestation

When quick/phase/full/external pass:

1. freeze the candidate Implementation Subject SHA;
2. create a fresh detached persistent attestation Worktree at that exact SHA;
3. ensure clean status and exact expected tree;
4. run `attest`, which must itself run/verify all required profiles;
5. verify 80/80 unique Critical Cases, no skip/expectedFailure;
6. verify both real projects and complete cleanup;
7. verify no main write, remote project write, dependency install, Workflow or RLS;
8. perform an independent design/correctness review with Blocker=0, Major=0.

Any source change unfreezes the Subject and restarts this section.

## Evidence/Handoff commit

Only after fresh exact-SHA PASS, generate:

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

Requirements:

- every report `source_sha` equals the frozen Implementation Subject;
- `vfy-verification-result.json` validates against the design schema;
- SHA-256 manifests use repository-relative names and verify;
- manual Evidence is present only when actually supplied; negative fixtures do
  not claim a real human acceptance;
- Handoff distinguishes Implementation Subject from Evidence Delivery Head;
- final result contains only `PASS`, never partial/skipped;
- no implementation/test/tool file changes in this commit.

Commit:

```text
chore(vfy): archive verification evidence and handoff
```

This commit's direct parent is the frozen Implementation Subject. Never amend or
overwrite it with a later Subject rewrite. Push it fast-forward to the same
`impl/vfy-v2`; do not create an Evidence branch.

## Draft PR

Update the existing `impl/vfy-v2 → main` PR:

- keep Draft until Web review accepts;
- record design merge commit, Implementation Subject and Evidence Delivery Head;
- record all exact validation results and paths;
- state GitHub Actions are not authority;
- state RLS not started;
- never merge the PR.

## Absolute prohibitions

Do not modify or merge `main`; do not rebase after design merge; do not create
`impl/vfy-v2-evidence`, `internal/*`, Observer, Finalizer, Materializer, Payload,
Chunk or Release Asset; do not create a Workflow; do not auto-push main or merge
a PR; do not enter RLS.

## Terminal output

Success:

```text
VFY_CLOSED_LOOP = PASS
VFY_IMPLEMENTATION_SUBJECT_SHA = <sha>
VFY_EVIDENCE_DELIVERY_HEAD_SHA = <sha>
CRITICAL_CASES = 80/80 PASS
QUICK = PASS
PHASE = PASS
FULL = PASS
EXTERNAL = PASS
ATTEST = PASS
MAIN_MODIFIED = NO
PR_MERGED = NO
RLS_STARTED = NO
```

Failure after bounded recovery:

```text
VFY_CLOSED_LOOP = HARD_BLOCKED
FIRST_REAL_BLOCKER = <command/file/case/error>
LAST_SAFE_SUBJECT_SHA = <sha>
REMOTE_HEAD = <sha>
REF_DRIFT = <YES|NO>
RECOVERY = <exact safe steps>
```

Do not finish with RUNNING, PENDING or “wait for GitHub”.
