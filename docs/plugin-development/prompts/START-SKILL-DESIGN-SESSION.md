# Start Skill Design Session

```text
承接 sdlc-ai-spec Plugin 的一个 design 工作包。

Candidate Skill Name：
<sdlc-NNN-xxx>

Intended User Outcome：
<一句话用户结果>

Design-time Source：
- <docs/v1.x path>
- <其他必要来源>

本轮只允许创建：

- docs/plugin-development/work-items/<skill-name>/DESIGN.md
- docs/plugin-development/work-items/<skill-name>/EVAL-PLAN.md
- docs/plugin-development/HANDOFF.md

开始前读取：

- 当前路径适用的 AGENTS.md
- docs/plugin-development/DEVELOPMENT.md
- docs/plugin-development/SKILL-DEVELOPMENT-WORKFLOW.md
- docs/plugin-development/HANDOFF.md
- 两份模板
- 本轮最小 Design-time Source
- skills/_shared/README.md
- packages/sdlc_artifact_store/CONTRACT.md（Artifact Skill 时）

设计必须明确：

1. 名称符合 sdlc-NNN-xxx；
2. docs/v1.x 只作为 design-time Source；
3. Runtime 不读取 docs/**；
4. Bundled Runtime Contract、Shared Contract、Shared Package 的边界；
5. 标准 Invocation / Result Envelope；
6. Phase Builder、Domain Validator、ArtifactStore 的职责；
7. Runtime Independence Test；
8. 触发、输入、输出、失败、权限和 Eval；
9. 不依赖兄弟业务 Skill。

不得：

- 创建 SKILL.md；
- 创建 Runtime Script、Asset 或 Fixture；
- 修改稳定 Spec；
- 修改 Manifest；
- 自动进入 approval 或 implement；
- push 或外部写入。

全部 Design DoD 满足且阻塞项为零时可以标记 ready；
不得自行标记 approved。

完成后执行 git diff --check，更新 Handoff，只登记一个下一工作包并停止。
```
