---
title: VFY Phase Spec
status: stable
version: "1.0"
scope: Verification and Validation Phase 固定模板、执行边界与 Gate
---

# VFY Phase Spec

VFY 对准确、不可变的产品结果执行或复核适用方法，证明其是否符合已确认的 Requirement、Design 和预期用途，并形成可供返工或发版判断使用的结论。

VFY 不是独立 QA Phase 或 Test Phase。Test、Inspection、Analysis 和 Demonstration 是方法；QA 仍由各 Phase 的 Check、Evidence、Gate 和 Final Confirmation 贯穿承载。

## 目标与边界

VFY 负责：

- 绑定当前交付范围内的权威 Target 和准确 Subject；
- 执行尚未完成的方法，或复核可准确复用的上游 Evidence；
- 对每个 Target 形成明确结论；
- 分别形成 Verification 与 Validation 结论；
- 将已确认问题返回其权威 Phase；
- 明确当前未被证明的范围和下游限制。

VFY 不负责：

- 实现产品代码或测试资产；
- 静默补充 Requirement、Design 或 Plan 决策；
- 为提高数量而强制执行无关 Test、工具或环境；
- 把 Artifact `ready` 解释为产品通过或允许交付；
- 定义实际发版、流量控制或持续运行的具体机制。

## 输入与输出

| 类型 Type | 内容 Content |
|---|---|
| Input | 当前交付范围的准确 Scope Source、Target Contract、Subject Result、相关上游 Evidence、项目 Spec 和未关闭 Exception |
| Output | 一个 VFY Artifact、Method Result、Target Conclusion、固定 Verification / Validation Conclusion、必要 Return Record 和支持其结论的 Evidence |

Front Matter `inputs` 必须包含本次实际采用的全部直接上游 Artifact Revision。正文 Item Reference 所属 Artifact 必须已经登记为 Input；外部运行环境和可变数据不是 Artifact Input，其实际状态通过 Evidence 保存。

## Applicability

VFY Artifact 固定为 `required`，不能整体为 `embedded`、`n/a` 或 `waived`。具体 VFY Method 可以使用全部 Lifecycle Disposition。

没有实施变化时，VFY 仍根据当前 Scope 对 Requirement、Design、文档、配置、基线或其他结果形成适用结论，不创建空 Artifact。

## Front Matter

VFY 使用 Core Artifact Front Matter：

```yaml
---
contract: sdlc-ai-spec/artifact/v1
phase: VFY
id: VFY-20260824160000-01
revision: 1
status: draft
context: CTX-20260828143025-01@1
profile: full
inputs:
  - DSN-20260824120000-01@1
  - IMP-20260824150000-01@1
---
```

返工后的 VFY 必须把尚未解决 VFY Return，以及 Follow-up Disposition 为 `return_req`、`return_dsn` 或 `return_imp` 的 RLS Issue 所属冻结 Revision，作为 Control Input 登记到 Front Matter `inputs`。Control Input 不改变 Delivery Scope；Scope 仍由当前权威 Scope Source 决定。

## 固定模板

```markdown
# <VFY Title>

## 摘要 Summary

## 范围 Scope

## 输入与结果集 Input and Result Set

## 追踪与覆盖 Traceability and Coverage

## VFY 方法 VFY Methods

## 方法结果 Method Results

## VFY 结论 VFY Conclusions

## 失败与返回 Failures and Returns

## 待确认项 Open Items

## 证据 Evidence

## 支撑产物清单 Supporting Artifact Manifest

## 豁免 Exceptions

## 生命周期适用性 Lifecycle Applicability

## 门禁 Gate
```

所有固定章节必须保留。详细测试用例、命令输出、日志、截图、录像和扫描报告放入 Evidence 或 Supporting Artifact，不在主要 Markdown 重复展开。

## Scope

一个 VFY Artifact 只判断一个完整 Delivery Scope：

- PLN 为 `required` 时，Scope 绑定准确 PLN Revision 及其完整 Delivery Scope；
- PLN 为 `n/a` 或 `waived` 时，Scope 绑定最近可供下游使用的完整 REQ 或 DSN Artifact，并保留其处置依据或 Exception；
- 多个完整 Scope Input 共同交付时必须先按 Core 完成 Delivery Scope Aggregation；
- 当前 Artifact Contract 不在 VFY 内选择上游 Artifact 的部分 Item，也不自行组合多个候选 Result；
- VFY 可以同时验证当前 Scope 中多个终端 IMP Result，但每个 Subject 必须准确且依赖链连续有效。

