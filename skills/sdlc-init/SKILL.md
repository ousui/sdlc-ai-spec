---
name: sdlc-init
description: 初始化、诊断或复制本地SDLC工作区；已有库保留数据，独立副本重新绑定身份与权限。
disable-model-invocation: true
---

# SDLC 初始化（INIT）

## 适用范围

初始化、诊断或复制本地SDLC工作区；已有库保留数据，独立副本重新绑定身份与权限。
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
| `workspace.discover` | 列出Git登记的可用来源 | 否 |
| `workspace.init` | 幂等建立本地工作区 | 是，须满足本阶段授权 |
| `workspace.inspect` | 只读检查库和资源绑定 | 否 |
| `workspace.clone` | 复制到明确独立产品目录 | 是，须满足本阶段授权 |
| `workspace.bind` | 绑定本机资源路径 | 是，须满足本阶段授权 |
| `workspace.rebind` | 重绑定手工复制或移动的工作区 | 是，须满足本阶段授权 |
| `workspace.export` | 导出一个需求的完整离线归档 | 是，须满足本阶段授权 |
| `workspace.collect` | 逻辑交回一个需求并保留冲突 | 是，须满足本阶段授权 |

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

1. 确认产品目录、现存.sdlc及Python/SQLite环境；先workspace.inspect，缺Store才进入初始化路径。

2. 已有Git worktree时workspace.discover只读列出登记来源；用户已授权默认复制且来源唯一时workspace.clone，否则明确选择复制来源或新建。

3. 新建使用workspace.init；手工复制导致root漂移时说明来源并workspace.rebind。复制保留历史，外部resource需workspace.bind，来源授权不激活。

4. 回读workspace.inspect并保存project/workspace绑定。init完成不产生业务需求，不把初始化或环境准备当作IMP/VFY结果。

5. 移交用workspace.export选择change_id；workspace.collect只导入事实与证据，不合并源码。冲突保留原包和双方head，交由已授权的内容修订处理。

## 输出与完成条件

已有有效workspace、可用资源与明确下一入口。全链已授权时由当前Agent继续读取CTX。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
