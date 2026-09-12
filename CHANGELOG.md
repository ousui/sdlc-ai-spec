# Changelog

## 1.0.0-beta — 2026-09-10

- Consolidate the Spec Kit core migration as the sole repository implementation.
- Place source, adapters, tools, tests and three generated packages at the root;
  remove superseded runtimes, plugin entries, plans and unrelated workflows.
- Define product version, Blade authorship and the declared repository centrally
  in plugin-metadata.json; generate consistent package manifests and provenance.
- Keep nine English upstream commands, runtime scripts and migrated template
  behavior unchanged. INIT and native client validation remain unimplemented.
- Retain engineering-only differential verification against three empty projects
  initialized by the installed pinned Spec Kit tool; add layout/metadata checks.

The beta version remains fixed during debugging. Use the exact Git commit and
CI evidence to identify a tested build. Earlier development is available in Git
history rather than copied into the current product tree.

## Unreleased changes (version remains 1.0.0-beta)

- Replace three copied distributions with one self-contained dist package.
- Generate three marketplace catalogs pointing to ./dist and native thin entries.
- Losslessly factor host workflow differences and bind them without AI/CLI calls.
- Vendor watched original generator source; add detached candidate upgrade/review.
- Add explicit installation, cache, upgrade and Codex/Cursor smoke-test procedures.
- INIT and native/model-driven acceptance remain deferred.

## Project-only initialization (same 1.0.0-beta)

- Add generated sdlc-init entries for all three hosts and one shared initializer.
- Complete fresh/partial project data without copying tools or invoking specify.
- Preserve existing documents and feature state; reject unsupported layouts.
- Add init-versus-installed-CLI projection tests and downstream script fixtures.
- Replace manual smoke-test seeding with the real init entry; no version/tag bump.

## PR #24 — numbered product naming (1.0.0-beta unchanged)

- Use the approved INIT/RULE/SPEC/CLAR/PLAN/TASK/XCHK/HUMA/IMPL/CONV IDs in all
  generated host entries, workflow filenames, loader arguments and references.
- Product ID `sdlc-ai-spec`, display name SDLC AI SPEC, SDLC runtime identifiers;
  keep `.sdlc` and existing business-artifact paths.
- Generate through the documented naming map, retaining untouched upstream
  provenance and independent parity checks.
- STATUS, RULE auto-init and shared host entrypoints remain separate work.

## Development tooling — uv migration

- Manage repository development/build/test dependencies with `pyproject.toml` and
  committed `uv.lock`; use Python 3.12 as the canonical development interpreter.
- Pin CI to uv 0.12.13 and use `uv sync --locked` / `uv run --locked`; isolate the
  upstream Spec Kit CLI in a separate `uv venv` installed through `uv pip`.
- Remove `tools/requirements.txt` as a second dependency source of truth.
- Keep installed `dist` runtime uv-independent; only BUILD.json metadata changes
  to record the new reproducibility inputs.
- Make path-valued unit-test assertions compare canonical filesystem identity so
  macOS `/var` and `/private/var` aliases do not produce false failures; run the
  engineering workflow on both Ubuntu 24.04 and macOS 15 ARM64.

## Shared core Skills and zh-CN projection (1.0.0-beta)

- Nine core entries now share dist/skills; INIT keeps three minimal host-policy
  wrappers. Each host still exposes ten capabilities without changing its policy.
- Full core workflow prose, metadata, binding and INIT guidance are localized.
  Template skeletons and machine contracts stay English; authored content is Chinese.
- Reviewed locale assets bind exact rendered inputs; stale translations block new
  packages. Localization-only candidate refresh rebuilds and invalidates old evidence.
- Correct local-only event-key renaming, blanket unrelated environment rejection
  and blanket external-state symlink rejection. No independent upstream bug fixes.

## Unified entries and read-only STATUS (1.0.0-beta)

- Move INIT into public skills/ and remove all three host-private Skill directories.
- Omit only the approved UI/selection metadata; use each host's default behavior.
- Add local sdlc-status with bounded standard-library collection, JSON/Chinese
  stdout, explicit/current/list selection and no persistence or project execution.
- Preserve upstream sources, nine workflow bodies, English template structures
  and existing INIT data behavior. STATUS adds no stage completion verdicts.
- Expand synthetic path/format/read-only tests and retain deterministic build,
  localization freshness and upstream upgrade compatibility checks.

## Review and document-localization corrections (1.0.0-beta)

- REV-007: return an actual selected template path to SPEC, without changing the
  content resolver used by other commands.
- REV-008–010: correct STATUS example-title, nested-list and code/comment handling;
  retain query nonmutation and explicit uncertainty for unsupported task formats.
- Localize five default template presentations, the 16-item built-in requirements
  checklist and new-project README; preserve machine anchors and user-owned files.
- Prohibit artificial language-tag comments; extend incremental locale freshness,
  whole-template baseline projection and negative-control regression tests.
## Constitution generation provenance (1.0.0-beta)

- Record the exact generated constitution SHA-256 and source only when INIT actually
  creates the constitution; preserve existing/manual projects without backfilling.
- Keep provenance optional and non-authoritative: it is not phase completion, approval,
  signature, template-sync permission, or a new prerequisite for core workflows.
- Let read-only STATUS compare stable raw constitution bytes with the historical baseline,
  separately reporting record health and placeholder observations without current-template guesses.
- Preserve malformed/orphaned records for diagnosis, keep provenance-only write failures
  non-destructive, and add lifecycle/read-only regression coverage.

## 仓库布局与维护文档可读性整理（1.0.0-beta）

- 将根目录 `adapters/` 迁移到 `src/adapters/`，明确其属于产品源码/构建输入，而不是 `tools/` 实现或 Runtime 目录；六个既有 adapter 文件保持原字节和权限。
- 新增 `src/adapters/README.md`，说明当前职责、数据流、修改规则，以及未来按 `workflows/`、`resources/`、`scripts/` 进一步拆分的演进参考。
- 将 `AGENTS.md` 与 `docs/INITIALIZATION.md` 的维护说明统一为简体中文；命令、路径、环境变量、状态枚举和其他机器契约保持原样。
- 在 `docs/LOCALIZATION.md` 明确上游原文、英文适配基线、中文呈现、维护文档和 `dist` 的语言分层；`src/adapters/*.md` 继续作为英文 source baseline，不改现有翻译内容。
- 同步构建器、移植器、本地化 catalog、文档和测试中的路径引用；最终 Runtime workflow、模板、脚本、bindings 和用户文案保持不变，仅构建来源元数据及 INIT/STATUS `metadata.source` 反映新路径。
