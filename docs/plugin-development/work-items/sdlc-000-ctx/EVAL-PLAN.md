# Skill Eval Plan — `sdlc-000-ctx`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `sdlc-000-ctx` |
| Design Contract | `docs/plugin-development/work-items/sdlc-000-ctx/DESIGN.md` |
| Stage | `design` |
| Status | `ready` |

本文件只定义评测案例、Oracle 和通过条件；不记录未执行结果。

## 2. 评测目标

验证：

1. 仅显式调用时执行；
2. `create / revise / check` 严格按各自边界运行；
3. Project Root 与 Project Boundary 业务事实不会混淆；
4. 同一 Boundary Key 只产生一个 CTX Lineage；
5. Runtime 使用共享 Envelope、Source Lock、Runtime Kernel 和 ArtifactStore；
6. Builder/Validator 生成符合固定 CTX Contract 的完整 Payload；
7. 输入不足使用 Open Items / `waiting_input`，不猜测；
8. Gate、Exception、Final Confirmation、Status 和 Store State 一致；
9. check 绝对只读；
10. 删除 `docs/**` 后 Critical Fixture 仍可执行；
11. with-skill 相比 without-skill 减少结构、状态和副作用错误；
12. 三端 Discovery / Explicit Invocation / Behavior 分别保留证据。

## 3. 核心检查

| Check ID | Requirement | Pass Condition |
|---|---|---|
| CHK-01 | 显式调用 | 未显式调用时不加载；显式调用进入正确操作 |
| CHK-02 | 单一职责 | 不创建其他 Phase Artifact，不调用兄弟 Skill |
| CHK-03 | Invocation Envelope | 输入符合共享 Schema，额外字段或相对 Project Root 被拒绝 |
| CHK-04 | Target Boundary | 目标不唯一时零 Store 打开/写入，返回 `TARGET_AMBIGUOUS` |
| CHK-05 | Boundary Confirmation | 未 confirmed 的 Project Boundary 不生成 Boundary Key、不分配 CTX |
| CHK-06 | Boundary Key | NFC、LF、trim、UTF-8、SHA-256 算法确定性一致 |
| CHK-07 | Unique CTX Lineage | `ContextLineageRegistry.reserve` 重复/并发返回同一 CTX ID |
| CHK-08 | Source Lock | 符合共享 Schema，集合/版本/摘要全等，漂移失败 |
| CHK-09 | Runtime Independence | 删除 `docs/**` 后 Critical Fixture 通过；运行文件无 docs 路径依赖 |
| CHK-10 | CTX Structure | 固定 Front Matter、章节、表格、空表示与顺序正确 |
| CHK-11 | Basis / Evidence | 正式事实只使用合法 Basis 与可解析 Evidence |
| CHK-12 | Identity / Revision | ID 稳定；open 原地修订；frozen 后 max+1；no-change 不增号 |
| CHK-13 | Open Items | 缺失事实唯一登记，Gate pending，无 fail 时 `waiting_input` |
| CHK-14 | ArtifactStore | 只用公共 API；无直接 SQL、私有 Schema 或 fallback |
| CHK-15 | Payload Closure | primary、Member、Manifest、Media Type、摘要和身份闭合 |
| CHK-16 | Gate / Status | Core+CTX Check、Exception、Final Confirmation、Gate、Status 一致 |
| CHK-17 | Check Read-only | 缺 Store/Schema 时不创建任何文件；现有 Store 前后字节不变 |
| CHK-18 | Abandoned / Control | 不作为 Context Authority，不回退其他 Revision |
| CHK-19 | Standard Result | 输出符合共享 Schema，只有一个准确 next_action |
| CHK-20 | Minimal Side Effects | 无网络、安装、Git、外部写入或 Secret 持久化 |
| CHK-21 | With/Without | with-skill 在 Critical Checks 上明显优于 without-skill，且无副作用回归 |
| CHK-22 | Exclusive Execution | 未授权不调用其他 Skill；授权不传递 |
| CHK-23 | Client Evidence | 每个 Client 分别记录 Discovery、Invocation、Behavior，不跨端推断 |

## 4. Fixture

所有 Fixture 使用 `tempfile` 隔离项目、固定 UTC 时间、确定性 Evidence 和共享 Runtime；不包含真实凭证或生产数据。

