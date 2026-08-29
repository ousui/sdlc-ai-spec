读取并遵守当前路径适用的全部 AGENTS.md，并读取：

docs/plugin-development/HANDOFF.md

执行 HANDOFF 中登记的唯一下一工作包。

HANDOFF 是当前状态和下一工作包的权威来源。
不得依据上一会话记忆、历史聊天或个人判断扩大工作范围。

## 开始前

1. 确认：
   - Git 仓库根目录；
   - 当前分支；
   - 当前 HEAD；
   - git status --short；
   - Origin Fetch / Push 目标。
2. 读取本工作包直接适用的嵌套 AGENTS.md。
3. 读取 HANDOFF 指定的最小 Source of Truth。
4. 明确输出：
   - 当前阶段；
   - 唯一目标；
   - 允许修改的路径；
   - 明确不处理的内容；
   - Definition of Done；
   - 验证方式；
   - 停止条件。
5. 如果工作树、分支、基线、允许写入范围或唯一工作包无法确定，
   立即停止并报告，不得猜测后继续。

## 执行规则

- 一次会话只完成当前一个阶段。
- 不得在同一会话中自动进入下一阶段。
- 只修改 HANDOFF 或当前工作包明确授权的路径。
- 不得修改当前稳定 Spec，除非工作包明确属于 Spec 修订。
- 不得根据实现便利改变 Artifact、Reference、Status、Check、
  Gate、Final Confirmation 或责任边界。
- 输入不足时登记 Open Item、等待输入或明确失败，不得补造事实。
- Design 未获 Maintainer 明确批准时，不得创建正式 SKILL.md。
- Agent 不得自行将 Design 标记为 approved。
- Review 阶段默认不修改被审查对象；只有工作包明确授权时，
  才可以修改 REVIEW.md、HANDOFF.md 或指定修复文件。
- 发现 Blocker、Major、Contract 冲突或未授权副作用时，
  记录问题并停止，不得绕过 Gate。
- 不执行未经授权的 push、merge、rebase、tag、release、
  Marketplace、远程 API 写入或其他外部副作用。

## 完成后

1. 执行当前阶段规定的全部验证。
2. 执行 git diff --check。
3. 检查实际 Diff 只包含允许路径。
4. 更新 HANDOFF.md：
   - 实际完成内容；
   - 验证结果；
   - 未验证内容；
   - 已知限制；
   - 当前 Git 状态；
   - 唯一下一工作包；
   - 下一工作包明确不处理的内容。
5. HANDOFF 只能登记一个下一工作包，不得一次展开多个后续阶段。
6. 如果当前工作包允许提交，本地 commit。
7. 不执行 push。
8. 达到当前阶段停止条件后立即结束。

如果 HANDOFF 中的下一动作需要 Maintainer 批准，只输出批准所需的
摘要、风险和建议，不得自行批准，也不得进入后续实现。