---
name: sdlc-300-pln
description: 创建、修订和检查交付计划 PLN Artifact，将完整 REQ/DSN 范围转化为稳定 Work Item 与生命周期绑定。
disable-model-invocation: true
---

# SDLC 300 Plan

## 用户入口

显式使用：

```text
/sdlc-300-pln
```

支持：

```text
auto
create
revise --reference PLN-...@1
check --reference PLN-...@1
--input / -i REQ-...@1       # 可重复
--input / -i DSN-...@1       # 可重复
help / -h / --help
version / -V / --version
commands / --commands
examples / --examples
```

## 共享接口绑定

- 通用参数、冲突检查和元命令入口：`scripts/sdlc_skill_interface.py`
- 本 Skill 命令、版本和示例：`references/interface.json`
- `decision_policy` 默认 `user`
- `write_policy` 默认 `auto`，只覆盖标准项目内 ArtifactStore 写入

元命令只读取 bundled interface，不扫描项目、不初始化 Store，也不产生写入。

## 默认工作流

1. 解析唯一 Project Root、准确 PLN Reference 和重复 `--input/-i`；
2. 只读解析 frozen REQ/DSN Scope Input 与允许的 Return/Issue Control Input；
3. 聚合 Delivery Scope、下游 Applicability 和全部权威义务；
4. 生成稳定 `WI-NNN`，每个 Work Item 只归属 IMP、VFY 或 RLS；
5. 校验 Scope Token、来源、约束、依赖图、资源串行链、完成条件和预期证据；
6. 通过 `skills/sdlc-300-pln/scripts/runtime.py` 执行确定性构建、验证、Gate 和 ArtifactStore 操作；
7. 通过 Lifecycle Query 投影最早且依赖已满足的 Work Item，并使用准确绑定 `<PLN-ID>@<Revision>#WI-NNN`；
8. 输出简明 Plan 摘要、阻塞项以及唯一下一动作或全部并行候选。

## 决策和写入

- PLN 只有在上游适用性为 `required` 时分配 Artifact；
- `n/a / waived` 返回完成且 `artifact=null`；`pending` 不分配 Artifact；
- `decision_policy=user` 为默认值；真实交付取舍、责任角色、Exception 和 Waiver 不得由模型静默承诺；
- `write_policy=auto` 只授权标准项目内 `.sdlc/store.sqlite3` 写入；
- 不执行实现、验证或发布，不写源码计划文件，不维护 Work Item 实时状态；
- `check` 绝对只读。

## 执行

```text
python3 <plugin-root>/skills/sdlc-300-pln/scripts/runtime.py [arguments] < request.json
```

- `summary`：默认中文摘要；
- `json`：单个结构化结果；
- `debug`：参数归一化和完整结果，不泄露 Secret。

## 严格边界

- Runtime 只读取 bundled Contract 与项目内 ArtifactStore；
- 不读取开发期 `docs/**`、测试或 Agent 配置；
- 不调用兄弟 Skill；
- 不直接 SQL 或复制 Store Schema；
- 不使用 `latest/current` 或标题相似度选择 Authority；
- 不自动进入 IMP、VFY 或 RLS；
- 不记录真实 Secret、Token、密码或私钥。
