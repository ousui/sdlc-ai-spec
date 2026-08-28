# Plugin Development Documentation Agent Instructions

## 1. 适用范围

本文件适用于 `docs/plugin-development/**`。这里保存开发治理、工作包、评测证据和跨会话交接，不是生产 Plugin 的运行时内容，也不是领域 Contract。

修改前必须读取根目录 `AGENTS.md`、`DEVELOPMENT.md`、`SKILL-DEVELOPMENT-WORKFLOW.md`、`HANDOFF.md` 和当前工作包直接相关的模板与 Source of Truth。

## 2. 文档角色边界

必须保持以下单一职责：

| File | Role |
|---|---|
| `DEVELOPMENT.md` | 稳定的 Plugin 工程标准 |
| `SKILL-DEVELOPMENT-WORKFLOW.md` | 通用阶段流程与转换条件 |
| `COMPATIBILITY.md` | 按 Client / Surface 记录兼容性事实 |
| `HANDOFF.md` | 当前状态、风险和唯一下一工作包 |
| `templates/` | 可复用的通用结构 |
| `prompts/` | 只启动一个阶段的透明会话入口 |
| `work-items/<skill-name>/` | 单个 Skill 的设计、评测和审查证据 |

不得让多个文件同时成为同一决定的权威来源。重复信息应改为引用。

## 3. Work Item 规则

每个工作包只对应一个 Skill：

```text
docs/plugin-development/work-items/<skill-name>/
├── DESIGN.md
├── EVAL-PLAN.md
├── EVAL-RESULTS.md   # evaluate 后按需
└── REVIEW.md         # review 后按需
```

必须：

- 从模板创建，但删除占位符并填写可判定内容；
- 只绑定完成当前 Skill 所需的最小 Source of Truth；
- 明确 In Scope、Out of Scope、权限、副作用和失败行为；
- 将阻塞问题放入 Open Items，不在正文中猜测解决；
- 保持 Design、实现和 Eval 之间可追踪；
- 不在 `docs/` 下创建正式 `SKILL.md` 或运行时代码。

## 4. 状态与批准

允许的 Design 状态：

- `draft`
- `ready`
- `approved`
- `superseded`

Agent 可以在全部 Design DoD 满足且阻塞项为零时建议或写入 `ready`，但不得自行写入 `approved`。

`approved` 只来自 Maintainer 的明确决定，并必须在确认记录中保存依据。用户没有明确批准时保持 `ready` 或 `draft`。

不得为了进入实现阶段而降低 DoD、删除阻塞项或把未知改写为假设。

## 5. Eval 文档

`EVAL-PLAN.md` 只定义案例、检查和通过条件；Design 阶段不得写入虚假执行结果。

`EVAL-RESULTS.md` 必须保存可复现证据，包括：

- Case ID；
- Agent、Client、Surface 和版本；
- 日期；
- Skill Revision 或 Git Commit；
- 输入 Prompt 与 Fixture；
- 是否加载 Skill；
- 实际输出位置；
- 每个 Check 的结果；
- 失败与偏差；
- 是否发生重试或人工补充。

不得只写总分、主观印象或“整体通过”。

## 6. Compatibility 记录

`COMPATIBILITY.md` 中每一项状态必须有对应证据。

- JSON 或 Schema 校验只能证明 Manifest 静态有效；
- 宿主加载只能证明 Plugin 可加载；
- Discovery、Invocation、Behavior 必须分别验证；
- 一个 Client 或 Surface 的结果不得复制到另一个；
- 没有测试版本、日期和输出证据时不得写 `Verified`；
- 工具不可用或未执行时写 `Unknown` 或适用的待处理状态。

## 7. Handoff 单写者规则

`HANDOFF.md` 是当前状态快照，不是会话流水账。

每次更新必须：

- 删除已经失效的“当前”描述；
- 记录实际完成项，不记录计划中但未完成的能力；
- 明确当前阶段、验证、未知项和已知风险；
- 只登记一个下一工作包；
- 明确下一工作包不处理的内容；
- 使用 `git status --short` 作为 Git 状态事实来源；
- 避免写入容易立即过期的模型、Token 或临时时间估算。

并行会话中只能有一个 Owner 修改 `HANDOFF.md`。

## 8. Template 与 Prompt 规则

模板必须保持跨 Skill 通用，不得混入某个 Phase 的具体字段或结论。

Prompt 必须：

- 只启动一个阶段；
- 要求读取适用 `AGENTS.md`；
- 明确 Source of Truth、写入白名单、DoD 和停止条件；
- 禁止自动进入下一阶段；
- 禁止未经授权的 commit、push 和外部写入；
- 不复制整份 `DEVELOPMENT.md` 或领域 Spec；
- 不使用本机绝对路径；
- 对缺失输入要求登记 Open Item，而不是猜测。

只有当至少两个真实工作包暴露出同一缺口时，才修改通用模板；单个 Skill 的特例保留在其 Work Item。

## 9. 变更纪律

- 当前阶段不需要的文档不得顺手重写；
- 不因文风偏好进行全仓格式化；
- 不把未来路线图展开进 `HANDOFF.md`；
- 不在兼容性未知时先写发布声明；
- 不用文档承诺代替实际 Validator、Fixture 或宿主测试；
- 修改通用流程时必须检查现有模板和 Prompt 是否仍一致；
- 完成前运行 `git diff --check` 并检查链接、状态和路径。
