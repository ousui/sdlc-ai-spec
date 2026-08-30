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
- 原子发现或保留 Project Boundary 对应的唯一 CTX Lineage；
- 提供严格只读 Artifact Catalog，供未来 `sdlc-status` 查询层使用。

## 边界

- 设计规范仍位于 `docs/v1.x/**`，生产 Runtime 不读取这些文档；
- `ContextLineageRegistry` 只保存调用方提供的 `sha256:<hex>` Boundary Key，
  不解释或确认 Project Boundary 业务语义；
- `ArtifactCatalog` 只提供列表 Projection，不提供 Artifact Authority；
- Phase Builder、Domain Validator、Human Review View 和状态 Skill 不属于本组件；
- 不增加远程 Store、多 Provider、MCP 或第三方依赖。

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
