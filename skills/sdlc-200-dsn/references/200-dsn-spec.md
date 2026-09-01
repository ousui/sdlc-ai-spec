---
title: Design Phase Spec
status: stable
version: "1.1"
scope: 已确认的 DSN 边界、结构与 Design Applicability Matrix
---

# Design Phase Spec

## Phase 目标

DSN 将已确认的 Requirement 转换为可实施、可验证的设计结果。

DSN 不是单指架构设计、概要设计或详细设计，而是这些设计活动的统一承载 Phase。它负责提前发现问题、明确边界、记录设计选择，并防止后续实施偏离 Requirement。

DSN 是高判断密度的 Phase，但 Spec 不限定由人工还是 AI 生成设计。关键选择、边界与风险由具备相应权限的决策者负责；Final Confirmation 只确认当前 Artifact 与 Gate，是否逐项阅读不改变决策责任。

## Phase 边界

DSN 负责：

- 将 Requirement 映射为明确的设计边界；
- 记录关键 Design Decision、候选方案和选择依据；
- 判断全部注册 Design Domain 的适用性；
- 形成可以被 PLN、IMP 和 VFY 使用的设计结果；
- 发现 Requirement 中的缺失、冲突或不可实现内容。

DSN 不负责：

- 静默修改 Requirement 目标、范围或 Acceptance Criteria；
- 拆分具体实施任务或制定执行排期；
- 编写实现代码；
- 给出最终交付结论。

发现 Requirement 存在问题时，必须返回 REQ，不能在 DSN 中自行改变业务语义。

## Artifact 关系

DSN 不强制一项 Requirement 对应一个 Design。

```text
一个 REQ → 多个 DSN
多个 REQ → 一个共享 DSN
多个 REQ → 多个 DSN
```

创建独立 DSN Artifact 的判断依据：

- 具有独立设计边界；
- 可以独立评审和确认；
- 可能独立修改或复用；
- 具有独立 Design Result 和 Gate。

仅仅因为存在多个 Design Domain，不需要拆成多个 DSN Artifact。

## Front Matter

```yaml
---
contract: sdlc-ai-spec/artifact/v1
phase: DSN
id: DSN-20260823150010-01
revision: 1
status: draft
context: CTX-20260828143025-01@1
profile: full
inputs:
  - REQ-20260823143025-01@1
---
```

DSN 必须至少绑定一个准确的 Requirement Revision。输入为 `ready_with_exception` 时，DSN 必须处理与当前 Scope 相交的未关闭 Exception：在当前 Artifact 的 Exceptions 中记为 `carried`，或用 Evidence 证明不相交、已 `resolved` / `superseded`；无法判断时仍按相关处理。

- `Return Phase=DSN` 的冻结 VFY Return，以及 Follow-up Disposition 为 `return_dsn` 的冻结 RLS Issue Reference，是 Control Input，不是 Scope Input；其所属 Revision 必须进入 Front Matter `inputs`；
- Control Input 不自动改变 Design Scope。实际修正必须由受影响的 Change、Decision、Domain 设计或 Evidence 准确引用；确认需要改变 Requirement 或 Delivery Scope 时返回 REQ；
- 新 DSN Revision 只证明问题已在设计层处理；只有后续冻结 VFY Revision 采用修正后的当前 Subject 并证明对应 Required Outcome 后，该问题才算解决。

## 固定模板

DSN 使用“主设计总纲 + required Domain Member”的 Artifact Set。primary Canonical Blob 是唯一总览和 Gate；Domain Member 只承载该领域的详细设计。

```markdown
# <设计标题>

## 摘要 Summary

## 范围 Scope

## 设计基线与变更 Design Baseline and Change

## 需求追踪 Requirement Traceability

## 设计决策 Design Decisions

## 设计总纲 Design Index

<固定 16 行 Design Applicability Matrix>

### 复合 Domain 子领域适用性 Composite Domain Subdomain Applicability

<固定 5 行 Composite Domain Subdomain Applicability>

## 产物集清单 Artifact Set Manifest

## 待确认项 Open Items

## 证据 Evidence

## 豁免 Exceptions

## 生命周期适用性 Lifecycle Applicability

## 门禁 Gate
```

