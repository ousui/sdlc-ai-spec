---
title: Implementation Phase Spec
status: draft
version: "1.1"
scope: 已确认的 IMP Binding、领取、实施方法、结果、检查与 Gate Contract
---

# Implementation Phase Spec

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

Front Matter 的 `inputs` 保存本次实际使用的全部直接上游 Artifact Reference，包括承载已采用前置 Result 的可解析冻结 IMP Artifact，以及 Rework References 所属 Artifact；`IMP Binding Reference` 只保存唯一执行身份。两者用途不同，不得相互替代。唯一例外是下文严格限定的同一 IMP Artifact 控制恢复引用：它只进入 `Rework References`，不得进入 `inputs`。其他 Lineage 的失效前驱必须先恢复为新的可解析 Revision，不得以失效引用进入 `inputs`。

## IMP Binding

每个实际生成的 IMP Artifact 必须只有一个 `IMP Binding Reference`。该引用根据前置 PLN Disposition 确定：

| PLN Disposition | IMP Binding Reference | 进入条件 |
|---|---|---|
| `required` | `<PLN-ID>@<Revision>#<WI-ID>` | Work Item 的 `Target Phase=IMP`，且可独立实施和确认完成 |
| `n/a` | 最近且可供下游使用的完整 REQ 或 DSN Artifact Reference | 只有一个完整直接 Input 和一个原子 Implementation Outcome；REQ Goal / AC 或 DSN Change / VFY Point 能提供等价完成依据，不需要聚合、拆分或协调 |
| `embedded` | 不允许 | 当前内置 Spec 没有注册可实际承载 PLN 结果的 Host，不能用 Work Item 或自由文本代替 |
| `waived` | 最近且可供下游使用的完整 REQ 或 DSN Artifact Reference | 有效 Exception 明确授权不执行独立 PLN，并且其作用域只对应一个原子 Implementation Outcome |
| `pending` | 不允许 | 必须先返回上游完成判定 |

本表描述的是“PLN 如何被处置后，required IMP 如何绑定”。当前 Artifact Contract 只要产生实际 Implementation Result，IMP 就必须为 `required` 并生成独立 Artifact；没有实现工作时为 `n/a`，经授权不实施时为 `waived`，当前不支持 IMP `embedded`。

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

`Attempt` 和 `Owner` 是当前成功领取的快照。`Claim State` 只在 Claim Provider 中维护，不重复写入 Artifact。

## Claim Record

Claim Record 是执行控制记录，不是 Lifecycle Artifact，不修改冻结的上游 Artifact，也不代替 Artifact Status。

| 字段 Field | 规则 Rule |
|---|---|
| `Binding Lineage Key` | 从准确 Binding Reference 派生的稳定唯一领取键 |
| `IMP Binding Reference` | 当前 Attempt 使用的完整、带 Revision Binding |
| `IMP Artifact ID` | 由 Claim Provider 在首次成功 `acquire` 时分配；它是稳定 IMP Artifact ID 的唯一分配 Authority，重新领取不得改变 |
| `IMP Artifact Revision` | Claim Provider 在当前 `acquire` 中分配并登记的准确目标 Revision Reservation；Artifact Store 的 `allocate revision` 只采用该准确值建立 open Revision Control Record。该 Control Record 不是 Canonical Revision Payload 或可供下游使用的 Artifact Revision；只有完整 Payload 已通过第一次 `write open revision` 原子持久化，并在该操作成功前完成完整读回验证后，才成为 materialized open Revision；后续才可执行独立的 `read revision` |
| `Attempt` | 首次领取为 `1`；每次从 `abandoned` 或 `completed` 重新激活时加 `1` |
| `Claim State` | Claim Provider 中的权威执行状态，只允许 `active`、`completed`、`abandoned`；没有 Claim Record 表示未领取 |
| `Owner` | 当前 Attempt 的唯一执行 Owner |
| `Execution Scope` | 当前 Attempt 原子领取的 Scope Token 集合，也是范围冲突判断依据 |
| `Dependency Result References` | 领取时解析到的全部直接前驱 Current IMP Result Reference；没有前驱写 `None`。Provider 在 `complete` 的同一条件写入中递归复核这些 Result 及其已登记依赖链仍对应 Current `completed` Claim |
| `Rework References` | `completed → active` 时必填的准确返工依据集合，只允许 VFY Return Reference、RLS Issue Reference、同 Lineage 的更新 Binding Reference、使当前输入或资源链失效的新前驱 IMP Result Reference，以及下文限定的同一 IMP Artifact 控制恢复引用；按 Core Reference Set 语法保存全部适用引用。同一返工序列的 abandoned 重试继承该集合，其他首次领取写 `None` |
| `Abandoned By` | 只有 Claim State 为 `abandoned` 时填写实际执行方；可以是当前 Owner，也可以是已阻断旧 Owner 写入后的项目授权恢复执行方，其他状态写 `N/A` |
| `Abandoned At` | 只有 Claim State 为 `abandoned` 时填写 RFC 3339 时间，其他状态写 `N/A` |
| `Abandon Reason` | 只有 Claim State 为 `abandoned` 时填写。普通放弃与 Revision Control Record 原因一致；frozen 最终化失败恢复固定写作 `complete:<Provider error code>:<specific detail or stale reference>`，作为该失败的权威控制记录；其他状态写 `N/A` |

