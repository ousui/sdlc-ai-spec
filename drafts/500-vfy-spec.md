---
title: VFY Phase Spec
status: draft
scope: Verification and Validation Phase 固定模板、执行边界与 Gate
---

# VFY Phase Spec（草稿）

VFY 对准确、不可变的产品结果执行或复核适用方法，证明其是否符合已确认的 Requirement、Design 和预期用途，并形成可供返工或发版判断使用的结论。

VFY 不是独立 QA Phase 或 Test Phase。Test、Inspection、Analysis 和 Demonstration 是方法；QA 仍由各 Phase 的 Check、Evidence、Gate 和 Human Confirmation 贯穿承载。

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
contract: sdlc-ai-spec/artifact/v0.1
phase: VFY
id: VFY-20260824160000-01
revision: 1
status: draft
profile: full
inputs:
  - DSN-20260824120000-01@1
  - IMP-20260824150000-01@1
---
```

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
- v0.1 不在 VFY 内选择上游 Artifact 的部分 Item，也不自行组合多个候选 Result；
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
- `Reference` 使用准确 Artifact 或 Item Reference；同一引用承担多个角色时分别登记；
- `Included Scope` 使用准确 Item Reference、Scope Token 或 `Full Artifact`，不得写“相关内容”；
- 每个当前有效的已变化终端 Implementation Result 必须直接或通过可解析派生关系进入 Subject Set；未变化的继承资源可以只作为 Input 保存；
- VFY 开始和 Gate 前都必须复核 Subject 仍是当前有效终端 Result，不得自动选择最新、其他或旧 Result；
- Subject 无法准确解析、依赖链不连续或存在尚未吸收的更新时，VFY 不能继续形成结论。

## Target Set

Target Set 按以下固定顺序确定：

1. 当前 Scope 存在可解析 VFY Objective Set 时，使用全部 `VFO-ID`；VFO 已承载其关联的 AC、Goal、Design Decision 和 Domain VFY Point，不在 VFY 重复展开为平行 Target；
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
| ID | Purpose | Target References | Subject References | Method Type | Disposition | 依据或原因 Basis Reference or Reason |
|---|---|---|---|---|---|---|
| VFM-001 | verification | | | test | required | |
```

| Method Type | 含义 Meaning |
|---|---|
| `inspection` | 不运行目标，通过静态查看判断符合性 |
| `analysis` | 根据计算、模型、数据或工具结果推导结论 |
| `demonstration` | 操作或展示产品以确认可观察能力或预期用途 |
| `test` | 在明确输入和条件下执行，并与预期结果及通过条件比较 |

规则：

- Method ID 使用 `VFM-001` 顺序编号，在当前 VFY Artifact 内稳定且不得复用；
- 每个适用 Target 至少被一个 Method 覆盖，每个 Method 至少引用一个 Target 和一个准确 Subject；
- 一个 Method 只有在同一 Procedure、Pass Criteria 和结果能够同时支持多个 Target 时才可以引用多个 Target；结果可能独立变化时必须拆分；
- `manual`、`automated` 或 `hybrid` 是 Execution Mode，不是 Method Type；
- Unit、Component、Interface、Integration、System 和 End-to-End 是 Test Level，不是 Method Type；
- Functional、Regression、Performance、Security、Recovery、Compatibility 和 Accessibility 是目标或范围描述，不是并列 Method Type；
- Review 通常归为 Inspection；静态计算或扫描通常归为 Analysis；人工操作按是否具有明确输入、预期和通过条件归为 Demonstration 或 Test；
- 不要求每个 Artifact 使用全部四类方法，不设置固定 Test 数量、覆盖率或自动化比例。

### required Method Detail

每个 `required` Method 使用固定详情块：

```markdown
### VFM-001 <Method Title>

- Contract References:
- Method Detail:
- Procedure or Basis:
- Pass Criteria or References:
- Evidence Requirement:
```

- `Contract References` 引用上游 VFY Objective、Method、Pass Criteria 和 Evidence Contract；没有独立 DSN Contract 时引用准确 AC 或 Goal；
- `Method Detail` 记录适用的 Test Level、Objective、Execution Mode、环境或范围，不增加顶层枚举；
- `Procedure or Basis` 必须足以重复执行或复核，不绑定无必要的具体工具；
- `Pass Criteria or References` 必须明确可判定，不得只写“正常”或“符合预期”；
- `Evidence Requirement` 说明支持 `pass` 或 `fail` 所需的最小 Evidence。

`embedded` 不复制 Host 内容；索引的 Basis 必须引用准确 Host Method、当前 Subject 和可复核 Evidence。`n/a` 与 `waived` 不生成空详情块，其原因或 Exception 由索引承载。`pending` 不能通过 Gate。

### IMP Test Boundary

