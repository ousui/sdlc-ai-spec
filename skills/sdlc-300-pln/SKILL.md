---
name: sdlc-300-pln
description: 创建、修订和检查交付计划 PLN Artifact，将完整 REQ/DSN 范围转化为稳定 Work Item 与生命周期绑定。
disable-model-invocation: true
---

# SDLC 300 · 交付计划（PLN）

## 适用范围

把完整 REQ/DSN 范围转为稳定 Work Item、依赖与生命周期绑定；不执行实施、验证或发布。 内部 Evidence ID、Digest、Manifest 与 Invocation 由 Skill 整理，用户无需手填内部 JSON。

```text
/sdlc-300-pln
/sdlc-300-pln create -i DSN-20260901090000-01@1
/sdlc-300-pln revise -r PLN-20260901130000-01@1 -i DSN-20260901090000-01@1
```

## 约定与边界

从显式调用到结束保持 Exclusive Skill Execution，不调用兄弟 Skill，不传递授权。只使用本 Skill 与共享 Runtime/ArtifactStore；不直接 SQL、不复制 Store Schema、不使用文件或数据库 fallback，不读取开发期文档、测试或 Handoff。

事实区分 observed / referenced / confirmed；缺口进入 Open Items，不猜测。Authority 使用准确数字 Revision，不使用 branch/tag/PR/latest/current 或标题相似度。`decision_policy=user` 默认由用户决定多解业务问题；model/experiment 需明确授权，实验还需范围、指标、成本和停止条件。

`write_policy` 不替代业务批准、Exception、Final Confirmation 或独立效果授权。check/inspect 不修复、不初始化、不创建旁车。Git、远端、安装、项目外写入不属于本 Skill 的默认许可；真实 Secret 不进入 Artifact、日志或输出。

标准 auto 写入只限当前项目的 ArtifactStore；本阶段不自动执行后续阶段。

## 子命令

以 [interface.json](references/interface.json) 为命令 Authority；元命令 help/version/commands/examples 不扫描项目、不读取业务 stdin、不打开 Store。

| 子命令 | 职责 | 可能写入 |
|---|---|---|
| `auto` | 根据准确 Scope、PLN 适用性和已有 Plan 自动选择 create、revise 或 check。 | 是，须满足本阶段授权 |
| `create` | 基于一个或多个完整 frozen REQ/DSN 创建 Plan Artifact。 | 是，须满足本阶段授权 |
| `revise` | 修订准确 Plan Revision；open 原地修订，frozen 有变化时创建新 Revision。 | 是，须满足本阶段授权 |
| `check` | 严格只读检查 Plan、Work Item、依赖、覆盖与 Gate。 | 否 |
| `help` | 显示用途、输入参数和写入边界。 | 否 |
| `version` | 显示 Skill Version 与 Interface Contract。 | 否 |
| `commands` | 列出支持的命令。 | 否 |
| `examples` | 显示常用调用示例。 | 否 |

## 参数

先按共享 Parser 归一化公共参数，再由本 Skill 注册扩展。公共参数描述不意味着旧 JSON Runtime 可直接接受所有 CLI 开关：CTX/REQ 先构造标准 Invocation，再通过 stdin 调用其正式入口；其他阶段使用本 Skill 的 CLI。

| 参数 | 短参数 | 语义／默认值 |
|---|---|---|
| `--command` | `-c` | `auto`；也可直接写子命令，兼容 `--operation/-o` |
| `--project-root` | `-p` | 宿主提供的唯一当前工作区；多个项目时选择，不猜测 |
| `--reference` | `-r` | 准确 `TYPE-ID@数字Revision`；修改/检查时按命令要求提供 |
| `--decision-policy` | `-d` | `user`（默认）/ `model` / `experiment`；后两者需要明确授权 |
| `--write-policy` | `-w` | `auto`（默认）/ `confirm` / `deny`；仅约束本阶段允许的标准写入 |
| `--dry-run` | `-n` | 默认 `false`；不生成权威完成结论，不替代 check |
| `--output` | `-f` | `summary`（默认）/ `json` / `debug` |
| `--input` | `-i` | 可重复；完整准确 REQ/DSN Scope 及允许的 Control Input |

`--` 后为请求正文，不是新增开关。help 支持 `-h`，version 支持 `-V`；其他兼容别名以共享 parser 为准。多个工作区、Revision 或操作均不猜选。

## 执行流程

1. 解析唯一 Project Root、准确 PLN Reference 和重复 `--input/-i`；
2. 只读解析 frozen REQ/DSN Scope Input 与允许的 Return/Issue Control Input；
3. 聚合 Delivery Scope、下游 Applicability 和全部权威义务；
4. 生成稳定 `WI-NNN`，每个 Work Item 只归属 IMP、VFY 或 RLS；
5. 校验 Scope Token、来源、约束、依赖图、资源串行链、完成条件和预期证据；
6. 通过 `skills/sdlc-300-pln/scripts/runtime.py` 执行确定性构建、验证、Gate 和 ArtifactStore 操作；
7. 通过 Lifecycle Query 投影最早且依赖已满足的 Work Item，并使用准确绑定 `<PLN-ID>@<Revision>#WI-NNN`；
8. 输出简明 Plan 摘要、阻塞项以及唯一下一动作或全部并行候选。

- PLN 只有在上游适用性为 `required` 时分配 Artifact；
- `n/a / waived` 返回完成且 `artifact=null`；`pending` 不分配 Artifact；
- `decision_policy=user` 为默认值；真实交付取舍、责任角色、Exception 和 Waiver 不得由模型静默承诺；
- `write_policy=auto` 只授权标准项目内 `.sdlc/store.sqlite3` 写入；
- 不执行实现、验证或发布，不写源码计划文件，不维护 Work Item 实时状态；
- `check` 绝对只读。

## 输出与完成条件

`summary` 默认只呈现事实、准确 Artifact、Gate、已执行写入、阻塞和下一动作。`json` 只返回正式 Runtime 的结构化结果，不添加进度文本、不改写字段或说明；调试信息不混入 JSON。`debug` 展示有界诊断，先脱敏。

上游 required 时才分配 PLN；n/a/waived 返回完成且 artifact=null，pending 不分配。计划只描述稳定义务，不维护 WI 实时执行状态；查询展示唯一下一动作或全部并行候选。

## 资源索引

- 先读 [运行契约](references/contract.md) 和 [命令定义](references/interface.json)。
- 执行入口：[runtime](scripts/runtime.py)；共用参数：`scripts/sdlc_skill_interface.py` 与 [共享接口](../_shared/contracts/skill-interface.md)。
- [独占执行约定](../_shared/contracts/skill-execution.md)；仅在处理相应业务对象时按契约读取 bundled references/assets，不整包加载。
