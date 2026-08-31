# Skill Eval Results — `sdlc-000-ctx`

## 1. 结论

| Field | Value |
|---|---|
| Eval Status | `passed`（Portable Formal；Client 状态仍按实际证据记录） |
| Eval Plan | `docs/plugin-development/work-items/sdlc-000-ctx/EVAL-PLAN.md` (`ready`，Oracle 未修改) |
| Design | `docs/plugin-development/work-items/sdlc-000-ctx/DESIGN.md` (`approved`) |
| Git Branch | `skill/sdlc-000-ctx` |
| Baseline HEAD | `78028dc67707593420380b61f43f4a1bf7fc9fcd` |
| Skill Commit | `None`；被测 Runtime 位于当前未提交工作树 |
| Runtime SHA-256 | `c4edaae3de4cede691f59ac69741bc0f6d4f7ee948a1f42a207fe74d0cf054ac` |
| ArtifactStore Runtime SHA-256 | `sqlite_store.py=ba9e654dfde018820500357a3945c720291450da0f7e4d5d498cdc61d40dcb4f`；`context_lineage.py=e70c7e0811f2dde3c9f9d1c5eb196b83880b3ef9164668b8412b929adc0c6aff` |
| Producer Test SHA-256 | `c25c784ddef47fb8572a1ed0af2102c337dcc857c6367cd155b333a45af90fe8` |
| Source Lock SHA-256 | `41556818abc125e73b2717520af8e4b8aef17ab885607f73813f7b298b63ea64` |
| Eval Runner | `tests/evals/run_sdlc_000_ctx_eval.py` |
| Eval Runner SHA-256 | `c8076eb03658ff7dd9d24d92726ce4c9ae4411fcf090dacd8eab930e6c9488d7` |
| Fixed UTC Time | `2026-08-30T10:11:12+00:00` |
| Fresh Re-evaluation | `2026-08-31`；独立 `evaluate-fix` 已完成 |
| EVAL-001 Implement-fix | `passed`；fresh Formal recheck 已关闭 Critical 回归 |

修订后的 Runner 共登记 51 项。正常运行汇总为 `PASS=44 / FAIL=0 / NOT_RUN=4 /
DEFERRED=3`；四个 `NOT_RUN` 已由四个相互独立的 fresh without-skill 普通 Agent
对照补齐，比较 Oracle `4/4 PASS`。`REV-001 / REV-002 / REV-003 / REV-006` 的新增
Formal 回归全部通过，`REV-004` 已获得真实外部输出冲突、单一授权、依赖未获传递授权、
call log 与 canary 零写入证据。

历史 Runner 重复执行中发生过一次 `EV-C04 DATABASE_ERROR`；该失败继续保留在本文作为
真实回归来源。Producer 修复后，本次 fresh `evaluate-fix` 使用未修改的 Runner、Fixture
和 Critical Oracle 独立重跑：`EV-C04 PASS`，两个并发首次 create 返回同一 CTX ID，结果
集合为 `action_required + blocked/CTX_LINEAGE_EXISTS`，公共 API 只读回一个 Artifact。

同一 fresh 会话又执行现有有限重复回归，并以临时独立辅助校验逐次收紧错误码断言：
200 个隔离线程 Boundary Fixture 和 10 个隔离双进程 CLI Fixture 全部通过；每次结果集合
均为 `action_required + blocked/CTX_LINEAGE_EXISTS`，且由 `ArtifactCatalog` 与
`ContextLineageRegistry.find` 读回唯一 Artifact 和 Binding。空 Schema 与非 SQLite Store
继续 fail closed，ArtifactStore 快照验证损坏文件集合与字节不变。`EVAL-001` 因此关闭为
`passed`。`REV-005` 本轮未执行，下一唯一工作包为独立 `adapt-codex-fix`。

## 2. 环境与执行边界

