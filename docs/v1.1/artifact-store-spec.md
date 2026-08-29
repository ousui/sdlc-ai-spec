---
title: Artifact Store Spec
status: draft
version: "1.1"
scope: Canonical Artifact Revision 的逻辑存储、完整 Payload、状态控制与准确解析
---

# Artifact Store Spec

> 本文件定义实现中立的最小逻辑 Artifact Store Contract；它不规定物理存储结构或执行技术。

## 目标与边界

Artifact Store 负责保存、读取、校验和准确解析 Canonical Artifact Revision。一个 Project Boundary 必须能够唯一确定一个 Canonical Store；无法唯一确定、Store 不可用、内容损坏或操作失败时必须 fail closed，不得改用文件副本、临时材料或其他候选内容。

Artifact Store Spec 只定义 Artifact Authority 的逻辑持久化边界，不创建新的 Artifact 字段、Revision State、Artifact Status、Reference 类型、Manifest 字段、Phase、Gate 或 Final Confirmation 类型。

## 逻辑对象

### Canonical Store

Canonical Store 是一个 Project Boundary 内唯一的 Canonical Artifact Authority。它保存 Artifact Lineage、Revision Control Record 与完整 Canonical Revision Payload，并保证所有准确 Reference 解析到指定 Revision，而不是解析到阅读视图、导出副本或候选材料。

### Artifact Lineage

Artifact Lineage 是同一稳定 Artifact ID 的全部 Revision 历史。Artifact ID 在项目范围内唯一，分配后不得覆盖、复用或转移。一个 Lineage 同时最多存在一个 `open` Revision。

没有 Claim Contract 的 Artifact 继续由 Artifact Store 分配 Artifact ID 和 Revision。IMP 是唯一例外：Claim Provider 是稳定 IMP Artifact ID 和当前 Claim Attempt 目标 Revision Reservation 的唯一分配 Authority；`acquire` 同时登记准确的 Binding Lineage、Artifact ID、Attempt、Owner 与目标 Revision Reservation。Artifact Store 只采用并校验这些准确值，不得为同一 IMP Binding Lineage 生成第二个 Artifact ID，也不得为同一 Claim Attempt 选择第二个 Revision Number。

### Revision Control Record

Revision Control Record 保存既有 Revision 控制语义：

- Revision；
- State；
- Base Revision；
- Allocated At；
- Frozen At；
- Abandon Reason。

`State` 只使用 `open`、`frozen` 或 `abandoned`；合法变化只有 `open → frozen` 和 `open → abandoned`。Revision 单调增加，分配后不得删除或复用。

`allocate revision` 只创建 `State=open` 的 Revision Control Record。完整 Canonical Revision Payload 首次成功写入并读回前，该记录只是 open Store Control Reservation，不是 Canonical Revision Payload、Lifecycle Artifact、可供下游使用的 Artifact Revision、Gate 或 Final Confirmation 对象。

### Canonical Revision Payload

Canonical Revision Payload 是一个 Revision 的完整逻辑存储单元，必须包含：

1. primary Canonical Markdown/YAML Blob 的完整原始字节及其既有 SHA-256；
2. 当前 Revision locally owned 的全部 Member 原始字节；
3. 每个本地 Member 的既有稳定身份；
4. 每个本地 Member 的 Canonical Member Name 或等价稳定名称；
5. 每个本地 Member 的 Media Type；
6. 每个 Blob 与本地 Member 的 SHA-256；
7. 能唯一闭合实际本地 Member 集合的既有 Canonical Manifest 内容。

本地 Member 至少包括 DSN Artifact Set Domain Member、当前 Store 本地保存的 Supporting Member，以及既有 Phase 或 Domain Contract 定义并由当前 Revision 本地拥有的成员。Manifest 中的每个本地 Member 必须与实际保存的 Member 一一对应，形成 Manifest-Member closure。

外部不可变 Reference 不要求复制为本地 Member。Store 必须继续保存其既有准确 Reference、摘要和访问边界；不得因为外部内容不由当前 Store 保存而删除、替换或降低这些信息。

