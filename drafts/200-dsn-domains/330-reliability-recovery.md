---
title: "可靠性与恢复 Reliability and Recovery"
status: draft
scope: DSN Domain 固定模板、规则与专属 Gate
parent: ../200-dsn-spec.md
---

# 可靠性与恢复 Reliability and Recovery

文件名：`330-reliability-recovery.md`

边界：

- 负责故障发生时限制影响、维持关键能力并恢复正常状态；
- 高负载阈值和性能退化由 `Performance and Capacity` 承载；
- 恶意攻击造成的故障由 Security 承载；
- Interface Domain 记录具体超时、重试和幂等 Contract；
- Deployment Domain 落实冗余、备份和运行拓扑；
- `Observability and Operability` 负责发现故障和触发告警；
- 项目既有运行机制负责日常 Runbook 和人工操作；RLS 只执行当前发版明确需要的恢复或确认动作；
- VFY 负责故障注入、恢复及数据一致性验证。

适用性：

- 改变关键能力、故障语义、恢复边界、数据丢失风险，或现有机制不能覆盖新的状态、外部依赖或异步行为时，存在独立设计义务则为 `required`；
- 存在服务可用性 Availability、连续性、RTO 或 RPO 要求，且尚无准确 Host 完整承载设计响应时，为 `required`；
- 现有可靠性机制完整覆盖且行为没有变化时，可以为 `embedded`；
- 不存在有意义的故障或恢复影响时，可以为 `n/a`；
- 仅迁移过程的停止、恢复或降级由 `Compatibility and Migration` 承载；存在迁移可靠性义务且被其完整覆盖时，本 Domain 为 `embedded`，完全不存在稳态或迁移可靠性义务时才为 `n/a`；只有稳态关键能力、故障语义或恢复边界也发生变化时才独立设计 Reliability；
- 缺少必要恢复目标时不得编造，必须返回 REQ 补充或进入 `waiting_input`；
- 紧急而经授权跳过可靠性设计时必须使用 `waived`。

固定专属模板：

```markdown
## 设计结果 Design Result

### 关键能力与依赖 Critical Capabilities and Dependencies

| ID | 关键能力 Critical Capability | 承载对象 Host | 关键依赖 Critical Dependencies | 不可用影响 Unavailability Impact | Requirement or Target Reference |
|---|---|---|---|---|---|
| CAP-001 | | | | | |

### 故障模式与影响 Failure Modes and Impact

| ID | 来源或触发 Source or Trigger | 可观察表现 Observable Symptom | 影响范围 Impact Scope | 发现方式引用 Detection Reference | Control or Residual Risk Reference |
|---|---|---|---|---|---|
| FLT-001 | | | | | RLC-001 |

### 可靠性控制 Reliability Controls

| ID | 类型 Type | 适用条件 Applicable Condition | 行为 Behavior | 限制 Limit | 承载位置 Host | Decision 引用 Decision Reference |
|---|---|---|---|---|---|---|
| RLC-001 | retry | | | | | |

### 恢复目标 Recovery Objectives

| 范围 Scope | 可用性目标 Availability Target | 恢复时间目标 Recovery Time Objective, RTO | 恢复点目标 Recovery Point Objective, RPO | Requirement or Evidence | 假设 Assumptions |
|---|---|---|---|---|---|
| | | | | | |

### 恢复流程 Recovery Flow

| Failure Mode | 发现或触发 Detection or Trigger | 限制影响 Containment | 恢复行为 Recovery Action | 责任方或自动化 Owner or Automation | 完成条件 Completion Condition |
|---|---|---|---|---|---|
| FLT-001 | | | | | |

### 数据与状态恢复 Data and State Recovery

| Data or State | 恢复来源 Recovery Source | 允许损失 Allowed Loss | 恢复与一致性检查 Restoration and Consistency Check | Data or State Reference |
|---|---|---|---|---|
| | | | | |

### 降级与恢复正常 Degradation and Normalization

| 降级状态 Degraded State | 进入条件 Entry Condition | 保留与不可用能力 Available and Unavailable Capabilities | 退出条件 Exit Condition | 校正行为 Reconciliation | Verification |
|---|---|---|---|---|---|
| | | | | | |
```

规则：

- RTO 表示允许从故障发生到恢复目标能力的最长时间；
- RPO 表示恢复后允许丢失数据或状态的最大时间范围；
- 可用性、RTO 和 RPO 必须包含单位、适用范围和 Requirement 或 Evidence，不适用时填写 `N/A` 和原因；
- 每个适用 Failure Mode 必须在 `Control or Residual Risk Reference` 中引用可靠性 Control，或直接引用父 DSN 的 Decision / Exception；不新增平行风险表；
- 重试必须明确限制和最终失败行为，不得设计无限重试；
- 恢复流程必须具有确定的启动条件、责任方或自动化方式以及完成条件；
- 持久数据恢复引用 `Data Design`，业务状态恢复引用 `Workflow and State`，并明确一致性检查；
- 降级模式必须明确保留能力、不可用能力、退出条件和恢复后校正行为；
- 本 Domain 只定义恢复设计，不在此展开长期 Runbook 的逐步操作；
- VFY Points 必须覆盖适用的 Failure Mode、Control、恢复目标和数据一致性结果。

专属 Gate：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-330-002 | 关键能力、承载对象和依赖明确 | pending |  |
| DSN-DG-330-003 | 适用的 Failure Mode 和影响范围已识别 | pending |  |
| DSN-DG-330-004 | 每个 Failure Mode 具有 Control 或父 Decision / Exception 引用 | pending |  |
| DSN-DG-330-005 | 可用性、RTO 和 RPO 具有准确来源 | pending |  |
| DSN-DG-330-006 | 恢复流程、责任方和完成条件明确 | pending |  |
| DSN-DG-330-007 | 数据或状态恢复及一致性检查明确 | pending |  |
| DSN-DG-330-008 | 降级和恢复正常条件已按适用性处理 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
