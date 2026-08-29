# Plugin Development Handoff

## 当前目标

把 `docs/v1.0/` 中已经稳定的软件研发与变更交付规范，逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 执行支持能力；后续变化通过新的 Spec Snapshot 演进，不原地修改已冻结的 v1.0。

## 当前阶段

v1.1 Spec Delta Planning 已完成。`docs/architecture/v1.1-spec-delta-plan.md` 已把 Artifact Store、Projection、Runtime Workspace 与 Retention 架构输入映射到每一份 v1.0 正式 Spec，并给出 v1.1 的版本边界、生成顺序和静态验证计划。

该 Delta Plan 不是正式 Spec，不进入任何 Artifact 的 `Evaluation Contract Set`。当前尚未创建 `docs/v1.1/`；必须先完成独立、只读架构审查，审查通过并获得新的创建授权后，才能进入 v1.1 Spec 编制。

候选 Skill `sdlc-project-context` 的 Design Status 继续为 `draft`，阻塞 Open Item 不变：Artifact Store Contract、Projection Contract 尚未进入正式 v1.1 Source of Truth。在 v1.1 Spec Snapshot 完成前不得批准或实现该 Skill。

## 已完成内容

- 建立 `.cursor-plugin/plugin.json`、`.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`，三个 Manifest 指向同一根级 `skills/`。
- 建立 Plugin 开发标准、兼容矩阵、Skill 分阶段开发流程、Design / Eval 模板和只启动 `design` 的会话入口。
- 建立根级、`skills/` 与 `docs/plugin-development/` 三级 Agent 开发约束；这些约束不是安装后运行时组件。
- 建立 Exclusive Skill Execution Contract 与 Explicit Invocation First 设计规则。
- 固定 `blade-cdn/sdlc-ai-spec` 为唯一权威远程仓库，旧 `ousui/sdlc-ai-spec` 仅作为历史记录。
- 建立 `sdlc-project-context` Design Contract 与未执行的 Eval Plan；尚未创建正式或占位 Skill。
- 完成 Artifact Store、Provider、Resolver、Projection、Runtime Workspace、Retention、Reference、Canonical Serialization 与 v1.1 Compatibility 的架构决策。
- 完成 `docs/v1.0/` 全量耦合搜索，逐项区分 Artifact 物理布局与产品 Resource、业务路径、Evidence、Spec / Authority Reference 等保留语义。
- 完成覆盖 24 份 v1.0 正式 Spec、16 份 DSN Domain、新增 Store / Projection Spec 和 4 份非 Contract 文档的文件影响矩阵。
- 决定 v1.1 沿用三个现有 `/v1` Contract ID；任何领域字段、Reference 结构或 Artifact 内容语义变化都触发停止，不在 v1.1 内静默升级。
- 决定 `artifact-store-spec.md` 是所有 v1.1 Canonical Artifact 的正式 Contract；`artifact-projection-spec.md` 是正式 Projection Contract，但默认不进入 Canonical Artifact 的 `Evaluation Contract Set`。
- 决定 v1.1 继续使用完整 Markdown / YAML Canonical Blob 和原生成员；SQLite、MCP/API、Provider Profile 与具体物理路径不进入正式领域 Spec。
- 删除重复且非权威的 `docs/GUIDE.md`；其中内容未复制到其他文件，开发规则继续以适用的 `AGENTS.md`、`DEVELOPMENT.md`、`SKILL-DEVELOPMENT-WORKFLOW.md` 和本 Handoff 为准。

架构决定和 Delta Mapping 的详细来源分别是：

- `docs/architecture/artifact-store-and-projection.md`
- `docs/architecture/v1.1-spec-delta-plan.md`

本 Handoff 只保存当前状态和唯一下一工作包，不复制完整架构或 Delta Contract。

## 当前目录结构

```text
.
├── AGENTS.md
├── CLAUDE.md
├── .cursor-plugin/
│   └── plugin.json
├── .claude-plugin/
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
├── skills/
│   ├── AGENTS.md
│   └── README.md
├── docs/
│   ├── architecture/
│   │   ├── artifact-store-and-projection.md
│   │   └── v1.1-spec-delta-plan.md
│   ├── v1.0/
│   └── plugin-development/
│       ├── AGENTS.md
│       ├── DEVELOPMENT.md
│       ├── SKILL-DEVELOPMENT-WORKFLOW.md
│       ├── COMPATIBILITY.md
│       ├── HANDOFF.md
│       ├── templates/
│       ├── prompts/
│       └── work-items/
│           └── sdlc-project-context/
│               ├── DESIGN.md
│               └── EVAL-PLAN.md
├── README.md
└── CHANGELOG.md
```

`docs/v1.1/` 当前不存在。

## 已确定决策

