---
title: sdlc-ai-spec 核心 Spec
status: draft
scope: 已确认的通用术语、生命周期与 Artifact Contract
---

# sdlc-ai-spec 核心 Spec（草稿）

> 本文件仅记录当前已确认内容。未讨论内容不在本文件中推断或补全。

## 核心原则

- Spec 只判断产物、证据和 Gate 是否符合要求，不区分由人工还是 AI 完成。
- Artifact 可以由人工、AI 或其他执行主体生成和检查；Spec 不限定作者。业务目标、风险接受和最终确认由有责任的人工角色承担。
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
| 修订解析器 | Revision Resolver | `Revision Resolver` | 将准确 Artifact Reference 解析到不可变 Revision Snapshot 的规则 |
| 修订索引 | Revision Index | `Revision Index` | 保存 Revision 分配与冻结状态的最小索引 |
| 修订快照 | Revision Snapshot | `Revision Snapshot` | 已冻结且可被准确解析的 Artifact Revision |
| 质量保证 | Quality Assurance | `QA` | 由 Check Set、Evidence 和 Gate 承载的跨 Phase 质量保证，不作为独立 Phase |
| 验证与确认 | Verification & Validation | `VFY` | 判断产物是否符合上游要求，并满足预期用途 |
| 发版 | Release | `RLS` | 将准确的已验证结果发布到约定目标，确认目标侧状态并形成发版结论 |
| 工作项 | Work Item | `WI` | PLN 中可执行且可独立确认完成的最小计划单元 |

## 生命周期

本 Spec 的研发与变更交付控制位置固定为：

```text
REQ → DSN → PLN → IMP → VFY → RLS
```

| 位置 Order | Phase | Code | Artifact 目录 Artifact Directory |
|---|---|---|---|
| 100 | Requirement | `REQ` | `artifacts/100-req/` |
| 200 | Design | `DSN` | `artifacts/200-dsn/` |
| 300 | Plan | `PLN` | `artifacts/300-pln/` |
| 400 | Implementation | `IMP` | `artifacts/400-imp/` |
| 500 | Verification & Validation | `VFY` | `artifacts/500-vfy/` |
| 600 | Release | `RLS` | `artifacts/600-rls/` |

目录数字仅用于固定展示顺序，不作为 Artifact 身份或依赖依据。生命周期按上述位置逐项作出处置决定；下游发现问题时可以返回上游，形成新的 Revision 后继续向前。

这是一条 Artifact 与 Gate 控制流，不表示研发活动只能线性执行一次。活动可以在控制位置之间并行、迭代或递归；维护、运行反馈和新问题重新进入 REQ。长期监控、告警、值守、故障处置以及产品退役不属于每次变更的固定 Lifecycle Phase。

VFY 是证据汇总和结论控制位置；Verification 和 Validation 可以在此前各 Phase 发生，顶层 Method Type 统一为 Inspection、Analysis、Demonstration 和 Test，不要求集中到 IMP 之后才开始。Review、人工或自动化方式及 Test Level 由 VFY Phase Spec 归入对应 Method 或 Method Detail。

`PLN` 表示依据已确认设计形成实施计划，不表示项目启动前的战略规划。

## Artifact 格式

每个独立执行的 Phase 生成一个主要 Markdown Artifact：

- 主要产物使用固定 Markdown 模板；
- 少量机器字段使用 YAML Front Matter；
- 图片、OpenAPI、Schema、源代码、日志和报告保留原生格式，作为 Supporting Artifact；
- JSON 可以由验证器临时生成，但不要求人工编写或提交；
- XML 不作为通用 Artifact 格式。

## Artifact Identity

Artifact ID 格式固定为：

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
- 重新执行必须携带已有 Artifact ID，不重新分配；
- ID 一经分配不得修改、转移或复用；
- 主要文件名必须为 `<Artifact ID>.md`；
- 不依赖目录位置、文件顺序、标题或内容相似度识别 Artifact；
- 同一文字输入不代表同一业务身份，未指定 ID 时不得自动覆盖疑似相同 Artifact。

