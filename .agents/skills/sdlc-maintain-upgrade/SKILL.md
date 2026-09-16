---
name: sdlc-maintain-upgrade
description: Explicit maintainer workflow for upgrading this SDLC AI SPEC repository to a selected stable Spec Kit version and returning a verified candidate diff; not for upgrading dependencies or business projects.
disable-model-invocation: true
argument-hint: "[latest|vX.Y.Z|tag|commit]"
---

# SDLC AI SPEC Maintainer Upgrade

Run this skill only when the user explicitly invokes `sdlc-maintain-upgrade` to maintain the **SDLC AI SPEC source repository itself**. It is not a numbered SDLC phase and must never be used to upgrade a business project's dependencies, runtime, framework, `.sdlc` data, or application version.

The user's target is: `$ARGUMENTS`.

## Authority and invariants

1. User instructions for this maintenance run take precedence over defaults in this skill, subject to repository permissions and safety constraints.
2. Read the repository-root `AGENTS.md`, then `README.md`, `docs/DEVELOPMENT.md`, `docs/UPGRADING.md`, `docs/LOCALIZATION.md`, `docs/NAMING.md`, `docs/naming-map.json`, `plugin-metadata.json`, and `upstream.lock.json` before writes.
3. The authoritative deterministic tools are `tools/upgrade.py`, `tools/localize.py`, `tools/port.py`, `tools/build.py`, and `tools/verify.py`. Do not duplicate or weaken their rules inside this skill.
4. Preserve the existing 11 public product Skills and their execution behavior. This maintenance Skill is repository infrastructure and must never enter `dist/skills`, product manifests, or Marketplace skill inventory.
5. Never modify tests, checkers, ignore rules, adapters, or accepted product behavior merely to make a target upstream version pass. A required change outside the approved localization recovery path is a separate maintenance change and this run stops with `REVIEW_REQUIRED`.
6. Default completion is a **verified, uncommitted detached candidate plus a concise difference report**. Do not call formal `upgrade.py accept`, commit the candidate, push, merge, tag, release, or rewrite the source worktree unless the user separately authorizes that effect.
7. Do not read or modify real business project `.sdlc` data during this workflow.

Read `references/review-checklist.md` before semantic review and use `references/report-template.md` for the final report.

## 1. Repository preflight

Resolve the Git repository root and stop unless all are true:

- `plugin-metadata.json` names `sdlc-ai-spec`;
- `tools/upgrade.py`, `tools/localize.py`, `tools/verify.py`, and `upstream.lock.json` exist;
- the selected source worktree is clean, unless the user explicitly supplied another clean checkout for this maintenance run;
- the current HEAD, branch/ref, product version, locked upstream tag/version/SHA, Python and uv identities are recorded before work starts.

Do not clean, stash, reset, checkout another branch, or discard unrelated user work automatically.

## 2. Resolve one exact target upstream

The upstream repository comes from `upstream.lock.json`. A repository change is structural scope change and requires explicit review.

- For an explicit tag/version, resolve that exact ref.
- For `latest`, inspect official upstream stable tags and choose the highest stable release only; exclude prerelease/dev refs. Resolve it once and freeze the selected tag, commit SHA, and package version for the run.
- For an explicit commit, use the exact commit and read the package version from that checkout; never infer package version from the ref string.
- Never follow upstream `main` implicitly.

Use a new clean upstream checkout outside this repository and a new run directory outside both source and upstream checkouts. Keep raw evidence outside the repository.

If the resolved target is identical to the currently locked upstream, treat the run as a same-version rehearsal unless the user explicitly requested another purpose.

## 3. Review the upstream delta before candidate generation

Compare the currently locked exact SHA to the frozen target SHA. Review actual source changes, not only release notes.

Classify changes across:

- core command inventory and `templates/commands/*.md`;
- templates and Bash runtime sources copied by the lock;
- all `watch_files` and any newly relevant transitive generator/integration dependency;
- CLI/package metadata and version;
- initialization, event, host integration and invocation behavior;
- license/provenance.

Continue automatically only when the existing supported profile remains valid: Bash, core commands, `events=false`, no presets/extensions, and current approved naming/path projections.

Return `REVIEW_REQUIRED` before changing the accepted source when any of these occurs:

- core command added, removed, renamed, or re-scoped;
- `.sdlc` project-data layout or formal artifact path/schema changes;
- new or changed machine identifiers, enums, placeholders, protocol/config keys, or structural aliases that need a new approved mapping;
- existing adapter anchor or host rendering no longer applies exactly;
- current profile can no longer be preserved;
- upstream license/provenance changes materially;
- the impact cannot be determined confidently from source.

Do not classify risk from line count alone.

## 4. Generate the detached candidate

From the clean accepted source checkout, run the repository's locked environment and existing prepare command:

```sh
uv sync --locked
uv run --locked python -B tools/upgrade.py prepare \
  --upstream "$UPSTREAM" \
  --ref "$TARGET_REF" \
  --out "$CANDIDATE"
```

`$CANDIDATE` must be a new external directory. Read the command exit status, the candidate worktree state, and the sibling `*.upgrade.json`; do not manufacture a status when prepare fails before a record exists.

Interpret the resulting state:

- `CANDIDATE_READY`: proceed to independent verification.
- `LOCALIZATION_REQUIRED`: inspect the actual failure and enter section 5 only if the candidate is recoverable through localization alone.
- `BLOCKED` or missing record: preserve evidence and stop with `REVIEW_REQUIRED` unless the failure is a clearly transient environment failure that can be retried without changing source or policy.

## 5. Incremental localization recovery

Only this state authorizes edits to the candidate, and only inside:

