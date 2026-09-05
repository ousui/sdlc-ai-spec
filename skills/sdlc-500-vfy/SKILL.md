---
name: sdlc-500-vfy
description: 显式调用时，从准确上游 Artifact 编译完整交付范围和不可变实施结果，执行或复核验证方法，形成产品结论、返工记录与可信 VFY Gate。
disable-model-invocation: true
---

# VFY 验证与确认

从显式调用到结束保持 Exclusive Skill Execution。不得调用上下游兄弟 Skill、安装依赖、把 branch/tag/PR/latest/current 当作 Subject、把 Artifact ready 当作产品 pass，或自动进入 RLS。

正式入口为 `scripts/runtime.py`，并通过共享 `scripts/sdlc_skill_interface.py`、`references/interface.json`、`decision_policy` 与 `write_policy` Contract 解析命令、决策和写入授权。支持 `auto/create/run/revise/check/help/version/commands/examples`。

`create` 和 `revise` 的持久化路径必须从 repeatable `--input/-i` 读取准确 REQ/DSN/PLN/IMP Result、VFY Return、RLS Issue 或 Exception Reference，再通过 ArtifactStore、Lifecycle Query、Current completed Claim 和 Frozen Authority 编译完整 Candidate。stdin JSON 只能作为 Method、执行环境和人工输入提示，不能覆盖权威 Scope、Subject、Target、Control 或 Exception。

每个 Subject 必须属于完整 Current terminal IMP Result Set，并绑定 Current completed Claim、冻结 IMP Revision、Binding Lineage、Attempt、Result Digest 和连续有效依赖链。每个 Target 来自全部权威 VFO；只有合法 fallback 时才使用 AC 和 Goal。

Method Type 仅为 `inspection/analysis/demonstration/test`；`automated/manual/hybrid` 是 Execution Mode。自动命令只能使用冻结的正向 deterministic policy，在隔离副本中执行，无 Shell、inline arbitrary code、网络、依赖安装或 Git 写。人工/Hybrid Method 必须等待与 Method Contract 身份一致的真实评价者，并提供场景、预期、范围、RFC 3339 时间和不可变 Evidence Reference。

Method Result、Target Conclusion、`CON-VER`、`CON-VAL`、Product Result、Artifact Status、Artifact Gate 与 RLS readiness 相互独立。准确记录产品 fail 的 Artifact 可以 Gate pass；只有有效 Exception 才能形成 `ready_with_exception/pass_with_exception`。early-stop、pending 或 unresolved Return/Control 永不进入 RLS。

`check` 仅接受准确持久化 VFY Reference，通过只读 Store 重新验证 Primary、VFY-STATE、Manifest、Current Subject 和 Lifecycle Projection，前后项目与 Store 字节必须一致。生产 Runtime 不读取 `docs/**`。
