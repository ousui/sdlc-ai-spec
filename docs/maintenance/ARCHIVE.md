# 开发历史与恢复索引

本轮删除的是当前检出树中的过程副本，不重写 Git 历史，不声称清除历史中的任何内容。有效设计、固定 Eval Plan、领域 Spec、Runtime Contract、真实安全回归与必要 Fixture 留在工作树。

## 恢复对象

| 内容 | 精确对象 |
|---|---|
| 清理前 main 与全部在库过程文件 | `9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9`，tree `d90e81a94e5b7b5628eb6849cef15bb3f96deb36` |
| Status 最终交付（未全部重放至 main） | `f15fefe15e5d5155ce319fe804447f31fa034bf4`，tree `5f6d1320428fb0040fef924e3b961bf63d8d1f19` |
| Status 最终 Web 接受 | PR #11 review `5124073264`，只接受该准确 source/delivery 对 |
| 已接受 RLS Subject / Evidence | `b790af812cd8d317675d264583711aed59e1460c` / `2db5b77288ea890f60ed7b07fc8e01b955ebaa13` |
| 已接受 VFY Subject / Evidence | `5ea3ba9aa7288021c4d99b14cff76ec0fc405841` / `46509eb6688df30e71ed094132b2d10e81ceb2ac` |
| IMP Subject / Delivery | `207a4a16bea8979faee0474cc43cb642cef1f655` / `86aaa04a0238d3151606073e89219eea0d60b7d3` |

本次提供仓库外 `PRE_CLEANUP_FULL_HISTORY.bundle`，SHA-256 `d91d71a824c576a534897c2b9573e235f9521bcefa4f5c0856a37b5adef1797a`。原完整 Status 审查包 `sdlc-pr11-status-path-review-f15fefe.zip` 的 SHA-256 为 `e5d06cd930ed398ff6879bdaaff60f647db927d2cb31e38a5049905f5c821d24`。备份须下载到持久存储；不要只依赖聊天沙箱路径永久可用。

```bash
git clone PRE_CLEANUP_FULL_HISTORY.bundle recovered-history
cd recovered-history
git show 9d9dbf8bc1b9241f80af53cdf5b0426fcbfe3ab9:docs/plugin-development/HANDOFF.md
# 对原始文件核验摘要；不得把旧 Manifest 套到已修改的当前 Handoff。
```

## 删除/迁移原则

- `work-items/*/evidence`、旧 Goal、原生候选、过程日志和每轮验证报告：由上表原始对象恢复；未来不再回填当前源码树。
- `work-items/sdlc-*/DESIGN.md` 与 `EVAL-PLAN.md`：保留准确原字节。历史正文中的 goal/evidence 相对引用按本索引到原始 Git 对象读取，不当作当前工作流。
- VFY 分类 Case 包装器：与主 80 Case 使用同一 harness/参数，删除重复执行层，主表与严格命令 Oracle 保留。
- RLS provisional Case 与 legacy CLI：最终真实 Store Case 已替代；所有独立安全回归仍保留。
- 旧 B/D/S 拓扑专用校验与 Observer/预收口脚本：退出当前执行路径；通用 exact-SHA、完整执行、失败与日志校验迁移到统一入口。
- REQ inherited TestCase：提取无 test 方法的 Fixture 类，原 Case 方法保留且不再多次执行。
- native 自动认证台账与其模拟证书测试：本轮明确移出门禁。长期库存检查继续存在，不删除实际 Runtime 测试。

文件级删除 SHA-256、字节数和替代说明随本次仓库外交付包提供；Git diff 是新增提交的精确路径清单。大量回归测试虽然名字含 repair/web，并不等于废物；授权、篡改、并发、路径与失败恢复测试不会为减少数量而删除。
