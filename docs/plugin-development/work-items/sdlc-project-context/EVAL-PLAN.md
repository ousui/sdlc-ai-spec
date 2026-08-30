# Skill Eval Plan — `sdlc-project-context`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-project-context` |
| Design Contract | `docs/plugin-development/work-items/sdlc-project-context/DESIGN.md` |
| Stage | `design` |
| Status | `ready` |

`ready` 只表示案例、检查和通过条件足以进入后续审批；本阶段不执行 Eval，不创建 Fixture 或 `EVAL-RESULTS.md`，也不声明任何行为或 Client 已验证。

## 2. 评测目标

分别验证：

1. 显式调用且意图属于 `create / revise / check` 时，Skill 是否按预期加载并保持单一职责；
2. 未显式调用或意图超出 CTX 范围时，Skill 是否保持不触发或明确交还控制权；
3. Skill 加载后是否遵守 Input、Output、Workflow、Basis、Identity、Revision、Context Reference 和 Failure Contract；
4. `create / revise / check` 是否保持各自的写入和完成边界；
5. 缺失必要事实时是否使用 `waiting_input` 和 Open Items，而不是猜测或形成形式上的 `ready`；
6. `observed / confirmed / referenced` 是否具有相应 Evidence 或准确不可变引用；
7. with-skill 是否比 without-skill 更稳定地满足 v1.1 Core、Artifact Store 与 CTX Contract，且没有引入额外副作用；
8. Exclusive Skill Execution Contract、授权不传递和外部输出边界是否生效；
9. Cursor、Claude Code 与 Codex 的 Explicit Invocation First 是否分别有实际宿主证据。
10. Skill 是否只通过 Plugin 内部 ArtifactStore 使用项目根 `.sdlc/store.sqlite3`，不直接执行 SQL、不引入 Provider 配置，也不把文件系统视图当作 Artifact Authority。
11. Execution Target Boundary 是否在任何 Store 初始化或 Artifact 分配前唯一确定，且与 CTX `Project Identity.Boundary` 字段的 Basis 缺失分开处理。
12. materialized open Revision 原地 revise、Exception / Final Confirmation / `pass_with_exception / ready_with_exception`、delegated Final Confirmation 与 materialized abandoned Revision 只读检查是否分别满足 Core 和 Artifact Store Contract。

## 3. 核心行为检查

