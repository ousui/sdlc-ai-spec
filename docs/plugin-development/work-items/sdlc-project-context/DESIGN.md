# Skill Design Contract — `sdlc-project-context`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-project-context` |
| Stage | `design` |
| Status | `ready` |
| Intended Plugin | `sdlc-ai-spec` |
| Domain Source of Truth | `docs/v1.1/core-spec.md`, `docs/v1.1/artifact-store-spec.md`, `docs/v1.1/000-ctx-spec.md` |
| Plugin Execution Boundary | `docs/plugin-development/DEVELOPMENT.md` §3.1：Local SQLite + Plugin 内部 `ArtifactStore` |
| Work Package | `docs/plugin-development/work-items/sdlc-project-context/` |

`ready` 只表示 Design Definition of Done 已满足且没有阻塞 Open Item，可以提交 Maintainer 审批；不表示 `approved`，也不授权进入 `implement`。

## 2. 问题与用户结果

### Problem

项目长期事实、规则和约束如果只存在于会话记忆、宿主指令、可移动路径或零散文档中，后续 Lifecycle Artifact 容易重复获取、误推断或绑定错误上下文。当前需要一个只围绕 Project Context（CTX）Artifact 工作的稳定执行入口，使创建、修订和检查均遵守同一 v1.1 Evaluation Contract Set，并以 Canonical Store 而不是文件系统阅读视图作为 Artifact Authority。

### Intended User Outcome

用户显式调用本 Skill 后，可以：

- 创建一个符合 `sdlc-ai-spec/project-context/v1` 的 CTX Artifact；
- 修订同一 Project Boundary 的既有 CTX Lineage，同时保持 CTX ID、Item ID、Revision 和冻结语义；
- 只读检查指定 CTX Revision 的结构、引用、Basis、Open Items、Gate 与可解析性；
- 在必要事实不足时得到准确的 `waiting_input` 和 Open Items，而不是猜测事实或形成形式上的 `ready`；
- 在确认冲突、无效引用或 Check 失败时得到 `failed` 或明确检查失败结论，而不是静默降级。

## 3. 单一职责

本 Skill 的单一职责是：依据绑定的 v1.1 Core Spec、Artifact Store Spec 与 Project Context Spec，对一个 Project Boundary 的 CTX Artifact 执行创建、修订或检查，并保持其长期事实、完整 Canonical Revision Payload、控制结构和状态语义一致。

创建、修订和检查是同一 CTX Contract 的三个操作模式，不是三个独立 Skill，也不授权执行任何 Lifecycle Phase。

### In Scope

- 识别本次意图为 `create`、`revise` 或 `check`。
- 读取并绑定 `docs/v1.1/core-spec.md`、`docs/v1.1/artifact-store-spec.md` 与 `docs/v1.1/000-ctx-spec.md` 的准确 Spec Reference。
- 收集、分类和验证 Project Identity、Resource、Technology、Engineering Entry、Project Topology、Project Rule、Environment 与 Constraint。
- 为正式 Context 数据登记 `observed`、`confirmed` 或 `referenced` Basis 和可解析的 Basis References。
- 通过 Artifact Store Spec 登记的逻辑 Store Operation 初始化或验证 Canonical Store，分配 CTX Artifact / Revision，并读写、冻结、放弃或准确解析 CTX Revision；不得用目录、文件名或导出副本代替 Store Authority。
- 保持 CTX Identity、Revision、Item ID、Evidence ID、Supporting Artifact ID、Exception ID 和 Open Item ID 的稳定性。
- 生成或修订包含 CTX primary Canonical Blob、全部 locally owned Member、稳定 Member 身份、元数据、逐项摘要和 Manifest-Member closure 的完整 Canonical Revision Payload。
- 按 Core 与 CTX Gate 映射派生 `draft / waiting_input / failed / ready / ready_with_exception`。
- 只读检查指定 CTX Revision 是否可作为 Context Reference，或检查 open Revision 当前存在的契约问题。
- 报告已验证事实、待确认事实、冲突、实际副作用和未完成 Gate。

### Out of Scope

- 创建或修订 REQ、DSN、PLN、IMP、VFY、RLS Artifact。
- 把 CTX 当作 Phase、Lifecycle Profile、Disposition 或业务 Input。
- 记录单次 Requirement、针对具体 Requirement 的 Design Decision、Work Item、实施结果、验证结论或发版状态。
- 复制完整依赖清单、完整目录树、临时调试信息、凭证、Token 或 Secret。
- 创建宿主适配指令，或把宿主适配文件、路径、`latest`、`current` 当作 Context Reference。
- 自动修订仍绑定旧 CTX Revision 的 Lifecycle Artifact；只报告影响与最早可能受影响位置。
- 代替有责任的人工确认业务语义、关键取舍、Exception、风险接受或外部动作授权。
- 自动调用其他 Skill / Plugin、安装依赖、修改 Manifest、发布 Plugin 或执行远程写入。
- 把检查模式自动升级为修订模式，或在检查中静默修复目标 Artifact。

## 4. Trigger Contract