| Fixture ID | State | Purpose |
|---|---|---|
| FX-EMPTY | 已初始化 Store，无 CTX Binding，Context 完整 | create ready |
| FX-MISSING | 目标和 Boundary 已确认，但 Purpose/Resource 等必要事实缺失 | waiting_input |
| FX-UNCONFIRMED-BOUNDARY | Project Root 唯一，但 Boundary 未 confirmed | 禁止分配 |
| FX-AMBIGUOUS-TARGET | 两个可能 Project Root/Store | target fail closed |
| FX-BOUNDARY-EXISTING | 已有 Boundary Key → CTX ID Binding | duplicate create |
| FX-BOUNDARY-RACE | 两个并发 create 使用同一 Boundary Key | atomic uniqueness |
| FX-OPEN | materialized open / waiting_input | open revise |
| FX-FROZEN | frozen ready Revision，存在一项有效变化 | frozen revise |
| FX-NO-CHANGE | frozen Revision，输入无有效变化 | no-op |
| FX-CONTROL | 只有 open Control Record | non-authority |
| FX-ABANDONED | materialized abandoned Revision | historical check |
| FX-INVALID | Payload / Manifest / Digest / Gate 至少一项错误 | check failure |
| FX-EXCEPTION | active Exception + human Final Confirmation | ready_with_exception |
| FX-DELEGATED | 无 Exception/waived，独立 Reviewer 合法委托 | delegated confirmation |
| FX-STORE-MISSING | `.sdlc` 或数据库/Schema 不存在 | strict read-only |
| FX-SOURCE-DRIFT | Runtime Contract 或 Build Source 摘要改变 | source-lock fail |
| FX-NO-DOCS | 临时 Plugin 删除全部 docs | independence |
| FX-EXTERNAL-CONFLICT | 获授权外部输出与 CTX Contract 冲突 | external output boundary |

每个 Store Fixture 保存运行前后文件集合、大小和 SHA-256；只读案例还记录 journal/WAL/SHM/绑定表是否出现。

## 5. 测试案例

### 5.1 Trigger 与基础输入

| Case | Fixture | Invocation | Expected | Forbidden |
|---|---|---|---|---|
| EV-T01 | FX-EMPTY | 未显式调用的一般项目总结 | Skill 不加载 | 创建 Store/CTX |
| EV-T02 | FX-EMPTY | 显式 create | 进入 create | 调用其他 Phase Skill |
| EV-T03 | FX-FROZEN | 显式 revise + 准确 Reference | 进入 revise | 选择 latest/current |
| EV-T04 | FX-FROZEN | 显式 check + 准确 Reference | 进入 check | 隐式修复 |
| EV-I01 | FX-AMBIGUOUS-TARGET | create | `action_required/TARGET_AMBIGUOUS`；零 Store 访问 | 选择任一目录 |
| EV-I02 | FX-FROZEN | revise 无 Reference | `ARTIFACT_REFERENCE_REQUIRED` | 扫描最近 CTX |
| EV-I03 | FX-FROZEN | `latest` Reference | `ARTIFACT_REFERENCE_INVALID` | 自动解析当前最大 Revision |
| EV-I04 | FX-UNCONFIRMED-BOUNDARY | create | `PROJECT_BOUNDARY_CONFIRMATION_REQUIRED`；无 Binding/Artifact | 从路径推断 Boundary |

### 5.2 Create

| Case | Fixture | Expected | Critical Oracle |
|---|---|---|---|
| EV-C01 | FX-EMPTY | 一个 CTX ID、Revision 1、完整 Payload；合法时 frozen/ready | Binding、ID、Revision、readback、Gate 一致 |
| EV-C02 | FX-MISSING | materialized open / waiting_input + 唯一 Open Items | 不猜测，不返回 Authority Reference |
| EV-C03 | FX-BOUNDARY-EXISTING | blocked / `CTX_LINEAGE_EXISTS`，返回已有 ID | artifacts/bindings/revisions 数量不增加 |
| EV-C04 | FX-BOUNDARY-RACE | 两个并发请求获得同一 CTX ID | 只有一个 CTX Artifact 与 Binding |
| EV-C05 | FX-EMPTY + dry_run | 非权威候选 Result | `.sdlc` 和数据库不变化 |

### 5.3 Revise

| Case | Fixture | Expected | Critical Oracle |
|---|---|---|---|
| EV-R01 | FX-OPEN | 同一 Revision 原地更新，generation +1 | Revision 数量不变；旧 Gate/FC 失效后重算 |
| EV-R02 | FX-FROZEN | 新最大 Revision，Base 指向 frozen | 原 frozen 字节不变 |
| EV-R03 | FX-NO-CHANGE | completed no-change | 不分配新 Revision |
| EV-R04 | FX-CONTROL | failed / `CONTROL_RESERVATION` | 不将 Control 当 Payload |
| EV-R05 | FX-ABANDONED | failed / `INVALID_STATE` | 不复活 abandoned |

### 5.4 Check

| Case | Fixture | Expected | Critical Oracle |
|---|---|---|---|
| EV-K01 | FX-FROZEN | 只读 pass，报告有效 Context Reference | Store 前后完全一致 |
| EV-K02 | FX-OPEN | 报告非权威 open 状态 | 不 freeze、不写 Gate |
| EV-K03 | FX-ABANDONED | 历史检查可读，但不可 resolve 为 Authority | 不回退其他 Revision |
| EV-K04 | FX-CONTROL | failed / `CONTROL_RESERVATION` | 不读取部分 Payload |
| EV-K05 | FX-STORE-MISSING | failed / `STORE_NOT_FOUND` | 不创建 `.sdlc`、DB、Schema 或旁车 |
| EV-K06 | FX-INVALID | failed，准确 failed checks | 未执行项不记 pass |

