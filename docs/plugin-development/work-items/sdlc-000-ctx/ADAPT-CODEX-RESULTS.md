# sdlc-000-ctx Codex Adapt Results

## 结论

- 状态：`passed`；历史 Review Finding `REV-005` 已获得独立修复证据。
- 验证日期：2026-08-31。
- Client / Surface：Codex CLI TUI / `codex exec`。
- Tested Version：`codex-cli 0.151.0-alpha.7.1`。
- 分支 / HEAD：`skill/sdlc-000-ctx` /
  `78028dc67707593420380b61f43f4a1bf7fc9fcd`。
- 本结论只使用本轮 fresh Codex 会话与安装缓存 Runtime 的直接证据；历史读取过开发仓库
  `tests/**` 的 Behavior 证据不再作为通过依据。
- 仅完成 Codex Discovery、未调用对照、显式 Invocation、安装缓存路径、权限边界和真实
  Behavior；未执行 Cursor、Claude Code、Review 或 `finalize`。

## 部署隔离与安装

本轮先把当前工作树复制为独立 Plugin 部署单元，Plugin 根顶层只保留：

```text
.codex-plugin/
skills/
packages/
scripts/
```

隔离 Plugin 根和安装缓存均确认不存在 `docs/`、`tests/` 或 Handoff。行为会话的工作目录是
只含预置 `.git` 的隔离项目；Invocation 没有从主 worker 已读取的开发资产派生，行为会话
只收到操作、准确 Project Root、准确 CTX Reference 与部署隔离约束。

通过临时本地 Marketplace 安装：

```text
codex plugin marketplace add <isolated-local-marketplace> --json
codex plugin add sdlc-ai-spec@sdlc-000-ctx-adapt-fix-local --json
```

安装结果为 `installed=true`、`enabled=true`，接受 Behavior 的安装缓存路径为：

```text
/private/tmp/sdlc-000-ctx-adapt-codex-fix.QqzVdz/codex-home-behavior/plugins/cache/
sdlc-000-ctx-adapt-fix-local/sdlc-ai-spec/0.1.0
```

隔离 Plugin Source 与安装缓存执行 `diff -qr` 无差异。关键文件摘要：

| 文件 | SHA-256 | 结果 |
|---|---|---|
| `.codex-plugin/plugin.json` | `03b2e7dd36c014c05a63cc778746a328ca57074d1134c26af4a12255f202b526` | PASS |
| `skills/sdlc-000-ctx/agents/openai.yaml` | `af756653873aba9a035c517c8ce808be8193faf3e05549f6b444c24dd28f79be` | PASS |
| `skills/sdlc-000-ctx/SKILL.md` | `8cb7223f6186b0cad2f0b678f00405e58f5a6e0e57d9bb3db7093212862ff547` | PASS |
| `skills/sdlc-000-ctx/references/contract.md` | `26716a5dd71e2a492f32e90c3c47b987d76193e5dc6437f749c8b558bc8fcf61` | PASS |
| `skills/sdlc-000-ctx/scripts/runtime.py` | `c4edaae3de4cede691f59ac69741bc0f6d4f7ee948a1f42a207fe74d0cf054ac` | PASS |

Manifest 的 `name`、`version`、`skills` 路径被原生 Marketplace 接受；`openai.yaml` 的
`interface.display_name`、中文 `short_description` 可被 Codex 读取，且
`policy.allow_implicit_invocation: false`。安装文件为 `-rw-r--r--`，目录为
`drwxr-xr-x`。

## Client 直接证据

| 检查项 | 直接证据 | 结果 |
|---|---|---|
| Discovery | fresh TUI 输入 `$sdlc`，显示 `SDLC Project Context [Skill] 显式创建、修订或检查准确的 CTX Revision` | PASS |
| 显式 Invocation | 选择候选后 Composer 插入 `$sdlc-ai-spec:sdlc-000-ctx`；TUI Session `01a05596-5b9a-7581-acbf-69bf3af8d363` | PASS |
| 未调用对照 | fresh `codex exec` 只输出 `NO_SKILL_CONTROL`；事件流无任何 Tool Call；Thread `01a05597-0c39-7be1-a774-6f0d4977fdcb` | PASS |
| 安装缓存 Skill 注入 | fresh Behavior Rollout 中 Codex 注入的 selected Skill path 指向安装缓存 `skills/sdlc-000-ctx/SKILL.md` | PASS |
| Runtime 路径 | 真实命令在安装缓存 Plugin Root 运行 `python3 skills/sdlc-000-ctx/scripts/runtime.py` | PASS |
| 开发资产隔离 | Rollout 中 6 个 Tool Call 全为 `exec`，workdir 全位于安装缓存；工具参数扫描对开发仓库、`docs/**`、`tests/**`、Handoff 的命中为 `0` | PASS |
| 结构化 Result | Runtime 返回完整 `sdlc-ai-spec/runtime-result/v1` Envelope | PASS |
| 中文摘要 | 摘要与 `STORE_NOT_FOUND`、`pending` Gate、空 Open Items 和唯一 `next_action` 一致 | PASS |
| 严格只读 | 执行前后隔离项目均无 `.sdlc`，`git status --short` 为空 | PASS |

