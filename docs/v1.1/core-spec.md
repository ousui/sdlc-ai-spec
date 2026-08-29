---
title: sdlc-ai-spec 核心 Spec
status: draft
version: "1.1"
scope: 已确认的通用术语、Project Context、生命周期与 Artifact Contract
---

# sdlc-ai-spec 核心 Spec

> 本文件只定义明确登记的 Core Contract；未登记内容不构成隐含要求。

## 核心原则

- Spec 只判断产物、证据和 Gate 是否符合要求，不区分由人工还是 AI 完成。
- Artifact 可以由人工、AI 或其他执行主体生成和检查；Spec 不限定作者。业务取舍、主观产品判断、Exception、风险接受及外部动作授权仍由有责任的人工或外部权威承担；满足本节严格边界时，Artifact 的最终合规确认可以委托给独立 Reviewer。
- 每个 Phase 使用固定模板和字段，允许自然语言不同，但不允许结构、枚举和语义边界漂移。
- 缺少必要输入时进入 `waiting_input`，不得猜测事实后生成形式上的合格产物。
- Lifecycle Profile 只提供默认建议，逐项 Disposition 才是最终执行依据。
- 在满足可追踪、可验证和可判定的前提下，优先使用最少的概念、文件、字段和状态；现有结构能够闭合的问题不得新增抽象。

## 术语

| 中文 | English | 固定写法 | 含义 |
|---|---|---|---|
| 规范、标准 | Specification | `Spec` | 本项目统一使用的约束与产物定义 |
| 阶段 | Phase | `Phase` | 生命周期中的固定控制位置 |
| 活动 | Activity | `Activity` | Phase 内部的命名工作单元，不建立独立生命周期位置或 Artifact 身份 |
| 步骤 | Step | `Step` | Activity 或 Artifact 内按语义顺序组织的动作，不等同于 Work Item |
| 输入 | Input | `Input` | 当前 Phase 使用的上游产物或原始资料 |
| 范围输入 | Scope Input | `Scope Input` | 直接贡献当前交付 Requirement、Design 或 Delivery Scope 的 Input；仅提供前置结果、返工或证据的控制输入不属于此类 |
| 输出 | Output | `Output` | 当前 Phase 形成的结果 |
| 产物 | Artifact | `Artifact` | 可保存、引用和验证的输出 |
| 证据 | Evidence | `Evidence` | 支撑结论、Gate 或 Exception 的可追溯材料 |
| 门禁 | Gate | `Gate` | 判断 Artifact 能否进入下游的检查结论 |
| 生命周期配置 | Lifecycle Profile | `Profile` | 为常见交付路径提供的默认处置建议 |
| 处置 | Disposition | `Disposition` | Phase 或 Phase Spec 明确注册的子义务的实际处理方式 |
| 豁免 | Exception / Waiver | `Exception` / `waived` | 适用但经授权主动跳过的事项 |
| 修订号 | Revision | `revision` | 同一 Artifact 的编号化内容版本；冻结后不可变 |
| Artifact 存储 | Artifact Store | `Artifact Store` | 保存完整 Canonical Revision Payload 并执行准确 Reference 解析的逻辑 Authority |
| Artifact 沿袭 | Artifact Lineage | `Artifact Lineage` | 同一稳定 Artifact ID 的全部 Revision 历史 |
| 修订控制记录 | Revision Control Record | `Revision Control Record` | 保存 Revision 分配、State、Base Revision、时间与放弃原因的逻辑记录 |
| 修订快照 | Revision Snapshot | `Revision Snapshot` | 已冻结且可被准确解析的 Artifact Revision |
| 规范修订载荷 | Canonical Revision Payload | `Canonical Revision Payload` | primary Canonical Blob、全部本地 Member、稳定身份、元数据、摘要和 Manifest 闭包组成的完整 Revision 存储单元 |
| 执行前清单 | Pre-execution Checklist | `Pre-execution Checklist` | 正式 action 前必须已绑定规则、持久化并读回的当前 Phase 固定字段集合；不是独立 Artifact、状态或 Gate |
| 质量保证 | Quality Assurance | `QA` | 由 Check Set、Evidence 和 Gate 承载的跨 Phase 质量保证，不作为独立 Phase |
| 验证与确认 | Verification & Validation | `VFY` | 判断产物是否符合上游要求，并满足预期用途 |
| 发版 | Release | `RLS` | 将准确的已验证结果发布到约定目标，确认目标侧状态并形成发版结论 |
| 工作项 | Work Item | `WI` | PLN 中可执行且可独立确认完成的最小计划单元 |
| 项目上下文 | Project Context | `CTX` | Lifecycle 开始前建立并由各 Phase 准确绑定的项目级共享基线；不是 Phase |

## Spec 层级

规范层级固定为：

```text
Core Spec
├── Artifact Store Spec
├── Project Context Spec
└── Phase Spec
    └── Domain Spec
```

- Core Spec 定义全部 Artifact 共用的身份、Revision、状态、引用、Evidence、Exception 和 Gate 语义；
- Artifact Store Spec 定义完整 Canonical Revision Payload、Revision Control Record、逻辑状态转换与准确 Reference 解析；
- Project Context Spec 定义项目级共享基线及其固定 Artifact Contract；
- Phase Spec 定义 Lifecycle 各控制位置的固定模板、专属字段和增量 Check；
- Domain Spec 只补充所属 Phase 已注册领域的固定结构和 Check，不建立新的 Lifecycle 位置；
- Project Context 与 Lifecycle Artifact 都受同一 Core Spec 约束，但使用各自固定的 Front Matter 和专属 Spec；
- 规范的阅读顺序由规范索引声明，不使用基础 Spec 文件名模拟 Lifecycle Phase。

## 生命周期

Project Context 位于 Lifecycle 之前，在当前 Project Boundary 的 Canonical Store 中维护唯一 CTX Lineage，但不进入 Phase 枚举、Lifecycle Profile 或 Phase Disposition。Lifecycle Artifact 必须准确绑定一个可解析的 CTX Revision，具体结构与刷新规则由 Project Context Spec 定义。

本 Spec 的研发与变更交付控制位置固定为：

```text
REQ → DSN → PLN → IMP → VFY → RLS
```

| 位置 Order | Phase | Code | Artifact Type |
|---|---|---|---|
| 100 | Requirement | `REQ` | Requirement Artifact |
| 200 | Design | `DSN` | Design Artifact Set |
| 300 | Plan | `PLN` | Plan Artifact |
| 400 | Implementation | `IMP` | Implementation Artifact |
| 500 | Verification & Validation | `VFY` | VFY Artifact |
| 600 | Release | `RLS` | Release Artifact |

位置数字仅用于固定展示顺序，不作为 Artifact 身份、存储定位或依赖依据。生命周期按上述位置逐项作出处置决定；下游发现问题时可以返回上游，形成新的 Revision 后继续向前。

这是一条 Artifact 与 Gate 控制流，不表示研发活动只能线性执行一次。活动可以在控制位置之间并行、迭代或递归；维护、运行反馈和新问题重新进入 REQ。长期监控、告警、值守、故障处置以及产品退役不属于每次变更的固定 Lifecycle Phase。

VFY 是证据汇总和结论控制位置；Verification 和 Validation 可以在此前各 Phase 发生，顶层 Method Type 统一为 Inspection、Analysis、Demonstration 和 Test，不要求集中到 IMP 之后才开始。Review、人工或自动化方式及 Test Level 由 VFY Phase Spec 归入对应 Method 或 Method Detail。

`PLN` 表示依据已确认设计形成实施计划，不表示项目启动前的战略规划。

## Artifact 格式

Project Context 与每个独立执行的 Phase 都生成一个 primary Canonical Markdown/YAML Blob：