## 输入与结果集

```markdown
| ID | 角色 Role | 引用 Reference | 纳入范围 Included Scope | 选择依据 Selection Basis |
|---|---|---|---|---|
| VIN-001 | scope_source | | | |
| VIN-002 | subject | | | |
```

`Role` 只使用：

| Role | 含义 Meaning |
|---|---|
| `scope_source` | REQ、DSN 或 PLN 等当前 Scope 权威来源 |
| `subject` | 实际被判断的 IMP Result、基线或其他准确产品结果 |
| `evidence_source` | 需要复核的上游 Check 或 Evidence |

规则：

- Input ID 使用 `VIN-001` 顺序编号，在当前 Artifact 内稳定且不得复用；
- `Reference` 通常使用准确 Artifact 或 Item Reference；`Role=subject` 时还允许 Core VCS Locator 或项目已注册的不可变 Product Result Locator；同一引用承担多个角色时分别登记；
- `Included Scope` 使用准确 Item Reference、Scope Token 或 `Full Artifact`，不得写“相关内容”；
- PLN 为 `required` 时，必须从其完整 Work Item Set 派生全部 `Target Phase=IMP` 义务；每个 WI 必须唯一解析到匹配 Binding 的 Current `completed` Claim、冻结 IMP Revision 和完整依赖链，未领取、`active`、`abandoned` 或未冻结的 WI 都阻止 VFY 继续；
- 每个计划内 Resource 的权威终端 Result 都进入 Subject Set；是否发生变化按完整 Delivery Scope 的初始 Baseline 到当前终端 Result 的累计差异判断，不能只看最后 Attempt 的局部 Changed Scope；只有整个 Scope 从未变化的基线资源才可以只作为 Input 保存；
- VFY 开始和 Gate 前都必须复核 Subject 仍是当前有效终端 Result，不得自动选择最新、其他或旧 Result；
- Subject 无法准确解析、依赖链不连续或存在尚未吸收的更新时，VFY 不能继续形成结论。

## Target Set

Target Set 按以下固定顺序确定：

1. 当前 Scope 存在可解析 VFY Objective Set 时，使用全部 `VFO-ID`；VFO 已承载其关联的 AC、Goal、Design Decision 和 Domain VFY Point，不在 VFY 重复展开为平行 Target，也不复制 VFP 正文；
2. DSN 为 `n/a` 或 `waived` 且不存在 VFY Objective Set 时，每个 Acceptance Criterion 是 Verification Target，每个 Goal 的 Intended Outcome / Use 和 Success Condition 是 Validation Target；
3. 多个权威 Target Set 按完整 Reference 取并集；不同 Reference 不按标题或文字相似度合并；
4. 上游 Target 缺失、冲突或不可判定时返回 REQ 或 DSN，VFY 不自行补写通过条件。

Requirement 不单独重复进入 Target Set，因为 REQ Gate 已要求每个 Requirement 由 Acceptance Criteria 覆盖。PLN Work Item 是执行安排，IMP Result 是 Subject，IMP Check 是候选 Evidence，三者都不能替代 Target。

## 追踪与覆盖

```markdown
| 目标引用 Target Reference | 目标摘要 Target Summary | Purpose | Conclusion | 依据引用 Basis References | Exception Reference |
|---|---|---|---|---|---|
| DSN-...@1#VFO-001 | | both | pending | None | None |
```

规则：

- 每个权威 Target 恰好一行；
- `Purpose` 使用 `verification`、`validation` 或 `both`；
- Target 到 Method 的唯一权威映射是 VFY Method 索引的 `Target References`；本表只保存聚合结论；
- `Conclusion` 使用 `pending`、`pass`、`fail`、`n/a` 或 `waived`；
- `Basis References` 必须引用实际支持结论的 Method ID 和 Evidence；
- `n/a` 只能继承或引用权威上游不适用依据，环境不可用、没有人员或未执行不能写为 `n/a`；
- `waived` 必须引用有效 Exception，不能计为 `pass`。

## VFY 方法

VFY Method 使用一个简短索引：

