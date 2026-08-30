# Shared Local SQLite ArtifactStore

## 定位

`ArtifactStore` 是 Plugin 级共享确定性组件，不是 Skill，也不包含 Phase
业务规则。

```text
Phase Runtime
    ↓ 构造 Payload / 执行 Domain Validator
ArtifactStore
    ↓ ID、Revision、事务、Member、Digest、Reference
<project-root>/.sdlc/store.sqlite3
```

唯一实现：

```text
packages/sdlc_artifact_store/
```

共享 CLI：

```text
scripts/sdlc_artifact_store.py
```

公开运行 Contract：

```text
packages/sdlc_artifact_store/CONTRACT.md
```

## 使用边界

所有 Artifact Skill 必须：

- 使用共享 Python API 或 Runtime Adapter；
- 不直接执行 SQL；
- 不拥有私有 Schema；
- 不复制 Store；
- `create / revise` 使用读写入口并显式初始化；
- `check` 使用严格只读入口；
- 将领域 Builder / Validator 与 Store 分离。

ArtifactStore 不负责：

- 判断业务事实；
- 生成 Basis；
- 批准 Exception；
- 生成 Final Confirmation；
- 计算领域 Gate；
- 调用其他 Skill；
- 读取 `docs/**`；
- 联网或安装依赖。

## Shared API

九个逻辑操作：

```text
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

Phase Skill 不应让 Agent 手工串联多个 CLI 命令。推荐由单一
`scripts/runtime.py` 通过 Python API 编排完整业务事务。

## Runtime Independence

该组件运行时只依赖 Python 标准库和 Plugin 内 `packages/**`，不读取
`docs/v1.x/**`。

## Test Evidence

见：

```text
docs/plugin-development/components/artifact-store/TEST-RESULTS.md
```
