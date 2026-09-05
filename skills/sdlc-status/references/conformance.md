# Status conformance notes

This additive note explains the implemented boundaries of `contract.md`; it does not replace the locked shared domain contract.

## Post-integration conformance

- `auto -r` uses the same exact REQ and missing-Store rules as `inspect -r`.
- Symbolic, Member and non-REQ references fail before opening a Store.
- A missing Store is distinct from a conflicting filesystem node: a runtime
  directory occupied by a file, a database path occupied by a directory, dangling
  links, or inspection errors fail closed with no overview or initialization
  recommendation. Truly absent paths retain the unbound `not_started` behavior.
  Live symlinks keep the existing shared backend policy; this check grants no
  new authority and never opens SQLite, retries a failed open, or writes files.
- `summary` metadata output is text; `json/debug` always emit one JSON document.
- Debug resolution omits free-form user prose. Failure results keep bounded error
  codes but never echo raw exception text or arbitrary payload details.
- Multiple RLS targets remain selectable and visible in the summary; no automatic
  selection or effects are introduced.
- `source-lock.json` is build/review traceability, not runtime authorization. It
  follows the shared source-lock shape and names contract IDs, versions and hashes.
  The build-time utility validator binds the full declared shared-code set and
  utility resources. Runtime neither imports the validator nor reads development assets.