首版采用 Explicit Invocation First；以下“应该触发”均要求用户显式调用 `$sdlc-project-context`。未显式调用时，即使语义相似也不得自动加载本 Skill。

### 应该触发

| ID | 用户意图或场景 | 示例表达 | 触发方式 |
|---|---|---|---|
| TRG-P01 | 为已确定的 Project Boundary 首次建立 CTX | “使用 `$sdlc-project-context` 为这个仓库创建 Project Context” | `explicit` |
| TRG-P02 | 根据稳定事实变化修订既有 CTX Lineage | “使用 `$sdlc-project-context` 把 `CTX-20260828143025-01@1` 修订为新 Revision” | `explicit` |
| TRG-P03 | 只读检查 CTX Artifact 或 Context Reference | “使用 `$sdlc-project-context` 检查这个 CTX Revision 是否可供 Lifecycle Artifact 使用” | `explicit` |

### 不应该触发

| ID | 相邻但不属于本 Skill 的意图 | 示例表达 | 应由什么处理 |
|---|---|---|---|
| TRG-N01 | 未显式调用时的一般项目介绍或仓库分析 | “总结一下这个项目的技术栈和目录” | 普通分析；不得自动加载本 Skill |
| TRG-N02 | 创建或修订 Lifecycle Artifact | “为这个需求创建 REQ/DSN/PLN” | 对应 Phase 工作流；本 Skill 不调用兄弟 Skill |
| TRG-N03 | 仅修改宿主配置、Agent 指令或 Plugin Manifest | “把这些规则写进 AGENTS.md / plugin.json” | 对应配置或 Plugin 开发工作流 |
| TRG-N04 | 对完整依赖、代码目录或临时故障做专项盘点 | “导出全部依赖并排查当前报错” | 普通工具或专项工作流；稳定结论需由用户另行授权纳入 CTX |

### 歧义处理

- 已显式调用但未说明 `create / revise / check` 时，先根据请求中的目标动作和目标 Artifact 判定；不能唯一判定时只询问一个阻塞问题，不写入。
- 用户要求“检查并修复”时，将 `check` 和 `revise` 分开：先说明检查是只读，只有用户明确授权修订且目标 Lineage 唯一时才进入 `revise`。
- 无法唯一确定 Project Root、Canonical Store、Project Boundary 或目标 Lineage 时，不按名称、路径、导出内容或相似度猜测，也不分配或修改 Artifact；只有目标 Lineage 已安全确定但 CTX 内必要事实尚待确认时，才在 materialized open Revision 登记 Open Item 并保持 `waiting_input`。检查模式只报告无法判定。
- 用户显式调用本 Skill 但请求完全超出范围时，说明边界并交还控制权，不自动调用其他 Skill。

## 5. 三种用户意图边界

| Intent | Preconditions | Allowed Mutation | Identity / Revision Behavior | Completion Boundary |
|---|---|---|---|---|
| `create` | Project Boundary 可确定；当前项目唯一 Canonical Store 可初始化或验证；不存在同一 Boundary 的 CTX Lineage；Store 写入已由当前请求授权 | 只可通过逻辑 Store Operation 分配一个新 CTX Lineage 和 Revision 1，并写入完整 Canonical Revision Payload | 分配新 `CTX-<YYYYMMDDHHMMSS>-<NN>`；Revision 1；`Base Revision=None`；Control Reservation 与 Payload 明确分离 | 完整 Payload 已原子写入并读回，形成 materialized open Revision；只有全部 Gate 与 Final Confirmation 满足时才可冻结 |
| `revise` | 目标 CTX ID、Base Revision 和 Revision Control Record 可准确解析；写入已由当前请求授权 | 只可通过 `write open revision` 修改唯一 materialized open Revision，或在 Frozen Revision 后分配并物化新的最大 Revision | 不改变 CTX ID；open Revision 原地修正不增号；Frozen Revision 后使用最大 Revision + 1；无有效变化不分配空 Revision | Refresh Summary 准确登记变化；不自动改写下游 Context Reference |
| `check` | CTX ID 与 Revision 或准确 Context Reference 可由 Canonical Store 唯一解析 | 默认只调用只读 Store Operation；不修复、不分配 ID、不改变 Gate、Status 或 Revision State | 按指定 Revision 原样检查；不得回退到 `latest/current`、阅读视图或其他 Revision | 输出可判定的检查报告；报告不构成 Artifact Gate 或 Final Confirmation |

补充规则：

- 未冻结的 `draft`、`waiting_input` 或 `failed` Revision 可以在 `revise` 中继续修正；内容变化后旧 Check、Gate Summary 和 Final Confirmation 立即失效并重置为 `pending`。
- `ready` 或 `ready_with_exception` Revision 冻结后，任何内容或控制字段变化都必须创建新 Revision；排版或文字修正也不例外。
- 项目重命名、目录迁移或仓库地址变化不改变 CTX ID。只有 Project Boundary 明确拆分为独立项目时，新项目分别创建 CTX ID。
- 已确认同一 Canonical Store 中存在两个描述同一 Project Boundary 的 CTX Lineage 时属于冲突，不得选择其中一个继续或再创建第三个 Lineage。

