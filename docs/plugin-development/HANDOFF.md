# Plugin Development Handoff

## 当前目标

把 `docs/v1.0/` 中已经稳定的软件研发与变更交付规范，逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 执行支持能力。

## 当前阶段

跨 Agent Plugin 工程初始化完成，尚未创建正式 Skill。

## 已完成内容

- 建立 `.cursor-plugin/plugin.json`。
- 建立 `.claude-plugin/plugin.json`。
- 建立 `.codex-plugin/plugin.json`。
- 三个 Manifest 指向同一根级 `skills/`。
- 建立插件开发标准。
- 建立跨 Agent 兼容矩阵。
- 建立统一跨会话交接文件。
- 建立根目录项目说明和 Changelog。

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
│       ├── COMPATIBILITY.md
│       └── HANDOFF.md
├── README.md
└── CHANGELOG.md
```

## 已确定决策

1. 使用一个共享 `skills/` 权威源码目录。
2. Cursor、Claude Code 和 Codex 分别使用自己的原生 Manifest。
3. 平台入口保持薄层，不复制 Skill 或领域语义。
4. 当前不增加根目录 Agent Plugins 开放格式 Manifest。
5. 当前不创建占位 Skill。
6. 当前不引入 MCP、Hook、Agent、Command、Marketplace、安装器或更新器。
7. Plugin Version 与领域 Spec Version 独立管理。
8. 后续每个 Skill 按 `design → implement → evaluate → adapt → review` 分会话推进。

## 当前验证结果

- 三个 Manifest 的 JSON 语法、共同元数据和 `skills` 路径可进行本地确定性检查。
- Claude Code Manifest 已有原生 Validator 通过记录，仅存在可选作者元数据提示。
- Cursor 和 Codex 尚未完成宿主加载测试。
- 当前尚无正式 Skill，因此三端 Skill Discovery、显式调用和行为验证均处于 `Pending first skill`。

## 当前 Git 状态摘要

插件初始化文件当前保持为未提交工作；精确状态以执行 `git status --short` 的结果为准。本阶段不授权自动 commit 或 push。

## 已知风险

- 三端 Manifest 能被解析，不代表共享 Skill 的发现和行为已经兼容。
- 首个正式 Skill 建立前，无法完成真实的端到端插件验证。
- 不同 Agent 对 Skill Front Matter、路径解析和自动触发行为可能存在差异，需要分别验证。
- 过早建立自动 Creator、公共脚本或平台增强会固化未经验证的流程。

## 下一次唯一工作包

建立透明的 Skill 创建流程、Skill Design Contract 模板和新会话快捷入口。

下一次只制定开发流程与模板，不创建第一个正式 Skill。

## 下一次明确不处理

- 不设计或实现第一个领域 Skill。
- 不创建 `SKILL.md`。
- 不创建 Script、MCP、Hook、Agent 或 Command。
- 不执行 Marketplace、安装、发布、commit 或 push。
