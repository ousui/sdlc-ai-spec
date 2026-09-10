# Repeatable upstream upgrades

## What is locked

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
python3 -B tools/upgrade.py prepare \
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
python3 -B tools/upgrade.py accept \
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
