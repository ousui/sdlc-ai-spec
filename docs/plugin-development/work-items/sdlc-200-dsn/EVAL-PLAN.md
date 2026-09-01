# Skill Eval Plan — `sdlc-200-dsn`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-200-dsn` |
| Design Contract | `docs/plugin-development/work-items/sdlc-200-dsn/DESIGN.md` |
| Stage | `design` |
| Status | `ready` |
| Design Status | `ready` |
| Maintainer Decision | `pending` |

本文件只定义 Case、Oracle 和 Pass Gate，不记录未执行结果。

## 2. 目标

验证：

1. 显式调用、负向抑制、裸调用和统一参数；
2. 新增重复 `--input/-i` 后 Shared Skill Interface 仍向后兼容；
3. 一个/多个 REQ 与一个/多个 DSN 的边界决策不被模型静默选择；
4. CTX、REQ、VFY Return、RLS Issue 使用准确 frozen Authority；
5. Scope、Baseline、Change、Traceability、Decision 与 Lifecycle Applicability 完整；
6. 固定 16 Domain、5 个复合子领域和 `DOM-510` 规则完整；
7. primary Blob、Domain Member、Supporting Member、Manifest 和摘要原子闭合；
8. Builder、Validator、ArtifactStore、Lifecycle Query 分层；
9. open/frozen/no-change Revision 行为；
10. Requirement 问题返回 REQ，不在 DSN 修改业务语义；
11. Human Review Projection 可读且不提供 Authority；
12. Runtime Independence、Source Lock、Exclusive Execution 和无 Secret；
13. DSN 冻结后 `sdlc-status` 能形成下一阶段闭环；
14. Codex 实际安装、发现、显式调用和参数尾行为。

## 3. Core Checks

| Check ID | Requirement | Pass Condition |
|---|---|---|
| CHK-01 | Explicit invocation | 仅显式调用进入 Skill |
| CHK-02 | Negative suppression | 未调用或错误阶段不执行 Runtime |
| CHK-03 | Bare invocation | 唯一项目与唯一 Scope 时自动推进最大确定性范围 |
| CHK-04 | Interface aliases | 子命令、command、operation 和快捷别名归一化一致 |
| CHK-05 | Repeatable input | `--input/-i` 可重复、去重、保序并稳定分类 |
| CHK-06 | Meta commands | help/version/commands/examples 零扫描、零 Runtime、零写入 |
| CHK-07 | Defaults | 默认值来源稳定、可审计，不使用主观置信度 |
| CHK-08 | Conflict handling | 未知、缺值、引号、目标/输入冲突失败关闭 |
| CHK-09 | Decision ownership | 共享/拆分 Boundary 和多方案默认由用户决定 |
| CHK-10 | Model delegation | model/experiment 只在明确授权下运行且受保护决定不越权 |
| CHK-11 | Write policy | auto/confirm/deny 仅控制标准 Store 写入 |
| CHK-12 | Standard input | Runtime 请求符合 Invocation Schema 和 DSN Input Contract |
| CHK-13 | Standard output | Result Schema 通过，summary 不暴露内部协议 |
| CHK-14 | Missing input | 不猜测；按分配前/分配后边界返回或 materialize open |
| CHK-15 | Upstream Authority | CTX/REQ/Control Input 准确、冻结、Authority 有效 |
| CHK-16 | Requirement return | 上游缺陷返回 REQ，不静默改变业务语义 |
| CHK-17 | Design cardinality | one-to-many / many-to-one / many-to-many 可判定且不重复假设 |
| CHK-18 | Domain catalog | 16 行、顺序、名称、Code 和 Member Name 全等 |
| CHK-19 | Composite domains | 140/310 子领域聚合、Waiver 和 Exception 传播正确 |
| CHK-20 | DOM-510 | DSN 存在时固定 required，VFY Objective 覆盖完整 |
| CHK-21 | Traceability | REQ/AC/Change/Decision/Domain/VFY 双向可追踪 |
| CHK-22 | Baseline and change | Scope + Baseline + Change 唯一确定 Target State |
| CHK-23 | Cross-domain consistency | 无冲突、重复权威或未授权复杂度 |
| CHK-24 | Artifact set | Member 集合、身份、名称、Media Type、原始字节和摘要闭合 |
| CHK-25 | Gate aggregation | Core → DSN → required Domain Check，ID 唯一、优先级正确 |
| CHK-26 | Revision semantics | open 原地、frozen 新 Revision、no-change 零新 Revision |
| CHK-27 | Human review | ID-light、可读、非权威、修订重新验证 |
| CHK-28 | Runtime independence | 删除 docs 后 Critical Fixture 通过 |
| CHK-29 | No sibling invocation | 不调用其他业务 Skill / Plugin |
| CHK-30 | Source lock | 26 个 Contract ID、Version、Digest 全等 |
| CHK-31 | Secret boundary | Secret/Token/私钥/密码不进入 Blob 或 Member |
| CHK-32 | Lifecycle closure | `sdlc-status` 读取真实 DSN 并给出准确下一 Phase |
| CHK-33 | Client evidence | Codex 真实宿主证据可复现；未测平台不声明 Verified |

