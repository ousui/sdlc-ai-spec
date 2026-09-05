# RLS Final VFY Integration Review — 2026-09-05

## 结论与适用边界

VFY_RLS_INTERFACE_DELTA_REVIEW = STATIC_REVIEW_COMPLETE_WITH_OPEN_IMPLEMENTATION_GATES

RLS_CLOSED_LOOP = HARD_BLOCKED

本轮第一个不可在现有执行边界内消除的阻塞是 `RLS_REQUIRED_OS_SANDBOX_UNAVAILABLE`：Web 执行宿主为 Linux，没有 bwrap，也没有 macOS sandbox-exec。最终 VFY Fixed Eval 的 E041/E046 必须执行实际 OS-contained command；不能用能力探测通过、旧日志、skip 或无沙箱 fallback 代替。RLS 最终闭环要求重跑这些门禁，因此本宿主不能产生有效最终 PASS。未安装依赖，未执行生产效果。

这是 RLS 本次验证宿主的阻塞，不是 VFY 未完成或未集成。以下代码问题是应修复的 RLS 工作，不能据此退回或重写已接受的 VFY。

本文是设计检查点，不是正式 Evidence；没有新 Implementation Subject，没有 87/87 本轮执行结论，没有执行最终 Git 拓扑。旧报告中声称存在或通过的预收口组件，仅在精确远程源码和本轮实际日志支持时才可复用其结论。

## 1. 已重新读取的 Authority

| 对象 | SHA / Tree |
|---|---|
| main | `644218e02876c5649fd87cfca12e1876d3b3b8bf` |
| main Tree | `3a75052b5ab1a10b91eb4cc1582b527a86e7dd5b` |
| Accepted VFY Subject | `5ea3ba9aa7288021c4d99b14cff76ec0fc405841` |
| Accepted VFY Evidence Head | `46509eb6688df30e71ed094132b2d10e81ceb2ac` |
| Accepted VFY Evidence Tree | `3a75052b5ab1a10b91eb4cc1582b527a86e7dd5b` |
| VFY Design | `638e27221b13d74208b54f78530cf338f67879af` |
| main Design replay | `8d293355235057142235f1ca63c241d586c8abdc` |
| 上述两个 Design Tree | `a825ab8be9cda8bf95d25c9e79c702438656a282` |
| RLS Design source | `91f51d5b32e95114ea3d234f8fc0928ec608aaa1` |
| RLS provisional source | `70e6f92fd1644831c836de1e2b8a0aa567c5a979` |
| RLS provisional source Tree | `85ea4c14c7b7219b60f78a5191e1138045228714` |

`VFY_MAIN_INTEGRATION_MODE = TREE_EQUIVALENT_LINEAR_REPLAY`。Maintainer 于本轮明确授权该模式；它替代旧 Goal/PR 正文中的“必须先 merge PR #7/#9”启动条件。PR #7/#9 保留为 historical delivery records，严禁再次 merge、评论或修改。PR #8/#10 也不在本轮直接 merge。

Final Web Review 的独立接受记录：
https://github.com/ousui/sdlc-ai-spec/pull/9#issuecomment-5548759714

其已接受的历史测试与 Evidence 不是本轮重新执行的 RLS/VFY 回归。

## 2. 精确源码锚点

下列 VFY 路径均读取自 accepted Evidence Head `46509eb...`，不是 moving branch：

| 路径 | Git Blob |
|---|---|
| `skills/sdlc-500-vfy/scripts/vfy_release.py` | `d5529be9b3efeb30c834884e3fa53bc8bb532dcc` |
| `skills/sdlc-500-vfy/references/vfy-release-candidate-v1.schema.json` | `98cf80e38de063ffe4254aab1ab34dc16da6faa2` |
| `skills/sdlc-500-vfy/scripts/vfy_builder.py` | `a4adcb604e7569b7903eeb0ce63989084ea6024c` |
| `packages/sdlc_lifecycle/query_vfy.py` | `dc2790f569ea5bd364b30a33d2d1229afaa06d53` |
| `packages/sdlc_artifact_store/__init__.py` | `3ba9d862f8ac1ca6662c33fe6fef54e518befaa3` |
| `packages/sdlc_artifact_store/models.py` | `3f3e59b8bd0a4dba931e07dda69a5ade169723f7` |
| `packages/sdlc_phasekit/__init__.py` | `212f021f77232913acab1a20d16c6224a8f7d488` |
| `skills/sdlc-500-vfy/scripts/vfy_executor.py` | `180eb60b8adc27ce5b5b62aa8ce4408ced06ceff` |
| `tests/evals/run_sdlc_500_vfy_eval.py` | `9e70341fe693cfa4a76d5f2a3798faedfe00821a` |