推荐阅读顺序为：摘要与边界 → 基线与变化 → 决策 → 16 行 Domain Matrix 与 5 行复合 Domain 子领域表 → 按需打开 required Domain Member → Gate。

参与者可以按需要选择阅读 Domain Member；未逐项阅读不改变 Domain 的适用性、完成状态和最终确认责任。

## DSN Artifact Set

一个 DSN Revision 是一个完整 Canonical Revision Payload：

- 使用本 Spec 固定模板的主 Design primary Canonical Blob 原始字节；
- Matrix 中全部 `required` Domain 的 locally owned Domain Member 原始字节；
- 当前 Store 本地保存的全部 Supporting Member 原始字节；
- 每个 Member 的稳定 `DOM-*` 或 `SUP-*` 身份；
- 每个 Member 的 Canonical Member Name、Media Type 和 SHA-256；
- 既有 Artifact Set Manifest 内容，并且与实际本地 Member 集合形成唯一 Manifest-Member closure。

规则：

- primary Canonical Blob 是唯一主要 Artifact、总纲、索引和 Gate；
- 只为 `required` Domain 创建 Domain Member；当前内置 Spec 不开放 Domain `embedded`；
- Domain Member 属于父 DSN Artifact Set，不分配独立 Artifact ID 或 Revision；
- Domain Member 的语义变化触发父 DSN Revision 变化；
- Domain 固定文件名继续作为 Canonical Member Name；图片、图表、Schema 和其他原生内容使用稳定 Canonical Member Name，并由 Domain Member 引用；
- Domain 如果需要独立复用、评审或 Revision，应创建新的 DSN Artifact；
- Artifact Set Manifest 必须列出全部本地 Domain Member 和 Supporting Member，并固定稳定身份、Canonical Member Name、Media Type 与原始字节 SHA-256；
- 外部不可变 Reference 不要求复制为本地 Member，但其准确 Reference、摘要和访问边界必须保留；
- Gate 结果只保存在 primary Canonical Blob；open Revision 直接重跑，frozen Revision 按 Core 创建新 Revision。

## 核心章节

以下章节不得删除或标记为 `n/a`：Summary、Scope、Design Baseline and Change、Requirement Traceability、Design Index、Artifact Set Manifest、Open Items、Evidence、Exceptions、Lifecycle Applicability 和 Gate。

Design Decisions 没有条目时固定写作 `None — <客观原因>`；不得为满足模板虚构决策。Core 已定义空行的章节继续使用 Core 空表示。

## Design Baseline and Change

DSN 必须明确当前状态、目标状态和两者之间的设计变化，避免 PLN、IMP 或 VFY 重新猜测范围。

```markdown
| Change Type | Current Baseline References | Target State Summary | Impact Summary |
|---|---|---|---|
| incremental | | | |

| Change ID | Object or Boundary | Change | Baseline References | Baseline State | Target State | Affected Domains |
|---|---|---|---|---|---|---|
| CHG-001 | | modify | | | | |
```

规则：

- `Change Type` 使用 `new`、`incremental` 或 `reuse`；
- `Change` 使用 `add`、`modify`、`remove` 或 `reuse`；
- `new` 可以将 Current Baseline 标记为 `N/A`，但必须说明不存在有效基线的原因；
- `incremental` 的 Baseline 与 Change Set 必须足以还原 Target State；
- `reuse` 必须引用准确基线，并记录其对当前 Requirement 的适配结论和 Evidence；
- Baseline 必须从 Front Matter 绑定的 CTX Revision 解析适用 Resource、Component、Rule、Environment 和 Constraint；版本化产品内容的具体状态使用不可变 Artifact Reference、Core VCS Locator 或 Evidence，任何可移动引用都无效；
- 当前 Scope 内的 Change Set 必须完整枚举，未列入 Change Set 的 Baseline 内容保持不变；
- `Scope + Baseline + Change Set` 必须唯一确定 Target State；
- `Target State Summary` 只是该唯一结果的阅读摘要，不是独立权威来源；多个 DSN 的 Target State 共同进入 Delivery Scope 时必须可共同成立，冲突进入阻塞 Open Item；
- `Impact Summary` 是 Change Set 与 Matrix 的阅读摘要，不得引入新的影响；
- Change Set 只描述设计对象和变化，不包含任务、顺序、工期或实施负责人；
- 两处 `Affected Domains` 都使用固定 Catalog Code `DOM-<DOMAIN-NO>`，按 Design Index 顺序以 `, ` 分隔；该字段是分类集合，不是 Member Reference。只有 `required` Domain 的内容位置才使用完整 `DSN-ID@Revision/DOM-<DOMAIN-NO>`；
- 当 DSN 是直接 Binding 来源、建议 `PLN=n/a/waived` 且 `IMP=required` 时，每个 Change Item 的 `Object or Boundary` 使用 PLN Scope Token；全部 Change Item 的并集只能包含一个 `resource:<versioned-resource-id>`，否则 PLN 必须为 `required`。