## 4. Interface Cases

| Case ID | Invocation | Expected Outcome | Forbidden Behavior |
|---|---|---|---|
| EV-UX01 | bare | `auto`，唯一 ready REQ 时进入 create 候选 | 要求用户写长提示词 |
| EV-UX02 | `create` / `--create` | create | |
| EV-UX03 | `command create / cmd=create / -c=create` | create | |
| EV-UX04 | `operation create / op=create / -o=create` | create | |
| EV-UX05 | `revise -r DSN-...@1` | revise | 把 `-r` 当 REQ Input |
| EV-UX06 | `check --reference=DSN-...@1` | check，严格只读 | |
| EV-UX07 | `-i REQ-A@1 -i=REQ-B@1` | 两个 Scope Input，第一次出现顺序保留 | last wins |
| EV-UX08 | 重复相同 `--input` | 去重 + warning | 创建重复 Front Matter Input |
| EV-UX09 | `-i VFY-...@2#RET-001` | 分类为 DSN Control Input | 当作 Scope Input |
| EV-UX10 | 不支持的 Input 类型 | `ARGUMENT_VALUE_INVALID` 或稳定 Phase error | 静默忽略 |
| EV-UX11 | `-h/--help` | 只显示帮助和新增 input 语法 | 扫描项目 |
| EV-UX12 | `-V/--version`、commands、examples | 预定义信息 | 执行 Runtime |
| EV-UX13 | 多个不同 operation | `ARGUMENT_CONFLICT` | last wins |
| EV-UX14 | `--input` 缺值 / unknown option / quote error | 稳定参数错误 + help 入口 | 猜测值 |
| EV-UX15 | 显式 `--input` 与自由文本 Reference 冲突 | 推荐 + 用户决定 | 自动并集 |
| EV-UX16 | 多个 active REQ | 列出准确候选和建议 | 选最新或标题最像 |
| EV-UX17 | 多个 matching DSN Boundary | 用户选择 create/revise/check 目标 | 任意选取 |
| EV-UX18 | `decision_policy=model` | 记录候选、理由、代价和残余风险 | 接受 Exception/法律适用性 |
| EV-UX19 | `decision_policy=experiment` | 先固定指标、成本和停止条件 | 模型偏好冒充实验 |
| EV-UX20 | `write_policy=auto/confirm/deny` | 标准 Store 写入边界准确 | 扩展到 Git/源码写入 |
| EV-UX21 | `output=summary/json/debug` | 三种输出事实一致，层次不同 | summary 泄露 Digest/Secret |

### Shared Interface 回归

新增 `input_references` 后必须重新执行 CTX、REQ、Status 的全部参数测试：

- 未使用 `--input` 时 normalized command 与现有快照一致；
- 元命令仍拒绝执行参数；
- `-i` 不占用既有短参数；
- Skill Interface Schema、Skill Command Schema 和 CLI Help 同步；
- 现有 `references/interface.json` 无需强制新增字段。

## 5. Phase Critical Cases

