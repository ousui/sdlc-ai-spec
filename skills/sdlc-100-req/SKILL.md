---
name: sdlc-100-req
description: 显式创建、修订或严格只读检查需求 REQ；裸调用会自动解析项目、CTX、操作和标准写入。
disable-model-invocation: true
---

# SDLC 100 · 需求（REQ）

## 适用范围

把用户需求和准确 frozen CTX 转为有来源、范围、需求项与验收标准的 REQ；不替业务方决定含糊需求。 内部 Evidence ID、Digest、Manifest 与 Invocation 由 Skill 整理，用户无需手填内部 JSON。

```text
/sdlc-100-req
/sdlc-100-req create -- 让已授权用户导出当前筛选结果
/sdlc-100-req --create -p /workspace/project
```

## 约定与边界

从显式调用到结束保持 Exclusive Skill Execution，不调用兄弟 Skill，不传递授权。只使用本 Skill 与共享 Runtime/ArtifactStore；不直接 SQL、不复制 Store Schema、不使用文件或数据库 fallback，不读取开发期文档、测试或 Handoff。

事实区分 observed / referenced / confirmed；缺口进入 Open Items，不猜测。Authority 使用准确数字 Revision，不使用 branch/tag/PR/latest/current 或标题相似度。`decision_policy=user` 默认由用户决定多解业务问题；model/experiment 需明确授权，实验还需范围、指标、成本和停止条件。

`write_policy` 不替代业务批准、Exception、Final Confirmation 或独立效果授权。check/inspect 不修复、不初始化、不创建旁车。Git、远端、安装、项目外写入不属于本 Skill 的默认许可；真实 Secret 不进入 Artifact、日志或输出。

标准 ArtifactStore 写入按 auto/confirm/deny 处理；auto 封装 `artifact_store_write` confirmation，不伪造业务/最终批准。REQ check 的缺 Store 结果应由正式 Runtime 返回，不能以 Agent 自述预检替代。

## 子命令

以 [interface.json](references/interface.json) 为命令 Authority；元命令 help/version/commands/examples 不扫描项目、不读取业务 stdin、不打开 Store。

| 子命令 | 职责 | 可能写入 |
|---|---|---|
| `auto` | 根据唯一工作区、CTX、已有 REQ 和请求意图自动选择 create、revise 或 check。 | 是，须满足本阶段授权 |
| `create` | 基于准确 frozen CTX 创建需求 REQ。 | 是，须满足本阶段授权 |
| `revise` | 修订准确 REQ Revision；open 原地修订，frozen 创建新 Revision。 | 是，须满足本阶段授权 |
| `check` | 严格只读检查准确 REQ Revision。 | 否 |
| `help` | 显示用途、默认行为、公共参数和写入边界。 | 否 |
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

`--` 后为请求正文，不是新增开关。help 支持 `-h`，version 支持 `-V`；其他兼容别名以共享 parser 为准。多个工作区、Revision 或操作均不猜选。

## 执行流程



1. 当前唯一项目存在准确 frozen CTX，但没有 REQ：`create`；
2. 用户当前请求明确提出新需求，且不存在同一需求 Lineage：`create`；
3. 唯一 materialized open REQ：`revise`；
4. 唯一 frozen REQ 且请求没有变更意图：`check`；
5. 唯一 frozen REQ 且请求明确变更：`revise`；
6. 多个 CTX、REQ、Revision 或合法操作：请求用户选择，不按标题相似度、`latest` 或 `current` 猜测。

`project_root=auto` 只接受唯一现存工作区。`artifact_reference=auto` 只在候选准确且唯一时使用；否则展示准确 Reference 列表。

在提交 Runtime 前，从当前用户请求、会话中已确认事实、准确 frozen CTX、获授权 VFY/RLS Control Input 及最小项目证据构造候选 REQ：

- 保留原始需求语义和来源；
- 可证明内容登记为 observed / referenced；
- 业务范围、优先级、取舍和验收语义存在多种合法解释时，按 `decision_policy` 处理；
- 缺口形成 Open Item，不伪造 Requirement 或 Acceptance Criterion；
- 用户不需要提供内部 Source ID、Goal ID、Requirement ID 或 JSON 表格。

只有参数完整、准确 frozen CTX 已唯一解析、必要业务决策已完成后，才构造 `sdlc-ai-spec/runtime-invocation/v1` 并调用：

```text
python3 <plugin-root>/skills/sdlc-100-req/scripts/runtime_final.py < request.json
```

- create/revise 使用共享 ArtifactStore，不直接 SQL、不创建私有 Schema；
- check 严格只读，不 initialize、不修复、不创建旁车文件；
- 不调用 CTX 或其他业务 Skill，只消费共享 Authority 接口；
- 不把写入成功描述为 Gate 通过；
- 底层错误转换为用户可理解的决策或下一动作，默认不暴露内部 Envelope。

## 输出与完成条件

`summary` 默认只呈现事实、准确 Artifact、Gate、已执行写入、阻塞和下一动作。`json` 只返回正式 Runtime 的结构化结果，不添加进度文本、不改写字段或说明；调试信息不混入 JSON。`debug` 展示有界诊断，先脱敏。

`output=summary` 默认展示：需求状态、准确 Artifact、上游 CTX、主要来源、Gate、Open Items、实际写入和唯一下一动作。

`output=json` 只返回结构化结果；`output=debug` 才展示参数归一化、Source/Evidence、内部 Invocation 和 Runtime Result，且不得泄露 Secret。

`action_required / blocked / failed` 时立即停止；不自动进入 DSN、PLN 或其他阶段。

## 资源索引

- 先读 [运行契约](references/contract.md) 和 [命令定义](references/interface.json)。
- 执行入口：[runtime](scripts/runtime_final.py)；共用参数：`scripts/sdlc_skill_interface.py` 与 [共享接口](../_shared/contracts/skill-interface.md)。
- [独占执行约定](../_shared/contracts/skill-execution.md)；仅在处理相应业务对象时按契约读取 bundled references/assets，不整包加载。