- primary Canonical Blob 使用固定 Markdown 模板；
- 少量机器字段使用 YAML Front Matter；
- 图片、OpenAPI、Schema、源代码、日志和报告保留原生格式，作为 locally owned Supporting Member 或外部不可变 Reference；
- JSON 可以由验证器临时生成，但不要求人工编写或提交；
- XML 不作为通用 Artifact 格式。

## Lifecycle Artifact Identity

Lifecycle Artifact ID 格式固定为：

```text
<PHASE>-<YYYYMMDDHHMMSS>-<NN>
```

示例：

```text
REQ-20260823143025-01
DSN-20260823150010-01
```

规则：

- 日期时间为 Artifact 首次创建时间；
- 时间使用项目配置时区，未配置时使用 UTC；
- `NN` 为同一秒内从 `01` 开始的顺序号；
- ID 在项目范围内唯一；创建时先分配并持久化 ID，再生成内容；
- 发生并发冲突时递增 `NN` 后重新分配，不得覆盖已有 Artifact；
- 重新执行必须携带已有 Artifact ID，不重新分配；只有满足下述“身份命名空间恢复”全部条件时，才允许为同一 Scope 和义务分配新的恢复 Artifact ID；
- ID 一经分配不得修改、转移或复用；
- primary Canonical Blob 必须由 Artifact ID 和 Revision 唯一绑定；
- 不依赖目录位置、文件顺序、标题或内容相似度识别 Artifact；
- 同一文字输入不代表同一业务身份，未指定 ID 时不得自动覆盖疑似相同 Artifact。

身份命名空间恢复 Identity Namespace Recovery 只处理一种不可原地修复的控制故障：同一 Artifact 已物化的历史 Revision 将同一稳定 Item、Member 或 Evidence ID 分配给不同逻辑角色，且历史冻结或状态改变 Evidence 不能改写，使任何后续 Revision 都无法同时满足稳定 ID Contract。它不是普通重试、内容返工或规避失败 Gate 的方式。

- 旧 Artifact 必须以新的最大 Revision 或已经存在的当前最大 Revision 准确记录冲突、实际状态和 `fail` Gate，并在 Revision Control Record 中标记为 `abandoned`；既有状态改变和 Evidence 不得删除；
- 新 Artifact 使用新的唯一 ID、Revision 1 和 `Base Revision=None`，在 Evidence 中准确引用旧 Artifact 的最终失败 Revision、Revision Control Record 摘要和不可修复原因；旧 Artifact 不是 Input，也不提供 Gate、Final Confirmation、Result、Conclusion 或其他 Authority；
- 新 Artifact 必须保持相同 Phase、完整 Scope、义务和适用目标，重新绑定全部有效直接 Input，并按当前 Contract 重新持久化、读回和执行全部适用控制；已有执行对象状态只能作为重新捕获的 Baseline，不得伪装成新 Artifact 的 Result；
- 同一旧 Artifact、Phase、Scope 和适用目标只能分配一个恢复 Artifact ID。恢复 Artifact 后续失败时继续创建其新最大 Revision，不得再次分配新 ID；
- 若冲突可以通过不改写历史的新 Revision、未使用 ID 或准确 Member 延续解决，则不得使用本恢复路径。

引用语法固定为：

| 引用类型 Reference Type | 格式 Format | 用途 Purpose |
|---|---|---|
| Context 引用 Context Reference | `<CTX-ID>@<Revision>` | Lifecycle Artifact 绑定一个准确 Project Context Revision |
| Artifact 引用 Artifact Reference | `<Artifact-ID>@<Revision>` | 引用一个准确 Artifact Revision |
| Item 引用 Item Reference | `<Artifact-ID>@<Revision>#<Item-ID>` | 跨 Artifact 引用内部 Item |
| Member 引用 Member Reference | `<Artifact-ID>@<Revision>/<Member-ID>` | 引用 Artifact Set 成员或 Supporting Artifact |
| Spec 引用 Spec Reference | `<仓库相对 Spec 路径>@sha256:<64 位小写十六进制>` | 在 Spec 版本解析机制未定义时绑定准确规则内容 |
| VCS 定位符 VCS Locator | `vcs:<resource>@<immutable-revision>` | 在 Phase Spec 明确允许时定位版本控制系统中的不可变产品内容 |

裸 Item ID 只允许在同一 Artifact 或 Artifact Set 内使用；跨 Artifact 的 Requirement、Decision、Exception、Evidence 和 VFY Point 必须使用完整 Item Reference。

VCS Locator 的 `resource` 必须是项目内唯一且可解析的版本化资源标识，`immutable-revision` 必须是该系统的完整不可变对象 ID；分支、可移动 Tag、`latest`、`current` 或工作树名称不满足该格式。VCS Locator 只标识产品内容，不替代 Lifecycle Artifact Reference。

Spec 路径使用 `/` 分隔，不得以 `/`、`./` 或 `../` 开头；同一文件必须使用仓库根目录下的唯一相对路径。

所有由 Project Context Spec、Phase Spec 或 Domain Spec 定义、可被引用的 Item ID 都遵循同一稳定性规则；Project Context 与 Phase Spec 登记公共前缀，Domain Spec 的固定模板登记专属前缀：

- ID 在 Artifact 或 Artifact Set 内唯一，分配后不得因排序、插入、改名或 Revision 变化而改变；
- 删除或替代 Item 时不得把原 ID 分配给新语义，历史 Revision 继续保存原 Item；同一语义跨 Revision 保持原 ID，语义被替代时创建新 ID；只有当前专属 Spec 已定义来源或替代引用字段且确有替代项时，新 Item 才引用旧 Item；
- Project Context 或 Phase Spec 只登记前缀、格式和专属字段，不得放宽上述规则。

引用字段使用固定集合语法：

- 字段名或语义为单数 `Reference` 时只允许一个合法引用；
- 字段名或语义为复数 `References` 时，以英文逗号加一个空格 `, ` 分隔，去重后按完整引用字符串升序排列；
- 空集合写 `None`；只有当前专属 Spec 明确允许该字段不适用时才写 `N/A`；`None` 或 `N/A` 不能与其他引用并列；
- 同一 Artifact 内允许的裸 Item ID 仍按相同集合语法排序；Markdown 链接、分号、换行或 `<br>` 不得作为 Reference Set 的替代格式。

## Lifecycle Artifact Front Matter

Lifecycle Artifact 的字段和顺序固定：

```yaml
---
contract: sdlc-ai-spec/artifact/v1
phase: REQ
id: REQ-20260823143025-01
revision: 1
status: draft
context: CTX-20260828143025-01@1
profile: full
inputs: []
---
```

| 字段 Field | 规则 Rule |
|---|---|
| `contract` | 当前 Artifact Contract 版本 |
| `phase` | `REQ / DSN / PLN / IMP / VFY / RLS` |
| `id` | 稳定 Artifact ID |
| `revision` | 正整数，从 `1` 开始 |
| `status` | 固定 Artifact 状态 |
| `context` | 准确且可解析的 Context Reference；不得使用路径、宿主适配文件、`latest` 或 `current` 替代 |
| `profile` | 当前 Lifecycle Profile |
| `inputs` | 上游 Artifact Reference 列表；去重后按完整引用字符串升序排列，空集合固定为 `[]` |

`context` 是 Lifecycle Artifact 的项目级共享基线，不属于业务或控制 Input，不能放入 `inputs`。当前 Core Snapshot 只接受 `contract: sdlc-ai-spec/project-context/v1` 的 CTX Revision；未来 Contract 版本必须由 Core 明确登记兼容关系后才能绑定。Project Context Artifact 使用 Project Context Spec 定义的独立 Front Matter，不使用 `phase`、`context`、`profile` 或 `inputs`。