### 5.1 正向与状态转换

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-C01 | 单 REQ、一个明确 Boundary、代表性 required Domain：110/220/230/240/310/510 | frozen `ready` DSN，全部 Member 闭合，准确 Reference |
| EV-C02 | 固定 16 Domain 全部 required 的完整 Fixture | 16 个 `DOM-*` Member、全部 subordinate Check 唯一且通过 |
| EV-C03 | 两个同 CTX ready REQ，共享一个独立 Design Boundary | 一个 DSN，Front Matter 含两个准确 Scope Input，Traceability 全覆盖 |
| EV-C04 | 一个 REQ 明确拆成两个可独立评审 Boundary | 用户选择后只创建当前一个 DSN；另一个不被隐式创建 |
| EV-R01 | materialized open DSN 补齐输入 | 原 Revision 原地修订，generation 增加 |
| EV-R02 | frozen DSN 有有效设计变化 | 同 Artifact 创建新最大 Revision，Base Revision 准确 |
| EV-R03 | frozen DSN 无有效变化 | no-change，Artifact/Revision 数不变 |
| EV-K01 | check frozen ready / ready_with_exception | 严格只读，完整 Payload、Domain 和 Gate 复核通过 |
| EV-K02 | check 缺 Store | `STORE_NOT_FOUND`，不创建 `.sdlc` |
| EV-K03 | check 损坏 Store | fail closed，原始字节不变，不 repair |

### 5.2 不适用、缺失与上游返回

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-N01 | REQ 明确 `DSN=n/a` 且准确 Basis 闭合 | `completed`、`artifact=null`、无 DSN 分配、下一阶段明确 |
| EV-N02 | REQ 明确 `DSN=waived` 且有效上游 Exception | `completed`、`artifact=null`、warning 保留 Waiver 依据 |
| EV-M01 | Boundary 已确认但关键 Design Decision 缺失 | materialized open `waiting_input`，OPI 阻塞准确项 |
| EV-M02 | Boundary 尚未确定 | 零 DSN Artifact 分配，用户决定共享/拆分边界 |
| EV-U01 | REQ Requirement 与 AC 冲突 | `RETURN_TO_REQUIREMENT`，不得在 DSN 改写 REQ |
| EV-U02 | 既有 open DSN 设计中发现上游缺陷 | 保存 waiting_input + OPI，停止冻结并返回准确 REQ |
| EV-I01 | 多个 Scope Input 绑定不同 CTX | blocked / RETURN_TO_REQUIREMENT，不选择任一 CTX |
| EV-I02 | REQ `ready_with_exception` 与 DSN Scope 相交 | 父 DSN Exception 为 carried；遗漏时 Gate fail |
| EV-I03 | 无法证明上游 Exception 不相交 | 按相关处理，不允许静默丢弃 |
| EV-I04 | VFY Return 的 Return Phase 非 DSN | Control Input 失败，零新 DSN 分配 |
| EV-I05 | RLS Issue disposition 非 `return_dsn` | Control Input 失败 |
| EV-I06 | Control Input 未被 Change/Decision/Domain 准确承接 | `DSN-G-001=fail/pending`，不算已解决 |

### 5.3 Scope、Baseline、Traceability 与复杂度

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-B01 | incremental 变更 | Baseline + Change Set 可还原 Target State |
| EV-B02 | new 变更 | Baseline `N/A` 具有客观不存在原因 |
| EV-B03 | reuse 变更 | 准确 immutable Baseline、适配结论和 Evidence 完整 |
| EV-B04 | 可移动分支/路径作为版本基线 | Gate fail，不接受移动引用 |
| EV-T01 | 每个 R/AC 映射到 Design 与 VFY | `DSN-G-003=pass` |
| EV-T02 | 孤立 Design Item 或遗漏 AC | `DSN-G-003=fail` |
| EV-T03 | DSN 新增未经 REQ 确认的业务规则 | RETURN_TO_REQUIREMENT / Gate fail |
| EV-S01 | 直接实现足够但候选选择复杂抽象 | `DSN-G-009=fail` 或要求有效 Decision 依据 |
| EV-S02 | 多 DSN Target State 冲突 | blocker OPI，不任意覆盖 |

## 6. Domain Contract Cases

### 6.1 Catalog 完整性

Build-time Validator 必须从稳定 Spec 重新提取并与 bundled contract 比较：

```text
DOM-110 DOM-120 DOM-130 DOM-140
DOM-210 DOM-220 DOM-230 DOM-240
DOM-310 DOM-320 DOM-330 DOM-340 DOM-350
DOM-410 DOM-420 DOM-510
```

逐项核对：固定顺序、中英文名称、Canonical Member Name、section/table header、枚举、ID pattern 和 subordinate Check ID。缺一项、重复、重排或未知 Domain 均失败。

