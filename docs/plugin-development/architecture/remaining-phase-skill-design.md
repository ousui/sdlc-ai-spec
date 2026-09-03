# Remaining Phase Skill Architecture

## 1. 范围

本文件统一约束以下四个正式 Phase Skill 的设计：

```text
sdlc-300-pln
sdlc-400-imp
sdlc-500-vfy
sdlc-600-rls
```

Design-time Source：

- `docs/v1.1/core-spec.md`
- `docs/v1.1/artifact-store-spec.md`
- `docs/v1.1/300-pln-spec.md`
- `docs/v1.1/400-imp-spec.md`
- `docs/v1.1/500-vfy-spec.md`
- `docs/v1.1/600-rls-spec.md`
- 各阶段需要解析的上游稳定 Phase Spec

生产 Runtime 不读取上述路径；实现阶段必须将必要规则转化为 Skill 私有 bundled contract、共享 Runtime Contract、确定性程序和 Source Lock。

## 2. 总体结论

采用“一阶段一个主 Skill”，不把平台、语言、测试工具或执行方式拆成兄弟 Skill：

| Phase | 唯一用户入口 | 主要 Authority |
|---|---|---|
| PLN | `sdlc-300-pln` | 一份 Plan Artifact 与稳定 Work Item Set |
| IMP | `sdlc-400-imp` | 一个 Binding Lineage 对应的 IMP Artifact、Current Claim 与不可变 Result Set |
| VFY | `sdlc-500-vfy` | 一个完整 Delivery Scope 的 VFY Artifact、Method Result 与 Conclusion |
| RLS | `sdlc-600-rls` | 一个 Release Target 的 RLS Artifact 与最终 Release Record |

用户意图使用 Command 表达；同一行为的技术差异由内部 Strategy、Executor 或 Adapter 隔离。任何内部模块都不得拥有第二套 Artifact ID、Revision、Gate 或 Final Confirmation。

## 3. 统一接口

所有 Skill 继承 `sdlc-ai-spec/runtime/skill-interface/v1`：

- 裸调用合法，默认 `auto`；
- 必须支持 `create / revise / check`；
- 必须支持 `help / version / commands / examples`；
- 复用 `--input/-i` 传递多个准确 Scope、Subject、Dependency 或 Control Input；
- 元命令绝对无项目扫描和副作用；
- `decision_policy=user` 为默认；
- `write_policy=auto` 只允许当前 Skill Contract 明确声明的标准项目内局部写入；
- Git、远端操作、依赖安装、Project Root 外写入和真实目标副作用始终需要单独授权；
- `summary` 默认隐藏内部 ID、Digest、Manifest 和 Runtime Envelope。

附加业务命令只在确有独立用户意图时增加：

| Skill | 附加命令 |
|---|---|
| PLN | 无 |
| IMP | `abandon` |
| VFY | `run` |
| RLS | `execute`、`confirm`、`cancel` |

## 4. 统一分层

```text
SKILL.md / Interface Adapter
        ↓
Phase Handler
        ↓
Phase Analyzer + Builder + Verifier
        ↓
Shared ArtifactStore / Lifecycle Query / Execution Evidence
```

- Agent 层解析自然语言、观察工作区、给出候选和最小决策；
- Runtime 层只接收完整结构化输入并执行确定性校验；
- Store 层只负责 Artifact ID、Revision、Payload、Member、Manifest 和摘要；
- Lifecycle Query 只产生只读 Projection，不提供 Artifact Authority；
- 执行层保存实际命令、环境、Subject、输出摘要和原始 Evidence，不保存隐藏推理。

## 5. 共享基础能力决定

### 5.1 PLN

PLN 不要求新的 Authority Provider。它复用：

- ArtifactStore；
- Frozen Artifact Authority；
- Control Input Resolver；
- Lifecycle Query；
- Shared Skill Interface。

Work Item、依赖图、资源冲突域和覆盖关系保持 PLN 私有领域逻辑。

### 5.2 IMP 前置

IMP 实现前必须完成两个共享基础包：

```text
packages/sdlc_claim_provider/
packages/sdlc_resource/
```

`Claim Provider` 是 Binding Lineage、Current Attempt、Owner、Resource Scope、稳定 IMP Artifact ID 和目标 Revision Reservation 的唯一 Authority，至少提供：

