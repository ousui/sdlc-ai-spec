---
title: Release Phase Spec
status: draft
version: "1.1"
scope: 最小 RLS 发版合约、上线后确认、结论与 Gate
---

# Release Phase Spec

RLS 将已经完成 VFY 的准确结果发到一个约定目标，记录实际执行和目标侧状态，并形成一份可追溯的上线报告。

RLS 只回答四个问题：发什么、发到哪里；有哪些变化和必要操作；实际执行结果怎样；上线后必要确认是否通过。长期运行不属于本 Phase，也不建立独立运行阶段。

## Phase 目标与边界

RLS 负责：

- 绑定一个完整 Scope、准确 Result、冻结 VFY 和一个 Release Target；
- 汇总本次实际变化、注意事项及必要的应用、SQL、配置、数据或人工操作；
- 记录人工、自动化流水线、交付平台、数据管理或运维执行方返回的实际结果；
- 确认目标版本、必要状态和基本可用性，形成发版结论。

RLS 不负责：

- 新增或改变 Requirement、Design Decision、Delivery Scope 或 Work Item；
- 修改或重新构建代码、SQL、配置、测试资产及其他 Implementation Result；
- 临时缩减完整 Scope，或替换 VFY 已判断的 Result；
- 重新执行完整 VFY；
- 规定组织审批、发布窗口、灰度、流量控制或特定工具流程；
- 管理长期监控、告警、值守、故障处置或日常 Runbook；
- 顺手处理当前 Scope 之外的目标环境问题。

需要改变产品结果时返回相应上游，并在形成新 Result 后重新进入 VFY；只需重试发版、补权限、修复环境或等待外部执行时留在 RLS。

## Applicability

| Disposition | RLS 条件 |
|---|---|
| `required` | 已验证结果将进入正式环境、发布渠道或其他约定的可用目标，产生实际目标状态变化 |
| `n/a` | 当前 Scope 不存在正式发版或目标状态变化 |
| `waived` | 原本存在发版义务，但在任何发版操作或目标效果发生前，经有效 Exception 授权不执行 |
| `pending` | Release Target、发版意图或必要范围事实尚未确定 |
| `embedded` | 不支持；外部平台记录只能作为 Evidence，不能替代 RLS Artifact |

一旦发版操作开始或目标侧可能已经产生效果，RLS 必须为 `required`，不得再改为 `n/a` 或 `waived`。没有 RLI / RCF `fail`、目标尚未产生效果且已明确主动停止时，以 `cancelled` Release Conclusion 结束当前 RLS；发版前已经发生明确失败时仍为 `failed`。

仅用于 VFY 的开发、测试或预发布环境部署不属于 RLS；项目明确把该目标作为正式可用目标时除外。

## 输入与输出

| 类型 Type | 内容 Content |
|---|---|
| Input | 一个完整 VFY Scope、冻结 VFY Revision、VFY 判断的准确 Result、Release Target、Target Baseline、适用 RLS Work Item、项目 Spec 和未关闭 Exception |
| Output | 一份同时记录发版清单、实际执行、上线后确认、结论和 Evidence 的 RLS Artifact；冻结后即为最终上线报告 |

RLS Front Matter `inputs` 必须包含冻结 VFY Revision，以及正文直接引用的其他上游 Artifact Revision。外部环境、流水线、工单和平台不是 Artifact Input，其结果作为 Evidence 或 Supporting Artifact 保存。

## Front Matter

RLS 使用 Core Artifact Front Matter：

```yaml
---
contract: sdlc-ai-spec/artifact/v1
phase: RLS
id: RLS-20260825160000-01
revision: 1
status: draft
context: CTX-20260828143025-01@1
profile: full
inputs:
  - PLN-20260825130000-01@1
  - IMP-20260825140000-01@1
  - VFY-20260825150000-01@1
---
```

## 输入就绪

一个 RLS Artifact 只绑定一个完整 VFY Scope 和一个明确 Release Target：

