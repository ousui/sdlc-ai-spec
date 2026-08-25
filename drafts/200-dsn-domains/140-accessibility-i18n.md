---
title: "可访问性与国际化 Accessibility and Internationalization"
status: draft
scope: DSN Domain 固定模板、规则与专属 Gate
parent: ../200-dsn-spec.md
---

# 可访问性与国际化 Accessibility and Internationalization

文件名：`140-accessibility-i18n.md`

边界：

- Accessibility 负责不同能力用户能否感知、操作、理解和完成任务，以及界面能否由用户代理和辅助技术可靠解释；
- `UX and Interaction` 负责操作过程和反馈意图；
- `UI and Content` 负责具体界面、内容和状态呈现；
- Internationalization 负责内容如何适配语言、Locale 和区域格式，不负责在当前 Domain 重复具体文案；
- 核心 Spec 不绑定特定标准版本、合规等级、翻译平台或验证工具。

适用性：

- Accessibility 和 Internationalization 在文件内分别判断 Disposition；
- 子领域先分别判定，再按固定聚合规则形成 Domain Disposition；
- 新增或改变用户界面及交互时，Accessibility 通常为 `required`；
- 已有设计系统完整覆盖且可以准确引用时，可以为 `embedded`；
- 涉及多语言、Locale、时区、货币或区域格式时，Internationalization 通常为 `required`；
- 项目明确限定单一语言和区域且不存在相关影响时，Internationalization 可以为 `n/a`；
- 不影响任何人机界面、交互、内容、程序化语义、用户代理或辅助技术暴露，且不改变 Locale-sensitive Contract、Data 或格式时，整个 Domain 可以为 `n/a`。

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
| drafts/200-dsn-domains/140-accessibility-i18n.md@sha256:... | Accessibility | pending | | | | | | | |
| drafts/200-dsn-domains/140-accessibility-i18n.md@sha256:... | Internationalization | pending | | | | | | | |

### 适用基线 Applicable Baseline

| 子领域 Subdomain | 标准、规范或既有能力 Standard, Spec or Existing Capability | 适用范围 Scope | 准确引用 Reference | 偏差 Deviation |
|---|---|---|---|---|
| | | | | |

### 可访问性设计 Accessibility Design

| ID | 类别 Category | 影响对象 Affected Object | 设计要求 Design Requirement | 处理或回退 Handling or Fallback |
|---|---|---|---|---|
| A11Y-001 | | | | |

### 语言与区域范围 Language and Locale Scope

| 语言或 Locale Language or Locale | 适用范围 Scope | 是否默认 Default | 回退顺序 Fallback Order | 内容来源 Content Source |
|---|---|---|---|---|
| | | | | |

### 本地化格式 Locale-sensitive Formats

| 类型 Type | 数据或来源 Data or Source | 格式规则 Formatting Rule | Locale 或时区依据 Locale or Timezone Basis | 回退行为 Fallback Behavior |
|---|---|---|---|---|
| | | | | |

### 内容与布局适配 Content and Layout Adaptation

| 影响对象 Affected Object | 场景 Scenario | 适配方式 Adaptation | 不变约束 Invariant |
|---|---|---|---|
| | | | |

### 降级与例外 Fallback and Exceptions

| 条件 Condition | 影响范围 Impact | 降级行为 Fallback Behavior | Exception 引用 Exception Reference |
|---|---|---|---|
| | | | |
```

规则：

- 子领域 Disposition 使用统一的 `required`、`embedded`、`n/a`、`waived` 或 `pending`；
- 两行顺序固定为 Accessibility、Internationalization；不得删除、重排或拆成多个控制表；
- `embedded` 必须准确引用承载的项目规范、设计系统或既有能力；
- `waived` 必须引用主文件中的 Exception；
- 不得为了填充模板虚构标准版本、支持语言、Locale 或合规目标；
- Accessibility Category 按实际影响填写，例如语义、感知、操作、焦点、反馈、时限或兼容性；
- 具体界面和内容引用 `UI and Content`，具体用户旅程引用 `UX and Interaction`；
- 具体翻译文本可以由 `UI and Content` 或 Supporting Artifact 承载，本 Domain 记录其语言、来源、适配和回退规则；
- Domain 整体适用但某个子章节不适用时，使用父 Spec 的统一 `N/A — <客观原因>` 表示；
- VFY Points 必须覆盖适用的可访问性要求、Locale、格式、适配和回退行为。

专属 Gate：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-140-001 | 两个子领域均已判断 Disposition | pending |  |
| DSN-DG-140-003 | 适用基线和准确引用明确 | pending |  |
| DSN-DG-140-004 | 适用且未豁免的可访问性设计已覆盖 | pending |  |
| DSN-DG-140-005 | 适用且未豁免的语言、Locale、默认值和回退顺序明确 | pending |  |
| DSN-DG-140-006 | 适用且未豁免的区域格式规则明确 | pending |  |
| DSN-DG-140-007 | 适用且未豁免的内容和布局适配已处理 | pending |  |
| DSN-DG-140-008 | 降级行为和 Exception 准确 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