## Requirement Traceability

```markdown
| Source References | Design Item or Member References | Decision References | VFY Point or Objective References | N/A Reason |
|---|---|---|---|---|
| REQ-...@1#R-001 | DSN-...@1#CHG-001 | DEC-001 | VFP-230-001 | N/A |
```

规则：

- 当前 DSN Scope 内的每个 Requirement Item 必须至少关联一个稳定 Design Item 或 Member Reference；
- 当前 Scope 内的每个 Acceptance Criterion 必须映射到 Design Item 和后续 VFY Objective；无需独立 Design Item 时填写准确 `N/A Reason`，但仍须映射 VFY Objective；
- 多值字段使用 Core Reference Set；跨 Artifact 引用使用准确 `Artifact ID@Revision#Item ID`；
- Design Item、Decision 和 VFY Point 必须能够反向查到 Requirement、Acceptance Criterion、Goal、约束或准确 Baseline；
- 无上游来源或 Baseline 依据的孤立设计内容不能通过 Gate；
- DSN 不得创建未经 REQ 确认的新业务规则。

## Design Decisions

```markdown
| ID | Requirement or Constraint References | 决策问题 Decision Question | 候选方案 Options | 选择结果 Decision | 选择依据 Rationale | 影响 Domain Affected Domains |
|---|---|---|---|---|---|---|
| DEC-001 | | | | | | |
```

规则：

- Design Decision 使用 `DEC-001` 顺序编号；
- 不得只写最终方案而不记录选择依据；
- 强制约束必须引用 Requirement 或 Evidence，设计偏好不得伪装成 Requirement；
- 技术选型统一记录为 Design Decision，并由受影响 Domain 引用同一个 `DEC-ID`；
- 项目规范已经强制指定的技术属于既有约束，只需准确引用；
- Design Pattern 不是独立 Domain；只有改变系统、组件、稳定 Contract、扩展点或质量属性时才记录为 Decision；
- 局部、可逆且不影响稳定边界或质量属性的实现方式留给 IMP；
- 存在直接实现时，应将其作为候选方案；选择更复杂方案时必须说明直接实现为何不足以及新增代价；
- 只有存在真实选择时才创建 Decision；
- 一个 DSN Artifact 至少包含一个可追踪 Design Result。若 REQ 与准确 Baseline 已完整确定结果且不存在设计义务，DSN 应为 `n/a`，不创建空 DSN。

## Scope and Simplicity

- 每项设计内容必须追踪到 Requirement、准确 Baseline 或已确认约束；
- 不得增加未被要求的功能、配置能力、扩展点或抽象层；
- 不得顺手重构、替换或优化范围外内容；
- 相邻问题只有阻塞当前目标或改变当前风险时才进入当前 DSN，否则只报告；
- 歧义、缺失或多种合理解释必须显式记录，不得静默选择后扩张；
- 采用比直接实现更复杂的方案时，必须说明简单方案为何不足；
- 每项关键 Design Decision 必须具有对应 VFY Point；
- 最小设计是满足 Requirement 和适用质量约束的最小充分设计，不表示省略必要的安全、可靠性或验证工作。

## 设计适用性矩阵 Design Applicability Matrix

primary Canonical Blob 必须保留下列 16 行，顺序、中文名称和英文标准名称不得改变。

