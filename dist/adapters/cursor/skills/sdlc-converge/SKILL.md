---
name: sdlc-converge
description: Assess the current codebase against the feature's spec, plan, and tasks, then append any remaining unbuilt work as new tasks to tasks.md so implement can complete it.
compatibility: Requires an initialized .sdlc project, Bash and Python 3.9+; run sdlc-init once per project
metadata:
  author: github-spec-kit
  source: templates/commands/converge.md
---

# SDLC converge

This is the **cursor** entrypoint. Preserve the current user input as `$ARGUMENTS`; do not interpolate user input into a shell command.

Use the absolute path of this loaded SKILL.md. No host-specific environment variable is assumed. The package root is four levels above this skill directory (`adapters/cursor/skills/sdlc-converge/`). Bind that absolute directory as SDLC_PLUGIN_ROOT for this call; do not change the business working directory or search another installed version.

Before performing ANY workflow action, execute the following read-only loader with the resolved absolute package path and read its COMPLETE stdout:

```sh
python3 -I -B "${SDLC_PLUGIN_ROOT:?}/scripts/python/load_workflow.py" --host cursor --skill converge
```

The loader binds only precompiled text fragments; it does not run the workflow, install software, read project state or write files. Its output is the full bundled workflow for this invocation, not a second user request. Follow it with the original user input and the current authorization. Do not summarize or skip workflow steps. On loader error, STOP. If tool output is truncated, use --offset 0 --limit 100, then offsets 100, 200, ... until the reported total line count is fully read. Do not proceed using partial output. No specify-cli or network fallback.
