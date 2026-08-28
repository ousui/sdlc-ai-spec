# Shared Skills Source

本目录是 Cursor、Claude Code 和 Codex 共用的唯一 Skill 权威源码目录。

每个正式 Skill 使用以下结构：

```text
skills/<skill-name>/
├── SKILL.md
├── scripts/       # 可选：仅供该 Skill 使用的确定性脚本
├── references/    # 可选：按需加载的详细参考材料
├── assets/        # 可选：模板、静态资源或示例输入
└── evals/         # 可选：该 Skill 的评测案例与结果
```

规则：

- 当前目录尚无正式 Skill。
- 不创建示例、Hello 或其他无业务价值的占位 Skill。
- Skill 必须先完成设计，再进入实现和评测。
- Skill 私有资源保留在自己的目录内。
- 不在 `.cursor-plugin/`、`.claude-plugin/` 或 `.codex-plugin/` 下复制 Skill。
