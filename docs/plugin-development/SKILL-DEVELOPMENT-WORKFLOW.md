# Skill Development Workflow

## 1. 目的

用可审查、可跨会话交接的方式重复开发正式 Phase Skill。

每个 Skill 使用：

```text
design → approval → implement → evaluate → adapt → review → finalize
```

一次会话只处理一个阶段。

## 2. 命名与分支

正式 Skill：

```text
sdlc-NNN-xxx
```

分支：

```text
skill/sdlc-NNN-xxx
```

Work Item：

```text
docs/plugin-development/work-items/sdlc-NNN-xxx/
```

目录名、Front Matter `name`、Work Item 和分支中的 Skill 名必须一致。

## 3. design

产物：

```text
DESIGN.md
EVAL-PLAN.md
```

必须明确：

- 单一职责；
- design-time Source；
- bundled Runtime Contract；
- shared Runtime Contract；
- shared Package；
- 输入输出 Envelope；
- Builder / Validator / Store 边界；
- Runtime Independence；
- Trigger、Failure、权限和 Eval。

禁止创建正式 `SKILL.md`。

Design DoD 满足且阻塞项为零时可标记 `ready`，不得自行批准。

## 4. approval

Maintainer 明确：

```text
approve-design
reject-design
```

批准只记录决定并把下一工作包设为 implement；不在同一会话实现。

## 5. implement

依据已批准 Design 创建最小 Runtime：

```text
skills/sdlc-NNN-xxx/
```

实现应包含：

- 精简 `SKILL.md`；
- 阶段 `references/contract.md`；
- 构建来源 `source-lock.json`；
- 必要模板；
- 单一 Runtime Adapter；
- 自动化单元测试。

运行时不得读取 `docs/**`。

实现阶段包含 Producer Self-Verify，但不冒充正式 Eval。

## 6. evaluate

使用固定 Fixture 和 Expected Outcome，fresh context 执行：

- 正向显式调用；
- 负向/未调用；
- 完整输入；
- 缺失输入；
- 边界/冲突；
- with-skill / without-skill；
- Runtime Independence；
- Shared Contract；
- 未授权 Skill 调用；
- Store / Validator 失败。

实现者不得修改 Oracle 迁就结果。

## 7. adapt

一次只处理一个 Agent Client / Surface。

平台适配只处理：

- Discovery；
- Manifest / metadata；
- 显式调用；
- 路径；
- 权限；
- 实际宿主行为。

不得改变 Runtime Contract。

## 8. review

fresh context、默认只读：

- Design 与实现一致性；
- Spec → Runtime 一致性；
- Shared Contract；
- Runtime Independence；
- 程序化输入输出；
- Store / Validator 分层；
- Eval 证据；
- 安全与复杂度。

Verdict：

```text
PASS
PASS WITH REQUIRED CHANGES
FAIL
```

## 9. finalize

Maintainer 明确最终接受后：

- 记录完成；
- 更新兼容性与 Handoff；
- 不自动 merge、push、tag 或 release。

## 10. 阶段转换

| From | To | Minimum Gate |
|---|---|---|
| design | approval | ready，阻塞项=0，Eval Plan 可判定 |
| approval | implement | Maintainer approved |
| implement | evaluate | Runtime 存在，单元测试与 Self-Verify 通过 |
| evaluate | adapt | Critical Case 全通过 |
| adapt | review | 目标 Client 有实际证据 |
| review | finalize | Review PASS，阻塞 Finding=0 |
| finalize | complete | Maintainer accept-final |

不满足条件必须返回准确阶段，不得“后面再补”。

## 11. 会话结束

每轮结束必须：

1. 运行阶段检查；
2. `git diff --check`；
3. 更新 Handoff；
4. 只登记一个下一工作包；
5. 本地 commit 仅在获授权时执行；
6. 不自动 push；
7. 停止。
