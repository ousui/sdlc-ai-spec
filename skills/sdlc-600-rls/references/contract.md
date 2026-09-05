# RLS Bundled Runtime Contract — final

Contract: `sdlc-ai-spec/rls-runtime/v1`

This bundled contract implements deterministic RLS over the shared ArtifactStore.
It has no network, dependency installation, arbitrary process or production release
capability. Accepted VFY upstream is 46509eb6688df30e71ed094132b2d10e81ceb2ac.

## Entry predicate

Only `read_vfy_candidate` can produce final persisted Authority. It reads an exact
frozen VFY Revision through the shared Store and Core Authority verifier, validates
Primary/State/Manifest/Evidence, reconstructs Final Confirmation, recomputes the
producer full-state source digest and a separate Candidate digest, and compares
current IMP Claims, complete Result Set, Scope, controls and scoped Exceptions.
No standalone Candidate Member exists. A caller-provided JSON is never authority.
Historical pure parsers remain solely for explicit compatibility/negative tests.
Required RLS must be ready; n/a and waived create no Artifact or effect. Pending,
early-stop, stale/current-set mismatch and unresolved Return/Control block entry.
A scoped product-failure Exception preserves the original VFY failure conclusion.

## Release contract

One RLS Revision binds exactly one Release Reference, Scope, Result Set, VFY
Reference, Target, pre-effect Target Baseline, RLI set, RCF set and Checklist.
The Contract preserves both the VFY state `source_digest` supplied by VFY and an
RLS-computed `vfy_candidate_digest` over the exact candidate transport bytes.
It also preserves VFY Exception references, final readiness, Status and Gate.
Scope/Result changes return upstream. A target change creates a new Artifact.
Retry keeps the Artifact ID but creates a new Revision and reacquires Baseline
and Effect Authorization.

## Effect authorization

`create` does not require Effect Authorization. Every `execute` target effect
requires a current authorization that binds the exact Artifact ID/Reference,
Revision, Release/Scope/Result/VFY references, VFY source and candidate digests,
Target, Baseline digest, the complete Release Contract digest, selected RLI IDs
and action summaries, selected RLI contract digest, complete RLI-set digest,
complete RCF-set digest, Checklist digest, authorizer identity, validity
interval and Effect Digest.

Effect binding uses an immutable Item Contract projection. RLI `result`,
`follow_up` and Evidence references, plus RCF `result`, `follow_up`, Evidence
references and `observed`, are execution outcomes rather than pre-effect Contract
fields. A legitimate outcome transition therefore does not self-invalidate the
historical authorization. Authorization issuance and reuse still require every
selected RLI to be `pending`; any immutable field change in a selected or
unselected RLI, any RCF Contract change, or any Release Contract change makes the
old authorization stale.

A terminal RLI cannot receive a fresh execution authorization. `write_policy`,
filesystem/GitHub access, Approval/Trigger, Final Confirmation and prior
authorization never substitute for Effect Authorization. Final Confirmation is
computed over the projected frozen Artifact identity so its digest is stable
before and after the actual Store freeze.

Immediately after authorization validation and before any target or Evidence
write, the Runtime compares the actual Sandbox Target with the Contract Baseline
for the first operation, or with the last RLS-observed post-effect snapshot for a
later operation. Any mismatch invalidates execution with zero new effect. The
complete authorization record is retained in an append-only per-Revision audit
history; a reduced ID-only projection is not sufficient evidence.

## Target boundary

The only supported target is a dedicated directory below the operating
system temporary directory. It supports baseline, no-op, success, partial,
failure, pre-effect cancellation, target-side confirmation, immutable
content-addressed Evidence and cleanup. `REAL_TARGET_EFFECTS` is always zero.
Target identity is checked against the Release Contract for execute, confirm,
check and cancel. Secret-like data is rejected before immutable Evidence bytes
are created.

## Interface behavior

`--input/-i` and `--item` are repeatable and preserve first-occurrence order.
`auto` may select all currently pending RLI or RCF only when that action is the
unique state-machine transition; effect execution still requires an exact
Authorization covering the complete auto-selected RLI set. Explicit Artifact and Target selectors must match the exact persisted Revision.

## State and conclusion

