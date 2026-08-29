---
title: Plan Phase Spec
status: stable
version: "1.1"
scope: 已确认的 PLN 边界、Delivery Scope 与 Work Item Contract
---

# Plan Phase Spec

## Phase 目标

PLN 将已确认的交付范围和设计结果转换为可执行、可追踪、可验证的交付执行计划。

PLN 中的一份 Plan Artifact 表示完整计划；`Work Item` 表示计划内最小的、可执行且可独立确认完成的工作单元。PLN 不等同于单个 Work Item，也不表示战略规划或完整项目管理计划。

## Phase 边界

PLN 负责：

- 确认本次 Delivery Scope；
- 聚合上游对后续 Phase 的 Applicability 建议；
- 把纳入范围的变化、验证和交付义务转换为 Work Item；
- 明确 Work Item 的来源、执行范围、约束、依赖、完成条件、预期 Evidence 和责任角色；
- 为下游 Artifact 提供稳定的 Work Item Reference。

PLN 不负责：

- 新增或改变 Requirement；
- 补造 DSN 中缺失的设计或技术选择；
- 执行实现、验证或发版工作；
- 保存 Work Item 的实时执行状态；
- 强制定义工期、排期、预算、人员或外部跟踪对象。

发现上游范围、设计或 VFY 目标不足时，必须返回对应 Phase 形成新 Revision，不能在 Work Item 中静默补充。

## PLN Applicability

PLN Disposition 按 Core 固定顺序判断，并使用以下 Phase 专属条件：

| Disposition | PLN 条件 |
|---|---|
| `required` | Core 要求 Delivery Scope Aggregation；或存在多个独立变化范围；或两个以上下游结果之间的依赖、顺序、冲突、角色或环境交接必须显式记录；或约束与 Exception 必须分配到具体工作 |
| `embedded` | 已注册且可解析的 Host 已实际承载 PLN 结果 Contract、覆盖关系和 Gate 所需 Evidence；Work Item 只描述未来工作，不能作为 Host。当前内置 Spec 未注册此类 Host |
| `n/a` | 不存在独立规划义务；若有实际实现，只允许一个完整直接 Input 和一个原子 Implementation Outcome，且不存在未满足的执行依赖，也不需要拆分、显式顺序、冲突协调或新的计划决策 |
| `waived` | 已确认存在独立规划义务，但经有效 Exception 授权不执行 |
| `pending` | 是否需要拆分、协调或独立计划的事实不足 |

- 按 Core 固定顺序得到最终 `required` 后才创建 PLN Artifact；命中规划义务但具有有效 Waiver 时仍为 `waived`；
- `n/a` 只表示不需要独立计划，不改变 IMP、VFY 或 RLS 的实际 Applicability；
- Profile 只能提供默认建议，不能直接决定 PLN Disposition；
- `n/a`、`embedded` 或 `waived` 时不创建独立 PLN Artifact，由最近的上游 Artifact Gate 验证其原因、Host 或 Exception。

## 输入与输出

| 类型 Type | 内容 Content |
|---|---|
| Input | 一个或多个可供下游使用的 REQ 或 DSN Scope Input、与当前计划修正相关的冻结 VFY Return 或 RLS Issue Reference，以及未关闭 Exception |
| Output | 一份固定 Markdown Plan Artifact，包含 Delivery Scope、Applicability 和 Work Items |

Scope Input 只允许准确的 REQ 或 DSN Artifact Revision，其 Lifecycle Disposition 链必须可解析：

- DSN 为 `required` 且已经形成 Artifact 时，PLN 引用 DSN，不重复把其已覆盖的 REQ 作为直接 Input；
- DSN 为 `n/a` 或没有独立 Artifact 的 `embedded` 时，PLN 可以直接引用保存该 Disposition 和 Host 的 REQ；
- 存在多个 Scope Input 时，必须按 Core Delivery Scope Aggregation Contract 执行聚合；当前 Artifact Contract 只纳入完整 Artifact，不在 PLN 选择部分 Item。
- `Return Phase=PLN` 的冻结 VFY Return，以及 Follow-up Disposition 为 `return_pln` 的冻结 RLS Issue Reference，是 Control Input，不是 Scope Input；其所属 Revision 必须进入 Front Matter `inputs`，但不得因此改变 Delivery Scope；
- 每个 PLN Control Input 必须由受影响 Work Item 的 `Source References` 或 `Constraint References` 准确引用；删除、合并或保留原 Work Item 时，还必须由 Evidence 引用该 Return 或 Issue Reference 并说明处理依据；
- 新 PLN Revision 只证明问题已在计划层处理。VFY Return 只有后续冻结 VFY 证明 Required Outcome 后才解决；RLS Issue 只有后续冻结 RLS 引用修订后的 Plan 并证明范围、顺序或协调结果已生效才解决，若同时改变产品则仍须先经过 IMP 与 VFY。

