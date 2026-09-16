# maintenance 目录约束

本目录只保存 SDLC AI SPEC 源码仓库自身的可复用维护说明和流程图，不属于产品 `dist`，不参与业务项目 000–500 生命周期。

- `sdlc-maintain-upgrade` 的唯一 canonical 指令位于仓库根 `.agents/skills/sdlc-maintain-upgrade/SKILL.md`。
- 不在本目录复制第二份 `SKILL.md`，避免不同宿主加载不同版本。
- 维护文档可以解释工具和流程，但不能成为绕过 `tools/upgrade.py` / `tools/localize.py` / `tools/verify.py` 检查的替代实现。
- 不把具体某次升级的原始日志、个人工作记录、临时候选摘要或 CI 批次证据提交到本目录；这些证据保存在 checkout 外或 PR 中。
- 修改维护 Skill 或校验工具时，必须重新证明现有 11 个公共产品 Skill 的执行内容未被改变。
