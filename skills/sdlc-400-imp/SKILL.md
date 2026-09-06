---
name: sdlc-400-imp
description: 显式调用时，领取一个准确实施 Binding，保存真实 Baseline，按已批准 Method 在 Scope 内实施，并生成可读回的不可变 Result 与局部检查记录。
disable-model-invocation: true
---

# SDLC 400 · 实施（IMP）

## 适用范围

领取一个准确实施 Binding，保存真实 Baseline，并在 Claim Scope 内执行已批准 Method，产生不可变 Result。 内部 Evidence ID、Digest、Manifest 与 Invocation 由 Skill 整理，用户无需手填内部 JSON。

```text
/sdlc-400-imp
/sdlc-400-imp create -b PLN-20260903090000-01@1#WI-001 --owner executor-a
/sdlc-400-imp revise -r IMP-20260903100000-01@1 -i VFY-20260903110000-01@1#RET-001 --owner executor-a
```

## 约定与边界

从显式调用到结束保持 Exclusive Skill Execution，不调用兄弟 Skill，不传递授权。只使用本 Skill 与共享 Runtime/ArtifactStore；不直接 SQL、不复制 Store Schema、不使用文件或数据库 fallback，不读取开发期文档、测试或 Handoff。

事实区分 observed / referenced / confirmed；缺口进入 Open Items，不猜测。Authority 使用准确数字 Revision，不使用 branch/tag/PR/latest/current 或标题相似度。`decision_policy=user` 默认由用户决定多解业务问题；model/experiment 需明确授权，实验还需范围、指标、成本和停止条件。

`write_policy` 不替代业务批准、Exception、Final Confirmation 或独立效果授权。check/inspect 不修复、不初始化、不创建旁车。Git、远端、安装、项目外写入不属于本 Skill 的默认许可；真实 Secret 不进入 Artifact、日志或输出。

IMP 的 auto 仅允许准确 Baseline 和 Claim Scope 内项目写入；confirm 在首次产品写入前确认准确摘要；deny 只允许只读检查和 Method Preview。决策策略不授权改变 REQ/DSN/PLN。

## 子命令

以 [interface.json](references/interface.json) 为命令 Authority；元命令 help/version/commands/examples 不扫描项目、不读取业务 stdin、不打开 Store。

| 子命令 | 职责 | 可能写入 |
|---|---|---|
| `auto` | 根据唯一准确 Binding、Current Claim 和合法 Rework 选择操作。 | 是，须满足本阶段授权 |
| `create` | 准确领取 Binding，保存 Baseline 与 Method，在 Scope 内实施并形成 Result。 | 是，须满足本阶段授权 |
| `revise` | 继续 active/open Attempt，或依据合法 Rework 创建同 Artifact 的新 Attempt。 | 是，须满足本阶段授权 |
| `check` | 严格只读复核 Context、Binding、Claim、Result、Dependency 和 Gate。 | 否 |
| `abandon` | 校验 Owner、Attempt 和 Revision，先终止 open Revision，再终止 active Claim。 | 是，须满足本阶段授权 |
| `help` | 显示命令、参数及 Scope 内写入边界。 | 否 |
| `version` | 显示 Skill 和 Interface 版本。 | 否 |
| `commands` | 列出全部命令及副作用说明。 | 否 |
| `examples` | 显示准确 Binding 与 Artifact Reference 的使用示例。 | 否 |

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
| `--input` | `-i` | 可重复；准确前驱、上游或 Rework，保持首次出现顺序 |
| `--binding` | `-b` | 准确 `PLN@Revision#WI-NNN`，或合法直达的 REQ/DSN Revision |
| `--owner` | `—` | 稳定执行身份；缺省读取 `SDLC_EXECUTOR_TOKEN`，不代表额外权限 |

`--` 后为请求正文，不是新增开关。help 支持 `-h`，version 支持 `-V`；其他兼容别名以共享 parser 为准。多个工作区、Revision 或操作均不猜选。

