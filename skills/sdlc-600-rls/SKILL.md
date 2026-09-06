---
name: sdlc-600-rls
description: 显式调用时，从准确冻结 VFY 建立持久发版合约，经独立宿主授权执行本地 Sandbox，完成目标侧确认、只读复核、重试或最终冻结。
disable-model-invocation: true
---

# SDLC 600 · 发版（RLS）

## 适用范围

从准确 frozen VFY 建立发版合约，经独立效果授权执行本地 Sandbox，并完成目标侧确认；不接入生产发布。 内部 Evidence ID、Digest、Manifest 与 Invocation 由 Skill 整理，用户无需手填内部 JSON。

```text
/sdlc-600-rls
/sdlc-600-rls create -i VFY-20260904100000-01@1 --target sandbox-a --release-reference 1.0.0
/sdlc-600-rls execute -r RLS-20260904110000-01@1 --item RLI-001 --item RLI-002
```

## 约定与边界

从显式调用到结束保持 Exclusive Skill Execution，不调用兄弟 Skill，不传递授权。只使用本 Skill 与共享 Runtime/ArtifactStore；不直接 SQL、不复制 Store Schema、不使用文件或数据库 fallback，不读取开发期文档、测试或 Handoff。

事实区分 observed / referenced / confirmed；缺口进入 Open Items，不猜测。Authority 使用准确数字 Revision，不使用 branch/tag/PR/latest/current 或标题相似度。`decision_policy=user` 默认由用户决定多解业务问题；model/experiment 需明确授权，实验还需范围、指标、成本和停止条件。

`write_policy` 不替代业务批准、Exception、Final Confirmation 或独立效果授权。check/inspect 不修复、不初始化、不创建旁车。Git、远端、安装、项目外写入不属于本 Skill 的默认许可；真实 Secret 不进入 Artifact、日志或输出。

仅支持 OS 临时目录内专用 Sandbox，Target ID 与准确位置绑定并使用 no-follow 操作。工作区/GitHub 权限、Trigger、write_policy 和 Final Confirmation 均不替代 Effect Authorization。

## 子命令

以 [interface.json](references/interface.json) 为命令 Authority；元命令 help/version/commands/examples 不扫描项目、不读取业务 stdin、不打开 Store。

| 子命令 | 职责 | 可能写入 |
|---|---|---|
| `auto` | 根据唯一 VFY、RLS 状态和目标效果选择唯一合法动作。 | 是，须满足本阶段授权 |
| `create` | 建立 Release Contract、RLI、RCF 和 Checklist；不产生目标效果。 | 是，须满足本阶段授权 |
| `execute` | 在精确 Effect Authorization 下执行一个或多个选定 RLI。 | 是，须满足本阶段授权 |
| `confirm` | 执行或记录一个或多个选定的目标侧 RCF。 | 是，须满足本阶段授权 |
| `revise` | 同目标重试时创建新 Revision；目标改变时创建新 Artifact。 | 是，须满足本阶段授权 |
| `check` | 严格只读复核 Contract、Evidence、Conclusion、Gate 和目标当前状态。 | 否 |
| `cancel` | 仅在确认未产生目标效果且目标未漂移时取消当前发版。 | 是，须满足本阶段授权 |
| `finalize` | 验证独立最终确认与当前 Gate 后冻结准确 Revision。 | 是，须满足本阶段授权 |
| `help` | 显示用途、参数和副作用边界。 | 否 |
| `version` | 显示 Skill 和 Interface 版本。 | 否 |
| `commands` | 列出全部命令及副作用。 | 否 |
| `examples` | 显示最小安全调用示例。 | 否 |

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
| `--input` | `-i` | 准确 VFY Revision；不得以自述 Candidate JSON 代替读回 |
| `--item` | `—` | 可重复；execute 选择 RLI，confirm 选择 RCF |
| `--target` | `—` | 明确的本地 Sandbox Target ID；位置由受控输入绑定 |
| `--release-reference` | `—` | Release Reference；不是 VFY 或 Result Authority |

`--` 后为请求正文，不是新增开关。help 支持 `-h`，version 支持 `-V`；其他兼容别名以共享 parser 为准。多个工作区、Revision 或操作均不猜选。

## 执行流程

1. 从共享 Store 读取准确 frozen VFY 的 Primary、State、Manifest、Evidence、Current IMP 和控制输入，经 `rls_vfy_adapter.py` 重建 Final Confirmation 并验证 producer state digest；历史 parser 不签发 Authority。
2. create 分配并持久化 open Revision，绑定完整 Scope/Result/Target/Baseline/RLI/RCF/Checklist，不产生目标效果。
3. execute 前，可信宿主在用户明确批准后通过 `TrustedEffectRecords.grant` 签发不可覆盖授权；CLI 只能消费已有记录。Revision、合约、Target/Baseline 或所选集合变化均使旧授权失效。
4. 每个效果前保存恢复 intent，每项已观察结果立即记录和 CAS 回写。效果可能发生但 Evidence/回写失败时保留 `effect_uncertain` 与追加日志，停止、禁止自动重放或取消；不得伪造零效果。
5. confirm 按原始 RCF Expected 与 Evidence Requirement 判定；不支持的条件失败关闭，不用版本相同代替其他检查。人工确认消费准确绑定的可信宿主观察，不从自由文本伪造批准。
6. 同 Revision 执行和确认；同 Scope/Result/Target 的重试创建新 Revision，重新取得 Baseline 和 Authorization。Target 改变创建新 Artifact；Scope/Result 改变返回上游。
7. cancel 仅在无可能目标效果时允许。finalize 需要独立、当前 Final Confirmation；域与共享 Core 验证通过才冻结。check 始终使用准确持久化读回。

## 输出与完成条件

`summary` 默认只呈现事实、准确 Artifact、Gate、已执行写入、阻塞和下一动作。`json` 只返回正式 Runtime 的结构化结果，不添加进度文本、不改写字段或说明；调试信息不混入 JSON。`debug` 展示有界诊断，先脱敏。

Gate pass 不等于 Release success：可信 failed/partial/cancelled 可以 Gate pass。按实际结果展示后续 retry 或 return，不从 PR、写入成功或授权存在推断发布成功。本地 Sandbox 结果不是生产验收。

## 资源索引

- 先读 [运行契约](references/contract.md) 和 [命令定义](references/interface.json)。
- 执行入口：[runtime](scripts/runtime.py)；共用参数：`scripts/sdlc_skill_interface.py` 与 [共享接口](../_shared/contracts/skill-interface.md)。
- [独占执行约定](../_shared/contracts/skill-execution.md)；仅在处理相应业务对象时按契约读取 bundled references/assets，不整包加载。
