# Initialize project data

This is SDLC AI SPEC's project-only initializer, not the upstream CLI installer. This
invocation is in **@HOST@**. Use the original user input and current authorization.
Initialization never requires a pre-existing `.sdlc` or an installed upstream CLI.

## 1. Select the project and installed package

Resolve `SDLC_PLUGIN_ROOT` from this already-loaded Skill/package (as the wrapper
instructs). Select the explicit project directory from the user's request or the
current workspace root. Use its resolved absolute path as `SDLC_PROJECT_ROOT`.
Do not substitute a parent Git root: a nested module such as `helloserver` can be
the intended project. When no path is explicit and the working directory is a
subdirectory of an already initialized workspace, use that workspace's `.sdlc`
root. In a multi-root or genuinely ambiguous workspace, ask which root to use.
Never select the plugin directory, home or filesystem root by guessing.

Read any applicable project instructions. Do not inspect all business code to
invent project principles. Confirm Python 3.9+, Bash and the bundled script are
available. If an execution dependency is missing, report it; do not install one
or fall back to the upstream CLI, `uv`, network access or ad-hoc shell scaffolding.

## 2. Run the deterministic initializer once

Pass the selected absolute paths in this tool call; do not rely on shell variables
persisting between calls. Preserve quoting, and do not interpolate raw natural
language user input into a shell command.

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/init_project.py" --project "${SDLC_PROJECT_ROOT:?}" --json
```

Use `--dry-run` only when the user requested a preview. Use
`--feature-numbering timestamp` only when explicitly requested; the default is
sequential and existing valid numbering is preserved. No `--force` or reset exists.

The script creates `.sdlc/memory/`, `.sdlc/specs/`, `init-options.json`, a project
copy of the resolved constitution template, a data README and `.sdlc/.gitignore`.
When this invocation actually creates `memory/constitution.md`, it also attempts to
record the exact generated-byte SHA-256 and source in
`memory/.constitution-template.json`. The record is generation provenance only:
matching or differing bytes do not prove RULE completion, approval or governance
quality. Existing constitutions are preserved and never backfilled with invented
historical provenance. A provenance-only write failure is reported without deleting
or rewriting the created constitution.

The initializer does not copy Skills, scripts, applications, integrations or core
templates into the project. Existing compatible partial/manual `.sdlc` directories
are completed. Existing documents and feature selection are preserved. Malformed,
symlinked, legacy or unsupported profiles stop with a diagnostic, not automatic
conversion.

On nonzero exit, report the diagnostic and STOP. Do not fabricate success,
hand-repair a legacy layout, delete `.sdlc`, or invoke a different initializer.
On success, report `initialized`, `completed` or `unchanged`, the selected project,
created/updated/preserved paths and warnings. A successful dry-run is not an
initialized project. Ignore rules do not untrack files already in Git.

## 3. Stop at the initialization boundary

Do not create a feature, `feature.json`, spec, plan or task list. Do not implement
business code, change user/system/Agent configuration, initialize Git, create or
switch branches, commit, push, or install tools. Git inspection is read-only.

Initialization is normally needed once per project, not once per Agent or session.
Repeat calls are safe completion/no-ops, not resets. Suggest @CONSTITUTION_COMMAND@
to ratify project principles, or @SPEC_COMMAND@ to resume the already requested
specification. Do not launch either automatically unless the current user request
explicitly authorizes continuation beyond initialization.
