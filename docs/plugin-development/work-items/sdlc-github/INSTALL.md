# sdlc-github — 安装与离线使用

本候选使用批准设计 `97c5f17bfcdb2751d446a89b068db2400436631d`。安装不是原生宿主验收；三个宿主实际执行另见唯一 `CLIENT-GOAL.md`。

## 1. 环境与依赖

首版支持目标为 Python 3.12/3.13、POSIX 文件系统（Linux/macOS）。Web 实测环境是 Linux + Python 3.13；macOS 与三个本地宿主未在 Web 实测。Windows 缺少本期使用的 POSIX 安全文件接口时失败关闭，不以较弱路径实现降级。

在独立源码工作树执行；虚拟环境与结果目录放在工作树外。以下是主动安装命令，不是 Runtime 启动行为：

```bash
export SOURCE="$(pwd -P)"
export GH_WORK="$(dirname "$SOURCE")/sdlc-github-client"
mkdir -p "$GH_WORK"
python3 -m venv "$GH_WORK/venv"
export PY="$GH_WORK/venv/bin/python"
"$PY" -m pip install --require-hashes -r "$SOURCE/packages/sdlc_github/requirements.lock"
"$PY" "$SOURCE/scripts/sdlc_github_mcp.py" --check-install
```

锁定 MCP SDK `1.26.0` 及全部传递依赖的版本和 SHA-256。完整环境版本逐项核对；现有环境中一个包版本不匹配即阻断，不静默兼容。安装期间可以由用户的包管理器联网；Runtime 不安装任何东西。不要使用包含其他项目依赖的公共 Python 环境。

## 2. 离线验证

以下两层不需要真实 Token，不连接 GitHub。integration 使用真正的 stdio 子进程与 HTTP 服务，但 HTTP 目标仅为测试独立进程的 loopback Fake MCP。

```bash
"$PY" tests/skill_github/validate.py --layer offline --output "$GH_WORK/offline"
"$PY" tests/skill_github/validate.py --layer integration --output "$GH_WORK/integration"
```

两者在测试内清空真实 Token 环境，只注入 synthetic fixture 值。结果为 `VALIDATION.json`、逐案例状态、unittest.log、协议证据和 `SHA256SUMS.json`。`PASS` 只表示该层 Oracle 通过，不代表真实 GitHub/原生宿主通过。退出码 0=PASS、1=FAIL、2=BLOCKED。

## 3. 三端顺序生成安装副本

每个目标目录必须不存在；安装器不覆盖旧安装、不迁移用户数据、不改任何宿主全局设置。版本化代码路径与稳定数据根分离。三个宿主依次执行同一个安装器：

```bash
for host in codex cursor claude-code; do
  "$PY" tools/install_sdlc_github.py --host "$host" \
    --destination "$GH_WORK/installed/$host" \
    --data-root "$GH_WORK/data/$host" --python "$PY"
done
```

安装器将一个共享 Runtime 复制到三个独立目录；无业务实现分叉。每份选定 manifest 的 `mcpServers` 指向对应 `config/github/<host>.mcp.json`，并已替换为准确解释器、代码路径和稳定数据根。`INSTALL.json` 记录安装文件摘要和依赖检查，不记录凭据。

分发副本排除 docs、开发 AGENTS/CLAUDE、tests/evals、.git、.local、.cache 及字节码。安装后的 Runtime 不读这些文件。其他既有 Skill 不需要此 MCP 或 PAT 就可继续执行。

## 4. 原生注册与环境

Codex：manifest 引用 JSON MCP 文件，`env_vars=["SDLC_GITHUB_TOKEN"]` 从启动进程环境透传。另生成 `codex.standalone.toml`，仅供不使用插件的独立 MCP 注册作为替代；不能同时注册两份。独立 MCP 注册本身不证明 Skill/Plugin 发现成功。

Cursor：manifest 引用 JSON MCP 文件，env 值为 `${env:SDLC_GITHUB_TOKEN}`。Claude Code：对应值为 `${SDLC_GITHUB_TOKEN}`。Claude 可使用 `claude --plugin-dir "$GH_WORK/installed/claude-code"` 在单会话加载本地插件，插件 Skill 名称可能显示为 `/sdlc-ai-spec:sdlc-github`；以真实发现结果为准。Codex/Cursor 应在当前版本的原生插件管理界面加载该准确目录/本地 marketplace；如果该客户端不支持本地目录导入，记录安装阻塞，不虚构命令或改用 SDK 测试声称通过。

原生安装、会话信任与工具批准保持宿主自己的机制；禁止全局自动允许、跳过权限或把模型文本当作批准。每份安装只应发现一个 `sdlc_github` 服务。依赖检查和工具发现不访问远端；只有显式在线调用建立官方 MCP 连接。

安全注入由用户完成：在将要启动该宿主的终端/安全环境中配置 `SDLC_GITHUB_TOKEN`，不粘贴到 Skill 业务参数、配置 JSON、命令行参数或证据。换 Token 后重启对应进程。GUI 启动环境可能不继承 shell 环境，须在真实客户端核验，不用静态配置正确替代行为证据。

首次实际调用 `sdlc_github_status {}` 取得 actor.id；写工具使用此值做一致性检查。它不是授权凭证。未知副作用只执行 `sdlc_github_operation_status` 的只读核对，不重放或改 UUID 掩盖原请求。

## 5. 发布边界

不要直接发布含 `/ABS/` 模板的源码目录当作即插即用包。先生成绑定路径的安装副本。代码目录移动后应在明确安装任务中重新绑定配置，但必须复用既有稳定数据根；不得删除 .local 回执。清除 .cache 不改变已执行请求的历史。

Hosted GitHub MCP 不能由本地 SDK 版本锁定；所需工具/参数漂移时返回 CAPABILITY_UNAVAILABLE，由真实验证报告登记，不增加 REST fallback。

## 官方核对来源

- GitHub MCP v1.12.0 操作目录：https://github.com/github/github-mcp-server/blob/v1.12.0/README.md
- 官方 Python SDK：https://github.com/modelcontextprotocol/python-sdk
- Codex MCP：https://developers.openai.com/codex/mcp
- Codex 官方插件 manifest 示例：https://github.com/openai/plugins/blob/main/plugins/notion/.codex-plugin/plugin.json
- Cursor MCP：https://cursor.com/docs/mcp
- Cursor 插件 manifest：https://cursor.com/docs/reference/plugins
- Claude Code MCP：https://code.claude.com/docs/en/mcp
- Claude Code Plugin Reference：https://code.claude.com/docs/en/plugins-reference

这些来源用于构建期核对；安装后不加载文档。实际版本、批准与调用行为必须在本地取证。
