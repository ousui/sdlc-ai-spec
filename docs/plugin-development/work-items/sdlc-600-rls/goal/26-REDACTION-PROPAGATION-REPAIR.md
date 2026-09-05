# RLS-WEB-003 — sensitive-value propagation repair

## Authority and checkpoint

Maintainer explicitly authorized Web repair of the reopened finding in PR #10
review 5120883644. This is a repair-source checkpoint, not independent acceptance.

- Reviewed S2: `797bde43a31b6e5afdb028de7f8944cea996b460`.
- Historical E2: `93e98c577b5c3136df55ee5a7cb7a1c2adfcda30`.
- Code/test checkpoint: `206c379b77bb47ba0cf7913ea6dc1f8a39ed9bcd`.
- Code/test Tree: `ed770c67d196b881365457e7329d034c29f145f0`.
- Accepted VFY: `46509eb6688df30e71ed094132b2d10e81ceb2ac`.
- main: `644218e02876c5649fd87cfca12e1876d3b3b8bf`.
- Preserved D: `c9615cec2da3b39949a3fdd8be32396eae6db3aa`.
- Preserved B: `f171118380535d8c27a1929d0ef061510f82305f`.

Only `impl/rls-v2` receives normal fast-forward commits in this Web work package.
VFY/main/D, shared packages, RCF implementation, fixtures, the 87 primary oracles,
workflows and old Evidence are not changed. No Release, asset, extra branch,
dependency installation, production effect or final Evidence is created.

## Root cause and implemented change

The v1 helper masked credential arguments or structured fields only in their
original position. Those values did not enter the context used for other fields
or stdout/stderr. Existing unit tests covered argument masking and environment
value echo separately, not their composition.

`tools/rls_validation_support.py` now uses policy
`sdlc-ai-spec/validation-redaction/v2` and a per-operation, memory-only two-pass
context. It discovers explicitly labelled values before writing any sink from:

- recognized sensitive environment names;
- credential arguments in separate and equals forms, whole JSON arguments, and
  recognized credential/header/URL syntax;
- both complete captured streams, including structured objects, nested encoded
  JSON, JSONL, mixed diagnostic JSON, duplicate keys and labelled assignments;
- captured errors and the same receipt's source metadata.

The same fixed context scrubs both streams, argument receipts, nested fields and
errors. Execution still receives the original argv/environment. A program's
variable name inside `-c` source is not inferred to be a password value.

JSON strings are decoded before scrubbing, including escaped values in JSONL.
Duplicate keys are all inspected before normalized safe JSON is rendered.
Longest-first simultaneous substitution prevents overlaps from corrupting the
redaction marker. Nonsecret Effect Authorization objects and source/digest
bindings remain normal audit data. No context values are serialized or cached
across unrelated calls.

Both streams are scrubbed before the first log write; hashes bind their final
archived UTF-8 bytes. The returned receipt equals its stored JSON. A nested
receipt whose newly discovered sensitive value would alter an already-bound
stream fails before writing rather than silently retaining stale hashes or
retroactively claiming that its previous archive was safe.

Sensitive receipt locators, malformed step names, nonfinite JSON, excessive
nesting (>128) and excessive distinct sensitive values (>2048) fail closed.
Tracked-source receipts must be outside that source tree. Source-state failures
are scrubbed with the invocation context and do not run/finalize an unsafe step.

The contract covers recognized plaintext values within one captured operation or
object. It does not infer arbitrary unknown credentials, decrypt arbitrary
encodings, protect malicious same-user processes, rewrite historical archives or
promise discovery of secrets first labelled in a future unrelated invocation.
A child that writes its own artifact must use the safe writer before that write;
a parent's later capture cannot undo an earlier child leak.

## Actual Web execution

Execution used a restored, Blob-checked source subset, not a complete repository
checkout. The helper input Blob was re-read from actual E2 as
`89bf3cc13de639b95e5aa10421b8e6ef7265bae6`. New helper/test Blob identities match
those created by the Connector:

- helper: `a7fb955175a2a48b739965f6c5deec280c037de1`;
- new tests: `fa0ecad0c33cdd702237e75e4cc44d6123f6db0f`.

| Suite | Actual Web result |
|---|---|
| New propagation/composition tests | 56/56 PASS |
| Unchanged existing redaction tests | 18/18 PASS |
| Unchanged RCF/human components | 28/28 PASS |
| Unchanged batch/Evidence components | 8/8 PASS |
| Total | 110/110 PASS; no skip/expectedFailure/unexpectedSuccess |
| Four original independent review probes | 4/4 safe; real local child processes |
| Source registration delta | syntax/constant registration checked, allowed() unchanged |
| Real Store, RLS 87, strict VFY 80, full regression, installed/external/attest | NOT_RUN_IN_WEB_ENVIRONMENT |

The new tests include real parameter-echo processes, a child safe writer, real
timeout, cross-stream and cross-field propagation, escaping/duplicate keys,
first-write interception, context isolation, original execution arguments,
source-change detection, nested hash consistency and audit-binding preservation.
All credential canaries are synthetic. A discovery run exposed accidental
classification of program variable names; implementation was corrected without
weakening those tests. Local discovery and final logs are retained outside the
source repository; they are not formal RLS Evidence.

`validate_rls_delivery_source.py` registers exactly the new test path and excludes
S2, E2 and this code checkpoint from future final Subject ancestry. The original
52 planned files, allowed() policy, 87 cases, VFY protection, D/B topology and
shared query/status byte comparisons are retained. No checker is disabled.

## Sole next work package

Use `27-LOCAL-CODEX-GOAL-REDACTION-PROPAGATION.md` to validate the repair in the
complete Client checkout and create D -> S3 -> E3. E2 remains historical;
`WEB_RLS_REVIEW=CHANGES_REQUIRED` remains until independent review of new S3/E3.
