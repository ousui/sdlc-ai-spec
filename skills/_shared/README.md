# Shared Skill Runtime

本目录保存多个正式 Skill 共同遵守的安装后运行合约与 Schema。

```text
skills/_shared/
├── contracts/
│   ├── registry.json
│   ├── skill-execution.md
│   ├── skill-interface.md
│   ├── artifact-runtime.md
│   └── phase-runtime.md
└── schemas/
    ├── skill-interface.schema.json
    ├── skill-command.schema.json
    ├── invocation.schema.json
    ├── result.schema.json
    └── source-lock.schema.json
```

- 本目录不得包含 `SKILL.md`，不能作为可调用 Skill；
- `registry.json` 是共享 Runtime Contract ID / Version 的唯一登记表；
- `skill-interface.md` 统一裸调用、命令、参数别名、默认推断、决策权、写入和用户输出；
- 正式 Skill 必须提供私有 `references/interface.json`，并使用共享参数解析器；
- 正式 Skill 可以读取本目录，但不得读取兄弟业务 Skill 私有目录；
- 设计期规范只用于设计、构建和审查，不是运行时依赖；
- 构建期使用 `packages/sdlc_runtime` 生成并验证 Skill 私有 `source-lock.json`。
