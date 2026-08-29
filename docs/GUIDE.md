## 结论

**现在可以全面转入 Codex App。**

当前仓库已经具备完整的开发治理层：

* 根级与路径级 `AGENTS.md`；
* Claude Code 的 `CLAUDE.md` 桥接；
* `design → implement → evaluate → adapt → review` 阶段隔离；
* Design Contract、Eval Plan 与 Handoff；
* Exclusive Skill Execution；
* Git 身份、写入范围、兼容性证据与停止条件。

这些约束已经足够支持 Codex App 独立推进后续开发，不需要继续依赖本会话逐步生成长提示词。

---

# 一、在 Codex App 中怎样开展开发

## 1. 使用 Codex，而不是 Work

这个项目属于：

* 本地 Git 仓库；
* Plugin、Skill、Script 与测试开发；
* 需要执行命令、检查 Diff、提交代码。

因此使用桌面应用中的 **Codex 本地项目**。Work 更偏向研究、文件处理与最终交付物；Codex 是软件开发视图，并提供代码 Diff、仓库操作和多 Agent 工作流。([OpenAI Help Center][1])

GPT-5.6 在 Codex 中要求桌面应用至少为 `26.707.30751`。先检查并升级到当前最新版。([OpenAI Help Center][2])

## 2. 打开权威仓库

在 Codex App 中打开：

```text
~/Workspace/goedge.cloud/sdlc-ai-spec
```

开始正式工作前执行：

```bash
git remote -v
git status --short
git branch --show-current
git rev-parse --short HEAD
```

权威远端应当是：

```text
git@github.com:blade-cdn/sdlc-ai-spec.git
```

## 3. 每个正式 Skill 使用独立分支

建议从首个 Skill 开始，不再直接在 `main` 上完成整个开发生命周期。

```bash
git switch main
git pull --ff-only
git switch -c skill/sdlc-project-context
```

一个 Skill 的五个阶段都可以位于同一分支，但每个阶段独立提交：

```text
skill/sdlc-project-context
├── design commit
├── implement commit
├── evaluate commit
├── adapt commits
└── review/fix commit
```

待完整 Review 后再合并回 `main`。

这样可以：

* 保持 `main` 始终可用；
* 审查各阶段变化；
* 回退单独阶段；
* 避免半完成 Skill 进入主分支。

---

# 二、Codex 会话的使用规则

## 一个会话只处理一个阶段

推荐关系：

```text
一个 Skill
  ├── 会话 1：design
  ├── 会话 2：implement
  ├── 会话 3：evaluate
  ├── 会话 4：adapt Cursor
  ├── 会话 5：adapt Claude Code
  ├── 会话 6：adapt Codex
  └── 会话 7：review
```

不要为了节省会话数量而使用一个长会话贯穿全部阶段。

你的核心目标正是：

* 防止上下文膨胀；
* 防止早期错误扩散；
* 防止 Agent 自动进入下一阶段；
* 让每个阶段都有独立证据。

Codex App 支持多个 Agent 和并行任务，但当前第一个 Skill 不应并行开发。核心行为稳定后，三个平台的 `adapt` 才适合在相互隔离的分支或 worktree 中并行。([OpenAI][3])

---

# 三、以后不需要再发送超长提示词

仓库中的 `AGENTS.md` 和 `HANDOFF.md` 已经承担主要约束。

新会话只需要发送一个短工作包。

## 通用启动格式

```text
读取并遵守当前路径适用的全部 AGENTS.md，并读取
docs/plugin-development/HANDOFF.md。

执行 HANDOFF 中登记的唯一下一工作包。

本轮阶段：<design / implement / evaluate / adapt / review>
本轮唯一目标：<一句话>
允许修改：<路径白名单>
明确不处理：<边界>
完成后：运行阶段检查、检查 Diff、更新 HANDOFF，并停止，
不得自动进入下一阶段。

本轮允许使用 Blade <blade@breaklegsquad.com> 创建本地 commit。
不允许 push，完成后先报告结果。
```

首两个正式 Skill 建议采用：

```text
允许 commit
不允许自动 push
```

你检查 Diff 和报告后，再单独发送：

```text
检查当前提交身份、分支和远端；确认无误后 push 当前分支，
不得修改文件或创建额外提交。
```

等开发流程已经稳定，可以在单次工作包中授权自动 commit 和 push 到功能分支，但仍不建议自动 push `main`。

---

# 四、模型与推理级别

