# SDLC AI SPEC 维护运行手册

`maintenance/` 保存 SDLC AI SPEC 源码仓库的维护运行手册和可视化说明。该目录不包含可执行 Skill 定义，不属于安装后的插件 Runtime，也不进入 `dist/`。

## 维护架构

| 层级 | 位置 | 职责 |
| --- | --- | --- |
| Agent 维护入口 | `.agents/skills/sdlc-maintain-upgrade/` | `sdlc-maintain-upgrade` 的唯一 canonical Skill 定义及其执行期 references |
| Claude Code 适配 | `.claude/commands/sdlc-maintain-upgrade.md` | 加载同一 canonical Skill，不维护独立流程正文 |
| 确定性工具 | `tools/` | 上游候选、本地化、构建、验证及摘要计算 |
| 维护运行手册 | `maintenance/` | 维护边界、流程图和面向维护者的长期说明 |
| 工程规范 | `docs/` | 开发、本地化、升级、命名和验证契约 |
| 用户产品 | `dist/` | 安装后的 11 个公共 Skill 与 Runtime |

## `sdlc-maintain-upgrade`

该 Skill 只能显式调用，并且只维护 SDLC AI SPEC 源码仓库本身。默认流程为：

```text
准确上游 → 差异审查 → detached candidate
          → 必要的受控增量本地化
          → 三宿主独立 baseline → 完整 verifier
          → VERIFIED_CANDIDATE_READY / REVIEW_REQUIRED / BLOCKED
```

默认终点是已验证、未提交的 detached candidate 和差异报告。正式 `accept`、提交、push、merge、tag、Release 以及真实业务项目迁移均属于独立授权操作。

确定性事实与安全边界由 `tools/upgrade.py`、`tools/localize.py`、`tools/port.py`、`tools/build.py`、`tools/verify.py` 及对应 `docs/` 规范定义。维护 Skill 只编排这些能力，不复制或放宽其规则。

完整流程见 [UPGRADE-FLOW.html](UPGRADE-FLOW.html)。
