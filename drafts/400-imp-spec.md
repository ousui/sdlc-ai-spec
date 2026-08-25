---
title: Implementation Phase Spec
status: draft
scope: 已确认的 IMP Binding、领取、实施方法、结果、检查与 Gate Contract
---

# Implementation Phase Spec（草稿）

> 本文件只定义 IMP 的通用 Artifact 与控制边界，不规定具体编程语言、工具、平台或执行者。

## Phase 目标

IMP 按已确认的 Requirement、Design 和适用的 Plan 实施一个明确 Binding，形成可追踪、可复现并可进入 VFY 的实现结果。

IMP Gate 通过只表示实现完整且已准备进入 VFY，不表示完整 Requirement 已通过验证、满足预期用途或可以交付。

## Phase 边界

IMP 负责：

- 解析一个准确 `IMP Binding Reference`；
- 在开始修改前确认 Input、范围与实施语义已经就绪；
- 领取唯一执行权并防止重复或范围冲突；
- 把已确认语义转换为连续、可执行的 Implementation Method Contract；
- 实施代码、配置、文档或其他产品变更；
- 执行适用的本地检查并保存 Evidence；
- 准确绑定实施基线、变更集和结果；
- 形成可供 VFY 使用的 IMP Artifact。

IMP 不负责：

- 新增或改变 Requirement、Design Decision、Delivery Scope 或 Work Item；
- 为未来可能需求创建抽象、依赖、组件或扩展点；
- 顺手重构、优化或修复当前 Binding 之外的内容；
- 代替 VFY 判断完整 Requirement、系统集成或预期用途是否满足；
- 代替 RLS 判断结果是否可以发版；
- 记录执行者的隐藏推理过程。

产品代码、配置、文档和其他实际变更是 Implementation Result；IMP Markdown 是控制与追踪 Artifact，两者不得混作同一结果。

## 输入与输出

| 类型 Type | 内容 Content |
|---|---|
| Input | 一个准确 Binding、其解析链、相关上游 Artifact Revision、已采用的前置 IMP Revision、项目 Spec、与当前范围相关的未关闭 Exception 和必要基线 |
| Output | 一个 IMP Artifact、一个或多个 Implementation Result Item，以及支持检查和 Gate 的 Evidence |

Front Matter 的 `inputs` 保存本次实际使用的全部直接上游 Artifact Reference，包括承载已采用前置 Result 的冻结 IMP Artifact，以及 Rework References 所属 Artifact；`IMP Binding Reference` 只保存唯一执行身份。两者用途不同，不得相互替代。

## IMP Binding

每个实际生成的 IMP Artifact 必须只有一个 `IMP Binding Reference`。该引用根据前置 PLN Disposition 确定：

| PLN Disposition | IMP Binding Reference | 进入条件 |
|---|---|---|
| `required` | `<PLN-ID>@<Revision>#<WI-ID>` | Work Item 的 `Target Phase=IMP`，且可独立实施和确认完成 |
| `n/a` | 最近且可供下游使用的完整 REQ 或 DSN Artifact Reference | 只有一个完整直接 Input 和一个原子 Implementation Outcome；REQ Goal / AC 或 DSN Change / VFY Point 能提供等价完成依据，不需要聚合、拆分或协调 |
| `embedded` | 不允许 | 当前 v0.1 没有注册可实际承载 PLN 结果的 Host，不能用 Work Item 或自由文本代替 |
| `waived` | 最近且可供下游使用的完整 REQ 或 DSN Artifact Reference | 有效 Exception 明确授权不执行独立 PLN，并且其作用域只对应一个原子 Implementation Outcome |
| `pending` | 不允许 | 必须先返回上游完成判定 |

本表描述的是“PLN 如何被处置后，required IMP 如何绑定”。v0.1 只要产生实际 Implementation Result，IMP 就必须为 `required` 并生成独立 Artifact；没有实现工作时为 `n/a`，经授权不实施时为 `waived`，当前不支持 IMP `embedded`。

直接绑定路径还必须满足：

- 不得组合多个 Scope Input 或只选择其中部分范围；同一 Binding 内的前置 Result、Rework Artifact 和 Evidence 是控制输入，不单独触发 PLN；
- 同一上游 Artifact 不能被解释为多个直接 IMP Binding；存在多个独立 Outcome 时必须进入 PLN 拆分；
- `waived` 必须承接有效 Exception，不能把缺少计划误写为 `n/a`；
- 不创建 `Direct Work Item`、临时任务或其他合成身份。

准确 `IMP Binding Reference` 负责版本追踪；唯一领取使用从该引用确定性派生、不含 Revision 的 `Binding Lineage Key`：

| Binding Reference | Binding Lineage Key |
|---|---|
| `<Artifact-ID>@<Revision>#<Item-ID>` | `<Artifact-ID>#<Item-ID>` |
| `<Artifact-ID>@<Revision>` | `<Artifact-ID>` |

同一 Item ID 跨 Revision 代表同一语义 Lineage。准确 Binding Reference 更新但 Lineage 不变时，沿用 IMP Artifact ID 并创建新 IMP Revision；Item 语义被替代时必须使用新的 Item ID 和新 Lineage。

映射关系固定为：

```text
一个 Binding Lineage ↔ 一个权威 IMP Artifact
```

- 一个 Binding Lineage 只允许分配一个 IMP Artifact ID；
- 一个 IMP Artifact 只允许绑定一个 Binding Lineage 和一个当前准确 Binding Reference；
- 重新领取同一 Lineage 时沿用原 IMP Artifact ID；
- IMP 不拆分、合并或重组 Binding；
- 无法保持一对一时返回 PLN 修正范围或粒度。

