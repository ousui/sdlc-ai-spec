---
title: "安全、隐私与合规 Security, Privacy and Compliance"
status: draft
scope: DSN Domain 适用性、固定模板与父 Gate 子检查
parent: ../200-dsn-spec.md
---

# 安全、隐私与合规 Security, Privacy and Compliance

文件名：`310-security-privacy-compliance.md`

边界：

- 负责设计阶段的保护要求和控制设计，不代替安全审计或渗透测试；
- Interface Domain 记录具体 Contract 如何应用认证和授权；
- Data Domain 记录隐私、保留和删除要求如何落实到数据生命周期；
- Deployment Domain 记录网络、凭据、Secret 和运行配置；
- `Observability and Operability` 记录安全日志、告警和响应信号；
- VFY 负责执行安全验证并生成 Evidence；
- 恶意攻击导致的可用性风险属于 Security，普通故障恢复属于 `Reliability and Recovery`；
- 核心 Spec 不硬编码具体法律、标准版本或司法辖区。

适用性：

- Security、Privacy 和 Compliance 按本 Spec 分别判断 Disposition；
- 子领域先分别判定，再按固定聚合规则形成 Domain Disposition；
- 涉及身份、权限、外部暴露、敏感操作、Secret、信任边界或滥用风险时，Security 通常为 `required`；
- 新增或改变个人数据、敏感数据的收集、使用、共享或生命周期时，Privacy 通常为 `required`；
- Requirement 或可验证项目基线指定法律、合同、行业或组织义务时，Compliance 通常为 `required`；
- 已有控制完整覆盖且当前变化没有新增或改变相关义务时，可以引用准确 Baseline 判定相应子领域为 `n/a`；
- 紧急并不代表 `n/a`，适用但经授权跳过时必须使用 `waived`。

聚合规则：

1. 任一子领域为 `pending` 时，本 Domain 为 `pending`；
2. 否则任一子领域为 `required` 时，本 Domain 为 `required`；
3. 否则任一子领域为 `waived` 时，本 Domain 为 `waived`；
4. 仅当全部子领域为 `n/a` 时，本 Domain 才为 `n/a`。

子领域 Waiver 即使未成为聚合后的 Domain Disposition，也必须独立关联并传播到父 DSN Exceptions。只有不存在 `fail`、`pending` 且其他必要 Check 均已关闭时，父 DSN 才按 Core 由该未关闭 Exception 派生 `ready_with_exception`。

三个子领域的处置始终记录在父 DSN 主文件的固定 Composite Domain Subdomain Applicability 表；顶层 Domain 为 `required` 时才创建本 Domain 子文件承载详细设计。

固定专属模板：

```markdown
## 设计结果 Design Result

### 资产与信任边界 Assets and Trust Boundaries

| ID | 资产、参与方或边界 Asset, Actor or Boundary | 类型 Type | 保护目标 Protection Objective | 责任方 Owner | 暴露或变化 Exposure or Change |
|---|---|---|---|---|---|
| AST-001 | | asset | | | |

### 威胁与滥用 Threats and Abuse Cases

| ID | 影响对象 Affected Object | 威胁或滥用场景 Threat or Abuse Case | 前置条件 Preconditions | 影响 Impact | Control 引用 Control Reference |
|---|---|---|---|---|---|
| THR-001 | AST-001 | | | | CTL-001 |

### 安全控制 Security Controls

| ID | 类型 Type | 控制目标 Control Objective | 设计响应 Design Response | 承载位置 Host | 失败行为 Failure Behavior |
|---|---|---|---|---|---|
| CTL-001 | preventive | | | | |

### 身份与访问 Identity and Access

| 身份或主体 Identity or Principal | 资源或操作 Resource or Action | 认证 Authentication | 授权规则 Authorization Rule | 拒绝行为 Denial Behavior | Security Control |
|---|---|---|---|---|---|
| | | | | | CTL-001 |

### 隐私处理 Privacy Processing

| Data or Contract Reference | 处理目的 Purpose | 收集或来源 Collection or Source | 使用或共享 Use or Sharing | 最小化措施 Minimization | Lifecycle 引用 Lifecycle Reference | Requirement 引用 Requirement Reference |
|---|---|---|---|---|---|---|
| DAT-001 | | | | | | |

### 合规映射 Compliance Mapping

| ID | 义务来源 Obligation Source | 适用范围 Scope | 设计或 Control 引用 Design or Control Reference | 预期 Evidence | 确认角色 Confirming Role |
|---|---|---|---|---|---|
| OBL-001 | | | | | |

### 剩余风险 Residual Risks

| ID | 风险场景 Risk Scenario | 已有控制 Existing Controls | 剩余影响 Residual Impact | Decision 或 Exception | 责任方 Owner |
|---|---|---|---|---|---|
| RSK-001 | | | | | |
```

规则：

- Security、Privacy 与 Compliance 的 Disposition、Basis、原因和 Exception 只记录在父 DSN 主文件，不在本文件复制；
- 执行主体可以辅助识别威胁、隐私影响和合规候选项；法律适用性、Waiver 和剩余风险只能由授权人工角色确认；
- 不得为了填充模板虚构资产、威胁、法律、标准版本、司法辖区或合规义务；
- 每个适用威胁必须关联有效 Control，或登记为剩余风险并关联 Decision 或 Exception；
- 身份与访问必须明确授权规则和拒绝行为，不得只写认证方式；
- 设计文件不得记录真实 Secret、Token、私钥或密码；
- 持久化或共享数据的 Privacy Processing 必须引用 Data Design；仅存在瞬时接口数据时可以引用 Interface Contract 或 Requirement，不得因此强制创建 Data Domain；
- Compliance Mapping 必须准确记录义务来源、适用范围、设计响应和预期 Evidence；
- Security Event、日志和响应信号引用 `Observability and Operability`，不在本 Domain 重复运行方案；
- 完整 Threat Model、风险评估和合规矩阵可以作为 Supporting Artifact；
- VFY Points 必须覆盖适用的威胁、控制、访问、隐私和合规结果。

父 Gate 子检查：

以下检查只在父 DSN Artifact Gate 中按 Check ID 登记一次，不写入 Domain 子文件。

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-310-001 | 三个子领域的 Disposition、依据、N/A 原因和 Exception 完整一致 | pending |  |
| DSN-DG-310-002 | 适用的资产、保护目标、信任边界、威胁、访问与 Control 完整，真实 Secret 未写入 | pending |  |
| DSN-DG-310-003 | 适用的隐私目的、最小化、Lifecycle 和合规义务映射准确 | pending |  |
| DSN-DG-310-004 | 剩余风险具有 Decision 或 Exception、责任方和 VFY Points | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