固定表格的行顺序遵循以下规则：有 `ID` 或 `Member ID` 主键时按稳定 ID 升序排列；当前专属 Spec 已定义固定 Catalog 顺序时按 Catalog 顺序；业务语义依赖先后关系时必须使用显式 `Step` 或 `Order` 字段并按该字段排列。不得仅为排版重排已分配 ID。

## Revision

- 新 Artifact 从 `revision: 1` 开始。
- 新 Revision 固定为该 Artifact 已持久化最大 Revision 加 `1`；成功分配必须通过 Artifact Store 建立 Revision Control Record 与最小 Canonical Revision Payload 骨架，并完成 read-after-write；
- 发生并发冲突时重新读取最大 Revision 后再分配，不得覆盖、跳回或复用已有 Revision；
- `draft` 或 `waiting_input` 期间修改，不增加 Revision。
- `failed` Artifact 在形成可供下游使用的快照前修正，可以沿用当前 Revision；修改后当前 Check、Gate Summary 和 Final Confirmation 立即失效并重置为 `pending`，Status 按阻塞事实回到 `draft` 或 `waiting_input`。Core 不要求保存 open Revision 的中间失败尝试；确需留痕时登记为 Evidence。
- `ready` 或 `ready_with_exception` Revision 冻结后，任何内容、Context Reference、Input、Manifest、Spec Binding、Check、Gate Summary、Final Confirmation 或 Status 需要更新时，都必须先创建新 Revision 并回到 `draft`；不以“语义是否变化”作为例外。
- 下游使用 `Artifact ID@Revision` 精确绑定上游。
- 当前交付范围选择采用新的上游 Revision 时，仍绑定旧 Revision 的相关下游 Artifact 必须重新检查；仅仅存在一个新 Revision，不会使既有精确引用自动失效。
- `ready` 或 `ready_with_exception` Revision 必须形成不可变快照，且能够通过 `Artifact ID@Revision` 唯一解析；不得只保留 primary Canonical Blob 或被后续 Revision 覆盖的阅读视图。
- 快照冻结后不再原地修改；排版或文字修正也形成新 Revision，非权威阅读视图的渲染变化除外。

### Artifact Store 与准确 Reference 解析

每个 Artifact ID 对应一个 Artifact Lineage。每个 Revision 由一个 Revision Control Record 和一个完整 Canonical Revision Payload 表达。Revision 在 Reference 和 Front Matter 中继续使用不补零的正整数，不建立 `current`、`working` 或 `latest` 别名。

Revision Control Record 保留以下既有字段和语义：

```markdown
| Revision | State | Base Revision | Allocated At | Frozen At | Abandon Reason |
|---|---|---|---|---|---|
| 1 | open | None | 2026-08-23T10:00:00+08:00 | N/A | N/A |
```

Canonical Revision Payload 必须包含 primary Canonical Blob 原始字节、全部 locally owned Member 原始字节、每个 Member 的稳定身份、Canonical Member Name 或等价稳定名称、Media Type、逐 Blob / Member SHA-256，以及能唯一闭合实际本地 Member 集合的既有 Canonical Manifest 内容。外部不可变 Reference 不要求复制为本地 Member，但其准确 Reference、摘要和访问边界必须保留。

规则：

- `State` 只允许 `open`、`frozen` 或 `abandoned`；合法变化只有 `open → frozen` 和 `open → abandoned`，终态不能重新打开；
- 一个 Artifact 同时最多存在一个 `open` Revision；新 Revision 是 Lineage 内已持久化最大 Revision 加 `1`；
- `Base Revision` 为 `None` 或同一 Artifact 已存在的 `frozen` Revision；它只定位新 Revision 的内容来源，不是 Input 或 Authority；选择旧 Base 仍必须创建新的最大 Revision；
- Revision 分配只有在 Artifact Store 通过 `allocate revision` 建立 Revision Control Record 与最小 Canonical Revision Payload 骨架，并读回验证后才成功；写入必须通过 `write open revision` 在一个 Store transaction 中一致保存 primary Blob、全部本地 Member、Member 元数据和 Manifest，不允许部分成功；
- Phase 执行控制若在 Core 分配前预留目标 Revision，该预留号必须等于当前已持久化最大 Revision 加 `1`，且不得跳过或复用。正常执行前必须完成 `allocate revision`、`write open revision` 与 `read revision`；物化失败只能对准确的 `open` Revision 执行 `abandon revision`，任一步失败时继续保留执行权并重试恢复；
- `open` 与 `frozen` Revision 必须具有完整 Canonical Revision Payload。只有证明未改变执行对象状态时，不完整的 `open` Payload 才可直接放弃且不得被解析为 Artifact；状态改变已经发生或无法排除时，必须先保留原始日志或目标读回，后续同 Phase 恢复 Revision 必须承接这些 Evidence、记录实际状态，并按该 Phase 规则选择或恢复 Baseline 后再执行；
- `Artifact Gate Summary.Evaluation Contract Set` 在 `Gate Result=pending` 时就是当前 `open` Revision 的 Spec Binding。正式 action 前必须非空、随完整 Payload 持久化并读回；工具默认快照只可校验尚未开始正式 action 的草稿结构，不能为既有正式 Result、Evidence 或 Target effect 事后选择规则版本；
- 会改变产品、受控验证环境或测试数据、Release Target、外部系统等执行对象状态，或形成正式 VFY Evidence 的 Phase action，只能在当前 `open` Revision 的完整 Payload 和 Phase Spec 定义的 Pre-execution Checklist 已持久化并读回后开始。该 Checklist 复用当前 Phase 的固定字段，不默认新增平行状态或表；此前输出只能作为候选材料，事后补录不能追溯满足该控制。为建立此前提而进行、且已由 Core 或 Phase 单独规定顺序的 Store Control Record 和 Claim 等控制写入不属于本条所称执行对象状态改变，仍须遵守各自原子性和顺序；
- Pre-execution 读回复用 Evidence 和 Supporting Artifact Manifest 保存不可变读回内容，至少记录 Artifact Reference、Observed At、准确 Evaluation Contract Set 和 Phase 固定 Checklist 的字段和值，并在 Manifest 登记 Member SHA-256。Checklist 或 Contract Set 变化后，旧读回内容下的正式输出不得继续作为当前 Result 或 Evidence，必须重新读回并重执行或独立复核；已经发生的状态改变仍是事实，不能降为候选材料；
- 时间使用 RFC 3339；`abandoned` 必须填写原因，其他不适用字段写 `N/A`；
- Revision Control Record 是 Artifact Store 控制元数据，不属于 Lifecycle Artifact，不进入 Artifact Set Manifest、Evidence 或 Gate Digest；
- Snapshot 内容完成并通过最终一致性检查后，最后执行逻辑 `freeze revision`。只有 primary Blob、全部本地 Member、Manifest-Member closure、逐项摘要、既有 Gate 与 Final Confirmation 全部通过并读回一致时才可转为 `frozen`；当前专属 Spec 若定义其他耦合最终化条件，则全部条件满足后才允许下游解析。

解析准确 Artifact Reference 时：

1. 使用 Artifact ID 在当前 Canonical Store 中定位唯一 Artifact Lineage，并找到指定 Revision 的唯一 Revision Control Record；
2. 下游 Input 只接受 `frozen`，并通过 `read revision` 读取完整 Canonical Revision Payload；
3. primary Canonical Blob 的 `id`、`revision` 和 `status` 必须匹配，且 `status` 只能为 `ready` 或 `ready_with_exception`；
4. 验证全部本地 Member、稳定身份、Media Type、Manifest-Member closure、逐 Blob / Member SHA-256、Control Input Digest、当前 Check Set Result Digest、Final Confirmation、Gate Summary，以及专属 Spec 注册的耦合发布控制记录；Lifecycle Artifact 还必须解析其 Context Reference，并以每个 Input 自身的 Contract 递归验证完整 Input 链；不得使用下游当前 Spec 重新解释已冻结 Artifact；
5. Member Reference 通过 Manifest 解析；Item Reference 按 Project Context、Phase 或 Domain 固定模板解析到唯一 Item 定义；
6. 任一条件不满足即解析失败，不得自动改用最新、其他或旧 Revision。