| Field | Value |
|---|---|
| Runtime Client / Surface | Portable Runtime CLI；未执行 Cursor、Claude Code 或 Codex Client Adapt |
| Runtime Environment | Python `3.9.6`；macOS `26.5.1`；`arm64` |
| Baseline Agent | Codex CLI `0.151.0-alpha.7.1`；`gpt-5.6-sol`；reasoning `none` |
| Fixture | `tempfile` 与 `/private/tmp/sdlc-000-ctx-eval-004.D92ksx/**` 隔离 Project Root、Store、外部输出、Prompt 与 Agent Output |
| Allowed Tools | 本地 Python、共享 Runtime / ArtifactStore 公共 API、Git 只读检查；baseline 仅访问各自隔离 Project Root |
| Runtime Network | 未使用 |
| Baseline Network | 仅模型服务本身；Agent Prompt 禁止联网 |
| External Capability Authorization | 仅 `fixture:external-context-producer`；`fixture:external-normalizer` 未获授权 |
| Other Skill / Plugin Invocation | `None`；外部能力为 Runner 私有本地 Fixture，不是已安装 Skill / Plugin |
| Git-visible Side Effects | 本次 evaluate-fix 只更新本文和 Handoff；保留既有 Runtime、测试和历史阶段产物，当前仓库未创建 `.sdlc`，未 commit/push |

四个 without-skill 会话分别为：

| Case | Ephemeral Session ID |
|---|---|
| `EV-W01-C01` | `01a05572-4808-7cc2-b4d0-f5b3fed8f342` |
| `EV-W02-C02` | `01a05573-0fa2-7592-9072-3d9571cd68d3` |
| `EV-W03-R01` | `01a05573-fae4-7341-8281-31ebeeb75777` |
| `EV-W04-K05` | `01a05574-b5cc-7311-968c-76c773a64012` |

## 3. 执行命令与基础验证

```text
env PYTHONPYCACHEPREFIX=/private/tmp/sdlc-000-ctx-evaluate-fix-pycache python3 -m compileall -q packages scripts skills/sdlc-000-ctx/scripts tests/skills tests/evals
python3 tools/validate_runtime_contracts.py
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.skills.test_sdlc_000_ctx -v
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
shasum -a 256 docs/v1.1/core-spec.md docs/v1.1/artifact-store-spec.md docs/v1.1/000-ctx-spec.md
env PYTHONDONTWRITEBYTECODE=1 python3 tests/evals/run_sdlc_000_ctx_eval.py
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.skills.test_sdlc_000_ctx.CtxRuntimeTests.test_concurrent_first_create_converges_on_one_ctx_id tests.skills.test_sdlc_000_ctx.CtxRuntimeTests.test_concurrent_cli_first_create_converges_across_processes tests.skills.test_sdlc_000_ctx.CtxRuntimeTests.test_corrupt_schema_is_not_hidden_by_initialize_recovery tests.skills.test_sdlc_000_ctx.CtxRuntimeTests.test_corrupt_store_is_not_hidden_by_lock_recovery
```

基础结果：

- Python compile：`PASS`；bytecode 定向到
  `/private/tmp/sdlc-000-ctx-evaluate-fix-pycache`，验证后已删除；
- Runtime Contract Validator：`PASS`，5 个共享 Contract、1 个正式 Skill；
- CTX Producer 单元测试：`20/20 PASS`，其中并发首次 create 回归连续执行 200 个隔离
  线程 Boundary Fixture，并执行 10 个隔离双进程 CLI Fixture；
- 全量单元测试：`75/75 PASS`；
- 三个 Design-time Source SHA-256：与 approved Design / Source Lock 全等；
- Fresh Formal Runner 为 `PASS=44 / FAIL=0 / NOT_RUN=4 / DEFERRED=3`；`EV-C04 PASS`。
  退出码 `1` 只来自四个普通 Agent 槽位，四个槽位已有历史 fresh Agent 对照证据；
- Fresh 有限重复为 200 个隔离线程 Fixture、10 个隔离双进程 CLI Fixture，全部逐次确认
  `action_required + blocked/CTX_LINEAGE_EXISTS`、同一非空 CTX ID、一个 Artifact / Binding；
- 空 Schema 返回 `SCHEMA_ERROR`，非 SQLite Store 返回 `DATABASE_ERROR`；ArtifactStore
  前后快照相同，非 SQLite 原始损坏字节不变；
- 历史一次 `EV-C04 FAIL` 与其后 40 次通过继续保留，不删除真实失败记录；
- Cursor、Claude Code、Codex Client Case 保持 `DEFERRED`，没有跨入 Adapt。

