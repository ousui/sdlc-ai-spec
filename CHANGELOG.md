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
