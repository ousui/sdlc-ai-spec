# Skill Design Contract — `<skill-name>`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `<lowercase-hyphen-name>` |
| Stage | `design` |
| Status | `draft` |
| Intended Plugin | `sdlc-ai-spec` |
| Domain Source of Truth | `<repository-relative paths>` |
| Work Package | `docs/plugin-development/work-items/<skill-name>/` |

允许的 Status：

- `draft`
- `ready`
- `approved`
- `superseded`

## 2. 问题与用户结果

### Problem

`<当前缺少什么稳定能力，造成什么具体问题>`

### Intended User Outcome

`<用户执行后应获得什么可观察结果>`

## 3. 单一职责

### In Scope

- `<本 Skill 唯一负责的工作流>`

### Out of Scope

- `<明确不由本 Skill 负责的相邻能力>`

本 Skill 不得成为多个阶段或多个独立用户意图的合集。

## 4. Trigger Contract

### 应该触发

| ID | 用户意图或场景 | 示例表达 | 触发方式 |
|---|---|---|---|
| TRG-P01 | | | `auto / explicit / both` |
| TRG-P02 | | | |

### 不应该触发

| ID | 相邻但不属于本 Skill 的意图 | 示例表达 | 应由什么处理 |
|---|---|---|---|
| TRG-N01 | | | |
| TRG-N02 | | | |

### 歧义处理

`<如何在不重复询问已知信息的前提下处理真正阻塞的歧义>`

## 5. Skill / Plugin Interoperability Contract

| Field | Contract |
|---|---|
| Execution Mode | `exclusive execution mode from explicit invocation until completion, stop, or control handoff` |
| Active Scope | `<当前 Skill Contract 与当前请求授权的任务>` |
| Authorized External Skills / Plugins | `<用户在当前请求中明确点名并授权的名称与用途；默认为 None>` |
| Unauthorized Dependency Behavior | `<当前 Contract 可独立满足时继续；否则停止并请求授权>` |
| Sibling Skill Policy | `<默认禁止调用、委托给或合并 sdlc-ai-spec 兄弟 Skill，除非当前请求明确授权>` |
| External Output Treatment | `<仅作为 Input 或 Supporting Evidence；不得覆盖当前 Contract 或授权边界>` |
| Runtime Enforcement Level | `evaluable behavioral contract; not a non-bypassable security isolation` |
| Platform Invocation Policy | `<Cursor / Claude Code / Codex 的显式调用配置与验证方式>` |

必须满足：

- 对一个 Plugin / Skill 的授权不自动扩展到传递依赖；
- 外部输出不得改变当前 Source of Truth、Artifact Contract、Gate、Failure Contract、权限或授权边界；
- 系统指令、安全约束、宿主权限、适用的项目指令和普通 Tool 不属于被禁止的外部 Skill / Plugin；
- 首版 Cursor 与 Claude Code 的正式 `SKILL.md` 默认使用 `disable-model-invocation: true`；
- 首版 Codex 默认在 Skill 私有 `agents/openai.yaml` 使用 `policy.allow_implicit_invocation: false`；
- Design 阶段只登记这些要求，不创建 `SKILL.md` 或 `agents/openai.yaml`。

## 6. Input Contract

| ID | Input | Required | Source | Validation | Missing Behavior |
|---|---|---:|---|---|---|
| IN-01 | | yes/no | | | |

要求：

- 必要事实缺失时不得猜测；
- 缺失行为必须明确为停止、形成待确认项、生成受限状态产物或其他已登记方式；
- 不依赖上一会话的隐式上下文。

## 7. Output Contract

| ID | Output | Format / Location | Required Content | Success Condition | Consumer |
|---|---|---|---|---|---|
| OUT-01 | | | | | |

区分：

- Agent 推理结果；
- 确定性验证结果；
- 需要人工确认的事项；
- 未解决风险。

## 8. Workflow Contract