引用语法固定为：

| 引用类型 Reference Type | 格式 Format | 用途 Purpose |
|---|---|---|
| Artifact 引用 Artifact Reference | `<Artifact-ID>@<Revision>` | 引用一个准确 Artifact Revision |
| Item 引用 Item Reference | `<Artifact-ID>@<Revision>#<Item-ID>` | 跨 Artifact 引用内部 Item |
| Member 引用 Member Reference | `<Artifact-ID>@<Revision>/<Member-ID>` | 引用 Artifact Set 成员或 Supporting Artifact |
| Spec 引用 Spec Reference | `<仓库相对 Spec 路径>@sha256:<64 位小写十六进制>` | 在 Spec 版本解析机制未定义时绑定准确规则内容 |
| VCS 定位符 VCS Locator | `vcs:<resource>@<immutable-revision>` | 在 Phase Spec 明确允许时定位版本控制系统中的不可变产品内容 |

裸 Item ID 只允许在同一 Artifact 或 Artifact Set 内使用；跨 Artifact 的 Requirement、Decision、Exception、Evidence 和 VFY Point 必须使用完整 Item Reference。

VCS Locator 的 `resource` 必须是项目内唯一且可解析的版本化资源标识，`immutable-revision` 必须是该系统的完整不可变对象 ID；分支、可移动 Tag、`latest`、`current` 或工作树名称不满足该格式。VCS Locator 只标识产品内容，不替代 Lifecycle Artifact Reference。

Spec 路径使用 `/` 分隔，不得以 `/`、`./` 或 `../` 开头；同一文件必须使用仓库根目录下的唯一相对路径。

所有由 Phase Spec 或 Domain Spec 定义、可被引用的 Item ID 都遵循同一稳定性规则；Phase 的 `内部编号` 登记公共前缀，Domain Spec 的固定模板登记专属前缀：

- ID 在 Artifact 或 Artifact Set 内唯一，分配后不得因排序、插入、改名或 Revision 变化而改变；
- 删除或替代 Item 时不得把原 ID 分配给新语义，历史 Revision 继续保存原 Item；同一语义跨 Revision 保持原 ID，语义被替代时创建新 ID；只有当前 Phase 已定义来源或替代引用字段且确有替代项时，新 Item 才引用旧 Item；
- Phase Spec 只登记前缀、格式和专属字段，不得放宽上述规则。

引用字段使用固定集合语法：

- 字段名或语义为单数 `Reference` 时只允许一个合法引用；
- 字段名或语义为复数 `References` 时，以英文逗号加一个空格 `, ` 分隔，去重后按完整引用字符串升序排列；
- 空集合写 `None`；只有 Phase Spec 明确允许该字段不适用时才写 `N/A`；`None` 或 `N/A` 不能与其他引用并列；
- 同一 Artifact 内允许的裸 Item ID 仍按相同集合语法排序；Markdown 链接、分号、换行或 `<br>` 不得作为 Reference Set 的替代格式。

## Artifact Front Matter

字段和顺序固定：