| 分组 Group | 设计领域 Design Domain | 处置 Disposition | 完成状态 Completion | 责任角色 Responsible Role | 内容引用 Content Reference | 适用性依据引用 Applicability Basis References | 不适用或豁免说明 N/A or Waiver Reason |
|---|---|---|---|---|---|---|---|
| 行为设计 Behavior | 流程与状态 Workflow and State | pending | not_started | | N/A | | Pending |
| 行为设计 Behavior | 用户体验与交互 UX and Interaction | pending | not_started | | N/A | | Pending |
| 行为设计 Behavior | 界面与内容 UI and Content | pending | not_started | | N/A | | Pending |
| 行为设计 Behavior | 可访问性与国际化 Accessibility and Internationalization | pending | not_started | | N/A | | Pending |
| 技术设计 Technical | 系统与架构 System and Architecture | pending | not_started | | N/A | | Pending |
| 技术设计 Technical | 组件与模块 Components and Modules | pending | not_started | | N/A | | Pending |
| 技术设计 Technical | 接口与集成 Interfaces and Integration | pending | not_started | | N/A | | Pending |
| 技术设计 Technical | 数据设计 Data Design | pending | not_started | | N/A | | Pending |
| 质量属性 Quality | 安全、隐私与合规 Security, Privacy and Compliance | pending | not_started | | N/A | | Pending |
| 质量属性 Quality | 性能与容量 Performance and Capacity | pending | not_started | | N/A | | Pending |
| 质量属性 Quality | 可靠性与恢复 Reliability and Recovery | pending | not_started | | N/A | | Pending |
| 质量属性 Quality | 兼容与迁移 Compatibility and Migration | pending | not_started | | N/A | | Pending |
| 质量属性 Quality | 可维护性与扩展性 Maintainability and Extensibility | pending | not_started | | N/A | | Pending |
| 运行设计 Operations | 部署与配置 Deployment and Configuration | pending | not_started | | N/A | | Pending |
| 运行设计 Operations | 可观测性与可运维性 Observability and Operability | pending | not_started | | N/A | | Pending |
| 验证设计 Verification | 可验证性与 VFY 策略 Verifiability and VFY Strategy | pending | not_started | | N/A | | Pending |

### Disposition 与 Completion

当前 Artifact Contract 的 Domain Disposition 只允许 `required`、`n/a`、`waived` 或 `pending`。不开放 `embedded`，避免跨 Member Host、内容摘要和 primary Blob 摘要形成循环；确需复用既有设计时，通过 Baseline Reference 减少重复内容，但只要当前变化仍有设计义务，该 Domain 就是 `required`。

| Disposition | 使用条件 | Completion | Content Reference | 说明字段 |
|---|---|---|---|---|
| `pending` | 事实不足，暂不能判断 | `not_started` | `N/A` | `Pending — <OPI-ID>` |
| `required` | 当前变化存在该领域设计义务 | `not_started` / `in_progress` / `complete` | 完整 `DSN-ID@Revision/DOM-<DOMAIN-NO>` | `N/A` |
| `n/a` | 当前变化客观不存在该领域义务 | `not_applicable` | `N/A` | 客观原因 |
| `waived` | 义务存在但经授权不执行 | `waived` | `N/A` | 有效 `EX-ID` 与原因 |

规则：

- 必须按 Core 固定顺序判断 Disposition，不能因为工作量小、不熟悉或不准备阅读而判定 `n/a`；
- `required` 无 Domain Member 时为 `not_started`，Member 已创建但内容或父 Gate 子检查未完成时为 `in_progress`，全部完成且子检查通过时为 `complete`；
- `n/a` 必须有准确 Basis Reference 和客观原因；
- `waived` 必须引用父 DSN Exceptions 中有效的 `active` 或 `carried` Exception；
- `pending` 必须引用 Open Item，不能通过 Gate；
- Responsible Role 只在 `required` 时必填，表示确保内容完整的责任，不规定实际作者；
- 不得创建未注册 Domain、自由增列或删除固定行；无法映射的关注进入阻塞 Open Item；
- Matrix 是顶层 Domain 适用性和完成状态的唯一权威；顶层原因、Exception 和 Content Reference 不在其他控制表重复登记。140 与 310 的子领域处置只保存在紧随 Matrix 的固定 Composite Domain Subdomain Applicability 表，不在 Domain Member 重复。

### 复合 Domain 子领域适用性 Composite Domain Subdomain Applicability

primary Canonical Blob 固定保留下列 5 行，使 140 和 310 即使聚合为 `n/a`、`waived` 或 `pending`，逐子领域判断仍可复核。

