---
title: "部署与配置 Deployment and Configuration"
status: stable
version: "1.0"
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 部署与配置 Deployment and Configuration

文件名：`410-deployment-configuration.md`

边界：

- 负责将逻辑设计映射为部署单元、运行拓扑、环境和配置 Contract；
- System Architecture 定义逻辑结构，本 Domain 定义其运行映射；
- Performance 定义资源目标，本 Domain 落实资源规格；
- Reliability 定义冗余与恢复目标，本 Domain 落实实例和拓扑；
- Security 定义保护要求，本 Domain 落实网络、Secret 和权限配置；
- Compatibility 定义过渡策略，本 Domain 落实部署机制；
- RLS 执行当前发版的实际部署并确认目标状态；长期运行和 Runbook 由项目既有运行机制负责。

适用性：

- 新增或改变部署单元、环境、拓扑、配置、Secret、资源或部署策略时，通常为 `required`；
- 完全沿用现有部署能力且当前变化没有运行或配置设计义务时，可以引用准确 Baseline 判定为 `n/a`；
- 不存在任何运行或配置影响时，可以为 `n/a`；
- 发生实际发版不代表本 Domain 必须为 `required`，RLS 可以复用既有部署设计；
- 环境或配置事实不明确时必须进入 `waiting_input`，不得猜测默认值、地址或资源规格。

固定专属模板：

```markdown
## 设计结果 Design Result

### 部署单元 Deployment Units

| ID | Artifact or Unit | 版本来源 Version Source | Runtime or Host | 用途 Purpose | 变化 Change | 责任方 Owner |
|---|---|---|---|---|---|---|
| DPU-001 | | | | | new | |

### 部署定义来源 Deployment Definition Source

| Scope | 定义方式 Definition Mode | 格式 Format | 原生 Artifact Native Artifact | Inline Host | Version |
|---|---|---|---|---|---|
| DPU-001 | inline | Markdown | N/A | Runtime Topology | |

### 环境矩阵 Environment Matrix

| 环境 Environment | 用途 Purpose | Topology or Reference | 配置来源 Configuration Source | 外部依赖 External Dependencies | 差异或约束 Differences or Constraints |
|---|---|---|---|---|---|
| | | | | | |

### 运行拓扑 Runtime Topology

| Deployment Unit | Environment or Scope | 实例与放置 Instances and Placement | 网络与暴露 Network and Exposure | Runtime Dependencies | Resource Target Reference | Reliability Reference |
|---|---|---|---|---|---|---|
| DPU-001 | | | | | | |

### 配置 Contract Configuration Contract

| ID | Key or Name | 类型 Type | 作用域 Scope | 必填 Required | 默认值 Default | 来源与优先级 Source and Precedence | 生效方式 Apply Mode | 敏感性引用 Sensitivity Reference |
|---|---|---|---|---|---|---|---|---|
| CFG-001 | | | | | | | startup | |

### Secret 管理 Secret Management

| Secret Reference | 用途 Purpose | 存储或提供方 Store or Provider | 消费方 Consumer | 提供与轮换 Provisioning and Rotation | Security Reference |
|---|---|---|---|---|---|
| | | | | | |

### 部署策略 Deployment Strategy

| Deployment Unit | 策略 Strategy | 顺序或依赖 Order or Dependency | 就绪或成功条件 Readiness or Success Condition | 流量或切换 Traffic or Cutover | 失败处理 Failure Handling | Compatibility Reference |
|---|---|---|---|---|---|---|
| DPU-001 | | | | | | |

### 初始化与迁移 Initialization and Migration

| ID | 行为 Action | 触发或顺序 Trigger or Order | 幂等 Idempotency | 前置条件 Preconditions | 成功 Evidence | 失败行为 Failure Behavior | Migration Reference |
|---|---|---|---|---|---|---|---|
| INI-001 | | | | | | | |
```

规则：

- `Change` 使用 `new`、`changed`、`reused` 或 `removed`；
- `Definition Mode` 使用 `native` 或 `inline`；
- 使用 `native` 时，项目已有的部署、配置或基础设施定义文件可以作为细节来源，Markdown 不重复抄写字段；
- 核心 Spec 不强制使用容器、云平台或特定部署工具；
- Configuration 必须明确类型、作用域、必填性、默认值、来源、优先级和生效方式；
- `Apply Mode` 使用 `startup`、`dynamic`、`restart` 或 `other`；
- 不得记录真实 Secret、Token、密码、私钥或生产凭据；
- 默认值、资源规格和环境差异必须引用 Requirement、Decision、可验证项目基线或 Evidence，不得猜测；
- Runtime Topology 必须与 Performance、Reliability 和 Security Design 一致；
- Deployment Strategy 必须与 Compatibility Design 一致，并具有确定的就绪、成功和失败行为；
- Initialization and Migration 必须说明顺序、幂等、成功 Evidence 和失败行为；
- 原生部署文件属于父 DSN Artifact Set，其语义变化触发父 DSN Revision 变化；
- 本 Domain 不记录实际部署日志、执行结果或长期 Runbook；
- VFY Points 必须覆盖部署单元、配置解析、就绪条件、迁移和失败行为。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-410-001 | 部署单元、版本来源、环境、Runtime、责任方和定义来源完整 | pending |  |
| DSN-DG-410-002 | 拓扑、依赖、配置和 Secret 管理完整一致，不含猜测值或真实凭据 | pending |  |
| DSN-DG-410-003 | 部署、初始化与迁移的顺序、幂等、成功和失败行为明确，并由 VFY Points 覆盖 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