```yaml
---
contract: sdlc-ai-spec/artifact/v0.1
phase: REQ
id: REQ-20260823143025-01
revision: 1
status: draft
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
| `profile` | 当前 Lifecycle Profile |
| `inputs` | 上游 Artifact Reference 列表；去重后按完整引用字符串升序排列，空集合固定为 `[]` |

固定表格的行顺序遵循以下规则：有 `ID` 或 `Member ID` 主键时按稳定 ID 升序排列；Phase Spec 已定义固定 Catalog 顺序时按 Catalog 顺序；业务语义依赖先后关系时必须使用显式 `Step` 或 `Order` 字段并按该字段排列。不得仅为排版重排已分配 ID。

## Revision

- 新 Artifact 从 `revision: 1` 开始。
- 新 Revision 固定为该 Artifact 已持久化最大 Revision 加 `1`；分配必须先于新内容写入并保证原子性；
- 发生并发冲突时重新读取最大 Revision 后再分配，不得覆盖、跳回或复用已有 Revision；
- `draft` 或 `waiting_input` 期间修改，不增加 Revision。
- `failed` Artifact 在形成可供下游使用的快照前修正，可以沿用当前 Revision；修改后当前 Check、Gate Summary 和 Human Confirmation 立即失效并重置为 `pending`，Status 按阻塞事实回到 `draft` 或 `waiting_input`。Core 不要求保存 open Revision 的中间失败尝试；确需留痕时登记为 Evidence 或由项目扩展规定。
- `ready` 或 `ready_with_exception` Revision 冻结后，任何内容、Input、Manifest、Phase Spec Binding、Check、Gate Summary、Human Confirmation 或 Status 需要更新时，都必须先创建新 Revision 并回到 `draft`；不以“语义是否变化”作为例外。
- 下游使用 `Artifact ID@Revision` 精确绑定上游。
- 当前交付范围选择采用新的上游 Revision 时，仍绑定旧 Revision 的相关下游 Artifact 必须重新检查；仅仅存在一个新 Revision，不会使既有精确引用自动失效。
- `ready` 或 `ready_with_exception` Revision 必须形成不可变快照，且能够通过 `Artifact ID@Revision` 唯一解析；不得只保留被后续 Revision 覆盖的当前文件。
- 快照冻结后不再原地修改；排版或文字修正也形成新 Revision，非权威阅读视图的渲染变化除外。

### Revision Resolver

每个 Artifact 使用一个根目录、一个 Revision Index 和按 Revision 分隔的目录：

```text
artifacts/<ORDER>-<phase>/<Artifact-ID>/
├── revision-index.md
└── revisions/
    └── <6 位 Revision>/
        ├── <Artifact-ID>.md
        └── <Artifact Set Members>
```

Revision 在引用和 Front Matter 中仍使用不补零的正整数；目录补足六位只用于稳定排序。Revision 目录在 `open` 时就是唯一工作位置，冻结后原地成为 Revision Snapshot；不建立 `current`、`working` 或 `latest` 副本。

`revision-index.md` 使用唯一固定表：

```markdown
| Revision | State | Base Revision | Allocated At | Frozen At | Abandon Reason |
|---|---|---|---|---|---|
| 1 | open | None | 2026-08-23T10:00:00+08:00 | N/A | N/A |
```

规则：

- `State` 只允许 `open`、`frozen` 或 `abandoned`；合法变化只有 `open → frozen` 和 `open → abandoned`，终态不能重新打开；
- 一个 Artifact 同时最多存在一个 `open` Revision；新 Revision 是索引内最大 Revision 加 `1`；
- `Base Revision` 为 `None` 或同一 Artifact 已存在的 `frozen` Revision；选择旧 Base 仍必须创建新的最大 Revision；
- Revision 分配、索引行和目录创建必须形成一个原子结果；失败后可以继续完成或标记为 `abandoned`，编号不得删除或复用；
- 时间使用 RFC 3339；`abandoned` 必须填写原因，其他不适用字段写 `N/A`；
- Revision Index 是 Resolver 元数据，不属于 Lifecycle Artifact，不进入 Artifact Set Manifest、Evidence 或 Gate Digest；
- Snapshot 内容完成并通过最终一致性检查后，最后将索引状态更新为 `frozen`；该更新是通用发布条件。Phase Spec 若定义与其他控制记录耦合的原子发布，则全部条件同时满足后才允许下游解析。

解析准确 Artifact Reference 时：

1. 根据 Phase Code 定位 Artifact 根目录，并在 Revision Index 中找到唯一 Revision 行；
2. 下游 Input 只接受 `frozen`，再定位对应六位 Revision 目录；
3. 主文件的 `id`、`revision` 和 `status` 必须匹配，且 `status` 只能为 `ready` 或 `ready_with_exception`；
4. 按现有 Contract 验证 Manifest、成员摘要、Control Input Digest、Evaluation Contract Set、当前 Check Set Result Digest、Human Confirmation、Gate Summary，以及 Phase Spec 注册的耦合发布控制记录；
5. Member Reference 通过 Manifest 解析；Item Reference 按 Phase 或 Domain 固定模板解析到唯一 Item 定义；
6. 任一条件不满足即解析失败，不得自动改用最新、其他或旧 Revision。

需要重新采用旧 Revision 内容时，以其作为 `Base Revision` 创建新的最大 Revision 并重新执行 Gate；旧 Revision 不能重新打开或原地修改。

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
| 不存在 `fail`，但至少一个 Open Item 为 `Blocking=yes` 且 `State=open` | 对应 Check 保持 `pending`，Artifact Gate 为 `pending` | `waiting_input` |
| 不存在上述输入阻塞，但检查或人工确认尚未完成 | Artifact Gate 为 `pending` | `draft` |
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

执行主体或工具可以依据固定检查项推荐 Profile 并说明原因；人工负责最终确认。项目扩展可以增加已注册、带版本的 Profile，但不能改变核心 Disposition 语义。

## Disposition

| 值 Value | 含义 Meaning |
|---|---|
| `required` | 在当前位置独立、完整执行 |
| `embedded` | 必须完成，但结果写入指定 Artifact 或章节 |
| `n/a` | 客观不适用 |
| `waived` | 原本适用，但经授权主动跳过 |
| `pending` | 尚未决定 |

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
| ID | State | Origin Exception Reference | 作用域或被跳过义务 Scope or Skipped Obligation | 原因 Reason | 已知风险 Known Risk | 补偿措施 Compensating Control | 批准记录 Approver, Role and Time | 复查条件 Revisit Condition | 下游限制 Downstream Obligation | 解决或替代引用 Resolution or Superseding Reference |
|---|---|---|---|---|---|---|---|---|---|---|
| None | none | N/A | N/A | No Exceptions | N/A | N/A | N/A | N/A | N/A | N/A |
```

