---
title: "组件与模块 Components and Modules"
status: stable
version: "1.1"
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 组件与模块 Components and Modules

文件名：`220-components-modules.md`

定义：

- Component 是承担独立责任的逻辑或运行单元；
- Module 是 Component 内部的实现组织单元；
- 两者使用同一模板并通过 `Type` 区分。

边界：

- 负责实现单元、责任边界、依赖协作以及 Requirement 的变化分配；
- 系统级结构由 `System and Architecture` 承载；
- 精确请求、响应、事件和错误约定由 `Interfaces and Integration` 承载；
- 数据结构及存储由 `Data Design` 承载；
- Work Item 与 Execution Scope 由 PLN 承载；具体实施逻辑和代码步骤由 IMP 承载；
- 技术选择及权衡集中记录在主文件 `Design Decisions`。

适用性：

- 新增或改变稳定 Component、Module 责任、所有权、依赖 Contract 或跨实现单元的职责分配时为 `required`；
- 局部修改完全落在既有组件内且不改变稳定责任或依赖 Contract 时，可以引用准确 Baseline 判定为 `n/a`；
- 不涉及任何实现单元变化时，可以为 `n/a`；
- 不得仅因为后续进入 IMP 就强制生成组件设计。
- 普通模块内部代码修改、文件调整或新增 Controller，不改变稳定责任或依赖 Contract 时，不自动触发 `required`。

固定专属模板：

```markdown
## 设计结果 Design Result

### 组件清单 Component Inventory

| ID | 名称 Name | 类型 Type | 所属系统 Parent System | 主要责任 Primary Responsibility | 变化 Change |
|---|---|---|---|---|---|
| CMP-001 | | component | SYS-001 | | new |

### 责任边界 Responsibility Boundaries

| Component or Module | 负责 Owns | 不负责 Excludes | 必须保持的约束 Invariants | Decision 引用 Decision Reference |
|---|---|---|---|---|
| CMP-001 | | | | DEC-001 |

### 依赖与协作 Dependencies and Collaboration

| ID | 来源 Source | 目标 Target | 协作目的 Collaboration Purpose | Contract 引用 Contract Reference | 失败影响 Failure Impact |
|---|---|---|---|---|---|
| DEP-001 | | | | | |

### 变化分配 Change Allocation

| Requirement Item | Component or Module | 设计变化 Design Change | 分配依据 Allocation Basis | 影响对象 Affected Object |
|---|---|---|---|---|
| REQ-...@1#R-001 | CMP-001 | | | |

### 生命周期与状态所有权 Lifecycle and State Ownership

| Component or Module | 创建或启动 Creation or Start | 生命周期 Lifetime | 状态所有权 State Ownership | 关闭或释放 Shutdown or Release |
|---|---|---|---|---|
| CMP-001 | | | | |
```

规则：

- `Type` 使用 `component`、`module`、`service`、`library` 或 `other`；
- `Change` 使用 `new`、`changed`、`reused` 或 `removed`；
- 每个 Component 和 Module 必须具有单一、清晰的主要责任；
- Responsibility Boundaries 必须同时说明负责和明确不负责的关键内容；
- Requirement Item 必须分配到一个或多个实现单元，并说明跨单元分配依据；
- 依赖关系只描述协作目的和 Contract 引用，不在此重复接口字段；
- 技术或库选型必须引用主文件中的 Design Decision；
- 数据所有权可以在此声明，但数据结构和持久化规则必须引用 `Data Design`；
- 不要求列出每个源代码文件、类或函数，除非它们本身构成稳定设计边界；
- Domain 整体适用但某个子章节不适用时，使用父 Spec 的统一 `N/A — <客观原因>` 表示；
- 组件图可以作为辅助材料，但固定表格是规范判定依据；
- VFY Points 必须覆盖责任边界、关键依赖和状态所有权的可观察结果。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-220-001 | Component、Module、所属系统、责任、变化和所有权明确且无缺口或冲突 | pending |  |
| DSN-DG-220-002 | 关键依赖、协作 Contract、生命周期和状态所有权完整一致 | pending |  |
| DSN-DG-220-003 | 技术选择可追踪，设计粒度足以支持 PLN 与 VFY 且未提前拆任务 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
