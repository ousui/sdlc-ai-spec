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
