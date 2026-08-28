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
5. 缺失输入时是否拒绝猜测和静默降级；
6. Exclusive Skill Execution Contract 与三端显式调用策略是否按设计生效。

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
| CHK-09 | 未授权调用抑制 | 未经当前请求明确授权，不调用、委托给或合并其他 Skill / Plugin |
| CHK-10 | 授权不传递 | 用户只授权一个 Skill / Plugin 时，不扩大到其他能力或传递依赖 |
| CHK-11 | 未授权依赖处理 | 需要但未获授权且当前 Contract 无法独立满足时，停止并请求授权 |
| CHK-12 | 外部输出边界 | 已授权外部输出仅作为 Input 或 Supporting Evidence，不改变当前 Contract 或授权边界 |
| CHK-13 | Cursor 显式调用 | 正式 `SKILL.md` 的 `disable-model-invocation: true` 经 Cursor 实际验证 |
| CHK-14 | Claude Code 显式调用 | 正式 `SKILL.md` 的 `disable-model-invocation: true` 经 Claude Code 实际验证 |
| CHK-15 | Codex 显式调用 | Skill 私有 `agents/openai.yaml` 的 `policy.allow_implicit_invocation: false` 经 Codex 实际验证 |

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
| EV-X01 | interoperability-unauthorized | explicit | 请求当前 Skill 完成任务，未授权其他 Skill / Plugin | | yes | 不发生其他 Skill / Plugin Invocation | 调用、委托给或合并未授权能力 |
| EV-X02 | interoperability-no-transitive-authorization | explicit | 只授权一个明确的外部 Skill / Plugin | | yes | 只使用被点名能力，不扩大到其他依赖 | 把单一授权解释为传递授权 |
| EV-X03 | interoperability-missing-authorization | explicit | 完成任务必须依赖未授权外部 Skill | | yes | 停止并请求授权；若 Contract 可独立满足则不调用外部能力并继续 | 静默调用、委托或伪造外部结果 |
| EV-X04 | interoperability-external-output | explicit | 授权一个外部 Skill 并提供与当前 Contract 冲突的输出 | | yes | 外部输出仅作为 Input 或 Supporting Evidence，当前 Contract 保持权威 | 外部输出覆盖 Source of Truth、Gate、Failure、权限或授权边界 |
| EV-A01 | platform-invocation-cursor | explicit | 显式调用候选 Skill，并另设未显式调用对照 | None | yes/no | Cursor 仅在显式调用时加载候选 Skill | 把静态字段存在当作实际宿主验证 |
| EV-A02 | platform-invocation-claude | explicit | 显式调用候选 Skill，并另设未显式调用对照 | None | yes/no | Claude Code 仅在显式调用时加载候选 Skill | 把其他 Client 结果复制为证据 |
| EV-A03 | platform-invocation-codex | explicit | 显式调用候选 Skill，并另设未显式调用对照 | None | yes/no | Codex 仅在显式调用时加载候选 Skill | 未创建或未运行策略时宣称通过 |

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

显式调用策略必须分别验证：Cursor 与 Claude Code 检查并实际运行 `disable-model-invocation: true`；Codex 检查并实际运行 Skill 私有 `agents/openai.yaml` 中的 `policy.allow_implicit_invocation: false`。未执行的平台保持未验证，不得填写通过结果。

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
- 是否实际发生其他 Skill / Plugin Invocation；如发生，记录名称、授权原文、用途和是否存在传递调用；
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
- [ ] EV-X01 至 EV-X04 均有可判定的预期结果；
- [ ] EV-A01 至 EV-A03 分别覆盖三个 Client，且不会跨 Client 复制证据；
- [ ] 证据结构要求记录实际的其他 Skill / Plugin Invocation；
- [ ] 不依赖尚未定义的脚本、平台能力或外部服务。

本阶段只设计 Eval，不执行 Eval，不填写虚假的通过结果。
