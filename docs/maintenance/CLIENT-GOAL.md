# Client：同一分支的一次全流程验收

读取 PR 的当前交付 Head，fetch 后在独立干净 worktree 检出 `refactor/skill-unification-cleanup`。只处理该分支，不写 main，不重新合并旧 PR，不重写历史。先保存 SHA/tree 与工作树状态；发现非本轮已说明的并发变化时停止核对。

## 本次定向重验：收据身份与备份闭包

旧 Client 被测 `c8f6f7263e24ea8375065833f5741fbaf4d0f190` 的 e2e 归档
有 33/962 个 ID 被 `basic use` 误脱敏。Web 已修复 helper 与统一入口，旧结果
不得反填、修改或重用于新源码。本次不是重新做清理，也不重建 RLS Subject。

- 先读实际分支 Head，核对变更仅为 receipt helper、test_plan/validate、13 项新
  身份回归和紧凑文档。已有 120 项安全修复测试、阶段 Case Expected 不修改。
- 可先短跑 `tests.conformance.test_receipt_identity`；真正含秘密的证明字段必须
  失败关闭，不允许白名单漏密。tuple→JSON array 仅按相同 JSON 值比较。
- 新完整收集预计 975（962+13），以实际唯一 ID 为准。最终只跑一次 e2e。
- e2e 完成后用新进程重新 collect，与实际落盘 suite.json 的 executed_ids 和
  successful_ids 逐项/集合核对；失败、跳过和重复均不能签 PASS。核对所有 VFY
  proof 字段的 JSON 语义不受脱敏破坏，不只看计数或文件哈希。
- 新增失败不删除；退出后必须检查实际落盘字节。不要把旧日志的 [REDACTED]
  替换回来，源码变更后重新执行，输出仍先脱敏再落盘。

备份：当前上传的 FINAL_FULL_HISTORY.bundle 能恢复主线与整理源码，但缺少
ARCHIVE.md 中六个 IMP/VFY/RLS 的精确 Subject/Delivery 对象。Web 从既有
附件恢复了 VFY/RLS 和 Status 的补充 bundle，IMP 两个精确对象尚需补入。
只在**独立本地 bare 备份库**读取历史 PR head（例如 #5/#9/#10/#11）或精确
SHA，不更改远程分支/PR。实际读回必须等于 ARCHIVE 表中的准确值；同树的新
main 提交不能替代旧 Subject。必要时使用已有授权的 Git 只读 fetch；失败就明确
报告备份缺失，不伪称全历史已保全。

给所需根添加本地备份 refs 后生成 bundle，克隆到另一个空对象库，逐个执行
`git cat-file -e <SHA>^{commit}`、`git rev-list --objects --missing=print <roots>`
及 `git fsck --full --strict`。同时恢复一次清理前树和 Status 最终树，确认文件/mode。
本地 archive refs 不推送 GitHub。补充 bundle 不包含旧 PRE_CLEANUP 文件，也不
等于该旧文件的 SHA；不要再声称它已找到。归档校验清单记录每个所需根与实际结果。

最后更新 Handoff 时先提交再验证，避免已经验证后又增加源码 SHA；也可保持本
Handoff 为阶段说明，只在 PR 写最终交付身份。日志、备份、失败轨迹均在仓库外。

## 目标

完成统一样式和清理后的最后真实验证。复用 Web 修复，不再运行旧的七阶段开发 Goal、旧 RLS S4/E4 或40单元原生留痕任务。用户手动 Client 反馈不作为伪造证书，也不阻塞此轮。

1. 核对当前 Spec、有效 Case ID/Expected 和历史备份；不要重新导入被清理的几百份过程文件。
2. 准备现有 Python 与 OS 沙箱，检查 macOS sandbox-exec 或 Linux bwrap 真正可激活；不安装依赖、不使用无沙箱 fallback。缓存目录已有两个固定真实项目 Git 对象；缺少时准确报告，不能伪造通过。
3. 在 clean exact SHA 上只执行一次 `tools/validate.py --profile e2e --source-sha <SHA> --project-cache <缓存目录> --json-out <源码树外路径>/e2e.json`。它已包含结构、普通/严格回归、固定案例、安装边界和两条 CTX→RLS 链，不必先重复 full/strict/private/fixed 多层入口。
4. 基于真实失败修复第一个问题；不删除失败记录、不删 Case、不降低 Expected、不加 skip。只修改本轮允许的测试/样式/通用工具，发现领域逻辑问题需单独说明。代码变化后建立新准确提交，再对最终 SHA 跑一次所需完整验收。
5. 检查每个 Skill 按统一标题/命令/参数格式可读；主要操作流程不缩水，RLS 无生产效果，VFY 真实 OS containment。无法在工具中验证的主观观感由维护者确认，不填造运行轨迹。
6. 输出紧凑结果：最终 SOURCE_SHA、tree、每阶段实际测试数、全仓唯一 ID、零 skip/expectedFailure、两项目实际恢复与清理状态、REAL_TARGET_EFFECTS=0。原始日志、失败轨迹、源快照和摘要打包放仓库外；不要把新一轮100个报告再次回填仓库。
7. 更新同一 Draft PR 的摘要和必要的简短 Handoff，交 Web 做最终差异/证据审查，不自签独立 ACCEPTED，不合并。最终统一一次合入 main 由 Maintainer 决定。

成功：`MAINTENANCE_E2E = PASS`；存在无法恢复的真实阻塞：`MAINTENANCE_E2E = HARD_BLOCKED`，附第一个准确失败和可恢复位置。不得以测试计数变少、缺历史过程文件或暂停原生留痕为理由恢复已明确退役的流程。
