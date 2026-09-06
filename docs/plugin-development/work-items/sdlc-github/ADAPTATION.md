# 三个顺序适配子阶段

共用同一生产 Runtime，顺序为 Codex → Cursor → Claude Code。每个子阶段生成独立配置/安装副本，真实 stdio 到 Fake HTTP MCP 执行均在固定 test_installed_copy_three_sequential_host_configs 中完成。三端原生状态均为 NOT_RUN。

| Host | Manifest / 配置 | 程序验证 | 原生验证 |
|---|---|---|---|
| Codex | .codex-plugin/plugin.json → config/github/codex.mcp.json；env_vars 透传 | JSON/TOML 等价、单服务、剥离安装、同一 Service 读写/重启 | NOT_RUN |
| Cursor | .cursor-plugin/plugin.json → config/github/cursor.mcp.json；${env:SDLC_GITHUB_TOKEN} | 配置路径绑定、单服务、剥离安装、同一 Service 读写/重启 | NOT_RUN |
| Claude Code | .claude-plugin/plugin.json → config/github/claude-code.mcp.json；${SDLC_GITHUB_TOKEN} | 配置路径绑定、单服务、剥离安装、同一 Service 读写/重启 | NOT_RUN |

安装不写入宿主全局设置，不展开 Token，不保留工作区文档/测试/开发指令。数据根与代码目录分别绑定；代码路径变化后仍可读取同数据根回执。正式 Native 必须在真实客户端保存 discovery、显式调用、批准拒绝和行为证据，按 CLIENT-GOAL 一次执行。配置合法不是最终宿主兼容性结论；旧台账里的历史 PASS 也不属于本新增 Skill。
