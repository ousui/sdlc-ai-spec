# SDLC v2 structured runtime implementation

## Authority and baseline

- Baseline: `main@f25ed518f662c0ac7306c94f845297f5642c44b2` (read and confirmed from GitHub).
- Approved design: user-reviewed `sdlc-v2-detailed-design.zip`, design dated 2026-09-09, including DESIGN.md, DATABASE.md, schema-model.sql, ACCEPTANCE.md and HANDOFF.md.
- Current user explicitly authorizes implementation, testing, two additional complex-demand rounds, commits, pushes and PR progress within this work package. This supersedes the older per-session single-stage stop rule for this package only.
- Do not merge main, tag or publish a release. Preserve the baseline and use this isolated branch.

## Checkpoints

1. A: normative contracts, initialization, CTX, structured SQLite model and diagnostic entry.
2. B: REQ / DSN / PLN domain commands and projections.
3. C: IMP / VFY execution evidence, findings and convergence.
4. D: RLS local delivery, assets, snapshot/copy/return and baseline evolution.
5. E: replace superseded runtime/tests/manifests and validate installed-copy behavior.
6. Baseline closure against the recorded projects in ousui/test-sdlc.
7. Complex round 1: evidence-backed requirements selected after reading project records.
8. Complex round 2: additional requirements and repair/regression as needed.

## Evidence boundaries

- Local schema or deterministic fixture PASS is not actual host Skill execution PASS.
- Record exact source commit and the commands/exit codes/files used for each result.
- Product repositories are disposable verification workspaces. No product deployment, product remote writes or credential exposure.
- Read retained test-sdlc project requirements before selecting scenarios.
- Do not mark the user's core acceptance met until actual Skill-guided REQ -> DSN -> PLN -> IMP -> VFY -> RLS on those projects has run and evidence is retained.

## 2026-09-09 本地执行覆盖

当前用户通过 goal-objective.md 批准连续实施、三项目三轮真实 Skill 验证、修复与本地 commit。
本工作包覆盖旧单会话单阶段、禁止连续调用和 v1 兼容限制；不修改宿主安全限制。
只修改可丢弃产品副本。独立评审或互不干扰产品副本可以并行，共享 Schema/契约/进度单写。
本地优先，默认不 push，不 merge/tag/release，不改产品上游；上述旧 pushes 授权以此收紧。
已批准设计复制至 docs/work-items/sdlc-v2/approved-design，顶部待批准为历史措辞。
唯一进度和下一动作见 docs/work-items/sdlc-v2/PROGRESS.md；旧 Handoff 不再指定本包动作。
当前客户端将显式读取安装版 Skill 并走公开 CLI；不冒称原生发现认证或独立 AI 审查。
