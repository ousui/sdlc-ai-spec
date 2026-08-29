---
title: Artifact Store、Projection 与 Retention 架构决策
status: accepted
decision_date: 2026-08-29
target_spec: docs/v1.1
---

# Artifact Store、Projection 与 Retention 架构决策

## 1. 目的与边界

本文件确定后续 `docs/v1.1/` 必须采用的 Artifact Store、Projection、Runtime Workspace 与 Retention 架构。它是 Spec 编制输入，不是正式领域 Spec，不进入 v1.0 Artifact 的 `Evaluation Contract Set`，也不原地修改 `docs/v1.0/`。

本架构接受以下基本方向：

1. Artifact 是逻辑领域对象，不由文件路径、数据库表或 Provider 类型定义身份。
2. 一个逻辑 Workspace 在任一时刻只有一个 Canonical Artifact Store Authority。
3. VCS、SQLite、filesystem、temp 与 remote service 都只是可替换 Provider。
4. `.sdlc/` 是跨 Agent Runtime Workspace，不天然等于 Canonical Store。
5. Canonical Artifact 与所有 Projection 分离；Human Review View 可编辑，但不形成第二份 Authority。
6. v1.1 保留 v1.0 的领域字段、ID、Revision、Reference、Gate 与 Markdown/YAML Canonical Serialization，只解除其对固定文件布局的绑定。

本轮不定义 SQLite Schema、文件锁实现、MCP/API 协议、Provider 代码、初始化脚本或实际 `.sdlc/` Workspace，也不实现任何 Skill。

## 2. Layer Model

| Layer | Responsibility | Authority Boundary | Must Not Become |
|---|---|---|---|
| Domain Spec | 定义 Artifact 字段、ID、Revision、Reference、Evidence、Exception、Check、Gate、状态和兼容规则 | 领域语义的 Source of Truth | Provider API、数据库 Schema 或固定路径说明 |
| Canonical Artifact | 一个 Artifact Lineage 中由 Store 管理的权威 Revision 内容；Frozen Revision 是不可变 Snapshot | Artifact 内容、稳定 ID、Revision、Gate 与 Final Confirmation 的 Authority | Review View、查询索引或导出副本 |
| Artifact Store | 管理 Workspace 内 Artifact Namespace、Revision 状态、Canonical Blob、Supporting Members、完整性和 Authority Binding | 当前 Workspace 的唯一 Canonical Authority | 某个固定目录名或特定数据库产品 |
| Artifact Resolver | 将 Workspace 内短 Reference 或跨 Store Locator 解析到准确 Revision，并验证 Authority、状态、摘要和兼容性 | 解析结果与当前 Canonical Store Binding | `latest/current` 查找器、路径猜测器或 fallback 路由器 |
| Runtime Workspace | 保存运行配置、Provider Binding、非权威缓存、Projection 与 host/session 协调数据 | 只有明确标记为 Provider-owned canonical data 的成员可具备 Authority | 默认 Canonical Store 或领域 Artifact |
| Projection | 从准确 Canonical Revision 派生的机器视图、人工评审视图或导出视图 | 仅对“该视图由哪个 Source 派生”提供 Provenance | Canonical Artifact、Final Confirmation 或下游 Input Authority |
| Provider | 实现 Artifact Store Contract 的技术适配层 | 只能实现 Store 语义，不能重定义领域语义 | 新的 Artifact Contract 或隐式降级策略 |
| Retention Policy | 决定 Canonical data、Projection、cache 与 tombstone 的保存期限、删除条件和 Promote 要求 | Provider 生命周期与 Reference 可解析性的约束 | 所有数据永久保存的统一要求 |
| Export / Publish Target | 接收导出包、文档、报告、API Payload 或发布内容的外部目标 | 只对目标侧交付结果负责 | Canonical Store；除非经过显式 Import 与 Promote |

### 2.1 Authority 不变量