Artifact 使用以下固定记录：

```markdown
| IMP Binding Reference | Binding Lineage Key | Attempt | Owner | Rework References |
|---|---|---:|---|---|
| | | | | None |
```

`Attempt` 和 `Owner` 是当前成功领取的快照，不重复写入由 Revision Index 派生的 `Claim State`。

## Claim Record

Claim Record 是执行控制记录，不是 Lifecycle Artifact，不修改冻结的上游 Artifact，也不代替 Artifact Status。

| 字段 Field | 规则 Rule |
|---|---|
| `Binding Lineage Key` | 从准确 Binding Reference 派生的稳定唯一领取键 |
| `IMP Binding Reference` | 当前 Attempt 使用的完整、带 Revision Binding |
| `IMP Artifact ID` | 首次成功领取时分配；重新领取不得改变 |
| `IMP Artifact Revision` | 当前 Attempt 唯一对应的 Revision；`active` 指向 open Revision，`completed` 指向 frozen Revision，`abandoned` 指向 abandoned Revision |
| `Attempt` | 首次领取为 `1`；每次从 `abandoned` 或 `completed` 重新激活时加 `1` |
| `Claim State` | 只读派生值：对应 Revision Index 为 `open` 时是 `active`，`frozen` 时是 `completed`，`abandoned` 时是 `abandoned`；不独立存储或更新，没有 Claim Record 表示未领取 |
| `Owner` | 当前 Attempt 的唯一执行 Owner |
| `Execution Scope` | 当前 Attempt 原子领取的 Scope Token 集合，也是范围冲突判断依据 |
| `Rework References` | `completed → active` 时必填的准确返工依据集合，只允许 VFY Return Reference、同 Lineage 的更新 Binding Reference，以及使当前输入或资源链失效的新前驱 IMP Result Reference；按 Core Reference Set 语法保存全部适用引用。同一返工序列的 abandoned 重试继承该集合，其他首次领取写 `None` |
| `Abandoned By` | 只有对应 Revision 为 `abandoned` 时填写实际执行方，其他状态写 `N/A` |
| `Abandoned At` | 只有对应 Revision 为 `abandoned` 时填写 RFC 3339 时间，其他状态写 `N/A` |

`Responsible Role` 表示 PLN 中对 Outcome 负责的角色；`Owner` 表示当前实际执行方，两者不得混用。Owner 可以是人工、AI 或其他执行主体，核心 Contract 不据此判断合规性。

由 Revision State 派生的 Claim 状态变化只有：

```text
no record → active
active → completed
active → abandoned
abandoned → active
completed → active
```

这些变化描述 Binding Lineage 的 Current Claim 视图；`frozen` 或 `abandoned` Revision 从不重新打开，重新激活始终创建更大 Attempt 和新的 `open` Revision。

同一 Binding Lineage 中 `Attempt` 最大的记录是唯一 Current Claim；历史 Attempt 只保留事实，不参与当前状态、依赖或资源链判断，也不得自动回退。Claim Resolver 必须找到唯一最大 Attempt，并通过其 `IMP Artifact Revision` 解析对应 Revision Index；最大 Attempt 重复、Revision 不存在或映射不一致时解析失败。Revision 为 `abandoned` 时 `Abandoned By / At` 与 Revision Index 的 `Abandon Reason` 必须完整，其他状态两字段必须为 `N/A`。所有条件写入都必须同时比较 Binding Lineage、Attempt、IMP Revision、Owner 和当前 Revision State；新领取还必须在提交时确认 Lineage 尚未被领取，且当前全部其他 `active` Claim 不含相同 `resource:<versioned-resource-id>`。物理存储格式不影响该逻辑 Contract。

领取顺序固定为：

1. 无副作用地解析 Binding、Lineage、Input、适用性链和现有 Claim；
2. Current Claim 为 `active` 或 `completed` 时，只有请求 Binding 与规范化后的 Rework References 都与当前记录完全一致，才幂等返回现有 Attempt；任一不同都先按新请求校验。`active` 期间不同请求返回 mismatch；`completed` 后只有合法且不同的非空 Rework References 才可能启动新返工序列，Binding 更新时集合必须包含新 Binding，陈旧或不完整集合返回 mismatch。`abandoned` 只有收到合法的显式重试或新返工请求才继续；
3. PLN 为 `required` 时，将 `Depends On` 的传递闭包展开为当前 Plan Revision 的准确 Binding；只有闭包内每个当前 Attempt 均为 `completed`、IMP Artifact Revision 可解析，且每条依赖边的后继 `inputs` 仍包含前驱 Current frozen IMP Revision 时才接受。当前 Work Item 登记直接采用的冻结 IMP Artifact、Result、Exception 和各 Resource 的 Baseline 来源；
4. 直接 Binding 时收集完整上游与返工控制输入，并从准确 State Check Reference 重新检查 Dependency 已达到 Required State；存在未满足依赖、新范围、多个结果间顺序或协调义务时停止并返回 PLN；
5. 仅对新领取或合法重新激活，在完整待登记 Input Set、前置 Result、Exception 和 Baseline 来源均已解析后，无副作用地执行 IMP Input Readiness Check Set；
6. 无副作用地预检查不存在与其他 `active` Claim 相同的 `resource:<versioned-resource-id>`；其他 Scope Token 只用于范围与追踪，不作为 v0.1 Claim 冲突键；
7. 以 Lineage 仍唯一、且全部 Resource 仍无其他 `active` Claim 为提交条件，原子地创建 Claim Attempt 记录和对应 `open` Revision，并写入准确 Binding Reference、Owner、Execution Scope 和 IMP Artifact Revision；条件失败时不创建任何 Claim、Artifact ID 或 Revision，并返回现有或冲突 Claim。首次领取同时分配唯一 IMP Artifact ID，重新激活时始终分配新的最大 Revision；`active` 由该 `open` Revision 派生；
8. 在该 IMP Artifact 中保存成功的 Readiness 结果、Attempt、Owner、Rework References 和全部实际采用的直接上游 Artifact Reference；
9. Claim 成功后、首次产品修改前，为每个已有 Resource 生成或复用准确不可变 Baseline Reference 并登记到当前 Revision；同资源前驱存在时 Baseline 必须等于其当前 Result Reference。全新 Resource 必须登记可复核的“不存在或尚未创建”依据，Baseline 固定为 `N/A`；目标已存在时不得按全新资源覆盖。捕获、依据或匹配失败时不得修改产品内容，必须将对应 Revision 从 `open` 条件更新为 `abandoned`，Claim 随之派生为 `abandoned`。