```markdown
| ID | Purpose | Target References | Subject References | 义务引用 Obligation References | Method Type | Disposition | 依据或原因 Basis Reference or Reason |
|---|---|---|---|---|---|---|---|
| VFM-001 | verification | | | | test | required | |
```

| Method Type | 含义 Meaning |
|---|---|
| `inspection` | 不运行目标，通过静态查看判断符合性 |
| `analysis` | 根据计算、模型、数据或工具结果推导结论 |
| `demonstration` | 操作或展示产品以确认可观察能力或预期用途 |
| `test` | 在明确输入和条件下执行，并与预期结果及通过条件比较 |

规则：

- Method ID 使用 `VFM-001` 顺序编号，在当前 VFY Artifact 内稳定且不得复用；
- `Purpose` 只使用 `verification`、`validation` 或 `both`；
- 每个适用 Target 至少被一个 Method 覆盖，每个 Method 至少引用一个 Target 和一个准确 Subject；
- Target 与 Method 的 Purpose 必须相容：`verification` Target 只允许由 `verification` 或 `both` Method 覆盖，`validation` Target 只允许由 `validation` 或 `both` Method 覆盖；
- `Obligation References` 是方法义务映射的唯一权威字段：存在 DSN VFY Strategy 时引用准确的上游 `VFP`、`VFM`、`VPC`、`VEC`；没有独立 DSN Contract 时引用准确 AC 或 Goal；PLN 为 `required` 时同时引用适用的 `Target Phase=VFY` Work Item；返工后的 VFY 同时引用尚未解决的 VFY Return，以及 Follow-up Disposition 为 `return_req`、`return_dsn` 或 `return_imp` 的 RLS Issue Reference；
- 每条 VFO 到 VFP 的上游映射，至少由一个同时将该 VFO 列入 `Target References`、并将该 VFP 列入 `Obligation References` 的 Method 承接；
- Method 引用的 VFP 不得超出其全部 Target VFO 所映射 VFP 的并集；VFP 引用只证明映射关系，Method Detail、Procedure、Pass Criteria 和 Evidence Requirement 仍必须完整表达该 Method 在对应 VFO 上下文中实际承接的可判定语义，不能仅凭 ID 引用判定覆盖；
- 当前 Scope 中每个上游 VFM、VPC、VEC、每个 VFY Work Item 和每个适用 Return 必须至少被一个当前 Method 引用，不得只因生成了 Method 行就视为已承接；
- 一个上游义务可以因结果可独立变化而拆到多个 Method；一个 Method 只有在 Procedure、Pass Criteria 和 Evidence Result 可共同判定时才能承接多个义务；
- `Purpose=both` 的 Target 必须由至少一个 verification Method 和一个 validation Method 共同覆盖，或由一个 `Purpose=both` 且其 Procedure、Pass Criteria 与结果可同时支持两个维度的 Method 覆盖；否则 Target 不能为 `pass`；
- 每个 VFY Work Item 的 Completion Criteria 与 Expected Evidence 必须由其映射 Method、Method Result、Target Conclusion 和 Evidence 共同覆盖；未满足时必须形成 Return 或有效 Exception，不能伪装为已完成；
- VFY Work Item 的每个 `Depends On` 必须按目标 Phase 的权威完成规则满足；同为 VFY 的前驱必须先具有最终 Method Result 和 Evidence，不能只因两者出现在同一 Artifact 就视为依赖已满足；
- 一个 Method 只有在同一 Procedure、Pass Criteria 和结果能够同时支持多个 Target 时才可以引用多个 Target；结果可能独立变化时必须拆分；
- `manual`、`automated` 或 `hybrid` 是 Execution Mode，不是 Method Type；
- Unit、Component、Interface、Integration、System 和 End-to-End 是 Test Level，不是 Method Type；
- Functional、Regression、Performance、Security、Recovery、Compatibility 和 Accessibility 是目标或范围描述，不是并列 Method Type；
- Review 通常归为 Inspection；静态计算或扫描通常归为 Analysis；人工操作按是否具有明确输入、预期和通过条件归为 Demonstration 或 Test；
- 不要求每个 Artifact 使用全部四类方法，不设置固定 Test 数量、覆盖率或自动化比例。

