# Shared Runtime Core

## 组成

```text
skills/_shared/contracts/registry.json
skills/_shared/schemas/*.json
packages/sdlc_runtime/
packages/sdlc_artifact_store/context_lineage.py
packages/sdlc_artifact_store/catalog.py
```

## 职责

- 为共享运行合约登记稳定 Contract ID 与 Version；
- 校验统一 Invocation / Result Envelope；
- 为 Phase Runtime 提供 `create / revise / check` 单操作路由；
- 在构建期生成和校验 `source-lock.json`；
- 解析正式 Runtime 使用的受限 Canonical Markdown/YAML；
- 计算 Control Input Digest 与 Check Set Result Digest；
- 验证已冻结上游 Artifact 的持久化 Authority 绑定；
- 解析冻结 VFY Return 与 RLS Issue Control Input；
- 原子发现或保留 Project Boundary 对应的唯一 CTX Lineage；
- 提供严格只读 Artifact Catalog，供未来 `sdlc-status` 查询层使用。

## 边界

- 设计规范仍位于 `docs/v1.x/**`，生产 Runtime 不读取这些文档；
- `FrozenArtifactAuthorityVerifier` 只验证已经冻结的上游 Authority，不重新执行
  Phase 业务 Check，也不得用于冻结新 Revision；
- `ControlInputResolver` 只验证已注册的 Return / Issue 路由，不改变 Scope、不判断
  问题解决，也不调用目标 Phase Skill；
- 当前 Phase 的 Builder、Domain Validator、Exception、Final Confirmation 和 Gate
  仍由当前 Skill 私有 Runtime 负责；
- `ContextLineageRegistry` 只保存调用方提供的 `sha256:<hex>` Boundary Key，
  不解释或确认 Project Boundary 业务语义；
- `ArtifactCatalog` 只提供列表 Projection，不提供 Artifact Authority；
- Human Review View 和状态 Skill 不属于本组件；
- 不增加远程 Store、多 Provider、MCP 或第三方依赖。

## Consuming Frozen Inputs

```python
from packages.sdlc_artifact_store import ArtifactStore
from packages.sdlc_runtime import FrozenArtifactAuthorityVerifier

store = ArtifactStore.open_read_only(project_root)
verifier = FrozenArtifactAuthorityVerifier(project_root)
resolved = store.resolve_exact_reference("CTX-...@1", verifier=verifier)
```

该入口验证 Store 的 frozen / ready 状态、Payload 完整性、Gate、Final
Confirmation、Control Input Digest、Check Set Result Digest 与 Authority Reference。
它只证明已冻结记录的持久化 Authority 绑定，不替代生成该 Artifact 时的领域验证。

## Consuming Return / Issue Control Inputs

```python
from packages.sdlc_runtime import ControlInputResolver

resolver = ControlInputResolver(project_root)
control = resolver.resolve_for_phase(
    store,
    "VFY-...@1#RET-001",
    "REQ",
)
```

同一入口也支持冻结 RLS 的 `#RLI-NNN` 与 `#RCF-NNN`。调用方必须提供准确
Reference 和目标 Phase；Resolver 不扫描相似内容，不自动选择最新 Revision。

## CTX 原子绑定

```python
from sdlc_artifact_store import ArtifactStore, ContextLineageRegistry

store = ArtifactStore.open_read_write(project_root)
store.initialize()
binding = ContextLineageRegistry(store).reserve(boundary_key, now=clock())
```

同一 Boundary Key 的重复调用返回同一 CTX Artifact ID。首次绑定和 CTX Artifact
Lineage 创建在一个 SQLite 写事务中完成。严格只读查询使用
`ArtifactStore.open_read_only` 与 `ContextLineageRegistry.find`，不会创建绑定表或文件。

## Future Utility Skill

跨生命周期只读查询 Skill 预留名称：

```text
sdlc-status
```

它与开发辅助插件命令 `$sdlc-worker:sdlc-status` 通过 Plugin Namespace 区分。
Phase 编号只用于 `sdlc-NNN-xxx`，因此状态 Utility 不占用 `000`。
