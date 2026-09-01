# Plugin Development Handoff

## 当前目标

第一个正式 Phase Skill `sdlc-000-ctx` 已完成；固定 Eval、自包含 Runtime、共享
ArtifactStore、Runtime Kernel、Source Lock、Exclusive Execution 和安装后 Codex CLI TUI
行为均已完成验证并获 Maintainer 最终接受。

## 当前阶段

- 当前活动 Skill：`None`。
- 已完成 Skill：`sdlc-000-ctx`。
- 阶段：`complete`。
- `DESIGN.md`：`approved`；本轮未修改。
- `EVAL-PLAN.md`：`ready`；本轮未修改 Oracle。
- Maintainer Design Decision：`approved`（2026-08-30）。
- Maintainer Final Decision：`accept-final`（2026-08-31）。依据：Design=`approved`；
  Critical Eval 全部通过；Codex CLI TUI 的 Discovery、显式 Invocation、未调用对照和安装缓存
  Runtime Behavior 均有直接证据；Review Verdict=`PASS`，`REV-001`～`REV-006` 与
  `EVAL-001` 全部关闭且无阻塞 Finding；live Runtime Contract Validator、`75/75` 单元测试和
  `git diff --check` 均通过。
- 当前分支：`skill/sdlc-000-ctx`；合并前 HEAD：
  `4905c0ebf7fa7ab5a9dc6fc73d1aea12061d1b1a`；本次合入 `origin/main`：
  `3ff5a992b27ae468c850b97f9b8393b70ace7c98`。
- 当前请求已授权本地 merge commit，未授权 push；主线既有提交的 Author / Committer 保持
  不变，merge commit 使用当前仓库 Git 身份。

## Foundation 与 Runtime 基线

- Shared Runtime Core Foundation Commit：
  `dcb2769a5f32f55445e16cea7e0b17a1a472bece`；历史 CI 55 个测试通过。
- 当前 Runtime 使用共享 `execute_phase`、ArtifactStore 与
  `ContextLineageRegistry`，并合入 `main` 的 Frozen Artifact Authority、Canonical Parser 与
  Control Input Resolver；不直接 SQL、不复制 Schema。
- Runtime SHA-256：
  `c4edaae3de4cede691f59ac69741bc0f6d4f7ee948a1f42a207fe74d0cf054ac`。
- Source Lock SHA-256：
  `137ae1571a8e94236066935374f67dc0be3bc98e55d0c699f3cd9f84cafa143f`；已按合入后的
  Runtime Contract 确定性重建。
- Runtime Contract Validator：通过，5 个共享 Contract、1 个正式 Skill。
- CTX Producer 测试：`20/20 PASS`；合并后全量单元测试：`92/92 PASS`。

## EVAL-001 Implement-fix

- 旧 Runtime 已在 Producer 测试中稳定复现：第 73 次并发首次 create 返回
  `CTX Lineage reservation failed: disk I/O error`；插桩另捕获到首次初始化清理与并发
  `.sdlc` 创建竞态，以及两个 Lineage reserve 已收敛后 Revision 分配前的
  `Cannot validate SQLite Schema: database is locked`。
- 根因位于共享 ArtifactStore 初始化和连接锁等待边界，不是 CTX Oracle、Lineage 唯一约束
  或 Revision 算法：首次 `initialize()` 没有进程内互斥，且连接在 Schema 校验前使用
  `busy_timeout=0`。
- 修复只串行首次 `initialize()`，并在所有 SQLite 连接及 Lineage reserve 的 Schema 校验前
  使用固定 5 秒 busy timeout；没有新增无限重试、直接 SQL、私有 Store、Schema 复制、
  fallback 或错误吞并。
- Producer 回归连续执行 200 个隔离 Boundary Fixture：每次两个并发请求都返回同一 CTX
  ID，结果集合为 `action_required + blocked/CTX_LINEAGE_EXISTS`，且公共 API 读回一个
  Artifact 和唯一 Binding。
