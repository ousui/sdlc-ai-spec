# Plugin Development Standard

## 1. 适用范围

本文件规定本仓库中跨 Agent Plugin、Skill 及其辅助资源的工程规则。

`docs/v1.0/` 是领域 Contract 的权威来源。Plugin 只提供执行支持，不得修改、替代或重新定义领域 Artifact、Reference、Evidence、Exception、Check 和 Gate 语义。

规范等级：

- **必须**：违反即不接受。
- **应该**：默认遵守；偏离时必须记录依据。
- **可以**：按实际需要采用。

## 2. 总体架构

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

## 3. Skill Contract

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

## 4. 资源所有权

### 4.1 Skill 私有资源

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

### 4.2 Plugin 共享资源

只有出现两个或以上真实使用者后，才可以把资源提升为 Plugin 级共享资源。

例如：

```text
scripts/
packages/
lib/
```

没有真实的第二个使用者时，不得为了“以后可能复用”提前建立公共层。

### 4.3 Script

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

## 5. Skill 开发阶段

每个 Skill 固定分为以下阶段：

1. `design`
2. `implement`
3. `evaluate`
4. `adapt`
5. `review`

每个会话必须只处理一个阶段，达到停止条件后结束，不自动进入下一阶段。

### 5.1 design

只形成 Skill Design Contract 和初始评测案例，不创建正式实现。

### 5.2 implement

只依据已经确认的设计实现最小版本，不重新发散整体架构。

### 5.3 evaluate

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

### 5.4 adapt

一次只适配一个明确 Agent 和运行载体。平台适配不得改变共享 Skill 的领域语义。

### 5.5 review

独立检查设计一致性、领域语义、路径、权限、安全、兼容性和评测证据。默认只报告问题，除非当前工作包明确授权修改。

## 6. 会话与变更控制

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

## 7. 安全与写入边界

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

## 8. 兼容性与版本

- Plugin Version 与领域 Spec Version 必须独立管理。
- Plugin 必须明确声明其兼容的领域 Spec。
- Manifest JSON 语法通过不等于宿主兼容。
- Skill 被发现不等于 Skill 行为正确。
- 没有实际运行证据时，兼容状态不得写为 `Verified`。
- 三端公共元数据应该保持一致；平台特有字段可以不同。
- 兼容性结果统一记录在 `COMPATIBILITY.md`。

## 9. 简约原则

- 没有外部服务，不引入 MCP。
- 没有自动触发刚需，不引入 Hook。
- 没有上下文隔离、专门权限或并行价值，不引入 Subagent。
- 没有真实共享，不抽公共库。
- 没有分发需求，不建设 Marketplace。
- 没有更新需求，不建设更新器。
- 没有评测证据，不提升兼容性声明。

## 10. 关联流程文件

- [Skill 开发流程](SKILL-DEVELOPMENT-WORKFLOW.md)
- [Skill Design Contract 模板](templates/SKILL-DESIGN-CONTRACT.md)
- [Skill Eval Plan 模板](templates/SKILL-EVAL-PLAN.md)
- [开始 Skill 设计会话](prompts/START-SKILL-DESIGN-SESSION.md)

这些文件用于重复开发 Skill，但不得替代当前 Skill 绑定的领域 Source of Truth。