不同 Spec Snapshot 可以通过准确 Artifact Reference 衔接，但下游必须支持上游 Front Matter 声明的 Artifact Contract。v1 只读取 `sdlc-ai-spec/artifact/v1` Input；其他 Contract 必须先由新版 Core 明确登记兼容关系，否则 Input Readiness 失败。兼容性必须对每条直接和传递 Input 边分别检查，不能由缓存或顶层版本推断跳过，也不能使用当前 Spec 重新解释已冻结 Artifact。

需要重新采用旧 Revision 内容时，以其作为 `Base Revision` 创建新的最大 Revision 并重新执行 Gate；旧 Revision 不能重新打开或原地修改。

冻结 Revision 后若发现其自身或直接、传递 Input 无法解析，其完整 Payload 与 Control Record 仍是不改写的历史冻结记录，但不能继续作为 Input，也不能为其 Item、Member、Evidence 或 Result 提供 Authority。恢复必须从最早失效的上游开始，依次创建各 Artifact 的新最大 Revision；只有 Artifact 稳定 ID 命名空间本身满足前述不可修复条件时，才改用唯一的 Identity Namespace Recovery Artifact。`Base Revision` 只允许作为同一 Artifact 的内容来源，Recovery Artifact 的首个 Revision 固定为 `Base Revision=None`。新 Revision 或 Recovery Artifact 必须绑定完整、当前可解析且兼容的直接 Input；失效引用不得保留，也不得在没有当前 Authority 覆盖相同 Scope 和义务时静默删除。复制内容或旧字节只属于 Candidate Material，必须按当前 Contract 重新登记、复核和通过 Gate。旧 Claim 的历史记录保留，但其执行权、Result Authority，以及旧 Gate、Final Confirmation、Exception、Method Result、Conclusion 和 RLS 结论均不继承；产品字节相同不能替代当前 Authority。

## Artifact 状态

| 状态 Status | 含义 Meaning |
|---|---|
| `draft` | 内容正在生成或修改 |
| `waiting_input` | 缺少必要输入或存在待补充事实 |
| `failed` | 已执行 Gate，但存在未通过项 |
| `ready` | 必要 Gate 全部通过且不存在 Waiver |
| `ready_with_exception` | 必要工作完成，但存在已授权 Waiver |

`status` 只表示 Artifact 是否可以供下游使用，不表示业务需求、任务或实际发版结果。

`status` 由必要输入、Artifact Gate Result 和 Exception 派生，不得为通过下游检查而手工指定。按下列顺序取第一个满足的结果：

| 条件 Condition | Check 或 Gate 处理 | Artifact Status |
|---|---|---|
| 已确认引用无效、事实冲突、任一必要 Check 为 `fail`，或人工明确拒绝 | Artifact Gate 为 `fail` | `failed` |
| 不存在 `fail`，但至少一个 Open Item 为 `State=open` | 其 `Blocked References` 对应 Check 保持 `pending`，Artifact Gate 为 `pending` | `waiting_input` |
| 不存在上述输入阻塞，但检查或最终确认尚未完成 | Artifact Gate 为 `pending` | `draft` |
| 所有必要 Check 已关闭，且存在有效、未关闭的 Waiver | Artifact Gate 为 `pass_with_exception` | `ready_with_exception` |
| 所有必要 Check 已关闭，且不存在有效、未关闭的 Waiver | Artifact Gate 为 `pass` | `ready` |

“尚未提供”与“已经确认无效”不得混用：前者等待输入，后者是已知不合格事实。

## Lifecycle Profile

内置 Profile：

| Profile | 含义 Meaning |
|---|---|
| `full` | 默认要求较完整的 Phase、活动和产物 |
| `lite` | 默认允许更多内容嵌入执行或标记不适用 |
| `hotfix` | 默认采用面向紧急恢复的执行配置 |

Profile 选择依据至少包括：

- 是否属于正在发生的故障或紧急恢复；
- 影响单个位置、单个组件还是多个系统；
- 是否改变接口、数据或用户行为契约；
- 是否涉及安全、权限、隐私、资金或合规；
- 是否存在未知依赖或明显不确定性；
- 验收边界是否明确。

执行主体或工具可以依据固定检查项推荐 Profile 并说明原因；Profile 选择由有责任的决策者确认。v1 Profile 只使用上述固定枚举。

## Disposition

| 值 Value | 含义 Meaning |
|---|---|
| `required` | 在当前位置独立、完整执行 |
| `embedded` | 必须完成，但结果写入指定 Artifact 或章节 |
| `n/a` | 客观不适用 |
| `waived` | 原本适用，但经授权主动跳过 |
| `pending` | 尚未决定 |

所有作为 Contract 控制值的枚举——包括 Disposition、Result、State、Conclusion、Mode 和 Follow-up Disposition——必须直接填写 Spec 定义的规范裸值，不使用 Markdown 强调、链接、HTML 或其他展示包装。展示格式不能把未知值变为合法值，也不能隐藏 `waived`、`pending` 或失败状态。

规则：

- `embedded` 必须填写承载位置；
- `embedded` 只有在目标 Phase 或子规范已经注册可引用的 Host 类型、完整内容要求和对应检查时才允许使用；没有已注册 Host Contract 时不得仅凭自由文本或章节名判定为 `embedded`；
- `n/a` 必须填写客观原因；
- `waived` 必须关联 Exception；
- `pending` 不能通过 Gate；
- `n/a` 与 `waived` 不得混用；
- Profile 只提供初始建议，Disposition 是最终决定。

Disposition 使用以下固定判定顺序：

1. 事实不足时为 `pending`，Artifact 按阻塞性进入 `draft` 或 `waiting_input`；
2. 事实充分且不存在该事项的义务或影响时为 `n/a`；
3. 事项适用但经有效授权不执行时为 `waived`；
4. 事项适用，且既有基线或另一个准确 Host 已完整覆盖、没有必须由目标位置独立承载的新义务时为 `embedded`；
5. 其他适用事项为 `required`。

`embedded` 只改变结果的承载位置，不降低内容、Evidence 或 Gate 要求。

## Evidence

每个 Artifact 的 Evidence 章节使用固定索引：

```markdown
| ID | Type | Supports References | Source or Producer | Reference | Integrity or Digest | Produced At | Sensitivity or Access | Empty Reason |
|---|---|---|---|---|---|---|---|---|
| None | none | N/A | N/A | N/A | N/A | N/A | N/A | No independent Evidence |
```

规则：

- Evidence ID 使用 `EVD-001` 顺序编号，在当前 Artifact 内稳定且不得复用；
- `Supports References` 必须引用 Requirement、Decision、VFY Point、Gate Check、Exception 或其他明确结论，不能只写“供参考”；
- 外部内容必须使用不可变引用、版本、内容摘要或其他可复核的完整性信息；
- Evidence 不得把推测写成已观察事实，也不得记录真实 Secret、Token、私钥或不必要的敏感值；
- 跨 Artifact 引用 Evidence 时使用完整 `Artifact-ID@Revision#EVD-ID`；
- 无 Evidence 时只保留上表唯一 `None` 行并填写客观 `Empty Reason`；存在 Evidence 时删除 `None` 行，实际行的 `Empty Reason` 填 `N/A`。