`Responsible Role` 表示 PLN 中对 Outcome 负责的角色；`Owner` 表示当前实际执行方，两者不得混用。Owner 可以是人工、AI 或其他执行主体，核心 Contract 不据此判断合规性。

Claim Provider 是项目内唯一的执行权来源，也是稳定 IMP Artifact ID 和当前 Claim Attempt 目标 Revision Reservation 的唯一分配 Authority；同一项目及 Resource 命名空间必须确定性解析到唯一 Provider，无法解析或解析到多个 Provider 时不得领取。Claim Provider 的 `acquire` 同时登记准确的 Binding Lineage、IMP Artifact ID、Attempt、Owner 与目标 Revision Reservation。Claim Provider 与 Artifact Store 是不同 Authority：前者控制 Binding Lineage 与 Resource 的执行权并分配上述 IMP 身份，后者只采用和校验 Claim 的准确值并保存 Canonical Artifact Revision；Artifact Store 不得为同一 IMP Binding Lineage 生成第二个 Artifact ID，也不得为同一 Claim Attempt 选择第二个 Revision Number，Revision Control Record 也不授予执行权。Claim 状态变化只有：

```text
no record → active
active → completed
active → abandoned
abandoned → active
completed → active
```

这些变化描述 Binding Lineage 的 Current Claim 视图。同一 Lineage 中 `Attempt` 最大的记录是唯一 Current Claim；历史 Attempt 只保留事实，不参与当前执行权、依赖或资源链判断，也不自动回退。重新激活始终沿用 IMP Artifact ID，递增 Attempt 并预留新的目标 Revision。

Claim Resolver API 只定义以下四个逻辑操作，物理存储与锁实现不作规定：

| 操作 Operation | Contract |
|---|---|
| `resolve` | 按 Binding 或 Lineage 返回唯一 Current Claim，不修改状态 |
| `acquire` | 原子防止同 Lineage 重复领取和 Resource 冲突，并同时分配和登记准确的稳定 IMP Artifact ID、Attempt、Owner 与目标 Revision Reservation |
| `abandon` | 只接受两个互斥入口：准确 Revision 已通过 Artifact Store `abandon revision` 转为 `abandoned` 的普通放弃；或准确 Revision 已为 `frozen`、同 Attempt 的 `complete` 已产生不能以相同条件成功的明确错误且 Reason 按固定格式记录错误的最终化失败恢复。两者都必须匹配 Lineage、Attempt、Revision、Expected Owner 和 `active` 状态，再原子更新 Claim 为 `abandoned` 并记录 Actor 与 Reason |
| `complete` | 在 Artifact 已冻结且 Gate 通过后，按同一组条件递归复核已登记的 Dependency Result 及其依赖链仍对应 Current `completed` Claim，再幂等地将 `active` 更新为 `completed` |

领取顺序固定为：

