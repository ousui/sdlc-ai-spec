# Plugin Development Standard

## 1. 适用范围

本文件规定本仓库中跨 Agent Plugin、Skill 及其辅助资源的工程规则。

`docs/v1.1/` 是当前稳定领域 Contract 的权威来源，新 Plugin 和 Skill 开发默认绑定该 Snapshot。`docs/v1.0/` 保留为冻结、只读的历史 Snapshot；已冻结的 v1.0 Artifact 仍按其原 `Evaluation Contract Set` 解释。Plugin 只提供执行支持，不得修改、替代或重新定义领域 Artifact、Reference、Evidence、Exception、Check 和 Gate 语义。

本仓库中的 `AGENTS.md`、嵌套 `AGENTS.md` 和根级 `CLAUDE.md` 只约束 Plugin 开发，不是安装后业务项目的运行时 Plugin Component。生产运行时约束必须进入正式 `SKILL.md`，或进入经过独立设计、授权和验证的平台组件。任何 Skill 都不得依赖安装后的 Agent 自动读取本仓库开发指令。

## 1.1 权威仓库

本项目唯一权威代码与发布仓库是：

```text
blade-cdn/sdlc-ai-spec
git@github.com:blade-cdn/sdlc-ai-spec.git
```

`ousui/sdlc-ai-spec` 是已停止同步的历史仓库，不得作为当前开发、兼容性、发布或安装依据。所有仓库链接、远端配置、发布记录和后续 Plugin 元数据必须使用 `blade-cdn/sdlc-ai-spec`。

远程写入获授权时，执行前仍必须检查实际 Fetch / Push 目标和 Git URL rewrite；仓库名称正确但有效路由错误时不得继续。

规范等级：

- **必须**：违反即不接受。
- **应该**：默认遵守；偏离时必须记录依据。
- **可以**：按实际需要采用。

## 2. 文档与 Skill 语言

- 面向维护者的开发文档、Design Contract、Eval Plan、
  `SKILL.md` 正文和 References 默认使用中文。
- 文件名、目录名、Front Matter 字段、Schema 字段、ID、
  Reference、枚举、状态值、命令和代码符号保持规范定义的英文形式。
- 固定领域术语可以采用“中文 English”并列写法。
- `name` 必须使用 lowercase kebab-case，并与 Skill 目录名一致。
- `description` 可以使用中文。
- 不得维护含义相同但可能漂移的中英文两份正文。

## 3. 总体架构

项目采用：

```text
One Shared Skill Source + Three Thin Native Manifests
```

目录职责：

| 路径 | 职责 |
|---|---|
| `.cursor-plugin/plugin.json` | Cursor 原生 Plugin 入口 |
| `.claude-plugin/plugin.json` | Claude Code 原生 Plugin 入口 |
| `.codex-plugin/plugin.json` | Codex 原生 Plugin 入口 |
| `skills/` | 三端共用的唯一 Skill 权威源码 |
| `docs/plugin-development/` | 工程标准、兼容性记录和跨会话交接 |

必须遵守：

1. 平台 Manifest 只承载身份、组件路径和平台元数据。
2. 平台 Adapter 不得复制或改变领域工作流语义。
3. 不得建立 `.cursor-plugin/skills/`、`.claude-plugin/skills/` 或 `.codex-plugin/skills/`。
4. 平台专有 Rules、Hooks、Agents、Commands 或 MCP 只有在真实需求和验证证据存在时才可以增加。
5. 不为未来可能出现的需求提前创建空目录或抽象层。

### 3.1 当前 Artifact Store 实现决定