接受的 Behavior Thread：`01a0559a-7f1e-7a41-b4bb-3ad0fab7db8b`。其 Rollout
SHA-256 为：

```text
fd213dd99c9fda9043f9f73d34a68c2cec1a7e990d4279eddf01fb2125628b7f
```

该 Rollout 中的 6 个 Tool Call 只读取安装缓存的 bundled contract、共享 Envelope、目标
Runtime 与 Package，并执行一次安装缓存 Runtime；没有调用其他 Skill、没有访问开发仓库，
也没有由 Agent 或 Runtime 发起网络命令。Codex 宿主后台仍尝试同步 curated plugin catalog；
该宿主同步未被行为会话读取、未参与 Invocation 或 Runtime 结果，不能作为 Runtime 网络行为。

## 真实 Behavior

fresh Codex 会话没有获得预构造 JSON。它先从安装缓存的 `references/contract.md`、共享
Envelope 与 Runtime 自行确定 Invocation 字段，再通过标准输入执行一次严格只读 `check`：

```json
{
  "contract": "sdlc-ai-spec/runtime-invocation/v1",
  "operation": "check",
  "project_root": "/private/tmp/sdlc-000-ctx-adapt-codex-fix.QqzVdz/project",
  "artifact_reference": "CTX-20260831000000-01@1",
  "inputs": {},
  "confirmations": [],
  "options": {
    "dry_run": false
  }
}
```

实际 Result Envelope：

```json
{
  "artifact": null,
  "contract": "sdlc-ai-spec/runtime-result/v1",
  "errors": [
    {
      "code": "STORE_NOT_FOUND",
      "message": "Runtime directory does not exist: /private/tmp/sdlc-000-ctx-adapt-codex-fix.QqzVdz/project/.sdlc"
    }
  ],
  "gate": {
    "failed_checks": [],
    "result": "pending"
  },
  "next_action": {
    "code": "RESOLVE_STORE_FAILURE",
    "command": null,
    "message": "根据准确错误修复目标 Store 或选择有效 Project Root",
    "requires_user": true
  },
  "ok": false,
  "open_items": [],
  "operation": "check",
  "status": "failed",
  "warnings": []
}
```

Codex 中文摘要准确说明：项目缺少 `.sdlc` Store，无法读取指定 Revision；Artifact 不可确定，
Gate 为 `pending`，Open Items 为空，唯一下一动作是解决 Store 缺失或选择有效 Project Root。
Runtime 退出码 `1` 是预期的结构化失败，不是宿主执行失败。

## 权限与宿主限制

先以 Codex 原生 `workspace-write` 启动 Behavior。当前工作会话已处于 macOS 外层沙箱，
内层 Seatbelt 在任何命令执行前失败：

```text
sandbox-exec: sandbox_apply: Operation not permitted
```

该次 Thread `01a05597-6807-70e1-a50c-454541ff3fe8` fail closed，没有生成伪造 Result、
没有创建 `.sdlc` 或修改项目。随后按 Codex 为已受外层隔离的自动化环境提供的
`--dangerously-bypass-approvals-and-sandbox` 模式重跑；实际进程仍受本工作会话外层
`workspace-write` 边界约束。

最终 Behavior 的每个 Tool Call 都有直接 Rollout 记录，且 workdir 只在安装缓存内。目标
项目执行前后只有预置 `.git`；安装缓存目录权限可读，Runtime 不需要额外安装或开发资产。
本结论验证的是 Plugin Runtime 权限语义与真实只读行为，不宣称嵌套 macOS Seatbelt 可用。

## 收口验证

| 验证 | 结果 |
|---|---|
| `python3 -m compileall -q packages scripts skills/sdlc-000-ctx/scripts` | PASS |
| `python3 tools/validate_runtime_contracts.py` | PASS；5 个 Runtime Contract、1 个 Formal Skill |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | PASS；75 tests |
| Plugin Manifest `name` / `version` / `skills` 静态检查 | PASS |
| `policy.allow_implicit_invocation: false` 静态检查 | PASS |
| Source of Truth 三个锁定摘要复核 | PASS |
| `git diff --check` | PASS |

Source of Truth 摘要仍分别为 `1eefa7a1...b7a89b`、`b340ca2a...7d4764`、
`1d98e7cc...530470`；本工作包没有改变锁定 Source、Runtime 或 Eval Oracle。

## REV-005 Closure

- Finding 要求的 fresh、安装后部署隔离已满足；
- Invocation 只由 bundled Runtime Contract 构造；
- Behavior 未读取开发仓库 `docs/**`、`tests/**`、Handoff 或其他开发资产；
- Discovery、显式调用、未调用对照、安装缓存路径、权限与实际 Runtime 结果均有本轮直接证据；
- `REV-005` 判定为 `passed`，Codex CLI TUI Behavior 维持 `Verified`；
- 该结论不外推到 Codex Desktop / App、Cursor 或 Claude Code。

## 未改变与未执行

- `DESIGN.md`、`EVAL-PLAN.md`、`EVAL-RESULTS.md`、`REVIEW-RESULTS.md` 未修改；
- Runtime Contract、Runtime、Formal Fixture、Expected Outcome、Validator 与 Eval Oracle 未修改；
- 未执行 Cursor / Claude Code Adapt、fresh Review、`finalize`、commit、push、merge、rebase、
  tag 或 release。
