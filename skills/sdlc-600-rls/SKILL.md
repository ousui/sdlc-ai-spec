---
name: sdlc-600-rls
description: 显式调用时，从准确冻结 VFY 建立持久发版合约，经独立宿主授权执行本地 Sandbox，完成目标侧确认、只读复核、重试或最终冻结。
disable-model-invocation: true
---

# RLS 发版

从调用到结束保持 Exclusive Skill Execution。只执行本 Skill，不调用兄弟 Skill。
先读取 `references/contract.md` 和 `references/interface.json`。
共用参数合约由 `scripts/sdlc_skill_interface.py` 提供；实际入口为本目录的
`scripts/runtime.py`，通过共享 parser 解析 `decision_policy`、`write_policy`。

命令为 `auto/create/execute/confirm/revise/check/cancel/finalize`，meta 为
`help/version/commands/examples`。`-p` 指定 Project Root，`-i` 指定准确 VFY，
`-r` 指定准确 RLS Revision，`--item` 可重复。业务 JSON 只表达输入；不能提供
自述 Artifact 或 VFY 来代替 Store Authority。`check -r` 绝对只读。

`create` 经共享 ArtifactStore 分配并持久化 open Revision。它不产生目标效果。
`execute` 之前，宿主必须在用户明确批准后通过 `TrustedEffectRecords.grant`
签发不可覆盖的独立授权记录；CLI 只能消费已有记录，不能从 JSON 签发权限。
批准完整 Release Contract、Target 位置与 Baseline、准确 RLI 集合及 Checklist。
`write_policy=auto`、GitHub 权限、Trigger 和 Final Confirmation 均不替代此授权。

本 Runtime 只支持 OS 临时目录内的专用 Sandbox。没有生产发布、网络、Git、
任意进程或安装能力。目标以 ID 和准确本地位置绑定，采用 no-follow 文件操作。
Secret 在持久化或效果之前拒绝；未知异常不回显输入。

所有 VFY wire 解析集中于 `rls_vfy_adapter.py`。正式入口只从共享 Store 读取
准确 frozen VFY 的 Primary、State、Manifest、Evidence、Current IMP 与控制输入，
重建 Final Confirmation 并校验 producer state digest。历史 parser 不能签发 Authority。

每个效果前保存恢复 intent；每项已观察结果立即记录和 CAS 回写。
效果可能发生但 Evidence 或回写失败时，保留 `effect_uncertain` 和追加恢复日志，
停止执行、禁止自动重放与取消。由显式恢复工作核对原效果和日志，不伪造零效果。

同 Revision 执行与确认；同 Scope/Result/Target 的实际重试创建新 Revision并重取
Baseline 与 Authorization；Target 改变创建新 Artifact；Scope/Result 改变返回上游。
`finalize` 需要独立的当前 Final Confirmation，域验证和共享 Core 验证通过后才冻结。
Gate pass 与 Release Conclusion 分开：可信 failed/partial/cancelled 可以 Gate pass。

只读 lifecycle/status 投影提供一个后续动作，不从 PR 或 Gate 推断发布成功。
本地验证不代表生产验收，也不代替独立 Web Review。
