# Migration delta ledger

Scope: the user's 2026-09-10 engineering-only instruction. The source baseline is
Spec Kit v1.0.5 at `a4e25ce6b96dc8e85f84206c6a54353fa9c5260b`, configured for Bash,
no events, no presets and no extensions. This is NOT equivalence to the entire CLI.

| Change | Reason / preserved behavior |
| --- | --- |
| Nine original command sources are kept byte-for-byte | Do not modify raw sources; reviewed derived Chinese prose preserves steps and machine contracts |
| `speckit-*` callable references become host-native `sdlc-*` references | Codex `$`, Claude plugin namespace, Cursor `/`; illustrative hook variants stay illustrative |
| `.specify` state becomes project `.sdlc`; default `specs` becomes `.sdlc/specs` | Keep file names, field keys, numbering and explicit feature overrides |
| Core templates/scripts move to plugin resources | Project overrides still resolve from project `.sdlc`; no shared state |
| Business root can no longer fall back to script location | Missing project is an error; explicit target / nearest project still supported |
| A small Python path check protects plugin resources | Validate canonical paths, symlink targets and explicit feature paths before script writes; not a sandbox or general authorization engine |
| `specify preset resolve spec-template` instruction uses local `resolve-template-path.sh` | SPEC receives an existing path for its copy/read consumer; the existing content resolver is unchanged; project override precedes bundled core in the selected profile |
| Native hints use invocation host, not saved default integration | One project can be used sequentially by different hosts |
| Binding preamble is added to generated skills | Identify resources, resolve project, pass variables per tool call and fail clearly outside the selected profile |
| Plugin packaging + provenance | Three native manifests discovering one shared set of eleven entries |

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
It has no subprocess, network or writes. All 27 English pre-localization bodies are independently compared with original
CLI outputs under the address allowlist. Chinese resolved bodies additionally
match reviewed full translations, with source freshness and machine-span checks.
Shared wrappers omit only approved UI/selection fields, retaining explicit calling-host identity,
original user input and an explicit full-output reading requirement. Truncation
must be handled with bounded pages, never silently accepted.

Eleven capabilities live only in `skills/`, including local INIT and STATUS.
Claude uses its default scan; Codex/Cursor explicitly select the same directory. No portable root manifest is shipped. References for the path rules:
https://developers.openai.com/plugins/build/plugins
https://code.claude.com/docs/en/plugins-reference
https://cursor.com/docs/reference/plugins
Static documented-field/path checks are NOT native-host certification.

Shared artifact templates use canonical capability IDs such as `sdlc-200-plan` instead
of a host's literal invocation prefix. They are instruction references, not shell
commands. The wrapper/loaded workflow retains native invocation semantics. This
is a separately allowlisted reference-only change: all other words, whitespace,
checklist ownership and business steps remain part of exact comparison.

Root marketplace catalogs all reference `./dist`. No component references paths
outside this installation boundary. See [UPGRADING.md](UPGRADING.md) for the
source map, watched generator code and fail-closed candidate acceptance.

## Deliberately deferred

Real business project use; actual Codex/Claude/Cursor install,
discovery and invocation; model quality; Windows/PowerShell;
concurrent writes to one feature; legacy data migration; GitHub operations.

Project-only INIT was separately authorized after the native-user smoke test
exposed the missing `.sdlc` first-use path. See INITIALIZATION.md for its exact
project-data projection and differences from the upstream installer. The original
nine command sources and upstream lock are unchanged. See DEVELOPMENT.md and
VERIFICATION.md for validation commands and evidence boundaries.

## Local INIT provenance

The reference is the locked `src/specify_cli/commands/init.py`: its
`ensure_constitution_from_template` creates only a missing constitution, and its
`init_opts` persists script, numbering and upstream version defaults. We preserve
that project-data behavior and project override precedence. Agent registries,
CLI/integration setup, shared scripts/templates, presets, events and Git creation
are deliberately not migrated into project initialization. Our `.sdlc/.gitignore`,
layout marker, README and safe partial-state completion are local additions.

The new helper is not called `specify init` and never invokes that executable.
A successful local INIT is not a claim of full CLI initialization equivalence.

## PR #24: numbered product identity migration

[NAMING.md](NAMING.md) and [naming-map.json](naming-map.json) now govern product
names. Raw sources, lock and upstream oracle remain unchanged. Generated Skill
directories, name fields, full workflow filenames, binding keys and loader IDs
use the approved four-letter stage names. The product ID is `sdlc-ai-spec`;
display name is **SDLC AI SPEC**. Existing project data paths are unchanged.

Runtime declarations/callers and emitted hints use SDLC identifiers. All three
hosts retain explicit host binding and the input-handling contract. The approved
UI/selection metadata is omitted from generated entries; original source metadata
remains in the independent upstream comparison. Compatibility/provenance
exceptions are listed in NAMING.md. Unrelated obsolete environment prefixes are
not rejected; public overrides use the documented SDLC names.

Full workflow parity uses an independently enumerated inverse mapping and keeps
the negative prose-mutation control. Script leaf comparisons enumerate only
path/function/argument renames. No permissive whitespace or business-rule
normalization was added. This supersedes the historical unnumbered name ledger
above, not the original nine workflows, INIT idempotence or native test boundary.

## Shared Skills and localization delta

This round corrects only previously introduced deviations: event keys remain
`before_specify/after_specify`; unrelated SPECIFY_* environment variables no longer
cause blanket refusal; an external state alias is allowed unless it targets the
plugin. Shared-resource isolation remains necessary for external plugin resources.
Upstream bugs, including prerequisite persistence, are not independently repaired.

Chinese sources live under src/locales/zh-CN. English-dependent rendering precedes
translation; factoring follows it. Five reviewed template presentations and the built-in requirements checklist are
localized. Original English template projections remain in src/templates; bilingual
heading anchors, placeholders, code paths and task grammar are checked separately. No existing project data is rewritten during upgrade.
See [LOCALIZATION.md](LOCALIZATION.md) for checks, review limits and resumption.

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

## REV-007–010 and expanded document localization

SPEC now uses a local path-only adapter backed by the existing resolve_template
function. resolve-template.sh still returns content, and its other consumers are
unchanged. No original command source or upstream Bash script was patched.

STATUS narrows example-section recognition to explicit labels, honors nested
checklists, and recognizes fenced/indented code before HTML comments. It remains
read-only; this corrects our own statistics, not upstream workflow behavior.

Default template output, the exact built-in requirements example and new project
README are reviewed Chinese presentations. Only exact whole-template equality
can be projected back for the independent English baseline and script comparison;
unknown/modified text fails, rather than being stripped or loosely retranslated.
Existing project files are preserved, including existing English/custom templates.