## Front Matter

```yaml
---
contract: sdlc-ai-spec/artifact/v1
phase: PLN
id: PLN-20260824103000-01
revision: 1
status: draft
context: CTX-20260828143025-01@1
profile: full
inputs:
  - DSN-20260823150010-01@1
---
```

## 固定模板

```markdown
# <计划标题>

## 摘要 Summary

## 范围 Scope

## 交付范围 Delivery Scope

## 聚合适用性 Aggregated Applicability

## 工作项 Work Items

## 待确认项 Open Items

## 证据 Evidence

## 支撑产物清单 Supporting Artifact Manifest

## 豁免 Exceptions

## 生命周期适用性 Lifecycle Applicability

## 门禁 Gate
```

各通用章节直接使用 Core Contract，不在 PLN 重复建立平行格式。

## Delivery Scope 与 Applicability

`Delivery Scope` 和 `Aggregated Applicability` 使用 Core 中的固定表格和聚合顺序。

- Work Item 只能覆盖 Delivery Scope 已纳入的内容；
- Aggregated Applicability 保存上游建议的确定性聚合结果；
- Lifecycle Applicability 保存 PLN 根据聚合结果和已确认规划事实作出的最终建议；
- 两者不一致时，必须在 Lifecycle Applicability 的 Basis 中引用新增事实；
- 上游 `embedded` Host 和 `waived` Exception 即使被更高优先级 Disposition 覆盖，也不得丢失；
- 任一必要结果为 `pending` 时，PLN 不能通过 Gate。

## Work Item Contract

Work Item 使用唯一固定表格：

```markdown
| ID | 目标 Phase Target Phase | 结果 Outcome | 执行范围 Execution Scope | 来源引用 Source References | 约束引用 Constraint References | 依赖 Depends On | 完成条件 Completion Criteria | 预期证据 Expected Evidence | 责任角色 Responsible Role |
|---|---|---|---|---|---|---|---|---|---|
| WI-001 | IMP | | | | None | None | | | |
```

### 字段规则

| 字段 Field | 规则 Rule |
|---|---|
| `ID` | 使用 `WI-001` 顺序编号，在当前 Plan Artifact 内唯一并跨 Revision 保持稳定 |
| `Target Phase` | 只允许一个 `IMP`、`VFY` 或 `RLS`；跨 Phase 的工作必须拆分，顺序固定为 `IMP < VFY < RLS` |
| `Outcome` | 描述完成后的可观察结果，不写宽泛目标或详细操作步骤 |
| `Execution Scope` | 使用固定 Scope Token 列出受影响范围；必须足以区分工作边界和识别潜在冲突 |
| `Source References` | 至少包含一个准确上游 Artifact 或 Item Reference；上游存在相关稳定 Item 时必须引用 Item，不得退化为模糊章节名 |
| `Constraint References` | 引用当前 Work Item 必须遵守的 Requirement、Decision、Constraint 或 Exception；没有时写 `None` |
| `Depends On` | 只引用同一 Plan 内相同或更早 Target Phase 的 Work Item ID；IMP Work Item 因此只能依赖 IMP Work Item；没有时写 `None` |
| `Completion Criteria` | 描述该 Work Item 自身可以判定的完成条件，不复制完整业务 Acceptance Criteria，也不能只写“已完成” |
| `Expected Evidence` | 描述完成后必须形成的可观察证据；实际 Evidence 由下游 Artifact 保存并反向引用当前 Work Item |
| `Responsible Role` | 填写对结果负责的角色，不在核心 Contract 中绑定具体人员 |

多值 Reference 使用 Core Reference Set 语法。`Depends On` 使用相同的 `, ` 分隔、去重和升序规则。

`Execution Scope` 的每个值固定为 `<type>:<project-local-identifier>`：

| Type | 用途 |
|---|---|
| `component` | 可独立变更或部署的组件、服务或应用 |
| `module` | 组件内部模块或功能边界 |
| `interface` | API、事件、协议或其他稳定接口 |
| `path` | 指定版本化资源内的文件或目录，格式为 `path:<resource-id>/<resource-relative-path>` |
| `environment` | 开发、验证、预发布、生产等目标环境 |
| `resource` | 能形成不可变 Implementation Result 的版本化代码、配置、Schema、文档或其他产品资源 |

多个 Scope Token 使用 `, ` 分隔、去重后按完整字符串升序排列；值必须使用项目或上游 DSN 中的准确名称，不能用“相关模块”“必要文件”等模糊描述，也不能填写 `None` 或 `N/A`。不同 Type 不自动证明互斥。

