# Plugin Development Handoff

## 当前目标

把稳定的 `docs/v1.0/` 领域 Contract 逐步转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。v1.0 保持冻结；v1.1 当前只形成 Draft Spec Snapshot，不是稳定兼容基线。

## 当前阶段

- `SQLITE-DELTA-001` 针对完整 Canonical Revision Payload / Manifest-Member closure 的定向、独立、只读验证结果为 `PASS`。
- 完整 `docs/v1.1/` Draft Spec Snapshot 已创建：25 份正式 Spec、29 个总文件。
- v1.1 仍为 `draft`；独立 Spec Review 和 Maintainer Finalization 尚未完成。
- Plugin 当前稳定 Source of Truth 仍为 `docs/v1.0/`，未切换到 v1.1。
- 候选 Skill `sdlc-project-context` 继续保持 `draft`，未批准、未实现。

## 本工作包已完成

- 以字节完整的 v1.0 Snapshot 为基线创建 `docs/v1.1/`。
- 新增实现中立的 `artifact-store-spec.md`，定义 Canonical Store、Artifact Lineage、Revision Control Record、完整 Canonical Revision Payload、九个最小逻辑操作和准确 Reference 解析。
- 仅在 Core、CTX、DSN 与 IMP 中解除固定文件系统 Authority；全部现有 Artifact 字段、Reference、Status、Revision State、Check、Gate、Final Confirmation、Phase、Domain 和固定模板保持。
- 20 份 reference-update-only Spec 只更新 Front Matter `status/version`，没有非预期正文变化。
- README、overview、SHA256SUMS 已按 Draft Snapshot 边界更新；`ai-human-collaboration.md` 与 v1.0 字节一致。

## 当前验证结果

- v1.0 `SHA256SUMS`：24/24 通过，`docs/v1.0/**` 无 Diff。
- v1.1 `SHA256SUMS`：25/25 通过。
- v1.1 文件计数：25 份正式 Spec、29 个总文件、16 份 Domain Spec、25 行 SHA256SUMS。
- 25 份正式 Spec 的 Front Matter 均为 `status: draft` 与 `version: "1.1"`。
- 三个 Contract ID 保持 `/v1`；现有 Check ID 与 Gate ID 集合保持不变。
- Store、Core 与 DSN 对 primary Canonical Blob、全部 locally owned Member、稳定 Member 身份、原始字节、Media Type、逐 Member SHA-256、Manifest-Member closure 和外部不可变 Reference 边界保持一致。
- Core、CTX、DSN 与 IMP 不再通过固定 Artifact 目录、Revision Index 文件、六位 Revision 目录、主文件路径或目录扫描确定 Canonical Authority。
- `git diff --check` 和受保护路径 Diff 检查通过。

## Git 与远端状态

- 本工作包开始基线为 `main@6652cc9c51272c275efebf5650c74734e11506f8`，开始时工作树干净，`HEAD...origin/main` 为 `0 0`。
- Origin Fetch / Push 均指向权威仓库 `git@github.com:blade-cdn/sdlc-ai-spec.git`；有效 rewrite 未指向 `ousui` 或其他仓库。
- 此前“当前工作未 push”的描述已过期：本轮开始时预期基线已经与 `origin/main` 一致。
- 本轮 v1.1 Draft 提交只保留在本地，不执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 未实现与已知限制

- 未实现 SQLite Schema、Migration、`ArtifactStore` 模块、Projection、Human Review View 或任何 Skill。
- 未创建 `.sdlc/`、运行时 Store、Provider 配置或多 Provider 能力。
- Draft 摘要只证明 Review Snapshot 的字节完整性，不表示 v1.1 已 `stable`、已发布或已兼容 Plugin。
- 三端 Skill 行为兼容性继续为 `Pending first skill`。

## 下一唯一工作包

对完整 `docs/v1.1/` Draft Snapshot 进行独立、只读 Spec Review。

Review 不修改文件。Review 通过并由 Maintainer 最终批准前，不把 v1.1 改为 `stable`，不切换 Plugin Source of Truth，不批准或实现 `sdlc-project-context`，不实现 SQLite Store、`ArtifactStore`、Projection 或任何 Skill。
