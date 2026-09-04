# Resource Runtime Contract

Contract ID: `sdlc-ai-spec/runtime/resource-result/v1`
Contract Version: `1`

本包提供确定性本地文件 Snapshot 与显式 Scope 内文件操作，不拥有 Claim 或 Artifact Authority。
调用方提供稳定的 canonical Resource ID，并负责将它唯一映射到项目内资源根目录。

- `capture_snapshot(root, resource_id)` 只读捕获真实工作区文件，包括未提交、未跟踪和二进制内容；
  不用 Git HEAD 代替 Baseline。根级 `.git`、`.sdlc` 不属于产品 Snapshot。
- `ResourceSnapshot` 包含排序的 `entries`、`paths`、完整 `raw_bytes` 和
  `snapshot:<resource_id>@sha256:<digest>`；摘要由 Resource ID、相对路径及文件 SHA-256 确定。
  每个 Entry 保存 `path`、`sha256`、`content_hex`，可以独立核对完整文件字节。
  保存到 ArtifactStore 的 immutable Member 后，后续工作区变化不改变既有 Snapshot。
- 不存在的资源返回空 Entries；是否存在、N/A Baseline Evidence、文件权限和目录信息由
  IMP Adapter 在首次写入前另行记录。完整 Snapshot Member 是当前实现的不可变 Result 形式，
  不把分支、可移动 Tag、`latest` 或 `current` 当作 Result Authority。
- `apply_operations(root, resource_id, operations, allowed_scope=...)` 支持
  `write_text`、`delete`、`mkdir`。操作必须含 `resource:<id>` 授权，并满足已声明的
  `path:<id>/...` 子范围；绝对路径、父目录逃逸及根级控制路径失败关闭。
  返回 `ResourceChange`，包含真实 before/after Snapshot 和排序后的 `changed_paths`。
- `restore_snapshot(root, snapshot)` 是调用方明确请求的产品恢复操作，保留根级控制目录。
  `apply_operations` 不隐式回滚已执行的操作；IMP Adapter 负责整批预检、Claim、Baseline、
  链接/特殊文件检查及失败现场处理，不能把本包当作事务或执行授权。

上述 API 不执行 Git 命令，不创建提交或移动 Ref，不联网，不安装依赖。
只读捕获不创建资源目录；产品写入必须由上层先验证 Claim 和 write_policy。