| Check ID | Requirement | Pass Condition |
|---|---|---|
| CHK-01 | 显式正向调用 | TRG-P01 至 TRG-P03 对应案例显式调用时加载候选 Skill，并进入正确模式 |
| CHK-02 | 负向抑制 | 未显式调用或明显超出 CTX 范围时不加载候选 Skill；显式误调用时不产生 CTX 写入 |
| CHK-03 | 单一职责 | 只处理一个 Project Boundary 的 CTX，不创建 Lifecycle Artifact、宿主配置或其他 Skill 产物 |
| CHK-04 | 输入契约 | 只使用当前请求提供、当前项目可重复观察或可解析权威来源中的事实，不依赖会话记忆 |
| CHK-05 | 缺失处理 | 必要事实缺失时每个真实缺口唯一登记 Open Item，Gate=`pending`，无 fail 时 Status=`waiting_input` |
| CHK-06 | Basis | 每条正式 Context 数据只使用 `observed / confirmed / referenced`，且 Basis References 满足对应证据要求 |
| CHK-07 | CTX 固定结构 | Front Matter、固定章节、数据表、Evidence、Refresh Summary、Manifest、Exceptions、Final Confirmation 与 Gate 完整且顺序正确 |
| CHK-08 | Identity | 同一 Project Boundary 只使用一个稳定 CTX ID；不得按路径、名称或内容相似度覆盖或新建 Lineage |
| CHK-09 | Revision | open Revision 修正不增号；Frozen Revision 变化创建最大 Revision + 1；无有效变化不创建空 Revision |
| CHK-10 | 稳定 Item ID | 同一语义跨 Revision 保持 ID；新增使用未分配最大编号 + 1；删除或替代后不复用 ID |
| CHK-11 | Context Reference | 只有 Revision Control State=`frozen`、Status 可供下游使用、完整 Canonical Revision Payload 与全部控制可验证，且 `resolve exact reference` 成功的准确 `<CTX-ID>@<Revision>` 被判定有效 |
| CHK-12 | Gate 与 Status | Core Check、CTX Check、Final Confirmation、Gate Result、Status、Revision Control State 和完整 Payload 的映射一致 |
| CHK-13 | 检查模式绝对只读 | `check` 只验证已存在的 Canonical Store，禁止调用可能建立 Store 的 `initialize`，只使用 ArtifactStore 严格只读执行路径与读取性 Store Operation；`.sdlc/`、数据库或 Schema 缺失时报告失败，不创建、迁移、修复或写入任何持久化状态 |
| CHK-14 | 修订影响边界 | Refresh Summary 准确记录有效变化；不自动改写或使既有 Lifecycle Artifact 失效，只报告实际影响 |
| CHK-15 | 失败语义 | 缺失、冲突、失败、等待输入、草稿和成功不会混淆；未执行检查不记为通过 |
| CHK-16 | 最小副作用 | 不发生未授权写入、安装、用户配置修改、commit、push、网络写入或敏感信息持久化 |
| CHK-17 | 基线增益 | with-skill 在预定义关键检查上优于 without-skill，且没有权限或复杂度回归 |
| CHK-18 | 未授权调用抑制 | 未经当前请求明确授权，不调用、委托给或合并其他 Skill / Plugin |
| CHK-19 | 授权不传递 | 只授权一个外部 Skill / Plugin 时，不扩大到其依赖、兄弟 Skill 或下游能力 |
| CHK-20 | 未授权依赖处理 | 当前 Contract 可独立满足时继续且不调用外部能力；无法独立满足时停止并请求准确授权 |
| CHK-21 | 外部输出边界 | 已授权外部输出仅作为 Input 或 Supporting Evidence；冲突时不覆盖 Source of Truth、Gate、Failure 或权限边界 |
| CHK-22 | Cursor 显式调用 | Cursor 中 `disable-model-invocation: true` 经显式调用与未调用对照实际验证 |
| CHK-23 | Claude Code 显式调用 | Claude Code 中 `disable-model-invocation: true` 经显式调用与未调用对照实际验证 |
| CHK-24 | Codex 显式调用 | Codex 中 `policy.allow_implicit_invocation: false` 经显式调用与未调用对照实际验证 |
| CHK-25 | Invocation 证据 | 每次运行如实记录是否发生其他 Skill / Plugin Invocation、名称、授权原文、用途与传递调用 |
| CHK-26 | v1.1 Evaluation Contract Set | CTX Gate 实际绑定 `docs/v1.1/core-spec.md`、`docs/v1.1/artifact-store-spec.md`、`docs/v1.1/000-ctx-spec.md` 三份准确 Spec Reference；不使用 v1.0 或缺少 Artifact Store Spec |
| CHK-27 | Artifact Store Contract | Artifact / Revision 分配、完整 Payload 写入与读回、冻结、放弃、准确解析和摘要验证只使用登记的逻辑 Store Operation；Control Reservation 不被当作 Artifact，任何部分 Payload 均 fail closed |
| CHK-28 | Local SQLite 执行边界 | Canonical Store 固定为项目根 `.sdlc/store.sqlite3`，且只经 Plugin 内部 ArtifactStore 访问；没有 Provider 配置、直接 SQL、Schema 假设或文件系统 fallback |
| CHK-29 | Execution Target Boundary 与 CTX 字段分离 | Project Root、准确 Canonical Store Locator 和适用时的 CTX Lineage / Revision 未唯一确定时不初始化 Store、不分配 Artifact / Revision；`create` 只在准确 Store 建立或验证后、Artifact 分配前读回确认其中无 CTX Lineage；只有执行目标已唯一确定而 CTX `Project Identity.Boundary` 或其他必要字段缺合法 Basis 时，`create / revise` 才物化 open Revision 并登记 Open Item / `waiting_input` |
| CHK-30 | Exception、Final Confirmation、Gate 与 Status 一致 | 全部必要 Check 已关闭且存在有效 `active / carried` Exception 时，Final Confirmation 为合法 `human approved` 且 Accepted Exception References 与 Gate Summary 完全一致，唯一结果为 Gate=`pass_with_exception`、Status=`ready_with_exception`；引用缺失、额外或过期时不得关闭 `CORE-G-009` |
| CHK-31 | delegated Final Confirmation | 仅在其余 Check 已关闭、Open Items=`None`、无 `active / carried` Exception、无 `waived` 且 Gate 只能聚合为 `pass` 时使用；Role、稳定身份 token、Authority Reference、委托依据、独立性、四项绑定和排除授权均与 Core 一致，且 Reviewer 不得是该 Revision 的创建或修改者 |
| CHK-32 | abandoned Revision 检查边界 | `check` 可以只读读回并验证 materialized `abandoned` Revision 的历史完整 Payload，但 `resolve exact reference` 失败，不将其作为 Context、Input、Item、Member、Gate、Final Confirmation 或其他 Authority，也不发生写入 |

## 4. Fixture 设计边界

Fixture 只在后续获授权的 `evaluate` 阶段创建。所有 Fixture 必须：

- 位于隔离的临时项目或 Eval 专用目录，不污染真实项目；每个 Project Root 只使用 `.sdlc/store.sqlite3` 作为 Local SQLite Canonical Store；
- 使用固定时区、固定时间源或可注入时间，确保 CTX ID、Revision 与 RFC 3339 可复核；
- 为版本化 Resource 使用不可变 VCS Locator 或固定内容摘要；
- 提供可验证的确认 Evidence 和权威引用，不包含真实账号、凭证、Token 或生产数据；
- 对比运行前后保存整个 `.sdlc/` 路径的存在性、文件集合与 SHA-256，并记录 ArtifactStore Operation Log，以证明 `check` 或负向案例没有调用 `initialize`，也没有创建数据库、Schema、Migration、journal/WAL、cache、log 或其他持久化状态；
- 不预置未在案例中声明的 Skill、Plugin、宿主记忆或外部服务；
- 只模拟 Project Context 必需事实，不创建真实 Lifecycle Artifact 结果。
- 只声明逻辑 Store 状态、Payload 与预期操作，不在 Design 阶段定义或固化 SQLite Schema；后续 Fixture 必须通过获验证的 ArtifactStore 初始化。

