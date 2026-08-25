---
title: "用户体验与交互 UX and Interaction"
status: draft
scope: DSN Domain 固定模板、规则与专属 Gate
parent: ../200-dsn-spec.md
---

# 用户体验与交互 UX and Interaction

文件名：`120-ux-interaction.md`

边界：

- 负责描述用户如何完成目标以及系统如何反馈；
- 系统业务流程和状态由 `Workflow and State` 承载；
- 视觉样式和具体展示内容由 `UI and Content` 承载；
- 技术接口和数据结构由对应 Technical Domain 承载。

适用性：

- Requirement 改变用户目标、任务路径、动作顺序、反馈语义、交互状态或中断恢复路径时，存在独立设计义务则为 `required`；
- 交互极简单且已经由其他 required Domain 完整表达并准确追踪时，可以为 `embedded`；
- 纯系统间处理、后台任务且用户无感知时，可以为 `n/a`；
- 仅改变已确定的静态文案或视觉表达且不存在交互义务时，本 Domain 为 `n/a`；存在简单交互义务且由 `UI and Content` 完整承载时，本 Domain 为 `embedded`；
- 不得因为沿用现有交互、参与者不准备阅读或接受 AI 设计而直接判定为 `n/a`。

固定专属模板：

```markdown
## 设计结果 Design Result

### 用户与目标 Users and Goals

| ID | 用户或用户组 User or User Group | 使用场景 Context | 目标 Goal | 成功条件 Success Condition |
|---|---|---|---|---|
| USR-001 | | | | |

### 入口与完成条件 Entry and Completion

| Journey ID | Journey Name | User or Goal References | 入口 Entry | 前置条件 Preconditions | 完成条件 Completion Condition | 完成后去向 Destination |
|---|---|---|---|---|---|---|
| JNY-001 | | USR-001 | | | | |

### 用户旅程 User Journey

| Journey ID | Step ID | 用户动作 User Action | 系统反馈 System Feedback | 关联状态 Related State |
|---|---|---|---|---|
| JNY-001 | JST-001 | | | |

### 旅程转换 Journey Transitions

| Transition ID | Journey ID | From Step | Condition or Event | To Step or Terminal | Priority |
|---|---|---|---|---|---|
| JTR-001 | JNY-001 | JST-001 | | terminal | 1 |

### 交互状态 Interaction States

| 对象或区域 Object or Area | 状态 State | 触发条件 Trigger | 反馈意图 Feedback Intent | 可执行操作 Available Actions |
|---|---|---|---|---|
| | default | | | |

### 输入与反馈 Input and Feedback

| 输入或操作 Input or Action | 约束 Constraint | 校验时机 Validation Timing | 反馈意图 Feedback Intent | 修正路径 Correction Path |
|---|---|---|---|---|
| | | | | |

### 中断与恢复 Interruption and Recovery

| 场景 Scenario | 保留的数据或状态 Retained Data or State | 用户反馈 User Feedback | 恢复路径 Recovery Path |
|---|---|---|---|
| | | | |
```

规则：

- 不得为了填充模板虚构用户画像、使用场景或交互需求；
- Journey 使用 `JNY-001`、Step 使用 `JST-001`、Transition 使用 `JTR-001` 顺序编号；每个 Step 和 Transition 必须引用所属 Journey ID；
- 每个 Journey 必须通过 `User or Goal References` 引用至少一个本文件 `USR-ID`，并按适用性补充上游 Goal Item Reference；多值引用使用 Core Reference Set，不能靠 Journey 名称或自然语言目标匹配；
- 每个非终止 Step 至少有一条 Transition；`From Step` 和 `To Step` 必须可解析到同一 Journey，终止路径使用 `terminal`；同一来源存在多条可满足转换时以正整数 `Priority` 明确顺序；
- 每条用户旅程必须具有明确入口、完成条件和完成后去向；
- 每个关键用户动作必须具有系统反馈或明确说明无需反馈；
- 交互状态按 Requirement 影响填写，通常检查 `default`、`loading`、`empty`、`success`、`error` 和 `disabled`；
- Feedback Intent 只描述反馈目的和语义，不在此规定具体文案、颜色、位置或视觉样式；
- 具体页面、组件和文案引用 `UI and Content`，不在本 Domain 重复；
- Domain 整体适用但某个子章节不适用时，使用父 Spec 的统一 `N/A — <客观原因>` 表示；
- 原型图和交互图可以作为辅助材料，但固定表格是规范判定依据；
- VFY Points 必须覆盖关键旅程、交互状态、输入反馈和恢复路径。

专属 Gate：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-120-002 | 用户、场景、目标和成功条件明确 | pending |  |
| DSN-DG-120-003 | Journey 的 User or Goal References 可解析，Step、Transition、入口、完成条件和完成后去向明确 | pending |  |
| DSN-DG-120-004 | 关键用户动作均有确定的系统反馈 | pending |  |
| DSN-DG-120-005 | 适用的交互状态已覆盖 | pending |  |
| DSN-DG-120-006 | 输入约束、校验时机和修正路径明确 | pending |  |
| DSN-DG-120-007 | 中断和恢复路径已按适用性处理 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