## 执行流程

1. 解析唯一 Project Root 和 Binding。PLN required 时必须选中一个 Target Phase=IMP 的准确 WI。
2. 从 ArtifactStore 读取准确 PLN 的真实 Context、Scope、依赖和上游链。IMP Context 必须等于该 CTX Reference。
3. 从现有源码和上游 Contract 形成 Method；读取 [Runtime Contract](references/contract.md)。
   Agent 整理内部 Payload，用户无需填写 JSON、Attempt、Digest 或内部 Evidence ID。
4. 完成七项 Consideration 和连续语义 Step。缺少业务、设计、计划决定时分别返回 REQ、DSN、PLN。
5. Runtime acquire 正式 Claim；按 Claim 的准确 Artifact ID / Revision Reservation
   物化 open Payload，持久化完整工作区 Baseline 和 Method，再独立读回。
   Claim 前候选变化必须另带完整 Baseline / Candidate Evidence；Runtime 在 acquire 前
   核对当前 Candidate 与 Scope，在 open Payload 读回后只恢复声明差异，再从 Baseline
   重放 Method，并要求新 Result 与 Candidate 完全一致，不能倒签既有 Patch。
6. Runtime 在首次产品写入前再次检查 Owner、Claim、Scope 和 Baseline。
   仅执行声明的有内容前置条件的操作，保留用户已有修改。
7. 保存完整 Snapshot Members、每 Resource 一行的 Result、真实执行的局部 Checks 和 Evidence。
8. 向用户展示 Outcome、Baseline、Approach、Changed Scope、Result、Checks 和待确认项。
   把针对当前完整结果的自然语言批准映射为 Final Confirmation。
9. 缺少或陈旧确认保持 open/waiting_input；freeze 成功后才 complete Claim。
   complete 临时失败时只重试终结，保留 frozen Payload。
10. check 全程只读。abandon 先检查准确 Owner/Attempt/Revision，先 abandon Revision 再
    CAS Claim，并分别保存预期 Owner 与实际终结 Actor；幂等重试还要匹配原 Reason。

固定 Consideration 顺序：

1. Calculation Rules
2. Decision Rules
3. State Transitions
4. Algorithm & Invariants
5. Data Contract & Transformation
6. Boundary & Failure Handling
7. Effects & Consistency

required 必须有 Step 和固定方法块；n/a 有客观理由；waived 有已批准 Exception。
pending 不可通过 Readiness 或 Gate。Step 按语义动作、事务和失败边界组织。

## 输出与完成条件

`summary` 默认只呈现事实、准确 Artifact、Gate、已执行写入、阻塞和下一动作。`json` 只返回正式 Runtime 的结构化结果，不添加进度文本、不改写字段或说明；调试信息不混入 JSON。`debug` 展示有界诊断，先脱敏。

局部 Checks 只表示 VFY ready。Artifact frozen 且 Current Claim completed 才可交给 VFY。
不宣称完整产品验证、发布通过或 RLS 可发布；不自动执行下一阶段。

不执行网络、安装依赖、Git commit/push/merge/tag/ref 操作、外部效果或 Scope 外写入。
共享 Effect Authorization 只用于外部发布效果，不能把它转换成 IMP 的本地或越界授权。
遇到产品执行中断，保留准确 Baseline、已持久化 Method 和现场，停止并明确恢复或 abandon；
不得从现场变化倒签 Claim、静默重放或推断完成。

## 资源索引

- 先读 [运行契约](references/contract.md) 和 [命令定义](references/interface.json)。
- 执行入口：[runtime](scripts/runtime.py)；共用参数：`scripts/sdlc_skill_interface.py` 与 [共享接口](../_shared/contracts/skill-interface.md)。
- [独占执行约定](../_shared/contracts/skill-execution.md)；仅在处理相应业务对象时按契约读取 bundled references/assets，不整包加载。