1. 使用一个共享 `skills/` 权威源码目录和三个薄原生 Manifest。
2. 每个 Skill 按 `design → implement → evaluate → adapt → review` 分会话推进；阶段不得自动跨越。
3. 根级和路径级 `AGENTS.md` 是开发行为约束，不是领域 Contract 或安装后运行时组件。
4. 同一个 Skill 的同一阶段只允许一个写入 Owner；`HANDOFF.md` 保持单写者。
5. 新提交使用 `Blade <blade@breaklegsquad.com>` 作为 Author 和 Committer。
6. 正式 Skill 使用 Exclusive Skill Execution Contract，并默认 Explicit Invocation First。
7. 唯一权威远程仓库为 `blade-cdn/sdlc-ai-spec`；旧仓库不得用于当前版本判断或后续写入。
8. v1.0 保持冻结；Store / Resolver 架构只能通过新的 v1.1 Snapshot 落地。
9. v1.1 每份正式 Spec 的 Front Matter `version` 使用 `"1.1"`；无正文规则变化的文件归类为 `reference-update-only`。
10. `sdlc-ai-spec/artifact/v1`、`sdlc-ai-spec/project-context/v1` 与 `sdlc-ai-spec/final-confirmation-authority/v1` 继续使用；发现必须改变其字段或语义时停止 v1.1。
11. Canonical Store Binding 不进入 Artifact / CTX 字段；一个 Workspace 同时只有一个 Canonical Store Authority。
12. `sdlc-project-context` 在 v1.1 Source of Truth 完成前保持 `draft`，不得批准或进入 `implement`。
13. Creator 工具只能依据已确认 Design Contract 辅助实现或评测，不能决定领域范围。

## 当前验证结果

- 工作包开始基线为 `main@a8052f23ad9f5fa810d0533595f96a87830e9aa1`，相对指定基线 `c07130d5392fd1cf34fb07209c7f1ebe66cc1178` 恰好多 1 个提交。
- 工作包开始时 `git status --short` 为空；不存在需避让的 staged、unstaged 或 untracked 用户修改。
- Origin Fetch / Push 指向 `git@github.com:blade-cdn/sdlc-ai-spec.git`；本机 SSH Alias 最终解析到 `github.com`，未路由到旧仓库。
- 已逐份读取 24 份正式 v1.0 Spec、README、overview、协作建议与 `SHA256SUMS`，并完成 16 个指定 Concept 的大小写不敏感固定字符串搜索。
- `docs/v1.0/SHA256SUMS` 校验通过；本工作包未修改 `docs/v1.0/`、`skills/` 或三个平台 Manifest。
- Delta Plan 覆盖版本边界、Contract ID、每文件影响矩阵、新 Spec 职责、Core / Phase / Domain 变化、Binding / Locator、Provider 能力分层、Canonical Serialization、Projection、Retention、v1.0 Migration、生成顺序和静态验证。
- 未创建 `docs/v1.1/`、SQLite、MCP/API、Provider、Resolver、Projection、Script、Skill 或实际 `.sdlc/` Workspace。
- 已执行工作包白名单检查、`git diff --check` 和完整 Diff 审查。

## 当前 Git 状态摘要

- 本工作包的本地提交主题为 `docs(spec): plan v1.1 storage abstraction changes`，Author 与 Committer 均为 `Blade <blade@breaklegsquad.com>`。
- 提交只包含 `docs/architecture/v1.1-spec-delta-plan.md`、`docs/plugin-development/HANDOFF.md` 和删除 `docs/GUIDE.md`。
- 提交完成后 `git status --short` 为空。
- 未执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 已知限制与风险

- Delta Plan 仍是架构规划，不是正式 v1.1 Source of Truth，也没有运行时实现证据。
- `artifact-store-spec.md` 是否进入全部 Canonical Artifact Contract Set、Projection Spec 的独立合规边界和三个 `/v1` Contract ID 的兼容结论仍需独立审查。
- Locator、Authority Generation、Promote、Retention 与迁移失败关闭规则尚未通过正式 Spec 编制和交叉引用验证。
- SQLite、filesystem、Git、temp 与 remote Provider 均未实现，也没有事务、Promote、Retention 或 Resolver 运行证据。
- `sdlc-project-context` Design 中既有固定 Persistence 与路径正文尚未重写；本轮只维持 `draft` 和阻塞 Open Item，待正式 v1.1 Source of Truth 建立后由独立工作包校正。
- 三端对 Skill Front Matter、发现、显式调用和行为的差异仍为 `Pending first skill`。

## 下一次唯一工作包

对 `docs/architecture/v1.1-spec-delta-plan.md` 进行独立、只读架构审查，重点确认完整性、跨 Spec 一致性、Contract ID 兼容、单一 Authority、Projection 无越权、Provider 实现未泄漏和生成 / 验证顺序可执行。

Review 未通过前不得创建 `docs/v1.1/**`，不得批准或实现 `sdlc-project-context`，不得实现 Provider、Resolver、Projection、SQLite、MCP/API 或迁移工具。

## 下一次明确不处理

- 不修改 `docs/v1.0/`。
- 不创建或修改 `docs/v1.1/**`。
- 不批准、修改或实现 `sdlc-project-context`。
- 不创建 Skill、Script、SQLite Schema、MCP/API、Provider 或实际 `.sdlc/` Workspace。
- 不修改三个平台 Manifest。
- 不执行数据迁移、平台适配、Eval 或兼容性运行验证。
- 不自动进入 Spec 编制、Skill 或实现阶段。
- 不执行 push、tag、PR、Release、Marketplace 或其他未经新工作包授权的外部写入。