规则：

- Waiver 只能由项目定义的人工授权角色批准；其他执行主体只能提出建议；
- Exception ID 使用 `EX-001` 顺序编号；同一 Exception 跨 Revision 保持 ID，已关闭 ID 不得复用；
- 被豁免义务的 Disposition 为 `waived`；只有对应 Spec 明确允许豁免的专属 Check 才可以记为 `waived`，Contract Integrity Check 仍必须实际通过；
- `State` 使用 `active`、`carried`、`resolved` 或 `superseded`：当前 Artifact 新批准且仍有效为 `active`，从上游承接且仍有效为 `carried`；
- `carried` 必须填写准确的上游 `Artifact-ID@Revision#EX-ID`；`active` 的 Origin 填写 `N/A`；
- `resolved` 必须引用解决 Evidence 或 Artifact，`superseded` 必须引用替代它的 Exception；
- 合法状态变化为 `active/carried → resolved/superseded`；关闭后不得重新打开同一 ID，需要重新接受风险时创建新 Exception 并引用原记录；
- `active` 和 `carried` 属于未关闭 Exception，必须进入 Artifact Gate Summary，并派生 `ready_with_exception`；
- 下游必须继续引用其当前 Scope 所涉及的尚未关闭 Exception；当前 Artifact 只覆盖直接 Input 的部分范围时，只有能够由 `Scope or Skipped Obligation` 和当前固定追踪关系确定性证明不相交的 Exception 才可排除，无法确定时仍按相关处理；不得仅通过改写 `State` 关闭风险；
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

所有 Artifact 先执行同一组 Core Gate Checks，再执行 Phase-specific Gate Checks：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| CORE-G-001 | Contract、Artifact ID、Revision 和 Revision Index 一致有效 | pending | |
| CORE-G-002 | 已声明的 Input Reference 存在、已冻结且可准确解析 | pending | |
| CORE-G-003 | 模板、必填字段、Manifest 成员集及成员摘要完整一致 | pending | |
| CORE-G-004 | Disposition 与内容、Host、Evidence 一致 | pending | |
| CORE-G-005 | Evidence Index 完整，引用可解析并支持对应结论 | pending | |
| CORE-G-006 | 必要输入缺口均已唯一登记；最终化时不存在未解决的阻塞项 | pending | |
| CORE-G-007 | 直接 Input 中与当前纳入范围相关的未关闭 Exception 已被 carried，或有 Evidence 证明不相交、resolved / superseded；当前 Exception 记录和授权有效 | pending | |
| CORE-G-008 | QA Check Set 与 Evaluation Contract Set 一致，全部应执行 Check 均已唯一登记 | pending | |
| CORE-G-009 | 已完成人工最终确认，且确认记录绑定当前 Revision、Control Input Digest、Evaluation Contract Set 与 Check Set Result Digest | pending | |

