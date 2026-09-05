# Shared Skills Source

本目录是 Cursor、Claude Code 和 Codex 共用的唯一 Skill Runtime 源码目录。

正式 Phase Skill 命名：

```text
sdlc-000-ctx
sdlc-100-req
sdlc-200-dsn
sdlc-300-pln
sdlc-400-imp
sdlc-500-vfy
sdlc-600-rls
```

跨生命周期 Utility 不占用 Phase 编号。项目状态查询预留名称为：

```text
sdlc-status
```

Plugin Namespace 会将其与开发辅助插件的 `$devsdlc:devsdlc-status` 区分。

每个正式 Skill 使用：

```text
skills/<skill-name>/
├── SKILL.md
├── scripts/
├── references/
│   ├── interface.json
│   ├── contract.md
│   └── source-lock.json
├── assets/
├── agents/
└── evals/                     可选开发资源；正式评测可位于 tests/**
```

## 统一调用

推荐：

```text
/<skill> [command] [options] [-- free-form request]
```

裸调用默认 `operation=auto`。全部 Skill 统一支持：

```text
-h --help
-V --version
--commands
--examples
-o --operation
-p --project-root
-r --reference
-d --decision-policy
-w --write-policy
-n --dry-run
-f --output
```

共享运行规则位于 `skills/_shared/`；该目录没有 `SKILL.md`，不是可调用 Skill。正式 Runtime 不读取 `docs/**`。业务 Skill 不依赖兄弟业务 Skill，但可以使用 `skills/_shared/**` 与 `packages/**`。

## Eval 布局与执行证据边界

开发期固定案例、Oracle 和 Fixture 可集中位于 `tests/evals/**`、`tests/skill_*/**`、`tests/skills/**`，结果与 Handoff 位于对应 Work Item。不存在 `skills/<name>/evals/` 不表示缺少评测；不创建空占位目录。安装后的 Runtime 不依赖开发评测、`docs/**` 或仓库 Agent 指令。

目录、静态元数据、普通 Python 回归和 installed-copy 执行是不同层次的证据，均不能代替真实 Client 的 Discovery / Invocation / Behavior。当前阶段与历史报告的适用范围见 `docs/plugin-development/HANDOFF.md` 和逐 Skill 的 `COMPATIBILITY.json`；这些文件仅供开发期使用。