## 6. Skill / Plugin Interoperability Contract

| Field | Contract |
|---|---|
| Execution Mode | `exclusive execution mode from explicit invocation until completion, stop, or control handoff` |
| Active Scope | 当前 CTX Artifact 的 `create / revise / check` 意图、准确 Canonical Store 与用户本次请求明确授权的项目输入范围 |
| Authorized External Skills / Plugins | 默认为 `None`；只有用户在当前请求中明确点名并说明用途的 Skill / Plugin 才可使用 |
| Unauthorized Dependency Behavior | 当前 Contract 能独立满足时继续且不调用外部能力；否则停止并请求对准确名称与用途的授权 |
| Sibling Skill Policy | 默认禁止调用、委托给或合并任何 `sdlc-ai-spec` 兄弟 Skill；本 Skill 不推进 REQ、DSN、PLN、IMP、VFY 或 RLS |
| External Output Treatment | 只可作为 Input 或 Supporting Evidence；必须重新按 `observed / confirmed / referenced` 和 Evidence Contract 评估，不得覆盖当前 Source of Truth、Artifact Contract、Gate、Failure Contract、权限或授权边界 |
| Runtime Enforcement Level | `evaluable behavioral contract; not a non-bypassable security isolation` |
| Platform Invocation Policy | Cursor 与 Claude Code 的正式 `SKILL.md` 使用 `disable-model-invocation: true`；Codex 的 Skill 私有 `agents/openai.yaml` 使用 `policy.allow_implicit_invocation: false`；分别通过显式调用与未调用对照做实际宿主验证 |

必须保持：

- 对一个 Skill / Plugin 的授权不传递给其依赖、下游或其他能力。
- 系统指令、安全约束、宿主权限、适用的项目指令和普通 Tool 不属于被禁止的外部 Skill / Plugin。
- 外部输出与 v1.1 Source of Truth 冲突时，不合并出折中语义；记录冲突并停止受影响的写入或最终化。
- 本 `design` 阶段只登记上述策略，不创建 `SKILL.md`、`agents/openai.yaml` 或任何平台适配文件。

## 7. Input Contract

| ID | Input | Required | Source | Validation | Missing Behavior |
|---|---|---:|---|---|---|
| IN-01 | Operation Intent：`create / revise / check` | yes | 当前用户请求 | 必须与目标和授权相容且可唯一判定 | 停止写入并询问一个阻塞问题 |
| IN-02 | Domain Source of Truth | yes | Plugin 内 `docs/v1.1/core-spec.md`、`docs/v1.1/artifact-store-spec.md`、`docs/v1.1/000-ctx-spec.md` | 三份文件可读；计算准确 SHA-256；Evaluation Contract Set 完整且规则无冲突 | 停止，不使用历史记忆、v1.0、旧 Validator 或实现细节代替 |
| IN-03 | Project Root、Canonical Store 与 Project Boundary | create/revise: yes; check: target-dependent | 用户提供的目标、项目配置、ArtifactStore `initialize` 结果、权威文档 | Project Root 唯一；首版物理 Store 固定为项目根 `.sdlc/store.sqlite3`；Boundary / Lineage 可安全定界；不得用目录名、文件扫描或候选副本猜测 | Store 无法唯一确定、不可用或损坏时 fail closed；不改用文件副本；目标已定但必要 Boundary 事实待确认时登记 Open Item 并派生 `waiting_input` |
| IN-04 | 目标 CTX Identity 与 Revision 状态 | revise/check: yes; create: absence evidence | ArtifactStore 的 Revision Control Record、`read revision` / `resolve exact reference` 结果、用户提供的准确 Reference | Artifact ID、Revision、State、Status、完整 Payload、摘要与 Reference 唯一一致；检查是否已有同 Boundary Lineage | 不创建或覆盖；只有 Control Reservation 或 Payload 不完整时失败；确认冲突时失败 |
| IN-05 | Project Identity：Project Name、Purpose、Boundary、Primary Resource Reference | ready: yes | `confirmed` Evidence，或 Primary Resource 的 `observed` Evidence | 四个固定字段非 `None / N/A`；Basis 与引用合法 | 不猜测；每个真实缺口唯一登记 Open Item，Status=`waiting_input` |
| IN-06 | Resource Registry 与不可变 Baseline | ready: yes | 可重复观察的 Resource 状态、权威引用或确认 Evidence | 至少一个 `Role=primary`；Locator 唯一可解析；版本化 Resource 有不可变 Baseline Reference | 建立 Open Item；不能用可移动分支、`latest/current` 代替 |
| IN-07 | 适用的长期 Technology、Engineering Entry、Topology、Rule、Environment、Constraint | applicable facts: yes | 代码、配置、工具结果、项目状态、权威文档或有权确认者 | 只保留后续重复使用的稳定内容；适用性和 Basis 可证明 | 未知且影响 Gate 时建立 Open Item；客观不存在时使用带 Basis 的唯一 `None` 行 |
| IN-08 | Basis References 与 Evidence | yes for every formal Context datum | 本地可验证结果、确认记录、准确不可变引用 | `observed` 引用 Evidence；`confirmed` 引用确认 Evidence；`referenced` 使用准确不可变引用 | 候选推断不进入正式数据；转为 Open Item |
| IN-09 | Revision 变化依据 | revise: yes | Frozen Base Revision、当前项目状态、确认或权威引用 | Effective Change 可解析；同一语义保持 Item ID；无有效变化可证明 | 不创建空 Revision；报告 no-op |
| IN-10 | Final Confirmation 与权限依据 | only for finalization | 项目实际授权角色或符合 Core 委托边界的独立 Reviewer 记录 | 绑定当前 Revision、Control Input Digest、Evaluation Contract Set、Check Set Result Digest；Authority Reference 可解析 | Gate 保持 `pending`；若只是确认尚未完成则 Status=`draft`，不伪造人工身份 |
| IN-11 | 写入授权 | create/revise: yes; check: no | 当前用户请求与宿主权限 | 授权覆盖准确项目与 CTX Artifact Store；不推断远程写入权限 | 不写入；报告被阻塞的目标和所需授权 |
| IN-12 | 外部 Skill / Plugin 授权 | no | 当前用户请求 | 必须逐项点名并限定用途；不接受传递授权 | 默认为 `None`；能独立完成则继续，否则停止请求授权 |
| IN-13 | ArtifactStore 执行入口 | create/revise/check: yes | 后续独立工作包实现并验证的 Plugin 内部 `ArtifactStore` 模块 | 仅支持 Local SQLite；覆盖所需逻辑 Store Operation；Skill 不接触 SQL、Schema 或 Migration；读写后均可验证准确结果 | 模块缺失、操作不受支持或读回失败时停止；不得直接 SQL、扫描目录或建立文件系统 fallback |

