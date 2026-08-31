# Skill Review Results — sdlc-000-ctx

## 1. Review Metadata

| Field | Value |
|---|---|
| Review Stage | `review` |
| Review Date | `2026-08-31` |
| Branch | `skill/sdlc-000-ctx` |
| Baseline / HEAD | `78028dc67707593420380b61f43f4a1bf7fc9fcd` |
| Design Input | `DESIGN.md` — `approved` |
| Eval Plan Input | `EVAL-PLAN.md` — `ready` |
| Formal Eval Input | `EVAL-RESULTS.md` — current evidence independently rechecked |
| Codex Adapt Input | `ADAPT-CODEX-RESULTS.md` and raw accepted Behavior rollout |
| Review Verdict | `PASS` |

本轮使用 fresh context，从当前工作树、固定 Source、Runtime、测试、Formal Runner、评测输出
和 Codex 原始 rollout 独立复核；历史 `REVIEW-RESULTS.md` 的 `FAIL` 及后续工作包自报结论
均未作为通过依据。本轮未修改 Runtime、测试、Formal Eval、Codex Adapt 证据、Design 或
Eval Oracle，也未执行 `finalize`。

## 2. Finding Closure

### REV-001 — PASS — 缺少 primary Resource 时 fail closed 且不创建 Store

- `skills/sdlc-000-ctx/scripts/runtime.py:591-599` 对缺失 Resource Section 或 primary
  Reference 返回 `CTX_CONTENT_INVALID`；`create` 在 Store 初始化前完成 preliminary
  Payload 校验（`1846-1853`）。
- focused 回归及当前 Formal `EV-REV001` 均确认：结果为 `CTX_CONTENT_INVALID`，
  `store_created=false`。
- 结论：历史 Authority 绕过已关闭。

### REV-002 — PASS — 旧 frozen Base 按 Lineage 最大 Revision 分配且失败无 open Reservation

- `packages/sdlc_artifact_store/sqlite_store.py:475-500` 从 Lineage 已有 Revision 求最大值并
  分配 `max + 1`；Runtime 使用 Store 返回的 `control.revision` 重建 Payload
  （`skills/sdlc-000-ctx/scripts/runtime.py:1967-1979`）。
- 分配后失败路径调用 `_abandon_unmaterialized_reservation`（`2021-2040`），只留下
  `abandoned / materialized=false`，不留下 open Control Reservation。
- focused 回归及当前 Formal `EV-REV002-MAX / EV-REV002-CLEANUP` 均通过：Revision
  序列为 `1, 2, 3`，失败后 open Reservation 数为零。
- 结论：历史 Revision 分配与原子性问题已关闭。

### REV-003 — PASS — delegated Authority 完整满足固定 Authority Contract

- `_validate_delegated_authority`（`skills/sdlc-000-ctx/scripts/runtime.py:957-1012`）严格校验
  固定 Front Matter、Contract、Artifact、Decision、RFC3339 `decided_at`、固定表头与唯一
  数据行，并按固定 Delegation Basis、Identity 和集合摘要进行字节级绑定。
- delegated Final Confirmation 路径（`1054-1070`）同时禁止 Exception、固定角色并要求
  Authority / Runner 身份独立。
- focused 回归与当前 Formal `EV-D02` 通过；缺 `decided_at`、固定集合不精确和
  Delegation Basis 越界三个反例均保持 open / 非 Authority。
- 结论：历史不完整 Authority Contract 接受问题已关闭。

### REV-004 — PASS — 仅执行获授权 external producer，外部输出不能覆盖 Contract

- Formal Runner 在隔离目录实际执行一次唯一获授权的
  `fixture:external-context-producer`；其请求的 `fixture:external-normalizer` 未获授权且未执行，
  call log 只有 producer，canary 不存在。
- 外部输出只进入同级 Evidence / Supporting Member；冲突候选
  `resource_type=workspace` 被 Runtime 以 `CTX_CONTENT_INVALID` 拒绝，Store 未创建。
- 当前 `EV-D03 / EV-X02` 通过，真实 producer 输出 SHA-256 为
  `bea4795214f9dac3654462750d38bcc3e4fceb33176ad57a95c8035f8171dde7`。
- 结论：授权不可传递与 Contract 优先级均由行为证据关闭。

### REV-005 — PASS — Codex Behavior 只使用安装缓存 bundled contract 与 Runtime

- 独立读取接受的 Behavior Thread `01a0559a-7f1e-7a41-b4bb-3ad0fab7db8b` 原始事件流，
  重建出 6 个已完成 Tool Call；selected Skill、contract、Envelope、Runtime 和所读 package
  均位于安装缓存。
