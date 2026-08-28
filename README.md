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

## Agent 开发指令

- 根目录 [`AGENTS.md`](AGENTS.md) 规定全仓工作包、领域完整性、安全、证据、Git 和并行会话边界。
- [`skills/AGENTS.md`](skills/AGENTS.md) 规定正式 Skill 的实现、资源和评测约束。
- [`docs/plugin-development/AGENTS.md`](docs/plugin-development/AGENTS.md) 规定工作包、模板、兼容性和 Handoff 的维护约束。
- 根目录 `CLAUDE.md` 仅导入 `AGENTS.md`，为 Claude Code 提供同一权威指令，不维护第二份规则。

处理任意子目录前，Agent 必须读取根级和目标路径适用的全部 `AGENTS.md`。

这些 `AGENTS.md` 和根级 `CLAUDE.md` 只用于开发本 Plugin，不是安装后业务项目的运行时组件。生产运行时约束必须进入正式 `SKILL.md` 或经过独立设计的平台组件。

## Skill 运行边界

后续正式 Skill 默认只允许显式调用，并从调用开始到完成、停止或交还控制权期间进入 exclusive execution mode。未经用户在当前请求中明确点名并授权，不调用其他 Plugin 或 Skill，包括本 Plugin 的兄弟 Skill；授权不自动覆盖传递依赖。

这是需要实际评测的行为契约，不是不可绕过的硬安全隔离。Cursor、Claude Code 和 Codex 的显式调用配置将在首个正式 Skill 的后续实现与适配阶段分别创建和验证。

## 当前状态

当前版本：`0.1.0`

已完成跨 Agent Plugin 工程初始化和 Skill 开发流程初始化，尚无正式 Skill。Skill Discovery、显式调用和行为兼容性将在首个真实 Skill 创建后分别验证。

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