```text
resolve
acquire
abandon
complete
```

`Resource` 包负责：

- 项目内 canonical versioned resource ID；
- VCS Locator；
- 实际工作区 Baseline Snapshot；
- 不可变 Result Reference；
- Changed Scope 与 Claim Scope 的包含关系；
- 不移动 Git Ref、不自动 commit/push。

默认实现保持本地、SQLite-only 和 fail-closed；具体 Schema 在实现阶段确定，不进入 Phase Artifact Contract。

### 5.3 IMP / VFY / RLS 共用执行 Evidence

实现阶段应评估并尽量复用一个小型共享包：

```text
packages/sdlc_execution/
```

只负责：

- 结构化命令或人工执行记录；
- 工作目录、时间、退出状态、环境摘要和 Subject 绑定；
- stdout/stderr 或报告的脱敏与 Supporting Member；
- timeout、取消和失败分类；
- 不安装依赖、不扩大权限、不决定 Phase Gate。

若 IMP 实现证明共享抽象没有实际收益，则先保持 Skill 私有；到 VFY 第二次出现相同稳定需求时再提取，避免预先过度设计。

### 5.4 RLS 外部副作用

RLS 不预设平台或 Provider。核心只定义 Release Contract、Release Item、Post-release Confirmation、Evidence 与结论。

外部目标副作用必须使用独立的 `effect authorization`，绑定：

- 准确 RLS Revision；
- Release Reference；
- Release Target；
- Result Set；
- 本次执行的 RLI 集合；
- 不可变 Pre-execution Checklist Digest。

`write_policy`、工作区写权限或 Final Confirmation 均不能替代该授权。

## 6. Authority 边界

| 对象 | Authority |
|---|---|
| PLN Artifact / Work Item | ArtifactStore 中冻结 PLN Revision |
| IMP Binding 执行权 | Claim Provider Current Claim |
| IMP 产品结果 | 不可变 Result Reference + 冻结 IMP Revision + completed Current Claim |
| VFY 产品符合性 | 冻结 VFY Revision 的 Method Result、Target Conclusion、CON-VER / CON-VAL |
| RLS 目标侧结果 | 冻结 RLS Revision 的 RLI、RCF、Evidence 和 Release Conclusion |
| 当前全局状态 | Lifecycle Query Projection，仅只读，不是 Authority |

不得把外部任务编号、分支、可移动 Tag、当前工作树、流水线成功状态或平台页面替代上述 Authority。

## 7. 决策所有权

模型可以自动完成：

- 唯一 Scope/Input/Artifact 解析；
- 固定字段、编号、排序、摘要和 Gate 聚合；
- 可由规则唯一确定的 Applicability；
- 项目文件、构建清单和现有 Artifact 的 observed Evidence；
- 无主观选择的最简单局部实现与确定性方法执行。

默认由用户决定：

- Delivery Scope Aggregation 和 Work Item 拆分存在多个合法方案；
- 新的技术或架构选择；
- Responsible Role 的组织承诺；
- 风险接受、Exception、Waiver 与法律适用性；
- 主观体验或业务 Validation；
- 外部目标副作用；
- Release Target 和真实执行权限。

## 8. 实现顺序

严格按依赖顺序推进：

```text
sdlc-300-pln
    ↓
Claim Provider + Resource Result Foundation
    ↓
sdlc-400-imp
    ↓
sdlc-500-vfy
    ↓
sdlc-600-rls
```

每个阶段合入 `main` 且联合 CI 成功后，下一个阶段才能进入实现。设计可以批量完成，但实现、评测、Review 和 Finalization 必须分别进行。

## 9. 公共完成条件

每个正式 Skill 必须同时满足：

1. bundled runtime contract 与 Source Lock；
2. Runtime Independence；
3. `auto/create/revise/check` 和全部声明命令；
4. open/frozen/abandoned/no-change Revision 语义；
5. 正向、反向、并发、篡改和失败恢复测试；
6. `check` 绝对只读；
7. Lifecycle Query 与 `sdlc-status` 闭环；
8. 用户无需手写内部 JSON、Evidence ID 或 Digest；
9. Codex 静态 Adapter 和真实宿主证据分开报告；
10. PR 中的远端文件、CI、Eval 和 Review 证据可复核。
