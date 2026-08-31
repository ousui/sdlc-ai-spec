# Skill Eval Plan — `sdlc-100-req`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-100-req` |
| Design | `DESIGN.md` |
| Status | `approved` |

## 2. Critical Cases

| Case ID | 场景 | 预期 |
|---|---|---|
| EV-C01 | 完整 create + human Final Confirmation | frozen `ready` REQ，返回准确 Reference |
| EV-C02 | create 缐少业务事实 | materialized open `waiting_input`，持久化 OPI，`action_required` |
| EV-C03 | create 缺写入授权 | 零 Store 写入，`action_required` |
| EV-R01 | revise materialized open | 原 Revision 原地修订，Revision 不增加，generation 增加 |
| EV-R02 | revise frozen | 创建同 Artifact 新最大 Revision，Base Revision 准确 |
| EV-R03 | frozen revise 无有效变化 | 不创建空 Revision，返回 no-change |
| EV-K01 | check frozen ready | 严格只读，完整 Domain Check 通过 |
| EV-K02 | check 缺 Store | 不创建 `.sdlc`，返回 `STORE_NOT_FOUND` |
| EV-F01 | Requirement 来源图循环 | `REQ-G-005=fail`，顶层 `failed` |
| EV-F02 | Acceptance Criteria 未覆盖 Requirement | `REQ-G-006=fail`，顶层 `failed` |
| EV-F03 | stale Final Confirmation | `CORE-G-009=fail`，不得冻结 |
| EV-I01 | CTX 不准确或非 frozen | `failed`，不自动选择其他 CTX |
| EV-I02 | VFY Return Phase 非 REQ | Control Input 失败 |
| EV-I03 | RLS Issue 非 `return_req` | Control Input 失败 |
| EV-X01 | Runtime 删除 docs 后执行 | Critical Fixture 通过，无 docs 路径依赖 |
| EV-X02 | 未显式调用 | Skill 不自动触发 |
| EV-X03 | 兄弟 Skill 隔离 | 无其他 Skill Invocation |
| EV-S01 | source-lock | Contract 集合、版本和原始字节摘要全等 |
| EV-P01 | Codex 配置 | 禁止隐式调用；静态验证只记 Partial |

## 3. Oracle

- Fixture 和期望在实现测试前固定；
- 失败案例不能删除或改为 warning；
- with/without 使用同一输入；
- 真实宿主未执行时不得声明 Verified；
- Eval 记录 Commit、命令、测试数量、失败和重试。

## 4. Pass Gate

- 全部自动化测试通过；
- Runtime Independence 通过；
- source-lock 校验通过；
- 独立 Review 无 Blocker / Major；
- GitHub Actions 成功；
- 无未授权外部副作用。