Input Contract 不依赖上一会话的隐式记忆。会话中已知但尚未持久化、无法形成合法 Basis 的信息只能作为候选材料。

## 8. Output Contract

| ID | Output | Format / Location | Required Content | Success Condition | Consumer |
|---|---|---|---|---|---|
| OUT-01 | CTX Revision Control Record | 当前项目 Canonical Store | 准确 Revision、`open / frozen / abandoned` State、Base Revision、Allocated At、Frozen At 与 Abandon Reason | 通过 ArtifactStore 原子建立并读回；编号不复用；状态变化合法；不被当作 Artifact Payload | ArtifactStore、后续 CTX Revision |
| OUT-02 | CTX Canonical Revision Payload | 当前项目 Canonical Store | CTX primary Canonical Blob 的完整原始字节、全部 locally owned Member、稳定身份、Canonical Member Name 或等价名称、Media Type、逐项 SHA-256 与 Manifest-Member closure | 与 Revision Control Record 身份一致；完整写入并读回；结构、引用、摘要、Check、Status 和 Gate 一致；不存在猜测的正式事实 | Lifecycle Artifact、人工 Reviewer、Validator |
| OUT-03 | CTX Supporting Members | 当前 Canonical Revision Payload，由 Manifest 登记 | 只包含确有必要的不可变 Evidence 或原生材料；准确稳定身份、名称、Media Type、Purpose 与 SHA-256 | Manifest 与实际本地 Member 集合、字节摘要一致；无成员时保留 Contract 规定的 `None` 表达 | CTX Gate、后续检查 |
| OUT-04 | Open Items / `waiting_input` 结果 | CTX 主 Artifact 的 `Open Items` 与 Front Matter | 每个真实必要缺口恰好一条稳定 `OPI-<NNN>`；Expected Source、Blocked References、State 完整 | 任一 `State=open` 在无 fail 时派生 `waiting_input`；不存在自由占位或伪输入项 | 用户、后续修订 |
| OUT-05 | 检查报告 | 当前响应；除非用户另行授权，不创建独立文件 | 目标、检查基线、通过项、失败项、缺失项、预期 Status、Context Reference 可用性、副作用=`None` | 结论可追溯到 Core / CTX Check；不修改目标 Artifact | 当前用户 |
| OUT-06 | 影响报告 | 当前响应；修订模式同时由 Refresh Summary 保存权威变化 | 新 Revision 对 Scope、Resource、Rule、Engineering Entry、Constraint 的有效变化，以及下游重新检查边界 | 不自动改写旧 Context Reference；只指出最早可能受影响 Artifact | 当前用户、后续 Lifecycle 工作流 |

输出必须区分：

- Agent 对候选材料的分析；
- 由 ArtifactStore、Validator 或普通 Tool 得到的确定性检查与摘要；
- 需要人工确认的 Project Boundary、业务事实、Exception、风险与 Final Confirmation；
- 尚未解决、会阻塞合法结论的 Open Items。

“Payload 已写入”不等于 Gate 通过。只有完整 Canonical Revision Payload 可读、Status 为 `ready` 或 `ready_with_exception`、Revision Control State 为 `frozen`，且准确 Reference 解析全部通过的 CTX Revision 才可作为有效 Context Reference。

## 9. Workflow Contract

