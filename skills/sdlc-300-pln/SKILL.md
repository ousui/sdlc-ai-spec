---
name: sdlc-300-pln
description: 拆分可执行的实施任务，明确依赖关系、执行顺序与交付条件。
disable-model-invocation: true
---

# SDLC-300-PLN · 交付计划

## 适用范围

把设计拆为可执行任务、验证和交付安排；明确前驱、条件时点及资源权限，避免循环等待。
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
| `change.revise` | 建立前序内容修订草稿 | 是，须满足本阶段授权 |
| `change.resolve` | 从双方内容检查点建立显式合并草稿 | 是，须满足本阶段授权 |
| `phase.submit` | 按generation提交结构化批次 | 是，须满足本阶段授权 |
| `phase.complete` | 校验并完成当前阶段 | 是，须满足本阶段授权 |
| `run.request_input` | 保存冲突并等待用户澄清 | 是，须满足本阶段授权 |
| `run.answer_input` | 保存实际回答并恢复当前需求 | 是，须满足本阶段授权 |
| `asset.unlink` | 解除当前草稿附件链接并保留历史字节 | 是，须满足本阶段授权 |

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

1. 读取准确设计与验收方法，列出IMP/VFY/RLS需要的任务。保留每个task的designs/criteria覆盖。

2. 为任务写明target_phase、kind、完成事实与scope_paths；权限使用稳定resource键和最小read/write路径。

3. 分别建立task_dependencies和preconditions。条件绑定真实Check、producer/consumer与start/execute/complete时点；准备任务不能在开始前依赖自己的未来输出。

4. command Check所属task应与实际运行时点一致。构建和测试可能写缓存/输出目录，把这些实际范围纳入任务；环境探针完成必须有真实Check结果。

5. 校验所有必要验收覆盖、联合图无环和RLS回读方法；phase.complete后使用已采用revision_id进入IMP，不能沿用旧草稿generation。

## 输出与完成条件

计划提交且依赖可执行，任务/Check关系准确；总授权下继续IMP。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
