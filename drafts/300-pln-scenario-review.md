---
title: PLN Representative Scenario Review
status: working-review
scope: 固定文案、单服务 API 与跨组件紧急恢复的 Work Item Contract 回放
---

# PLN 代表场景回放

> 本文件是规划期 Review 快照，不是 Lifecycle Artifact 或正式模板。以下 ID 是固定测试夹具，只用于验证相同 Contract 在不同事实下能否得到稳定结果。

## Review 目标

本次只检查：

- 什么时候不应创建 PLN Artifact；
- 10 个 Work Item 字段是否足以形成完整交付执行计划；
- Source、Constraint、Dependency、Execution Scope 和 Evidence 是否可以闭合；
- Profile 是否错误代替了事实判断；
- 是否需要新增字段、状态或子文件。

## 场景 A：固定静态文案

### 精确假设

- REQ 为 `REQ-20260824090000-01@1`；
- REQ 的 In Scope 使用固定 `Direct IMP Scope` 行登记唯一 canonical Scope（包含 `resource:content-repo`），`R-001` 给出准确文案，`AC-001` 给出准确预期文本；执行时能够绑定首次修改前的不可变 Baseline；
- 不改变布局、交互、程序化语义、国际化、接口、数据或质量属性；
- 只有一个完整直接 Input、一个原子修改结果，不存在拆分、依赖、冲突协调或计划选择；
- 使用既有实现、验证和交付基线。

### Disposition 结果

| Phase | Disposition | Basis |
|---|---|---|
| DSN | `n/a` | 没有设计选择、结构变化或质量影响 |
| PLN | `n/a` | 上游已准确确定单一执行结果，不存在独立规划义务 |
| IMP | `required` | 必须修改目标内容 |
| VFY | `required` | 必须确认实际结果符合 `AC-001` |
| RLS | `required` | 发生实际发版并需要确认目标状态 |

### 结论

- 不创建空 DSN 或 PLN Artifact；
- IMP 绑定最近可用的 `REQ-20260824090000-01@1`，并保留 DSN、PLN 的 `n/a` 解析链；
- VFY 和 RLS 仍分别形成 Artifact，不能因为变更简单而消失；
- `lite` 只能是 Profile 建议，不是跳过 PLN 的依据。

## 场景 B：既有服务新增 JSON API

### 精确假设

- REQ 为 `REQ-20260824100000-01@1`；
- DSN 为 `DSN-20260824110000-01@1`，完整覆盖对应 REQ，因此 PLN 不重复把 REQ 作为直接 Input；
- 回放使用的 Plan 为 `PLN-20260824120000-01@1`；
- DSN 包含 `CHG-001` 领域行为、`CHG-002` API Adapter、`DEC-001` 既有认证与错误 Contract、VFY Contract 以及既有部署和运行基线；
- API 与领域行为是两个可独立确认的变化范围，存在实现依赖；
- 不新增部署平台或可观测组件。

### Applicability

| Phase | Effective Disposition | Host | Basis |
|---|---|---|---|
| IMP | `required` | N/A | 两个独立实现范围 |
| VFY | `required` | N/A | 必须执行 API Contract 与业务行为验证 |
| RLS | `required` | N/A | 发生实际发版并需要确认目标版本和既有运行基线 |

PLN 为 `required`，触发依据是多个独立变化范围和明确依赖，不是 Profile。

### Work Items

| ID | Target Phase | Outcome | Execution Scope | Source References | Constraint References | Depends On | Completion Criteria | Expected Evidence | Responsible Role |
|---|---|---|---|---|---|---|---|---|---|
| WI-001 | IMP | 报价领域行为按设计产生稳定结果 | component:quote-service, module:quote-domain, resource:quote-service-repo | DSN-20260824110000-01@1#CHG-001 | DSN-20260824110000-01@1#DEC-001, REQ-20260824100000-01@1#R-002 | None | 设计规定的正常、异常和边界行为均已实现，且未改变既有无关行为 | 实现差异、构建结果和实现阶段检查记录 | Backend Developer |
| WI-002 | IMP | JSON API Adapter 按稳定 Contract 暴露报价能力 | component:quote-service, interface:/v1/quotes, module:quote-api, resource:quote-service-repo | DSN-20260824110000-01@1#CHG-002 | DSN-20260824110000-01@1#DEC-001 | WI-001 | 请求、响应、认证和错误映射均与设计 Contract 一致 | 实现差异、接口 Schema 检查和实现阶段检查记录 | API Developer |
| WI-003 | VFY | API Contract、领域行为和预期用途得到明确结论 | component:quote-service, environment:verification, interface:/v1/quotes | DSN-20260824110000-01@1#VEC-001, DSN-20260824110000-01@1#VFM-001, DSN-20260824110000-01@1#VFO-001, DSN-20260824110000-01@1#VPC-001 | None | WI-001, WI-002 | 全部 Pass Criteria 得到 pass 或形成有效 Exception，Verification 与 Validation 均有结论 | VFY 结果、执行记录和 Evidence Contract 指定证据 | Verification Owner |
| WI-004 | RLS | 已验证版本按既有基线完成发版并进入既有运行承载 | component:quote-service, environment:production | DSN-20260824110000-01@1#CHG-001, DSN-20260824110000-01@1#CHG-002, DSN-20260824110000-01@1#DDR-410-001, DSN-20260824110000-01@1#DDR-420-001 | DSN-20260824110000-01@1#DEC-001 | WI-003 | 目标版本、配置和既有运行基线均已确认生效 | Release Record、版本标识和目标确认记录 | Release Owner |