## 4. Formal Runner 结果

### 4.1 既有 Critical Case

| Group | Result | Actual / Check |
|---|---|---|
| `EV-T01～T04` | `4 PASS` | 显式触发元数据与 `create/revise/check` 路由正确；真实 Client 行为未推断 |
| `EV-I01～I04` | `4 PASS` | 目标、Reference、Boundary 输入 fail closed；零未授权写入 |
| `EV-C01～C03/C05` | `4 PASS` | ready create、waiting_input、重复 Lineage、dry-run 边界通过 |
| `EV-R01～R05` | `5 PASS` | open 原地修订、frozen 新 Revision、no-change、Control、abandoned 通过 |
| `EV-K01～K06` | `6 PASS` | frozen/open/abandoned/Control/missing Store/非法 Domain 的只读行为通过 |
| `EV-S01～S06` | `6 PASS` | Source Lock、无 docs Runtime、不同 CWD、Foundation 失败、无直接 SQL 通过 |
| `EV-X01` | `PASS` | bundled target Skill 无兄弟 Skill 调用路径 |

### 4.2 Implement-fix 回归

| Case | Finding | Result | Actual / Check |
|---|---|---|---|
| `EV-REV001` | `REV-001` | `PASS` | 无 primary Resource 返回 `CTX_CONTENT_INVALID`，零 Store 创建 |
| `EV-REV002-MAX` | `REV-002` | `PASS` | Revision 1、2 已 frozen 后，以 Revision 1 为 Base 创建 Lineage 最大 Revision 3；Payload 声明 3，Base=1 |
| `EV-REV002-CLEANUP` | `REV-002` | `PASS` | 分配后、物化前异常使 Revision 2 变为 `abandoned/materialized=false`；不存在 open Control Reservation |
| `EV-D02` | `REV-003` | `PASS` | 完整 `final-confirmation-authority/v1`、独立 Delegation Basis、固定集合与摘要绑定可冻结 ready |
| `EV-D02-N01` | `REV-003` | `PASS` | 缺 `decided_at` 被拒绝，Revision 保持 open / 非 Authority |
| `EV-D02-N02` | `REV-003` | `PASS` | `Independence` 固定集合不精确被拒绝 |
| `EV-D02-N03` | `REV-003` | `PASS` | 越界/不可解析 Delegation Basis 被拒绝 |
| `EV-REV006-PEER` | `REV-006` | `PASS` | 同级 `inputs.context/evidence/supporting_members` 被消费；`SUP-001` 随 Payload 保存 |
| `EV-REV006-NESTED` | `REV-006` | `PASS` | 嵌套 Evidence / Supporting Member 漂移形状返回 `CTX_CONTENT_INVALID`，零 Store 创建 |

### 4.3 External Conflict 与非传递授权

`EV-D03 / EV-X02` 使用 Runner 私有本地进程 Fixture：

1. 授权集合只有 `fixture:external-context-producer`；
2. 生产者实际运行一次并输出 JSON，SHA-256 为
   `bea4795214f9dac3654462750d38bcc3e4fceb33176ad57a95c8035f8171dde7`；
3. 输出请求 `fixture:external-normalizer`，但该依赖不在授权集合；
4. call log 只有生产者，`dependency_invoked=false`，dependency canary 不存在；
5. 原始外部输出只进入同级 `inputs.evidence` 与 `inputs.supporting_members`；
6. 其中冲突的 `resource_type=workspace` 作为候选映射进入 CTX 时返回
   `CTX_CONTENT_INVALID`，没有覆盖 Contract，也没有创建 Store。

| Case | Result | Actual / Check |
|---|---|---|
| `EV-D03` | `PASS` | 真实外部输出、摘要与冲突候选进入 Fixture；Runtime fail closed |
| `EV-X02` | `PASS` | 单一授权未传递到请求依赖；call log 与 canary 共同证明零依赖执行 |

该证据只证明 Portable Eval Fixture 与 Runtime 边界，不冒充任何 Client 的 Skill 调用
行为；Client 仍必须在独立 Adapt 工作包验证。

### 4.4 并发首次 create

