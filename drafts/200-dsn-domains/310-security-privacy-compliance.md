---
title: "安全、隐私与合规 Security, Privacy and Compliance"
status: draft
scope: DSN Domain 固定模板、规则与专属 Gate
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

- Security、Privacy 和 Compliance 在文件内分别判断 Disposition；
- 子领域先分别判定，再按固定聚合规则形成 Domain Disposition；
- 涉及身份、权限、外部暴露、敏感操作、Secret、信任边界或滥用风险时，Security 通常为 `required`；
- 新增或改变个人数据、敏感数据的收集、使用、共享或生命周期时，Privacy 通常为 `required`；
- Requirement 或可验证项目基线指定法律、合同、行业或组织义务时，Compliance 通常为 `required`；
- 已有控制完整覆盖且可以准确引用时，可以为 `embedded`；
- 紧急并不代表 `n/a`，适用但经授权跳过时必须使用 `waived`。

聚合规则：

1. 任一子领域为 `pending` 时，本 Domain 为 `pending`；
2. 否则任一子领域为 `required` 时，本 Domain 为 `required`；
3. 否则任一子领域为 `embedded` 时，本 Domain 为 `embedded`；
4. 否则任一子领域为 `waived` 时，本 Domain 为 `waived`；
5. 仅当全部子领域为 `n/a` 时，本 Domain 才为 `n/a`。

子领域 Waiver 即使未成为聚合后的 Domain Disposition，也必须独立关联 Exception，并使父 DSN 进入 `ready_with_exception`。

每个子领域始终保存固定 Subdomain Control Record。本 Domain 为 `required` 时全部记录保存在 Domain 子文件并进入 Domain Control Input Digest；其他 Disposition 时按父 Spec 的同字段单一 DDR Block 保存在主文件。`embedded` 子领域记录 Host 与摘要，`n/a` 记录原因与 Evidence，`waived` 记录 Exception 引用。

固定专属模板：

```markdown
## 设计结果 Design Result

### 子领域控制记录 Subdomain Control Records

| Domain Spec Reference or Digest | Domain or Subdomain | Disposition | Obligation or Impact | Applicability Basis References | Baseline or Host Reference | Host Content Digest | Deviation or N/A Reason | VFY Point References | Exception References |
|---|---|---|---|---|---|---|---|---|---|
| drafts/200-dsn-domains/310-security-privacy-compliance.md@sha256:... | Security | pending | | | | | | | |
| drafts/200-dsn-domains/310-security-privacy-compliance.md@sha256:... | Privacy | pending | | | | | | | |
| drafts/200-dsn-domains/310-security-privacy-compliance.md@sha256:... | Compliance | pending | | | | | | | |

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

- 子领域 Disposition 使用统一的 `required`、`embedded`、`n/a`、`waived` 或 `pending`；
- 三行顺序固定为 Security、Privacy、Compliance；不得删除、重排或拆成多个控制表；
- `embedded` 必须准确引用已有控制，`waived` 必须引用主文件中的 Exception；
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

专属 Gate：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-310-001 | 三个子领域均已判断 Disposition | pending |  |
| DSN-DG-310-002 | 适用的可验证项目安全、隐私与合规基线已覆盖 | pending |  |
| DSN-DG-310-003 | 适用且未豁免的资产、保护目标和信任边界明确 | pending |  |
| DSN-DG-310-004 | 适用且未豁免的威胁和滥用场景已识别 | pending |  |
| DSN-DG-310-005 | 适用且未豁免的威胁具有 Control 或剩余风险记录 | pending |  |
| DSN-DG-310-006 | 适用且未豁免的身份、认证、授权和拒绝行为明确 | pending |  |
| DSN-DG-310-007 | 适用且未豁免的隐私目的、最小化和 Lifecycle 引用准确 | pending |  |
| DSN-DG-310-008 | 适用且未豁免的合规义务、范围、Control 和 Evidence 准确 | pending |  |
| DSN-DG-310-009 | 适用且未豁免的剩余风险具有 Decision 或 Exception，并明确责任方 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
