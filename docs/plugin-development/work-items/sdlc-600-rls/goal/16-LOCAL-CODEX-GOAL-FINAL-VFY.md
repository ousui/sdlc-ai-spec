# /goal — RLS 最终闭环：已接受 VFY、Tree-equivalent main

将本文件全文作为一次独立 RLS Goal 执行。目标不是报告计划或跑绿部分测试，而是在授权边界内完成最终 RLS 实现、准确验证和交付，或记录第一个真实不可恢复阻塞。先读取本目录 `15-FINAL-VFY-INTEGRATION-REVIEW.md`，保留有效旧 Design/Eval 和 87 个 Critical Cases。

本 Goal 依据 Maintainer 2026-09-05 的明确授权，取代旧 `10-LOCAL-CODEX-GOAL.md`、旧 PR 正文及旧 Web Review 提示词中关于“必须先合并 #7/#9/#8”或“RLS Subject 必须直接继承 main”的启动/拓扑条件；其他 Spec、安全与证据要求不得降低。

## 0. 精确输入与唯一目标

```text
repository = ousui/sdlc-ai-spec
VFY_FINAL_WEB_REVIEW = ACCEPTED
VFY_SUBJECT = 5ea3ba9aa7288021c4d99b14cff76ec0fc405841
VFY_EVIDENCE = 46509eb6688df30e71ed094132b2d10e81ceb2ac
VFY_EVIDENCE_TREE = 3a75052b5ab1a10b91eb4cc1582b527a86e7dd5b
OBSERVED_MAIN = 644218e02876c5649fd87cfca12e1876d3b3b8bf
OBSERVED_MAIN_TREE = 3a75052b5ab1a10b91eb4cc1582b527a86e7dd5b
INTEGRATION_MODE = TREE_EQUIVALENT_LINEAR_REPLAY
RLS_OLD_DESIGN_SOURCE = 91f51d5b32e95114ea3d234f8fc0928ec608aaa1
RLS_PROVISIONAL_SOURCE = 70e6f92fd1644831c836de1e2b8a0aa567c5a979
OWNED_REFS = design/sdlc-600-rls-goal, impl/rls-v2
```

PR #7/#9 为 historical delivery records；其 Open/Draft/Unmerged 不构成启动阻塞。不要 merge、评论、关闭或更新它们。PR #8/#10 不直接 merge。main、impl/vfy-v2、VFY Design、IMP 和其他所有 refs 均只读。只能向两个 owned refs 写入 RLS 交付。

## 1. Preflight 与事实读回

1. fetch 当前 refs，读取实际 main、VFY Design/Implementation、RLS Design/Implementation 和 PR #8/#10，记录完整 SHA/tree/parents。PR prose 不是 Ref Authority。
2. 独立核验 final Web Review comment `5548759714` 接受 exact VFY pair；核验 Evidence Head 的 sole parent=Subject，Subject parent=638e27221b13d74208b54f78530cf338f67879af。核验 main Tree=accepted Evidence Tree。不要因为 Handoff 内较早的未 Review/未集成状态推翻后续准确接受记录。
3. 若 main 已前进，先区分纯 Ref 时间变化和内容变化。只有重新证明与授权 VFY Tree 等价时可使用新 main SHA；非等价的新产品内容不得静默取代本 Goal 的上游，记录实际 diff 和真实新输入阻塞。
4. 读取当前 RLS Design checkpoint；允许它在旧91f51d5之后追加本轮 RLS-only 恢复文档。实施前审查差异与来源。impl 若不是70e6f92或本 Goal 自己的已记录 Head，按单写者规则停止，不覆盖。
5. 使用干净持久 worktree，保留未知 staged/unstaged/untracked。记录工作根、HEAD、状态；不要 reset 用户工作树。备份两个旧来源的本地 bundle，并校验可恢复；不创建额外远程分支。
6. **先测正式执行能力**：在 accepted VFY 的独立临时 detached worktree，运行其真实 strict E041/E046，使用当前宿主现有且可激活的 macOS sandbox-exec 或 Linux bwrap。普通 unittest 的 missing-capability 路径不代替 Formal Eval。禁止安装、无沙箱降级或修改 VFY 测试；任一能力缺失则 HARD_BLOCKED，保留日志与零效果事实。
7. 两个 external 固定项目必须可读取精确 SHA。网络读取可有界重试（最多3次，记录每次失败）；缺少本地对象且读取失败是环境阻塞，不是项目通过。

