# Skill Design Contract — `sdlc-400-imp`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-400-imp` |
| Stage | `design` |
| Status | `ready` |
| Intended Plugin | `sdlc-ai-spec` |
| Base | `main@0c38135e3e8bdad0d60d674c93ad42078e880134` |
| Design Branch | `design/remaining-phase-skills` |
| Maintainer Decision | `pending` |

### Design-time Source

- Core、Artifact Store、CTX、REQ、DSN、PLN、IMP、VFY、RLS v1.1 Spec；
- Shared Skill Interface、Artifact Runtime、Phase Runtime；
- 当前 ArtifactStore 的 IMP external ID / Revision Reservation 能力。

生产 Runtime 不读取 `docs/**`。

## 2. Problem 与用户结果

### Problem

IMP 不只是生成一份 Markdown；它必须解析一个准确 Binding、领取唯一执行权、保护资源范围、形成实施方法、修改产品资源、保存不可变 Result、执行局部检查，并在 Artifact freeze 后原子完成 Current Claim。缺少统一 Skill 时，AI 容易直接改代码却没有 Baseline、Claim、Result、Evidence 或返工闭环，也可能吸收用户既有修改、越界重构、重复执行或把本地检查误写为产品验证通过。

### Intended User Outcome

用户通过短命令即可：

- 选择一个准确 IMP Binding；
- 在修改前完成 Readiness、Claim、Baseline 和 Execution Scope；
- 看到连续、最小充分的 Implementation Approach；
- 让 Skill 在 Claim Scope 内实施代码、配置、文档或其他产品变化；
- 得到不可变 Result Set、局部 Checks、Evidence、Gate 和下一步 VFY；
- 中断后安全恢复、返工或显式 abandon；
- 不需要手工管理 Attempt、Claim Record、RES/CHK ID、VCS Locator 或 Runtime JSON。

## 3. 单一职责

### In Scope

- 解析一个准确 IMP Binding Reference；
- Claim `resolve / acquire / abandon / complete`；
- IMP Artifact ID、Revision Reservation 与 Claim 一致性；
- Readiness、Dependency Result、Rework Reference 和 Baseline；
- 七项 Implementation Consideration 与连续 Approach；
- 在准确 Claim Scope 内修改版本化产品资源；
- Implementation Result Set、局部 Check、Evidence、Supporting Member；
- freeze Artifact 后完成 Current Claim；
- open Revision 修订、completed Lineage 返工、新 Attempt、新 Revision；
- 失败恢复、资源冲突和依赖链失效处理；
- Lifecycle Query 投影 Current Claim、IMP Result 和 VFY 就绪性。

### Out of Scope

- 新增或改变 Requirement、Design、Delivery Scope 或 Work Item；
- 重组、拆分或合并 Binding；
- 顺手重构、推测性抽象或 Claim Scope 外优化；
- 完整系统/业务 VFY、发布判断或 Release Target 操作；
- 自动安装依赖；
- 自动 commit、push、merge、tag 或移动 Git Ref；
- 保存隐藏推理过程；
- 绑定具体语言、框架或开发工具。

## 4. Decomposition Decision

| Question | Decision |
|---|---|
| 是否独立 Skill | 是；IMP 拥有独立 Artifact、Binding、Claim、Result 和 Gate |
| 是否按语言/工具拆 Skill | 否；语言与工具属于内部执行 Strategy |
| Claim 是否 Skill 私有 | 否；Claim 是共享执行 Authority，独立 Package |
| VCS/Snapshot 是否 Skill 私有 | 否；不可变资源 Result 可被 VFY/RLS 复用，独立 Package |
| Test 是否拆 Skill | 否；局部 Check 属于 IMP，完整符合性属于 VFY |

## 5. 前置 Foundation

IMP 实现前必须先完成并独立验证：

```text
packages/sdlc_claim_provider/
packages/sdlc_resource/
```

### Claim Provider Contract

至少支持：

```text
resolve(binding_or_lineage)
acquire(request)
abandon(request)
complete(request)
```

它是以下事实的唯一 Authority：

- Binding Lineage；
- Current Attempt；
- Current Owner；
- Execution Scope / Resource 锁；
- 稳定 IMP Artifact ID；
- 当前 Attempt 的目标 Revision Reservation；
- Claim State：active/completed/abandoned。

默认本地 SQLite-only；不得用 ArtifactStore Revision Control Record 代替 Claim。

### Resource Contract

至少提供：

- canonical Resource ID；
- 实际工作区 Baseline Snapshot，包括用户既有修改；
- `vcs:<resource>@<immutable-revision>` 或完整 Snapshot Member；
- Claim Scope 与 Changed Scope 包含关系；
- Pre-execution / Post-execution 读回；
- 不移动分支、Tag 或远端 Ref。

## 6. Trigger 与 Interface

只接受显式调用，进入 Exclusive Execution。

### Commands