1. 无副作用地解析 Binding、Lineage、Input、适用性链和现有 Claim；
2. Current Claim 为 `active` 或 `completed` 时，只有请求 Binding、Dependency Result References 与规范化后的 Rework References 都与当前记录完全一致，才幂等返回现有 Attempt；任一不同都先按新请求校验。`active` 期间不同请求返回 mismatch；`completed` 后只有合法且不同的非空 Rework References 才可能启动新返工序列，Binding 或前驱更新时集合必须包含对应新引用，陈旧或不完整集合返回 mismatch。`abandoned` 只有收到合法的显式重试或新返工请求才继续；
3. PLN 为 `required` 时，将 `Depends On` 的传递闭包展开为当前 Plan Revision 的准确 Binding；只有闭包内每个当前 Attempt 均为 `completed`、IMP Artifact Revision 可解析，且每条依赖边的后继 `inputs` 仍包含前驱 Current frozen IMP Revision 时才接受。当前 Work Item 登记直接采用的冻结 IMP Artifact、Result、Exception 和各 Resource 的 Baseline 来源；
4. 直接 Binding 时收集完整上游与返工控制输入，并从准确 State Check Reference 重新检查 Dependency 已达到 Required State；存在未满足依赖、新范围、多个结果间顺序或协调义务时停止并返回 PLN；
5. 仅对新领取或合法重新激活，在完整待登记 Input Set、前置 Result、Exception 和 Baseline 来源均已解析后，无副作用地执行 IMP Input Readiness Check Set；
6. 无副作用地预检查不存在与其他 `active` Claim 相同的 `resource:<versioned-resource-id>`；其他 Scope Token 只用于范围与追踪，不作为当前内置 Claim Contract 的冲突键；
7. 以 Lineage 仍唯一、且全部 Resource 仍无其他 `active` Claim 为提交条件，在 Claim Provider 中原子创建 `active` Attempt，同时分配并登记准确的唯一 IMP Artifact ID、Attempt、Owner 与不可复用的目标 Revision Reservation；条件失败时不分配执行权，返回现有或冲突 Claim；
8. 成功领取后，Owner 使用同一 active Claim 的准确值依次执行 `allocate artifact`、`allocate revision`、第一次 `write open revision` 和后续 `read revision`。`allocate artifact` 必须校验 Binding Lineage、Attempt、Owner 与 Artifact ID：尚未登记时原子登记 Claim 的准确 ID，已按同一 ID 绑定同一 IMP Lineage 时幂等成功，ID 或 Lineage 任一交叉冲突时明确失败且不得生成替代 ID。`allocate revision` 必须采用 Claim 的准确 Reservation：未登记时校验它等于 Lineage 内已持久化最大 Revision 加 `1` 且不存在其他 `open` Revision，再只建立 open Revision Control Record；同一 Claim 和 Lineage 的准确 Reservation 重复请求幂等，已被其他 Revision 占用、存在其他 `open` Revision 或 Lineage 不一致时明确失败且不得改选 Revision。第一次 `write open revision` 必须在一个原子 Store transaction 中写入包含 primary Canonical Blob、全部本地 Member、稳定 Member 身份、Member 元数据、逐项 SHA-256 与 Manifest-Member closure 的完整 Payload，并写入成功的 Readiness 结果、Attempt、Owner、Rework References 与全部实际输入；该操作成功前必须完整读回并校验 Lineage、Binding、Artifact ID、Revision、Attempt 和 Owner 与 Claim 完全一致，成功后才成为 materialized open Revision。随后执行独立的 `read revision` 复核；完整分配、物化和后续读回全部成功前不得修改产品；
9. 任一 Store 登记、物化、读回或校验失败都 fail closed，Claim 保持 `active`，准确 Artifact ID、Attempt、Owner 与 Revision Reservation 不变，并继续锁定 Lineage 和 Resource；不得重新 `acquire`、分配新 Artifact ID、改选或跳过预留 Revision，也不得修改产品。恢复边界固定为：
   - Claim 已成功但 Store 尚未登记 Artifact 时，只能以相同条件重试准确的 `allocate artifact`。需要放弃时，必须在 Store 恢复可用后依次幂等登记 Claim 中的准确 Artifact ID、使用准确 Revision Reservation 创建 Revision Control Record、对该准确 open Control Record 执行 `abandon revision`，再使用同一原因对匹配 active Claim 执行 `abandon`；
   - 准确 IMP Artifact ID 已与其他 Lineage 冲突时停止恢复并报告项目 Authority 解决身份冲突；不得自动分配新 ID、释放或覆盖 Claim；
   - `allocate revision` 事务未提交时不存在 Revision Control Record，只能以同一 Claim 和 Reservation 重试；
   - Revision Control Record 已建立但第一次 `write open revision` 事务未提交时，可以使用同一 Claim 和 Reservation 重试第一次完整写入，或先对该 Control Record 执行 `abandon revision`，再以同一原因 `abandon` Claim；
   - `read revision` 失败时不得把不完整或无法验证的内容当作成功；完整 Payload 已写入但无法验证时，必须保留 Revision Control Record 和实际内容，以明确原因执行 `abandon revision`，再以同一原因 `abandon` Claim；
   - Owner 以外的项目授权恢复执行方只有在先阻断旧 Owner 写入后，才可按上述固定顺序终结准确 Reservation；不得补写实现内容或修改产品。任一步未完成时 Claim 继续保持 `active`；
