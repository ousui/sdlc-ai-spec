# Engineering verification boundary

Product: SDLC `1.0.0-beta`. Author: Blade.
Upstream: Spec Kit `v1.0.5`, commit
`a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`.

This document defines the current evidence contract, not a permanent PASS for
all builds carrying the same beta version. Obtain the exact commit's completed
`SDLC engineering` run and artifact `sdlc-engineering-<source-sha>`. Do not reuse a
previous run or a baseline-acquisition-only success as proof for a new commit.

## Checks

| Group | Evidence |
| --- | --- |
| Upstream identity | Selected source hashes against upstream.lock.json |
| Original English commands | Nine source files compared byte-for-byte |
| Three independent integrations | 27 renderer results compared with installed CLI output |
| Migrated skills | 27 bodies and native metadata checked under the explicit address mapping |
| Templates | 15 package templates compared with installed-tool baselines |
| Packaging | Native manifest fields, portable schemas, version, author, repository, license and NOTICE |
| Code | Bash/Python syntax, script derivation, reproducible package inventory |
| Runtime boundaries | 15 existing synthetic filesystem test methods, exercised across host packages |
| Upstream script behavior | 21 differential cases: return codes, stdout/stderr and output bytes |
| Repository | Root layout, product metadata, generated provenance, license copies, documentation links and CI paths |

The verifier reports its actual count; groups and test methods are not added
together as a fabricated total. `result.json` contains itemized checks,
`runtime_test_methods`, `repository_test_methods`, and `differential_cases`.
A normalization negative control must reject extra business prose.

## Consolidation invariants

The repository cleanup changes placement, product metadata, package notices,
build/verification wiring and maintenance documentation only. The nine command
sources, migrated templates, runtime scripts and binding instructions remain the
reviewed implementation; core content differences must still fail parity checks.
No old runtime, old plugin entry, historical plan tree or obsolete workflow is
required by the current build. Earlier records remain available in Git history.

## What a pass does not establish

INIT is not implemented. No native plugin installation, discovery, parameter
substitution or host-driven Skill execution is certified. No real business
project or LLM workflow is run. macOS and Windows/PowerShell execution remain
unverified. Concurrent editing of one feature is not guaranteed.

All filesystem scenarios use synthetic temporary fixtures. The fixture seeding
helper is not an initialization product and must not be exposed as one. The
same fixed beta version may identify multiple commits, so source SHA and
artifact hashes—not the version label alone—bind a verification result.