- Test 资产的实现和修改属于 IMP；
- 为开发反馈和 IMP 完成检查而执行的 Unit Test、Build、Static Check 或局部运行检查属于 Implementation Check；
- VFY 只在这些结果支持当前 Target 且准确对应最终 Subject 时，将其作为 `embedded` Method 复核；
- Subject 变化、Evidence 无法证明对应关系、上游要求独立复核或风险需要重执行时，VFY 使用 `required` Method；
- IMP Test 通过只表示实现具备进入 VFY 的条件，不表示 VFY 通过或允许 RLS。

### Execution Limitations

VFY 只保留限制的最小处置规则：

- 暂时缺少必要环境、网络、数据或人工输入时，Method 保持 `pending`，必要事实进入阻塞 Open Item；
- 限制不能被解释为 `n/a`；
- 确认只能在正式 Release Target 执行且当前发版需要继续时，该 Method 在当前 VFY Revision 使用 `waived` 并关联有效 Exception，Exception 必须登记准确的 RLS 下游义务；
- Exception 只授权其明确范围和下游义务，Target 不能记为 `pass`；
- 实际发版、流量、停止或恢复机制由 RLS 或项目扩展定义，不在 VFY 展开。

## 方法结果

```markdown
| Method ID | Result | 实际结果 Actual Result | 依据引用 Basis References | Return Reference |
|---|---|---|---|---|
| VFM-001 | pending | | None | None |
```

规则：

- 每个 VFY Method ID 恰好一行，不增加 Execution ID 或 Attempt 状态；
- `pass` 和 `fail` 必须记录已观察事实并引用 Evidence；
- `n/a` 必须引用权威依据，`waived` 必须引用有效 Exception；
- `embedded` 行保存的是 VFY 对已有 Evidence 的复核结果，不自动复制上游结论；
- Method Subject、Contract、环境或必要数据变化后，旧结果不能沿用；
- 当前 Revision 未冻结时可以在重执行后更新当前行，具有诊断价值的历史输出保存在 Evidence；Revision 冻结或 Subject 变化后创建新 VFY Revision；
- 结果内包含可独立判定且相互不同的子结果时，应在执行前拆分 Method；未拆分的必要子项任一失败，Method 为 `fail`。

## Conclusion Aggregation

同一 Target 关联多个 Method 时按以下顺序取第一个满足的结论：

| 顺序 | 条件 | Target Conclusion |
|---:|---|---|
| 1 | 任一必要 Method 为 `fail` | `fail` |
| 2 | 不存在 fail，但任一必要 Method 为 `pending` | `pending` |
| 3 | 不存在 fail 或 pending，但必要证明被 `waived` | `waived` |
| 4 | 至少一个必要 Method 为 pass，其他仅为 pass 或 n/a | `pass` |
| 5 | 全部 Method 均具有权威 n/a 依据 | `n/a` |

如果被豁免的方法并非必要，应删除该方法或根据事实改为 `n/a`；必要方法被豁免时 Target 不能标记为 `pass`。

## VFY 结论

VFY 使用两个固定结论：

```markdown
| ID | Dimension | Conclusion | Target References | Basis References | Exception References |
|---|---|---|---|---|---|
| CON-VER | verification | pending | | | None |
| CON-VAL | validation | pending | | | None |
```

- `CON-VER` 聚合 `verification` 和 `both` Target；
- `CON-VAL` 聚合 `validation` 和 `both` Target；
- 两个维度分别使用 Target Conclusion 的相同固定顺序；
- 某个维度没有适用 Target 时，只有 Target Set 推导能够证明该维度客观不适用，才能以 Scope Source 为 Basis 写 `n/a`；否则保持 `pending` 并返回 REQ 或 DSN；
- `both` Target 在两个维度都成立时才可以支持完整 `pass`；
- 不增加 Overall Conclusion；RLS 根据两个固定结论、Exception 和发版条件作出自身判断；
- 完整引用分别为 `<VFY-ID>@<Revision>#CON-VER` 和 `<VFY-ID>@<Revision>#CON-VAL`。

产品结论与 Artifact Status 必须分离：准确、完整地得出产品 `fail` 的 VFY Artifact 可以通过自身 Gate 并冻结。VFY Artifact `ready` 只表示验证结果可信且可供返工或下游判断，不表示产品通过或允许交付。

## 失败与返回

```markdown
| ID | Return Phase | Target References | Method References | Subject References | 已观察缺口 Observed Gap | 必须达到的结果 Required Outcome | Evidence References |
|---|---|---|---|---|---|---|---|
| None | N/A | None | None | None | No upstream return required | N/A | None |
```

规则：