### 6.2 Disposition 与 Member

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-D01 | required Domain + complete Member | Completion=complete，Content Reference 准确 |
| EV-D02 | required Domain 无 Member | open 可为 not_started；不得 freeze |
| EV-D03 | required Domain 有 incomplete Member | in_progress + OPI；不得 freeze |
| EV-D04 | n/a + 准确 Basis/客观原因 | not_applicable，无 Member |
| EV-D05 | n/a 无 Basis 或因工作量小 | fail/pending，不接受 |
| EV-D06 | waived + 有效父 EX | waived，无 Member，父 Status 可派生 exception |
| EV-D07 | waived 无 EX / EX 已关闭 | fail |
| EV-D08 | pending + OPI | not_started，Gate pending |
| EV-D09 | pending 无 OPI | fail |
| EV-D10 | n/a/waived/pending 创建了 Member | Manifest / Domain Contract fail |

### 6.3 复合 Domain

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-D140-01 | Accessibility required，I18N n/a | DOM-140 required，单 Member，只填 required 详细设计 |
| EV-D140-02 | 任一子领域 pending | 顶层 pending，不创建 Member，不通过 Gate |
| EV-D140-03 | required + waived 混合 | 顶层 required，Waiver 仍传播父 Exception |
| EV-D310-01 | Security required，Privacy/Compliance n/a | DOM-310 required，聚合和子表一致 |
| EV-D310-02 | Compliance waived、其他 n/a | 顶层 waived，有效 EX，无 Member |
| EV-D310-03 | 顶层结果与子领域不一致 | `DSN-G-007` / subordinate Check fail |

### 6.4 代表性领域语义

| Case ID | Domain | Invalid Fixture | Expected Failure |
|---|---|---|---|
| EV-110 | Workflow | Step 无 Transition / State 不可解析 | `DSN-DG-110-*` fail |
| EV-210 | Architecture | Driver 无响应 / 系统责任冲突 | `DSN-DG-210-*` fail |
| EV-230 | Interface | Contract 字段或错误语义不闭合 | `DSN-DG-230-*` fail |
| EV-240 | Data | Lifecycle/一致性/迁移缺失 | `DSN-DG-240-*` fail |
| EV-310 | Security | 威胁无 Control、真实 Secret、风险无责任方 | `DSN-DG-310-*` fail |
| EV-340 | Compatibility | 切换/回滚/共存不确定 | `DSN-DG-340-*` fail |
| EV-410 | Deployment | 猜测默认值、Secret 明文、失败行为缺失 | `DSN-DG-410-*` fail |
| EV-420 | Operability | 信号、告警、责任和操作动作不闭合 | `DSN-DG-420-*` fail |
| EV-510 | Verifiability | AC/Decision/VFY Point 未汇总或 Pass Criteria 不可判定 | `DSN-DG-510-*` fail |

其他 7 个 Domain 至少各有一个正向 required Fixture、一个 n/a Fixture和一个固定表/枚举反例；不能只靠 all-16 Fixture 冒充专属语义验证。

### 6.5 DOM-510

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-510-01 | DSN 存在但 DOM-510=n/a/waived/missing | fail，不冻结 |
| EV-510-02 | 所有 AC、关键 Decision、其他 required Domain VFY Point 均映射 | pass |
| EV-510-03 | Objective 无可观察结果或不可判定 Pass Criteria | fail/pending |
| EV-510-04 | Method waived 但无父 Exception | fail |
| EV-510-05 | 需要可验证性机制但未返回 Host Domain | fail |
| EV-510-06 | 强制无依据覆盖率/自动化比例/工具 | fail |

