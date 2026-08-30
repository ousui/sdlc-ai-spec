# Skills Runtime

本目录是正式 Skill 与共享运行合约的唯一源码目录。

```text
skills/
├── _shared/
│   ├── contracts/
│   └── schemas/
└── sdlc-NNN-xxx/
    ├── SKILL.md
    ├── agents/
    ├── references/
    ├── assets/
    ├── scripts/
    └── evals/
```

## Shared Runtime

`_shared/` 保存多个正式 Skill 安装后共同遵守的 Contract 和 JSON Schema。

- `_shared/` 不包含 `SKILL.md`；
- 它不是可调用 Skill；
- 正式 Skill 可以读取 `_shared/`；
- 业务 Skill 不得读取其他业务 Skill 的私有目录。

## Phase Names

```text
sdlc-000-ctx
sdlc-100-req
sdlc-200-dsn
sdlc-300-pln
sdlc-400-imp
sdlc-500-vfy
sdlc-600-rls
```

目录名和 Front Matter `name` 使用英文；`description` 与正文默认使用中文。

## Runtime Independence

正式 Skill 运行时不读取 `docs/**`。设计来源通过 `source-lock.json`
固化为版本和摘要；真正执行所需规则必须存在于 Skill Runtime 或共享组件中。