只有 primary Canonical Blob、locally owned Member、Manifest 与 Revision Control Record 身份一致，并已完整写入和读回验证后，才构成 materialized open Revision。`materialized` 只是本 Contract 对完整 Payload 已成功写入并读回的描述，不是新的 Revision State 或正式字段；只保存或验证 primary Blob 不构成完整 Canonical Revision Payload。

## 最小操作

Artifact Store 只定义以下逻辑操作：

- `initialize`
- `allocate artifact`
- `allocate revision`
- `read revision`
- `write open revision`
- `freeze revision`
- `abandon revision`
- `resolve exact reference`
- `verify digest`

### initialize

- 建立或验证当前项目唯一 Canonical Store；
- 不改变任何领域 Artifact 内容；
- Store 无法唯一确定时失败。

### allocate artifact

- 对没有 Claim Contract 的 Artifact，原子分配项目范围内唯一 Artifact ID；
- 对 IMP，接收 active Claim 中已分配的准确 IMP Artifact ID，并校验 Claim 的 Binding Lineage、Attempt、Owner 和 Artifact ID；
- IMP Artifact ID 尚未登记时，原子登记该准确 ID；同一 ID 已登记到同一 IMP Binding Lineage 时幂等成功返回；
- IMP 的同一 ID 已绑定其他 Lineage，或同一 Lineage 已绑定其他 ID 时明确失败，不得生成替代 ID，也不得自动释放或覆盖 Claim；
- 不得根据标题、时间、目录或相似内容为 IMP 选择其他 Artifact；
- 不覆盖、不复用、不转移已有 Artifact ID；
- 成功前必须能够读回分配结果。

### allocate revision

- 对没有 Claim Contract 的 Artifact，分配当前 Artifact 已持久化最大 Revision 加 `1`；
- 对 IMP，采用 active Claim 中的准确目标 Revision Reservation，并校验 Binding Lineage、Artifact ID、Attempt、Owner、Reservation 与 Store 当前 Lineage 状态一致；
- IMP 的准确 Reservation 尚未登记时，它必须等于当前已持久化最大 Revision 加 `1` 且不存在其他 `open` Revision，随后原子建立对应 Revision Control Record；同一准确 Reservation 已由同一 Claim 与 Lineage 建立时幂等成功返回；
- IMP 的准确 Reservation 已被其他 Revision 占用、存在其他 `open` Revision、同一 Claim Attempt 已登记其他 Revision，或与当前 Lineage 不一致时明确失败；不得自行选择第二个 Revision Number；
- 同一 Artifact 同时最多存在一个 `open` Revision；
- Revision 分配后不得删除或复用；
- 只建立 `State=open` 的 Revision Control Record，不创建 Canonical Revision Payload；
- 分配结果和 Revision Control Record 成功前必须能够读回。

完整 Payload 首次写入前，open Revision Control Record 只允许作为第一次 `write open revision` 的准确目标，或通过 `abandon revision` 终结。它不得被 `read revision` 当作 Canonical Artifact 读取，不得被 `resolve exact reference` 解析，不得执行 Artifact Gate、Final Confirmation 或 `freeze revision`，也不得被下游作为 Context、Input、Item 或 Member Authority。

### read revision

`read revision` 只读取已经物化的 Revision；只有 Revision Control Record、完整 Canonical Revision Payload 和二者身份一致性都存在时才可继续。只有 Control Reservation、Payload 缺失或任何内容不完整时必须失败，不得返回部分内容或把 Control Reservation 描述为 Canonical Artifact。

读取指定的 materialized Revision 时必须验证：

- primary Canonical Blob；
- 全部 locally owned Member；
- 每个 Member 的稳定身份、Canonical Member Name 或等价稳定名称、Media Type；
- Manifest-Member closure；
- primary Blob 与每个本地 Member 的原始字节 SHA-256；
- Revision Control Record 与 Payload 身份一致。

Member 缺失、存在未登记 Member、Member ID 重复、摘要不匹配、Manifest 无法唯一闭合、Revision 不存在或身份不一致时必须失败。

### write open revision