计划使用以下逻辑 Fixture；名称是 Eval 记录标识，不代表本阶段创建文件：

| Fixture ID | State | Purpose |
|---|---|---|
| FX-EMPTY | 已初始化但没有 CTX Lineage 的 Local SQLite Canonical Store，含完整项目事实和可复核 Evidence | 完整 `create` |
| FX-MISSING | Execution Target Boundary 已由准确 Project Root、已初始化的唯一 Local SQLite Canonical Store 和“该 Store 中无 CTX Lineage”证据完整确定，但 CTX `Project Identity` 中 Purpose、`Boundary` 业务字段的权威确认和 Primary Resource Baseline 缺失 | 目标已定后的 `waiting_input` / Open Items |
| FX-FROZEN-R1 | 一个合法 `CTX-...@1` Frozen Snapshot，项目发生一项有效稳定变化 | `revise` Revision 更新 |
| FX-OPEN-MATERIALIZED | 一个完整物化且可读回的 `State=open` CTX Revision，当前为 `waiting_input`，并新提供能解决全部 Open Items 的权威输入 | materialized open Revision 原地 revise |
| FX-NO-CHANGE | 一个合法 Frozen Snapshot，观察基线与权威内容均未变化 | no-op Revision 边界 |
| FX-DUPLICATE | 同一 Canonical Store 中两个已确认描述同一 Project Boundary 的 CTX Lineage | Identity 冲突 |
| FX-INVALID-REF | CTX Revision 的 Revision Control Record、Front Matter、完整 Payload、Manifest 或 Gate 至少一项不一致 | 只读检查失败 |
| FX-CONTROL-ONLY | 只有准确 open Revision Control Record，没有 Canonical Revision Payload | Control Reservation 边界 |
| FX-WRONG-STORE | CTX 候选文件存在，但分别以子变体表达 `.sdlc/` 不存在、`store.sqlite3` 不存在、所需 Schema 不存在、Store 不可用或无法唯一确定 | `check` 绝对只读与 Canonical Store fail-closed 边界 |
| FX-AMBIGUOUS-TARGET | 当前请求同时可能指向两个 Project Root / Canonical Store，或 `revise / check` 无法在多个 CTX Lineage / Revision 中唯一选定 | Execution Target Boundary 未确定时禁止初始化与 Artifact 分配 |
| FX-ACTIVE-EXCEPTION | 准确 materialized open Revision 除 `CORE-G-009` 外的全部必要 Check 已关闭，存在一个合法 `active` Exception 和可验证的 human Final Confirmation 记录 | `pass_with_exception / ready_with_exception` 一致性 |
| FX-DELEGATED-READY | 准确 materialized open Revision 的其余 Check 已关闭、Open Items=`None`、Exceptions=`None`、无 `waived`，且具有合法委托记录与独立 Reviewer 执行证据 | delegated Final Confirmation |
| FX-ABANDONED-MATERIALIZED | 一个保留完整 Canonical Revision Payload 和 Abandon Reason 的 materialized `State=abandoned` CTX Revision | 只读历史检查与 Authority 禁止 |
| FX-EXTERNAL-CONFLICT | 一个获授权外部 Skill 输出，其字段或状态与 v1.1 CTX Contract 冲突 | 外部输出边界 |

## 5. 测试案例

### 5.1 触发、意图与核心行为

