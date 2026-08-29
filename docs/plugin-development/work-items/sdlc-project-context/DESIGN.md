# Skill Design Contract — `sdlc-project-context`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-project-context` |
| Stage | `design` |
| Status | `draft` |
| Intended Plugin | `sdlc-ai-spec` |
| Domain Source of Truth | `docs/v1.0/core-spec.md`, `docs/v1.0/000-ctx-spec.md` |
| Work Package | `docs/plugin-development/work-items/sdlc-project-context/` |

`draft` 表示 Artifact Store Contract、Projection Contract 尚未进入正式 v1.1 Source of Truth，当前 Persistence 与路径假设不能批准；阻塞项关闭前不得进入 `implement`。

## 2. 问题与用户结果

### Problem

项目长期事实、规则和约束如果只存在于会话记忆、宿主指令、可移动路径或零散文档中，后续 Lifecycle Artifact 容易重复获取、误推断或绑定错误上下文。当前需要一个只围绕 Project Context（CTX）Artifact 工作的稳定执行入口，使创建、修订和检查均遵守同一 v1.0 Contract。

### Intended User Outcome

用户显式调用本 Skill 后，可以：

- 创建一个符合 `sdlc-ai-spec/project-context/v1` 的 CTX Artifact；
- 修订同一 Project Boundary 的既有 CTX Lineage，同时保持 CTX ID、Item ID、Revision 和冻结语义；
- 只读检查指定 CTX Revision 的结构、引用、Basis、Open Items、Gate 与可解析性；
- 在必要事实不足时得到准确的 `waiting_input` 和 Open Items，而不是猜测事实或形成形式上的 `ready`；
- 在确认冲突、无效引用或 Check 失败时得到 `failed` 或明确检查失败结论，而不是静默降级。

## 3. 单一职责

本 Skill 的单一职责是：依据绑定的 v1.0 Core Spec 与 Project Context Spec，对一个 Project Boundary 的 CTX Artifact 执行创建、修订或检查，并保持其长期事实、控制结构和状态语义一致。

创建、修订和检查是同一 CTX Contract 的三个操作模式，不是三个独立 Skill，也不授权执行任何 Lifecycle Phase。

### In Scope

- 识别本次意图为 `create`、`revise` 或 `check`。
- 读取并绑定 `docs/v1.0/core-spec.md` 与 `docs/v1.0/000-ctx-spec.md` 的准确 Spec Reference。
- 收集、分类和验证 Project Identity、Resource、Technology、Engineering Entry、Project Topology、Project Rule、Environment 与 Constraint。
- 为正式 Context 数据登记 `observed`、`confirmed` 或 `referenced` Basis 和可解析的 Basis References。
- 创建或维护 `artifacts/000-ctx/<CTX-ID>/revision-index.md` 与对应 Revision 目录。
- 保持 CTX Identity、Revision、Item ID、Evidence ID、Supporting Artifact ID、Exception ID 和 Open Item ID 的稳定性。
- 生成或修订 CTX 固定 Markdown Artifact、Evidence、Refresh Summary、Supporting Artifact Manifest、Exceptions、Open Items、Final Confirmation 和 Gate。
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
- 无法定位唯一 Project Root、Artifact Store 或目标 Lineage 时，不按名称、目录或内容相似度猜测，也不分配或修改 Artifact；只有目标 Lineage 已安全确定但 CTX 内必要事实尚待确认时，才在该 open Revision 登记 Open Item 并保持 `waiting_input`。检查模式只报告无法判定。
- 用户显式调用本 Skill 但请求完全超出范围时，说明边界并交还控制权，不自动调用其他 Skill。

## 5. 三种用户意图边界