1. **进入独占模式并定界**：确认 `$sdlc-project-context` 被显式调用，判定 `create / revise / check`，记录当前授权、目标 Project Boundary、项目根、固定 Local SQLite Store 和 External Skill / Plugin 授权清单。
2. **绑定规则**：从 Plugin 根定位并读取准确 Core Spec、Artifact Store Spec 与 Project Context Spec，计算包含三者的 Evaluation Contract Set；规则缺失、不可读或冲突时停止。
3. **初始化并解析 Store Authority**：只通过 Plugin 内部 ArtifactStore 对项目根 `.sdlc/store.sqlite3` 执行 `initialize`，验证当前 Boundary 只有一个 Canonical Store。`create` 证明不存在同 Boundary Lineage；`revise` 通过 Store 解析唯一 Lineage 和 Base Revision；`check` 锁定准确 Revision，不使用目录扫描、阅读视图或可移动别名。
4. **分配并物化 open Revision**：仅 `create / revise` 执行。先用 `allocate artifact` / `allocate revision` 原子建立并读回身份与 Revision Control Record，再用 `write open revision` 原子写入完整 Canonical Revision Payload 并以 `read revision` 完整读回。Control Reservation 不得被当作 CTX Revision；无法验证时按 Artifact Store Spec 重试准确写入或执行 `abandon revision`，编号不得删除或复用。
5. **收集并分类事实**：只读取当前 Boundary 和请求必要的本地资料。将正式数据分类为 `observed / confirmed / referenced`，生成对应 Evidence 或准确引用；不稳定推断留作候选材料。
6. **处理缺口与冲突**：缺少必要事实时建立唯一 Open Item，并在无 fail 时派生 `waiting_input`；已确认冲突、无效引用或 Check 失败时记录 Evidence、Gate `fail` 和 `failed`；不通过 Exception 把未知变成已知。
7. **执行意图分支**：`create` 完成 Revision 1；`revise` 保持稳定 ID、对比 Base Revision 并更新 Refresh Summary；`check` 只读复算结构、引用、摘要、Check 与 Status，不生成或修改 Revision。
8. **验证与最终化**：仅对 `create / revise` 按 Core 固定顺序处理 Evaluation Contract Set、完整 Payload 读回、Control Input Digest、Check Set Result Digest、Final Confirmation、`CORE-G-001` 至 `CORE-G-009`、`CTX-G-001` 至 `CTX-G-006`、Gate Summary 和派生 Status，并再次 `write open revision` / `read revision`。缺少合法 Final Confirmation 时保持 `draft` 或由真实 Open Item 派生 `waiting_input`。
9. **冻结或停止**：只有 Gate 为 `pass / pass_with_exception`、Status 对应 `ready / ready_with_exception`，且 primary Blob、全部本地 Member、Manifest-Member closure 和逐项摘要均读回一致时才执行 `freeze revision`。其余保持准确 `open`，只有 Artifact Store Spec 允许的失败恢复才转为 `abandoned`，均不得描述为可供下游使用。
10. **报告**：报告模式、目标 Reference、实际写入、Status、Open Items、Check 结果、下游影响、未执行项和外部 Skill / Plugin 实际调用记录；完成、停止或明确交还控制权后退出独占模式。

## 10. CTX Identity、Revision、冻结与 Context Reference 边界

- 一个 Project Boundary 维护一个稳定 CTX ID；内容更新只增加 Revision。
- CTX ID、Front Matter、Revision Control Record 和 Canonical Revision Payload 身份必须一致，且同一 Canonical Store 内不得存在两个同 Boundary CTX Lineage。
- ID 和 Revision 分配先原子持久化控制记录并读回，再以准确 Control Reservation 为目标原子写入完整 Payload；并发或内容冲突必须明确失败，不使用 last-write-wins。
- 同一时刻最多一个 `open` Revision；`frozen` 与 `abandoned` 是终态，不可重新打开。
- 只有 Revision Control Record 而没有完整 Payload 时只是 Store Control Reservation，不可读取、解析、执行 Gate、Final Confirmation 或冻结，也不可供下游使用。
- `Base Revision` 只定位同一 CTX 的内容来源，不是 Input 或 Authority；Revision 1 固定为 `None`。
- `ready / ready_with_exception` 冻结后不可原地修改；任何变化创建新最大 Revision。
- 新 CTX Revision 不自动改写或使既有 Lifecycle Artifact 失效；采用新 Revision 时，根据 Refresh Summary 只修订最早实际受影响的 Lifecycle Artifact。
- 有效 Context Reference 固定为 `<CTX-ID>@<Revision>`，并要求 Revision Control State=`frozen`、Status 可供下游使用、完整 Canonical Revision Payload 与控制结构可验证。
- Item Reference 固定为 `<CTX-ID>@<Revision>#<Item-ID>`；不得用路径、宿主适配文件、`latest`、`current` 或内容相似度替代。
- `check` 可以检查 open、frozen 或 abandoned 记录，但只有满足有效 Context Reference 的 Revision 才报告为可供 Lifecycle Artifact 使用。

## 11. Basis Contract