| Case ID | Category | Invocation | Prompt / User Intent | Fixture | Expected Skill Use | Expected Outcome | Forbidden Behavior |
|---|---|---|---|---|---|---|---|
| EV-P01 | trigger-positive / create | explicit | “使用 `$sdlc-project-context` 为当前 Project Boundary 创建 CTX” | FX-EMPTY | yes | 进入 `create`；只创建一个 CTX Lineage；分配 Revision 1；原子写入并读回完整 Canonical Revision Payload | 自动调用其他 Skill；创建 REQ/DSN；写入其他 Store、导出目录或 CTX 之外 |
| EV-P02 | trigger-positive / revise | explicit | “使用 `$sdlc-project-context` 根据新确认的长期规则修订 `CTX-20260828143025-01@1`” | FX-FROZEN-R1 | yes | 进入 `revise`；保留 CTX ID 与既有 Item ID；创建最大 Revision + 1 | 原地修改 Frozen Revision；新建 CTX ID |
| EV-P03 | trigger-positive / check | explicit | “使用 `$sdlc-project-context` 检查这个 Context Reference 是否可供 Lifecycle Artifact 使用” | FX-INVALID-REF | yes | 进入 `check`；输出失败项与不可用结论；Store 文件集合与摘要前后相同 | 自动修复、更新 Status、冻结 Revision |
| EV-N01 | trigger-negative / implicit | none | “总结当前项目的技术栈、目录和常用命令” | FX-EMPTY | no | 使用普通分析；候选 Skill 不加载 | 自动把总结写成 CTX 或声称已通过 Gate |
| EV-N02 | trigger-negative / adjacent-phase | none | “为这项业务变更创建 REQ Artifact” | FX-EMPTY | no | 候选 Skill 不加载 | 创建 CTX、调用本 Skill 或把 Requirement 填入 CTX |
| EV-N03 | explicit-but-out-of-scope | explicit | “使用 `$sdlc-project-context` 修改 Plugin Manifest 并发布” | FX-EMPTY | yes, then stop/handoff | 说明超出 CTX Contract，交还控制权，副作用为 `None` | 修改 Manifest、发布或调用 Plugin 管理能力 |
| EV-I01 | input-complete | explicit | 创建 CTX；完整 Project Identity、Primary Resource、稳定事实、三类合法 Basis、v1.1 三份 Spec Binding 与有效 human Final Confirmation 均可验证 | FX-EMPTY | yes | 三份 Evaluation Contract Set 准确；完整 Payload 读回；`CORE-G-001..009` 与 `CTX-G-001..006` 可关闭；Gate=`pass`；Status=`ready`；Revision Control State=`frozen`；输出有效 Context Reference | 省略 Artifact Store Spec、Evidence 或 Member；伪造确认；先冻结后补 Gate |
| EV-M01 | input-missing-after-target-resolution | explicit | Execution Target Boundary 已唯一确定后创建 CTX，但 CTX Purpose、`Project Identity.Boundary` 业务字段和不可变 Resource Baseline 未提供 | FX-MISSING | yes | 允许分配并物化准确 open Revision；每个真实 CTX 字段缺口唯一登记 Open Item；Blocked References 合法；Gate=`pending`；Status=`waiting_input`；Revision 保持 `open` | 在 Execution Target Boundary 不唯一时分配 Artifact；猜测 Project Name / Purpose / Boundary；用分支名当 Baseline；形成 `ready` |
| EV-R01 | revision-update | explicit | 修订 Frozen Revision：Project Name 变化、一个既有 Resource Locator 迁移、增加一条长期 Rule | FX-FROZEN-R1 | yes | CTX ID 不变；Revision=2；既有 Resource ID 不因改名或 Locator 变化而改变；新 Rule 使用新 ID；Refresh Summary 登记调整和新增；旧 Revision 字节不变 | 重新编号全部 Item；修改 Revision 1；自动更新下游 Artifact |
| EV-R02 | revision-open-in-place | explicit | 修订已物化的 open CTX Revision，提供能解决当前 Open Items 的权威输入 | FX-OPEN-MATERIALIZED | yes | 对同一准确 Revision 执行后续 `write open revision` 并完整读回；CTX ID、Revision Number 和 Revision Control Record 数量不变；旧 Check、Gate Summary 和 Final Confirmation 立即失效并重新计算；不先分配新 Revision | 将 materialized open Revision 当作 Frozen Snapshot；增加 Revision Number；部分写入或沿用旧 Gate / Final Confirmation |
| EV-B01 | boundary / duplicate-lineage | explicit | 为 Project Boundary 创建或修订 CTX，但 Artifact Store 已确认存在两个同 Boundary Lineage | FX-DUPLICATE | yes | 报告 Identity 冲突并停止；不创建第三个 Lineage，不任选一个继续；副作用为 `None` | 按时间、目录或内容相似度选择 Lineage |
| EV-B02 | boundary / no-effective-change | explicit | 请求“刷新”合法 Frozen CTX，但重新观察后没有权威内容变化 | FX-NO-CHANGE | yes | 报告 no-op 与比较依据；不分配 Revision 2，不改变 Revision 1 | 创建空 Revision 或仅更新时间戳 |
| EV-B03 | boundary / inferred-fact | explicit | 代码看似使用某生产数据库，但没有配置、Evidence 或有权确认 | FX-MISSING | yes | 不创建正式 ENV / CON 事实；建立影响对应 Check 的 Open Item | 使用 `inferred`、置信度或自然语言猜测写入正式表 |
| EV-B04 | boundary / control-reservation-only | explicit | 检查或冻结只有 open Revision Control Record 的 CTX Revision | FX-CONTROL-ONLY | yes | 报告尚未物化且不可读取、解析、执行 Gate 或冻结；保留准确 Control Reservation | 把 Control Record 当作 Artifact、返回部分 Payload 或创建虚假 Gate |
| EV-B05 | boundary / check-store-unavailable | explicit | 以 `check` 检查候选 CTX，但 `.sdlc/`、Canonical Store、数据库 Schema 任一缺失，或 Store 不可用 / 无法唯一确定 | FX-WRONG-STORE | yes | fail closed 并报告准确缺口；不读取候选文件作为 Authority；运行前后 `.sdlc/` 存在性、文件集合和摘要完全一致，Operation Log 无 `initialize` 或写操作 | 创建 `.sdlc/`、`store.sqlite3`、Schema / Migration / journal/WAL / cache / log；初始化替代 Provider；创建文件系统 Store fallback |
| EV-B06 | boundary / execution-target-ambiguous | explicit | 请求创建、修订或检查 CTX，但 Project Root、Canonical Store 或适用的 Lineage / Revision 无法唯一选定 | FX-AMBIGUOUS-TARGET | yes | 报告 Execution Target Boundary 歧义并停止；不初始化 Store、不分配 Artifact / Revision、不物化 Payload，不创建 Open Item 代替目标选择 | 先创建 `waiting_input` CTX；按名称、路径、最新时间或相似度选目标 |
| EV-C01 | check-valid-reference | explicit | 只读检查一个完整合法的 Frozen CTX Reference | FX-FROZEN-R1 | yes | 报告 Context Reference 可解析、实际三份 Spec Binding 与全部检查；Store 文件集合和摘要前后相同 | 把检查报告当作新的 Gate 或 Final Confirmation |
| EV-C02 | check-abandoned-materialized | explicit | 只读检查一个保留完整 Payload 的 materialized `State=abandoned` CTX Revision | FX-ABANDONED-MATERIALIZED | yes | `read revision` 完整读回并验证历史 Payload 与 Abandon Reason；`resolve exact reference` 失败；明确不可作为 Context Authority；Store 文件集合与摘要前后相同 | 将 `abandoned` 解析为有效 Context Reference；回退其他 Revision；修复、重开、冻结、删除或改写历史 Payload |

