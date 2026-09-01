# Skill Design Contract — `sdlc-200-dsn`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-200-dsn` |
| Stage | `design` |
| Status | `ready` |
| Intended Plugin | `sdlc-ai-spec` |
| Base | `main@18d2d73f07be719dee8f813f707e5fe589be2734` |
| Work Item | `docs/plugin-development/work-items/sdlc-200-dsn/` |
| Maintainer Decision | `pending` |

### Design-time Source

- `docs/v1.1/core-spec.md`
- `docs/v1.1/artifact-store-spec.md`
- `docs/v1.1/000-ctx-spec.md`
- `docs/v1.1/100-req-spec.md`
- `docs/v1.1/200-dsn-spec.md`
- `docs/v1.1/200-dsn-domains/*.md`，固定 16 份 Domain Spec

### Bundled Runtime Contract

计划由以下安装后资源承载，不在运行时读取 `docs/**`：

```text
skills/sdlc-200-dsn/**
skills/_shared/**
packages/sdlc_runtime/**
packages/sdlc_artifact_store/**
packages/sdlc_lifecycle/**
scripts/sdlc_skill_interface.py
```

## 2. Problem 与用户结果

### Problem

当前 Plugin 已能建立 CTX、REQ 并查询生命周期状态，但缺少把一个或多个已确认 REQ 转换为可实施、可验证设计结果的统一执行能力。DSN 还包含固定 16 个 Design Domain、复合子领域、多个本地 Member、Manifest 闭包和跨 Domain Gate；若继续依靠临时长提示词，容易遗漏适用性、追踪、成员摘要、设计决策和用户确认边界。

### Intended User Outcome

用户通过短命令即可：

- 自动选择唯一项目和准确 REQ Scope Input；
- 由 Skill 读取 CTX、REQ、项目基线和必要工程事实；
- 只在设计边界、关键取舍、风险接受或多种合法方案无法唯一决定时交互；
- 创建、修订或只读检查一个完整 DSN Artifact Set；
- 得到面向人的设计摘要、变化、关键决策、Domain 适用性、阻塞项和唯一下一动作；
- 无需手工构造 Matrix、Member ID、Evidence ID、Digest、Manifest、Confirmation JSON 或 Runtime Envelope。

## 3. 单一职责

### In Scope

- `create / revise / check` DSN Artifact；
- 一个 REQ 到多个 DSN、多个 REQ 到一个共享 DSN、多个 REQ 到多个 DSN 的边界决策；
- 至少一个准确 frozen REQ Scope Input，以及适用的 VFY Return / `return_dsn` RLS Issue Control Input；
- 唯一 CTX、设计 Scope、Baseline、Change Set、Requirement Traceability、Design Decisions 和 Lifecycle Applicability；
- 固定 16 行 Design Applicability Matrix 与固定 5 行 Composite Domain Subdomain Applicability；
- 只为 `required` Domain 创建 `DOM-*` Member；`DOM-510` 在 DSN 存在时固定 `required`；
- primary Blob、全部本地 Domain / Supporting Member、Manifest 和摘要的原子闭包；
- Core、DSN 和 required Domain subordinate Checks、Final Confirmation、Gate 与 Freeze；
- open Revision 原地修订、frozen Revision 创建新 Revision、无有效变化不创建空 Revision；
- 通过 Lifecycle Query 形成 DSN 后的状态闭环。

### Out of Scope

- 静默修改 REQ Goal、Scope、Requirement 或 Acceptance Criteria；
- 拆解任务、排期、实施负责人或执行顺序；
- 编写产品代码、执行部署、执行 VFY 或给出 Release 结论；
- 将 16 个 Domain 暴露为独立可调用 Skill；
- 自动调用 `sdlc-000-ctx`、`sdlc-100-req`、`sdlc-status` 或其他业务 Skill；
- 写入项目源码树中的设计文件；Canonical Artifact 只进入共享 ArtifactStore；
- Git、远端系统、网络、依赖安装或 Project Root 外写入；
- 运行时读取或解释 `docs/v1.1/**`。

## 4. Trigger Contract

只接受用户显式调用，调用后进入 Exclusive Execution。

### 应触发

