# Skill Eval Plan — `sdlc-400-imp`

## 1. 元数据

| Field | Value |
|---|---|
| Skill | `sdlc-400-imp` |
| Status | `ready` |
| Design | `DESIGN.md` |
| Oracle | v1.1 Core / Store / IMP 与批准后的 Claim、Resource Contract |
| Maintainer Decision | `pending` |

Claim Provider 与 Resource Foundation 的 Eval 必须先独立通过；IMP 不得用私有 Mock 替代正式共享 Contract 的核心行为。

## 2. 测试层

1. Claim Provider Contract；
2. Resource/Baseline/Result Contract；
3. Interface 与 `abandon`；
4. Readiness、Method、Scope、Result、Checks；
5. Store + Claim 跨 Authority 状态机；
6. 项目工作区真实修改与恢复；
7. Lifecycle Query；
8. Runtime Independence、Source Lock、全仓回归；
9. Codex 静态与真实宿主证据。

## 3. Foundation Critical Cases

### Claim Provider

| ID | Case | Expected |
|---|---|---|
| IMP-F001 | 同 Lineage 首次 acquire | 唯一 IMP ID、Attempt=1、Revision Reservation=1、active |
| IMP-F002 | 并发 acquire 同 Lineage | 只有一个成功，其余幂等或 conflict |
| IMP-F003 | 不同 Lineage 共享 resource | 原子冲突，不能双重 active |
| IMP-F004 | active 完全相同请求 | 幂等返回当前 Attempt |
| IMP-F005 | active 请求 Binding/Input/Rework 不同 | mismatch |
| IMP-F006 | completed 无 Rework 再领取 | 返回现有 completed，不新 Attempt |
| IMP-F007 | completed + 合法非空 Rework | Attempt+1，IMP ID 不变，新 Revision Reservation |
| IMP-F008 | abandoned 显式 retry | Attempt+1 |
| IMP-F009 | abandon Owner/Attempt/Revision 不匹配 | CAS fail，Claim 不变 |
| IMP-F010 | complete 依赖链失效 | fail，Claim 保持 active |
| IMP-F011 | complete 幂等重试 | 已 completed 时成功返回同记录 |
| IMP-F012 | 历史 Attempt 不参与 Current 权威 | PASS |

### Resource

| ID | Case | Expected |
|---|---|---|
| IMP-F013 | clean VCS resource Baseline | 完整 immutable Locator |
| IMP-F014 | 有用户未提交变化 | Baseline 捕获真实工作区，不用 HEAD 冒充 |
| IMP-F015 | 新资源 | N/A Baseline + 未创建 Evidence |
| IMP-F016 | Result 不可变且可读回 | PASS |
| IMP-F017 | 分支/可移动 tag/latest/current | 拒绝为 Result |
| IMP-F018 | Result 超出 Claim Scope | fail |
| IMP-F019 | Changed Scope 缺 resource token | fail |
| IMP-F020 | 不移动 Git Ref、不自动 commit/push | PASS |

## 4. IMP Critical Cases

### Interface 与 Binding

| ID | Case | Expected |
|---|---|---|
| IMP-E001 | 裸调用唯一可执行 WI | auto create |
| IMP-E002 | 多个 WI | 列出候选，用户选择 |
| IMP-E003 | `create --binding PLN@N#WI` | acquire + execute |
| IMP-E004 | `revise -r IMP@N` active/open | 继续同 Attempt/Revision |
| IMP-E005 | `check -r IMP@N` | 绝对只读 |
| IMP-E006 | `abandon -r IMP@N` | 仅合法 active/open 路径终结 |
| IMP-E007 | meta command | 零扫描、零 Claim、零写入 |
| IMP-E008 | 模糊 Binding/非准确 Revision | fail closed |
| IMP-E009 | Owner 无法唯一确定 | action_required |

### Readiness 与上游返回

| ID | Case | Expected |
|---|---|---|
| IMP-E010 | PLN required WI 完整 | Readiness pass |
| IMP-E011 | WI Target Phase 非 IMP | reject |
| IMP-E012 | PLN pending/n/a 路径不符合直接 Binding | 返回 PLN |
| IMP-E013 | Dependency Current Claim 非 completed | blocked |
| IMP-E014 | 依赖后继 inputs 未含当前前驱 Result | blocked |
| IMP-E015 | Binding/Scope/Resource 不一对一 | 返回 PLN |
| IMP-E016 | Requirement 语义不清 | RETURN_TO_REQUIREMENT |
| IMP-E017 | Design Decision 缺失 | RETURN_TO_DESIGN |
| IMP-E018 | Work Item 粒度/依赖错误 | RETURN_TO_PLAN |
| IMP-E019 | VFY Return Phase=IMP 同 Lineage | 合法 Rework |
| IMP-E020 | return_imp RLS Issue 无唯一 Lineage | 返回 PLN |
| IMP-E021 | stale/incomplete Rework Set | mismatch |

### Method Contract

| ID | Case | Expected |
|---|---|---|
| IMP-E022 | 7 项 Consideration 固定顺序 | PASS |
| IMP-E023 | required Consideration 无 Step | pending/fail |
| IMP-E024 | n/a 无客观原因 | fail |
| IMP-E025 | waived 无 Exception | fail |
| IMP-E026 | pending 试图 Gate pass | fail |
| IMP-E027 | Step 按文件机械拆分 | Review/Eval fail |
| IMP-E028 | Step 跨越不同事务/失败边界 | 必须拆分 |
| IMP-E029 | 新公共抽象/依赖无 DSN Decision | RETURN_TO_DESIGN |
| IMP-E030 | 推测性重构或 Scope Expansion | IMP-G-002/003 fail |
| IMP-E031 | Method Block ID 跨 Revision 稳定 | PASS |