| Intent | Preconditions | Allowed Mutation | Identity / Revision Behavior | Completion Boundary |
|---|---|---|---|---|
| `create` | Project Boundary 可确定；Artifact Store 可定位；没有同一 Boundary 的既有 CTX Lineage；写入已由当前请求授权 | 只可创建一个新 CTX Lineage、Revision Index 和 Revision 1 | 分配新 `CTX-<YYYYMMDDHHMMSS>-<NN>`；Revision 1；`Base Revision=None` | 形成准确 open Revision；只有全部 Gate 与 Final Confirmation 满足时才可冻结 |
| `revise` | 目标 CTX ID 唯一；Revision Index 和 Base Revision 可解析；写入已由当前请求授权 | 只可修改唯一 open Revision，或在 Frozen Revision 后创建新的最大 Revision | 不改变 CTX ID；open Revision 原地修正不增号；Frozen Revision 后使用最大 Revision + 1；无有效变化不创建空 Revision | Refresh Summary 准确登记变化；不自动改写下游 Context Reference |
| `check` | 指定文件、CTX ID 或准确 Context Reference 可唯一解析 | 默认无写入；不修复、不分配 ID、不改变 Gate 或 Status | 按目标 Revision 原样检查；不得回退到 `latest/current` 或其他 Revision | 输出可判定的检查报告；报告不构成 Artifact Gate 或 Final Confirmation |

补充规则：

- 未冻结的 `draft`、`waiting_input` 或 `failed` Revision 可以在 `revise` 中继续修正；内容变化后旧 Check、Gate Summary 和 Final Confirmation 立即失效并重置为 `pending`。
- `ready` 或 `ready_with_exception` Revision 冻结后，任何内容或控制字段变化都必须创建新 Revision；排版或文字修正也不例外。
- 项目重命名、目录迁移或仓库地址变化不改变 CTX ID。只有 Project Boundary 明确拆分为独立项目时，新项目分别创建 CTX ID。
- 已确认同一 Artifact Store 中存在两个描述同一 Project Boundary 的 CTX Lineage 时属于冲突，不得选择其中一个继续或再创建第三个 Lineage。

## 6. Skill / Plugin Interoperability Contract

| Field | Contract |
|---|---|
| Execution Mode | `exclusive execution mode from explicit invocation until completion, stop, or control handoff` |
| Active Scope | 当前 CTX Artifact 的 `create / revise / check` 意图及用户本次请求明确授权的文件范围 |
| Authorized External Skills / Plugins | 默认为 `None`；只有用户在当前请求中明确点名并说明用途的 Skill / Plugin 才可使用 |
| Unauthorized Dependency Behavior | 当前 Contract 能独立满足时继续且不调用外部能力；否则停止并请求对准确名称与用途的授权 |
| Sibling Skill Policy | 默认禁止调用、委托给或合并任何 `sdlc-ai-spec` 兄弟 Skill；本 Skill 不推进 REQ、DSN、PLN、IMP、VFY 或 RLS |
| External Output Treatment | 只可作为 Input 或 Supporting Evidence；必须重新按 `observed / confirmed / referenced` 和 Evidence Contract 评估，不得覆盖当前 Source of Truth、Artifact Contract、Gate、Failure Contract、权限或授权边界 |
| Runtime Enforcement Level | `evaluable behavioral contract; not a non-bypassable security isolation` |
| Platform Invocation Policy | Cursor 与 Claude Code 的正式 `SKILL.md` 使用 `disable-model-invocation: true`；Codex 的 Skill 私有 `agents/openai.yaml` 使用 `policy.allow_implicit_invocation: false`；分别通过显式调用与未调用对照做实际宿主验证 |

必须保持：

- 对一个 Skill / Plugin 的授权不传递给其依赖、下游或其他能力。
- 系统指令、安全约束、宿主权限、适用的项目指令和普通 Tool 不属于被禁止的外部 Skill / Plugin。
- 外部输出与 v1.0 Source of Truth 冲突时，不合并出折中语义；记录冲突并停止受影响的写入或最终化。
- 本 `design` 阶段只登记上述策略，不创建 `SKILL.md`、`agents/openai.yaml` 或任何平台适配文件。

## 7. Input Contract

