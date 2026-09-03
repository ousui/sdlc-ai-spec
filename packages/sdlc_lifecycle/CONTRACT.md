# Lifecycle Query Contract

`packages/sdlc_lifecycle/` 是安装后 Plugin 的严格只读生命周期查询层。

## 稳定标识

| Field | Value |
|---|---|
| Projection Contract | `sdlc-ai-spec/lifecycle-status/v1` |
| Contract Version | `1` |

该 Contract 不进入 Canonical Artifact 的 Evaluation Contract Set，也不提供 Artifact Authority。

## 职责

- 只读列举 Artifact Lineage 和 materialized Revision；
- 解析准确 `Artifact@Revision` 的 Front Matter、Gate、Open Item、Context 和 Input；
- 构建 `context / scope_input / control_input / return / issue` 关系图；
- 以准确 REQ Revision 为根生成祖先、下游、前沿、阻塞和下一动作 Projection；
- 在不写项目的前提下判断 Skill 是否随当前 Plugin 安装；
- 支持一个项目中多个并行 REQ Lineage。

## 严格只读边界

只能使用：

```text
ArtifactStore.open_read_only
ArtifactCatalog
read_revision
verify_digest
FrozenArtifactAuthorityVerifier
ClaimProvider.open_read_only
ClaimProvider.resolve / resolve_artifact
```

禁止：

- `initialize`；
- 直接 SQL；
- 创建 `.sdlc`、数据库、Schema、日志或缓存；
- 修改 Artifact、Gate、Open Item 或 Revision；
- 自动修复 Store；
- 使用 `latest/current` 代替准确 Revision；
- 保存全局 `current_requirement`；
- 把 Projection 写回 Canonical Store。

## Reference 规则

- `inspect_requirement` 只接受准确基础引用：`REQ-...@<数字Revision>`；
- `list_requirements` 可列出每个 Lineage 的所有 materialized 精确 Revision；
- `lineage_head=true` 仅表示列表中该 Lineage 的最高 materialized Revision，不提供 Authority，也不创建 `latest` 别名；
- Item / Member Reference 仅作为 Edge 的 `declared_reference` 保留，节点始终使用基础 Artifact Reference。

## 图语义

```text
source_reference --relation--> target_reference
```

- `context`：CTX 为当前 Artifact 的 Context；
- `scope_input`：基础 Artifact Scope Input；
- `control_input`：通用 Item / Member Control Input；
- `return`：VFY `#RET-NNN` 返工输入；
- `issue`：RLS `#RLI-NNN / #RCF-NNN` 问题输入。

共享 DSN/PLN 等节点可以依赖多个 REQ；查询一个 REQ 时允许展示与其共同支撑同一下游节点的其他准确上游 Revision。

## Projection 状态

`overall_state` 只用于用户查询：

```text
not_started
context_only
context_action_required
selection_required
ready_for_next_phase
in_progress
parallel
action_required
blocked
complete
```

这些值不是新的 Artifact Status、Revision State 或 Gate。

## 失败关闭

以下情况必须返回稳定错误或 blocker，不得忽略：

- Store 缺失或损坏；
- 非准确 Reference；
- Control Reservation 被当作 Artifact；
- 摘要不闭合；
- Canonical Markdown 无法解析；
- Front Matter 与 Store 身份不一致；
- Frozen ready Artifact 的 Authority 无效；
- 声明的依赖不存在；
- Gate / Open Item 状态异常。

## 扩展

新 Phase Skill 合入后，应通过真实 Artifact Fixture 扩充关系和下一阶段测试；核心图模型不应按阶段复制。

## PLN Work Item Projection

- frozen ready PLN 必须解析唯一 `Work Items` 表；
- 下一动作必须绑定准确 `<PLN-ID>@<Revision>#<WI-ID>`；
- 只投影最早 Target Phase 中依赖已满足的 Work Item；
- 同一最早 Target Phase 存在多个候选时全部返回，不静默选择“第一个”；
- Work Item 运行状态不写回 PLN Artifact 或 Store。

## Current IMP Claim Projection

`current_claims` 逐个展示当前 Claim 的准确 Binding、IMP Reservation、Owner、Attempt、
Claim State、Revision State、Outcome、Scope、Dependency Results 与各 Resource Result。
未物化的 Reservation 标记 `materialized=false`，不创建 Artifact 节点。
历史 Artifact 仍保留在 `nodes` 中，不参与 Current Claim 完成判断或当前前沿。

只有以下条件全部成立，Claim Projection 的 `completed` 才为 true：

- Current Claim 为 `completed`，准确 IMP Revision 为 frozen ready 且 Authority 有效；
- Canonical Binding、IMP-STATE、Reservation 与 Current Claim 的 Binding、Owner、Attempt、
  Artifact、Revision、Scope、Dependency Results、Rework References 一致；
- Result Set 对 Claim 中每个 Resource 恰有一行，Baseline、Change、Result Member 可读回，
  Changed Scope 与不可变 Snapshot 一致；
- PLN 的准确直接依赖与所有传递前驱均为 Current completed，后继 inputs 保留准确前驱
  Revision；同 Resource 后继 Baseline 等于唯一前驱终端 Result。

active、abandoned、open、frozen+active 均不能完成 Work Item。前驱新 Attempt 会使
所有仍引用旧 Result 的后继失效。abandoned 请求明确 retry/rework，不自动领取执行权。

`vfy_inputs` 只列出当前有效、唯一终端 Result 所在的准确 IMP Revision；每个入选
Claim 的 `vfy_ready=true`。存在未完成 IMP Work Item、未吸收的前驱更新或无序的同
Resource Result 时，不提供 VFY 输入，也不回退到旧结果或合并多个候选。
VFY 就绪只说明可进入验证；是否安装 `sdlc-500-vfy` 由 `skill_available` 单独表达。
`vfy_results` 明确每个 Resource 的唯一终端 `artifact_reference / result_reference`。
当一个早期 IMP 同时包含多个 Resource、其中部分 Resource 有后继时，只选择尚无
后继的 Resource Result；不能把该 Artifact 内其他旧 Result 也作为终端结果。

查询只读打开 Claim Store，既不初始化缺失 Store，也不修复损坏 Store。每次 inspect
重新读取 Current Claim 与可变 Revision；检测到查询期间 Claim 改变时失败关闭。
无 Claim 的 PLN 保留原有准确 Work Item 候选语义。
已有后续 Artifact 且准确引用当前终端 IMP 时，保留既有后续 Phase 查询路由；
仅作为 Rework 输入的 VFY Return / RLS Issue 不代替当前 IMP 前沿。
