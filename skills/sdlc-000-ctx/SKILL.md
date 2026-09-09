---
name: sdlc-000-ctx
description: 收集项目事实、规则与资源，建立可追踪的项目上下文。
disable-model-invocation: true
---

# SDLC-000-CTX · 项目上下文

## 适用范围

收集实际项目事实、规则、资源和命令，保存可追踪CTX；用于新项目接管或已知上下文刷新。
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
| `context.commit` | 提交项目上下文 | 是，须满足本阶段授权 |

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

1. 读取项目结构、实际工具链和用户约束；检查已有Context来源及适用范围，不把推测登记为已观察事实。

2. 以fact/rule/resource/command结构组织entries。resource settings保存稳定resource键，command settings保存argv数组和环境变量名称，不存凭证值。

3. 新建context.commit；刷新传parent_id并明确本次完整entries，保留仍适用事实。只关联已经绑定的实际资源。

4. 保存Runtime返回context_id及摘要；后续change.create明确采用这版，不能以新CTX静默替换已有需求依据。

## 输出与完成条件

已提交CTX及准确来源可读；总授权包含实现时由当前Agent继续REQ。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
