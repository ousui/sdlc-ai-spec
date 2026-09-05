# Independent Web conformance review

只审查，不修改 main、七阶段源码、历史 Evidence、Workflow、发布元数据，不自动合并。读取最新 PR #11、准确 VALIDATED_SOURCE_SHA 和 DELIVERY_HEAD_SHA，不从 PR 文本或通过计数推断证据真实。

核对 main 基线祖先和允许 Diff；确认历史 IMP/VFY/RLS 树中非本包授权路径、Spec、Case Expected 和旧 Evidence 未改。独立查看 Status 准确引用与权限错误边界、JSON/summary/debug、multi-target selection。检查一次性项目与损坏 Store 前后字节/mode，不以 mock 覆盖替代真实 Store 证据。

重跑可用 portable gates；严格 VFY 记录需要真实 OS containment 而不是 capability-only PASS。核验八锁、Status 14 个唯一且实际执行的主测试、installed-copy 12 命令、全仓唯一测试 ID、零 skip/expectedFailure、每个 stdout/stderr/receipt 摘要、source SHA/tree、运行前后状态和首次归档脱敏。缺宿主能力的 Web 可审计完整 Client 归档，但不得写成独立执行了它。

全局 Handoff 应与实际阶段矩阵一致；历史 CTX 成功只能用于其准确范围。COMPATIBILITY.json 需恰有八 Skill/五载体，native candidate 须有七维真实安装和宿主轨迹，不能用 Python CLI 或合成 receipt 代替。验证器检查的是绑定，不能为 receipt 自述的 operator/reviewer 背书；审阅原始 trace 后才决定逐单元接受。

结果分别给出：

```text
WEB_CONFORMANCE_REVIEW = ACCEPTED | CHANGES_REQUIRED
VALIDATED_SOURCE_SHA = <exact>
RUNTIME_CONFORMANCE = PASS | FAIL
NATIVE_ACCEPTED_CELLS = <exact list, may be empty>
NATIVE_UNVERIFIED_CELLS = <exact list>
OPEN_BLOCKERS = <actual>
OPEN_MAJORS = <actual>
PR_MERGED = NO
```

Runtime 包可单独接受而 native 仍未完成，但绝不能称为三端正式兼容或产品发布批准。未经用户明确授权，不代替 Maintainer 决定分发仓库，也不把旧 closed/unmerged PR 重新合并。
