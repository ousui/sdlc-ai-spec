---
title: "兼容与迁移 Compatibility and Migration"
status: stable
version: "1.1"
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 兼容与迁移 Compatibility and Migration

文件名：`340-compatibility-migration.md`

边界：

- 负责旧状态与目标状态的兼容关系、共存条件和迁移过程；
- Interface Domain 定义目标 Contract；
- Data Domain 定义目标 Schema 和数据转换关系；
- Deployment Domain 落实发布、路由和配置机制；
- RLS 执行当前发版的实际切换并记录 Evidence；
- Reliability Domain 负责运行故障恢复，本 Domain 负责迁移过程失败后的处理；
- 本 Domain 只设计迁移顺序和约束，不提前形成执行任务或排期。
- 旧态、目标态、共存、切换和迁移过程失败处理以本 Domain 为权威来源；Deployment 和 Reliability 只记录各自落实结果并引用本 Domain Item。

适用性：

- 改变 Interface、Schema、Data、Config 或 Runtime，且影响已有消费者或已有状态时，通常为 `required`；
- 新旧版本需要并行运行或分阶段切换时，为 `required`；
- 变化完全兼容且不需要新增或改变兼容与迁移规则时，可以引用准确 Baseline 判定为 `n/a`；
- 全新且隔离的能力，不存在旧版本、旧数据或既有消费者时，可以为 `n/a`；
- 无法确认现有消费者、版本或数据规模时，必须进入 `waiting_input`，不得猜测；
- 紧急直接切换而经授权跳过必要兼容设计时必须使用 `waived`。

固定专属模板：

```markdown
## 设计结果 Design Result

### 影响对象 Affected Objects

| ID | 类型 Type | 对象引用 Object Reference | 当前版本或状态 Current Version or State | 目标版本或状态 Target Version or State | 消费者或影响范围 Consumers or Impact Scope |
|---|---|---|---|---|---|
| MIG-001 | interface | IFC-001 | | | |

### 兼容矩阵 Compatibility Matrix

| Object | 生产方或写入方 Producer or Writer | 消费方或读取方 Consumer or Reader | 兼容结论 Compatibility Result | 条件 Conditions | Evidence |
|---|---|---|---|---|---|
| MIG-001 | | | compatible | | |

### 变化分类 Change Classification

| ID | Object | 变化 Change | 兼容结论 Compatibility Result | 判断依据 Basis | 影响对象 Affected Consumer or State |
|---|---|---|---|---|---|
| MCH-001 | MIG-001 | | | | |

### 共存与过渡 Coexistence and Transition

| 过渡状态 Transition State | 活跃版本 Active Versions | 路由、读或写行为 Routing, Read or Write Behavior | 进入条件 Entry Condition | 退出条件 Exit Condition | 时间或其他限制 Time or Other Limit |
|---|---|---|---|---|---|
| | | | | | |

### 迁移映射 Migration Mapping

| Object, Field or Config | 旧值或结构 Old Value or Structure | 新值或结构 New Value or Structure | 转换 Transformation | 校验 Validation | 异常处理 Exception Handling |
|---|---|---|---|---|---|
| | | | | | |

### 切换与失败处理 Cutover and Failure Handling

| 步骤或条件 Step or Condition | 前置条件 Preconditions | 切换行为 Cutover Action | 责任角色 Responsible Role | 授权或约束引用 Authorization or Constraint Reference | 成功 Evidence | 失败停止点 Failure Stop Point | 恢复或降级 Recovery or Fallback | 可逆性 Reversibility |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

### 废弃与移除 Deprecation and Removal

| Object or Version | 废弃通知 Deprecation Notice | 观察条件 Observation Condition | 移除条件 Removal Condition | 残留清理 Cleanup | 责任方 Owner |
|---|---|---|---|---|---|
| | | | | | |
```

规则：

- Compatibility Result 使用 `compatible`、`conditionally_compatible` 或 `breaking`；
- 兼容判断必须明确生产方或写入方、消费方或读取方及其版本，不能只写含义不清的“向前兼容”或“向后兼容”；
- 每个已有消费者、版本和数据状态必须具有 Evidence，不得根据代码局部推测全部使用情况；
- `conditionally_compatible` 必须列出完整条件，`breaking` 必须关联迁移或 Exception；
- 不强制假设迁移可以 rollback；可恢复时写明路径，不可逆时必须明确不可逆点、进入条件、风险和失败处理；
- 迁移映射必须具有校验方式和异常处理，不得只描述目标结构；
- 共存状态必须具有明确进入和退出条件，不能无限期保留临时兼容逻辑；
- 废弃与移除必须依据可观察条件，不得只填写计划日期；
- API Diff、Schema Diff、数据盘点和消费者清单可以作为 Supporting Artifact；
- VFY Points 必须覆盖兼容组合、迁移映射、切换条件、失败处理和移除条件。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-340-001 | 受影响对象、消费者、版本、数据及当前和目标状态具有 Evidence | pending |  |
| DSN-DG-340-002 | 兼容矩阵、结论、共存和迁移映射完整一致 | pending |  |
| DSN-DG-340-003 | 切换、校验、异常停止、可逆性、废弃与清理条件明确，并由 VFY Points 覆盖 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
