# Plugin Development Handoff

## 当前目标

把 `docs/v1.0/` 中稳定的研发与变更交付规范逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。v1.0 保持冻结，后续 Store 语义只通过新的 Spec Snapshot 演进。

## 当前阶段

Storage Architecture Scope Correction 已完成。原多 Provider、分布式 Store 架构和对应 v1.1 Delta Plan 已被 SQLite-only 决策替换。

当前架构固定：

- 当前 Plugin 只支持项目根目录下的 `.sdlc/store.sqlite3`；
- Local SQLite Store 是当前唯一 Canonical Artifact Store；
- v1.1 只计划新增 `artifact-store-spec.md`；
- Human Review View 是 Plugin Projection，不是正式领域 Artifact；
- 当前未创建 `docs/v1.1/`，也未实现 SQLite、Projection 或 Skill。

候选 Skill `sdlc-project-context` 的 Design Status 继续为 `draft`。在 SQLite-only v1.1 Source of Truth 完成前不得批准或实现。

## 本工作包已完成

- 重写 `docs/architecture/artifact-store-and-projection.md`，删除多 Store 与分布式设计，固定 Local SQLite Authority、最小 Store Contract、Runtime Workspace、Candidate Material 和 Human Review View 边界。
- 重写 `docs/architecture/v1.1-spec-delta-plan.md`，只保留一个新增正式 Spec，并把 v1.1 正式 Spec 数量修正为 25。
- 保留逐文件影响矩阵；Core、CTX、DSN、IMP 只解除物理目录耦合，其他 Phase 与 Domain Spec 只计划必要版本和引用更新。
- 在 `docs/plugin-development/DEVELOPMENT.md` 登记 SQLite-only 实现决定和单一 `ArtifactStore` 模块边界。
- 更新 `CHANGELOG.md`，记录本次架构收敛。

## 已确定决策

- 一个项目只有一个本地 Canonical Store，固定为 `<project-root>/.sdlc/store.sqlite3`。
- 不增加 Store 或 Provider 配置文件，不建设多 Provider 框架。
- Canonical Authority 是 SQLite 中保存的准确 Canonical Revision；Review、临时和导出文件不具有 Authority。
- Canonical 内容保持完整 Markdown/YAML Blob，并保存 Canonical Blob SHA-256。
- v1.1 的 `artifact-store-spec.md` 只定义最小逻辑 Store Contract，不定义 SQLite Schema。
- Human Review View 的格式、映射 Schema 与编辑器适配留到 Skill 实现阶段。
- v1.0 的 Artifact Contract ID、字段、ID、Revision、Reference、Status、Gate 与 Final Confirmation 保持不变。

## 当前验证结果

- 工作包输入基线为 `main@e23b982aa80d545f88c6fb0dfb3cd0e5229190bf`，开始时 `git status --short` 为空。
- Origin Fetch / Push 指向 `git@github.com:blade-cdn/sdlc-ai-spec.git`；有效 SSH Host 为 `github.com`。
- 修改范围仅为本工作包五个白名单文档。
- `docs/v1.0/`、`skills/`、三个平台 Manifest 均无变化。
- 未创建 `docs/v1.1/`、`.sdlc/`、SQLite 数据库、Schema、Script 或 Skill。
- 已执行内容边界检查、完整 Diff 审查与 `git diff --check`。

## 当前 Git 状态摘要

- 本工作包本地提交主题为 `docs(architecture): simplify storage to local sqlite`。
- Author 与 Committer 均为 `Blade <blade@breaklegsquad.com>`。
- 提交完成后 `git status --short` 为空。
- 未执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 已知限制与风险

- 当前文件仍是架构决策和 Delta Plan，不是正式 v1.1 Source of Truth，也没有 SQLite 运行证据。
- SQLite Schema、Migration、备份、恢复、具体 Projection 格式和 `ArtifactStore` 模块尚未设计或实现。
- `sdlc-project-context` 仍可能包含基于旧 Source of Truth 的 draft 内容；本工作包未修改其 Design 或 Eval Plan。
- 三端 Skill 行为兼容性继续为 `Pending first skill`。

## 下一唯一工作包

对收敛后的 SQLite-only v1.1 Delta Plan 进行独立、只读审查。

审查只判断架构与 Delta Plan 的完整性、领域兼容性、单一 Authority、逐文件影响和边界一致性，不修改文件。审查通过前不得创建 `docs/v1.1/**`，不得批准或实现 `sdlc-project-context`，不得实现 SQLite、`ArtifactStore`、Projection、迁移工具或 Skill。
