# Plugin Development Handoff

## 当前目标

把 `docs/v1.0/` 中已经稳定的软件研发与变更交付规范，逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 执行支持能力。

## 当前阶段

Skill 开发工作流初始化完成，尚未创建正式 Skill。

## 已完成内容

- 建立 `.cursor-plugin/plugin.json`。
- 建立 `.claude-plugin/plugin.json`。
- 建立 `.codex-plugin/plugin.json`。
- 三个 Manifest 指向同一根级 `skills/`。
- 建立插件开发标准和兼容矩阵。
- 建立透明的 Skill 分阶段开发流程。
- 建立 Skill Design Contract 模板。
- 建立 Skill Eval Plan 模板。
- 建立只启动 `design` 阶段的新会话快捷入口。
- 尚未创建正式或占位 Skill。

## 当前目录结构

```text
.
├── .cursor-plugin/
│   └── plugin.json
├── .claude-plugin/
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
├── skills/
│   └── README.md
├── docs/
│   ├── v1.0/
│   └── plugin-development/
│       ├── DEVELOPMENT.md
│       ├── SKILL-DEVELOPMENT-WORKFLOW.md
│       ├── COMPATIBILITY.md
│       ├── HANDOFF.md
│       ├── templates/
│       │   ├── SKILL-DESIGN-CONTRACT.md
│       │   └── SKILL-EVAL-PLAN.md
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

## 当前验证结果

- 三个原生 Manifest 已在初始化阶段完成静态检查。
- Skill 开发流程、Design Contract、Eval Plan 和设计会话入口已经建立。
- 当前没有任何 `SKILL.md`，因此三端 Skill Discovery、显式调用和行为验证仍为 `Pending first skill`。
- 本阶段只建立开发支持文档，不改变兼容性矩阵结论。

## 当前 Git 状态摘要

- 插件初始化检查点：`e724a94`。
- 本阶段新增和修改的 Skill 开发流程文件尚待人工检查与提交。
- 精确状态以 `git status --short` 为准。

## 已知风险

- 模板本身不能证明后续 Skill 设计正确，首个真实工作包仍需人工审查。
- Creator 工具可能引入平台偏好或扩大范围，必须受 Design Contract 约束。
- 三端对 Skill Front Matter、发现和自动触发的差异尚未通过真实 Skill 验证。
- 过早创建 Skill Authoring 元 Skill 会固化未经实际验证的步骤。

## 下一次唯一工作包

C1 — 确认第一个正式 Skill 的目标，只完成该 Skill 的 `DESIGN.md` 和 `EVAL-PLAN.md`，不创建 `SKILL.md`。

## 下一次明确不处理

- 不实现正式 Skill。
- 不创建 Script、Reference、Asset 或 Eval Result。
- 不修改三个平台 Manifest。
- 不进行平台安装、适配或兼容性验证。
- 不创建 Skill Authoring 元 Skill。
- 不执行 Marketplace、发布、Git commit、Git push 或其他外部写入。