- Workspace 使用稳定的技术标识 `workspace-id`；它用于 Resolver/Store Binding，不新增或替代 Artifact 领域字段，也不等同于 Project Boundary 的业务定义。每个 `workspace-id` 必须恰好绑定一个 Project Boundary 的 Artifact Authority Namespace，同一 Project Boundary 同时只能有一个 active `workspace-id`。同一项目的本地 clone、Agent session 或 Runtime Workspace 必须共享该标识与 Binding，或明确保持 non-authoritative。
- `Canonical Store Binding` 至少记录 `workspace-id`、`store-instance-id`、Provider Profile、Authority Generation、Retention Policy 与 Binding State；不得包含 Secret。
- 同一 `workspace-id` 同时只能有一个 `active` Canonical Store Binding。缓存、镜像、Export 和 staged Import 都是非权威副本。
- `Canonical Store Binding` 自身由 Artifact Resolver 的 `Binding Authority` 管理，不由任意本地副本自我声明。单机 Profile 使用带排他锁和原子替换的本地 Binding record；共享 filesystem 必须使用共享 lease/fencing；共享 Git 使用受保护 remote ref 的 CAS；managed/remote 使用服务端 Workspace Authority Registry。`.sdlc/workspace.yaml` 在 shared/remote 场景只是带 Registry version 的 pointer/cache。
- 每个 Canonical write 必须携带 Binding Authority 发出的 Authority Generation 与 fencing token；Store 必须拒绝旧 Generation、过期 lease 或已被 Promote 封存的 writer，防止 split-brain。
- Provider 的表、路径、对象 Key、Git Commit 或远程 URL 都是物理定位信息；Artifact ID 与 Revision 不能从这些信息推断。
- Store 或 Projection 不得重算、覆盖或弱化 Domain Spec 定义的 Status、Gate、Final Confirmation 与现有摘要语义。

## 3. Artifact Store Provider Contract

Provider 可以采用不同持久化技术，但必须提供相同的可观察语义。不能满足某项必要保证的实现必须报告 `unsupported` 或明确失败，不得用其他 Provider 静默代替。

### 3.1 最小操作

| Operation | Minimum Behavior | Required Guarantee |
|---|---|---|
| Workspace Resolve | 从当前 Profile 指定的 Binding Authority 解析唯一 `Canonical Store Binding`，返回 `workspace-id`、Project Boundary binding、`store-instance-id`、Profile、Authority Generation、fencing token、Retention Policy 与能力声明 | Binding version 可验证、结果唯一、可读回、无路径猜测；无绑定、多个绑定或本地 cache 与 Registry 冲突时失败 |
| Artifact Allocate | 在绑定一个 Project Boundary 的 Workspace Authority Namespace 中分配稳定且唯一的 Artifact ID，并创建 Lineage 控制记录 | 保持项目范围唯一；原子分配；冲突重试但不覆盖、转移或复用 ID |
| Revision Allocate | 为指定 Lineage 分配已持久化最大 Revision 加 `1`，原子建立 Revision 控制记录、Base Revision、`open` State，以及包含固定 Front Matter 与专属章节骨架的主 Canonical Blob | 同一 Artifact 最多一个 `open`；编号不跳回、不删除、不复用；控制记录和主 Blob 均持久化并读回后才报告成功 |
| Read | 按准确 ID、Revision 或 Store metadata key 读取 Canonical Blob、Supporting Members 与控制记录 | Read-after-write；返回内容摘要、状态与 Authority Generation；不自动读取其他 Revision |
| Write | 仅对当前 `open` Revision 执行带 expected digest / generation 的条件写入 | 原子替换或等价事务；冲突返回明确错误；不得写 Frozen/Abandoned Revision |
| Freeze | 在全部领域最终化条件已经满足后，将准确 `open` Revision 转为 `frozen` | `open → frozen` 原子且幂等；冻结后内容、成员与领域控制字段不可变 |
| Abandon | 将无法继续的准确 `open` Revision 转为 `abandoned`，保存原因与必要 Evidence | `open → abandoned` 原子且幂等；编号和 Lineage 历史不得复用 |
| Exact Reference Resolve | 将准确 `<Artifact-ID>@<Revision>` 解析为当前 Authority 中唯一 Revision，并按 Domain Contract 验证 State、Status、成员、摘要、Gate、Context 与 Input 链 | 只接受明确 Revision；任一条件失败即失败，不回退到 `latest`、其他 Store 或缓存副本 |
| Query | 按 Artifact 类型、状态、Lineage、时间或索引字段检索候选记录 | 查询索引是可重建的派生数据；结果必须携带准确 Reference 与 digest，消费前仍执行 Exact Resolve |
| Export | 生成带 Source Locator、Reference、Revision Package Digest、Contract Binding、成员摘要与 Retention Mode 的不可变包或视图 | Export 不改变 Authority；只有显式取得 live-reference lease 才延长 Source 生命周期，自包含归档不依赖 Source 继续在线 |
| Import | 验证外部包的身份、Revision、内容、成员、摘要与兼容性后写入 staged namespace | Import 默认只产生非权威 staged copy；不得覆盖现有 Lineage 或自动成为 Canonical |
| Promote | 将已验证 staged Workspace 迁移为新的唯一 Canonical Store，并封存旧 Authority | 以 Authority Generation 做条件切换；成功后恰好一个可写 Authority，失败时不得出现双 Authority |
| Integrity Digest | 对完整 Canonical Blob 和 Supporting Members 提供可复核 SHA-256 | 原始字节可读回；摘要算法版本固定；不得用查询索引或 Projection 内容代替 |

