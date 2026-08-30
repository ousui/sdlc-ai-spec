# Plugin Development Handoff

## 当前目标

把当前稳定的 `docs/v1.1/` 领域 Contract 转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。`docs/v1.0/` 保留为冻结、只读的历史 Snapshot；已冻结的 v1.0 Artifact 仍按其原 `Evaluation Contract Set` 解释。

## 当前阶段

- v1.1 已完成独立 Review、Maintainer Finalization 和远端同步；25 份正式 Spec 均为 `status: stable`、`version: "1.1"`。
- `sdlc-project-context` 仍处于 `design`；本次唯一 `design-fix` 工作包已完成，未进入 `approval` 或 `implement`。
- `DESIGN.md` 与 `EVAL-PLAN.md` 状态均为 `ready`，Design 阻塞 Open Item 为零。
- 上一次 Maintainer `rejected` 的三项 Basis 已通过 Design / Eval 修订响应；当前 Maintainer Decision 为 `pending`，不得解释为已批准。
- 下一阶段内工作包唯一为 `approval`；获得 Maintainer 当前明确决定前不得进入 `implement`。

## 当前设计结论

- CTX Artifact Authority 是当前 Project Boundary 的唯一 Canonical Store；首版物理执行只支持项目根 `.sdlc/store.sqlite3`，Skill 只通过后续独立实现并验证的 Plugin 内部 `ArtifactStore` 模块访问。
- `create / revise` 可在准确写入授权内执行可能建立 Store 的 `initialize`；`check` 禁止调用 `initialize`，只能验证已经存在的 Canonical Store 并调用读取性 Store Operation。
- `check` 为绝对只读；`.sdlc/`、`store.sqlite3` 或所需 Schema 不存在时报告失败，不创建、迁移、修复或写入任何持久化状态，不使用文件系统 fallback。
- Execution Target Boundary 只是用于唯一选定 Project Root、Canonical Store Locator 和适用时 CTX Lineage / Revision 的执行前置，不是新的 Artifact 或 CTX 字段。它未确定时不初始化 Store、不分配 Artifact / Revision，也不用 Open Item 掩盖选目标歧义。
- CTX `Project Identity.Boundary` 是已选定项目的正式业务字段。只有 Execution Target Boundary 已唯一确定，但该字段或其他必要 Context 事实缺合法 Basis 时，`create / revise` 才可在准确 materialized open Revision 中登记 Open Item 并派生 `waiting_input`。
- Eval Plan 现在独立覆盖 materialized open Revision 原地 revise 且不增 Revision、Exception / human Final Confirmation / `pass_with_exception / ready_with_exception` 一致性、delegated Final Confirmation，以及 materialized `abandoned` Revision 的只读检查与不可作为 Context Authority。

## 当前验证结果

- 已对照 `docs/v1.1/core-spec.md`、`docs/v1.1/artifact-store-spec.md` 与 `docs/v1.1/000-ctx-spec.md` 复核上述修订；三份 Source of Truth 未修改。
- `DESIGN.md` 的 Design DoD 已重新检查；Open Items 仍为唯一 `None` 行，当前 Maintainer Decision 为 `pending`。
- `EVAL-PLAN.md` 已增加独立 Fixture 设计、Case、Check 和 Case-to-Check 追踪；所有新增 Expected Outcome 与 Forbidden Behavior 可判定。
- 已执行 `git diff --check`、完整 Diff 和路径白名单检查；只有本次授权的三份 Markdown 文件变化，`docs/v1.0/**` 无变化。
- 未执行 Skill 行为 Eval、ArtifactStore 测试或三端宿主验证；本工作包只修订 Design / Eval Plan，三端行为兼容性继续为 `Pending first skill`。

## 未实现与已知限制

- 未创建 `SKILL.md`、`agents/openai.yaml`、Fixture、`EVAL-RESULTS.md` 或任何其他 Skill。
- 未实现 SQLite Schema、Migration、`ArtifactStore` 模块、Projection、Human Review View 或文件导出。
- 未新增领域字段、状态、Store Operation、Check、Gate、Contract ID、Provider、远程能力或数据库 Schema。
- 新增 Eval Fixture 仅是逻辑设计标识，未创建任何 Fixture 文件或运行结果。

## Git 与远端状态

- 本工作包开始时位于 `main@38c33e6c9346bd961f1267308bb1ab0a0c7f5248`，`origin/main=80701bb15c24713bf63de8dbc7dda05b11b61aae`，工作树干净，`main` 领先 `origin/main` 1 个本地提交。
- 本 `design-fix` 工作包完成后创建一个本地提交；完成后工作树干净，`main` 领先 `origin/main` 2 个本地提交。
- Origin 权威配置为 `git@github.com:blade-cdn/sdlc-ai-spec.git`；未执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 下一唯一工作包

`approval`：Maintainer 只对当前 `sdlc-project-context` 的 `DESIGN.md` 与 `EVAL-PLAN.md` 作出明确 `approved` 或 `rejected` 决定，并按实际决定更新确认记录与本文件。该工作包不创建 `SKILL.md`、`agents/openai.yaml`、SQLite Schema、`ArtifactStore` 实现、Fixture 或 `EVAL-RESULTS.md`，不执行行为 Eval、平台适配、`implement`、push 或其他远程写入。
