# Start Skill Design Session

复制下面的提示词启动一个独立会话。发送前只替换尖括号中的字段。

```text
承接 `sdlc-ai-spec` Plugin 的一个增量工作包。

本轮阶段：`design`
本轮只设计一个候选 Skill，不创建正式 `SKILL.md`，不进入实现、评测或平台适配。

## 工作包参数

- Candidate Skill Name:
  `<lowercase-hyphen-name>`

- Intended User Outcome:
  `<一句话说明用户执行后应获得的结果>`

- Domain Source of Truth:
  - `<repository-relative-path-1>`
  - `<repository-relative-path-2，如无则删除>`

- Allowed Write Scope:
  - `docs/plugin-development/work-items/<skill-name>/DESIGN.md`
  - `docs/plugin-development/work-items/<skill-name>/EVAL-PLAN.md`
  - `docs/plugin-development/HANDOFF.md`

## 开始前

1. 确认 Git 仓库根目录和当前工作树状态。
2. 读取当前目录适用的 Agent 指令。
3. 读取：
   - `docs/plugin-development/DEVELOPMENT.md`
   - `docs/plugin-development/SKILL-DEVELOPMENT-WORKFLOW.md`
   - `docs/plugin-development/HANDOFF.md`
   - 本轮列出的 Domain Source of Truth。
4. 读取模板：
   - `docs/plugin-development/templates/SKILL-DESIGN-CONTRACT.md`
   - `docs/plugin-development/templates/SKILL-EVAL-PLAN.md`
5. 不读取与当前候选 Skill 无关的全部领域文档。
6. 不依赖上一会话的隐式记忆。

## 执行前先输出

- 已确认事实；
- 当前候选 Skill 的单一职责假设；
- 本轮允许修改的文件；
- 本轮明确不处理的内容；
- Design 阶段 Definition of Done。

如 Source of Truth 不足以完成设计，不猜测；在 Design Contract 的 Open Items 中登记阻塞项，并保持 `draft`。

## 本轮工作

1. 创建：
   `docs/plugin-development/work-items/<skill-name>/DESIGN.md`

   使用 `SKILL-DESIGN-CONTRACT.md` 模板，完成：
   - Problem 和 Intended User Outcome；
   - In Scope / Out of Scope；
   - 应触发与不应触发场景；
   - Input、Output、Workflow 和 Failure Contract；
   - 权限与副作用；
   - `SKILL.md`、references、scripts、assets 的边界；
   - Portable Core 与三端 Adapter 边界；
   - Open Items 和 Design DoD。

2. 创建：
   `docs/plugin-development/work-items/<skill-name>/EVAL-PLAN.md`

   使用 `SKILL-EVAL-PLAN.md` 模板，至少设计：
   - 2 个正向触发案例；
   - 2 个负向不触发案例；
   - 1 个完整输入案例；
   - 1 个缺失必要输入案例；
   - 1 个边界或冲突案例；
   - 1 组 with-skill / without-skill 对比。

3. 只在没有阻塞实现的 Open Item 且 Eval Plan 可判定时，将 Design Status 标记为 `ready`。不得自行标记为 `approved`。

4. 更新 `docs/plugin-development/HANDOFF.md`，只登记下一次唯一工作包。

## 禁止事项

本轮不得：

- 创建或修改 `skills/<skill-name>/SKILL.md`；
- 创建 Script、Reference、Asset 或 Eval Result；
- 修改三个平台 Manifest；
- 创建 Hook、MCP、Agent、Command 或 Marketplace；
- 执行平台安装或兼容性测试；
- 修改 Domain Source of Truth；
- Git commit、push 或任何外部写入；
- 自动进入 `implement` 阶段。

## 完成检查

完成后：

1. 检查两个工作包文件是否完整；
2. 检查没有创建任何 `SKILL.md`；
3. 执行 `git diff --check`；
4. 输出 Git Diff 摘要；
5. 报告 Design Status、Open Items 和下一次唯一工作包。

达到 design 停止条件后立即结束。
```
