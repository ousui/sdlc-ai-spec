# Remaining Phase Foundation Contracts

## 1. 目标

本文件冻结 PLN 之后、IMP/VFY/RLS 实现所需的共享基础设计。它不创建新的 Lifecycle Phase，也不改变 Core Artifact Contract。

```text
Claim Provider
Resource Result
Execution Evidence
Effect Authorization
```

这些能力由 Phase Skill 调用，但不得拥有第二套 Artifact Gate、Final Confirmation 或业务结论。

## 2. Local Claim Provider

### 2.1 稳定 Contract

计划 Contract ID：

```text
sdlc-ai-spec/runtime/imp-claim/v1
```

默认实现：

```text
packages/sdlc_claim_provider/
```

物理存储使用项目内 `.sdlc/store.sqlite3` 的 namespaced Claim tables；Claim Provider 只管理自己的表和事务，ArtifactStore 不直接操作 Claim 表。额外表不得改变 ArtifactStore 九个逻辑操作的语义。

### 2.2 Claim Record

```text
binding_lineage_key
current_binding_reference
imp_artifact_id
imp_revision
attempt
state: active|completed|abandoned
owner
execution_scope[]
dependency_result_references[]
rework_references[]
created_at
updated_at
completed_at
abandoned_by
abandoned_at
abandon_reason
generation
```

不含 Artifact Payload、Gate、产品 Result 内容或隐藏推理。

### 2.3 Operations

#### `resolve`

- 按 Binding 或 Lineage 返回唯一 Current Claim；
- 绝对只读；
- 历史 Attempt 可列出但不自动回退为 Current。

#### `acquire`

原子完成：

1. 规范化 Binding、Lineage、Owner、Scope、Dependency 和 Rework Set；
2. 检查同 Lineage Current Claim；
3. 检查 canonical `resource:<id>` 冲突；
4. 首次分配稳定 IMP Artifact ID；
5. 分配 Attempt 与目标 Revision Reservation；
6. 写入 `active` Current Claim。

相同请求幂等返回；不同请求返回 mismatch。completed 只有合法非空 Rework 才新 Attempt；abandoned 只有显式 retry/rework 才新 Attempt。

#### `abandon`

只接受：

- open Revision 已被 ArtifactStore abandon 的普通放弃；
- frozen Revision 的 complete 已明确不可成功的最终化失败恢复。

必须 CAS 匹配 Lineage、Attempt、Revision、Owner、generation 和 active State。

#### `complete`

前置：

- Artifact Revision 已 frozen；
- Gate 通过；
- Binding/Owner/Attempt/Revision 匹配；
- Dependency Result References 与递归 Current completed Claim 仍一致；
- Resource 链仍连续。

成功 CAS `active → completed`；相同请求幂等。

### 2.4 Invariants

- 一个 Binding Lineage ↔ 一个稳定 IMP Artifact ID；
- 同一 Lineage 只有一个 Current Claim；
- active Claims 的 Resource Scope 不冲突；
- Attempt 单调递增且不复用；
- Claim 分配 Artifact ID/Revision，ArtifactStore 只采用并校验；
- frozen+active 是允许的短暂状态，但不可供下游使用；
- Claim State 不是 Artifact Status。

### 2.5 Read-only Catalog

提供只读 Catalog 给 Lifecycle Query：

```text
list_current_claims
list_attempts(lineage)
resolve_resource_owner(resource)
```

Query 不直接 SQL，不写 Claim。

## 3. Resource Result Foundation

### 3.1 稳定 Contract

计划 Contract ID：

```text
sdlc-ai-spec/runtime/resource-result/v1
```

默认实现：

```text
packages/sdlc_resource/
```

### 3.2 Resource Registry

每个 versioned resource 使用项目内 canonical ID：

```text
resource:<versioned-resource-id>
```

Registry 记录：

```text
resource_id
project_relative_root
kind
vcs_repository_root
result_locator_scheme
```

ID 不能重叠；无法证明两个单元不相交时使用最小共同上层 Resource。

### 3.3 Baseline Snapshot

Baseline 必须表示首次产品修改前的真实状态：

- tracked、staged、unstaged、untracked 和必要元数据；
- 用户已有修改不丢失；
- `HEAD` 只有与真实工作区完全一致时才可作为 Baseline；
- 全新 Resource 使用可复核的未创建 Evidence；
- Snapshot 不修改用户 index、branch、tag 或 remote。

### 3.4 Immutable Result

支持：