| Basis | Allowed Source | Required Treatment | Forbidden Treatment |
|---|---|---|---|
| `observed` | 代码、配置、工具结果或可重复验证的项目状态 | 创建 Evidence，记录 Source or Producer、Reference、Integrity、Produced At 和访问边界；正式数据引用该 Evidence | 把一次猜测、无法复现的会话判断或未保存输出当作观察事实 |
| `confirmed` | 具备相应权威的人明确确认 | 保存确认 Evidence；记录确认者、角色、时间、内容与完整性；正式数据引用该 Evidence | 模型代替人工确认，或把用户未确认的建议写为事实 |
| `referenced` | 既有权威文档、冻结 Artifact 或规则来源 | 使用准确不可变引用；项目级 Design Decision 只登记完整 `DSN-ID@Revision#DEC-ID`，不复制决策 | 使用可移动 URL、分支、`latest/current`，或复制并改写原权威语义 |

- 不使用置信度分数，不允许 `inferred` 成为正式 Context 数据。
- 同一正式数据只登记实际成立的 Basis；多个来源应由 Evidence 或 Reference Set 完整表达，不新增枚举。
- 候选推断只有转为合法 `observed / confirmed / referenced` 后才可进入正式表；否则建立 Open Item。

## 12. `waiting_input` 与 Open Items Contract

- 每个已知但尚未提供、且会影响当前 Revision 合法结论或控制流的必要事实，必须恰好对应一条 `State=open` 的 Open Item。
- `Blocked References` 只使用稳定 Check ID，按固定 Reference Set 语法去重升序；不得为空。
- 在没有已确认 `fail` 或人工拒绝时，任一 open Open Item 确定性派生 Front Matter `status: waiting_input` 和 Gate `pending`。
- 已确认 `fail`、事实冲突、无效引用或人工拒绝的优先级高于 Open Item，Status 为 `failed`；“尚未提供”和“已确认无效”不得混用。
- Artifact 内部尚未完成的编写或检查工作由 Gate `pending` 和 `draft` 表达，不创建伪 Open Item。
- `resolved` 必须有可解析 Resolution 或 Evidence；不得删除记录或清空阻塞关系来伪装解决。
- 没有 Open Item 时只保留唯一 `None` 行；`ready / ready_with_exception` 不允许存在 open Open Item。
- `None` 仅表示已确认集合为空或客观不存在；`N/A` 仅表示 Contract 明确不适用；禁止用空白、`TBD / Unknown / - / 待定` 代替未知事实。

## 13. Failure Contract

| Failure | Detection | Required Behavior | Forbidden Fallback |
|---|---|---|---|
| Source of Truth 缺失或冲突 | Spec 文件不可读、摘要不可计算，或 Core、Artifact Store 与 CTX 语义无法同时满足 | 停止受影响工作；报告路径、冲突和所需权威；不创建或最终化 Artifact | 使用记忆、旧 Validator、常识或折中语义代替 |
| Operation Intent 或目标不唯一 | 无法唯一判定模式、Project Boundary、Artifact Store、CTX ID 或 Revision | 不写入；请求一个阻塞输入；可在已分配的合法 open Revision 中登记 Open Item | 按名称、目录、最新时间或内容相似度选择目标 |
| 必要事实未提供 | Project Identity、Primary Resource、Baseline、适用长期事实或 Basis 缺失 | 建立 Open Item，Gate=`pending`，Status=`waiting_input`；保留已验证部分 | 猜测事实、使用自由占位或形成 `ready` |
| 已确认冲突或无效引用 | 同 Boundary 多 Lineage、Locator 冲突、Reference 不可解析、Check=`fail` | 保存 Evidence；Gate=`fail`，Status=`failed`；检查模式报告失败 | 当作待输入、忽略冲突或选择方便的 Lineage |
| Canonical Store 不唯一、不可用或损坏 | `initialize` 无法唯一确定项目 Store，或读回、完整性校验失败 | fail closed；报告准确项目与 Store 问题；恢复 Canonical Store 后再继续 | 改用目录、导出文件、缓存、临时材料或其他候选内容 |
| Revision 分配或物化中断 | Control Record 未提交、只有 Control Reservation、完整 Payload 未原子提交或完整读回失败 | 按 Artifact Store Spec 重试同一准确写入；无法验证时保留编号和实际内容并准确 `abandon revision` | 删除或复用编号、返回部分 Payload、覆盖既有内容或留下伪 Artifact |
| Frozen Revision 被要求原地修改 | 目标 Revision Control State=`frozen` | 分配新最大 Revision；保持 Frozen Snapshot 不变 | 原地编辑、重开 Frozen Revision、只更新阅读视图冒充 Revision |
| 修订没有有效内容变化 | Base 与候选内容在权威字段上无变化 | 不创建空 Revision；报告 no-op 和比较依据 | 为显示进度增加 Revision |
| Final Confirmation 缺失或无效 | Authority Reference、身份、绑定摘要或独立性不满足 Core | Gate 保持 `pending`；通常 Status=`draft`，真实事实缺口另建 Open Item | 模型虚构人工身份、复用旧确认或自我委托独立复核 |
| Check 模式发现问题 | 任一 Core / CTX Check 不通过，或目标不能解析为有效 Context Reference | 输出只读失败报告和最小修订建议；副作用为 `None` | 自动修复、改变 Status、冻结 Revision 或创建新 Revision |
| 写入权限或授权不足 | 用户请求或宿主权限不覆盖准确目标 | 不写入；报告准确目标与所需授权 | 写入相邻路径、外部系统或用户级配置 |
| 未授权外部 Skill / Plugin 成为必要依赖 | 当前 Contract 无法独立满足且当前请求未点名授权 | 停止并请求准确名称和用途授权 | 静默调用、委托、伪造外部结果或扩大既有授权 |

