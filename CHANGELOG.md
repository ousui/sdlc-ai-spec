# Changelog

## 1.0.0-beta — 2026-09-10

- Consolidate the Spec Kit core migration as the sole repository implementation.
- Place source, adapters, tools, tests and three generated packages at the root;
  remove superseded runtimes, plugin entries, plans and unrelated workflows.
- Define product version, Blade authorship and the declared repository centrally
  in plugin-metadata.json; generate consistent package manifests and provenance.
- Keep nine English upstream commands, runtime scripts and migrated template
  behavior unchanged. INIT and native client validation remain unimplemented.
- Retain engineering-only differential verification against three empty projects
  initialized by the installed pinned Spec Kit tool; add layout/metadata checks.

The beta version remains fixed during debugging. Use the exact Git commit and
CI evidence to identify a tested build. Earlier development is available in Git
history rather than copied into the current product tree.

## Unreleased changes (version remains 1.0.0-beta)

- Replace three copied distributions with one self-contained dist package.
- Generate three marketplace catalogs pointing to ./dist and native thin entries.
- Losslessly factor host workflow differences and bind them without AI/CLI calls.
- Vendor watched original generator source; add detached candidate upgrade/review.
- Add explicit installation, cache, upgrade and Codex/Cursor smoke-test procedures.
- INIT and native/model-driven acceptance remain deferred.

## Project-only initialization (same 1.0.0-beta)

- Add generated sdlc-init entries for all three hosts and one shared initializer.
- Complete fresh/partial project data without copying tools or invoking specify.
- Preserve existing documents and feature state; reject unsupported layouts.
- Add init-versus-installed-CLI projection tests and downstream script fixtures.
- Replace manual smoke-test seeding with the real init entry; no version/tag bump.

## PR #24 — numbered product naming (1.0.0-beta unchanged)

- Use the approved INIT/RULE/SPEC/CLAR/PLAN/TASK/XCHK/HUMA/IMPL/CONV IDs in all
  generated host entries, workflow filenames, loader arguments and references.
- Product ID `sdlc-ai-spec`, display name SDLC AI SPEC, SDLC runtime identifiers;
  keep `.sdlc` and existing business-artifact paths.
- Generate through the documented naming map, retaining untouched upstream
  provenance and independent parity checks.
- STATUS, RULE auto-init and shared host entrypoints remain separate work.

## Development tooling — uv migration

- Manage repository development/build/test dependencies with `pyproject.toml` and
  committed `uv.lock`; use Python 3.12 as the canonical development interpreter.
- Pin CI to uv 0.12.13 and use `uv sync --locked` / `uv run --locked`; isolate the
  upstream Spec Kit CLI in a separate `uv venv` installed through `uv pip`.
- Remove `tools/requirements.txt` as a second dependency source of truth.
- Keep installed `dist` runtime uv-independent; only BUILD.json metadata changes
  to record the new reproducibility inputs.
- Make path-valued unit-test assertions compare canonical filesystem identity so
  macOS `/var` and `/private/var` aliases do not produce false failures; run the
  engineering workflow on both Ubuntu 24.04 and macOS 15 ARM64.

## Shared core Skills and zh-CN projection (1.0.0-beta)

- Nine core entries now share dist/skills; INIT keeps three minimal host-policy
  wrappers. Each host still exposes ten capabilities without changing its policy.
- Full core workflow prose, metadata, binding and INIT guidance are localized.
  Template skeletons and machine contracts stay English; authored content is Chinese.
- Reviewed locale assets bind exact rendered inputs; stale translations block new
  packages. Localization-only candidate refresh rebuilds and invalidates old evidence.
- Correct local-only event-key renaming, blanket unrelated environment rejection
  and blanket external-state symlink rejection. No independent upstream bug fixes.

## Unified entries and read-only STATUS (1.0.0-beta)

- Move INIT into public skills/ and remove all three host-private Skill directories.
- Omit only the approved UI/selection metadata; use each host's default behavior.
- Add local sdlc-status with bounded standard-library collection, JSON/Chinese
  stdout, explicit/current/list selection and no persistence or project execution.
- Preserve upstream sources, nine workflow bodies, English template structures
  and existing INIT data behavior. STATUS adds no stage completion verdicts.
- Expand synthetic path/format/read-only tests and retain deterministic build,
  localization freshness and upstream upgrade compatibility checks.
