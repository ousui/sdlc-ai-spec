---
name: sdlc-200-dsn
description: 根据需求和现有代码形成适用领域设计与真实验证方法；用于方案设计或VFY返回的设计修订。
disable-model-invocation: true
---

# SDLC 200 · 设计（DSN）

## 适用范围

根据需求和现有代码形成适用领域设计与真实验证方法；用于方案设计或VFY返回的设计修订。
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

1. phase.prepare读准确需求、Context、附件和现有实现。按需读取共享design-domains.md，选择实际相关领域。

2. 保存design的decision/rationale/alternatives/detail，并用requirements关系表示覆盖；不补固定空域或只写笼统技术标签。

3. 为验收定义command Check、明确argv及断言，criteria逐项关联；input_paths覆盖实际输入依赖，不能直接复制Task写范围。

4. 另定义required convergence Check，executor=agent、method=inspection或analysis，覆盖整个需求。定义required release_readback Check，command argv=["@runtime","delivery.readback"]；input_paths固定交付源码范围，省略时为完整main，同root多产品须显式限定。

5. 真实缺少业务方案时形成最小决定；已具备授权的实现细节由Agent判断。phase.complete成功后保存PLN新草稿。

## 输出与完成条件

适用设计与需求覆盖、验收方法、收敛和交付回读Check齐备；总授权下继续PLN。
默认用简短中文说明实际写入、验证、交付或阻塞。返回JSON时保持原字段，不混入进度叙述。
失败保留原回执与diagnostic_path；先识别责任层，再在已授权范围内修复/复验。

## 资源索引

- [共享执行约定](../_shared/runtime.md)：绑定、权限、证据与恢复，首次使用时读取。
- [本入口命令](references/interface.json)：真实命令与写入属性。
- [适用设计领域](../_shared/design-domains.md)：选择领域时按需读取。
