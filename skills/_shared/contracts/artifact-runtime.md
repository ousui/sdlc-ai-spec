# Shared Artifact Runtime Contract

所有创建、修订或检查 Canonical Artifact 的 Phase Skill 必须遵守本 Contract。

## Store

唯一共享实现：

```text
packages/sdlc_artifact_store/
```

Skill 不直接 SQL、不创建私有 Schema、不复制 Store。

## Operation Modes

### create

1. 确定唯一 Project Root；
2. 使用读写 facade；
3. 在明确写入授权下 initialize；
4. 分配 Artifact 和 Revision Control Record；
5. 构造完整 Payload；
6. Domain Validator；
7. 原子写入并读回；
8. 满足条件时 freeze。

### revise

1. 准确解析 Artifact / Revision；
2. open Revision 原地修订或 frozen 后创建新 Revision；
3. 构造完整 Payload；
4. Domain Validator；
5. 原子写入并读回；
6. 不自动改写下游引用。

### check

1. 使用严格只读 facade；
2. 不 initialize；
3. 不创建 `.sdlc`、数据库或 Schema；
4. 读取、摘要校验和领域检查；
5. 不修复、不写入、不回退到其他 Revision。

## State Boundary

- Control Reservation 不是 Artifact Authority；
- materialized open Revision 可继续修订；
- frozen Revision 不可修改；
- abandoned Revision 不提供下游 Authority；
- Store State 与 Artifact Status 分离；
- freeze / authoritative resolve 必须有当前 Payload 的 DomainVerifier。

## Failure

Store 缺失、损坏、冲突、摘要失败或 verifier 失败时必须返回结构化错误，
不得 fallback 到 Markdown、tmp、导出副本或其他数据库。