| 复合 Domain 分类码 Composite Domain Catalog Code | 子领域 Subdomain | Disposition | Applicability Basis References | 不适用、豁免或待确认说明 N/A, Waiver or Pending Reason | Exception References |
|---|---|---|---|---|---|
| DOM-140 | 可访问性 Accessibility | pending | | Pending — <OPI-ID> | N/A |
| DOM-140 | 国际化 Internationalization | pending | | Pending — <OPI-ID> | N/A |
| DOM-310 | 安全 Security | pending | | Pending — <OPI-ID> | N/A |
| DOM-310 | 隐私 Privacy | pending | | Pending — <OPI-ID> | N/A |
| DOM-310 | 合规 Compliance | pending | | Pending — <OPI-ID> | N/A |

规则：

- 行、名称和顺序固定，不得删除、重排或拆成多个表；
- Disposition 只使用 `required`、`n/a`、`waived` 或 `pending`；
- `required` 必须填写准确 Basis，说明写 `N/A`，Exception 写 `None`；
- `n/a` 必须填写准确 Basis 与客观原因，Exception 写 `N/A`；
- `waived` 必须填写准确 Basis、原因和父 DSN 中有效的 Exception Reference；
- `pending` 必须引用阻塞 Open Item，不能通过 Gate；
- DOM-140 和 DOM-310 的顶层 Matrix Disposition 分别由其固定行按 `pending → required → waived → n/a` 取第一个满足的结果；子领域 Waiver 即使未成为顶层 Disposition，仍必须传播到父 Exceptions。只有不存在 `fail`、`pending` 且其他必要 Check 均已关闭时，父 Artifact 才按 Core 由该未关闭 Exception 派生 `ready_with_exception`。

## 产物集清单 Artifact Set Manifest

Artifact Set Manifest 是 Core Supporting Artifact Manifest 的 DSN 扩展，不再另建第二份清单。

```markdown
| Member ID | Type | Domain | Domain Spec Reference or Digest | Path or Reference | Media Type | Purpose | SHA-256 Digest | Empty Reason |
|---|---|---|---|---|---|---|---|---|
| DOM-110 | domain | Workflow and State | docs/v1.1/200-dsn-domains/110-workflow-state.md@sha256:816a9c5144fa2980e5d9675c6b74bed74a7bb07c9cacab655a9ce57c64790f0c | domains/110-workflow-state.md | text/markdown | Domain Design | | N/A |
| SUP-001 | supporting | Multiple | N/A | assets/flow.svg | image/svg+xml | Design Diagram | | N/A |
```

规则：

- Manifest 只登记 primary Canonical Blob 以外的真实 Member；
- required Domain 使用固定 `DOM-<DOMAIN-NO>`，Supporting Member 使用 `SUP-001` 顺序编号；
- Domain Member 必须填写对应 Domain Spec Reference；其他 Member 填 `N/A`；
- `Path or Reference` 对本地 Member 保存 Canonical Member Name，对外部成员保存准确不可变 Reference；它不提供物理 Artifact Authority；
- `SHA-256 Digest` 对成员原始字节计算；父 Artifact 的 Core Control Input Digest 通过 Manifest 绑定全部成员；
- frozen Revision 的成员关系、稳定身份、Canonical Member Name、Media Type、Domain Spec 和摘要必须固定；
- Manifest 声明集合必须与实际 locally owned Member 集合完全一致；Member 缺失、未登记、ID 重复或摘要不匹配时整个 Revision 解析失败；
- 无成员时使用 Core 空清单规则。由于存在 DSN 时 Verifiability Domain 固定为 required，DSN Artifact Set 至少包含一个 Domain Member。

## Domain Member

每个 `required` Domain 使用相同外壳，Domain Spec 只定义 `Design Result` 内的固定专属表格和规则。

```markdown
# <中文名称 English Name>

| 关联项 Relation | 值 Value |
|---|---|
| 父 DSN ID Parent DSN ID | DSN-... |
| Requirement References | REQ-...@1#R-001 |
| Decision References | DEC-001 |

<当前 Domain Spec 的固定专属模板，从 `## 设计结果 Design Result` 开始>

## 约束与影响 Constraints and Impact

