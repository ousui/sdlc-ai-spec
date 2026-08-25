---
title: Release Phase Spec
status: draft
scope: 最小 RLS 发版合约、目标确认、结论与 Gate
---

# Release Phase Spec（草稿）

RLS 将准确的、已经完成 VFY 的结果发布到约定目标，确认目标侧实际状态，并形成可追溯的发版结论。

RLS 不是上线文档整理活动。真实目标状态和 Release Record 共同构成本 Phase 的结果；只有 Markdown 而没有实际目标状态或明确取消结果，不能视为完成。

## Phase 目标与边界

RLS 负责：

- 绑定一个完整 Scope、准确 Result、Release Target 和 Target Baseline；
- 读取 VFY Conclusion、Return、Exception 和目标环境义务，确认是否可以继续；
- 执行发版操作，或承接外部执行系统、研发、DBA、运维等执行方的实际结果；
- 确认目标版本、配置、数据及适用的基本可用状态；
- 形成 `pending / success / partial / failed / cancelled` 发版结论和剩余事项。

RLS 不负责：

- 新增或改变 Requirement、Design Decision、Delivery Scope 或 Work Item；
- 修改代码、SQL、配置、测试资产或其他 Implementation Result；
- 临时选择完整 Scope 的部分内容，或使用不同于 VFY Subject 的重新构建结果；
- 重新执行完整 VFY；
- 管理长期监控、告警、值守、故障处置或日常 Runbook；
- 强制规定审批、发布窗口、灰度、流量控制或特定发布工具；
- 处理当前 Scope 之外的目标环境问题。

需要改变产品结果时返回 IMP 并重新进入 VFY；需要改变业务、设计或计划时返回对应权威 Phase。

## Applicability

| Disposition | RLS 条件 |
|---|---|
| `required` | 已验证结果将进入正式环境、发布渠道或其他约定的可用目标，产生实际目标状态变化 |
| `n/a` | 当前 Scope 不存在正式发版或目标状态变化 |
| `waived` | 原本存在发版义务，但在任何发版操作或目标效果发生前，经有效 Exception 授权不执行 |
| `pending` | Release Target、发版意图或必要范围事实尚未确定 |
| `embedded` | 不支持；外部流水线、工单或平台记录只能作为 Evidence，不能代替 RLS Artifact |

一旦 Release Action 已开始或目标侧可能已经产生效果，RLS 必须为 `required`，不得再以 `n/a` 或 `waived` 省略 Artifact。已经创建 RLS 后，在产生目标效果前停止使用 `cancelled` Conclusion 表达，不重新解释 Phase Applicability。

仅用于 VFY 的开发、测试或预发布环境部署不属于 RLS；项目将某个渠道明确指定为正式可用目标时除外。

## 输入与输出

| 类型 Type | 内容 Content |
|---|---|
| Input | 一个完整 VFY Scope、准确 VFY Revision 与 Subject Result、Release Target、Target Baseline、适用 PLN Work Item、相关项目 Spec 和未关闭 Exception |
| Output | 目标侧实际状态，以及一份记录发版合约、变化、操作、目标确认、结论和 Evidence 的 RLS Artifact |

RLS Front Matter `inputs` 必须包含冻结的 VFY Revision，以及正文实际引用的其他直接上游 Artifact Revision。外部环境、流水线和平台不是 Artifact Input，其状态通过 Evidence 保存。

## Front Matter

RLS 使用 Core Artifact Front Matter：

```yaml
---
contract: sdlc-ai-spec/artifact/v0.1
phase: RLS
id: RLS-20260825160000-01
revision: 1
status: draft
profile: full
inputs:
  - IMP-20260825140000-01@1
  - VFY-20260825150000-01@1
---
```

## Scope 与输入就绪

一个 RLS Artifact 只绑定一个完整 VFY Scope 和一个明确 Release Target：

- `Scope Reference` 必须与 VFY 的完整 Scope 一致，不得在 RLS 选择部分 Change、Work Item 或 Result；
- `Result References` 必须与 VFY 最终 Subject Set 一致，不能重新构建或替换为未经该 VFY 覆盖的结果；
- PLN 为 `required` 时，当前 Scope 和 Target 对应的全部 `Target Phase=RLS` Work Item 必须进入 `Release Work Item References`；RLS 不建立 Work Item 领取或实时状态；
- Release Target 必须使用项目内唯一且可解析的名称；相互独立的正式目标分别形成 RLS Artifact；
- Target Baseline 必须是发版前可复核状态；首次发版固定写 `N/A — Initial Release`；
- VFY Revision 必须已冻结，且 Verification、Validation、Return 和 Exception 都能准确解析；
- VFY 产品结论为 `fail` 或存在未解决 Return 时默认停止；只有有效 RLS Exception 明确接受当前风险和范围后才能继续，VFY 原结论不得被改写；
- VFY `waived` Method 只有在其 Exception 明确登记 RLS 下游义务时，才转换为 Target Confirmation；永久获准跳过的义务只携带 Exception，不创建伪检查。