Readiness 未通过时不创建 Claim 或 IMP Artifact。成功领取与 Artifact ID 分配必须形成一个原子结果，不能先读取后无条件覆盖。

- 遇到同一 Lineage 已有 `active` Claim 时，只有准确 Binding 与 Rework References 都相同才停止并返回现有 Owner、Attempt、IMP Artifact ID 和当前记录；任一不同都返回 mismatch，不得把返回结果解释为新请求已接受；
- 遇到已有 `completed` Claim 时，Binding 与 Rework References 都相同则返回当前完成结果；只有合法且不同的非空 Rework References 明确要求同一 Lineage 继续实施时才允许重新激活，Binding 更新时该集合必须包含新的准确 Binding；
- 同一 Owner 使用相同 Binding 与 Rework References 重复领取也只返回现有 Claim；任一不同仍按 mismatch 处理；
- `active → abandoned` 只通过一次条件写入完成：匹配当前 Owner 和 Attempt，把 Revision Index 从 `open` 改为 `abandoned`、填写唯一 `Abandon Reason`，并填写 Claim Attempt 的 `Abandoned By / At`；任一写入失败时全部保持原值，不得释放执行权；
- `abandoned → active` 必须显式发生，沿用 IMP Artifact ID、递增 Attempt 并分配新的最大 Revision，不复用旧 Owner 的 Revision；只有 Binding 和全部当前前驱 Result 均未改变时才属于原序列重试并继承原 Rework References，任一变化都必须以当前完整 Rework References 启动新序列；
- 每个重试都重新选择 Baseline：目标 Resource 未前进时可以复用原不可变 Baseline；已前进时必须以当前准确不可变状态为新 Baseline，丢弃旧可变视图并重新应用仍需保留的变化；无法确定性协调时返回 PLN 或 DSN；
- `completed → active` 必须沿用 IMP Artifact ID、递增 Attempt、重新执行 Readiness，并从最近 frozen Revision 分配新的最大 Revision；
- `completed → active` 处理原 Lineage 内的局部返工或同一稳定 Item 的新上游 Revision；Requirement、Design 或 Plan 变化必须先形成新的上游 Revision，Item 语义被替代时使用新 Lineage；
- 相同 `Binding Lineage Key + Rework References` 只能启动一个返工序列；集合使用 Core 固定排序和去重规则，重复请求返回该序列的最新 Attempt。只有该 Attempt 已 `abandoned`、Binding 与全部当前前驱 Result 均未改变且显式重试时，才在同一序列追加 Attempt；任一因果引用变化时启动新序列，陈旧或指向其他 Lineage / Result 的请求必须拒绝；
- 只有当前 Owner 和 Attempt 可以修改或完成对应 IMP Artifact 及当前 Claim 覆盖的产品内容；项目授权的恢复执行方只有在先阻断旧 Owner 写入后，才能按上述同一条件写入把匹配 Revision 更新为 `abandoned`；Claim 随之派生为 `abandoned`，不得自动超时接管；
- 不新增 `blocked` Claim State；等待输入时保持 `active`，释放执行权时显式改为 `abandoned`；
- `completed` 必须以 IMP Artifact 已通过 Gate 并形成可解析 Revision 为依据。

Claim Record 必须为每个 Attempt 保留准确 Binding Reference、IMP Revision、Owner、Execution Scope 和 Rework References；状态及变化从对应 Revision Index 解析，不得通过覆盖当前行删除先前领取事实。集合必须包含启动本序列时全部已变化的 Binding、前驱 Result 和有效 VFY Return；每个来源所属 Artifact 都必须进入 `inputs`。VFY Return Reference 固定使用 `<VFY-ID>@<Revision>#RET-ID`，并且只有在所属 VFY Revision 已冻结、`Return Phase=IMP`，且其 Subject References 包含当前 Binding Lineage 的 Result，或包含以该 Result 为传递输入的当前终端 Result 时才能触发返工。无法解析、仍为 open、指向其他 Phase 或无法沿 `inputs` 追踪到当前 Lineage 的 Return 不得接受。同一 Lineage 的更新 Binding 或使当前输入或资源链失效的新前驱 IMP Result 也可以作为返工依据。

