# Skill Design Contract — `sdlc-300-pln`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-300-pln` |
| Stage | `design` |
| Status | `ready` |
| Intended Plugin | `sdlc-ai-spec` |
| Base | `main@0c38135e3e8bdad0d60d674c93ad42078e880134` |
| Design Branch | `design/remaining-phase-skills` |
| Maintainer Decision | `pending` |

### Design-time Source

- `docs/v1.1/core-spec.md`
- `docs/v1.1/artifact-store-spec.md`
- `docs/v1.1/000-ctx-spec.md`
- `docs/v1.1/100-req-spec.md`
- `docs/v1.1/200-dsn-spec.md`
- `docs/v1.1/300-pln-spec.md`
- `docs/v1.1/500-vfy-spec.md` 与 `600-rls-spec.md`，仅用于准确解析 Return / Issue Control Input
- `skills/_shared/**`、`packages/sdlc_runtime/**`、`packages/sdlc_artifact_store/**`、`packages/sdlc_lifecycle/**`

生产 Runtime 不读取 `docs/**`。

## 2. Problem 与用户结果

### Problem

当前 Plugin 已能建立 CTX、REQ、DSN 并查询状态，但缺少把完整 Delivery Scope、下游 Applicability、Change、VFY Point、Exception 和协调义务转化为稳定 Work Item Set 的统一能力。若由 Agent 临时拆任务，容易出现范围遗漏、重复工作、跨 Phase 混合、依赖环、资源冲突和下游无法准确绑定。

### Intended User Outcome

用户通过短命令即可：

- 自动解析唯一可规划的 REQ / DSN Scope Input；
- 在 PLN 确实 `required` 时创建完整 Plan Artifact；
- 对 `n/a / waived / pending` 给出准确无 Artifact 结果；
- 得到可执行、可追踪、可独立闭合的 `WI-*`；
- 看见 Delivery Scope、依赖、角色、完成条件、预期 Evidence 与下一阶段；
- 无需手工维护 Scope Token、WI ID、覆盖矩阵、依赖排序、Evidence ID 或 Gate JSON。

## 3. 单一职责

### In Scope

- `create / revise / check` PLN Artifact；
- 聚合一个或多个完整 REQ / DSN Scope Input；
- 解析 `return_pln` VFY Return / RLS Issue Control Input；
- 计算 PLN Applicability 与完整 Delivery Scope；
- 形成 `Target Phase=IMP / VFY / RLS` 的 Work Item；
- 校验 Work Item 粒度、来源、约束、Scope Token、依赖、Completion Criteria、Expected Evidence 和 Responsible Role；
- 构建资源级保守冲突域和同资源 IMP 串行链；
- 覆盖全部 Change、VFY Point、下游义务、Exception 和 Control Input；
- open Revision 原地修订、frozen Revision 新建 Revision、no-change 不创建空 Revision；
- 扩展 Lifecycle Query，使 PLN 进入后续 IMP / VFY / RLS 前沿。

### Out of Scope

- 新增或改变 Requirement、Design Decision 或 Delivery Scope；
- 执行实现、验证、发布或维护实时任务状态；
- 强制工期、预算、具体人员、外部工单或项目管理平台；
- 导出或同步外部任务系统；
- 把 Work Item 当成实际 Phase 结果 Host；
- 自动调用兄弟 Skill；
- 写入项目源码树中的计划文件；
- Git、远端系统、依赖安装或 Project Root 外写入。

## 4. Decomposition Decision

| Question | Decision |
|---|---|
| 是否独立 Skill | 是；PLN 拥有独立 Plan Artifact、Revision、Gate 与 Work Item Authority |
| 是否按 IMP/VFY/RLS 拆 Skill | 否；三类 Work Item 必须在一个完整 Delivery Scope 内统一覆盖和依赖分析 |
| 是否拆外部任务平台 Skill | 当前不做；外部 Projection 不属于 PLN Authority |
| 共享能力 | ArtifactStore、Authority、Control Input Resolver、Lifecycle Query、Shared Interface |
| PLN 私有逻辑 | Delivery Scope Aggregation、Work Item、Scope Token、Coverage、Dependency Graph |

## 5. Trigger 与 Interface

只接受显式调用，进入 Exclusive Execution。

### Commands

