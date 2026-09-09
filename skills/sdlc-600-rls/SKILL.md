---
name: sdlc-600-rls
description: 按已授权的发布计划执行本地交付，核对目标副本并保存交付证据。
disable-model-invocation: true
---

# SDLC-600-RLS · 发布交付

## 适用范围

将已验证产品交付到预先约定的本地包并独立回读，保留完整归档；不默认发布或部署。
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
| `task.start` | 开始已计划任务 | 是，须满足本阶段授权 |
| `delivery.prepare` | 准备准确本地包字节 | 是，须满足本阶段授权 |
| `delivery.execute` | 实际写包并独立回读 | 是，须满足本阶段授权 |
| `delivery.get` | 读取交付记录 | 否 |
| `task.finish` | 记录任务实际完成事实 | 是，须满足本阶段授权 |
| `phase.complete` | 校验并完成当前阶段 | 是，须满足本阶段授权 |
| `workspace.export` | 导出一个需求的完整离线归档 | 是，须满足本阶段授权 |
| `operation.reconcile` | 回查未知效果 | 是，须满足本阶段授权 |
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

1. 读REQ固定delivery_mode/target及当前VFY适用结果。只有local适配器已实现，不能把部署需求改为文件包以声称完成。

2. 启动RLS任务，delivery.prepare提供实际用法说明，保存delivery_id/package_path。准备仅固定包字节，不是交付成功。

3. delivery.execute实际写包并运行独立readback。核对succeeded和真实结果；输入变化或回读过期必须重新验证/回读，不能沿用旧包关闭新产品。

4. 完成RLS任务后phase.complete RLS；Runtime再次核对目标字节、结果适用性、任务和VFY。unknown先恢复，不重复盲发。

5. 使用新的管理请求、不附已关闭run_id，workspace.export的payload.change_id指定本需求。回读返回归档路径与摘要，保留原始日志、附件和离线index。

## 输出与完成条件

本地包与独立回读成功、RLS已关闭、完整离线归档可读。报告真实使用方式和未验证边界，停止本需求。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
