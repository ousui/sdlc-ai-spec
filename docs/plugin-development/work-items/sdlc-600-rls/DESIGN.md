# Skill Design Contract — `sdlc-600-rls`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-600-rls` |
| Stage | `design` |
| Status | `ready` |
| Intended Plugin | `sdlc-ai-spec` |
| Base | `main@0c38135e3e8bdad0d60d674c93ad42078e880134` |
| Design Branch | `design/remaining-phase-skills` |
| Maintainer Decision | `pending` |

### Design-time Source

- Core、Artifact Store、CTX、REQ、DSN、PLN、IMP、VFY、RLS v1.1 Spec；
- Shared Skill Interface、Artifact Runtime、Lifecycle Query；
- 已批准的 Resource / Execution Evidence Contract。

生产 Runtime 不读取 `docs/**`。本设计保持平台中立，不定义特定托管、流水线或发布系统。

## 2. Problem 与用户结果

### Problem

RLS 既要在发版前锁定准确 Scope、Result、VFY、Target 和 Target Baseline，又要执行或记录真实目标副作用、采集目标侧 Evidence、完成 Post-release Confirmation、形成 Conclusion 和 Follow-up。若仅把它实现成“调用发布命令”，会把流水线成功误当目标状态正确，丢失失败/部分/取消事实，或在没有独立授权时执行外部副作用。

### Intended User Outcome

用户通过短命令即可：

- 从冻结 VFY 自动建立完整 Release Contract；
- 在任何目标效果前审阅 Release Item、RCF、Target 和 Baseline；
- 对准确执行集合进行一次明确授权；
- 执行或记录实际发版操作和目标侧确认；
- 形成 success/partial/failed/cancelled 的可信最终 Release Record；
- 把问题准确路由为 retry_rls 或 return_req/dsn/pln/imp；
- 不需要手工构造 RLI/RCF、Evidence ID、Conclusion、Gate 或 Runtime JSON。

## 3. 单一职责

### In Scope

- `create / revise / check` RLS Artifact；
- `execute` 一个或多个 pending Release Item；
- `confirm` 一个或多个 Post-release Confirmation；
- `cancel` 在目标效果前主动终止；
- 绑定一个完整 VFY Scope、准确 Result Set、一个 Release Target 与 Target Baseline；
- 覆盖 RLS Work Item 和 VFY Release Target 下游义务；
- 保存真实 Executor、Observed、Evidence 和 Follow-up；
- 固定 Release Conclusion 聚合；
- 重试同一稳定发版身份的新 Revision；
- 形成最终冻结上线报告。

### Out of Scope

- 修改或重建代码、SQL、配置、测试资产或 Implementation Result；
- 临时缩小完整 Scope 或换包；
- 重新执行完整 VFY；
- 规定组织审批、发布窗口、灰度、流量控制或特定平台流程；
- 长期监控、值守、告警、故障处置和日常 Runbook；
- 当前 Scope 外目标环境问题；
- 自动 Git tag/push、远端 API 或真实目标操作，除非有准确 effect authorization；
- 平台专属字段进入 Core Artifact Contract。

## 4. Decomposition Decision

| Question | Decision |
|---|---|
| 是否独立 Skill | 是；RLS 是终点 Artifact 和最终 Release Record Authority |
| 是否按平台拆 Skill | 否；当前设计不考虑特定平台，执行方式属于内部 Executor |
| 是否建立独立长期运行 Skill | 否；长期运行不属于 RLS Phase |
| 执行结果是否外部 Authority | 否；外部记录是 Evidence，RLS Artifact 聚合为最终权威记录 |
| Provider/Adapter | 本阶段设计不定义；实现保持通用 Executor Contract |

## 5. Trigger 与 Interface

只接受显式调用，进入 Exclusive Execution。

### Commands

| Command | Writes / Effects | Behavior |
|---|---|---|
| `auto` | conditional | 根据 Applicability、已有 RLS、pending RLI/RCF 和 Target effect 选择 create/execute/confirm/revise/check |
| `create` | local write | 创建 Release Contract、RLI/RCF 和 Pre-execution Checklist，不产生 Target effect |
| `execute` | external effect | 执行/记录一个或多个 Release Item |
| `confirm` | external/read effect | 执行/记录 Post-release Confirmation |
| `revise` | local write | 在允许边界内修订 open RLS；重试 frozen 记录时创建新 Revision |
| `check` | no | 严格只读检查 Release Record |
| `cancel` | external state/local write | 仅在未产生 Target effect 时主动取消并形成结论 |
| `help / version / commands / examples` | no | 元命令 |

### Inputs 与参数

```text
--input / -i <exact VFY/upstream/control reference>   # 可重复
--reference / -r <RLS-...@N>
--item <RLI-NNN|RCF-NNN>                              # 可重复，execute/confirm
--target <project-registered release-target-id>
--release-reference <stable release/batch/version id>
```

