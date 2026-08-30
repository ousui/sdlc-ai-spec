# Shared Phase Runtime Contract

## Runtime Package

正式 Phase Skill 建议结构：

```text
skills/sdlc-NNN-xxx/
├── SKILL.md
├── references/
│   ├── contract.md
│   └── source-lock.json
├── assets/
│   └── <phase-template>
├── scripts/
│   └── runtime.py
├── agents/
└── evals/
```

`SKILL.md` 保存核心 SOP；详细阶段规则保持单层 Reference；确定性编排放在
`runtime.py`。

## Standard Request

请求必须符合：

```text
skills/_shared/schemas/invocation.schema.json
```

阶段变量只放入 `inputs`。

## Standard Result

结果必须符合：

```text
skills/_shared/schemas/result.schema.json
```

错误必须提供稳定 `code` 和可读 `message`。

## Responsibility

Agent：

- 识别意图；
- 收集候选事实；
- 解释 Open Item 和下一动作。

Phase Runtime：

- 校验参数；
- 构造 Payload；
- 执行 Domain Validator；
- 编排共享 Package；
- 输出结构化结果。

Shared Package：

- 事务、ID、Revision、摘要和持久化。

## Source Lock

`source-lock.json` 保存：

- runtime contract version；
- source spec version；
- Contract ID；
- SHA-256；
- build timestamp / commit（按需）。

不得保存运行时必须读取的 `docs/**` 路径。

## Independence

Review 前必须在删除 `docs/**` 的临时 Plugin 中执行 Critical Fixture。
