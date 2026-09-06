# Skill 内容与样式约定 v1

适用于全部正式 `skills/sdlc-*/SKILL.md`；命名、命令、授权和领域语义仍由已有 Spec/Runtime Contract 决定。风格检查不能替代行为验证。

## 官方依据与本地选择

截至 2026-09-06，已阅读 Agent Skills 开放规范、OpenAI/Anthropic 官方 skill-creator 示例、Codex 与 Cursor 的 Skill 文档。共同做法是：YAML 元数据＋Markdown 操作指令、清楚的用途/触发条件、按需读取 scripts/references/assets，主文件保持简洁。

本仓库选择下述固定标题和表格，这是**项目一致性约定，不是所有 Agent 官方强制模板**。保留显式调用，不能为了“官方示例自动触发”而放宽权限。官方示例不授权改变本项目 Gate、Authority 或效果控制。

参考：
- https://agentskills.io/specification
- https://developers.openai.com/codex/skills/ （现重定向至官方 Build skills）
- https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md ，已读 Blob `72bc0b97e7a6476254a9d5c424c9971748402ec3`
- https://code.claude.com/docs/zh-CN/skills
- https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md ，已读 Blob `65b3a402dbd09b8e83f9d637c6b553875189085c`
- https://cursor.com/docs/skills

## 固定结构

YAML 保留 name、清晰中文 description、disable-model-invocation: true；目录与 name 一致。一个 H1 使用 `SDLC 编号 · 中文名称（缩写）`，Utility 无编号。Codex display_name 与 H1 一致，allow_implicit_invocation 保持 false。

七个 H2 顺序：适用范围 → 约定与边界 → 子命令 → 参数 → 执行流程 → 输出与完成条件 → 资源索引。目标 80–130 行，硬上限 200 行；超出时将详细表结构与算法放入 references，入口明确何时读取，不整包加载。

子命令表逐项对应 `references/interface.json` 的 name/description/writes，不手工发明命令。参数表列出公共长/短参数与实际阶段扩展；默认值、可重复性、准确引用和写入语义需要清晰。规范化用户参数与旧 JSON Runtime 的调用层不同，不把所有开关直接传给不接受它们的脚本。

流程写有序步骤：解析 → 权威读回/预检 → 组织内部输入 → 执行 → 读回/验证 → 输出/停止。保留阶段差异，不强迫 VFY 与 RLS 使用相同授权或结论。命令中的英文 ID/枚举保持原样。

JSON 输出不混入进度消息，不改写程序字段；summary/debug 依据实际结果，安全错误不泄漏 Secret。Skill 内不放开发历史、临时报告、逐轮 Goal、空目录或重复 Quick Reference。

## 新 Skill 与变更检查

从 `templates/SKILL.md.template` 起步；先定义合法 interface 与 Runtime，再填表。新增阶段扩展同时更新 `tools/validate_skill_style.py` 的参数契约及实际 parser 测试。必要时显式重建受影响 Source Lock，然后独立验证。运行 `python3 tools/validate_skill_style.py` 和统一 quick/full；模型行为或宿主差异根据实际使用反馈检查，不由样式检查伪造 PASS。
