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