所有由当前上游 Contract 或 VFY Work Item 派生、且 Disposition 不是 `n/a` 的 Method 都是必要义务；`waived` 只改变其执行处置，不把它变成非必要项。VFY 不另设可由执行者自由切换的“必要”字段。

### required Method Detail

每个 `required` Method 使用固定详情块：

```markdown
### VFM-001 <Method Title>

- Executor Identity:
- Method Detail:
- Procedure or Basis:
- Pass Criteria or References:
- Evidence Requirement:
```

- `Executor Identity` 记录实际执行该 Method 的稳定执行身份；`required` Method 必须按 Core 填写一个可追踪的执行身份 token；
- `Method Detail` 记录适用的 Test Level、Objective、Execution Mode、环境或范围，不增加顶层枚举；
- `Procedure or Basis` 必须足以重复执行或复核，不绑定无必要的具体工具；
- `Pass Criteria or References` 必须明确可判定，不得只写“正常”或“符合预期”；
- `Evidence Requirement` 说明支持 `pass` 或 `fail` 所需的最小 Evidence。

VFY 的 Pre-execution Checklist 由当前 Revision 的非空 Evaluation Contract Set、Front Matter Context、Input and Result Set、Target 与 Traceability、完整 Method Index 和适用 Method Detail 组成。正式执行会改变隔离环境、测试数据或形成正式 Evidence 的 Method 前，必须按 Core 持久化、读回并保存 Evidence；此前输出只能作为候选材料，必须在 Checklist 建立后按当前 Subject 和 Method Contract 独立执行或复核。

不可解析 Artifact 及其 Evidence Reference 不能作为当前 Input、`evidence_source` 或 Basis，其底层不可变字节也只能作为 Candidate Material。需要采用这些字节时，必须在当前 Checklist 读回后以新 Supporting Member 和摘要重新登记，按当前 Subject、Target 与 Method Contract 独立执行或复核，并形成新的 Evidence 和 Method Result。旧字节复核只能证明本次可观察内容，不能重新证明旧环境、时间、执行动作或外部副作用；无法由当前读回重建时必须重新执行。旧 Evidence、Method Result、Conclusion、Gate、Final Confirmation、Return 或 RLS 结论均不提供当前 Authority。

`embedded` 不复制 Host 内容；索引的 Basis 必须引用准确 Host Method、当前 Subject 和可复核 Evidence。`n/a` 不生成详情块；普通 `waived` 不生成空详情块，其 Exception 由索引承载。只能在正式 Release Target 执行而延期到 RLS 的 `waived` Method 必须保留上述完整 Method Detail，固定下游 Procedure、Pass Criteria 和 Evidence Requirement。Method 的 `Disposition=pending` 不能通过 Gate，失败检查点早停也不例外。

### IMP Test Boundary

- Test 资产的实现和修改属于 IMP；
- 为开发反馈和 IMP 完成检查而执行的 Unit Test、Build、Static Check 或局部运行检查属于 Implementation Check；
- VFY 只在这些结果支持当前 Target 且准确对应最终 Subject 时，将其作为 `embedded` Method 复核；
- Subject 变化、Evidence 无法证明对应关系、上游要求独立复核或风险需要重执行时，VFY 使用 `required` Method；
- IMP Test 通过只表示实现具备进入 VFY 的条件，不表示 VFY 通过或允许 RLS。

### Execution Limitations

VFY 只保留限制的最小处置规则：

- 已确定适用但暂时缺少必要环境、网络、数据或人工输入时，Method 的 Disposition 保持 `required` 并保留完整 Method Detail，Method Result 保持 `pending`，必要事实进入阻塞 Open Item；
- 限制不能被解释为 `n/a`；
- 确认只能在正式 Release Target 执行且当前发版需要继续时，该 Method 在当前 VFY Revision 使用 `waived`、保留完整 Method Detail 并关联有效 Exception，Exception 必须登记准确的 RLS 下游义务；
- Exception 只授权其明确范围和下游义务，Target 不能记为 `pass`；
- 实际发版、流量、停止或恢复机制由 RLS 或项目既有交付机制处理，不在 VFY 展开。

### 失败检查点早停 Failure Checkpoint Early Stop

VFY 已取得足以触发返工的失败事实时，不能因为其他环境或人工 Method 尚不可执行而阻断 Return。当前 Revision 只有同时满足以下条件，才允许按失败检查点早停：