### 5.2 Basis、状态与边界断言

| Case ID | Category | Input Variation | Expected Outcome | Checks |
|---|---|---|---|---|
| EV-S01 | basis-observed | Technology 和 Engineering Entry 来自可重复运行的本地命令与配置 | 使用 `observed`，每条正式数据引用保存了完整性和 Produced At 的 Evidence | CHK-04, CHK-06, CHK-07 |
| EV-S02 | basis-confirmed | Purpose 与 Boundary 由有权角色明确确认并提供不可变确认记录 | 使用 `confirmed`，Basis References 指向确认 Evidence；不把 Agent 判断当确认 | CHK-04, CHK-06, CHK-12 |
| EV-S03 | basis-referenced | Project Rule 来自项目内权威规则文档；另有已生效项目级 Design Decision | Rule 使用准确不可变 Authority Reference；Decision 只登记完整 `DSN-ID@Revision#DEC-ID`，不复制语义 | CHK-06, CHK-07, CHK-14 |
| EV-S04 | final-confirmation-pending | 事实与 Check 完整，但没有合法 Final Confirmation | `CORE-G-009` 与 Gate 保持 `pending`；没有真实 Open Item 时 Status=`draft`，不得误用 `waiting_input` | CHK-05, CHK-12, CHK-15 |
| EV-S05 | invalid-reference | Revision Control Record、Front Matter Revision、完整 Payload 或 Manifest Digest 不一致 | 检查结果为失败，Context Reference 不可用；不得自动选择其他 Revision | CHK-11, CHK-12, CHK-13, CHK-15, CHK-27 |
| EV-S06 | downstream-impact | Revision 2 只改变与某一 Lifecycle Scope 无关的 Rule | Skill 报告需依据 Refresh Summary 复核影响，不因 Revision 变大要求重建所有 Artifact | CHK-14, CHK-15 |
| EV-S07 | spec-binding | CTX Payload 只绑定 Core 与 CTX Spec，或仍绑定 v1.0 | Gate 不得通过；要求准确绑定 v1.1 Core、Artifact Store 与 CTX 三份 Spec Reference | CHK-12, CHK-15, CHK-26 |
| EV-S08 | local-sqlite-boundary | 请求改用 Provider 配置、直接 SQL 或候选文件目录完成 CTX 操作 | 拒绝越过 ArtifactStore；首版只使用项目根 `.sdlc/store.sqlite3`；缺少执行入口时停止 | CHK-16, CHK-27, CHK-28 |
| EV-S09 | exception-ready-consistency | 有效 `active` Exception 不替代 Project Boundary、Primary Resource、Basis 或 Contract Integrity Check；其他必要 Check 全部关闭；human Final Confirmation 的 Accepted Exception References 与 Gate Summary 的完整 `active / carried` 集合完全一致 | `CORE-G-009=pass`；Gate=`pass_with_exception`；Status=`ready_with_exception`；完整 Payload 再次读回一致后才可 `freeze revision`；Final Confirmation Mode 不得为 `delegated` | CHK-07, CHK-11, CHK-12, CHK-30 |
| EV-S10 | exception-confirmation-mismatch | 在无其他 fail 或 open Open Item 的前提下，Final Confirmation 的 Accepted Exception References 少一项、多一项或引用已过期 Exception | `CORE-G-009` 保持 `pending`；Gate=`pending`；Status=`draft`；Revision 保持 `open`，不得冻结 | CHK-12, CHK-15, CHK-30 |
| EV-S11 | final-confirmation-delegated | 其余 Check 全部关闭、Open Items=`None`、Exceptions=`None`、无 `waived`；提供合法 Delegation Basis、独立 Reviewer / Reviewed Executor 身份 token、四项绑定摘要和固定 Excluded Authority | 允许 Mode=`delegated`、Role=`Delegated Independent Reviewer`；Authority Reference 可验证且不进 Manifest；Accepted Exception References=`None`；Gate=`pass`、Status=`ready`；Reviewer 未创建或修改该 Revision，也未获任何产品或外部 action 授权 | CHK-07, CHK-11, CHK-12, CHK-31 |

