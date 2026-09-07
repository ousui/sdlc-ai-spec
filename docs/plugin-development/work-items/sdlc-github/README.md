# sdlc-github Work Item

`sdlc-github-foundation/v1` 已完成设计、实现、Mock/协议验证、真实 GitHub 定向验证与 Linux/macOS 回归，
Maintainer 于 2026-09-07 确认当前能力无阻塞问题。当前源码只保留仍有维护价值的文档：

| 文件 | 作用 |
|---|---|
| `DESIGN.md` | 已批准 v1 设计与固定边界 |
| `EVAL-PLAN.md` | 固定 Oracle 和验收条件 |
| `INSTALL.md` | 解释器绑定、稳定数据根与三宿主安装说明 |
| `HANDOFF.md` | 当前收口状态和唯一下一动作 |

正式运行时位于 `skills/sdlc-github/`、`packages/sdlc_github/`、`scripts/sdlc_github_mcp.py` 和
`config/github/`；固定测试位于 `tests/skill_github/`。Work Item 过程文档、旧 Goal、Repair/Revalidation/Portability
结果不再留在当前源码树，按 [全局归档索引](../../../maintenance/ARCHIVE.md) 的准确 Git 提交恢复。

用户使用从 `/sdlc-github status` 开始，完整命令见 [`SKILL.md`](../../../../skills/sdlc-github/SKILL.md)。