- 至少一个必要 Method 的 Method Result 对当前准确 Subject 得出 `fail`，并由充分、不可变 Evidence 支持；
- 受影响 Target 和维度按既有失败优先级得出 `fail`；每个需要返工的失败都有准确 Return Phase、IMP Lineage（适用时）、Subject、Observed Gap 和 Required Outcome；
- 任何尚未取得的事实都不会改变该失败事实或 Return 归因，只会影响其余覆盖；若未决事实可能推翻失败或改变返回 Phase，不得早停；
- 其他未执行 `required` Method 的 Method Result 保持 `pending` 并逐项引用导致早停的 fail Method 与 Return；Target 和固定 Conclusion 继续按既有失败优先规则聚合，聚合后仍为 `pending` 的项同样引用该 fail Method 与 Return；Method Disposition 不得改写为 `pending`、`n/a` 或 `waived`；
- 所有已有 Method Result、Evidence、Return 和未证明边界均准确完整，且当前 Revision 不产生任何 RLS 准入结论。

失败检查点早停不是新的 Status、Disposition 或 Conclusion。它只允许冻结一份可信的失败与返工记录；产品仍未通过。后续 VFY Revision 必须依据准确的当前 Scope 重新评估全部 `pending` Method Result、Target 和固定 Conclusion：仍适用的义务重新建立并执行，只有权威范围改变时才可引用准确的新 Scope Source 或 Item 关闭不再适用的义务。

## 方法结果

```markdown
| Method ID | Result | 实际结果 Actual Result | 依据引用 Basis References | Return References |
|---|---|---|---|---|
| VFM-001 | pending | | None | None |
```

规则：

- 每个 VFY Method ID 恰好一行，不增加 Execution ID 或 Attempt 状态；
- `Return References` 使用 Core Reference Set；一个 Method 同时确认多个权威 Phase 或多个 IMP Lineage 的缺口时，必须引用拆分后的全部 Return；
- `pass` 和 `fail` 必须记录已观察事实并引用 Evidence；
- `n/a` 必须引用权威依据，`waived` 必须引用有效 Exception；
- `embedded` 行保存的是 VFY 对已有 Evidence 的复核结果，不自动复制上游结论；
- Method Subject、Contract、环境或必要数据变化后，旧结果不能沿用；
- 当前 Revision 未冻结时可以在重执行后更新当前行，具有诊断价值的历史输出保存在 Evidence；Revision 冻结或 Subject 变化后创建新 VFY Revision；
- 结果内包含可独立判定且相互不同的子结果时，应在执行前拆分 Method；未拆分的必要子项任一失败，Method 为 `fail`。
- 失败检查点早停时，尚未执行的 `required` Method 只在 Method Result 写 `pending`，`Actual Result` 必须说明因哪个已确认 fail / Return 停止，并在 `Return References` 引用对应 Return；这不表示该 Method 已执行或不再适用。

## Conclusion Aggregation

同一 Target 关联多个 Method 时按以下顺序取第一个满足的结论：

| 顺序 | 条件 | Target Conclusion |
|---:|---|---|
| 1 | 任一必要 Method Result 为 `fail` | `fail` |
| 2 | 不存在 fail，但任一必要 Method Result 为 `pending` | `pending` |
| 3 | 不存在 fail 或 pending，但必要证明被 `waived` | `waived` |
| 4 | 至少一个必要 Method Result 为 `pass`，其他 Method Result 仅为 `pass` 或 `n/a` | `pass` |
| 5 | 全部 Method Result 均为具有权威依据的 `n/a` | `n/a` |

如果被豁免的方法并非必要，应删除该方法或根据事实改为 `n/a`；必要方法被豁免时 Target 不能标记为 `pass`。

## VFY 结论

VFY 使用两个固定结论：

```markdown
| ID | Dimension | Conclusion | Target References | Basis References | Exception References |
|---|---|---|---|---|---|
| CON-VER | verification | pending | | | None |
| CON-VAL | validation | pending | | | None |
```

