---
name: sdlc-000-ctx
description: 显式创建、修订或严格只读检查项目上下文 CTX，并通过共享 ArtifactStore 保存可验证的准确 Revision。
disable-model-invocation: true
---

# SDLC Project Context

本 Skill 只在用户显式调用 `$sdlc-000-ctx` 时运行。从调用开始到完成、停止或交还控制权，保持 exclusive execution：不调用其他业务 Skill，不把本次授权传递给其他能力。

## 使用边界

- 只处理 `create`、`revise`、`check` 中一个操作。
- `create` 必须先获得唯一绝对 `project_root`、明确写入授权，以及带合法 `confirmed` Basis 的 Project Boundary 确认。
- `revise` 和 `check` 必须使用准确数字 Revision 的 `CTX-...@<Revision>`，禁止 `latest`、`current` 或相似度选择。
- `check` 绝对只读；Store、数据库或 Schema 缺失时直接失败，不初始化、不修复。
- 不读取设计文档，不联网、不安装依赖、不提交 Git、不写外部系统、不调用兄弟 Skill。

## 执行 SOP

1. 阅读 [运行合约](references/contract.md)，按其中结构收集 Invocation JSON；事实不足时保留缺口，不推断正式事实。
2. 将一次 Invocation 交给单一 Runtime Adapter：

   ```text
   python3 <plugin-root>/skills/sdlc-000-ctx/scripts/runtime.py <invocation.json>
   ```

3. Runtime 使用共享 Envelope 和单操作路由；`create/revise` 仅在授权后编排共享 ArtifactStore 与 ContextLineageRegistry，`check` 仅使用共享只读入口。
4. 保留 Runtime 输出的完整 Result Envelope，并用简明中文说明状态、准确 Artifact 状态、Open Items、错误和唯一 `next_action`。
5. `action_required`、`blocked` 或 `failed` 时立即停止；不得以临时 Markdown、其他数据库或手工 Store 命令 fallback。

## 结果解释

- 只有 `frozen` 且 `ready` 或 `ready_with_exception`、摘要闭合并通过 Domain Validator 的准确 Revision 才是 Context Authority。
- materialized `open` Revision 只可继续修订；其 Result 中 `artifact.reference` 必须为 `null`。
- `abandoned` Revision 和只有 Control Reservation 的 Revision 不提供 Authority。
- Runtime 的 JSON 是机器结果；当前会话还必须给出与其一致的中文摘要，不能把未执行检查写成通过。
