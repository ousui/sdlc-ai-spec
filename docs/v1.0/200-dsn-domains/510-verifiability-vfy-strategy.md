---
title: "可验证性与 VFY 策略 Verifiability and VFY Strategy"
status: stable
version: "1.0"
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 可验证性与 VFY 策略 Verifiability and VFY Strategy

文件名：`510-verifiability-vfy-strategy.md`

边界：

- 负责将 Requirement、Design Decision 和其他 required Domain 的 VFY Points 汇总为可执行、可判定的验证策略；
- REQ 定义 Acceptance Criteria；
- 其他 required DSN Domain 提供局部 VFY Points；510 不再生成重复的 `VFP-510-*`；
- 本 Domain 识别跨领域验证目标以及必要的可验证性设计；
- PLN 安排验证工作，IMP 实现必要测试、控制点或观测能力；
- VFY 执行尚未完成的方法，汇总和复核此前各 Phase 的 Evidence，并形成 Verification 与 Validation 结论；
- QA 由各 Phase 的 Check Set、Evidence 和 Gate 贯穿承载，不等同于 Test，也不由本 Domain 重复定义；
- 本 Domain 不提前编写完整测试用例或绑定具体验证工具。

适用性：

- DSN Artifact 存在时，本 Domain 不能为 `n/a`；
- 验证跨多个 Domain、涉及重要风险、质量属性或特殊环境与数据时，通常为 `required`；
- 本 Domain 在当前内置 DSN Spec 中固定为 `required`；VFY Objective 是必须保留的验证目标，不能在 DSN 中删除或豁免；具体 Method 可以经 Exception 豁免，但不能豁免整体可验证性义务，后续 VFY Artifact 仍然必须存在；
- 无法确定可观察结果或通过条件时，DSN 不能进入 `ready` 或 `ready_with_exception`，必须返回上游或进入 `waiting_input`。

固定专属模板：

```markdown
## 设计结果 Design Result

### VFY 目标 VFY Objectives

| ID | Kind | Requirement, AC, Goal or Intended-use References | Design or Decision References | Domain VFY Point References | 可观察结果 Observable Result | 风险或重要性 Risk or Importance | Method References | Pass Criteria References | Evidence Contract References |
|---|---|---|---|---|---|---|---|---|---|
| VFO-001 | both | | | VFP-230-001 | | | VFM-001 | VPC-001 | VEC-001 |

### 方法选择 VFY Methods

| ID | 类型 Type | Disposition | 方法明细 Method Detail | 适用范围 Scope | 方法 Method | 选择依据 Selection Basis | 承载位置 Host | Exception Reference |
|---|---|---|---|---|---|---|---|---|
| VFM-001 | test | required | level=integration, mode=automated | | | | VFY | N/A |

### 可验证性设计 Verifiability Design

| 验证对象 Verification Object | 当前障碍 Current Barrier | 设计机制或控制点 Design Mechanism or Control Point | 承载 Domain Host Domain | 预期作用 Expected Effect |
|---|---|---|---|---|
| | | | | |

### 环境与数据 Environment and Data

| VFY Objective | 环境 Environment | Dependencies | 数据 Data | 隔离与重置 Isolation and Reset | Sensitivity Reference |
|---|---|---|---|---|---|
| VFO-001 | | | | | |

### 覆盖策略 Coverage Strategy

| 范围或风险 Scope or Risk | 正常 Normal | 异常 Exception | 边界 Boundary | 兼容或质量属性 Compatibility or Quality Attribute | 排除项及原因 Exclusion and Reason |
|---|---|---|---|---|---|
| | | | | | |

### 通过条件 Pass Criteria

| ID | VFY Objective | 输入或条件 Input or Condition | 预期结果 Expected Result | 容差 Tolerance | 失败条件 Failure Condition |
|---|---|---|---|---|---|
| VPC-001 | VFO-001 | | | | |

### Evidence Contract

| ID | VFY Objective | Evidence Type | 生成方或来源 Producer or Source | 必要内容 Required Content | 敏感性与处理 Sensitivity and Handling | 保留要求 Retention Requirement | 保存或引用位置 Storage or Reference |
|---|---|---|---|---|---|---|---|
| VEC-001 | VFO-001 | | | | | | |

### 限制与例外 Limitations and Exceptions

| VFY Objective | 限制 Limitation | 未覆盖风险 Uncovered Risk | 缓解 Mitigation | Exception Reference |
|---|---|---|---|---|
| VFO-001 | | | | |
```