输入不足时必须返回权威 Phase：业务目标或范围返回 REQ，部署、数据或兼容方案返回 DSN，顺序、依赖或责任返回 PLN，产品结果返回 IMP，产品符合性结论返回 VFY。RLS 不补造缺失内容。

## 固定模板

```markdown
# <Release Title>

## 摘要 Summary

## 范围 Scope

## 发版合约 Release Contract

## 发版变更 Release Changes

## 发版操作 Release Actions

## 目标确认 Target Confirmation

## 发版结论 Release Conclusion

## 待确认项 Open Items

## 证据 Evidence

## 支撑产物清单 Supporting Artifact Manifest

## 豁免 Exceptions

## 门禁 Gate
```

RLS 是终点 Phase，不包含 `Lifecycle Applicability`。所有固定章节必须保留；外部平台日志、截图、报告和操作手册作为 Evidence、Supporting Artifact 或不可变引用保存，不在主要 Markdown 重复展开。

## Release Contract

```markdown
| Field | Value |
|---|---|
| Release Reference | |
| Scope Reference | |
| Result References | |
| Release Work Item References | None |
| Release Target | |
| Target Baseline | |
| VFY Conclusions | verification=pending, validation=pending — <CON references> |
```

规则：

- Release Reference 是当前发版的稳定版本、批次或等价标识，不代替 RLS Artifact ID；
- Scope、Result、Work Item 和 VFY Conclusion 使用 Core Reference Set 语法；
- 没有独立 PLN 时 `Release Work Item References` 写 `None`；
- `VFY Conclusions` 必须同时保存两个实际结论及准确 `CON-VER`、`CON-VAL` 引用，不能只引用 VFY Artifact Status；
- Contract 任一字段改变时，原 Action、Target Confirmation、Gate 和 Human Confirmation 立即失效。

## Release Changes

```markdown
| ID | 变更 Change | 来源引用 Source References | 结果 Result | 证据引用 Evidence References |
|---|---|---|---|---|
| RCH-001 | | | pending | None |
```

`Result` 只使用 `pending`、`released`、`partial` 或 `not_released`。

- 当前完整 Scope 的每项实际发版变化必须且只能登记一行；多个来源共同构成同一变化时合并引用，不能重复登记，也不能写入无上游来源的相邻变化；
- `released`、`partial` 和 `not_released` 必须引用支持目标侧事实的 Evidence 或 Target Confirmation；
- 任一 `pending` 阻止 RLS 最终化；
- 变化粒度应能区分独立结果，但不按文件、日志行或平台步骤机械拆分。

## Release Actions

```markdown
| ID | Order | 操作或资产引用 Action or Asset Reference | 执行方 Executor | 结果 Result | 证据引用 Evidence References |
|---|---:|---|---|---|---|
| RAC-001 | 1 | | | pending | None |
```

`Result` 只使用 `pending`、`success`、`fail`、`cancelled` 或 `waived`。

- `Order` 使用从 `1` 开始的唯一正整数，表达真实执行顺序；
- 应用发布、制品、SQL、配置、数据和人工操作使用同一张表，只有实际适用内容才创建行；
- Action 可以由 AI、人工、流水线或外部团队执行，Executor 保存实际执行角色或系统；
- `success` 和 `fail` 必须引用实际执行 Evidence，`waived` 必须引用有效 Exception；
- 同一语义 Action 的重复执行只更新当前未冻结行的最终结果，详细 Attempt 保存在外部执行记录或 Evidence，不新增 RLS 状态机。

## Target Confirmation

```markdown
| ID | 来源引用 Source References | 确认项 Confirmation | 预期 Expected | 观察结果 Observed | 结果 Result | 证据引用 Evidence References |
|---|---|---|---|---|---|---|
| RCK-001 | | | | | pending | None |
```

`Result` 只使用 `pending`、`pass`、`fail`、`n/a` 或 `waived`。

- Target Confirmation 只确认目标版本或制品、必要配置、SQL、数据状态、基本可用状态，以及 VFY 明确带入的目标环境检查；
- 每项确认必须描述可判定的 Expected 和实际 Observed，`pass`、`fail` 必须引用目标侧 Evidence；
- 流水线或平台 Action 成功只证明执行完成，不能单独代替目标侧确认；
- VFY 带入项必须在 Source References 中引用准确 Method、Target 和 Exception；结果为 `pass` 或 `fail` 时，当前 RLS 中承接的 Exception 必须转为 `resolved`，并以该 RCK 和 Evidence 作为 Resolution Reference；结果为 `waived` 时必须有新的或仍有效的 RLS Exception；
- RLS 不为复制结果创建后续 VFY Revision，也不重新执行完整 VFY；需要修改产品时返回上游形成新结果；
- `n/a` 只表示目标效果不存在或该确认客观不适用，必须在 Observed 中写明原因；未执行不能写为 `n/a`；
- 除 `cancelled` 且未产生目标效果外，RLS 至少需要一个实际目标侧 `pass` 或 `fail` 结果。

## Release Conclusion

```markdown
| Conclusion | Basis References | Remaining Risks or Follow-up | Completed At |
|---|---|---|---|
| pending | None | None | N/A |
```