10. 完整 Payload 物化并读回成功后、首次产品修改前，为每个已有 Resource 生成或复用准确不可变 Baseline Reference 并登记到当前 Revision；同资源前驱存在时 Baseline 必须等于其当前 Result Reference。全新 Resource 必须登记可复核的“不存在或尚未创建”依据，Baseline 固定为 `N/A`；目标已存在时不得按全新资源覆盖。捕获、依据或匹配失败时仍不得修改产品，并按第 9 步放弃 Claim。

Readiness 未通过时不创建 Claim 或 IMP Artifact。成功领取与准确 Artifact ID、Attempt、Owner、Revision Reservation 的分配和登记必须形成 Claim Provider 中的一个原子结果，不能先读取后无条件覆盖；Artifact Store 只幂等采用并校验该结果。

- 遇到同一 Lineage 已有 `active` Claim 时，只有准确 Binding、Dependency Result References 与 Rework References 都相同才停止并返回现有 Owner、Attempt、IMP Artifact ID 和当前记录；任一不同都返回 mismatch，不得把返回结果解释为新请求已接受；
- 遇到已有 `completed` Claim 时，Binding、Dependency Result References 与 Rework References 都相同则返回当前完成结果；只有合法且不同的非空 Rework References 明确要求同一 Lineage 继续实施时才允许重新激活，Binding 或前驱更新时该集合必须包含对应新引用；
- 同一 Owner 使用相同 Binding、Dependency Result References 与 Rework References 重复领取也只返回现有 Claim；任一不同仍按 mismatch 处理；
- `active → abandoned` 只允许两个互斥入口：未冻结 Attempt 先对尚未物化的准确 open Revision Control Record 或已经物化的准确 `open` Revision 执行 `abandon revision`，Claim 与 Revision 使用同一原因；或 frozen Attempt 在 `complete` 已返回不可同条件重试的明确错误后，保持 Revision 不变，并把准确错误码和细节写入 Claim `Abandon Reason`。两者都以 Expected Owner 匹配当前 Lineage、Attempt、Revision、Owner 和 `active` 状态，将实际 Actor、时间和原因条件写入；当前 Owner 自行放弃时 Actor 默认等于 Expected Owner；
- `abandoned → active` 必须显式发生，沿用 IMP Artifact ID、递增 Attempt 并预留新的最大 Revision，不复用旧 Owner 的 Revision；只有 Binding 和全部当前前驱 Result 均未改变时才属于原序列重试并继承原 Rework References，任一变化都必须以当前完整 Rework References 启动新序列；
- 每个重试都重新选择 Baseline：目标 Resource 未前进时可以复用原不可变 Baseline；已前进时必须以当前准确不可变状态为新 Baseline，丢弃旧可变视图并重新应用仍需保留的变化；无法确定性协调时返回 PLN 或 DSN；
- `completed → active` 必须沿用 IMP Artifact ID、递增 Attempt、重新执行 Readiness，并预留新的最大目标 Revision；
- `completed → active` 处理原 Lineage 内的局部返工或同一稳定 Item 的新上游 Revision；Requirement、Design 或 Plan 变化必须先形成新的上游 Revision，Item 语义被替代时使用新 Lineage；
- 相同 `Binding Lineage Key + Rework References` 只能启动一个返工序列；集合使用 Core 固定排序和去重规则，重复请求返回该序列的最新 Attempt。只有该 Attempt 已 `abandoned`、Binding 与全部当前前驱 Result 均未改变且显式重试时，才在同一序列追加 Attempt；任一因果引用变化时启动新序列，陈旧或指向其他 Lineage / Result 的请求必须拒绝；
- 只有当前 `active` Claim 的 Owner 才可把准确 open Revision Control Record 作为第一次 `write open revision` 的目标；完整 Payload 物化并读回校验通过后，仍只有该 Owner 可通过后续 `write open revision` 修改对应 IMP Artifact，并修改 Claim 覆盖的产品内容。Revision 进入 `frozen` 或 `abandoned` 后立即失去写权限。项目授权的恢复执行方只有在先阻断旧 Owner 写入后，才可按第 9 步终结预留 Revision，或按 frozen 最终化失败入口释放匹配 Claim；调用时以旧 Owner 为 Expected Owner、恢复执行方为 Actor，不得补写实现、修改 frozen Artifact、修改产品或自动超时接管；
- 不新增 `blocked` Claim State；等待输入时保持 `active`，释放执行权时显式改为 `abandoned`；
- `completed` 必须以 IMP Artifact 已通过 Gate 并形成可解析 Revision 为依据。

