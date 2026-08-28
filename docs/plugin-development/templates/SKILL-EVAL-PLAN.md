# Skill Eval Plan — `<skill-name>`

## 1. 元数据

| Field | Value |
|---|---|
| Skill Name | `<skill-name>` |
| Design Contract | `docs/plugin-development/work-items/<skill-name>/DESIGN.md` |
| Stage | `design` |
| Status | `draft` |

## 2. 评测目标

分别验证：

1. 应使用 Skill 时是否能够发现或调用；
2. 不应使用 Skill 时是否保持不触发；
3. Skill 加载后是否遵守 Input、Output、Workflow 和 Failure Contract；
4. Skill 是否优于不加载 Skill 的基线；
5. 缺失输入时是否拒绝猜测和静默降级。

## 3. 核心行为检查

| Check ID | Requirement | Pass Condition |
|---|---|---|
| CHK-01 | 正向触发 | 应触发案例按预期调用 Skill |
| CHK-02 | 负向抑制 | 不应触发案例不调用 Skill |
| CHK-03 | 输入契约 | 只使用已提供或可验证的输入 |
| CHK-04 | 缺失处理 | 缺少必要事实时执行已定义行为，不猜测 |
| CHK-05 | 输出契约 | 输出位置、结构和内容符合 Design Contract |
| CHK-06 | 失败语义 | 失败、等待输入和成功不会混淆 |
| CHK-07 | 最小副作用 | 不发生未授权写入、安装或配置修改 |
| CHK-08 | 基线增益 | with-skill 比 without-skill 更稳定地满足契约 |

## 4. 测试案例

| Case ID | Category | Invocation | Prompt / User Intent | Fixture | Expected Skill Use | Expected Outcome | Forbidden Behavior |
|---|---|---|---|---|---|---|---|
| EV-P01 | trigger-positive | auto | | None | yes | | |
| EV-P02 | trigger-positive | explicit | | None | yes | | |
| EV-N01 | trigger-negative | auto | | None | no | | |
| EV-N02 | trigger-negative | auto | | None | no | | |
| EV-I01 | input-complete | explicit | | | yes | | |
| EV-M01 | input-missing | explicit | | | yes | | 猜测必要事实 |
| EV-B01 | boundary | explicit | | | yes/no | | |
| EV-C01 | comparison | explicit | | | with/without | | |

## 5. With-Skill / Without-Skill 对比

对同一个 Prompt 和 Fixture 使用两个全新会话：

1. `without-skill`：不加载候选 Skill；
2. `with-skill`：显式加载候选 Skill。

比较：

- 是否遵守领域结构；
- 是否识别缺失输入；
- 是否减少猜测；
- 是否形成正确输出；
- 是否出现额外副作用；
- 是否产生新的错误或不必要复杂度。

不得使用设计或实现会话残留上下文作为评测依据。

## 6. 平台边界

核心行为评测与平台适配评测分开记录。

本计划在 `evaluate` 阶段首先验证共享 Skill 语义。Cursor、Claude Code、Codex 的发现、自动触发和路径差异在各自 `adapt` 工作包中单独验证。

一个平台的成功结果不得复制为另一个平台的证据。

## 7. 证据记录

评测执行后建立：

`docs/plugin-development/work-items/<skill-name>/EVAL-RESULTS.md`

每次运行至少记录：

- Case ID；
- Agent 与运行载体；
- 版本；
- 日期；
- 是否加载 Skill；
- 输入 Fixture；
- 实际输出定位；
- Check 结果；
- 失败说明；
- 修订前后的 Skill Revision 或 Git Commit。

## 8. 通过标准

Design 阶段的 Eval Plan 可以标记为 `ready`，当且仅当：

- [ ] 正向触发案例不少于 2 个；
- [ ] 负向案例不少于 2 个；
- [ ] 输入完整、输入缺失和边界案例均存在；
- [ ] with-skill / without-skill 对比已定义；
- [ ] 每个案例都有可判定的 Expected Outcome；
- [ ] 每个关键禁用行为都有对应检查；
- [ ] 不依赖尚未定义的脚本、平台能力或外部服务。

本阶段只设计 Eval，不执行 Eval，不填写虚假的通过结果。
