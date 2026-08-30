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
- 读取 `skills/_shared/contracts/registry.json` 中登记的运行合约。

## 非职责

- 不读取 `docs/**` 执行业务流程；
- 不判断 CTX、REQ、DSN 等领域事实；
- 不创建 Artifact ID、Revision 或 SQLite Schema；
- 不替代 Phase Builder、Domain Validator 或 ArtifactStore；
- 不联网、不安装依赖、不执行 Git 或外部写入。

正式 Skill 可以依赖本 Package，但不得复制其 Envelope、Source Lock 或路由逻辑。