允许部分结果仅限：

- `create / revise` 中已验证内容可以保存在准确的 `draft / waiting_input / failed` open Revision；不得称为可用 Context Reference。
- `check` 可以在目标部分损坏时报告已能确定的问题和未能执行的检查；不得把未执行项记为通过。

## 14. 权限与副作用

| Capability | Required | Scope | Authorization |
|---|---:|---|---|
| Read local files | yes | 当前 Project Boundary、Plugin 内三份 Source of Truth，以及用户提供的准确 Evidence | 当前请求允许的项目读取；敏感信息按最小必要读取 |
| Read Local SQLite Store | yes | 仅项目根 `.sdlc/store.sqlite3`，通过 Plugin 内部 ArtifactStore 逻辑操作 | 当前请求允许的项目读取；`check` 使用只读操作，不直接 SQL |
| Write Local SQLite Store | create/revise: yes; check: no | 仅项目根 `.sdlc/store.sqlite3`，通过 Plugin 内部 ArtifactStore 原子事务 | `create / revise` 的明确用户意图；不写其他 Provider、导出目录或阅读视图 |
| Execute local commands | yes | 只读发现、SHA-256、结构校验和经 ArtifactStore 暴露的逻辑 Store Operation | 当前项目内普通 Tool；不安装依赖、不修改全局配置、不直接执行 SQL |
| Network read | no by default | 只有用户明确提供且当前 Basis 必须使用的权威来源 | 每个外部来源按当前请求授权；结果仍需不可变引用或摘要 |
| External write | no | None | 未纳入本 Skill Contract；即使用户授权外部读取也不含写入 |
| Invoke other Skill / Plugin | no by default | 仅用户当前请求逐项点名的能力和用途 | explicit only; no transitive authorization |

默认禁止自动安装依赖、修改用户级或系统级配置、破坏性 Git 操作、commit、push、远程 API 写入和读取无关敏感信息。

## 15. 资源边界

### `SKILL.md`

后续 `implement` 只在 `skills/sdlc-project-context/SKILL.md` 保留：显式触发边界、三个意图路由、三份 Source of Truth 定位、ArtifactStore 调用边界、最小 Input / Output / Workflow / Failure Contract、Exclusive Skill Execution Contract 和资源按需加载规则。不得复制整份 Core Spec、Artifact Store Spec 或 Project Context Spec，也不得成为第二份领域 Contract。

本阶段不创建该文件。

### `agents/openai.yaml`

Codex 适配时使用 Skill 私有 `skills/sdlc-project-context/agents/openai.yaml` 登记 `policy.allow_implicit_invocation: false`。在获得独立 Codex `adapt` 工作包授权前不得创建；本阶段不创建。

### `references/`

最小实现预期为 `None`。正式规则直接从 Plugin 内 `docs/v1.1/core-spec.md`、`docs/v1.1/artifact-store-spec.md` 与 `docs/v1.1/000-ctx-spec.md` 读取并计算 Spec Reference，避免复制形成平行 Contract。只有实际实现证明 `SKILL.md` 无法精炼表达非领域的操作路由时，才可在新的明确工作包中增加 Skill 私有 reference；reference 只能解释操作，不得重定义字段、Store Operation、枚举或 Gate。

### `scripts/`

Skill 私有脚本预期为 `None`。确定性的 Store 读写、原子事务、read-after-write、完整 Payload 校验和摘要验证必须由后续独立工作包实现并验证的 Plugin 内部 `ArtifactStore` 模块提供；本 Skill 不散落 SQL，也不拥有 SQLite Schema 或 Migration。

`ArtifactStore` 必须只实现 Artifact Store Spec 已登记的逻辑操作，并在首版把物理执行限定为项目根 `.sdlc/store.sqlite3`；不得判断业务事实、选择 Project Boundary、批准 Exception、生成 Final Confirmation、联网、安装依赖、修改用户配置、建立 Provider 框架或生成文件系统 Artifact fallback。本阶段不创建模块或脚本。

### `assets/`

`None`。CTX 固定模板由 Source of Truth 定义，生成时直接依据准确 Spec Snapshot 物化；不维护可漂移的独立模板副本。

### Fixtures / Eval Results

`None` in this stage。Fixture 仅在后续 `evaluate` 工作包按已批准 Eval Plan 创建；`EVAL-RESULTS.md` 只记录实际运行证据。

### 共享资源判断