- 当前 Plugin 只支持 Local SQLite Store，固定路径为项目根目录下的 `.sdlc/store.sqlite3`。
- 不需要 Provider 配置；当前不建设多 Provider 框架。
- 唯一共享实现为 `packages/sdlc_artifact_store/`；稳定 Python facade 对应 Artifact Store Spec 的九个逻辑操作，Schema Version 初始固定为 `1`。
- 共享 CLI 为 `scripts/sdlc_artifact_store.py`，使用显式 `--project-root` 和单个 JSON 输入/输出协议；完整接口、Payload 和错误码见 [组件文档](components/artifact-store/README.md)。
- Skill 不得直接执行 SQL、复制该模块、拥有私有 SQLite Schema，或通过 `../` 调用兄弟 Skill 私有脚本；只能使用共享 Python API 或共享 CLI。
- `create / revise` 使用 `ArtifactStore.open_read_write(project_root)`，并在准确写入授权内显式调用 `initialize`；不得把打开 facade 当作隐式初始化。
- `check` 使用 `ArtifactStore.open_read_only(project_root)`；该入口不调用 `initialize`，不创建 `.sdlc/`、数据库、Schema、Migration、journal/WAL/cache/log 或其他持久化状态，Store 或 Schema 缺失时明确失败。
- `freeze_revision` 与权威 `resolve_exact_reference` 必须由 Phase Skill 提供绑定准确 Reference 和当前 Payload 的领域 verifier；Store 不判断业务事实、Gate、Exception 或 Final Confirmation。
- 当前只支持 Schema 首次创建和版本一致性验证；Schema 缺失、损坏或版本不匹配时 fail closed，不自动迁移未知 Schema。

## 4. Skill Contract

每个 Skill 必须只承担一个稳定、可描述的工作流，并明确：

- 何时应该使用；
- 何时不应该使用；
- 输入和前置条件；
- 工作步骤；
- 输出 Artifact；
- 成功条件；
- 失败条件；
- 允许的副作用；
- 所需最小权限；
- 输入不足时的处理方式。

Skill 必须：

- 不依赖上一会话的隐式记忆；
- 不依赖作者本机绝对路径；
- 不假设固定 shell 工作目录；
- 不通过流畅文本掩盖必要输入缺失；
- 不使用静默降级；
- 不把“文件已生成”视为“Gate 已通过”；
- 区分 Agent 推理、确定性检查、人工确认和未决风险。

### 4.1 Exclusive Skill Execution Contract

每个正式 Skill 必须定义并接受评测：

1. **Execution Mode**：从该 Skill 被显式调用开始，到完成、停止或明确交还控制权为止，进入 exclusive execution mode。
2. **Active Scope**：仅执行当前 Skill Contract 和用户当前请求授权的任务。
3. **Authorized External Skills / Plugins**：只有用户在当前请求中明确点名并授权的 Plugin / Skill 才可调用、委托或合并；该规则同样适用于 `sdlc-ai-spec` 内的兄弟 Skill。
4. **No Transitive Authorization**：授权只覆盖被点名的 Plugin / Skill 和当前任务，不自动覆盖其依赖或下游能力。
5. **Unauthorized Dependency Behavior**：需要外部 Skill 但未获授权时，只有当前 Skill Contract 仍可独立满足才继续；否则停止并请求授权。
6. **External Output Treatment**：已授权外部 Skill 的输出只可作为 Input 或 Supporting Evidence，不得覆盖当前 Source of Truth、Artifact Contract、Gate、Failure Contract、权限或授权边界。
7. **Exclusions**：系统指令、安全约束、宿主权限、适用的项目指令和普通 Tool 不属于被禁止的外部 Skill / Plugin。

这是可评测的行为契约，用于限制模型行为和暴露越界；它不是、也不得宣称为不可绕过的硬安全隔离。真实隔离仍取决于宿主权限与安全机制。

### 4.2 Explicit Invocation First

首版默认策略：

- Cursor：正式 `SKILL.md` 默认设置 `disable-model-invocation: true`；
- Claude Code：正式 `SKILL.md` 默认设置 `disable-model-invocation: true`；
- Codex：默认在 Skill 私有 `agents/openai.yaml` 中设置：

  ```yaml
  policy:
    allow_implicit_invocation: false
  ```

Design Contract 必须登记平台调用策略，Eval Plan 必须分别覆盖三个 Client。当前治理阶段只建立设计要求，不创建任何 `SKILL.md` 或 `agents/openai.yaml`。后续改变默认策略必须有独立设计决定和实际宿主证据。

## 5. 资源所有权

### 5.1 Skill 私有资源

只被一个 Skill 使用的资源必须放在该 Skill 目录中：

```text
skills/<skill-name>/
├── SKILL.md
├── scripts/
├── references/
├── assets/
└── evals/
```

其他 Skill 不得通过 `../` 跨目录直接调用该 Skill 的私有脚本或引用材料。

### 5.2 Plugin 共享资源

只有出现两个或以上真实使用者后，才可以把资源提升为 Plugin 级共享资源。

例如：

```text
scripts/
packages/
lib/
```