| Command | Writes | Behavior |
|---|---:|---|
| `auto` | conditional | 根据 Binding、Current Claim、Revision 和 Rework 选择 create/revise/check |
| `create` | yes | 首次 acquire 并实施一个 Binding |
| `revise` | yes | 继续 active/open Attempt，或为合法返工创建新 Attempt/Revision |
| `check` | no | 只读检查 Artifact、Claim、Result、依赖和 Gate |
| `abandon` | yes | 显式终止可放弃的 active Claim 与 open Revision |
| `help / version / commands / examples` | no | 元命令 |

### Phase Parameters

```text
--binding / -b <exact binding reference>
--input / -i <dependency/rework/input reference>   # 可重复
--owner <stable executor token>
--reference / -r <IMP-...@N>
```

规则：

- `--binding` 恰好一个；PLN required 时为 `PLN-...@N#WI-*`，直接路径为完整 REQ/DSN Reference；
- `--input` 可包含前驱 frozen IMP Revision、VFY Return、RLS Issue、新 Binding 或控制恢复引用；
- `--owner` 可从宿主稳定执行身份唯一解析；无稳定身份或多个候选时用户决定；
- `--reference` 用于 revise/check/abandon 的准确 IMP Revision；
- 不能用标题、分支或最近修改推断 Binding。

### 裸调用与 `auto`

1. 解析唯一 Project Root 和可执行 Binding 候选；
2. 多个 WI/直接 Binding 时列出候选；
3. 无 Claim → create/acquire；
4. Current active 且请求与 Owner/Binding/Input/Rework 完全匹配 → revise/resume；
5. Current completed 且无合法 Rework → check；
6. completed/abandoned 只有收到合法非空 Rework 或显式 retry 才新 Attempt；
7. mismatch、依赖失效、资源冲突或范围不闭合时停止，不抢占；
8. 产品修改前展示 Binding、Baseline、Resource、Execution Scope 和预期副作用摘要。

## 7. 写入和授权

`write_policy=auto` 在 IMP 中只授权：

- Claim Scope 内、已建立准确 Baseline 的项目内产品资源修改；
- `.sdlc` Claim / Artifact 记录；
- Skill Contract 声明的 Supporting Evidence。

它不授权：

- Claim Scope 外修改；
- 删除用户未纳入 Baseline 的工作；
- Git commit/push/merge/tag；
- 依赖安装；
- 外部系统写入；
- Project Root 外文件。

`write_policy=confirm` 在第一次产品修改前确认；`deny` 仅允许 Readiness、Method Preview 和 check。

存在未提交用户变化时必须形成完整 Baseline Snapshot；不能用 `HEAD` 冒充工作区 Baseline。

## 8. 决策所有权

IMP 可以自动决定：

- 由上游 Design/项目 Spec 唯一确定的局部实现；
- 格式、导入、命名、私有函数组织；
- 最简单局部实现；
- 确定性工具命令和局部 Check。

必须返回上游或用户决定：

| 缺失 | Return |
|---|---|
| 业务规则、验收边界 | REQ |
| 架构、接口、数据、状态、一致性、技术选择 | DSN |
| Outcome、WI 粒度、依赖、Scope | PLN |
| 已确认边界内局部实现错误 | IMP 内修正 |

模型不得自行接受风险、引入公共抽象/新依赖/跨模块接口，或借 `decision_policy=model` 修改上游权威语义。

## 9. Runtime Architecture

计划结构：

```text
packages/sdlc_claim_provider/**
packages/sdlc_resource/**

skills/sdlc-400-imp/
├── SKILL.md
├── references/{contract.md,interface.json,source-lock.json}
├── assets/imp-template.md
├── scripts/
│   ├── imp_common.py
│   ├── imp_binding.py
│   ├── imp_readiness.py
│   ├── imp_method.py
│   ├── imp_executor.py
│   ├── imp_result.py
│   ├── imp_builder.py
│   ├── imp_verifier.py
│   ├── imp_handler.py
│   └── runtime.py
└── agents/openai.yaml
```

- Binding/Readiness 无副作用；
- Claim Acquire 在首次产品修改前；
- Executor 只使用批准的 Method Contract 和 Claim Scope；
- Result Capture 形成不可变 Baseline/Change/Result；
- Artifact freeze 与 Claim complete 是两个有序 Authority 写入；
- complete 失败不重写 frozen Artifact，按 Spec 恢复为 abandoned Claim。

## 10. Input Contract

| ID | Input | Required | Validation | Failure |
|---|---|---:|---|---|
| IMP-IN-01 | Binding | yes | 唯一准确 WI 或直接 Binding；Lineage 可派生 | 返回 PLN/上游 |
| IMP-IN-02 | Claim Owner | yes | 稳定唯一身份 | user decision |
| IMP-IN-03 | Execution Scope | yes | 与 WI/Direct Scope 完全一致，含全部 resource token | fail closed |
| IMP-IN-04 | Dependency Results | conditional | Current completed Claim、frozen Revision、连续依赖链 | blocked |
| IMP-IN-05 | Rework References | rework | 合法 Return/Issue/Binding/前驱/控制恢复集合 | mismatch |
| IMP-IN-06 | Baseline | per Resource | 实际首次修改前不可变状态 | 不修改产品 |
| IMP-IN-07 | Project Spec | conditional | 不与上游 Contract 冲突 | 返回 DSN/用户 |
| IMP-IN-08 | Final Confirmation | freeze | 绑定当前 Method、Result、Checks、Claim | 保持 open |

