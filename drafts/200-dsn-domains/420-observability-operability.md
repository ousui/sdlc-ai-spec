---
title: "可观测性与可运维性 Observability and Operability"
status: draft
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 可观测性与可运维性 Observability and Operability

文件名：`420-observability-operability.md`

边界：

- 负责系统应暴露的运行信号、诊断上下文、健康状态、告警和受控运行操作；
- Performance、Reliability 和 Security 定义需要满足的目标与事件；
- 本 Domain 定义通过什么信号发现、关联和诊断；
- Deployment Domain 负责启用相关运行配置；
- VFY 验证信号、告警和运行操作；
- RLS 只使用当前发版所需的健康、就绪或目标确认；Dashboard、Alert 和 Runbook 的长期使用属于项目持续运行活动；
- 本 Domain 设计 Operability，不执行长期 Operations 活动。

适用性：

- 需要独立设计新的 Metric、Log 语义、Trace、Event、Alert、Health Check、Runbook 要求或运行操作时，通常为 `required`；
- 现有日志和运行规范完整覆盖且当前变化没有新增或改变相关义务时，可以引用准确 Baseline 判定为 `n/a`；
- 没有新增或改变任何诊断、告警、健康检查或运行操作时，可以为 `n/a`；
- 实际存在需要但经授权决定跳过时，必须使用 `waived`；
- Domain 为 `required` 不表示必须引入新的日志、指标、追踪、检索或告警平台；
- 只有现有能力无法满足已确认目标时，才能提出新技术方案并记录为 Design Decision；
- 缺少必要阈值、语义或责任信息时必须进入 `waiting_input`，不得补造。

固定专属模板：

```markdown
## 设计结果 Design Result

### 运行目标 Operational Objectives

| ID | 关键能力或场景 Critical Capability or Scenario | 可观察目标 Observable Objective | Requirement or Domain Reference | 使用方 Consumer | 预期动作 Expected Action |
|---|---|---|---|---|---|
| OPR-001 | | | | | |

### 信号清单 Signal Inventory

| ID | 类型 Type | 来源 Source | 语义 Semantics | 单位或级别 Unit or Level | 维度或上下文 Dimensions or Context | 敏感性引用 Sensitivity Reference | 用途 Purpose |
|---|---|---|---|---|---|---|---|
| SIG-001 | log | | | N/A | | | |

### 关联与诊断 Correlation and Diagnostics

| 上下文 Context | 标识 Identifier | 生成来源 Creation Source | 传播范围 Propagation Scope | 敏感性或保留 Sensitivity or Retention | 诊断用途 Diagnostic Usage |
|---|---|---|---|---|---|
| | | | | | |

### 健康与就绪 Health and Readiness

| Component or Deployment Unit | 检查类型 Check Type | Dependencies | 通过条件 Pass Condition | 失败含义 Failure Meaning | Deployment or Reliability Reference |
|---|---|---|---|---|---|
| | | | | | |

### 告警与响应 Alerts and Response

| ID | Signal | 条件与窗口 Condition and Window | 级别 Severity | 接收方或责任方 Recipient or Owner | 预期动作 Expected Action | Target or Evidence Reference |
|---|---|---|---|---|---|---|
| ALT-001 | SIG-001 | | | | | |

### 运行操作 Operational Actions

| ID | 操作 Action | 触发 Trigger | 权限 Permission | 输入 Input | 幂等 Idempotency | 成功条件 Success Condition | 失败结果 Failure Result | 审计 Audit |
|---|---|---|---|---|---|---|---|---|
| OPA-001 | | | | | | | | |

### Runbook 要求 Runbook Requirements

| 场景 Scenario | 触发或 Alert Trigger or Alert | 处理目标 Objective | 必要约束 Required Constraints | 升级条件 Escalation Condition | 完成条件 Completion Condition | Host |
|---|---|---|---|---|---|---|
| | | | | | | |
```

规则：

- Signal Type 使用 `metric`、`log`、`trace` 或 `event`；
- 每个 Signal 必须关联明确运行目标和用途，不得因为日志或指标越多越好而无目的采集；
- Metric 必须定义名称、单位、语义、维度和来源，不适用字段填写 `N/A` 和原因；
- Log、Trace 和 Event 必须定义必要上下文，并处理敏感信息、保留和高基数风险；
- Alert 条件、窗口和级别必须引用 Performance、Reliability、Security、Requirement 或 Evidence，不得猜测；
- 每个 Alert 必须对应接收方和可执行动作，不能只负责通知；
- Operational Action 必须定义权限、输入、幂等性、成功条件、失败结果和审计要求；
- 现有 Logger、Metric、Trace、Alert 和运行平台优先通过可验证项目基线或 Evidence 引用；
- Dashboard、Alert Rule、Telemetry Config 和 Runbook 可以作为 Supporting Artifact；
- 核心 Spec 不强制使用 ELK 或任何特定日志、指标、追踪和告警平台；
- 本 Domain 不记录实际告警、长期运行操作结果或运行期 Evidence；
- VFY Points 必须覆盖信号语义、关联、健康检查、告警和受控运行操作。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-420-001 | 可观测与运维目标、Signal 的语义、来源、用途、上下文和敏感性处理完整 | pending |  |
| DSN-DG-420-002 | 健康、就绪、Alert、响应和 Operational Action 具有确定条件、责任和结果 | pending |  |
| DSN-DG-420-003 | Runbook 与 VFY Points 完整，且未因适用而无依据引入新平台 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
