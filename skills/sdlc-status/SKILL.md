---
name: sdlc-status
description: 严格只读查询当前项目的 SDLC 状态、准确需求流转、阻塞项和下一动作；仅在用户显式调用时执行。
disable-model-invocation: true
---

# SDLC Status

## 用户入口

裸调用即可：

```text
/sdlc-status
```

统一参数由 `scripts/sdlc_skill_interface.py` 与本 Skill 的 `references/interface.json` 解析。支持：

```text
auto
list
inspect --reference REQ-...@1
help / -h / --help
version / -V / --version
commands / --commands
examples / --examples
```

公共 `decision_policy`、`write_policy`、`output` 参数继续可用；本 Skill 的有效 `write_policy` 永远为 `deny`。

## 默认行为

1. `project_root` 未指定时，使用宿主提供的唯一当前工作区；
2. 无 Store：说明尚未开始，推荐 `sdlc-000-ctx`；
3. 有 CTX、无活跃 REQ：说明上下文状态，推荐 `sdlc-100-req`；
4. 只有一个活跃 REQ：自动 inspect；
5. 多个活跃 REQ：列出准确 Revision，由用户选择；
6. 提供准确 `REQ-...@数字Revision`：直接 inspect。

不得根据标题、相似度、`latest` 或 `current` 猜选 Requirement。

## 执行

```text
python3 <plugin-root>/skills/sdlc-status/scripts/runtime.py [arguments]
```

- `summary`：默认中文结果；
- `json`：单个结构化 JSON；
- `debug`：参数归一化和完整 Projection，不泄露 Secret。

## 严格只读

从调用到停止保持 exclusive execution：

- 不调用兄弟 Skill；
- 不初始化或修改 `.sdlc`；
- 不直接 SQL；
- 不改变 Artifact、Gate、Open Item 或 Revision；
- 不 commit、push、调用外部 API 或安装依赖；
- 只输出下一命令，不自动进入下一 Phase。

Graph、Frontier、Overall State 和 Next Action 是查询 Projection，不提供 Canonical Authority。

## 决策

多个 REQ 或多个合法业务目标时，默认 `decision_policy=user`：给出准确候选和推荐依据，由用户选择。用户无需填写 SQLite、Evidence ID、Digest、Manifest 或 Runtime Envelope。