Gate 前必须重新解析 `Depends On` 的完整传递闭包；只有闭包内全部 Current Claim、冻结 IMP Revision、Result 和依赖边仍连续有效，且当前 Attempt 直接登记的输入未变化时才可继续。任一祖先前驱形成新 Result 后，当前 Attempt 不得发布；应将匹配 Revision 从 `open` 条件更新为 `abandoned`，待依赖链按顺序恢复后，把全部已变化前驱 Result 纳入新的 Rework References 重新领取。

Claim 的 Execution Scope 必须与 IMP Artifact Scope 一致，领取后不可变。v0.1 的 Result Changed Scope 只能使用 Claim Scope 中已有的准确 Token；更细文件位置保存在 Change Reference 或 Evidence。需要增加 Claim 未授权的 Scope Token 时必须停止并返回 PLN 或准确上游，不能在实施中覆盖 Claim。

两类冲突分别判断：

| 冲突 | 判断键 | 处理 |
|---|---|---|
| 重复领取 | 相同 Binding Lineage Key | 停止并返回现有 Claim |
| 范围冲突 | 不同 Lineage 的 Execution Scope 存在相同 `resource:<versioned-resource-id>` | 停止领取并返回冲突 Claim |

## IMP Input Readiness Check Set

Readiness Check Set 由实际把工作交给 IMP 的位置执行：

- PLN 为 `required`：针对所选 IMP Work Item；
- PLN 为 `n/a`：针对最近的完整 REQ 或 DSN Artifact；
- PLN 为 `waived`：针对最近上游 Artifact 和有效 Exception。

```markdown
| Check ID | 检查项 Check | Result | Evidence or Notes |
|---|---|---|---|
| IMP-RDY-001 | Binding 唯一、可解析且与 PLN Disposition 一致 | pending | |
| IMP-RDY-002 | Binding 只对应一个原子 Implementation Outcome，不需要在 IMP 中重组 | pending | |
| IMP-RDY-003 | 目标、验收依据及完成依据足以判断实施完成；有 Work Item 时使用 Completion Criteria / Expected Evidence，直接 Binding 使用 REQ Goal / AC 或 DSN Change / VFY Point 的等价依据 | pending | |
| IMP-RDY-004 | 当前 Attempt 各版本化资源的 Baseline 来源、捕获方式、Target、输入输出和 Execution Scope 明确且一致；全新资源具有可复核的未创建依据，同资源前驱存在时能够准确继承其 Result | pending | |
| IMP-RDY-005 | 七项 Implementation Consideration 可以分类，适用项具有权威上游语义或设计 | pending | |
| IMP-RDY-006 | Requirement、Decision、Constraint、Dependency 和 Exception 可追踪；可变 Dependency 可以在领取时确定性复核，且没有阻塞 Open Item | pending | |
```

- Result 只允许 `pending`、`pass` 或 `fail`；
- 六项都是 Contract Integrity Check，不允许 `n/a` 或 `waived`；
- 全部为 `pass` 才能领取；
- Readiness 只判断输入契约完整性，不要求尚未到执行时点的运行依赖提前完成；
- 上游 Gate 判断“未来 IMP 是否有完整输入”，实际领取另外检查当时的 Dependency 和 Claim 状态。

## IMP 内部执行流程

IMP 使用五个 Activity，不建立子 Phase 或子 Artifact：

| 活动 Activity | 主要动作 | 完成结果 |
|---|---|---|
| 接收 Accept | 解析 Binding、完成 Readiness 并原子领取 | 输入就绪且只有一个有效 Owner |
| 准备 Prepare | 登记不可变 Baseline，分类 Implementation Consideration，形成 Method Contract | 基线、实施逻辑、顺序和边界明确 |
| 实施 Implement | 按 Method Contract 修改产品内容 | 形成 Implementation Result |
| 检查 Check | 执行适用的格式化、静态检查、构建和单元测试等 | 形成可追踪 Evidence |
| 关闭 Close | 校准实际结果、执行 Gate、确认并冻结 Artifact | 结果可以进入 VFY |

Prepare 允许读取和分析产品内容，但在 Method Contract 完成前不得修改产品内容。

## Front Matter

IMP 直接使用 Core Artifact Front Matter：

```yaml
---
contract: sdlc-ai-spec/artifact/v0.1
phase: IMP
id: IMP-20260824143000-01
revision: 1
status: draft
profile: full
inputs:
  - PLN-20260824120000-01@1
---
```

## 固定模板

```markdown
# <实施标题>

## 摘要 Summary

## 范围 Scope

## 实施控制 Implementation Control

### 实施绑定 Implementation Binding

### 输入就绪检查 Input Readiness Check Set

## 实施方法合约 Implementation Method Contract

### 实施考量矩阵 Implementation Consideration Matrix

### 实施步骤 Implementation Approach

## 实施结果 Implementation Result

## 实施检查 Implementation Checks

## 待确认项 Open Items

## 证据 Evidence

## 支撑产物清单 Supporting Artifact Manifest

## 豁免 Exceptions

## 生命周期适用性 Lifecycle Applicability

## 门禁 Gate
```

Summary 用一至三句话说明 Outcome 和最终结果，不复制完整上游内容。Scope 固定使用：

```markdown
- 结果 Outcome:
- 执行范围 Execution Scope:
- 排除项 Exclusions:
```

`Execution Scope` 沿用 PLN Scope Token 语法。PLN 为 `n/a/waived` 时只允许使用 REQ `Direct IMP Scope` 行，或 DSN Change Item `Object or Boundary` 的确定性并集。无法确定时 Readiness 为 `fail` 并返回 PLN，不能由 IMP 猜测范围。