- 实际 Return ID 使用 `RET-001` 顺序编号，在当前 Artifact 内稳定且不得复用；
- `Return Phase` 只允许 `REQ`、`DSN`、`PLN` 或 `IMP`；VFY 自身未完成的执行留在当前 Revision 修正，不生成 Return；
- Requirement、业务语义、AC 或 Intended Use 问题返回 REQ；Design、接口、数据、状态或质量约束问题返回 DSN；Work Item、Scope、依赖或顺序问题返回 PLN；已确认边界内的产品实现问题返回 IMP；
- `Observed Gap` 只记录已确认事实，`Required Outcome` 描述必须恢复的结果，不越权指定未确认实现方案；
- 一个 Return 只指向一个权威 Phase；需要不同 Phase 修正时拆分；
- 每个需要上游修正后才能继续的失败必须引用 Return；当前 Scope 不再继续时不创建伪 Return；没有 RLS Exception 明确接受失败 Target、未解决义务和对应风险时，RLS 不能开始；
- 完整 Return Reference 为 `<VFY-ID>@<Revision>#RET-ID`。冻结后 Return 不更新状态，后续 Artifact 通过准确引用和新 Revision 证明解决；
- `Return Phase=IMP` 的 Return 可以作为 IMP `Rework References`；其 Subject References 必须包含该 Binding Lineage 的 Result，或包含以该 Result 为传递输入的当前终端 Result，不能只靠标题、Target 摘要或缺陷文字猜测归属。

## Open Items

VFY 直接使用 Core Open Items Contract。尚未提供的必要环境、数据、人工判断或外部事实进入阻塞 Open Item；VFY 自身尚未运行的方法只由 Method Result 与 Gate `pending` 表达，不创建伪输入缺口。

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
| RLS | pending | N/A | Pending — <OI-ID> |
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

人工参与 VFY Method 与 Core Human Confirmation 是两种记录：前者是产品评价 Evidence，后者确认当前 Artifact、Gate 和未关闭风险；不得用一次模糊签字同时替代两者。

## Gate

VFY 使用 Core Gate Checks，并增加以下 Phase Check：

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| VFY-G-001 | Input、Scope Source、Subject 和当前终端 Result 完整、准确且可解析 | pending | |
| VFY-G-002 | 权威 Target Set 推导完整，不存在遗漏、重复或 VFY 自行新增的目标 | pending | |
| VFY-G-003 | 每个 Method 的 Purpose、Target、Subject、类型、Disposition、通过条件和 Evidence Requirement 完整一致 | pending | |
| VFY-G-004 | 所有 Method 已形成准确结果，实际 Subject 与 Contract 一致，Evidence 足以支持对应结果 | pending | |
| VFY-G-005 | Target Conclusion、CON-VER 和 CON-VAL 按固定规则正确聚合且不存在 pending | pending | |
| VFY-G-006 | 已确认问题准确返回权威 Phase；未把 VFY 执行问题误判为上游缺陷，也未在 VFY 新增 Requirement、Design 或 Plan 决策 | pending | |
| VFY-G-007 | Evidence、Supporting Artifact、Exception、人工评价和 Return Reference 完整一致 | pending | |
| VFY-G-008 | Lifecycle Applicability 与产品结论一致，未把 VFY Artifact ready 误判为允许交付 | pending | |
```

VFY Gate Checks 都是 Contract Integrity Check，只允许 `pending`、`pass` 或 `fail`。Method 或 Target 的产品结果可以为 `fail`；只要失败事实、Evidence、聚合结论和 Return 准确，对应 VFY Gate Check 仍可以为 `pass`。Gate Check `fail` 表示 VFY Artifact 自身不合规，不表示产品验证失败。

## 最终化顺序

1. 解析完整 Delivery Scope、Target Set、Subject Set、上游 Method Contract 和未关闭 Exception；
2. Gate 前重新确认全部 Subject 及其依赖链仍是当前有效终端 Result；
3. 完成 Method Contract、Method Result、Target Conclusion、固定 Conclusions 和必要 Return；
4. 按 Core 关闭 Check、Evidence、Exception、Human Confirmation 和 Gate；
5. 只有 VFY Artifact Gate 为 `pass` 或 `pass_with_exception` 时冻结 Revision。

存在 Method 或 Target `pending` 时不能冻结；已完整证明的产品 `fail` 不阻止 VFY Artifact 自身冻结。Human Confirmation 确认的是当前 VFY Artifact 及其结论准确，不把产品 `fail` 改写为 `pass`。

## 内部编号

| 对象 Item | 格式 Format |
|---|---|
| Input | `VIN-001` |
| VFY Method | `VFM-001` |
| Verification Conclusion | `CON-VER` |
| Validation Conclusion | `CON-VAL` |
| Return | `RET-001` |
| Open Item | `OI-001` |
| Evidence | `EVD-001` |
| Exception | `EX-001` |
| Gate Check | `VFY-G-001` |

## 当前未定义

- VFY 与外部测试平台的自动 Evidence 适配；
- Project Extension 注册项目专属环境、数据、命令和工具适配的实现方式；
- VFY 自动化入口和执行工具。