`export`、`import` 与 `promote` 是三个不同动作：复制不是迁移，导入不是授权，只有 Promote 能改变 Canonical Authority。

### 3.2 Canonical integrity

Provider 必须分别保存并返回：

- Canonical Markdown/YAML Blob 的原始字节 SHA-256；
- 每个 Supporting Member 的原始字节 SHA-256；
- 一个版本化、确定性计算的 `Revision Package Digest`，覆盖主 Blob digest 与按稳定 Member ID 排序的成员 digest 集合。

`Revision Package Digest` 是 Store/Projection 完整性元数据，不替代 v1.0 已有的 `Control Input Digest`、`Check Set Result Digest`、Supporting Artifact Manifest digest 或 Gate Authority。其准确 envelope 与规范化算法由 v1.1 固定。

### 3.3 Concurrency and transaction

所有 Provider 必须提供以下可观察保证，内部可以使用数据库事务、文件锁与 journal、Git 协调记录或远程 CAS 实现：

- Artifact ID 分配、Revision 分配、条件写入、Freeze、Abandon 与 Promote 都有明确原子边界；
- 并发写入使用 expected digest、Authority Generation、lease 或等价 CAS，冲突不能用 last-write-wins 掩盖；
- 所有 Revision Allocation 都必须在控制记录和主 Canonical Blob 骨架均已持久化并读回后才返回成功；多成员 Revision 的后续物化只有在主 Blob、全部成员和控制记录均已持久化并读回后才能报告相应写入成功；
- 远程写操作必须支持 idempotency key 或等价幂等语义，超时后可查询真实结果；
- Provider 崩溃恢复不得复用已分配 ID/Revision，也不得把部分写入报告为成功；
- Promote 期间必须暂停或拒绝旧 Authority 的新写入，直到切换成功或完整回滚。

### 3.4 No silent fallback

当已绑定 Provider 不可用、摘要不匹配、事务能力不足或 Retention 不满足当前 Reference 生命周期时，Resolver 必须 fail closed。禁止：

- 自动从 `sqlite` 降级到 `temp` 或 `filesystem`；
- 远程不可用时把本地 cache 当成 Authority；
- 精确 Reference 失败时查找同 ID 的其他 Revision、Store、Git 分支或 Export；
- Import/Promote 失败后同时保留两个可写 Authority。

切换 Provider 只能由显式 Promote 完成。

## 4. Provider Profiles

| Profile | Durability | Sharing | Concurrency | Retention | Authority | Limitations |
|---|---|---|---|---|---|---|
| `temp` | 仅保证声明的 session/process 生命周期；崩溃后可丢失 | 单会话或单机临时协作 | Provider-local lock/CAS；不假定跨主机协调 | `session / ephemeral` | 可在明确单会话范围内暂任 Canonical | 不得承载跨会话 Reference；会话结束前有持久义务时必须 Promote |
| `sqlite` | Workspace-local durable file；事务提交后可读回 | 同一机器、同一 Workspace 的多个 Agent/process | ACID transaction；典型为多读单写，写冲突显式返回 | `workspace / local persistent` | 推荐的本地默认 Canonical Provider | 不适合无协调的多主机共享；需要备份、文件权限与锁语义；领域 Spec 不绑定 SQLite |
| `filesystem` | 由配置目录与底层文件系统保证 | 本机或受控共享文件系统 | 必须额外实现排他锁、atomic replace、journal 与恢复 | `workspace / local persistent` 或显式 managed filesystem | 满足 Contract 且被 Binding 指定时可为 Canonical | 跨平台原子性和网络文件锁较弱；移动/复制目录不能自动改变 Authority |
| `git` | 已提交对象由 Git 保留；远程耐久性取决于仓库策略 | 通过明确仓库和协作流程共享 | 需要 Provider 级分配/CAS；普通 merge 不能代替 Revision 事务 | 由 repository retention、GC 与 archive policy 决定 | 只有显式绑定的 Git Store 才是 Canonical | 工作树、分支名和“已跟踪文件”本身不构成 Authority；冲突、Secret、大二进制与提交延迟成本较高 |
| `mcp / remote-api` | 由受管服务声明并验证 | 团队、多主机、CI 与长期 Agent | 服务端 transaction/CAS、幂等请求和审计记录 | `managed / shared` | 精确 remote instance 与 workspace 被 Binding 指定时可为 Canonical | 依赖网络、认证、服务 SLA、导出能力和数据治理；本地 cache 不能在离线时替代 Authority |

