# Plugin Development Handoff

## 当前目标

把当前稳定的 `docs/v1.1/` 领域 Contract 转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。`docs/v1.0/` 保留为冻结、只读的历史 Snapshot；已冻结的 v1.0 Artifact 仍按其原 `Evaluation Contract Set` 解释。

## 当前阶段

- `V11-DR-MAJ-001`: `PASS`。
- `V11-DR-MAJ-002`: `PASS`。
- v1.1 已完成独立 Review 和 Maintainer Finalization。
- 25 份正式 Spec 均为 `status: stable`、`version: "1.1"`。
- Plugin 稳定 Source of Truth 已切换为 `docs/v1.1/`。

## 当前验证结果

- v1.0 `SHA256SUMS`：24/24 通过，`docs/v1.0/**` 无 Diff。
- v1.1 `SHA256SUMS`：25/25 通过；25 份正式 Spec、29 个总文件。
- 全部 v1.1 内嵌 Spec Reference SHA-256 与目标文件最终原始字节一致，不存在旧摘要或占位摘要残留。
- 三个 Contract ID、9 个 Store Operation、Check ID 与 Gate ID 集合保持不变。
- `ai-human-collaboration.md` 与 v1.0 字节一致。
- `skills/` 与 Cursor、Claude Code、Codex 三个平台 Manifest 无变化。

## 未实现与已知限制

- 未实现 SQLite Schema、Migration、`ArtifactStore` 模块、Projection、Human Review View 或任何 Skill。
- 未创建新的字段、状态、操作、Check、Gate、Contract ID、Provider、远程能力或数据库 Schema。
- 三端 Skill 行为兼容性继续为 `Pending first skill`。

## Git 与远端状态

- Finalization 基线为 `main@72cd343e74d623fa1a8b806d795d5675dc6e3e94`，开始时工作树干净，且 HEAD、`origin/main` 与远端 `main` 一致。
- Origin Fetch / Push 均指向权威仓库 `git@github.com:blade-cdn/sdlc-ai-spec.git`；有效 SSH Host 最终为 `github.com`。
- 本工作包只创建本地提交，不执行 push、tag、PR、Release、Marketplace 或其他远程写入。

## 下一唯一工作包

修订 `sdlc-project-context` 的 `DESIGN.md` 和 `EVAL-PLAN.md`，将 Source of Truth 从 v1.0 切换为 v1.1，移除固定文件系统 Artifact Store 假设，绑定 Artifact Store Spec 和 Local SQLite 执行边界。

本轮仍属于 `design`，不创建 `SKILL.md`、SQLite Schema 或实现代码。
