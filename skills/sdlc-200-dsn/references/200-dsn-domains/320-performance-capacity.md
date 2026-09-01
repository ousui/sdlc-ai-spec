---
title: "性能与容量 Performance and Capacity"
status: stable
version: "1.1"
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 性能与容量 Performance and Capacity

文件名：`320-performance-capacity.md`

边界：

- 负责将已有性能和容量目标转换为可实施的设计响应；
- 业务或用户可感知目标必须来自 REQ；
- 资源规格及运行配置由 `Deployment and Configuration` 承载；
- 指标采集和告警由 `Observability and Operability` 承载；
- 性能测试执行由 VFY 承载；
- 过载阈值和服务行为由本 Domain 承载，故障恢复机制引用 `Reliability and Recovery`。

适用性：

- 改变关键路径、外部依赖、查询、缓存、并发、数据量或资源消耗时，先判断是否超出现有基线适用范围或产生实质工作负载、资源包络或质量目标偏差；存在独立设计义务时才为 `required`；
- 存在明确 SLA、SLO、吞吐量、延迟或容量要求，且当前变化需要设计响应时，为 `required`；
- 现有性能基线完整覆盖，且没有实质工作负载、资源包络或质量目标偏差时，可以引用准确 Baseline 判定为 `n/a`；
- 不存在有意义的性能或容量影响时，可以为 `n/a`；
- 明显存在性能影响但缺少目标值时，不能标记为 `n/a`，必须返回 REQ 补充或进入 `waiting_input`；
- 紧急而经授权跳过性能设计时必须使用 `waived`。

固定专属模板：

```markdown
## 设计结果 Design Result

### 工作负载 Workload Profile

| ID | 操作或路径 Operation or Path | 平均负载 Average Load | 峰值负载 Peak Load | 并发 Concurrency | 数据量 Data Volume | 增长依据 Growth Basis | Source or Evidence |
|---|---|---|---|---|---|---|---|
| WRK-001 | | | | | | | |

### 性能目标 Performance Targets

| ID | 指标 Metric | 范围 Scope | 统计口径 Aggregation | 目标 Target | 条件或窗口 Condition or Window | 依据类型 Basis Type | Requirement or Evidence |
|---|---|---|---|---|---|---|---|
| PRF-001 | | | | | | requirement | |

### 容量模型 Capacity Model

| 维度或资源 Dimension or Resource | 当前基线 Current Baseline | 计划容量 Planned Capacity | 峰值 Peak | 余量 Headroom | 限制 Limit | 计算或 Evidence Calculation or Evidence |
|---|---|---|---|---|---|---|
| | | | | | | |

### 资源预算与瓶颈 Resource Budgets and Bottlenecks

| 路径或组件 Path or Component | 资源或指标 Resource or Metric | 预算或限制 Budget or Limit | 预计使用 Expected Usage | 潜在瓶颈 Potential Bottleneck | 设计响应 Design Response |
|---|---|---|---|---|---|
| | | | | | |

### 扩展与优化 Scaling and Optimization

| 触发条件 Trigger | 策略 Strategy | 影响对象 Affected Object | 预期效果 Expected Effect | Decision 引用 Decision Reference | 代价或限制 Cost or Limitation |
|---|---|---|---|---|---|
| | | | | | |

### 过载与降级 Overload and Degradation

| 条件或阈值 Condition or Threshold | 发现方式 Detection | 行为 Behavior | 影响范围 Impact Scope | 恢复条件 Recovery Condition | Reliability 引用 Reliability Reference |
|---|---|---|---|---|---|
| | | | | | |
```

规则：

- 所有数值必须包含单位、统计口径和来源；
- `Basis Type` 使用 `requirement`、`baseline` 或 `estimate`；
- `requirement` 必须引用 REQ，`baseline` 必须引用可复现 Evidence；
- `estimate` 必须记录计算方法、输入来源和不确定性，不得制造虚假精度；
- 不得默认使用任意响应时间、百分位、吞吐量、并发量、容量或余量；
- 同一指标必须明确测量范围、统计口径以及适用条件或时间窗口；
- 性能或存储技术选型必须引用主文件中的 Design Decision；
- 共享或稳定 Cache Contract 的 Key、TTL 和一致性引用 `Data Design`；局部缓存不因此强制创建 Data Domain，运行资源和配置引用 `Deployment and Configuration`；
- 过载和降级行为必须与 `Reliability and Recovery` 一致；
- 监控数据、压测报告和容量报表可以作为 Supporting Artifact；
- VFY Points 必须覆盖目标工作负载、性能指标、容量限制和降级行为。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-320-001 | 工作负载和性能目标具有来源、指标、单位、口径与窗口，未知值未被编造 | pending |  |
| DSN-DG-320-002 | 容量、余量、资源和瓶颈具有计算或 Evidence，估算不含虚假精度 | pending |  |
| DSN-DG-320-003 | 扩展、优化、过载、降级与恢复策略可追踪，并由 VFY Points 覆盖 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