### QA Check Set

QA 复用现有 Check、Evidence、Gate 和 Human Confirmation，不创建独立 QA Artifact、Phase、Manifest、Status 或平行 Ruleset。

每个 Artifact 的 QA Check Set 由以下内容确定性组成：

1. 全部 Core Check；
2. 当前 Phase 的全部 Check；
3. 当前 Phase Spec 注册的 subordinate checks；
4. 实际启用的 Extension Check。

QA Check Set 是逻辑集合，不新增正文表格。每个当前应执行 Check 必须恰好登记一次；存在历史 Attempt 时，Phase Spec 必须确定唯一 Current Attempt，只有其 Check 行进入 QA Check Set，历史行不参与重复判断或摘要。`pass` 必须有可复核 Evidence 或确定性说明，`fail` 必须记录失败事实，`pending` 表示尚未完成。`n/a` 或 `waived` 只有对应 Spec 明确允许时才可使用；QA Check Set 不能整体豁免，具体义务继续通过 Exception 处理。

Gate 按 Core → Phase → Domain Matrix → Extension 的固定顺序聚合 QA Check Set。Gate Summary 决定 Artifact 是否可以进入下游，Human Confirmation 确认结论和未关闭风险；VFY 判断产品是否符合 Requirement、Design 和预期用途，不代替各 Phase 的 QA。

### Control Input Digest

Gate 和人工确认必须绑定实际被检查的内容，不能只绑定可在草稿期继续修改的 Revision。

`Control Input Digest` 按以下固定方式计算：

1. 主要 Markdown 使用 UTF-8、LF 换行且无 BOM；
2. 移除 YAML Front Matter 中派生字段 `status` 的整行；
3. 移除从 `## 门禁 Gate` 标题开始到文件末尾的全部 Gate 派生内容；
4. 保留其余内容原有顺序和字节，计算 SHA-256，写作 `sha256:<64 位小写十六进制>`；
5. 复合 Artifact 必须先验证 Manifest 中每个成员的原始字节摘要；主要 Markdown 中的 Manifest 因此把全部成员绑定到同一 Control Input Digest。

所有“单元格视为空值”的摘要投影使用同一字节级算法：

1. 固定表格每行必须是单个物理行，且只使用一个开头 `|`、一个结尾 `|`；单元格内的竖线写作 `&#124;`，不得使用原始 `|` 或换行；
2. Phase Spec 通过准确章节标题、表头名称和列名定位目标表与目标列；目标缺失、重复或表格结构不合法时摘要无效；
3. 对每个目标数据单元格，保留左右分隔符，把两者之间的全部原始字节替换为一个 ASCII 空格；其他字节完全不变；
4. Digest 自身单元格也使用同一替换规则；投影完成后直接对结果字节计算 SHA-256，不再由 Markdown 解析器重新序列化。

Domain Gate 的 `Domain Control Input Digest` 必须由 Phase Spec 固定输入范围，并排除全部 Gate Attempt、Gate Summary 和其他 Gate 派生字段；Artifact Gate 在全部 Domain Gate 关闭后计算父 Artifact 的 Control Input Digest。

任何参与摘要的内容或成员发生变化，旧逐项检查、Gate Summary 和 Human Confirmation 都立即失效；不得复制旧结果后仅更新摘要。

每个 Phase Gate 必须使用稳定 Check ID。全部 Check 在人工确认前形成唯一 `Check Set Result Digest`：

