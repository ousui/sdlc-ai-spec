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

## 5. Input Contract

| ID | Input | Required | Source | Validation | Missing Behavior |
|---|---|---:|---|---|---|
| IN-01 | | yes/no | | | |

要求：

- 必要事实缺失时不得猜测；
- 缺失行为必须明确为停止、形成待确认项、生成受限状态产物或其他已登记方式；
- 不依赖上一会话的隐式上下文。

## 6. Output Contract

| ID | Output | Format / Location | Required Content | Success Condition | Consumer |
|---|---|---|---|---|---|
| OUT-01 | | | | | |

区分：

- Agent 推理结果；
- 确定性验证结果；
- 需要人工确认的事项；
- 未解决风险。

## 7. Workflow Contract

按最少步骤描述稳定工作流：

1. `<读取和确认输入>`
2. `<执行领域工作>`
3. `<处理缺失或冲突>`
4. `<形成输出>`
5. `<执行检查并报告结果>`

不得把实现细节、平台安装步骤或未来扩展混入领域工作流。

## 8. Failure Contract

| Failure | Detection | Required Behavior | Forbidden Fallback |
|---|---|---|---|
| | | | |

必须明确：

- 哪些情况是失败；
- 哪些情况是等待输入；
- 是否允许部分结果；
- 如何避免静默降级；
- 如何保证失败不会被描述为成功。

## 9. 权限与副作用

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

## 10. 资源边界

### `SKILL.md`

`<只保留触发、核心工作流、输入输出和必要约束>`

### `references/`

`<需要按需加载的详细规则；没有则写 None>`

### `scripts/`

`<需要确定性执行的操作；没有则写 None>`

### `assets/`

`<模板或静态资源；没有则写 None>`

### 共享资源判断

`<是否已有第二个真实使用者；没有则不得提升到 Plugin 根级>`

## 11. Portability Contract

| Concern | Portable Core | Cursor Adapter | Claude Code Adapter | Codex Adapter |
|---|---|---|---|---|
| Skill source | | | | |
| Invocation | | | | |
| Path resolution | | | | |
| Platform-specific metadata | | | | |

平台差异不得改变输出 Artifact、失败语义或领域完成条件。

## 12. Eval Plan

对应文件：

`docs/plugin-development/work-items/<skill-name>/EVAL-PLAN.md`

最低案例：

- 至少 2 个应该触发案例；
- 至少 2 个不应该触发案例；
- 至少 1 个输入完整案例；
- 至少 1 个必要输入缺失案例；
- 至少 1 个边界或冲突案例；
- 至少 1 组 with-skill / without-skill 对比。

## 13. Definition of Done — Design

- [ ] 单一职责明确。
- [ ] In Scope 和 Out of Scope 不重叠。
- [ ] 应触发和不应触发场景可区分。
- [ ] 必要输入和缺失行为明确。
- [ ] 输出、成功和失败条件可判定。
- [ ] 权限和副作用满足最小权限。
- [ ] `SKILL.md`、references、scripts、assets 边界明确。
- [ ] Eval Plan 足以验证触发和行为。
- [ ] 不存在阻塞实现的 Open Item。
- [ ] 本阶段没有创建正式 `SKILL.md`。

## 14. Open Items

| ID | Question / Missing Decision | Blocks | Expected Source | Status |
|---|---|---|---|---|
| None | No blocking open items | N/A | N/A | closed |

## 15. 确认记录

| Role | Decision | Basis |
|---|---|---|
| Maintainer | `pending / approved / rejected` | |
