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
without importing `specify_cli` or reading initialized projects. Use `--marketplaces`
to also regenerate the three repository-root catalogs.
There is no root plugin manifest because the root is a source/build workspace.

All three native manifests declare `skills: ./adapters/<host>/skills/` inside
the same dist package. No portable root manifest/default skills scan is shipped.
The loaded wrapper pins its host and reads the complete, deterministic loader
output. The shared workflows plus literal fragments reconstruct each formerly
expanded host body exactly; this is tested against installed upstream output.
[Installation](INSTALLATION.md) lists current official format references.

## Build from source

Use Python 3.11+ in an isolated development environment:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r tools/requirements.txt
.venv/bin/python -B tools/build.py --marketplaces
.venv/bin/python -B -m unittest discover -s tests -v
git diff --check
```

To reproduce source materialization, obtain the upstream commit recorded in
`upstream.lock.json` in a separate checkout. Run the command below with its
absolute path; the tool checks the selected source hashes against the lock.

```sh
.venv/bin/python -B tools/port.py --upstream "$UPSTREAM"
.venv/bin/python -B tools/build.py --marketplaces
```

Do not use `specify init` output to construct the port. It is an independent
comparison baseline only. Do not introduce CLI callbacks into runtime scripts.

## Independent installed-tool comparison

Use three new empty directories and an isolated upstream tool environment, all
outside this repository and outside business projects. Set absolute paths for
`UPSTREAM`, `TOOL_ENV`, `BASELINES` and `EVIDENCE` first. The upstream checkout must
be exactly `a4e25ce6b96dc8e85f84206c6a54353fa9c5260b` (Spec Kit `v1.0.5`).

```sh
test "$(git -C "$UPSTREAM" rev-parse HEAD)" = a4e25ce6b96dc8e85f84206c6a54353fa9c5260b
python -m venv "$TOOL_ENV"
"$TOOL_ENV/bin/python" -m pip install -r tools/requirements.txt "$UPSTREAM"
"$TOOL_ENV/bin/specify" version
for agent in codex claude cursor-agent; do
  mkdir -p "$BASELINES/$agent"
  (cd "$BASELINES/$agent" && "$TOOL_ENV/bin/specify" init . \
    --integration "$agent" --script sh --ignore-agent-tools \
    --non-interactive --integration-options="--events=false")
done
"$TOOL_ENV/bin/python" -B tools/verify.py --upstream "$UPSTREAM" \
  --baselines "$BASELINES" --evidence "$EVIDENCE"
git diff --check
```

Use Bash with no events, presets or extensions. These CLI calls do not launch
Codex, Claude or Cursor and do not implement `sdlc-init`. Do not pass `--force`
to reuse nonempty baseline directories: create new directories instead.

## CI and evidence

`.github/workflows/engineering.yml` fetches the triggering repository's exact
commit and the pinned upstream, installs the tool, initializes three empty
projects and verifies already committed packages. It must not regenerate and
commit packages in CI or silently skip checks when files are absent.

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