1. 选择 QA Check Set 中除 `CORE-G-009` 外每个 Check 的当前完整 Markdown 数据行；subordinate 只选择 Phase Spec 确定的唯一 Current Attempt；缺失、当前重复或 Result 为 `pending` 时摘要无效；
2. 按 Core → Phase → subordinate → Extension 排序，每组内按 Check ID 升序；每行保持原始 UTF-8 字节并追加一个 LF；
3. 对连接后的字节计算 SHA-256，写作 `sha256:<64 位小写十六进制>`；
4. 任一当前 Check 行的 Result 或 Evidence or Notes 变化都会使旧 Check Set Result Digest 失效；Current subordinate record 的其他字段通过 Control Input Digest 绑定，并使旧 Human Confirmation 失效。

`CORE-G-009` 由匹配当前 Revision、Control Input Digest、Evaluation Contract Set 和 Check Set Result Digest 的 Human Confirmation 关闭，因此不进入该摘要，避免自引用。

最终 Artifact Gate Summary 聚合 Core、Phase 及适用的 Domain Gate，并保存以下唯一汇总记录：

```markdown
| Evaluated Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Gate Result | Exception References | Evaluator | Evaluated At |
|---|---|---|---|---|---|---|---|
| 1 | | | | pending | None | | |
```

Aggregate Gate Result 使用 `pending`、`pass`、`pass_with_exception` 或 `fail`。所有必要 Check 为 `pass` 或具有有效理由的 `n/a`，且没有 Waiver 时为 `pass`；存在有效 Waiver 时只能为 `pass_with_exception`；存在 `fail` 时为 `fail`；其余为 `pending`。

`Evaluation Contract Set` 必须使用固定 Reference Set 语法，列出本次 Gate 实际执行的全部不可变规则来源：至少包含 Core Spec 和当前 Phase Spec；复合 Artifact 还包含适用的 Domain Spec，实际启用的 Extension Contract 也必须加入。版本机制未闭合前，每个元素固定写作 `<仓库相对 Spec 路径>@sha256:<64 位小写十六进制>`。集合变化时，未冻结 Revision 立即失效旧 Gate 与 Human Confirmation 并在当前 Revision 重跑；已冻结 Revision 必须创建新 Revision。

`CORE-G-001` 至 `CORE-G-009` 都是 Contract Integrity Check，不可标记为 `n/a` 或 `waived`。Phase Spec 必须明确允许豁免的专属 Check；未声明时只允许 `pass`、`fail` 或 `pending`。

人工确认使用固定记录，并绑定被确认的 Revision、Control Input Digest、Evaluation Contract Set 与 Check Set Result Digest：

```markdown
| Revision | Control Input Digest | Evaluation Contract Set | Check Set Result Digest | Result | Confirmer | Role | Accepted Exception References | Confirmed At |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | pending | | | None | |
```

Human Confirmation `Result` 使用 `pending`、`approved` 或 `rejected`。只有 `approved` 可以满足人工确认 Gate Check。

Human Confirmation 为 `approved` 时，`Accepted Exception References` 必须与将写入当前 Artifact Gate Summary 的全部 `active` 和 `carried` Exception 集合完全一致；缺失、额外或过期引用均不能关闭 `CORE-G-009`。

Revision、Control Input Digest、Evaluation Contract Set 或 Check Set Result Digest 变化后，旧 Gate 汇总和人工确认不得自动沿用。

Artifact 最终化顺序固定为：冻结当前待检查内容并计算 Phase 定义的前置 Input Digest → 关闭适用的 subordinate checks → 更新派生字段和最终成员摘要 → 执行 Core 与 Phase Check（暂不关闭 `CORE-G-009`）→ 计算最终 Control Input Digest 与 Check Set Result Digest → 完成人工确认 → 关闭 `CORE-G-009` → 聚合唯一 Artifact Gate Summary → 按固定映射派生并写入 Artifact Status。只有 Aggregate Gate Result 为 `pass` 或 `pass_with_exception` 时，才固化 Revision 目录并将 Revision Index 更新为 `frozen`；`fail` 写入 `failed`，`pending` 写入 `draft` 或 `waiting_input`，Revision 均保持 `open` 以便修正。Gate Result 与 Status 必须在同一次最终化尝试中写入；冻结前再检查 Revision、摘要、Gate Result 与 Status 一致。复合 Artifact 的 Phase Spec 必须进一步固定前置摘要与成员刷新的顺序。