### 回放结论

- 所有 Change Item、VFY Contract 和运行承载都有唯一可追踪位置；
- `Outcome`、`Completion Criteria` 和 `Expected Evidence` 含义不同，没有重复字段；
- `Constraint References` 成功承载认证、错误 Contract 和 Requirement 边界，不能删除；
- `WI-002` 直接继承 `WI-001` 的同资源 Result，不产生两个无法组合的仓库快照；
- 不需要增加优先级、工时、实时状态或外部编号。

## 场景 C：跨组件紧急恢复

### 精确假设

- REQ 为 `REQ-20260824120000-01@1`，Profile 为 `hotfix`；
- 生产中 Gateway 与 Service 的兼容行为不一致，导致有效请求失败；
- Gateway DSN 为 `DSN-20260824130000-01@1`，Service DSN 为 `DSN-20260824130000-02@1`；
- 两个 DSN 都完整纳入本次 Delivery Scope，并共享准确兼容 Decision；
- Gateway DSN 的 VFY Contract 汇总跨组件目标，并准确引用 Service DSN 的接口 VFY Point；
- 两个 DSN 中 Deployment 与 Observability Domain 均为 `required`，表中引用的 VFY Point 已在对应 Domain Member 中定义；
- 两项实现可以独立进行，集成 VFY 必须等待两项实现；
- Gateway 与 Service 分别映射到 `gateway-repo` 和 `service-repo` 两个独立版本化资源；
- 交付必须先发布兼容 Service，再发布 Gateway，随后观察恢复结果；
- 不改变公开业务 Contract，不顺手重构相邻代码。

### Delivery Scope

| Source Artifact Reference | Inclusion Basis |
|---|---|
| DSN-20260824130000-01@1 | Gateway 恢复范围 |
| DSN-20260824130000-02@1 | Service 恢复范围 |

### Applicability

| Phase | Effective Disposition | Host | Basis |
|---|---|---|---|
| IMP | `required` | N/A | 两个独立组件均需修改 |
| VFY | `required` | N/A | 必须验证跨组件兼容和恢复结果 |
| RLS | `required` | N/A | 存在明确发版顺序，并需要确认生产恢复和约定观察结果 |

PLN 为 `required`，同时命中多 Input 聚合、多个独立范围、依赖顺序和运行协调；`hotfix` 不改变这些事实。

### Work Items

| ID | Target Phase | Outcome | Execution Scope | Source References | Constraint References | Depends On | Completion Criteria | Expected Evidence | Responsible Role |
|---|---|---|---|---|---|---|---|---|---|
| WI-001 | IMP | Gateway 按共享兼容 Decision 处理目标请求 | component:gateway, module:request-filter, resource:gateway-repo | DSN-20260824130000-01@1#CHG-001 | DSN-20260824130000-01@1#DEC-001, REQ-20260824120000-01@1#R-002 | None | 目标兼容路径已实现，公开业务 Contract 和无关路径未改变 | Gateway 实现差异、构建结果和范围检查记录 | Gateway Developer |
| WI-002 | IMP | Service 按共享兼容 Decision 接受目标请求 | component:service, module:compatibility-handler, resource:service-repo | DSN-20260824130000-02@1#CHG-001 | DSN-20260824130000-01@1#DEC-001, REQ-20260824120000-01@1#R-002 | None | 目标兼容路径已实现，无关服务行为未改变 | Service 实现差异、构建结果和范围检查记录 | Service Developer |
| WI-003 | VFY | 两个组件组合后满足兼容 Contract 和恢复条件 | component:gateway, component:service, environment:verification, interface:gateway-service | DSN-20260824130000-01@1#VEC-001, DSN-20260824130000-01@1#VFO-001, DSN-20260824130000-01@1#VPC-001, DSN-20260824130000-02@1#VFP-230-001 | None | WI-001, WI-002 | 兼容场景、失败场景和无回归范围均得到明确结论 | 集成 VFY 结果及 Evidence Contract 指定证据 | Verification Owner |
| WI-004 | RLS | 兼容 Service 版本先进入目标环境 | component:service, environment:production | DSN-20260824130000-02@1#VFP-410-001 | DSN-20260824130000-01@1#DEC-001 | WI-003 | Service 目标版本和配置已确认生效，且仍兼容旧 Gateway | Service Release Action、版本与配置确认 | Service Release Owner |
| WI-005 | RLS | Gateway 版本在兼容 Service 就绪后进入目标环境 | component:gateway, environment:production | DSN-20260824130000-01@1#VFP-410-001 | DSN-20260824130000-01@1#DEC-001 | WI-004 | Gateway 目标版本和配置已确认生效 | Gateway Release Action、版本与配置确认 | Gateway Release Owner |
| WI-006 | RLS | 生产请求恢复并在约定观察窗口内达到目标状态 | component:gateway, component:service, environment:production, resource:request-error-metric | DSN-20260824130000-01@1#VFP-420-001, DSN-20260824130000-02@1#VFP-420-001 | REQ-20260824120000-01@1#R-001 | WI-005 | 目标请求成功率和错误指标满足 REQ，且没有新增阻塞异常 | RLS Target Confirmation、观察窗口记录和指标快照 | Release Owner |

