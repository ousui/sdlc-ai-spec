---
title: "数据设计 Data Design"
status: draft
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 数据设计 Data Design

文件名：`240-data-design.md`

边界：

- 负责具有稳定业务或系统生命周期的数据，不要求记录普通变量、临时对象或纯实现细节；
- 只在接口中传输、不形成共享或持久化数据的 Payload 由 `Interfaces and Integration` 承载；
- 数据库或存储技术选型集中记录在主文件 `Design Decisions`；
- 存储实例、连接和运行配置由 `Deployment and Configuration` 承载；
- 性能目标由 `Performance and Capacity` 承载，本 Domain 记录索引、分区或缓存等具体响应；
- 隐私及保留要求由 `Security, Privacy and Compliance` 承载，本 Domain 记录具体落实方式；
- Migration 策略由 `Compatibility and Migration` 承载，本 Domain 记录目标结构和转换映射。

适用性：

- 新增或改变持久化或共享数据、Schema、所有权、一致性或生命周期，或者改变共享或稳定 Cache Contract、所有权、失效规则或一致性时，通常为 `required`；
- 完全复用现有数据模型且当前变化没有数据设计义务时，可以引用准确 Baseline 判定为 `n/a`；
- 仅涉及局部临时数据且不改变任何数据契约时，可以为 `n/a`；
- 普通组件内部临时缓存不触发 Data Design；其实现归 Components、Performance 或 IMP，除非形成共享或稳定 Cache Contract；
- 没有传统数据库不代表 `n/a`，事件状态、文件、缓存等仍可能需要 Data Design。

固定专属模板：

```markdown
## 设计结果 Design Result

### 数据清单与所有权 Data Inventory and Ownership

| ID | 名称 Name | 类型 Type | 责任方 Owner | 事实来源 Source of Truth | 数据分类引用 Data Classification Reference | 变化 Change |
|---|---|---|---|---|---|---|
| DAT-001 | | entity | CMP-001 | | | new |

### 数据定义来源 Data Definition Source

| Data Object | 定义方式 Definition Mode | 格式 Format | 原生 Artifact Native Artifact | Inline Section | Schema Version |
|---|---|---|---|---|---|
| DAT-001 | inline | Markdown | N/A | Inline Data Definition | |

### Inline 数据定义 Inline Data Definition

| Data Object | 字段路径 Field Path | 类型 Type | 必填 Required | 默认值 Default | 语义 Semantics | 约束 Constraints |
|---|---|---|---|---|---|---|
| DAT-001 | | | | | | |

### 标识与关系 Identity and Relationships

| Data Object | 标识 Identifier | 标识类型 Identifier Type | 关联对象 Related Object | 基数 Cardinality | 引用、更新或删除行为 Reference, Update or Delete Behavior |
|---|---|---|---|---|---|
| DAT-001 | | | | | |

### 存储与访问 Storage and Access

| Data Object | 存储位置 Storage Host | 持久性 Persistence | 访问模式 Access Pattern | 索引、分区或缓存 Index, Partition or Cache | Decision 引用 Decision Reference |
|---|---|---|---|---|---|
| DAT-001 | | | | | DEC-001 |

### 一致性与事务 Consistency and Transactions

| 操作或范围 Operation or Scope | Data Objects | 一致性模型 Consistency Model | 事务边界 Transaction Boundary | 并发或冲突处理 Concurrency or Conflict Handling | 失败结果 Failure Result |
|---|---|---|---|---|---|
| | | | | | |

### 数据生命周期 Data Lifecycle

| Data Object | 创建或来源 Creation or Source | 更新 Update | 保留 Retention | 归档 Archive | 删除或清理 Deletion or Cleanup | Privacy or Compliance Reference |
|---|---|---|---|---|---|---|
| DAT-001 | | | | | | |

### 演进与转换 Evolution and Transformation

| Data Object | 来源版本 Source Version | 目标版本 Target Version | 映射或转换 Mapping or Transformation | 兼容窗口 Compatibility Window | Migration 引用 Migration Reference |
|---|---|---|---|---|---|
| DAT-001 | | | | | |
```

规则：

- `Type` 使用 `entity`、`document`、`event_state`、`file`、`cache`、`reference` 或项目扩展的已注册类型；
- `Change` 使用 `new`、`changed`、`reused` 或 `removed`；
- `Source of Truth` 表示业务或系统事实的权威来源，不表示 Schema 文件位置；
- `Definition Mode` 使用 `native` 或 `inline`；
- 使用 `native` 时，DDL、Schema、ORM Model 等原生文件是字段级事实来源，Markdown 不重复抄写字段；
- 使用 `inline` 时，Inline Data Definition 必须完整定义字段、类型、语义和约束；
- 原生 Schema 与 Markdown 索引、语义或 Gate 冲突时，Artifact 不得进入 `ready` 或 `ready_with_exception`；
- 业务标识、存储标识以及它们之间的关系必须明确；
- 数据责任方、事实来源、事务边界和冲突结果不得缺失；
- 保留、归档、删除和隐私规则必须引用 Requirement 或对应 Domain，不得自行虚构；
- 存储、数据库或缓存技术选型必须引用主文件中的 Design Decision；
- 迁移和兼容结果必须与 `Compatibility and Migration` 一致；
- 原生 Schema 文件属于父 DSN Artifact Set，其语义变化触发父 DSN Revision 变化；
- VFY Points 必须覆盖数据约束、一致性、生命周期和适用的转换结果。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-240-001 | 数据对象、责任方、事实来源、唯一定义、标识和关系完整一致 | pending |  |
| DSN-DG-240-002 | 存储访问、一致性、事务、冲突及适用的索引、分区或缓存明确 | pending |  |
| DSN-DG-240-003 | 保留、删除、Schema 演进与迁移按适用性处理，并由 VFY Points 覆盖 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