当前付费 Codex 可使用 GPT-5.6 Sol、Terra 和 Luna；Sol 负责复杂任务，Terra 平衡能力与速度，Luna 面向高速、低成本任务。具体可见选项会受 App 版本、套餐和 Workspace 设置影响。([OpenAI Help Center][2])

## 推荐配置

| 工作类型                       | 模型                   | 推理级别                  |
| -------------------------- | -------------------- | --------------------- |
| 首个 Skill 的 Design Contract | GPT-5.6 Sol          | **High**              |
| 领域 Contract 映射、架构设计        | GPT-5.6 Sol          | **High**              |
| 存在冲突、边界不清或安全问题             | GPT-5.6 Sol          | **Extra High**        |
| 根据已批准设计实现首个 Skill          | GPT-5.6 Sol 或 Terra  | **High**              |
| 第二、第三个同类 Skill 的常规实现       | GPT-5.6 Terra        | **High**              |
| 简单 Script、Fixture、格式校验     | GPT-5.6 Terra        | **Medium**            |
| Changelog、路径同步、机械修改        | GPT-5.6 Luna 或 Terra | **Medium**            |
| Eval 案例批量执行                | GPT-5.6 Terra        | **Medium**            |
| 分析 Eval 失败根因               | GPT-5.6 Sol          | **High**              |
| 首次适配某个平台                   | GPT-5.6 Sol          | **High**              |
| 已有成熟模式的平台适配                | GPT-5.6 Terra        | **High**              |
| 独立最终 Review                | GPT-5.6 Sol          | **Extra High**        |
| 修改领域 Spec、权限或总体架构          | GPT-5.6 Sol Pro，如可用  | **High / Extra High** |

## 当前项目的默认值

目前处于首个正式 Skill 阶段，因此默认使用：

```text
GPT-5.6 Sol
High
```

只在以下情况升级到 Extra High：

* `docs/v1.0` 不同条款看起来冲突；
* Skill 边界无法收敛；
* 涉及权限、外部写入或安全问题；
* 跨平台行为出现不可解释差异；
* Review 发现设计与实现存在系统性偏差；
* 准备决定是否合并首个 Skill。

不要每轮都使用 Extra High。高推理并不自动等于更好的工程结果；官方也建议通过代表性任务比较收益，而不是假定最高推理始终具有最佳性价比。([OpenAI Developers][4])

## Pro 与 Extra High 不是同一个概念

* `High / Extra High` 是推理强度；
* `Pro` 是更高计算投入的执行模式或模型选项；
* Pro 与 reasoning effort 可以相互独立。

Pro 只适合：

* 高价值架构决策；
* 极难 Review；
* 规范冲突；
* 安全边界；
* 一旦错误会导致大量后续返工的问题。

常规 Skill 实现没有必要使用 Pro。([OpenAI Developers][4])

---

# 五、遇到“大改”时怎么做

下面这些属于大改：

* 修改 `docs/v1.0`；
* 改变 Plugin 总体架构；
* 改变 `design → implement → evaluate → adapt → review` 流程；
* 改变 Exclusive Skill Execution；
* 改变显式调用策略；
* 引入 Hook、MCP、Subagent 或共享框架；
* 合并多个 Skill；
* 修改 Artifact、Gate、Reference 或 Revision 语义。

大改不要直接进入实现。

固定过程应为：

```text
新建 governance 分支
    ↓
单独 design 会话
    ↓
形成问题、方案、影响面和迁移计划
    ↓
独立 review 会话
    ↓
人工批准
    ↓
另开 implement 会话
```

分支示例：

```bash
git switch main
git pull --ff-only
git switch -c governance/<topic>
```

模型配置：

```text
设计：GPT-5.6 Sol / Extra High
独立审查：GPT-5.6 Sol / Extra High 或 Pro
实现：GPT-5.6 Sol / High
```

大改至少使用两个相互独立的会话：

1. 一个提出设计；
2. 一个不读取前一会话隐式上下文，只根据仓库文档审查。

---

# 六、还需不需要增加指导文件

## 不需要增加新的全局 `AGENTS.md`

当前已经有：

```text
AGENTS.md
skills/AGENTS.md
docs/plugin-development/AGENTS.md
CLAUDE.md
```

这已经是合理的分层。继续增加全局或重叠的指导文件，反而会导致：

* 指令重复；
* 同一规则出现多个权威来源；
* 上下文消耗；
* 修改时不同步；
* Agent 难以判断优先级。

现有 `DEVELOPMENT.md` 也已经定义了 Skill Contract、独占执行、显式调用、资源所有权和阶段流转，不需要再创建另一份“总体开发规范”。

