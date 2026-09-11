# Development and engineering verification

## Metadata and layout

`plugin-metadata.json` at the repository root is the single source for the plugin
name, version (`1.0.0-beta`), author (Blade), declared repository and license.
Use `v1.0.0-beta` as a display label; machine manifests use `1.0.0-beta`.
Do not increment the version during this debugging period or create/move a tag
as part of an ordinary code change. Use the exact commit SHA to identify builds.

The root contains the implementation. `src/upstream/templates/commands` retains original English
source; `src/templates` and `src/scripts` contain documented port deltas.
`adapters/` supplies resource binding and host differences. `tools/build.py`
generates a single self-contained `dist` package and three thin native entrypoint sets,
without importing the upstream CLI or reading initialized projects. Use `--marketplaces`
to also regenerate the three repository-root catalogs.
There is no root plugin manifest because the root is a source/build workspace.

All three native manifests declare `skills: ./adapters/<host>/skills/` inside
the same dist package. No portable root manifest/default skills scan is shipped.
The loaded wrapper pins its host and reads the complete, deterministic loader
output. The shared workflows plus literal fragments reconstruct each formerly
expanded host body exactly; this is tested against installed upstream output.
[Installation](INSTALLATION.md) lists current official format references.

## Development environment: uv only

Development, build, test and verification dependencies outside `dist/` are managed
by **uv**. `pyproject.toml` declares direct development dependencies; committed
`uv.lock` locks their transitive graph. `.python-version` selects Python 3.12 as
the canonical development interpreter while the project accepts Python 3.11–3.15.
The tooling project version `0.0.0` is not the plugin/product version; product
metadata remains authoritative in `plugin-metadata.json`.

Use uv `0.12.13` or another compatible `0.12.x` version allowed by
`tool.uv.required-version`:

```sh
uv sync --locked
uv run --locked python -B tools/build.py --marketplaces
uv run --locked python -B -m unittest discover -s tests -v
git diff --check
```

`uv sync` creates/manages `.venv`; activation is unnecessary. CI pins uv exactly
to `0.12.13` and uses `--locked`, so stale or missing lock changes fail closed.
When dependencies change, update `pyproject.toml`, run `uv lock`, review `uv.lock`,
and commit both together. `tools/requirements.txt` is intentionally absent; do
not add a second dependency source of truth.

`dist/` does **not** use uv at runtime and does not ship `pyproject.toml`, `uv.lock`,
`.python-version`, or a virtual environment. Installed plugin requirements remain
Bash, Python 3.9+ and standard POSIX tools. Build metadata may record the hashes
of the uv project files as reproducibility inputs; that is not a runtime dependency.

## Reproduce source materialization

Obtain the upstream commit recorded in `upstream.lock.json` in a separate checkout.
Run the commands below with its absolute path; the tool checks the selected source
hashes against the lock.

```sh
uv sync --locked
uv run --locked python -B tools/port.py --upstream "$UPSTREAM"
uv run --locked python -B tools/build.py --marketplaces
```

Do not use upstream initialized output to construct the port. It is an independent
comparison baseline only. Do not introduce CLI callbacks into runtime scripts.

## Independent installed-tool comparison

Use three new empty directories and a separate uv-created upstream tool environment,
all outside this repository and outside business projects. Set absolute paths for
`UPSTREAM`, `TOOL_ENV`, `BASELINES` and `EVIDENCE` first. The upstream checkout must
be exactly `a4e25ce6b96dc8e85f84206c6a54353fa9c5260b` (Spec Kit `v1.0.5`).

```sh
test "$(git -C "$UPSTREAM" rev-parse HEAD)" = a4e25ce6b96dc8e85f84206c6a54353fa9c5260b
uv sync --locked
uv venv "$TOOL_ENV" --python 3.12
uv pip install --python "$TOOL_ENV/bin/python" "$UPSTREAM"
"$TOOL_ENV/bin/specify" version
for agent in codex claude cursor-agent; do
  mkdir -p "$BASELINES/$agent"
  (cd "$BASELINES/$agent" && "$TOOL_ENV/bin/specify" init . \
    --integration "$agent" --script sh --ignore-agent-tools \
    --non-interactive --integration-options="--events=false")
done
uv run --locked python -B tools/verify.py --upstream "$UPSTREAM" \
  --baselines "$BASELINES" --evidence "$EVIDENCE"
git diff --check
```

`uv pip` is used only for the explicitly isolated upstream CLI environment; it
does not replace the repository project's lockfile. Use Bash with no events,
presets or extensions. These upstream CLI calls do not launch Codex, Claude or
Cursor. Their project settings and constitution are independently compared with
our local `sdlc-000-init` output; host registries and installed tool resources are
intentionally excluded. Always use new empty baseline directories.

## CI and evidence

`.github/workflows/engineering.yml` fetches the triggering repository's exact
commit and the pinned upstream, installs the pinned uv version, runs
`uv sync --locked`, creates an isolated upstream CLI environment with `uv venv` /
`uv pip`, initializes three empty projects and verifies already committed packages.
It must not regenerate and commit packages in CI or silently skip checks when
files are absent.

The workflow has read-only repository permissions. Source transport uses
`GITHUB_REPOSITORY`; package metadata uses the separately declared repository.
This permits verification before or after an explicit repository transfer without
claiming that the transfer happened. No production credentials are required.

Evidence is uploaded as `sdlc-engineering-<source-sha>` and includes installed-tool
logs, baseline hashes, the source snapshot and verifier results. The report records
source SHA, actual source repository, declared repository, product version,
environment, individual checks and distribution hashes. See VERIFICATION.md.

## Upgrade a pinned upstream

Do not edit hashes to make a check pass. Follow [UPGRADING.md](UPGRADING.md): prepare
a detached candidate, compare installed tool outputs, review changed original
source and accept only exact verified bytes. BUILD.json identifies a reproducible
build while the beta product version remains fixed.

## Local project initializer

`adapters/INIT.md` is a local workflow, not a tenth upstream command.
`src/scripts/python/init_project.py` is its deterministic stdlib-only implementation.
The build generates three thin entries and one shared init body, through the same
loader as the nine upstream commands, but without the initialized-project gate.
`COMMANDS` and the upstream lock stay at nine; `ALL_COMMANDS` adds local INIT for
package inventory. Upgrade preparation must retain this local source and its tests.

`tests/test_init.py` covers initial setup, manual-state completion, byte/mode/mtime
idempotence, safety failures, no CLI fallback, local ignore rules, and downstream
script compatibility. These are synthetic script tests, not Agent executions.

## Mandatory naming projection

Read [NAMING.md](NAMING.md) and [naming-map.json](naming-map.json) before changing
the upstream version. `tools/naming.py` applies the reviewed mapping after raw
source rendering; `tools/naming_check.py` is an independently maintained finite
comparison oracle. The build identity includes the naming map. Upstream locks
and copied source paths retain original names, while generated workflows use
`references/workflows/<full-skill-id>.md` and loader calls use the same public ID.
Unknown source references must stop preparation; never infer new abbreviations
or weaken full-body parity to accept a candidate. See PR #24 for execution evidence.