## 7. Artifact Set 与 Gate Cases

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-A01 | primary + required Domain + supporting bytes | 单事务写入、读回、闭包和摘要通过 |
| EV-A02 | required Member 缺失 | 不冻结；完整 Revision 解析/Gate 失败 |
| EV-A03 | 未登记额外 Member | Manifest closure fail |
| EV-A04 | Member ID / Canonical Name 重复 | fail |
| EV-A05 | Media Type / Domain Spec / Digest 不匹配 | fail |
| EV-A06 | Supporting Member 含 Secret | 写入前拒绝，Store 原样 |
| EV-A07 | frozen 后 Member 改字节 | 必须创建父新 Revision，原 Revision 不变 |
| EV-G01 | Domain subordinate Check 重复 | fail，Check ID 只允许一次 |
| EV-G02 | required Domain Check fail | 父 Gate=fail |
| EV-G03 | 无 fail 但有 pending | 父 Gate=pending |
| EV-G04 | 全部关闭且无 Exception | pass / ready |
| EV-G05 | 全部关闭且有未关闭有效 Exception | pass_with_exception / ready_with_exception |
| EV-G06 | stale Control / Check Digest 或 Exception Set | `CORE-G-009=fail`，不得 freeze |
| EV-G07 | delegated Final Confirmation 非独立、含 Exception 或越权决定 | 拒绝 |

## 8. Lifecycle Query 与 Status 闭环

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-L01 | REQ→frozen DSN，PLN=required | Graph 有准确 REQ→DSN Edge；Frontier=DSN；下一 Skill=`sdlc-300-pln` unavailable |
| EV-L02 | frozen DSN，PLN=n/a/waived，IMP=required，单一 resource Scope Token | 下一 Phase=IMP；不得固定返回 PLN |
| EV-L03 | PLN skip 条件不闭合或多 resource | blocker / PLN required，不直接 IMP |
| EV-L04 | DSN open / failed / Authority invalid | Status 显示 action_required/blocked，不当作下游 Authority |
| EV-L05 | 多个 DSN 并行支撑不同 REQ | Projection 保留并行前沿，不创建全局 current DSN |
| EV-L06 | Lifecycle Query 执行前后项目快照 | 零写入、零缓存、零修复 |

`packages/sdlc_lifecycle` 是唯一状态逻辑位置；`sdlc-status` 只消费 Projection，不复制 DSN 规则。

## 9. Human Review 与输出

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-H01 | 完整 DSN summary | 显示 Scope、Change、Decision、Domain 状态、风险和下一步；默认隐藏 Digest/Manifest |
| EV-H02 | 多个待决策项 | 只提出当前最小决策，并给推荐、理由和备选 |
| EV-H03 | 用户用自然语言修订 review | 重新规范化和验证，不直接修改 frozen 内容 |
| EV-H04 | `output=json` | 单个标准 Runtime Result，无额外非 Schema 字段 |
| EV-H05 | `output=debug` | 包含参数来源、candidate、member metadata 和 Runtime Result；Secret 脱敏 |
| EV-H06 | review 视图被用户编辑为文件 | 不自动导入、不提供 Authority，除非重新进入显式输入流程 |

## 10. Failure Injection 与并发

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-F01 | open generation stale | blocked，不 last-write-wins |
| EV-F02 | 写 primary 后 Member 写失败 | 整个事务回滚，无部分 Payload |
| EV-F03 | read-back digest mismatch | failed，不 Final Confirmation |
| EV-F04 | ArtifactStore Schema mismatch | failed，不自动迁移/repair |
| EV-F05 | Foundation package 缺失 | 稳定错误，无 traceback 冒充用户结果 |
| EV-F06 | 同一 frozen Revision 并发 revise | 一个成功，其余冲突；Revision 不复用 |
| EV-F07 | 两次显式 create 同 Scope | 允许独立 Design Boundary；若 Boundary 未区分则要求用户确认，不假定重复 |

## 11. Runtime Independence 与 Source Lock

在隔离部署目录只保留：

```text
manifests
skills/**
packages/**
scripts/**
```

删除：

```text
docs/**
tests/**
AGENTS.md
CLAUDE.md
```

必须执行：

- one-REQ create；
- many-REQ shared create；
- all-16 Domain create/check；
- open revise；
- frozen revise；
- n/a no-artifact；
- Control Input；
- Manifest tamper；
- `sdlc-status` DSN Projection。

Runtime 源码和工具参数不得包含 `docs/v1.1`、Work Item 或 Handoff 路径。`source-lock.json` 只保存 Contract ID、Version、Digest。

Source Lock Oracle：

- 5 个 Shared Runtime Contract；
- Core / Store / CTX / REQ / DSN 5 个 Spec；
- 16 个 Domain Spec；
- 总计 26，零重复、零遗漏、零清单外项；
- DSN Evaluation Contract Set 固定 19 个 Spec；
- 任一设计期源字节变化必须使 build-time lock 校验失败。

