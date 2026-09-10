# v0 source-port work package

Repository: https://github.com/ousui/sdlc-ai-spec
Upstream: github/spec-kit v1.0.5 @ a4e25ce6b96dc8e85f84206c6a54353fa9c5260b.

The user's 2026-09-10 instruction authorizes source-based migration and engineering validation in this isolated subtree. It supersedes historical phase numbering, Chinese template content, ArtifactStore, one-phase-per-session and old-runtime requirements for v0 only. Preserve unrelated repository content.

This work package ports the nine upstream local skills (constitution, specify, clarify, plan, tasks, analyze, checklist, implement, converge), English templates and their required Bash scripts into user-scoped Codex, Claude Code and Cursor packages. Do not implement INIT yet. Do not add GitHub integration, CTX/status/RLS, an orchestrator, database, external service, business rules or translations.

Build from pinned source, not from initialized example files. Verify against independent empty-project outputs produced by an installed pinned specify-cli for codex, claude and cursor-agent, using --script sh and --integration-options=--events=false, without presets or extensions. Those upstream init calls are fixture acquisition, not construction of sdlc-init.

Allowed validation: deterministic resource/content comparisons, syntax checks, manifest checks, code tests with synthetic temporary filesystem fixtures, dependency and boundary checks. Do not call an LLM, run a skill against a real project, install plugins into the user's clients, or claim native host compatibility from static checks.

Keep plugin resource root separate from project data root. Shared resources are read-only at runtime. Project data lives in .sdlc. A missing/invalid project cannot fall back to the plugin directory. Preserve upstream semantic content except documented name/path/packaging changes.

Commit and push only to the explicit implementation branch. Do not change main, prior design commits, old runtime files or unrelated workflows. The v0-engineering workflow exists only to install the pinned upstream and run this work package's checks; contents permission is read-only, no credentials or production secrets are used.

Report source SHA, upstream SHA, exact commands/results, allowed deltas and checks not performed. A baseline-acquisition pass is not a migration pass. Stop before INIT construction.
