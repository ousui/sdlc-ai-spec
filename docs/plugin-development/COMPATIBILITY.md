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

验证日期：2026-08-31

| Client | Surface | Tested Version | Manifest | Manifest Validation | Skill Discovery | Explicit Invocation | Behavior Validation | Status | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| Cursor | IDE | Unknown | `.cursor-plugin/plugin.json` | Local static checks | Pending | Pending | Pending | `Pending first skill` | Runtime Contract Validator、JSON、路径和官方 schema 字段检查 | Marketplace 元数据已建立；尚未执行本地宿主加载 |
| Cursor | CLI | Unknown | `.cursor-plugin/plugin.json` | Local static checks | Unknown | Unknown | Unknown | `Pending first skill` | Runtime Contract Validator、JSON、路径和官方 schema 字段检查 | Marketplace 元数据已建立；CLI 可用性与插件行为需单独验证 |
| Claude Code | CLI | `2.1.204` | `.claude-plugin/plugin.json` | Native validator passed with warning and local static checks | Pending | Pending | Pending | `Pending first skill` | `claude plugin validate`、Runtime Contract Validator、JSON 与路径检查 | Marketplace 元数据已建立；严格校验受既有根级 `CLAUDE.md` 未作为 Plugin Context 加载的警告阻塞，尚未执行远程安装 |
| Codex | CLI | Local installed version | `.codex-plugin/plugin.json` | Local static checks | Pending | Pending | Pending | `Pending first skill` | Runtime Contract Validator、JSON、路径和 Plugin Creator schema 字段检查 | Marketplace 元数据已建立；Plugin Creator 自动校验器受本机缺少 PyYAML 阻塞，远程安装待仓库推送后验证 |
| Codex | Desktop / App | Unknown | `.codex-plugin/plugin.json` | Local static checks | Pending | Pending | Pending | `Pending first skill` | Runtime Contract Validator、JSON、路径和 Plugin Creator schema 字段检查 | Marketplace 元数据已建立；Plugin Creator 自动校验器受本机缺少 PyYAML 阻塞，尚未执行宿主安装与发现验证 |

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
