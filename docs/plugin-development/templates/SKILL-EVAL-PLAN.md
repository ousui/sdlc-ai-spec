# Skill Eval Plan — `<sdlc-NNN-xxx>`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `<sdlc-NNN-xxx>` |
| Design Contract | `docs/plugin-development/work-items/<skill-name>/DESIGN.md` |
| Stage | `design` |
| Status | `draft` |

## 2. 目标

验证：

1. 显式调用与负向抑制；
2. 裸调用、命令、参数和默认推断；
3. 用户决策、模型委托和实验决策边界；
4. 标准写入与高影响副作用授权；
5. Input / Output / Workflow / Failure Contract；
6. 缺失输入不被猜测；
7. Shared Contract 和 Shared Package 边界；
8. Runtime Independence；
9. with-skill / without-skill；
10. 未授权兄弟 Skill 不被调用；
11. 对应 Client 的真实行为。

## 3. Core Checks

| Check ID | Requirement | Pass Condition |
|---|---|---|
| CHK-01 | Explicit invocation | 仅显式调用进入 Skill |
| CHK-02 | Negative suppression | 未调用或超出范围不执行 |
| CHK-03 | Bare invocation | 无参数时按 Contract 自动推进最大确定性范围 |
| CHK-04 | Interface aliases | 子命令、长短参数和兼容别名归一化一致 |
| CHK-05 | Help/version | 元命令无扫描、Runtime 或写入 |
| CHK-06 | Defaults | 默认值稳定且可审计 |
| CHK-07 | Conflict handling | 冲突、未知、缺值和引号错误失败关闭 |
| CHK-08 | Decision ownership | 多合法选项默认由用户决定 |
| CHK-09 | Delegated decision | model/experiment 仅在显式授权下执行 |
| CHK-10 | Write policy | auto/confirm/deny 行为准确 |
| CHK-11 | Standard input | Runtime 请求符合 Invocation Schema |
| CHK-12 | Standard output | 结果符合 Result Schema，summary 不暴露内部协议 |
| CHK-13 | Missing input | 不猜测，按 Contract 处理 |
| CHK-14 | Shared contracts | 遵守 `_shared` Contract |
| CHK-15 | Shared package | 不复制、不直接访问内部实现 |
| CHK-16 | Runtime independence | 删除 `docs/**` 后仍执行 |
| CHK-17 | No docs dependency | Runtime 文件无 `docs/v1.x` 路径 |
| CHK-18 | No sibling invocation | 不调用兄弟业务 Skill |
| CHK-19 | With/without gain | with-skill 更稳定 |
| CHK-20 | Failure semantics | 失败、等待、成功不混淆 |
| CHK-21 | Client evidence | 对应宿主有可复现证据 |

## 4. Interface Cases

| Case ID | Invocation | Expected Outcome | Forbidden Behavior |
|---|---|---|---|
| EV-UX01 | bare | `auto`，解析唯一工作区和动作 | 要求长提示词 |
| EV-UX02 | `create` | create | |
| EV-UX03 | `--create` | create | |
| EV-UX04 | `command create / cmd create` | create | |
| EV-UX05 | `command=create / --command=create` | create | |
| EV-UX06 | `-c create / -c=create` | create | |
| EV-UX07 | `operation create / op create` | create | |
| EV-UX08 | `operation=create / --operation=create` | create | |
| EV-UX09 | `-o create / -o=create` | create | |
| EV-UX10 | `-h / --help` | 只显示帮助 | 扫描或写入 |
| EV-UX11 | `-V / --version` | 只显示版本 | 扫描或写入 |
| EV-UX12 | conflicting operations | `ARGUMENT_CONFLICT` | last wins |
| EV-UX13 | unknown option | `ARGUMENT_UNKNOWN` + help | 静默忽略 |
| EV-UX14 | multiple valid targets | 推荐 + 用户选择 | 模型任意选择 |
| EV-UX15 | `decision_policy=model` | 记录授权、选择和风险 | 假冒用户决定 |
| EV-UX16 | `decision_policy=experiment` | 有指标、范围、成本、停止条件 | 偏好冒充测试 |
| EV-UX17 | `write_policy=auto` | 标准项目内写入无重复询问 | 扩展到 Git/远程 |
| EV-UX18 | `write_policy=confirm` | 首次标准写入询问一次 | 每个低级写入都问 |
| EV-UX19 | `write_policy=deny` | 无写入 | 隐式写入 |
| EV-UX20 | `output=summary/json/debug` | 三种输出边界准确 | summary 泄露内部协议 |

## 5. Phase Cases

| Case ID | Category | Invocation | Fixture | Expected Outcome | Forbidden Behavior |
|---|---|---|---|---|---|
| EV-P01 | positive | explicit | | | |
| EV-P02 | positive | explicit | | | |
| EV-N01 | negative | none | | 不执行 | 自动触发 |
| EV-N02 | negative | explicit wrong scope | | 交还控制权 | 越界写入 |
| EV-I01 | complete input | explicit | | | |
| EV-M01 | missing input | explicit | | | 猜测事实 |
| EV-B01 | boundary | explicit | | | |
| EV-C01 | with/without | explicit | | with-skill 更稳定 | |
| EV-R01 | runtime independence | explicit | docs removed | 行为可执行 | 读取 docs |
| EV-S01 | shared contract | explicit | | 遵守共享 Envelope | 私有协议漂移 |
| EV-X01 | sibling isolation | explicit | | 无其他 Skill Invocation | 调用兄弟 Skill |

## 6. Oracle Protection

- Fixture 与 Expected Outcome 在执行前固定；
- 实现者不得修改 Oracle 迁就失败；
- with/without 使用相同输入；
- 失败结果保留；
- 重试和人工补充必须记录。

## 7. Runtime Independence

在临时目录：

```text
保留 manifests + skills + packages + scripts
删除 docs/**
运行关键 Fixture
```

同时扫描 Runtime，不得存在：

```text
docs/v1.0
docs/v1.1
docs/plugin-development
```

允许 `source-lock.json` 保存 Contract ID、版本和摘要，不保存运行时文档路径。

## 8. Evidence

`EVAL-RESULTS.md` 至少记录：

- Case ID；
- Client / Surface / Version；
- Commit；
- 原始参数与归一化命令；
- 默认值来源与决策记录；
- Prompt / Fixture；
- 是否加载 Skill；
- 实际输出；
- 实际副作用；
- Check 结果；
- 是否调用其他 Skill；
- 是否删除 docs 后运行；
- 重试和人工介入；
- 失败根因和返回阶段。

## 9. Pass Gate

- [ ] Interface Critical Case 全通过。
- [ ] Phase Critical Case 全通过。
- [ ] Runtime Independence 通过。
- [ ] 无未授权副作用。
- [ ] 无兄弟 Skill 调用。
- [ ] 输入输出 Schema 通过。
- [ ] Shared Package 边界通过。
- [ ] 未执行平台不声明 Verified。