| Case | Result | Actual / Check |
|---|---|---|
| `EV-C04` | `PASS (fresh recheck)` | 未修改 Runner / Fixture / Oracle；两个请求得到 `action_required + blocked/CTX_LINEAGE_EXISTS`、同一 `CTX-20260830101112-01`、1 个 Artifact；随后 200 个线程 Fixture 与 10 个双进程 Fixture 均逐次确认相同状态/错误码并由公共 API 读回唯一 Artifact / Binding |

历史间歇失败仍作为 EVAL-001 回归来源保留；当前 `PASS` 只表示修复后的 fresh Formal
recheck 和有限重复均满足同一冻结 Oracle，不删除或改写历史失败事实。

### 4.5 Client Case

| Case | Result | Actual / Check |
|---|---|---|
| `EV-P01` Cursor | `DEFERRED` | 未执行 Discovery / Invocation / Behavior |
| `EV-P02` Claude Code | `DEFERRED` | 未执行 Discovery / Invocation / Behavior |
| `EV-P03` Codex | `DEFERRED` | 未重做 Codex Adapt；`REV-005` 保持未验证 |

## 5. Fresh without-skill 对照

四个对照使用修订后的同级 Invocation 形状，各自使用隔离 Project Root、fresh ephemeral
普通 Agent，未加载目标 Skill Runtime。四个输出均未通过共享 `validate_result`；with-skill
对应 Case 全部通过固定 Oracle。

| Baseline | Invocation SHA-256 | Prompt SHA-256 | Output SHA-256 |
|---|---|---|---|
| `EV-W01-C01` | `35bf7d74e277475616c8b01f920552b793f54e7b77eda9a098d1a0aaff665362` | `cd60572ae4865da4ac90d3f469bac19cc7ee830f71a4f059e2a5d7fe9a1233ad` | `78e9937924b73500105321140c06960193a07559ab4646ab07a02d6209677607` |
| `EV-W02-C02` | `6023627942fd70416d8c7fac99a39fc45b108873aec9fc374f9e42ec19fec65b` | `8e7d246ea3624018ea9a0f93ddd21320e7ba00046779946ac74862d3e23e362b` | `3ae23362e7c54be198a52718ec1f7742b21722b749e6c44cc64c7869b90a62d8` |
| `EV-W03-R01` | `48f7fd0fcaa117fd7637bfeff9e14e176bf6fe79fadf6e428fefa27d67883274` | `b0ce0f3f4e73fe10c004250537d6d069cf85c1b2575c2bffb58ca5a244ebccf1` | `33c424d031ba2def470ece3b19d3a24c2fcf3c53a37abb4edeb42b952a84c25e` |
| `EV-W04-K05` | `b287542bf45d39a5a81b4f9ab4ba77a101a7e2881d3458c82e6c05de6570c89f` | `92f7347dec0cf9d60c978e82e52ae75e40ce24497a797cdafffe719ace60d695` | `249c4f1776708e71d9147473c17b613ec0c93ef9c2ee17893563d988ef69bb6b` |

| Baseline | without-skill Actual | Result Schema | Side Effect | with-skill | Comparison |
|---|---|---|---|---|---|
| `EV-W01-C01` | `blocked/RUNTIME_NOT_AVAILABLE`，未创建 Artifact | `FAIL`，含不支持字段且缺标准 Envelope 字段 | Store 字节不变 | frozen / ready / Gate pass | `PASS` |
| `EV-W02-C02` | 普通 Agent 直接操作 SQLite，生成并冻结非法 `CTX-001`，未保留正确 waiting_input Authority 边界 | `FAIL`，`status=succeeded` 等字段不合约 | Store 被修改 | materialized open / waiting_input / 3 个 Open Items | `PASS` |
| `EV-W03-R01` | 因缺 Final Confirmation 安全阻塞，未完成修订 | `FAIL`，缺标准 Envelope 字段 | Store 字节不变 | Revision 数量不变、generation +1 | `PASS` |
| `EV-W04-K05` | `inconclusive`，未返回稳定 `STORE_NOT_FOUND` | `FAIL`，不支持字段且缺标准 Envelope 字段 | 零写入，仍无 `.sdlc` | failed / `STORE_NOT_FOUND` / 唯一下一动作 | `PASS` |