```text
<CANDIDATE>/src/locales/zh-CN/**
```

Do not edit candidate `tools/`, tests, adapters, upstream source, derived English templates/scripts, `dist/`, lock data, or the upgrade record.

### 5.1 Export and identify stale items

Using the **candidate's** tool, export current English inputs to a new external directory:

```sh
uv run --locked python -B tools/localize.py export --out "$TRANSLATION_INPUTS"
```

Compare current source hashes/metadata with the candidate catalog and identify only affected commands, presentations, and source-backed resources. Reuse unchanged translations and review records; do not re-record everything just because the upstream repository SHA changed.

### 5.2 Translate incrementally

For each affected item, compare old English, new English, and old Chinese. Update only the changed natural-language presentation while preserving machine contracts and approved read aliases. If upstream metadata description changes, update its recorded source and reviewed Chinese value deliberately.

Do not invent new `structural_aliases` or input aliases. Unknown required aliases make the run `REVIEW_REQUIRED`.

### 5.3 Run read-only precheck before approval

For every changed item, run the candidate's read-only precheck:

```sh
uv run --locked python -B tools/localize.py precheck --command NAME
uv run --locked python -B tools/localize.py precheck --presentation NAME
uv run --locked python -B tools/localize.py precheck --resource NAME
```

Use the appropriate selector. Precheck must not modify `catalog.json`. Machine/structure failure means fix the translation or stop; never edit the checker or exception policy inside the upgrade run.

### 5.4 Perform a separate semantic review

After precheck, reread the complete **new source** and complete proposed Chinese text independently from the translation step. Apply `references/review-checklist.md`, especially:

- MUST / MUST NOT and other obligations/prohibitions;
- actors and ownership;
- quantities, limits, defaults, booleans and status meaning;
- wait/stop/continue semantics;
- write targets and authorization boundaries;
- command/path/identifier compatibility;
- legacy English input compatibility.

If the same Agent performs translation and review, report that accurately; do not call it independent-model evidence. Any uncertain high-impact semantic difference is `REVIEW_REQUIRED`.

### 5.5 Record only completed reviews, then run full check

Record each actually reviewed changed item with an honest reviewer string that identifies this AI-assisted maintenance review; never reuse an older `User-approved` identity for new bytes.

Examples:

```sh
uv run --locked python -B tools/localize.py record \
  --command NAME --reviewer "sdlc-maintain-upgrade AI review" --reviewed

uv run --locked python -B tools/localize.py record \
  --presentation NAME --reviewer "sdlc-maintain-upgrade AI review" --reviewed

uv run --locked python -B tools/localize.py record \
  --resource NAME --reviewer "sdlc-maintain-upgrade AI review" --reviewed
```

After all affected items are recorded:

```sh
uv run --locked python -B tools/localize.py check
```

Do not use `record` as proof that translation semantics are correct; it records the review after precheck and semantic review.

### 5.6 Refresh the frozen candidate

Compute the candidate localization digest with the repository's existing implementation, create an external `refresh-localization` review JSON bound to the exact target upstream SHA and exact localization bytes, then run:

```sh
uv run --locked python -B tools/upgrade.py refresh-localization \
  --record "$UPGRADE_RECORD" \
  --review "$TRANSLATION_REVIEW"
```

The non-localization freeze must still match. A changed frozen input means stop and prepare again from an accepted source change; do not patch around the freeze.

Any evidence from before refresh is stale.

## 6. Create independent target baselines

Install the exact frozen target upstream checkout into a fresh isolated Python 3.12 environment outside source and candidate. Generate three **new** empty-project baselines using:

- `codex`
- `claude`
- `cursor-agent`

with Bash, `--events=false`, no presets/extensions, and the same documented init options used by `docs/DEVELOPMENT.md` / CI.

Do not build an oracle from this project's migrated output. Do not reuse baselines from another upstream SHA.

## 7. Verify the exact candidate

Run the **candidate's** verifier using the exact target checkout and newly created baselines, with evidence outside both repositories:

```sh
uv run --locked python -B tools/verify.py \
  --upstream "$UPSTREAM" \
  --baselines "$BASELINES" \
  --evidence "$EVIDENCE"
```

Also run the repository's relevant locked tests and `git diff --check` as required by current maintenance docs.

A successful report must bind:

- exact candidate `source_digest` / `candidate_digest`;
- exact target upstream SHA;
- the complete required verification contract/groups;
- nonzero unit/runtime and differential evidence;
- distribution inventory and environment identity;
- explicit `not_performed` items.

Do not truncate or hand-edit verifier JSON into a PASS.

If verification fails, preserve evidence and classify the cause. Localization may return only through the documented localization recovery path with new digest/evidence; adapter/code/mapping/checker/test changes are a separate maintenance work package and require a fresh candidate. Do not make the upgrade pass by weakening checks.

## 8. Default final report and stop boundary

Use `references/report-template.md`. Report:

- accepted source branch/HEAD and locked upstream identity;
- frozen target tag/ref, exact SHA, package version and resulting candidate product version;
- upstream change classification and any behavior changes adopted;
- localization items changed and actual reviewer identity;
- candidate path and exact digest;
- tests/verifier evidence and environment;
- files/areas intentionally out of profile;
- maintenance documents that need synchronization after candidate acceptance;
- every action not performed.

Default terminal state is one of:

- `VERIFIED_CANDIDATE_READY`
- `REVIEW_REQUIRED`
- `BLOCKED`

`VERIFIED_CANDIDATE_READY` does **not** mean source branch upgraded, candidate accepted, main merged, release published, clients reloaded, or business projects migrated.

Stop here unless the user separately authorizes candidate acceptance/integration/release effects.