## 12. Exclusive Execution 与 With/Without

| Case ID | Fixture | Expected Outcome |
|---|---|---|
| EV-X01 | 未授权兄弟 Skill canary | call log 为空，canary 不存在 |
| EV-X02 | 外部设计工具输出 | 仅作 candidate/evidence，冲突时不覆盖 Contract |
| EV-X03 | Skill 无法完成 required Domain | waiting_input/failed 并停止，不调用其他 Skill |
| EV-W01 | 同一复杂 DSN 输入 with-skill vs without-skill | with-skill 的 Matrix、Traceability、Member 和 Gate 更完整稳定 |
| EV-W02 | 同一多 REQ Boundary 输入 | with-skill 不静默共享/拆分，without 结果原样保留 |

With/without 使用同一 Fixture、同一权限和同一评分 Oracle；不得修改输入迁就结果。

## 13. Codex Adapt Cases

| Case ID | Scenario | Required Evidence |
|---|---|---|
| EV-P01 | Plugin install/cache Discovery | 能发现 `sdlc-200-dsn`，未显式调用时不加载 |
| EV-P02 | Bare invocation | 唯一项目/REQ 时进入正确 auto 路径 |
| EV-P03 | Repeatable argument tail | `-i` 多次传递后 normalized command 全等 |
| EV-P04 | Human decision interaction | 多 Boundary 只询问一次当前最小决策 |
| EV-P05 | Installed runtime independence | Tool Call 只访问安装缓存和目标项目，不访问开发 docs/tests |
| EV-P06 | Sandbox / permission denial | fail closed，不描述为成功 |

Cursor、Claude Code 未执行时保持 `Unknown`；静态 metadata 只能记 `Partial`。

## 14. Oracle Protection

- Fixture、Expected Outcome、固定 Domain Code、Check ID 和 Pass Gate 在 implement 前冻结；
- all-16 Fixture 不得由被测 Runtime 反向生成 Expected Outcome；
- 实现者不得删除失败 Case、把 fail 改成 warning、把 required 改成 n/a，或减少 Domain 数量；
- with/without、Revision、tamper 和 Client Case 必须保留原始失败；
- 重试、人工补充、模型决策和实验步骤必须记录；
- 真实宿主未执行时不得声称 Verified；
- SpringGear 或其他外部仓库不是持续 CI 依赖；需要真实项目复核时使用授权的一次性临时副本并记录精确 Commit，远端零写入。

## 15. Evidence Contract

`EVAL-RESULTS.md` 至少记录：

- Case ID、Client / Surface / Version；
- Skill Commit、Foundation/Shared Commit；
- 原始参数与 normalized command；
- Scope Input、Control Input、CTX、Boundary 和决策记录；
- Fixture 与不可变项目基线；
- primary / Member 数量、Code、Name、Media Type 和摘要校验结果；
- Gate Check 数、失败 ID、Final Confirmation Mode；
- Artifact / Revision / generation 前后状态；
- 实际输出与副作用；
- Human Review Projection；
- 是否调用其他 Skill / Plugin；
- 是否在删除 docs 后执行；
- `sdlc-status` Projection 和下一阶段；
- 重试、人工介入、失败根因和返回阶段。

## 16. Pass Gate

- [ ] Shared `--input/-i` 扩展及 CTX/REQ/Status 全回归通过；
- [ ] Interface Critical Case 全通过；
- [ ] Phase Critical Case 全通过；
- [ ] 16 个 Domain 均有专属正向、n/a 和结构反例证据；
- [ ] 140/310 Composite 和 510 mandatory Case 全通过；
- [ ] all-16 Artifact Set、Manifest、Gate 和 Revision Case 全通过；
- [ ] Runtime Independence 与 26 项 Source Lock 通过；
- [ ] Secret、Sibling Invocation 和外部副作用为零；
- [ ] Lifecycle Query / `sdlc-status` DSN 闭环通过；
- [ ] Codex 目标 Surface 有实际证据；
- [ ] 全仓单元测试、静态 Validator、`git diff --check` 和 GitHub Actions 通过；
- [ ] Fresh Review Verdict=`PASS`，Blocker=0，Major=0；
- [ ] 未执行平台不声明 Verified；
- [ ] 精确最终分支 HEAD 已 push，远端必需文件检查通过。