- 另以真实 Runtime CLI 执行 10 个隔离双进程并发 Fixture，结果和 Store 唯一性相同。
- 空 Schema 与非 SQLite Store 损坏回归继续 fail closed；后者原始损坏字节保持不变。

## Implement-fix 后 Formal 验证

- Formal Runner 已修订为 approved 同级 `inputs.context / inputs.evidence /
  inputs.supporting_members` 输入形状；Runner SHA-256：
  `c8076eb03658ff7dd9d24d92726ce4c9ae4411fcf090dacd8eab930e6c9488d7`。
- `REV-001`：`EV-REV001 PASS`；无 primary Resource 返回
  `CTX_CONTENT_INVALID`，零 Store 创建。
- `REV-002`：`EV-REV002-MAX PASS`；旧 frozen Revision 1 作为 Base 时创建 Lineage
  最大 Revision 3；`EV-REV002-CLEANUP PASS`，分配后失败留下的是
  `abandoned/materialized=false`，不存在 open Control Reservation。
- `REV-003`：合规 delegated Authority 正例通过；缺 `decided_at`、固定集合不精确、
  Delegation Basis 越界三个反例均保持 open / 非 Authority。
- `REV-006`：同级 Evidence / Supporting Member 被消费并持久化；嵌套漂移形状被拒绝。
- 既有 create/revise/check、Source Lock、Runtime Independence、Foundation 缺失和只读 Case
  均通过。

## REV-004 Formal 证据

- Runner 在隔离目录实际执行一次仅获授权的
  `fixture:external-context-producer`；真实输出 SHA-256 为
  `bea4795214f9dac3654462750d38bcc3e4fceb33176ad57a95c8035f8171dde7`。
- 输出请求 `fixture:external-normalizer`，但该依赖未获授权；call log 只有生产者，
  `dependency_invoked=false`，canary 不存在。
- 外部输出仅作为同级 Evidence / Supporting Member；冲突候选
  `resource_type=workspace` 返回 `CTX_CONTENT_INVALID`，没有覆盖 Contract、没有创建 Store。
- `EV-D03 / EV-X02 PASS`；该结果只证明 Portable Formal Fixture 与 Runtime 边界，不冒充
  Cursor、Claude Code 或 Codex Client 行为。

## With-skill / Without-skill

- 四个 fresh without-skill 普通 Agent 已使用修订后的同级 Invocation 独立重跑；输出
  `4/4` 均未通过共享 Result Schema。
- 对应 with-skill `EV-C01 / EV-C02 / EV-R01 / EV-K05` 全部通过固定 Oracle，比较
  `4/4 PASS`，`CHK-21 PASS`。
- C02 without-skill 对照直接操作隔离 SQLite，并把缺 primary Resource 的 CTX 错误冻结；
  该副作用只位于 `/private/tmp` Fixture，证明 with-skill 的 Domain / Authority 边界更严格。

## EVAL-001 Fresh Formal 复核

- 未修改 `EVAL-PLAN.md`、Runner、Fixture 或 Critical Oracle；完整 Formal Runner 的
  `EV-C04 PASS`，汇总为 `PASS=44 / FAIL=0 / NOT_RUN=4 / DEFERRED=3`。四个 `NOT_RUN`
  已有历史 fresh Agent 对照证据，三项 Client Case 继续按实际状态 `DEFERRED`。
- 两个同 Boundary 的并发首次 create 返回同一 `CTX-20260830101112-01`，结果集合为
  `action_required + blocked/CTX_LINEAGE_EXISTS`，公共 API 读回一个 Artifact。
- 有限重复覆盖 200 个隔离线程 Fixture 与 10 个隔离双进程 CLI Fixture；每次结果集合均为
  `action_required + blocked/CTX_LINEAGE_EXISTS`，返回同一非空 CTX ID，并由
  `ArtifactCatalog` 与 `ContextLineageRegistry.find` 读回唯一 Artifact / Binding。
