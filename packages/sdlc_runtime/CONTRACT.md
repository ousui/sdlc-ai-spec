# Shared Runtime Kernel Contract

`packages/sdlc_runtime/` 是所有正式 Phase Skill 的共享应用层内核。

## 稳定标识

| Field | Value |
|---|---|
| Contract ID | `sdlc-ai-spec/runtime/kernel/v1` |
| Contract Version | `1` |

## 职责

- 校验标准 Invocation / Result Envelope；
- 将 `create / revise / check` 路由到单一 Phase Handler；
- 生成稳定结构化错误结果；
- 在构建期生成和验证 `source-lock.json`；
- 读取 `skills/_shared/contracts/registry.json` 中登记的运行合约；
- 解析正式 Runtime 使用的受限 Canonical Markdown/YAML 子集；
- 确定性计算 Control Input Digest 与 Check Set Result Digest；
- 验证已冻结上游 Artifact 的持久化 Authority 绑定；
- 只读解析跨阶段 VFY Return 与 RLS Issue Control Input。

## Frozen Artifact Authority

`FrozenArtifactAuthorityVerifier` 只用于消费已经冻结的准确上游 Artifact：

- 校验 Front Matter 身份、Revision、Status 与 Store Payload 一致；
- 重算 Control Input Digest 和 Check Set Result Digest；
- 校验 `CORE-G-009`、Final Confirmation 和 Gate Summary 的绑定；
- 校验 Human / Delegated Authority Reference 的项目内路径与原始字节摘要；
- 对 `delegated` 严格校验固定单行 Authority 文档、RFC 3339 决定时间、独立 Reviewer、
  可复用 Delegation Basis、三项当前摘要绑定，以及固定的 Independence / Excluded Authority；
- 对 IMP 进一步把 `Reviewed Executor Identity` 与 Revision Control Record 中持久化的
  Claim Owner 交叉核对；其他 Artifact 没有权威执行身份字段时不宣称已证明执行者身份；
- 返回绑定当前 Store Payload 的 `DomainVerification`。

它不得用于 `freeze_revision`。新 Revision 的业务事实、Phase Check、Exception、
Final Confirmation 和 Gate 仍由当前 Phase 私有 Domain Validator 负责。

## Cross-phase Control Inputs

`ControlInputResolver` 只处理两个已注册的跨阶段返工入口：

- 冻结 VFY Revision 中的准确 `#RET-NNN`；
- 冻结 RLS Revision 中的准确 `#RLI-NNN` 或 `#RCF-NNN`。

调用方必须提供准确 Item Reference 和期望目标 Phase。Resolver 先验证所属冻结
Artifact Authority，再读取固定控制表并验证：

- VFY Return 的 `Return Phase` 与期望 Phase 一致；
- RLS Issue 的 `Follow-up Disposition` 与 `return_<phase>` 一致；
- Return / Issue 行在当前 Artifact 中恰好出现一次；
- 必要 Source、Target、Method、Subject、Evidence、Observed Gap 与 Required Outcome
  不为空；
- RLS 行的 Result 允许形成相应 `return_*` 路由。

Resolver 不改变 Delivery Scope、不判断问题已经解决、不执行目标 Phase Skill，也不
自动选择最新或相似 Artifact。

## 非职责

- 不读取 `docs/**` 执行业务流程；
- 不判断 CTX、REQ、DSN 等领域事实；
- 不重新执行上游 Phase 的业务 Check；
- 不把接收 Control Input 解释为问题已解决；
- 不创建 Artifact ID、Revision 或 SQLite Schema；
- 不替代 Phase Builder、Domain Validator 或 ArtifactStore；
- 不联网、不安装依赖、不执行 Git 或外部写入。

正式 Skill 可以依赖本 Package，但不得复制其 Envelope、Source Lock、Canonical
解析、摘要计算、上游 Authority、Control Input 校验或路由逻辑。