每个 IMP Execution Scope 必须为实际修改的每个版本化资源包含一个 `resource:<versioned-resource-id>`，并与 Implementation Result Set 的 `Resource` 一一对应。

## Implementation Method Contract

Method Contract 只把已确认语义转换为代码级实施方式，不创建新的业务或设计决策，也不要求保存隐藏推理过程。

### Implementation Consideration Catalog

Catalog 固定为以下七项，并按此顺序展示：

| 实施考量项 Implementation Consideration | 客观触发条件 |
|---|---|
| 计算规则 Calculation Rules | 存在公式、费率、聚合、单位、精度、舍入或数值边界 |
| 决策规则 Decision Rules | 多个条件相互作用，存在优先级、冲突或默认结果 |
| 状态转换 State Transitions | 存在持久化或业务可观察状态、事件及合法或非法转换 |
| 算法与不变量 Algorithm & Invariants | 存在非平凡解析、匹配、搜索、排序、聚合或必须持续成立的不变量 |
| 数据契约与转换 Data Contract & Transformation | 跨模型、接口、Schema 或格式转换，并存在映射、校验、Null 或默认语义 |
| 边界与失败处理 Boundary & Failure Handling | 存在输入边界、错误分类、异常传播、失败响应或降级语义 |
| 副作用与一致性 Effects & Consistency | 存在多次写入、外部调用、消息、资源、并发、顺序、幂等或一致性影响 |

普通条件语句、数值赋值、布尔判断、调用已有方法、同结构透传、沿用未改变的全局异常处理和局部变量修改，不单独触发对应 Consideration。

以下内容不增加为并列 Consideration：

- Security、Privacy、Performance、Compatibility、Observability 和 Migration 是上游 DSN 约束，通过七项实施方式落实；
- 抽象、复用、公共库和 Design Pattern 由 Implementation Decision Rules 控制；
- 命名、格式、导入和 Style 由项目 Spec 与工具控制；
- Test 由 Implementation Checks 和 VFY 承载。

### Implementation Consideration Matrix

矩阵只作为覆盖索引，不承载长篇实施说明：

```markdown
| 实施考量项 Implementation Consideration | Disposition | 触发依据或 N/A 原因 | Approach Step 引用 | Exception 引用 |
|---|---|---|---|---|
| 计算规则 Calculation Rules | pending | | None | None |
| 决策规则 Decision Rules | pending | | None | None |
| 状态转换 State Transitions | pending | | None | None |
| 算法与不变量 Algorithm & Invariants | pending | | None | None |
| 数据契约与转换 Data Contract & Transformation | pending | | None | None |
| 边界与失败处理 Boundary & Failure Handling | pending | | None | None |
| 副作用与一致性 Effects & Consistency | pending | | None | None |
```

Disposition 只允许 `pending`、`required`、`n/a` 或 `waived`：

- `required` 必须关联至少一个 Approach Step；
- `n/a` 必须填写客观原因；
- `waived` 必须关联有效 Exception；
- `pending` 不能通过 IMP Gate；
- `embedded` 不适用于 Consideration；复用既有实现仍由 `required` Step 说明复用方式。

### Implementation Decision Rules

实施选择按以下顺序确定：

1. 已确认的 DSN Decision 和 Constraint；
2. 不冲突的项目级 Spec 与既有项目实现；
3. 能正确完成当前 Outcome 的最简单局部实现；
4. 只有存在明确重复或稳定变化点时才建立局部抽象；
5. 新依赖、公共抽象、跨模块接口或架构变化返回 DSN 决策。

不得为了使用设计模式而使用设计模式，不做推测性抽象，不顺手重构当前范围之外的内容。格式、导入、命名和可由项目工具确定的等价选择不进入 Method Contract。

### Implementation Approach

Approach 是当前 Binding 的一份连续、按实际逻辑顺序组织的实施说明，不按 Consideration 拆分文件：

```markdown
#### STEP-001 <步骤名称>

- 顺序 Order:
- 目标位置 Target:
- 依据引用 Basis References:
- 适用考量项 Considerations:
- 预期结果 Expected Result:

实施逻辑：

1. ...
2. ...
```

规则：

- `STEP-001` 是稳定身份；实际顺序由唯一正整数 `Order` 决定，并按 Order 升序展示；
- 一个 Step 表示一次独立的业务判断、数据转换、状态变化、外部副作用或紧密相关的语义动作；
- 执行顺序、事务边界、失败处理或权威依据不同，应拆成不同 Step；
- 相互依赖且共同完成一个语义结果的动作可以合并；
- 不按文件、类、函数或代码行机械拆分；
- Step 不是 Work Item，不建立新的领取或任务身份；
- 一个 Step 可以覆盖多个 Consideration，一个 Consideration 也可以映射多个 Step；
- 简单修改可以只有一个 Step；
- 实际变更和检查结果分别由 Implementation Result Set、Implementation Checks 与 Evidence 承载，不在 Step 重复维护。

`Target` 使用一个或多个准确 Execution Scope Token；`Basis References` 使用 Core Reference Set；`Considerations` 使用 Catalog 英文名称并按 Catalog 顺序以 `, ` 分隔。Gate 前所有字段必须填写，空集合写 `None`。

### 方法块 Method Blocks

每个 `required` Consideration 必须在相关 Step 下至少使用一个对应固定方法块；多个紧密相关规则可以共用同一方法块。`n/a` 或 `waived` 不生成空方法块。方法块不是独立 Artifact 或文件。

#### 计算规则 Calculation Rules

