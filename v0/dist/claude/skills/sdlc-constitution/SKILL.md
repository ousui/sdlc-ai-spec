---
name: sdlc-constitution
description: Create or update the project constitution from interactive or provided principle inputs.
compatibility: Requires an initialized .sdlc project, Bash and Python 3.9+; INIT is not included in this engineering build
metadata:
  author: github-spec-kit
  source: templates/commands/constitution.md
user-invocable: true
disable-model-invocation: false
argument-hint: Principles or values for the project constitution
---

<!-- SDLC-PACKAGE-BINDING:BEGIN -->
## Installed package and project binding

This is the claude package of SDLC's fixed Spec Kit core port. Resolve paths before executing the unchanged workflow below.

- Use the host-provided `${CLAUDE_PLUGIN_ROOT}` or the absolute path of this loaded SKILL.md. `SDLC_PLUGIN_ROOT` is the package directory two levels above this skill's directory (`skills/<name>/SKILL.md`). Do not infer it from the business working directory, scan other installed versions, or assume this variable is already exported.
- Keep the shell working directory in the selected business project. Run `SDLC_HOST=claude bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/project-paths.sh"` to resolve the nearest initialized `.sdlc`. When the user explicitly selected a project, pass its absolute path as command-local `SPECIFY_INIT_DIR`. Use the returned `PROJECT_ROOT` as `SDLC_PROJECT_ROOT`. If the project is missing or invalid, stop; this engineering build does not yet include `sdlc-init`.
- Set these resolved absolute values in EVERY shell invocation that uses them; shell state is not guaranteed to persist across tool calls. `${VAR:?}` intentionally fails on an unresolved variable. For non-shell file tools, substitute the resolved absolute value rather than passing `${VAR}` literally. Never change directory to the plugin to fix a resource lookup.
- Before creating/updating feature files, call the same `project-paths.sh --feature <resolved-feature-directory>` with command-local `SPECIFY_INIT_DIR` to validate that explicit paths and symlinks cannot target this plugin. The script is read-only and is not an initializer. Project state, current feature and constitution are never written under the plugin.
- This package carries the core-only, no-Preset/no-Extension/no-event profile. Do not install or invoke extensions or a `specify` command to satisfy a reference. If the project contains `.sdlc/extensions.yml`, installed presets or extension state, stop and report that profile as unsupported. The upstream conditional hook text is retained below for source equivalence, not an authorization to enable that optional subsystem.
- `$ARGUMENTS` denotes the current invocation's user input. Where the host does not substitute it, read that input from the conversation; never treat the literal placeholder as the feature description.
<!-- SDLC-PACKAGE-BINDING:END -->



## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Scope Guard

This command's own work is limited to updating the project constitution itself. Dependent templates
and commands read the constitution at runtime and are not modified here.

- Classify every part of the user input as either constitution content or a separate,
  non-governance intent.
- If the input includes feature implementation, code generation, refactoring, building, or
  deployment requests, you **MUST NOT** execute them. Extract them as deferred intents instead.
- You **MUST NOT** create, modify, or delete application source files, feature routes,
  components, tests, deployment files, or other artifacts unrelated to the constitution
  workflow.
- If it is unclear whether an instruction is constitution content, ask for clarification before
  making changes.
- After completing the constitution update, include a `Next Actions` section for each deferred
  intent. List the original intent and suggest the appropriate follow-up Spec Kit command, such
  as `/sdlc:sdlc-specify`, without invoking it.
- If there are no non-governance intents, omit the `Next Actions` section.

## Pre-Execution Checks

