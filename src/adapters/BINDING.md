
<!-- SDLC-PACKAGE-BINDING:BEGIN -->
## Installed package and project binding

This is the @HOST@ package of SDLC AI SPEC. Resolve paths before executing the unchanged workflow below.

- @ROOT_DETAIL@ `SDLC_PLUGIN_ROOT` is the package directory two levels above the loaded core skill directory (`skills/<name>/SKILL.md`). Do not infer it from the business working directory or assume this variable is already exported. Use one complete package during normal execution. If an update removes that package, locate the current package from the host's current Skill catalog, installation record or an explicit user path; never guess by cache version ordering. Read its entry and `skills/sdlc-refine/references/compatibility.md`, assess compatibility and prior effects, then reload the complete workflow from the selected package. Do not mix packages or replay unverified writes. A version difference or a missing old package alone does not require migration or another user invocation.
- Keep the shell working directory in the selected business project. Run `SDLC_HOST=@HOST@ bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/project-paths.sh"` to resolve the selected code project and its effective `.sdlc` store. When the user explicitly selected a project, pass its absolute path as command-local `SDLC_INIT_DIR`. Use the returned `PROJECT_ROOT` as `SDLC_PROJECT_ROOT`. If the project is missing or invalid, stop; run `sdlc-000-init` explicitly to initialize or complete the project; do not fall back to another tool.
- Set these resolved absolute values in EVERY shell invocation that uses them; shell state is not guaranteed to persist across tool calls. `${VAR:?}` intentionally fails on an unresolved variable. For non-shell file tools, substitute the resolved absolute value rather than passing `${VAR}` literally. Never change directory to the plugin to fix a resource lookup.
- Before creating/updating feature files, call the same `project-paths.sh --feature <resolved-feature-directory>` with command-local `SDLC_INIT_DIR` to validate that explicit paths and symlinks cannot target this plugin. The script is read-only and is not an initializer. Project state, current feature and constitution are never written under the plugin.
- This package carries the core-only, no-Preset/no-Extension/no-event profile. Do not install or invoke extensions or the upstream CLI to satisfy a reference. If the project contains `.sdlc/extensions.yml`, installed presets or extension state, stop and report that profile as unsupported. The upstream conditional hook text is retained below for source equivalence, not an authorization to enable that optional subsystem.
- `$ARGUMENTS` denotes the current invocation's user input. Where the host does not substitute it, read that input from the conversation; never treat the literal placeholder as the feature description.
<!-- SDLC-PACKAGE-BINDING:END -->

## Workspace storage extension

The selected code project remains `SDLC_PROJECT_ROOT`; the resolver also returns `SDLC_DIR`, `AUTHORITY_DIR`, `FEATURE_JSON`, `mode` and `can_collect`. An independent local `.sdlc` takes precedence; without it, ordinary commands read and write authority. Only main may collect copies. Never bypass local data or an invalid local selection by targeting authority. Main means the primary workspace, not a branch name.

If main's registry is unavailable, valid independent local work may continue: `AUTHORITY_DIR` and `authority_exists` are null and `authority_error` reports the cause. Do not guess an authority path; authority imports and unverifiable external feature targets or local aliases stop.

Interpret every `.sdlc/` data reference below relative to `SDLC_DIR`; interpret `.sdlc/feature.json` as `FEATURE_JSON`. Keep code, implementation, tests and non-data relative paths in `SDLC_PROJECT_ROOT`. Resolve an explicit feature with `project-paths.sh --feature`; use its returned `FEATURE_DIR`. Read `memory/long-term.md` under the effective store if present as project context; it does not override the constitution or user instructions. Do not copy another workspace's selection.

Explicit feature input takes precedence over saved selection. Merely resolving storage, creating a new feature or editing explicitly named files does not require a valid unused selection. When the workflow needs saved selection, use only this workspace's record; do not fall back to another store. Preserve the existing persistence and read-only rules. Explicit `.` or `./` selects the code project directory, subject to the same path checks. Independent local and authority data roots must not overlap.

For model-authored writes inside the effective store, prepare a candidate before editing documents:

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" prepare --project "${SDLC_PROJECT_ROOT:?}" --kind edit --path '<store-relative-file>'
```

Repeat `--path` for all files in this change. Edit only the returned `proposal.json`: each prepared file uses `{"action":"replace","text":"complete candidate text"}`, `{"action":"skip"}`, or `{"action":"delete"}` for an explicitly authorized retired document. Delete removes a regular document, not a control file or leaf symlink; an empty replacement is still a file. Include active references in the same reviewed change. Import/collection never infer deletion from missing source files. Then publish through the program:

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" apply --project "${SDLC_PROJECT_ROOT:?}" --transaction '<returned-transaction-directory>'
```

Ordinary edit snapshots cover only the selected files, their task ID history when editing `tasks.md`, `init-options.json` and the current workspace's `FEATURE_JSON`. Unrelated artifacts and other worktrees' selections do not invalidate the candidate; changes to these targets or required bindings do. Import and collection retain their source/target snapshot checks.

Task numbering after refinement is an explicit local storage extension. Before TASK, CONV or an authorized revision allocates new task IDs, read the selected requirement's active IDs and reserved maximum:

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/task_ids.py" --project "${SDLC_PROJECT_ROOT:?}" --feature '<resolved-feature-directory>'
```

Use the returned `high_water` as the allocation maximum (`M` in CONV), starting new IDs at `next_id`. Keep IDs for retained obligations; never assign a retired ID to different work. A new requirement with no history still starts at `T001`. The read-only helper includes `.task-ids.json` beside `tasks.md`; this is numbering metadata, not active work or evidence of completion. Do not restore retired tasks from transaction snapshots or treat reserved numbers as implementation gaps. TASK preserves this history when regenerating an existing requirement; IMPL executes only active task checkboxes. The edit transaction maintains the maximum when removing IDs and thereafter, even when deleting the entire task file, and rejects reuse of retired IDs. It does not retain discarded business text or create history for unchanged task sets. Never manually reset or delete the history; apply/recover it with the task change. An unreadable record stops allocation rather than restarting at `T001`.

This applies existing workflow authorization, not new permission to change other artifacts. Unresolved decisions or changed inputs stop publication; prepare again rather than forcing stale changes. Packaged writing helpers acquire the same store lock. Explicit external feature directories retain their existing path checks; do not redirect them into authority when a local copy exists. Read-only stages do not prepare or apply candidates. An interrupted application is diagnosed and can be restored with the same program's `recover` action; never delete another operation's lock or overwrite later edits to force recovery.

If a stopped process left a lock after INIT or preparation, use `sdlc_store.py recover-lock --project` with the selected project. It only releases a lock whose recorded process is no longer running; an interrupted data application still requires `store_changes.py recover`. Incomplete ownership or a live owner stops recovery.