| Command | Writes | Behavior |
|---|---:|---|
| `auto` | conditional | 根据准确 Input、PLN Applicability 和已有 PLN 选择 create/revise/check 或无 Artifact 结果 |
| `create` | yes | 创建新 Plan Artifact |
| `revise` | yes | 修订准确 PLN Revision |
| `check` | no | 严格只读检查完整 Plan、Work Item、依赖和 Gate |
| `help / version / commands / examples` | no | 只读取 bundled interface |

### Inputs

复用：

```text
--input / -i <exact-reference>   # 可重复
--reference / -r <PLN-...@N>     # revise/check 目标
```

`--input` 分类：

- 基础 frozen REQ / DSN Revision：Scope Input；
- VFY `RET-*` Return Phase=PLN：Control Input；
- RLS `RLI-* / RCF-*` Follow-up=`return_pln`：Control Input；
- 其他类型失败关闭。

### 裸调用与 `auto`

1. 解析唯一 Project Root；
2. 有准确 PLN Reference 时，open → revise，frozen 且无变化意图 → check；
3. 否则从 Lifecycle Query 读取唯一可供 PLN 使用的完整 Scope；
4. DSN 已 required 并存在时使用 DSN，不重复直接加入其覆盖的 REQ；
5. DSN 为 `n/a/waived` 时使用保存该处置的完整 REQ / DSN；
6. 多个完整 Scope Input 需要聚合时，默认给出推荐 Delivery Scope，存在多个合法边界时由用户决定；
7. PLN=`n/a/embedded/waived` 且依据闭合时，返回 `completed + artifact=null`；
8. PLN=`pending` 或 Scope 不完整时不分配 Artifact；
9. 唯一 matching open PLN → revise；唯一 frozen PLN 且无变化意图 → check；不存在 → create。

## 6. 决策所有权

模型可以自动完成：

- 固定 Applicability 聚合顺序；
- Scope Token 规范化、排序和去重；
- 明确的覆盖缺口、重复工作、依赖环和更晚 Phase 依赖检查；
- 同 `resource:<id>` IMP Work Item 的保守串行链；
- 可由一个 Outcome、Scope 和 Evidence 唯一确定的拆分或合并。

默认由用户决定：

- 多个合法 Delivery Scope Aggregation；
- Work Item 拆分或合并存在真实交付取舍；
- 非规则可确定的业务顺序、外部协调和 Responsible Role；
- Exception、Waiver、风险接受和组织承诺。

`decision_policy=model` 不能改变上游语义、接受 Exception 或承诺具体人员；`experiment` 只可用于可测量的计划结构比较，不替代责任或业务顺序决定。

## 7. Runtime Architecture

计划结构：

```text
skills/sdlc-300-pln/
├── SKILL.md
├── references/
│   ├── contract.md
│   ├── interface.json
│   └── source-lock.json
├── assets/
│   └── pln-template.md
├── scripts/
│   ├── pln_common.py
│   ├── pln_scope.py
│   ├── pln_analyzer.py
│   ├── pln_builder.py
│   ├── pln_verifier.py
│   ├── pln_handler.py
│   └── runtime.py
└── agents/openai.yaml
```

职责：

- `pln_scope.py`：Scope Input、Applicability、Delivery Scope、Control Input；
- `pln_analyzer.py`：Coverage、粒度、Scope Token、依赖和资源链；
- `pln_builder.py`：Canonical Markdown、Open Item、Gate、Manifest；
- `pln_verifier.py`：持久化 PLN Authority；
- `pln_handler.py`：create/revise/check 与 Store；
- `runtime.py`：共享接口和用户输出。

不新建共享 Provider 或数据库。

## 8. Input Contract

| ID | Input | Required | Validation | Missing / Invalid Behavior |
|---|---|---:|---|---|
| PLN-IN-01 | Scope Input | yes for Artifact | 完整准确 frozen REQ / DSN；同一 CTX；Authority 有效 | 不分配 Artifact，返回上游或选择 |
| PLN-IN-02 | Aggregation Basis | multi-input | 完整 Delivery Scope，不选择部分 Item | 用户决定或 action_required |
| PLN-IN-03 | Control Input | no | Return Phase=PLN / return_pln；所属 frozen Revision 可解析 | fail closed |
| PLN-IN-04 | Applicability | yes | required/n/a/embedded/waived/pending 与 Host/Exception 完整 | pending 不分配；非 required 不创建 Artifact |
| PLN-IN-05 | Work Item Candidate | yes for write | 固定字段、唯一 Phase、稳定 ID、准确来源 | Boundary 闭合后可 waiting_input |
| PLN-IN-06 | Final Confirmation | frozen only | 当前 Subject、Check Set 和 Authority Reference | 保持 open，不伪造批准 |