| ID | Input | Required | Source | Validation | Missing Behavior |
|---|---|---:|---|---|---|
| IN-01 | Operation Intent：`create / revise / check` | yes | 当前用户请求 | 必须与目标和授权相容且可唯一判定 | 停止写入并询问一个阻塞问题 |
| IN-02 | Domain Source of Truth | yes | Plugin 内 `docs/v1.0/core-spec.md`、`docs/v1.0/000-ctx-spec.md` | 文件可读；计算准确 SHA-256；规则无冲突 | 停止，不使用历史记忆或旧 Validator 代替 |
| IN-03 | Project Root、Artifact Store 与 Project Boundary | create/revise: yes; check: target-dependent | 用户提供、项目配置、可验证目录状态、权威文档 | 路径在授权项目内；目标 Boundary / Lineage 可安全定界；不得用目录名猜测业务边界 | 无法安全定界时不分配或修改 Artifact；目标已定但必要 Boundary 事实待确认时登记 Open Item 并派生 `waiting_input`；check 只报告无法唯一检查 |
| IN-04 | 目标 CTX Identity 与 Revision 状态 | revise/check: yes; create: absence evidence | Revision Index、目录、Front Matter、用户提供的准确 Reference | ID、目录、Revision、Index State 唯一一致；检查是否已有同 Boundary Lineage | 不创建或覆盖；未知时等待输入，确认冲突时失败 |
| IN-05 | Project Identity：Project Name、Purpose、Boundary、Primary Resource Reference | ready: yes | `confirmed` Evidence，或 Primary Resource 的 `observed` Evidence | 四个固定字段非 `None / N/A`；Basis 与引用合法 | 不猜测；每个真实缺口唯一登记 Open Item，Status=`waiting_input` |
| IN-06 | Resource Registry 与不可变 Baseline | ready: yes | 可重复观察的 Resource 状态、权威引用或确认 Evidence | 至少一个 `Role=primary`；Locator 唯一可解析；版本化 Resource 有不可变 Baseline Reference | 建立 Open Item；不能用可移动分支、`latest/current` 代替 |
| IN-07 | 适用的长期 Technology、Engineering Entry、Topology、Rule、Environment、Constraint | applicable facts: yes | 代码、配置、工具结果、项目状态、权威文档或有权确认者 | 只保留后续重复使用的稳定内容；适用性和 Basis 可证明 | 未知且影响 Gate 时建立 Open Item；客观不存在时使用带 Basis 的唯一 `None` 行 |
| IN-08 | Basis References 与 Evidence | yes for every formal Context datum | 本地可验证结果、确认记录、准确不可变引用 | `observed` 引用 Evidence；`confirmed` 引用确认 Evidence；`referenced` 使用准确不可变引用 | 候选推断不进入正式数据；转为 Open Item |
| IN-09 | Revision 变化依据 | revise: yes | Frozen Base Revision、当前项目状态、确认或权威引用 | Effective Change 可解析；同一语义保持 Item ID；无有效变化可证明 | 不创建空 Revision；报告 no-op |
| IN-10 | Final Confirmation 与权限依据 | only for finalization | 项目实际授权角色或符合 Core 委托边界的独立 Reviewer 记录 | 绑定当前 Revision、Control Input Digest、Evaluation Contract Set、Check Set Result Digest；Authority Reference 可解析 | Gate 保持 `pending`；若只是确认尚未完成则 Status=`draft`，不伪造人工身份 |
| IN-11 | 写入授权 | create/revise: yes; check: no | 当前用户请求与宿主权限 | 授权覆盖准确项目与 CTX Artifact Store；不推断远程写入权限 | 不写入；报告被阻塞的目标和所需授权 |
| IN-12 | 外部 Skill / Plugin 授权 | no | 当前用户请求 | 必须逐项点名并限定用途；不接受传递授权 | 默认为 `None`；能独立完成则继续，否则停止请求授权 |

