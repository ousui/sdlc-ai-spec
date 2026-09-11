# Repeatable upstream upgrades

## What is locked

## Development-tool environment

Run upgrade tooling through the repository's locked uv project: `uv sync --locked`
then `uv run --locked ...`. The candidate's upstream CLI remains an independently
created `uv venv` / `uv pip` environment as documented in DEVELOPMENT.md. uv is
never added to the installed `dist` runtime. Changes to `pyproject.toml`, `uv.lock`
or `.python-version` are reviewed build inputs and must remain synchronized.

`upstream.lock.json` records the exact Spec Kit commit, the selected Bash/core-only
profile, copied source identities and watched renderer/integration identities.
`src/upstream/` retains those original bytes, including their original licenses.
Derived source lives in `src/templates/` and `src/scripts/`; nine commands are
read directly from `src/upstream/templates/commands/`. `adapters/` holds reviewed
changes; `tools/port.py` applies strict anchors. `dist` is generated, not edited.

Watched files include `integrations/base.py`, `agents.py`, the Codex/Claude/Cursor
integrations, invocation styles, init, shared infrastructure, and events. A watch
change requires review even when a patch still applies. Review the transitive
imports if those files start depending on additional generator modules. This is
not a claim that a fixed watch list can detect every future upstream architecture.

## Prepare (no overwrite, no downloads)

Use a clean checkout of this repository and a separately obtained, clean upstream
Git checkout. The maintainer fetches/selects a release explicitly. Never follow
`main` automatically or delete the accepted lock to bypass validation.

```sh
uv sync --locked
uv run --locked python -B tools/upgrade.py prepare \
  --upstream /absolute/path/to/spec-kit \
  --ref <EXACT_COMMIT_OR_TAG> \
  --out /absolute/path/outside/this-repo/sdlc-candidate
```

The selected ref must equal upstream HEAD. The command creates a detached Git
worktree from the current accepted commit, writes its candidate lock, materializes
source, builds one package and generates marketplaces. A sibling file
`sdlc-candidate.upgrade.json` records source/base identity, all changed watched or
copied paths, readiness and exact content/mode fingerprint. The active worktree,
its branch and accepted dist remain untouched. A failure leaves a BLOCKED
candidate for inspection, not a half-updated accepted product.

New core commands, changed patch anchors, host line-structure differences,
missing watched modules or unknown source inventory are review events. Do not
silently exclude them or loosen parity checks. If adapter code must change,
review and commit that change first, then prepare a fresh candidate.

## Verify independently

Install the candidate's exact upstream in an isolated tool environment and
initialize three NEW empty directories with Codex, Claude, Cursor, Bash,
`--events=false`, no presets/extensions. Run the candidate's `tools/verify.py`
against those outputs; use evidence outside both worktrees. See
[DEVELOPMENT.md](DEVELOPMENT.md). Never build from these initialized directories;
they are an independent oracle.

The report must bind `source_digest` to the complete candidate bytes and executable
modes, including dist, not merely claim PASS at the previous source commit. A
same-version replay is an engineering regression, not acceptance of a new version.
Existing synthetic project fixtures cover continued use of the established
`.sdlc` format. A real format incompatibility requires a separate explicit project
data migration; updating/installing the plugin must not rewrite users' projects.

## Review and accept

Inspect ALL changed original code, especially whole functions replaced by port
patches: an upstream function can keep its name while adding a necessary fix.
Also inspect original new English instructions; do not normalize away behavioral,
permission, checklist ownership or stop-condition changes.

Create an external review JSON after that review:

```json
{
  "decision": "accept",
  "reviewer": "<maintainer>",
  "candidate_digest": "<from the candidate record and verifier>",
  "reviewed_paths": ["<every changed upstream path, exactly once>"]
}
```

```sh
uv run --locked python -B tools/upgrade.py accept \
  --record /absolute/path/sdlc-candidate.upgrade.json \
  --evidence /absolute/path/candidate-evidence/result.json \
  --review /absolute/path/review.json --check
```

After a successful check, the same command without `--check` commits ONLY the
candidate detached worktree using the maintainer's Git identity. It never pushes,
merges, changes the current branch, or creates/moves tags. Integrate that exact
candidate commit through the normal reviewed Git process. Until then members
continue to install the accepted dist. `accept` rejects changed candidate bytes,
stale reports, incomplete reviews, a moved source HEAD or a dirty source tree.
The JSON review is an explicit local workflow record, not cryptographic identity
or a security boundary against a developer who controls the machine.

## Version and rollback

