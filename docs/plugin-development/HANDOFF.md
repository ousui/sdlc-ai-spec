# Plugin Development Handoff

## 当前目标

把当前稳定的 `docs/v1.1/` 领域 Contract 转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。`docs/v1.0/` 保留为冻结、只读的历史 Snapshot；已冻结的 v1.0 Artifact 仍按其原 `Evaluation Contract Set` 解释。

## 当前阶段

- v1.1 已完成独立 Review、Maintainer Finalization 和远端同步；25 份正式 Spec 均为 `status: stable`、`version: "1.1"`。
- `sdlc-project-context` 当前仍处于 `design`。
- `DESIGN.md` 与 `EVAL-PLAN.md` 已切换到 v1.1 Core、Artifact Store 与 Project Context 三份 Source of Truth。
- `DESIGN.md` 与 `EVAL-PLAN.md` 的文档状态仍为 `ready`；Maintainer 已明确记录决定为 `rejected`，当前 Design 未获批准，不得进入 `implement`。
- 下一阶段内工作包固定为 `design-fix`，完成修订并重新达到审批条件前不得再次请求实现授权。

## 当前设计结论

- CTX Artifact Authority 是当前 Project Boundary 的唯一 Canonical Store，不再假设 `artifacts/000-ctx/`、Revision Index 文件或 Revision 目录构成 Authority。
- CTX 的 Evaluation Contract Set 必须包含 `docs/v1.1/core-spec.md`、`docs/v1.1/artifact-store-spec.md` 和 `docs/v1.1/000-ctx-spec.md` 的准确 Spec Reference。
- Artifact / Revision 分配、完整 Canonical Revision Payload 写入与读回、冻结、放弃、准确解析和摘要验证只通过 Artifact Store Spec 登记的逻辑 Store Operation 完成。
- 首版物理执行仅支持项目根 `.sdlc/store.sqlite3`；Skill 只通过后续独立实现并验证的 Plugin 内部 `ArtifactStore` 模块访问，不直接 SQL，不引入 Provider 配置或文件系统 fallback。
- Eval Plan 已覆盖 Control Reservation、完整 Payload、三份 Spec Binding、Local SQLite 边界、Store fail-closed、with-skill / without-skill、Exclusive Execution 和三端显式调用。

## 当前验证结果

- Maintainer 的 `rejected` 决定及三项 Basis 已写入 `DESIGN.md` 确认记录；Design 正文和 Eval 案例正文未修改。
- 本审批工作包只修改 `DESIGN.md` 的确认记录与本文件；`EVAL-PLAN.md`、`docs/v1.0/**`、`skills/**`、三个平台 Manifest 与其他工作包无变化。
- 未写入 Eval Result，也未把此前 `ready` 或 Review 意见解释为 Maintainer approval。

## 未实现与已知限制

- 未创建 `SKILL.md`、`agents/openai.yaml`、Fixture、`EVAL-RESULTS.md` 或任何其他 Skill。
- 未实现 SQLite Schema、Migration、`ArtifactStore` 模块、Projection、Human Review View 或文件导出。
- 未执行 Skill 行为 Eval 或三端宿主验证；三端 Skill 行为兼容性继续为 `Pending first skill`。
- 未创建新的领域字段、状态、操作、Check、Gate、Contract ID、Provider、远程能力或数据库 Schema。
- `check` 与 `initialize` 的只读边界仍存在未授权写入歧义。
- Execution Target Boundary 与 CTX 内 Project Boundary 业务字段尚未清楚分离，Artifact 分配和 `waiting_input` 的前置条件仍不充分。
- Eval Plan 尚未独立覆盖 materialized open Revision 原地修订且不增加 Revision、`pass_with_exception / ready_with_exception`、delegated Final Confirmation 和 abandoned Revision 的 `check` 行为。

## Git 与远端状态

- 本审批工作包开始时，当前 worktree 位于 `main`，`HEAD`、`main` 与 `origin/main` 均为 `80701bb15c24713bf63de8dbc7dda05b11b61aae`，工作树干净；此前 detached HEAD 与 `73a2da2` 基线描述已过期。
- 本审批工作包完成后只创建一个本地提交；`main` 比 `origin/main` 领先 1 个提交，工作树干净。
- Origin 权威目标为 `git@github.com:blade-cdn/sdlc-ai-spec.git`；未执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 下一唯一工作包

`design-fix`：只修订 `sdlc-project-context` 的 `DESIGN.md` 与 `EVAL-PLAN.md`，消除已记录的三项拒绝 Basis，并按实际结果更新本文件。该工作包不得创建 `SKILL.md`、SQLite Schema、`ArtifactStore` 实现、Fixture 或 `EVAL-RESULTS.md`，不得执行行为 Eval、平台适配或进入 `implement`；完成后只能重新提交 Maintainer 审批。
