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
- 验证已冻结上游 Artifact 的持久化 Authority 绑定。

## Frozen Artifact Authority

`FrozenArtifactAuthorityVerifier` 只用于消费已经冻结的准确上游 Artifact：

- 校验 Front Matter 身份、Revision、Status 与 Store Payload 一致；
- 重算 Control Input Digest 和 Check Set Result Digest；
- 校验 `CORE-G-009`、Final Confirmation 和 Gate Summary 的绑定；
- 校验 Human / Delegated Authority Reference 的项目内路径与原始字节摘要；
- 返回绑定当前 Store Payload 的 `DomainVerification`。

它不得用于 `freeze_revision`。新 Revision 的业务事实、Phase Check、Exception、
Final Confirmation 和 Gate 仍由当前 Phase 私有 Domain Validator 负责。

## 非职责

- 不读取 `docs/**` 执行业务流程；
- 不判断 CTX、REQ、DSN 等领域事实；
- 不重新执行上游 Phase 的业务 Check；
- 不创建 Artifact ID、Revision 或 SQLite Schema；
- 不替代 Phase Builder、Domain Validator 或 ArtifactStore；
- 不联网、不安装依赖、不执行 Git 或外部写入。

正式 Skill 可以依赖本 Package，但不得复制其 Envelope、Source Lock、Canonical
解析、摘要计算、上游 Authority 校验或路由逻辑。