Input Contract 不依赖上一会话的隐式记忆。会话中已知但尚未持久化、无法形成合法 Basis 的信息只能作为候选材料。

## 8. Output Contract

| ID | Output | Format / Location | Required Content | Success Condition | Consumer |
|---|---|---|---|---|---|
| OUT-01 | CTX Revision Index | `artifacts/000-ctx/<CTX-ID>/revision-index.md` | Core 固定表；准确 `open / frozen / abandoned` State、Base Revision 与时间 | 与目录和主文件一致；编号不复用；状态变化合法 | Revision Resolver、后续 CTX Revision |
| OUT-02 | CTX 主 Artifact | `artifacts/000-ctx/<CTX-ID>/revisions/<6 位 Revision>/<CTX-ID>.md` | 固定 Front Matter、全部固定章节、Basis、Open Items、Evidence、Refresh Summary、Manifest、Exceptions、Final Confirmation 与 Gate | 结构、引用、摘要、Check、Status 和 Index 一致；不存在猜测的正式事实 | Lifecycle Artifact、人工 Reviewer、Validator |
| OUT-03 | Supporting Artifacts | 当前 Revision 目录内，由 Manifest 登记 | 只包含确有必要的不可变 Evidence 或原生材料；准确 Media Type、Purpose 与 SHA-256 | Manifest 与成员集合、字节摘要一致；无成员时使用唯一 `None` 行 | CTX Gate、后续检查 |
| OUT-04 | Open Items / `waiting_input` 结果 | CTX 主 Artifact 的 `Open Items` 与 Front Matter | 每个真实必要缺口恰好一条稳定 `OPI-<NNN>`；Expected Source、Blocked References、State 完整 | 任一 `State=open` 在无 fail 时派生 `waiting_input`；不存在自由占位或伪输入项 | 用户、后续修订 |
| OUT-05 | 检查报告 | 当前响应；除非用户另行授权，不创建独立文件 | 目标、检查基线、通过项、失败项、缺失项、预期 Status、Context Reference 可用性、副作用=`None` | 结论可追溯到 Core / CTX Check；不修改目标 Artifact | 当前用户 |
| OUT-06 | 影响报告 | 当前响应；修订模式同时由 Refresh Summary 保存权威变化 | 新 Revision 对 Scope、Resource、Rule、Engineering Entry、Constraint 的有效变化，以及下游重新检查边界 | 不自动改写旧 Context Reference；只指出最早可能受影响 Artifact | 当前用户、后续 Lifecycle 工作流 |

输出必须区分：

- Agent 对候选材料的分析；
- 由脚本或普通 Tool 得到的确定性检查与摘要；
- 需要人工确认的 Project Boundary、业务事实、Exception、风险与 Final Confirmation；
- 尚未解决、会阻塞合法结论的 Open Items。

“文件已生成”不等于 Gate 通过。只有 `ready` 或 `ready_with_exception` 且 Revision Index 为 `frozen` 的 CTX Revision 才可作为有效 Context Reference。

## 9. Workflow Contract

