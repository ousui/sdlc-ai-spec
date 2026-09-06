# Client：同一分支的一次全流程验收

读取 PR 的当前交付 Head，fetch 后在独立干净 worktree 检出 `refactor/skill-unification-cleanup`。只处理该分支，不写 main，不重新合并旧 PR，不重写历史。先保存 SHA/tree 与工作树状态；发现非本轮已说明的并发变化时停止核对。

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
