---
name: sdlc-500-vfy
description: 围绕验收标准验证实施结果，记录验收结论、返工项与发布条件。
disable-model-invocation: true
---

# SDLC-500-VFY · 验证确认

## 适用范围

执行真实验收和完整范围审阅，记录缺口并修复复验至收敛；用于实现验收及回归判断。
裸调用按当前明确请求与准确Runtime状态工作；整体需求已获授权时，由当前Agent衔接已授权阶段。
help/version/commands可通过CLI帮助、版本与本Skill命令表读取，不创建业务事实。

## 约定与边界

首次使用本插件先读[共享执行约定](../_shared/runtime.md)，后续仅在需要时回查。
不读取开发docs、测试、Handoff或兄弟私有资源，不执行SQL，不手工修改.sdlc数据库。
保留当前用户的范围和总授权；缺少必要决定或环境时报告具体缺口，不伪造human、pass或交付成功。
本Skill只处理本阶段。单阶段授权完成即停止；连续授权由当前Agent读取下一入口后继续。

## 子命令

[interface.json](references/interface.json)列出本入口使用的真实公开命令；字段以phase.prepare或--contract为准。

| 子命令 | 职责 | 可能写入 |
|---|---|---|
| `phase.prepare` | 读取准确内容和本阶段Schema | 否 |
| `task.next` | 查询当前可执行任务 | 否 |
| `task.start` | 开始已计划任务 | 是，须满足本阶段授权 |
| `task.finish` | 记录任务实际完成事实 | 是，须满足本阶段授权 |
| `check.run` | 运行实际命令验证 | 是，须满足本阶段授权 |
| `check.reuse` | 显式复用适用证据 | 是，须满足本阶段授权 |
| `check.record_review` | 记录实际Agent审阅 | 是，须满足本阶段授权 |
| `check.evaluate` | 只读判断当前收敛 | 否 |
| `finding.list` | 读取当前缺口 | 否 |
| `finding.address` | 标记已采取修复 | 是，须满足本阶段授权 |
| `finding.resolve` | 用适用新结果关闭缺口 | 是，须满足本阶段授权 |
| `phase.complete` | 校验并完成当前阶段 | 是，须满足本阶段授权 |
| `run.configure` | 有依据地调整执行预算 | 是，须满足本阶段授权 |
| `run.request_input` | 保存冲突并等待用户澄清 | 是，须满足本阶段授权 |
| `run.answer_input` | 保存实际回答并恢复当前需求 | 是，须满足本阶段授权 |

## 参数

下列是唯一公共CLI的参数；业务ID和payload由Agent使用Runtime回执组织，用户无需手填内部JSON。

| 参数 | 短参数 | 语义／默认值 |
|---|---|---|
| `--root` | `-r` | 明确的产品目录；默认`.`，不能误用插件目录 |
| `--request` | `-i` | UTF-8请求文件或默认`-`从stdin读取 |
| `--contract` | — | 输出当前机器契约，业务只读 |
| `--version` | `-V` | 输出Runtime/API/Schema版本，不打开Store |
| `--help` | `-h` | 输出CLI用法，不执行阶段 |

```text
<python> -B <plugin-root>/scripts/sdlc.py --root <product-root> --request -
```

## 执行流程

1. 读取当前实现、需求/验收/设计和证据适用性，执行计划所需VFY任务。对必要command Check实际check.run。

2. 已有结果只在内容/代码/环境/定义/时效都适用时check.reuse；保留原观察时间，不把历史版本结果当当前新执行。

3. 当前Agent真正检查完整需求范围与实际代码，用convergence agent Check记录审阅及缺口。声明self_review，不冒充独立或human审查。

4. 已知失败使验证任务无法完成或依赖审阅无法开始时，也调用phase.complete VFY退修；保留原条件和依赖。按返回阶段重新读取Skill并修复，原未完成任务留为interrupted/unknown，恢复后重新开始。

5. finding.address仅记录已采取修复；finding.resolve必须引用适用的新通过结果。再次完成所有必要Check与收敛审阅，check.evaluate为真才继续。

6. 格式/修复/无进展预算触发时保留错误并诊断。正常业务红绿如实计数，不通过降低Expected、删依赖或手工pass消除阻塞。

## 输出与完成条件

必要结果适用且通过、无未解决blocking finding、所有前置任务完成；总授权下继续RLS。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