| ID | 场景 | Invocation |
|---|---|---|
| TRG-P01 | 为唯一 ready REQ 形成设计 | `/sdlc-200-dsn` 或 `create` |
| TRG-P02 | 为多个准确 REQ 建立共享设计 | `create -i REQ-A@1 -i REQ-B@1` |
| TRG-P03 | 修订准确 DSN Revision | `revise -r DSN-...@1` |
| TRG-P04 | 只读检查准确 DSN Revision | `check -r DSN-...@1` |
| TRG-P05 | 承接准确 VFY / RLS 返工输入 | `create/revise -i <exact item reference>` |

### 不应触发

| ID | 场景 | Required Behavior |
|---|---|---|
| TRG-N01 | 普通架构或技术讨论但未显式调用 | 不加载 Runtime，不写 Store |
| TRG-N02 | 用户要修改 Requirement 业务语义 | 返回 REQ，不代替 REQ 决策 |
| TRG-N03 | 用户要任务拆解、编码、验证或发版 | 说明阶段边界并停止 |
| TRG-N04 | 仅需查询状态 | 交还控制权，不调用 `sdlc-status` |

## 5. Skill Interface Contract

绑定现有 `sdlc-ai-spec/runtime/skill-interface/v1`，并在 implement 阶段做一个向后兼容的公共输入集合扩展。

### Commands

| Command | Default / Alias | Writes | User Outcome |
|---|---|---:|---|
| `auto` | default | conditional | 根据唯一项目、Scope Input、已有 DSN 和请求意图选择 create/revise/check |
| `create` | `--create`、`--command=create`、`-c create`、`--operation=create`、`-o create` | yes | 创建新 DSN Artifact |
| `revise` | shared aliases | yes | 修订准确 DSN Revision |
| `check` | shared aliases | no | 严格只读检查完整 DSN Artifact Set |
| `help / version / commands / examples` | shared | no | 只显示预定义信息 |

### 公共输入集合扩展

现有 `--reference/-r` 继续只表示目标 Artifact Revision；DSN 的多 Scope / Control Input 使用新的公共参数：

```text
--input <exact-reference>
--input=<exact-reference>
-i <exact-reference>
-i=<exact-reference>
```

规则：

- `--input/-i` 可重复；不把逗号字符串静默拆成多个 Reference；
- Parser 在 `SkillCommand` 中新增可选 `input_references` 数组；未使用时为空数组，现有 Skill 行为不变；
- 重复同值去重并返回 warning，保留第一次出现顺序；
- Phase Adapter 再按准确 Reference 分类：基础 `REQ-...@N` 为 Scope Input，`VFY-...@N#RET-*` 与 `RLS-...@N#RLI-* / #RCF-*` 为 Control Input；其他类型失败关闭；
- `--` 后自由文本中的准确 Reference 可以补充候选，但显式 `--input` 优先；两者不一致时进入用户决策，不能合并猜测；
- 元命令不得与 `--input` 等执行参数组合；
- 扩展必须同步更新 Shared Contract、Schema、Parser、CLI Help 和现有 CTX / REQ / Status 回归测试，不改变现有命令输出。

### Common Parameters

| Parameter | Default | Resolution Rule | Ambiguous Behavior |
|---|---|---|---|
| `project_root` | `auto` | 宿主唯一当前工作区 | 列出候选，由用户选择 |
| `artifact_reference` | `auto` | revise/check 的唯一准确 DSN | 不按标题或相似度猜测 |
| `input_references` | `[]` | 显式参数 → 请求中的准确 Reference → Lifecycle Query 唯一候选 | 多候选由用户选择 |
| `decision_policy` | `user` | explicit override | 见下节 |
| `write_policy` | `auto` | 仅标准项目内 ArtifactStore 写入 | 高影响副作用单独授权 |
| `dry_run` | `false` | explicit override | 构造和验证，不持久化 |
| `output` | `summary` | `summary / json / debug` | 不泄露 Secret |

### 裸调用与 `auto`

按以下顺序解决，任何一步出现多个合法选择即停止并请求当前最小决策：