- VFY Revision 必须准确、冻结且可进入 RLS；
- Result Set 必须与 VFY Subject Set 完全一致；
- 一个 RLS 只绑定一个完整 Scope 和一个 Release Target；
- `--item` 只能选择当前 open Revision 中适用的 RLI/RCF；
- 不根据最近流水线、默认环境或字符串相似度猜测 Target。

### 裸调用与 `auto`

1. 解析唯一 VFY Scope 和 RLS Applicability；
2. RLS=`n/a/waived` 且尚无 Target effect 时返回无 Artifact 结果；pending 时请求 Target/意图决定；
3. required 时查找同一稳定发版身份和 Target 的 RLS；
4. 不存在 → create；
5. open 且有 pending RLI、未产生 effect → execute；
6. 已产生 effect 且有 pending RCF → confirm；
7. open 且存在 Contract/Scope/Result 漂移 → 返回上游或 revise；
8. frozen 且同 Scope/Result/Target 需要实际重试 → 新 Revision；
9. frozen 且无变化 → check。

## 6. 外部副作用授权

RLS 引入独立 `Effect Authorization`，不能由 `write_policy`、工作区权限、Approval/Trigger Reference 或 Final Confirmation 替代。

授权必须绑定：

```text
RLS Artifact ID + Revision
Release Reference
Scope Reference
Result References
Release Target
Target Baseline
本次 RLI ID 集合及动作摘要
Pre-execution Checklist Digest
授权主体、范围和时间
```

规则：

- `create` 只写 ArtifactStore，不需要 effect authorization；
- `execute` 每次目标效果前必须有匹配当前 Contract 的授权；
- Contract 任一字段变化使旧授权失效；
- `confirm` 的只读目标检查可按项目权限执行；会改变目标状态的确认动作同样需要授权；
- `cancel` 只有 Evidence 证明未产生目标效果时可使用；
- 自动化委托必须由用户明确限定目标、操作集合和有效条件；
- 不保存 Secret 或长期凭证。

## 7. 决策所有权

模型可以自动完成：

- 从 VFY/PLN/Result 推导 RLI、RCF 候选；
- 固定 Conclusion 与 Follow-up 聚合；
- 可安全执行的已授权确定性操作；
- Evidence、Target Baseline 和结果完整性检查。

用户/权威责任人决定：

- Release Target、真实发版意图和执行权限；
- 目标效果可能产生的操作；
- Exception、风险接受和继续发版；
- 主观目标侧体验；
- 多个合法执行顺序或人工操作；
- 是否取消或重试。

`decision_policy=model` 不授予外部权限，也不能接受风险或用流水线成功替代 RCF。

## 8. Runtime Architecture

计划结构：

```text
skills/sdlc-600-rls/
├── SKILL.md
├── references/{contract.md,interface.json,source-lock.json}
├── assets/rls-template.md
├── scripts/
│   ├── rls_common.py
│   ├── rls_scope.py
│   ├── rls_contract.py
│   ├── rls_items.py
│   ├── rls_executor.py
│   ├── rls_confirmation.py
│   ├── rls_conclusion.py
│   ├── rls_builder.py
│   ├── rls_verifier.py
│   ├── rls_handler.py
│   └── runtime.py
└── agents/openai.yaml
```

`rls_executor.py` 只接受已批准的结构化 RLI 和 Effect Authorization，返回 Executor、状态、原始 Evidence、是否产生 Target effect；不包含平台特定字段或第二套 Gate。

## 9. Input Contract

| ID | Input | Required | Validation | Failure |
|---|---|---:|---|---|
| RLS-IN-01 | VFY Revision | yes | frozen，Method/Target/CON 无不允许 pending，非 early-stop |
| RLS-IN-02 | Scope Reference | yes | 与 VFY 完整 Scope 完全一致 |
| RLS-IN-03 | Result References | yes | 与 VFY final Subject Set 完全一致，不换包 |
| RLS-IN-04 | Release Target | yes | 项目内唯一、可解析、单 Target |
| RLS-IN-05 | Target Baseline | yes | 发版前可复核；首次为固定 Initial Release |
| RLS-IN-06 | RLS Work Items | conditional | 当前 Target 全覆盖 |
| RLS-IN-07 | Release-target VFY obligations | conditional | 全部映射到 RCF，不降低口径 |
| RLS-IN-08 | Effect Authorization | execute | 精确绑定当前 Contract/Checklist/RLI |
| RLS-IN-09 | Final Confirmation | freeze | 绑定真实 RLI/RCF/Conclusion/Evidence |

VFY product fail/unresolved Return 默认禁止 RLS；只有有效 Exception 明确接受风险和范围时可继续，原结论不修改。

## 10. Canonical Artifact Contract

固定章节：

```text
Summary
Scope
Release Contract
Release Items
Post-release Confirmation
Release Conclusion
Open Items
Evidence
Supporting Artifact Manifest
Exceptions
Gate
Final Confirmation
Artifact Gate Summary
```