RLS 对照读取自 `70e6f92...`：`rls_persistence.py` Blob `165e9721b2f4127f28f044db789377212dee9239`；`rls_domain_verifier.py` Blob `6c6409d62d3800841274cf0ad6798fac4cb9a285`；`rls_canonical.py` Blob `3e22fa1883b6fc9920c98b1d3622644a82be3087`。

## 3. 可复核静态结果

RLS bundled Candidate Schema Blob `f9f642a005e5b04b0721f9567af209681b8bd4f0` 与最终 VFY Schema JSON 语义相等，但字节不相等。实际重算两个 Git Blob 后匹配在线 Blob；24 个 required 字段无重复，Draft 2020-12 metaschema 校验通过。这只证明 Schema 对齐，不证明真实 Artifact 读回和执行通过。

- Final VFY Schema SHA-256: `15aff25625c2d43c29e62129ea3aaff9ee5ab45dd146eecff2b417e135d98027`
- RLS shadow Schema SHA-256: `3a3f5a81837b7b2bca6bd84abd32610a7b0da77ec2fac95eb5687ea2a863a5ab`

必须保留上游 `source_digest`，另算 Candidate transport digest；不能把二者混为一谈。最终 `canonical_members` 只持久化 `VFY-STATE` 与 `VFY-EVIDENCE-*`，并将 State Member 的 Final Confirmation 清空；准确读回时从 Primary 重建 Final Confirmation。不得假定存在 standalone Release Candidate Member，不得用原始 State Member 哈希冒充 producer 对完整 state 的 `source_digest`。

## 4. 必须修复的 RLS 接线问题

| ID / severity | 精确落点和事实 | 最小修复及必需验证 |
|---|---|---|
| RLS-FINAL-INT-001 / Major | `rls_persistence.py` 导入不存在的 `ArtifactStoreFacade`；实际共享包公开 `ArtifactStore` | 改用已存在的公开 API；独立 import、真实 Store create/read/write/freeze 测试，不增加伪 facade |
| RLS-FINAL-INT-002 / Major | Payload 使用不存在的 `context_reference/base_revision/primary/final_confirmation` 参数；真实模型要求 `primary_blob/primary_media_type/primary_sha256` | 逐签名适配；allocate 返回对象而非字符串/整数；generation 来自 Revision control；真实 CAS/abandon/freeze 回归 |
| RLS-FINAL-INT-003 / Major | DomainVerifier 从 phasekit 导入未导出的 `DomainVerification`，使用不存在的 `payload.primary`，构造不存在的 `details` 且缺 `approved` | 从共享 Store 使用真实模型；比较原始 stored Gate 与纯重算 Gate；调用者必须检查 `approved` 和当前 payload_binding；篡改冻结记录应失败 |
| RLS-FINAL-INT-004 / Major | `rls_canonical.py` Front Matter 缺 CTX context/profile，inputs 只写 VFY；工作流 status 被直接当作 Artifact Status | 从准确 Authority 获取 context/profile/直接上游 inputs；区分工作状态、Artifact Status、Gate、Release Conclusion；执行 Core parser 与语义交叉验证 |
| RLS-FINAL-INT-005 / Major | 已接受 VFY 不存 standalone Candidate Member，Schema 通过不能证明当前 Subject、Return、Exception 和 Evidence Authority | adapter 内完成准确 state/Primary/Manifest 读回、当前 IMP/Lifecycle/Control 校验及 Candidate 投影；与真实 VFY producer 差分测试，禁止运行时私读兄弟 Skill |
| RLS-FINAL-INT-006 / Observation | 旧 Goal 与 PR 正文仍要求 VFY merge；旧报告对 preclose、Store/scaffold 和测试的描述不等于远程事实 | 使用本轮新 Goal；逐项核对文件和命令，缺项记实施待办，不造 PASS，不把历史 PR 状态当集成障碍 |