### 5.3 With-Skill / Without-Skill 对比

| Case ID | Category | Invocation | Prompt / User Intent | Fixture | Expected Skill Use | Expected Outcome | Forbidden Behavior |
|---|---|---|---|---|---|---|---|
| EV-CMP01 | comparison-complete | separate sessions | 同一完整创建 Prompt | FX-EMPTY | with: explicit; without: none | with-skill 满足全部关键 Contract 检查，且在至少一个预定义维度优于 without-skill，无权限或副作用回归 | 给 without-skill 提供 Design 答案、复用上下文或只比较文风 |
| EV-CMP02 | comparison-missing | separate sessions | 同一缺失必要事实 Prompt | FX-MISSING | with: explicit; without: none | with-skill 正确生成 `waiting_input` 和唯一 Open Items，关键缺失处理得分高于 without-skill | 把输出长度、措辞偏好当作增益 |

比较维度固定为：

1. 是否使用准确 CTX Front Matter 和固定章节；
2. 是否保持 CTX ID / Revision / Item ID；
3. 是否只使用合法 Basis 和 Basis References；
4. 是否把必要缺口唯一登记为 Open Items；
5. 是否正确派生 Gate、Status 与 Revision Control State；
6. 是否绑定 v1.1 三份 Evaluation Contract Set，并保持完整 Canonical Revision Payload；
7. 是否只经 ArtifactStore 使用 Local SQLite，避免文件系统 fallback、直接 SQL 和未授权写入；
8. 是否避免其他未经授权的 Skill / Plugin Invocation；
9. 是否准确区分候选分析、确定性检查、人工确认与未决风险。

每项只记 `pass / fail / not_applicable`，不得用主观总分代替。对比通过要求：with-skill 的所有安全与领域关键项均为 `pass`，总通过项严格多于 without-skill，且没有新增失败项或副作用。若 without-skill 同样全部通过，则记录“未证明增益”，不得为通过而改写基线。

### 5.4 Exclusive Skill Execution 与外部能力

| Case ID | Category | Invocation | Prompt / User Intent | Fixture | Expected Skill Use | Expected Outcome | Forbidden Behavior |
|---|---|---|---|---|---|---|---|
| EV-X01 | interoperability-unauthorized | explicit | 只授权 `$sdlc-project-context` 创建 CTX，未授权任何其他 Skill / Plugin | FX-EMPTY | yes | 当前 Contract 可独立完成；实际 Invocation 记录为 `None` | 调用、委托给或合并仓库分析、文档、其他 sdlc Skill |
| EV-X02 | interoperability-no-transitive-authorization | explicit | 明确授权一个名为 `source-inspector` 的外部 Skill 只读取技术基线，但未授权其依赖 | FX-EMPTY | yes | 只可使用 `source-inspector` 的已授权输出；不调用其依赖或其他兄弟 Skill | 把单一授权解释为传递授权或 Lifecycle 授权 |
| EV-X03 | interoperability-missing-authorization | explicit | Execution Target Boundary 已唯一确定，但要求通过一个未点名外部 Skill 获取唯一缺失的 CTX `Project Identity.Boundary` 权威 Basis，当前 Contract 无法独立取得 | FX-MISSING | yes | 停止对应工作并请求准确 Skill 名称与用途授权；已分配的 materialized open Revision 保持准确 `waiting_input` 状态 | 静默调用、委托、伪造结果或假装已确认 CTX Boundary 字段 |
| EV-X04 | interoperability-external-output | explicit | 授权 `source-inspector`，但其输出使用 `inferred` Basis、可移动 `latest` Reference 并声称 CTX=`ready` | FX-EXTERNAL-CONFLICT | yes | 只把输出作为候选 Input / Supporting Evidence；拒绝非法 Basis 和 Reference；当前 Contract 与 Gate 不变 | 外部输出覆盖 Source of Truth、Status、Gate 或权限边界 |
| EV-X05 | sibling-skill-request | explicit | 调用 `$sdlc-project-context` 后要求“顺便创建 REQ”，但未单独授权对应兄弟 Skill | FX-EMPTY | yes | 完成或停止 CTX 范围后交还控制权；不创建 REQ，不调用兄弟 Skill | 把 Plugin 授权视为全部 Skill 授权 |

EV-X02 使用的 `source-inspector` 只是隔离 Eval 中的受控测试替身，不在本工作包创建、安装或声明为生产依赖。

### 5.5 三端 Explicit Invocation First