1. **进入独占模式并定界**：确认 `$sdlc-project-context` 被显式调用，判定 `create / revise / check`，记录当前授权、目标 Project Boundary、Artifact Store 和 External Skill / Plugin 授权清单。
2. **绑定规则**：从 Plugin 根定位并读取准确 Core Spec 与 Project Context Spec，计算 Spec References；规则缺失、不可读或冲突时停止。
3. **解析 Identity 与 Revision**：检查 `artifacts/000-ctx/`、Revision Index、目录和 Front Matter。`create` 证明不存在同 Boundary Lineage后分配唯一 CTX ID；`revise` 解析唯一 Lineage 和 Base Revision；`check` 锁定准确目标而不使用可移动别名。
4. **建立可恢复的 open Revision**：仅 `create / revise` 执行。按 Core Revision Resolver 在同一排他临界区内持久化并读回 Index 行、Revision 目录及带固定骨架的主文件；失败时继续恢复或准确标记 `abandoned`，编号不得删除或复用。
5. **收集并分类事实**：只读取当前 Boundary 和请求必要的本地资料。将正式数据分类为 `observed / confirmed / referenced`，生成对应 Evidence 或准确引用；不稳定推断留作候选材料。
6. **处理缺口与冲突**：缺少必要事实时建立唯一 Open Item，并在无 fail 时派生 `waiting_input`；已确认冲突、无效引用或 Check 失败时记录 Evidence、Gate `fail` 和 `failed`；不通过 Exception 把未知变成已知。
7. **执行意图分支**：`create` 完成 Revision 1；`revise` 保持稳定 ID、对比 Base Revision 并更新 Refresh Summary；`check` 只读复算结构、引用、摘要、Check 与 Status，不生成或修改 Revision。
8. **验证与最终化**：仅对 `create / revise` 按 Core 固定顺序处理 Control Input Digest、Check Set Result Digest、Final Confirmation、`CORE-G-001` 至 `CORE-G-009`、`CTX-G-001` 至 `CTX-G-006`、Gate Summary 和派生 Status。缺少合法 Final Confirmation 时保持 `draft` 或由真实 Open Item 派生 `waiting_input`。
9. **冻结或停止**：只有 Gate 为 `pass / pass_with_exception` 且 Status 对应 `ready / ready_with_exception` 时才把 Index State 更新为 `frozen`。其余保持准确 open/abandoned 状态，不描述为可供下游使用。
10. **报告**：报告模式、目标 Reference、实际写入、Status、Open Items、Check 结果、下游影响、未执行项和外部 Skill / Plugin 实际调用记录；完成、停止或明确交还控制权后退出独占模式。

## 10. CTX Identity、Revision、冻结与 Context Reference 边界

- 一个 Project Boundary 维护一个稳定 CTX ID；内容更新只增加 Revision。
- CTX ID、目录、Front Matter 和 Revision Index 必须一致，且同一 Artifact Store 内不得存在两个同 Boundary CTX Lineage。
- ID 和 Revision 分配先持久化控制记录并读回，再生成正式内容；并发冲突时重新读取最大值并重试，不覆盖已有内容。
- 同一时刻最多一个 `open` Revision；`frozen` 与 `abandoned` 是终态，不可重新打开。
- `Base Revision` 只定位同一 CTX 的内容来源，不是 Input 或 Authority；Revision 1 固定为 `None`。
- `ready / ready_with_exception` 冻结后不可原地修改；任何变化创建新最大 Revision。
- 新 CTX Revision 不自动改写或使既有 Lifecycle Artifact 失效；采用新 Revision 时，根据 Refresh Summary 只修订最早实际受影响的 Lifecycle Artifact。
- 有效 Context Reference 固定为 `<CTX-ID>@<Revision>`，并要求 Revision `frozen`、Status 可供下游使用、主文件与控制结构可验证。
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
| Source of Truth 缺失或冲突 | Spec 文件不可读、摘要不可计算、Core 与 CTX 语义无法同时满足 | 停止受影响工作；报告路径、冲突和所需权威；不创建或最终化 Artifact | 使用记忆、旧 Validator、常识或折中语义代替 |
| Operation Intent 或目标不唯一 | 无法唯一判定模式、Project Boundary、Artifact Store、CTX ID 或 Revision | 不写入；请求一个阻塞输入；可在已分配的合法 open Revision 中登记 Open Item | 按名称、目录、最新时间或内容相似度选择目标 |
| 必要事实未提供 | Project Identity、Primary Resource、Baseline、适用长期事实或 Basis 缺失 | 建立 Open Item，Gate=`pending`，Status=`waiting_input`；保留已验证部分 | 猜测事实、使用自由占位或形成 `ready` |
| 已确认冲突或无效引用 | 同 Boundary 多 Lineage、Locator 冲突、Reference 不可解析、Check=`fail` | 保存 Evidence；Gate=`fail`，Status=`failed`；检查模式报告失败 | 当作待输入、忽略冲突或选择方便的 Lineage |
| Revision 分配或物化中断 | Index、目录、主文件任一未按 Core 原子边界完成或读回失败 | 保持执行权并恢复；无法完成时准确标记 `abandoned`，保留编号和原因 | 删除编号、复用 Revision、覆盖既有内容或留下伪 Artifact |
| Frozen Revision 被要求原地修改 | 目标 Index State=`frozen` | 创建新最大 Revision；保持 Frozen Snapshot 不变 | 原地编辑、重开 Frozen Revision、只更新阅读视图冒充 Revision |
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
| Read local files | yes | 当前 Project Boundary、CTX Artifact Store、Plugin 内两份 Source of Truth，以及用户提供的准确 Evidence | 当前请求允许的项目读取；敏感信息按最小必要读取 |
| Write repository files | create/revise: yes; check: no | 仅当前项目 `artifacts/000-ctx/<CTX-ID>/` 及用户明确提供的项目内确认依据路径 | `create / revise` 的明确用户意图；检查默认无写入 |
| Execute local commands | yes | 只读发现、SHA-256、结构校验、确定性 ID / Revision 分配和读回 | 当前项目内普通 Tool；不安装依赖、不修改全局配置 |
| Network read | no by default | 只有用户明确提供且当前 Basis 必须使用的权威来源 | 每个外部来源按当前请求授权；结果仍需不可变引用或摘要 |
| External write | no | None | 未纳入本 Skill Contract；即使用户授权外部读取也不含写入 |
| Invoke other Skill / Plugin | no by default | 仅用户当前请求逐项点名的能力和用途 | explicit only; no transitive authorization |

