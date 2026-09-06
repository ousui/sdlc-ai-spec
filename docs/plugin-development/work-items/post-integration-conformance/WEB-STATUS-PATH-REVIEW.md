# Web review and repair — Status Store path classification

## Verdict and exact scope

`WEB_CONFORMANCE_REVIEW = CHANGES_REQUIRED` for Client delivery
`1b9326e7447a481453fbbeccd8d104a02f6c67e9`, which has the sole parent
`fb1d8fb989e5e31d75cd6f311c0e5e663437262d` (the Client's validated source).
One reproducible Runtime Major was identified: `CONFORMANCE-WEB-001`.
The maintainer authorized a Web-first repair. The commit containing this file is
repair source, not new final validation Evidence or independent acceptance of
that repaired source. Its exact SHA is read from the owned Ref and recorded in
PR #11 after the push; this document does not self-reference its commit hash.

main remains `0289a5ee8d702450fb3f3bc73c89f30a11664bdb`. Only
`fix/post-integration-skill-conformance` may be advanced, normally and without
rewriting accepted history. No seven-Phase Runtime, shared Package, original
Case/Expected, old Evidence, compatibility certification or Workflow is changed.

## CONFORMANCE-WEB-001 — incompatible Store paths reported as not_started

Authority: Status DESIGN sections 9–12 and STS-E14. A genuinely absent Store is
a valid empty overview for unbound auto/list; a corrupt or failing Store must
fail closed. The shared unavailable exception can also be caused by a filesystem
type conflict, so it is not sufficient proof of absence.

On exact source fb1d8fb, an existing regular file at `.sdlc` or a directory at
`.sdlc/store.sqlite3` made unbound auto/list return `ok=true/state=not_started`.
Dangling links were similarly misclassified. Existing data was not modified in
the probes, but the successful overview and recommended CTX creation were false.

The independent old-source harness observed 30 command/state combinations. Six
new regression methods run against the original Runtime produced 21 failing
assertions/subtests (six methods, not 21 distinct primary cases), without test
errors. A real CLI case also proved the incorrect zero exit code.

## Repair

`skills/sdlc-status/scripts/runtime.py` now refines an unavailable observation
using only filesystem metadata and the public read-only ArtifactStore facade's
`store_path`. It does not connect to SQLite, use SQL, initialize a Store, or retry
a previously unsuccessful query.

- Existing incompatible node types and dangling links produce bounded
  `LIFECYCLE_STORE_PATH_INVALID`, `ok=false`, `state=query_failed` and no overview
  or automatic next action.
- Filesystem inspection errors fail closed without echoing the exception.
- A valid-looking Store that is present after the unavailable observation is
  not downgraded to absence or automatically retried.
- Genuine absence keeps the original unbound auto/list `not_started` behavior.
- Exact missing references remain structured failures; invalid references and
  meta commands retain their pre-Store ordering.
- The existing shared backend policy for live symlinks is preserved. This patch
  does not claim race-free filesystem isolation or change shared Store policy.

Fourteen new tests cover real file/directory/link conflicts, absence controls,
exact references, zero-write snapshots, inspection errors, a real initialized
Store plus an injected unavailable observation, an installed copy without
siblings/development assets, and real CLI JSON/exit behavior. Only the last
error/race observations use injection; the primary path-conflict reproductions
are actual filesystem and CLI executions. The original fourteen STS primary
mappings and their Expected values are unchanged.

The Status 51-entry source lock is regenerated for the changed Runtime and the
additive conformance note. Its already-locked `contract.md` bytes are unchanged;
VFY and other Phase locks are not refreshed to hide drift.

## Actually executed in Web

The complete original fb1d8fb source was restored from the previously supplied
Git bundle. Its fifteen non-document root entries match the remotely read
Client delivery tree. On a clean detached original source, portable ran 10/10
steps successfully, including 1104/1104 ordinary repository tests, Status 14/14,
coverage 4/4, Status installed 12 commands and RLS 87/87. Source state remained
clean and unchanged. The omitted path cases explain why that suite was green.

On the repaired source bytes, ten focused verification steps passed: Python
compile, all Status tests 52/52 (38 existing plus 14 new), shared Runtime contract,
eight Skill interfaces, conformance inventory, all eight source locks, Status
static validation, original Status 14/14, coverage 4/4 and installed 12 commands.
No skipped, expectedFailure or unexpectedSuccess is counted. Subsets and repeated
runs are not added to the 52-test total. The source byte bindings and process
exit/duration/stream digests are in `WEB-STATUS-PATH-VALIDATION.json`; full raw
logs, reproduction scripts and failed attempts are in the chat attachment.

The repaired checks used a detached copy of fb1d8fb plus the recorded file bytes,
not a newly attested remote commit. Git Data publication applies only those
files and these handoff documents on top of exact delivery 1b9326, preserving all
Client archive files. No post-repair strict VFY, full-repository or native Client
PASS is claimed; the next Client recheck binds its own exact published source.

## Native observations and evidence limits

The inspected Client report, candidate summary, REQ receipt/audit, CTX audit and
native harness preserve their restricted missing-authority/read-only scope.
REQ's formal Runtime was NOT_RUN; safe upstream preflight is not a substitute.
CTX/IMP final JSON rewording and host progress messages cannot be silently
accepted as an exact JSON-output guarantee. These are unresolved native
certification observations, not reasons to rewrite seven accepted Runtime
implementations in this narrow repair.

`NATIVE_ACCEPTED_CELLS = []`. The existing forty ledger cells remain NOT_RUN;
none is promoted from the producer's PASS label. No complete cross-client or
positive lifecycle certification is claimed.

The current Web environment has the prior complete source bundle, not the new
Client byte-complete archive. Some individual Client records were fetched, but
the full 75-receipt/150-stream audit was NOT completed. Those figures are Client
claims pending byte-level independent audit. GitHub connector text reads worked;
direct GitHub DNS and binary archive acquisition did not. This transfer limit is
not the reason for the Runtime Major: that defect was independently reproduced.

## Next work package

Use `CLIENT-STATUS-PATH-RECHECK.md`. Perform one exact-source strict Runtime
recheck and supply a byte-complete archive. Do not rerun the old RLS development
Goals or all eight native sessions merely for this repair. Retain the previous
Client records as historical exact-fb1d8fb evidence; append new results instead
of overwriting them. Keep PR #11 Draft, do not merge, then request an independent
Web review of the repaired source and complete evidence.
