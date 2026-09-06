# Client — narrow Status path repair recheck

Run only this bounded verification work package. It is not a new seven-stage
implementation, RLS S4/E4, or an eight-Skill native certification campaign.

## Start and boundaries

1. Fetch `origin/main` and `origin/fix/post-integration-skill-conformance`.
2. Record the actual repair Head and tree from the Ref; confirm it contains
   `WEB-STATUS-PATH-REVIEW.md` and descends from Client delivery
   `1b9326e7447a481453fbbeccd8d104a02f6c67e9` without rewriting it.
3. Use a clean separate worktree. Do not switch, clean or reset the user's worktree.
4. Read this file, `WORK-PACKAGE.md`, `WEB-STATUS-PATH-REVIEW.md`,
   `WEB-STATUS-PATH-VALIDATION.json` and the original `WEB-REVIEW.md`.
5. Work only on the existing repair branch. Do not modify main, seven Phase
   runtimes, shared packages, original Case Expected, historical Evidence,
   Workflow or distribution metadata. Do not recreate deleted phase branches.

## Execute

Record `SOURCE_SHA=$(git rev-parse HEAD)` and put logs outside the worktree. Use
a host with functioning OS containment for strict VFY; no dependency install or
unsandboxed fallback is authorized by this prompt.

First execute the 14 new regressions:

```bash
python3 -B -m unittest tests.skill_status.test_store_absence -v
```

Then execute the existing single strict entry:

```bash
python3 -B tools/run_post_integration_validation.py \
  --profile strict \
  --source-sha "$SOURCE_SHA" \
  --json-out "$EVIDENCE_DIR/strict-status-path-repair.json"
```

The strict entry already runs shared contracts, eight interfaces/source locks,
Status static/fixed/coverage/installed checks, RLS 87, full ordinary repository
regression, VFY strict 80, and VFY/RLS installed checks. Do not run the duplicate
portable profile solely to increase counts. Expected repository collection is
1118 if the only test addition to the previous 1104 is these 14 methods; report
the actually collected unique IDs and investigate any difference. All required
cases must execute; skip, expectedFailure and a capability-only strict VFY PASS
are forbidden.

Confirm unchanged bytes/modes for malformed `.sdlc`, malformed database path,
dangling links and genuine-absence controls. JSON must be one document, with
failure exit 2 for path conflicts and no initialization or sibling invocation.

If a real failure occurs, preserve the first log and repair only the authorized
Status/conformance paths. Do not weaken an assertion, change Expected, silence a
failing gate or modify accepted upstream code. Source changes require a new
clean exact-source execution. An unavailable host or unresolvable scope conflict
is HARD_BLOCKED, not PASS.

## Native scope

No eight-Skill native rerun is required for Runtime closure. Existing eight
Codex CLI candidates remain observations of fb1d8fb, not certifications of the
new source. Leave COMPATIBILITY.json at its accurate current state, with no
self-signed ACCEPTED. REQ formal Runtime and JSON output-contract limitations
remain explicitly unverified. A separately authorized native certification task
can address them later; it must not block this Runtime-only review by implication.

## Archive and publish

Keep the old CLIENT-VALIDATION files and CLIENT-SHA256-MANIFEST.json unchanged.
In particular their HANDOFF entry remains bound to the old delivery 1b9326;
validate that old manifest in its original tree, not against a later handoff.

Append new results under a separate `status-path-recheck/` directory. Capture
argv, cwd, exit code, duration, source before/after, full redacted stdout/stderr,
unique test IDs, hashes and all failure attempts. Archive through the existing
accepted redaction helper before first persistence. Do not archive authentication
files, tokens or unredacted secrets.

Create a byte-complete review tar/zip with a separate SHA-256 file. Include the
new validation and the preserved previous Client evidence (75 process receipts,
150 streams and eight native candidates), their original manifests and source
bindings, the reviewed source tree, and a recoverable Git bundle containing
source and delivery commits. Verify archive hashes and that it unpacks correctly.
Upload the actual archive and checksum to the Web conversation; a `/tmp` or
`/Users` link alone is not a transferred attachment.

Append evidence/handoff normally on this same branch, retain the tested source
as its parent, use a checked fast-forward push, and read back branch/main/PR
identities. Do not consolidate or rewrite phase history. Update PR #11, keep
Draft, do not merge or publish. If the remote Head moves unexpectedly, stop
without overwriting it.

## Terminal output

```text
POST_INTEGRATION_STATUS_PATH_RECHECK = PASS | HARD_BLOCKED
VALIDATED_SOURCE_SHA = <actual tested source>
DELIVERY_HEAD_SHA = <actual evidence head>
STATUS_NEW_REGRESSIONS = <actual>/14
STATUS_FIXED_EVAL = <actual>/14
VFY_STRICT = <actual>/80
RLS_FIXED_EVAL = <actual>/87
REPOSITORY_TESTS = <actual unique count>
WEB_CONFORMANCE_REVIEW = REQUIRED
NATIVE_ACCEPTED_CELLS = []
REAL_TARGET_EFFECTS = 0
MAIN_MODIFIED = NO
PR_MERGED = NO
```

Stop after the report and archive. Do not start another native/phase Goal or
claim independent Web acceptance.