## 支撑产物清单 Supporting Artifact Manifest

Artifact 存在图片、Schema、日志、报告或其他独立成员时，必须使用固定清单；纯单文件 Artifact 仍保留该章节并填写 `None` 和原因。DSN 的 Artifact Set Manifest 是本清单的 Phase 扩展，不重复创建两份清单。

```markdown
| Member ID | Type | Path or Reference | Media Type | Purpose | SHA-256 Digest | Empty Reason |
|---|---|---|---|---|---|---|
| None | none | N/A | N/A | N/A | N/A | No supporting artifacts |
```

规则：

- Member ID 使用 `SUP-001` 顺序编号；同一逻辑成员跨 Revision 保持 ID，已移除 ID 不得改配给其他成员；
- Manifest 行按 Member ID 升序排列；`None` 空行是唯一例外；
- Phase Spec 可以注册其他稳定 Member 前缀和 Type，但扩展 Manifest 必须是本表字段的超集；
- 路径必须位于 Artifact Set 内，外部成员必须使用不可变引用；
- SHA-256 对成员原始字节计算，写作 `sha256:<64 位小写十六进制>`；
- Phase Spec 只有在成员同时包含输入与派生内容时才可以扩展额外摘要列，并必须固定计算范围；
- 无成员时只保留一行：`Member ID=None`、`Type=none`、`Empty Reason` 填写客观原因，其余字段填写 `N/A`；
- Manifest 与实际成员不一致时不得进入任何可供下游使用的状态；
- 跨文件引用成员时使用完整 Member Reference。

## Exceptions

```markdown
| ID | State | Origin Exception Reference | 作用域或被跳过义务 Scope or Skipped Obligation | 原因 Reason | 已知风险 Known Risk | 补偿措施 Compensating Control | 批准记录 Approver, Role and Time | 复查条件 Revisit Condition | 下游限制 Downstream Obligation | 解决或替代引用 Resolution or Superseding References |
|---|---|---|---|---|---|---|---|---|---|---|
| None | none | N/A | N/A | No Exceptions | N/A | N/A | N/A | N/A | N/A | N/A |
```

规则：

- Waiver 只能由项目定义的人工授权角色批准；其他执行主体只能提出建议；
- Exception ID 使用 `EX-001` 顺序编号；同一 Exception 跨 Revision 保持 ID，已关闭 ID 不得复用；
- 被豁免义务的 Disposition 为 `waived`；只有对应 Spec 明确允许豁免的专属 Check 才可以记为 `waived`，Contract Integrity Check 仍必须实际通过；
- `State` 使用 `active`、`carried`、`resolved` 或 `superseded`：当前 Artifact 新批准且仍有效为 `active`，从上游承接且仍有效为 `carried`；
- `carried` 必须填写准确的上游 `Artifact-ID@Revision#EX-ID`；`active` 的 Origin 填写 `N/A`；
- `resolved` 必须引用一个或多个可解析的解决 Evidence、Item 或已冻结 Artifact：当前 Artifact Set 内使用已登记裸 Item ID，跨 Artifact 使用指向冻结 Revision 的完整引用；`superseded` 必须且只能引用一个已存在、不同于自身的替代 Exception；该字段统一使用 Core Reference Set 语法；
- 合法状态变化为 `active/carried → resolved/superseded`；关闭后不得重新打开同一 ID，需要重新接受风险时创建新 Exception 并引用原记录；
- `active` 和 `carried` 属于未关闭 Exception，必须进入 Artifact Gate Summary，并派生 `ready_with_exception`；
- 下游必须继续引用其当前 Scope 所涉及的尚未关闭 Exception；当前 Artifact 只覆盖直接 Input 的部分范围时，只有能够由 `Scope or Skipped Obligation` 和当前固定追踪关系确定性证明不相交的 Exception 才可排除，无法确定时仍按相关处理；不得仅通过改写 `State` 关闭风险；
- 同一早期 Exception 经多个直接 Input 分别承接时，当前内置 Spec 将每个直接 Input 的当前未关闭 Exception Reference 视为独立承接义务，分别创建 `carried` 行，不沿 Origin 链自动合并；只有全部相关直接 Input 的义务已由其中一个直接 Input 的冻结 Artifact 形成唯一汇总 Exception，且其他直接 Input 不再保留独立的相关未关闭 Exception 时，才承接该唯一直接引用；
- 无 Exception 时只保留上表唯一 `None` 行；`State=none` 只允许用于该行。存在 Exception 时删除 `None` 行。

## Gate

逐项 Check Result 固定为：

| 结果 Result | 含义 Meaning |
|---|---|
| `pass` | 已通过 |
| `fail` | 未通过 |
| `pending` | 尚未检查或确认 |
| `n/a` | 客观不适用，必须说明原因 |
| `waived` | 适用但经授权跳过 |

所有 Artifact 先执行同一组 Core Gate Checks，再执行 Project Context 或 Phase 专属 Gate Checks：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| CORE-G-001 | Contract、Artifact ID、Revision、Artifact Lineage 和 Revision Control Record 一致有效 | pending | |
| CORE-G-002 | Context 与 Input Reference 符合当前 Front Matter Contract：Lifecycle Artifact 的 Context 可解析；全部 Input 已冻结、可按自身 Evaluation Contract Set 解析且版本兼容；Contract 排除的字段不存在 | pending | |
| CORE-G-003 | 模板、必填字段、Manifest 成员集及成员摘要完整一致 | pending | |
| CORE-G-004 | Disposition 与内容、Host、Evidence 一致 | pending | |
| CORE-G-005 | Evidence Index 完整，引用可解析并支持对应结论；存在正式 action 时包含适用的 Pre-execution 读回 Evidence | pending | |
| CORE-G-006 | 必要输入缺口均已唯一登记；最终化时不存在未解决的阻塞项 | pending | |
| CORE-G-007 | Context 与直接 Input 中和当前纳入范围相关的未关闭 Exception 已被 carried，或有 Evidence 证明不相交、resolved / superseded；当前 Exception 记录和授权有效 | pending | |
| CORE-G-008 | QA Check Set 与 Evaluation Contract Set 一致，全部应执行 Check 均已唯一登记 | pending | |
| CORE-G-009 | 已完成最终确认，且确认记录绑定当前 Revision、Control Input Digest、Evaluation Contract Set 与 Check Set Result Digest | pending | |

### QA Check Set

QA 复用现有 Check、Evidence、Gate 和 Final Confirmation，不创建独立 QA Artifact、Phase、Manifest、Status 或平行 Ruleset。

每个 Artifact 的 QA Check Set 由以下内容确定性组成：

1. 全部 Core Check；
2. 当前 Project Context 或 Phase 的全部专属 Check；
3. 当前专属 Spec 注册的 subordinate checks；

QA Check Set 是逻辑集合，不新增正文表格。每个当前应执行 Check 必须恰好登记一次；存在历史 Attempt 时，当前专属 Spec 必须确定唯一 Current Attempt，只有其 Check 行进入 QA Check Set，历史行不参与重复判断或摘要。`pass` 必须有可复核 Evidence 或确定性说明，`fail` 必须记录失败事实，`pending` 表示尚未完成。`n/a` 或 `waived` 只有对应 Spec 明确允许时才可使用；QA Check Set 不能整体豁免，具体义务继续通过 Exception 处理。

Gate 按 Core → Project Context 或 Phase → subordinate 的固定顺序聚合 QA Check Set。Gate Summary 决定 Artifact 是否可以进入下游，Final Confirmation 确认当前 Artifact 与 Gate 结论；VFY 判断产品是否符合 Requirement、Design 和预期用途，不代替各 Artifact 的 QA。

### Control Input Digest

