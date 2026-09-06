---
name: sdlc-status
description: 严格只读查询当前项目的 SDLC 状态、准确需求流转、阻塞项和下一动作；仅在用户显式调用时执行。
disable-model-invocation: true
---

# SDLC · 生命周期状态

## 适用范围

严格只读地展示准确 REQ 生命周期、阻塞与全部候选下一动作；Projection 不构成 Canonical Authority。 内部 Evidence ID、Digest、Manifest 与 Invocation 由 Skill 整理，用户无需手填内部 JSON。

```text
/sdlc-status
/sdlc-status list
/sdlc-status inspect --reference REQ-20260831190000-01@1
```

## 约定与边界

从显式调用到结束保持 Exclusive Skill Execution，不调用兄弟 Skill，不传递授权。只使用本 Skill 与共享 Runtime/ArtifactStore；不直接 SQL、不复制 Store Schema、不使用文件或数据库 fallback，不读取开发期文档、测试或 Handoff。

事实区分 observed / referenced / confirmed；缺口进入 Open Items，不猜测。Authority 使用准确数字 Revision，不使用 branch/tag/PR/latest/current 或标题相似度。`decision_policy=user` 默认由用户决定多解业务问题；model/experiment 需明确授权，实验还需范围、指标、成本和停止条件。

`write_policy` 不替代业务批准、Exception、Final Confirmation 或独立效果授权。check/inspect 不修复、不初始化、不创建旁车。Git、远端、安装、项目外写入不属于本 Skill 的默认许可；真实 Secret 不进入 Artifact、日志或输出。

有效 write_policy 永远为 deny；Graph、Frontier 和 Overall State 只是只读 Projection，不提供 Canonical Authority。

## 子命令

以 [interface.json](references/interface.json) 为命令 Authority；元命令 help/version/commands/examples 不扫描项目、不读取业务 stdin、不打开 Store。

| 子命令 | 职责 | 可能写入 |
|---|---|---|
| `auto` | 根据唯一工作区和 Artifact 状态自动选择 overview、list 或 inspect | 否 |
| `list` | 列出项目内全部准确 REQ Revision 候选及其状态 | 否 |
| `inspect` | 检查一个准确 REQ-...@数字Revision 的生命周期图 | 否 |
| `help` | 显示用途、命令、参数和写入边界 | 否 |
| `version` | 显示 Skill 与 Interface 版本 | 否 |
| `commands` | 列出全部命令及是否写入 | 否 |
| `examples` | 显示可复制的最小示例 | 否 |

## 参数

先按共享 Parser 归一化公共参数，再由本 Skill 注册扩展。公共参数描述不意味着旧 JSON Runtime 可直接接受所有 CLI 开关：CTX/REQ 先构造标准 Invocation，再通过 stdin 调用其正式入口；其他阶段使用本 Skill 的 CLI。

| 参数 | 短参数 | 语义／默认值 |
|---|---|---|
| `--command` | `-c` | `auto`；也可直接写子命令，兼容 `--operation/-o` |
| `--project-root` | `-p` | 宿主提供的唯一当前工作区；多个项目时选择，不猜测 |
| `--reference` | `-r` | 准确 REQ Revision；auto 带引用与 inspect 采用相同准确读回边界 |
| `--decision-policy` | `-d` | `user`（默认）/ `model` / `experiment`；后两者需要明确授权 |
| `--write-policy` | `-w` | 公共语法接受 auto/confirm/deny；本 Skill 强制有效值为 `deny` |
| `--dry-run` | `-n` | 默认 `false`；不生成权威完成结论，不替代 check |
| `--output` | `-f` | `summary`（默认）/ `json` / `debug` |

`--` 后为请求正文，不是新增开关。help 支持 `-h`，version 支持 `-V`；其他兼容别名以共享 parser 为准。多个工作区、Revision 或操作均不猜选。

## 执行流程

1. `project_root` 未指定时，使用宿主提供的唯一当前工作区；
2. 无 Store：说明尚未开始，推荐 `sdlc-000-ctx`；
3. 有 CTX、无活跃 REQ：说明上下文状态，推荐 `sdlc-100-req`；
4. 只有一个活跃 REQ：自动 inspect；
5. 多个活跃 REQ：列出准确 Revision，由用户选择；
6. 提供准确 `REQ-...@数字Revision`：直接 inspect。

不得根据标题、相似度、`latest` 或 `current` 猜选 Requirement。

仅在未绑定准确引用且 Store 真正不存在时显示 `not_started`。普通文件冲突、数据库目录、悬空链接或损坏 Store 失败关闭，不回退为成功空概览。准确引用必须在访问 Store 前校验。

存在 IMP 时，显示准确 Binding、Owner、Attempt、Current Claim 状态、Resource
Baseline/Result、Changed Scope 与 VFY 就绪性。历史 frozen Artifact 不代表当前完成；
只有 Current Claim 已完成且 Result、依赖链有效，才提供终端 IMP 作为 VFY 输入。
VFY Skill 未安装时明确说明；多个下一动作完整展示，由用户选择。
存在 VFY 时，另外显示 Product Result、Artifact Gate、Return Phase 与 RLS readiness，
不得把可信的失败记录显示为产品通过，也不得从 unresolved Return 进入 RLS。

## 输出与完成条件

`summary` 默认只呈现事实、准确 Artifact、Gate、已执行写入、阻塞和下一动作。`json` 只返回正式 Runtime 的结构化结果，不添加进度文本、不改写字段或说明；调试信息不混入 JSON。`debug` 展示有界诊断，先脱敏。

summary 展示状态和候选；json 返回一个结构化结果；debug 省略自由文本及 Secret。多个 REQ/Target 需要用户选择，不默认选第一个。只建议下一命令，不自动调用下一阶段。

## 资源索引

- 先读 [运行契约](references/contract.md) 和 [命令定义](references/interface.json)。
- 执行入口：[runtime](scripts/runtime.py)；共用参数：`scripts/sdlc_skill_interface.py` 与 [共享接口](../_shared/contracts/skill-interface.md)。
- [独占执行约定](../_shared/contracts/skill-execution.md)；仅在处理相应业务对象时按契约读取 bundled references/assets，不整包加载。
