# Plugin Development Handoff

## 当前目标

把当前稳定的 `docs/v1.1/` 领域 Contract 转化为 Cursor、Claude Code 和 Codex 可复用、可验证的 Agent Plugin 支持能力。`docs/v1.0/` 保留为冻结、只读的历史 Snapshot；已冻结的 v1.0 Artifact 仍按其原 `Evaluation Contract Set` 解释。

## 当前阶段

- v1.1 仍是当前稳定 Source of Truth；本次 Foundation 未修改 `docs/v1.0/**` 或 `docs/v1.1/**`。
- 一次性的 Plugin Foundation 工作包已实现共享 Local SQLite `ArtifactStore`；它不是 Skill，也没有进入 `sdlc-project-context implement`。
- `sdlc-project-context` 的 `DESIGN.md` 保持 `approved`，`EVAL-PLAN.md` 保持 `ready`，阻塞 Open Item 为零。
- 下一唯一工作包恢复为 `sdlc-project-context implement`；必须在新会话中只依据已批准 Design 推进。

## ArtifactStore Foundation 完成状态

- 唯一实现：`packages/sdlc_artifact_store/`；共享 CLI：`scripts/sdlc_artifact_store.py`。
- 物理 Store 固定为 `<project-root>/.sdlc/store.sqlite3`；Schema Version 固定为 `1`。
- Python facade 已实现九个逻辑操作：`initialize`、`allocate_artifact`、`allocate_revision`、`read_revision`、`write_open_revision`、`freeze_revision`、`abandon_revision`、`resolve_exact_reference`、`verify_digest`。
- `open_read_write` 与 `open_read_only` 已分离；严格只读入口使用 SQLite read-only URI，不调用 initialize，不创建或修复任何持久化状态。
- 完整 Payload 包含 primary raw bytes、Artifact Status / Media Type / SHA-256、locally owned Members、稳定 ID / Canonical Name / Media Type / SHA-256、Canonical Manifest raw bytes 及本地 Member closure。
- Control Reservation 与 materialized Revision 已分离；同一 Artifact 最多一个 open Revision；Revision 单调且不复用；frozen 不可写；abandoned 保留编号、原因和已有历史 Payload 但不提供 Authority。
- `write_open_revision` 使用单个 SQLite transaction、完整读回、摘要/closure 验证和 generation conflict，拒绝部分成功与 last-write-wins。
- IMP 只提供采用外部准确 Artifact ID / Revision Reservation 的最小参数与幂等/冲突校验；未实现 Claim Provider。
- `freeze_revision` 与权威 `resolve_exact_reference` 缺少领域 verifier、verifier 拒绝或 stale 时均 fail closed；当前未实现 CTX 专属 verifier。
- `.sdlc/.gitignore` 固定为 `*`；initialize 不修改项目根 `.gitignore`，检测到 `.sdlc` 已有 Git-tracked 内容时停止且不改 Git Index。

## 当前验证结果

- Python：`3.14.7`。
- `python3 -m compileall packages scripts`：通过。
- `python3 -m unittest discover -s tests -p 'test_*.py' -v`：34 个测试全部通过，0 failure，0 error。
- 严格只读案例已验证 `.sdlc` / 数据库缺失时不创建；已有 Store 读取前后文件集合和 SHA-256 不变，未产生 journal/WAL/SHM 或旁车文件。
- 自动化覆盖 30 类指定场景，并增加 Schema 损坏、generation conflict、Git-tracked `.sdlc` 和 CLI verifier error 边界。
- 无第三方依赖、无网络调用、无安装行为；全部 Store 测试使用 `tempfile` 隔离项目。
- 详细证据见 `docs/plugin-development/components/artifact-store/TEST-RESULTS.md`。

## 未实现与已知限制

- 未创建或修改任何 `SKILL.md`、`agents/openai.yaml`、Fixture、`EVAL-RESULTS.md`、三个平台 Manifest 或 Plugin Version。
- 未实现 CTX / REQ / DSN 等领域 validator；deterministic fake verifier 只证明内部 protocol 的通过、拒绝和 stale 路径。
- 未执行 `sdlc-project-context` 正式行为 Eval、Codex adapt、独立 review 或三端宿主验证；兼容性仍为 `Pending first skill`。
- 未实现 Projection、Human Review View、Projection Import、Candidate Material、远程 Store、多 Provider、自动 Migration framework 或文件系统 fallback。
- 未做多进程压力/性能基准；当前并发证据限于 SQLite 原子事务、唯一索引和 generation conflict 自动化测试。

## Git 与远端状态

- Foundation 开始基线为 `main@496328e25d8bdd4fa3f0aea7be21dd725c08ebbd`；开始时 HEAD、本地 `origin/main` 与远端 `refs/heads/main` 一致，工作树干净。
- Origin Fetch / Push 配置均为 `git@github.com:blade-cdn/sdlc-ai-spec.git`；有效 rewrite 为 `git@github-goedge-blade:blade-cdn/sdlc-ai-spec.git`，SSH Alias 的实际 hostname 为 `github.com`，未路由到其他仓库。
- Foundation 由当前 `main` HEAD 的本地 `feat(store)` 提交承载；交接时 `git status --short` 必须为空，`main` 仅领先 `origin/main` 1 个本地提交。
- 未执行 push、merge、tag、PR、Release、Marketplace 或其他远程写入。

## 下一唯一工作包

`sdlc-project-context implement`：仅依据已批准 Design 实现 CTX Payload builder、CTX domain validator、`SKILL.md` 和 Design 已批准的最小运行逻辑。

该 implement 必须使用共享 `packages/sdlc_artifact_store/`，不得创建 Skill 私有 Store、私有 Schema 或直接 SQL，不重新设计 Schema。只完成 implement 生产者自检并路由后续 `evaluate`；不进入正式 Eval、adapt、review、push、发布或 Marketplace 写入，也不修改稳定 v1.1 Contract、已批准 Design 或 Eval Plan。