默认禁止自动安装依赖、修改用户级或系统级配置、破坏性 Git 操作、commit、push、远程 API 写入和读取无关敏感信息。

## 15. 资源边界

### `SKILL.md`

后续 `implement` 只在 `skills/sdlc-project-context/SKILL.md` 保留：显式触发边界、三个意图路由、Source of Truth 定位、最小 Input / Output / Workflow / Failure Contract、Exclusive Skill Execution Contract 和资源按需加载规则。不得复制整份 Core Spec 或 Project Context Spec，也不得成为第二份领域 Contract。

本阶段不创建该文件。

### `agents/openai.yaml`

Codex 适配时使用 Skill 私有 `skills/sdlc-project-context/agents/openai.yaml` 登记 `policy.allow_implicit_invocation: false`。在获得独立 Codex `adapt` 工作包授权前不得创建；本阶段不创建。

### `references/`

最小实现预期为 `None`。正式规则直接从 Plugin 内 `docs/v1.0/core-spec.md` 与 `docs/v1.0/000-ctx-spec.md` 读取并计算 Spec Reference，避免复制形成平行 Contract。只有实际实现证明 `SKILL.md` 无法精炼表达非领域的操作路由时，才可在新的明确工作包中增加 Skill 私有 reference；reference 只能解释操作，不得重定义字段、枚举或 Gate。

### `scripts/`

后续最小实现预期需要一个 Skill 私有确定性工具，边界限于：

- 在授权的 Artifact Store 内分配或恢复 CTX ID / Revision；
- 原子物化并读回 Revision Index、Revision 目录和固定主文件骨架；
- 计算 SHA-256、Control Input Digest、Check Set Result Digest；
- 只读验证固定 Front Matter、章节、表格、Reference Set、Manifest、Index 与 Gate 一致性；
- 输出明确退出码和诊断。

脚本不得判断业务事实、选择 Project Boundary、批准 Exception、生成 Final Confirmation、联网、安装依赖、修改用户配置、自动修复 Frozen Revision 或写出 `artifacts/000-ctx/` 之外。脚本名称与 CLI 形态由 `implement` 在不扩大本边界的前提下选择；本阶段不创建脚本。

### `assets/`