## 现在只建议补两条现有规则

不创建新文件，只修改现有：

```text
AGENTS.md
docs/plugin-development/DEVELOPMENT.md
```

### 1. 文档语言规则

```markdown
## 文档与 Skill 语言

- 面向维护者的开发文档、Design Contract、Eval Plan、
  `SKILL.md` 正文和 References 默认使用中文。
- 文件名、目录名、Front Matter 字段、Schema 字段、ID、
  Reference、枚举、状态值、命令和代码符号保持规范定义的英文形式。
- 固定领域术语可以采用“中文 English”并列写法。
- `name` 必须使用 lowercase kebab-case，并与 Skill 目录名一致。
- `description` 可以使用中文。
- 不得维护含义相同但可能漂移的中英文两份正文。
```

### 2. 分支规则

```markdown
## 正式 Skill 分支规则

- 每个正式 Skill 应使用独立的 `skill/<skill-name>` 分支。
- 未完成 review 的 Skill 不得直接合入 `main`。
- 每个阶段应形成独立提交。
- Agent 不得在没有当前工作包授权时切换分支、合并或 rebase。
- `main` 只接受已完成阶段检查和独立 review 的结果。
```

这两项补完后，**停止继续增加治理规则**，进入真实 Skill 开发。只有真实开发暴露出重复问题，才修改通用规范。

---

# 七、后续按需增加的模板

这些不需要现在建立。

进入相应阶段前再增加：

| 到达阶段                   | 再创建                                       |
| ---------------------- | ----------------------------------------- |
| `evaluate`             | `templates/SKILL-EVAL-RESULTS.md`         |
| `adapt`                | `templates/PLATFORM-ADAPTATION-RESULT.md` |
| `review`               | `templates/SKILL-REVIEW.md`               |
| 首个 Skill 完整完成后         | 评估 `sdlc-skill-authoring`                 |
| 两个以上 Skill 共用 Script 后 | 再考虑根级共享 `scripts/`                        |

不要现在一次性创建全部模板和空目录。

模型名称同样不建议写死进 `AGENTS.md`。Codex 的可用模型和选择器会持续更新，且 Workspace 可以配置默认模型和推理级别；仓库规则中只需写“高能力模型”“高推理独立审查”等稳定要求。([OpenAI Help Center][5])

---

# 八、当前实际启动方式

完成权威仓库、语言和分支规则的小型治理提交后，在 Codex App 中：

```bash
git switch main
git pull --ff-only
git switch -c skill/sdlc-project-context
```

新建 Codex 会话：

```text
Model: GPT-5.6 Sol
Reasoning: High
```

发送：

```text
读取并遵守当前路径适用的全部 AGENTS.md 和
docs/plugin-development/HANDOFF.md。

执行 HANDOFF 中登记的 C1 工作包。

候选 Skill：sdlc-project-context
本轮阶段：design

领域 Source of Truth：

- docs/v1.0/core-spec.md
- docs/v1.0/000-ctx-spec.md

本轮只允许修改：

- docs/plugin-development/work-items/sdlc-project-context/DESIGN.md
- docs/plugin-development/work-items/sdlc-project-context/EVAL-PLAN.md
- docs/plugin-development/HANDOFF.md

正文默认使用中文，机器字段、ID、Reference、枚举和固定状态保持英文。

完成后执行阶段验证并停止，不创建 SKILL.md，不进入 implement。
允许创建本地 commit，Author 和 Committer 使用
Blade <blade@breaklegsquad.com>；不允许 push。
```

从这一轮开始，后续工作可以全部在 Codex App 内完成。

[1]: https://help.openai.com/en/articles/6825453-codex-release-notes%2525252525252525252525252525252525252525252525252525252525252525252525252525252525252525252525252525252525252525252525252525253F.ejs "ChatGPT — Release Notes | OpenAI Help Center"
[2]: https://help.openai.com/en/articles/20001354-gpt-56-in-chatgpt/ "GPT-5.6 in ChatGPT | OpenAI Help Center"
[3]: https://openai.com/index/introducing-the-codex-app/?utm_source=chatgpt.com "Introducing the Codex app | OpenAI"
[4]: https://developers.openai.com/api/docs/guides/latest-model?utm_source=chatgpt.com "Model guidance | OpenAI API"
[5]: https://help.openai.com/id-id/articles/11369540-using-codex-with-your-chatgpt-plan "Menggunakan Codex dengan paket ChatGPT Anda | OpenAI Help Center"