- `CON-VER` 聚合 `verification` Target，并对 `both` Target 只使用其 `verification` 或 `both` Method 形成的维度投影；
- `CON-VAL` 聚合 `validation` Target，并对 `both` Target 只使用其 `validation` 或 `both` Method 形成的维度投影；
- 维度投影与两个固定结论都使用 Target Conclusion 的相同固定顺序；Target Conclusion 仍聚合该 Target 的全部必要 Method，任一维度失败时 `both` Target 的整体结论为 `fail`；
- 某个维度没有适用 Target 时，只有 Target Set 推导能够证明该维度客观不适用，才能以 Scope Source 为 Basis 写 `n/a`；否则保持 `pending` 并返回 REQ 或 DSN；
- `both` Target 只有两个维度投影都为 `pass` 时才可以支持完整 `pass`；CON-VER 与 CON-VAL 的 Basis References 必须分别引用本维度实际 Method 和 Evidence；
- 不增加 Overall Conclusion；RLS 根据两个固定结论、Exception 和发版条件作出自身判断；
- 完整引用分别为 `<VFY-ID>@<Revision>#CON-VER` 和 `<VFY-ID>@<Revision>#CON-VAL`。

产品结论与 Artifact Status 必须分离：准确、完整地得出产品 `fail` 的 VFY Artifact 可以通过自身 Gate 并冻结。VFY Artifact `ready` 只表示验证结果可信且可供返工或下游判断，不表示产品通过或允许交付。

## 失败与返回

```markdown
| ID | Return Phase | IMP Binding Reference | Target References | Method References | Subject References | 已观察缺口 Observed Gap | 必须达到的结果 Required Outcome | Evidence References |
|---|---|---|---|---|---|---|---|---|
| None | N/A | N/A | None | None | None | No upstream return required | N/A | None |
```

规则：

- 实际 Return ID 使用 `RET-001` 顺序编号，在当前 Artifact 内稳定且不得复用；
- `Return Phase` 只允许 `REQ`、`DSN`、`PLN` 或 `IMP`；VFY 自身未完成的执行留在当前 Revision 修正，不生成 Return；
- `Return Phase=IMP` 时 `IMP Binding Reference` 必须填写产生待修正 Result 的当前准确 Binding；其他 Return Phase 固定写 `N/A`；
- Requirement、业务语义、AC 或 Intended Use 问题返回 REQ；Design、接口、数据、状态或质量约束问题返回 DSN；Work Item、Scope、依赖或顺序问题返回 PLN；已确认边界内的产品实现问题返回 IMP；
- `Observed Gap` 只记录已确认事实，`Required Outcome` 描述必须恢复的结果，不越权指定未确认实现方案；
- 一个 Return 只指向一个权威 Phase；需要不同 Phase 修正时拆分；
- 一个 IMP Return 必须解析到一个且仅一个 Binding Lineage；涉及多个 Binding 时按 Lineage 拆分，无法确定修改归属或需要重新协调时返回 PLN；
- 每个需要上游修正后才能继续的失败必须引用 Return；当前 Scope 不再继续时不创建伪 Return；没有 RLS Exception 明确接受失败 Target、未解决义务和对应风险时，RLS 不能开始；
- 失败检查点早停形成的 Return 只有在当前 VFY Revision 按本节规则冻结后，才可被上游作为返工输入；当前 Revision 的其他 `pending` 义务不能被解释为已验证或已豁免；
- 完整 Return Reference 为 `<VFY-ID>@<Revision>#RET-ID`。冻结后 Return 不更新；
- 上游新 Revision 引用 Return 只表示已接收处理；IMP 的新 `completed` Claim 只表示已形成候选修正结果，二者都不能单独把 Return 判为 resolved；
- Return 只有在后续冻结 VFY Revision 将其所属冻结 Revision 作为 Control Input、在 Method `Obligation References` 中引用该 Return、采用修正后的当前 Subject，并以 Method Result、Target Conclusion 和 Evidence 证明 `Required Outcome` 后才算 resolved；权威范围改变使义务消失时必须引用准确的新 Scope Source 或 Item，不能删除历史 Return；
- `Return Phase=IMP` 的 Return 可以作为 IMP `Rework References`，但其 `IMP Binding Reference`、Subject References 和当前 Claim 必须属于同一 Binding Lineage；Binding Revision 已更新时同时携带新的准确 Binding。

