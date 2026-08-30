# Plugin Development Handoff

## 当前目标

以自包含 Runtime、共享 ArtifactStore 和统一 Phase Runtime Contract 支撑正式
`sdlc-ai-spec` Skills；生产 Runtime 不读取 `docs/**`。

## 当前阶段

- `main` 不包含正式 Phase Skill。
- Shared Runtime Core Foundation 已进入独立验证。
- 正式 CTX Work Item 位于独立 Skill 分支，待在 Foundation 合并后重新审查。
- `docs/v1.x/**` 继续作为 design/build/review Source，不作为安装后 Runtime 依赖。

## 已完成基础能力

### ArtifactStore

- 共享实现：`packages/sdlc_artifact_store/`
- Local SQLite Store：`<project-root>/.sdlc/store.sqlite3`
- 九个逻辑 Store 操作、严格只读入口、事务、Revision、Digest 和 Member closure 已实现。

### Shared Runtime Contracts

- Contract Registry：`skills/_shared/contracts/registry.json`
- Shared Schemas：`skills/_shared/schemas/`
- Shared Runtime Kernel：`packages/sdlc_runtime/`
- 标准 Invocation / Result Envelope、单操作路由和 Source Lock 构建期校验已建立。

### CTX Identity Foundation

- `ContextLineageRegistry` 通过调用方提供的稳定 Boundary Key 原子发现或保留唯一
  CTX Artifact Lineage。
- 重复和并发保留不得产生第二个 CTX Artifact ID。
- 只读 `find` 不初始化 Store、不创建扩展表或其他持久化状态。

### Read-only Catalog

- `ArtifactCatalog` 提供 Artifact Lineage 与 Revision Control 列表 Projection。
- Catalog 不提供 Artifact Authority，未来供 `sdlc-status` 查询层使用。

### Native Marketplace Adapters

- Codex：`.codex-plugin/plugin.json` 与 `.agents/plugins/marketplace.json`
- Cursor：`.cursor-plugin/plugin.json` 与 `.cursor-plugin/marketplace.json`
- Claude Code：`.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json`
- Cursor 与 Claude Code 只映射各自原生 schema 支持的 Codex 基准字段，不重新解释、
  改写或补充 Plugin 内容。
- Marketplace 与 Plugin 中文描述已建立，仓库 Source 使用 Maintainer 当前明确指定的
  分发地址；固定远端只保存在分发元数据中。
- 远程安装、Skill Discovery 与行为验证尚未执行；当前状态仍为
  `Pending first skill`。

## 固定命名

- Phase Skill：`sdlc-NNN-xxx`
- 跨生命周期状态 Utility：`sdlc-status`
- `sdlc-status` 与 `$sdlc-worker:sdlc-status` 通过 Plugin Namespace 区分。

## 验证命令

```bash
python3 -m compileall packages scripts
python3 tools/validate_runtime_contracts.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

详细结果以对应 GitHub Actions 运行记录和组件 Test Results 为准。

## 未实现

- 尚无正式 `SKILL.md`。
- 尚无 CTX / REQ / DSN 等 Phase Builder 和 Domain Validator。
- 尚未实现 Human Review View。
- 尚未实现 Lifecycle Query Graph 或 `sdlc-status` Runtime。
- 尚未执行正式 Skill Discovery / Invocation / Behavior 评测。

## 下一唯一工作包

在 Foundation 验证并合入 `main` 后，将 `sdlc-000-ctx` Work Item 更新到新的
Runtime Core 基线：

- 把两个 Foundation 前置依赖标记为已实现并绑定准确公共 API / Contract ID；
- 使用共享 Source Lock Schema 与 Runtime Kernel；
- 保持 Design=`ready`、Maintainer Decision=`pending`；
- 重新执行 approval，只读确认不存在 Blocker / Major；
- 未经 Maintainer 明确批准，不进入 implement。
