# Plugin Development Handoff

## 当前目标

把 `docs/v1.0/` 中稳定的研发与变更交付规范逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。v1.0 保持冻结，后续 Store 语义只通过新的 Spec Snapshot 演进。

## 当前阶段

SQLite-only Delta Plan 独立审查结果为 `PASS WITH REQUIRED CHANGES`。唯一必修问题 `SQLITE-DELTA-001` 已按完整 Canonical Revision Payload 修正，当前等待定向、独立、只读验证。

当前架构固定：

- 当前 Plugin 只支持项目根目录下的 `.sdlc/store.sqlite3`；
- Local SQLite Store 是当前唯一 Canonical Artifact Store，其 Authority 对象是包含主要 Canonical Blob、全部本地 Member 及 Manifest-Member closure 的完整 Canonical Revision Payload；
- v1.1 只计划新增 `artifact-store-spec.md`；
- Human Review View 是 Plugin Projection，不包含完整 Member 闭包，也不是正式领域 Artifact 或 Authority；
- 当前未创建 `docs/v1.1/`，也未实现 SQLite、Projection 或 Skill。

候选 Skill `sdlc-project-context` 的 Design Status 继续为 `draft`。在 SQLite-only v1.1 Source of Truth 完成前不得批准或实现。

## 本工作包已完成

- 记录 SQLite-only Delta Plan 独立审查结论为 `PASS WITH REQUIRED CHANGES`。
- 在架构文档和 Delta Plan 中关闭 `SQLITE-DELTA-001`：Store 层最小 `read revision`、`write open revision`、`freeze revision` 与 `verify digest` 现在都覆盖主要 Canonical Blob、全部本地 Member、稳定 Member 身份、原始字节 SHA-256 和 Manifest-Member closure。
- 明确 DSN Domain Member 与本地 Supporting Member 必须保留原始字节、稳定身份和摘要；外部不可变 Reference 继续保留既有准确 Reference、摘要与访问边界，不要求复制进 SQLite。
- 保持 SQLite-only、25 份正式 Spec、29 个总文件和不新增 Projection Spec 的既有边界。
- `DOC-FRESHNESS-001` 已修正；用户确认当前工作包输入基线 `main@07441bcab98bba4b8436e0f3e2eb001e639006d2` 已 push，开始时本地 `HEAD` 与 `origin/main` 一致。
- `sdlc-project-context` 继续保持 `draft`，未批准、未实现任何 Skill。

## 已确定决策

- 一个项目只有一个本地 Canonical Store，固定为 `<project-root>/.sdlc/store.sqlite3`。
- 不增加 Store 或 Provider 配置文件，不建设多 Provider 框架。
- Canonical Authority 是 SQLite 中保存的完整 Canonical Revision Payload；Review、临时和导出文件不具有 Authority。
- Canonical Revision Payload 是 Store 层逻辑存储单元，不新增 Artifact 字段、Reference 类型、Status、Gate、Manifest 字段、数据库表或领域 Artifact。
- Payload 保持完整主要 Markdown/YAML Blob、全部本地 Member 原始字节、稳定 Member 身份、既有元数据、逐 Member SHA-256 与现有 Manifest 闭包。
- 外部不可变 Reference 不是本地 Member 原始字节，但其准确 Reference、摘要和访问边界必须保留。
- v1.1 的 `artifact-store-spec.md` 只定义最小逻辑 Store Contract，不定义 SQLite Schema。
- Human Review View 的格式、映射 Schema 与编辑器适配留到 Skill 实现阶段。
- v1.0 的 Artifact Contract ID、字段、ID、Revision、Reference、Status、Gate 与 Final Confirmation 保持不变。

## 当前验证结果

- 工作包输入基线为 `main@07441bcab98bba4b8436e0f3e2eb001e639006d2`，开始时 `git status --short` 为空，本地 `HEAD...origin/main` 为 `0 0`。
- `git remote -v` 显示 Origin Fetch / Push URL 为 `git@github-goedge-blade:blade-cdn/sdlc-ai-spec.git`；本工作包未重新验证 Alias 路由，也未执行远程操作。
- 修改范围仅为本工作包四个白名单文档。
- `docs/v1.0/`、`skills/`、三个平台 Manifest 均无变化。
- 未创建 `docs/v1.1/`、`.sdlc/`、SQLite 数据库、Schema、Script 或 Skill；未新增 Store 操作或额外摘要概念。
- 已执行闭包语义检查、完整 Diff 审查与 `git diff --check`。

## 当前 Git 状态摘要

- 本工作包本地提交主题为 `docs(architecture): complete canonical revision payload`。
- Author 与 Committer 均为 `Blade <blade@breaklegsquad.com>`。
- 提交完成后 `git status --short` 为空。
- 未执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 已知限制与风险

- 当前文件仍是架构决策和 Delta Plan，不是正式 v1.1 Source of Truth，也没有 SQLite 运行证据。
- `SQLITE-DELTA-001` 修正尚待一次定向、独立、只读验证；验证通过前不得创建 `docs/v1.1/`。
- SQLite Schema、Migration、备份、恢复、具体 Projection 格式和 `ArtifactStore` 模块尚未设计或实现。
- `sdlc-project-context` 仍可能包含基于旧 Source of Truth 的 draft 内容；本工作包未修改其 Design 或 Eval Plan。
- 三端 Skill 行为兼容性继续为 `Pending first skill`。

## 下一唯一工作包

对 `SQLITE-DELTA-001` 的修正进行一次定向、独立、只读验证；验证只检查完整 Revision Payload / Member 闭包是否已准确关闭。

验证不修改文件。通过后才允许创建 `docs/v1.1/**`；通过前不得批准或实现 `sdlc-project-context`，不得实现 SQLite、`ArtifactStore`、Projection、迁移工具或 Skill。
