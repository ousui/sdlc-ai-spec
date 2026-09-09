---
name: sdlc-100-req
description: 把原始需求、范围、来源和验收转为结构化变更；用于新需求或已有需求的明确修订。
disable-model-invocation: true
---

# SDLC 100 · 需求（REQ）

## 适用范围

把原始需求、范围、来源和验收转为结构化变更；用于新需求或已有需求的明确修订。
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
| `change.create` | 保存原始请求并建立需求 | 是，须满足本阶段授权 |
| `change.get` | 读取当前需求内容 | 否 |
| `change.revise` | 建立前序内容修订草稿 | 是，须满足本阶段授权 |
| `change.resolve` | 从双方内容检查点建立显式合并草稿 | 是，须满足本阶段授权 |
| `phase.prepare` | 读取准确内容和本阶段Schema | 否 |
| `phase.submit` | 按generation提交结构化批次 | 是，须满足本阶段授权 |
| `asset.add` | 关联真实原始附件 | 是，须满足本阶段授权 |
| `phase.complete` | 校验并完成当前阶段 | 是，须满足本阶段授权 |
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

1. 先保留原始用户提示词和验收意图，再检查准确CTX和已有change。多个候选不能按最新时间猜选。

2. 新需求change.create固定slug、目标、范围、original_text和当前用户授权；local交付target为.sdlc/exports/<name>。保存change_id/run_id/source_id。

3. phase.prepare后使用client_key批量创建requirements/criteria，分别建立来源与覆盖关系；必要附件asset.add使用产品root内相对路径并保留名称/顺序。

4. 已有需求修订先change.revise REQ，再根据当前输入更新。验收应可观察且覆盖需求，不先编造候选代码或后补阶段答案。

5. phase.complete带准确generation，通过后保存下一草稿revision_id。缺必需业务决定时只问最小问题，不请用户修UUID、JSON或SQL。

## 输出与完成条件

原始请求、必要需求/验收和关系已提交，目标与权限明确；总授权下继续DSN。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
