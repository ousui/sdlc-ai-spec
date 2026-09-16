# SDLC AI SPEC 维护能力

`maintenance/` 只记录 SDLC AI SPEC 源码仓库自身的可复用维护说明，不属于已安装插件 Runtime，也不进入 `dist/`。

正式上游升级维护 Skill 为 `sdlc-maintain-upgrade`。唯一 canonical Skill 定义位于：

```text
.agents/skills/sdlc-maintain-upgrade/SKILL.md
```

Codex 与 Cursor 使用项目级 `.agents/skills/` 发现该 Skill。Claude Code 使用 `.claude/commands/sdlc-maintain-upgrade.md` 作为极薄兼容入口；该入口只负责读取同一 canonical Skill，不维护第二份升级流程。

该 Skill 必须显式调用。它默认完成“准确上游 → 差异审查 → detached candidate → 必要的受控增量本地化 → 独立三宿主 baseline → 完整 verifier → 差异报告”，并停在未提交的 verified candidate。正式 `accept`、提交、push、merge、tag 和 Release 需要独立授权。

升级工具的确定性事实与安全边界仍由 `tools/upgrade.py`、`tools/localize.py`、`tools/port.py`、`tools/build.py`、`tools/verify.py` 和仓库维护文档定义。Skill 不复制或放宽这些规则。

交互式升级流程图见 [UPGRADE-FLOW.html](UPGRADE-FLOW.html)。