| ID | 类型 Type | 内容 Content | 影响的下游 Phase Affected Downstream Phase | Reference |
|---|---|---|---|---|
| CIM-<DOMAIN-NO>-001 | constraint | | IMP | |

以下 `VFY Points` 区块只适用于 110 至 420 Domain。510 已在专属 `VFY Objectives` 中直接汇总其他 required Domain 的 VFY Points，不再创建重复的 `VFP-510-*`。

## VFY 要点 VFY Points

| ID | Requirement, AC or Design References | 验证对象 Verification Object | 可观察结果 Observable Result | 预期 Evidence Expected Evidence |
|---|---|---|---|---|
| VFP-<DOMAIN-NO>-001 | | | | |

## 证据引用 Evidence References

| Evidence or Member Reference | Supports Item References | Purpose |
|---|---|---|
| None | N/A | No domain-specific Evidence references |
```

规则：

- 只创建 Matrix 中 `required` 的 Domain Member；`n/a`、`waived` 和 `pending` 不创建；
- Domain Member 按照 Matrix 固定编号和 Canonical Member Name；
- Domain Member 不得重复 Summary、Scope、候选方案、Open Items、Exceptions 或 Gate；
- 候选方案与选择依据只记录在父 primary Canonical Blob 的 Design Decisions；
- Domain Member 必须记录稳定父 `DSN-ID`，准确 Revision 和成员摘要由 Manifest 绑定；
- Relation 中的复数字段使用 Core Reference Set；没有 Design Decision 时 `Decision References` 写 `None`；
- Domain Item ID 在父 Artifact Set 内必须唯一；跨 Artifact 引用使用完整 `DSN-ID@Revision#Item-ID`；
- 110 至 420 Domain 的 VFY Point 使用 `VFP-<DOMAIN-NO>-<NNN>`；只描述需要观察的结果，不提前指定测试工具和执行计划；510 不创建 `VFP-510-*`；
- Evidence 只保存在父 DSN Evidence 表或 Supporting Member，Domain Member 仅引用，不复制 Evidence 元数据；
- 没有 Domain 专属 Evidence 引用时只保留固定 `None` 行；存在引用时删除该行；
- Domain 整体 required 但某个固定子章节不适用时保留标题并写 `N/A — <客观原因>`；不得保留空白占位行；
- 140 与 310 是复合 Domain。逐子领域处置始终保存在父 primary Canonical Blob 的固定 Composite Domain Subdomain Applicability 表；顶层为 `required` 时创建一个 Domain Member 承载详细设计，其他处置不创建 Member。

### 复合 Domain 子领域规则

140 与 310 的固定 Subdomain 只在父 primary Canonical Blob 表中判断和聚合，不创建子领域 Artifact、Gate、摘要或历史记录。顶层为 `required` 时，同一个 Domain Member 只填写实际 required 的详细设计；`n/a` 或 `waived` 子领域对应的固定章节按统一 `N/A — <客观原因或 Exception>` 表示，不重复处置字段。

## 核心 Domain 子规范