规则：

- VFY Method Type 只使用 `inspection`、`analysis`、`demonstration` 或 `test`；Review 通常归入 Inspection，静态计算或扫描通常归入 Analysis，人工操作按是否具有明确输入、预期和通过条件归入 Demonstration 或 Test；
- VFY Objective 不设置 Disposition；每个 Objective 都是后续 VFY Target。Method Disposition 只使用 `required`、`waived` 或 `pending`：`required` 的 Exception 写 `N/A`，`waived` 必须引用父 DSN 中有效 Exception，`pending` 必须引用阻塞 Open Item 且不能通过 Gate；不适用的方法不创建行；
- VFY Objective `Kind` 使用 `verification`、`validation` 或 `both`；Verification 追踪 Requirement、Acceptance Criteria 和 Design；Validation 至少追踪 Goal、Stakeholder Need 或 Intended Use，并按适用性补充 Affected Parties 和 Operational Context；
- `manual`、`automated` 或 `hybrid` 是 Execution Mode，不是 Method Type；Unit、Component、Interface、Integration、System 和 End-to-End 是 Test Level；Performance、Security、Recovery、Compatibility 和 Accessibility 是目标或范围描述；以上内容统一写入 Method Detail；
- 当前 DSN Scope 内的每个 Requirement Acceptance Criterion 和关键 Design Decision 必须关联至少一个 VFY Objective；每个 Validation Objective 必须至少关联 Goal、Stakeholder Need 或 Intended Use；
- 其他 required Domain 的 VFY Points 必须通过引用汇总，不在本 Domain 重复抄写设计内容；没有其他 required Domain VFY Point 时，`Domain VFY Point References` 写 `None`；
- 每个其他 required Domain VFY Point 必须由 `Domain VFY Point References` 映射到至少一个 VFY Objective；
- Evidence Contract 使用 `VEC-001` 顺序编号，每个 VFY Objective 必须引用至少一个准确 Evidence Contract；
- Observable Result 和 Pass Criteria 必须能够得出明确 `pass` 或 `fail`，不得只写“正常”“正确”或“符合预期”；
- 方法选择由风险、目标和可观察结果决定，不得为了提高自动化比例而强制采用工具；
- 需要额外接口、状态、控制点、数据或观测能力时，必须记录在 Verifiability Design 并返回对应 Domain；
- Environment and Data 必须明确依赖、隔离、重置和敏感性，不得记录真实 Secret 或生产敏感值；
- 排除项、限制和未覆盖风险必须具有原因，适用但跳过时引用 Exception；
- 本 Domain 不规定固定覆盖率数字、自动化比例或特定测试平台；
- 后续 VFY Artifact 必须准确绑定当前 DSN Revision，并执行或承接本策略。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-510-001 | DSN Artifact 存在时本 Domain 为 required，Acceptance Criteria、关键 Decision 和其他 required Domain 的全部 VFY Points 均映射到 VFY Objective | pending |  |
| DSN-DG-510-002 | 每个 Objective 具有可观察结果、匹配风险的 required 或已授权 waived Method、明确 Pass Criteria 和 Evidence Contract | pending |  |
| DSN-DG-510-003 | 必要的可验证性机制已返回对应 Domain，环境、依赖、数据、隔离和重置要求明确 | pending |  |
| DSN-DG-510-004 | 正常、异常、边界、质量属性、限制和未覆盖风险已处理 | pending |  |
| DSN-DG-510-005 | Validation Objective 覆盖预期用途，Evidence 处理合规，且未强制无依据的覆盖率、自动化比例或工具 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