1. 元命令直接返回，不扫描项目；
2. 解析唯一 Project Root；
3. 若提供准确 DSN Reference：materialized open → `revise`；frozen 且无变化意图 → `check`；frozen 且有明确变化意图 → `revise`；
4. 若提供 `--input`：验证完整 Scope / Control Input 集合；
5. 否则通过 `LifecycleQueryService` 找到唯一 active frozen REQ；多个 REQ 不自动选择；
6. 对准确 REQ 集合查找已有 DSN：唯一 matching open DSN → `revise`；唯一 matching frozen DSN 且无变化意图 → `check`；不存在 → `create`；存在多个合法 DSN Boundary → 用户选择；
7. 一个 REQ 是否拆成多个 DSN、多个 REQ 是否共享一个 DSN，依据独立边界、可独立评审、可独立修改或复用判断；默认由用户决定；
8. 上游 Lifecycle Applicability 明确 `DSN=n/a/waived` 且证据闭合时，不创建空 DSN，返回 `completed + artifact=null` 和下一阶段建议；
9. `DSN=pending`、REQ/CTX 不一致或上游事实不足时，不分配新 Artifact。

### 决策所有权

`decision_policy=user` 为默认：模型提出推荐方案、依据、代价和备选，用户决定设计边界、关键技术取舍、主观体验、风险接受、Waiver、法律适用性和残余风险。

`decision_policy=model` 仅在用户明确授权后允许模型从合法技术候选中选择，并记录候选、选择、理由、代价和残余风险；它仍不得：

- 修改 REQ 业务语义；
- 接受 Exception、残余风险或法律/合规适用性；
- 假冒 human Final Confirmation；
- 执行外部或高影响副作用。

`decision_policy=experiment` 必须先确定候选、指标、范围、成本、数据和停止条件；实验结果只能解决可测试的技术选择。

### Human Review Projection

Skill 在用户层渲染非权威、ID-light 的设计审阅视图，至少包含：

- Scope 与 Target State；
- Change 摘要；
- 关键 Decision 与未决选择；
- 16 个 Domain 的处置和完成状态；
- 重要风险、Exception、Open Item；
- 下一动作。

该视图默认只显示必要 Reference，不展示 Manifest、Digest 和完整内部 ID。它不写入项目文件、不提供 Authority；用户自然语言修订必须重新进入规范化、Validator 和 Store 流程。

## 6. Runtime Independence Contract

安装后最小部署单元是整个 Plugin。Runtime 仅依赖：

```text
skills/sdlc-200-dsn/**
skills/_shared/**
packages/sdlc_runtime/**
packages/sdlc_artifact_store/**
packages/sdlc_lifecycle/**
scripts/sdlc_skill_interface.py
```

禁止：

- 读取 `docs/v1.1/**`、Work Item、AGENTS 或 Handoff；
- 读取兄弟 Skill 的私有资源；
- 直接 SQL、私有 Store、私有 Schema 或文件 fallback；
- 联网、安装依赖或动态下载模板；
- 将 Domain 规范复制为不可验证的第二套自由文本。

### Source Lock

`references/source-lock.json` 固化：

- 共享 Runtime Registry 的 5 个 Contract；
- Core、Artifact Store、CTX、REQ、DSN 共 5 个设计期 Spec；
- 固定 16 个 Domain Spec；
- 合计 26 个 Contract ID、Version 和原始字节 SHA-256。

DSN Artifact 自身的 Evaluation Contract Set 只包含 Core、Artifact Store、DSN 和 16 个 Domain Spec，共 19 个规范；CTX/REQ Spec 只用于上游读取与构建验证，不进入 DSN Artifact Gate 的 Evaluation Contract Set。

删除 `docs/**` 后，create/revise/check、全成员闭包、全部 Domain Validator 和 `sdlc-status` 查询闭环仍必须可执行。

## 7. Input Contract

公共 Runtime Envelope 使用 `sdlc-ai-spec/runtime-invocation/v1`。

| ID | Phase Input | Required | Validation | Missing Behavior |
|---|---|---:|---|---|
| IN-01 | `scope_inputs` | yes | 至少一个准确 frozen `REQ-...@N`；Authority 有效 | 零新 Artifact 写入，返回选择/修订 REQ |
| IN-02 | `context_reference` | yes | 从全部 Scope Input 解析为同一准确 frozen CTX | 不选择其他 CTX，失败关闭 |
| IN-03 | `control_inputs` | no | 准确 VFY Return / `return_dsn` RLS Issue | 类型、Return Phase 或目标不符则失败 |
| IN-04 | `design_candidate` | yes for write | 完整结构化设计候选 | Boundary 已确定后可形成 waiting_input open Revision |
| IN-05 | `final_confirmation` | no | human/delegated 精确绑定当前 Payload | 缺失时不冻结 |
| IN-06 | `expected_generation` | no | materialized open 并发代次 | stale 时 blocked |
| IN-07 | `confirmations.artifact_store_write` | create/revise | 当前请求写入授权 | 零写入，action_required |