| 顺序 Order | 分组 Group | 设计领域 Design Domain | 子规范 Domain Spec |
|---|---|---|---|
| 110 | 行为设计 Behavior | 流程与状态 Workflow and State | [110-workflow-state.md](200-dsn-domains/110-workflow-state.md) |
| 120 | 行为设计 Behavior | 用户体验与交互 UX and Interaction | [120-ux-interaction.md](200-dsn-domains/120-ux-interaction.md) |
| 130 | 行为设计 Behavior | 界面与内容 UI and Content | [130-ui-content.md](200-dsn-domains/130-ui-content.md) |
| 140 | 行为设计 Behavior | 可访问性与国际化 Accessibility and Internationalization | [140-accessibility-i18n.md](200-dsn-domains/140-accessibility-i18n.md) |
| 210 | 技术设计 Technical | 系统与架构 System and Architecture | [210-system-architecture.md](200-dsn-domains/210-system-architecture.md) |
| 220 | 技术设计 Technical | 组件与模块 Components and Modules | [220-components-modules.md](200-dsn-domains/220-components-modules.md) |
| 230 | 技术设计 Technical | 接口与集成 Interfaces and Integration | [230-interfaces-integration.md](200-dsn-domains/230-interfaces-integration.md) |
| 240 | 技术设计 Technical | 数据设计 Data Design | [240-data-design.md](200-dsn-domains/240-data-design.md) |
| 310 | 质量属性 Quality | 安全、隐私与合规 Security, Privacy and Compliance | [310-security-privacy-compliance.md](200-dsn-domains/310-security-privacy-compliance.md) |
| 320 | 质量属性 Quality | 性能与容量 Performance and Capacity | [320-performance-capacity.md](200-dsn-domains/320-performance-capacity.md) |
| 330 | 质量属性 Quality | 可靠性与恢复 Reliability and Recovery | [330-reliability-recovery.md](200-dsn-domains/330-reliability-recovery.md) |
| 340 | 质量属性 Quality | 兼容与迁移 Compatibility and Migration | [340-compatibility-migration.md](200-dsn-domains/340-compatibility-migration.md) |
| 350 | 质量属性 Quality | 可维护性与扩展性 Maintainability and Extensibility | [350-maintainability-extensibility.md](200-dsn-domains/350-maintainability-extensibility.md) |
| 410 | 运行设计 Operations | 部署与配置 Deployment and Configuration | [410-deployment-configuration.md](200-dsn-domains/410-deployment-configuration.md) |
| 420 | 运行设计 Operations | 可观测性与可运维性 Observability and Operability | [420-observability-operability.md](200-dsn-domains/420-observability-operability.md) |
| 510 | 验证设计 Verification | 可验证性与 VFY 策略 Verifiability and VFY Strategy | [510-verifiability-vfy-strategy.md](200-dsn-domains/510-verifiability-vfy-strategy.md) |

所有子规范受本文件的 Scope、Disposition、Matrix、Artifact Set 和父 Gate 约束。最终 Evaluation Contract Set 绑定 Core Spec、Artifact Store Spec、DSN Spec 和 16 个 Domain Spec，确保 required、n/a 与 waived 使用同一组适用性规则。

## DSN 最终化顺序

DSN 使用 Core Revision 和 Gate 机制完成重跑，不保存 Phase 内的 Attempt 历史：

1. 完成本次 Scope、Baseline、Change、Decision 和 Requirement Traceability；
2. 按固定顺序判断 16 个 Domain 的 Disposition；先填写 140、310 的 5 行子领域表并聚合对应顶层结果，再完成 Matrix；
3. 只创建 required Domain Member，完成其 Design Result、Constraints and Impact 与 Evidence References；110 至 420 Domain 另外完成 VFY Points，510 以 VFY Objectives 作为汇总结果；
4. 刷新 Artifact Set Manifest，验证每个 Member SHA-256 和 Manifest-Member closure，并通过 `write open revision` 原子持久化 primary Blob、全部本地 Member、元数据与 Manifest，再以 `read revision` 读回；
5. 在父 Gate 中依次登记 Core Check、DSN Check，以及每个 required Domain Spec 的全部子检查；每个 Check ID 只出现一次；
6. 按 Core 计算 Control Input Digest 与 Check Set Result Digest，完成 Final Confirmation，聚合唯一 Artifact Gate Summary 并派生 Status；
7. 内容或规则变化时，open Revision 直接重跑；ready / ready_with_exception 已冻结后按 Core 创建新 Revision。父 Gate、Final Confirmation 与完整 Payload 全部一致后才执行 `freeze revision`。

## Lifecycle Applicability

```markdown
| Phase | Disposition | Host | 判断依据 Basis |
|---|---|---|---|
| PLN | pending | N/A | Pending — <OPI-ID> |
| IMP | pending | N/A | Pending — <OPI-ID> |
| VFY | required | N/A | VFY Artifact 为固定控制点 |
| RLS | pending | N/A | Pending — <OPI-ID> |
```

该表只记录当前 DSN Scope 对后续 Phase 的建议，不负责排期和任务分配。多个完整 Scope Input 共同交付时，按 Core Delivery Scope Aggregation Contract 执行，并将 PLN 标记为 `required`。

## AI 与人工协作 AI and Human Collaboration

本节是 Phase 执行指导，不进入 DSN Artifact 模板，也不作为 Gate 或 AI 使用率指标。