```markdown
##### CAL-001 <名称>

- 输出 Output:
- 表达式 Expression:
- 输入与单位 Inputs and Units:
- 精度与舍入 Precision and Rounding:
- 边界与非法值 Boundary and Invalid Values:
```

#### 决策规则 Decision Rules

```markdown
##### DEC-001 <名称>

| Rule ID | 优先级 Priority | 条件 Conditions | 结果或动作 Outcome or Action |
|---|---:|---|---|
| RUL-001 | 1 | | |
| RUL-002 | 最后 | DEFAULT | |
```

决策按 Priority 求值；`DEFAULT` 必须明确，不能由执行者猜测未列出的分支。

#### 状态转换 State Transitions

```markdown
##### STA-001 <名称>

| Transition ID | 当前状态 | 事件或条件 | 下一状态 | 动作或副作用 | 非法转换处理 |
|---|---|---|---|---|---|
| TRN-001 | | | | | |
```

只记录持久化或业务可观察状态，不记录普通局部变量变化。

#### 算法与不变量 Algorithm & Invariants

````markdown
##### ALG-001 <名称>

- 输入 Inputs:
- 输出 Outputs:
- 不变量 Invariants:
- 规模或限制 Scale or Limits:

```text
按执行顺序编写伪代码
```
````

简单循环或直接调用已有算法不生成伪代码块。

#### 数据契约与转换 Data Contract & Transformation

```markdown
##### MAP-001 <名称>

| 来源 Source | 目标 Target | 转换规则 | 校验规则 | Null or Default |
|---|---|---|---|---|
| | | | | |
```

同结构直接透传不生成映射表。

#### 边界与失败处理 Boundary & Failure Handling

```markdown
##### ERR-001 <名称>

- 触发条件或边界 Trigger or Boundary:
- 分类 Classification:
- 处理方式 Handling:
- 对外可观察结果 Observable Result:
- 恢复或传播 Recovery or Propagation:
```

不重复未改变的项目全局异常规范。

#### 副作用与一致性 Effects & Consistency

```markdown
##### EFF-001 <名称>

- 资源或副作用 Resource or Effect:
- 顺序与条件 Order and Condition:
- 一致性或原子性 Consistency or Atomicity:
- 幂等性 Idempotency:
- 失败处理 Failure Handling:
```

只有实际存在一致性义务时才要求事务、补偿或幂等设计。

全部方法块 ID 在当前 IMP Artifact 内唯一并跨 Revision 保持稳定。字段不得留空；字段客观不适用时写 `N/A`。

## Implementation Result Set

Implementation Result 使用一个固定集合：

```markdown
| ID | 资源 Resource | 基线引用 Baseline Reference | 变更引用 Change Reference | 结果引用 Result Reference | 变更范围 Changed Scope | Approach Step References |
|---|---|---|---|---|---|---|
| RES-001 | | | | | | |
```

| 字段 Field | 规则 Rule |
|---|---|
| `ID` | 使用 `RES-001` 顺序编号，在当前 Artifact 内唯一并跨 Revision 保持稳定；同一 Resource 沿用同一 ID |
| `Resource` | Core VCS Locator 定义的项目内唯一版本化资源 ID，不是 Scope Token；一行不是一个文件 |
| `Baseline Reference` | 当前 Attempt 首次产品修改前准确且不可变的状态；全新资源写 `N/A` |
| `Change Reference` | 可选的不可变 Patch、Diff 或其他审计材料；没有时写 `N/A`，不能替代完整 Result |
| `Result Reference` | 修改后准确且不可变的版本或完整快照，始终必填 |
| `Changed Scope` | 当前 Resource 内实际变化的 Scope Token 集合，不写“相关文件”等模糊描述 |
| `Approach Step References` | 产生该结果的全部 Step ID |

合法组合只有：

| 场景 | Baseline | Change | Result |
|---|---|---|---|
| 修改已有资源 | 必填 | 可选 | 必填 |
| 全新生成的独立资源 | `N/A`，并有可复核的未创建依据 | 可选 | 必填 |
| 本 Attempt 未改变的资源 | 当前准确 Baseline | `N/A` | 与 Baseline 相同 |

- 每个 `RES` 必须通过不可变 Result 唯一确定 VFY 将检查的内容；Patch / Diff 不能单独证明完整结果，因为它可能遗漏权限、二进制、未跟踪内容或其他资源状态；
- 每个冻结 IMP Revision 必须对 Claim 中每个 `resource:<id>` 恰好保留一行；当前 Attempt 未改变的 Resource 固定写作 `Baseline Reference=Result Reference=<当前准确 Baseline>`、`Change Reference=N/A`、`Changed Scope=None`、`Approach Step References=None`。默认 Baseline 是上一冻结 Result；Resource 已前进时，只有新的准确不可变状态已登记为当前 Input / Baseline 来源并通过 Readiness 与协调检查，才允许使用新的 Baseline；无法确定性协调时返回 PLN 或 DSN；
- 一个版本化资源修改多个文件通常仍是一行；一个 Work Item 修改多个版本化资源时每个资源各一行；
- VCS Locator 固定写作 `vcs:<resource>@<immutable-revision>`，其中 `<resource>` 必须与当前行 `Resource` 完全一致，Revision 必须是完整不可变对象 ID；
- Patch、完整快照或生成文件可以使用完整 Member Reference，并由 Supporting Artifact Manifest 保存 SHA-256；未提交的版本化内容可以使用持久 VCS Tree / Object 或完整 Snapshot Member；
- 分支、可移动 Tag、`latest`、`current`、当前工作树、单独路径或无摘要临时文件不能作为准确 Result；
- 项目扩展可以注册其他不可变 Result Locator，但不能放宽唯一解析要求；注册机制闭合前不得使用未定义格式；
- 下游引用某个结果单元时使用 `<IMP-ID>@<Revision>#<RES-ID>`。

