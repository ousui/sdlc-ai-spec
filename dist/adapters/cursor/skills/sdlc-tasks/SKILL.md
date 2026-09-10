---
name: sdlc-tasks
description: Generate an actionable, dependency-ordered tasks.md for the feature based on available design artifacts.
compatibility: Requires an initialized .sdlc project, Bash and Python 3.9+; run sdlc-init once per project
metadata:
  author: github-spec-kit
  source: templates/commands/tasks.md
---

# SDLC tasks

This is the **cursor** entrypoint. Preserve the current user input as `$ARGUMENTS`; do not interpolate user input into a shell command.

Use the absolute path of this loaded SKILL.md. No host-specific environment variable is assumed. The package root is four levels above this skill directory (`adapters/cursor/skills/sdlc-tasks/`). Bind that absolute directory as SDLC_PLUGIN_ROOT for this call; do not change the business working directory or search another installed version.

Before performing ANY workflow action, execute the following read-only loader with the resolved absolute package path and read its COMPLETE stdout:

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/load_workflow.py" --host cursor --skill tasks
```

The loader binds only precompiled text fragments; it does not run the workflow, install software, read project state or write files. Its output is the full bundled workflow for this invocation, not a second user request. Follow it with the original user input and the current authorization. Do not summarize or skip workflow steps. On loader error, STOP. If tool output is truncated, use --offset 0 --limit 100, then offsets 100, 200, ... until the reported total line count is fully read. Do not proceed using partial output. No specify-cli or network fallback.
