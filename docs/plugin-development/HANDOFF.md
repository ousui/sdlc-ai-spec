# Plugin Development Handoff

## 当前目标

把当前稳定的 `docs/v1.1/` 领域 Contract 转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。`docs/v1.0/` 保留为冻结、只读的历史 Snapshot；已冻结的 v1.0 Artifact 仍按其原 `Evaluation Contract Set` 解释。

## 当前阶段

- v1.1 已完成独立 Review、Maintainer Finalization 和远端同步；25 份正式 Spec 均为 `status: stable`、`version: "1.1"`。
- `sdlc-project-context` 当前仍处于 `design`。
- `DESIGN.md` 与 `EVAL-PLAN.md` 已切换到 v1.1 Core、Artifact Store 与 Project Context 三份 Source of Truth。
- Design 状态为 `ready`，阻塞 Open Item 为零；Maintainer 决定仍为 `pending`，尚未 `approved`。

## 当前设计结论

- CTX Artifact Authority 是当前 Project Boundary 的唯一 Canonical Store，不再假设 `artifacts/000-ctx/`、Revision Index 文件或 Revision 目录构成 Authority。
- CTX 的 Evaluation Contract Set 必须包含 `docs/v1.1/core-spec.md`、`docs/v1.1/artifact-store-spec.md` 和 `docs/v1.1/000-ctx-spec.md` 的准确 Spec Reference。
- Artifact / Revision 分配、完整 Canonical Revision Payload 写入与读回、冻结、放弃、准确解析和摘要验证只通过 Artifact Store Spec 登记的逻辑 Store Operation 完成。
- 首版物理执行仅支持项目根 `.sdlc/store.sqlite3`；Skill 只通过后续独立实现并验证的 Plugin 内部 `ArtifactStore` 模块访问，不直接 SQL，不引入 Provider 配置或文件系统 fallback。
- Eval Plan 已覆盖 Control Reservation、完整 Payload、三份 Spec Binding、Local SQLite 边界、Store fail-closed、with-skill / without-skill、Exclusive Execution 和三端显式调用。

## 当前验证结果

- `DESIGN.md` 与 `EVAL-PLAN.md` 的 Design DoD 和通过标准完整，状态均为 `ready`，没有写入虚假 Eval Result。
- 旧文件系统 Artifact Store 权威路径与 v1.0 正向 Source of Truth 已从当前工作包移除；保留的 v1.0 仅用于明确禁止旧绑定的负向检查。
- `docs/v1.0/**`、`skills/**`、三个平台 Manifest 与其他工作包无变化。
- 本轮只修改 `DESIGN.md`、`EVAL-PLAN.md` 与本文件；`git diff --check` 通过。

## 未实现与已知限制

- 未创建 `SKILL.md`、`agents/openai.yaml`、Fixture、`EVAL-RESULTS.md` 或任何其他 Skill。
- 未实现 SQLite Schema、Migration、`ArtifactStore` 模块、Projection、Human Review View 或文件导出。
- 未执行 Skill 行为 Eval 或三端宿主验证；三端 Skill 行为兼容性继续为 `Pending first skill`。
- Design `ready` 不是 Maintainer `approved`，不得据此进入 `implement`。
- 未创建新的领域字段、状态、操作、Check、Gate、Contract ID、Provider、远程能力或数据库 Schema。

## Git 与远端状态

- v1.1 Finalization 提交 `73a2da2055a85df3d1715f4c49301c9162d65c18` 已 push；本工作包开始时 `HEAD`、`main` 与 `origin/main` 一致，工作树干净。
- 当前 worktree 使用 detached HEAD；本 `design` 工作包只创建一个本地提交，`main` 与 `origin/main` 保持在上述 Finalization 基线。
- Origin 权威目标仍为 `git@github.com:blade-cdn/sdlc-ai-spec.git`；本工作包不执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 下一唯一工作包

由 Maintainer 审查并明确决定是否批准 `sdlc-project-context` 的 `ready` Design Contract 与 Eval Plan，只记录审批决定和必要 Handoff；不得创建 `SKILL.md`、SQLite Schema、`ArtifactStore` 实现或进入 `implement`。