Result Set 所有单元格都必须填写；可选值不存在时写 `N/A`。实际变化行的 `Changed Scope` 必须包含 `resource:<Resource>`，其他值只使用当前 Claim 中已有的准确 Scope Token；沿用行按前述规则写 `None`。`path:<resource-id>/<resource-relative-path>` 的 `resource-id` 必须与当前行 `Resource` 相同。更细位置写入 Change Reference 或 Evidence；`Approach Step References` 使用 Core Reference Set，沿用行写 `None`。

每个 Attempt 的已有 Resource 必须使用由 Baseline 初始化的隔离或独占可变视图，全新 Resource 从已验证未创建的空目标初始化；Result 不得吸收其他 Claim 的变化。存在用户已有修改时，必须将其纳入完整 Baseline Snapshot，不得把 `HEAD` 误作实际 Baseline。全部实际变更只表示当前 Attempt 的 Result 相对该 Baseline 或空目标的差异，且 `Changed Scope` 必须是当前 Claim Execution Scope Token 的子集。VCS 对象必须在生命周期保留期内可解析，否则保存完整 Snapshot Member。

任一 `Depends On` 的 Current Result 在下游完成后发生变化，都会使所有仍引用旧 Result 的传递下游失去 VFY 就绪性；原 frozen Revision 保留为历史事实，但不能继续作为当前交付结果。受影响 Work Item 必须把全部已变化前驱 Result 纳入 Rework References，并按依赖顺序重新执行。VFY 开始前必须复核当前 Plan 的每条已执行依赖边：后继 `inputs` 包含前驱 Current frozen IMP Revision，且不存在尚未吸收的更新或 `active/abandoned` Attempt。

同一 Plan 内多个 IMP Work Item 修改相同 Resource 时，必须按 PLN 的单一依赖链执行。当前 Work Item 通过 Gate 时只检查截至自身的已执行链前缀：所有同资源前驱的 Current Claim 均为 `completed` 且 Binding 匹配当前 Plan Revision；每条已执行边的后继 `inputs` 包含当前前驱冻结 IMP Revision；后继 Baseline 等于当前前驱 Result；当前候选 Result 完整；前缀中不存在尚未吸收的前驱更新或其他 `active/abandoned` Attempt。当前 Claim 在 Gate 时仍为 `active`，不检查尚未执行的后继；原子发布成功后才加入 completed 链。前驱形成新 Result 后，原后继不再是有效链尾，必须把全部已变化前驱 Result 纳入 Rework References，按依赖顺序重新执行受影响后继。VFY 开始前，所需整条链的 Current Claim 必须全部 `completed`、连续且只有一个有效链尾；VFY 只采用该终端 Result，不能自行合并或回退到旧链。

## Implementation Checks

Implementation Checks 保存本次实际执行的局部检查，不建立平行 QA Artifact：

```markdown
| ID | 检查或方法 Check or Method | 范围 Scope | 结果 Result | 依据 Basis |
|---|---|---|---|---|
| None | none | N/A | n/a | No applicable independent implementation checks |
```

- 实际 Check ID 使用 `CHK-001` 顺序编号并保持稳定；存在实际 Check 时删除 `None` 行；
- Result 使用 `pending`、`pass`、`fail`、`n/a` 或 `waived`；
- `Basis` 由 Result 决定：`pass` / `fail` 引用 Evidence，`n/a` 填写客观原因，`waived` 引用有效 Exception，`pending` 说明尚未完成的事实；
- `n/a` 不能表示适用但未执行；
- 适用检查由当前实现、项目 Spec 和上游 Expected Evidence 决定，不强制执行无关工具；
- 详细命令输出、日志和报告保存在 Evidence 或 Supporting Artifact，表内只保存摘要；
- Test 资产的实现和修改属于 IMP；
- IMP 可以执行格式化、静态检查、类型检查、构建、单元测试和必要的局部运行检查；这些结果只证明当前实现已完成相应局部检查；
- VFY 可以在 Evidence 准确对应最终 Subject 时复核这些结果，也可以因 Subject 变化、独立复核要求或风险重新执行；
- IMP Check 通过只表示结果具备进入 VFY 的条件；完整 Requirement、系统集成、预期用途及是否允许交付的结论不属于 IMP。

## 缺失决策与执行裁量

实施中发现问题时按以下边界处理：

| 缺失或问题 | 返回位置 |
|---|---|
| 业务语义、规则、验收边界不清 | REQ |
| 架构、接口、数据、状态、一致性或技术选择不清 | DSN |
| Outcome、Work Item 粒度、依赖或 Execution Scope 不正确 | PLN |
| 已确认边界内的局部实现错误 | IMP 内修正 |

等价的局部语法、变量名、私有函数组织和工具可确定格式属于执行裁量，不需要上升为 Method Contract。实施前的 Method Contract 可以在同一未冻结 Revision 内调整；最终内容必须反映实际结果，不要求保留每一次中间草稿。

## Lifecycle Applicability

```markdown
| Phase | Disposition | Host | 判断依据 Basis |
|---|---|---|---|
| VFY | required | N/A | VFY Artifact 为固定控制点 |
| RLS | pending | N/A | Pending — <OI-ID> |
```