`design_candidate` 至少包含：

```text
title / summary / scope
baseline_and_change
requirement_traceability
design_decisions
domain_applicability[16]
composite_subdomain_applicability[5]
domain_results{DOM-*}
supporting_members
evidence
exceptions
lifecycle_applicability
```

规则：

- Scope Input 使用准确集合，不使用 `latest/current`；
- 多个 REQ 必须属于同一项目边界并收敛到一个 CTX Revision；否则返回上游修订或拆分建议；
- `ready_with_exception` REQ 与当前 Scope 相交的 Exception 必须 carried；有证据证明不相交或已 resolved/superseded 时才可不 carried；无法判断按相关处理；
- Design Boundary 在任何新 Artifact 分配前必须确定；Domain 内容不足可以在已确定 Boundary 的 open Revision 中形成 Open Item；
- 上游 Requirement 缺失、冲突或不可实现时，返回 `RETURN_TO_REQUIREMENT`，不得在 DSN 内改变业务语义；
- 新建时若预检已发现上游缺陷，不分配 DSN；既有 open DSN 在设计过程中发现缺陷时可保存 `waiting_input` 与准确 OPI，但不得冻结。

## 8. Output Contract

公共 Runtime Result 使用 `sdlc-ai-spec/runtime-result/v1`。

| Outcome | Result |
|---|---|
| 完整通过 | `completed`，frozen `ready / ready_with_exception`，准确 DSN Reference |
| 输入或设计决策不足 | `action_required`，可为 materialized open `waiting_input` |
| 多目标、并发或边界冲突 | `blocked`，不任意选择 |
| Contract、Integrity 或 Gate 失败 | `failed`，`ok=false` |
| DSN 客观 n/a/waived | `completed`，`artifact=null`，`gate=pending`，warning 记录依据与下一阶段 |
| Requirement 需要修订 | `action_required`，`next_action.code=RETURN_TO_REQUIREMENT` |

成功 Store 写入不等于设计成功。只有完整 Payload、全部 necessary Check、Final Confirmation 和 Gate 一致时才冻结。

## 9. Workflow Contract

1. 使用共享 Parser 归一化命令和重复 `input_references`；
2. 解析唯一 Project Root、目标 DSN 和准确 Scope / Control Input；
3. 使用 Lifecycle Query 与 Frozen Authority Verifier 只读验证 REQ、CTX 和既有 DSN；
4. 判断 `n/a/waived`、共享/拆分 Design Boundary 和上游返回条件；
5. 最小读取项目基线，形成 observed/referenced Evidence；不执行项目命令或修改源码；
6. 形成 Scope、Baseline、Change Set、Traceability 和 Design Decision 候选；
7. 按固定顺序判断 16 个 Domain，先处理 140/310 子领域并聚合，强制 510 required；
8. 只加载 required Domain 的完整 bundled contract，构造结构化 Domain Result；
9. Builder 生成 primary Blob、Domain Member、Supporting Member 和 Manifest；
10. Validator 执行领域、跨 Domain、追踪、VFY、Secret、Manifest 和 Gate 检查；
11. create/revise 通过共享 ArtifactStore 原子写入、读回和摘要验证；check 全程只读；
12. 输出 Human Review Projection；满足确认条件后绑定 Final Confirmation、Gate 并 freeze；
13. Lifecycle Query 读回当前 DSN，并给出 PLN 或按 Lifecycle Applicability 跳转后的准确下一 Phase。

## 10. Builder / Validator / Store 边界

| Component | Responsibility | Forbidden |
|---|---|---|
| Skill Adapter | 参数、工作区观察、候选事实、用户决策、summary | 直接 SQL、替代 Domain Validator |
| DSN Normalizer | ID、Reference Set、枚举、固定行和输入模型 | 选择业务语义 |
| Primary Builder | 主文件固定章节、Matrix、Manifest、Gate 外壳 | 写 Store、判断 Authority |
| Domain Builder | 根据 bundled machine-readable contract 渲染 required Member | 创建独立 Artifact ID |
| Domain Validator | 16 Domain 专属字段、ID、枚举和 subordinate Checks | 修改输入迁就 Gate |
| Cross-domain Validator | Scope、Baseline、Traceability、Decision、冲突、VFY 汇总、复合聚合 | 静默修复 Requirement |
| Shared Runtime | Envelope、Authority、Control Input、Source Lock | DSN 领域判断 |
| ArtifactStore | ID、Revision、原子闭包、摘要、Freeze | 设计内容判断 |
| Lifecycle Query | 准确状态、Graph、Frontier、Next Action Projection | 提供 Artifact Authority |