## 9. Canonical Artifact Contract

固定章节：

```text
Summary
Scope
Delivery Scope
Aggregated Applicability
Work Items
Open Items
Evidence
Supporting Artifact Manifest
Exceptions
Lifecycle Applicability
Gate
Final Confirmation
Artifact Gate Summary
```

Work Item 固定字段完全采用 `300-pln-spec.md`：

```text
ID
Target Phase
Outcome
Execution Scope
Source References
Constraint References
Depends On
Completion Criteria
Expected Evidence
Responsible Role
```

关键不变量：

- `WI-NNN` 当前 Plan 内唯一并跨 Revision 稳定；
- 一个 WI 只归属 IMP、VFY 或 RLS；
- 不保存实时 Status；
- 每个 required Phase 至少一个 WI；n/a/waived 不创建伪 WI；
- `Depends On` 无环，不指向更晚 Phase；
- IMP WI 对每个版本化资源包含 `resource:<id>`；
- 共享资源的 IMP WI 形成确定依赖链；
- RLS WI 恰好一个 `environment:<release-target-id>`；
- Delivery Scope 每个执行义务均有覆盖；
- 下游使用 `<PLN-ID>@<Revision>#<WI-ID>`，外部编号不能替代。

PLN Phase Checks：`PLN-G-001` 至 `PLN-G-007`。

## 10. Revision 与状态

- Applicability 未确定或不是 required：不分配 PLN；
- Scope 已确定但 Work Item 不完整：materialized open / `waiting_input`；
- Contract Integrity 失败：open / `failed`；
- Gate 通过、无 Open Item、Final Confirmation 有效：freeze；
- frozen Revision 有有效变化：新 Revision；
- no-change：返回现有 Revision；
- build 失败的新 Control Reservation：abandon；
- check：绝对只读。

## 11. Lifecycle Query

扩展关系：

```text
REQ / DSN → PLN
PLN → IMP / VFY / RLS Work Item
```

Projection：

- open / failed PLN：停留 PLN；
- frozen ready PLN：返回尚未闭合的最早 Target Phase Work Item；
- 多个可并行 Work Item：列出候选，不选“第一个”；
- IMP Work Item 通过 Current completed Claim 闭合；
- VFY / RLS Work Item 通过目标 Phase 固定引用闭合；
- Query 不写入 Work Item Status。

## 12. 用户输出

默认 Summary：

- Delivery Scope；
- IMP / VFY / RLS Work Item 数；
- 关键依赖与资源串行链；
- 未覆盖来源、Open Item 和 Exception；
- 是否形成 frozen PLN；
- 唯一下一动作或可并行候选。

默认隐藏完整 Gate、Digest、Manifest 和内部 Evidence ID。

## 13. 稳定错误

至少包含：

```text
PLN_SCOPE_INPUT_REQUIRED
PLN_SCOPE_CONFLICT
PLN_APPLICABILITY_PENDING
PLN_NOT_REQUIRED
PLN_WORK_ITEM_INVALID
PLN_COVERAGE_INCOMPLETE
PLN_DEPENDENCY_CYCLE
PLN_PHASE_ORDER_INVALID
PLN_RESOURCE_CHAIN_UNRESOLVED
PLN_ROLE_DECISION_REQUIRED
PLN_FINAL_CONFIRMATION_STALE
```

## 14. Source Lock 与 Runtime Independence

计划锁定：

- 5 个 Shared Runtime Contract；
- Core、Artifact Store、CTX、REQ、DSN、PLN、VFY、RLS；
- 合计 13 项。

PLN Artifact Evaluation Contract Set 只包含 Core、Artifact Store 和 PLN。其他 Spec 只用于上游/Control Input 解析。

删除 `docs/**` 后，meta command、create/revise/check、Work Item、依赖图、Source Lock 和 Lifecycle Query 必须运行。

## 15. Definition of Done

Design 达到 ready，当且仅当：

- Applicability 与 no-artifact 结果明确；
- Work Item、Scope Token、Coverage、Dependency 和闭合规则可确定实现；
- 没有外部平台或实时进度扩张；
- Lifecycle Query 关系明确；
- Eval Plan 能判定所有关键不变量；
- 阻塞设计 Open Item 为零。