- `Scope Reference` 必须与 VFY 的完整 Scope 一致；
- `Result References` 必须与 VFY 最终 Subject Set 一致，不得临时换包、重建或选择部分结果；
- Release Target 必须使用项目内唯一且可解析的名称；相互独立的正式目标分别形成 RLS Artifact；
- Target Baseline 必须是发版前可复核状态；首次发版写 `N/A — Initial Release`；
- PLN 为 `required` 时，当前 Target 的全部 RLS Work Item 必须进入 Release Contract；归属不清时返回 PLN；
- VFY Revision 必须已冻结，且 Verification、Validation、Return 和 Exception 可以准确解析；
- VFY 中任一 Method Disposition、Method Result、Target、`CON-VER` 或 `CON-VAL` 仍为 `pending` 时不得开始 RLS，Exception 也不能覆盖该限制；按失败检查点早停冻结的 VFY 只可供 Return、返工和审计消费；
- VFY 产品结论为 `fail` 或存在未解决 Return 时默认停止；只有有效 Exception 明确接受风险和范围后才可继续，VFY 原结论不得改写。
- VFY 中每个明确要求在 Release Target 执行的 waived Method、Target 和 Exception，必须映射到至少一个 RCF；发版前必须明确对应 Confirmation、Expected、执行方及 Evidence 获取方式，并确认所需权限、数据来源与方法的获取路径可用，缺少映射或存在未解决的执行前提时不得开始发版。

必要输入不足时返回对应权威 Phase；RLS 不补造业务、设计、计划、产品结果或验证结论。

## 固定模板

```markdown
# <Release Title>

## 摘要 Summary

## 范围 Scope

## 发版合约 Release Contract

## 发版项 Release Items

## 上线后确认 Post-release Confirmation

## 发版结论 Release Conclusion

## 待确认项 Open Items

## 证据 Evidence

## 支撑产物清单 Supporting Artifact Manifest

## 豁免 Exceptions

## 门禁 Gate
```

RLS 是终点 Phase，不包含 `Lifecycle Applicability`。所有固定章节必须保留；外部日志、截图、报告和操作手册作为 Evidence、Supporting Artifact 或不可变引用保存，不在正文重复展开。

## Release Contract

```markdown
| Field | Value |
|---|---|
| Release Reference | |
| Scope Reference | |
| Result References | |
| VFY Reference and Conclusions | |
| RLS Work Item References | None |
| Release Target | |
| Target Baseline | |
| Approval or Trigger Reference | None — no separate approval defined |
```

规则：

- Release Reference 是当前版本、批次或等价稳定标识，不代替 RLS Artifact ID；
- Scope、Result、Work Item 和 VFY Conclusion 使用 Core Reference Set 语法；
- VFY Reference 必须同时保存准确 Revision、Verification Conclusion 和 Validation Conclusion，不能只引用 VFY Artifact Status；
- 没有独立 PLN 时 `RLS Work Item References` 写 `None`；
- `Approval or Trigger Reference` 只记录项目或工具已有的审批、触发或执行依据，不在 RLS 新建审批流程；没有独立审批时使用固定 `None — no separate approval defined`；
- `Approval or Trigger Reference=None` 只表示没有独立审批记录，不授予实际执行权限；任何外部副作用仍必须符合项目与执行工具的授权规则；
- Release Contract 任一字段改变后，旧执行结果、确认、Gate 和 Final Confirmation 不得沿用。

## Release Items

```markdown
| ID | 变更或操作 Change or Action | 来源引用 Source References | 前置条件或注意事项 Prerequisite or Note | 执行方 Executor | 结果 Result | Follow-up Disposition | 证据引用 Evidence References |
|---|---|---|---|---|---|---|---|
| RLI-001 | | | | | pending | none | None |
```

`Result` 只使用以下固定值：

| Value | 含义 Meaning |
|---|---|
| `pending` | 本项尚未结束，或结束状态尚未明确 |
| `success` | 本项预期动作和结果已完整达成 |
| `partial` | 已产生部分目标效果，但本项未完整达成 |
| `fail` | 本项发生明确失败 |
| `cancelled` | 本项在产生目标效果前被明确主动终止 |
| `waived` | 本项经有效 Exception 授权不执行 |