没有真实的第二个使用者时，不得为了“以后可能复用”提前建立公共层。

### 5.3 Script

Script 应该用于解析、格式转换、Schema 校验、Artifact 检查、Diff 分析和其他确定性工作。

Script 必须：

- 可重复执行；
- 尽可能幂等；
- 非交互式；
- 使用明确退出码；
- 失败时返回明确诊断；
- 不吞掉错误；
- 不自动联网；
- 不自动安装依赖；
- 不自动修改用户级或系统级配置；
- 不执行未经授权的远程写入。

## 6. Skill 开发阶段

每个 Skill 固定分为以下阶段：

1. `design`
2. `implement`
3. `evaluate`
4. `adapt`
5. `review`

每个会话必须只处理一个阶段，达到停止条件后结束，不自动进入下一阶段。

### 6.1 design

只形成 Skill Design Contract 和初始评测案例，不创建正式实现。

### 6.2 implement

只依据已经确认的设计实现最小版本，不重新发散整体架构。

### 6.3 evaluate

分别验证：

- 应触发；
- 不应触发；
- 显式调用；
- 输入完整；
- 输入缺失；
- 边界输入；
- with-skill；
- without-skill。

Skill 能被发现或调用，不等于其行为正确。

### 6.4 adapt

一次只适配一个明确 Agent 和运行载体。平台适配不得改变共享 Skill 的领域语义。

### 6.5 review

独立检查设计一致性、领域语义、路径、权限、安全、兼容性和评测证据。默认只报告问题，除非当前工作包明确授权修改。

## 7. 会话与变更控制

每次开发会话必须明确：

- 当前工作包；
- 当前阶段；
- 权威输入；
- 允许修改的路径；
- 唯一主要产物；
- Definition of Done；
- 明确不处理的内容；
- 停止条件。

每轮结束必须：

1. 运行本轮相关验证；
2. 检查 Git Diff；
3. 更新 `docs/plugin-development/HANDOFF.md`；
4. 记录已验证、未验证和已知限制；
5. 只登记下一个工作包，不展开后续全部阶段。

## 8. 正式 Skill 分支规则

- 每个正式 Skill 应使用独立的 `skill/<skill-name>` 分支。
- 未完成 review 的 Skill 不得直接合入 `main`。
- 每个阶段应形成独立提交。
- Agent 不得在没有当前工作包授权时切换分支、合并或 rebase。
- `main` 只接受已完成阶段检查和独立 review 的结果。

## 9. 安全与写入边界

默认禁止：

- 自动安装全局软件或依赖；
- 修改用户级、系统级或全局 Agent 配置；
- 写入密钥、Token、Cookie 或真实账号信息；
- 自动执行 Git commit、push、tag 或历史重写；
- 创建或修改远程 PR、Issue、Release；
- 发布 Plugin、Package 或 Marketplace；
- 调用会产生外部副作用的 API；
- 未经授权的其他远程写入。

外部写入必须获得当前工作包中的明确授权。

## 10. 兼容性与版本

- Plugin Version 与领域 Spec Version 必须独立管理。
- Plugin 必须明确声明其兼容的领域 Spec。
- Manifest JSON 语法通过不等于宿主兼容。
- Skill 被发现不等于 Skill 行为正确。
- 没有实际运行证据时，兼容状态不得写为 `Verified`。
- 三端公共元数据应该保持一致；平台特有字段可以不同。
- 兼容性结果统一记录在 `COMPATIBILITY.md`。

## 11. 简约原则

- 没有外部服务，不引入 MCP。
- 没有自动触发刚需，不引入 Hook。
- 没有上下文隔离、专门权限或并行价值，不引入 Subagent。
- 没有真实共享，不抽公共库。
- 没有分发需求，不建设 Marketplace。
- 没有更新需求，不建设更新器。
- 没有评测证据，不提升兼容性声明。

## 12. 关联流程文件

- [Skill 开发流程](SKILL-DEVELOPMENT-WORKFLOW.md)
- [Skill Design Contract 模板](templates/SKILL-DESIGN-CONTRACT.md)
- [Skill Eval Plan 模板](templates/SKILL-EVAL-PLAN.md)
- [开始 Skill 设计会话](prompts/START-SKILL-DESIGN-SESSION.md)

这些文件用于重复开发 Skill，但不得替代当前 Skill 绑定的领域 Source of Truth。
