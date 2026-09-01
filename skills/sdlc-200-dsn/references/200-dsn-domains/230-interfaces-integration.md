---
title: "接口与集成 Interfaces and Integration"
status: stable
version: "1.1"
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 接口与集成 Interfaces and Integration

文件名：`230-interfaces-integration.md`

边界：

- 负责系统或稳定组件边界之间如何准确交换信息；
- 组件之间为什么协作由 `Components and Modules` 承载；
- 共享业务数据和持久化结构由 `Data Design` 承载；
- 安全目标由 `Security, Privacy and Compliance` 承载，本 Domain 记录具体应用方式；
- 兼容策略由 `Compatibility and Migration` 承载，本 Domain 记录具体 Contract 的版本结果；
- 普通函数调用不要求登记，除非它构成稳定设计边界。

适用性：

- 新增或改变接口、消息、事件、错误、版本或集成行为时，通常为 `required`；
- 完全复用现有 Contract 且当前变化没有接口或集成设计义务时，可以引用准确 Baseline 判定为 `n/a`；
- 不跨越任何系统或稳定组件边界时，可以为 `n/a`；
- 使用客户端库本身不自动产生 Interface Domain，只有 Contract 发生设计变化时才适用。

固定专属模板：

```markdown
## 设计结果 Design Result

### Contract 清单 Contract Inventory

| ID | 名称 Name | 类型 Type | 提供方 Provider | 消费方 Consumer | 用途 Purpose | 交互方式 Interaction | 变化 Change |
|---|---|---|---|---|---|---|---|
| IFC-001 | | api | CMP-001 | CMP-002 | | request-response | new |

### Contract 定义来源 Contract Definition Source

| Contract | 定义方式 Definition Mode | 格式 Format | 原生 Artifact Native Artifact | Inline Section | Schema Version |
|---|---|---|---|---|---|
| IFC-001 | native | OpenAPI | | N/A | |

### Inline 数据结构 Inline Contract Shape

| Contract | 方向 Direction | 字段路径 Field Path | 类型 Type | 必填 Required | 语义 Semantics | 约束 Constraints |
|---|---|---|---|---|---|---|
| IFC-001 | request | | | | | |

### 交互语义 Interaction Semantics

| Contract | 模式 Mode | 成功条件 Success Condition | 超时或期限 Timeout or Deadline | 幂等 Idempotency | 顺序或交付语义 Ordering or Delivery Semantics |
|---|---|---|---|---|---|
| IFC-001 | sync | | | | |

### 错误约定 Error Contract

| Contract | 错误 ID 或 Code Error ID or Code | 发生条件 Condition | 提供方行为 Provider Behavior | 消费方行为 Consumer Behavior | 可重试 Retryable |
|---|---|---|---|---|---|
| IFC-001 | | | | | |

### 安全绑定 Security Binding

| Contract | 调用身份 Caller Identity | 认证 Authentication | 授权 Authorization | 数据分类引用 Data Classification Reference | Security 引用 Security Reference |
|---|---|---|---|---|---|
| IFC-001 | | | | | |

### 演进与兼容 Evolution and Compatibility

| Contract | 当前版本 Current Version | 变化类型 Change Type | 兼容性 Compatibility | 废弃策略 Deprecation | Migration 引用 Migration Reference |
|---|---|---|---|---|---|
| IFC-001 | | | | | |
```

规则：

- `Type` 使用 `api`、`event`、`message`、`webhook`、`callback`、`file`、`command` 或 `interface`；
- `Change` 使用 `new`、`changed`、`reused` 或 `removed`；
- Provider 和 Consumer 必须引用已登记的系统、Component、Module 或外部对象；
- `Definition Mode` 使用 `native` 或 `inline`；
- 使用 `native` 时，OpenAPI、AsyncAPI、Protobuf、GraphQL SDL、JSON Schema 等原生文件是字段级事实来源，Markdown 不重复抄写字段；
- 使用 `inline` 时，Inline Contract Shape 必须完整定义字段、方向、语义和约束；
- 原生 Contract 与 Markdown 索引、语义或 Gate 冲突时，Artifact 不得进入 `ready` 或 `ready_with_exception`；
- 超时、幂等、顺序和交付语义按实际影响填写，不适用时填写 `N/A` 和原因；
- 安全绑定必须引用对应 Security Design，不得在此重新制定安全目标；
- 版本、废弃和迁移结果必须与 `Compatibility and Migration` 一致；
- Interface Payload 可以在本 Domain 定义；成为共享或持久化业务数据时，必须引用 `Data Design`；
- 原生 Contract 文件属于父 DSN Artifact Set，其语义变化触发父 DSN Revision 变化；
- VFY Points 必须覆盖 Contract、成功行为、错误行为和适用的兼容性结果。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-230-001 | Contract 类型、提供方、消费方、用途和唯一定义来源明确且一致 | pending |  |
| DSN-DG-230-002 | 数据结构、成功、错误、超时、幂等和交付语义完整 | pending |  |
| DSN-DG-230-003 | 安全、版本、兼容与迁移引用准确，并由 VFY Points 覆盖 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
