---
title: Requirement Phase Spec
status: stable
version: "1.0"
scope: 已确认的 REQ Artifact 结构与 Gate
---

# Requirement Phase Spec

## Phase 目标

REQ 将任意形式的原始需求转换为结构固定、边界明确、可以被下游准确引用的 Requirement Artifact。

一句话、对话、文档和线上故障都是 Input 形式，不是独立 Lifecycle Profile。输入不足时必须生成结构完整的 `waiting_input` Artifact，不得猜测后生成形式上的 `ready` Artifact。

REQ 描述目标、行为、规则、质量要求和强制约束，不提前决定非强制实现方案。

## 输入与输出

| 项目 Item | 要求 Requirement |
|---|---|
| Input | 任意形式的原始需求、可追溯资料、上游 Artifact，以及与当前需求修正相关的冻结 VFY Return 或 RLS Issue Reference 控制输入 |
| Output | 一个主要 Markdown Requirement Artifact 及可选 Supporting Artifact |
| 必要下游条件 | Artifact 达到 `ready` 或经授权的 `ready_with_exception` |

短输入直接保存原文；长输入保存不可变引用或 Evidence。没有上游 Artifact 时，Front Matter 中的 `inputs` 可以为空，原始输入仍必须在正文保留。

- `Return Phase=REQ` 的冻结 VFY Return，以及 Follow-up Disposition 为 `return_req` 的冻结 RLS Issue Reference，是 Control Input，不是 Scope Input；其所属 Revision 必须进入 Front Matter `inputs`，并由 Source Input 使用准确引用承接；
- Control Input 不自动改变 Delivery Scope。对目标、Requirement 或 Acceptance Criteria 的实际修正必须由对应条目和 Evidence 准确引用；确认需要改变 Scope 时按正常 REQ 规则显式修订；
- 新 REQ Revision 只证明问题已在需求层处理；只有后续冻结 VFY Revision 采用修正后的当前 Subject 并证明对应 Required Outcome 后，该问题才算解决。

## Front Matter

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

## 固定模板

```markdown
# <需求标题>

## 摘要 Summary

## 原始输入 Source Input

## 目标与成功条件 Goal and Success

## 范围 Scope

## 影响对象 Affected Parties

## 需求项 Requirements

## 验收条件 Acceptance Criteria

## 依赖 Dependencies

## 生命周期配置 Lifecycle Profile

## 待确认项 Open Items

## 证据 Evidence

## 支撑产物清单 Supporting Artifact Manifest

## 豁免 Exceptions

## 生命周期适用性 Lifecycle Applicability

## 门禁 Gate
```

所有固定章节必须保留。达到 `ready` 或 `ready_with_exception` 前，`Summary`、`Source Input`、`Goal and Success`、`Scope`、`Requirements`、`Acceptance Criteria`、`Lifecycle Profile`、`Lifecycle Applicability` 和 `Gate` 必须具有有效内容；`Affected Parties`、`Dependencies` 及 Core 通用章节允许使用各自唯一的 `None` 空表示。普通章节不使用 Lifecycle Disposition。

`draft` 或 `waiting_input` 中，`Pending — <OPI-ID>` 只用于自由文本单元格或章节正文。ID、枚举、Reference、Front Matter 等 typed value 未确认时保留固定表头但不创建对应正式数据行，由 Open Item 的 `Blocked References` 指向阻塞该位置的稳定 Gate Check ID；不得留歧义空白、使用非法占位值或猜测补全。

## 摘要

用一至三句话说明当前问题和目标结果，不描述非强制实现方案。

## 原始输入

```markdown
| ID | Type | Content or Immutable Reference | Evidence Reference |
|---|---|---|---|
| SRC-001 | text | | N/A |
```

- 短内容直接保留原文；
- 长内容提供不可变引用并在 Evidence 中保留来源；
- 不得仅保存改写后的摘要而丢失原始语义；
- 多个来源必须明确区分；
- Source Input 使用 `SRC-001` 顺序编号，ID 创建后不得重新排序或复用；
- `Type` 使用 `text`、`document`、`conversation`、`incident`、`artifact` 或 `other`；使用 `other` 时说明具体类型；
- `Content or Immutable Reference` 必须填写内联原文或不可变引用；`Evidence Reference` 对完整内联原文和可直接解析的 `Type=artifact` 固定写 `N/A`，其他非内联来源必须填写一个对应 `EVD-ID`，不得留空；
- `Type=artifact` 时必须使用完整 Artifact Reference，并在 Front Matter `inputs` 中登记同一引用；Front Matter 中每个 Input 也必须由一个 Source row 承接，正文 Source 与依赖图不得指向不同 Revision。

## 目标与成功条件

```markdown
| ID | 当前问题 Current Problem | 目标结果与预期用途 Goal, Intended Outcome and Use | 成功条件 Success Condition |
|---|---|---|---|
| GOAL-001 | | | |
```

Goal 使用 `GOAL-001` 顺序编号。成功条件必须可以观察或验证，不得只使用“优化”“提升”“体验更好”等无边界表述。预期用途没有独立内容时仍保留在目标结果中，不另外制造重复条目。