`None`。CTX 固定模板由 Source of Truth 定义，生成时直接依据准确 Spec Snapshot 物化；不维护可漂移的独立模板副本。

### Fixtures / Eval Results

`None` in this stage。Fixture 仅在后续 `evaluate` 工作包按已批准 Eval Plan 创建；`EVAL-RESULTS.md` 只记录实际运行证据。

### 共享资源判断

当前没有第二个真实使用者，不建立 Plugin 根级共享脚本、参考资料、模板或库。未来如出现第二个已验证使用者，必须通过独立工作包评估提升，且不得改变 CTX Contract。

## 16. Portability Contract

| Concern | Portable Core | Cursor Adapter | Claude Code Adapter | Codex Adapter |
|---|---|---|---|---|
| Skill source | `skills/sdlc-project-context/` 是唯一共享权威源码 | 只引用共享目录 | 只引用共享目录 | 只引用共享目录 |
| Invocation | 只接受显式调用；未调用不自动加载 | `SKILL.md` 使用 `disable-model-invocation: true` 并实际验证 | `SKILL.md` 使用 `disable-model-invocation: true` 并实际验证 | Skill 私有 `agents/openai.yaml` 使用 `policy.allow_implicit_invocation: false` 并实际验证 |
| Path resolution | 从宿主提供的 Plugin / Skill 根定位 Source of Truth；从用户目标或项目根定位 Artifact Store；不依赖固定 CWD、作者绝对路径或脆弱多层 `../` | Adapter 只提供原生根路径解析 | Adapter 只提供原生根路径解析 | Adapter 只提供原生根路径解析 |
| Platform-specific metadata | 不进入 CTX Artifact、Gate 或状态语义 | 仅 Cursor 原生元数据 | 仅 Claude Code 原生元数据 | 仅 `agents/openai.yaml` UI 与调用策略 |
| Behavior evidence | 相同 Fixture 分别验证核心语义 | 证据只适用于 Cursor | 证据只适用于 Claude Code | 证据只适用于 Codex |

任何平台差异不得改变 CTX 文件结构、Basis、Identity、Revision、Open Items、Gate、Status、Failure Contract 或权限边界。一个 Client 的成功证据不得复制给另一个 Client。

## 17. Eval Plan

对应文件：

`docs/plugin-development/work-items/sdlc-project-context/EVAL-PLAN.md`

覆盖范围：

- 至少 2 个显式正向触发案例和 2 个未触发 / 不应触发案例；
- `create` 完整输入、必要输入缺失、`revise` Revision 更新、`check` 只读检查；
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
- [x] `observed / confirmed / referenced` Basis 行为明确。
- [x] `waiting_input` 和 Open Items 行为明确。
- [x] 权限和副作用满足最小权限。
- [x] Skill / Plugin Interoperability Contract 全部字段可判定。
- [x] Exclusive Skill Execution Contract 未被描述为硬安全隔离。
- [x] 三端 Explicit Invocation First 默认策略已登记。
- [x] `SKILL.md`、`agents/openai.yaml`、references、scripts、assets、fixtures 和 Eval Results 边界明确。
- [x] Eval Plan 足以验证触发、行为、隔离与三端调用策略。
- [ ] 不存在阻塞实现的 Open Item。
- [x] 本阶段没有创建正式 `SKILL.md`。

## 19. Open Items

| ID | Question / Missing Decision | Blocks | Expected Source | Status |
|---|---|---|---|---|
| OI-001 | Artifact Store Contract、Projection Contract 尚未进入正式 v1.1 Source of Truth；在 `docs/v1.1/` Spec Snapshot 完成前，当前 Persistence 与路径假设不能批准 | Design approval、`implement` | `docs/architecture/artifact-store-and-projection.md` 与待创建的 `docs/v1.1/` Spec Snapshot | open |

## 20. 确认记录

| Role | Decision | Basis |
|---|---|---|
| Maintainer | `pending` | Design 已回退为 `draft`；`OI-001` 关闭前不得批准或进入 `implement` |