**Check for extension hooks (before constitution update)**:
- Check if `.sdlc/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_constitution` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- When constructing command invocations from hook command names, replace dots (`.`) with hyphens (`-`). For example, `sdlc.git.commit` → `/sdlc:sdlc-git-commit`.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:sdlc-...` or `$sdlc-...`). Emitting the block alone does not run the hook.
- If no hooks are registered or `.sdlc/extensions.yml` does not exist, skip silently

## Outline

You are updating the project constitution at `.sdlc/memory/constitution.md`. The active
constitution scaffold is resolved at command time from `constitution-template` through the Spec Kit
preset/template resolution stack.

Follow this execution flow:

1. Run `SDLC_HOST=claude SPECIFY_INIT_DIR="${SDLC_PROJECT_ROOT:?}" bash "${SDLC_PLUGIN_ROOT:?}/scripts/bash/resolve-template.sh" constitution-template --json` from the repository root and parse `TEMPLATE_CONTENT` as the active template.
   - The shared resolver applies project overrides, composing preset layers, and extension layers
     before the core template fallback. It MUST succeed before continuing.
   - If it fails, stop and report the resolution error; do not continue with only one contributing
     template layer.
   - If `.sdlc/memory/constitution.md` exists, load it as the source of current project-specific
     values and amendments. Preserve information that is still applicable when applying the newly
     resolved scaffold.
   - If it does not exist, use the resolved template as the initial document.
   - Do not write back to any versioned template layer.
   - Identify every placeholder token of the form `[ALL_CAPS_IDENTIFIER]`.
   **IMPORTANT**: The user might require less or more principles than the ones used in the template. If a number is specified, respect that - follow the general template. You will update the doc accordingly.

2. Collect/derive values for placeholders:
   - If user input (conversation) supplies a value, use it.
   - Otherwise infer from existing repo context (README, docs, prior constitution versions if embedded).
   - For governance dates: `RATIFICATION_DATE` is the original adoption date (if unknown ask or mark TODO), `LAST_AMENDED_DATE` is today if changes are made, otherwise keep previous.
   - `CONSTITUTION_VERSION` must increment according to semantic versioning rules:
     - MAJOR: Backward incompatible governance/principle removals or redefinitions.
     - MINOR: New principle/section added or materially expanded guidance.
     - PATCH: Clarifications, wording, typo fixes, non-semantic refinements.
   - If version bump type ambiguous, propose reasoning before finalizing.

3. Draft the updated constitution content using the resolved template as the required structure:
   - Replace every placeholder with concrete text (no bracketed tokens left except intentionally retained template slots that the project has chosen not to define yet—explicitly justify any left).
   - Preserve heading hierarchy and comments can be removed once replaced unless they still add clarifying guidance.
   - Ensure each Principle section: succinct name line, paragraph (or bullet list) capturing non‑negotiable rules, explicit rationale if not obvious.
   - Ensure Governance section lists amendment procedure, versioning policy, and compliance review expectations.

4. Produce a Sync Impact Report (prepend as an HTML comment at top of the constitution file after update):
   - Version change: old → new
   - List of modified principles (old title → new title if renamed)
   - Added sections
   - Removed sections
   - Follow-up TODOs if any placeholders intentionally deferred.

5. Validation before final output:
   - No remaining unexplained bracket tokens.
   - Version line matches report.
   - Dates ISO format YYYY-MM-DD.
   - Principles are declarative, testable, and free of vague language ("should" → replace with MUST/SHOULD rationale where appropriate).

6. Write the completed constitution back to `.sdlc/memory/constitution.md` (overwrite).

7. Output a final summary to the user with:
   - New version and bump rationale.
   - Any TODO placeholders or deferred items requiring manual follow-up.
   - Suggested commit message (e.g., `docs: amend constitution to vX.Y.Z (principle additions + governance update)`).
   - A `Next Actions` section for any deferred non-governance intents.

Formatting & Style Requirements:

- Use Markdown headings exactly as in the template (do not demote/promote levels).
- Wrap long rationale lines to keep readability (<100 chars ideally) but do not hard enforce with awkward breaks.
- Keep a single blank line between sections.
- Avoid trailing whitespace.

If the user supplies partial updates (e.g., only one principle revision), still perform validation and version decision steps.

If critical info missing (e.g., ratification date truly unknown), insert `TODO(<FIELD_NAME>): explanation` and include in the Sync Impact Report under deferred items.

Write only `.sdlc/memory/constitution.md`; do not create or modify template source files.

## Post-Execution Checks

**Check for extension hooks (after constitution update)**:
Check if `.sdlc/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.after_constitution` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- When constructing command invocations from hook command names, replace dots (`.`) with hyphens (`-`). For example, `sdlc.git.commit` → `/sdlc:sdlc-git-commit`.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:sdlc-...` or `$sdlc-...`). Emitting the block alone does not run the hook.
- If no hooks are registered or `.sdlc/extensions.yml` does not exist, skip silently
