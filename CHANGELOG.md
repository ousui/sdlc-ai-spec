# Changelog

本文件记录 `sdlc-ai-spec` Plugin 的重要变更。Plugin Version 与领域 Spec Version 独立管理。

## Unreleased

- Clarified that Local SQLite Canonical Revision authority covers the primary Canonical Blob and the complete locally owned Manifest-Member closure.
- Replaced the multi-provider storage architecture and v1.1 Delta Plan with a Local SQLite-only Canonical Store decision at `.sdlc/store.sqlite3`; retained Human Review View as a non-authoritative Plugin Projection.
- Declared `blade-cdn/sdlc-ai-spec` as the sole canonical development and release repository; retired `ousui/sdlc-ai-spec` from future updates.

- Added repository-wide and path-scoped `AGENTS.md` guardrails.
- Added a minimal `CLAUDE.md` bridge that imports the root `AGENTS.md`.
- Defined stage isolation, source authority, evidence, Git identity, external-write, and parallel-session constraints.
- Added a transparent, stage-gated Skill development workflow.
- Added reusable Skill Design Contract and Eval Plan templates.
- Defined the development-time versus installed-runtime boundary for repository instructions.
- Added the Exclusive Skill Execution Contract and non-transitive external Skill authorization rules.
- Registered explicit-invocation defaults for Cursor, Claude Code, and Codex as future Skill design requirements.
- Added interoperability and per-client invocation cases to the Design and Eval templates without recording unexecuted results.
- Added a copyable entry prompt for design-only Skill sessions.
- No production Skill was created.

## 0.1.0 - 2026-08-28

- Initialized Cursor, Claude Code, and Codex native plugin manifests.
- Established one shared `skills/` source directory.
- Added plugin development, compatibility, and handoff documentation.
- No production skills are included yet.