- 同一张表同时记录相较上个目标基线的实际变化、必要操作、上线前注意事项、实际执行方和执行结果；
- 应用、制品、SQL、配置、数据和人工操作仅在实际适用时创建行，不生成空分类；
- 表格按预期执行顺序排列；需要依赖或前置条件时写入 `Prerequisite or Note`，不复制流水线内部步骤；
- 一个发版项只覆盖一个可独立判断的结果；同一外部执行记录可以作为整项 Evidence；
- `Executor` 按 Core 填写一个稳定执行身份 token；多人、团队或流水线共同执行时使用本次统一执行或运行 ID；
- `success`、`partial`、`fail` 和 `cancelled` 必须引用实际结果 Evidence，`waived` 必须引用有效 Exception；
- `Follow-up Disposition` 使用下文固定枚举；同一行只能选择一个去向；
- 每个适用 RLS Work Item 至少被一个 RLI 或 RCF 的 `Source References` 覆盖，并由相关行共同满足 Completion Criteria 和 Expected Evidence。

## Post-release Confirmation

```markdown
| ID | 来源引用 Source References | 确认项 Confirmation | 预期 Expected | 执行方 Executor | Evidence 要求及获取方式 Evidence Requirement and Acquisition | 实际 Observed | 结果 Result | Follow-up Disposition | 证据引用 Evidence References |
|---|---|---|---|---|---|---|---|---|---|
| RCF-001 | | | | | | | pending | none | None |
```

`Result` 只使用 `pending`、`pass`、`fail`、`not_run`、`n/a` 或 `waived`。`not_run` 表示本次发版在目标产生效果前已经失败或取消，该确认项未执行且不再等待；它不是通过结论。

上线后确认只覆盖：

- 实际目标版本或制品；
- 适用的配置、SQL、数据状态；
- 基本可用性；
- 上游明确要求在正式目标完成的检查。

规则：

- 每项确认必须在发版前确定可判定的 Expected、Executor 及 Evidence Requirement and Acquisition；实际执行后填写 Observed，`pass`、`fail` 必须引用目标侧 Evidence；
- `Executor` 按 Core 填写一个稳定执行身份 token，并与实际目标侧 Evidence 的执行记录一致；
- 流水线或平台执行成功只证明操作完成，不能单独证明目标状态正确；
- `n/a` 只用于客观不适用并写明原因，未执行不能写为 `n/a`；`waived` 必须引用有效 Exception；
- `not_run` 只允许在 Evidence 已证明本次发版失败或取消且未产生目标效果时使用，Observed 必须说明阻断原因并关联实际结果 Evidence；它不创建重复 Follow-up，问题由导致失败或取消的 RLI 路由；
- 已产生或可能产生目标效果时，至少保留一项实际目标侧 `pass` 或 `fail`；Evidence 已证明未产生目标效果的 `failed` 或 `cancelled` 不新增伪 RCF，发版前已登记的确认项按上一条记为 `not_run`；
- VFY 带入的每项 Release Target 下游义务必须由至少一个 RCF 的 `Source References` 同时引用准确 Method、Target 和 Exception；
- 上述映射 RCF 不得使用 `n/a`；只有本次发版在目标效果前失败或取消时可以使用 `not_run`。Scope 或产品义务已经改变时返回权威上游，不得在 RLS 静默删除义务；
- 对应 RCF 的 `Confirmation`、`Expected` 和所需 Evidence 必须完整承接 VFY Method 的 Procedure or Basis、Pass Criteria or References 与 Evidence Requirement，不得收窄、替换或降低原判定口径；
- 每个承接的 VFY Exception 按其全部映射 RCF 只聚合一次终态：存在 `pending` 时，当前 RLS 中对应 `carried` 行保持未关闭且 RLS 不得最终化；存在 `not_run` 且不存在 `pending` 时，该行保持 `carried`，允许准确的 `failed` 或 `cancelled` RLS 以未关闭 Exception 冻结；不存在 `pending/not_run` 且至少一个 RCF 再次 `waived` 时，不得沿用旧授权，必须以当前 RLS 的一个有效 `active` Exception 覆盖该来源 Exception 的全部再次豁免义务，并将 `carried` 行标记为 `superseded`；不存在 `pending/not_run` 且全部 RCF 均为实际 `pass` 或 `fail` 时，该 `carried` 行标记为 `resolved`，Resolution References 必须包含全部映射 RCF 和支持其实际结果的 Evidence。冻结 VFY 中的原记录始终不修改；
- `Follow-up Disposition` 使用下文固定枚举；同一行只能选择一个去向；
- RLS 不重新执行完整 VFY；发现产品问题时返回上游形成新 Result，再重新进入 VFY。

