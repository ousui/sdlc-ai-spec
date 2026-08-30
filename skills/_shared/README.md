# Shared Skill Runtime

本目录保存多个正式 Skill 共同遵守的安装后运行合约与 Schema。

```text
skills/_shared/
├── contracts/
│   ├── registry.json
│   ├── skill-execution.md
│   ├── artifact-runtime.md
│   └── phase-runtime.md
└── schemas/
    ├── invocation.schema.json
    ├── result.schema.json
    └── source-lock.schema.json
```

- 本目录不得包含 `SKILL.md`，不能作为可调用 Skill；
- `registry.json` 是共享 Runtime Contract ID / Version 的唯一登记表；
- 正式 Skill 可以读取本目录，但不得读取兄弟业务 Skill 私有目录；
- `docs/v1.x/**` 只用于设计、构建和审查，不是运行时依赖；
- 构建期使用 `packages/sdlc_runtime` 生成并验证 Skill 私有 `source-lock.json`。