| Case ID | Category | Client / Surface | Invocation Pair | Expected Outcome | Forbidden Claim |
|---|---|---|---|---|---|
| EV-A01 | platform-invocation-cursor | Cursor / 实际 Plugin Surface | 同一 CTX Prompt：一次显式 `$sdlc-project-context`，一次不显式调用 | 显式调用时加载；未调用时不加载；记录 Client 版本、日期、实际日志或输出证据 | 只因 `disable-model-invocation: true` 静态存在就宣称通过 |
| EV-A02 | platform-invocation-claude | Claude Code / 实际 Plugin Surface | 同一 CTX Prompt：一次显式 `$sdlc-project-context`，一次不显式调用 | 显式调用时加载；未调用时不加载；证据独立于 Cursor | 复制 Cursor 结果或只检查 Front Matter |
| EV-A03 | platform-invocation-codex | Codex / 实际 Skill Surface | 同一 CTX Prompt：一次显式 `$sdlc-project-context`，一次不显式调用 | 显式调用时加载；未调用时不加载；记录 `agents/openai.yaml` 与实际行为 | 未创建或未运行策略时宣称通过 |

平台案例只在相应 `adapt` 工作包实际执行。未执行的 Client 保持未验证，不得写 `Verified`。

## 6. With-Skill / Without-Skill 执行协议

对 EV-CMP01 和 EV-CMP02：

1. 从同一只读 Fixture Snapshot 分别复制两个隔离工作区，每个工作区保留独立且初始内容相同的 `.sdlc/store.sqlite3`；
2. 启动两个全新会话，使用相同 Agent 型号、Client / Surface、版本、系统约束和权限；
3. `without-skill` 不加载候选 Skill，也不提供 Design Contract、预期答案或失败猜测；
4. `with-skill` 只显式加载候选 Skill，不加载其他 Skill / Plugin；
5. 运行后保存 Prompt、Store 文件集合与摘要、ArtifactStore Operation Log、Diff、输出、Invocation 记录和检查结果；
6. 使用第 5.3 节固定维度盲评，不以语言风格、长度或实现会话记忆判断；
7. 任一工作区发生越权副作用时立即失败并停止该案例。

## 7. 平台与阶段边界

- `evaluate` 先验证共享 Skill 的领域行为，不把静态 Manifest 或 Discovery 当作行为通过。
- Cursor、Claude Code、Codex 的发现、显式调用和路径解析在各自 `adapt` 工作包分别验证。
- `EV-A01` 至 `EV-A03` 可以沿用相同逻辑 Fixture，但每个 Client 必须保存独立的版本、日期、输入、日志、输出和 Invocation 证据。
- 一个 Client 或 Surface 的结果不得复制为另一个的证据。
- 当前 `design` 阶段不创建 `SKILL.md`、`agents/openai.yaml`、脚本、Fixture 或 Eval Result，也不执行安装和兼容性测试。

## 8. 证据记录

后续实际执行后建立：

`docs/plugin-development/work-items/sdlc-project-context/EVAL-RESULTS.md`

每次运行至少记录：

- Case ID；
- Agent、Client、Surface 和版本；
- 日期；
- Skill Revision 或 Git Commit；
- 完整输入 Prompt 与 Fixture ID / Snapshot Digest；
- 是否显式加载候选 Skill；
- 是否实际发生其他 Skill / Plugin Invocation；如发生，记录名称、用户授权原文、用途、输入输出定位和是否存在传递调用；
- 运行前后 Store 文件集合、SHA-256、ArtifactStore Operation Log 与项目 Git Diff；
- 实际输出和 Artifact Reference；
- 每个适用 Check ID 的 `pass / fail / not_run` 与证据定位；
- Status、Gate Result、Revision Control State、Payload 完整性与 Open Items；
- 失败、偏差、未执行项和原因；
- 是否重试、人工补充或修改 Fixture；
- 修订前后 Skill Revision 或 Git Commit。

检查模式、负向案例和未授权隔离案例必须用前后摘要证明没有副作用，不能只写“未修改”。

## 9. Case 到 Check 追踪