## 2. 干净收敛：先局部验证，再迁移 Ref

不要 merge/rebase 旧 impl/rls-v2；旧 RLS history 只是源文件来源。

使用如下精确拓扑，在本地 detached/worktree 中建立，不改上游 refs：

```text
V = 46509eb6688df30e71ed094132b2d10e81ceb2ac
M = 已验证与 V Tree 等价的当前 main
B = tree(V), first-parent V, second-parent M（零内容 bridge）
B -> D（RLS final design）-> S（RLS implementation subject）-> E（RLS Evidence/Handoff）
```

B 可通过 `git commit-tree <tree(V)> -p <V> -p <M>` 建立；使用已配置身份，不硬编码他人身份。建立后必须证明 parents 顺序、tree 相等和 main 为祖先。此桥接不等于重新合并 #7/#9，也不改变 VFY/main。

D 从 B 开始，只迁移 `docs/plugin-development/work-items/sdlc-600-rls/**`。审查旧设计和70e来源中的有效修订，再纳入本轮15/16文件，修订最终 Authority/适配计划，保留原00历史基线而另记最终绑定。D 相对 B 必须只有 RLS 设计路径。

S 从 D 开始，只迁移以下旧实现路径，再修复/最终化：

- `skills/sdlc-600-rls/**` 与 `tests/skill_rls/**`；
- `tests/evals/sdlc_600_rls_cases.json`、`test_sdlc_600_rls_case_coverage.py`、`run_sdlc_600_rls_eval.py`；
- RLS 专用 Source Lock、Runtime Independence、provisional/pre-integration 工具，逐文件列入 migration manifest，不使用宽泛 tools/** 覆盖。

逐路径记录 source commit、source blob、迁移/修改/不迁移理由。最终集成允许新增 query_rls、RLS status projection、对应 lifecycle/status/system integration 测试与 RLS delivery/external 工具；共享包只作必要的 additive RLS 接线，不改 VFY 文件、不覆写现有行为、不复制 Store/Claim/Lifecycle Schema。

不迁入旧 VFY 设计文件、repair history、IMP/VFY Evidence、.github、internal、payload 或 quarantine 来源。accepted VFY 自身的既有祖先保留；S 不得新增旧 RLS 源分支作为祖先。

## 3. 第一实施关：真实 ArtifactStore / Canonical

先修复15号审查记录的 INT-001..004，不要相信旧报告声称已完成的 Store 桥接。

- 使用实际 `ArtifactStore.open_read_only/open_read_write` 与返回对象；不创建不存在的 ArtifactStoreFacade，不用反射猜方法绕过契约。
- `CanonicalRevisionPayload` 使用实际模型：artifact_id/type/revision/status、primary_blob/media_type/sha256、members、manifest。
- ArtifactAllocation/RevisionControlRecord 不能当作字符串/整数；generation 来自准确 Revision Control。
- DomainVerification 从实际共享 Store 导入，显式返回 approved 与当前 payload_binding；不得忽略 approved=False，不得接受旧 binding。
- context 是准确 CTX，不是 Scope；profile、直接输入集、Artifact Status、Gate、Release Conclusion 分别解析。
- create/execute/confirm 同 Revision，写入使用 CAS；first-write失败 abandon；retry新Revision；Target变化新Artifact；Scope/Result变化返回上游。
- `check -r` 必须读精确 persisted Revision，拒绝 stdin 伪 Artifact、移动选择器及错误 member；绝对只读。
- Primary ↔ RLS-STATE ↔ Manifest ↔ Supporting Evidence 交叉验证，先保存 stored 值再纯重算比较，不能比较已被 verifier 改写的同一对象。
- freeze 前证明 Gate 与当前 Final Confirmation 有效；失败不得假冻结。Effect发生但回写失败必须保留可恢复执行日志与不确定状态，禁止自动重放或伪取消。

必测真实 Store：fresh create、CAS冲突、exact读回、缺失/重复成员、Primary/State/Manifest篡改、冻结不可改、旧确认、写失败abandon、读回零写入和效果后持久化失败恢复。

## 4. VFY_RLS_INTERFACE_DELTA_REVIEW：关闭 A01..A12

最终 Authority 仅来自 accepted VFY Runtime/Schema/Artifact/Evidence/Handoff。旧影子 fixture 只保留作显式负向/历史兼容测试，不作为 final PASS输入。

1. 对照24字段Schema；语义已相等不代表字节相等，最终bundle锁定准确选择的上游字节。
2. 通过共享 Store 和规范化 Authority API 读取精确 VFY Revision、Primary、VFY-STATE、Manifest 和 Evidence；不要寻找并不存在的 standalone Candidate Member。
3. 从 Primary 重建 Final Confirmation 所需规范字段，以 producer 的完整 state 语义验证 `source_digest`；另算 Candidate digest。任何重算必须有真实 producer 差分测试，不得删除 digest 校验或改用 raw Member hash。
4. 使用共享 Lifecycle/Current IMP Claim 和 Result 读回验证完整当前 Subject Set、依赖链、Return/Control 与 Exception。候选里自报 true 不是事实来源。
5. VFY wire/state解析集中 `rls_vfy_adapter.py`；其他 RLS模块只用稳定内部对象。运行时不读取兄弟 VFY Skill 的私有代码，也不读取 docs。必要共享扩展应为 additive deterministic contract，不能搬入完整 VFY引擎。
6. final adapter 对真实 VFY producer 输出执行正负差分；冻结合法输入、stale、early-stop、pending、Return、scope/result不一致、Exception过期或错范围、Evidence缺失全部覆盖。
7. required须ready；n/a/waived仅合法无效果处置；product fail只有有效 scoped Exception可继续，原结论不改。
8. carried Release Target obligations必须完整映射RCF，包含准确来源和原判定口径，不收窄。
9. 每个 ledger行记录 source SHA/blob、测试方法、日志和最终状态。只有真实最终测试通过才CLOSED，不把 STATIC_REVIEW_COMPLETE 当运行通过。

## 5. 复用并加固 Effect / Sandbox / Revision

保留现有独立 Effect Authorization、历史绑定、RLI/RCF、Fake Target、87Case与私有测试；先运行再最小修复，不盲目重写。

验证授权绑定：Artifact ID/Revision、Release、Scope、Result Set、VFY引用及digests、Target/Baseline、selected/full RLI contract、RCF contract、Checklist、authorizer、有效期。write_policy、GitHub权限、Final Confirmation、Trigger不能代替授权。

确认授权来自可信授予通道而非可任意伪造的自述JSON；授权历史完整、不可回改，校验使用和执行时间、范围与唯一消费；重试必须新基线、新授权。历史合法结果变化不能抹除或错误自失效旧授权，但变更不可变Contract必须拒绝。

只有本地专用temp Sandbox：baseline/no-op/success/partial/failure/cancel-before-effect/retry/target-side confirmation/immutable Evidence/cleanup。测试symlink/path escape、目标漂移、第二项异常保留第一项效果、Evidence写失败、未知效果不能取消、Secret不落Artifact/日志、错误Envelope不泄露秘密。

Gate与ReleaseConclusion分离；可信failed/partial/cancelled可以Gate pass，Gate fail的success不能freeze。Follow-up唯一且符合Spec；check不产生Store或Target写入。

## 6. Shared lifecycle/status 与 Source Lock

实现 additive `packages/sdlc_lifecycle/query_rls.py` 及 `skills/sdlc-status` RLS投影，保持现有VFY字段和行为。覆盖 absent、n/a/waived/pending、open各等待态、frozen success/partial/failed/cancelled/retry/return_req/dsn/pln/imp、new revision、new target、no-change、abandoned。

投影只读，不从Artifact Gate推断发布成功，不以PR状态判阶段就绪。Source Lock最终non-provisional，绑定实际bundled contracts、schema和共享接口；不得仅改provisional=false而无真实输入/测试。

安装副本Runtime Independence移除docs/tests/AGENTS/Handoff，执行受支持命令及真实Store读回；不联网、不安装、不私读兄弟Skill。

## 7. 最终验证、修复循环与证据

实现或修正唯一稳定入口：

```bash
python3 tools/run_rls_delivery_validation.py --profile quick --source-sha "$S" --json-out "$OUT/quick.json"
python3 tools/run_rls_delivery_validation.py --profile phase --source-sha "$S" --json-out "$OUT/phase.json"
python3 tools/run_rls_delivery_validation.py --profile full --source-sha "$S" --json-out "$OUT/full.json"
python3 tools/run_rls_delivery_validation.py --profile external --source-sha "$S" --json-out "$OUT/external.json"
python3 tools/run_rls_delivery_validation.py --profile attest --source-sha "$S" --json-out "$OUT/attest.json"
```

OUT在工作树外。每个receipt记录exact SHA/tree、argv/cwd/exit/duration、实际stdout/stderr及digest、失败和重试、前后工作树状态。缺文件/命令/能力不能SKIP；失败也必须输出JSON。

phase包含RLS-E001..E087真实执行、唯一primary test与oracle检查，missing/duplicate/out-of-order/skip/expectedFailure/未执行均失败。full包含全部RLS私有测试、独立Effect审查、VFY80/80严格Eval、VFY installed Runtime Independence及全仓回归。

external必须在固定精确项目执行真实链：

```text
ousui/springgear@e855096ff19dcdb303dc4250ba19c30acd743ac7
flipped-aurora/gin-vue-admin@a6882210a80bb27e3aa5dff0b4c21aa4afe8988a
CTX -> REQ -> DSN -> PLN -> IMP -> VFY -> RLS
```

RLS Target为本地Sandbox；记录当前IMP绑定、真实VFY Candidate、RLS持久化/授权/确认/Evidence；只clone或探测commit不算链路。记录项目前后HEAD/refs/status/tracked/untracked摘要和cleanup，远程写与安装为0。说明是生命周期集成验证而非完整产品验收。

读取第一处真实失败，修实现后重跑受影响门禁；不得删除测试、收窄Scope或降低Expected。每次S变化后旧报告失效。最后在干净detached exact S重新运行fresh attest，覆盖全套要求；独立源码/行为审查不能以文档存在检查代替。

## 8. Checkpoint、发布与最终输出

中间本地正常commit/日志可保留，GitHub只使用两个owned refs及RLS PR checkpoint，不用Actions执行器，不新增Workflow/Release/asset/tag/observer/finalizer/materializer/evidence分支。

D/S的最终清晰历史必须符合第2节。发布前检查两个Ref仍等于记录的expected-old，使用精确force-with-lease只收敛RLS refs。每次成功更新立刻回读SHA/tree/parents/路径。并发写入则停止，不普通force。不要重写accepted VFY/main。PR8/10维持Draft，不merge；更新RLS PR正文，显式说明新拓扑及历史来源。

全部验证通过后，在S的唯一子提交E中保存正式RLS Evidence/Handoff、SHA-256 manifest、final result与新review请求。Handoff不能嵌入自己的未知commit SHA；用PR最终读回登记E。Evidence必须绑定S，不是Web旧checkpoint或E本身。

正式Web Review提示词仍保留独立审查全部代码/证据要求，但其拓扑验收改为B/D/S/E和本轮tree-equivalence，不要求历史#7/#9变为Merged。本Goal不自签最终Web Review ACCEPTED，不合并PR。

成功终态必须为：

```text
RLS_CLOSED_LOOP = PASS
VFY_UPSTREAM_SHA = 46509eb6688df30e71ed094132b2d10e81ceb2ac
RLS_DESIGN_HEAD_SHA = <D>
IMPLEMENTATION_SUBJECT_SHA = <S>
EVIDENCE_HEAD_SHA = <E>
FIXED_EVAL = 87/87 PASS
VFY_REGRESSION = 80/80 PASS
FULL_REGRESSION = <实际执行数及结果>
EXTERNAL_PROJECTS = 2/2 PASS
REAL_TARGET_EFFECTS = 0
PR_MERGED = NO
WEB_RLS_REVIEW = REQUIRED
```

出现新的真实不可恢复阻塞时，保存已完成commit/日志/checkpoint并输出：

```text
RLS_CLOSED_LOOP = HARD_BLOCKED
FIRST_BLOCKER = <具体事实>
EXPECTED = <能力、SHA或输入要求>
ACTUAL = <实际观察>
RLS_DESIGN_REF = <完整SHA>
RLS_IMPLEMENTATION_REF = <完整SHA>
LAST_VERIFIED_CHECKPOINT = <准确对象>
VFY_MODIFIED = NO
MAIN_MODIFIED = NO
REAL_TARGET_EFFECTS = 0
```

不得以RUNNING/PENDING/等待GitHub/稍后继续作为最终结果。只因代码还需要修复不是不可恢复阻塞；缺实际安全执行能力且禁止安装/降级则是。