产品修正类 RLS Issue Reference 使用 `<RLS-ID>@<Revision>#<RLI-ID|RCF-ID>`，Follow-up Disposition 为 `return_req`、`return_dsn` 或 `return_imp`。后续 VFY 必须把所属冻结 RLS Revision 作为 Control Input，在 Method `Obligation References` 中引用该 Issue，并以当前 Subject、Method Result、Target Conclusion 和 Evidence 证明对应产品缺口已经消除；仅完成上游修正或重新执行 RLS 都不等于解决。`return_imp` 还必须唯一绑定一个准确 IMP Lineage；其他 RLS Follow-up 由其指定 Phase 与后续 RLS 闭合，不进入本条产品验证规则。

## Open Items

VFY 直接使用 Core Open Items Contract。尚未提供的必要环境、数据、人工判断或外部事实进入阻塞 Open Item；VFY 自身尚未运行的方法只由 Method Result 与 Gate `pending` 表达，不创建伪输入缺口。

失败检查点早停后，某项外部输入若已不再是冻结当前失败与 Return 所需的事实，可以按 Core 已注册的失败早停规则把对应 Open Item 标记为 `resolved`。Resolution 必须引用准确 fail Method、Return 和 Evidence，并明确“本 Revision 因返工早停，未取得该输入”；这不表示输入已经提供。后续 VFY 必须按当前 Scope 重新评估，仍需要该输入时重新登记，不能沿用本次 Resolution。若该输入会影响失败有效性或 Return 归因，Open Item 必须保持 `open`，当前 Revision 不得早停冻结。

## Evidence

VFY 直接使用 Core Evidence Contract，并增加以下要求：

- `pass` 与 `fail` Evidence 必须能够解析到实际 Method、Target 和 Subject；
- 运行类 Evidence 必须说明实际环境、必要数据、执行时间和 Subject 对应关系；
- 人工或 Hybrid 评价必须记录评价场景、判定、观察事实和评价范围，不能只写“感觉正常”或“体验不好”；
- Detailed Test Case、日志、截图、录像和报告使用 Supporting Artifact 或不可变外部引用，主表只保留摘要；
- 不保存真实 Secret、不必要的生产数据或超出当前结论所需的敏感内容。

## Lifecycle Applicability

```markdown
| Phase | Disposition | Host | 判断依据 Basis |
|---|---|---|---|
| RLS | pending | N/A | Pending — <OPI-ID> |
```

- RLS Disposition 表示是否存在正式发版或目标状态变化，不表示当前产品已经具备发版资格；产品 Conclusion 为 fail 时不能通过修改 Disposition 掩盖结果；
- 存在只能在 Release Target 执行、且具有明确下游义务的 waived Method 时，当前发版继续则 RLS 必须为 `required` 并承接对应 Exception；没有实际发版时不能为了保存检查结果创建伪 RLS；
- `pending` 只用于适用性事实不足并引用阻塞 Open Item；结论失败本身不把 Phase Applicability 改为 pending；
- RLS 的输入准入、实际发版和目标确认 Contract 由 RLS Phase Spec 定义。

## AI 与人工协作 AI and Human Collaboration

本节是 Phase Spec 的执行建议，不进入 VFY Artifact 模板，不作为 AI 使用率、人员配置或 Gate 指标。

| 工作 Activity | AI 适合做什么 | 人工适合做什么 | 原因 Reason |
|---|---|---|---|
| Target 与方法设计 | 追踪 AC、VFO，生成适用场景与覆盖检查 | 确认高风险业务语义 | AI 擅长完整枚举，人工掌握业务权威 |
| 确定性验证 | 准备环境、运行 Test / Analysis、保存 Evidence | 提供受限权限或特殊环境支持 | 自动执行更稳定、可重复 |
| UI / UX 评价 | 准备场景、截图、差异和可测量检查 | 判断视觉、动效、易用性和品牌感受 | 主观体验需要人的感知和上下文 |
| 产品验收 | 汇总 Requirement 与实际结果 | 判断是否满足真实预期用途 | 最终业务价值需要权威责任人确认 |
| Exception 与返回 | 分析风险、定位权威 Phase、提出候选方向 | 批准风险和确认业务或设计改变 | 风险接受与权威决策不能由执行者代替 |

人工参与 VFY Method 与 Core Final Confirmation 是两种记录：前者是产品评价 Evidence，后者确认当前 Artifact 与 Gate；不得用一次模糊签字同时替代两者。主观产品评价没有真实人工 Method Evidence 时，Final Confirmation 不得使用 `delegated`。

