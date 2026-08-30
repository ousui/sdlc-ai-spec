# Plugin Development Standard

## 1. 适用范围

本文件规定 `sdlc-ai-spec` Plugin、正式 Skill、共享 Runtime 与确定性组件的
工程规则。

规范等级：

- **必须**：违反即不接受；
- **应该**：默认遵守，偏离时记录依据；
- **可以**：按实际需要采用。

不在本文件中绑定固定远端仓库、分支或提交身份。每个工作包使用用户当前明确
指定的 Git 上下文。

## 2. Design Source 与 Runtime

```text
docs/v1.x/**
    Design / Build / Review Source
          ↓
skills/** + packages/** + scripts/**
    Bundled Runtime
```

必须：

- `docs/v1.x/**` 只在设计、构建、审查和兼容性校验时读取；
- 正式 Skill 运行时不得读取 `docs/v1.x/**`；
- 运行所需 SOP、合约、模板和程序随 Plugin 打包；
- `source-lock.json` 记录来源 Contract ID、版本和 SHA-256；
- 不手工维护两份含义相同但无法校验的一致性文本；
- 删除 `docs/**` 后，已支持的 Runtime 行为仍能执行。

构建期工具放在 `tools/**`，可以读取 Spec；运行时代码放在
`skills/**`、`packages/**`、`scripts/**`，不得读取 Spec 文件路径。

## 3. Plugin 架构

```text
One Shared Skill Source + Three Thin Native Manifests
```

| Path | Responsibility |
|---|---|
| `.cursor-plugin/plugin.json` | Cursor 入口 |
| `.claude-plugin/plugin.json` | Claude Code 入口 |
| `.codex-plugin/plugin.json` | Codex 入口 |
| `skills/` | 正式 Skill 与共享运行合约 |
| `packages/` | 共享确定性组件 |
| `scripts/` | Plugin Runtime CLI |
| `tools/` | 构建期工具 |
| `docs/` | 设计规范和开发证据 |

平台入口不得复制 Skill 或领域语义。

## 4. Skill 命名

正式 Phase Skill 使用：

```regex
^sdlc-[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$
```

建议固定：

| Phase | Name |
|---:|---|
| 000 | `sdlc-000-ctx` |
| 100 | `sdlc-100-req` |
| 200 | `sdlc-200-dsn` |
| 300 | `sdlc-300-pln` |
| 400 | `sdlc-400-imp` |
| 500 | `sdlc-500-vfy` |
| 600 | `sdlc-600-rls` |

`name` 使用英文；`description` 与正文默认使用中文。

## 5. Runtime Contract 分层

### 5.1 Shared Runtime Contract

多个 Skill 共同遵守：

```text
skills/_shared/contracts/
skills/_shared/schemas/
```

`_shared` 不包含 `SKILL.md`。

### 5.2 Skill Runtime

单个 Skill 只保存本阶段 SOP：

```text
skills/sdlc-NNN-xxx/
├── SKILL.md
├── references/
│   ├── contract.md
│   └── source-lock.json
├── assets/
├── scripts/
├── agents/
└── evals/
```

### 5.3 Shared Package

确定性通用能力放在 `packages/**`。业务 Skill 只通过公开 API 使用，
不复制、不直接访问内部表结构。

## 6. 标准输入输出

所有 Phase Runtime 使用：

- `skills/_shared/schemas/invocation.schema.json`
- `skills/_shared/schemas/result.schema.json`

标准请求至少包含：

```text
operation
project_root
artifact_reference
inputs
confirmations
options
```

标准结果至少包含：

```text
ok
status
artifact
gate
open_items
warnings
errors
next_action
```

阶段私有变量只放入 `inputs` 和阶段 Payload，不重新发明公共 Envelope。

## 7. ArtifactStore

当前唯一共享实现：

```text
packages/sdlc_artifact_store/
scripts/sdlc_artifact_store.py
```

物理 Store：

```text
<project-root>/.sdlc/store.sqlite3
```

约束：

- 不建设多 Provider；
- 不需要 Store 配置；
- Skill 不直接 SQL；
- `check` 使用严格只读入口；
- `create / revise` 使用读写入口并显式初始化；
- Domain Builder / Validator 与 Store 分层；
- Store 不判断业务事实、Exception、Gate 或 Final Confirmation；
- 共享 API 见 `packages/sdlc_artifact_store/CONTRACT.md`。

## 8. Skill 实现模式

```text
User request
    ↓
SKILL.md：意图与 SOP
    ↓
Phase runtime.py：参数、Builder、Validator、编排
    ↓
ArtifactStore：事务、Revision、摘要、持久化
    ↓
Structured Result + Human Summary
```

不得让 Agent 手工执行多个低级 Store 命令来模拟业务事务。

## 9. Exclusive Execution

每个正式 Skill 必须：

- 只接受显式调用；
- 从调用到结束保持 exclusive execution mode；
- 不调用兄弟业务 Skill；
- 不扩大外部授权；
- 外部输出只作为 Input / Evidence；
- 无法独立完成时停止并请求明确授权。

这是可评测行为 Contract，不是硬隔离声明。

## 10. 资源所有权

- 多 Skill 共享合约：`skills/_shared/**`
- Skill 私有规则和模板：当前 Skill 目录
- 共享确定性能力：`packages/**`
- 运行时 CLI：`scripts/**`
- 构建期生成与检查：`tools/**`

除 `_shared` 外，业务 Skill 不得跨目录读取另一个业务 Skill 的私有资源。

## 11. 开发阶段

```text
design → approval → implement → evaluate → adapt → review → finalize
```

每阶段独立会话、独立停止条件和可辨识提交。

## 12. Runtime Independence Test

每个正式 Skill 在 review 前必须：

1. 将 Plugin Runtime 复制到临时目录；
2. 删除 `docs/**`；
3. 只保留平台 Manifest、`skills/**`、`packages/**`、`scripts/**`；
4. 执行核心 Fixture；
5. 扫描 Runtime，不得存在 `docs/v1.x` 路径依赖；
6. 验证不需要网络或额外安装。

失败时不得发布。

## 13. 安全与变更

默认禁止：

- 自动联网；
- 自动安装依赖；
- 修改用户级或系统级配置；
- 未授权 Git 或远程写入；
- Secret 持久化；
- 静默 fallback；
- 把生成文件当作 Gate 通过。

## 14. 验证命令

基础验证：

```bash
python3 -m compileall packages scripts
python3 scripts/validate_runtime_contracts.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```