Release Conclusion is `pending|success|partial|failed|cancelled`. Follow-up is
`none|retry_rls|return_req|return_dsn|return_pln|return_imp`. Artifact Gate and
product/target outcome are independent. Accurate `failed`, `partial` or
`cancelled` records may freeze with Gate pass; Gate pass never means release
success. Cancellation is legal only before any target effect and only while the
actual target still matches the expected Contract/last-observed state.

## Persistence and confirmation

Shared Store allocations return objects; writes use the exact Revision generation.
First-write failure abandons the new reservation. Immutable contract and historical
authorizations cannot change within a Revision. Primary, RLS-STATE, every Evidence
Member and the Manifest must agree byte-for-byte. CTX context, profile and direct
inputs are separate from Scope, Artifact Status, Gate and Release Conclusion.
Final State Member omits Final Confirmation to avoid a digest cycle; the Primary
contains the Core confirmation table. Freeze requires approved DomainVerification
bound to the current payload and a separately approved current Core authority.
`check -r` opens only read-only Store APIs and never writes Target or Evidence.

## Trusted host and recovery boundary

`TrustedEffectRecords.grant` is a host integration API, invoked only after explicit
approval. No business CLI command creates a grant. Immutable grant and one-time
consumption files bind complete authorization bytes and real runtime time. The
trust boundary is the project-local host/filesystem, not cryptographic isolation
from a malicious same-user process. Arbitrary self-described JSON is insufficient.
The complete Release Contract digest also binds the Sandbox location, not only ID.

Each selected item has a durable pre-effect intent, observed state/evidence and
CAS persistence receipt. If an exception occurs, earlier item effects remain;
unknown effects prevent cancellation, abandon, retry and freeze. Missing post-write
receipt requires explicit reconciliation; automatic replay is forbidden. Journal
records are recoverable outside the failed payload and never contain exception
text, Secret or fabricated no-effect assertions.

## Local path and projection boundary

All Sandbox file access uses directory descriptors and O_NOFOLLOW, rejects path
traversal and symlinks, and atomically writes state plus exclusive Evidence files.
Only local temporary Sandbox effects are supported; real target effects remain 0.
Shared lifecycle/status adds RLS fields without changing VFY conclusions. Frozen
Return controls use exact #RLI-NNN or #RCF-NNN references and shared ControlInputResolver.

## 当前风险授权与 Exception

`TrustedRlsExceptions.grant` 仅供可信宿主在明确风险批准后调用，每个 Revision 支持一条 `EX-900`，绑定准确 Revision、不可变效果合约、完整再次豁免项集合、批准人与有效期。业务 `execute/confirm` 只能携带已存在的 `exception_authorization`，选中项必须与批准集合一致；任意字符串、旧 VFY Exception 或自述 JSON 不能构成新授权。无真实目标效果授权从此记录派生。

真实 VFY Exception 在 RLS 中按准确来源建立 carried 行。全部映射 RCF 的实际 pass/fail 与 Evidence 才可 resolved；pending/not_run 保持 carried；再次 waived 必须由当前 RLS active 授权完整覆盖后 superseded，VFY 原记录不改。存在未关闭 Exception 时使用 pass_with_exception 与 ready_with_exception，Final Confirmation 必须由 Core 认可的人类模式显式接受准确集合，委托模式不能接受风险。

status 使用独立 `rls-projection.schema.json` 作 additive 扩展，既有 VFY 锁定的 status-result/v1 字节保持不变。

`release_target_obligations` 保留真实 producer 的 wire 值；adapter 另外从冻结 Method、Target、Exception 和 RLS Work Item 推导 `obligation_source_references`。承接 waived Method 的每条 RCF 必须同时引用准确 VFY Method、原 Target 与来源 Exception，逐项保留原 Confirmation、Expected、Evidence Requirement。waived VFY Method 的 Evidence 引用其准确 Exception，pass/fail Method 仍必须具有实际 Supporting Evidence，二者不能混淆。

## RLS-WEB-001/002 修订：RCF 可判定语义

