---
title: "可维护性与扩展性 Maintainability and Extensibility"
status: draft
scope: DSN Domain 固定模板、规则与专属 Gate
parent: ../200-dsn-spec.md
---

# 可维护性与扩展性 Maintainability and Extensibility

文件名：`350-maintainability-extensibility.md`

边界：

- 负责已确认的可维护性目标、维护压力、变化边界、扩展点和多实现模型；
- Component 的当前责任由 `Components and Modules` 承载；
- 精确扩展 Contract 由 `Interfaces and Integration` 承载；
- 命名、格式、代码风格和分支规范等项目级规则由可验证项目基线或 Project Extension 承载；
- 测试方法由 VFY Strategy 承载，本 Domain 只记录扩展实现必须满足的验证约束；
- 当前 Domain 描述被研发产品自身的扩展设计，不定义 `sdlc-ai-spec` 的 Project Extension 机制。

适用性：

- Requirement 明确需要插件、Provider、跨编程语言实现或多种可替换技术实现，且尚无准确 Host 完整承载扩展模型时，为 `required`；
- 存在明确的模块化、复用、可分析、可修改等维护目标，或可以由 Requirement 或 Evidence 证明的持续变化压力时，存在独立设计义务则为 `required`；
- 项目已有固定扩展模型并且完整覆盖时，可以为 `embedded`；
- 普通局部实现且没有新的维护或扩展边界时，可以为 `n/a`；
- 不得为了未来可能需求而虚构扩展点、接口或抽象层。

固定专属模板：

```markdown
## 设计结果 Design Result

### 维护与变化驱动 Maintenance and Variation Drivers

| ID | Requirement or Evidence | 已知变化或维护压力 Known Variation or Maintenance Pressure | 影响范围 Impact Scope | 判断依据 Basis |
|---|---|---|---|---|
| MNT-001 | | | | |

### 可维护性目标 Maintainability Objectives

| ID | 关注点 Concern | Requirement or Evidence | 目标或约束 Objective or Constraint | 设计响应 Design Response | VFY Reference |
|---|---|---|---|---|---|
| MAO-001 | modifiability | | | | |

### 变化边界 Change Boundaries

| ID | 稳定核心 Stable Core | 可变区域 Variable Area | 允许变化 Permitted Change | 禁止影响 Prohibited Impact | 承载对象 Host |
|---|---|---|---|---|---|
| BND-001 | | | | | |

### 扩展点清单 Extension Point Registry

| ID | 用途 Purpose | Contract 引用 Contract Reference | 默认实现 Default Implementation | 注册或选择机制 Registration or Selection | 约束 Constraints |
|---|---|---|---|---|---|
| EXT-001 | | | | | |

### 实现模型 Implementation Model

| Extension Point | Implementation ID | 类型 Type | 适用条件 Applicable Condition | 依赖 Dependencies | 变化 Change |
|---|---|---|---|---|---|
| EXT-001 | EIM-001 | built_in | | | new |

### 依赖约束 Dependency Rules

| 来源 Source | 允许依赖 Allowed Dependency | 禁止依赖 Prohibited Dependency | 原因 Reason | Enforcement or Evidence |
|---|---|---|---|---|
| | | | | |

### 演进约束 Evolution Constraints

| Extension Point or Contract | 版本或兼容规则 Version or Compatibility Rule | 废弃或移除条件 Deprecation or Removal Condition | Migration 引用 Migration Reference |
|---|---|---|---|
| | | | |

### 维护支持 Maintenance Support

| Object | 文档 Documentation | 诊断或 Observability | VFY 引用 VFY Reference | 责任方 Owner |
|---|---|---|---|---|
| | | | | |
```

规则：

- 每个维护或变化驱动必须具有 Requirement 或 Evidence，不得根据想象创建未来需求；
- `Concern` 使用 `modularity`、`reusability`、`analyzability`、`modifiability` 或项目扩展的已注册值；没有明确目标时不得为了覆盖术语而虚构指标；
- 每个 Extension Point 必须关联至少一个有效 Driver 和稳定 Contract；
- 存在默认实现时必须准确记录；不存在默认实现时填写 `N/A` 和原因，不得虚构；
- `Type` 使用 `built_in`、`project`、`external` 或项目扩展的已注册类型；
- `Change` 使用 `new`、`changed`、`reused` 或 `removed`；
- 只设计当前需要的实现，不得预先创建没有 Requirement 的实现变体；
- 注册、选择和依赖机制必须明确，不得依赖未记录的隐式约定；
- 扩展 Contract 必须引用 Interface Domain，兼容和移除规则必须引用 `Compatibility and Migration`；
- 项目级代码和分支规范只需准确引用，不在当前 DSN 重复全文；
- 不要求列出每个源文件、类或函数，除非它们本身构成稳定维护边界；
- VFY Points 必须覆盖默认实现、适用扩展实现、选择机制和依赖约束。

专属 Gate：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-350-001 | 适用的维护压力与变化驱动已完整识别并具有准确来源 | pending |  |
| DSN-DG-350-002 | 稳定核心、可变区域和禁止影响明确 | pending |  |
| DSN-DG-350-003 | 每个 Extension Point 具有现实需求和 Contract | pending |  |
| DSN-DG-350-004 | 默认实现或其 N/A 原因明确 | pending |  |
| DSN-DG-350-005 | 当前需要的实现及适用条件明确 | pending |  |
| DSN-DG-350-006 | 注册、选择和依赖规则明确 | pending |  |
| DSN-DG-350-007 | 不存在推测性实现或无依据抽象 | pending |  |
| DSN-DG-350-008 | 演进、兼容和移除规则准确 | pending |  |
| DSN-DG-350-009 | 维护文档、诊断和 VFY 引用完整 | pending |  |
| DSN-DG-350-012 | 适用的可维护性目标具有设计响应和 VFY 引用 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