Gate 和 Final Confirmation 必须绑定实际被检查的内容，不能只绑定可在草稿期继续修改的 Revision。

`Control Input Digest` 按以下固定方式计算：

1. 主要 Markdown 使用 UTF-8、LF 换行且无 BOM；
2. 移除 YAML Front Matter 中派生字段 `status` 的整行；
3. 移除从 `## 门禁 Gate` 标题开始到文件末尾的全部 Gate 派生内容；
4. 保留其余内容原有顺序和字节，计算 SHA-256，写作 `sha256:<64 位小写十六进制>`；
5. 复合 Artifact 必须先验证 Manifest 中每个成员的原始字节摘要；主要 Markdown 中的 Manifest 因此把全部成员绑定到同一 Control Input Digest。

所有“单元格视为空值”的摘要投影使用同一字节级算法：

1. 固定表格每行必须是单个物理行，且只使用一个开头 `|`、一个结尾 `|`；单元格内的竖线写作 `&#124;`，不得使用原始 `|` 或换行；
2. 当前 Artifact Spec 通过准确章节标题、表头名称和列名定位目标表与目标列；目标缺失、重复或表格结构不合法时摘要无效；
3. 对每个目标数据单元格，保留左右分隔符，把两者之间的全部原始字节替换为一个 ASCII 空格；其他字节完全不变；
4. Digest 自身单元格也使用同一替换规则；投影完成后直接对结果字节计算 SHA-256，不再由 Markdown 解析器重新序列化。

任何参与摘要的内容或成员发生变化，旧逐项检查、Gate Summary 和 Final Confirmation 都立即失效；不得复制旧结果后仅更新摘要。

每个 Artifact Gate 必须使用稳定 Check ID。全部 Check 在最终确认前形成唯一 `Check Set Result Digest`：

1. 选择 QA Check Set 中除 `CORE-G-009` 外每个 Check 的当前完整 Markdown 数据行；subordinate 只选择当前专属 Spec 确定的唯一 Current Attempt；缺失、当前重复或 Result 为 `pending` 时摘要无效；
2. 按 Core → Project Context 或 Phase → subordinate 排序，每组内按 Check ID 升序；每行保持原始 UTF-8 字节并追加一个 LF；
3. 对连接后的字节计算 SHA-256，写作 `sha256:<64 位小写十六进制>`；
4. 任一当前 Check 行的 Result 或 Evidence or Notes 变化都会使旧 Check Set Result Digest 失效；Current subordinate record 的其他字段通过 Control Input Digest 绑定，并使旧 Final Confirmation 失效。

`CORE-G-009` 由匹配当前 Revision、Control Input Digest、Evaluation Contract Set 和 Check Set Result Digest 的 Final Confirmation 关闭，因此不进入该摘要，避免自引用。

最终 Artifact Gate Summary 聚合 Core、Project Context 或 Phase 与 subordinate Check，并保存以下唯一汇总记录：

```markdown
| Evaluated Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Gate Result | Exception References | Evaluator | Evaluated At |
|---|---|---|---|---|---|---|---|
| 1 | | | | pending | None | | |
```

Aggregate Gate Result 使用 `pending`、`pass`、`pass_with_exception` 或 `fail`。所有必要 Check 为 `pass` 或具有有效理由的 `n/a`，且没有 Waiver 时为 `pass`；存在有效 Waiver 时只能为 `pass_with_exception`；存在 `fail` 时为 `fail`；其余为 `pending`。

`Evaluation Contract Set` 必须使用固定 Reference Set 语法，列出本次 Gate 实际执行的全部不可变规则来源。全部 v1.1 Canonical Artifact 必须包含 Core Spec 和 `docs/v1.1/artifact-store-spec.md@sha256:7de6fb26835da7ceedb38ada064be39276eeedeaf52892523d59d649c09009c6`；CTX Artifact 还必须包含 Project Context Spec；Lifecycle Artifact 还必须包含当前 Phase Spec，复合 Artifact 还包含适用的 Domain Spec。Lifecycle Artifact 通过 Front Matter `context` 解析 CTX 自身的 Evaluation Contract Set，不把 Project Context Spec 重复加入当前 Phase 的集合。每个元素固定写作 `<仓库相对 Spec 路径>@sha256:<64 位小写十六进制>`。`Gate Result=pending` 时允许先只填写该字段作为当前 Spec Binding，其他摘要在最终化时补齐。集合变化时，未冻结 Revision 立即失效旧 Gate、Final Confirmation 和旧规则下的正式 action 输出，并按 Pre-execution 规则重新处理；已冻结 Revision 必须创建新 Revision。

同一 Artifact 的 Core、当前 Project Context 或 Phase Contract，以及适用 Domain Contract 必须来自同一 Spec Snapshot。不同 Artifact 可以分别绑定不同 Snapshot，并按跨 Snapshot 输入兼容规则衔接。

`CORE-G-001` 至 `CORE-G-009` 都是 Contract Integrity Check，不可标记为 `n/a` 或 `waived`。当前专属 Spec 必须明确允许豁免的专属 Check；未声明时只允许 `pass`、`fail` 或 `pending`。

最终确认使用固定记录，并绑定被确认的 Revision、Control Input Digest、Evaluation Contract Set 与 Check Set Result Digest：

```markdown
| Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Result | Mode | Confirmer | Role | Authority Reference | Accepted Exception References | Confirmed At |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | pending | | | | None | None | |
```

Final Confirmation `Result` 使用 `pending`、`approved` 或 `rejected`。非 `pending` 时 `Mode` 必须为 `human` 或 `delegated`；只有 `approved` 可以满足最终确认 Gate Check。`human` 使用项目实际授权角色，`Authority Reference` 引用本次人工确认依据；业务取舍、主观 UI / UX 且没有真实人工 Method Evidence、生产或外部或不可逆动作及其权限、Exception 和风险接受必须使用 `human` 或既有外部权威，不能委托给模型。

`Authority Reference` 固定写作 `<项目相对路径>@sha256:<64 位小写十六进制>`，指向已持久化的确认或委托记录；路径不得越出项目，摘要必须匹配原始字节。

`delegated` 只允许在其余 Check 全部关闭、Open Items 为 `None`、没有 `active/carried` Exception、没有 `waived`、Gate 只能聚合为 `pass` 时使用。Role 固定为 `Delegated Independent Reviewer`；Confirmer 必须如实填写独立 review execution 或 agent ID，不得填写 `User` 或任何虚构人工身份；`Authority Reference` 的记录必须同时保存准确委托依据、独立复核执行、当前 Revision 与四项绑定摘要。Reviewer 不得创建或修改该 Revision，不得是 IMP Claim Owner、产品 Result 执行者、VFY Method 执行者或 RLS effect executor。委托确认只关闭 Artifact 合规确认，不授予产品修改、验证环境操作、发版、生产、外部或其他 action 权限。

参与委托确认交叉检查的执行身份字段——Final Confirmation Confirmer、Authority Reviewer / Reviewed Executor、IMP Claim Owner、VFY Method Executor 和 RLS Executor——每项只能填写一个稳定身份 token，格式为 `[A-Za-z0-9][A-Za-z0-9._:/@%+#-]*`。Markdown 行内代码只影响显示，比较前移除最外层反引号；不得用逗号、空格或展示格式在一个字段内合并多个身份。多人或多组件共同执行时，填写本次实际负责的统一执行、流水线或运行 ID，人员分工另由项目 Evidence 保存。

