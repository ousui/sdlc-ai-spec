# sdlc-ai-spec v1.1 Draft 概览

> **核心定位：**建立覆盖软件研发与变更交付过程的统一 Spec。Spec 规定产物和完成标准，AI 是可选的提效手段。

## 1. 要解决的问题

| 问题 | 影响 |
|---|---|
| 上下游产物缺少稳定接口 | 需求、设计、计划和实现容易断链 |
| 模板、字段和完成口径不一致 | 多次执行或更换执行主体后产生漂移 |
| 简单与复杂工作使用同一固定深度 | 一边增加形式负担，一边遗漏真实风险 |
| 通用规则与项目规则混杂 | 难以复用、更新和验证 |

## 2. 建设目标

- 统一术语、Artifact、引用、Evidence、Exception 和 Gate；
- 用统一 Project Context 保存项目级共享基线，并由各 Lifecycle Artifact 绑定准确 Revision；
- 固定各 Lifecycle Phase 的输入、输出和衔接条件；
- 允许按事实裁剪，但对 `n/a` 与 `waived` 保留明确依据；
- 让人工、AI 或其他执行主体使用同一套完成标准；
- 用最少结构保证结果可读、可追踪、可验证。

## 3. 生命周期控制流

```text
REQ → DSN → PLN → IMP → VFY → RLS
```

这是一条 Artifact 与 Gate 控制流，不表示活动只能线性执行一次。活动可以并行、迭代或返回上游；每个位置仍需作出明确 Disposition。

Lifecycle Profile 使用 `full / lite / hotfix` 提供默认建议，实际执行由 `required / embedded / n/a / waived / pending` 决定。Profile 不直接跳过 Phase。

## 4. 体系边界

| 层次 | 负责内容 |
|---|---|
| Core Spec | 通用术语、身份、Revision、状态、引用、Evidence、Exception、Disposition 和 Gate |
| Artifact Store Spec | Artifact Lineage、完整 Canonical Revision Payload、Revision 持久化与准确解析 |
| Project Context Spec | Lifecycle 前置的项目身份、资源、技术、结构、规则、环境和约束基线 |
| Phase Spec | 当前 Phase 的固定模板、专属字段、适用规则和增量 Check |
| 执行支持 | 模板生成、提示、检查和快捷入口；可以由人工或工具使用 |

Core、Project Context、Phase 和适用 Domain Spec 是合规依据；执行支持只降低使用门槛，不能改变 Contract。

## 5. v1.1 Artifact 导航

v1.1 只解除 Canonical Artifact Authority 与固定物理存储布局的耦合，Artifact 继续是具有稳定 ID、Revision、Status、Reference、Check 和 Gate 的逻辑对象。

Artifact Store 负责 Revision 的逻辑持久化、读回与准确解析。一个 Canonical Revision Payload 包含 primary Canonical Blob 及 locally owned Member 的完整闭包，并通过既有 Manifest 和逐 Member 摘要保持一致；外部不可变 Reference 继续按其访问边界引用。

领域 Spec 不规定 SQLite Schema 或其他具体存储实现数据结构。Human Review View 属于执行支持，只便于人工阅读和候选修改，不是正式 Artifact Authority。

## 6. 核心原则

| 原则 | 要求 |
|---|---|
| 执行主体中立 | 不以是否使用 AI 判断合规，只检查产物、证据和 Gate |
| 固定接口 | Markdown 章节、字段、枚举和引用语法保持稳定 |
| 按事实裁剪 | 不适用必须有原因，适用但跳过必须有授权 Exception |
| 单一权威 | 同一事实只由一个字段或 Artifact 承载，其他位置只引用 |
| 风险负责 | 业务目标、主观判断、外部授权和风险接受由有责任的人工或外部权威承担；客观 Artifact 合规确认可按 Core 委托独立 Reviewer |
| 简约优先 | 现有结构能够闭合的问题不新增 Phase、Artifact、状态或抽象 |

## 7. 规范组成

| 组成 | 作用 |
|---|---|
| Core Spec | 定义跨 Artifact 稳定的公共 Contract |
| Artifact Store Spec | 定义 Revision 的完整逻辑存储与准确解析边界 |
| Project Context Spec | 定义项目级共享基线及准确 Revision 绑定 |
| Phase Spec | 定义各 Lifecycle 控制位置的输入、模板、检查和 Gate |
| Domain Spec | 定义 DSN 中可按事实选择的领域设计 Contract |

## 8. 范围边界

本规范不规定具体模型、Agent、IDE、编程语言、框架、执行入口、物理存储实现或外部平台；长期 Operations 不作为每次变更的固定 Artifact Phase。工具可以实现本规范，但不能改变其字段、语义和 Gate。

## 9. 结论

> **Spec 统一输入、输出和完成标准；Project Context 提供项目基线；执行支持降低使用成本；Evidence 与 Gate 保证结果可复核。**

## 附件

- [AI 与人工协作建议](./ai-human-collaboration.md)
