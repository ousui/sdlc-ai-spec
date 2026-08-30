# Plugin Development Handoff

## 当前目标

在不让正式 Skill 运行时依赖 `docs/**` 的前提下，将稳定领域规范转换为
自包含、可验证、可跨 Agent 运行的 Phase Skills。

## 当前阶段

- 当前没有活动 Skill Work Item。
- `main` 不包含正式 Phase Skill。
- 旧的 CTX Work Item 已清理，不再作为后续实现输入。
- 下一正式 Skill 使用新名称 `sdlc-000-ctx`，从零重新设计。

## 已完成的 Foundation

### Shared ArtifactStore

- 共享实现：`packages/sdlc_artifact_store/`
- 运行时 CLI：`scripts/sdlc_artifact_store.py`
- 物理 Store：`<project-root>/.sdlc/store.sqlite3`
- 九个逻辑操作、严格只读入口、事务、Revision、摘要和 Member closure 已实现。
- 34 个自动化测试通过；详细证据见组件 Test Results。

### Shared Skill Runtime Contracts

- 共享 Contract：`skills/_shared/contracts/`
- 标准 Schema：`skills/_shared/schemas/`
- 正式 Skill 命名：`sdlc-NNN-xxx`
- `docs/v1.x/**` 只作为 design/build/review Source。
- 正式 Runtime 不读取 `docs/**`。
- Plugin 是最小部署单元；业务 Skill 不依赖兄弟 Skill。
- Artifact Skill 统一使用共享 ArtifactStore，不直接 SQL。

## 当前验证

基础命令：

```bash
python3 -m compileall packages scripts
python3 tools/validate_runtime_contracts.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

## 未实现

- 尚无正式 `SKILL.md`。
- 尚无 CTX / REQ / DSN 等 Phase Builder 和 Domain Validator。
- 尚未执行 Runtime Independence 的真实 Phase Fixture。
- 尚未执行三个 Agent 的 Skill Discovery / Invocation / Behavior 验证。
- Human Review View 与 Projection 尚未实现。

## 下一唯一工作包

在分支：

```text
skill/sdlc-000-ctx
```

执行 `design`：

- Work Item 名称：`sdlc-000-ctx`
- Design-time Source：稳定 Core、Artifact Store 与 CTX Spec
- Runtime Contract 必须自包含，不读取 `docs/**`
- 使用 `skills/_shared/**`
- 使用 `packages/sdlc_artifact_store/`
- 只创建 `DESIGN.md`、`EVAL-PLAN.md` 和必要 Handoff
- 不创建 `SKILL.md`
- 不进入 approval 或 implement

达到 design 停止条件后结束。