`Conclusion` 只使用 `pending`、`success`、`partial`、`failed` 或 `cancelled`，按以下顺序取第一个满足的结果：

| 顺序 | 条件 | Conclusion |
|---:|---|---|
| 1 | 任一必要 Change、Action 或 Target Confirmation 为 `pending`，或必要事实尚未确定 | `pending` |
| 2 | 在产生任何目标效果前明确停止，且不存在执行失败 | `cancelled` |
| 3 | 任一必要 Action 为 `fail`、Target Confirmation 为 `fail`，或发版目标不可用 | `failed` |
| 4 | 已产生部分效果，但存在 `partial`、`not_released`、影响完整性的 `waived`，或仍由未关闭 Exception 接受的验证缺口 | `partial` |
| 5 | 全部 Change 为 `released`，Action 为 `success`，Target Confirmation 为 `pass` 或客观 `n/a`，且不存在影响发版完整性或可信度的未关闭 Exception | `success` |

`Basis References` 必须引用实际支持结论的 RCH、RAC、RCK、Evidence 或 Exception。最终结论的 `Completed At` 使用 RFC 3339；`pending` 固定为 `N/A`。持续影响、遗留问题和后续义务统一写入 `Remaining Risks or Follow-up`，不建立独立持续运行 Artifact。

VFY Conclusion、RLS Conclusion 与 Artifact Status 回答不同问题：VFY 判断产品符合性，RLS 判断目标侧发版结果，Artifact Status 判断当前记录是否合规。准确记录 `failed`、`partial` 或 `cancelled` 的 RLS Artifact 可以通过自身 Gate 并冻结。

## AI 与人工协作 AI and Human Collaboration

本节是 Phase 执行指导，不进入 RLS Artifact 模板，也不作为 Gate 或 AI 使用率指标。

| 工作 Activity | AI 适合做什么 | 人工适合做什么 | 原因 Reason |
|---|---|---|---|
| 发版准备 | 汇总准确范围、结果、SQL、配置和操作引用 | 确认真实目标及受限条件 | AI 擅长结构化，目标事实和权限来自项目 |
| 发版执行 | 执行可自动化操作并采集 Evidence | 提供受限权限或完成必要人工操作 | 实际执行主体不改变同一 Contract |
| 目标确认 | 运行确定性检查并整理目标侧事实 | 判断 UI、业务体验或受限环境结果 | 部分结果需要人的感知、权限或业务权威 |
| 最终结论 | 按固定规则聚合结果和剩余风险 | 完成 Human Confirmation 并接受未关闭 Exception | 风险接受和最终责任不能由模型承担 |

## Gate

RLS 使用 Core Gate Checks，并只增加以下 Phase Check：

```markdown
| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| RLS-G-001 | Release Contract 准确绑定完整 Scope、已验证 Result、Release Target、Target Baseline、VFY Conclusion 和适用 Work Item | pending | |
| RLS-G-002 | Release Changes 和 Release Actions 完整覆盖实际发版范围、顺序与执行结果，未增加或遗漏变化 | pending | |
| RLS-G-003 | 必要 Target Confirmation 已完成，目标侧状态及 VFY 带入义务具有明确 Evidence | pending | |
| RLS-G-004 | Release Conclusion 按固定顺序正确聚合，不存在未处理的 pending、范围漂移或被掩盖的风险 | pending | |
```

RLS Gate Checks 都是 Contract Integrity Check，只允许 `pending`、`pass` 或 `fail`。Release Conclusion 为 `failed`、`partial` 或 `cancelled` 不自动使 Gate Check 失败；Gate 只判断记录是否准确、完整、可信。

## 最终化

RLS 只执行一次最终 Artifact Gate：

- 发版前和执行中，当前 Revision 保持 `draft` 或 `waiting_input`，同一 Markdown 作为工作清单；
- 发版结束、失败或取消后补全实际结果，再按 Core 完成 Gate、Human Confirmation 和 Snapshot 冻结；
- 不生成第二份上线报告；冻结后的 RLS Artifact 就是最终 Release Record；
- 项目需要发版前审批或额外冻结点时通过 Project Extension 增加，不进入 Core RLS；
- 冻结后重复同一 Release Contract 的实际重试创建新 Revision；Scope 或 Result 改变时返回上游并形成新的 RLS Artifact，Release Target 改变时为该独立目标创建新的 RLS Artifact；目标变化使原设计或计划不再适用时再返回对应上游 Phase。

## 内部编号

| 对象 Item | 格式 Format |
|---|---|
| Release Change | `RCH-001` |
| Release Action | `RAC-001` |
| Target Confirmation | `RCK-001` |
| Open Item | `OI-001` |
| Evidence | `EVD-001` |
| Exception | `EX-001` |
| Gate Check | `RLS-G-001` |

## 当前未定义

- Project Extension 注册审批、职责分离、发布窗口、灰度、流量控制和专项合规规则的方式；
- CI/CD、Jenkins、制品库、变更单或其他平台的自动 Evidence 适配；
- Release Target 项目级注册和发现机制；
- RLS 模板生成、引用解析和自动验证工具。