## 11. Shared / Private Boundary

计划实现结构：

```text
skills/sdlc-200-dsn/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── interface.json
│   ├── contract.md
│   ├── source-lock.json
│   ├── domain-catalog.json
│   └── domains/
│       ├── DOM-110.json
│       └── ... DOM-510.json
├── assets/
│   ├── dsn-template.md
│   └── domain-shell.md
└── scripts/
    ├── runtime.py
    └── dsn/
        ├── normalize.py
        ├── builder.py
        └── validator.py
```

规则：

- `runtime.py` 是唯一入口；私有模块不是 Skill；
- `domain-catalog.json` 只保存 16 个固定 Code、名称、Member Name、复合关系、顺序和 Contract 文件；
- 每个 Domain JSON 保存固定 section/table schema、枚举、ID pattern 和 subordinate Check；AI 可先读取 Catalog 的适用性摘要，只为 required Domain 读取完整 contract；
- Build-time Validator 必须从 16 份 Design-time Spec 提取并核对 Code、文件名、表头、枚举和 Check ID，禁止不可校验的手工双写；
- 不创建 16 个独立 `SKILL.md`；
- 只有重复输入集合和 DSN 生命周期查询属于共享修改，其他全部保持 Skill 私有。

## 12. Domain 与 Artifact Set Invariants

- Matrix 固定 16 行，顺序和中英文名称不可变；
- Composite 表固定 5 行；140/310 按 `pending → required → waived → n/a` 聚合；
- `DOM-510` 在 DSN Artifact 存在时固定 required，不能整体 waived 或 n/a；
- `pending` 必须引用 OPI；`n/a` 必须有准确 Basis 与客观原因；`waived` 必须引用有效父 Exception；
- 只为 required Domain 生成 Member；required Member 的 Canonical Name、Media Type、SHA-256 和 Manifest 必须一一闭合；
- 110–420 的 VFY Point 必须被 510 VFY Objective 汇总；510 不生成重复 `VFP-510-*`；
- primary Blob 是唯一 Summary、Scope、Decision、Matrix、Open Item、Exception 和 Gate 权威；Domain Member 不复制这些控制信息；
- Gate 顺序固定为 Core → DSN-G-001..010 → required Domain subordinate Checks；每个 Check ID 只出现一次；
- 任何 Member 语义变化都触发父 DSN Revision 变化；frozen Revision 不可原地修改。

## 13. Failure Contract

| Failure | Required Behavior | Forbidden Fallback |
|---|---|---|
| 无 REQ 或多个合法 REQ | action_required，列出准确候选 | 选最近、标题最像或最高 Revision |
| 多个合法 DSN Boundary | 推荐 + 用户决定 | 任意共享或拆分 |
| Scope Input 使用不同 CTX | blocked / RETURN_TO_REQUIREMENT | 选择任一 CTX |
| REQ Authority 无效 | failed，零新 DSN 分配 | 降级读取文件 |
| Requirement 缺失、冲突或不可实现 | RETURN_TO_REQUIREMENT | 在 DSN 改写业务语义 |
| required Domain 缺 Member 或 incomplete | open waiting_input 或 Gate fail，不冻结 | 当作 n/a |
| n/a 无 Basis / waived 无 Exception | fail 或 waiting_input | 自动补理由 |
| Composite 聚合不一致 | fail | 采用顶层结果覆盖子领域 |
| Domain 冲突或重复权威 | blocked / fail | 选择其中一个版本 |
| Traceability / VFY 覆盖缺口 | Gate fail 或 waiting_input | 生成空映射 |
| Manifest、Member、摘要不闭合 | failed，整个 Revision 不可解析 | 忽略缺失成员 |
| stale Final Confirmation | `CORE-G-009=fail`，不冻结 | 自动重签 |
| check 缺 Store / Store 损坏 | failed 且零写入 | initialize / repair |
| 真实 Secret 候选 | 拒绝持久化并要求脱敏 Reference | 写入 Member |

## 14. 权限与副作用

