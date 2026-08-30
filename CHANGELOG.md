# Changelog

本文件记录 `sdlc-ai-spec` Plugin 的重要变更。Plugin Version 与领域 Spec Version 独立管理。

## Unreleased

- Added the shared Runtime Kernel for invocation/result envelopes, Phase operation routing, and build-time source locks.
- Added a stable Runtime Contract Registry and Source Lock Schema under `skills/_shared/`.
- Added an atomic CTX Project Boundary lineage registry and a strictly read-only Artifact Catalog.
- Reserved `sdlc-status` as the cross-lifecycle read-only status utility name.
- Standardized self-contained runtime contracts and removed legacy `sdlc-project-context` work items.
- Implemented the shared Local SQLite ArtifactStore with Schema v1, nine logical operations, a JSON CLI, verifier binding, and automated tests.
- Finalized sdlc-ai-spec v1.1 as the current stable Spec Snapshot and switched Plugin development to the v1.1 Source of Truth.
- Closed v1.1 Review findings `V11-DR-MAJ-001` and `V11-DR-MAJ-002` by making the Claim Provider the sole IMP ID and Revision Reservation allocator, and by separating Revision Control Reservation from the first atomic full-Payload write.
- Created the sdlc-ai-spec v1.1 review snapshot with a provider-neutral Artifact Store Contract and preserved v1 Artifact semantics.
- Clarified that Local SQLite Canonical Revision authority covers the primary Canonical Blob and the complete locally owned Manifest-Member closure.
- Replaced the multi-provider storage architecture and v1.1 Delta Plan with a Local SQLite-only Canonical Store decision at `.sdlc/store.sqlite3`; retained Human Review View as a non-authoritative Plugin Projection.
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

## 0.1.0 - 2026-08-28

- Initialized Cursor, Claude Code, and Codex native plugin manifests.
- Established one shared `skills/` source directory.
- Added plugin development, compatibility, and handoff documentation.
- No production skills are included yet.