### 依赖与冲突结果

```text
WI-001 ─┐
        ├→ WI-003 → WI-004 → WI-005 → WI-006
WI-002 ─┘
```

- `WI-001` 与 `WI-002` 使用不同版本化 Resource、没有依赖且 Scope Token 不重叠，可以成为并行候选，但 Plan 不保存 `parallel`；
- `WI-003` 明确等待两个实现结果；
- `WI-004` 与 `WI-005` 通过依赖表达发版顺序，不需要 `conflicts_with`；
- `WI-006` 是同一 RLS Artifact 的目标确认工作，不能被“紧急”省略，也不因此增加独立运行 Phase。

## Binding 与 Result 交接回放

场景 B 使用固定引用验证同一资源的执行链；十六进制值只代表测试夹具中的不可变对象 ID：

| Work Item | 准确 IMP Binding | Resource | Baseline Reference | Result Reference | 下游采用的 IMP Reference |
|---|---|---|---|---|---|
| WI-001 | PLN-20260824120000-01@1#WI-001 | quote-service-repo | vcs:quote-service-repo@1111111111111111111111111111111111111111 | vcs:quote-service-repo@2222222222222222222222222222222222222222 | IMP-20260824150000-01@1#RES-001 |
| WI-002 | PLN-20260824120000-01@1#WI-002 | quote-service-repo | vcs:quote-service-repo@2222222222222222222222222222222222222222 | vcs:quote-service-repo@3333333333333333333333333333333333333333 | IMP-20260824150000-02@1#RES-001 |

- `WI-002` 只接受当前 Plan Revision 中 `WI-001` 的 completed Attempt，并把 `IMP-20260824150000-01@1` 写入 `inputs`；
- `WI-002` 的 Baseline 等于前驱 Result，因此链尾 `IMP-20260824150000-02@1#RES-001` 唯一表示进入 VFY 的 `quote-service-repo` 结果；
- 若 `WI-001` 返工形成新 Result，原 `WI-002` 链尾立即失效，必须以新前驱 Result 重新执行后才能进入 VFY；
- 若 Plan Revision 改变，旧 Revision 的 completed Attempt 不能直接满足新 Binding。

## Contract Review 结果

| 检查项 | 结果 | 处理 |
|---|---|---|
| 10 个 Work Item 字段能否闭合三个场景 | pass | 不新增字段 |
| PLN 自身的 Applicability 是否确定 | pass | 使用固定 required、embedded、n/a、waived、pending 条件 |
| 跳过 DSN 或 PLN 后下游 Input 是否连续 | pass | 绑定最近可用上游 Revision 并保留完整处置链 |
| Execution Scope 是否可稳定比较 | pass | 固定六类 Scope Token；IMP 明确版本化 Resource 并串行化同资源结果 |
| 依赖是否采用准确 Plan Revision | pass | 当前 Plan Revision 的 Binding 与已采用 IMP Revision 同时固定 |
| Result 是否能唯一交给 VFY | pass | 同资源沿单一 Baseline→Result 链，使用链尾 Result |
| 是否需要 Work Item 实时状态 | 不需要 | 由下游执行 Artifact 承载 |
| 是否需要 parallel 或 conflicts_with | 不需要 | 由 Depends On 和 Scope Token 推导 |
| 是否需要优先级、工时和排期 | 核心不需要 | 保留为未来项目扩展候选 |
| Profile 是否决定 Work Item 数量 | 否 | 只由当前事实与 Applicability 决定 |

## 最终判断

当前 10 字段 Work Item 表可以支撑简单、常规和紧急复杂交付，不需要新增状态、覆盖矩阵、子文件或外部工具概念。
