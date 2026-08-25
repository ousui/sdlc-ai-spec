---
title: "流程与状态 Workflow and State"
status: draft
scope: DSN Domain 固定模板、规则与专属 Gate
parent: ../200-dsn-spec.md
---

# 流程与状态 Workflow and State

文件名：`110-workflow-state.md`

适用性：

- 新增或改变业务规则、计算规则、资格判断、决策逻辑、不变量、多步骤流程、状态变化、角色协作、审批、异步处理、重试、取消或恢复时，存在独立设计义务则为 `required`；
- 简单行为已经由其他 required Domain 完整表达且可以准确追踪时，可以为 `embedded`；
- Requirement 不引入任何业务行为、规则、计算、决策、不变量、流程或状态影响时，可以为 `n/a`；
- 不得因为流程简单、参与者不准备阅读或接受 AI 设计而判定为 `n/a`。
- 迁移旧态、目标态、共存和切换流程以 `Compatibility and Migration` 为权威来源；迁移流程义务被其完整承载时，本 Domain 为 `embedded`，完全不存在流程、规则或状态义务时才为 `n/a`；只有存在独立业务或角色流程时，本 Domain 才单独为 `required`。

固定专属模板：

```markdown
## 设计结果 Design Result

### 参与者与触发 Participants and Triggers

| ID | 参与者或系统 Actor or System | 触发 Trigger | 前置条件 Preconditions | 预期结果 Expected Result | Flow References |
|---|---|---|---|---|---|
| ACT-001 | | | | | FLW-001 |

### 流程 Flow

| Flow ID | Step ID | 类型 Type | 执行者 Actor | 输入或事件 Input or Event | 行为 Action | 结果或状态 Result or State |
|---|---|---|---|---|---|---|
| FLW-001 | FST-001 | main | | | | |

### 流程转换 Flow Transitions

| Transition ID | Flow ID | From Step | Condition or Event | To Step or Terminal | Priority |
|---|---|---|---|---|---|
| TRN-001 | FLW-001 | FST-001 | | terminal | 1 |

### 状态与转换 States and Transitions

| State ID | 状态 State | 含义 Meaning | 进入条件 Entry Condition | 是否终止 Terminal |
|---|---|---|---|---|
| WST-001 | | | | |

### 状态转换 State Transitions

| Transition ID | From State | Condition or Event | To State | Action or Effect | Priority |
|---|---|---|---|---|---|
| STT-001 | WST-001 | | WST-001 | | 1 |

### 业务规则、决策与不变量 Business Rules, Decisions and Invariants

| ID | 类型 Type | 输入 Input | 条件 Condition | 结果 Result | 优先级或冲突处理 Priority or Conflict Handling | 来源 Source | 违反时处理 Violation Handling |
|---|---|---|---|---|---|---|---|
| RUL-001 | rule | | | | | | |

### 异常与恢复 Exceptions and Recovery

| 条件 Condition | 发现方式 Detection | 处理 Handling | 最终结果或状态 Final Result or State |
|---|---|---|---|
| | | | |
```

规则：

- `Type` 使用 `main`、`alternate` 或 `exception`；
- Business Rule `Type` 使用 `rule`、`calculation`、`eligibility`、`decision` 或 `invariant`；
- Flow 使用 `FLW-001`，Step 使用 `FST-001`，Flow Transition 使用 `TRN-001`，State 使用 `WST-001`，State Transition 使用 `STT-001` 顺序编号；同一 Flow 的每个 Step 和 Flow Transition 必须引用同一 Flow ID；
- 每条参与者与触发记录必须通过 `Flow References` 引用其启动的一个或多个 Flow ID；多值引用使用 Core Reference Set，不能靠表格顺序或文字相似度推断；
- 每个非终止 Step 至少有一条 Transition；`From Step` 和 `To Step` 必须可解析到同一 Flow，终止路径使用 `terminal`；同一来源存在多条可满足转换时以正整数 `Priority` 明确顺序；
- 每个 State Transition 的 From/To State 必须可解析；同一来源存在多条可满足转换时同样使用正整数 `Priority`；
- 图示可以作为辅助材料，但固定表格是规范判定依据；
- Domain 整体适用但某个子章节不适用时，使用父 Spec 的统一 `N/A — <客观原因>` 表示；
- 流程步骤必须明确执行者、输入或事件、行为以及结果；
- 状态必须含义唯一，并明确允许的转换和终止状态；
- 重试、取消、超时、失败和恢复按 Requirement 影响填写，不适用时不得虚构；
- VFY Points 必须能够覆盖关键流程、状态转换和异常结果。

专属 Gate：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-110-002 | 参与者、触发、前置条件及其 Flow References 明确且可解析 | pending |  |
| DSN-DG-110-003 | Flow、Step、Transition 及主流程、替代流程和异常流程已按适用性处理 | pending |  |
| DSN-DG-110-004 | State ID、状态含义、转换和终止条件明确 | pending |  |
| DSN-DG-110-005 | 规则与不变量可追踪 | pending |  |
| DSN-DG-110-006 | 异常和恢复具有确定结果 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