## 范围

```markdown
### 包含 In Scope

-

### 不包含 Out of Scope

-
```

范围必须同时说明包含和不包含内容。Out of Scope 中的内容不再写入 Requirements。

当 REQ 是直接 Binding 来源、建议 `DSN=n/a/waived`、`PLN=n/a/waived` 且 `IMP=required` 时，In Scope 必须额外包含且只包含一行固定格式的直接实施范围：

```markdown
- Direct IMP Scope: <Scope Token Set>
```

Scope Token Set 使用 PLN 固定语法，必须且只能包含一个 `resource:<versioned-resource-id>`，其他 Scope Token 按事实选填；该行是直接 IMP Execution Scope 的权威来源。`DSN=waived` 时还必须由 Lifecycle Applicability 关联有效 Exception。无法从已确认需求确定准确 Token、涉及多个版本化 Resource 或需要协调时，PLN 必须为 `required`，不能由 IMP 补造。

## 影响对象

```markdown
| ID | 对象 Affected Party | Stakeholder Need or Impact |
|---|---|---|
| None | No distinct affected parties | N/A |
```

存在实际对象时删除 `None` 行，并使用 `AP-001` 顺序编号。Affected Party 记录相关人员、系统或群体及其 Need 或 Impact；对象本身不能替代 Goal 或 Requirement 作为 Validation 结论。

## 需求项

```markdown
| ID | 类型 Type | 来源或父项引用 Source or Parent References | 需求描述 Requirement Statement |
|---|---|---|---|
| R-001 | behavior | GOAL-001, SRC-001 | |
```

来源关系必须形成有根无环图：

- `Source or Parent References` 使用 Core Reference Set，直接指向 `SRC-ID`、`GOAL-ID`、`AP-ID`、Parent Requirement 或已登记的不可变外部 Constraint；
- 任一 Requirement 不得直接或间接引用自身，也不得与其他 Requirement 形成循环；
- 每条来源链最终必须到达 `SRC-ID`、`GOAL-ID`、`AP-ID` 中明确的 Stakeholder Need，或已由 `SRC-ID` 登记的不可变外部约束；Requirement Statement 本身不是来源根；
- Parent Requirement 或 Constraint 只作为中间来源时，必须继续满足同一终止规则；无法找到稳定根的派生项不能通过 Gate。

需求类型：

| 值 Value | 含义 Meaning |
|---|---|
| `behavior` | 可观察的系统或用户行为 |
| `rule` | 必须遵守的业务或领域规则 |
| `quality` | 性能、安全、可靠性、服务可用性 Availability、易用性 Usability 等质量要求 |
| `constraint` | 已确定且不可自由选择的边界条件 |

规则：

- 每个需求项保持原子、明确和可验证；
- 内部 ID 使用 `R-001` 顺序编号；
- ID 创建后不得重新排序或复用；
- 每个需求项必须追踪到 `SRC-ID`、`GOAL-ID`、`AP-ID` 或上级 Requirement；引用的条目必须存在且语义支持该需求；
- 设计偏好不能伪装为 `constraint`；
- 新发现的业务规则必须先进入 REQ，不得由下游静默补充。
- Requirements 表中的每一项都是当前 REQ Scope 的正式义务；尚未纳入本次范围的可选想法放入 Out of Scope，不再用优先级暗示可以静默跳过。
- 生命周期执行动作不是产品 Requirement：规划、实现、验证、发版和目标回读分别由 Lifecycle Applicability 与对应 Phase Artifact 约束，不得为了要求某个 Phase 执行而创建产品 Requirement。

## 验收条件

```markdown
| ID | 关联需求 Requirement References | 条件 Condition | 预期结果 Expected Result |
|---|---|---|---|
| AC-001 | R-001 | | |
```

规则：

- Acceptance Criteria 使用 `AC-001` 顺序编号；
- 每个 Requirement Item 至少关联一个 Acceptance Criterion；
- 一个 Acceptance Criterion 可以覆盖多个 Requirement Item；
- 条件和预期结果必须可由 VFY 方法检查；
- 具体发版动作、发版流程是否完成、版本或 Manifest 等发布记录不写入 Acceptance Criteria；产品在目标场景中的可观察行为、可用性和运行约束仍属于 Requirement / Acceptance Criteria，由 VFY 判断，确实只能在正式 Release Target 检查时再以 VFY Method、Exception 和 RLS Post-release Confirmation 承接；
- 不在 REQ 中指定不必要的测试工具或实现方式。

## 依赖

```markdown
| ID | 依赖项 Dependency | 要求状态 Required State | 当前状态 Current State | 状态检查引用 State Check Reference |
|---|---|---|---|---|
| None | No dependencies | N/A | N/A | N/A |
```

存在实际依赖时删除 `None` 行，并使用 `DEP-001` 顺序编号。`Current State` 是生成当前 Revision 时的状态快照；`State Check Reference` 必须准确引用检查来源：可变状态使用可重复执行或实时观察的检查来源，不可变 Artifact 或 Evidence 只证明不可变或单调成立的 Required State。未确认、执行时无法确定性复核或需要协调顺序的依赖进入 Open Items，或使 PLN 为 `required`，不能作为直接 IMP 的已满足事实。