- 空 Schema 与非 SQLite Store 分别返回 `SCHEMA_ERROR`、`DATABASE_ERROR`；ArtifactStore
  前后快照相同，非 SQLite 原始损坏字节不变。
- Runtime Contract Validator、编译检查与全量 `75/75` 单元测试通过；没有使用无限重试、
  吞错、直接 SQL、私有 Store、Schema 复制或 fallback。
- 历史一次间歇 `EV-C04 DATABASE_ERROR` 继续保留为回归来源；当前修复后的 fresh 证据满足
  同一冻结 Oracle，`EVAL-001` 关闭为 `passed`。

## REV-005 Codex Adapt Fix

- 独立 Plugin 部署根及安装缓存顶层只包含 `.codex-plugin/`、`skills/`、`packages/`、
  `scripts/`，不存在 `docs/`、`tests/` 或 Handoff。
- fresh Codex TUI 发现 `SDLC Project Context [Skill]`，选择后插入
  `$sdlc-ai-spec:sdlc-000-ctx`；fresh 未调用对照只返回 `NO_SKILL_CONTROL`，无 Tool Call。
- 接受的 Behavior Thread 为 `01a0559a-7f1e-7a41-b4bb-3ad0fab7db8b`；Codex 注入的
  selected Skill path 指向安装缓存。6 个 Tool Call 全部在安装缓存，开发仓库、`docs/**`、
  `tests/**`、Handoff 的工具参数命中为 `0`。
- Codex 仅根据 bundled contract 和共享 Envelope 构造严格只读 `check` Invocation，安装缓存
  Runtime 返回完整 `STORE_NOT_FOUND` / `RESOLVE_STORE_FAILURE` Result；隔离项目执行前后均无
  `.sdlc`，Git 状态为空。
- 原生内层 `workspace-write` 因当前 macOS 外层沙箱不能嵌套 Seatbelt 而 fail closed；无内层
  沙箱复测仍受本工作会话外层边界约束。该宿主限制和后台 curated plugin sync 均已在
  `ADAPT-CODEX-RESULTS.md` 准确披露，未参与 Runtime Behavior 结论。
- `REV-005` 关闭为 `passed`；历史读取过开发测试文件的 Codex 证据不再作为通过依据。

## 最终 Review 状态

- fresh Review 未沿用历史 `FAIL` 或后续工作包自报结论，已从当前 Runtime、测试、Formal
  输出和 Codex 原始 rollout 独立复核 `REV-001`～`REV-006` 与 `EVAL-001`。
- `REV-001`～`REV-006` 与 `EVAL-001` 均为 `PASS`；Review Verdict 为 `PASS`，无阻塞
  Finding。
- 全量单元测试 `75/75 PASS`；历史 Finding focused 回归 `5/5 PASS`；EVAL-001 focused
  有限重复两组并行重跑均为 `4/4 PASS`；Formal Runner 为
  `PASS=44 / FAIL=0 / NOT_RUN=4 / DEFERRED=3`。
- Codex Behavior 原始事件流确认 6 个 Tool Call 均位于安装缓存，对开发仓库、`docs/**`、
  `tests/**`、Handoff 命中为零；宿主后台 curated plugin sync 与 Runtime Behavior 已分开
  判断。
- 该 Review 工作包只更新 `REVIEW-RESULTS.md` 和 `HANDOFF.md`，未在 Review 会话中进入
  `finalize`；后续 Maintainer 已通过 `accept-final` 完成收口。

## 未执行

- Cursor、Claude Code 适配；Codex Desktop / App 验证；
- push、tag 或 release。

## 完成状态

- `sdlc-000-ctx`：`complete`。
- 下一工作包：`None`。
- Maintainer 最终接受本身未授权 Git 操作；当前请求另行授权把 `origin/main` 合入当前分支并
  创建本地 merge commit，不包含 push、tag、release 或其他后续阶段授权。