`delegated` 的 Authority 文件不进入当前 Artifact Supporting Manifest，避免摘要自引用；文件使用以下最小固定记录。`artifact` 保存准确 Artifact Reference；`decision` 固定为 `approved`；`decided_at` 使用 RFC 3339；`Delegation Basis` 必须是可复用的项目相对 `path@sha256` 授权记录。表内 Reviewer 必须与 Final Confirmation 一致，Reviewed Executor 必须是不同的执行身份，三项摘要必须与当前 Final Confirmation 一致，`Independence` 与 `Excluded Authority` 使用下列固定集合。Validator 只对 Artifact 已有执行身份字段做交叉校验并验证声明绑定，不能从本地文件密码学证明真实人员或 agent 身份；身份真实性依赖执行平台和项目审计信任边界。Artifact 没有权威执行身份字段时同样由该外部边界保证，不得宣称 Validator 已证明创作者身份。`human` Authority 只需满足项目相对路径与原始字节摘要，不强制使用此表。

```markdown
---
contract: sdlc-ai-spec/final-confirmation-authority/v1
artifact: <ARTIFACT-ID>@<Revision>
decision: approved
decided_at: <RFC3339>
---

| Delegation Basis | Reviewer Identity | Reviewer Role | Reviewed Executor Identity | Independence | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Excluded Authority |
|---|---|---|---|---|---|---|---|---|
| <项目相对授权路径>@sha256:<摘要> | <独立复核执行 ID> | Delegated Independent Reviewer | <被复核执行 ID> | fresh_read, recomputed, separate_execution_identity | <当前摘要> | <当前规则集合> | <当前摘要> | business_or_design_choice, exception_or_risk_acceptance, external_action_or_side_effect, external_permission_or_authorization, subjective_or_human_experience_judgment |
```

Final Confirmation 为 `approved` 时，`Accepted Exception References` 必须与将写入当前 Artifact Gate Summary 的全部 `active` 和 `carried` Exception 集合完全一致；`delegated` 时两者都必须为 `None`。缺失、额外或过期引用均不能关闭 `CORE-G-009`。

Revision、Control Input Digest、Evaluation Contract Set 或 Check Set Result Digest 变化后，旧 Gate 汇总和最终确认不得自动沿用。

Artifact 最终化顺序固定为：冻结当前待检查内容并计算当前专属 Spec 要求的前置摘要 → 关闭适用的 subordinate checks → 更新派生字段和最终成员摘要 → 通过 `write open revision` 原子持久化完整 Payload 并以 `read revision` 读回 → 执行 Core 与专属 Check（暂不关闭 `CORE-G-009`）→ 计算最终 Control Input Digest 与 Check Set Result Digest → 完成 Final Confirmation → 关闭 `CORE-G-009` → 聚合唯一 Artifact Gate Summary → 按固定映射派生并写入 Artifact Status → 再次写入、读回并验证完整 Payload。只有 Aggregate Gate Result 为 `pass` 或 `pass_with_exception`，且 primary Blob、全部本地 Member、稳定身份、Media Type、逐项 SHA-256 和 Manifest-Member closure 全部一致时，才执行 `freeze revision`；`fail` 写入 `failed`，`pending` 写入 `draft` 或 `waiting_input`，Revision 通常保持 `open` 以便修正。只有适用的 Core 或专属规则明确要求保留已经发生的 action 或控制失败，并通过新最大 Revision 或 Identity Namespace Recovery Artifact 继续时，才可在准确保存状态、Evidence 和 `fail` Gate 后对当前 `open` Revision 执行 `abandon revision`；不得借此规避失败 Gate 或删除既有 Evidence。Gate Result 与 Status 必须在同一次最终化尝试中写入；冻结前再检查 Revision、摘要、Gate Result、Status 和完整 Payload 一致。复合 Artifact 的专属 Spec 必须进一步固定前置摘要与成员刷新的顺序。

## Lifecycle Applicability

每个 Lifecycle Artifact 重新评估其后的 Phase：

```markdown
| Phase | Disposition | Host | 判断依据 Basis |
|---|---|---|---|
| DSN | pending | N/A | Pending — OPI-001 |
```

规则：

- 表中只保留当前 Phase 之后的 Phase；
- 只有 `embedded` 的 Host 填写一个已注册且可解析的 Host Reference；其他 Disposition 的 Host 固定为 `N/A`；
- Basis 必须非空：`pending` 引用对应 Open Item，`n/a` 说明客观原因，`waived` 引用有效 Exception，其他值引用其判断依据；
- 当前 Artifact 只对自身覆盖范围给出后续适用性建议；多 Artifact 或多 DSN 并行时，必须在同一交付范围内聚合后再作为执行依据；
- 与上游判断不同时必须说明新增事实；
- REQ Artifact 必须存在；
- VFY Artifact 必须存在，不能整体标记为 `n/a` 或 `embedded`；
- VFY Method 可以使用全部 Disposition；
- 发生实际发版或目标状态变化时 RLS Artifact 必须存在；
- `required` Phase 必须生成独立 Artifact；`embedded`、`n/a` 或 `waived` Phase 不生成独立 Artifact，其 Host、原因或 Exception 由最近的上游 Artifact Gate 验证；
- 跳过未生成独立 Artifact 的 Phase 后，下一个 `required` Phase 必须绑定最近的可用上游 Artifact Revision，并保留完整 Disposition、Host 和 Exception 解析链；
- 跳过后只有在下一个 `required` Phase 的 Input Readiness 能由现有固定字段、准确引用和执行时不可变基线确定性满足时才可继续；否则必须返回需要补齐该契约的上游 Phase，PLN 缺少原子执行依据时必须改为 `required`；
- 每个实际生成的 Phase Artifact 都必须执行完整 QA Check Set 和 Artifact Gate；
- 所有 Artifact 都需要 Final Confirmation；只有满足委托边界时可使用 `delegated`。

### Delivery Scope Aggregation

Delivery Scope Aggregation 解决多个完整的直接上游 Artifact 共同进入一次交付时的范围与 Applicability 合并，不创建独立 Artifact、ID、Revision 或 Status。

- 只计算直接 Scope Input，不重复计算其已完整覆盖的传递上游；
- 同一已选 Binding 范围内的前置 Implementation Result、Rework Artifact、Evidence 或其他控制输入不因数量单独触发聚合；若其引入新 Outcome、范围或协调义务，则成为 Scope Input；
- 只有一个 Scope Input 时，不因聚合要求强制创建 PLN；
- 存在多个 Scope Input 时必须执行聚合，PLN Disposition 必须为 `required`；
- 当前 Artifact Contract 的 Scope Input 只允许纳入完整 Artifact，不支持只选择其中部分 Item；需要独立交付部分范围时，先由上游形成边界完整的独立 Artifact，避免在 PLN 猜测 Requirement、Decision、Dependency、VFY Point 和 Exception 的闭包；
- PLN 因其他规划义务为 `required` 时，无论 Input 数量多少都保留以下固定章节；
- Delivery Scope 使用 PLN 的 Artifact ID、Revision、Status 和 Gate，不建立 `delivery_scope_id` 或平行状态。

PLN 中的来源范围表固定为：

```markdown
## 交付范围 Delivery Scope

| Source Artifact Reference | Inclusion Basis |
|---|---|
| DSN-20260823150010-01@1 | |
```

规则：

- Source 必须是已声明、可解析且状态可供下游使用的直接 Input；
- 每个 Source 的完整范围均纳入 Delivery Scope；来源行按 Source Artifact Reference 升序排列；
- Inclusion Basis 只解释纳入当前交付的原因，不得改写来源 Artifact 的 Requirement 或 Design。

聚合结果固定为：

```markdown
## 聚合适用性 Aggregated Applicability

| Phase | Effective Disposition | Host References | Basis References | Exception References |
|---|---|---|---|---|
| IMP | pending | None | None | None |
| VFY | required | None | None | None |
| RLS | pending | None | None | None |
```

每个下游 Phase 按以下顺序取第一个出现的 Disposition：

```text
pending → required → embedded → waived → n/a
```

