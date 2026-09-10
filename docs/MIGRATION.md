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
| Plugin packaging + provenance | Two portable manifests and one Claude manifest; resources self-contained |

`check-prerequisites.sh`, `resolve-template.sh` and `setup-plan.sh` are otherwise
byte-identical to the upstream source after the marker relocation. `common.sh`,
`create-new-feature.sh` and one setup-tasks diagnostic have explicit checked
patch anchors. The existing resolver's dormant optional code is not rewritten;
optional ecosystems are not installed or advertised as supported.

`src/commands` is the reviewed raw source, not copied generated Skills. The
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

The portable manifest schema is captured from
https://agent-plugins.org/schemas/1.0.0/plugin.schema.json (read 2026-09-10).
Claude uses the documented minimal manifest subset from
https://code.claude.com/docs/en/plugins-reference. Neither is a native host test.

## Deliberately deferred

INIT construction; real business project use; actual Codex/Claude/Cursor install,
discovery and invocation; model quality; macOS execution; Windows/PowerShell;
concurrent writes to one feature; legacy data migration; GitHub operations.

INIT requires a separately authorized work package. Repository consolidation
does not authorize its construction. See DEVELOPMENT.md and VERIFICATION.md for
current validation commands and evidence boundaries.