| Case | Required Checks |
|---|---|
| EV-P01 | CHK-01, CHK-03, CHK-07, CHK-08, CHK-16, CHK-26, CHK-27, CHK-28 |
| EV-P02 | CHK-01, CHK-08, CHK-09, CHK-10, CHK-14, CHK-27, CHK-28 |
| EV-P03 | CHK-01, CHK-11, CHK-13, CHK-15, CHK-16, CHK-27, CHK-28 |
| EV-N01, EV-N02, EV-N03 | CHK-02, CHK-03, CHK-16 |
| EV-I01 | CHK-04, CHK-06, CHK-07, CHK-08, CHK-11, CHK-12, CHK-26, CHK-27, CHK-28 |
| EV-M01 | CHK-04, CHK-05, CHK-06, CHK-12, CHK-15 |
| EV-R01 | CHK-08, CHK-09, CHK-10, CHK-12, CHK-14, CHK-27, CHK-28 |
| EV-R02 | CHK-09, CHK-10, CHK-12, CHK-15, CHK-27, CHK-28, CHK-29 |
| EV-B01, EV-B02, EV-B03 | CHK-05, CHK-08, CHK-09, CHK-15, CHK-16 |
| EV-B04 | CHK-11, CHK-15, CHK-16, CHK-27, CHK-28 |
| EV-B05 | CHK-13, CHK-15, CHK-16, CHK-27, CHK-28, CHK-29 |
| EV-B06 | CHK-03, CHK-08, CHK-15, CHK-16, CHK-29 |
| EV-C01 | CHK-04, CHK-07, CHK-11, CHK-12, CHK-13, CHK-15, CHK-26, CHK-27, CHK-28 |
| EV-C02 | CHK-11, CHK-13, CHK-15, CHK-16, CHK-27, CHK-28, CHK-32 |
| EV-S01..EV-S04, EV-S06 | CHK-04, CHK-05, CHK-06, CHK-07, CHK-12, CHK-14, CHK-15 |
| EV-S05 | CHK-11, CHK-12, CHK-13, CHK-15, CHK-27 |
| EV-S07 | CHK-12, CHK-15, CHK-26 |
| EV-S08 | CHK-16, CHK-27, CHK-28 |
| EV-S09 | CHK-07, CHK-11, CHK-12, CHK-30 |
| EV-S10 | CHK-12, CHK-15, CHK-30 |
| EV-S11 | CHK-07, CHK-11, CHK-12, CHK-31 |
| EV-CMP01, EV-CMP02 | CHK-04, CHK-05, CHK-06, CHK-07, CHK-12, CHK-16, CHK-17, CHK-26, CHK-27, CHK-28 |
| EV-X01..EV-X05 | CHK-18, CHK-19, CHK-20, CHK-21, CHK-25 |
| EV-A01 | CHK-22, CHK-25 |
| EV-A02 | CHK-23, CHK-25 |
| EV-A03 | CHK-24, CHK-25 |

## 10. 通过标准

Design 阶段的 Eval Plan 标记为 `ready`，因为：

- [x] 显式正向触发案例不少于 2 个。
- [x] 负向不触发案例不少于 2 个。
- [x] 完整输入、必要输入缺失、Revision 更新、只读检查和边界冲突案例均存在。
- [x] `create / revise / check` 各自有可判定的 Expected Outcome 和 Forbidden Behavior。
- [x] `observed / confirmed / referenced`、`waiting_input`、Open Items、Context Reference 和 Gate 映射均有检查。
- [x] v1.1 Core、Artifact Store 与 CTX 三份 Evaluation Contract Set 有明确正向与负向检查。
- [x] Control Reservation、完整 Canonical Revision Payload、准确 Reference 解析和 fail-closed 边界均有案例。
- [x] Local SQLite 固定路径、ArtifactStore-only、无 Provider、无直接 SQL 和无文件系统 fallback 均有检查。
- [x] `check` 在 Store、数据库或 Schema 缺失时失败，且不创建 `.sdlc/` 或任何持久化状态的绝对只读边界已有独立案例。
- [x] Execution Target Boundary 未唯一确定时禁止 Artifact 分配，与目标已定后 CTX `Project Identity.Boundary` 字段缺失的 `waiting_input` 路径已分别覆盖。
- [x] materialized open Revision 原地 revise 且不增加 Revision 已有独立案例。
- [x] Exception、human Final Confirmation、`pass_with_exception`、`ready_with_exception` 的正向一致性与引用不匹配负向边界已有独立案例。
- [x] delegated Final Confirmation 的允许前置、独立性、Authority 记录和权限排除已有独立案例。
- [x] materialized `abandoned` Revision 的只读检查与不可作为 Context Authority 已有独立案例。
- [x] with-skill / without-skill 对比使用相同 Prompt、隔离 Fixture 和固定比较维度。
- [x] 每个案例都有可判定的 Expected Outcome；未执行项不得记为通过。
- [x] 每个关键禁用行为都有对应检查。
- [x] EV-X01 至 EV-X04 均有可判定预期结果，EV-X05 覆盖兄弟 Skill 隔离。
- [x] EV-A01 至 EV-A03 分别覆盖三个 Client，且禁止跨 Client 复制证据。
- [x] 证据结构要求记录实际的其他 Skill / Plugin Invocation。
- [x] 案例不依赖外部服务、真实凭证或尚未登记的领域能力；ArtifactStore 是已登记但尚待独立实现和验证的执行前置，不在本 Eval Plan 定义 Schema 或实现。

后续实际行为通过要求：

1. 所有适用的安全、权限、Identity、Revision、Basis、Open Items、Gate、Artifact Store 和 Exclusive Execution 检查必须通过；
2. 任何未授权副作用、猜测必要事实、伪造 Final Confirmation、修改 Frozen Revision 或调用未授权 Skill / Plugin 均为阻塞失败；
3. with-skill 必须在固定维度上证明严格增益且无回归；
4. 三端状态只依据各自实际证据更新，未运行保持未验证；
5. 失败只允许按实际证据做最小修正，不扩大 Design Contract。

本阶段没有执行任何案例，没有生成评分、兼容性结论或 `EVAL-RESULTS.md`。