默认选择规则：

- 本地、需要跨会话恢复且无需团队共享时，推荐 `sqlite`。
- 一次性、无跨会话 Reference、无持久 Evidence 义务的小任务可以显式选择 `temp`。
- 既有 `artifacts/**` 布局通过 `filesystem` Profile 支持。
- 需要 VCS 审计、代码评审或仓库分发时可以选择 `git`，但 VCS 不是强制持久化方式。
- 团队、多主机或集中治理场景使用 `mcp / remote-api`；网络失败不触发本地 Authority fallback。

## 5. Reference Model

### 5.1 Workspace 内 Reference

Canonical Artifact 继续使用现有语法：

```text
<Artifact-ID>@<Revision>
<Artifact-ID>@<Revision>#<Item-ID>
<Artifact-ID>@<Revision>/<Member-ID>
```

`<Artifact-ID>@<Revision>` 是 Project-scoped logical Reference，由与该 Project Boundary 一一绑定的 Workspace Authority Namespace 解析。Resolver 必须先解析当前 `workspace-id` 的唯一 Canonical Store Binding，再执行 Exact Resolve。它不携带路径、Provider 类型或 Store endpoint，因此 Provider 迁移不会改写 Canonical Artifact 内既有 Reference。

`Context Reference` 继续使用 `<CTX-ID>@<Revision>`。`latest`、`current`、目录路径、Git branch/tag、内容相似度和查询排序都不能替代准确 Reference。

### 5.2 跨 Store Artifact Locator

跨 Workspace、跨 Store、Export/Import、离线包或审计 Provenance 必须使用完全限定 `Artifact Locator`；仅有短 Reference 不足以确定 Authority 边界。规范化形态为：

```text
sdlc-artifact://<store-instance-id>/<workspace-id>/<Artifact-ID>@<Revision>?generation=<N>&digest=sha256:<64hex>
```

各路径段使用稳定、可编码的技术 ID；参数顺序和转义规则由 v1.1 固定。Locator 必须包含 Store Instance、Workspace、Authority Generation、准确 Artifact Reference 与 Revision Package Digest。

Artifact Locator 是 Resolver/transport metadata，不是新的领域 Artifact Reference，也不得写入当前只接受 Context、Artifact、Item、Member 或 VCS Reference 的字段。`vcs:<resource>@<immutable-revision>` 仍只定位产品内容，不能替代 Artifact Locator 或 Artifact Authority。

项目相对 `Authority Reference` 与仓库相对 `Spec Reference` 继续保留现有语法，但其解析根必须来自当前 Artifact 已绑定的不可变 Project Resource / Spec Snapshot；不得依赖执行主机的偶然路径或本地 cache。

### 5.3 Store switch and Promote

Provider 切换以整个 Workspace Authority Namespace 为默认 Promote 单位，保持短 Reference 语义稳定：

1. 读取当前 Binding 与 Authority Generation，阻止源 Store 新写入；
2. Export 完整 Namespace、Revision 状态、Reference closure、Canonical bytes 与 integrity metadata；
3. 在目标 Store Import 为只读 staged copy，逐一验证 ID、Revision、State、Reference 与 digest；
4. 在 Binding Authority 中以旧 Authority Generation 为前置条件执行 CAS，原子切换 Canonical Store Binding、递增 Generation 并签发新的 fencing token；
5. 目标 Store 只接受新 fencing token 并成为唯一可写 Authority；源 Store 拒绝新 Generation、标记为 sealed/non-authoritative archive，之后按 Retention 删除或保留；
6. 旧 Locator 只能返回明确 `moved / non-authoritative` 结果或历史副本，不得继续对外宣称 Canonical。

