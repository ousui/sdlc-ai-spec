# Skills Subtree Agent Instructions

## 1. 适用范围

本文件适用于 `skills/**`。它补充根目录 `AGENTS.md`，不替代领域 Spec、Plugin 开发标准或当前 Skill 的 Design Contract。

在修改任意 Skill 前，必须读取：

- 根目录 `AGENTS.md`；
- `docs/plugin-development/DEVELOPMENT.md`；
- `docs/plugin-development/SKILL-DEVELOPMENT-WORKFLOW.md`；
- `docs/plugin-development/HANDOFF.md`；
- 当前 Skill 的 `DESIGN.md` 和 `EVAL-PLAN.md`；
- Design 明确绑定的最小领域 Source of Truth。

## 2. 实现准入

创建或修改正式 `SKILL.md` 前必须同时满足：

- 当前工作包阶段为 `implement`、`evaluate`、`adapt` 或明确授权的修复阶段；
- `DESIGN.md` 状态至少为 `ready`；
- Maintainer 确认记录为 `approved`；
- 阻塞 Open Item 为零；
- `EVAL-PLAN.md` 可判定；
- 当前写入白名单包含目标 Skill 路径。

条件不满足时不得先写实现再补设计。

## 3. Skill 结构与单一职责

正式 Skill 使用：

```text
skills/<skill-name>/
├── SKILL.md
├── references/    # 按需
├── scripts/       # 按需
├── assets/        # 按需
└── evals/         # 按需
```

必须：

- 目录名使用稳定的 lowercase-hyphen 名称；
- 一个 Skill 只实现 Design Contract 中一个稳定用户意图；
- `SKILL.md` 保持短小，承载触发、核心流程、输入输出、失败语义和必要约束；
- 详细领域规则通过 `references/` 按需加载，不把完整 Spec 复制进 `SKILL.md`；
- 所有路径使用仓库相对或 Skill 相对路径；
- 不创建无业务价值的示例、Hello 或占位 Skill；
- 不把多个 Lifecycle Phase 粗暴合并为一个“大而全” Skill。

## 4. Trigger Contract

Skill 的名称和描述必须支持准确发现，并与 Design 中的正向、负向场景一致。

不得：

- 使用“处理所有研发工作”“任何情况下均应调用”等无边界描述；
- 为提高召回率而吞并相邻 Skill 意图；
- 把显式命令场景伪装为可靠自动触发；
- 在未评测前声称自动触发稳定；
- 通过平台专有字段改变三端共享语义。

触发不足或误触发应通过 Eval 证据修正，不凭直觉堆叠关键词。

## 5. 输入、输出与失败行为

Skill 必须：

- 只使用已提供、可解析或经授权读取的输入；
- 缺少必要事实时执行 Design 登记的等待、Open Item、失败或受限输出；
- 不从文件名、相似内容、历史会话或模型常识猜测业务身份；
- 明确区分生成结果、Validator 结果、人工确认和未解决风险；
- 不把 Artifact 已生成视为 Gate 已通过；
- 不在下游 Skill 中静默补造上游领域决定；
- 不把失败、部分完成或未知状态描述为成功。

## 6. References、Scripts 与 Assets

### References

- 每个 Reference 必须有明确使用条件；
- 优先引用权威文件，不复制形成第二份 Contract；
- 避免深层引用链；`SKILL.md` 应能直接定位所需 Reference；
- 不默认加载与当前场景无关的全部 Phase 或 Domain Spec。

### Scripts

只有确定性、可重复的操作才使用 Script，例如解析、Schema 校验、引用检查或格式转换。

Script 必须：

- 非交互式并使用明确退出码；
- 可从非固定工作目录调用；
- 不自动联网、安装依赖或修改全局配置；
- 不吞错、不伪造成功；
- 结构化输出稳定，诊断信息清楚；
- 默认不修改领域 Artifact；需要写入时必须由 Skill Contract 明确授权；
- 具有对应测试或 Fixture 后才作为 Gate 证据使用。

### Assets

- 只保存模板、静态资源或明确输入样例；
- 不把评测结果、临时输出或用户敏感数据当作 Asset；
- 不在 Asset 中预填虚构业务事实。

## 7. 可移植性

共享 Skill 是 Portable Core。

必须：

- 不依赖 Cursor、Claude Code 或 Codex 独有命令才能完成核心工作流；
- 平台增强缺失时仍保留明确的显式调用路径；
- 不在共享 `SKILL.md` 中写死插件安装位置；
- 不以一个平台的成功证明另外两个平台兼容；
- 平台适配只处理发现、元数据、路径和宿主能力，不改变输出 Contract 或失败语义。

## 8. Eval 约束

评测必须依据当前 `EVAL-PLAN.md`，并使用全新会话或隔离上下文。

至少分别记录：

- 应触发；
- 不应触发；
- 显式调用；
- 完整输入；
- 缺失输入；
- 边界或冲突；
- with-skill；
- without-skill。

禁止：

- 在设计或实现会话中用残留上下文冒充 Skill 能力；
- 修改预期结果以迁就实际失败；
- 只保留成功运行；
- 把人工提示补充后的结果记为自动触发成功；
- 为尚未执行的 Case 填写 `pass`；
- 用截图或总结替代可复现输入、输出定位和版本信息。

## 9. 完成前检查

结束本阶段前必须确认：

- 实现没有超出 Design Contract；
- 没有复制领域 Spec 或其他 Skill；
- 私有资源没有被提升为无依据的共享层；
- 所有相对路径和引用可解析；
- Script 和 Fixture 的实际检查已运行；
- 没有修改三个平台 Manifest，除非当前阶段明确为对应 Adapter；
- 没有修改 `docs/v1.0/`；
- `HANDOFF.md` 只登记一个下一工作包。
