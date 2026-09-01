# Plugin Development Handoff

## 当前基线

- 主线基线：`main@18d2d73f07be719dee8f813f707e5fe589be2734`。
- 主线最新 GitHub Actions：`33468118983`，结论 `success`。
- 已完成正式能力：`sdlc-000-ctx`、`sdlc-100-req`、Lifecycle Query Graph、`sdlc-status`。
- SpringGear 实时外部仓库 CI 已按主线决定移除；本地 Fixture、Runtime Contract、Skill Interface、Lifecycle Query、Status、Runtime Independence 和全仓单元测试仍由主线 CI 执行。

## 当前工作

- 当前活动 Skill：`sdlc-200-dsn`。
- 当前分支：`skill/sdlc-200-dsn`。
- 当前阶段：`approval`。
- `DESIGN.md`：`ready`。
- `EVAL-PLAN.md`：`ready`。
- Maintainer Design Decision：`pending`。
- 本轮只完成 Design 与 Eval Plan；未创建 `SKILL.md`、Runtime、Fixture、Adapter、Source Lock 或正式 Domain Contract。

## 已收敛设计决定

1. DSN 是一个父 Artifact Set：primary Canonical Blob、全部 required Domain Member、Supporting Member 和 Manifest-Member closure 必须原子一致。
2. 固定 16 个 Design Domain 作为 `sdlc-200-dsn` 私有 bundled contract，不创建 16 个可调用 Skill；`DOM-510` 在 DSN 存在时固定 required。
3. Shared Skill Interface 在 implement 阶段增加向后兼容、可重复的 `--input/-i`，归一化为 `input_references`；现有 CTX、REQ 和 Status 在未使用该参数时行为不变。
4. Lifecycle Query 在 implement 阶段扩展真实 DSN Projection、REQ→DSN Edge 和基于 Lifecycle Applicability 的下一阶段判断；`sdlc-status` 只消费 Projection，不复制 DSN 规则。
5. 设计边界、共享/拆分、关键方案、风险接受、Waiver、法律适用性和 Final Confirmation 均保留明确决策权；默认不由模型静默决定。
6. Runtime 不读取 `docs/**`，不调用兄弟 Skill，不直接 SQL，不把设计文件写入项目源码树，不执行 Git、远端、网络或依赖安装。
7. 当前没有证据表明 DevSDLC 存在新的通用缺口，本阶段不修改 DevSDLC。

## Design 阶段验证

- 已读取适用 `AGENTS.md`、Skill Development Workflow、Design/Eval 模板和当前 Shared Runtime / Skill Interface Contract。
- 已核对 Core、Artifact Store、CTX、REQ、DSN 以及固定 16 份 Domain Spec；DSN Source Lock 计划为 26 项，DSN Artifact Evaluation Contract Set 为 19 项。
- Design DoD：满足。
- Eval Oracle：可判定。
- Blocking Open Item：0。
- 未执行实现测试、行为 Eval 或 Client Adapt；这些不属于当前阶段。

## 唯一下一工作包

进入 `approval`，由 Maintainer 明确执行其一：

```text
approve-design
reject-design
```

批准阶段只记录决定并把唯一下一工作包设为 `implement`；不得在同一工作包创建 Skill、Runtime、Fixture、Adapter，也不得进入实现。