Product version stays `1.0.0-beta` in this debugging period. It is independent of
the upstream tag; do not mix the two. Record commit and BUILD.json build_id.
Rollback is selecting an earlier accepted source/distribution commit, followed by
client-specific cache reload/reinstall verification. Do not delete project data.

## Source map

| Upstream | Local derivation | Verification |
| --- | --- | --- |
| templates/commands/*.md | original source -> source renderer -> host factoring | resolved full bodies vs 3 installed CLI baselines |
| templates/*-template.md | default feature path and logical capability IDs | exact text except explicit path/reference projection |
| scripts/bash/*.sh | strict port anchors and global-resource binding | source deltas + return codes, output and files on fixtures |
| integrations/base.py, agents.py, three integrations | watched original source -> reviewed renderer/adapters | each host's metadata and original generated body |
| LICENSE | unchanged in source and dist | byte equality |

Source copying, rendering, factoring, manifests and comparison are deterministic.
AI is not invoked by any tool. A future unsupported upstream change stops the
candidate; it does not trigger an uncontrolled AI rewrite.

## Local initializer across upgrades

`init` is a local command, not part of the upstream command inventory. Preserve
`adapters/INIT.md`, `src/scripts/python/init_project.py` and its tests during
candidate generation. Changes to watched upstream `commands/init.py` require
review of the project-data projection (template seeding and defaults), not a
blind copy of the installer. Reinitialization does not rewrite an existing
project to the new upstream version or reset documents; layout incompatibility
needs a separate migration, never an implicit action of plugin installation.

Upstream package version is read from watched `pyproject.toml` and recorded
separately from the tag/ref. Preparing an upgrade by exact SHA must not write that
SHA into project `speckit_version`. INIT retains existing project defaults; it
does not silently run a data migration after a package update.

## Mandatory naming projection

Read [NAMING.md](NAMING.md) and [naming-map.json](naming-map.json) before changing
the upstream version. `tools/naming.py` applies the reviewed mapping after raw
source rendering; `tools/naming_check.py` is an independently maintained finite
comparison oracle. The build identity includes the naming map. Upstream locks
and copied source paths retain original names, while generated workflows use
`references/workflows/<full-skill-id>.md` and loader calls use the same public ID.
Unknown source references must stop preparation; never infer new abbreviations
or weaken full-body parity to accept a candidate. See PR #24 for execution evidence.

## Shared entrypoints and localized candidate resumption

Current distribution uses eleven public entries under `dist/skills/`, including
local INIT and STATUS, with no host-private wrappers. Original English source rendering
is still independently checked; Chinese source assets are version-bound in
`src/locales/zh-CN`. No translation service runs during build or installation.
English template skeletons and existing project data remain unchanged.

A changed upstream input can now stop preparation as `LOCALIZATION_REQUIRED`.
Only the candidate translation subtree can be edited in this state. After explicit
translation review, `tools/upgrade.py refresh-localization --record ... --review ...`
validates frozen non-translation inputs, rechecks Chinese and rebuilds the candidate.
It creates a new candidate digest, not a new accepted version. Old test evidence
must not be reused. Full commands and the review record format are in
[LOCALIZATION.md](LOCALIZATION.md). Review strings are workflow records, not auth.

The original "candidate must not be edited" rule still applies outside this
explicit, narrow translation-resumption path. Changed adapter/code requires a
reviewed source update and freshly prepared candidate, not a digest edit.

## Unified public inventory and STATUS

The current package exposes exactly eleven entries under `dist/skills`: nine
upstream core Skills plus local INIT and STATUS. There are no private host Skill
wrappers. All public entries omit user-invocable, disable-model-invocation and
argument-hint; host defaults apply. This supersedes earlier descriptions of the
INIT policy exception, not the existing INIT data-preservation contract.
Claude uses default skills/ discovery without a duplicate custom path. Other
manifests select ./skills/. All wrappers resolve the package two levels up.

STATUS is an optional local read-only utility, not another lifecycle phase or an
upstream command. It tolerates incomplete/uninitialized state, never persists a
feature switch, never initializes, and never executes the suggested next Skill.
See [STATUS.md](STATUS.md). Existing core bodies/templates and runtime behavior
are not modified to store history for STATUS.

Upgrades must retain adapters/STATUS.md, src/locales/zh-CN/status.md and its local
resource catalog record, src/scripts/python/project_status.py and its tests.
These are local sources, not copied upstream commands. Materialization rebuilds
the same eleven-entry package without overwriting this utility. Source changes
that affect field interpretation require STATUS compatibility review and tests;
do not silently migrate business data. The existing localization refresh path
remains scoped to reviewed locale changes. No new release/permission platform
is introduced in this iteration.
