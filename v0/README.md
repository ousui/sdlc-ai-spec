# SDLC v0 — Spec Kit core source port

Repository: **https://github.com/ousui/sdlc-ai-spec**

This is an **engineering-stage source port**, not an end-user release. It moves
Spec Kit's core resources into user-scoped plugin packages while keeping project
state under `.sdlc`. It does not include `sdlc-init` yet. Do not install the legacy
plugin at this repository's root as a way to test this implementation.

## Scope

Pinned upstream: `github/spec-kit` `v1.0.5`, commit
`a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`.

Nine core skills: constitution, specify, clarify, plan, tasks, analyze, checklist,
implement, converge. English source instructions and template content are retained;
only documented name, path, resource-binding and packaging changes are made.
`taskstoissues`, GitHub integration, events, presets/extensions installation,
workflow engines, translation, legacy SDLC runtimes and INIT are out of scope.

## Layout

- `src/commands/`: unchanged upstream English command source, NOT installed output.
- `src/templates/`: upstream templates with feature-document paths relocated.
- `src/scripts/bash/`: upstream Bash scripts with reviewed address changes.
- `src/scripts/python/path_guard.py`: small stdlib-only read-only path guard.
- `adapters/`: common binding text and the explicit global-resource path patches.
- `tools/port.py`: reproduce the reviewed source migration from pinned source.
- `tools/build.py`: independent renderer; no specify-cli imports or initialized projects.
- `tools/verify.py`: source, installed-tool differential and synthetic fixture checks.
- `dist/codex/`, `dist/claude/`, `dist/cursor/`: self-contained generated packages.
- `upstream.lock.json`: selected upstream source identities and profile.

Codex/Cursor use a root `plugin.json` in the Agent Plugins 1.0.0 format; Claude
uses `.claude-plugin/plugin.json`. Core content is shared, but command references
are rendered for each host (`$sdlc-*`, `/sdlc:sdlc-*`, `/sdlc-*`). Metadata mirrors
the respective upstream integration. A valid manifest is not proof of actual host
loading or invocation; those checks are explicitly deferred.

## Runtime boundary

The package contains all core scripts and templates. A project does not receive
copies of them, agent skill directories, a global current-feature file, or an
absolute plugin installation path. Plugin resources are not written at runtime.
The current feature and project constitution remain in `.sdlc`.

Run resources by absolute package path with the business project as the working
directory. The small `project-paths.sh` helper only resolves/checks paths; it does
not create project state and is not an initializer. Uninitialized or invalid
projects fail instead of falling back to the plugin's directory. The actual
loaded Skill path, or Claude's documented plugin variable, identifies the package;
no invented Codex/Cursor plugin environment variable is assumed.

Runtime dependencies: Bash, Python 3.9+ (stdlib only for the guard), and the
standard POSIX commands used by upstream scripts. `jq` is optional as upstream
provides fallbacks. The selected core profile needs neither `uv`, `specify-cli`
nor PyYAML at runtime. Development tooling uses Python 3.11+ and the packages in
`tools/requirements.txt`. Windows/PowerShell is outside this engineering profile.

## Reproduce engineering verification

Use a separate temporary workspace, not a business project. Check out the exact
upstream commit into `$UPSTREAM`, install it in an isolated tool environment,
then run the following once in EACH of three independent empty directories:

```sh
# Substitute exactly one actual agent name in each empty directory.
specify init . --integration codex --script sh --ignore-agent-tools \
  --non-interactive --integration-options="--events=false"
# Repeat separately with claude and cursor-agent.
```

Keep these directories as `$BASELINES/codex`, `$BASELINES/claude`, and
`$BASELINES/cursor-agent`. No Agent or LLM is launched by these CLI init calls.
They are an independent oracle, not the port's source.

From the repository root, with build dependencies installed in an isolated env:

```sh
python -B v0/tools/port.py --upstream "$UPSTREAM"
python -B v0/tools/build.py
python -B v0/tools/verify.py --upstream "$UPSTREAM" \
  --baselines "$BASELINES" --evidence "$EVIDENCE_OUTSIDE_REPO"
git diff --check
```

Verification does not execute a real development requirement. Synthetic fixtures
create only temporary test directories. No INIT Skill, real-project verification,
LLM execution, native host discovery, plugin marketplace publication, or production
access is claimed. See `MIGRATION.md` for the exact allowed differences.

The `.github/workflows/v0-engineering.yml` workflow installs the pinned upstream,
collects all three empty-project baselines and verifies the checked-in packages.
Evidence is an Actions artifact tied to its source SHA; passing baseline
acquisition alone is not treated as passing migration validation.

## Upstream attribution

Spec Kit is MIT-licensed, copyright GitHub, Inc. Its license is retained in
`src/LICENSE` and in every generated package. Port/build tools in this subtree
are also distributed under those terms. Upstream provenance strings are retained;
this port is not represented as an official GitHub, OpenAI, Anthropic or Cursor release.
