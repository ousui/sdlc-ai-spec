---
title: "系统与架构 System and Architecture"
status: draft
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 系统与架构 System and Architecture

文件名：`210-system-architecture.md`

边界：

- 负责系统边界、系统或子系统责任、高层关系以及架构约束；
- 模块和代码内部拆分由 `Components and Modules` 承载；
- 协议、接口字段和错误约定由 `Interfaces and Integration` 承载；
- 数据模型和存储由 `Data Design` 承载；
- 部署拓扑和配置由 `Deployment and Configuration` 承载；
- 架构方案选择及依据集中记录在主文件 `Design Decisions`。

适用性：

- 新增系统、服务、子系统或改变系统边界时，通常为 `required`；
- 改变架构级依赖、系统或子系统责任、质量属性策略，或引入高成本演进约束时为 `required`；
- 完全沿用已有架构且当前变化不存在架构义务时，可以引用准确 Baseline 判定为 `n/a`；
- 纯内容修改或不存在任何结构影响时，可以为 `n/a`；
- 不得仅因为 Requirement 涉及代码就自动判定为 `required`。

固定专属模板：

```markdown
## 设计结果 Design Result

### 架构驱动 Architecture Drivers

| ID | 利益相关方 Stakeholder | 关注点 Concern | 类型 Type | Requirement 或 Evidence | 驱动或约束 Driver or Constraint | 架构影响 Architecture Impact |
|---|---|---|---|---|---|---|
| DRV-001 | | | requirement | | | |

### 系统上下文 System Context

| ID | 参与者或系统 Actor or System | 边界 Boundary | 责任 Responsibility | 交互目的 Interaction Purpose | 变化 Change |
|---|---|---|---|---|---|
| SYS-001 | | inside | | | reused |

### 结构总览 Structural Overview

| ID | 系统或子系统 System or Subsystem | 责任 Responsibility | 边界 Boundary | 变化 Change | Decision 引用 Decision Reference |
|---|---|---|---|---|---|
| ARC-001 | | | | | DEC-001 |

### 高层关系 High-level Relationships

| ID | 来源 Source | 目标 Target | 关系目的 Relationship Purpose | 依赖类型 Dependency Type | 变化 Change |
|---|---|---|---|---|---|
| REL-001 | | | | | |

### 变化影响 Change Impact

| 影响对象 Affected Object | 变化 Change | 设计影响 Design Impact | 影响的下游 Domain Affected Downstream Domain | 关联引用 Reference |
|---|---|---|---|---|
| | | | | |

### 约束与权衡 Constraints and Trade-offs

| Driver | 架构响应 Architecture Response | 代价或限制 Cost or Limitation | Decision 引用 Decision Reference | Evidence |
|---|---|---|---|---|
| DRV-001 | | | DEC-001 | |
```

规则：

- Architecture Driver Type 使用 `requirement`、`quality` 或 `constraint`；
- `Boundary` 明确为系统内部 `inside` 或外部 `outside`；
- `Change` 使用 `new`、`changed`、`reused` 或 `removed`；
- 每个 Architecture Driver 必须具有架构响应，或明确说明不产生架构影响；
- 系统和子系统必须具有清晰且不重叠的主要责任；
- High-level Relationships 只描述方向、目的和依赖，不在此展开协议、字段或错误码；
- 技术选择、架构模式和权衡结论必须引用主文件中的 Design Decision；
- 复用既有架构时必须准确引用可验证项目基线、现有 Artifact 或 Evidence；
- 不得在本 Domain 重复组件、接口、数据或部署的详细设计；
- C4、UML 和架构图可以作为辅助材料，但固定表格是规范判定依据；
- 表示物只有在声明 Purpose、Viewpoint 和 Covered Concerns 时才称为 Architecture View；
- Domain 整体适用但某个子章节不适用时，使用父 Spec 的统一 `N/A — <客观原因>` 表示；
- VFY Points 必须覆盖边界、关键关系和重要架构约束的可观察结果。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-210-001 | Architecture Driver、Stakeholder、Concern 和来源完整 | pending |  |
| DSN-DG-210-002 | 系统边界、责任、外部依赖、高层关系和变化项明确且不冲突 | pending |  |
| DSN-DG-210-003 | 约束、架构响应与权衡可追踪至 Decision，结果足以支持后续设计和 VFY | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
