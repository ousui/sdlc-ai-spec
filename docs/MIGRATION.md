# Migration delta ledger

Scope: the user's 2026-09-10 engineering-only instruction. The source baseline is
Spec Kit v1.0.5 at `a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`, configured for Bash,
no events, no presets and no extensions. This is NOT equivalence to the entire CLI.

| Change | Reason / preserved behavior |
| --- | --- |
| Nine original command sources are kept byte-for-byte | Do not translate, optimize prompts, alter stages or introduce unrelated process rules |
| `speckit-*` callable references become host-native `sdlc-*` references | Codex `$`, Claude plugin namespace, Cursor `/`; illustrative hook variants stay illustrative |
| `.specify` state becomes project `.sdlc`; default `specs` becomes `.sdlc/specs` | Keep file names, field keys, numbering and explicit feature overrides |
| Core templates/scripts move to plugin resources | Project overrides still resolve from project `.sdlc`; no shared state |
| Business root can no longer fall back to script location | Missing project is an error; explicit target / nearest project still supported |
| A small Python path check protects plugin resources | Validate canonical paths, symlink targets and explicit feature paths before script writes; not a sandbox or general authorization engine |
| `specify preset resolve spec-template` instruction uses bundled `resolve-template.sh` | No persistent specify-cli runtime dependency; original template selection remains for selected core profile |
| Native hints use invocation host, not saved default integration | One project can be used sequentially by different hosts |
| Binding preamble is added to generated skills | Identify resources, resolve project, pass variables per tool call and fail clearly outside the selected profile |
| Plugin packaging + provenance | Three native manifests selecting thin entries in one self-contained package |

`check-prerequisites.sh`, `resolve-template.sh` and `setup-plan.sh` are otherwise
byte-identical to the upstream source after the marker relocation. `common.sh`,
`create-new-feature.sh` and one setup-tasks diagnostic have explicit checked
patch anchors. The existing resolver's dormant optional code is not rewritten;
optional ecosystems are not installed or advertised as supported.

`src/upstream/templates/commands` is the reviewed raw source, not copied generated Skills. The
independent builder is checked against the installed upstream CLI's three-agent
outputs before applying port deltas. Normalization has a closed name/path
allowlist: it does NOT drop arbitrary paragraphs, whitespace, normative words,
sections or task requirements. An extra prose rule is a required failing control.
Native YAML frontmatter is compared structurally; command bodies are compared
byte-for-byte before migration and under the explicit mapping after migration.

Engineering checks also compare upstream and migrated script exit codes,
stdout, stderr and produced documents on synthetic fixtures. Those comparisons
normalize address changes and the intentional correction of Codex script hints;
they do not replace actual business or model-driven acceptance testing.

## Single-package factoring and native selection

`tools/build.py` first derives the complete host bodies using the reviewed source
renderer and existing relocation rules. It then factors byte-identical portions
into one workflow file; only the exact differing substrings become named literal
fragments in `bindings/<host>.json`. Different line structures fail closed.
`load_workflow.py` performs nonrecursive literal binding and emits the full body.
It has no subprocess, network or writes. All 27 resolved bodies are independently
compared with the original CLI outputs under the existing address allowlist.
The thin wrappers keep the respective upstream frontmatter, literal host identity,
original user input and an explicit full-output reading requirement. Truncation
must be handled with bounded pages, never silently accepted.

All three native manifests select `adapters/<host>/skills/`. No default skill
scan or portable root manifest is shipped. References for the path rules:
https://developers.openai.com/plugins/build/plugins
https://code.claude.com/docs/en/plugins-reference
https://cursor.com/docs/reference/plugins
Static documented-field/path checks are NOT native-host certification.

Shared artifact templates use canonical capability IDs such as `sdlc-plan` instead
of a host's literal invocation prefix. They are instruction references, not shell
commands. The wrapper/loaded workflow retains native invocation semantics. This
is a separately allowlisted reference-only change: all other words, whitespace,
checklist ownership and business steps remain part of exact comparison.

Root marketplace catalogs all reference `./dist`. No component references paths
outside this installation boundary. See [UPGRADING.md](UPGRADING.md) for the
source map, watched generator code and fail-closed candidate acceptance.

## Deliberately deferred

INIT construction; real business project use; actual Codex/Claude/Cursor install,
discovery and invocation; model quality; macOS execution; Windows/PowerShell;
concurrent writes to one feature; legacy data migration; GitHub operations.

INIT requires a separately authorized work package. Repository consolidation
does not authorize its construction. See DEVELOPMENT.md and VERIFICATION.md for
current validation commands and evidence boundaries.
