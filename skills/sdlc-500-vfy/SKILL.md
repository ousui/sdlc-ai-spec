---
name: sdlc-500-vfy
description: 显式调用时，从准确上游 Artifact 编译完整交付范围和不可变实施结果，执行或复核验证方法，形成产品结论、返工记录与可信 VFY Gate。
disable-model-invocation: true
---

# SDLC 500 · 验证与确认（VFY）

## 适用范围

从完整 Current IMP Result Set 编译验证范围，执行或复核方法，分别形成产品结论、返工与可信 Artifact Gate。 内部 Evidence ID、Digest、Manifest 与 Invocation 由 Skill 整理，用户无需手填内部 JSON。

```text
/sdlc-500-vfy
/sdlc-500-vfy create -i PLN-20260904100000-01@1 -i IMP-20260904110000-01@1/RESULT-RES-001
/sdlc-500-vfy run -r VFY-20260904120000-01@1 -m VFM-001 -m VFM-002
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
| `auto` | 根据准确 Scope、当前 Subject Set 和已有 VFY 状态选择 create、run、revise 或 check。 | 是，须满足本阶段授权 |
| `create` | 从 repeatable exact input 编译 VFY Contract，并执行当前安全可执行 Method。 | 是，须满足本阶段授权 |
| `run` | 执行或记录当前 open Revision 中选定的 pending Method。 | 是，须满足本阶段授权 |
| `revise` | 基于新的权威 Subject 或 Control Input 创建新 Revision；无变化返回 NO_CHANGE。 | 是，须满足本阶段授权 |
| `check` | 从准确持久化 Reference 绝对只读复核 Scope、Subject、Evidence、Return 与 Gate。 | 否 |
| `help` | 显示用途、参数和副作用边界。 | 否 |
| `version` | 显示 Skill 与接口版本。 | 否 |
| `commands` | 列出全部命令及是否写入。 | 否 |
| `examples` | 显示准确 Reference 与 Method 选择示例。 | 否 |

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
| `--input` | `-i` | 可重复；准确 Scope、IMP Result 和 Control/Exception 引用 |
| `--method` | `-m` | 可重复；run 选择的准确 `VFM-NNN` |

`--` 后为请求正文，不是新增开关。help 支持 `-h`，version 支持 `-V`；其他兼容别名以共享 parser 为准。多个工作区、Revision 或操作均不猜选。

## 执行流程

1. 先归一化命令；create/revise 从重复 `--input/-i` 读取准确 REQ/DSN/PLN/IMP Result、VFY Return、RLS Issue 或 Exception Reference。
2. 通过 ArtifactStore、Lifecycle Query、Current completed Claim 和 Frozen Authority 编译完整 Candidate。stdin 只表达 Method、执行环境和人工提示，不能覆盖权威 Scope、Subject、Target、Control 或 Exception。
3. 每个 Subject 绑定 Current completed Claim、冻结 IMP Revision、Binding Lineage、Attempt、Result Digest 和连续有效依赖链；必须覆盖完整 Current terminal IMP Result Set。Target 来自全部权威 VFO；只有合法 fallback 才使用 AC 和 Goal。
4. Method Type 为 `inspection/analysis/demonstration/test`；`automated/manual/hybrid` 是独立的 Execution Mode。自动命令仅使用冻结的正向 deterministic policy，在 OS 隔离副本中执行；无 Shell、inline arbitrary code、网络、安装或 Git 写入。能力不足不算测试通过。
5. Manual/Hybrid 等待与 Method Contract 身份一致的真实评价者，绑定场景、预期、范围、RFC 3339 时间和不可变 Evidence Reference。
6. 分别计算 Method Result、Target Conclusion、`CON-VER`、`CON-VAL`、Product Result、Artifact Status、Artifact Gate 与 RLS readiness，不以一个字段替代另一个。
7. `check` 只读准确持久化 Revision，重验 Primary、VFY-STATE、Manifest、Current Subject 与 Lifecycle Projection；Store 和项目字节必须不变。

## 输出与完成条件

`summary` 默认只呈现事实、准确 Artifact、Gate、已执行写入、阻塞和下一动作。`json` 只返回正式 Runtime 的结构化结果，不添加进度文本、不改写字段或说明；调试信息不混入 JSON。`debug` 展示有界诊断，先脱敏。

准确记录产品 fail 的 Artifact 可以 Gate pass；有效 Exception 才能产生 ready_with_exception/pass_with_exception。early-stop、pending 或 unresolved Return/Control 永不进入 RLS。缺失能力、输入或人工观察时明确停止，不伪造 PASS。

## 资源索引

- 先读 [运行契约](references/contract.md) 和 [命令定义](references/interface.json)。
- 执行入口：[runtime](scripts/runtime.py)；共用参数：`scripts/sdlc_skill_interface.py` 与 [共享接口](../_shared/contracts/skill-interface.md)。
- [独占执行约定](../_shared/contracts/skill-execution.md)；仅在处理相应业务对象时按契约读取 bundled references/assets，不整包加载。
