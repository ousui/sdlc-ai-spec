# Project initialization

Install the plugin once through the marketplace. In each selected project, invoke
`sdlc-000-init` once before the core workflow. It runs the bundled initializer, not
`specify init`: no uv/specify-cli/application installation, network access or
project-local copies of Skills, scripts and core templates are required.

| Client | Entry |
| --- | --- |
| Codex | `$sdlc-000-init` |
| Claude Code | `/sdlc-ai-spec:sdlc-000-init` |
| Cursor | `/sdlc-000-init`, or the actual plugin-namespaced entry in its menu |

Select the project root explicitly in multi-root workspaces. For a nested module
such as `example/helloserver`, select that module, not its enclosing Git root.
This command is not automatically launched merely by installing the plugin.

## What is created

```text
<selected-project>/.sdlc/
├── init-options.json
├── .gitignore
├── README.md
├── memory/
│   └── constitution.md
└── specs/
```

`init-options.json` defaults to Bash (`script: sh`), sequential feature numbering,
locked upstream version, `sdlc_layout: 1` and the plugin version `1.0.0-beta`.
No host selection, plugin installation path or active feature is stored globally.
The `sdlc_version` records the initializer used; repeat calls do not rewrite
existing version data. It is not a document-freeze or runtime-version gate.

`constitution.md` is copied byte-for-byte from the installed localized core template, or an
existing project `templates/overrides/constitution-template.md`. It is NOT a
ratified constitution: use `sdlc-010-rule` to establish project principles.
If you have already established principles, they are preserved verbatim.

The data-local `.gitignore` contains `*`, including the ignore file itself. It
prevents new accidental additions; already tracked data stays tracked. The script
can inspect tracking with read-only Git commands and warns about tracked files.
It does not edit the Git index, configuration, branches or repository excludes.
An existing `.gitignore` is preserved, with a warning to check its existing policy.
Non-Git projects work without `git init`; absent Git does not block initialization.

No `feature.json`, specification, plan or tasks are generated. The core
`sdlc-100-spec` creates and selects the first feature under `.sdlc/specs` later.

## Repeated calls and manual-state completion

A project normally needs one successful call, regardless of later Agent/session
switches. Subsequent calls are safe:

- `initialized`: a new `.sdlc` was prepared.
- `completed`: missing compatible data was added to an existing partial directory.
- `unchanged`: nothing needed writing, including no mtime updates to existing files.

A manually created `.sdlc/memory`, existing `specs`, and a valid active
`feature.json` can be retained. Only missing `init-options.json` keys are merged;
existing values and unknown configuration keys are not silently replaced. Explicit
numbering conflicting with existing numbering stops rather than reconfiguring.

Existing `.specify`, legacy runtime/tool directories, unrecognized top-level
`.sdlc` entries, invalid JSON, non-sh profiles, unknown layout versions, wrong
file types, and symlinks stop for review. This is intentionally not a legacy data
migration tool. Do not delete data or use another initializer to bypass an error.
Local I/O failure can leave some newly created files; already-existing documents
are never used as reset targets. Fix the I/O problem and rerun to complete it.
Concurrent mutation of the same project is not supported as a transaction system.

## Direct script contract (support and engineering use)

The Skill resolves both absolute paths and calls:

```sh
python3 -I -B "$SDLC_PLUGIN_ROOT/scripts/python/init_project.py" \
  --project "$SDLC_PROJECT_ROOT" --json
```

Requires Python 3.9+ and Bash already installed. Optional `--dry-run` reports
planned changes without writing; optional `--feature-numbering timestamp` changes
the default for a new project only. There is no force/reset/upgrade switch.
`--project` is mandatory: the script never guesses from its installation path,
ambient `SDLC_INIT_DIR`, or an enclosing Git repository.

On success stdout is one JSON object with `status`, `dry_run`, selected paths,
created/updated/preserved paths and warnings. On failure it exits nonzero with an
error on stderr; a failed or dry-run call is not completed initialization.

## Continuation and verification

Normally INIT reports and stops. Run constitution (when not yet ratified), then
specify. Existing core Skills still stop on missing state and never silently
invoke another initializer. Explicit user authorization can request INIT followed
by another phase; INIT alone does not authorize implementation.

Engineering checks compare project-data defaults and constitution bytes with real
pinned CLI initialization in three empty projects. Synthetic fixtures also test
preservation and interoperability with existing core scripts. They do not prove
native client discovery or model-driven execution. See [VERIFICATION.md](VERIFICATION.md)
and the updated [smoke test](SMOKE-TEST.md).

## Names and existing data

The initializer now emits SDLC AI SPEC product wording and numbered Skill IDs in
new project README files. Existing README, constitution, features, config keys
and `speckit_version` (upstream provenance) are preserved; installation is not a
project-data rewrite. The legacy `.specify` detector still refuses implicit
conversion. Runtime Bash overrides use `SDLC_INIT_DIR`, `SDLC_FEATURE` and
`SDLC_FEATURE_DIRECTORY`. The blanket rejection of unrelated `SPECIFY_*` names
has been removed to retain upstream behavior. External state symlinks are allowed
by core path resolution unless they target plugin resources; INIT itself retains
its separately specified preservation and refusal rules.
There is no old-variable alias and no automatic RULE-to-INIT transition.

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

## Default document language

New `.sdlc/README.md` comes from the reviewed Chinese
`references/PROJECT-README.md`. The default constitution contains Chinese example
text and bilingual heading anchors. An existing project override, README or
constitution is still preserved verbatim; repeat INIT is not a translation tool.
A missing packaged README fails before writes, like a missing core template.
The guidance forbids language-tag comments, but does not delete legitimate comments
or create additional write permissions.