### 产品修改与 Result

| ID | Case | Expected |
|---|---|---|
| IMP-E032 | write_policy=deny | 只做 Readiness/Preview，零产品写入 |
| IMP-E033 | auto 写入 Claim Scope | 只改声明范围 |
| IMP-E034 | 试图修改 Scope 外文件 | 阻止并恢复/保留现场 Evidence |
| IMP-E035 | 用户既有变化 | 保留且包含在 Baseline，不丢失 |
| IMP-E036 | 一个 resource 多文件 | 一个 RES 行 |
| IMP-E037 | 多 resource | 每个 resource 恰一行 |
| IMP-E038 | 未改变 resource | Baseline=Result、Changed Scope=None |
| IMP-E039 | Patch 有但完整 Result 缺失 | fail |
| IMP-E040 | Result 读回不一致 | fail |
| IMP-E041 | Candidate pre-existing patch | 从准确 Baseline 重放，不倒签 Claim |
| IMP-E042 | Secret 出现在 Artifact/Evidence | 拒绝或脱敏，不泄露 |

### Checks、Gate 与状态机

| ID | Case | Expected |
|---|---|---|
| IMP-E043 | 格式/构建/单测等适用 Check | 保存 CHK 与 Evidence |
| IMP-E044 | 适用 Check 未执行写 n/a | fail |
| IMP-E045 | 局部 Check pass | 只表示 VFY ready，不宣称产品通过 |
| IMP-E046 | missing Final Confirmation | open waiting_input |
| IMP-E047 | stale Final Confirmation | open/failed，不 freeze |
| IMP-E048 | frozen + complete success | VFY 可用 |
| IMP-E049 | frozen + Claim active | 不供 VFY 使用 |
| IMP-E050 | complete CAS transient fail | 相同条件重试，不重写 Artifact |
| IMP-E051 | complete 因依赖失效永久失败 | frozen 历史 + Claim abandoned |
| IMP-E052 | pre-freeze abandon | Revision abandoned 后 Claim abandoned |
| IMP-E053 | build failure after allocation | 新 Revision Reservation abandoned |
| IMP-E054 | frozen no-change rework | 按 Spec 控制恢复，不继承 Authority |
| IMP-E055 |篡改 Binding/Result/Status/Member/Digest | check fail |

### Revision 与依赖链

| ID | Case | Expected |
|---|---|---|
| IMP-E056 | active/open 修订 | 同 Revision |
| IMP-E057 | completed 合法 Rework | 同 IMP ID、新 Attempt、新 Revision |
| IMP-E058 | no-change 普通 revise | 不创建空 Revision |
| IMP-E059 | 前驱产生新 Attempt | 旧后继失去 current validity |
| IMP-E060 | 同 resource 链连续 | Baseline=前驱 Current Result |
| IMP-E061 | 同 resource 两个无序 active Work Item | Claim conflict |
| IMP-E062 | VFY 查询终端链 | 只采用唯一 current completed 链尾 |

## 5. Lifecycle Query

- Current active → 前沿 IMP，显示 Owner/Attempt；
- abandoned → action required retry/rework；
- frozen+active → 仍在 IMP；
- frozen+completed → 可进入 VFY；
- dependency changed → 所有受影响后继失效；
- Query 不修改 Claim 或 Artifact。

## 6. 真实项目测试

使用临时 clone 或可丢弃 Worktree：

1. 建立 CTX→REQ→DSN→PLN；
2. 选一个范围小、可自动检查的真实 WI；
3. 捕获包含工作区状态的 Baseline；
4. acquire Claim；
5. 实施局部变化；
6. 执行项目已有构建/单测，不安装依赖；
7. 形成 immutable Result；
8. freeze + complete；
9. 验证源项目无远端写入，用户既有变化未丢失；
10. 清理临时测试现场。

项目专用 Fixture/测试不得进入主仓库。

## 7. Runtime Independence

安装副本保留 IMP Skill、Shared Runtime、ArtifactStore、Claim Provider、Resource 包和必要执行包；删除 docs/tests/Handoff 后执行完整 Readiness、Claim、dry-run、局部临时资源实施、Result、check、abandon。

扫描生产 Runtime，禁止开发路径、固定用户路径、网络下载和依赖安装。

## 8. Source Lock

Source Lock 必须覆盖所有稳定 Runtime Contract 和设计来源。Claim/Resource Contract ID 未批准前 Eval Plan 不固定最终数量；实现审批时必须先冻结集合，之后缺失、额外、重复、排序或摘要漂移均失败。

## 9. Host Evidence

真实 Codex 至少验证：

```text
/sdlc-400-imp --help
/sdlc-400-imp
/sdlc-400-imp create --binding <exact>
/sdlc-400-imp check -r <exact IMP>
/sdlc-400-imp abandon -r <open IMP>
```

明确区分：Agent 生成代码、Runtime 修改工作区、Claim Authority 和真实宿主权限。

## 10. PASS 条件

- Claim Foundation 与 Resource Foundation 独立 PASS；
- 所有 Critical Case PASS；
- 真实项目局部实施 PASS；
- Runtime Independence、Source Lock、全仓回归 PASS；
- Review 无 Blocker/Major；
- 产品结果和 Claim 远端分支证据完整；
- 未执行 Git/远端副作用；
- 未验证兼容性不虚报。