## Follow-up Disposition

RLS 不新增 Return 表。每个 RLI 和 RCF 直接使用以下唯一枚举：

| Value | 含义 Meaning |
|---|---|
| `none` | 不需要后续处理，或当前行尚未形成需要路由的问题 |
| `retry_rls` | 只需重试发版、补权限、修环境或等待外部执行 |
| `return_req` | Requirement、业务目标或 Acceptance Criteria 必须改变 |
| `return_dsn` | Design Decision、接口、数据、状态或质量设计必须改变 |
| `return_pln` | Delivery Scope、Work Item、顺序或协调必须改变，或产品修正无法唯一归属一个 IMP Lineage |
| `return_imp` | 已确认边界内的产品 Result 必须改变，且可唯一解析到一个 IMP Binding Lineage；修正后必须重新进入 VFY |

`pending`、`success`、`pass`、`not_run`、`n/a` 和最终接受的 `waived` 行使用 `none`。`not_run` 的原因与后续去向由导致其未执行的 RLI 记录，不创建重复 Issue Reference。`partial`、`fail` 或 `cancelled` 行只有在确实不需要重试或改变上游，且 Release Conclusion 已说明依据时才能使用 `none`；其余必须选择与事实匹配的唯一去向。Follow-up 只描述下一步，不改变当前行的实际 Result。

完整的 `RLS Issue Reference` 使用 `<RLS-ID>@<Revision>#<RLI-ID|RCF-ID>`。只有冻结 RLS 中 Follow-up Disposition 为相应 `return_*` 的行才能由对应上游 Phase 接收；`retry_rls` 留在 RLS，`none` 不触发返工。后续 Artifact 将 Issue Reference 作为 Control Input 并记录处理结果；仅接收或重试不等于问题已经解决。RLS 不复制问题行，也不建立平行状态。

## Release Conclusion

```markdown
| Conclusion | Basis References | Remaining Risks or Follow-up | Completed At |
|---|---|---|---|
| pending | None | None | N/A |
```

`Conclusion` 只使用 `pending`、`success`、`partial`、`failed` 或 `cancelled`，按以下顺序取第一个满足的结果：

1. 存在必要 `pending`、发版尚未结束、结束状态尚未明确或其他必要事实尚未确定：`pending`；
2. 任一 RLI 或 RCF 为 `fail`：`failed`；
3. 未产生目标效果且已明确主动停止：`cancelled`；
4. 全部必要 RLI 为 `success` 或有效 `waived`，全部必要 RCF 为 `pass`、客观 `n/a` 或有效 `waived`，至少一个 RCF 为实际 `pass`，且全部 RLS Work Item 已满足：`success`；
5. 前述均未命中且已经产生目标效果：`partial`。

`Basis References` 必须引用支持结论的 RLI、RCF、Evidence 或 Exception。最终结论的 `Completed At` 使用 RFC 3339；`pending` 固定为 `N/A`。未完成事项、剩余风险和后续义务统一写入 `Remaining Risks or Follow-up`。

VFY Conclusion、RLS Conclusion 与 Artifact Status 分别表示产品符合性、目标侧发版结果和记录合规性。准确记录 `failed`、`partial` 或 `cancelled` 的 RLS Artifact 可以通过自身 Gate 并冻结，不能伪装为成功。

## AI 与人工协作 AI and Human Collaboration

本节是 Phase 执行指导，不进入 RLS Artifact 模板，也不作为 Gate 或 AI 使用率指标。