Claim Record 必须为每个 Attempt 保留准确 Binding Reference、IMP Revision、Owner、Execution Scope、Dependency Result References、Rework References 和 Claim State，不得通过覆盖当前记录删除先前领取事实。Rework References 必须包含启动本序列时全部已变化的 Binding、前驱 Result 和有效 Return；除同一 IMP Artifact 控制恢复引用外，每个来源所属 Artifact 都必须进入 `inputs`。

VFY Return Reference 固定使用 `<VFY-ID>@<Revision>#RET-ID`。只有所属 VFY Revision 已冻结、`Return Phase=IMP`、Subject References 可追踪到当前 Lineage Result，且 Return 尚未被后续 VFY 解决时才能触发返工。Return 的 `IMP Binding Reference` 应与当前准确 Binding 相同；若上游 Revision 已更新，则必须保持同一 Binding Lineage，并在 Rework References 中同时包含该 Return 与更新后的准确 Binding。不同 Lineage 必须拒绝。

RLS Issue Reference 固定使用 `<RLS-ID>@<Revision>#<RLI-ID|RCF-ID>`。只有所属 RLS Revision 已冻结、Follow-up Disposition 为 `return_imp`、Release Conclusion 为 `failed`、`partial` 或 `cancelled`、该行及 Evidence 明确证明产品 Result 必须改变，且 Source References 可追踪到当前唯一 Lineage Result 时才能触发返工。无法唯一归属时必须使用 `return_pln`；环境、权限、发版重试或外部执行失败不得误作 IMP 返工。

无法解析、仍为 open、指向其他 Lineage 或不能证明产品结果需要改变的 Return 必须拒绝。同一 Lineage 的更新 Binding 或使当前输入或资源链失效的新前驱 IMP Result 仍可作为返工依据。

Gate 前必须重新解析 `Depends On` 的完整传递闭包；只有闭包内全部 Current Claim、冻结 IMP Revision、Result 和依赖边仍连续有效，且当前 Attempt 直接登记的输入未变化时才可继续。任一祖先前驱形成新 Result 后，当前 Attempt 不得发布；应先对已物化的 `open` Revision 执行 `abandon revision`，确认成功后再将匹配 Claim 放弃。待依赖链按顺序恢复后，把全部已变化前驱 Result 纳入新的 Rework References 重新领取。

