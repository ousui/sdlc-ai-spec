# Engineering verification

The CI run for the **exact source SHA** is authoritative for a particular build.
Do not reuse a previous three-package PASS to claim the new single package passed.

The verifier installs no Agent and runs no business task. CI independently installs
the pinned Spec Kit CLI and initializes three new empty projects, Bash, events
false, no presets/extensions. It compares upstream-generated frontmatter and full
English workflow bodies before localization. The localized loader is separately
compared with reviewed Chinese assets for each host; translation identity alone
is not semantic proof.

The package now uses native manifests and explicit component paths. The old
portable-schema check is intentionally replaced by documented native-field/path
checks and eleven-entry unified-inventory tests. This does NOT count as a native client test.

Checks cover raw source hashes and watched generator hashes; 27 original source
renderer comparisons; 27 English migrated workflow comparisons; 27 localized resolved bodies; shared template
reference projections; literal factoring, malformed binding failures, bounded
output pages, relocation and symlink boundaries; one reproducible dist; three root
marketplaces; existing synthetic filesystem behavior and 21 upstream-script
differential cases; candidate preparation/acceptance rejection tests. The local INIT additionally
compares its project data with three actual upstream CLI initializations and
executes dedicated preservation, failure and downstream-script fixtures.

Evidence contains source SHA, source content/mode digest, upstream SHA, declared
and actual repositories, fixed product version, environment, individual results,
unit-test output and package inventory. Evidence is outside the checkout. The
read-only workflow checks that committed output is not rewritten during tests.

No automated native plugin install/discovery, LLM-driven end-to-end result,
Windows, production or concurrent same-feature write guarantee is claimed.
Synthetic scripts on macOS are covered when that platform job actually runs;
this is not native-client or model acceptance.
The user will run [SMOKE-TEST.md](SMOKE-TEST.md) independently in Codex and Cursor.

## Historical single-package engineering record (before INIT)

The materialization job for source event `fcf212aeb3148ce1e200c55e955fda481a99360b`
produced the independently checked tree
`6846f3d52066dc4acc85e964868cc33f7a3e4a26` and code commit
`ffd8449cbd27da3c19cf4af45c2cce6c8e52063f` (Blade). It then verified the committed
code again: 180 recorded checks, 35 unit-test methods and 21 script-differential
cases passed on Ubuntu with Python 3.12.3 and Bash 5.2.21. Counts overlap by
reporting level and must not be summed. The same-version detached candidate
rehearsal also passed without modifying the accepted source or committing the
candidate. This is an upgrade-mechanism rehearsal, not approval of a new upstream.

Evidence: https://github.com/ousui/sdlc-ai-spec/actions/runs/34500754265
Artifact ID: `10161762096`. Its `verification/result.json` binds the post-commit
check to the code commit above; `upgrade-rehearsal/result.json` records the
accept-check result. The job's final push failed because the Actions credential
could not modify workflow files. That delivery failure does not invalidate the
recorded tests, but the overall materialization job must NOT be described as a
successful delivery run. The verified Git objects were read back and the
implementation branch is updated through the authorized GitHub connector instead.

The following documentation-only delivery commit must receive its own successful
read-only `SDLC engineering` run. Always select that final exact SHA, not this
historical event SHA, when checking delivery. The temporary transport/workflow is
absent from the tested product tree. Product version remains `1.0.0-beta`.

## Project initialization coverage

The init entry has its own local source and is tested without an existing `.sdlc`.
A fresh initialization must seed the same constitution bytes and the same `script`,
`feature_numbering` and `speckit_version` as each installed upstream CLI baseline.
No Agent registry, tools or feature selection may be copied from those baselines.
The synthetic suite covers manual-state completion, safe repeated calls, profile
and JSON conflicts, template overrides, package isolation, read-only Git warnings,
missing dependencies, interruption recovery, and init followed by existing core
scripts for all hosts. A fixture-created tasks file tests script interoperability;
it is not LLM-authored implementation evidence.

Use the final exact source SHA CI run for counts and status; historical counts
above describe only the previous implementation. Native INIT invocation remains
for the user to verify in the installed clients.

## Unified public inventory and STATUS

The current package exposes exactly eleven entries under `dist/skills`: nine
upstream core Skills plus local INIT and STATUS. There are no private host Skill
wrappers. All public entries omit user-invocable, disable-model-invocation and
argument-hint; host defaults apply. This supersedes earlier descriptions of the
INIT policy exception, not the existing INIT data-preservation contract.
Claude uses default skills/ discovery without a duplicate custom path. Other
manifests select ./skills/. All wrappers resolve the package two levels up.

STATUS is an optional local read-only utility, not another lifecycle phase or an
upstream command. It tolerates incomplete/uninitialized state, never persists a
feature switch, never initializes, and never executes the suggested next Skill.
See [STATUS.md](STATUS.md). Existing core bodies/templates and runtime behavior
are not modified to store history for STATUS.
