# Repository Agent Instructions

## 1. 目标

本仓库把稳定的 SDLC 领域规范转化为可独立运行、可验证、可分发的
Cursor、Claude Code 和 Codex Plugin / Skills。

本文件约束开发行为，不是领域 Contract，也不是安装后的运行时组件。

## 2. 来源分层

| Concern | Source of Truth |
|---|---|
| 领域语义与兼容目标 | 当前稳定的 `docs/v1.x/**` |
| Plugin 工程规则 | `docs/plugin-development/DEVELOPMENT.md` |
| Skill 阶段流程 | `docs/plugin-development/SKILL-DEVELOPMENT-WORKFLOW.md` |
| 当前状态与唯一下一工作包 | `docs/plugin-development/HANDOFF.md` |
| 单个 Skill 的设计与评测 | 对应 Work Item |
| 安装后共享运行合约 | `skills/_shared/**` |
| 确定性共享能力 | `packages/**` 与运行时 `scripts/**` |

`docs/v1.x/**` 是设计、构建、审查和追溯来源。正式 Skill 运行时不得重新读取、
解释或编译这些文档。安装后的执行 Contract 必须随 Plugin 打包在 `skills/**`、
`packages/**`、`scripts/**` 或平台组件中。

## 3. 仓库与 Git

- 使用用户当前明确指定的仓库、分支和工作树，不在规范中绑定固定远端名称。
- 每次写入前确认 Git 根目录、当前分支、HEAD 和 `git status --short`。
- 保留未知的 staged、unstaged 和 untracked 内容；工作树不干净且范围不明确时停止。
- 不自动 push、merge、rebase、tag、release 或修改远端资源。
- Commit、push 和其他外部写入只在当前工作包明确授权时执行。
- 不依赖固定作者身份；使用当前仓库或当前用户明确指定的 Git 身份。

## 4. 阶段隔离

每个正式 Skill 按以下阶段推进：

```text
design → approval → implement → evaluate → adapt → review → finalize
```

一次会话只处理一个阶段。不得自动进入下一阶段。

- `design`：只维护 Design、Eval Plan 和 Handoff，不创建正式 `SKILL.md`。
- `approval`：只记录 Maintainer 明确决定。
- `implement`：只实现已批准的最小 Runtime。
- `evaluate`：执行固定案例并保存证据。
- `adapt`：一次只处理一个 Client / Surface。
- `review`：fresh context，默认只报告问题。
- `finalize`：只在明确最终接受后收口，不自动发布。

## 5. Skill 命名与语言

正式 Phase Skill 使用：

```text
sdlc-<三位阶段编号>-<英文缩写>
```

例如：

```text
sdlc-000-ctx
sdlc-100-req
sdlc-200-dsn
sdlc-300-pln
sdlc-400-imp
sdlc-500-vfy
sdlc-600-rls
```

规则：

- 目录名和 Front Matter `name` 必须一致并使用英文 lowercase kebab-case。
- Front Matter `description` 和 Skill 正文默认使用中文。
- 文件名、字段、ID、Reference、枚举、命令和代码符号保持规范定义的英文形式。

## 6. Runtime Independence

正式 Skill 的最小部署边界是整个 Plugin，不是孤立的 Skill 目录。

运行时必须满足：

- 不读取 `docs/v1.x/**` 或 `docs/plugin-development/**`；
- 不依赖开发仓库中的 `AGENTS.md`、`CLAUDE.md` 或 Handoff；
- 可以使用 `skills/_shared/**` 的共享运行合约；
- 可以使用 `packages/**` 和运行时 `scripts/**` 的共享确定性能力；
- 不依赖兄弟业务 Skill；
- 删除 `docs/**` 后，受支持行为仍可执行；
- 不联网、不自动安装依赖、不静默降级。

设计期 Source 与运行时 Contract 使用单向关系：

```text
docs/v1.x → Design / Build / Review → bundled runtime
```

不得在运行时反向修改或重新解释设计期 Source。

## 7. 共享与私有资源

- 多个业务 Skill 共同遵守的运行合约放在 `skills/_shared/**`。
- `skills/_shared/**` 不得包含 `SKILL.md`，不能成为可调用 Skill。
- 单个 Skill 私有的规则、模板、脚本和 Eval 放在自己的目录。
- 只有共享的确定性能力放在 `packages/**` 或根级运行时 `scripts/**`。
- 构建期工具放在 `tools/**`；构建期工具可以读取 `docs/**`，运行时代码不可以。
- 业务 Skill 不得跨目录读取其他业务 Skill 的私有资源。

## 8. ArtifactStore 边界

当前共享持久化能力位于：

```text
packages/sdlc_artifact_store/
scripts/sdlc_artifact_store.py
```

所有 Artifact Skill 必须：

- 通过共享 API / Runtime Adapter 使用 Store；
- 不直接执行 SQL；
- 不创建私有 Schema 或 Store；
- 不复制 ArtifactStore；
- 将领域 Builder / Validator 与 Store 持久化分离；
- `check` 使用严格只读入口；
- `create / revise` 仅在明确写入授权下使用读写入口。

## 9. 安全与授权

默认禁止：

- 未授权外部写入；
- 自动安装依赖；
- 修改用户级或系统级配置；
- 破坏性 Git 操作；
- 写入 Secret、Token、Cookie 或真实凭证；
- 自动调用其他 Skill / Plugin；
- 把失败、未知或部分完成描述为成功。

正式 Skill 必须采用 Exclusive Skill Execution Contract，并通过 Eval 验证。
该契约限制模型行为，不代表不可绕过的硬隔离。

## 10. 完成检查

每个工作包结束前必须：

1. 执行阶段规定的测试；
2. 执行 `git diff --check`；
3. 检查 Diff 仅包含允许路径；
4. 更新 Handoff，只登记一个下一工作包；
5. 明确已验证、未验证和已知限制；
6. 达到停止条件后结束。