- 6 个 Tool Call 对开发仓库、`docs/**`、`tests/**`、Handoff 的参数命中均为零；严格只读
  `check` Invocation 由 bundled contract 构造，Runtime 返回完整
  `STORE_NOT_FOUND / RESOLVE_STORE_FAILURE` Result，隔离项目未产生 `.sdlc`。
- 原始事件流另含 Codex 宿主启动期 `codex_core_plugins::startup_sync` 的 curated plugin
  同步告警；它不属于 Agent Tool Call 或 Runtime Invocation，适配报告已与 Runtime Behavior
  分开披露。原生内层 `workspace-write` 因当前 macOS 外层沙箱不能嵌套 Seatbelt 而 fail
  closed，接受的复测仍受本会话外层文件系统边界约束。
- 结论：历史读取开发测试文件的证据未被沿用，安装后 Codex CLI TUI Behavior 边界已关闭。

### REV-006 — PASS — approved 同级 peer input 被实际消费

- bundled contract 和 Runtime 采用同级 `inputs.context / inputs.evidence /
  inputs.supporting_members`；Runtime 分别消费 Evidence（`491-518`）与 Supporting Members
  （`613-676`），并拒绝嵌套漂移字段（`478-489`）。
- focused 回归和当前 Formal `EV-REV006-PEER` 均通过：`EVD-001`、`SUP-001` 被持久化，
  嵌套漂移形状返回 `CTX_CONTENT_INVALID` 且不创建 Store。
- 结论：历史 Invocation 形状漂移已关闭。

### EVAL-001 — PASS — 并发首次 create 与损坏 Store 的有限重复证据稳定

- ArtifactStore 首次初始化使用进程内互斥，所有 SQLite 连接及 Lineage reserve 在 Schema
  校验前设置固定 5 秒 `busy_timeout`；Runtime 恢复边界为有限 deadline，无无限重试、吞错、
  fallback、直接 SQL、私有 Store 或 Schema 复制。
- 当前 full unittest 为 `75/75 PASS`，其中一次执行 200 个隔离双线程 Fixture、10 个隔离
  双进程 CLI Fixture及损坏 Store 回归；Review 再并行重复同组 focused Case 两次，合计
  600 个线程 Fixture、30 个双进程 Fixture，全部稳定返回同一 CTX ID、唯一 Artifact / Binding
  与 `action_required + blocked/CTX_LINEAGE_EXISTS` 结果集合。
- 空 Schema 与非 SQLite Store 在三次执行中分别稳定返回 `SCHEMA_ERROR`、`DATABASE_ERROR`，
  Store 快照和原始损坏字节不变。当前 Formal `EV-C04` 同样通过。
- 结论：历史间歇 `DATABASE_ERROR` 被保留为回归来源，当前有限重复证据已关闭该问题。

## 3. Review Checks

- Runtime Contract Validator：通过，识别 5 个共享 Contract、1 个正式 Skill。
- Source Hash：Core、Artifact Store、CTX Source、Runtime、Source Lock、Formal Runner 均与当前
  固定记录一致。
- 历史 Finding focused 回归：`5/5 PASS`。
- 全量单元测试：`75/75 PASS`。
- EVAL-001 focused 有限重复：两组并行 Review 重跑均为 `4/4 PASS`。
- 固定 Formal Runner：`PASS=44 / FAIL=0 / NOT_RUN=4 / DEFERRED=3`；非零退出只来自四个
  由独立 fresh Agent 证据提供的 without-skill `NOT_RUN` 对照，未把三个未支持 Client Case
  的 `DEFERRED` 冒充为通过。
- 编译检查：通过；临时 bytecode 只写入 Review 专属 `/private/tmp` 目录。
- `git diff --check`：写入后执行并通过。
- Diff 白名单：本 Review 只更新 `REVIEW-RESULTS.md` 和 `HANDOFF.md`；进入会话前的其他
  dirty / untracked 阶段产物保持不变。

## 4. Remaining Limits

- Cursor、Claude Code 和 Codex Desktop / App 仍为未验证 Surface；当前 Review 只确认已声明
  范围内的 Codex CLI TUI。
- macOS 外层沙箱下不能嵌套原生 Seatbelt；这是已披露的宿主验证限制，不改变安装缓存
  Runtime 的 fail-closed 结果。
- 上述限制不构成本次 `sdlc-000-ctx` 当前支持范围的阻塞 Finding。

## 5. Verdict

`PASS`。

`REV-001`～`REV-006` 与 `EVAL-001` 均由当前代码、测试、Formal 输出和原始 Codex rollout
直接证据关闭，没有阻塞 Finding。下一唯一工作包可以路由至 `finalize`，但本 Review 未执行
最终接受、发布或任何 Git 外部写入。