Claim 的 Execution Scope 必须与 IMP Artifact Scope 一致，领取后不可变。当前内置 Claim Contract 的 Result Changed Scope 只能使用 Claim Scope 中已有的准确 Token；更细文件位置保存在 Change Reference 或 Evidence。需要增加 Claim 未授权的 Scope Token 时必须停止并返回 PLN 或准确上游，不能在实施中覆盖 Claim。

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
| IMP-RDY-006 | 当前 Context、Requirement、Decision、Constraint、Dependency 和 Exception 可追踪；可变 Dependency 可以在领取时确定性复核，且没有阻塞 Open Item | pending | |
```

- Result 只允许 `pending`、`pass` 或 `fail`；
- 六项都是 Contract Integrity Check，不允许 `n/a` 或 `waived`；
- 全部为 `pass` 才能领取；
- Readiness 只判断输入契约完整性，不要求尚未到执行时点的运行依赖提前完成；
- 上游 Gate 判断“未来 IMP 是否有完整输入”，实际领取另外检查当时的 Dependency 和 Claim 状态。

## IMP 内部执行流程

IMP 使用五个 Activity，不建立子 Phase 或子 Artifact：

IMP 的 Pre-execution Checklist 复用当前 Revision 已有内容：非空 Evaluation Contract Set、准确 Implementation Binding、Front Matter Context 与 Inputs、Scope、全部为 `pass` 的 Input Readiness Check Set、Claim identity、每个 Resource 的不可变 Baseline，以及完整的 Implementation Method Contract。首次产品修改前，完整 Canonical Revision Payload 必须通过 `write open revision` 原子持久化、通过 `read revision` 读回并保存 Evidence；缺少任一项只能继续分析或补全 Artifact，不得开始产品修改。

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
contract: sdlc-ai-spec/artifact/v1
phase: IMP
id: IMP-20260824143000-01
revision: 1
status: draft
context: CTX-20260828143025-01@1
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
- 下游引用某个结果单元时使用 `<IMP-ID>@<Revision>#<RES-ID>`。

Result Set 所有单元格都必须填写；可选值不存在时写 `N/A`。实际变化行的 `Changed Scope` 必须包含 `resource:<Resource>`，其他值只使用当前 Claim 中已有的准确 Scope Token；沿用行按前述规则写 `None`。`path:<resource-id>/<resource-relative-path>` 的 `resource-id` 必须与当前行 `Resource` 相同。更细位置写入 Change Reference 或 Evidence；`Approach Step References` 使用 Core Reference Set，沿用行写 `None`。

每个 Attempt 的已有 Resource 必须使用由 Baseline 初始化的隔离或独占可变视图，全新 Resource 从已验证未创建的空目标初始化；Result 不得吸收其他 Claim 的变化。存在用户已有修改时，必须将其纳入完整 Baseline Snapshot，不得把 `HEAD` 误作实际 Baseline。全部实际变更只表示当前 Attempt 的 Result 相对该 Baseline 或空目标的差异，且 `Changed Scope` 必须是当前 Claim Execution Scope Token 的子集。VCS 对象必须在生命周期保留期内可解析，否则保存完整 Snapshot Member。

Claim 前已存在、且被提议用来满足当前 Binding 的 commit、patch、bundle 或工作树变化只能作为 Candidate Material，不能直接吸入 Baseline 后以“本 Attempt 未改变”冒充当前 Result。正式 Attempt 必须从已声明的准确 Baseline 建立隔离视图，只重放 Claim Scope 内仍适用的候选变化，再执行当前 Method Contract、Checks 并登记新的不可变 Result。与当前 Binding 无关的用户既有修改仍按上一段纳入 Baseline；无法区分候选变化与真实基线时停止并补充 Evidence，不得倒签 Claim。