`rls_confirmation_policy.py` 只执行以下明确合约，不使用关键字猜测、eval、任意命令或“版本相等即所有检查通过”的兜底。未知合约返回 `RLS_CONFIRMATION_CAPABILITY_UNAVAILABLE`，保留原 Expected 与 pending 状态；不得为了通过而改写冻结 VFY 义务。新无下游义务 RCF 的默认项只声明版本检查，不声称基本可用性已经得到证明。

1. 版本观察的精确三字段：
   - Confirmation: `Observe the authorized local Sandbox release`
   - Expected: `The target version equals the bound release reference`
   - Evidence Requirement: `Immutable target-side snapshot after the selected RLI`
   这只比较 `version`，不证明健康、配置、数据或人工验收。
2. 有界状态相等判定：Confirmation=`Compare the declared Sandbox state fields`；Evidence Requirement=`Immutable target-side snapshot and per-field equality results`；Expected 为 JSON 字符串，例如：

```json
{"contract":"sdlc-ai-spec/sandbox-state-expectation/v1","equals":{"health":"healthy","version":"1.0.0"}}
```

只支持 1..16 个明确顶层字段与有限 JSON 标量；字段缺失、类型不同或任一不匹配返回实际 fail。重复 JSON key、嵌套路径、非有限值、未知合约一律拒绝。Evidence 保留每字段实际值、期望值、匹配结果和完整 RCF 合约摘要。`force_fail` 只作为显式 Sandbox 故障注入使自动判定失败，不能产生 PASS 或覆盖人工结论。

## RLS-WEB-002 修订：人工观察而非自述批准

人工 RCF 必须在发版前登记 `subjective=true`、非空 `scenario` 以及 `max_observation_age_seconds`（默认 900，允许 1..3600）。原 Confirmation、Expected 与 Evidence Requirement 不变。当前执行时间不能由 CLI 覆盖。

可信宿主在真实观察后调用 `TrustedHumanObservations.record`，显式提供 `attested=true`、contracted executor 身份、RFC3339 observed_at、独立明确的 pass/fail、observation，以及最多 64 KiB 的原始 UTF-8 source_bytes；该 API 不接受任意文件路径。宿主对观察真实性和文本语义负责；Runtime 不用自然语言推断“已接受”。人工 fail 必须保持 fail；不支持的来源格式或非明确判定不能变为 PASS。

记录绑定准确 RLS Revision/RCF、Release、Scope、Result Set、VFY 双摘要、完整 Release/RCF 合约摘要、场景、执行身份、Target ID/位置/当前 snapshot 摘要和有效时间。记录与原始来源在项目 `.sdlc/authority/rls-human-observations`、`rls-human-observation-sources` 中以内容寻址、exclusive/no-follow 方式保存。Secret、畸形/未来/过期时间、身份不匹配和超界内容在首次写入前拒绝。

业务 `confirm` 只能携带已存在的 host record，不能从 stdin 制造该 Authority。一个 record 只能对应一个准确 RCF；批量人工观察使用 RCF ID 到 record 的精确映射。服务及冻结 DomainVerifier 重新读取 host record/source bytes；仅一个自述 digest 或哈希正确的伪造 PASS 不足以通过。有效期限制观察被消费的时刻，不错误地使后来历史读回失效。

这是项目可信宿主/文件系统边界，不是对恶意同用户进程的密码学隔离；人工观察既不是 Effect Authorization，也不是 Final Confirmation 或风险豁免。三类 Authority 不可互相替代。

## 批量确认与历史复核

所有选中项先完成无写入预检；任何未知判定、终态项或错误人工记录使整个预检失败。执行时逐项重查 Target，记录真实结果并通过原共享 Store CAS 持久化，后项 I/O 失败不能丢弃已经持久化的前项结果。失败的 CAS 不声称该项已持久化。确认不执行发布效果；既有不确定效果日志仍阻止重放和假取消。

正式 RCF Evidence 必须同时包含 `confirmation_binding` 与 `confirmation_evaluation`。纯 Evidence verifier 从实际 Observed 和冻结 Expected 重算自动结果；人工结果从严格绑定的记录取得，并由服务/DomainVerifier 复核原始来源。旧版本的不足记录不能自动升级成修复后的正式 Authority。准确 fail 仍可形成可信 Gate pass；未知/未执行不可以。
