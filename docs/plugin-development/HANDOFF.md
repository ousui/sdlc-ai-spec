# Plugin Development Handoff

## 当前目标

把当前稳定的 `docs/v1.1/` 领域 Contract 转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。`docs/v1.0/` 保留为冻结、只读的历史 Snapshot；已冻结的 v1.0 Artifact 仍按其原 `Evaluation Contract Set` 解释。

## 当前阶段

- v1.1 已完成独立 Review、Maintainer Finalization 和远端同步；25 份正式 Spec 均为 `status: stable`、`version: "1.1"`。
- `sdlc-project-context` 的 `approval` 工作包已完成，本轮未进入 `implement`。
- `DESIGN.md` 状态为 `approved`；`EVAL-PLAN.md` 保持 `ready`，Design 阻塞 Open Item 为零。
- Maintainer 已明确批准当前 Design Contract 与 Eval Plan；决定与 Basis 已记录在 `DESIGN.md` 确认记录中。
- 下一唯一工作包为 `implement`；必须由新会话根据已批准 Design 确认准确白名单与 DoD 后开始。

## 当前设计结论

- CTX Artifact Authority 是当前 Project Boundary 的唯一 Canonical Store；首版物理执行只支持项目根 `.sdlc/store.sqlite3`，Skill 只通过后续独立实现并验证的 Plugin 内部 `ArtifactStore` 模块访问。
- `create / revise` 可在准确写入授权内执行可能建立 Store 的 `initialize`；`check` 禁止调用 `initialize`，只能验证已经存在的 Canonical Store 并调用读取性 Store Operation。
- `check` 为绝对只读；`.sdlc/`、`store.sqlite3` 或所需 Schema 不存在时报告失败，不创建、迁移、修复或写入任何持久化状态，不使用文件系统 fallback。
- Execution Target Boundary 只是用于唯一选定 Project Root、Canonical Store Locator 和适用时 CTX Lineage / Revision 的执行前置，不是新的 Artifact 或 CTX 字段。它未确定时不初始化 Store、不分配 Artifact / Revision，也不用 Open Item 掩盖选目标歧义。
- CTX `Project Identity.Boundary` 是已选定项目的正式业务字段。只有 Execution Target Boundary 已唯一确定，但该字段或其他必要 Context 事实缺合法 Basis 时，`create / revise` 才可在准确 materialized open Revision 中登记 Open Item 并派生 `waiting_input`。
- Eval Plan 现在独立覆盖 materialized open Revision 原地 revise 且不增 Revision、Exception / human Final Confirmation / `pass_with_exception / ready_with_exception` 一致性、delegated Final Confirmation，以及 materialized `abandoned` Revision 的只读检查与不可作为 Context Authority。

## 当前验证结果

- 批准写入前已核对 `DESIGN.md` 为 `ready`、Maintainer Decision 为 `pending`、Open Items 为唯一已关闭 `None` 行，满足当前批准 Gate。
- 已核对 `EVAL-PLAN.md` 只定义可判定案例、检查与通过条件，没有伪造执行结果。
- Maintainer 当前请求已明确对准 `sdlc-project-context` 的 `DESIGN.md` 与 `EVAL-PLAN.md`，并使用确定的批准决定与四项 Basis。
- 已对照 `docs/v1.1/core-spec.md`、`docs/v1.1/artifact-store-spec.md` 与 `docs/v1.1/000-ctx-spec.md` 复核批准边界；三份 Source of Truth 未修改。
- 未执行 Skill 行为 Eval、ArtifactStore 测试或三端宿主验证；本工作包只在 `DESIGN.md` 与本文件记录批准，三端行为兼容性继续为 `Pending first skill`。

## 未实现与已知限制

- 未创建 `SKILL.md`、`agents/openai.yaml`、Fixture、`EVAL-RESULTS.md` 或任何其他 Skill。
- 未实现 SQLite Schema、Migration、`ArtifactStore` 模块、Projection、Human Review View 或文件导出。
- 未新增领域字段、状态、Store Operation、Check、Gate、Contract ID、Provider、远程能力或数据库 Schema。
- 新增 Eval Fixture 仅是逻辑设计标识，未创建任何 Fixture 文件或运行结果。

## Git 与远端状态

- 本 `approval` 工作包开始时位于 `main@7cfc4ea572b80c68462937a66a2b68cbcc93c8dc`，`origin/main` 与 HEAD 一致，工作树干净。
- 本 `approval` 工作包已创建一个本地提交；完成后工作树干净，`main` 领先 `origin/main` 1 个本地提交。
- Origin 的 Fetch / Push 权威配置为 `git@github.com:blade-cdn/sdlc-ai-spec.git`；实际 SSH rewrite 仅将 `blade-cdn` 路由到对应 Host Alias，未路由到其他仓库。未执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 下一唯一工作包

`implement`：仅依据已批准的 `sdlc-project-context` Design Contract 实现最小共享 Skill。开始前必须在新会话中确认唯一产物、准确写入白名单、ArtifactStore 依赖的处理边界、DoD 与停止条件。该工作包不执行行为 Eval、平台适配、review、push、发布或 Marketplace 写入，不在实现中重新定义 Design 或 v1.1 领域 Contract。
