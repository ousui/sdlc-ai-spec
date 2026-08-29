# Plugin Development Handoff

## 当前目标

把稳定的 `docs/v1.0/` 领域 Contract 逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。v1.0 保持冻结；v1.1 当前仍是 Draft Spec Snapshot，不是稳定兼容基线。

## 当前阶段

- 完整 v1.1 Draft Spec Review 结果为 `PASS WITH REQUIRED CHANGES`。
- `V11-DR-MAJ-001` 与 `V11-DR-MAJ-002` 已在 Draft 中修正，尚未进行定向复核。
- v1.1 仍为 `draft`；Finalization 与稳定 Source of Truth 切换均未执行。
- Plugin 当前稳定 Source of Truth 仍为 `docs/v1.0/`。
- 候选 Skill `sdlc-project-context` 仍为 `draft`，未批准、未实现。

## 本工作包已完成

- 明确 Claim Provider 是稳定 IMP Artifact ID 与当前 Claim Attempt 目标 Revision Reservation 的唯一分配 Authority；`acquire` 同时登记准确的 Binding Lineage、Artifact ID、Attempt、Owner 与 Reservation。
- 明确 Artifact Store 对 IMP 的 `allocate artifact` 与 `allocate revision` 只幂等采用并校验 Claim 的准确值，不生成第二个 Artifact ID 或 Revision Number；其他 Artifact 仍由 Store 正常分配。
- 将 `allocate revision` 收窄为只建立 open Revision Control Record；删除 Canonical Revision Payload 骨架和不完整 Payload 可作为 Revision 的描述。
- 明确第一次 `write open revision` 原子写入并完整读回全部 Canonical Revision Payload；只有成功后才成为 materialized open Revision，且 `materialized` 不新增正式状态或字段。
- 明确未物化 Control Reservation 只可作为第一次完整写入的目标或通过 `abandon revision` 终结，不提供 read、resolve、Gate、Final Confirmation、Freeze 或下游 Authority。
- 补齐 IMP 首次 Store 登记、Revision 分配、首次完整写入和读回失败时的固定重试与放弃顺序，并同步架构决策、Delta Plan、Changelog 与 v1.1 摘要。

## 当前验证结果

- v1.0 `SHA256SUMS`：24/24 通过，`docs/v1.0/**` 无 Diff。
- v1.1 `SHA256SUMS`：25/25 通过；25 份正式 Spec、29 个总文件的 Draft Snapshot 数量不变。
- Artifact Store 逻辑操作仍恰好为 9 个，名称集合不变。
- Check ID 集合与基线一致：63 个唯一 ID，其中 57 个 `*-G-*` Gate Check ID、6 个 `IMP-RDY-*` Readiness Check ID；未新增或删除 Check / Gate ID。
- 三个 Contract ID 仍为 `/v1`，集合不变。
- 不存在“Canonical Revision Payload 骨架”或“最小 Canonical Revision Payload”残留。
- 静态断言确认未物化 Control Reservation 不会被 `read revision`、`resolve exact reference`、Artifact Gate、Final Confirmation 或 `freeze revision` 使用，也不提供 Context、Input、Item 或 Member Authority。
- 静态断言确认 IMP Artifact ID 与当前 Claim Attempt 目标 Revision Reservation 只有 Claim Provider 一个分配 Authority，Store 不为 IMP 生成第二个 ID 或 Revision Number。
- `git diff --check` 通过；`skills/` 与 Cursor、Claude Code、Codex 三个平台 Manifest 无变化。

## Git 与远端状态

- 本工作包开始基线为 `main@f5fe2a62863d27310f7dd2fcfcedff0ea90d0dad`，开始时工作树干净，且 HEAD 与 `origin/main` 一致；该基线已经 push。
- Origin Fetch / Push 均指向权威仓库 `git@github.com:blade-cdn/sdlc-ai-spec.git`；有效 rewrite 未指向 `ousui`、`goedgecloud` 或其他仓库。
- 本工作包修正与本 Handoff 保存在同一个本地提交中；不执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 未实现与已知限制

- 两项 Finding 的修正尚未经过全新会话定向复核，不能据此宣称 v1.1 Review 已完全通过。
- v1.1 仍为 Draft，不是 Plugin 稳定 Source of Truth，也没有运行时实现或三端兼容证据。
- 未实现 SQLite Schema、Migration、`ArtifactStore` 模块、Projection、Human Review View 或任何 Skill。
- 未创建新的字段、状态、操作、Check、Gate、Contract ID、Provider、远程能力或数据库 Schema。
- 三端 Skill 行为兼容性继续为 `Pending first skill`。

## 下一唯一工作包

在全新会话中定向复核 `V11-DR-MAJ-001` 与 `V11-DR-MAJ-002`。如果两项均 `PASS`，则在同一会话机械完成 v1.1 Finalization、重新生成 `SHA256SUMS`、切换 Plugin 稳定 Source of Truth，并把下一工作包交给 `sdlc-project-context` 的 v1.1 Design 修订。任一项 `FAIL` 时立即停止，不得 Finalize。