## Lifecycle Profile

```markdown
| Selected Profile | Basis |
|---|---|
| full | |
```

Profile 选择依据直接使用 Core Lifecycle Profile 的固定检查项。生成过程可以推荐并说明依据，最终 Final Confirmation 统一确认整个 Artifact，不建立第二套确认记录。`full`、`lite`、`hotfix` 不直接决定后续 Phase；最终以逐项 Disposition 为准。`Selected Profile` 必须与 Front Matter `profile` 一致。

## Open Items

```markdown
| ID | 所需输入或待确认决策 Needed Input or Decision | 预期来源 Expected Source | 被阻塞项 Blocked References | 状态 State | 解决结果或证据 Resolution or Evidence |
|---|---|---|---|---|---|
| None | No open items | N/A | N/A | none | N/A |
```

字段、枚举和 Status 派生遵循 Core Open Items Contract；`ready` 或 `ready_with_exception` 不允许存在未解决的阻塞项。

## Lifecycle Applicability

```markdown
| Phase | Disposition | Host | 判断依据 Basis |
|---|---|---|---|
| DSN | pending | N/A | Pending — <OPI-ID> |
| PLN | pending | N/A | Pending — <OPI-ID> |
| IMP | pending | N/A | Pending — <OPI-ID> |
| VFY | required | N/A | VFY Artifact 为固定控制点 |
| RLS | pending | N/A | Pending — <OPI-ID> |
```

REQ 提供初始适用性判断。后续 Phase 可以依据新增事实调整，但必须说明与上游判断不同的原因。

该表只对当前 Requirement Artifact 的覆盖范围给出建议；多个 Requirement Artifact 作为直接 Input 同时参与交付时，不能以最后修改时间覆盖其他 Artifact 的判断，必须遵循 Core Delivery Scope Aggregation Contract。

## AI 与人工协作 AI and Human Collaboration

本节是 Phase 执行指导，不进入 REQ Artifact 模板，也不作为 Gate 或 AI 使用率指标。

| 工作 Activity | AI 适合做什么 | 人工适合做什么 | 原因 Reason |
|---|---|---|---|
| 输入整理与追踪 | 保留原文、提取结构、建立 Source 关系 | 确认来源权威性和缺失背景 | AI 擅长结构化，人工掌握真实上下文 |
| Requirement 与 AC 草拟 | 检查原子性、歧义、覆盖和可验证性 | 确认业务语义、边界和预期用途 | 业务事实不能由模型猜测 |
| Profile 与 Applicability | 按固定条件提出建议并说明依据 | 确认风险和实际执行选择 | AI 可一致评估，人工承担决策责任 |
| Open Item 处理 | 识别冲突和所需输入 | 提供或协调权威答案 | AI 能发现缺口，不能创造事实 |

## Gate

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| REQ-G-001 | 原始输入、VFY Return 与 `return_req` RLS Issue Reference 完整保留，正文 Source、Scope 与 Front Matter Input 一致 | pending | |
| REQ-G-002 | 当前问题、目标、预期用途和成功条件明确且可观察 | pending | |
| REQ-G-003 | In Scope、Out of Scope、Affected Parties 和 Dependencies 完整且使用合法空表示；直接 IMP 时 Scope Token 与依赖检查来源准确 | pending | |
| REQ-G-004 | Requirement 原子、明确、属于当前 Scope，且未混入非必要设计方案 | pending | |
| REQ-G-005 | Requirement Source References 可解析、语义有效、无自引用或循环，且每条来源链到达稳定根 | pending | |
| REQ-G-006 | Acceptance Criteria 覆盖全部 Requirement，且可以由 VFY 检查 | pending | |
| REQ-G-007 | Selected Profile、Basis 与 Front Matter 一致 | pending | |
| REQ-G-008 | Lifecycle Applicability 的 Disposition、已注册 Host 和判断依据完整一致 | pending | |
```

Artifact Gate 先包含 Core Gate Checks，再包含以上 REQ Gate Checks；之后按 Core Spec 固定顺序保存 Final Confirmation 和唯一 Artifact Gate Summary，不得只修改 Front Matter `status`。REQ Gate Checks 均为 Contract Integrity Check，不允许直接标记为 `n/a` 或 `waived`；具体义务的 Waiver 通过 Lifecycle Applicability 或已注册子义务的 Disposition 与 Exception 表达，REQ Gate 只检查其记录是否合规。

## 内部编号

| 内容 Item | 格式 Format |
|---|---|
| Source Input | `SRC-001` |
| Goal | `GOAL-001` |
| Affected Party | `AP-001` |
| Requirement Item | `R-001` |
| Acceptance Criterion | `AC-001` |
| Dependency | `DEP-001` |
| Open Item | `OPI-001` |
| Evidence | `EVD-001` |
| Exception | `EX-001` |
| Gate Check | `REQ-G-001` |