部分 Artifact 的 Export/Import 不构成 Workspace Promote，只能保持非权威归档、Projection 或 Candidate Material。不得把同一 ID/Revision 子集直接提升到另一个 Workspace，也不得重定向其内部短 Reference。Project Boundary 明确拆分时，应在新 Workspace 按领域 Identity/Revision 规则形成新的 Canonical Artifact，并用 Artifact Locator 保存跨 Workspace Provenance；具体拆分迁移规则由 v1.1 另行固定。任何情况下都不能让两个 Store 对同一 Project Boundary Namespace 的短 Reference 声称权威。

## 6. Canonical Serialization

v1.1 继续采用完整 Markdown/YAML Artifact Blob：

- 主 Artifact 仍是带固定 YAML Front Matter 的完整 Markdown 原始字节；
- Supporting Artifacts 保留原生格式，由稳定 Member ID、Media Type 与 SHA-256 绑定；
- `open` Revision 的 Canonical Blob 只能通过条件写入修改；`frozen` Revision 的 Blob 与成员不可变；
- Store 可以解析字段并建立查询、全文搜索、Reference graph 或状态索引，但这些索引必须可从 Canonical bytes 重建，不能成为领域 Authority；
- Export 到 filesystem 时必须能还原完整 Canonical Blob 和 Supporting Members，而不是只导出数据库字段的近似重建结果。

此决定保持现有字节级 digest、固定章节、字段顺序、Gate 与人工可读性。v1.1 不把全部 Artifact 改造成关系型字段模型。

完全 Schema-first / relational Authority 只作为未来 v2.0 候选。进入 v2.0 前至少需要独立证明：

- 字段级 Schema 能无损表达全部 Markdown 语义与原生成员；
- 可定义稳定 canonical rendering 和跨版本 migration；
- Round-trip 不改变 ID、Reference、顺序、空值、Evidence 与 digest；
- 旧 Markdown Artifact 可以无损导入且可复核；
- 人工阅读、diff、签署和离线交换的成本可接受。

## 7. Projection Contract

### 7.1 Projection types

| Type | Purpose | Editable | Consumer Boundary |
|---|---|---:|---|
| Downstream Projection | 为 Validator、Agent、索引器或执行器提供经过验证的结构化读取、缓存或 Canonical materialization | no | Consumer 必须验证 Source Reference 与 digest；不能把 Projection 自身登记为 Input Authority |
| Human Review Projection | 在 Markdown、HTML、Office、Google Docs 或 UI 中提供便于评审和批注的视图 | yes | 编辑只形成候选 Change Set；Review View 不能被下游 Artifact 消费 |
| Export Projection | 面向归档、交换、发布目标或外部系统生成包、文档、表格或 Payload | target-dependent | Publish 成功不改变 Canonical Authority；回流必须经过 Import 或 Round-trip |

### 7.2 Common projection metadata and hidden mapping

每个 Projection 必须具有可读回的非秘密 metadata；对于 Human Review Projection，该 metadata 可以保存在 sidecar、文档自定义属性或受控服务 metadata 中，不要求污染可见正文。最小集合包括：

- `projection-kind` 与版本；
- `source-workspace-id`、Source Artifact Locator 和准确 Source Reference；
- `source-revision-package-digest` 与 Source Evaluation Contract Set；
- 生成时间、Projection format/version 和 view digest；
- Canonical stable ID、章节、字段、表格行与 View element 之间的 hidden mapping；
- mapping digest、Round-trip capability 与最近一次 Import 状态。
- Export Projection 的 `retention-mode`、`reference-horizon`，以及适用时由 Source Store 签发的 lease ID。

Hidden mapping 只用于确定性定位，不是安全边界，也不能隐藏或替代领域内容。Mapping 丢失、重复、损坏或无法唯一映射时，View 仍可阅读，但必须降为 non-round-trippable Export；禁止按标题、位置或文本相似度猜测回写目标。

### 7.3 Source digest and stale view

