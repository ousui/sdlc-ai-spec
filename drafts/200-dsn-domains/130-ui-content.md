---
title: "界面与内容 UI and Content"
status: draft
scope: DSN Domain 固定模板、规则与专属 Gate
parent: ../200-dsn-spec.md
---

# 界面与内容 UI and Content

文件名：`130-ui-content.md`

边界：

- 负责描述用户行为由什么界面承载以及具体展示什么；
- 用户目标、操作过程和反馈意图由 `UX and Interaction` 承载；
- 系统业务流程和状态由 `Workflow and State` 承载；
- 可访问性和国际化专项约束由 `Accessibility and Internationalization` 承载；
- 技术组件、接口和数据结构由对应 Technical Domain 承载。

适用性：

- 新增或改变展示位置、信息层级、界面元素、状态呈现、动态内容来源或适配规则，且存在独立设计义务时为 `required`；
- 完全复用已有界面且无需任何展示变化，并能够准确引用现有设计时，可以为 `embedded`；
- 没有用户界面和用户可见内容影响时，可以为 `n/a`；
- DSN 因其他变化存在、但精确文案已由 REQ 与准确 Host 完整确定时，本 Domain 可以为 `embedded`；只有仍需决定承载位置、状态、动态规则或回退时才为 `required`；
- 当整个 Requirement 的结果已由 REQ 与准确 Baseline 完整确定，且不存在独立设计义务时，DSN 整体可以为 `n/a`；不得为满足本模板虚构 Design Decision。

固定专属模板：

```markdown
## 设计结果 Design Result

### 界面清单 View Inventory

| ID | 页面或载体 View or Surface | 用途 Purpose | 入口或承载位置 Entry or Host | 变化 Change |
|---|---|---|---|---|
| VIEW-001 | | | | new |

### 信息层级 Information Hierarchy

| 页面 View | 区域或分组 Area or Group | 顺序或优先级 Order or Priority | 内容或操作 Content or Action | 可见条件 Visibility Condition |
|---|---|---|---|---|
| VIEW-001 | | | | |

### 界面元素 UI Elements

| ID | 页面 View | 组件或元素 Component or Element | 用途 Purpose | 关联交互 Interaction Reference | 变化 Change |
|---|---|---|---|---|---|
| UI-001 | VIEW-001 | | | | new |

### 状态呈现 State Presentation

| 页面或元素 View or Element | 交互状态 Interaction State | 可见呈现 Visible Presentation | 内容引用 Content Reference |
|---|---|---|---|
| | default | | |

### 内容定义 Content Specification

| ID | 承载位置 Host | 类型 Type | 内容或来源 Content or Source | 动态规则 Dynamic Rule | 回退内容 Fallback |
|---|---|---|---|---|---|
| CNT-001 | | | | | |

### 适配规则 Adaptation Rules

| 条件 Condition | 影响对象 Affected View or Element | 调整 Adjustment | 不变约束 Invariant |
|---|---|---|---|
| | | | |
```

规则：

- `Change` 使用 `new`、`changed` 或 `reused`；
- 新增或变化的用户可见静态内容必须记录准确内容；
- 动态内容必须记录来源、生成或格式化规则以及缺失时的回退内容；
- State Presentation 必须引用 `UX and Interaction` 中适用的交互状态，不得另行创造不一致的状态；
- 本 Domain 不得创建新的用户行为或业务规则，相关变化必须返回对应 Domain 或 REQ；
- 项目已有设计系统、组件库或内容规范时，可以准确引用，不在当前 DSN 重复全文；
- 不强制提供像素标注、视觉稿、原型图或特定工具源文件；
- Domain 整体适用但某个子章节不适用时，使用父 Spec 的统一 `N/A — <客观原因>` 表示；
- 原型、截图和设计源文件可以作为辅助材料，但固定表格是规范判定依据；
- VFY Points 必须覆盖变化的页面、元素、状态呈现和内容。

专属 Gate：

| Check ID | 检查项 Check | 结果 Result | 证据或说明 Evidence or Notes |
|---|---|---|---|
| DSN-DG-130-002 | 新增或变化的页面和承载位置明确 | pending |  |
| DSN-DG-130-003 | 信息层级和可见条件明确 | pending |  |
| DSN-DG-130-004 | 新增或变化的界面元素已登记 | pending |  |
| DSN-DG-130-005 | 适用的交互状态具有对应呈现 | pending |  |
| DSN-DG-130-006 | 静态内容准确，动态内容来源和回退明确 | pending |  |
| DSN-DG-130-007 | 适配条件和不变约束已按适用性处理 | pending |  |

> Parent Spec: [Design Phase Spec](../200-dsn-spec.md)