| 工作 Activity | AI 适合做什么 | 人工适合做什么 | 原因 Reason |
|---|---|---|---|
| Baseline 与 Domain 分析 | 发现现状、影响范围和跨 Domain 关系 | 确认关键现状和业务限制 | AI 擅长全量关联，人工掌握隐含约束 |
| 方案与影响比较 | 生成候选、分析一致性和代价 | 决定架构、接口、数据和体验取舍 | 关键设计决定需要权威与责任 |
| 详细设计 | 按 required Domain 模板形成可追踪设计 | 重点评审高风险或主观领域 | AI 提高完整度，人工校准方向和风险 |
| Gate 与缺口检查 | 检查追踪、冲突、VFY Point 和复杂度；满足 delegated 边界时执行独立客观复核 | 作出设计取舍并确认 Exception 与风险 | Final Confirmation 不替代权威设计或风险决策 |

## Gate

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-G-001 | Scope Input 至少包含一个准确 Requirement Revision，VFY Return 与 `return_dsn` RLS Issue Reference 已准确承接，且 Design Scope 与 Control Input 一致 | pending | |
| DSN-G-002 | Design Boundary、Current Baseline、Target State 和 Change Set 完整且可还原 | pending | |
| DSN-G-003 | 当前 DSN Scope 内的 Requirement、Acceptance Criteria、Design Item、Decision 与 VFY Objective 双向可追踪，不存在孤立项或静默修改 | pending | |
| DSN-G-004 | Summary、Design Decisions、Matrix 与 Domain 设计结果一致，不存在重复权威来源 | pending | |
| DSN-G-005 | 16 个 Domain 均已依据其 Spec 判断 Disposition，不存在 pending 或未注册 Domain | pending | |
| DSN-G-006 | required Domain 均有唯一 Domain Member、稳定身份、原始字节、Media Type、摘要和 Manifest 闭包；n/a 与 waived 均有有效依据 | pending | |
| DSN-G-007 | 复合 Domain 的固定子领域表与父 Matrix、Exception 一致 | pending | |
| DSN-G-008 | 各 Design Domain 不存在冲突、重复定义或相互矛盾的边界 | pending | |
| DSN-G-009 | 所有设计均在当前范围内，复杂度必要，未引入推测性能力或未授权相邻改动 | pending | |
| DSN-G-010 | Lifecycle Applicability、Host、Basis 和已注册 Host Contract 完整一致 | pending | |

<按 Design Applicability Matrix 固定顺序，展开每个 required Domain Spec 注册的 DSN-DG-<DOMAIN-NO>-<CHECK-NO> 行>
```

Artifact Gate 先包含 Core Gate Checks，再包含 DSN Gate Checks，随后只展开 required Domain 的子检查，最后按 Core 保存 Final Confirmation 和唯一 Artifact Gate Summary。

规则：

- Domain 子检查是父 Artifact Gate 的普通 subordinate rows，不是独立 Gate；
- 每个适用 Check ID 在当前 Revision 只登记一次，不创建平行记录或历史编号；
- Domain 子检查使用与父 Gate 相同的 `Result` 和 `Evidence or Notes` 字段；
- open Revision 重跑时直接刷新当前 Check 结果；frozen Revision 的任何变化都创建新 Revision；
- 父 Gate 严格按 Core 固定优先级聚合：任一 required Domain 子检查为 `fail` 时结果为 `fail`；不存在 `fail` 但仍有 `pending` 时结果为 `pending`；全部必要 Check 关闭后才按未关闭 Exception 派生 `pass` 或 `pass_with_exception`；
- `waived` 只通过 Matrix 与父 Exceptions 表表达，Contract Integrity Check 仍必须实际执行；
- Final Confirmation 和 Artifact Gate Summary 绑定 Core 定义的同一 Control Input Digest、Evaluation Contract Set、Check Set Result Digest 和未关闭 Exception 集合。

## 内部编号

| 内容 Item | 格式 Format |
|---|---|
| Change Item | `CHG-001` |
| Design Decision | `DEC-001` |
| Domain Constraint or Impact | `CIM-<DOMAIN-NO>-001` |
| Domain VFY Point | `VFP-<DOMAIN-NO>-001` |
| Open Item | `OPI-001` |
| Evidence | `EVD-001` |
| Exception | `EX-001` |
| DSN Gate Check | `DSN-G-001` |
| Domain Subordinate Check | `DSN-DG-<DOMAIN-NO>-001` |
