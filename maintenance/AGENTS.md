# maintenance 目录约束

`maintenance/` 只保存 SDLC AI SPEC 源码仓库的长期维护运行手册和可视化说明，不属于产品 `dist`，不参与业务项目 000–500 生命周期。

- 可执行维护 Skill 的唯一 canonical 定义位于 `.agents/skills/sdlc-maintain-upgrade/SKILL.md`。
- 本目录不保存 `SKILL.md`、宿主适配器、确定性实现代码或产品 Runtime。
- 维护文档只能描述已实现的接口、状态、权限和运行流程；不得记录开发流水、个人工作记录、临时候选摘要或特定 CI 批次。
- 原始运行证据保存在 checkout 外或 PR 中，不提交到本目录。
- 维护文档不得替代或放宽 `tools/upgrade.py`、`tools/localize.py`、`tools/verify.py` 的程序检查。
- 修改维护入口或校验工具时，必须重新验证现有 11 个公共产品 Skill 的执行内容与 Runtime 未发生非预期变化。
