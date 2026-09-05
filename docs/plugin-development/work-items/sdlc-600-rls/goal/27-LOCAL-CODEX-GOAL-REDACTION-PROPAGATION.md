# /goal — RLS-WEB-003 传播修复：最终 S3/E3 验证交付

将本文件全文作为一次 Goal。Web 已修复敏感值传播，不重新设计 RCF 或人工观察；
复用远程源码，修复真实集成失败，生成新的准确 Subject/Evidence，最后停止。

## 1. 准确输入与边界

```text
accepted VFY = 46509eb6688df30e71ed094132b2d10e81ceb2ac
main = 644218e02876c5649fd87cfca12e1876d3b3b8bf
B = f171118380535d8c27a1929d0ef061510f82305f
D = c9615cec2da3b39949a3fdd8be32396eae6db3aa
reviewed S2 = 797bde43a31b6e5afdb028de7f8944cea996b460
historical E2 = 93e98c577b5c3136df55ee5a7cb7a1c2adfcda30
propagation code checkpoint = 206c379b77bb47ba0cf7913ea6dc1f8a39ed9bcd
```

先 fetch 真实 Ref，记录实际 `origin/impl/rls-v2` SHA/tree 为 REPAIR_SOURCE_SHA/TREE。
它必须含上述 checkpoint 与本文件、26号说明。不要从 PR Body 获取 Head。
保留用户工作树、未知修改及备份；发现不明并发推进则 HARD_BLOCKED，不覆盖。

验证 B ordered parents=[accepted VFY, main] 且三者 Tree 相等，D sole parent=B。
VFY 已通过 TREE_EQUIVALENT_LINEAR_REPLAY 集成；#7/#9 是历史记录，不 merge、
评论或修改。保持 main/VFY/B/D、PR #8、shared Runtime 与 workflow 不变。
只允许本轮最终发布 `impl/rls-v2`，更新 PR #10 元数据并保持 Draft。
禁止生产/远程 Target effect、Release/Asset、Tag、额外远程分支、Actions 执行器、
依赖安装、关闭检查、降低 Spec/oracle 或伪造 PASS。仅使用本地 Sandbox。

## 2. 首先执行传播修复门禁

读取 26 号说明和 PR #10 review 5120883644。核对 helper/test Blob：

```text
tools/rls_validation_support.py = a7fb955175a2a48b739965f6c5deec280c037de1
tests/skill_rls/test_web_repair_redaction_propagation.py = fa0ecad0c33cdd702237e75e4cc44d6123f6db0f
```

执行并保留原始命令、退出码、实际计数与安全归档的日志：

```bash
python3 -m unittest -v \
  tests.skill_rls.test_web_repair_redaction_propagation \
  tests.skill_rls.test_web_repair_redaction
python3 -m unittest -v \
  tests.skill_rls.test_web_repair_confirmation \
  tests.skill_rls.test_web_repair_confirmation_batch \
  tests.skill_rls.test_web_repair_store
```

前一命令应实际执行 56+18=74 个测试，不能少测/skip/expectedFailure。必须独立
复验两种密码参数回显、JSON 敏感字段与旁路字段、跨 stdout/stderr、超时/异常、
嵌套 writer 首次写入、重复 JSON key 和合法审计字段保留。只能用模拟值。

检查原始 argv/environment 仍用于执行，敏感上下文只在内存内，归档字节/摘要/
返回 receipt/持久 receipt 一致。若聚合发现新的敏感值导致旧嵌套日志摘要过期，
修复其生成时序并重跑，不能删除一致性校验或仅在最终归档中事后替换。

新 source guard 已登记唯一新测试文件并排除 S2/E2/repair 祖先。若因新工作需要
额外路径，必须先记录最小必要理由；不能扩大 allowed() 来容纳无关文件。

## 3. 形成干净 S3

先用本地 Git bundle 保存 S2/E2/repair 对象，并独立 unbundle 检查可恢复性。
不创建远程备份分支、标签或 Release。不要切换/清理用户原 main 工作树。

在新的干净 worktree 中以 D 为唯一父系，选择性迁移 S2 的全部允许实现路径及
本轮传播修复，不盲目重写已有实现。保留 RCF、人工观察、Store、Lifecycle/Status
及所有旧测试。新实现应包含旧 84 个源码路径及一个新增测试路径，共85个；
逐项记录 source Blob、result Blob、mode 和变化理由。

不要 merge/cherry-pick 整个 E2 或 repair 历史，也不要把旧正式 Evidence 或新的
Goal/报告塞进 S3。S3 必须 sole parent=D。26/27号说明可随新 E3 的 Handoff 归档。
S1/E1/S2/E2、provisional 和 repair checkpoints 均不得成为 S3 祖先。