### 5.5 Domain Control

| Case | Fixture | Expected | Forbidden |
|---|---|---|---|
| EV-D01 | FX-EXCEPTION | `pass_with_exception / ready_with_exception`；accepted references 全等 | 丢失、额外或过期 Exception |
| EV-D02 | FX-DELEGATED | delegated FC 仅在 Core 条件全部成立时通过 | Reviewer 与创建/修改者相同 |
| EV-D03 | FX-EXTERNAL-CONFLICT | 外部内容只作 Evidence，冲突导致 fail/阻塞 | 外部输出覆盖 Contract |
| EV-D04 | 任意完整 Fixture | 三个固定 Spec Reference 与 bundled contract 一致 | 运行时读取 docs 重算 |

### 5.6 Runtime / Source Lock

| Case | Fixture | Expected |
|---|---|---|
| EV-S01 | 正常构建 | source-lock 包含 registry 全部 Contract + 3 个 Build Source，排序和摘要正确 |
| EV-S02 | FX-SOURCE-DRIFT | build/review fail，不生成或接受 stale Runtime |
| EV-S03 | FX-NO-DOCS | create/revise/check Critical Fixture 仍通过 |
| EV-S04 | 不同 CWD | Runtime 仅依赖 Plugin Root 与显式 project_root |
| EV-S05 | ArtifactStore/Runtime Package 缺失 | 明确 Foundation error，不直接 SQL 或复制实现 |
| EV-S06 | Runtime 扫描 | `skills/sdlc-000-ctx`、`packages`、`scripts` 无 docs 路径依赖 |

### 5.7 With-skill / Without-skill

对 EV-C01、EV-C02、EV-R01、EV-K05 使用同一 Prompt 和 Fixture执行：

- without-skill：普通 Agent，无当前 Skill Runtime；
- with-skill：显式调用固定 Skill Revision。

关键比较：结构完整性、Basis、Identity、Revision、只读副作用、Gate/Status、错误码和下一动作。Critical Check 任一回归即失败，不以平均分掩盖。

### 5.8 Exclusive Execution 与 Client

| Case | Expected |
|---|---|
| EV-X01 未授权兄弟 Skill | 不调用；当前 Contract 可独立完成则继续，否则请求准确授权 |
| EV-X02 授权一个外部 Skill | 不传递到其依赖；输出只作 Input/Evidence |
| EV-P01 Cursor | Discovery、显式调用、未调用对照、路径与行为分别记录 |
| EV-P02 Claude Code | 同上，证据仅适用于 Claude Code |
| EV-P03 Codex | 同上，验证 `allow_implicit_invocation: false` |

## 6. Eval Oracle Protection

- Fixture、Expected Outcome 和 Critical Check 在执行前冻结；
- 实现者不得为迁就输出修改 Oracle；
- Validator/Schema 变化需独立复核；
- with/without 使用相同输入和 fresh context；
- 重试、人工补充和其他 Skill Invocation 必须记录；
- 失败结果不得删除；真实逃逸问题加入永久回归集。

## 7. Execution Record

正式 Eval 至少记录：

- Plugin / Skill Commit；
- Client、Surface、Version、模型（可取得时）；
- Prompt、Fixture、Source Lock；
- 允许 Tool、权限和外部 Skill 授权；
- 实际输出、Store Operation Log、Validator 结果；
- 开始/结束时间、重试和人工干预。

## 8. 通过条件

必须同时满足：

1. 全部 Critical Case 通过；
2. 无未授权写入、隐式 Skill 调用或 docs Runtime 依赖；
3. create/revise/check 的身份、Revision、只读和 Gate 语义正确；
4. source-lock 与 Foundation Contract 全等；
5. Runtime Independence 通过；
6. with-skill 在关键检查上优于 without-skill；
7. 三端状态按实际证据记录，不虚报 Verified。

## 9. 回归触发

以下变化必须重跑相关 Eval：

- `SKILL.md`、私有 contract/template/runtime；
- `skills/_shared/**`；
- `packages/sdlc_runtime/**` 或 `packages/sdlc_artifact_store/**`；
- Source Lock、Schema、Validator、平台元数据；
- Client/模型重大版本；
- 真实使用故障。

## 10. 当前状态

- Eval Plan：`ready`；
- 实际 Fixture：未创建；
- 行为 Eval：未执行；
- Client 证据：未执行；
- 本阶段不得填写 `pass` 或创建 `EVAL-RESULTS.md`。
