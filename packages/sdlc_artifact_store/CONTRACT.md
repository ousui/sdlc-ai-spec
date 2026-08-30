# ArtifactStore Runtime Contract

## Purpose

`packages.sdlc_artifact_store` 是所有 Artifact Phase Runtime 共用的持久化
Facade。它只实现存储不变量，不实现领域业务规则。

## Public API

```text
ArtifactStore.open_read_write(project_root)
ArtifactStore.open_read_only(project_root)

initialize
allocate_artifact
allocate_revision
read_revision
write_open_revision
freeze_revision
abandon_revision
resolve_exact_reference
verify_digest
```

公开模型和异常从 `packages/sdlc_artifact_store/__init__.py` 导出。

## Caller Contract

Phase Runtime 必须：

- 提供绝对 `project_root`；
- 使用标准 Invocation Envelope；
- 在写入前获得准确授权；
- 通过 DomainVerifier 提供领域 Gate / Final Confirmation 结论；
- 使用最新 `generation` 处理 open Revision 重写；
- 把结构化错误映射到标准 Result Envelope。

## Forbidden Use

调用方不得：

- 直接 SQL；
- 读取内部表作为业务 Authority；
- 复制 Schema；
- 用 Store State 替代 Artifact Status；
- 让 Store 判断业务事实；
- 缺少 verifier 时伪造 freeze / resolve 成功；
- Store 失败时 fallback 到文件或临时数据；
- 运行时读取 `docs/**`。

## Compatibility

- Current Schema Version：`1`
- Current physical Store：`.sdlc/store.sqlite3`
- No provider configuration
- No automatic unknown-schema migration
- Python standard library only

对公开 API 或错误码的破坏性变化必须作为独立 Foundation 工作包处理，
不得由单个 Phase Skill 私自修改。
