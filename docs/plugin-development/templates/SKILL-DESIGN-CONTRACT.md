# Skill Design Contract — `<sdlc-NNN-xxx>`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `<sdlc-NNN-xxx>` |
| Stage | `design` |
| Status | `draft` |
| Intended Plugin | `sdlc-ai-spec` |
| Design-time Source | `<docs/v1.x paths>` |
| Bundled Runtime Contract | `<skill references/assets/scripts>` |
| Shared Runtime Contract | `skills/_shared/**` |
| Shared Package | `<packages/... or None>` |
| Work Item | `docs/plugin-development/work-items/<skill-name>/` |

允许状态：`draft / ready / approved / superseded`。

## 2. Problem 与用户结果

### Problem

`<缺少什么稳定能力>`

### Intended User Outcome

`<可观察结果；用户不需要重新编写长提示词或理解内部协议>`

## 3. 单一职责

### In Scope

- `<唯一阶段工作流>`

### Out of Scope

- `<相邻但不负责的能力>`

## 4. Trigger Contract

### 应触发

| ID | 场景 | 示例 | Invocation |
|---|---|---|---|
| TRG-P01 | | | `explicit` |

### 不应触发

| ID | 场景 | 示例 | 应由什么处理 |
|---|---|---|---|
| TRG-N01 | | | |

## 5. Skill Interface Contract

必须绑定：

```text
skills/_shared/contracts/skill-interface.md
skills/_shared/schemas/skill-interface.schema.json
skills/_shared/schemas/skill-command.schema.json
```

### Commands

| Command | Default / Alias | Writes | User Outcome |
|---|---|---:|---|
| `auto` | default | yes/no | |
| `create` | `--create`, `--command=create`, `-c create`, `--operation=create`, `-o create` | yes | |
| `revise` | | yes | |
| `check` | | no | |
| `help / version / commands / examples` | shared | no | 预定义信息 |

### Common Parameters

| Parameter | Default | Resolution Rule | Ambiguous Behavior |
|---|---|---|---|
| `project_root` | `auto` | 唯一工作区 | 用户选择 |
| `artifact_reference` | `auto` | 唯一准确候选 | 用户选择 |
| `decision_policy` | `user` | explicit override | |
| `write_policy` | `auto` | explicit Skill standard writes | |
| `dry_run` | `false` | explicit override | |
| `output` | `summary` | explicit override | |

必须明确：

- 裸调用行为；
- 确定性默认值与推断优先级；
- 多候选、无唯一最优解时的推荐与用户决策；
- `decision_policy=model / experiment` 的显式授权边界；
- 标准项目内写入与高影响/外部写入的区别；
- `summary / json / debug`；
- 未知参数、冲突、缺值和引号错误；
- 用户无需手工构造 Evidence ID、Confirmation JSON 或 Runtime Envelope；
- `references/interface.json` 的版本和示例。

## 6. Runtime Independence Contract

必须明确：

- 运行时不读取 `docs/**`；
- Plugin 是最小部署单元；
- Skill 不依赖兄弟 Skill；
- 使用哪些 `skills/_shared/**` Contract；
- 使用哪些 `packages/**`；
- 删除 `docs/**` 后如何验证；
- `source-lock.json` 固化哪些 Contract ID、版本和 SHA-256；
- 不手工双写无法校验的 Spec 与 Runtime 内容。

## 7. Input Contract

公共 Runtime Envelope 使用 `invocation.schema.json`；用户命令先经共享 Skill Interface Parser 归一化。

| ID | Phase Input | Required | Validation | Missing Behavior |
|---|---|---:|---|---|
| IN-01 | | yes/no | | |

## 8. Output Contract

公共 Runtime Envelope 使用 `result.schema.json`；用户层默认输出简明 summary。

| ID | Phase Output | Required Content | Success Condition | Consumer |
|---|---|---|---|---|
| OUT-01 | | | | |

## 9. Workflow Contract

1. 解析 Skill 命令；
2. 解决默认参数和唯一目标；
3. 只读观察工作区并形成候选事实；
4. 仅对真实决策或高影响副作用与用户交互；
5. 构造完整 Runtime 请求；
6. 构造 Phase Payload；
7. 执行 Domain Validator；
8. 通过共享 Package 完成确定性操作；
9. 返回标准结果和人类摘要。

## 10. Shared / Private Boundary

| Resource | Decision |
|---|---|
| `SKILL.md` | |
| `references/interface.json` | |
| `references/contract.md` | |
| `references/source-lock.json` | |
| `assets/` | |
| `scripts/runtime.py` | |
| `skills/_shared/**` | |
| `packages/**` | |

## 11. Failure Contract

| Failure | Detection | Required Behavior | Forbidden Fallback |
|---|---|---|---|
| Unknown argument | shared parser | help + stable error | ignore typo |
| Multiple legal choices | resolver | recommendation + user decision | arbitrary model choice |
| | | | |

## 12. 权限与副作用

| Capability | Required | Scope | Authorization |
|---|---:|---|---|
| Read project | | | explicit invocation |
| Standard project write | | | `write_policy` |
| Execute runtime | | | explicit invocation |
| Git / external write | no | None | separate explicit authorization |
| Network | no/default | | explicit only |

## 13. Exclusive Execution

- 显式调用；
- 不调用兄弟 Skill；
- 不传递授权；
- 外部输出仅作 Input / Evidence；
- 无法独立完成时停止；
- 不是硬隔离声明。

## 14. Portability

| Concern | Portable Core | Cursor | Claude Code | Codex |
|---|---|---|---|---|
| Discovery | | | | |
| Explicit invocation | | | | |
| Argument tail | | | | |
| Path resolution | | | | |
| Behavior evidence | | | | |

## 15. Eval Plan

对应：

```text
docs/plugin-development/work-items/<skill-name>/EVAL-PLAN.md
```

必须覆盖 Skill Interface、Runtime Independence、Shared Contract 和程序化输入输出。

## 16. Design DoD

- [ ] 名称符合 `sdlc-NNN-xxx`。
- [ ] 单一职责明确。
- [ ] Design-time Source 与 Runtime Contract 分离。
- [ ] Runtime 不读取 `docs/**`。
- [ ] Shared Contract / Package 边界明确。
- [ ] `references/interface.json` 已设计。
- [ ] 裸调用、help、version、commands、examples 已设计。
- [ ] 长短参数、兼容别名和冲突规则已设计。
- [ ] 默认推断、用户决策和模型委托边界明确。
- [ ] 标准写入与高影响副作用边界明确。
- [ ] 输入输出 Envelope 明确。
- [ ] Builder / Validator / Store 边界明确。
- [ ] Runtime Independence Eval 已设计。
- [ ] 阻塞 Open Item=0。
- [ ] 未创建正式 `SKILL.md`。

## 17. Open Items

| ID | Question | Blocks | Expected Source | Status |
|---|---|---|---|---|
| None | No blocking open items | N/A | N/A | closed |

## 18. Maintainer Decision

| Role | Decision | Basis |
|---|---|---|
| Maintainer | `pending / approved / rejected` | |