with-skill 四案在结构、Identity / Revision、Open Items、Gate / Status、稳定错误码和副作用
上均优于 without-skill，`CHK-21 PASS`。C02 baseline 的越界写入仅发生在隔离
`/private/tmp` Fixture，不在当前仓库或用户项目中。

## 6. Findings 状态

### `REV-001 / REV-002 / REV-003 / REV-006` — Formal verification `passed`

新增回归已覆盖 Finding 的准确失败路径和正向路径；本轮不修改历史
`REVIEW-RESULTS.md`，只记录当前 Formal 证据。

### `REV-004` — Formal evidence repair `passed`

`EV-D03 / EV-X02` 不再以非法 Basis 或静态文字替代行为证据，已形成外部输出摘要、授权
集合、实际 call log、依赖请求、canary 零写入、同级 Evidence/Supporting Member 与 Runtime
冲突拒绝结果。

### `EVAL-001` — Critical — `passed`

- 历史同一 Runner 逻辑曾观察到一次 `EV-C04 DATABASE_ERROR`，失败记录保留；
- 本次 fresh `evaluate-fix` 未修改 `EVAL-PLAN.md`、Runner、Fixture 或 Critical Oracle；
- Formal Runner 的 `EV-C04 PASS`：两个并发首次 create 返回同一 CTX ID，结果集合为
  `action_required + blocked/CTX_LINEAGE_EXISTS`，公共 API 读回一个 Artifact；
- 现有 Producer 回归独立执行 200 个隔离线程 Fixture 和 10 个隔离双进程 CLI Fixture；
  临时辅助校验复用同一 Fixture 与公共 API，逐次确认 `blocked` 分支错误码为
  `CTX_LINEAGE_EXISTS`，并由 `ArtifactCatalog` 与 `ContextLineageRegistry.find` 读回唯一
  Artifact / Binding；
- 空 Schema 与非 SQLite Store 分别返回 `SCHEMA_ERROR`、`DATABASE_ERROR`，均 fail closed；
  ArtifactStore 前后快照相同，非 SQLite 原始损坏字节不变；
- Runtime Contract Validator、全量 `75/75` 单元测试和编译检查通过；没有无限重试、吞错、
  直接 SQL、私有 Store、Schema 复制或 fallback 作为评测补偿。

### `REV-005` — `not evaluated`

本轮未执行 Codex Adapt，也未读取或修改 `ADAPT-CODEX-RESULTS.md`。该 Finding 继续保留，
但必须在当前 Critical Eval 回归关闭后再进入独立 Codex Adapt。

## 7. 重试、人工补充与限制

- 第一个 baseline 启动在受限外层沙箱内因 Codex state DB 只读而在 Agent 创建前失败；
  获准后以同一 Prompt、Invocation 和隔离 Project Root 重启，未改 Fixture；
- 其余三个 baseline 各创建一个 fresh ephemeral Agent；输出未人工编辑；
- C02 baseline 自行直接操作隔离 SQLite 并形成错误冻结结果，作为失败证据保留；
- 历史 Formal Runner 对 `EV-C04` 的 40 次有限复现全部通过；未删除先前失败；
- 本次 fresh evaluate-fix 独立执行一次完整 Formal Runner；没有重试失败 Case，Runner 因
  四个 `NOT_RUN` 普通 Agent 槽位按设计退出 `1`，但 `FAIL=0` 且 `EV-C04 PASS`；
- 本次有限重复固定为 200 个线程 Fixture 和 10 个双进程 Fixture，没有无限重试；临时
  辅助校验前两次分别因缺少仓库 `PYTHONPATH`、混用包命名空间在校验启动/首个只读检查处
  失败，未观察或重试 Runtime 竞态失败；只修正模块加载配置后完整运行固定 200/10 次通过；
- Runner 私有 external producer/dependency、baseline Prompt/Invocation/Output 与重复运行 JSON
  位于 `/private/tmp/sdlc-000-ctx-eval-004.D92ksx/**`；compile cache 位于
  `/private/tmp/sdlc-000-ctx-eval-pycache/**`；
- 本次在 `/private/tmp` 使用过辅助校验脚本与 compile cache，工作包结束前均已删除；
- 未执行 Cursor / Claude Code / Codex Adapt、Review、finalize、commit、push、merge、tag
  或 release。