RLS 不包含 Lifecycle Applicability。

### Release Contract

固定字段：Release Reference、Scope Reference、Result References、VFY Reference and Conclusions、RLS Work Item References、Release Target、Target Baseline、Approval or Trigger Reference。

### Release Item

`RLI-*` Result：`pending/success/partial/fail/cancelled/waived`。

### Post-release Confirmation

`RCF-*` Result：`pending/pass/fail/not_run/n/a/waived`。流水线执行成功不能单独支持 pass；产生或可能产生 Target effect 后至少一个实际目标侧 pass/fail。

### Follow-up

唯一枚举：

```text
none
retry_rls
return_req
return_dsn
return_pln
return_imp
```

### Conclusion

固定聚合：`pending/success/partial/failed/cancelled`。失败、部分或取消的 RLS Artifact 可以 Gate pass 并冻结，只要记录准确。

RLS Phase Checks：`RLS-G-001` 至 `RLS-G-003`。

## 11. 执行状态与 Revision

- 发版前/执行中：open draft/waiting_input；
- create 保存完整 Pre-execution Checklist 和计划；
- execute/confirm 更新同一 open Revision；
- 目标效果前主动停止：cancelled；
- 实际结束、失败或取消后补全结果、Conclusion、Gate、Final Confirmation 并 freeze；
- 相同 Scope/Result/Target 的实际重试：同 RLS ID 新 Revision，重新捕获 Baseline/授权/Checklist；
- Scope/Result 改变：返回上游，不能在 RLS 换包；
- Target 不同：独立 RLS Artifact；
- no-change check：不创建新 Revision；
- check 绝对只读。

## 12. Lifecycle Query

RLS 是终点：

- open/pending → 停留 RLS；
- retry_rls → 同 RLS 新 Revision；
- return_req/dsn/pln/imp → 准确 Issue Reference 作为对应 Phase Control Input；
- success → 生命周期完成；
- failed/partial/cancelled + return_* → 指向权威上游；
- failed/partial/cancelled + retry_rls → 指向 RLS；
- none 且无后续 → 显示终态和剩余风险；
- Query 不把 Gate pass 解释为 Release success。

## 13. 用户输出

### create 前

- 发什么、Scope/Result；
- Release Target 与 Baseline；
- RLI 顺序、Executor、前置条件；
- RCF Expected 和 Evidence 获取方式；
- 待授权的准确 Target effect。

### 执行后

- 每个 RLI/RCF 实际结果；
- Target 是否产生效果；
- Release Conclusion；
- Remaining Risks/Follow-up；
- Issue Reference 与下一动作；
- Artifact 是否冻结。

默认隐藏凭证、平台原始响应、Digest 和内部 Runtime JSON。

## 14. 稳定错误

至少包含：

```text
RLS_NOT_REQUIRED
RLS_APPLICABILITY_PENDING
RLS_VFY_NOT_READY
RLS_SCOPE_MISMATCH
RLS_RESULT_MISMATCH
RLS_TARGET_REQUIRED
RLS_TARGET_AMBIGUOUS
RLS_BASELINE_UNRESOLVED
RLS_WORK_ITEM_COVERAGE_INCOMPLETE
RLS_CONFIRMATION_CONTRACT_INCOMPLETE
RLS_EFFECT_AUTHORIZATION_REQUIRED
RLS_EFFECT_AUTHORIZATION_STALE
RLS_EXECUTION_FAILED
RLS_TARGET_STATE_UNVERIFIED
RLS_FOLLOW_UP_INVALID
RLS_CONCLUSION_INCONSISTENT
RLS_CANCEL_NOT_ALLOWED
RLS_FINAL_CONFIRMATION_STALE
```

## 15. Source Lock 与 Runtime Independence

计划锁定：

- 5 Shared Runtime Contract；
- 已批准 Resource/Execution Effect Contract；
- Core、Artifact Store、CTX、REQ、DSN、PLN、IMP、VFY、RLS；
- 最终数量在依赖固定后冻结。

RLS Artifact Evaluation Contract Set 只包含 Core、Artifact Store、RLS 和明确注册的执行 Evidence Contract。

删除 `docs/**` 后，create/execute/confirm/revise/check/cancel、Conclusion、Follow-up 和 Lifecycle Query 必须运行；外部测试使用受控 Fake Target 或一次性 sandbox，不依赖真实平台。

## 16. Definition of Done

- Effect Authorization 与 write policy 分离；
- VFY/Input/Result/Target 不可替换；
- RLI/RCF/Conclusion/Follow-up 模型闭合；
- failed/partial/cancelled Artifact 冻结语义明确；
- 平台中立，无 Provider 扩张；
- Lifecycle Query 能准确结束或返工；
- Eval 可判定真实目标效果和零副作用边界；
- 阻塞设计 Open Item 为零。
