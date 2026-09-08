# VFY Private Runtime Contract — v1

## Authority compiler

Persistent `auto/create/revise` compiles one Candidate from repeatable exact input References. Caller JSON is a hint only. The compiler opens ArtifactStore read-only, uses Frozen Artifact Authority, Lifecycle Query and Current Claim readback, and requires exact equality with:

- one complete REQ/DSN/PLN Scope Source;
- the complete current terminal IMP Product Result Set;
- all authoritative VFOs, or the legal AC/Goal fallback;
- every current VFY Return/RLS Issue through ControlInputResolver;
- every active/carried scoped Exception through its frozen owner Artifact.

Branches, tags, PRs, symbolic latest/current values and lifecycle routing names are never product Subject authority.

Scope fallback and RLS applicability are read from frozen upstream lifecycle tables. VFO Purpose, observable outcome and VFP mapping are compiled from the frozen owner. The required obligation set also includes upstream Method, Pass Criteria, Evidence Contract and applicable PLN VFY Work Items; caller hints cannot omit or replace them.

## Canonical Artifact

The primary Markdown is the human-readable canonical authority and implements the fixed v1.1 VIN, Target, Method, Method Detail, Method Result, fixed Conclusion and Return contracts. Every Item Reference owner Revision appears in Front Matter `inputs`. `VFY-STATE` is a machine Supporting Member, not an alternate authority. The Domain Verifier parses the primary and proves exact primary/state/manifest agreement before freeze.

## Execution and Evidence

Automated commands require the persisted `deterministic-test-v1` positive policy, run in an isolated workspace copy, use no shell or inline arbitrary code, have no network or dependency acquisition, and enforce timeout/output budgets. The source workspace and exact Subject are re-read before and after execution.

Command containment requires an available OS sandbox: macOS `sandbox-exec`, or Linux `bwrap` with working namespaces. It denies network access and writes outside the isolated copy, including effects of subprocesses. Proxy variables are not isolation evidence. Missing or unavailable containment is `VFY_METHOD_NOT_READY`, never an unsandboxed fallback; no sandbox dependency is installed by the Runtime. Escaping source symlinks are rejected before copying.

Manual/hybrid Evidence requires the exact contracted evaluator identity, scenario, expected result, scope, RFC 3339 observation time and immutable source `reference@sha256` object. Evidence is bound to Method, Target, Subject, result, environment, executor, time and Evidence Requirement. Secrets are rejected before persistence.

## Return, Control and Exception

A Return is always created open. Caller input cannot mark it resolved. Resolution is derived only when a later current VFY Revision carries the exact frozen Return/RLS Issue as Control Input, maps it to a Method obligation, uses the changed current Subject Set and records passing Method/Target/Evidence for the required outcome. Every failed Method not accepted by a scoped active Exception has an exact Return.

Waiver and `rls_applicability=waived` require a verified active/carried Exception whose scope covers the affected Method/Target/phase. Valid Exception closure produces `ready_with_exception/pass_with_exception`; downstream projection consumes those states without treating them as unqualified product pass.

## Persistence and read-only behavior

All persistence uses the shared ArtifactStore public API. The VFY Runtime creates no private Store and executes no SQL. Production `check` requires one exact persisted VFY Revision, opens the Store read-only, recomputes canonical/domain/currentness checks and preserves Store plus tracked/untracked product bytes.

## Delivery validation

The authoritative controller runs Skill Interface validation, Source Lock, 80 Case coverage, focused VFY tests, full repository regression, installed-copy Runtime Independence, both fixed external projects and Fresh exact-SHA Attestation. A prewritten review file is not itself an independent review result.

## 独立确认的可读业务快照

`VFY-STATE` 的 `control_projection=sdlc-ai-spec/vfy-state-control-projection/v2` 编码只保存业务状态与实际证据，排除随最终确认单独变化的 `final_confirmation`、`artifact_gate`、`rls_ready`、`next_action` 及 Artifact Status/Revision State。消费者从准确 Store 状态、Canonical Gate 和确认记录重建这些派生字段，仍执行原有领域、摘要和 Authority 验证，不能仅因存在投影标记宣称通过。

自动 Method 完成后先持久化 open draft，CORE-G-009 和 Aggregate Gate 保持 pending。独立 Reviewer 读取该实际 Payload、全部 Member 和检查结果后形成确认；最终确认不改变业务正文和 Member 摘要。产品结果、证据或规则变化仍使旧确认失效。当前业务证据不包含下游授权；是否可进入 RLS 必须查看已冻结 Artifact 的真实 Gate 与当前 Subject。

## CLI 业务 stdin（与输出 Schema 分开）

这里是 CLI 的平铺业务对象，不是 `inputs.design` 风格 Envelope；release-candidate Schema 描述输出，不能当输入模板。`create/revise` 在持久化模式从准确 `--input` 编译 Authority；candidate/replacement 仅为受控提示/非持久化候选，不能覆盖真实 Subject 或冻结 Method。

| 字段 | 类型 / 用途 |
|---|---|
| project_root、reference | 项目根和准确 VFY 引用；CLI 显式参数优先 |
| persist、run_automated、allow_commands、finalize | JSON boolean，默认分别 false/true/false/false；实际持久化还受 CLI write_policy/dry_run 约束，字符串 "false" 不合法 |
| candidate、replacement | 候选/替换对象；正式持久化 Authority 从上游重新解析 |
| method_ids | VFM-NNN 字符串数组；CLI 可重复 --method/-m；不能按拼写猜 Method |
| manual_observations | 对象：键 VFM-NNN，值真实观察记录，见下文 |
| failure_returns | 对象：键实际失败的 VFM-NNN，值 Return 输入；不是调用者自报 PASS |
| early_stop_basis | 提前停止的依据对象，按既有覆盖规则验证 |
| confirmation | 绑定当前摘要及独立复核记录的最终确认对象 |
| state | 非持久化/测试路径的已有状态，不是持久化 check 的 Authority 来源 |

manual_observations 的每个观察包含 decision（pass/fail）、evaluator_identity（必须与冻结 Method 执行者一致）、observed_at（RFC3339）、scenario、expected、scope、observed，以及 `evidence={"reference":"...","sha256":"sha256:..."}`。scope 为非空字符串/列表/对象，observed 为非空字符串/列表/对象；实际内容来自人类观察，不由 Agent 根据期望补造。缺真实观察时 action_required。

failure_returns 只挂到实际失败结果。Runtime 生成缺省 RET-ID、open 状态及当前失败 Evidence 引用，并校验目标/Subject Lineage；不能用其覆盖已发生效果。产品 fail、Artifact Gate、RLS ready 是独立结论。
