# Skills Subtree Agent Instructions

## 1. 适用范围

本文件适用于 `skills/**`，补充根级 `AGENTS.md`。

运行时必须遵守的规则应写入正式 `SKILL.md`、Skill 私有资源或 `skills/_shared/**`；不得依赖安装后读取本文件。

## 2. 目录角色

```text
skills/
├── _shared/                    多 Skill 共同运行合约；不得有 SKILL.md
└── sdlc-NNN-xxx/               正式 Phase Skill
```

正式 Skill 结构：

```text
skills/sdlc-NNN-xxx/
├── SKILL.md
├── agents/
│   └── openai.yaml             按适配阶段创建
├── references/
│   ├── interface.json          用户命令、版本和示例
│   ├── contract.md
│   └── source-lock.json
├── assets/
├── scripts/
└── evals/
```

目录按需创建，不允许空占位目录。

## 3. 命名

正式 Phase Skill 必须匹配：

```regex
^sdlc-[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$
```

- 目录名与 Front Matter `name` 完全一致；
- `name` 使用英文；
- `description` 使用清晰中文，说明做什么、何时显式调用；
- 一个 Skill 只实现一个阶段 Contract。

## 4. 实现准入

创建正式 `SKILL.md` 前必须满足：

- Work Item 已存在；
- Design=`approved`；
- 阻塞 Open Item=0；
- Eval Plan 可判定；
- 当前 Handoff 阶段允许实现；
- 写入白名单包含准确 Skill 路径。

不得先实现再补设计。

## 5. Spec 与 Runtime

- `docs/v1.x/**` 只用于 design、build、review 和 source-lock 生成。
- 正式运行时不得读取 `docs/v1.x/**`。
- Skill 必须把必要规则固化到自身 Contract、Asset、Script 或共享 Runtime。
- `source-lock.json` 记录构建来源的 Contract ID、版本和摘要，不保存运行时文档路径。
- 不把完整 Spec 复制进 `SKILL.md`。
- 删除 `docs/**` 后必须通过 Runtime Independence Test。

## 6. 共享合约

所有正式 Skill 必须遵守：

- `skills/_shared/contracts/skill-execution.md`
- `skills/_shared/contracts/skill-interface.md`
- Artifact Skill 还必须遵守：`skills/_shared/contracts/artifact-runtime.md`
- Phase Runtime 还必须遵守：`skills/_shared/contracts/phase-runtime.md`

`skills/_shared/**` 是唯一允许业务 Skill 跨目录读取的共享指令区域。不得读取其他 `skills/sdlc-*/` 的私有内容。

## 7. 用户接口

每个正式 Skill 必须：

- 提供 `references/interface.json`；
- 裸调用可用，默认 `operation=auto`；
- 提供 `help / version / commands / examples`；
- 使用共享 `packages/sdlc_runtime/skill_args.py`，不得实现第二套不兼容解析器；
- 支持 GNU 长参数、单字符短参数和 Contract 定义的兼容别名；
- 未知参数、缺值和冲突必须失败关闭；
- 自动读取工作区并完成确定性默认值；
- 只有存在真实业务决策、多候选无确定最优解或高影响副作用时才询问用户；
- 默认隐藏 Evidence ID、Digest、Manifest 和内部 Runtime JSON；
- 标准项目内写入遵守 `write_policy`，Git 与外部写入始终单独授权。

## 8. Skill 与程序职责

Agent / `SKILL.md` 负责：

- 识别用户意图；
- 解析用户命令并解决默认值；
- 读取工作区、收集和组织候选事实；
- 解释 Open Item、失败和下一动作；
- 提供推荐并请求必要人工决策。

Skill Runtime Script 负责：

- 标准参数校验；
- Builder / Validator 编排；
- 结构化输入输出；
- ArtifactStore 调用顺序；
- 错误码与退出码。

共享 Package 负责：

- 用户参数归一化；
- SQLite、事务、ID、Revision、摘要、Member closure 和准确解析。

不得让 Agent 手工串联多个低级 Store CLI 命令形成业务事务。

## 9. 触发与独占执行

首版默认显式调用：

- Cursor / Claude Code：`disable-model-invocation: true`
- Codex：`policy.allow_implicit_invocation: false`

正式 Skill 必须：

- 从显式调用到完成保持 exclusive execution mode；
- 不调用兄弟 Skill；
- 不把授权传递给其他能力；
- 输入不足时按 Contract 停止、等待或形成 Open Item；
- 不静默补造上游决定。

## 10. Script 与 Asset

Script 必须：

- Python 标准库优先；
- 非交互式；
- 输入输出稳定；
- 明确退出码；
- 不联网、不安装依赖、不吞错；
- 不依赖固定 CWD；
- 有自动化测试。

Asset 只保存模板和静态资源，不保存结果、Secret 或虚构事实。

## 11. Eval

每个 Skill 至少验证：

- 裸调用与 `operation=auto`；
- 所有声明命令、长参数、短参数和兼容别名；
- help、version、commands、examples；
- 默认值、显式覆盖、未知参数、冲突与引号错误；
- 唯一推断、多候选决策、推荐理由；
- `decision_policy` 和 `write_policy` 全路径；
- `summary / json / debug`；
- 显式正向调用、未调用和负向场景；
- 完整输入、缺失输入、边界/冲突；
- with-skill / without-skill；
- Runtime Independence；
- 共享合约遵守；
- 未授权兄弟 Skill 不被调用；
- 对应 Client 的真实 Discovery / Invocation / Behavior。

未执行的案例不得写成通过。