修复必要的真实失败后创建 S3，再运行准确 SHA 的 source guard。任何源文件变化
都使此前该 SHA 的结果失效；重新确定 S3 并重跑，不用旧日志拼接新 PASS。

## 4. 完整正式验证

确认宿主有现成 OS Sandbox 能力；没有则 HARD_BLOCKED，不安装或无沙箱降级。
严格运行最终 unified validator，OUT 必须在源码工作树外：

```bash
python3 tools/run_rls_delivery_validation.py --profile quick    --source-sha "$S3" --json-out "$OUT/quick.json"
python3 tools/run_rls_delivery_validation.py --profile phase    --source-sha "$S3" --json-out "$OUT/phase.json"
python3 tools/run_rls_delivery_validation.py --profile full     --source-sha "$S3" --json-out "$OUT/full.json"
python3 tools/run_rls_delivery_validation.py --profile external --source-sha "$S3" --json-out "$OUT/external.json"
python3 tools/run_rls_delivery_validation.py --profile attest   --source-sha "$S3" --json-out "$OUT/attest.json"
```

必须真实完成：RLS 87/87（原 IDs/Expected/ordered primary 不变）、strict VFY 80/80
（含真实 OS containment E041/E046）、完整私有/全仓回归、原64项Web修复测试加
本轮56项、10项真实Store、14项Source Lock及A01..A12、VFY/RLS installed independence、
独立Effect检查及新的detached exact-S3 fresh attest。

若没有其他测试变化，私有/全仓计数应从379/1012增加到435/1068；这只是计数核对，
不是允许硬编码 PASS。以实际执行测试身份、数量和退出码为准；任何差异须解释。
保留失败轨迹，不删除失败记录、不调低 Expected、不 skip、不期望失败计入PASS。

两个固定真实项目：
`ousui/springgear@e855096ff19dcdb303dc4250ba19c30acd743ac7`；
`flipped-aurora/gin-vue-admin@a6882210a80bb27e3aa5dff0b4c21aa4afe8988a`。
运行真实 CTX→REQ→DSN→PLN→IMP→VFY→RLS，仅本地一次性副本与Sandbox。
检查文件字节/mode、HEAD/refs/status、.sdlc 前后恢复并清理临时工作树/注册。
这是生命周期集成探针，不是完整产品验收或实际人工产品批准。

## 5. 新 E3 与独立审查交付

所有验证绑定稳定 S3 后，生成新 Evidence/Handoff，E3 sole parent=S3。不得沿用
旧 S2/E2 的 PASS。Manifest 必须完整覆盖归档文件与Handoff；更新新 verifier 的
实际测试计数和新policy=v2，不把原64项硬编码为全部修复测试。

完整检查每份归档日志的字节、SHA-256、stdout/stderr 与 receipt、source SHA/tree、
零skip、fresh清理及外部恢复。敏感值集合不归档；没有未脱敏原始副本。旧 E2 中
没有被证明存在真实凭据泄漏，不以猜测改写历史或声明泄漏。

在持久本地目录提供 byte-complete 的 E3 Evidence/Handoff 包、完整 Manifest 和
SHA-256，以及准确Git对象备份/完整源码包供 Web 独立读回。不要上传为 Release Asset，
也不要将大ZIP作为Runtime或仓库中间payload提交。

发布前回读 remote expected-old=REPAIR_SOURCE_SHA，检查没有并发写入；仅在本轮
bundle备份完成且所有门禁真实通过后，用精确 --force-with-lease 收敛 impl/rls-v2。
立即回读 E3/S3 parents/tree/路径/证据摘要。更新 PR #10 绑定新 S3/E3，保持 Draft。
不修改 PR #8/#7/#9，不合并 main，不自行签署 WEB_RLS_REVIEW=ACCEPTED。

成功输出 RLS_REPAIR_CLOSED_LOOP=PASS、RLS_CLOSED_LOOP=PASS、S3/E3完整SHA、
实际各套件计数、REAL_TARGET_EFFECTS=0、PR_MERGED=NO、WEB_RLS_REVIEW=REQUIRED。
真实不可恢复阻塞输出 RLS_REPAIR_CLOSED_LOOP=HARD_BLOCKED、首个阻塞、预期/实际
SHA和保留对象。RUNNING/PENDING/等待/稍后继续不是最终结果。

唯一下一工作包是独立 Web Review；仅由独立审查接受或要求继续修复。
