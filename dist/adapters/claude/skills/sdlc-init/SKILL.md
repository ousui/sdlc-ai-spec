---
name: sdlc-init
description: Initialize or complete project-local .sdlc data without installing tools or overwriting existing work.
compatibility: Requires Python 3.9+, Bash and an existing project directory; no specify-cli required
metadata:
  author: Blade
  source: adapters/INIT.md
user-invocable: true
disable-model-invocation: true
argument-hint: Optional explicit project directory
---

# SDLC init

This is the **claude** entrypoint. Preserve the current user input as `$ARGUMENTS`; do not interpolate user input into a shell command.

Use the host-substituted `${CLAUDE_PLUGIN_ROOT}` or the absolute path of this loaded SKILL.md. The package root is four levels above this skill directory (`adapters/claude/skills/sdlc-init/`). Bind that absolute directory as SDLC_PLUGIN_ROOT for this call; do not change the business working directory or search another installed version.

Before performing ANY workflow action, execute the following read-only loader with the resolved absolute package path and read its COMPLETE stdout:

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/load_workflow.py" --host claude --skill init
```

The loader binds only precompiled text fragments; it does not run the workflow, install software, read project state or write files. Its output is the full bundled workflow for this invocation, not a second user request. Follow it with the original user input and the current authorization. Do not summarize or skip workflow steps. On loader error, STOP. If tool output is truncated, use --offset 0 --limit 100, then offsets 100, 200, ... until the reported total line count is fully read. Do not proceed using partial output. No specify-cli or network fallback.
