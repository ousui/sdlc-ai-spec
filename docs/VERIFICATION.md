# Engineering verification

The CI run for the **exact source SHA** is authoritative for a particular build.
Do not reuse a previous three-package PASS to claim the new single package passed.

The verifier installs no Agent and runs no business task. CI independently installs
the pinned Spec Kit CLI and initializes three new empty projects, Bash, events
false, no presets/extensions. It compares upstream-generated frontmatter and full
workflow bodies with the migrated loader's resolved result for each host.

The package now uses native manifests and explicit component paths. The old
portable-schema check is intentionally replaced by documented native-field/path
checks and disjoint-discovery tests. This does NOT count as a native client test.

Checks cover raw source hashes and watched generator hashes; 27 original source
renderer comparisons; 27 resolved migrated workflow comparisons; shared template
reference projections; literal factoring, malformed binding failures, bounded
output pages, relocation and symlink boundaries; one reproducible dist; three root
marketplaces; existing synthetic filesystem behavior and 21 upstream-script
differential cases; candidate preparation/acceptance rejection tests.

Evidence contains source SHA, source content/mode digest, upstream SHA, declared
and actual repositories, fixed product version, environment, individual results,
unit-test output and package inventory. Evidence is outside the checkout. The
read-only workflow checks that committed output is not rewritten during tests.

No INIT Skill, native plugin install/discovery, LLM-driven end-to-end result,
macOS, Windows, production or concurrent same-feature write guarantee is claimed.
The user will run [SMOKE-TEST.md](SMOKE-TEST.md) independently in Codex and Cursor.

## Initial single-package engineering record

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
