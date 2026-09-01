# Skill Design Contract — `sdlc-500-vfy`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-500-vfy` |
| Stage | `design` |
| Status | `ready` |
| Intended Plugin | `sdlc-ai-spec` |
| Base | `main@0c38135e3e8bdad0d60d674c93ad42078e880134` |
| Design Branch | `design/remaining-phase-skills` |
| Maintainer Decision | `pending` |

### Design-time Source

- Core、Artifact Store、CTX、REQ、DSN、PLN、IMP、VFY、RLS v1.1 Spec；
- Shared Skill Interface、Control Input Resolver、Lifecycle Query；
- 后续批准的 Claim/Resource Contract，用于解析 Current completed IMP Result。

生产 Runtime 不读取 `docs/**`。

## 2. Problem 与用户结果

### Problem

VFY 必须同时处理完整 Delivery Scope、权威 Target、当前终端 Subject、上游 VFY Strategy、PLN Work Item、Method Contract、真实执行、Evidence、Verification/Validation 两类结论以及 Return。若只把它实现为“跑测试”，会遗漏 Inspection/Analysis/Demonstration、主观 Validation、失败早停、Return 归因和产品失败与 Artifact Gate 的语义分离。

### Intended User Outcome

用户通过短命令即可：

- 自动解析完整 Scope、Target 和 Current Subject；
- 生成最小充分的 VFY Method Set；
- 自动执行可安全确定的 Inspection、Analysis 和 Test；
- 对需要真实人工判断或受限环境的 Method 给出清晰场景和最小输入；
- 形成 Method Result、Target Conclusion、CON-VER、CON-VAL、Evidence 和 Return；
- 明确“产品 fail”与“VFY Artifact 自身 Gate pass”的区别；
- 得到进入 RLS 或返回 REQ/DSN/PLN/IMP 的唯一下一动作。

## 3. 单一职责

### In Scope

- `create / revise / check` VFY Artifact；
- `run` 当前 open Revision 中一个或多个 pending/selected Method；
- 解析完整 Scope Source、Target Set、Subject Set、上游 Evidence 和 Control Input；
- Inspection、Analysis、Demonstration、Test 四类 Method；
- automated/manual/hybrid Execution Mode；
- Method Result、Target Conclusion、CON-VER / CON-VAL；
- 产品失败早停与 Return Record；
- VFY Return、RLS 产品修正 Issue 的承接与解决证明；
- Evidence、Supporting Member、Exception、Final Confirmation 和 Gate；
- Lifecycle Query 投影 RLS 或上游返工。

### Out of Scope

- 实现产品代码或测试资产；
- 新增 Requirement、Design、Plan 或 Release 决策；
- 强制固定测试数量、覆盖率、自动化比例或特定工具；
- 把测试环境部署自动视为 RLS；
- 把 Artifact ready 解释为产品 pass 或允许交付；
- 自动安装测试依赖；
- 自动调用上游/下游 Skill；
- 保存不必要生产数据、Secret 或隐藏推理。

## 4. Decomposition Decision

| Question | Decision |
|---|---|
| 是否独立 Skill | 是；VFY 拥有独立 Target/Method/Conclusion/Return/Gate Authority |
| 是否按 unit/e2e/security 拆 Skill | 否；这些是目标、范围或方法细节，不是生命周期阶段 |
| 是否按四种 Method Type 拆 Skill | 否；统一 Method Contract 需要跨方法聚合同一 Target Conclusion |
| 执行器 | 内部 Method Executor；稳定命令/Evidence 能力可复用共享 execution 包 |
| QA/Test 是否独立 Authority | 否；Method Result 与 VFY Artifact 是唯一权威记录 |

## 5. Trigger 与 Interface

只接受显式调用，进入 Exclusive Execution。

### Commands

| Command | Writes | Behavior |
|---|---:|---|
| `auto` | conditional | 根据 Scope、已有 VFY、pending Method 和请求意图选择 create/run/revise/check |
| `create` | yes | 创建 VFY Contract，并执行所有当前可执行 Method |
| `run` | yes | 执行或记录现有 open VFY 中选定 Method |
| `revise` | yes | 上游/Control Input/Method Contract 改变后修订 |
| `check` | no | 严格只读检查 Scope、Subject、Method、Conclusion、Return 和 Gate |
| `help / version / commands / examples` | no | 元命令 |

### Inputs 与参数

```text
--input / -i <exact scope/subject/control reference>  # 可重复
--reference / -r <VFY-...@N>
--method / -m <VFM-NNN>                               # 可重复，仅 run
```

分类：

- REQ/DSN/PLN：Scope Source；
- frozen completed IMP Revision 或 `#RES-*`：Subject；
- frozen VFY Return、return_req/return_dsn/return_imp RLS Issue：Control Input；
- Evidence Source：准确 Artifact/Item 或 immutable Locator；
- 不能按标题或最新 Revision猜测。

