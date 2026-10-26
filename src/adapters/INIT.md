# Initialize project data and storage

This local INIT capability runs in **@HOST@**. Preserve the original input and authorization. It does not install the upstream CLI or run another business stage.

## 1. Select and discover

Resolve `SDLC_PLUGIN_ROOT` from the loaded Skill. Select the explicit project or current workspace as `SDLC_PROJECT_ROOT`, preserving nested module boundaries. Ask only when that project is ambiguous. Read applicable project instructions; do not crawl all code to invent principles. Python 3.9+ and Bash are required; do not install dependencies or substitute another initializer.

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/init_project.py" --project "${SDLC_PROJECT_ROOT:?}" --discover --json
```

Discovery is read-only. Explain `SDLC_DIR`, `AUTHORITY_DIR`, `mode`, `local_exists`, `authority_exists`, `can_collect` and `sources`. Main is the primary workspace, not the branch name. A local copy wins; without one, ordinary commands may read and write authority. Only main initiates collection. A damaged local store never falls back.

## 2. Choose storage and initialize

If main has no authority and no source, initialize authority. If other copies exist, offer collection or blank initialization. Existing authority is completed without resetting documents; collection is a separate explicit choice. In a worktree with local data, complete local data. Without local data, disclose the authority path and ask whether to share it or create a local copy; recommend sharing. If neither exists, offer blank authority with sharing or local initialization. Other copies may only be collected from main. Reuse an explicit choice already supplied by the user.

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/init_project.py" --project "${SDLC_PROJECT_ROOT:?}" --mode shared --json
```

Use `--mode local` for an independent worktree copy. Its default `--seed knowledge` imports the constitution and project `memory/long-term.md` if present; repeat `--feature` with exact directory names to include selected requirements and associated artifacts. `--seed none` selects blank initialization. Existing local files are preserved, not refreshed by repeat INIT. Do not copy `feature.json` or another workspace's selection. Project long-term memory is optional project information, not personal memory or chat history.

Use `--dry-run` only for a requested preview. Only explicit requests use `--feature-numbering timestamp`; the default is sequential and existing valid numbering is preserved. There is no force or reset. A `needs_choice` result is not initialization success. Do not proceed before the required choice arrives.

The initializer creates missing data directories, options, constitution, README and ignore file. It preserves existing data and rejects unsupported layouts. Only a constitution actually generated from a template receives new `memory/.constitution-template.json` provenance. Imported history is retained when available; missing history is not invented. Provenance alone failing does not authorize overwriting the constitution. Ignore rules do not untrack existing Git files.

To register a designated authority or additional source, operate from main and use the resolved absolute paths:

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/sdlc_store.py" register --project "${SDLC_PROJECT_ROOT:?}" --authority '<absolute-authority-directory>' --source '<absolute-source-directory>'
```

Omit unneeded options and repeat `--source` as needed. An existing authority cannot be silently redirected. Registration is explicit and is not collection or data migration. Discover again after registration.

## 3. Explicit import or collection

Use `--kind collect` only from main, with explicitly selected source directories. Use `--kind import` in a worktree to refresh its local copy from authority. If establishing an authority from sources, apply collection before template initialization so generated provenance is not confused with imported history.

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" prepare --project "${SDLC_PROJECT_ROOT:?}" --kind collect --source '<absolute-source-directory>'
```

Default scope is constitution and project long-term memory. Repeat `--feature` to opt in to exact requirement directories. Inspect the returned file differences and source snapshots in `manifest.json`. When `multiple_sources` is true, explicitly state that more than one source contributes differences and list `changed_sources`. Do not mistake scanned workspace count for contributing source count.

Edit only the returned `proposal.json`. Identical files are skipped, unique additions default to copying. Resolve every other entry as `{"action":"copy","source":"<prepared-source>"}`, `{"action":"replace","text":"complete candidate text"}` or `{"action":"skip"}`. Compare semantic meaning, requirement identity and available evidence. Ask for unresolved policy choices; do not repeatedly confirm already authorized nonconflicting imports. No invented common ancestor, latest-file wins, checkbox union or deletion inferred from absence. Document import does not prove code integration or task verification.

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/store_changes.py" apply --project "${SDLC_PROJECT_ROOT:?}" --transaction '<returned-transaction-directory>'
```

The program rechecks bindings and source/target snapshots, acquires the store lock, records recovery data, publishes and verifies the selected changes. Changed inputs or unresolved decisions stop publication. On an interrupted application, inspect its diagnostic and use `recover` with the same project and transaction. Never bypass this by copying a directory or directly editing authority. Preserve source copies; do not automatically distribute or delete them.

## 4. Report and stop

Report the effective store, action, created/updated/preserved/imported or skipped files and warnings. Nonzero exit means stop, not manual repair or fallback. A preview is not a completed write. An applied import can be followed by the authorized initialization to fill missing structure; it does not authorize new requirements or another business stage.

Do not create new requirements, implement code, install tools, initialize Git, switch branches, commit or push. Git discovery is read-only. Suggest @CONSTITUTION_COMMAND@ or @SPEC_COMMAND@ only as appropriate; do not automatically execute them without existing user authorization.