每个 `Target Phase=IMP` 的 Work Item 必须为其修改的每个版本化资源包含一个 `resource:<versioned-resource-id>`；该 ID 使用 Core VCS Locator 定义的项目内唯一资源标识。修改多个版本化资源时必须全部列出。同一 Plan 内共享该 Token 的 IMP Work Item 必须形成一条确定的 `Depends On` 链，后继直接依赖前一个共享资源的 Work Item；无法确定顺序时保持 `pending`。

当前内置 Spec 采用资源级保守冲突域；`path`、`module` 等 Token 只描述影响范围，不作为并行安全证明，因此可能牺牲同一资源内的并行度。项目只有在一个版本化单元能够独立捕获 Baseline、形成不可变 Result 并确定性集成时，才能把它登记为更小的 `resource`；否则按包含它的仓库或版本化资源串行。同一 Claim Provider 命名空间内的 Resource ID 必须使用项目注册的 canonical ID 且彼此不重叠；无法证明两个版本化单元不相交时，统一使用它们的最小共同上层 Resource。

运行中的数据库、队列、外部服务和部署环境不是版本化 Implementation Result，不使用独立 `resource` Token；按事实使用 `component`、`interface` 或 `environment` 表达影响。其 Schema、配置或基础设施代码仍归属承载它们的版本化 `resource`，实际目标侧操作和状态由 RLS 记录。

每个 `Target Phase=RLS` Work Item 必须在 Execution Scope 中包含且只包含一个 `environment:<release-target-id>`，该 ID 与后续 RLS `Release Target` 完全一致；相互独立的 Release Target 必须拆成不同 Work Item。该 Token 只负责 Target 归属与依赖，不表示环境本身是版本化 Result。

### Work Item 粒度

一个 Work Item 必须同时满足：

- 只产生一个主要 Outcome；
- 只归属一个 Target Phase；
- 具有明确且有限的 Execution Scope；
- 可以独立判断是否满足 Completion Criteria；
- 完成后能够形成明确 Expected Evidence。

工作过大而无法满足以上条件时必须拆分；多个条目只有描述不同、却共享同一 Outcome、Scope 和 Evidence 时应合并。拆分和合并不得破坏 Source References 的覆盖完整性。

## Coverage 与 Traceability

Work Item 的 `Source References` 是计划覆盖关系的唯一权威字段，不再建立重复的覆盖矩阵。

- Delivery Scope 内每个需要执行的 Change Item、VFY Point 或其他下游义务，必须由至少一个 Work Item 覆盖；
- 每个 Work Item 必须反向引用真实上游来源，不允许孤立工作；
- 一个来源可以映射多个 Work Item，一个 Work Item 也可以覆盖多个紧密相关的来源；
- `Constraint References` 必须覆盖影响当前 Work Item 的已知约束和未关闭 Exception；
- Work Item 不得创造上游没有确认的新业务语义、设计选择或扩展范围；
- 下游 Artifact 使用 `<PLN-ID>@<Revision>#<WI-ID>` 绑定实际结果，不以外部编号替代该引用。

Work Item 不保存实时状态，其当前闭合结果由目标 Phase 的权威 Artifact 确定：

- `Target Phase=IMP`：准确 WI Binding 对应的 IMP Revision 已冻结、Current Claim 为 `completed`，且 Completion Criteria 与 Expected Evidence 已由 Result、Check 和 Evidence 支持；
- `Target Phase=VFY`：WI 已进入 VFY Method 的 Obligation References，映射 Method 已形成最终结果，并由 Conclusion、Evidence、Return 或 Exception 准确说明完成情况；
- `Target Phase=RLS`：WI 已进入 Release Contract，并由 Release Item 或 Post-release Confirmation 的 Source References 映射；Release Conclusion 必须说明其完成情况；
- 未满足的 Work Item 不得从下游记录中消失，必须保留 Return、Exception 或剩余风险；PLN 不为此增加状态字段。

### IMP 执行绑定

每个 `Target Phase=IMP` 的 Work Item 必须可以被一个权威 IMP Artifact 独立绑定，IMP 不得重组 Work Item。完整 Binding、Lineage、Claim 与返工规则只由 IMP Phase Spec 定义；PLN 不建立第二套执行控制。

## Disposition 与 Work Item

| Lifecycle Disposition | Work Item 规则 |
|---|---|
| `required` | 必须至少存在一个对应 Target Phase 的 Work Item |
| `embedded` | 不创建对应 Work Item；必须引用已注册且可解析、已经实际承载该 Phase 结果的 Host。Work Item 不能作为结果 Host |
| `n/a` | 不创建对应 Work Item，并保留客观原因 |
| `waived` | 不为被豁免义务创建伪 Work Item，必须保留有效 Exception |
| `pending` | 不得完成 PLN Gate |

Work Item 的存在表示该工作已纳入计划，因此不在 Work Item 表中增加 `n/a`、`waived` 或实时 `status` 字段。

## Dependencies 与执行冲突