## Lifecycle Applicability

每个 Artifact 重新评估其后的 Phase：

```markdown
| Phase | Disposition | Host | 判断依据 Basis |
|---|---|---|---|
| DSN | pending | N/A | Pending — OI-001 |
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
- 所有 Artifact 都需要人工确认。

### Delivery Scope Aggregation

Delivery Scope Aggregation 解决多个完整的直接上游 Artifact 共同进入一次交付时的范围与 Applicability 合并，不创建独立 Artifact、ID、Revision 或 Status。

- 只计算直接 Scope Input，不重复计算其已完整覆盖的传递上游；
- 同一已选 Binding 范围内的前置 Implementation Result、Rework Artifact、Evidence 或其他控制输入不因数量单独触发聚合；若其引入新 Outcome、范围或协调义务，则成为 Scope Input；
- 只有一个 Scope Input 时，不因聚合要求强制创建 PLN；
- 存在多个 Scope Input 时必须执行聚合，PLN Disposition 必须为 `required`；
- v0.1 的 Scope Input 只允许纳入完整 Artifact，不支持只选择其中部分 Item；需要独立交付部分范围时，先由上游形成边界完整的独立 Artifact，避免在 PLN 猜测 Requirement、Decision、Dependency、VFY Point 和 Exception 的闭包；
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
- Host References 汇总全部 `embedded` 来源的 Host，Exception References 汇总全部与当前 Delivery Scope 相交的 `waived` 来源 Exception；即使最终结果被 `required` 覆盖也不得丢失，无法确定是否相交时必须纳入；
- `embedded` 结果必须至少有一个 Host Reference，任何 `waived` 来源都必须有 Exception Reference，`n/a` 必须可从来源解析客观原因；
- 来源事实无效或相互冲突时不能用优先级掩盖，必须进入阻塞 Open Item；
- Delivery Scope 或聚合结果变化后，按普通 PLN 内容变化处理 Revision、Gate 和下游重新检查。

## 固定正文骨架

每个 Phase 在以下骨架中加入自身固定章节：

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

除终点 RLS 外，每个 Phase 都必须保留 `Lifecycle Applicability`；RLS 没有下游 Phase，因此在固定骨架中删除该章节。`Summary`、`Scope`、`Evidence` 和 `Gate` 为所有 Artifact 的核心章节，不得删除或标记为 `n/a`；非终点 Phase 的 `Lifecycle Applicability` 同样不得删除或标记为 `n/a`。

### Open Items Contract

所有 Phase 的 `Open Items` 使用同一固定表格：

```markdown
| ID | 所需输入或待确认决策 Needed Input or Decision | 预期来源 Expected Source | 被阻塞项 Blocked References | 是否阻塞 Blocking | 状态 State | 解决结果或证据 Resolution or Evidence |
|---|---|---|---|---|---|---|
| None | No open items | N/A | N/A | N/A | none | N/A |
```

规则：

- Open Item ID 使用 `OI-001` 顺序编号，在当前 Artifact 内稳定且不得复用；
- 实际 Open Item 的 `Blocking` 只使用 `yes` 或 `no`，`State` 只使用 `open` 或 `resolved`；`Blocking=no` 只用于不影响当前 Artifact 最终化、但需要显式保留给下游或后续 Revision 的问题；
- `Open Items` 记录尚未获得的事实、澄清或外部决策；Artifact 内部尚未完成的编写或检查工作由 Gate `pending` 表达，不创建伪输入项；
- 每个已知但尚未提供的必要 Input 或事实必须恰好对应一条 `Blocking=yes, State=open` 记录；v0.1 的 `Blocked References` 只使用稳定 Check ID，按 `, ` 分隔、去重和升序，并作为该关系的唯一权威来源；
- 每条阻塞记录必须对应真实缺口；同一缺口不得拆成重复记录以改变 Status；
- 任一 `Blocking=yes` 且 `State=open` 的记录确定性派生 `waiting_input`；没有此类记录而 Gate 尚未关闭时派生 `draft`；
- `resolved` 必须填写可解析的 Resolution 或 Evidence；删除记录或把 `Blocking` 改为 `no` 不能替代解决；
- `ready` 或 `ready_with_exception` 不允许存在未解决的阻塞项；无记录时只保留上表唯一 `None` 行，`State=none` 只允许用于该行。

## AI 与人工协作指导

每个 Phase Spec 必须在 Gate 之前使用一个简短表格说明当前 Phase 中 AI 与人工各自适合承担的工作及原因。

- 该表属于 Phase 执行指导，不进入生成的 Lifecycle Artifact 模板；
- 每个 Phase 保留 3 至 5 行与自身直接相关的内容，不建立完整职责矩阵；
- Spec 合规性仍只由 Artifact、Evidence、Check、Gate 和 Human Confirmation 判断，不以 AI 使用、人工投入或固定比例作为条件；
- AI 可以分析、生成、执行和提出建议；业务语义、关键设计取舍、风险接受和最终确认仍由具有相应权威的人工决定；
- 项目扩展可以加强角色或审批要求，但不能降低核心 Contract。

## Project Initialization and Context

以下边界已经确认；Project Context Contract 是后续 Project Bootstrap 能力，不是冻结当前 Core、REQ 和 DSN Contract 的前置条件，本节不推断其具体模板：

- `/init` 是 Lifecycle 开始前的 Project Bootstrap 能力，不是独立 Phase；
- Project Context Contract 定义后，Existing Project 和 New Project 必须使用同一个 Contract，只允许采集策略不同；
- Existing Project 通过代码、配置、文档和仓库状态发现已有事实；
- New Project 根据已确认信息建立最小上下文，未知内容进入 Open Items，不把 `pending` 混作信息状态；
- `/init` 不定义业务 Requirement，不代替 DSN 完成架构或技术选型，也不拆分任务或开始实现；
- Project Context 需要在基线变化后刷新；初始化和刷新都不是 Lifecycle Phase；
- Project Context Contract 闭合后，已生效且具有可追溯生效依据的项目级 Design Decision，可以由 Context 登记完整 `DSN-ID@Revision#DEC-ID` 引用；原 DSN 仍是唯一权威来源，不在 Context 中复制或改写决策；
- Project Context 的文件格式、状态、Revision 和更新规则当前尚未定义；在此之前不能将它作为可验证来源，必须使用不可变 Artifact Reference 或 Evidence。

## 当前规划边界

- Revision Snapshot 与 Revision Resolver 的逻辑 Contract 已定义；本阶段不实现解析工具。
- 最低 QA 逻辑 Contract 已由 Check Set、Evidence、Gate 和 Human Confirmation 闭合；本阶段不创建独立 QA 产物或实现工具。
- PLN Phase 模板由 `drafts/300-pln-spec.md` 单独定义；本 Core 只保留通用 Delivery Scope Aggregation Contract，不重复 Phase 规则。
- IMP Binding、领取、实施方法、结果、检查与 Gate Contract 由 `drafts/400-imp-spec.md` 定义；Claim 存储和额外 Result Locator 的实现仍未定义。
- VFY Phase 模板由 `drafts/500-vfy-spec.md` 定义；本 Core 不重复其 Target、Method、Conclusion 和 Return 规则。
- RLS Phase 模板由 `drafts/600-rls-spec.md` 定义；长期 Operations 不作为每次变更的固定 Artifact Phase。
- 本草稿不定义项目扩展机制的实现方式。
- 本草稿不创建实施工作项、任务或实现代码。
- PRD 与总体规划是当前范围基线；改变项目范围时单独修订，不在 Phase Spec 中静默扩大。
