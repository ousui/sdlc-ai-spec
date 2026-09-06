---
name: sdlc-200-dsn
description: 创建、修订和检查设计 DSN Artifact Set；自动分析 REQ、项目基线和 16 个设计领域，仅在真实设计决策时请求用户选择。
disable-model-invocation: true
---

# SDLC 200 · 设计（DSN）

## 适用范围

从完整 REQ Scope 构造 DSN Artifact Set，承接全部设计义务；16 个 Domain 是私有契约，不是独立 Skill。 内部 Evidence ID、Digest、Manifest 与 Invocation 由 Skill 整理，用户无需手填内部 JSON。

```text
/sdlc-200-dsn
/sdlc-200-dsn create -i REQ-20260901090000-01@1
/sdlc-200-dsn create --input=REQ-20260901090000-01@1 --input=REQ-20260901090000-02@1
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
| `auto` | 根据唯一工作区、REQ Scope、已有 DSN 和请求意图自动选择 create、revise 或 check。 | 是，须满足本阶段授权 |
| `create` | 基于一个或多个准确 frozen REQ 创建 DSN Artifact Set。 | 是，须满足本阶段授权 |
| `revise` | 修订准确 DSN Revision；open 原地修订，frozen 创建新 Revision。 | 是，须满足本阶段授权 |
| `check` | 严格只读检查准确 DSN Revision 和完整 Member closure。 | 否 |
| `help` | 显示用途、重复输入参数、默认行为和写入边界。 | 否 |
| `version` | 显示 Skill Version 与 Interface Contract。 | 否 |
| `commands` | 列出本 Skill 支持的命令。 | 否 |
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
| `--input` | `-i` | 可重复；完整准确 REQ Scope 及允许的 Control Input |

`--` 后为请求正文，不是新增开关。help 支持 `-h`，version 支持 `-V`；其他兼容别名以共享 parser 为准。多个工作区、Revision 或操作均不猜选。

## 执行流程

1. 解析唯一 Project Root、准确 DSN Reference 和重复 `--input/-i`；
2. 无显式输入时，通过 Lifecycle Query 发现唯一可用 REQ；多个候选由用户选择；
3. 只读解析 frozen CTX、REQ、VFY Return 或 RLS Issue Authority；
4. 读取完成设计所需的最小项目基线，将可证明事实登记为 observed / referenced；
5. 仅在设计边界、共享或拆分、关键方案、风险接受、Waiver、法律适用性或 Final Confirmation 无唯一答案时请求用户决定；
6. 按 `references/200-dsn-spec.md` 和 16 个 bundled Domain Contract 构造父 DSN Artifact Set；
7. 通过 `scripts/runtime.py` 执行确定性 Builder、Domain Validator、Manifest 闭包、ArtifactStore 和 Gate；
8. 输出简明设计摘要、Domain 状态、阻塞项和唯一下一动作。

一个 DSN Revision 包含：

- primary Canonical Markdown；
- 每个 `required` Domain 的 `DOM-*` Member；
- Supporting Members；
- 完整 Manifest-Member closure。

16 个 Domain 是本 Skill 的私有 Contract，不是可单独调用的 Skill。`DOM-510` 在 DSN 存在时固定为 `required`。

## 输出与完成条件

`summary` 默认只呈现事实、准确 Artifact、Gate、已执行写入、阻塞和下一动作。`json` 只返回正式 Runtime 的结构化结果，不添加进度文本、不改写字段或说明；调试信息不混入 JSON。`debug` 展示有界诊断，先脱敏。

输出 DSN 摘要、Domain 状态、Gate、阻塞和唯一下一动作。REQ 缺失、冲突或不可实现时返回 REQ，不在设计中静默改变需求。DOM-510 固定 required；required Domain 必须具有 Member 和完整 Manifest closure。

## 资源索引

- 先读 [运行契约](references/contract.md) 和 [命令定义](references/interface.json)。
- 执行入口：[runtime](scripts/runtime.py)；共用参数：`scripts/sdlc_skill_interface.py` 与 [共享接口](../_shared/contracts/skill-interface.md)。
- [独占执行约定](../_shared/contracts/skill-execution.md)；仅在处理相应业务对象时按契约读取 bundled references/assets，不整包加载。