- `Depends On` 表示结果依赖，不用 Phase 顺序代替真实依赖；
- 所有依赖必须可解析、无自引用、无环，且不能指向更晚的 Target Phase；
- IMP 领取时，`WI-ID` 必须展开为当前 Plan Revision 的准确 `<PLN-ID>@<Revision>#<WI-ID>`；其他 Plan Revision 的结果不能直接满足该依赖；
- Work Item 的共享可变范围必须具有相同 canonical Scope Token；IMP 以 `resource:<versioned-resource-id>` 作为版本化结果冲突的权威 Token，并按前述规则串行化，不能以自由文本“已协调”假定并行；
- 不保存可从依赖和执行范围推导的 `parallel` 字段；
- 不维护成对的 `conflicts_with` 列表，避免 Work Item 增减后形成双向漂移；
- PLN 只记录计划依赖；实际领取由 IMP Claim Record 承载，详细进度和结果由下游 Artifact 承载。

## Lifecycle Applicability

PLN 只保留其后的 Phase：

```markdown
| Phase | Disposition | Host | 判断依据 Basis |
|---|---|---|---|
| IMP | pending | N/A | Pending — <OPI-ID> |
| VFY | required | N/A | VFY Artifact 为固定控制点 |
| RLS | pending | N/A | Pending — <OPI-ID> |
```

- Lifecycle Applicability 必须与 Work Item、Exception 和 Delivery Scope 一致；
- `required` Phase 必须具有 Work Item；
- `embedded` Phase 必须引用已注册且可解析、已经实际承载该 Phase 结果的 Host；同一 Plan 的 `WI-ID` 不能作为结果 Host。当前内置 Spec 没有为 IMP、VFY 或 RLS 注册此类 Host，因此 PLN 不得为这些 Phase 选择 `embedded`；
- 当前内置 Spec 的 IMP 只使用 `required`、`n/a` 或 `waived`，不使用 `embedded`；
- VFY Artifact 必须存在，不能整体标记为 `n/a` 或 `embedded`；
- 发生实际发版或目标状态变化时 RLS Artifact 必须存在。

## AI 与人工协作 AI and Human Collaboration

本节是 Phase 执行指导，不进入 PLN Artifact 模板，也不作为 Gate 或 AI 使用率指标。

| 工作 Activity | AI 适合做什么 | 人工适合做什么 | 原因 Reason |
|---|---|---|---|
| Work Item 拆分 | 按 Outcome、Scope 和 Evidence 形成原子工作 | 确认交付范围与业务顺序 | AI 擅长结构化，人工掌握实际优先关系 |
| 依赖与冲突分析 | 检查依赖图、资源链和覆盖缺口 | 确认外部协调和不可自动判断的约束 | AI 可系统检查，组织事实需要人工提供 |
| 责任与完成条件 | 草拟 Responsible Role、Completion Criteria 和 Expected Evidence | 确认责任边界和可接受结果 | 责任分配与承诺不能由模型决定 |
| Plan 复核 | 检查遗漏、重复和越界工作 | 最终确认计划可执行 | AI 降低结构性错误，人工承担计划选择 |

## Gate

PLN 使用 Core Gate Checks，并增加以下 Phase Check：

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| PLN-G-001 | Scope Input、Return Control Input、PLN Disposition、Delivery Scope 与 Aggregated Applicability 完整一致 | pending | |
| PLN-G-002 | 纳入范围的执行义务、约束、Exception 和 PLN Control Input 均由 Work Item、Evidence 或合法 Disposition 覆盖，不存在孤立、重复或越界工作 | pending | |
| PLN-G-003 | Work Item 字段、粒度、Target Phase、Completion Criteria 和 Expected Evidence 足以独立判断 Outcome | pending | |
| PLN-G-004 | Depends On 有效无环且不指向更晚 Phase；IMP Work Item 完整登记版本化资源，同一资源已形成确定依赖链 | pending | |
| PLN-G-005 | Lifecycle Applicability、已注册 Host、Work Item 与责任角色完整一致 | pending | |
| PLN-G-006 | PLN 未新增或静默改变 Requirement、Design 或 Delivery Scope | pending | |
| PLN-G-007 | 每个 IMP Work Item 均可被独立绑定和完成；每个 VFY、RLS Work Item 均可由目标 Phase 的固定字段唯一映射和闭合，不需要下游重新分组 | pending | |
```

PLN Gate Checks 都是 Contract Integrity Check，不允许直接标记为 `n/a` 或 `waived`。具体义务的 Waiver 通过 Lifecycle Applicability、Work Item 覆盖关系和 Exception 表达，Gate Check 只验证记录是否合规。

## 内部编号

| 对象 | 格式 |
|---|---|
| Work Item | `WI-001` |
| Gate Check | `PLN-G-001` |