| 工作 Activity | AI 适合做什么 | 人工适合做什么 | 原因 Reason |
|---|---|---|---|
| 发版准备 | 汇总准确范围、结果、SQL、配置、操作和注意事项 | 确认真实目标、权限及受限条件 | AI 擅长结构化，目标事实和权限来自项目 |
| 发版执行 | 执行已授权的自动化操作并采集 Evidence | 提供受限权限或完成必要人工操作 | 执行主体可以不同，结果使用同一 Contract |
| 上线后确认 | 运行确定性检查并整理目标侧事实 | 判断 UI、业务体验或受限环境结果 | 部分结果需要人的感知、权限或业务权威 |
| 最终结论 | 按固定规则聚合结果和剩余风险 | 对 Exception、风险或外部权限作权威决定；否则按 Core 完成 Final Confirmation | 委托确认不授予 action 权限或风险接受权 |

## Gate

RLS 使用 Core Gate Checks，并只增加以下 Phase Check：

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| RLS-G-001 | Context 与 Release Contract 准确绑定冻结 VFY、结果、目标和目标基线；VFY 不含 pending Method Disposition、Method Result、Target 或固定 Conclusion，且正式 Target effect 前的 Pre-execution 读回 Evidence 完整，不存在范围或结果漂移 | pending | |
| RLS-G-002 | 所有适用 Release Item、RLS Work Item、VFY Target 下游义务和 Post-release Confirmation 均已覆盖；RCF 准入字段完整且未降低原判定口径，结果、Follow-up Disposition、Evidence 与 Exception 状态一致，且不存在必要 pending | pending | |
| RLS-G-003 | Release Conclusion 与实际目标状态一致，未完成事项、RLS Issue Reference 和剩余风险均未隐藏 | pending | |
```

RLS Gate Checks 都是 Contract Integrity Check，只允许 `pending`、`pass` 或 `fail`。Release Conclusion 为 `failed`、`partial` 或 `cancelled` 不自动使 Gate Check 失败；Gate 只判断记录是否准确、完整、可信。

## 最终化

- RLS 的 Pre-execution Checklist 直接使用当前 Revision 的非空 Evaluation Contract Set、Front Matter Context、Release Contract、全部适用 Release Item 的动作、来源、前置条件和执行方，以及全部 Post-release Confirmation 的 Confirmation、Expected、执行方和 Evidence 获取方式；首次 Target effect 前必须按 Core 持久化、读回并保存 Evidence，不新增第二套清单；
- 发版前和执行中，当前 Revision 保持 `draft` 或 `waiting_input`，同一 Markdown 作为发版清单；
- 发版结束、失败或取消后补全实际结果，再按 Core 完成 Gate、Final Confirmation 和 Snapshot 冻结；
- 不生成第二份上线报告；冻结 RLS Artifact 就是最终 Release Record；
- 对相同有效 Input、Release Reference、Scope、Result、Target 和发版义务的实际重试创建新 Revision，并按当前事实重新捕获 Target Baseline 与 Approval or Trigger Reference；只有既有 RLS Artifact 的稳定 ID 命名空间满足 Core Identity Namespace Recovery 的不可修复条件时，才创建新的唯一 RLS Artifact ID。该 Recovery Artifact 使用 Revision 1、`Base Revision=None` 和相同稳定发版身份，保存旧 Artifact 最终失败 Evidence，不继承旧 Gate、Final Confirmation 或 RLS Authority，并重新完成 Pre-execution 读回、实际执行和目标侧确认；Target 已精确匹配时允许记录 no-op，不为制造新结果重写 Target。Scope 或 Result 改变时返回上游，独立 Target 使用独立 RLS Artifact；
- 项目既有交付机制可以增加审批、职责分离、发布窗口、灰度、平台适配和专项合规，但不能删除准确 Result、实际执行和目标侧确认这三项底线。

## 内部编号

| 对象 Item | 格式 Format |
|---|---|
| Release Item | `RLI-001` |
| Post-release Confirmation | `RCF-001` |
| Open Item | `OPI-001` |
| Evidence | `EVD-001` |
| Exception | `EX-001` |
| Gate Check | `RLS-G-001` |