以上是源码静态审查发现，本轮未对 RLS Runtime 执行 import 或测试；不将其包装成已运行失败日志。

## 5. Assumption Ledger：12/12 静态审查，0/12 最终执行关闭

沿用 `02-VFY-RLS-INTERFACE.md` 的 ID；所有行都须在最终 S 上执行后才能 CLOSED。

| ID suffix | 已接受 VFY 事实 / RLS 必要动作 | 剩余最终验证 |
|---|---|---|
| A01 | Candidate 使用精确 `vfy_reference`，不是 PR/branch/latest | exact persisted input + mismatch 负向 |
| A02 | frozen 来自 Store control，不信 JSON 自述 | open/abandoned/frozen 真实 Store 读回 |
| A03 | `scope_reference` 为精确 REQ/DSN/PLN Revision | 完整 Scope 与上游 Authority 一致，不缩 Scope |
| A04 | producer 的 Subject/Result 数组投影自同一 subjects；currentness 需当前 IMP Claim/Result | stale/partial/extra/result digest/Claim drift 负向 |
| A05 | `con_ver/con_val` 独立终态，pending 不允许 | Method/Target/fixed Conclusion 完整性 |
| A06 | product fail 不能因 Gate pass 被改写；需 active scoped Exception | fail-with-exception 与 fail-without-authority |
| A07 | Status ready/ready_with_exception 与 Gate pass/pass_with_exception 分离 | Primary/State/Manifest 篡改和重算 |
| A08 | early-stop 永不进入 RLS | 真实 early-stop Artifact 必须拒绝 |
| A09 | unresolved Return/Control 都阻止进入 RLS | 当前冻结 owner、resolution 证据与变更 |
| A10 | final Candidate applicability 仅 required/n/a/waived；required 必须 rls_ready | 合法无效果 disposition 与 pending 拒绝 |
| A11 | obligations 原样携带，不因 downstream 适配而收窄 | Method/Target/Exception -> RCF 全映射和执行前提 |
| A12 | Evidence 数组加真实 Supporting closure，不再要求旧 closure boolean | Member 存在/唯一/完整 digest，Final Confirmation 重建 |

## 6. 干净 Git 拓扑方案（尚未执行）

首选方案保留 accepted VFY 为第一物理父系，同时解决 main 的线性重放 merge-base：

```text
V = accepted VFY Evidence 46509eb...
M = main 644218e0...，且 tree(M) == tree(V)
B = 零内容 equivalence bridge：parents=[V,M]，tree(B)=tree(V)
B -> D（仅 RLS 设计）-> S（最终 RLS 实现）-> E（正式 Evidence/Handoff）
```

B 不执行 VFY 再合并，不改 VFY/main，只记录已核验的两条等价历史。第一父提交必须为 V，第二父提交为 M，tree 必须完全不变；M 因而成为 D/S/E 的祖先，PR 对 main 的净差异为 RLS。最终验收必须重新核对这一点。

D/S 只迁移允许的 RLS 文件，不能把旧 RLS Design/Implementation Commit 作为 parent，也不能 merge/rebase 旧 provisional implementation。已接受 VFY 本身的合法祖先当然保留；禁止的是新增旧 RLS/repair 侧支祖先，不是删除 accepted VFY 的历史。

先做本地备份与 git bundle，审查 path-level migration manifest，再在两个 owned refs 上用精确 force-with-lease 发布已验证的新链。此设计 checkpoint 仍附着旧设计来源，仅供恢复；不是 B/D/S/E 的任何一个已完成对象。本轮不更新 impl/rls-v2。

## 7. 执行状态和恢复入口

实际宿主预检：exit 2，Linux，backend=null，sandbox command launches=0。四个 GitHub 域名 DNS 失败；GitHub Connector 仍可读写设计 checkpoint。未执行 RLS Fixed Eval、VFY Fixed Eval、全仓、external 或 attest。没有正式 RLS Evidence。

恢复时运行 `16-LOCAL-CODEX-GOAL-FINAL-VFY.md`。它以 accepted final VFY 与 tree-equivalent main 为启动条件，先核验宿主能力，再完成干净收敛及全部最终实现/验证。不得重新启动 VFY 修复 Goal，不得再次合并 #7/#9。
