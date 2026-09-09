---
name: sdlc-status
description: 只读查看本地需求、阶段、Run、检查和交付事实；需要时显式生成阅读视图，不自动推进业务。
disable-model-invocation: true
---

# SDLC 状态（status）

## 适用范围

只读查看本地需求、阶段、Run、检查和交付事实；需要时显式生成阅读视图，不自动推进业务。
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
| `workspace.inspect` | 只读检查库和资源绑定 | 否 |
| `status` | 列出本地需求和Run状态 | 否 |
| `change.get` | 读取当前需求内容 | 否 |
| `run.get` | 读取准确Run及步骤 | 否 |
| `finding.list` | 读取当前缺口 | 否 |
| `delivery.get` | 读取交付记录 | 否 |
| `render` | 生成可再生阅读视图 | 是，须满足本阶段授权 |

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

1. 确定当前root以及用户选择的change/run。缺Store时报告缺少初始化，状态查询不自动建库或修复。

2. workspace.inspect/status列出候选；按准确ID读取change.get/run.get/finding.list/delivery.get，不把历史最新条目作为用户选择。

3. 区分draft/committed、task完成/Check通过、addressed/resolved、prepared/succeeded、unknown与实际交付。

4. 用户要求阅读视图时显式render并打开返回路径；视图由数据投影，不能编辑Markdown后写回业务状态。

5. 报告已知事实、适用版本和最小下一动作；不执行任务、扩大权限、关闭finding或重新发布。

## 输出与完成条件

已给出所选需求的准确状态和证据限制；只读请求没有业务状态变更。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
