---
name: sdlc-200-dsn
description: 创建、修订和检查设计 DSN Artifact Set；自动分析 REQ、项目基线和 16 个设计领域，仅在真实设计决策时请求用户选择。
disable-model-invocation: true
---

# SDLC 200 Design

## 用户入口

裸调用即可：

```text
/sdlc-200-dsn
```

支持：

```text
auto
create
revise --reference DSN-...@1
check --reference DSN-...@1
--input / -i REQ-...@1        # 可重复
help / -h / --help
version / -V / --version
commands / --commands
examples / --examples
```

统一参数由共享 Skill Interface 解析。用户无需手工构造 Matrix、DOM Member、Evidence ID、Digest、Manifest、Final Confirmation JSON 或 Runtime Envelope。

## 共享接口绑定

- 通用参数、冲突检查和元命令入口：`scripts/sdlc_skill_interface.py`
- 本 Skill 命令、版本和示例：`references/interface.json`
- 多 Scope / Control Input 扩展：`skills/_shared/contracts/skill-inputs.md`
- `decision_policy` 默认 `user`
- `write_policy` 默认 `auto`，只覆盖标准项目内 ArtifactStore 写入

元命令只读取 bundled interface，不扫描项目、不初始化 Store，也不产生写入。

## 默认工作流

1. 解析唯一 Project Root、准确 DSN Reference 和重复 `--input/-i`；
2. 无显式输入时，通过 Lifecycle Query 发现唯一可用 REQ；多个候选由用户选择；
3. 只读解析 frozen CTX、REQ、VFY Return 或 RLS Issue Authority；
4. 读取完成设计所需的最小项目基线，将可证明事实登记为 observed / referenced；
5. 仅在设计边界、共享或拆分、关键方案、风险接受、Waiver、法律适用性或 Final Confirmation 无唯一答案时请求用户决定；
6. 按 `references/200-dsn-spec.md` 和 16 个 bundled Domain Contract 构造父 DSN Artifact Set；
7. 通过 `scripts/runtime.py` 执行确定性 Builder、Domain Validator、Manifest 闭包、ArtifactStore 和 Gate；
8. 输出简明设计摘要、Domain 状态、阻塞项和唯一下一动作。

## Artifact Set

一个 DSN Revision 包含：

- primary Canonical Markdown；
- 每个 `required` Domain 的 `DOM-*` Member；
- Supporting Members；
- 完整 Manifest-Member closure。

16 个 Domain 是本 Skill 的私有 Contract，不是可单独调用的 Skill。`DOM-510` 在 DSN 存在时固定为 `required`。

## 决策和写入

- `decision_policy=user` 为默认值；多个合法方案且无确定最优解时给出推荐和主要备选，由用户决定；
- `decision_policy=model/experiment` 只有用户明确授权时有效；
- `write_policy=auto` 只授权标准项目内 `.sdlc/store.sqlite3` 写入；Git、远端、依赖安装和 Project Root 外写入始终需要单独授权；
- Requirement 存在缺失、冲突或不可实现内容时返回 REQ，不在 DSN 中静默改变业务语义。

## 执行

```text
python3 <plugin-root>/skills/sdlc-200-dsn/scripts/runtime.py [arguments] < request.json
```

- `summary`：默认中文摘要；
- `json`：单个结构化结果；
- `debug`：参数归一化和完整结果，不泄露 Secret。

## 严格边界

- 不调用兄弟 Skill；
- 不读取开发期文档、Work Item 或 Handoff；
- 不直接 SQL 或复制 Store Schema；
- 不把设计文件写入项目源码树；
- 不使用 `latest/current` 或标题相似度选择 Authority；
- `check` 绝对只读；
- 不记录真实 Secret、Token、密码或私钥；
- 不自动进入 PLN、IMP 或 VFY。