## Gate

VFY 使用 Core Gate Checks，并增加以下 Phase Check：

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| VFY-G-001 | Context、Input、Scope Source、完整 PLN IMP Work Item Set、Current completed Claim、Subject 和当前终端 Result 完整、准确且可解析 | pending | |
| VFY-G-002 | 权威 Target Set 推导完整，不存在遗漏、重复或 VFY 自行新增的目标 | pending | |
| VFY-G-003 | 每个 Method 的 Purpose 与 Target 相容，Target、Subject、上游 VFP / VFM / VPC / VEC、适用 VFY Work Item、Return、类型、Disposition、通过条件、Evidence Requirement 与正式执行前的 Pre-execution 读回 Evidence 映射完整一致 | pending | |
| VFY-G-004 | 所有 Method 已形成准确结果，实际 Subject 与 Contract 一致，Evidence 足以支持对应结果；失败检查点早停时，未执行 required Method 的 Method Result pending、fail 与 Return 映射完整准确，且不存在 pending Method Disposition | pending | |
| VFY-G-005 | Target Conclusion、`both` Target 的两个维度投影、CON-VER 和 CON-VAL 按固定 Purpose 兼容与聚合规则计算；正常最终化不存在 pending Result 或 Conclusion，失败检查点早停只保留已逐项绑定 fail / Return 的 pending Result 或 Conclusion | pending | |
| VFY-G-006 | 已确认问题准确返回权威 Phase；IMP Return 与产品修正类 RLS Issue 已完整承接，`return_imp` 绑定唯一准确 Lineage，接收、处理与解决语义未混用，也未在 VFY 新增 Requirement、Design 或 Plan 决策 | pending | |
| VFY-G-007 | Evidence、Supporting Artifact、Exception、人工评价和 Return References 完整一致 | pending | |
| VFY-G-008 | Lifecycle Applicability 与产品结论一致，未把 VFY Artifact ready 误判为允许交付 | pending | |
```

VFY Gate Checks 都是 Contract Integrity Check，只允许 `pending`、`pass` 或 `fail`。Method 或 Target 的产品结果可以为 `fail`；只要失败事实、Evidence、聚合结论和 Return 准确，对应 VFY Gate Check 仍可以为 `pass`。Gate Check `fail` 表示 VFY Artifact 自身不合规，不表示产品验证失败。

## 最终化顺序

1. 解析完整 Delivery Scope、PLN IMP / VFY Work Item obligation set、Target Set、Subject Set、上游 Method Contract 和未关闭 Exception；
2. Gate 前重新确认全部 Subject 及其依赖链仍是当前有效终端 Result；
3. 完成 Method Contract、Method Result、Target Conclusion、固定 Conclusions 和必要 Return；若采用失败检查点早停，逐项证明早停条件、关闭已不阻塞本 Revision 的 Open Item，把全部未执行 required Method 的 Method Result 保留为 `pending`，并按既有规则聚合 Target 与固定 Conclusion；
4. 按 Core 关闭 Check、Evidence、Exception、Final Confirmation 和 Gate；
5. 只有 VFY Artifact Gate 为 `pass` 或 `pass_with_exception` 时冻结 Revision。

正常最终化存在 Method Result、Target 或固定 Conclusion `pending` 时不能冻结。失败检查点早停是唯一例外：只有本节全部条件满足、所有 Method Disposition 均已决定、VFY-G-004 至 VFY-G-007 均准确关闭且不存在仍会影响失败或 Return 的 Open Item 时，才允许冻结；该 Revision 只能供 Return、返工和审计消费，不能进入 RLS。已完整证明的产品 `fail` 不阻止 VFY Artifact 自身冻结。Final Confirmation 确认的是当前 fail、pending 边界和 Return 准确，不把产品 `fail` 或未验证内容改写为 `pass`。

## 内部编号

| 对象 Item | 格式 Format |
|---|---|
| Input | `VIN-001` |
| VFY Method | `VFM-001` |
| Verification Conclusion | `CON-VER` |
| Validation Conclusion | `CON-VAL` |
| Return | `RET-001` |
| Open Item | `OPI-001` |
| Evidence | `EVD-001` |
| Exception | `EX-001` |
| Gate Check | `VFY-G-001` |