唯一例外是 Core 控制恢复：旧冻结 IMP 在关闭递归 Input 解析后必须通过自身本地校验，其唯一失效原因是 Lifecycle Authority 或 Input 链不可解析；当前 Revision 与旧 Revision 的 Binding Lineage、准确 Binding Reference、规范化 Execution Scope，以及 Implementation Result 中的 ID、Resource、Baseline、Change、Result、Changed Scope、Steps 必须完全一致，被移除的失效 Input 不参与比较，并已通过现有 Claim 转换建立新 Attempt。该旧 Revision 以同一 IMP Artifact 的准确 Artifact Reference 进入 `Rework References`，只说明重激活原因并定位 Base candidate；它不进入 Front Matter `inputs`，也不提供 Authority。同一引用只启动一个返工序列。当前 Checklist 后必须逐项读回不可变 Resource，证明它与旧候选 Result 完全一致；任何未解决的 Return、失败事实或风险，只要可能改变当前 Binding 的 Outcome、Resource、Scope、Target、可观察行为或 Result 身份，就会使等价性不成立；任何与当前 Result 相关且无法由当前读回重建的外部状态或副作用同样使等价性不成立。只有当前权威 Scope 明确排除、且 Evidence 证明不影响上述等价维度的环境或流程失败，才不单独否定等价性；该限制仍必须准确记录，且不得用于支持产品、VFY 或 RLS `pass`。全部条件成立时，本 Attempt 可以准确登记 `Baseline Reference=Result Reference=<当前不可变状态>`、`Change Reference=N/A`、`Changed Scope=None`、`Approach Step References=None`，但仍须形成当前 Evidence、Checks、Gate 和 Final Confirmation，不继承旧 Result Authority。无法由当前读回证明的状态必须重放或重新执行。

任一 `Depends On` 的 Current Result 在下游完成后发生变化，都会使所有仍引用旧 Result 的传递下游失去 VFY 就绪性；原 frozen Revision 保留为历史事实，但不能继续作为当前交付结果。受影响 Work Item 必须把全部已变化前驱 Result 纳入 Rework References，并按依赖顺序重新执行。VFY 开始前必须复核当前 Plan 的每条已执行依赖边：后继 `inputs` 包含前驱 Current frozen IMP Revision，且不存在尚未吸收的更新或 `active/abandoned` Attempt。

同一 Plan 内多个 IMP Work Item 修改相同 Resource 时，必须按 PLN 的单一依赖链执行。当前 Work Item 通过 Gate 时只检查截至自身的已执行链前缀：所有同资源前驱的 Current Claim 均为 `completed` 且 Binding 匹配当前 Plan Revision；每条已执行边的后继 `inputs` 包含当前前驱冻结 IMP Revision；后继 Baseline 等于当前前驱 Result；当前候选 Result 完整；前缀中不存在尚未吸收的前驱更新或其他 `active/abandoned` Attempt。当前 Claim 在 Gate 时仍为 `active`，不检查尚未执行的后继；Artifact 冻结且 `complete` 成功后才加入 completed 链。前驱形成新 Result 后，原后继不再是有效链尾，必须把全部已变化前驱 Result 纳入 Rework References，按依赖顺序重新执行受影响后继。VFY 开始前，所需整条链的 Current Claim 必须全部 `completed`、连续且只有一个有效链尾；VFY 只采用该终端 Result，不能自行合并或回退到旧链。

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
| RLS | pending | N/A | Pending — <OPI-ID> |
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
| 最终结果确认 | 整理 Result、Evidence 和 Gate；满足 delegated 边界时执行独立客观复核 | 处理主观判断、Exception、风险接受和授权事项 | Final Confirmation 按 Core 选择 delegated 或 human，不固定为人工职责 |

## Gate