### 裸调用与 `auto`

1. 解析唯一完整 Delivery Scope；
2. PLN required 时展开全部 IMP/VFY Work Item 和依赖链；
3. 确认全部 required IMP WI 有 Current completed Claim、frozen Revision 和唯一终端 Result；
4. 查找 matching VFY：不存在 → create；唯一 open 且有 pending Method → run；上游变化/返工 → revise；唯一 frozen 且无变化 → check；
5. 多个完整 Scope 或 Subject 候选由用户选择；
6. 自动执行安全、确定、无需新增权限的方法；
7. 需要人工体验、业务 Validation、受限环境或额外权限时只请求当前最小 Method 决策/执行；
8. 产品 fail 形成准确 Return，不调用上游 Skill。

## 6. 决策所有权

模型可以自动决定：

- 由 VFY Objective / AC / Goal 和上游 VFP/VFM/VPC/VEC 唯一导出的 Method；
- Method Type 与 Execution Mode 的确定性分类；
- 项目已有工具中唯一可执行的命令；
- 结果聚合和 Return Phase 的规则化建议。

用户或权威责任人决定：

- 主观 UX/业务预期用途；
- 多种方法在成本/风险上无确定最优项；
- 使用受限环境、敏感数据或外部权限；
- Exception、Waiver、风险接受；
- 产品失败是否需要改变 Requirement/Design，而非仅实现修正。

`decision_policy=model` 不允许伪造人工 Method Evidence、接受风险或降低 Pass Criteria；`experiment` 必须先冻结候选、指标、Subject、数据和停止条件。

## 7. Runtime Architecture

计划结构：

```text
skills/sdlc-500-vfy/
├── SKILL.md
├── references/{contract.md,interface.json,source-lock.json}
├── assets/vfy-template.md
├── scripts/
│   ├── vfy_common.py
│   ├── vfy_scope.py
│   ├── vfy_targets.py
│   ├── vfy_methods.py
│   ├── vfy_executor.py
│   ├── vfy_results.py
│   ├── vfy_builder.py
│   ├── vfy_verifier.py
│   ├── vfy_handler.py
│   └── runtime.py
└── agents/openai.yaml
```

内部 Strategy：

```text
inspection
analysis
demonstration
test
```

它们共享同一 Method 数据模型和 Result Contract，不拥有 Artifact Authority。Command Runner / Evidence Capture 优先复用已稳定的共享 execution 包；不存在稳定复用点时先保留私有实现。

## 8. Input Contract

| ID | Input | Required | Validation | Failure |
|---|---|---:|---|---|
| VFY-IN-01 | Scope Source | yes | 完整 REQ/DSN/PLN，Authority 有效 | 返回上游 |
| VFY-IN-02 | Subject Set | yes | immutable Product Result；Current terminal chain | blocked |
| VFY-IN-03 | Target Set | yes | VFO 或 AC/Goal 固定推导，无遗漏冲突 | RETURN_TO_REQ/DSN |
| VFY-IN-04 | PLN VFY WI | conditional | 全部覆盖、依赖完成 | blocked/RETURN_TO_PLAN |
| VFY-IN-05 | Method Obligations | yes | VFP/VFM/VPC/VEC/WI/Return 完整映射 | waiting_input/fail |
| VFY-IN-06 | Control Input | rework | frozen Return/RLS Issue，目标 Phase 合法 | fail closed |
| VFY-IN-07 | Environment/Data | method-specific | 当前 Method 可复核并有 Evidence | Open Item |
| VFY-IN-08 | Final Confirmation | freeze | 绑定当前 fail/pass/pending 边界 | 保持 open |

## 9. Canonical Artifact Contract

固定章节：

```text
Summary
Scope
Input and Result Set
Traceability and Coverage
VFY Methods
Method Results
VFY Conclusions
Failures and Returns
Open Items
Evidence
Supporting Artifact Manifest
Exceptions
Lifecycle Applicability
Gate
Final Confirmation
Artifact Gate Summary
```

### 固定对象

- `VIN-*`：Scope Source、Subject、Evidence Source；
- `VFM-*`：Purpose、Target、Subject、Obligation、Method Type、Disposition；
- Method Detail：Executor、Mode、Environment/Data、Procedure/Basis、Pass Criteria、Evidence Requirement；
- Method Result：实际 Subject、Result、Observed、Evidence；
- Target Conclusion：verification/validation/both 聚合；
- `CON-VER`、`CON-VAL`；
- `RET-*`：Return Phase、IMP Binding、Target/Method/Subject、Observed Gap、Required Outcome、Evidence。

Method Type 仅：inspection/analysis/demonstration/test。Disposition 使用 Lifecycle 枚举；Execution Mode 不是 Method Type。