- Projection 每次刷新、声称“当前”、评审提交或 Round-trip 前都要重新解析 Source Locator/Reference 并比较 Revision Package Digest。`self-contained-archive` 或 presentation 的纯离线阅读可以不连接 Source，但只能报告最后验证时间和历史 Provenance，不能声称当前 Authority 状态。
- Authority Generation 变化、Source digest 不匹配、mapping digest 不匹配或 Source 无法解析时，live/editable View 为 `stale`，禁止自动回写；完整性仍可由归档内摘要验证的 `self-contained-archive` 保持 historical snapshot 身份，但不因此成为当前 Authority。
- Frozen Source 本身不会变化；出现更高 Revision 时，旧 View 是准确的 historical view，但相对当前 Lineage 为 `superseded`。它可用于历史审阅，不能默认为当前修改基线。
- `stale` 与 `superseded` 是 Projection 状态，不改变 Canonical Artifact Status。

### 7.4 Round-trip import

Human Review View 的编辑只有在用户显式请求 Import、写入授权覆盖准确 Workspace 且 Source/mapping 校验通过时，才能进入 Canonical Store：

1. 读取 View metadata、hidden mapping、Source Reference 与 base digest；
2. 将可映射编辑转换为 Change Set，拒绝未知字段、身份重配、重复 ID 和无法表达的格式变化；
3. Source 仍为同一 `open` Revision 且 expected digest 匹配时，执行条件写入；内容变化使旧 Check、Gate Summary 与 Final Confirmation 失效；
4. Source 已 `frozen` 时，以其为 Base Revision 分配新的最大 `open` Revision；不得修改 Frozen bytes；
5. 编辑没有有效内容变化时报告 no-op，不创建空 Revision；
6. 产生冲突、Source 已移动或 Mapping 不完整时停止并输出冲突，不自动 rebase、合并或选择其他 Revision。

### 7.5 Edit versus approval

- 编辑、保存、接受 Track Changes、解决评论或完成 Review UI 流程，都不等于领域 Approval。
- Approval 只能由 Canonical Artifact Contract 定义的 Final Confirmation 完成，并准确绑定当前 Canonical Revision、Control Input Digest、Evaluation Contract Set 与 Check Set Result Digest。
- Round-trip 只生成或更新 `open` Revision；它不能直接写成 `ready / ready_with_exception`，不能 Freeze，也不能伪造人工 Authority。
- 对 Frozen Revision 的任何内容或控制字段修改都创建新 Revision。仅改变非权威 View 的排版不创建 Revision。
- 下游 Resolver、Skill 和 Phase 不得把 Human Review Projection、Office 文档、Google Doc、HTML 或 Export Payload 当作 Artifact、Context 或 Input Authority。

### 7.6 Export retention modes

Export 必须显式选择一种 Retention Mode，不能仅凭文件存在推断 Source 保存义务：

| Mode | Source Dependency | Retention Effect | Authority |
|---|---|---|---|
| `live-reference` | 依赖 Source Locator 持续可解析 | 必须在 Export 时取得明确 `reference-horizon` 与 Store lease；lease 有效期内 pin 被引用的完整 Reference closure | Source Store 仍是唯一 Authority |
| `self-contained-archive` | 包含 Canonical bytes、Supporting Members、digest、状态与足以独立验证的不可变 Contract package | Export 成功并读回后不 pin Source；归档自身按目标 Policy 保存 | 只是可验证历史副本；需成为 Canonical 时仍执行 Import/Promote |
| `presentation` | 仅用于阅读或发布，Locator/digest 只提供 Provenance | 不延长 Source 生命周期；Source 过期后明确显示不可重解析 | 永远不是 Artifact Authority |

未取得 lease 的 live-reference Export 必须标记为 non-durable，不能承诺跨 session 或长期可解析。撤销 lease、缩短 horizon 或删除自包含归档属于显式 Retention 动作，不能由 Provider 静默完成。

## 8. Runtime Workspace

推荐的本地 Runtime Workspace 结构如下；这是 Profile-aware 布局，不是所有 Provider 都必须创建全部成员：

```text
.sdlc/
├── workspace.yaml
├── store.sqlite3
├── connections/
│   └── remote.yaml
├── projections/
│   ├── downstream/
│   ├── review/
│   └── export/
├── cache/
└── runtime/
    ├── locks/
    └── sessions/
```

规则：

