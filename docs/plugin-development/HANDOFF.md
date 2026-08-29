# Plugin Development Handoff

## 当前目标

把 `docs/v1.0/` 中已经稳定的软件研发与变更交付规范，逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 执行支持能力。

## 当前阶段

C1 `design` 已完成：候选 Skill `sdlc-project-context` 的 Design Contract 与 Eval Plan 均为 `ready`，没有阻塞 Open Item，等待 Maintainer 明确批准。尚未创建正式 Skill，也未进入 `implement`。

## 已完成内容

- 建立 `.cursor-plugin/plugin.json`。
- 建立 `.claude-plugin/plugin.json`。
- 建立 `.codex-plugin/plugin.json`。
- 三个 Manifest 指向同一根级 `skills/`。
- 建立 Plugin 开发标准和兼容矩阵。
- 建立透明的 Skill 分阶段开发流程。
- 建立 Skill Design Contract 模板。
- 建立 Skill Eval Plan 模板。
- 建立只启动 `design` 阶段的新会话快捷入口。
- 建立根级 `AGENTS.md`，约束全仓工作包、领域完整性、证据、安全、Git 和并行会话。
- 建立 `skills/AGENTS.md`，约束 Skill 实现、资源、触发和 Eval。
- 建立 `docs/plugin-development/AGENTS.md`，约束 Work Item、Template、Compatibility 和 Handoff。
- 建立根级 `CLAUDE.md`，只导入根级 `AGENTS.md`。
- 明确仓库 `AGENTS.md`、嵌套 `AGENTS.md` 和根级 `CLAUDE.md` 只用于开发，不是安装后的运行时 Plugin Component。
- 建立 Exclusive Skill Execution Contract：显式调用后保持独占执行，其他 Skill / Plugin 必须由用户在当前请求中逐项授权，授权不传递。
- 明确外部 Skill 输出只可作为 Input 或 Supporting Evidence，不得覆盖当前 Contract、Gate、权限或授权边界。
- 登记首版 Explicit Invocation First 策略：Cursor / Claude Code 使用 `disable-model-invocation: true`，Codex 使用 `policy.allow_implicit_invocation: false`。
- Design 和 Eval 模板已经加入 Interoperability Contract、独占执行案例、三端调用策略验证和实际外部 Invocation 记录要求。
- 已将 `blade-cdn/sdlc-ai-spec` 固定为唯一权威远程仓库；`ousui/sdlc-ai-spec` 仅保留为停止同步的历史仓库。
- 建立 `sdlc-project-context` Design Contract，覆盖 `create / revise / check`、CTX Identity、Revision、Context Reference、Basis、Open Items、权限和失败边界。
- 建立 `sdlc-project-context` Eval Plan，覆盖正向与负向调用、完整与缺失输入、Revision 更新、冲突边界、with-skill / without-skill、Exclusive Skill Execution 和三端显式调用策略。
- `sdlc-project-context` Design Status 为 `ready`，Maintainer Decision 保持 `pending`。
- 尚未创建正式或占位 Skill。

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
│   ├── v1.0/
│   └── plugin-development/
│       ├── AGENTS.md
│       ├── DEVELOPMENT.md
│       ├── SKILL-DEVELOPMENT-WORKFLOW.md
│       ├── COMPATIBILITY.md
│       ├── HANDOFF.md
│       ├── templates/
│       │   ├── SKILL-DESIGN-CONTRACT.md
│       │   └── SKILL-EVAL-PLAN.md
│       ├── work-items/
│       │   └── sdlc-project-context/
│       │       ├── DESIGN.md
│       │       └── EVAL-PLAN.md
│       └── prompts/
│           └── START-SKILL-DESIGN-SESSION.md
├── README.md
└── CHANGELOG.md
```

后续候选 Skill 的设计工作包统一位于：

```text
docs/plugin-development/work-items/<skill-name>/
├── DESIGN.md
└── EVAL-PLAN.md
```

## 已确定决策

1. 使用一个共享 `skills/` 权威源码目录。
2. Cursor、Claude Code 和 Codex 分别使用自己的原生 Manifest。
3. 平台入口保持薄层，不复制 Skill 或领域语义。
4. 当前不增加根目录 Agent Plugins 开放格式 Manifest。
5. 每个 Skill 按 `design → implement → evaluate → adapt → review` 分会话推进。
6. 当前快捷入口是透明的 Markdown Prompt，而不是自动化元 Skill。
7. 在至少一个真实 Skill 完成完整流程前，不创建 Skill Authoring 元 Skill。
8. Creator 工具只能依据已确认 Design Contract 辅助实现或评测，不能决定领域范围。
9. Plugin Version 与领域 Spec Version 独立管理。
10. 根级和路径级 `AGENTS.md` 是 Agent 行为约束，不是领域 Contract。
11. Claude Code 通过 `CLAUDE.md` 导入根级 `AGENTS.md`；处理子目录时仍显式读取最近的嵌套 `AGENTS.md`。
12. 同一个 Skill 的同一阶段只允许一个写入 Owner；`HANDOFF.md` 保持单写者。
13. 新提交必须使用 `Blade <blade@breaklegsquad.com>` 作为 Author 和 Committer。
14. 开发期指令文件不进入安装后运行时；生产约束必须进入正式 `SKILL.md` 或独立设计的平台组件。
15. 正式 Skill 从显式调用到完成、停止或交还控制权期间执行 Exclusive Skill Execution Contract。
16. Exclusive Skill Execution Contract 是可评测的行为契约，不是不可绕过的硬安全隔离。
17. 首版 Skill 默认显式调用；改变默认值必须有独立设计决定和实际宿主证据。
18. 唯一权威远程仓库为 `blade-cdn/sdlc-ai-spec`；旧 `ousui/sdlc-ai-spec` 不得用于后续写入、发布或当前版本判断。

## 当前验证结果

- 三个原生 Manifest 已完成静态检查。
- Skill 开发流程、Design Contract、Eval Plan 和设计会话入口已经建立。
- Agent 约束分为全仓、`skills/` 和 `docs/plugin-development/` 三个作用域。
- `sdlc-project-context` Design Contract 已覆盖 C1 要求，状态为 `ready`，Open Items 为 `None`。
- `sdlc-project-context` Eval Plan 已定义可判定案例，但尚未执行 Eval，也未创建 Fixture 或 `EVAL-RESULTS.md`。
- 当前没有任何 `SKILL.md`，因此三端 Skill Discovery、显式调用和行为验证仍为 `Pending first skill`。
- C1 只增加 Work Item 设计文档，不改变领域 Spec、Manifest 或兼容性矩阵结论。
- 本阶段没有创建 `SKILL.md` 或 `agents/openai.yaml`，也没有执行三端安装或运行时验证。

## 当前 Git 状态摘要

- Plugin scaffold 检查点：`e724a94`。
- Skill framework 检查点：`5a5bc50`。
- C1 开始基线：`2d07179443dfbf16c6bcff22380c1fd67daa9660`，分支 `main`。
- 当前 `git status --short` 显示 `docs/plugin-development/HANDOFF.md` 已修改，`docs/plugin-development/work-items/` 为未跟踪；本会话没有 commit 或 push。
- 精确分支、HEAD 和工作树状态以当前会话执行的 Git 命令为准。
- Agent 不得根据本节推断工作树始终干净。
- 权威远端：`git@github.com:blade-cdn/sdlc-ai-spec.git`。

## 已知风险

- `AGENTS.md` 属于行为指导，不是客户端强制安全机制；外部写入和权限仍需宿主配置与人工审查。
- Exclusive Skill Execution Contract 只能通过行为评测发现偏差，不能替代宿主级隔离、权限控制或安全机制。
- 模板本身不能证明后续 Skill 设计正确，首个真实工作包仍需 Maintainer 审批。
- Creator 工具可能引入平台偏好或扩大范围，必须受 Design Contract 约束。
- 三端对 Skill Front Matter、发现和自动触发的差异尚未通过真实 Skill 验证。
- `sdlc-project-context` 尚未获得 Maintainer `approved`，不得据 `ready` 自动进入实现。
- CTX 确定性工具、路径解析和三端调用策略目前只有设计边界，没有实现或运行证据。
- 过早创建 Skill Authoring 元 Skill 会固化未经实际验证的步骤。
- 并行 Codex 会话如果没有路径隔离，仍可能造成 Handoff 或共享文件冲突。

## 下一次唯一工作包

C2 — Maintainer 审查并明确批准或拒绝 `sdlc-project-context` 的 `DESIGN.md` 与 `EVAL-PLAN.md`；未写入 `approved` 前不得进入 `implement`。

## 下一次明确不处理

- 不实现正式 Skill。
- 不创建 Script、Reference、Asset 或 Eval Result。
- 不修改三个平台 Manifest。
- 不进行平台安装、适配或兼容性验证。
- 不自动进入 `implement`、`evaluate`、`adapt` 或 `review`。
- 不创建 Skill Authoring 元 Skill。
- 不执行 Marketplace、发布或未经当前工作包授权的其他外部写入。