| Capability | Required | Scope | Authorization |
|---|---:|---|---|
| Read project and Store | yes | 最小必要项目内容 | 显式调用 |
| Standard ArtifactStore write | create/revise | `.sdlc/store.sqlite3` 当前 DSN | `write_policy` |
| Store Supporting Member bytes | conditional | 非 Secret、当前 DSN 闭包 | `write_policy` |
| Execute project commands | no by default | None | 单独明确授权 |
| Project source/config write | no | None | 不属于本 Skill |
| Git / remote / network / install | no | None | 单独明确授权且仍非标准流程 |

## 15. Exclusive Execution

- 仅显式调用；
- 不调用兄弟 Skill / Plugin；
- 不把本 Skill 授权传递给外部工具；
- 外部输出仅作为候选 Input / Evidence，必须重新验证；
- 内部可分批分析 Domain，但只有一个父 DSN Builder、Validator、Gate 和 Store 提交；
- 无法独立完成时保存准确状态并停止；
- 该约束是模型执行 Contract，不宣称不可绕过的硬隔离。

## 16. Portability

| Concern | Portable Core | Cursor | Claude Code | Codex |
|---|---|---|---|---|
| Runtime / Store / Domain Contract | required | adapter only | adapter only | adapter only |
| Explicit invocation | required | Unknown | Unknown | target for first adapt |
| Repeatable argument tail | required | Unknown | Unknown | must verify |
| Project path / installed cache | required | Unknown | Unknown | must verify |
| Human review interaction | required | Unknown | Unknown | must verify |
| Behavior evidence | automated core | not claimed | not claimed | adapt stage direct evidence |

一次只适配一个 Client；未执行的平台不得声明 Verified。

## 17. 共享实现前置

Implement 阶段允许且必须先完成两个最小共享扩展，然后再实现 DSN 私有 Runtime：

1. **Skill Input Set**：为 Shared Skill Interface 增加可选、重复的 `--input/-i` 与 `input_references`，保持现有 Skill 行为和 Contract ID 向后兼容；
2. **Lifecycle DSN Projection**：让 Lifecycle Query 读取真实 DSN、构建 REQ→DSN Edge，并依据 DSN Lifecycle Applicability 给出 PLN 或跳过后的下一 Phase；不得在 `sdlc-status` 中复制 DSN 规则。

两项扩展必须在同一分支接受独立单元测试和全仓回归；不修改 DevSDLC。只有两个以上真实 Work Item 证明 DevSDLC 通用模板缺口时才更新 DevSDLC。

## 18. Eval Plan

对应：

```text
docs/plugin-development/work-items/sdlc-200-dsn/EVAL-PLAN.md
```

必须覆盖全部 16 Domain、复合聚合、多 REQ、Artifact Set 闭包、Source Lock、Runtime Independence、`sdlc-status` 闭环和 Codex 实际行为。

## 19. Design DoD

- [x] 名称符合 `sdlc-NNN-xxx`；
- [x] 单一职责和阶段边界明确；
- [x] Design-time Source、Bundled Runtime Contract 和 Evaluation Contract Set 已区分；
- [x] Runtime 不读取 `docs/**`；
- [x] Shared Contract / Package 与 Skill 私有边界明确；
- [x] `references/interface.json`、裸调用和元命令已设计；
- [x] 重复输入参数、长短写法、冲突和默认推断已设计；
- [x] 用户决策、模型委托、实验和 Final Confirmation 边界明确；
- [x] 标准 Store 写入与高影响副作用边界明确；
- [x] Input / Output / Workflow / Failure Contract 明确；
- [x] Builder / Validator / Store / Lifecycle Query 分层明确；
- [x] 16 Domain、复合 Domain、DOM-510 和完整闭包不变量明确；
- [x] Human Review Projection 边界明确；
- [x] Runtime Independence、Source Lock 和 Closed-loop Eval 已设计；
- [x] 阻塞 Open Item 为零；
- [x] 未创建正式 `SKILL.md`、Runtime、Fixture 或 Adapter。

## 20. Open Items

| ID | Question | Blocks | Expected Source | Status |
|---|---|---|---|---|
| None | No blocking open items | N/A | N/A | closed |

## 21. Maintainer Decision

| Role | Decision | Basis |
|---|---|---|
| Maintainer | `pending` | Design 已达到 ready；等待明确 `approve-design` 或 `reject-design` |