## 11. Canonical Artifact Contract

固定内容至少包括：

```text
Summary
Scope
IMP Binding and Claim Snapshot
Input Readiness
Implementation Consideration Matrix
Implementation Approach and Method Blocks
Implementation Result Set
Implementation Checks
Open Items
Evidence
Supporting Artifact Manifest
Exceptions
Lifecycle Applicability
Gate
Final Confirmation
Artifact Gate Summary
```

固定 7 项 Consideration：

```text
Calculation Rules
Decision Rules
State Transitions
Algorithm & Invariants
Data Contract & Transformation
Boundary & Failure Handling
Effects & Consistency
```

Disposition：`pending/required/n/a/waived`。required 必须关联 Step 和相应方法块。

Result Set：每个 Claim `resource:<id>` 恰好一个 `RES-*`；实际变化行必须有 immutable Result，沿用行按 Spec 保存 Baseline=Result。

Implementation Checks：`CHK-*`；只证明局部实现可进入 VFY。

IMP Phase Checks：`IMP-G-001` 至 `IMP-G-006`。

## 12. Claim / Revision 状态机

```text
no claim → active
active → completed
active → abandoned
abandoned → active (new attempt)
completed → active (legal rework)
```

顺序：

1. resolve/readiness；
2. acquire，分配 Artifact ID、Attempt、Owner、Revision Reservation；
3. ArtifactStore 采用准确 external ID/Revision 建 open Control Record；
4. 首次完整 Payload 写入后才 materialized；
5. 实施、检查、Result、Gate；
6. freeze Revision；
7. Claim complete CAS；
8. 两者都成功才供 VFY 使用。

异常：

- pre-freeze abandon：先 abandon Revision，再 abandon Claim；
- frozen complete 失败：保留 Snapshot，Claim 以固定错误原因转 abandoned；
- Claim 终结失败：保持 active；
- 不创建第二 IMP Artifact。

## 13. Lifecycle Query

扩展：

```text
PLN#WI / REQ / DSN → IMP Binding
IMP dependency → IMP
IMP → VFY
```

只在以下条件同时成立时投影 IMP Work Item completed：

- frozen IMP Revision；
- Current Claim=completed；
- Binding/Attempt/Artifact/Revision/Dependency Result 完全匹配；
- Result Set 与 Claim Resource 完整；
- 无更新前驱尚未吸收。

active、abandoned、open 或 frozen+active 均不完成。前驱新 Attempt 会使旧下游失去当前有效性。

## 14. 用户输出

默认显示：

- Binding 和 Work Item Outcome；
- Owner、Attempt、Claim State；
- Baseline 与将修改的 Resource；
- Approach 摘要；
- 实际 Changed Scope；
- Result Reference；
- Checks 和失败；
- 是否可进入 VFY；
- 唯一下一动作。

默认隐藏内部 CAS、SQLite、Digest 和完整命令日志；debug 可展示脱敏证据。

## 15. 稳定错误

至少包含：

```text
IMP_BINDING_REQUIRED
IMP_BINDING_AMBIGUOUS
IMP_BINDING_MISMATCH
IMP_CLAIM_CONFLICT
IMP_OWNER_MISMATCH
IMP_RESOURCE_CONFLICT
IMP_DEPENDENCY_INCOMPLETE
IMP_READINESS_FAILED
IMP_BASELINE_UNRESOLVED
IMP_SCOPE_VIOLATION
IMP_UPSTREAM_DECISION_REQUIRED
IMP_RESULT_INCOMPLETE
IMP_CHECK_FAILED
IMP_FINAL_CONFIRMATION_STALE
IMP_COMPLETE_FAILED
IMP_ABANDON_NOT_ALLOWED
```

## 16. Source Lock 与 Runtime Independence

计划锁定：

- 5 Shared Runtime Contract；
- Claim Provider、Resource Contract；
- Core、Artifact Store、CTX、REQ、DSN、PLN、IMP、VFY、RLS；
- 具体总数在 Foundation Contract ID 固定后冻结。

IMP Artifact Evaluation Contract Set 只包含 Core、Artifact Store、IMP 及明确注册的共享 Claim/Resource Runtime Contract；上游 Phase Spec 只用于输入验证。

删除 `docs/**` 后，Claim、Readiness、dry-run、create/revise/check/abandon、Result Capture 和 Lifecycle Query 必须运行。

## 17. Definition of Done

Design ready 条件：

- Claim 与 ArtifactStore Authority 分离明确；
- 产品写入、Baseline、Result 和 Git 边界明确；
- 7 项 Consideration 与 Result Set 可确定实现；
- 失败恢复和 Claim 状态机闭合；
- 不按语言/工具拆 Skill；
- Eval 能验证并发、越界、篡改、依赖失效和 VFY 就绪；
- 阻塞设计 Open Item 为零。