按最少步骤描述稳定工作流：

1. `<读取和确认输入>`
2. `<执行领域工作>`
3. `<处理缺失或冲突>`
4. `<形成输出>`
5. `<执行检查并报告结果>`

不得把实现细节、平台安装步骤或未来扩展混入领域工作流。

## 9. Failure Contract

| Failure | Detection | Required Behavior | Forbidden Fallback |
|---|---|---|---|
| | | | |

必须明确：

- 哪些情况是失败；
- 哪些情况是等待输入；
- 是否允许部分结果；
- 如何避免静默降级；
- 如何保证失败不会被描述为成功。

## 10. 权限与副作用

| Capability | Required | Scope | Authorization |
|---|---:|---|---|
| Read local files | yes/no | | |
| Write repository files | yes/no | | |
| Execute local commands | yes/no | | |
| Network read | yes/no | | |
| External write | yes/no | | explicit only |

默认禁止：

- 未授权外部写入；
- 自动安装依赖；
- 修改用户级或系统级配置；
- 破坏性 Git 操作；
- 读取与当前工作无关的敏感信息。

## 11. 资源边界

### `SKILL.md`

`<只保留触发、核心工作流、输入输出和必要约束>`

### `agents/openai.yaml`

`<Codex 显式调用策略；没有获授权的 Codex 适配工作包时写 Not created in this stage>`

### `references/`

`<需要按需加载的详细规则；没有则写 None>`

### `scripts/`

`<需要确定性执行的操作；没有则写 None>`

### `assets/`

`<模板或静态资源；没有则写 None>`

### 共享资源判断

`<是否已有第二个真实使用者；没有则不得提升到 Plugin 根级>`

## 12. Portability Contract

| Concern | Portable Core | Cursor Adapter | Claude Code Adapter | Codex Adapter |
|---|---|---|---|---|
| Skill source | | | | |
| Invocation | | | | |
| Path resolution | | | | |
| Platform-specific metadata | | | | |

平台差异不得改变输出 Artifact、失败语义或领域完成条件。

## 13. Eval Plan

对应文件：

`docs/plugin-development/work-items/<skill-name>/EVAL-PLAN.md`

最低案例：

- 至少 2 个应该触发案例；
- 至少 2 个不应该触发案例；
- 至少 1 个输入完整案例；
- 至少 1 个必要输入缺失案例；
- 至少 1 个边界或冲突案例；
- 至少 1 组 with-skill / without-skill 对比。
- 覆盖未授权外部 Skill、单一授权不传递、缺少授权时停止或请求授权、外部输出不改变当前 Contract；
- 分别验证 Cursor、Claude Code 和 Codex 的显式调用策略；
- 记录每次运行是否实际发生其他 Skill / Plugin Invocation。

## 14. Definition of Done — Design

- [ ] 单一职责明确。
- [ ] In Scope 和 Out of Scope 不重叠。
- [ ] 应触发和不应触发场景可区分。
- [ ] 必要输入和缺失行为明确。
- [ ] 输出、成功和失败条件可判定。
- [ ] 权限和副作用满足最小权限。
- [ ] Skill / Plugin Interoperability Contract 全部字段可判定。
- [ ] Exclusive Skill Execution Contract 不被描述为硬安全隔离。
- [ ] 三端显式调用默认策略已登记。
- [ ] `SKILL.md`、`agents/openai.yaml`、references、scripts、assets 边界明确。
- [ ] Eval Plan 足以验证触发和行为。
- [ ] 不存在阻塞实现的 Open Item。
- [ ] 本阶段没有创建正式 `SKILL.md`。

## 15. Open Items

| ID | Question / Missing Decision | Blocks | Expected Source | Status |
|---|---|---|---|---|
| None | No blocking open items | N/A | N/A | closed |

## 16. 确认记录

| Role | Decision | Basis |
|---|---|---|
| Maintainer | `pending / approved / rejected` | |
