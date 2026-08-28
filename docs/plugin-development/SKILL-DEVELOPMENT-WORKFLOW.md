# Skill Development Workflow

## 1. 目的

本流程用于以可理解、可审查、可跨会话交接的方式重复开发 Skill。

它只规定开发过程，不定义任何领域工作流。领域语义始终来自当前 Skill 明确绑定的 Source of Truth；正式 `SKILL.md` 只是执行支持，不得成为第二份领域规范。

## 2. 工作包目录

每个候选 Skill 在进入实现前，必须先建立独立工作包：

```text
docs/plugin-development/work-items/<skill-name>/
├── DESIGN.md
└── EVAL-PLAN.md
```

后续阶段按实际需要增加：

```text
├── EVAL-RESULTS.md
└── REVIEW.md
```

工作包文档用于开发、评测和审查；正式运行内容仍位于：

```text
skills/<skill-name>/
```

不得把工作包文档复制进三个平台 Manifest 目录。

## 3. 固定阶段

每个 Skill 必须按以下阶段推进：

```text
design → implement → evaluate → adapt → review
```

一次会话只处理一个阶段。当前阶段达到停止条件后必须结束，不得自动进入下一阶段。

### 3.1 design

目标：明确 Skill 应当解决什么问题，以及如何证明设计有效。

主要产物：

- `DESIGN.md`
- `EVAL-PLAN.md`

本阶段必须明确：

- 单一职责；
- 触发与不触发场景；
- 输入、前置条件和权威来源；
- 输出和成功条件；
- 输入不足、冲突或失败时的行为；
- 权限和副作用；
- `SKILL.md`、references、scripts、assets 的预期边界；
- 初始正向、负向、缺失输入和边界评测案例。

本阶段禁止：

- 创建正式 `SKILL.md`；
- 编写运行脚本；
- 修改三个 Manifest；
- 增加 Hook、MCP、Agent 或 Command；
- 进行平台适配。

Design 只有在所有必填设计项明确、未决问题不阻塞实现、Eval Plan 足以判断行为后，才可以标记为 `ready`。

### 3.2 implement

目标：依据已经确认的 Design Contract 创建最小可工作的共享 Skill。

允许创建：

```text
skills/<skill-name>/SKILL.md
skills/<skill-name>/references/   # 仅在确有详细材料需要按需加载时
skills/<skill-name>/scripts/      # 仅在存在确定性操作需求时
skills/<skill-name>/assets/       # 仅在存在模板或静态资源需求时
```

实现必须服从 Design Contract，不得在实现会话中重新扩大范围。

没有确定性操作需求时，不创建 Script。没有复杂详细材料时，不创建 references。

### 3.3 evaluate

目标：分别验证 Skill 是否正确触发，以及加载后是否产生符合设计的行为。

至少覆盖：

- 应触发；
- 不应触发；
- 显式调用；
- 输入完整；
- 输入缺失；
- 边界输入；
- with-skill；
- without-skill。

评测结果必须记录为证据。只根据实际失败修正 Skill，不因主观偏好扩大内容。

### 3.4 adapt

目标：一次只验证和适配一个明确的 Agent 运行载体。

平台 Adapter 可以处理 Manifest、发现、路径、元数据或平台专有入口，但不得改变共享 Skill 的领域语义。

一个平台通过，不代表其他平台通过。

### 3.5 review

目标：由独立会话检查：

- 实现是否符合 Design Contract；
- 是否改变领域 Source of Truth；
- 是否存在重复权威来源；
- 是否存在路径、权限、安全或副作用问题；
- Eval 是否足以支撑兼容性与质量声明；
- 是否存在未经证明必要的基础设施。

默认只报告问题。是否修改由新的明确工作包决定。

## 4. 阶段转换规则

阶段转换必须满足：

| From | To | 最低条件 |
|---|---|---|
| design | implement | `DESIGN.md` 和 `EVAL-PLAN.md` 已完成并确认，阻塞项为零 |
| implement | evaluate | 最小实现存在，静态检查通过，没有超出设计范围 |
| evaluate | adapt | 核心行为评测通过，失败项已修正或明确接受 |
| adapt | review | 目标载体已有实际加载和调用证据，未知项已标记 |
| review | complete | 阻塞问题为零，剩余限制已记录 |

不满足最低条件时不得以“后面再补”的方式静默前进。

## 5. 会话规则

每次会话开始时必须读取：

- `docs/plugin-development/DEVELOPMENT.md`
- 本文件；
- `docs/plugin-development/HANDOFF.md`
- 当前工作包文档；
- 当前阶段明确列出的领域 Source of Truth。

不得依赖上一会话的隐式记忆。

每次会话开始前必须说明：

- 当前阶段；
- 唯一工作包；
- 允许修改的路径；
- 明确不处理的内容；
- Definition of Done；
- 停止条件。

每次会话结束必须：

1. 运行本阶段相关检查；
2. 检查 Git Diff；
3. 更新 `HANDOFF.md`；
4. 记录已验证、未验证和已知限制；
5. 只登记下一次唯一工作包。

## 6. Creator 工具的使用边界

平台提供的 `skill-creator` 或 `plugin-creator` 可以用于：

- 根据已确认的 Design Contract 生成初稿；
- 检查平台格式；
- 辅助建立 Eval；
- 审查已有实现。

Creator 不得：

- 取代领域 Source of Truth；
- 在没有 Design Contract 时自行决定 Skill 范围；
- 自动创建多个后续阶段产物；
- 引入未经确认的 Script、Hook、MCP、Agent、Command 或 Marketplace；
- 直接提升兼容性状态。

## 7. Skill 创建快捷入口

当前快捷入口是：

`docs/plugin-development/prompts/START-SKILL-DESIGN-SESSION.md`

它用于启动一个只完成 `design` 阶段的新会话，不会创建正式 Skill。

## 8. 是否创建 Skill Authoring 元 Skill

在至少一个真实 Skill 完成 `design → implement → evaluate → adapt → review` 全流程之前，不创建自动化的 Skill Authoring 元 Skill。

首个真实 Skill 完成后，再根据实际重复步骤决定是否建立独立的开发辅助 Plugin 或 Skill。开发辅助能力默认不进入面向最终使用者的生产 Plugin。
