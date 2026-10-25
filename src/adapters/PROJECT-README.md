# SDLC AI SPEC project data

This directory contains SDLC AI SPEC workflow data for the effective local or authority store.
- memory/constitution.md: project principles/scaffold; review with sdlc-010-rule.
- memory/.constitution-template.json: optional generation baseline for the constitution; not a phase/approval record.
- init-options.json: project defaults, not a global Agent selection.
- specs/: feature specifications, plans and tasks.
- feature.json: written by sdlc-100-spec, not by initialization.
- memory/long-term.md: optional shared project facts, decisions and their sources.
- workspaces/: current feature selection for each worktree sharing authority.
- store.json: explicit main-side authority and source registration.
- transactions/: prepared changes and recovery records; never imported from another copy.

Skills, scripts, applications and core templates stay in the user-installed
plugin. Do not run the upstream initializer here or copy plugin resources into this directory.
Re-running sdlc-000-init only completes missing compatible data; it does not reset
features or overwrite human documents. The local .gitignore excludes this data
from new Git additions; files already tracked by Git remain tracked.

A local copy takes precedence; a worktree without one normally reads and writes authority. Only main initiates collection. INIT imports knowledge by default when creating a local copy; requirements are opt-in. Imports never copy the current feature selection.
