# Skill Design Contract — `<sdlc-NNN-xxx>`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `<sdlc-NNN-xxx>` |
| Stage | `design` |
| Status | `draft` |
| Intended Plugin | `sdlc-ai-spec` |
| Design-time Source | `<docs/v1.x paths>` |
| Bundled Runtime Contract | `<skill references/assets/scripts>` |
| Shared Runtime Contract | `skills/_shared/**` |
| Shared Package | `<packages/... or None>` |
| Work Item | `docs/plugin-development/work-items/<skill-name>/` |

允许状态：`draft / ready / approved / superseded`。

## 2. Problem 与用户结果

### Problem

`<缺少什么稳定能力>`

### Intended User Outcome

`<可观察结果>`

## 3. 单一职责

### In Scope

- `<唯一阶段工作流>`

### Out of Scope

- `<相邻但不负责的能力>`

## 4. Trigger Contract

### 应触发

| ID | 场景 | 示例 | Invocation |
|---|---|---|---|
| TRG-P01 | | | `explicit` |

### 不应触发

| ID | 场景 | 示例 | 应由什么处理 |
|---|---|---|---|
| TRG-N01 | | | |

## 5. Runtime Independence Contract

必须明确：

- 运行时不读取 `docs/**`；
- Plugin 是最小部署单元；
- Skill 不依赖兄弟 Skill；
- 使用哪些 `skills/_shared/**` Contract；
- 使用哪些 `packages/**`；
- 删除 `docs/**` 后如何验证；
- `source-lock.json` 固化哪些 Contract ID、版本和 SHA-256；
- 不手工双写无法校验的 Spec 与 Runtime 内容。

## 6. Input Contract

公共 Envelope 使用 `invocation.schema.json`。

| ID | Phase Input | Required | Validation | Missing Behavior |
|---|---|---:|---|---|
| IN-01 | | yes/no | | |

## 7. Output Contract

公共 Envelope 使用 `result.schema.json`。

| ID | Phase Output | Required Content | Success Condition | Consumer |
|---|---|---|---|---|
| OUT-01 | | | | |

## 8. Workflow Contract

1. 解析标准请求；
2. 确定执行目标；
3. 收集候选事实；
4. 构造 Phase Payload；
5. 执行 Domain Validator；
6. 通过共享 Package 完成确定性操作；
7. 返回标准结果和人类摘要。

## 9. Shared / Private Boundary

| Resource | Decision |
|---|---|
| `SKILL.md` | |
| `references/contract.md` | |
| `references/source-lock.json` | |
| `assets/` | |
| `scripts/runtime.py` | |
| `skills/_shared/**` | |
| `packages/**` | |

## 10. Failure Contract

| Failure | Detection | Required Behavior | Forbidden Fallback |
|---|---|---|---|
| | | | |

## 11. 权限与副作用

| Capability | Required | Scope | Authorization |
|---|---:|---|---|
| Read project | | | |
| Write Artifact Store | | | |
| Execute runtime | | | |
| Network | | | |
| External write | no | None | explicit only |

## 12. Exclusive Execution

- 显式调用；
- 不调用兄弟 Skill；
- 不传递授权；
- 外部输出仅作 Input / Evidence；
- 无法独立完成时停止；
- 不是硬隔离声明。

## 13. Portability

| Concern | Portable Core | Cursor | Claude Code | Codex |
|---|---|---|---|---|
| Discovery | | | | |
| Explicit invocation | | | | |
| Path resolution | | | | |
| Behavior evidence | | | | |

## 14. Eval Plan

对应：

```text
docs/plugin-development/work-items/<skill-name>/EVAL-PLAN.md
```

必须覆盖 Runtime Independence、Shared Contract 和程序化输入输出。

## 15. Design DoD

- [ ] 名称符合 `sdlc-NNN-xxx`。
- [ ] 单一职责明确。
- [ ] Design-time Source 与 Runtime Contract 分离。
- [ ] Runtime 不读取 `docs/**`。
- [ ] Shared Contract / Package 边界明确。
- [ ] 输入输出 Envelope 明确。
- [ ] Builder / Validator / Store 边界明确。
- [ ] 触发、失败、权限可判定。
- [ ] Runtime Independence Eval 已设计。
- [ ] 阻塞 Open Item=0。
- [ ] 未创建正式 `SKILL.md`。

## 16. Open Items

| ID | Question | Blocks | Expected Source | Status |
|---|---|---|---|---|
| None | No blocking open items | N/A | N/A | closed |

## 17. Maintainer Decision

| Role | Decision | Basis |
|---|---|---|
| Maintainer | `pending / approved / rejected` | |
