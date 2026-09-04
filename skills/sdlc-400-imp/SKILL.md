---
name: sdlc-400-imp
description: 显式调用时，领取一个准确实施 Binding，保存真实 Baseline，按已批准 Method 在 Scope 内实施，并生成可读回的不可变 Result 与局部检查记录。
disable-model-invocation: true
---

# IMP 实施

从调用到结束遵守 [Exclusive Skill Execution](../_shared/contracts/skill-execution.md)。
不调用其他 Skill / Plugin，不读取开发文档，不重新解释上游决定。
运行时只使用本 Skill、共享 Runtime 与正式 Foundation。

## 入口

使用 scripts/runtime.py。公共参数经共享 scripts/sdlc_skill_interface.py 所用的
Parser 归一化；阶段参数由同一共享 Parser 的 Extension 注册。
命令和示例以 references/interface.json 为准：
auto、create、revise、check、abandon、help、version、commands、examples。

- --binding / -b：完整 PLN@Revision#WI，或允许直接实施的完整 REQ/DSN@Revision。
- --input / -i：可重复的准确前驱、上游或 Rework 引用，保持首次出现顺序。
- --owner：稳定执行身份；未提供时只读取 SDLC_EXECUTOR_TOKEN。
- --reference / -r：revise/check/abandon 的准确 IMP Revision。
- decision_policy 不能授权改变 Requirement、Design 或 Plan；多个候选必须让用户选择。
- write_policy=deny 仅允许只读检查和 Method Preview。
- write_policy=confirm 在第一次产品写入前展示准确摘要并获得确认。
- write_policy=auto 仅允许准确 Baseline 和 Claim Scope 内的项目写入。

help/version/commands/examples 不读取项目、stdin 业务 Payload、Owner、Claim 或 Store。
Unknown / latest / current / 模糊 Revision 一律失败关闭，不按分支、标题或最近 Artifact 选择。

## 工作流程

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

## 完成边界

局部 Checks 只表示 VFY ready。Artifact frozen 且 Current Claim completed 才可交给 VFY。
不宣称完整产品验证、发布通过或 RLS 可发布；不自动执行下一阶段。

不执行网络、安装依赖、Git commit/push/merge/tag/ref 操作、外部效果或 Scope 外写入。
共享 Effect Authorization 只用于外部发布效果，不能把它转换成 IMP 的本地或越界授权。
遇到产品执行中断，保留准确 Baseline、已持久化 Method 和现场，停止并明确恢复或 abandon；
不得从现场变化倒签 Claim、静默重放或推断完成。