- 只能修改准确的 `open` Revision；
- 第一次写入必须以准确的 open Revision Control Record 为目标，在一个原子 Store transaction 中同时写入完整 primary Blob、全部 locally owned Member、稳定 Member 身份、Member 元数据、每项 SHA-256 和能形成 Manifest-Member closure 的 Manifest；
- 第一次写入事务提交前不得留下任何 Canonical Revision Payload；提交后必须完整读回并验证，只有验证成功才成为 materialized open Revision；
- 后续写入只能修改准确的 materialized open Revision，并继续在一个原子 Store transaction 中一致写入完整 primary Blob、全部本地 Member、Member 元数据和 Manifest；
- 不允许部分成功；
- `frozen` 或 `abandoned` Revision 禁止写入；
- 并发或内容冲突必须明确失败，不使用 last-write-wins；
- 成功前必须读回并验证完整 Canonical Revision Payload。

### freeze revision

只有以下条件全部成立时才可执行：

- 当前 `open` Revision 已物化，不是只有 Revision Control Record 的 Control Reservation；
- primary Blob 已持久化并读回；
- 全部本地 Member 已持久化并读回；
- Manifest 与实际本地 Member 集合完全一致；
- primary Blob 与所有本地 Member 的 SHA-256 均验证通过；
- 对应 Artifact 的既有 Gate 与 Final Confirmation 条件成立。

冻结后以下内容不可修改：

- primary Blob 原始字节；
- 本地 Member 原始字节；
- Member 集合；
- 稳定 Member 身份；
- Canonical Member Name 或等价稳定名称；
- Media Type；
- SHA-256；
- Manifest-Member closure。

任何变化都必须创建新的最大 `open` Revision。

### abandon revision

- 可以将尚未写入 Payload 的准确 open Revision Control Record，或已经物化完整 Payload 的准确 `open` Revision，转为 `abandoned`；
- 必须保留准确原因；
- 必须保留 Revision Number；存在已经写入的实际内容时不得删除或改写；
- Revision 编号不得复用；
- `abandoned` Revision 不提供下游 Artifact Authority。

### resolve exact reference

只解析请求中指定的准确 Revision，不使用 `latest`、`current`、目录扫描、标题、内容相似度或排序作为 fallback，也不自动改用其他 Revision。

只有 Revision Control Record 的 Control Reservation 不得解析。解析必须验证 Artifact ID、Revision、State、Status、完整 Canonical Revision Payload、Manifest-Member closure、摘要、Gate、Context 和 Input；Member Reference 与 Item Reference 还必须按既有 Manifest 或固定模板解析到唯一对象。任一条件失败即解析失败。

### verify digest

必须同时验证：

- primary Blob SHA-256；
- 每个本地 Member SHA-256；
- Manifest 声明集合与实际本地 Member 集合完全一致。

只验证 primary Blob 不得将整个 Revision 判定为完整。

## Store 与领域 Contract 的关系

Store State 与 Artifact Status 是不同维度：

- `frozen` 只证明 Revision 已不可变，不等于 Artifact 内容合规；
- Artifact Gate 通过但 Revision 未 `frozen`，不可供下游使用；
- Revision 已 `frozen` 但 Artifact Gate 不满足，也不可供下游使用；
- `abandoned` 不提供 Authority；
- 只有 Revision Control Record 的 open Store Control Reservation 不提供 Artifact Authority；
- Store 不得重新计算、覆盖或替代 Artifact Status、Gate 或 Final Confirmation。

Artifact Store Spec 进入全部 v1.1 Canonical Artifact 的 Evaluation Contract Set，但不能替代 Core Spec、Project Context Spec、Phase Spec 或 Domain Spec。Store 完整性继续由 Core 现有 Check 与 Gate 语义承接，不新增平行 Artifact 表格、Front Matter 字段或 Gate。

## Spec 边界

- 本 Spec 不规定物理路径、存储结构、查询语言、表列、事务实现、迁移机制或运行时组件；
- Human Review View、导出内容和 Candidate Material 只属于执行支持，不是 Canonical Artifact Authority；
- 本 Spec 不定义 Store 选择、跨边界寻址、分布式协调或存储转换；
- 所有 Artifact、Reference、Evidence、Exception、Disposition、Check、Gate 与 Final Confirmation 业务语义继续由 Core、Project Context、Phase 和 Domain Spec 定义。
