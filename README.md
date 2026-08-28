# sdlc-ai-spec

`sdlc-ai-spec` 定义软件研发与变更交付过程中统一的 Artifact、Reference、Evidence、Exception、Check 和 Gate，并逐步提供对应的跨 Agent Plugin 执行支持。

## Spec 与 Plugin

- `docs/v1.0/` 是当前稳定的领域规范。
- Plugin 用于辅助形成、检查和使用标准 Artifact。
- Plugin 不得改变领域规范的字段、语义或 Gate。
- 规范不要求必须使用 AI；人工、AI 或其他执行主体使用同一完成标准。

## 目标 Agent

项目当前为三个宿主维护原生 Plugin 入口：

| Agent | Manifest |
|---|---|
| Cursor | `.cursor-plugin/plugin.json` |
| Claude Code | `.claude-plugin/plugin.json` |
| Codex | `.codex-plugin/plugin.json` |

三端共同使用根目录下唯一的 `skills/` 源码目录。

## 当前状态

当前版本：`0.1.0`

已完成跨 Agent Plugin 工程初始化，尚无正式 Skill。Skill Discovery、显式调用和行为兼容性将在首个真实 Skill 创建后分别验证。

## 文档入口

- [v1.0 规范索引](docs/v1.0/README.md)
- [Plugin 开发标准](docs/plugin-development/DEVELOPMENT.md)
- [兼容性矩阵](docs/plugin-development/COMPATIBILITY.md)
- [开发交接](docs/plugin-development/HANDOFF.md)
- [Skill 开发流程](docs/plugin-development/SKILL-DEVELOPMENT-WORKFLOW.md)
- [Skill Design Contract 模板](docs/plugin-development/templates/SKILL-DESIGN-CONTRACT.md)
- [Skill Eval Plan 模板](docs/plugin-development/templates/SKILL-EVAL-PLAN.md)
- [开始 Skill 设计会话](docs/plugin-development/prompts/START-SKILL-DESIGN-SESSION.md)
- [共享 Skills 目录说明](skills/README.md)
