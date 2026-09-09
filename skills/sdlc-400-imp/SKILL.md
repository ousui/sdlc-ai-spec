---
name: sdlc-400-imp
description: 按已采用计划实际编写代码和测试、收集操作证据；用于实现任务及VFY驱动的产品修复。
disable-model-invocation: true
---

# SDLC 400 · 实现（IMP）

## 适用范围

按已采用计划实际编写代码和测试、收集操作证据；用于实现任务及VFY驱动的产品修复。
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
| `run.start` | 建立当前本机Run | 是，须满足本阶段授权 |
| `run.acquire` | 取得本机执行lease | 是，须满足本阶段授权 |
| `authorization.grant` | 记录当前用户明确本机授权 | 是，须满足本阶段授权 |
| `task.next` | 查询当前可执行任务 | 否 |
| `task.start` | 开始已计划任务 | 是，须满足本阶段授权 |
| `task.write` | 保存实际产品文件变化 | 是，须满足本阶段授权 |
| `task.finish` | 记录任务实际完成事实 | 是，须满足本阶段授权 |
| `check.run` | 运行实际命令验证 | 是，须满足本阶段授权 |
| `operation.reconcile` | 回查未知效果 | 是，须满足本阶段授权 |
| `phase.complete` | 校验并完成当前阶段 | 是，须满足本阶段授权 |

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

1. 先phase.prepare读取当前计划；复制后run.start建立本机Run，按已有用户总授权用authorization.grant记录所需本机权限，再run.acquire取得lease，再task.next查询当前可做任务及条件；无法执行时看具体依赖或环境缺口。

2. task.start对应任务后，当前Agent实际设计并编写产品代码和测试，通过task.write保存文本文件变化。每个文件使用明确resource/path。

3. 声明的准备/构建/环境Check通过check.run真实执行，核对输出和退出码；不要把task.finish当作环境通过。

4. 完成代码与实际任务事实后task.finish。未知写入先operation.reconcile，保留原始失败再修责任层；禁止先制作所有产品答案再补Runtime记录。

5. IMP任务完成后phase.complete IMP；这只表示实现事实完成，不代表VFY或交付通过。

## 输出与完成条件

实际实现、测试代码和任务事实已保存；总授权下当前Agent继续VFY真实验证。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
