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