VFY Phase Checks：`VFY-G-001` 至 `VFY-G-008`。

## 10. 产品结论与 Artifact Gate

必须严格区分：

| Dimension | Meaning |
|---|---|
| Method Result | 单一方法的产品观察结果 |
| Target Conclusion | 一个权威 Target 的符合性 |
| CON-VER / CON-VAL | 当前 Scope 的产品验证/确认结论 |
| Artifact Status/Gate | VFY 记录是否完整、准确、可信 |

产品 `fail` 可以对应 Artifact Gate `pass`，前提是 Evidence、聚合、Return 和未验证边界准确。Gate Check fail 表示 VFY Artifact 自身不合规。

失败检查点早停是唯一允许冻结 pending Method Result/Conclusion 的路径，必须逐项满足 Spec 条件；该 Revision 只能用于返工与审计，不能进入 RLS。

## 11. Method 执行和 Evidence

自动执行前必须保存/确认：

- 准确 Subject；
- Method Contract；
- Environment/Data；
- Procedure/Basis；
- Pass Criteria；
- Evidence Requirement；
- 执行身份与时间。

执行后保存：

- exit/result 分类；
- 实际 Subject 读回；
- Observed；
- 原始日志/报告 Supporting Member 或 immutable reference；
- 脱敏摘要；
- 目标与 Method 绑定。

禁止因工具不可用写 `n/a`；未执行保持 pending/Open Item 或合法 waived。

## 12. Revision 与状态

- 完整 Scope 未确定：不分配 VFY；
- Scope 已确定但 Method/环境/人工输入不全：open waiting_input；
- Artifact Contract 失败：open failed；
- 正常全部 Method/Conclusion 终结 + Gate/Confirmation：freeze；
- 合法失败早停：可 freeze fail/pending 边界；
- frozen 有新 Subject/Return/Issue：新 Revision；
- no-change：不创建空 Revision；
- run 只更新当前 materialized open Revision；
- check 绝对只读。

## 13. Lifecycle Query

扩展：

```text
Scope Source / IMP Result → VFY
VFY Return → REQ / DSN / PLN / IMP
VFY → RLS
```

Projection：

- open/pending VFY：停留 VFY；
- frozen product fail 或 unresolved Return：指向准确 Return Phase；
- frozen pass/accepted exception + RLS required：下一阶段 RLS；
- RLS n/a/waived：Scope 生命周期完成；
- early-stop frozen VFY 永不进入 RLS；
- Query 不把 Artifact ready 误作产品 pass。

## 14. 用户输出

默认显示：

- Scope、Target、Subject 数量；
- 待运行/已运行 Method；
- Verification 与 Validation 结论；
- 产品 fail、未证明范围和 Return；
- 人工 Method 的场景、Expected 和所需 Evidence；
- Artifact 是否冻结；
- 唯一下一动作。

默认不展示全部日志、内部 Digest 或完整测试矩阵。

## 15. 稳定错误

至少包含：

```text
VFY_SCOPE_REQUIRED
VFY_SCOPE_AMBIGUOUS
VFY_SUBJECT_NOT_CURRENT
VFY_DEPENDENCY_CHAIN_INVALID
VFY_TARGET_SET_INVALID
VFY_METHOD_COVERAGE_INCOMPLETE
VFY_METHOD_NOT_READY
VFY_METHOD_EXECUTION_FAILED
VFY_EVIDENCE_INSUFFICIENT
VFY_PURPOSE_MISMATCH
VFY_CONCLUSION_INCONSISTENT
VFY_RETURN_INVALID
VFY_EARLY_STOP_INVALID
VFY_FINAL_CONFIRMATION_STALE
VFY_RLS_NOT_ALLOWED
```

## 16. Source Lock 与 Runtime Independence

计划锁定：

- 5 Shared Runtime Contract；
- 已批准的 Claim/Resource/Execution Contract；
- Core、Artifact Store、CTX、REQ、DSN、PLN、IMP、VFY、RLS；
- 最终数量在依赖 Contract 固定后冻结。

VFY Artifact Evaluation Contract Set 只包含 Core、Artifact Store、VFY 和明确注册的执行 Evidence Contract；上游 Spec 用于输入解析。

删除 `docs/**` 后，Target/Method 生成、run、Result、Return、Gate 和 Lifecycle Query 必须执行。

## 17. Definition of Done

- Target/Method/Subject/Obligation 模型闭合；
- 产品结论与 Artifact Gate 分离；
- 人工/自动方法和 Evidence 边界明确；
- 失败早停和 Return 规则可确定实现；
- 不拆 QA/Test 兄弟 Skill；
- Lifecycle Query 能准确进入 RLS 或返工；
- Eval 可判定全部关键行为；
- 阻塞设计 Open Item 为零。