```text
vcs:<resource>@<full-immutable-object-id>
member:<artifact-reference>/<member-id>@sha256:...
```

实际 Scheme 由 Resource Registry 明确。禁止：branch、可移动 tag、latest/current、当前工作树、无摘要临时文件、仅 path。

### 3.5 Diff 与 Scope

```text
capture_baseline(resource)
prepare_isolated_view(resource, baseline)
compare(baseline, candidate)
materialize_result(resource, candidate)
verify_result(locator)
```

- Changed Scope 必须是 Claim Scope 子集；
- actual changed Resource 必须有 immutable Result；
- Patch/Diff 仅作审计材料，不能替代完整 Result；
- no-change Resource 按 IMP Spec 保存 Baseline=Result。

### 3.6 Safety

- 不自动 commit/push/merge/tag；
- 不删除用户未纳入 Baseline 的内容；
- 失败时保留可恢复现场或准确恢复；
- 不读取 Project Root 外内容；
- 大型/二进制内容可存 Snapshot Member，但必须有摘要和保留策略。

## 4. Execution Evidence

### 4.1 稳定 Contract

第二个真实使用者出现并证明复用后，计划 Contract ID：

```text
sdlc-ai-spec/runtime/execution-evidence/v1
```

实现候选：

```text
packages/sdlc_execution/
```

### 4.2 Data Model

```text
ExecutionSpec
  execution_id
  executor
  working_directory
  subject_references[]
  command_or_manual_procedure
  environment_summary
  timeout
  expected_result
  evidence_requirement

ExecutionResult
  started_at
  completed_at
  state
  exit_or_manual_result
  observed
  stdout_summary
  stderr_summary
  evidence_members[]
  redactions[]
  target_effect
```

### 4.3 Boundary

- 不选择 Phase Result；
- 不决定 Gate、Conclusion 或 Follow-up；
- 不安装依赖；
- 不扩大工作目录和权限；
- 真实 stdout/stderr/报告先脱敏，再作为 Supporting Member；
- manual/hybrid 结果必须记录执行身份和真实观察；
- timeout/cancel/partial 必须可区分。

IMP 可先以私有实现验证接口；VFY 第二次出现相同模型时再提取共享包。RLS 可以复用 Evidence 模型，但外部效果仍受独立授权。

## 5. Effect Authorization

### 5.1 稳定 Contract

计划 Contract ID：

```text
sdlc-ai-spec/runtime/effect-authorization/v1
```

它是短期执行授权记录，不是 Lifecycle Artifact、Exception、Final Confirmation 或长期凭证。

### 5.2 Binding

```text
artifact_reference
operation
subject_or_result_references[]
target
item_references[]
pre_execution_digest
authorizer
authorized_at
expires_at_or_single_use
```

### 5.3 Rules

- RLS Target effect 必须使用；
- IMP 项目内 Claim Scope 产品修改由显式 Skill 调用和 `write_policy` 控制，不使用外部 Effect Authorization；
- Contract/Input/Target/Item/Digest 任一变化使授权失效；
- 默认 single-use；
- 不保存 Secret、Token 或可重复使用的远端凭证；
- 自动化委托必须准确限定目标和条件；
- Final Confirmation 不授予执行权限。

## 6. Transaction and Failure Order

### IMP

```text
resolve/readiness
→ claim acquire
→ ArtifactStore control reservation
→ materialize open payload
→ product execution/result
→ gate/freeze
→ claim complete
```

每一步失败都有确定恢复，不跨 Authority 假装单事务。

### VFY

```text
resolve subject
→ persist method contract
→ pre-execution readback
→ execute/record evidence
→ persist method result
→ aggregate conclusion/return
→ gate/freeze
```

### RLS

```text
persist release contract/checklist
→ readback
→ effect authorization
→ execute RLI
→ capture target evidence
→ execute RCF
→ conclusion/gate/freeze
```

## 7. Foundation Eval

必须覆盖：

- 并发与 CAS；
- Resource 冲突；
- stale binding/input/owner；
- Baseline 含用户变化；
- immutable Result 读回；
- 无 Git Ref/远端写入；
- Secret 脱敏；
- timeout/cancel/partial；
- stale/single-use Effect Authorization；
- crash recovery；
- Query 绝对只读；
- Runtime Independence；
- 与 ArtifactStore 全量回归兼容。

这些 Foundation 在各自实现前仍需要 Maintainer approval，但其逻辑边界已在本批设计中冻结，不再重新讨论是否需要或归属哪个 Skill。