- 任一来源为 `pending` 时，聚合结果为 `pending`，PLN 不能通过 Gate；
- 不存在 `pending` 时，任一来源为 `required` 则结果为 `required`；否则任一来源为 `embedded` 则为 `embedded`；否则任一来源为 `waived` 则为 `waived`；全部为 `n/a` 时才为 `n/a`；
- Basis References 必须包含参与该 Phase 聚合的全部直接 Source Artifact References；
- Host References 汇总全部 `embedded` 来源的 Host，Exception References 按准确直接来源引用汇总全部与当前 Delivery Scope 相交的 `waived` 来源 Exception，不沿 Origin 链自动合并；即使最终结果被 `required` 覆盖也不得丢失，无法确定是否相交时必须纳入；
- `embedded` 结果必须至少有一个 Host Reference，任何 `waived` 来源都必须有 Exception Reference，`n/a` 必须可从来源解析客观原因；
- 来源事实无效或相互冲突时不能用优先级掩盖，必须进入阻塞 Open Item；
- Delivery Scope 或聚合结果变化后，按普通 PLN 内容变化处理 Revision、Gate 和下游重新检查。

## 固定正文骨架

以下骨架只定义必须保留的通用章节和默认顺序；完整章节顺序以对应 Phase Spec 的固定模板为唯一权威。

```markdown
# <Artifact Title>

## 摘要 Summary

## 范围 Scope

## <Phase 固定章节>

## 待确认项 Open Items

## 证据 Evidence

## 支撑产物清单 Supporting Artifact Manifest

## 豁免 Exceptions

## 生命周期适用性 Lifecycle Applicability

## 门禁 Gate
```

除终点 RLS 外，每个 Phase 都必须保留 `Lifecycle Applicability`；RLS 没有下游 Phase，因此在固定骨架中删除该章节。`Summary`、`Scope`、`Evidence` 和 `Gate` 为所有 Lifecycle Artifact 的核心章节，不得删除或标记为 `n/a`；非终点 Phase 的 `Lifecycle Applicability` 同样不得删除或标记为 `n/a`。CTX 的固定章节由 Project Context Spec 单独定义。

正文只记录当前 Revision 的业务内容和控制依据，不复制由其他权威字段派生、且会随最终化变化的当前控制状态。`Summary`、`Scope` 和 `Open Items` 不得复述 Front Matter `status`、Revision Control Record `State`、Final Confirmation `Result`、逐项 Check Result 或 Artifact Gate Result；需要说明控制边界时只引用对应权威章节，不抄写其当前值。这样 open Revision 最终化时不需要同步修改多份状态描述，冻结 Snapshot 也不会保留相互矛盾的状态文字。

### Open Items Contract

所有 Project Context 与 Phase Artifact 的 `Open Items` 使用同一固定表格：

```markdown
| ID | 所需输入或待确认决策 Needed Input or Decision | 预期来源 Expected Source | 被阻塞项 Blocked References | 状态 State | 解决结果或证据 Resolution or Evidence |
|---|---|---|---|---|---|
| None | No open items | N/A | N/A | none | N/A |
```

规则：

- Open Item ID 使用 `OPI-001` 顺序编号，在当前 Artifact 内稳定且不得复用；
- 实际 Open Item 的 `State` 只使用 `open` 或 `resolved`；所有未解决 Open Item 都阻塞其 `Blocked References`，不影响当前 Artifact 最终化的想法、提醒或未来事项不进入 Open Items；
- `Open Items` 记录尚未获得的事实、澄清或外部决策；Artifact 内部尚未完成的编写或检查工作由 Gate `pending` 表达，不创建伪输入项；
- 每个已知但尚未提供、且仍会影响当前 Revision 合法结论或控制流的必要 Input 或事实，必须恰好对应一条 `State=open` 记录；当前 Artifact Contract 的 `Blocked References` 必须非空，只使用稳定 Check ID，按 `, ` 分隔、去重和升序，并作为阻塞关系的唯一权威来源；
- Phase Spec 明确注册的失败早停可以把仅影响未执行义务、但不会推翻已确认 fail 或改变 Return 归因的输入缺口转为当前 Revision 的 `resolved`；Resolution 必须引用 fail、Return 和 Evidence，明确输入尚未取得、只是不再阻塞当前失败检查点，并登记后续 Revision 对仍适用义务的重新评估要求。该处置不表示输入已提供、义务已完成或正常下游已获准；Phase Spec 必须保留未执行结果并禁止其进入正常下游；
- 每条阻塞记录必须对应真实缺口；同一缺口不得拆成重复记录以改变 Status；
- 不存在已确认的 `fail` 或人工拒绝时，任一 `State=open` 的记录确定性派生 `waiting_input`；存在 `fail` 或拒绝时仍按 Artifact Status 的固定优先级派生 `failed`；没有此类记录而 Gate 尚未关闭时派生 `draft`；
- `resolved` 必须填写可解析的 Resolution 或 Evidence；删除记录或清空 `Blocked References` 不能替代解决；
- `ready` 或 `ready_with_exception` 不允许存在未解决的阻塞项；无记录时只保留上表唯一 `None` 行，`State=none` 只允许用于该行。

## AI 与人工协作指导

每个 Phase Spec 必须在 Gate 之前使用一个简短表格说明当前 Phase 中 AI 与人工各自适合承担的工作及原因。

- 该表属于 Phase 执行指导，不进入生成的 Lifecycle Artifact 模板；
- 每个 Phase 保留 3 至 5 行与自身直接相关的内容，不建立完整职责矩阵；
- Spec 合规性仍只由 Artifact、Evidence、Check、Gate 和 Final Confirmation 判断，不以 AI 使用、人工投入或固定比例作为条件；
- AI 可以分析、生成、执行和提出建议；业务语义、关键设计取舍和风险接受仍由具有相应权威的人工决定；只有满足本节委托边界的 Artifact 合规确认可由独立 Reviewer 完成。

## Project Context

- 每个 Project Boundary 维护一个稳定 CTX ID；初次建立和后续刷新使用同一 Project Context Contract，更新只增加 Revision；
- CTX 保存长期稳定、可重复使用的项目事实、规则和约束，不保存单次 Requirement、具体 Design Decision、Work Item、实施结果、验证结论或发版状态；
- Lifecycle Artifact 必须通过 Front Matter `context` 绑定准确、已冻结且可解析的 CTX Revision；宿主适配文件、文件路径和可移动别名都不是 Context Reference；
- 新 CTX Revision 不自动改写或使既有 Lifecycle Artifact 失效；当前工作采用新 Revision 时，只修订实际受有效变化影响的最早 Artifact；
- 已生效且具有可追溯依据的项目级 Design Decision，可以由 CTX 登记完整 `DSN-ID@Revision#DEC-ID` 引用；原 DSN 仍是唯一权威来源，不在 CTX 中复制或改写决策；
- CTX 的固定模板、Basis、Identity、Revision、刷新与 Gate 规则由 Project Context Spec 定义；Core 不规定其执行入口、扫描方式或更新周期。

## Spec 边界

- Core 只定义跨 Artifact 稳定的领域 Contract；Artifact Store 的逻辑操作由 Artifact Store Spec 定义，物理存储、锁、执行入口或外部平台实现不在 Domain Spec 中规定；
- Project Context、Phase 和 Domain 的专属模板与增量规则由对应 Spec 负责，Core 不重复其业务字段；
- QA 由 Check Set、Evidence、Gate 和 Final Confirmation 承载，不建立独立 QA Phase 或 Artifact；
- 长期监控、告警、值守、故障处置和产品退役不属于每次变更的固定 Lifecycle Phase；
- Spec 不创建真实 Work Item、修改产品、执行验证、实施发版或写入外部系统。