- VFY 固定为 `required`；
- RLS 依据上游适用性、当前 Implementation Result 和新增事实按 Core 规则重新判断，不因 Profile 或实现完成自动取值；
- RLS 为 `required` 时必须明确待发版 Result；没有实际发版或目标状态变化时按事实使用 `n/a` 或有效 `waived`；
- `pending` 必须引用阻塞 Open Item，不能通过 IMP Gate。

## AI 与人工协作 AI and Human Collaboration

本节是 Phase 执行指导，不进入 IMP Artifact 模板，也不作为 Gate 或 AI 使用率指标。

| 工作 Activity | AI 适合做什么 | 人工适合做什么 | 原因 Reason |
|---|---|---|---|
| Readiness 与 Approach | 解析 Binding、检查输入并形成连续实施方式 | 补充缺失的权威业务或设计决定 | AI 可系统执行，不能替代上游决策 |
| 产品与测试资产实现 | 按已确认 Contract 编码、更新 Test 和执行局部检查 | 处理必须人工授权的环境或操作 | AI 适合完整实施和重复执行 |
| 质量与范围控制 | 检查 Consideration、越界变化和 Result 完整性 | 对新范围、架构或风险作上游决定 | AI 可发现偏差，权威改变必须人工确认 |
| 最终结果确认 | 整理 Result、Evidence 和 Gate | 审核关键结果并完成 Human Confirmation | Artifact 可信性需要独立责任确认 |

## Gate

IMP 使用 Core Gate Checks，并增加以下 Phase Check：

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| IMP-G-001 | Binding Lineage、准确 Binding Reference、Input、Attempt、IMP Revision 和 Claim 一致有效；`Depends On` 传递闭包的全部当前结果与依赖边连续有效，Readiness 全部通过 | pending | |
| IMP-G-002 | 实现只覆盖一个原子 Outcome，未重组 Work Item、超出不可变 Claim Scope 或违反依赖 | pending | |
| IMP-G-003 | 七项 Implementation Consideration、连续 Approach 和必要 Method Block 完整一致，未新增 Requirement、Design 或 Plan 决策 | pending | |
| IMP-G-004 | 实际实现、上游约束和完成依据一致；Result Set 对 Claim 中每个 Resource 恰有一行并以不可变 Result 唯一确定，截至当前 Work Item 的同资源链前缀连续有效 | pending | |
| IMP-G-005 | 所有适用 Implementation Check 已完成，Result 与 Basis 准确 | pending | |
| IMP-G-006 | 当前 Artifact 已完整登记可供 VFY 解析的 Result、未关闭 Exception 和必要 Evidence，不存在阻塞输入 | pending | |
```

IMP Gate Checks 都是 Contract Integrity Check，只允许 `pending`、`pass` 或 `fail`，不能直接标记为 `n/a` 或 `waived`。具体实施义务通过 Consideration、Implementation Check 和 Exception 表达处置，Gate 只验证记录是否合法。

`IMP-G-004` 只确认当前 Binding 的 Implementation Completion Criteria 或等价完成依据，不得解释为完整 Requirement 已验证、系统集成正确、满足预期用途或可以交付。

## 最终化顺序

IMP 先按 Core 最终化 Contract 完成冻结前的全部内容、检查、确认和摘要，再执行一次条件原子发布：仅当 Binding Lineage、Attempt、IMP Revision、Claim Owner 和 `Depends On` 传递闭包的全部当前结果与依赖边仍然匹配时，把 Revision Index 从 `open` 改为 `frozen`；Claim 随之唯一派生为 `completed`。

- Gate 未通过时可以在当前 open Revision 内修正并重新检查，Claim 保持 `active`；
- 发布成功后 Revision 与派生 Claim 同时可供下游解析；Claim 不存在独立状态写入，因此不会形成 `frozen + active` 中间状态；
- 下游解析 IMP Revision 时，除 Core Resolver 外还必须确认唯一 Current Claim 指向该 Revision，Binding Lineage、Attempt 和 IMP Revision 完全匹配，且由 `frozen` 派生为 `completed`；孤立的 frozen Revision 不能放行；
- 发布失败时 Revision 保持 `open`、Claim 仍派生为 `active`，不产生部分发布；按相同条件重复执行必须返回同一完成结果；
- 当前 Owner 明确放弃，或项目授权恢复执行方按 Claim 规则完成接管前处置时，使用 Claim 规定的同一条件写入更新 Revision `open → abandoned`、`Abandon Reason` 和 `Abandoned By / At`，Claim 同步派生为 `abandoned`；
- 不创建第二个 IMP Artifact，也不重新分配 Binding。

## 内部编号

| 对象 | 格式 |
|---|---|
| Approach Step | `STEP-001` |
| Calculation Block | `CAL-001` |
| Decision Block | `DEC-001` |
| Decision Rule | `RUL-001` |
| State Block | `STA-001` |
| State Transition | `TRN-001` |
| Algorithm Block | `ALG-001` |
| Data Mapping Block | `MAP-001` |
| Boundary or Failure Block | `ERR-001` |
| Effect Block | `EFF-001` |
| Implementation Result | `RES-001` |
| Implementation Check | `CHK-001` |
| Readiness Check | `IMP-RDY-001` |
| Gate Check | `IMP-G-001` |

## 当前未定义

- Claim Record 的文件路径、存储介质、条件更新和锁实现；
- Owner 的项目级身份格式；
- Project Extension 注册额外 Result Locator 和 Implementation Check 的实现方式；
- RLS 外部平台适配和自动 Evidence 采集方式。