IMP 使用 Core Gate Checks，并增加以下 Phase Check：

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| IMP-G-001 | Context、Binding Lineage、准确 Binding Reference、Input、Dependency Result References、Rework References、Attempt、IMP Revision 和 Claim 一致有效；`Depends On` 传递闭包的全部当前结果与依赖边连续有效，Readiness 全部通过 | pending | |
| IMP-G-002 | 实现只覆盖一个原子 Outcome，未重组 Work Item、超出不可变 Claim Scope 或违反依赖 | pending | |
| IMP-G-003 | 七项 Implementation Consideration、连续 Approach、必要 Method Block 与首次产品修改前的 Pre-execution 读回 Evidence 完整一致，未新增 Requirement、Design 或 Plan 决策 | pending | |
| IMP-G-004 | 实际实现、上游约束和 Work Item Completion Criteria / Expected Evidence 一致；Result Set 对 Claim 中每个 Resource 恰有一行并以不可变 Result 唯一确定，截至当前 Work Item 的同资源链前缀连续有效 | pending | |
| IMP-G-005 | 所有适用 Implementation Check 已完成，Result 与 Basis 准确 | pending | |
| IMP-G-006 | 当前 Artifact 已完整登记可供 VFY 解析的 Result、未关闭 Exception 和必要 Evidence，不存在阻塞输入 | pending | |
```

IMP Gate Checks 都是 Contract Integrity Check，只允许 `pending`、`pass` 或 `fail`，不能直接标记为 `n/a` 或 `waived`。具体实施义务通过 Consideration、Implementation Check 和 Exception 表达处置，Gate 只验证记录是否合法。

`IMP-G-004` 只确认当前 Binding 的 Implementation Completion Criteria 或等价完成依据，不得解释为完整 Requirement 已验证、系统集成正确、满足预期用途或可以交付。

## 最终化顺序

IMP 先按 Core 最终化 Contract 完成全部内容、检查、确认和摘要，再按固定顺序完成两个独立写入：

1. 只有 Binding Lineage、Attempt、IMP Revision、Claim Owner 和 `Depends On` 传递闭包仍然匹配，Gate 已通过，且 primary Blob、全部本地 Member、稳定身份、Media Type、逐项 SHA-256 和 Manifest-Member closure 已持久化并读回一致时，才按 Core 与 Artifact Store Contract 执行 `freeze revision`，把 Revision Control Record 从 `open` 转为 `frozen`；
2. 冻结成功后，重新解析直接前驱 Current Result，并以同一 Lineage、Attempt、Revision、Owner 和准确 Dependency Result References 调用 Claim Provider `complete`；Provider 在同一事务中递归复核每个前驱及其已登记依赖链仍为对应 Revision 的 Current `completed` Claim，再 CAS `active → completed`。

- Gate 未通过时可在当前 `open` Revision 内修正并重新检查，Claim 保持 `active`；
- Revision 已冻结、Claim 仍为 `active` 是允许的短暂中间状态；该 Claim 继续锁定 Lineage 和 Resource，不允许新 Owner；
- `complete` CAS 成功后，frozen Revision 与 `completed` Claim 才可供下游使用；下游必须确认 Current Claim 的 Binding Lineage、Attempt、Artifact ID、Revision 和 Dependency Result References 完全匹配。前驱在完成后形成新 Attempt 时，该结果立即失去当前有效性并按返工规则处理；
- `complete` CAS 失败且 Provider 仍解析到相同 `active` Claim、全部依赖仍准确时，不重新冻结或重写 Artifact，使用相同条件重试；
- 若 frozen Revision 的 `complete` 因依赖失效或条件不再成立而不能以相同条件成功，必须保留该 Revision 的不可变失败现场，并把准确 Provider 错误码与细节按 `complete:<code>:<detail>` 写入 Claim `Abandon Reason`，再以原 Owner或明确授权的恢复主体把匹配 Claim CAS `active → abandoned`；frozen Revision 保持历史 Snapshot，但不得供下游使用，随后按 Claim 返工规则创建新 Attempt 与新 Revision；
- 未冻结 Attempt 的放弃必须先对准确预留 Revision 执行 `abandon revision` 并记录原因，再 CAS Claim `active → abandoned`；frozen Attempt 只允许用于上一条最终化失败恢复，不能作为普通取消手段；任一 Claim 终结失败时 Claim 保持 `active`；
- 不创建第二个 IMP Artifact，也不重新分配 Binding。

PLN 为 `required` 时，只有匹配 WI 的冻结 IMP Revision 与 `completed` Current Claim 同时存在，且 Work Item 的 Completion Criteria 与 Expected Evidence 已由当前 Result、Check 和 Evidence 支持，该 IMP Work Item 才算当前完成。`active`、`abandoned`、`open` 或“已冻结但 Claim 仍为 active”都不完成 Work Item；后续合法返工重新激活 Claim 后，旧完成结果只保留为历史事实。

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
