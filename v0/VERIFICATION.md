# Engineering verification record

## Verified implementation

- Repository: https://github.com/ousui/sdlc-ai-spec
- Implementation commit: `2a9e0b8a6ed0aff0e7f90099c0ace1ffa073c7c3`
- Upstream: `github/spec-kit` `v1.0.5` at `a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`
- Evidence workflow: https://github.com/ousui/sdlc-ai-spec/actions/runs/34478826759
- Artifact: `v0-materialized-e5dd76220f397faead810728b3da416204be3b57`, ID `10152684310`.

The workflow started on the authoring commit `e5dd762...`, generated source and
packages from the pinned upstream source, verified them, committed only v0
resources, then ran verification AGAIN on `2a9e0b8...`. The artifact's
`verification/result.json` explicitly binds that second result to `2a9e0b8...`.
Do not confuse the workflow's original event SHA with the tested generated SHA.

The cleanup commit containing this record changes documentation and removes the
one-time materialization workflow; runtime sources and packages are unchanged.
The read-only `v0 engineering` run on that cleanup SHA is the final delivery check.
It must pass independently; this historical record does not substitute for it.

## Actual results

Result: **PASS — engineering scope only**.
Environment: Ubuntu runner, Linux x86_64, Python 3.12.3, Bash 5.2.21.

| Check group | Passed |
| --- | ---: |
| Pinned upstream source hashes | 21 |
| Unchanged original English command files | 9 |
| Independent source renderer vs installed CLI, three agents | 27 |
| Migrated Skill bodies/metadata vs installed CLI, allowed address changes only | 27 |
| Three packages' templates vs installed CLI | 15 |
| Bash syntax | 21 |
| Python runtime syntax | 3 |
| Build/verification tool syntax | 4 |
| Reviewed script transformation checks | 6 |
| Unchanged leaf-script parity | 3 |
| Minimal native manifest field checks | 3 |
| Official Agent Plugins schema (Codex/Cursor) | 2 |
| Runtime dependency and inventory checks | 3 |
| Reproducible three-package build | 1 |
| Synthetic filesystem suite | 1 suite / 15 test methods |
| Installed upstream script differential cases | 21 |

Total: **167 recorded check items**, including the one 15-method test-suite item.
These are not 167 business requirements or LLM evaluations. Exact return codes,
stdout, stderr and generated document bytes are compared in script differential
cases after explicit path/name normalization.

The 15 synthetic test methods cover template resolution, document preservation,
prerequisite failures, read-only path lookup, project overrides, two-project
isolation, cross-host sequential state reuse, nested and explicit roots, missing
initialization, plugin/symlink write boundaries, quoted/Unicode paths, relocated
read-only resources, feature numbering/dry-run, invalid flags and missing Python.
A trap executable confirms the exercised runtime paths do not call `specify`.

The downloaded CI distribution hashes were also compared with the locally built
packages: identical. No business project was used. CLI init was executed only
in three new empty directories for codex, claude and cursor-agent with Bash,
`--events=false`, and no extensions or presets.

## Limits and stop point

No INIT Skill was constructed. Native plugin installation/discovery/invocation,
model-driven workflow execution, real-project correctness, macOS execution,
Windows/PowerShell and concurrent edits to one feature were NOT tested.
Static manifest validation does not prove native host compatibility. These
checks do not establish that all possible execution paths are defect-free.

The engineering work stops here. INIT is a subsequent separately authorized task.
