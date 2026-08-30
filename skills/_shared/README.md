# Shared Skill Runtime Contracts

本目录保存多个正式 Phase Skill 安装后共同遵守的 Runtime Contract。

```text
_shared/
├── contracts/
│   ├── skill-execution.md
│   ├── artifact-runtime.md
│   └── phase-runtime.md
└── schemas/
    ├── invocation.schema.json
    └── result.schema.json
```

规则：

- 不创建 `SKILL.md`；
- 不是可调用 Skill；
- 不读取 `docs/**`；
- 不包含某个阶段的业务字段；
- 正式 Skill 可以直接加载这些共享 Contract；
- 业务 Skill 不得读取兄弟 Skill 的私有目录；
- Shared Contract 变化必须检查所有正式 Skill 和 Eval。
