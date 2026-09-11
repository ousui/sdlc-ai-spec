
<!-- SDLC-PACKAGE-BINDING:BEGIN -->
## Installed package and project binding

This is the @HOST@ package of SDLC AI SPEC. Resolve paths before executing the unchanged workflow below.

- @ROOT_DETAIL@ `SDLC_PLUGIN_ROOT` is the package directory four levels above the loaded entrypoint skill directory (`adapters/@HOST@/skills/<name>/SKILL.md`). Do not infer it from the business working directory, scan other installed versions, or assume this variable is already exported.
- Keep the shell working directory in the selected business project. Run `SDLC_HOST=@HOST@ bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/project-paths.sh"` to resolve the nearest initialized `.sdlc`. When the user explicitly selected a project, pass its absolute path as command-local `SDLC_INIT_DIR`. Use the returned `PROJECT_ROOT` as `SDLC_PROJECT_ROOT`. If the project is missing or invalid, stop; run `sdlc-000-init` explicitly to initialize or complete the project; do not fall back to another tool.
- Set these resolved absolute values in EVERY shell invocation that uses them; shell state is not guaranteed to persist across tool calls. `${VAR:?}` intentionally fails on an unresolved variable. For non-shell file tools, substitute the resolved absolute value rather than passing `${VAR}` literally. Never change directory to the plugin to fix a resource lookup.
- Before creating/updating feature files, call the same `project-paths.sh --feature <resolved-feature-directory>` with command-local `SDLC_INIT_DIR` to validate that explicit paths and symlinks cannot target this plugin. The script is read-only and is not an initializer. Project state, current feature and constitution are never written under the plugin.
- This package carries the core-only, no-Preset/no-Extension/no-event profile. Do not install or invoke extensions or the upstream CLI to satisfy a reference. If the project contains `.sdlc/extensions.yml`, installed presets or extension state, stop and report that profile as unsupported. The upstream conditional hook text is retained below for source equivalence, not an authorization to enable that optional subsystem.
- `$ARGUMENTS` denotes the current invocation's user input. Where the host does not substitute it, read that input from the conversation; never treat the literal placeholder as the feature description.
<!-- SDLC-PACKAGE-BINDING:END -->