当前不建立 Skill 私有或通用脚本、参考资料、模板或库。`DEVELOPMENT.md` 已将最小 Plugin 内部 `ArtifactStore` 模块登记为唯一持久化执行边界，但其 Schema、Migration、模块位置、接口实现和验证必须由后续独立工作包决定；本 Design 只依赖该边界，不实现或扩展它。

## 16. Portability Contract

| Concern | Portable Core | Cursor Adapter | Claude Code Adapter | Codex Adapter |
|---|---|---|---|---|
| Skill source | `skills/sdlc-project-context/` 是唯一共享权威源码 | 只引用共享目录 | 只引用共享目录 | 只引用共享目录 |
| Invocation | 只接受显式调用；未调用不自动加载 | `SKILL.md` 使用 `disable-model-invocation: true` 并实际验证 | `SKILL.md` 使用 `disable-model-invocation: true` 并实际验证 | Skill 私有 `agents/openai.yaml` 使用 `policy.allow_implicit_invocation: false` 并实际验证 |
| Path resolution | 从宿主提供的 Plugin / Skill 根定位三份 Source of Truth；从用户目标唯一确定 Project Root；首版 Store 只解析为 `<project-root>/.sdlc/store.sqlite3`；不依赖固定 CWD、作者绝对路径、目录扫描或脆弱多层 `../` | Adapter 只提供原生根路径解析 | Adapter 只提供原生根路径解析 | Adapter 只提供原生根路径解析 |
| Platform-specific metadata | 不进入 CTX Artifact、Gate 或状态语义 | 仅 Cursor 原生元数据 | 仅 Claude Code 原生元数据 | 仅 `agents/openai.yaml` UI 与调用策略 |
| Behavior evidence | 相同 Fixture 分别验证核心语义 | 证据只适用于 Cursor | 证据只适用于 Claude Code | 证据只适用于 Codex |

任何平台差异不得改变 CTX Canonical Payload、Artifact Store Operation、Basis、Identity、Revision、Open Items、Gate、Status、Failure Contract 或权限边界。一个 Client 的成功证据不得复制给另一个 Client。

## 17. Eval Plan

对应文件：

`docs/plugin-development/work-items/sdlc-project-context/EVAL-PLAN.md`

覆盖范围：

- 至少 2 个显式正向触发案例和 2 个未触发 / 不应触发案例；
- `create` 完整输入、必要输入缺失、`revise` Revision 更新、`check` 只读检查；
- v1.1 三份 Evaluation Contract Set、完整 Canonical Revision Payload、Store Control Reservation 与 materialized Revision 的边界；
- Local SQLite 固定路径、ArtifactStore-only 调用、无 Provider 配置、无直接 SQL 和无文件系统 fallback；
- 同 Boundary 多 Lineage、无有效变化和无效 Context Reference 等冲突或边界；
- `observed / confirmed / referenced` Basis、`waiting_input`、Open Items、冻结和下游影响边界；
- 同一 Prompt 与 Fixture 的 with-skill / without-skill 对比；
- 未授权外部 Skill、授权不传递、缺少授权时停止、外部冲突输出不改变当前 Contract；
- Cursor、Claude Code、Codex 的 Explicit Invocation First 实际验证，并记录每次运行是否发生其他 Skill / Plugin Invocation。

## 18. Definition of Done — Design

- [x] 单一职责明确。
- [x] In Scope 和 Out of Scope 不重叠。
- [x] 应触发和不应触发场景可区分。
- [x] `create / revise / check` 三种意图边界可判定。
- [x] 必要输入和缺失行为明确。
- [x] 输出、成功和失败条件可判定。
- [x] CTX Identity、Revision、冻结和 Context Reference 边界明确。
- [x] v1.1 Core、Artifact Store 与 Project Context 三份 Source of Truth 已完整绑定。
- [x] Canonical Store、Revision Control Record、完整 Canonical Revision Payload 与准确 Reference 解析边界明确。
- [x] Local SQLite 与 Plugin 内部 ArtifactStore 执行边界明确，未定义 Schema、Migration 或实现。
- [x] `observed / confirmed / referenced` Basis 行为明确。
- [x] `waiting_input` 和 Open Items 行为明确。
- [x] 权限和副作用满足最小权限。
- [x] Skill / Plugin Interoperability Contract 全部字段可判定。
- [x] Exclusive Skill Execution Contract 未被描述为硬安全隔离。
- [x] 三端 Explicit Invocation First 默认策略已登记。
- [x] `SKILL.md`、`agents/openai.yaml`、references、scripts、assets、fixtures 和 Eval Results 边界明确。
- [x] Eval Plan 足以验证触发、行为、隔离与三端调用策略。
- [x] 不存在阻塞实现的 Open Item。
- [x] 本阶段没有创建正式 `SKILL.md`。

## 19. Open Items

| ID | Question / Missing Decision | Blocks | Expected Source | Status |
|---|---|---|---|---|
| None | 当前没有阻塞 Design approval 的 Open Item | N/A | N/A | closed |

## 20. 确认记录

| Role | Decision | Basis |
|---|---|---|
| Maintainer | `pending` | Design 已达到 `ready`，但尚未收到 Maintainer 明确批准；不得自行标记 `approved` 或进入 `implement` |
