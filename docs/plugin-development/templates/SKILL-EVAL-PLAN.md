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
2. Input / Output / Workflow / Failure Contract；
3. 缺失输入不被猜测；
4. Shared Contract 和 Shared Package 边界；
5. Runtime Independence；
6. with-skill / without-skill；
7. 未授权兄弟 Skill 不被调用；
8. 对应 Client 的真实行为。

## 3. Core Checks

| Check ID | Requirement | Pass Condition |
|---|---|---|
| CHK-01 | Explicit invocation | 仅显式调用进入 Skill |
| CHK-02 | Negative suppression | 未调用或超出范围不执行 |
| CHK-03 | Standard input | 请求符合 Invocation Schema |
| CHK-04 | Standard output | 结果符合 Result Schema |
| CHK-05 | Missing input | 不猜测，按 Contract 处理 |
| CHK-06 | Shared contracts | 遵守 `_shared` Contract |
| CHK-07 | Shared package | 不复制、不直接访问内部实现 |
| CHK-08 | Runtime independence | 删除 `docs/**` 后仍执行 |
| CHK-09 | No docs dependency | Runtime 文件无 `docs/v1.x` 路径 |
| CHK-10 | No sibling invocation | 不调用兄弟业务 Skill |
| CHK-11 | With/without gain | with-skill 更稳定 |
| CHK-12 | Minimal side effects | 无未授权写入 |
| CHK-13 | Failure semantics | 失败、等待、成功不混淆 |
| CHK-14 | Client evidence | 对应宿主有可复现证据 |

## 4. Cases

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

## 5. Oracle Protection

- Fixture 与 Expected Outcome 在执行前固定；
- 实现者不得修改 Oracle 迁就失败；
- with/without 使用相同输入；
- 失败结果保留；
- 重试和人工补充必须记录。

## 6. Runtime Independence

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

## 7. Evidence

`EVAL-RESULTS.md` 至少记录：

- Case ID；
- Client / Surface / Version；
- Commit；
- Prompt / Fixture；
- 是否加载 Skill；
- 实际输出；
- Check 结果；
- 是否调用其他 Skill；
- 是否删除 docs 后运行；
- 重试和人工介入；
- 失败根因和返回阶段。

## 8. Pass Gate

- [ ] Critical Case 全通过。
- [ ] Runtime Independence 通过。
- [ ] 无未授权副作用。
- [ ] 无兄弟 Skill 调用。
- [ ] 输入输出 Schema 通过。
- [ ] Shared Package 边界通过。
- [ ] 未执行平台不声明 Verified。
