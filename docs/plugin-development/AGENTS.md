# Plugin Development Documentation Agent Instructions

## 1. 适用范围

本文件适用于 `docs/plugin-development/**`。这里保存开发治理、Work Item、
评测证据和 Handoff，不是安装后 Runtime。

## 2. 文档角色

| Path | Role |
|---|---|
| `DEVELOPMENT.md` | 稳定工程与 Runtime 规则 |
| `SKILL-DEVELOPMENT-WORKFLOW.md` | 阶段流程 |
| `COMPATIBILITY.md` | Client / Surface 证据 |
| `HANDOFF.md` | 当前状态和唯一下一工作包 |
| `templates/` | 通用 Work Item 模板 |
| `prompts/` | 单阶段启动入口 |
| `work-items/<skill-name>/` | 单个 Skill 的 Design / Eval / Review |
| `components/` | 共享基础组件设计与测试证据 |

不得让多个文件同时成为同一决定的权威来源。

## 3. Work Item

正式 Phase Skill 的 Work Item 路径必须使用：

```text
docs/plugin-development/work-items/sdlc-NNN-xxx/
```

名称必须与目标 Skill 完全一致。

Design 必须区分：

- Design-time Source；
- Bundled Runtime Contract；
- Shared Runtime Contract；
- Shared Package；
- Skill 私有资源。

不得把“运行时读取 docs/v1.x”写成实现方案。

## 4. 状态与批准

Design 状态：

```text
draft
ready
approved
superseded
```

Agent 可以在 DoD 满足且阻塞项为零时标记 `ready`，不得自行标记
`approved`。批准只来自 Maintainer 当前明确决定。

## 5. Eval 文档

`EVAL-PLAN.md` 只定义案例、Oracle 和通过条件。

`EVAL-RESULTS.md` 必须记录：

- Case ID；
- Client / Surface / 版本；
- Skill Commit；
- 输入与 Fixture；
- 实际输出；
- Check 结果；
- Runtime Independence；
- 是否调用其他 Skill / Plugin；
- 重试和人工补充；
- 失败及返回阶段。

## 6. Handoff

`HANDOFF.md` 是当前状态快照：

- 只登记一个下一工作包；
- 使用实时 Git 状态；
- 不硬编码固定仓库或远端名称；
- 不保留已经失效的当前描述；
- 无活动 Skill 时明确写 `None`；
- 不把路线图展开成多个待办。

并行会话只能有一个 Owner 修改 Handoff。

## 7. Template

模板必须：

- 使用 `sdlc-NNN-xxx` 命名；
- 把 Spec 作为 design-time Source；
- 要求自包含 Runtime；
- 要求共享 Contract 与 Package 边界；
- 包含 Runtime Independence Eval；
- 不混入某个阶段的具体业务字段。

只有两个以上真实 Work Item 暴露同一缺口时才修改通用模板。

## 8. 完成

修改完成前执行：

- `git diff --check`
- Runtime Contract Validator
- 相关单元测试
- 路径和链接检查

不得用文档承诺代替程序和 Eval 证据。