- `workspace.yaml` 保存非秘密 Workspace ID、Project Boundary binding、Canonical Store Binding、Provider Profile、Retention Policy、Binding Authority pointer/version 与能力声明；绑定无法解析时 fail closed。
- 对 `temp`、`sqlite` 和单机 filesystem，`.sdlc/workspace.yaml` 可以在排他锁、原子替换和 Provider 内 Generation 交叉校验成立时作为本地 Binding Authority。对共享 filesystem、共享 Git 和 `mcp / remote-api`，它只能是 cache/pointer，权威 Binding 分别来自共享 lease/fencing record、受保护 remote ref CAS 或服务端 Workspace Authority Registry。
- `sqlite` Provider 可以把 `.sdlc/store.sqlite3` 及其事务附属文件作为 Provider-owned Canonical data。Authority 来自 Binding 和 Provider Contract，不来自 `.sdlc/` 路径本身。
- `temp` Provider 可以完全位于系统临时目录，不要求创建 `.sdlc/store.sqlite3`；若需要跨 session 使用，先 Promote。
- `mcp / remote-api` 只在 `.sdlc/` 保存非秘密 endpoint、remote workspace/store ID、TLS/Provider metadata 与可删除 cache。Token、Cookie、私钥和长期 Credential 使用宿主凭据机制，不写入 `.sdlc/`。
- `projections/`、`cache/`、`runtime/` 以及任何 host-specific 目录都不是领域 Authority，不得保存唯一 Canonical bytes、唯一 Evidence 或唯一 Final Confirmation。
- filesystem/git Provider 的 Canonical root 由其 Binding 明确配置；不能通过扫描 `.sdlc/`、`artifacts/**` 或 Git tracked files 猜测当前 Authority。

### 8.1 Git ignore strategy

初始化流程必须根据已选 Provider 显式生成、展示并验证 Git ignore 策略，不得假定整棵 `.sdlc/` 永远跟踪或永远忽略：

- `cache/`、`runtime/` 和默认本地 Projection 应忽略；需要评审或发布的 Projection 通过显式 Export 管理；
- `sqlite` 数据库、WAL/SHM 与本地备份默认忽略，不把数据库提交当作 Git Provider；
- non-secret remote connection metadata 是否跟踪由项目策略明确决定；Secret 即使被忽略也不得写入；
- `git` Provider 只跟踪其明确配置的 canonical payload 与控制记录；不能用宽泛的 `.sdlc/**` 规则替代 Provider 配置；
- 初始化结束必须读回 `.gitignore` 与实际 `git status`，报告哪些 Provider data、Projection 与 runtime files 会被跟踪。

## 9. Retention

### 9.1 Policy profiles

| Policy | Intended Use | Minimum Lifetime | Delete Boundary | Promote Boundary |
|---|---|---|---|---|
| `session / ephemeral` | Temp Provider、小型单会话任务 | 当前声明 session 及其未完成写入 | 没有跨 session Reference、没有待保留外部 effect/Evidence、没有未导入 Review edits 时可在 session 结束删除 | 产生跨 session/downstream Reference、需要恢复、需要团队交接或正式 action Evidence 前必须 Promote |
| `workspace / local persistent` | SQLite/filesystem、本地长期工作 | Workspace 有效期以及全部有效 Reference 的可解析期 | Workspace 明确关闭、引用义务结束且没有未迁移 Authority 后可删除；派生 cache/view 可更早删除 | 进入多主机/团队场景、移除本地 Workspace、或 Reference 生命周期超过本地 Provider 保证前必须 Promote |
| `managed / shared` | MCP/remote API、团队与集中治理 | 服务声明的 retention、审计和全部有效 Reference 期限中的较长者 | 满足团队/法规策略、Reference closure、归档/迁移和明确授权后可删除 | 更换服务、租户或治理边界时按完整 Workspace Promote；普通 Export 不算 Promote |

### 9.2 Deletion rules

