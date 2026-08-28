# Compatibility Matrix

## 状态定义

| 状态 | 含义 |
|---|---|
| `Verified` | 已在明确版本和运行载体上实际执行并保留证据 |
| `Partial` | 仅部分能力完成实际验证 |
| `Unknown` | 尚未验证或缺少可用验证入口 |
| `Unsupported` | 官方明确不支持 |
| `Pending first skill` | Manifest 已建立，但尚无正式 Skill 可供发现和行为验证 |

## 当前矩阵

验证日期：2026-08-28

| Client | Surface | Tested Version | Manifest | Manifest Validation | Skill Discovery | Explicit Invocation | Behavior Validation | Status | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| Cursor | IDE | Unknown | `.cursor-plugin/plugin.json` | Local static checks | Pending | Pending | Pending | `Pending first skill` | JSON、路径和公共元数据检查 | 尚未执行本地宿主加载 |
| Cursor | CLI | Unknown | `.cursor-plugin/plugin.json` | Unknown | Unknown | Unknown | Unknown | `Unknown` | None | CLI 可用性与插件行为需单独验证 |
| Claude Code | CLI | Local installed version | `.claude-plugin/plugin.json` | Native validator previously passed with optional metadata warning | Pending | Pending | Pending | `Pending first skill` | `claude plugin validate` 与本地静态检查 | 尚无正式 Skill |
| Codex | CLI | Local installed version | `.codex-plugin/plugin.json` | Local static checks | Pending | Pending | Pending | `Pending first skill` | JSON、路径和公共元数据检查 | 当前未发现独立 Manifest 校验子命令 |
| Codex | Desktop / App | Unknown | `.codex-plugin/plugin.json` | Local static checks | Pending | Pending | Pending | `Pending first skill` | JSON、路径和公共元数据检查 | Marketplace 或宿主安装尚未建立 |

## 证据要求

后续把状态提升为 `Verified` 时，至少记录：

- Client 与具体运行载体；
- 版本；
- 验证日期；
- 加载或安装方式；
- Skill 发现结果；
- 显式调用结果；
- 关键输入与输出；
- 行为验证结果；
- 证据文件或可复现命令。

不得根据一个 Client 的结果推断另一个 Client 同样通过。
