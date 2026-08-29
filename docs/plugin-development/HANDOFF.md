# Plugin Development Handoff

## 当前目标

把 `docs/v1.0/` 中已经稳定的软件研发与变更交付规范，逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 执行支持能力；后续变化通过新的 Spec Snapshot 演进，不原地修改已冻结的 v1.0。

## 当前阶段

Artifact Store、Projection、Runtime Workspace 与 Retention 架构决策已完成并记录在 `docs/architecture/artifact-store-and-projection.md`。该文档是后续 v1.1 Spec 的架构输入，不是正式领域 Spec，也没有实现任何 Provider。

候选 Skill `sdlc-project-context` 的 Design Status 已从 `ready` 回退为 `draft`，存在一个阻塞 Open Item：Artifact Store Contract、Projection Contract 尚未进入正式 v1.1 Source of Truth，当前 Persistence 与路径假设不能批准。在 `docs/v1.1/` Spec Snapshot 完成前不得批准或实现该 Skill。

## 已完成内容

- 建立 `.cursor-plugin/plugin.json`、`.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`，三个 Manifest 指向同一根级 `skills/`。
- 建立 Plugin 开发标准、兼容矩阵、Skill 分阶段开发流程、Design/Eval 模板和只启动 `design` 的会话入口。
- 建立根级、`skills/` 与 `docs/plugin-development/` 三级 Agent 开发约束；这些约束不是安装后运行时组件。
- 建立 Exclusive Skill Execution Contract 与 Explicit Invocation First 设计规则。
- 固定 `blade-cdn/sdlc-ai-spec` 为唯一权威远程仓库，旧 `ousui/sdlc-ai-spec` 仅作为历史记录。
- 建立 `sdlc-project-context` Design Contract 与未执行的 Eval Plan；尚未创建正式或占位 Skill。
- 完成 Artifact Store、Provider、Resolver、Projection、Runtime Workspace、Retention、Reference、Canonical Serialization 与 v1.1 Compatibility 的架构决策。
- 明确 Artifact 是逻辑领域对象、一个 Workspace 同时只有一个 Canonical Store Authority、VCS 仅是可选 Provider、`.sdlc/` 不天然等于 Canonical Store。
- 明确本地默认实现推荐 SQLite，但领域 Spec 不绑定 SQLite；原 `artifacts/**` 布局在 v1.1 降为 filesystem Provider Profile。
- 明确 Canonical Artifact 与 Human Review Projection 分离；Review View 可编辑，但编辑、保存或评审完成不等于 Approval，也不得被下游消费为 Authority。
- 明确 v1.1 继续使用完整 Markdown/YAML Canonical Blob 和派生索引；完全 Schema-first 模型留作未来 v2.0 候选。

架构决定的唯一详细来源是：

`docs/architecture/artifact-store-and-projection.md`

本 Handoff 只保存当前状态和下一工作包，不复制完整架构 Contract。

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
│   │   └── artifact-store-and-projection.md
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

## 已确定决策

1. 使用一个共享 `skills/` 权威源码目录和三个薄原生 Manifest。
2. 每个 Skill 按 `design → implement → evaluate → adapt → review` 分会话推进；阶段不得自动跨越。
3. Creator 工具只能依据已确认 Design Contract 辅助实现或评测，不能决定领域范围。
4. 根级和路径级 `AGENTS.md` 是开发行为约束，不是领域 Contract 或安装后运行时组件。
5. 同一个 Skill 的同一阶段只允许一个写入 Owner；`HANDOFF.md` 保持单写者。
6. 新提交使用 `Blade <blade@breaklegsquad.com>` 作为 Author 和 Committer。
7. 正式 Skill 使用 Exclusive Skill Execution Contract，并默认 Explicit Invocation First。
8. 唯一权威远程仓库为 `blade-cdn/sdlc-ai-spec`；旧仓库不得用于当前版本判断或后续写入。
9. Artifact Store、Projection 与 Retention 的详细决定只以 `docs/architecture/artifact-store-and-projection.md` 为准。
10. v1.0 保持冻结；Store/Resolver 架构通过 `docs/v1.1/` 新 Snapshot 落地。
11. `sdlc-project-context` 在 v1.1 Source of Truth 完成前保持 `draft`，不得批准或进入 `implement`。

## 当前验证结果

- 架构文档覆盖 Layer Model、Provider Contract、五类 Provider Profile、Reference/Locator、Canonical Serialization、Projection、Runtime Workspace、三档 Retention、v1.1 Compatibility 与当前 Skill 影响。
- `sdlc-project-context` Design Status 为 `draft`，存在一个明确阻塞 Open Item，Maintainer Decision 仍为 `pending`。
- `docs/v1.0/` 无变化；`skills/` 无变化；三个平台 Manifest 无变化。
- 未创建 SQLite、MCP、Provider、Script、Skill 或实际 `.sdlc/` Workspace。
- 未执行 Eval、Fixture、平台安装、Discovery、Invocation 或兼容性运行验证。
- 本工作包完成前执行 `git diff --check`、白名单检查与完整 Diff 审查。

## 当前 Git 状态摘要

- 本工作包开始基线：`main@edcae81c809e2594c955dcb7b88700c5338eba0e`。
- 架构工作包使用本地提交 `docs(architecture): 定义 Artifact Store 抽象`，并关联当前 Codex session；未 push。
- 提交后 `git status --short` 只保留工作包开始前已经存在的 `?? docs/GUIDE.md`；该文件未修改、未暂存、未提交。
- 精确分支、HEAD 和工作树状态仍以当前会话执行的 Git 命令为准。

## 已知限制与风险

- 架构决定尚未成为正式 v1.1 Domain Spec，不能加入 Artifact `Evaluation Contract Set`。
- SQLite、filesystem、git、temp 与 remote Provider 均未实现，也没有事务、Promote、Retention 或 Resolver 运行证据。
- `sdlc-project-context` Design 中既有固定 Persistence 与路径正文尚未重写；本轮只用 `draft` 和阻塞 Open Item 明确其不可批准，待 v1.1 后由独立工作包校正。
- Human Review Projection 的具体格式、hidden mapping serialization、SQLite Schema 与 MCP/API Protocol 仍应由后续实现工作包依据 v1.1 设计，不得提前固化。
- 三端对 Skill Front Matter、发现、显式调用和行为的差异仍为 `Pending first skill`。
- `docs/GUIDE.md` 是本工作包之外的用户既有未跟踪文件；后续会话仍需保留并避免误提交。

## 下一次唯一工作包

根据已批准的 Artifact Store Architecture 创建 `docs/v1.1/` Spec Snapshot；在 v1.1 完成前不批准或实现 `sdlc-project-context`。

## 下一次明确不处理

- 不修改 `docs/v1.0/`。
- 不批准或实现 `sdlc-project-context`。
- 不创建 Skill、Script、SQLite Schema、MCP/API、Provider 或实际 `.sdlc/` Workspace。
- 不修改三个平台 Manifest。
- 不执行 Provider 实现、数据迁移、平台适配、Eval 或兼容性运行验证。
- 不自动进入任何后续 Skill 阶段。
- 不执行 push、tag、PR、Release、Marketplace 或其他未经当前工作包授权的外部写入。