- Projection 与 cache 是派生数据，可在 Source 仍可解析时重建；但包含尚未 Import 的人工编辑时，删除前必须明确告知并先导出 Change Set 或获得放弃决定。
- 在活跃 Workspace 中，已分配 Artifact ID、Revision 编号和终态 tombstone 不能因清理 payload 而复用。
- `frozen` Revision 只要仍被任何保留中的 Context、Input、Item、Member、Evidence、Authority，或尚在 `reference-horizon` 内的 live-reference Export 引用，就不得删除或使其静默不可解析。自包含归档和 presentation Export 不 pin Source。
- `open` 或 `abandoned` 数据只有在没有正式 action/effect Evidence 保留义务、没有外部 Reference、且当前 Policy 明确允许时才能清理；若保留 Lineage，至少保留不可复用编号和准确终态。
- 整个 Workspace 在 Reference horizon 已关闭、外部义务已完成并获得 Policy 所需授权后可以正式 retire；本架构不强制所有 Artifact 永久保存。
- 删除或过期必须返回明确的 `retention_expired / workspace_retired / non-authoritative` 结果；Resolver 不得用 cache、Export 或另一个 Store 静默补位。

### 9.3 Downstream Reference obligation

创建或冻结带下游 Reference 的 Artifact 前，Store 必须证明被引用 Revision 的 Provider 生命周期至少覆盖 Consumer 所需的可解析期。无法保证时只有两种合法结果：

1. 在写入/冻结下游 Reference 前把完整 Reference closure Promote 到满足期限的 Provider；
2. 停止并报告 Retention 不足。

不能先发布长期 Reference，再依赖 Temp Store、开发机目录或未声明保留期的 Export。Provider 可以使用 retention lease、reference graph 或 managed policy 实现该保证，但其索引只用于执行删除 Gate，不改变 Canonical Artifact Reference 语义。

## 10. Compatibility and v1.1

推荐创建 `docs/v1.1/` Spec Snapshot，而不是修改 `docs/v1.0/`，原因如下：

| Preserved | v1.1 Architectural Change |
|---|---|
| Artifact 与 CTX 的现有字段、枚举和领域语义 | 将物理 Store 与领域 Artifact 解耦 |
| Artifact ID、CTX ID、Revision、Context/Artifact/Item/Member Reference 语法 | 增加 Workspace-scoped Resolver 与跨 Store Locator |
| `open / frozen / abandoned`、Status、Evidence、Exception、Check、Gate 与 Final Confirmation | 由 Provider 事务实现相同可观察保证 |
| 完整 Markdown/YAML Canonical Blob、原生 Supporting Members 与现有 digest 语义 | Store 增加可重建派生索引和 Revision Package Digest |
| Frozen Revision 不可原地修改；非权威阅读视图可重新渲染 | 正式定义 editable Human Review Projection 与 Round-trip |
| 精确 Reference 失败即失败，不使用 `latest/current` | Provider 不可用时禁止 silent fallback，并定义 Promote |

v1.0 当前把 `artifacts/000-ctx/`、`artifacts/100-req/` 至 `artifacts/600-rls/` 及 Revision Index 目录直接写入 Resolver。v1.1 将该布局登记为 `filesystem` Provider 的兼容 Profile，不再把它规定为所有 Artifact 的唯一物理形式。

如果 v1.1 只改变 Store/Resolver/Projection/Retention 而不改变 Artifact 字段与语义，应继续使用 `sdlc-ai-spec/artifact/v1`、`sdlc-ai-spec/project-context/v1` 和现有 Reference/Gate Contract，仅由新的 `Evaluation Contract Set` 绑定 v1.1 Spec Snapshot。若 v1.1 编制过程中发现必须改变这些领域 Contract，必须另行作出兼容性决定并在新版 Core 中明确登记，不能在 Provider 设计中隐式改变。

现有 v1.0 filesystem Artifact 可以按原始字节、ID、Revision、State、成员和摘要导入 v1.1 filesystem Provider；迁移到 SQLite 或 Remote Provider 时必须经过 Import 验证与 Workspace Promote，不能通过复制后同时保留两份 Authority。

## 11. Current decision and next boundary

本架构决策已经完成，但它不等于 v1.1 Domain Spec、Provider 实现或运行验证。下一工作包只负责依据本文件创建 `docs/v1.1/` Spec Snapshot，并把 Store、Resolver、Projection、Retention 与兼容关系写入正式 Source of Truth。

在 v1.1 Snapshot 完成前：

- 不批准或实现 `sdlc-project-context`；
- 不依据现有固定 `artifacts/**` 路径假设实现 Persistence；
- 不创建 SQLite Schema、Provider、MCP/API、Skill、Script 或实际 `.sdlc/` Workspace；
- 不把本架构文档加入 v1.0 Artifact 的 `Evaluation Contract Set`。
