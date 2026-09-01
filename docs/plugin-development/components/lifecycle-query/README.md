# Lifecycle Query Graph

## Purpose

`packages/sdlc_lifecycle/` 将本地 Canonical ArtifactStore 投影为严格只读的生命周期关系图和状态结果。

```text
ArtifactStore.open_read_only
        ↓
ArtifactCatalog + exact read_revision
        ↓
Canonical Parser + Frozen Authority verifier
        ↓
Lifecycle Query Graph
        ↓
sdlc-status
```

## Current vertical slice

当前正式 Skill：

```text
CTX → REQ
```

当前查询能够：

- 列出全部准确 REQ Revision；
- 标识每个 Lineage 的最高 materialized Revision，但不创建 `latest` Authority；
- 检查准确 REQ Revision；
- 验证 CTX / REQ Store 摘要和 frozen Authority；
- 输出 Context / Input / Return / Issue Edge；
- 计算前沿、阻塞项和下一阶段；
- 在 DSN Skill 尚未安装时明确返回 `skill_available=false`。

## Non-authority

Graph、Frontier、Overall State 和 Next Action 都是本地只读 Projection：

- 不写 ArtifactStore；
- 不改变 Artifact Status、Gate、Open Item 或 Revision；
- 不替代准确 Artifact Reference；
- 不提供新的 Canonical Authority。

## Real-project integration

CI 使用 `ousui/springgear@devl` 的真实仓库快照：

1. 将快照复制到临时目录；
2. 使用正式 `sdlc-000-ctx` Runtime 创建并冻结 CTX；
3. 使用正式 `sdlc-100-req` Runtime 创建并冻结 REQ；
4. 执行 Lifecycle Query；
5. 比较查询前后完整项目文件摘要，必须零变化；
6. 临时运行态不提交到 springgear 仓库。
